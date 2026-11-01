"""Tests for pinned tip leader lines and tip drags, dashed markers and
the robustness of mouse drags (HLFR-00025, HLFR-00028, HLFR-00041).

Covers the dashed leader line of every pinned tip (LLFR-00151), moving
a pinned tip's label with the left button (LLFR-00152) with any plot
tool or none (LLFR-00153), the dashed vertical marker line
(LLFR-00143), drags whose button release was lost, a right press
during a drag, and the wheel steps of events that only report pixels
(LLFR-00113). Mouse events are sent to the canvas as matplotlib events,
and the full chain is checked through MainWindow with the real
controllers. No modal dialog or menu is ever opened.
"""

import unittest

import numpy as np

from tests.support import covers, get_qt_application, requires_qt
from tests.view.test_plot_tools import (
    ALL_TOOL_TUPLE, PlotWidgetToolTestCase, recorder)

from controller.plot_tools import (
    MARKER_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR)

# Allowed error, in display pixels, of positions that go through the
# rounding to whole widget pixels.
PIXEL_TOLERANCE_PX = 1.5
# The pinned tips of most tests: one on the ramp, one on the sine.
RAMP_TIP_TUPLE = ("Ramp", 5.0, 3.5)
SINE_TIP_TUPLE = ("Sine", 2.0, float(np.sin(2.0)))


class FakeButtonsEvent:
    """Stand-in for a Qt mouse event that only reports held buttons."""

    def __init__(self, held_buttons) -> None:
        """Store the buttons reported as held.

        Inputs:
            held_buttons: a Qt.MouseButton value (NoButton for none).
        Outputs: none.
        """
        self.held_buttons = held_buttons

    def buttons(self):
        """Return the held buttons, as QMouseEvent.buttons does.

        Inputs: none.
        Outputs: the Qt.MouseButton value given at creation.
        """
        return self.held_buttons


