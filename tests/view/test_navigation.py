"""Tests for zoom steps, reset zoom, pan and grid (HLFR-00027,
HLFR-00035, HLFR-00036, HLFR-00037).

Covers the 5% wheel and click zoom steps, the Reset zoom action button
and its feedback, the pan with the wheel button held, and the Grid
toggle button, in a plot widget and through MainWindow with the real
controllers. No modal dialog or menu is ever opened.
"""

import time
import unittest

import numpy as np

from tests.support import covers, get_qt_application, requires_qt
from tests.view.test_plot_tools import (
    ALL_TOOL_TUPLE, PlotWidgetToolTestCase, recorder)

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, PLOT_TOOL_TUPLE, TIP_TOOL_STR,
    ZOOM_TOOL_STR)

# LLFR-00116: the shortest active time of the Reset zoom button.
MINIMUM_ACTIVE_TIME_S = 0.3
# How long a test waits at most for a button to turn normal.
MAXIMUM_WAIT_TIME_S = 3.0
# Allowed pixel rounding error, in seconds, in a 10 s wide plot.
PIXEL_TOLERANCE_S = 0.03


class FakeAngleDelta:
    """Stand-in for the QPoint returned by QWheelEvent.angleDelta."""

    def __init__(self, eighths_i: int) -> None:
        """Store the vertical rotation.

        Inputs:
            eighths_i: rotation in eighths of a degree.
        Outputs: none.
        """
        self.eighths_i = eighths_i

    def y(self) -> int:
        """Return the vertical rotation.

        Inputs: none.
        Outputs: the rotation in eighths of a degree.
        """
        return self.eighths_i


class FakeWheelEvent:
    """Stand-in for a QWheelEvent that only offers angleDelta."""

    def __init__(self, eighths_i: int) -> None:
        """Store the vertical rotation.

        Inputs:
            eighths_i: rotation in eighths of a degree.
        Outputs: none.
        """
        self.eighths_i = eighths_i

    def angleDelta(self) -> FakeAngleDelta:
        """Return the rotation, as QWheelEvent does.

        Inputs: none.
        Outputs: a FakeAngleDelta.
        """
        return FakeAngleDelta(self.eighths_i)


class FakeScrollEvent:
    """Stand-in for a matplotlib scroll MouseEvent."""

    def __init__(self, step_f: float, gui_event=None) -> None:
        """Store matplotlib's step and the Qt event.

        Inputs:
            step_f: matplotlib's step value.
            gui_event: the Qt event, or None.
        Outputs: none.
        """
        self.step = step_f
        self.guiEvent = gui_event


