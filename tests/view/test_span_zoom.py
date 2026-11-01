"""Tests for the Zoom tool's time span selection and the trackpad wheel
direction (HLFR-00027: LLFR-00078, LLFR-00206, LLFR-00208, LLFR-00209).

The first classes drive one shown plot widget with matplotlib mouse
events (and real Qt wheel events); the last one runs the whole chain:
real Qt mouse and key events sent to a MainWindow with the real
controllers, two tabs and three plots. No modal dialog or menu is ever
opened.
"""

import unittest
from unittest import mock

import numpy as np

from tests.support import covers, get_qt_application, requires_qt
from tests.view.test_navigation import FakeScrollEvent
from tests.view.test_plot_tools import PlotWidgetToolTestCase, recorder
from tests.view.test_xyz_keys import XyzKeyWindowTestCase

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR)
from model.curve_colors import MARKER_COLOR_STR

# Allowed pixel rounding error, in seconds, in a 10 s wide plot.
PIXEL_TOLERANCE_S = 0.03
LEFT_BUTTON_I = 1
MIDDLE_BUTTON_I = 2
RIGHT_BUTTON_I = 3


def make_qt_wheel_event(canvas, local_point, angle_x_i: int,
                        angle_y_i: int, inverted_b: bool,
                        pixel_y_i: int = 0, shift_b: bool = False):
    """Build a real QWheelEvent for a canvas.

    Inputs:
        canvas: the matplotlib canvas widget.
        local_point: QPoint in the canvas' coordinates.
        angle_x_i: horizontal angleDelta in eighths of a degree.
        angle_y_i: vertical angleDelta in eighths of a degree.
        inverted_b: the value of QWheelEvent.inverted() (natural
            scrolling).
        pixel_y_i: vertical pixelDelta (0 for none).
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
        QPoint(0, pixel_y_i), QPoint(angle_x_i, angle_y_i),
        Qt.MouseButton.NoButton, modifier, Qt.ScrollPhase.NoScrollPhase,
        inverted_b)


class SpanWidgetTestCase(PlotWidgetToolTestCase):
    """Base class: the 600x400 plot widget (0 s to 10 s) with the Zoom
    tool and helpers that send mouse events at widget points."""

    def setUp(self) -> None:
        """Create the plot widget and activate the Zoom tool.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)

    def send(self, name_str: str, widget_point, button_i=None) -> None:
        """Send a matplotlib mouse event at a widget point.

        Inputs:
            name_str: the matplotlib event name.
            widget_point: QPoint in the plot widget's coordinates.
            button_i: matplotlib button number, or None for a move.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseEvent
        display_x_px, display_y_px = (
            self.plot_widget.widget_to_display_tuple(widget_point))
        event = MouseEvent(name_str, self.plot_widget.canvas, display_x_px,
                           display_y_px, button=button_i)
        self.plot_widget.canvas.callbacks.process(name_str, event)

    def left_press(self, widget_point) -> None:
        """Press the left button at a widget point.

        Inputs:
            widget_point: QPoint in the plot widget's coordinates.
        Outputs: none.
        """
        self.send("button_press_event", widget_point, LEFT_BUTTON_I)

    def move_to(self, widget_point) -> None:
        """Move the mouse to a widget point.

        Inputs:
            widget_point: QPoint in the plot widget's coordinates.
        Outputs: none.
        """
        self.send("motion_notify_event", widget_point)

    def left_release(self, widget_point) -> None:
        """Release the left button at a widget point.

        Inputs:
            widget_point: QPoint in the plot widget's coordinates.
        Outputs: none.
        """
        self.send("button_release_event", widget_point, LEFT_BUTTON_I)

    def drag(self, start_point, end_point) -> None:
        """Press at one point, move in steps to another and release there.

        Inputs:
            start_point: QPoint of the press.
            end_point: QPoint of the release.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.left_press(start_point)
        for fraction_f in (0.25, 0.5, 0.75, 1.0):
            self.move_to(QPoint(
                round(start_point.x() + fraction_f
                      * (end_point.x() - start_point.x())),
                round(start_point.y() + fraction_f
                      * (end_point.y() - start_point.y()))))
        self.left_release(end_point)

    def axes_edge_point(self, right_b: bool, outside_px_i: int):
        """Return a widget point beside the left or right axes edge.

        Inputs:
            right_b: True for the right edge, False for the left one.
            outside_px_i: widget pixels beyond the edge (outside the
                drawing area).
        Outputs: QPoint in the plot widget's coordinates, at mid height.
        """
        from PyQt6.QtCore import QPoint
        box = self.plot_widget.axes.bbox
        edge_x_px = box.x1 if right_b else box.x0
        edge_point = self.plot_widget.display_to_widget_point(
            edge_x_px, (box.y0 + box.y1) / 2.0)
        offset_i = outside_px_i if right_b else -outside_px_i
        return QPoint(edge_point.x() + offset_i, edge_point.y())

    def assert_range(self, start_s: float, end_s: float,
                     delta_s: float = PIXEL_TOLERANCE_S) -> None:
        """Check the shown time range.

        Inputs:
            start_s: expected start in seconds.
            end_s: expected end in seconds.
            delta_s: allowed error in seconds.
        Outputs: none.
        """
        shown_start_s, shown_end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(shown_start_s, start_s, delta=delta_s)
        self.assertAlmostEqual(shown_end_s, end_s, delta=delta_s)