class FakePixelWheelEvent:
    """Stand-in for a QWheelEvent with an angle and a pixel delta."""

    def __init__(self, angle_eighths_i: int, pixel_delta_i: int) -> None:
        """Store the vertical rotation and pixel movement.

        Inputs:
            angle_eighths_i: angleDelta().y(), in eighths of a degree.
            pixel_delta_i: pixelDelta().y(), in pixels.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.angle_point = QPoint(0, angle_eighths_i)
        self.pixel_point = QPoint(0, pixel_delta_i)

    def angleDelta(self):
        """Return the rotation, as QWheelEvent does.

        Inputs: none.
        Outputs: a QPoint.
        """
        return self.angle_point

    def pixelDelta(self):
        """Return the pixel movement, as QWheelEvent does.

        Inputs: none.
        Outputs: a QPoint.
        """
        return self.pixel_point


class FakeScrollEvent:
    """Stand-in for a matplotlib scroll MouseEvent."""

    def __init__(self, step_f: float, gui_event) -> None:
        """Store matplotlib's step and the Qt event.

        Inputs:
            step_f: matplotlib's step value.
            gui_event: the Qt event, or None.
        Outputs: none.
        """
        self.step = step_f
        self.guiEvent = gui_event


class TipDragTestCase(PlotWidgetToolTestCase):
    """Base class: the plot widget with two pinned tips and recorders."""

    def setUp(self) -> None:
        """Pin a tip on the ramp and one on the sine, record requests.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.plot_widget.set_pinned_tips([RAMP_TIP_TUPLE, SINE_TIP_TUPLE])
        self.draw()
        self.move_list = recorder(self.plot_widget.pinned_tip_move_requested)
        self.marker_place_list = recorder(
            self.plot_widget.marker_place_requested)
        self.marker_move_list = recorder(
            self.plot_widget.marker_move_requested)

    def send(self, name_str: str, display_tuple: tuple, button=None,
             held_buttons=None, double_click_b: bool = False) -> None:
        """Send a matplotlib mouse event to the canvas.

        Inputs:
            name_str: the matplotlib event name.
            display_tuple: (x, y) of the mouse in display pixels.
            button: the matplotlib MouseButton, or None for a move.
            held_buttons: the Qt buttons the event reports as held, or
                None for an event that does not report them.
            double_click_b: True for the second press of a double-click.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseEvent
        gui_event = (FakeButtonsEvent(held_buttons)
                     if held_buttons is not None else None)
        event = MouseEvent(name_str, self.plot_widget.canvas,
                           float(display_tuple[0]), float(display_tuple[1]),
                           button=button, dblclick=double_click_b,
                           guiEvent=gui_event)
        self.plot_widget.canvas.callbacks.process(name_str, event)

    def left_press(self, display_tuple: tuple) -> None:
        """Press the left button at a display point.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        self.send("button_press_event", display_tuple, MouseButton.LEFT)

    def move_to(self, display_tuple: tuple, held_buttons=None) -> None:
        """Move the mouse to a display point.

        Inputs:
            display_tuple: (x, y) in display pixels.
            held_buttons: Qt buttons reported as held, or None.
        Outputs: none.
        """
        self.send("motion_notify_event", display_tuple,
                  held_buttons=held_buttons)

    def left_release(self, display_tuple: tuple) -> None:
        """Release the left button at a display point.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        self.send("button_release_event", display_tuple, MouseButton.LEFT)

    def label_center(self, tip_index_i: int = 0) -> tuple:
        """Return the center of a pinned tip's label box.

        Inputs:
            tip_index_i: index of the tip.
        Outputs: (x, y) in display pixels.
        """
        return self.plot_widget.tip_label_center_tuple(tip_index_i)

    def point_display(self, tip_index_i: int = 0) -> tuple:
        """Return the display position of a pinned tip's point.

        Inputs:
            tip_index_i: index of the tip.
        Outputs: (x, y) in display pixels.
        """
        annotation = self.plot_widget.pinned_tip_annotation(tip_index_i)
        point_array = self.plot_widget.axes.transData.transform(
            annotation.xy)
        return (float(point_array[0]), float(point_array[1]))

    def drag_label(self, delta_x_px: float, delta_y_px: float,
                   tip_index_i: int = 0) -> tuple:
        """Press on a tip's label, move it in two steps and release it.

        Inputs:
            delta_x_px: total movement to the right, in display pixels.
            delta_y_px: total movement upwards, in display pixels.
            tip_index_i: index of the tip.
        Outputs: the label center before the drag, in display pixels.
        """
        start_tuple = self.label_center(tip_index_i)
        self.left_press(start_tuple)
        self.move_to((start_tuple[0] + delta_x_px / 2.0,
                      start_tuple[1] + delta_y_px / 2.0))
        end_tuple = (start_tuple[0] + delta_x_px,
                     start_tuple[1] + delta_y_px)
        self.move_to(end_tuple)
        self.left_release(end_tuple)
        self.draw()
        return start_tuple

    def assert_near(self, first_tuple: tuple, second_tuple: tuple,
                    tolerance_px: float = PIXEL_TOLERANCE_PX) -> None:
        """Check that two display points are within a tolerance.

        Inputs:
            first_tuple: (x, y) in display pixels.
            second_tuple: (x, y) in display pixels.
            tolerance_px: allowed distance per coordinate.
        Outputs: none.
        """
        self.assertAlmostEqual(first_tuple[0], second_tuple[0],
                               delta=tolerance_px)
        self.assertAlmostEqual(first_tuple[1], second_tuple[1],
                               delta=tolerance_px)

    def assert_leader_connected(self, tip_index_i: int) -> None:
        """Check that a tip's dashed leader joins its box and its point.

        Inputs:
            tip_index_i: index of the tip.
        Outputs: none.
        """
        annotation = self.plot_widget.pinned_tip_annotation(tip_index_i)
        leader = annotation.arrow_patch
        self.assertIsNotNone(leader)
        self.assertTrue(leader.get_visible())
        self.assertEqual(leader.get_linestyle(), "--")
        vertex_array = leader.get_path().vertices
        # The line ends exactly at the point the tip shows.
        self.assert_near(tuple(vertex_array[-1]),
                         self.point_display(tip_index_i), 0.5)
        # It starts on the edge of the label's box.
        box = self.plot_widget.tip_box_extent(annotation)
        start_x_px, start_y_px = vertex_array[0]
        self.assertTrue(box.x0 - 1.0 <= start_x_px <= box.x1 + 1.0)
        self.assertTrue(box.y0 - 1.0 <= start_y_px <= box.y1 + 1.0)


@requires_qt
class DashedMarkerTest(PlotWidgetToolTestCase):
    """The vertical marker line is dashed (LLFR-00143)."""

    @covers("LLFR-00143", "LLFR-00082", "LLFR-00083")
    def test_marker_line_is_dashed_full_height_marker_color(self) -> None:
        """Every marker line is dashed, spans y and keeps its color.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_hex
        from model.curve_colors import MARKER_COLOR_STR
        from view.plot_widget import MARKER_LINE_STYLE_TUPLE
        self.plot_widget.set_markers([(1, "Marker 1", 4.0),
                                      (2, "Marker 2", 7.0)])
        self.draw()
        self.assertGreater(MARKER_LINE_STYLE_TUPLE[1][1], 0)
        for marker_id_i in (1, 2):
            line = self.plot_widget.marker_artist_tuple(marker_id_i)[0]
            self.assertEqual(line.get_linestyle(), "--")
            self.assertEqual(to_hex(line.get_color()), MARKER_COLOR_STR)
            self.assertEqual(list(line.get_ydata()), [0, 1])
        # Moving, zooming and redrawing keep the dashes.
        self.plot_widget.move_marker_artists(1, 5.0)
        self.plot_widget.set_time_range(3.0, 8.0)
        self.plot_widget.rebuild_axes()
        self.draw()
        for marker_id_i in (1, 2):
            line = self.plot_widget.marker_artist_tuple(marker_id_i)[0]
            self.assertEqual(line.get_linestyle(), "--")