class NavigationWidgetTestCase(PlotWidgetToolTestCase):
    """Base class: the 600x400 plot widget with the wheel button events."""

    def setUp(self) -> None:
        """Create the plot widget and record the marker requests.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.marker_place_list = recorder(
            self.plot_widget.marker_place_requested)

    def display_x_px(self, time_s: float) -> float:
        """Return the display x of a time with the current x range.

        Inputs:
            time_s: x value in seconds.
        Outputs: the matplotlib display x coordinate.
        """
        return float(self.plot_widget.axes.transData.transform(
            (time_s, 0.0))[0])

    def mouse_event(self, name_str: str, display_x_px: float,
                    value_f: float = 0.0, button=None,
                    double_click_b: bool = False) -> None:
        """Send a matplotlib mouse event to the canvas.

        Inputs:
            name_str: the matplotlib event name.
            display_x_px: display x of the mouse.
            value_f: y data value of the mouse.
            button: the matplotlib MouseButton, or None for a move.
            double_click_b: True for the second press of a double-click.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseEvent
        display_y_px = float(self.plot_widget.axes.transData.transform(
            (0.0, value_f))[1])
        event = MouseEvent(name_str, self.plot_widget.canvas, display_x_px,
                           display_y_px, button=button,
                           dblclick=double_click_b)
        self.plot_widget.canvas.callbacks.process(name_str, event)

    def middle_press(self, display_x_px: float, value_f: float = 0.0,
                     double_click_b: bool = False) -> None:
        """Press the wheel button at a display x.

        Inputs:
            display_x_px: display x of the mouse.
            value_f: y data value of the mouse.
            double_click_b: True for the second press of a double-click.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        self.mouse_event("button_press_event", display_x_px, value_f,
                         MouseButton.MIDDLE, double_click_b)

    def move(self, display_x_px: float, value_f: float = 0.0) -> None:
        """Move the mouse to a display x.

        Inputs:
            display_x_px: display x of the mouse.
            value_f: y data value of the mouse.
        Outputs: none.
        """
        self.mouse_event("motion_notify_event", display_x_px, value_f)

    def middle_release(self, display_x_px: float,
                       value_f: float = 0.0) -> None:
        """Release the wheel button at a display x.

        Inputs:
            display_x_px: display x of the mouse.
            value_f: y data value of the mouse.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        self.mouse_event("button_release_event", display_x_px, value_f,
                         MouseButton.MIDDLE)

    def send_qt_wheel(self, time_s: float, angle_eighths_i: int,
                      pixel_delta_i: int = 0) -> None:
        """Send a real QWheelEvent to the canvas at a time.

        Inputs:
            time_s: x value in seconds under the mouse.
            angle_eighths_i: vertical angleDelta in eighths of a degree.
            pixel_delta_i: vertical pixelDelta (0 for none).
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint, QPointF, Qt
        from PyQt6.QtGui import QWheelEvent
        canvas = self.plot_widget.canvas
        widget_point = self.point_at(time_s)
        local_point = QPointF(canvas.mapFrom(self.plot_widget,
                                             widget_point))
        wheel_event = QWheelEvent(
            local_point, QPointF(canvas.mapToGlobal(local_point)),
            QPoint(0, pixel_delta_i), QPoint(0, angle_eighths_i),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase, False)
        self.application.sendEvent(canvas, wheel_event)

    def assert_width(self, expected_width_s: float) -> None:
        """Check the width of the shown time range.

        Inputs:
            expected_width_s: the expected width in seconds.
        Outputs: none.
        """
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(end_s - start_s, expected_width_s)


class WheelStepTest(NavigationWidgetTestCase):
    """One wheel notch changes the range width by 5%."""

    @covers("LLFR-00113", "LLFR-00074")
    def test_one_notch_forward_narrows_to_95_percent(self) -> None:
        """A forward notch keeps 95% of the width around the mouse.

        Inputs: none.
        Outputs: none.
        """
        point = self.point_at(3.0)
        mouse_s = self.plot_widget.time_at(point)
        self.plot_widget.wheel_at(point, 1.0)
        self.assert_width(9.5)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, mouse_s * 0.05)
        self.assertEqual(self.range_list, [(start_s, end_s)])
        self.draw()
        self.plot_widget.wheel_at(self.point_at(3.0), 1.0)
        self.assert_width(9.5 * 0.95)

    @covers("LLFR-00113", "LLFR-00074")
    def test_one_notch_backward_widens_to_1_over_0_95(self) -> None:
        """A backward notch multiplies the width by 1/0.95.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_time_range(2.0, 6.0)
        self.draw()
        point = self.point_at(4.0)
        mouse_s = self.plot_widget.time_at(point)
        self.plot_widget.wheel_at(point, -1.0)
        self.assert_width(4.0 / 0.95)
        start_s, end_s = self.plot_widget.time_range_tuple()
        # The time under the mouse keeps its place in the range.
        self.assertAlmostEqual((mouse_s - start_s) / (end_s - start_s),
                               (mouse_s - 2.0) / 4.0)
        # Forward then backward gives the start range back.
        self.draw()
        self.plot_widget.wheel_at(self.point_at(mouse_s), 1.0)
        self.assert_width(4.0)

    @covers("LLFR-00113")
    def test_fractional_steps_zoom_in_proportion(self) -> None:
        """Half a notch zooms by 0.95 ** 0.5; 3 notches by 0.95 ** 3.

        Inputs: none.
        Outputs: none.
        """
        for step_f in (0.5, 0.125, 3.0, -0.5):
            with self.subTest(step=step_f):
                self.plot_widget.set_time_range(2.0, 6.0)
                self.draw()
                self.plot_widget.wheel_at(self.point_at(4.0), step_f)
                self.assert_width(4.0 * 0.95 ** step_f)

    @covers("LLFR-00113", "LLFR-00074", "LLFR-00108")
    def test_real_wheel_event_uses_the_rotation_angle(self) -> None:
        """A QWheelEvent of 120 eighths of a degree is one notch.

        A touchpad event with both a pixel delta and a small angle delta
        zooms by its angle only, in proportion.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in ALL_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.plot_widget.set_time_range(0.0, 10.0)
                self.draw()
                self.send_qt_wheel(5.0, 120)
                self.assert_width(9.5)
        self.plot_widget.set_time_range(2.0, 6.0)
        self.draw()
        self.send_qt_wheel(4.0, -120)
        self.assert_width(4.0 / 0.95)
        self.plot_widget.set_time_range(2.0, 6.0)
        self.draw()
        self.send_qt_wheel(4.0, 60, pixel_delta_i=30)
        self.assert_width(4.0 * 0.95 ** 0.5)
        self.plot_widget.set_time_range(2.0, 6.0)
        self.draw()
        self.send_qt_wheel(4.0, 15, pixel_delta_i=4)
        self.assert_width(4.0 * 0.95 ** 0.125)

    @covers("LLFR-00113")
    def test_wheel_step_reads_angle_then_matplotlib_step(self) -> None:
        """wheel_step_f divides the Qt angle by 120, else uses step.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import WHEEL_NOTCH_EIGHTHS_I, wheel_step_f
        self.assertEqual(WHEEL_NOTCH_EIGHTHS_I, 120)
        self.assertEqual(wheel_step_f(FakeScrollEvent(
            30.0, FakeWheelEvent(120))), 1.0)
        self.assertEqual(wheel_step_f(FakeScrollEvent(
            -1.0, FakeWheelEvent(-240))), -2.0)
        self.assertEqual(wheel_step_f(FakeScrollEvent(
            5.0, FakeWheelEvent(60))), 0.5)
        self.assertEqual(wheel_step_f(FakeScrollEvent(2.0)), 2.0)
        self.assertEqual(wheel_step_f(FakeScrollEvent(-1.0, object())),
                         -1.0)


