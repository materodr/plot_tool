"""Tests for the pan by a two-finger swipe (HLFR-00036, HLFR-00027:
LLFR-00345, LLFR-00346, needs PyQt6).

Real QWheelEvents are sent to the canvas of a shown plot widget (time
plot from 0 s to 10 s, or frequency plot from 0 Hz to 25 Hz): a
sideways swipe pans by as many screen pixels as it moves, in the
physical direction of the fingers on macOS whatever the natural
scrolling setting, within the file's range; a mostly vertical event
only zooms, as before. The end-to-end tests send the swipe to a plot of
the main window with the real controllers: the time plots of the tab
follow, a frequency plot pans alone. No modal dialog is ever opened.
"""

import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt
from tests.view.test_frequency_plots_view import (
    FrequencyPlotEndToEndTest, FrequencyPlotWidgetTest)
from tests.view.test_navigation import NavigationEndToEndTest
from tests.view.test_plot_tools import ALL_TOOL_TUPLE, PlotWidgetToolTestCase

from controller.plot_tools import MARKER_TOOL_STR, NO_TOOL_STR

# Allowed error, in widget pixels, on where a time is drawn after a pan
# (the widget points are whole pixels).
PIXEL_TOLERANCE_F = 1.5


def make_swipe_event(canvas, local_point, pixel_x_i: int, pixel_y_i: int,
                     angle_x_i: int, angle_y_i: int, inverted_b: bool,
                     phase_name_str: str = "ScrollUpdate",
                     shift_b: bool = False):
    """Build a real QWheelEvent for a canvas, as a trackpad or a mouse
    sends it.

    Inputs:
        canvas: the matplotlib canvas widget.
        local_point: QPoint in the canvas' coordinates.
        pixel_x_i: horizontal pixelDelta (0 for none).
        pixel_y_i: vertical pixelDelta (0 for none).
        angle_x_i: horizontal angleDelta in eighths of a degree.
        angle_y_i: vertical angleDelta in eighths of a degree.
        inverted_b: the value of QWheelEvent.inverted() (natural
            scrolling).
        phase_name_str: name of the Qt.ScrollPhase ("NoScrollPhase" for
            a mouse wheel).
        shift_b: True to hold the Shift modifier.
    Outputs: the QWheelEvent.
    """
    from PyQt6.QtCore import QPoint, QPointF, Qt
    from PyQt6.QtGui import QWheelEvent
    position = QPointF(local_point)
    modifier = (Qt.KeyboardModifier.ShiftModifier if shift_b
                else Qt.KeyboardModifier.NoModifier)
    return QWheelEvent(
        position, QPointF(canvas.mapToGlobal(position)),
        QPoint(pixel_x_i, pixel_y_i), QPoint(angle_x_i, angle_y_i),
        Qt.MouseButton.NoButton, modifier,
        getattr(Qt.ScrollPhase, phase_name_str), inverted_b)


def send_swipe(application, plot_widget, widget_point, pixel_x_i: int,
               pixel_y_i: int = 0, angle_x_i: int = 0, angle_y_i: int = 0,
               inverted_b: bool = False,
               phase_name_str: str = "ScrollUpdate",
               shift_b: bool = False) -> None:
    """Send a QWheelEvent to a plot widget's canvas at a widget point.

    Inputs:
        application: the QApplication.
        plot_widget: the PlotWidget.
        widget_point: QPoint in the plot widget's coordinates.
        pixel_x_i, pixel_y_i: the pixelDelta.
        angle_x_i, angle_y_i: the angleDelta.
        inverted_b: the value of QWheelEvent.inverted().
        phase_name_str: name of the Qt.ScrollPhase.
        shift_b: True to hold the Shift modifier.
    Outputs: none.
    """
    canvas = plot_widget.canvas
    local_point = canvas.mapFrom(plot_widget, widget_point)
    application.sendEvent(canvas, make_swipe_event(
        canvas, local_point, pixel_x_i, pixel_y_i, angle_x_i, angle_y_i,
        inverted_b, phase_name_str, shift_b))
    application.processEvents()