@requires_qt
class ClickOrSpanTest(SpanWidgetTestCase):
    """The 5 pixel limit between a click zoom and a span selection."""

    @covers("LLFR-00078", "LLFR-00208")
    def test_release_less_than_5_pixels_away_is_a_click_zoom(self) -> None:
        """Moves of 4 pixels (straight or diagonal, 4.2 pixels) and a
        release there zoom to 95% around the pressed time.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        for offset_tuple in ((4, 0), (0, -4), (3, 3), (-3, -3)):
            with self.subTest(offset=offset_tuple):
                self.plot_widget.set_time_range(0.0, 10.0)
                self.draw()
                self.range_list.clear()
                press_point = self.point_at(5.0, 0.0)
                pressed_s = self.plot_widget.time_at(press_point)
                release_point = press_point + QPoint(*offset_tuple)
                self.left_press(press_point)
                self.assertEqual(self.range_list, [])
                self.move_to(release_point)
                self.assertFalse(self.plot_widget.time_span_line_shown())
                self.left_release(release_point)
                self.assertEqual(len(self.range_list), 1)
                start_s, end_s = self.plot_widget.time_range_tuple()
                self.assertAlmostEqual(end_s - start_s, 9.5)
                self.assertAlmostEqual((start_s + end_s) / 2.0, pressed_s)
                self.assertFalse(
                    self.plot_widget.is_mouse_drag_in_progress())

    @covers("LLFR-00208", "LLFR-00209", "LLFR-00078")
    def test_5_pixels_away_is_a_span(self) -> None:
        """At exactly 5 pixels (3 by 4 diagonal) the line is shown and
        the release zooms to the span, not by the click step.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        press_point = self.point_at(5.0, 0.0)
        end_point = press_point + QPoint(3, 4)
        self.left_press(press_point)
        self.move_to(end_point)
        self.assertTrue(self.plot_widget.time_span_line_shown())
        pressed_s, end_s = self.plot_widget.time_span_tuple()
        self.assertAlmostEqual(pressed_s,
                               self.plot_widget.time_at(press_point))
        self.assertAlmostEqual(end_s, self.plot_widget.time_at(end_point))
        self.left_release(end_point)
        self.assertEqual(len(self.range_list), 1)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertLess(end_s - start_s, 1.0)
        self.assertAlmostEqual(start_s, pressed_s)

    @covers("LLFR-00208", "LLFR-00078")
    def test_threshold_uses_screen_pixels_at_any_pixel_ratio(self) -> None:
        """With a device pixel ratio of 2, 4 screen pixels are still a
        click and 5 screen pixels a span.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        with mock.patch.object(type(self.plot_widget), "pixel_ratio_f",
                               return_value=2.0):
            press_point = QPoint(150, 100)
            self.plot_widget.span_press_at(press_point)
            self.assertTrue(self.plot_widget.time_span_drag_b)
            self.assertFalse(self.plot_widget.span_reached_b(
                press_point + QPoint(4, 0)))
            self.assertTrue(self.plot_widget.span_reached_b(
                press_point + QPoint(0, 5)))
            self.plot_widget.cancel_time_span()

    @covers("LLFR-00208")
    def test_back_within_5_pixels_stays_a_span(self) -> None:
        """Once the line is shown, coming back near the press point and
        releasing there does not turn the span into a click zoom.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        press_point = self.point_at(5.0, 0.0)
        self.left_press(press_point)
        self.move_to(press_point + QPoint(40, 0))
        self.assertTrue(self.plot_widget.time_span_line_shown())
        self.move_to(press_point + QPoint(0, 2))
        self.left_release(press_point + QPoint(0, 2))
        # A span of zero width: nothing zooms, no click zoom either.
        self.assertEqual(self.range_list, [])
        self.assertEqual(self.plot_widget.time_range_tuple(), (0.0, 10.0))
        self.assertFalse(self.plot_widget.time_span_line_shown())

    @covers("LLFR-00078", "LLFR-00208")
    def test_press_outside_the_drawing_area_does_nothing(self) -> None:
        """A press on the axis labels starts neither a click nor a span.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        outside_point = self.axes_edge_point(False, 20)
        self.left_press(outside_point)
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        self.move_to(outside_point + QPoint(200, 0))
        self.left_release(outside_point + QPoint(200, 0))
        self.assertFalse(self.plot_widget.time_span_line_shown())
        self.assertEqual(self.range_list, [])

    @covers("LLFR-00208", "LLFR-00078")
    def test_other_tools_never_select_a_span(self) -> None:
        """With Tip, Vertical marker or no tool a drag draws no line.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (TIP_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.left_press(self.point_at(2.0, 0.0))
                self.move_to(self.point_at(6.0, 0.0))
                self.assertFalse(self.plot_widget.time_span_line_shown())
                self.assertFalse(self.plot_widget.time_span_drag_b)
                self.left_release(self.point_at(6.0, 0.0))
        self.assertEqual(self.range_list, [])


@requires_qt
class SelectionLineTest(SpanWidgetTestCase):
    """The look and the fast drawing of the selection line."""

    @covers("LLFR-00208", "LLFR-00083", "LLFR-00172", "LLFR-00143")
    def test_line_is_horizontal_dashed_marker_colored_with_ticks(
            self) -> None:
        """The line is at the press height, from the pressed time to the
        time under the pointer, dashed, in the marker color, with a short
        vertical tick at each end.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_hex
        press_point = self.point_at(2.0, 1.0)
        _, press_y_px = self.plot_widget.widget_to_display_tuple(
            press_point)
        self.left_press(press_point)
        # The pointer moves up and down too: the line stays at the
        # height of the press.
        for time_s, value_f in ((6.0, -0.5), (7.0, 3.5), (4.0, 2.0)):
            pointer = self.point_at(time_s, value_f)
            self.move_to(pointer)
            self.assertTrue(self.plot_widget.time_span_line_shown())
            line = self.plot_widget.span_line
            x_list = list(line.get_xdata())
            y_list = list(line.get_ydata())
            self.assertEqual(y_list, [press_y_px, press_y_px])
            pressed_x_px = self.plot_widget.widget_to_display_tuple(
                press_point)[0]
            pointer_x_px = self.plot_widget.widget_to_display_tuple(
                pointer)[0]
            self.assertAlmostEqual(x_list[0], pressed_x_px, delta=1.0)
            self.assertAlmostEqual(x_list[1], pointer_x_px, delta=1.0)
            self.assertNotEqual(line.get_linestyle(), "-")
            self.assertEqual(to_hex(line.get_color()),
                             to_hex(MARKER_COLOR_STR))
            # Ticks: two vertical segments, one at each end, centred on
            # the line's height.
            ticks = self.plot_widget.span_end_ticks
            tick_x_list = list(ticks.get_xdata())
            tick_y_list = list(ticks.get_ydata())
            self.assertEqual(tick_x_list[0], tick_x_list[1])
            self.assertEqual(tick_x_list[3], tick_x_list[4])
            self.assertEqual(tick_x_list[0], x_list[0])
            self.assertEqual(tick_x_list[3], x_list[1])
            self.assertTrue(np.isnan(tick_x_list[2]))
            half_height_px = tick_y_list[1] - press_y_px
            self.assertGreater(half_height_px, 0.0)
            self.assertAlmostEqual(press_y_px - tick_y_list[0],
                                   half_height_px)
            self.assertEqual(tick_y_list[3], tick_y_list[0])
            self.assertEqual(tick_y_list[4], tick_y_list[1])
            self.assertEqual(to_hex(ticks.get_color()),
                             to_hex(MARKER_COLOR_STR))
        self.left_release(self.point_at(4.0, 2.0))
        self.assertFalse(self.plot_widget.time_span_line_shown())

    @covers("LLFR-00208")
    def test_line_is_blitted_without_full_redraws(self) -> None:
        """Following the pointer only blits the line: no full draw of
        the canvas, but the canvas image changes, and cancelling the
        selection puts the clean image back.

        Inputs: none.
        Outputs: none.
        """
        canvas = self.plot_widget.canvas
        self.draw()
        self.application.processEvents()
        clean_array = np.array(canvas.buffer_rgba(), copy=True)
        draw_count_list = [0]

        def count_draw(event) -> None:
            """Count a full draw of the canvas.

            Inputs:
                event: the matplotlib DrawEvent.
            Outputs: none.
            """
            draw_count_list[0] += 1

        connection_i = canvas.mpl_connect("draw_event", count_draw)
        try:
            self.left_press(self.point_at(2.0, 0.0))
            for move_i in range(20):
                self.move_to(self.point_at(3.0 + 0.3 * move_i, 0.5))
            self.application.processEvents()
            shown_array = np.array(canvas.buffer_rgba(), copy=True)
            self.assertEqual(draw_count_list[0], 0)
            self.assertFalse(np.array_equal(clean_array, shown_array))
            self.plot_widget.set_plot_tool(NO_TOOL_STR)
            self.application.processEvents()
            self.assertEqual(draw_count_list[0], 0)
        finally:
            canvas.mpl_disconnect(connection_i)
        hidden_array = np.array(canvas.buffer_rgba(), copy=True)
        self.assertTrue(np.array_equal(clean_array, hidden_array))

    @covers("LLFR-00208", "LLFR-00129", "LLFR-00133")
    def test_line_is_never_in_a_full_draw_or_export(self) -> None:
        """The line's artists are not part of the axes, a full draw (as
        the export and the copy make) never draws them, and the figure
        image of the PDF export is the same with and without the line.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.draw()
        clean_figure_image = plot_export.render_figure_image(
            self.plot_widget.figure, 100.0)
        self.left_press(self.point_at(2.0, 0.0))
        self.move_to(self.point_at(6.0, 0.0))
        self.assertTrue(self.plot_widget.time_span_line_shown())
        span_artist_list = [self.plot_widget.span_line,
                            self.plot_widget.span_end_ticks]
        for artist in span_artist_list:
            self.assertNotIn(artist, self.plot_widget.axes.get_children())
        with mock.patch.object(
                self.plot_widget.axes, "draw_artist",
                wraps=self.plot_widget.axes.draw_artist) as draw_artist:
            self.plot_widget.canvas.draw()
            for call in draw_artist.call_args_list:
                self.assertNotIn(call.args[0], span_artist_list)
        self.assertEqual(plot_export.render_figure_image(
            self.plot_widget.figure, 100.0), clean_figure_image)
        # The selection goes on after the draw.
        self.assertTrue(self.plot_widget.time_span_line_shown())
        self.left_release(self.point_at(6.0, 0.0))
        self.assert_range(2.0, 6.0)

    @covers("LLFR-00208", "LLFR-00203")
    def test_marker_preview_is_never_shown_with_the_line(self) -> None:
        """During a selection, a preview sent by another plot is not
        shown; a preview shown before a Zoom press is hidden.

        Inputs: none.
        Outputs: none.
        """
        self.left_press(self.point_at(2.0, 0.0))
        self.move_to(self.point_at(6.0, 0.0))
        self.plot_widget.show_marker_preview(4.0)
        self.assertFalse(self.plot_widget.marker_preview_shown())
        self.assertTrue(self.plot_widget.time_span_line_shown())
        self.left_release(self.point_at(6.0, 0.0))
        # A preview left on the plot (as the plot panel may show it) goes
        # away at the press.
        self.plot_widget.show_marker_preview(4.0)
        self.assertTrue(self.plot_widget.marker_preview_shown())
        self.left_press(self.point_at(3.0, 0.0))
        self.assertFalse(self.plot_widget.marker_preview_shown())
        self.plot_widget.cancel_time_span()