class ClickStepTest(NavigationWidgetTestCase):
    """Zoom tool: a click keeps 95% of the width."""

    @covers("LLFR-00078", "LLFR-00076")
    def test_click_in_a_zoomed_range_keeps_95_percent(self) -> None:
        """A click in a 2 s range gives 1.9 s centred on the click.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
        self.plot_widget.set_time_range(3.0, 5.0)
        self.draw()
        point = self.point_at(4.0)
        clicked_s = self.plot_widget.time_at(point)
        self.plot_widget.click_at(point)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(end_s - start_s, 1.9)
        self.assertAlmostEqual((start_s + end_s) / 2.0, clicked_s)
        self.assert_curves_fit()


class PanWidgetTest(NavigationWidgetTestCase):
    """The wheel button held down pans the x range."""

    @covers("LLFR-00117", "LLFR-00120")
    def test_pan_follows_the_pointer(self) -> None:
        """The time grabbed at the press stays under the pointer.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_time_range(2.0, 4.0)
        self.draw()
        self.middle_press(self.display_x_px(3.0))
        self.assertEqual(self.range_list, [])
        target_x_px = self.display_x_px(3.5)
        self.move(target_x_px)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 1.5, delta=PIXEL_TOLERANCE_S)
        self.assertAlmostEqual(end_s - start_s, 2.0)
        self.assertAlmostEqual(self.display_x_px(3.0), target_x_px,
                               delta=2.0)
        self.assert_curves_fit()
        # Moving left drags the curves left: later times come in.
        target_x_px = self.display_x_px(2.5)
        self.move(target_x_px)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 2.0, delta=PIXEL_TOLERANCE_S)
        self.assertAlmostEqual(self.display_x_px(3.0), target_x_px,
                               delta=2.0)
        self.middle_release(target_x_px)
        self.assertGreaterEqual(len(self.range_list), 2)
        self.assertEqual(self.range_list[-1],
                         self.plot_widget.time_range_tuple())
        # After the release a move no longer pans.
        emitted_count_i = len(self.range_list)
        self.move(self.display_x_px(2.0))
        self.assertEqual(len(self.range_list), emitted_count_i)
        self.assertFalse(self.plot_widget.panning_b)

    @covers("LLFR-00118")
    def test_no_pan_at_the_whole_range(self) -> None:
        """At the whole time range a drag changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.middle_press(self.display_x_px(5.0))
        for time_s in (7.0, 2.0, 9.9, 0.1):
            self.move(self.display_x_px(time_s))
            self.assertEqual(self.plot_widget.time_range_tuple(),
                             (0.0, 10.0))
        self.middle_release(self.display_x_px(1.0))
        self.assertEqual(self.range_list, [])
        # Zoomed out back to the whole range by the wheel: no pan either.
        self.plot_widget.wheel_at(self.point_at(5.0), 1.0)
        self.plot_widget.wheel_at(self.point_at(5.0), -5.0)
        self.assertEqual(self.plot_widget.time_range_tuple(), (0.0, 10.0))
        self.range_list.clear()
        self.draw()
        self.middle_press(self.display_x_px(5.0))
        self.move(self.display_x_px(8.0))
        self.assertEqual(self.range_list, [])

    @covers("LLFR-00119", "LLFR-00117")
    def test_pan_stops_at_first_and_last_sample(self) -> None:
        """A long drag stops at the data's ends and keeps the width.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_time_range(1.0, 3.0)
        self.draw()
        press_x_px = self.display_x_px(2.0)
        pixels_per_second_f = self.display_x_px(3.0) - press_x_px
        self.middle_press(press_x_px)
        # Far to the right: the range would start before 0.
        self.move(press_x_px + 5.0 * pixels_per_second_f)
        self.assertEqual(self.plot_widget.time_range_tuple(), (0.0, 2.0))
        # Far to the left: the range would end after 10.
        self.move(press_x_px - 20.0 * pixels_per_second_f)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 8.0)
        self.assertEqual(end_s, 10.0)
        for emitted_start_s, emitted_end_s in self.range_list:
            self.assertGreaterEqual(emitted_start_s, 0.0)
            self.assertLessEqual(emitted_end_s, 10.0)
            self.assertAlmostEqual(emitted_end_s - emitted_start_s, 2.0)
        # At the end, a further drag the same way changes nothing.
        emitted_count_i = len(self.range_list)
        self.move(press_x_px - 30.0 * pixels_per_second_f)
        self.assertEqual(len(self.range_list), emitted_count_i)
        self.middle_release(press_x_px - 30.0 * pixels_per_second_f)

    @covers("LLFR-00120", "LLFR-00076")
    def test_y_axis_fits_after_every_pan_step(self) -> None:
        """Each pan step fits y to the curves of the new range.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_time_range(0.0, 2.0)
        self.draw()
        first_ylim_tuple = self.plot_widget.axes.get_ylim()
        press_x_px = self.display_x_px(1.5)
        pixels_per_second_f = self.display_x_px(1.0) - self.display_x_px(
            0.0)
        self.middle_press(press_x_px)
        for shift_s in (1.0, 2.5, 4.0, 6.0, 8.0):
            with self.subTest(shift=shift_s):
                self.move(press_x_px - shift_s * pixels_per_second_f)
                self.assert_curves_fit()
                fitted_tuple = self.plot_widget.axes.get_ylim()
                self.plot_widget.apply_time_range()
                self.assertEqual(self.plot_widget.axes.get_ylim(),
                                 fitted_tuple)
        # The ramp rises from 3.0 to 4.0: the top of y moved up.
        self.assertGreater(self.plot_widget.axes.get_ylim()[1],
                           first_ylim_tuple[1])
        self.middle_release(press_x_px - 8.0 * pixels_per_second_f)

    @covers("LLFR-00117", "LLFR-00045", "LLFR-00078", "LLFR-00081",
            "LLFR-00108")
    def test_pan_with_every_tool_and_no_tool_action(self) -> None:
        """With any tool a wheel press pans and never pins, zooms or
        places a marker; no menu opens.

        Inputs: none.
        Outputs: none.
        """
        menu_list = []
        self.plot_widget.execute_menu = (
            lambda menu, point: menu_list.append(menu))
        sine_value_f = float(np.sin(4.0))
        for tool_str in ALL_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.plot_widget.set_time_range(3.0, 5.0)
                self.draw()
                self.range_list.clear()
                if tool_str == TIP_TOOL_STR:
                    self.plot_widget.hover_at(self.point_at(4.0,
                                                            sine_value_f))
                    self.assertNotEqual(self.plot_widget.hover_tip_text(),
                                        "")
                press_x_px = self.display_x_px(4.0)
                self.middle_press(press_x_px, sine_value_f)
                self.middle_press(press_x_px, sine_value_f,
                                  double_click_b=True)
                # The press alone changes nothing.
                self.assertEqual(self.plot_widget.time_range_tuple(),
                                 (3.0, 5.0))
                self.assertEqual(self.plot_widget.hover_tip_text(), "")
                target_x_px = self.display_x_px(4.5)
                self.move(target_x_px, sine_value_f)
                self.middle_release(target_x_px, sine_value_f)
                start_s, end_s = self.plot_widget.time_range_tuple()
                self.assertAlmostEqual(start_s, 2.5,
                                       delta=PIXEL_TOLERANCE_S)
                self.assertAlmostEqual(end_s - start_s, 2.0)
                self.assertEqual(len(self.range_list), 1)
                self.assertEqual(self.plot_widget.plot_tool_str, tool_str)
        self.application.processEvents()
        self.assertEqual(self.pin_list, [])
        self.assertEqual(self.marker_place_list, [])
        self.assertEqual(menu_list, [])
        self.assertEqual(self.plot_widget.pinned_tip_count(), 0)

    @covers("LLFR-00117", "LLFR-00078")
    def test_left_press_during_a_pan_does_nothing(self) -> None:
        """While the wheel button is held, a left press does not zoom.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
        self.plot_widget.set_time_range(3.0, 5.0)
        self.draw()
        self.middle_press(self.display_x_px(4.0))
        self.mouse_event("button_press_event", self.display_x_px(4.0),
                         0.0, MouseButton.LEFT)
        self.assertEqual(self.plot_widget.time_range_tuple(), (3.0, 5.0))
        self.middle_release(self.display_x_px(4.0))
        self.assertEqual(self.range_list, [])

    @covers("LLFR-00117")
    def test_real_qt_wheel_button_drag_pans(self) -> None:
        """Qt mouse events with the middle button go through the canvas.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        canvas = self.plot_widget.canvas
        self.plot_widget.set_time_range(2.0, 4.0)
        self.draw()

        # The points are taken before the pan moves the x range.
        grab_point = QPointF(canvas.mapFrom(self.plot_widget,
                                            self.point_at(3.0)))
        target_point = QPointF(canvas.mapFrom(self.plot_widget,
                                              self.point_at(3.5)))

        def send(event_type, local_point, button, buttons) -> None:
            """Send one QMouseEvent to the canvas at a point.

            Inputs:
                event_type: the QEvent.Type.
                local_point: QPointF in canvas coordinates.
                button: the Qt.MouseButton that changed.
                buttons: the Qt.MouseButton buttons held.
            Outputs: none.
            """
            mouse_event = QMouseEvent(
                event_type, local_point,
                QPointF(canvas.mapToGlobal(local_point)), button, buttons,
                Qt.KeyboardModifier.NoModifier)
            self.application.sendEvent(canvas, mouse_event)

        middle_button = Qt.MouseButton.MiddleButton
        send(QEvent.Type.MouseButtonPress, grab_point, middle_button,
             middle_button)
        self.assertTrue(self.plot_widget.panning_b)
        send(QEvent.Type.MouseMove, target_point, Qt.MouseButton.NoButton,
             middle_button)
        send(QEvent.Type.MouseButtonRelease, target_point, middle_button,
             Qt.MouseButton.NoButton)
        self.assertFalse(self.plot_widget.panning_b)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 1.5, delta=PIXEL_TOLERANCE_S)
        self.assertAlmostEqual(end_s - start_s, 2.0)
        self.assertTrue(self.range_list)


class GridWidgetTest(NavigationWidgetTestCase):
    """The grid of one plot widget."""

    @covers("LLFR-00122", "LLFR-00123", "LLFR-00147")
    def test_grid_is_hidden_until_shown(self) -> None:
        """A new plot has no grid; set_grid_shown shows and hides it.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(self.plot_widget.grid_shown())
        self.plot_widget.set_grid_shown(True)
        self.draw()
        self.assertTrue(self.plot_widget.grid_shown())
        self.assertTrue(all(line.get_visible() for line
                            in self.plot_widget.axes.get_xgridlines()))
        self.assertTrue(all(line.get_visible() for line
                            in self.plot_widget.axes.get_ygridlines()))
        self.plot_widget.set_grid_shown(False)
        self.draw()
        self.assertFalse(self.plot_widget.grid_shown())
        self.assertFalse(any(line.get_visible() for line
                             in self.plot_widget.axes.get_xgridlines()))

    @covers("LLFR-00122", "LLFR-00125")
    def test_grid_survives_redraws_and_zooms(self) -> None:
        """New curves, markers, tips and zooms keep the grid.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_grid_shown(True)
        self.plot_widget.set_curves([
            ("Ramp", self.time_array, self.ramp_array, "#0000ff", 3)])
        self.assertTrue(self.plot_widget.grid_shown())
        self.plot_widget.set_markers([(1, "Marker 1", 4.0)])
        self.plot_widget.set_pinned_tips([("Ramp", 2.0, 3.2)])
        self.plot_widget.rebuild_axes()
        self.draw()
        self.assertTrue(self.plot_widget.grid_shown())
        self.plot_widget.wheel_at(self.point_at(5.0, 3.5), 4.0)
        self.draw()
        self.assertTrue(self.plot_widget.grid_shown())
        self.plot_widget.set_grid_shown(False)
        self.plot_widget.set_curves([])
        self.assertFalse(self.plot_widget.grid_shown())


@requires_qt
class ActionButtonTest(unittest.TestCase):
    """The action button stays active while running, for a minimum time."""

    def setUp(self) -> None:
        """Create a shown action button with a 100 ms minimum time.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.action_button import ActionButton
        self.button = ActionButton("Act", 100)
        self.button.show()
        self.trigger_list = recorder(self.button.triggered)

    def tearDown(self) -> None:
        """Close and delete the button.

        Inputs: none.
        Outputs: none.
        """
        self.button.close()
        self.button.deleteLater()
        self.application.processEvents()

    def wait_until_normal(self) -> float:
        """Process events until the button is normal; return the time.

        Inputs: none.
        Outputs: the monotonic time when the button was seen normal.
        """
        from PyQt6.QtTest import QTest
        deadline_s = time.monotonic() + MAXIMUM_WAIT_TIME_S
        while self.button.is_active() and time.monotonic() < deadline_s:
            QTest.qWait(5)
        return time.monotonic()

    @covers("LLFR-00116", "LLFR-00001", "LLFR-00003")
    def test_finished_action_waits_for_the_minimum_time(self) -> None:
        """Finishing at once still shows the active color 100 ms.

        Inputs: none.
        Outputs: none.
        """
        from view.toggle_button import ACTIVE_COLOR_STR, NORMAL_COLOR_STR
        start_s = time.monotonic()
        self.button.click()
        self.assertEqual(len(self.trigger_list), 1)
        self.assertTrue(self.button.is_active())
        self.assertEqual(self.button.current_background_color_str(),
                         ACTIVE_COLOR_STR)
        self.button.finish()
        self.assertTrue(self.button.is_active())
        normal_s = self.wait_until_normal()
        self.assertFalse(self.button.is_active())
        self.assertEqual(self.button.current_background_color_str(),
                         NORMAL_COLOR_STR)
        self.assertGreaterEqual(normal_s - start_s, 0.1)

    @covers("LLFR-00116", "LLFR-00003")
    def test_unfinished_action_keeps_the_button_active(self) -> None:
        """Past the minimum time the button waits for finish.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        self.button.click()
        QTest.qWait(250)
        self.assertTrue(self.button.is_active())
        self.button.finish()
        self.assertFalse(self.button.is_active())

    @covers("LLFR-00116", "LLFR-00001")
    def test_click_while_active_runs_again_and_stays_active(self) -> None:
        """A second click is a new run, never a deactivation.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        self.button.click()
        self.button.finish()
        QTest.qWait(60)
        second_click_s = time.monotonic()
        self.button.click()
        self.assertTrue(self.button.is_active())
        self.assertEqual(len(self.trigger_list), 2)
        self.button.finish()
        normal_s = self.wait_until_normal()
        self.assertFalse(self.button.is_active())
        self.assertGreaterEqual(normal_s - second_click_s, 0.1)