@requires_qt
class TipLeaderLineTest(TipDragTestCase):
    """Each pinned tip has a dashed line to its point (LLFR-00151)."""

    @covers("LLFR-00151", "LLFR-00045")
    def test_every_pinned_tip_has_a_connected_dashed_leader(self) -> None:
        """Both tips have a dashed leader from the box to the point.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.plot_widget.pinned_tip_count(), 2)
        for tip_index_i in range(2):
            with self.subTest(tip=tip_index_i):
                self.assert_leader_connected(tip_index_i)
                annotation = self.plot_widget.pinned_tip_annotation(
                    tip_index_i)
                # In the color of the tip's curve.
                self.assertEqual(
                    tuple(annotation.arrow_patch.get_edgecolor())[:3],
                    tuple(annotation.get_bbox_patch().get_edgecolor())[:3])

    @covers("LLFR-00151", "LLFR-00152")
    def test_leader_follows_moved_label_zoom_and_redraw(self) -> None:
        """A moved label keeps a leader to the point at any range.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_pinned_tips([
            RAMP_TIP_TUPLE + ((-80.0, -50.0),), SINE_TIP_TUPLE])
        self.draw()
        for tip_index_i in range(2):
            self.assert_leader_connected(tip_index_i)
        self.plot_widget.set_time_range(1.0, 6.0)
        self.draw()
        for tip_index_i in range(2):
            self.assert_leader_connected(tip_index_i)
        self.plot_widget.rebuild_axes()
        self.draw()
        self.assert_leader_connected(0)

    @covers("LLFR-00046", "LLFR-00151")
    def test_leader_line_is_not_part_of_the_tip_hit_area(self) -> None:
        """Only the label box and the point are on the tip.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_pinned_tips([
            RAMP_TIP_TUPLE + ((-120.0, -60.0),)])
        self.draw()
        center_tuple = self.label_center()
        point_tuple = self.point_display()
        middle_tuple = ((center_tuple[0] + point_tuple[0]) / 2.0,
                        (center_tuple[1] + point_tuple[1]) / 2.0)
        # The middle of the leader is outside the box.
        box = self.plot_widget.tip_box_extent(
            self.plot_widget.pinned_tip_annotation(0))
        self.assertFalse(box.contains(*middle_tuple))
        middle_point = self.plot_widget.display_to_widget_point(
            *middle_tuple)
        self.assertEqual(self.plot_widget.pinned_tip_at(middle_point), -1)
        self.assertEqual(self.plot_widget.pinned_tip_at(
            self.plot_widget.display_to_widget_point(*center_tuple)), 0)


@requires_qt
class TipDragWidgetTest(TipDragTestCase):
    """Moving a pinned tip's label with the left button (LLFR-00152)."""

    @covers("LLFR-00152", "HLFR-00041", "LLFR-00151")
    def test_drag_moves_the_label_and_keeps_the_values(self) -> None:
        """The label follows the pointer; text and point stay the same.

        Inputs: none.
        Outputs: none.
        """
        text_str = self.plot_widget.pinned_tip_text(0)
        point_tuple = self.point_display()
        start_tuple = self.label_center()
        self.left_press(start_tuple)
        middle_tuple = (start_tuple[0] - 30.0, start_tuple[1] - 20.0)
        self.move_to(middle_tuple)
        self.draw()
        # The label follows during the drag; nothing is requested yet.
        self.assert_near(self.label_center(), middle_tuple)
        self.assertEqual(self.move_list, [])
        self.assert_leader_connected(0)
        end_tuple = (start_tuple[0] - 70.0, start_tuple[1] - 45.0)
        self.move_to(end_tuple)
        self.left_release(end_tuple)
        self.draw()
        self.assert_near(self.label_center(), end_tuple)
        self.assertEqual(self.plot_widget.pinned_tip_text(0), text_str)
        self.assertEqual(self.plot_widget.pinned_tip_annotation(0).xy,
                         (5.0, 3.5))
        self.assert_near(self.point_display(), point_tuple, 0.01)
        self.assert_leader_connected(0)
        # One request, with the offset from the point in points.
        self.assertEqual(len(self.move_list), 1)
        tip_index_i, offset_x_f, offset_y_f = self.move_list[0]
        self.assertEqual(tip_index_i, 0)
        pixels_per_point_f = self.plot_widget.pixels_per_point_f()
        self.assertAlmostEqual(offset_x_f * pixels_per_point_f,
                               end_tuple[0] - point_tuple[0],
                               delta=PIXEL_TOLERANCE_PX)
        self.assertAlmostEqual(offset_y_f * pixels_per_point_f,
                               end_tuple[1] - point_tuple[1],
                               delta=PIXEL_TOLERANCE_PX)
        # The other tip did not move.
        self.assertEqual(self.plot_widget.tip_label_offset_tuple(1), ())
        self.assertEqual(self.pin_list, [])
        self.assertEqual(self.range_list, [])

    @covers("LLFR-00152")
    def test_stored_offset_survives_redraw_and_zoom(self) -> None:
        """Drawn again with the requested offset, the label stays put.

        Inputs: none.
        Outputs: none.
        """
        self.drag_label(-60.0, -40.0)
        center_tuple = self.label_center()
        tip_index_i, offset_x_f, offset_y_f = self.move_list[0]
        # The controller draws the tips again with the stored offset.
        self.plot_widget.set_pinned_tips([
            RAMP_TIP_TUPLE + ((offset_x_f, offset_y_f),), SINE_TIP_TUPLE])
        self.draw()
        self.assert_near(self.label_center(), center_tuple)
        self.plot_widget.rebuild_axes()
        self.draw()
        self.assert_near(self.label_center(), center_tuple)
        # After a zoom the label keeps its place relative to the point.
        self.plot_widget.set_time_range(4.0, 6.0)
        self.draw()
        pixels_per_point_f = self.plot_widget.pixels_per_point_f()
        point_tuple = self.point_display()
        self.assert_near(self.label_center(),
                         (point_tuple[0] + offset_x_f * pixels_per_point_f,
                          point_tuple[1] + offset_y_f * pixels_per_point_f))
        self.assert_leader_connected(0)

    @covers("LLFR-00152")
    def test_grab_anywhere_on_the_label_does_not_jump(self) -> None:
        """A label grabbed off its center moves by the pointer movement.

        Inputs: none.
        Outputs: none.
        """
        box = self.plot_widget.tip_box_extent(
            self.plot_widget.pinned_tip_annotation(0))
        start_center_tuple = self.label_center()
        grab_tuple = (box.x0 + 3.0, box.y0 + 3.0)
        self.left_press(grab_tuple)
        self.move_to((grab_tuple[0] - 50.0, grab_tuple[1] - 30.0))
        self.left_release((grab_tuple[0] - 50.0, grab_tuple[1] - 30.0))
        self.draw()
        self.assert_near(self.label_center(),
                         (start_center_tuple[0] - 50.0,
                          start_center_tuple[1] - 30.0))

    @covers("LLFR-00152")
    def test_press_and_release_without_movement_emits_nothing(self) -> None:
        """A click on a pinned tip does not move it or ask for anything.

        Inputs: none.
        Outputs: none.
        """
        start_tuple = self.label_center()
        self.left_press(start_tuple)
        self.move_to(start_tuple)
        self.left_release(start_tuple)
        self.draw()
        self.assertEqual(self.move_list, [])
        self.assertEqual(self.plot_widget.tip_label_offset_tuple(0), ())
        self.assert_near(self.label_center(), start_tuple, 0.01)
        self.assertEqual(self.plot_widget.drag_tip_index_i, -1)

    @covers("LLFR-00152")
    def test_label_center_stays_inside_the_axes(self) -> None:
        """Dragging far outside leaves the label's center in the plot.

        Inputs: none.
        Outputs: none.
        """
        self.drag_label(5000.0, 5000.0)
        axes_box = self.plot_widget.axes.bbox
        center_x_px, center_y_px = self.label_center()
        self.assertLessEqual(center_x_px, axes_box.x1 + PIXEL_TOLERANCE_PX)
        self.assertLessEqual(center_y_px, axes_box.y1 + PIXEL_TOLERANCE_PX)
        self.drag_label(-10000.0, -10000.0)
        center_x_px, center_y_px = self.label_center()
        self.assertGreaterEqual(center_x_px,
                                axes_box.x0 - PIXEL_TOLERANCE_PX)
        self.assertGreaterEqual(center_y_px,
                                axes_box.y0 - PIXEL_TOLERANCE_PX)
        self.assertEqual(len(self.move_list), 2)

    @covers("LLFR-00152")
    def test_redraw_during_a_drag_ends_it_without_request(self) -> None:
        """New tips drawn during a drag end it; nothing is emitted.

        Inputs: none.
        Outputs: none.
        """
        start_tuple = self.label_center()
        self.left_press(start_tuple)
        self.move_to((start_tuple[0] - 40.0, start_tuple[1]))
        self.plot_widget.set_pinned_tips([RAMP_TIP_TUPLE])
        self.left_release((start_tuple[0] - 80.0, start_tuple[1]))
        self.assertEqual(self.move_list, [])
        self.assertEqual(self.plot_widget.drag_tip_index_i, -1)