@requires_qt
class SwipeClassifyTest(PlotWidgetToolTestCase):
    """The module functions that read a wheel event."""

    def event(self, pixel_x_i: int, pixel_y_i: int, angle_x_i: int,
              angle_y_i: int, inverted_b: bool = False,
              phase_name_str: str = "ScrollUpdate", shift_b: bool = False):
        """Build a QWheelEvent at the middle of the plot.

        Inputs: as make_swipe_event.
        Outputs: the QWheelEvent.
        """
        canvas = self.plot_widget.canvas
        local_point = canvas.mapFrom(self.plot_widget, self.point_at(5.0))
        return make_swipe_event(canvas, local_point, pixel_x_i, pixel_y_i,
                                angle_x_i, angle_y_i, inverted_b,
                                phase_name_str, shift_b)

    @covers("LLFR-00346")
    def test_larger_component_chooses_pan_or_zoom(self) -> None:
        """An event pans only when it moves more horizontally than
        vertically; the pixel delta decides when there is one.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import is_horizontal_swipe
        for arguments_tuple, expected_b in (
                ((30, 0, 0, 0), True), ((-30, 29, 0, 0), True),
                ((30, 30, 0, 0), False), ((10, -40, 0, 0), False),
                ((0, 0, 120, 0), True), ((0, 0, -120, 119), True),
                ((0, 0, 0, 120), False), ((0, 0, 60, -60), False),
                ((0, 0, 0, 0), False),
                # The pixel delta wins over the angle delta.
                ((5, 50, 120, 0), False), ((50, 5, 0, 120), True)):
            with self.subTest(arguments=arguments_tuple):
                self.assertEqual(is_horizontal_swipe(
                    self.event(*arguments_tuple)), expected_b)

    @covers("LLFR-00345", "LLFR-00206")
    def test_swipe_pixels_in_the_physical_direction(self) -> None:
        """On macOS the inverted delta of natural scrolling is turned
        back; elsewhere the delta is kept; an angle delta counts one
        pixel per eighth of a degree.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_widget as plot_widget_module
        from view.plot_widget import swipe_pixels_f
        with mock.patch.object(plot_widget_module, "RUNNING_ON_MACOS_B",
                               True):
            for arguments_tuple, expected_px in (
                    ((-60, 0, 0, 0, False), -60.0),
                    ((60, 0, 0, 0, True), -60.0),
                    ((60, 0, 0, 0, False), 60.0),
                    ((0, 0, -120, 0, False), -120.0),
                    ((0, 0, -120, 0, True), 120.0)):
                with self.subTest(arguments=arguments_tuple):
                    self.assertEqual(swipe_pixels_f(
                        self.event(*arguments_tuple)), expected_px)
        with mock.patch.object(plot_widget_module, "RUNNING_ON_MACOS_B",
                               False):
            for inverted_b in (True, False):
                self.assertEqual(swipe_pixels_f(
                    self.event(60, 0, 0, 0, inverted_b)), 60.0)

    @covers("LLFR-00345", "LLFR-00154")
    def test_trackpad_is_told_from_a_mouse(self) -> None:
        """A trackpad reports a pixel delta or a scroll phase; only a
        sideways Shift+wheel of a mouse is the Shift zoom.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import (
            is_shift_horizontal_wheel, is_trackpad_wheel)
        self.assertTrue(is_trackpad_wheel(self.event(10, 0, 0, 0)))
        self.assertTrue(is_trackpad_wheel(self.event(0, 0, 120, 0)))
        self.assertFalse(is_trackpad_wheel(self.event(
            0, 0, 120, 0, phase_name_str="NoScrollPhase")))
        self.assertTrue(is_shift_horizontal_wheel(self.event(
            0, 0, 120, 0, phase_name_str="NoScrollPhase", shift_b=True)))
        self.assertFalse(is_shift_horizontal_wheel(self.event(
            0, 0, 120, 0, shift_b=True)))
        self.assertFalse(is_shift_horizontal_wheel(self.event(
            12, 0, 120, 0, phase_name_str="NoScrollPhase", shift_b=True)))


@requires_qt
class SwipePanWidgetTest(PlotWidgetToolTestCase):
    """Swipes sent to the canvas of the 600x400 time plot (0 s to 10 s)."""

    def zoom_to(self, start_s: float, end_s: float) -> None:
        """Show a time range and draw it, so coordinates are final.

        Inputs:
            start_s: start of the range, in seconds.
            end_s: end of the range, in seconds.
        Outputs: none.
        """
        self.plot_widget.set_time_range(start_s, end_s)
        self.draw()
        self.range_list.clear()

    def swipe(self, pixel_x_i: int, **keyword_dict) -> None:
        """Send a swipe at the middle of the plot and draw.

        Inputs:
            pixel_x_i: horizontal pixelDelta.
            keyword_dict: other arguments of send_swipe.
        Outputs: none.
        """
        send_swipe(self.application, self.plot_widget, self.point_at(5.0),
                   pixel_x_i, **keyword_dict)
        self.draw()

    def assert_curves_moved(self, time_s: float, x_before_i: int,
                            expected_shift_px: float) -> None:
        """Check where a time is drawn after a pan.

        Inputs:
            time_s: a time, in seconds.
            x_before_i: the widget x of that time before the pan.
            expected_shift_px: how far right (widget pixels) it must be
                drawn now.
        Outputs: none.
        """
        x_after_i = self.point_at(time_s).x()
        self.assertAlmostEqual(x_after_i - x_before_i, expected_shift_px,
                               delta=PIXEL_TOLERANCE_F)

    @covers("LLFR-00345", "LLFR-00070", "LLFR-00120")
    def test_swipe_moves_the_curves_by_its_pixels(self) -> None:
        """The curves move by the swipe's pixel delta, the width is
        kept and the new range is reported for the tab.

        Inputs: none.
        Outputs: none.
        """
        for pixel_x_i in (-60, 60, -7, 150):
            with self.subTest(pixel=pixel_x_i):
                self.zoom_to(3.0, 7.0)
                x_before_i = self.point_at(5.0).x()
                self.swipe(pixel_x_i)
                # Off macOS the delta is physical: negative is fingers
                # right, so the curves move right.
                self.assert_curves_moved(5.0, x_before_i, -pixel_x_i)
                start_s, end_s = self.plot_widget.time_range_tuple()
                self.assertAlmostEqual(end_s - start_s, 4.0)
                self.assertEqual(self.range_list, [(start_s, end_s)])

    @covers("LLFR-00345", "LLFR-00206")
    def test_curves_follow_the_fingers_with_any_natural_setting(
            self) -> None:
        """On macOS, fingers moving right move the curves right with or
        without natural scrolling, and left moves them left.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_widget as plot_widget_module
        with mock.patch.object(plot_widget_module, "RUNNING_ON_MACOS_B",
                               True):
            # (reported pixel delta, inverted, curve shift to the right)
            for pixel_x_i, inverted_b, expected_shift_px in (
                    (-80, False, 80.0), (80, True, 80.0),
                    (80, False, -80.0), (-80, True, -80.0)):
                with self.subTest(pixel=pixel_x_i, inverted=inverted_b):
                    self.zoom_to(3.0, 7.0)
                    x_before_i = self.point_at(5.0).x()
                    self.swipe(pixel_x_i, inverted_b=inverted_b)
                    self.assert_curves_moved(5.0, x_before_i,
                                             expected_shift_px)

    @covers("LLFR-00345")
    def test_angle_only_swipe_counts_one_pixel_per_eighth(self) -> None:
        """A sideways event without a pixel delta (a Windows touchpad or
        a tilted wheel) pans by one pixel per eighth of a degree.

        Inputs: none.
        Outputs: none.
        """
        for phase_name_str in ("ScrollUpdate", "NoScrollPhase"):
            with self.subTest(phase=phase_name_str):
                self.zoom_to(3.0, 7.0)
                x_before_i = self.point_at(5.0).x()
                self.swipe(0, angle_x_i=-120, phase_name_str=phase_name_str)
                self.assert_curves_moved(5.0, x_before_i, 120.0)

    @covers("LLFR-00346", "LLFR-00345", "LLFR-00074", "LLFR-00113")
    def test_diagonal_swipe_either_pans_or_zooms(self) -> None:
        """A mostly sideways diagonal swipe only pans (width kept); a
        mostly vertical or exactly diagonal one only zooms around the
        pointer (the time under it stays put).

        Inputs: none.
        Outputs: none.
        """
        self.zoom_to(3.0, 7.0)
        x_before_i = self.point_at(5.0).x()
        self.swipe(-50, pixel_y_i=40, angle_x_i=-50, angle_y_i=40)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(end_s - start_s, 4.0)
        self.assert_curves_moved(5.0, x_before_i, 50.0)
        for pixel_x_i, pixel_y_i in ((40, 50), (60, 60), (-30, 60)):
            with self.subTest(pixel_x=pixel_x_i, pixel_y=pixel_y_i):
                self.zoom_to(3.0, 7.0)
                center_s = self.plot_widget.time_at(self.point_at(5.0))
                self.swipe(pixel_x_i, pixel_y_i=pixel_y_i,
                           angle_x_i=pixel_x_i, angle_y_i=pixel_y_i)
                start_s, end_s = self.plot_widget.time_range_tuple()
                factor_f = 0.95 ** (pixel_y_i / 120.0)
                self.assertAlmostEqual(end_s - start_s, 4.0 * factor_f)
                self.assertAlmostEqual(
                    start_s, center_s + (3.0 - center_s) * factor_f)

    @covers("LLFR-00074", "LLFR-00113", "LLFR-00206", "LLFR-00346")
    def test_vertical_mouse_wheel_still_zooms(self) -> None:
        """A mouse wheel with only a vertical rotation zooms by 95% per
        notch as before, in the physical direction on macOS.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_widget as plot_widget_module
        for macos_b, angle_y_i, inverted_b, expected_width_s in (
                (False, 120, False, 4.0 * 0.95),
                (False, -120, False, 4.0 / 0.95),
                (False, 240, True, 4.0 * 0.95 ** 2),
                (True, -120, True, 4.0 * 0.95),
                (True, 120, False, 4.0 * 0.95)):
            with self.subTest(macos=macos_b, angle=angle_y_i,
                              inverted=inverted_b):
                with mock.patch.object(plot_widget_module,
                                       "RUNNING_ON_MACOS_B", macos_b):
                    self.zoom_to(3.0, 7.0)
                    self.swipe(0, angle_y_i=angle_y_i,
                               inverted_b=inverted_b,
                               phase_name_str="NoScrollPhase")
                    start_s, end_s = self.plot_widget.time_range_tuple()
                    self.assertAlmostEqual(end_s - start_s,
                                           expected_width_s)

    @covers("LLFR-00345", "LLFR-00119", "LLFR-00120")
    def test_swipe_stops_at_the_first_and_last_sample(self) -> None:
        """A long swipe stops at the file's range, keeps the width and
        fits the y-axis to the shown range.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_to(1.0, 5.0)
        self.swipe(-5000)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 0.0)
        self.assertAlmostEqual(end_s, 4.0)
        self.swipe(9000)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 6.0)
        self.assertAlmostEqual(end_s, 10.0)
        # LLFR-00120: y is fitted as for the same range set directly.
        y_limits_tuple = tuple(self.plot_widget.axes.get_ylim())
        self.plot_widget.set_time_range(6.0, 10.0)
        self.assertEqual(tuple(self.plot_widget.axes.get_ylim()),
                         y_limits_tuple)
        # A swipe further out at the limit changes nothing.
        self.range_list.clear()
        self.swipe(300)
        self.assertEqual(self.range_list, [])

    @covers("LLFR-00345", "LLFR-00118")
    def test_no_pan_at_the_whole_range(self) -> None:
        """At the whole time range a swipe neither pans nor zooms.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_to(0.0, 10.0)
        for pixel_x_i in (-100, 100):
            self.swipe(pixel_x_i, pixel_y_i=10)
        self.assertEqual(self.plot_widget.time_range_tuple(), (0.0, 10.0))
        self.assertEqual(self.range_list, [])

    @covers("LLFR-00345", "LLFR-00108")
    def test_swipe_pans_with_every_tool_and_none(self) -> None:
        """The swipe pans whatever plot tool is active, and does nothing
        else (no tip pinned, no marker placed).

        Inputs: none.
        Outputs: none.
        """
        marker_list = []
        self.plot_widget.marker_place_requested.connect(
            lambda *arguments: marker_list.append(arguments))
        for tool_str in ALL_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.zoom_to(3.0, 7.0)
                x_before_i = self.point_at(5.0).x()
                self.swipe(-40)
                self.assert_curves_moved(5.0, x_before_i, 40.0)
        self.assertEqual(self.pin_list, [])
        self.assertEqual(marker_list, [])

    @covers("LLFR-00345", "LLFR-00346", "LLFR-00154", "LLFR-00074")
    def test_shift_swipe_pans_and_shift_mouse_wheel_zooms(self) -> None:
        """With Shift held (Vertical marker tool), a trackpad swipe
        still pans, while the sideways Shift+wheel of a mouse zooms.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.zoom_to(3.0, 7.0)
        x_before_i = self.point_at(5.0).x()
        self.swipe(-40, angle_x_i=-40, shift_b=True)
        self.assert_curves_moved(5.0, x_before_i, 40.0)
        self.zoom_to(3.0, 7.0)
        self.swipe(0, angle_x_i=120, phase_name_str="NoScrollPhase",
                   shift_b=True)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(end_s - start_s, 4.0 * 0.95)

    @covers("LLFR-00345", "LLFR-00117")
    def test_swipe_waits_during_a_wheel_button_pan(self) -> None:
        """While the wheel button pans, a swipe moves nothing, so the
        grabbed time stays under the pointer.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        self.zoom_to(3.0, 7.0)
        self.plot_widget.pan_press_at(self.point_at(5.0))
        self.swipe(-100)
        self.assertEqual(self.plot_widget.time_range_tuple(), (3.0, 7.0))
        self.plot_widget.pan_release_at(self.point_at(5.0))
        self.assertEqual(self.plot_widget.time_range_tuple(), (3.0, 7.0))


@requires_qt
class SwipeFrequencyWidgetTest(FrequencyPlotWidgetTest):
    """Swipes on a frequency plot (0 Hz to 25 Hz) on its own."""

    def setUp(self) -> None:
        """Create the frequency plot and record its range changes.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.range_list = self.recorder(self.plot_widget.time_range_changed)

    @covers("LLFR-00345", "LLFR-00258", "LLFR-00118", "LLFR-00119")
    def test_swipe_stays_in_the_frequency_range(self) -> None:
        """A swipe pans a zoomed frequency plot by its pixels, between
        0 Hz and the highest frequency, and not at the whole range.

        Inputs: none.
        Outputs: none.
        """
        middle_point = self.plot_widget.data_to_widget_point(12.5, 0.0)
        send_swipe(self.application, self.plot_widget, middle_point, -100)
        self.assertEqual(self.range_list, [])
        self.plot_widget.set_time_range(10.0, 15.0)
        self.draw()
        x_before_i = self.plot_widget.data_to_widget_point(12.5, 0.0).x()
        send_swipe(self.application, self.plot_widget, middle_point, -50)
        self.draw()
        x_after_i = self.plot_widget.data_to_widget_point(12.5, 0.0).x()
        self.assertAlmostEqual(x_after_i - x_before_i, 50.0,
                               delta=PIXEL_TOLERANCE_F)
        send_swipe(self.application, self.plot_widget, middle_point, -9000)
        self.assertAlmostEqual(self.range_list[-1][0], 0.0)
        self.assertAlmostEqual(self.range_list[-1][1], 5.0)
        send_swipe(self.application, self.plot_widget, middle_point, 9000)
        self.assertAlmostEqual(self.range_list[-1][0], 20.0)
        self.assertAlmostEqual(self.range_list[-1][1], 25.0)