@requires_qt
class ZoomToSpanTest(SpanWidgetTestCase):
    """The release zooms to the selected span."""

    @covers("LLFR-00209", "LLFR-00076", "LLFR-00070")
    def test_release_zooms_to_the_span_in_either_direction(self) -> None:
        """Dragging right or left gives the range [earlier, later], with
        y fitted, emitted once for the tab and the other tabs.

        Inputs: none.
        Outputs: none.
        """
        self.drag(self.point_at(2.0, 0.0), self.point_at(6.0, 0.0))
        self.assert_range(2.0, 6.0)
        self.assertEqual(len(self.range_list), 1)
        self.assertEqual(self.range_list[0],
                         self.plot_widget.time_range_tuple())
        self.assert_curves_fit()
        self.assertFalse(self.plot_widget.time_span_line_shown())
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        self.draw()
        self.drag(self.point_at(5.5, 0.0), self.point_at(3.0, 0.0))
        self.assert_range(3.0, 5.5)
        self.assertEqual(len(self.range_list), 2)
        self.assert_curves_fit()
        # LLFR-00109: the Zoom tool stays active.
        self.assertEqual(self.plot_widget.plot_tool_str, ZOOM_TOOL_STR)

    @covers("LLFR-00209")
    def test_release_outside_the_drawing_area_ends_at_the_edge(
            self) -> None:
        """Released beyond the right or left edge (also below the axes),
        the span ends at the time of that edge.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.plot_widget.set_time_range(2.0, 6.0)
        self.draw()
        outside_point = self.axes_edge_point(True, 60) + QPoint(0, 300)
        self.drag(self.point_at(4.0, 0.0), outside_point)
        self.assert_range(4.0, 6.0)
        self.plot_widget.set_time_range(2.0, 6.0)
        self.draw()
        self.left_press(self.point_at(5.0, 0.0))
        self.move_to(self.axes_edge_point(False, 80))
        # The line itself stops at the edge.
        self.assertAlmostEqual(self.plot_widget.time_span_tuple()[1], 2.0,
                               delta=PIXEL_TOLERANCE_S)
        self.left_release(self.axes_edge_point(False, 80))
        self.assert_range(2.0, 5.0)

    @covers("LLFR-00209", "LLFR-00119")
    def test_span_is_limited_to_the_file_range(self) -> None:
        """A span reaching beyond the data stops at the first or last
        sample; one wholly outside the data zooms nothing.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_time_range(-4.0, 14.0)
        self.draw()
        self.drag(self.point_at(-2.0, 0.0), self.point_at(4.0, 0.0))
        self.assert_range(0.0, 4.0)
        self.assertEqual(self.range_list[-1][0], 0.0)
        self.plot_widget.set_time_range(-4.0, 14.0)
        self.draw()
        self.drag(self.point_at(7.0, 0.0), self.point_at(13.0, 0.0))
        self.assert_range(7.0, 10.0)
        self.assertEqual(self.range_list[-1][1], 10.0)
        # Wholly after the last sample: zero width after the limit.
        self.plot_widget.set_time_range(-4.0, 14.0)
        self.draw()
        self.range_list.clear()
        self.drag(self.point_at(11.0, 0.0), self.point_at(13.0, 0.0))
        self.assertEqual(self.range_list, [])
        self.assertEqual(self.plot_widget.time_range_tuple(), (-4.0, 14.0))
        self.assertFalse(self.plot_widget.time_span_line_shown())

    @covers("LLFR-00209", "LLFR-00208")
    def test_vertical_drag_gives_an_empty_span_and_does_nothing(
            self) -> None:
        """A drag straight up shows the line (of zero length) and the
        release removes it without zooming.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        press_point = self.point_at(5.0, 0.0)
        self.left_press(press_point)
        self.move_to(press_point + QPoint(0, -40))
        self.assertTrue(self.plot_widget.time_span_line_shown())
        self.left_release(press_point + QPoint(0, -40))
        self.assertFalse(self.plot_widget.time_span_line_shown())
        self.assertEqual(self.range_list, [])
        self.assertEqual(self.plot_widget.time_range_tuple(), (0.0, 10.0))


@requires_qt
class SpanInteractionTest(SpanWidgetTestCase):
    """The selection with the other mouse actions and the tools."""

    @covers("LLFR-00208", "LLFR-00207")
    def test_drag_flag_is_set_from_press_to_release(self) -> None:
        """is_mouse_drag_in_progress is True from the Zoom press to the
        release, and False again after it (the Z key is ignored then).

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        self.left_press(self.point_at(2.0, 0.0))
        self.assertTrue(self.plot_widget.time_span_drag_b)
        self.assertTrue(self.plot_widget.is_mouse_drag_in_progress())
        self.move_to(self.point_at(6.0, 0.0))
        self.assertTrue(self.plot_widget.is_mouse_drag_in_progress())
        self.left_release(self.point_at(6.0, 0.0))
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        # LLFR-00207: a removed plot never blocks the Z key.
        self.left_press(self.point_at(2.0, 0.0))
        self.move_to(self.point_at(3.0, 0.0))
        self.plot_widget.retire()
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        self.assertFalse(self.plot_widget.time_span_line_shown())

    @covers("LLFR-00208", "LLFR-00148", "LLFR-00079")
    def test_tool_change_cancels_the_selection(self) -> None:
        """Deactivating the Zoom tool mid-selection (for example with the
        Tip key) removes the line; the release then zooms nothing.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (TIP_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
                self.left_press(self.point_at(2.0, 0.0))
                self.move_to(self.point_at(6.0, 0.0))
                self.assertTrue(self.plot_widget.time_span_line_shown())
                self.plot_widget.set_plot_tool(tool_str)
                self.assertFalse(self.plot_widget.time_span_line_shown())
                self.assertFalse(
                    self.plot_widget.is_mouse_drag_in_progress())
                self.left_release(self.point_at(6.0, 0.0))
        self.assertEqual(self.range_list, [])
        self.assertEqual(self.pin_list, [])
        self.assertEqual(self.plot_widget.time_range_tuple(), (0.0, 10.0))

    @covers("LLFR-00208", "LLFR-00117")
    def test_right_press_cancels_and_wheel_button_does_not_pan(
            self) -> None:
        """During a selection the wheel button starts no pan, and a right
        press cancels the selection.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_time_range(2.0, 6.0)
        self.draw()
        self.plot_widget.execute_menu = lambda menu, point: None
        self.left_press(self.point_at(3.0, 0.0))
        self.move_to(self.point_at(5.0, 0.0))
        self.send("button_press_event", self.point_at(5.0, 0.0),
                  MIDDLE_BUTTON_I)
        self.assertFalse(self.plot_widget.panning_b)
        self.assertTrue(self.plot_widget.time_span_line_shown())
        self.send("button_press_event", self.point_at(5.0, 0.0),
                  RIGHT_BUTTON_I)
        self.application.processEvents()
        self.assertFalse(self.plot_widget.time_span_line_shown())
        self.left_release(self.point_at(5.0, 0.0))
        self.assertEqual(self.range_list, [])
        # A wheel-button pan with the Zoom tool is still a pan.
        self.send("button_press_event", self.point_at(4.0, 0.0),
                  MIDDLE_BUTTON_I)
        self.assertTrue(self.plot_widget.panning_b)
        self.assertFalse(self.plot_widget.time_span_drag_b)
        self.move_to(self.point_at(4.5, 0.0))
        self.send("button_release_event", self.point_at(4.5, 0.0),
                  MIDDLE_BUTTON_I)
        self.assertFalse(self.plot_widget.time_span_line_shown())
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(end_s - start_s, 4.0)
        self.assertAlmostEqual(start_s, 1.5, delta=PIXEL_TOLERANCE_S)

    @covers("LLFR-00153", "LLFR-00208")
    def test_press_on_a_pinned_tip_still_moves_the_tip(self) -> None:
        """With the Zoom tool, a drag that starts on a pinned tip moves
        the tip: no line, no zoom.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        tip_move_list = recorder(self.plot_widget.pinned_tip_move_requested)
        self.plot_widget.set_pinned_tips([("Ramp", 5.0, 3.5)])
        self.draw()
        label_point = self.plot_widget.display_to_widget_point(
            *self.plot_widget.tip_label_center_tuple(0))
        self.left_press(label_point)
        self.assertEqual(self.plot_widget.drag_tip_index_i, 0)
        self.assertFalse(self.plot_widget.time_span_drag_b)
        self.move_to(label_point + QPoint(-60, 30))
        self.assertFalse(self.plot_widget.time_span_line_shown())
        self.left_release(label_point + QPoint(-60, 30))
        self.assertEqual(len(tip_move_list), 1)
        self.assertEqual(self.range_list, [])

    @covers("LLFR-00208", "LLFR-00209")
    def test_lost_release_applies_the_span_last_shown(self) -> None:
        """A move without the left button held (its release was lost)
        ends the selection as if released at the last position.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        canvas = self.plot_widget.canvas
        for event_type, position_s, button, buttons in (
                (QEvent.Type.MouseButtonPress, 2.0, Qt.MouseButton.LeftButton,
                 Qt.MouseButton.LeftButton),
                (QEvent.Type.MouseMove, 6.0, Qt.MouseButton.NoButton,
                 Qt.MouseButton.LeftButton),
                (QEvent.Type.MouseMove, 8.0, Qt.MouseButton.NoButton,
                 Qt.MouseButton.NoButton)):
            local_point = QPointF(canvas.mapFrom(
                self.plot_widget, self.point_at(position_s, 0.0)))
            self.application.sendEvent(canvas, QMouseEvent(
                event_type, local_point,
                QPointF(canvas.mapToGlobal(local_point)), button, buttons,
                Qt.KeyboardModifier.NoModifier))
        self.assertFalse(self.plot_widget.time_span_line_shown())
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        self.assert_range(2.0, 6.0)