@requires_qt
class PressOnTipTest(TipDragTestCase):
    """A press on a pinned tip only moves it (LLFR-00153)."""

    @covers("LLFR-00153", "LLFR-00152", "LLFR-00109")
    def test_press_on_tip_with_every_tool_starts_a_move(self) -> None:
        """With any tool or none: no pin, zoom or marker; the tip moves.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_markers([(1, "Marker 1", 5.0)])
        self.draw()
        for tool_str in ALL_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.plot_widget.set_pinned_tips([RAMP_TIP_TUPLE,
                                                  SINE_TIP_TUPLE])
                self.plot_widget.set_plot_tool(tool_str)
                self.draw()
                self.move_list.clear()
                range_tuple = self.plot_widget.time_range_tuple()
                for press_tuple in (self.label_center(),
                                    self.point_display()):
                    # The hover tip of the Tip tool is shown on the ramp.
                    self.plot_widget.hover_at(
                        self.plot_widget.display_to_widget_point(
                            *self.point_display()))
                    self.left_press(press_tuple)
                    self.assertEqual(self.plot_widget.drag_tip_index_i, 0)
                    self.assertEqual(self.plot_widget.hover_tip_text(), "")
                    end_tuple = (press_tuple[0] - 40.0,
                                 press_tuple[1] - 25.0)
                    self.move_to(end_tuple)
                    self.left_release(end_tuple)
                    self.draw()
                self.assertEqual(len(self.move_list), 2)
                self.assertEqual(self.pin_list, [])
                self.assertEqual(self.range_list, [])
                self.assertEqual(self.marker_place_list, [])
                self.assertEqual(self.marker_move_list, [])
                self.assertEqual(self.plot_widget.marker_time_s(1), 5.0)
                self.assertEqual(self.plot_widget.time_range_tuple(),
                                 range_tuple)
                self.assertEqual(self.plot_widget.plot_tool_str, tool_str)

    @covers("LLFR-00153", "LLFR-00045", "LLFR-00078", "LLFR-00081")
    def test_press_away_from_tips_still_uses_the_tool(self) -> None:
        """Off the tips, the tools work as before.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(TIP_TOOL_STR)
        ramp_point = self.point_at(8.0, 3.8)
        self.plot_widget.hover_at(ramp_point)
        display_tuple = self.plot_widget.widget_to_display_tuple(ramp_point)
        self.left_press(display_tuple)
        self.left_release(display_tuple)
        self.assertEqual(len(self.pin_list), 1)
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.left_press(display_tuple)
        self.left_release(display_tuple)
        self.assertEqual(len(self.marker_place_list), 1)
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
        self.left_press(display_tuple)
        self.left_release(display_tuple)
        self.assertEqual(len(self.range_list), 1)
        self.assertEqual(self.move_list, [])

    @covers("LLFR-00153", "LLFR-00117")
    def test_wheel_button_press_during_a_tip_drag_does_not_pan(self) -> None:
        """The wheel button does not start a pan while a tip is held.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        self.plot_widget.set_time_range(3.0, 7.0)
        self.draw()
        start_tuple = self.label_center()
        self.left_press(start_tuple)
        self.send("button_press_event", start_tuple, MouseButton.MIDDLE)
        self.assertFalse(self.plot_widget.panning_b)
        self.left_release(start_tuple)


@requires_qt
class LostReleaseTest(TipDragTestCase):
    """Drags end cleanly when their button release was lost."""

    @covers("LLFR-00152")
    def test_tip_drag_ends_at_last_position_without_button(self) -> None:
        """A move without the left button held ends the tip drag there.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        start_tuple = self.label_center()
        self.left_press(start_tuple)
        last_tuple = (start_tuple[0] - 50.0, start_tuple[1] - 30.0)
        self.move_to(last_tuple, Qt.MouseButton.LeftButton)
        self.assertEqual(self.move_list, [])
        # The release happened outside; the next move has no button.
        self.move_to((start_tuple[0] - 150.0, start_tuple[1] - 60.0),
                     Qt.MouseButton.NoButton)
        self.draw()
        self.assertEqual(len(self.move_list), 1)
        self.assertEqual(self.plot_widget.drag_tip_index_i, -1)
        self.assert_near(self.label_center(), last_tuple)
        # Later moves and a late release change nothing.
        self.move_to((start_tuple[0] - 200.0, start_tuple[1]),
                     Qt.MouseButton.NoButton)
        self.left_release((start_tuple[0] - 200.0, start_tuple[1]))
        self.draw()
        self.assertEqual(len(self.move_list), 1)
        self.assert_near(self.label_center(), last_tuple)

    @covers("LLFR-00086", "LLFR-00093")
    def test_marker_drag_ends_at_last_position_without_button(self) -> None:
        """A move without the left button held ends the marker drag.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        self.plot_widget.set_pinned_tips([])
        self.plot_widget.set_markers([(1, "Marker 1", 4.0)])
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.draw()
        line_tuple = tuple(self.plot_widget.axes.transData.transform(
            (4.0, 0.0)))
        self.left_press(line_tuple)
        self.assertEqual(self.plot_widget.drag_marker_id_i, 1)
        target_x_px = float(self.plot_widget.axes.transData.transform(
            (6.0, 0.0))[0])
        self.move_to((target_x_px, line_tuple[1]),
                     Qt.MouseButton.LeftButton)
        dragged_time_s = self.plot_widget.marker_time_s(1)
        self.assertAlmostEqual(dragged_time_s, 6.0, delta=0.05)
        far_x_px = float(self.plot_widget.axes.transData.transform(
            (8.0, 0.0))[0])
        self.move_to((far_x_px, line_tuple[1]), Qt.MouseButton.NoButton)
        self.assertEqual(self.marker_move_list, [(1, dragged_time_s)])
        self.assertEqual(self.plot_widget.drag_marker_id_i, -1)
        self.assertEqual(self.plot_widget.marker_time_s(1), dragged_time_s)
        self.assertEqual(self.marker_place_list, [])

    @covers("LLFR-00117")
    def test_pan_stops_when_the_wheel_button_is_not_held(self) -> None:
        """A move without the wheel button held ends the pan unmoved.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        from PyQt6.QtCore import Qt
        self.plot_widget.set_time_range(3.0, 5.0)
        self.draw()
        transform = self.plot_widget.axes.transData
        grab_tuple = tuple(transform.transform((4.0, 0.0)))
        self.send("button_press_event", grab_tuple, MouseButton.MIDDLE)
        self.assertTrue(self.plot_widget.panning_b)
        self.move_to(tuple(transform.transform((4.5, 0.0))),
                     Qt.MouseButton.MiddleButton)
        panned_tuple = self.plot_widget.time_range_tuple()
        self.assertNotEqual(panned_tuple, (3.0, 5.0))
        self.move_to((grab_tuple[0] - 100.0, grab_tuple[1]),
                     Qt.MouseButton.NoButton)
        self.assertFalse(self.plot_widget.panning_b)
        self.assertEqual(self.plot_widget.time_range_tuple(), panned_tuple)
        self.move_to((grab_tuple[0] - 150.0, grab_tuple[1]))
        self.assertEqual(self.plot_widget.time_range_tuple(), panned_tuple)