@requires_qt
class SwipeEndToEndTest(unittest.TestCase):
    """Swipes on the plots of the main window with the controllers."""

    @covers("LLFR-00345", "LLFR-00070", "LLFR-00120")
    def test_swipe_is_shared_by_the_time_plots(self) -> None:
        """A swipe in one time plot moves every time plot of the tab.

        Inputs: none.
        Outputs: none.
        """
        window_test = NavigationEndToEndTest("zoom_current_tab")
        window_test.setUp()
        self.addCleanup(window_test.tearDown)
        window_test.zoom_current_tab()
        first_widget, second_widget = window_test.plot_widgets()
        start_s, end_s = first_widget.time_range_tuple()
        width_s = end_s - start_s
        axes_width_px = (first_widget.axes.bbox.width
                         / first_widget.pixel_ratio_f())
        middle_point = first_widget.data_to_widget_point(
            start_s + width_s / 2.0, 0.0)
        send_swipe(get_qt_application(), first_widget, middle_point, 30)
        window_test.process_events()
        new_start_s, new_end_s = first_widget.time_range_tuple()
        self.assertAlmostEqual(new_start_s,
                               start_s + 30.0 * width_s / axes_width_px)
        self.assertAlmostEqual(new_end_s - new_start_s, width_s)
        self.assertEqual(second_widget.time_range_tuple(),
                         (new_start_s, new_end_s))

    @covers("LLFR-00345", "LLFR-00258")
    def test_frequency_plot_pans_alone(self) -> None:
        """A swipe on a frequency plot leaves the time plot alone, and a
        swipe on the time plot leaves the frequency plot alone.

        Inputs: none.
        Outputs: none.
        """
        window_test = FrequencyPlotEndToEndTest("create_fft")
        window_test.setUp()
        self.addCleanup(window_test.tearDown)
        application = get_qt_application()
        fft_name_str = window_test.create_fft()
        time_widget = window_test.double_click("Torque")
        frequency_widget = window_test.double_click(fft_name_str)
        time_widget.wheel_at(time_widget.data_to_widget_point(5.0, 0.0),
                             4.0)
        frequency_widget.wheel_at(
            frequency_widget.data_to_widget_point(12.0, 0.0), 4.0)
        application.processEvents()
        for plot_widget in (time_widget, frequency_widget):
            plot_widget.canvas.draw()
        time_range_tuple = time_widget.time_range_tuple()
        frequency_range_tuple = frequency_widget.time_range_tuple()
        send_swipe(application, frequency_widget,
                   frequency_widget.data_to_widget_point(12.0, 0.0), 40)
        self.assertEqual(time_widget.time_range_tuple(), time_range_tuple)
        moved_frequency_tuple = frequency_widget.time_range_tuple()
        self.assertGreater(moved_frequency_tuple[0],
                           frequency_range_tuple[0])
        send_swipe(application, time_widget,
                   time_widget.data_to_widget_point(5.0, 0.0), -40)
        self.assertLess(time_widget.time_range_tuple()[0],
                        time_range_tuple[0])
        self.assertEqual(frequency_widget.time_range_tuple(),
                         moved_frequency_tuple)


if __name__ == "__main__":
    unittest.main()