@requires_qt
class TrackpadDirectionTest(PlotWidgetToolTestCase):
    """The wheel direction with natural scrolling on macOS."""

    def wheel_event(self, angle_y_i: int, inverted_b: bool,
                    pixel_y_i: int = 0):
        """Build a QWheelEvent at the middle of the plot.

        Inputs:
            angle_y_i: vertical angleDelta in eighths of a degree.
            inverted_b: the value of QWheelEvent.inverted().
            pixel_y_i: vertical pixelDelta (0 for none).
        Outputs: the QWheelEvent.
        """
        canvas = self.plot_widget.canvas
        local_point = canvas.mapFrom(self.plot_widget, self.point_at(5.0))
        return make_qt_wheel_event(canvas, local_point, 0, angle_y_i,
                                   inverted_b, pixel_y_i)

    @covers("LLFR-00206", "LLFR-00113")
    def test_inverted_delta_is_turned_back_on_macos(self) -> None:
        """On macOS an inverted delta gives the opposite step (fingers up
        with natural scrolling report a backward delta), also for pixel
        deltas and fractions of a notch.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_widget as plot_widget_module
        from view.plot_widget import physical_wheel_sign_f, wheel_step_f
        with mock.patch.object(plot_widget_module, "RUNNING_ON_MACOS_B",
                               True):
            self.assertEqual(physical_wheel_sign_f(
                self.wheel_event(-120, True)), -1.0)
            self.assertEqual(physical_wheel_sign_f(
                self.wheel_event(-120, False)), 1.0)
            for angle_y_i, inverted_b, expected_f in (
                    (-120, True, 1.0), (120, True, -1.0),
                    (-60, True, 0.5), (120, False, 1.0),
                    (-240, False, -2.0)):
                with self.subTest(angle=angle_y_i, inverted=inverted_b):
                    self.assertEqual(wheel_step_f(FakeScrollEvent(
                        -9.0, self.wheel_event(angle_y_i, inverted_b))),
                        expected_f)
            # Pixel-only touchpads (no angle) are turned back too.
            self.assertEqual(wheel_step_f(FakeScrollEvent(
                -9.0, self.wheel_event(0, True, -60))), 0.5)
            # An object without inverted() (a plain mouse) is unchanged.
            self.assertEqual(physical_wheel_sign_f(object()), 1.0)

    @covers("LLFR-00206", "LLFR-00074", "LLFR-00113")
    def test_other_systems_keep_their_deltas(self) -> None:
        """Off macOS, inverted() is ignored: the mouse wheel and the
        touchpad zoom as before.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_widget as plot_widget_module
        from view.plot_widget import physical_wheel_sign_f, wheel_step_f
        with mock.patch.object(plot_widget_module, "RUNNING_ON_MACOS_B",
                               False):
            for inverted_b in (True, False):
                self.assertEqual(physical_wheel_sign_f(
                    self.wheel_event(120, inverted_b)), 1.0)
                self.assertEqual(wheel_step_f(FakeScrollEvent(
                    -9.0, self.wheel_event(120, inverted_b))), 1.0)
                self.assertEqual(wheel_step_f(FakeScrollEvent(
                    -9.0, self.wheel_event(-60, inverted_b))), -0.5)

    @covers("LLFR-00206", "LLFR-00074")
    def test_fingers_up_zoom_in_through_the_canvas(self) -> None:
        """Real wheel events sent to the canvas on macOS: fingers up with
        natural scrolling (backward delta, inverted) zoom in; fingers
        down zoom out; without natural scrolling the same holds.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_widget as plot_widget_module
        with mock.patch.object(plot_widget_module, "RUNNING_ON_MACOS_B",
                               True):
            for angle_y_i, inverted_b, expected_width_s in (
                    (-120, True, 4.0 * 0.95), (120, True, 4.0 / 0.95),
                    (120, False, 4.0 * 0.95), (-120, False, 4.0 / 0.95)):
                with self.subTest(angle=angle_y_i, inverted=inverted_b):
                    self.plot_widget.set_time_range(3.0, 7.0)
                    self.draw()
                    self.application.sendEvent(
                        self.plot_widget.canvas,
                        self.wheel_event(angle_y_i, inverted_b))
                    start_s, end_s = self.plot_widget.time_range_tuple()
                    self.assertAlmostEqual(end_s - start_s,
                                           expected_width_s)

    @covers("LLFR-00206", "LLFR-00154", "LLFR-00074")
    def test_sideways_shift_wheel_is_turned_back_too(self) -> None:
        """The Shift+wheel that macOS turns sideways follows the same
        direction rule.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_widget as plot_widget_module
        canvas = self.plot_widget.canvas
        local_point = canvas.mapFrom(self.plot_widget, self.point_at(5.0))
        with mock.patch.object(plot_widget_module, "RUNNING_ON_MACOS_B",
                               True):
            for angle_x_i, inverted_b, expected_width_s in (
                    (-120, True, 4.0 * 0.95), (120, False, 4.0 * 0.95),
                    (120, True, 4.0 / 0.95)):
                with self.subTest(angle=angle_x_i, inverted=inverted_b):
                    self.plot_widget.set_time_range(3.0, 7.0)
                    self.draw()
                    self.application.sendEvent(canvas, make_qt_wheel_event(
                        canvas, local_point, angle_x_i, 0, inverted_b,
                        shift_b=True))
                    start_s, end_s = self.plot_widget.time_range_tuple()
                    self.assertAlmostEqual(end_s - start_s,
                                           expected_width_s)