@requires_qt
class RightPressDuringDragTest(TipDragTestCase):
    """A right press cancels any drag before the menu logic runs."""

    def record_menus(self) -> list:
        """Replace the modal menu by a recorder that chooses nothing.

        Inputs: none.
        Outputs: the list that receives the texts of each shown menu.
        """
        shown_list = []

        def fake_execute_menu(menu, global_point):
            """Record the menu texts and close it without a choice.

            Inputs:
                menu: the QMenu that would be shown.
                global_point: QPoint in screen coordinates.
            Outputs: None.
            """
            shown_list.append([action.text() for action in menu.actions()])
            return None

        self.plot_widget.execute_menu = fake_execute_menu
        return shown_list

    def right_press(self, display_tuple: tuple) -> None:
        """Right-press at a display point and let the menu run.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        self.send("button_press_event", display_tuple, MouseButton.RIGHT)
        for _ in range(3):
            self.application.processEvents()

    @covers("LLFR-00152", "LLFR-00046")
    def test_right_press_cancels_a_tip_drag(self) -> None:
        """The label goes back, nothing is requested, the menu shows.

        Inputs: none.
        Outputs: none.
        """
        shown_list = self.record_menus()
        start_tuple = self.label_center()
        self.left_press(start_tuple)
        self.move_to((start_tuple[0] - 60.0, start_tuple[1] - 30.0))
        self.right_press(start_tuple)
        self.left_release((start_tuple[0] - 60.0, start_tuple[1] - 30.0))
        self.draw()
        self.assertEqual(self.move_list, [])
        self.assertEqual(self.plot_widget.drag_tip_index_i, -1)
        self.assert_near(self.label_center(), start_tuple)
        self.assertEqual(shown_list, [["Delete"]])

    @covers("LLFR-00086", "LLFR-00087")
    def test_right_press_cancels_a_marker_drag(self) -> None:
        """The marker goes back to its time and nothing is requested.

        Inputs: none.
        Outputs: none.
        """
        shown_list = self.record_menus()
        self.plot_widget.set_pinned_tips([])
        self.plot_widget.set_markers([(1, "Marker 1", 4.0)])
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.draw()
        transform = self.plot_widget.axes.transData
        line_tuple = tuple(transform.transform((4.0, 0.0)))
        self.left_press(line_tuple)
        self.move_to(tuple(transform.transform((6.0, 0.0))))
        self.right_press(line_tuple)
        self.left_release(tuple(transform.transform((6.0, 0.0))))
        self.assertEqual(self.marker_move_list, [])
        self.assertEqual(self.plot_widget.marker_time_s(1), 4.0)
        self.assertEqual(shown_list, [["Rename", "Delete"]])

    @covers("LLFR-00117", "LLFR-00048")
    def test_right_press_stops_a_pan(self) -> None:
        """A pan in progress stops; later moves do not pan.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        shown_list = self.record_menus()
        self.plot_widget.set_pinned_tips([])
        self.plot_widget.set_time_range(3.0, 5.0)
        self.draw()
        transform = self.plot_widget.axes.transData
        grab_tuple = tuple(transform.transform((4.0, -1.0)))
        self.send("button_press_event", grab_tuple, MouseButton.MIDDLE)
        self.right_press(grab_tuple)
        self.assertFalse(self.plot_widget.panning_b)
        self.move_to(tuple(transform.transform((4.5, -1.0))))
        self.assertEqual(self.plot_widget.time_range_tuple(), (3.0, 5.0))
        self.assertEqual(len(shown_list), 1)