@requires_qt
class NavigationEndToEndTest(unittest.TestCase):
    """Reset zoom, Grid and pan through MainWindow and the controllers."""

    def setUp(self) -> None:
        """Create the window and controllers, open a file, add 2 plots.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.main_window = MainWindow()
        self.main_window.resize(1100, 800)
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.plot_controller = self.controller.plot_controller
        self.plot_controller.on_file_opened(self.make_file(4.0), False)
        self.top_panel = self.main_window.top_panel
        self.main_window.show()
        self.main_window.signal_double_click_handler("speed")
        self.main_window.signal_double_click_handler("force")
        self.process_events()

    def tearDown(self) -> None:
        """Close the window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.process_events()

    def make_file(self, end_s: float):
        """Build an in-memory file whose time runs from 0 to end_s.

        Inputs:
            end_s: the last time sample, in seconds.
        Outputs: a SignalFile with Time, speed, force and angle.
        """
        from model.signal_file import SignalFile
        time_array = np.linspace(0.0, end_s, 41)
        return SignalFile("memory.csv", {
            "Time": time_array, "speed": time_array * 2.0,
            "force": np.sin(time_array), "angle": np.cos(time_array)})

    def process_events(self) -> None:
        """Let Qt lay out and draw the plots.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(3):
            self.application.processEvents()
        for plot_widget in self.main_window.plot_panel.plot_widget_dict.\
                values():
            plot_widget.canvas.draw()

    def plot_widgets(self) -> list:
        """Return the plot widgets of the current tab, top to bottom.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        panel = self.main_window.plot_panel
        return list(panel.page_dict[panel.current_tab_id()]
                    .plot_widget_list)

    def all_plot_widgets(self) -> list:
        """Return the plot widgets of every tab.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        return list(self.main_window.plot_panel.plot_widget_dict.values())

    def click(self, button) -> None:
        """Click a button with the left mouse button.

        Inputs:
            button: the QPushButton.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)

    def wait_until_normal(self, button) -> float:
        """Process events until a button is normal; return the time.

        Inputs:
            button: the ToggleButton to watch.
        Outputs: the monotonic time when the button was seen normal.
        """
        from PyQt6.QtTest import QTest
        deadline_s = time.monotonic() + MAXIMUM_WAIT_TIME_S
        while button.is_active() and time.monotonic() < deadline_s:
            QTest.qWait(5)
        return time.monotonic()

    def zoom_current_tab(self) -> None:
        """Zoom the current tab in with the wheel in the first plot.

        Inputs: none.
        Outputs: none.
        """
        first_widget = self.plot_widgets()[0]
        first_widget.wheel_at(first_widget.data_to_widget_point(1.0, 0.0),
                              10.0)
        self.process_events()

    @covers("LLFR-00114", "LLFR-00121", "LLFR-00147")
    def test_buttons_exist_after_the_plot_tools(self) -> None:
        """Reset zoom and Grid follow Vertical marker, both inactive.

        Inputs: none.
        Outputs: none.
        """
        from view.action_button import ActionButton
        from view.toggle_button import ToggleButton
        reset_button = self.top_panel.reset_zoom_button
        grid_button = self.top_panel.grid_button
        self.assertIsInstance(reset_button, ActionButton)
        self.assertIsInstance(grid_button, ToggleButton)
        self.assertEqual(reset_button.text(), "Reset zoom")
        self.assertEqual(grid_button.text(), "Grid")
        for button in (reset_button, grid_button):
            self.assertTrue(button.isVisible())
            self.assertIs(button.parentWidget(), self.top_panel)
            self.assertFalse(button.is_active())
            self.assertNotIn(button,
                             self.top_panel.plot_tool_button_dict.values())
        layout = self.top_panel.button_layout
        index_list = [layout.indexOf(button) for button in (
            self.top_panel.marker_button, reset_button, grid_button)]
        self.assertEqual(index_list, sorted(index_list))
        self.assertGreater(reset_button.x(),
                           self.top_panel.marker_button.x())
        self.assertGreater(grid_button.x(), reset_button.x())
        # LLFR-00147: the grid is hidden at start.
        self.assertFalse(self.main_window.is_grid_shown())
        self.assertFalse(self.plot_controller.grid_shown_b)
        for plot_widget in self.all_plot_widgets():
            self.assertFalse(plot_widget.grid_shown())

    @covers("LLFR-00115", "LLFR-00070", "LLFR-00076")
    def test_reset_zoom_shows_the_whole_range_in_the_tab(self) -> None:
        """All plots of the tab go back to 0..4 s with the start y.

        Inputs: none.
        Outputs: none.
        """
        start_ylim_list = [plot_widget.axes.get_ylim()
                           for plot_widget in self.plot_widgets()]
        self.zoom_current_tab()
        for plot_widget in self.plot_widgets():
            start_s, end_s = plot_widget.time_range_tuple()
            self.assertLess(end_s - start_s, 4.0)
        self.click(self.top_panel.reset_zoom_button)
        self.process_events()
        for plot_widget, start_ylim_tuple in zip(self.plot_widgets(),
                                                 start_ylim_list):
            self.assertEqual(plot_widget.time_range_tuple(), (0.0, 4.0))
            for index_i in range(2):
                self.assertAlmostEqual(plot_widget.axes.get_ylim()[index_i],
                                       start_ylim_tuple[index_i])
        # A zoom after the reset is shared again by the tab.
        self.zoom_current_tab()
        first_widget, second_widget = self.plot_widgets()
        self.assertEqual(first_widget.time_range_tuple(),
                         second_widget.time_range_tuple())

    @covers("LLFR-00115")
    def test_reset_zoom_leaves_other_tabs_zoomed(self) -> None:
        """Only the current tab is reset.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_current_tab()
        first_tab_id_i = self.main_window.current_tab_id()
        first_range_tuple = self.plot_widgets()[0].time_range_tuple()
        self.main_window.plot_panel.request_add_tab()
        self.main_window.signal_double_click_handler("angle")
        self.process_events()
        self.zoom_current_tab()
        self.main_window.set_current_tab(first_tab_id_i)
        self.process_events()
        self.click(self.top_panel.reset_zoom_button)
        self.process_events()
        for plot_widget in self.plot_widgets():
            self.assertEqual(plot_widget.time_range_tuple(), (0.0, 4.0))
        other_widget_list = [
            plot_widget for plot_widget in self.all_plot_widgets()
            if plot_widget not in self.plot_widgets()]
        self.assertEqual(len(other_widget_list), 1)
        start_s, end_s = other_widget_list[0].time_range_tuple()
        self.assertLess(end_s - start_s, 4.0)
        self.assertEqual(self.plot_widgets()[0].time_range_tuple(),
                         (0.0, 4.0))
        self.assertNotEqual(first_range_tuple, (0.0, 4.0))

    @covers("LLFR-00116", "LLFR-00001", "LLFR-00003")
    def test_reset_button_active_for_at_least_0_3_seconds(self) -> None:
        """The button is active from the click for 0.3 s, then normal.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        from view.toggle_button import ACTIVE_COLOR_STR, NORMAL_COLOR_STR
        reset_button = self.top_panel.reset_zoom_button
        self.zoom_current_tab()
        click_s = time.monotonic()
        self.click(reset_button)
        # The reset has already run, and the button is still active.
        self.assertEqual(self.plot_widgets()[0].time_range_tuple(),
                         (0.0, 4.0))
        self.assertTrue(reset_button.is_active())
        self.assertEqual(reset_button.current_background_color_str(),
                         ACTIVE_COLOR_STR)
        QTest.qWait(150)
        self.assertTrue(reset_button.is_active())
        normal_s = self.wait_until_normal(reset_button)
        self.assertFalse(reset_button.is_active())
        self.assertEqual(reset_button.current_background_color_str(),
                         NORMAL_COLOR_STR)
        self.assertGreaterEqual(normal_s - click_s, MINIMUM_ACTIVE_TIME_S)
        self.assertLess(normal_s - click_s, MAXIMUM_WAIT_TIME_S)

    @covers("LLFR-00116", "LLFR-00115")
    def test_second_reset_click_while_active_resets_again(self) -> None:
        """A click on the active button resets again and stays active.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        reset_button = self.top_panel.reset_zoom_button
        call_list = []
        original_handler = self.main_window.reset_zoom_handler

        def counting_handler() -> None:
            """Count the reset and run the real one.

            Inputs: none.
            Outputs: none.
            """
            call_list.append(time.monotonic())
            original_handler()

        self.main_window.set_reset_zoom_handler(counting_handler)
        self.click(reset_button)
        QTest.qWait(100)
        self.zoom_current_tab()
        second_click_s = time.monotonic()
        self.click(reset_button)
        self.assertTrue(reset_button.is_active())
        self.assertEqual(len(call_list), 2)
        self.assertEqual(self.plot_widgets()[0].time_range_tuple(),
                         (0.0, 4.0))
        normal_s = self.wait_until_normal(reset_button)
        self.assertFalse(reset_button.is_active())
        self.assertGreaterEqual(normal_s - second_click_s,
                                MINIMUM_ACTIVE_TIME_S)

    @covers("LLFR-00116", "LLFR-00115")
    def test_reset_without_plots_returns_to_normal(self) -> None:
        """With an empty tab the button still turns normal.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.plot_panel.request_add_tab()
        self.process_events()
        reset_button = self.top_panel.reset_zoom_button
        self.click(reset_button)
        self.assertTrue(reset_button.is_active())
        self.wait_until_normal(reset_button)
        self.assertFalse(reset_button.is_active())

    @covers("LLFR-00114", "LLFR-00109", "LLFR-00079")
    def test_reset_zoom_is_not_a_plot_tool(self) -> None:
        """Reset keeps the active tool; a tool click keeps the reset.

        Inputs: none.
        Outputs: none.
        """
        reset_button = self.top_panel.reset_zoom_button
        for tool_str in PLOT_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.click(self.top_panel.plot_tool_button_dict[tool_str])
                self.zoom_current_tab()
                self.click(reset_button)
                self.assertEqual(self.top_panel.active_plot_tool(),
                                 tool_str)
                self.assertEqual(self.main_window.current_plot_tool(),
                                 tool_str)
                self.assertTrue(reset_button.is_active())
                self.wait_until_normal(reset_button)
        # A tool button clicked while Reset zoom is active leaves it.
        self.click(reset_button)
        self.click(self.top_panel.zoom_button)
        self.assertTrue(reset_button.is_active())
        self.assertEqual(self.top_panel.active_plot_tool(), ZOOM_TOOL_STR)
        self.wait_until_normal(reset_button)

    @covers("LLFR-00122", "LLFR-00123", "LLFR-00124")
    def test_grid_button_shows_and_hides_grid_in_every_tab(self) -> None:
        """Every plot of every tab follows the Grid button.

        Inputs: none.
        Outputs: none.
        """
        from view.toggle_button import ACTIVE_COLOR_STR, NORMAL_COLOR_STR
        self.main_window.plot_panel.request_add_tab()
        self.main_window.signal_double_click_handler("angle")
        self.process_events()
        grid_button = self.top_panel.grid_button
        self.assertEqual(len(self.all_plot_widgets()), 3)
        for _ in range(2):
            self.click(grid_button)
            self.process_events()
            self.assertTrue(grid_button.is_active())
            self.assertEqual(grid_button.current_background_color_str(),
                             ACTIVE_COLOR_STR)
            self.assertTrue(self.plot_controller.grid_shown_b)
            for plot_widget in self.all_plot_widgets():
                self.assertTrue(plot_widget.grid_shown())
            self.click(grid_button)
            self.process_events()
            self.assertFalse(grid_button.is_active())
            self.assertEqual(grid_button.current_background_color_str(),
                             NORMAL_COLOR_STR)
            self.assertFalse(self.plot_controller.grid_shown_b)
            for plot_widget in self.all_plot_widgets():
                self.assertFalse(plot_widget.grid_shown())

    @covers("LLFR-00125", "LLFR-00122")
    def test_new_plots_follow_the_grid(self) -> None:
        """Plots made while the grid is shown show it, also after a
        redraw; plots made while it is hidden do not.

        Inputs: none.
        Outputs: none.
        """
        self.click(self.top_panel.grid_button)
        self.main_window.signal_double_click_handler("angle")
        self.main_window.plot_panel.request_add_tab()
        self.main_window.signal_double_click_handler("speed")
        self.process_events()
        self.assertEqual(len(self.all_plot_widgets()), 4)
        for plot_widget in self.all_plot_widgets():
            self.assertTrue(plot_widget.grid_shown())
        # A redraw of the curves (a drop, a width change) keeps it.
        plot_id_i = self.plot_widgets()[0].plot_id_i
        self.main_window.plot_panel.forward_plot_request(
            "signal_drop_handler", plot_id_i, "force")
        self.main_window.plot_panel.forward_plot_request(
            "curve_width_handler", plot_id_i, "force", 4)
        self.process_events()
        self.assertTrue(self.main_window.plot_view(plot_id_i).grid_shown())
        self.click(self.top_panel.grid_button)
        self.main_window.signal_double_click_handler("angle")
        self.process_events()
        for plot_widget in self.all_plot_widgets():
            self.assertFalse(plot_widget.grid_shown())

    @covers("LLFR-00124", "LLFR-00079", "LLFR-00109")
    def test_grid_and_plot_tools_do_not_affect_each_other(self) -> None:
        """Tool clicks keep the Grid button; Grid clicks keep the tool.

        Inputs: none.
        Outputs: none.
        """
        grid_button = self.top_panel.grid_button
        self.click(grid_button)
        for tool_str in PLOT_TOOL_TUPLE:
            self.click(self.top_panel.plot_tool_button_dict[tool_str])
            self.assertTrue(grid_button.is_active())
            self.assertEqual(self.top_panel.active_plot_tool(), tool_str)
        self.click(self.top_panel.marker_button)
        self.assertEqual(self.top_panel.active_plot_tool(), NO_TOOL_STR)
        self.assertTrue(grid_button.is_active())
        self.click(self.top_panel.marker_button)
        self.click(grid_button)
        self.assertFalse(grid_button.is_active())
        self.assertEqual(self.top_panel.active_plot_tool(), MARKER_TOOL_STR)
        self.click(grid_button)
        self.assertEqual(self.top_panel.active_plot_tool(), MARKER_TOOL_STR)
        for plot_widget in self.all_plot_widgets():
            self.assertTrue(plot_widget.grid_shown())
            self.assertEqual(plot_widget.plot_tool_str, MARKER_TOOL_STR)

    @covers("LLFR-00147", "LLFR-00125")
    def test_grid_choice_is_kept_on_file_replace(self) -> None:
        """A replaced file keeps the grid shown; a new window hides it.

        Inputs: none.
        Outputs: none.
        """
        self.click(self.top_panel.grid_button)
        self.plot_controller.on_file_opened(self.make_file(8.0), True)
        self.main_window.signal_double_click_handler("speed")
        self.process_events()
        self.assertTrue(self.top_panel.grid_button.is_active())
        self.assertEqual(len(self.all_plot_widgets()), 1)
        self.assertTrue(self.all_plot_widgets()[0].grid_shown())
        # A new app start (window and controllers) hides it again.
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        fresh_window = MainWindow()
        try:
            fresh_controller = MainController(fresh_window)
            fresh_controller.plot_controller.on_file_opened(
                self.make_file(2.0), False)
            fresh_window.signal_double_click_handler("speed")
            self.assertFalse(fresh_window.top_panel.grid_button.is_active())
            for plot_widget in (fresh_window.plot_panel.plot_widget_dict
                                .values()):
                self.assertFalse(plot_widget.grid_shown())
        finally:
            fresh_window.close()
            fresh_window.deleteLater()

    @covers("LLFR-00117", "LLFR-00070", "LLFR-00120")
    def test_pan_is_shared_by_the_tab(self) -> None:
        """A pan in one plot moves every plot of the tab; y fits.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton, MouseEvent
        self.zoom_current_tab()
        first_widget, second_widget = self.plot_widgets()
        start_s, end_s = first_widget.time_range_tuple()
        width_s = end_s - start_s
        canvas = first_widget.canvas

        # The points are taken before the pan moves the x range.
        grab_s = start_s + width_s / 2.0
        grab_tuple = tuple(first_widget.axes.transData.transform(
            (grab_s, 0.0)))
        target_tuple = tuple(first_widget.axes.transData.transform(
            (grab_s - width_s / 4.0, 0.0)))

        def send(name_str: str, display_tuple: tuple, button=None) -> None:
            """Send a matplotlib event at a display point to the plot.

            Inputs:
                name_str: the event name.
                display_tuple: (x, y) display coordinates.
                button: the MouseButton, or None for a move.
            Outputs: none.
            """
            event = MouseEvent(name_str, canvas, display_tuple[0],
                               display_tuple[1], button=button)
            canvas.callbacks.process(name_str, event)

        send("button_press_event", grab_tuple, MouseButton.MIDDLE)
        send("motion_notify_event", target_tuple)
        send("button_release_event", target_tuple, MouseButton.MIDDLE)
        self.process_events()
        new_start_s, new_end_s = first_widget.time_range_tuple()
        self.assertAlmostEqual(new_start_s, start_s + width_s / 4.0,
                               delta=width_s / 50.0)
        self.assertAlmostEqual(new_end_s - new_start_s, width_s)
        self.assertEqual(second_widget.time_range_tuple(),
                         (new_start_s, new_end_s))
        low_f, high_f = second_widget.axes.get_ylim()
        visible_array = np.sin(np.linspace(new_start_s, new_end_s, 201))
        self.assertLessEqual(low_f, float(np.min(visible_array)) + 1e-9)
        self.assertGreaterEqual(high_f, float(np.max(visible_array)) - 1e-9)


if __name__ == "__main__":
    unittest.main()