@requires_qt
class SpanZoomWindowTest(XyzKeyWindowTestCase):
    """Real Qt mouse and key events in the main window, two tabs."""

    def setUp(self) -> None:
        """Create the window, add a second tab with a plot, go back.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.first_tab_id_i = self.main_window.current_tab_id()
        self.main_window.plot_panel.request_add_tab()
        self.main_window.signal_double_click_handler("speed")
        self.application.processEvents()
        self.main_window.set_current_tab(self.first_tab_id_i)
        for _ in range(3):
            self.application.processEvents()
        self.draw_plots()

    def send_left(self, plot_widget, event_type_name_str: str,
                  time_s: float, buttons_name_str: str,
                  offset_y_i: int = 0) -> None:
        """Send a Qt left-button mouse event, without modifiers.

        Inputs:
            plot_widget: the PlotWidget.
            event_type_name_str: "MouseButtonPress", "MouseMove" or
                "MouseButtonRelease".
            time_s: the time of the point, in the middle of the y range.
            buttons_name_str: name of the Qt.MouseButton held after it.
            offset_y_i: widget pixels added to the point's y.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        bottom_f, top_f = plot_widget.axes.get_ylim()
        canvas = plot_widget.canvas
        widget_point = plot_widget.data_to_widget_point(
            time_s, (bottom_f + top_f) / 2.0) + QPoint(0, offset_y_i)
        local_point = QPointF(canvas.mapFrom(plot_widget, widget_point))
        button = (Qt.MouseButton.NoButton
                  if event_type_name_str == "MouseMove"
                  else Qt.MouseButton.LeftButton)
        self.application.sendEvent(canvas, QMouseEvent(
            getattr(QEvent.Type, event_type_name_str), local_point,
            QPointF(canvas.mapToGlobal(local_point)), button,
            getattr(Qt.MouseButton, buttons_name_str),
            Qt.KeyboardModifier.NoModifier))
        self.application.processEvents()

    @covers("LLFR-00208", "LLFR-00209", "LLFR-00070", "LLFR-00207",
            "LLFR-00076")
    def test_span_zooms_every_plot_and_z_waits_for_the_release(
            self) -> None:
        """A span drag on one plot zooms every plot of both tabs; the Z
        key does nothing during the drag and resets after it.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.plot_tool_button_dict[ZOOM_TOOL_STR].click()
        self.application.processEvents()
        undo_history = self.controller.plot_controller.undo_history
        history_length_i = len(undo_history.snapshot_list)
        plot_widget = self.plot_widgets()[1]
        self.send_left(plot_widget, "MouseButtonPress", 1.0, "LeftButton")
        self.assertTrue(self.main_window.is_mouse_drag_in_progress())
        self.send_left(plot_widget, "MouseMove", 2.0, "LeftButton")
        self.send_left(plot_widget, "MouseMove", 3.0, "LeftButton", 25)
        self.assertTrue(plot_widget.time_span_line_shown())
        self.press_key("Key_Z", plot_widget.canvas)
        self.release_key("Key_Z", plot_widget.canvas)
        self.assert_every_range((0.0, 4.0))
        self.assertTrue(plot_widget.time_span_line_shown())
        self.send_left(plot_widget, "MouseButtonRelease", 3.0, "NoButton",
                       25)
        self.assertFalse(plot_widget.time_span_line_shown())
        self.assertFalse(self.main_window.is_mouse_drag_in_progress())
        span_tuple = plot_widget.time_range_tuple()
        self.assertAlmostEqual(span_tuple[0], 1.0, delta=0.02)
        self.assertAlmostEqual(span_tuple[1], 3.0, delta=0.02)
        self.assertEqual(len(self.all_plot_widgets()), 3)
        self.assert_every_range(span_tuple)
        self.assertEqual(self.controller.plot_controller
                         .shared_time_range_tuple, span_tuple)
        # Not undoable (LLFR-00140): nothing was recorded.
        self.assertEqual(len(undo_history.snapshot_list), history_length_i)
        self.press_key("Key_Z")
        self.release_key("Key_Z")
        self.assert_every_range((0.0, 4.0))

    @covers("LLFR-00208", "LLFR-00148", "LLFR-00149")
    def test_tip_key_during_a_selection_cancels_it(self) -> None:
        """Holding the Tip key mid-selection removes the line; releasing
        the button then zooms nothing.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.plot_tool_button_dict[ZOOM_TOOL_STR].click()
        self.application.processEvents()
        plot_widget = self.plot_widgets()[0]
        self.send_left(plot_widget, "MouseButtonPress", 1.0, "LeftButton")
        self.send_left(plot_widget, "MouseMove", 3.0, "LeftButton")
        self.assertTrue(plot_widget.time_span_line_shown())
        self.press_key("Key_Control", plot_widget.canvas,
                       "ControlModifier")
        self.assert_tool_everywhere(TIP_TOOL_STR)
        self.assertFalse(plot_widget.time_span_line_shown())
        self.assertFalse(self.main_window.is_mouse_drag_in_progress())
        self.send_left(plot_widget, "MouseButtonRelease", 3.0, "NoButton")
        self.release_key("Key_Control", plot_widget.canvas)
        self.assert_every_range((0.0, 4.0))

    @covers("LLFR-00208", "LLFR-00129", "LLFR-00133")
    def test_copied_image_never_shows_the_line(self) -> None:
        """A tab grab (copy and PDF) taken during a selection draws no
        selection artist on any canvas.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.top_panel.plot_tool_button_dict[ZOOM_TOOL_STR].click()
        self.application.processEvents()
        plot_widget = self.plot_widgets()[0]
        self.send_left(plot_widget, "MouseButtonPress", 1.0, "LeftButton")
        self.send_left(plot_widget, "MouseMove", 3.0, "LeftButton")
        self.assertTrue(plot_widget.time_span_line_shown())
        panel = self.main_window.plot_panel
        page = panel.page_dict[self.first_tab_id_i]
        span_artist_list = [plot_widget.span_line,
                            plot_widget.span_end_ticks]
        with mock.patch.object(plot_widget.axes, "draw_artist",
                               wraps=plot_widget.axes.draw_artist) as drawn:
            page_image = plot_export.grab_page_image(page)
            drawn_list = [call.args[0] for call in drawn.call_args_list]
        self.assertFalse(page_image.isNull())
        for artist in span_artist_list:
            self.assertNotIn(artist, drawn_list)
        self.send_left(plot_widget, "MouseButtonRelease", 3.0, "NoButton")


if __name__ == "__main__":
    unittest.main()