@requires_qt
class PixelWheelTest(PlotWidgetToolTestCase):
    """Wheel events that only report pixels still zoom (LLFR-00113)."""

    @covers("LLFR-00113", "LLFR-00074")
    def test_pixel_delta_is_used_when_the_angle_is_zero(self) -> None:
        """120 pixels count as one notch; the angle wins when present.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import wheel_step_f
        self.assertEqual(wheel_step_f(FakeScrollEvent(
            9.0, FakePixelWheelEvent(0, 60))), 0.5)
        self.assertEqual(wheel_step_f(FakeScrollEvent(
            9.0, FakePixelWheelEvent(0, -120))), -1.0)
        self.assertEqual(wheel_step_f(FakeScrollEvent(
            9.0, FakePixelWheelEvent(0, 0))), 0.0)
        self.assertEqual(wheel_step_f(FakeScrollEvent(
            9.0, FakePixelWheelEvent(240, 30))), 2.0)
        # Through the scroll handler: half a notch keeps 0.95 ** 0.5.
        self.plot_widget.on_mouse_scroll(_scroll_at(
            self.plot_widget, 5.0, FakePixelWheelEvent(0, 60)))
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(end_s - start_s, 10.0 * 0.95 ** 0.5)

    @covers("LLFR-00113")
    def test_real_pixel_only_wheel_event_zooms(self) -> None:
        """A real QWheelEvent with only pixels zooms by its pixels.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint, QPointF, Qt
        from PyQt6.QtGui import QWheelEvent
        if self.application.platformName() == "xcb":
            self.skipTest("matplotlib ignores pixel deltas on X11")
        canvas = self.plot_widget.canvas
        local_point = QPointF(canvas.mapFrom(self.plot_widget,
                                             self.point_at(5.0)))
        wheel_event = QWheelEvent(
            local_point, QPointF(canvas.mapToGlobal(local_point)),
            QPoint(0, 120), QPoint(0, 0), Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
            False)
        self.application.sendEvent(canvas, wheel_event)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(end_s - start_s, 9.5)
        self.assertEqual(len(self.range_list), 1)


def _scroll_at(plot_widget, time_s: float, gui_event):
    """Return a fake scroll event at a time of a plot.

    Inputs:
        plot_widget: the PlotWidget.
        time_s: x value in seconds under the mouse.
        gui_event: the fake Qt wheel event.
    Outputs: a FakeScrollEvent with display x and y set.
    """
    scroll_event = FakeScrollEvent(1.0, gui_event)
    display_array = plot_widget.axes.transData.transform((time_s, 0.0))
    scroll_event.x = float(display_array[0])
    scroll_event.y = float(display_array[1])
    return scroll_event


@requires_qt
class TipMoveEndToEndTest(unittest.TestCase):
    """Drag a pinned tip through MainWindow and the real controllers."""

    def setUp(self) -> None:
        """Create the window and controllers, open a CSV, plot speed.

        Inputs: none.
        Outputs: none.
        """
        import os
        import tempfile
        from unittest import mock
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QFileDialog
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.temporary_directory = tempfile.TemporaryDirectory()
        path_str = os.path.join(self.temporary_directory.name, "data.csv")
        with open(path_str, "w", encoding="utf-8") as csv_file:
            csv_file.write("Time,speed\n")
            for index_i in range(11):
                csv_file.write(f"{index_i},{index_i * 2}\n")
        self.window = MainWindow()
        self.window.resize(1000, 700)
        self.controller = MainController(self.window)
        self.controller.start()
        self.window.show()
        with mock.patch.object(QFileDialog, "getOpenFileName",
                               return_value=(path_str, "")):
            self.window.top_panel.open_file_button.click()
            self.process_events()
        self.window.signal_double_click_handler("speed")
        self.process_events()

    def tearDown(self) -> None:
        """Close the window and remove the temporary file.

        Inputs: none.
        Outputs: none.
        """
        self.process_events()
        self.window.close()
        self.window.deleteLater()
        self.process_events()
        self.temporary_directory.cleanup()

    def process_events(self) -> None:
        """Let Qt handle pending events and deferred calls.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(3):
            self.application.processEvents()

    @covers("LLFR-00152", "LLFR-00151", "HLFR-00041")
    def test_dragged_tip_is_kept_by_the_controller(self) -> None:
        """The moved label is stored and drawn there after a zoom.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton, MouseEvent
        plot_widget_list = list(
            self.window.plot_panel.plot_widget_dict.values())
        self.assertEqual(len(plot_widget_list), 1)
        plot_widget = plot_widget_list[0]
        plot_widget.tip_pin_requested.emit("speed", 5.0, 10.0)
        self.process_events()
        plot_widget.canvas.draw()
        self.assertEqual(plot_widget.pinned_tip_count(), 1)
        start_tuple = plot_widget.tip_label_center_tuple(0)
        end_tuple = (start_tuple[0] - 60.0, start_tuple[1] - 40.0)
        for name_str, display_tuple, button in (
                ("button_press_event", start_tuple, MouseButton.LEFT),
                ("motion_notify_event", end_tuple, None),
                ("button_release_event", end_tuple, MouseButton.LEFT)):
            event = MouseEvent(name_str, plot_widget.canvas,
                               display_tuple[0], display_tuple[1],
                               button=button)
            plot_widget.canvas.callbacks.process(name_str, event)
        self.process_events()
        plot_widget.canvas.draw()
        plot = self.controller.plot_controller.workspace.find_plot(
            plot_widget.plot_id_i)
        pinned_tip = plot.pinned_tip_list[0]
        self.assertEqual((pinned_tip.signal_name_str, pinned_tip.time_s,
                          pinned_tip.value_f), ("speed", 5.0, 10.0))
        self.assertEqual(len(pinned_tip.label_offset_tuple), 2)
        self.assertEqual(plot_widget.pinned_tip_text(0),
                         "t = 5 s\nspeed = 10")
        center_tuple = plot_widget.tip_label_center_tuple(0)
        self.assertAlmostEqual(center_tuple[0], end_tuple[0],
                               delta=PIXEL_TOLERANCE_PX)
        self.assertAlmostEqual(center_tuple[1], end_tuple[1],
                               delta=PIXEL_TOLERANCE_PX)
        # A zoom keeps the label at its offset from the point.
        plot_widget.wheel_at(plot_widget.data_to_widget_point(5.0, 10.0),
                             2.0)
        self.process_events()
        plot_widget.canvas.draw()
        point_array = plot_widget.axes.transData.transform((5.0, 10.0))
        pixels_per_point_f = plot_widget.pixels_per_point_f()
        center_tuple = plot_widget.tip_label_center_tuple(0)
        offset_x_f, offset_y_f = pinned_tip.label_offset_tuple
        self.assertAlmostEqual(
            center_tuple[0], point_array[0] + offset_x_f * pixels_per_point_f,
            delta=PIXEL_TOLERANCE_PX)
        self.assertAlmostEqual(
            center_tuple[1], point_array[1] + offset_y_f * pixels_per_point_f,
            delta=PIXEL_TOLERANCE_PX)


if __name__ == "__main__":
    unittest.main()
