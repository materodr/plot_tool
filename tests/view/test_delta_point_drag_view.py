"""Tests for moving the points of a delta marker and for the delta
marker of value zero in the view (HLFR-00099, HLFR-00098).

The plot widget tests drive the same matplotlib callbacks that real
mouse events reach, on the shown 600x400 plot widget of
tests.view.test_delta_markers_view ("Sine" and "Ramp", sampled every
0.1 s from 0 s to 10 s). The end-to-end test uses a real MainWindow and
MainController. No modal dialog or menu is ever opened.
"""

import unittest

from tests.support import covers, requires_qt
from tests.view.test_delta_markers_view import (
    DeltaWidgetTestCase, DeltaWindowTestCase)
from tests.view.test_markers_view import (
    LEFT_BUTTON_I, RIGHT_BUTTON_I, recorder, send_mouse_event)

from controller.plot_tools import (
    DELTA_TOOL_TUPLE, DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR, MARKER_TOOL_STR,
    NO_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR)
from model.workspace import DELTA_X_KIND_STR

# Display pixels moved by a press that is not a drag (less than 5).
SHORT_MOVE_PX_F = 2.0
# Number of steps of a drag from the press point to the release point.
DRAG_STEP_COUNT_I = 6


@requires_qt
class DeltaPointWidgetTestCase(DeltaWidgetTestCase):
    """A Delta X marker (id 1) from Sine at 2 s to Ramp at 6 s."""

    def setUp(self) -> None:
        """Draw the marker and record the move requests.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.first_tuple = self.sine_point(2.0)
        self.second_tuple = self.ramp_point(6.0)
        self.set_delta_markers([(1, DELTA_X_KIND_STR, self.first_tuple,
                                 self.second_tuple)])
        self.point_move_list = recorder(
            self.plot_widget.delta_point_move_requested)

    def send_at(self, event_name_str: str, display_tuple: tuple,
                button_i: int = LEFT_BUTTON_I) -> None:
        """Send a mouse event at a display point.

        Inputs:
            event_name_str: the matplotlib event name.
            display_tuple: (x, y) in display pixels.
            button_i: matplotlib button number.
        Outputs: none.
        """
        send_mouse_event(self.plot_widget, event_name_str,
                         float(display_tuple[0]), float(display_tuple[1]),
                         button_i)

    def press_and_move(self, start_tuple: tuple, end_tuple: tuple) -> None:
        """Press the left button at one display point and move in steps
        to another, without releasing.

        Inputs:
            start_tuple: (x, y) of the press, in display pixels.
            end_tuple: (x, y) of the last move, in display pixels.
        Outputs: none.
        """
        self.send_at("button_press_event", start_tuple)
        for step_i in range(1, DRAG_STEP_COUNT_I + 1):
            fraction_f = step_i / DRAG_STEP_COUNT_I
            self.send_at("motion_notify_event", (
                start_tuple[0] + fraction_f * (end_tuple[0] - start_tuple[0]),
                start_tuple[1] + fraction_f * (end_tuple[1]
                                               - start_tuple[1])))

    def drag_display(self, start_tuple: tuple, end_tuple: tuple) -> None:
        """Press, move in steps and release, at display points.

        Inputs:
            start_tuple: (x, y) of the press, in display pixels.
            end_tuple: (x, y) of the release, in display pixels.
        Outputs: none.
        """
        self.press_and_move(start_tuple, end_tuple)
        self.send_at("button_release_event", end_tuple)

    def point_display(self, point_tuple: tuple) -> tuple:
        """Return the display point of a curve sample.

        Inputs:
            point_tuple: (signal_name_str, time_s, value_f).
        Outputs: (x, y) in display pixels.
        """
        return self.display_tuple(point_tuple[1], point_tuple[2])

    def drawn_points(self) -> tuple:
        """Return the two points of marker 1 as drawn now.

        Inputs: none.
        Outputs: (first_point_tuple, second_point_tuple).
        """
        marker_tuple = self.plot_widget.delta_marker_data_list[0]
        return (marker_tuple[2], marker_tuple[3])

    def assert_unchanged(self) -> None:
        """Check that marker 1 is drawn at its points and nothing was
        requested or picked.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.drawn_points(),
                         (self.first_tuple, self.second_tuple))
        self.assertEqual(self.point_move_list, [])
        self.assertEqual(self.pick_list, [])


class DeltaPointDragTest(DeltaPointWidgetTestCase):
    """Dragging a point with the delta tools and with no tool."""

    @covers("LLFR-00433", "LLFR-00862", "LLFR-00863", "LLFR-00864",
            "LLFR-00434", "LLFR-00454", "HLFR-00099")
    def test_drag_with_a_delta_tool_follows_the_curve(self) -> None:
        """With Delta X or Delta Y active, a drag of the second dot moves
        it along Ramp to the sample under the pointer; the first point
        stays; the value follows; the release asks once for the move
        and nothing is picked or pinned.

        Inputs: none.
        Outputs: none.
        """
        from view import value_text
        target_tuple = self.ramp_point(8.0)
        for tool_str in DELTA_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.set_delta_markers([(1, DELTA_X_KIND_STR,
                                         self.first_tuple,
                                         self.second_tuple)])
                self.point_move_list.clear()
                # Moved a little above the curve: the point stays on it.
                end_tuple = self.point_display(target_tuple)
                end_tuple = (end_tuple[0], end_tuple[1] + 15.0)
                self.press_and_move(self.point_display(self.second_tuple),
                                    end_tuple)
                self.assertTrue(self.plot_widget.delta_point_drag_shown())
                self.assertTrue(
                    self.plot_widget.is_mouse_drag_in_progress())
                first_tuple, second_tuple = self.drawn_points()
                self.assertEqual(first_tuple, self.first_tuple)
                self.assertEqual(second_tuple, target_tuple)
                delta_s = target_tuple[1] - self.first_tuple[1]
                self.assertEqual(
                    self.plot_widget.delta_marker_data_list[0][4], delta_s)
                self.assertEqual(self.plot_widget.delta_label_text(1),
                                 value_text.format_delta_x_text(delta_s))
                self.assertEqual(self.point_move_list, [])
                self.send_at("button_release_event", end_tuple)
                self.assertFalse(
                    self.plot_widget.is_mouse_drag_in_progress())
                self.assertEqual(self.point_move_list,
                                 [(1, 1, target_tuple[1], target_tuple[2])])
                self.assertEqual(self.pick_list, [])
                self.assertEqual(self.pin_list, [])

    @covers("LLFR-00794", "LLFR-00433", "LLFR-00862", "LLFR-00863",
            "HLFR-00085", "HLFR-00099")
    def test_drag_with_no_tool_moves_the_first_point(self) -> None:
        """With no tool active, the first dot is dragged along Sine.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        target_tuple = self.sine_point(3.0)
        self.drag_display(self.point_display(self.first_tuple),
                          self.point_display(target_tuple))
        self.assertEqual(self.drawn_points(),
                         (target_tuple, self.second_tuple))
        self.assertEqual(self.point_move_list,
                         [(1, 0, target_tuple[1], target_tuple[2])])
        self.assertEqual(self.pick_list, [])

    @covers("LLFR-00383", "LLFR-00794", "LLFR-00790")
    def test_dot_inside_an_area_moves_the_point(self) -> None:
        """With no tool, a dot drawn inside an area is dragged before the
        area, which stays where it is (delta marker points come before
        flags and areas).

        Inputs: none.
        Outputs: none.
        """
        area_change_list = recorder(self.plot_widget.area_change_requested)
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        self.plot_widget.set_areas([(7, "Area 1", 5.0, 7.0)])
        self.draw()
        target_tuple = self.ramp_point(6.5)
        self.drag_display(self.point_display(self.second_tuple),
                          self.point_display(target_tuple))
        self.assertEqual(self.point_move_list,
                         [(1, 1, target_tuple[1], target_tuple[2])])
        self.assertEqual(area_change_list, [])
        self.assertEqual(self.plot_widget.area_drawn_span_tuple(7),
                         (5.0, 7.0))

    @covers("LLFR-00433", "LLFR-00801", "LLFR-00384")
    def test_other_tools_never_move_a_point(self) -> None:
        """With the Tip, Zoom or Flag tool, a drag on a dot moves no
        point of the delta marker.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (TIP_TOOL_STR, ZOOM_TOOL_STR, MARKER_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.set_delta_markers([(1, DELTA_X_KIND_STR,
                                         self.first_tuple,
                                         self.second_tuple)])
                self.drag_display(self.point_display(self.second_tuple),
                                  self.point_display(self.ramp_point(8.0)))
                self.assertFalse(self.plot_widget.delta_point_drag_shown())
                self.assertEqual(self.drawn_points(),
                                 (self.first_tuple, self.second_tuple))
                self.assertEqual(self.point_move_list, [])

    @covers("LLFR-00435", "LLFR-00433", "HLFR-00098")
    def test_zero_value_keeps_the_last_other_sample(self) -> None:
        """Dragging the second point onto the first point's time stops
        on the last sample that gave another value.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        last_tuple = self.ramp_point(3.0)
        self.press_and_move(self.point_display(self.second_tuple),
                            self.point_display(last_tuple))
        self.assertEqual(self.drawn_points()[1], last_tuple)
        zero_display_tuple = self.point_display(self.ramp_point(2.0))
        self.send_at("motion_notify_event", zero_display_tuple)
        self.assertEqual(self.drawn_points()[1], last_tuple)
        self.assertNotEqual(self.plot_widget.delta_marker_data_list[0][4],
                            0.0)
        self.send_at("button_release_event", zero_display_tuple)
        self.assertEqual(self.point_move_list,
                         [(1, 1, last_tuple[1], last_tuple[2])])

    @covers("LLFR-00433")
    def test_point_stays_in_the_shown_range(self) -> None:
        """A pointer far right of the plot leaves the point on the last
        sample of the shown range.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        self.plot_widget.set_time_range(0.0, 7.0)
        self.draw()
        _, end_s = self.plot_widget.time_range_tuple()
        start_tuple = self.point_display(self.second_tuple)
        axes_box = self.plot_widget.axes.bbox
        self.drag_display(start_tuple, (axes_box.x1 + 60.0, start_tuple[1]))
        second_tuple = self.drawn_points()[1]
        self.assertEqual(second_tuple[0], "Ramp")
        self.assertLessEqual(second_tuple[1], end_s)
        # The samples are 0.1 s apart.
        self.assertGreater(second_tuple[1], end_s - 0.11)
        self.assertEqual(len(self.point_move_list), 1)

    @covers("LLFR-00865", "LLFR-00434")
    def test_drag_keeps_a_picked_first_point(self) -> None:
        """A first point already picked keeps its dot during and after
        the drag, and nothing is picked.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        picked_tuple = self.sine_point(5.0)
        self.plot_widget.set_delta_first_point(picked_tuple)
        self.draw()
        first_dot = self.plot_widget.delta_first_point_artist
        self.drag_display(self.point_display(self.second_tuple),
                          self.point_display(self.ramp_point(7.0)))
        self.assertEqual(self.plot_widget.delta_first_point_tuple,
                         picked_tuple)
        self.assertIs(self.plot_widget.delta_first_point_artist, first_dot)
        self.assertEqual(self.pick_list, [])
        self.assertEqual(len(self.point_move_list), 1)

    @covers("LLFR-00433", "LLFR-00140")
    def test_drag_back_to_the_start_or_cancelled_asks_nothing(self) -> None:
        """A drag that ends on the starting sample, or that a right press
        cancels, asks for no move and leaves the point where it was.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        start_tuple = self.point_display(self.second_tuple)
        self.press_and_move(start_tuple,
                            self.point_display(self.ramp_point(8.0)))
        self.send_at("motion_notify_event", start_tuple)
        self.send_at("button_release_event", start_tuple)
        self.assert_unchanged()
        # A right press during a drag cancels it.
        self.plot_widget.execute_menu = lambda menu, global_point: None
        self.press_and_move(start_tuple,
                            self.point_display(self.ramp_point(8.0)))
        self.assertEqual(self.drawn_points()[1], self.ramp_point(8.0))
        self.send_at("button_press_event",
                     self.point_display(self.ramp_point(8.0)),
                     RIGHT_BUTTON_I)
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        self.assert_unchanged()


class DeltaPointShortPressTest(DeltaPointWidgetTestCase):
    """A press on a dot that moves less than 5 pixels."""

    @covers("LLFR-00866", "LLFR-00163")
    def test_short_press_with_a_delta_tool_is_a_click(self) -> None:
        """With Delta X or Delta Y, it picks the curve sample under it.

        Inputs: none.
        Outputs: none.
        """
        start_tuple = self.point_display(self.second_tuple)
        end_tuple = (start_tuple[0] + SHORT_MOVE_PX_F, start_tuple[1])
        for tool_str in (DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.pick_list.clear()
                self.send_at("button_press_event", start_tuple)
                self.send_at("motion_notify_event", end_tuple)
                self.assertFalse(self.plot_widget.delta_point_drag_shown())
                self.assertEqual(self.pick_list, [])
                self.send_at("button_release_event", end_tuple)
                self.assertEqual(self.pick_list, [self.second_tuple])
                self.assertEqual(self.point_move_list, [])
                self.assertEqual(self.drawn_points(),
                                 (self.first_tuple, self.second_tuple))

    @covers("LLFR-00867", "LLFR-00868")
    def test_short_press_with_no_tool_does_nothing(self) -> None:
        """With no tool, it does nothing and asks for nothing.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        start_tuple = self.point_display(self.first_tuple)
        end_tuple = (start_tuple[0], start_tuple[1] + SHORT_MOVE_PX_F)
        self.send_at("button_press_event", start_tuple)
        self.send_at("motion_notify_event", end_tuple)
        self.send_at("button_release_event", end_tuple)
        self.assert_unchanged()
        self.assertEqual(self.pin_list, [])
        self.assertEqual(self.range_list, [])
        self.assertEqual(self.place_list, [])

    @covers("LLFR-00795", "LLFR-00796")
    def test_drag_on_the_bracket_with_no_tool_does_nothing(self) -> None:
        """A drag on the bracket, away from the dots, moves nothing.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        bracket_array = self.bracket_vertex_array(1)
        middle_tuple = tuple(bracket_array[len(bracket_array) // 2])
        self.assertEqual(self.plot_widget.delta_dot_at(
            self.plot_widget.display_to_widget_point(*middle_tuple)), ())
        self.drag_display(middle_tuple,
                          (middle_tuple[0] + 40.0, middle_tuple[1] - 30.0))
        self.assert_unchanged()


class DeltaZeroPreviewTest(DeltaWidgetTestCase):
    """No preview of a delta marker of value zero (LLFR-00432)."""

    @covers("LLFR-00432", "LLFR-00353", "HLFR-00098")
    def test_no_preview_where_the_value_would_be_zero(self) -> None:
        """Over the first point's time (Delta X) or value (Delta Y) no
        marker preview is shown; elsewhere it is.

        Inputs: none.
        Outputs: none.
        """
        for tool_str, first_tuple, zero_tuple, other_tuple in (
                (DELTA_X_TOOL_STR, self.sine_point(3.0),
                 self.ramp_point(3.0), self.ramp_point(4.0)),
                (DELTA_Y_TOOL_STR, self.ramp_point(5.0),
                 self.ramp_point(5.0), self.ramp_point(6.0))):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.plot_widget.set_delta_first_point(first_tuple)
                self.draw()
                self.mouse("motion_notify_event", *zero_tuple[1:])
                # The whole preview is hidden, the dot too.
                self.assertFalse(self.plot_widget.delta_preview_shown())
                self.assertFalse(
                    self.plot_widget.delta_preview_marker_shown())
                self.assertEqual(self.plot_widget.delta_preview_text(), "")
                self.mouse("motion_notify_event", *other_tuple[1:])
                self.assertTrue(
                    self.plot_widget.delta_preview_marker_shown())
                self.plot_widget.on_mouse_leave(None)


@requires_qt
class DeltaPointEndToEndTest(DeltaWindowTestCase):
    """Drag a point with the real window and controllers, then undo."""

    def send_at(self, plot_widget, event_name_str: str, time_s: float,
                value_f: float) -> None:
        """Send a left mouse event at a data point of a plot.

        Inputs:
            plot_widget: the PlotWidget.
            event_name_str: the matplotlib event name.
            time_s: x value in seconds.
            value_f: y value.
        Outputs: none.
        """
        display_x_px, display_y_px = (
            plot_widget.axes.transData.transform((time_s, value_f)))
        send_mouse_event(plot_widget, event_name_str, float(display_x_px),
                         float(display_y_px), LEFT_BUTTON_I)

    def current_plot_widget(self):
        """Return the only plot widget of the window.

        Inputs: none.
        Outputs: the PlotWidget.
        """
        plot_widget_list = list(
            self.main_window.plot_panel.plot_widget_dict.values())
        self.assertEqual(len(plot_widget_list), 1)
        return plot_widget_list[0]

    @covers("LLFR-00433", "LLFR-00431", "LLFR-00860", "LLFR-00140",
            "LLFR-00138", "HLFR-00099", "HLFR-00098")
    def test_measure_drag_and_undo(self) -> None:
        """A click at the first point's time draws nothing; speed at
        0.5 s to force at 1.5 s, then the second point is dragged to
        force at 2 s: "Δt = 1.5 s"; undo brings it back to 1.5 s.

        Inputs: none.
        Outputs: none.
        """
        plot_widget = self.plot_speed_and_force()
        self.click(self.top_panel.delta_x_button)
        for event_name_str in ("button_press_event", "button_release_event"):
            self.send_at(plot_widget, event_name_str, 0.5, 1.0)
        self.process_events()
        # LLFR-00431, LLFR-00860: force at 0.5 s has the same time.
        plot_widget = self.current_plot_widget()
        for event_name_str in ("button_press_event", "button_release_event"):
            self.send_at(plot_widget, event_name_str, 0.5, 0.0)
        self.process_events()
        plot_widget = self.current_plot_widget()
        self.assertEqual(plot_widget.delta_marker_id_list(), [])
        self.assertEqual(plot_widget.delta_first_point_tuple,
                         ("speed", 0.5, 1.0))
        for event_name_str in ("button_press_event", "button_release_event"):
            self.send_at(plot_widget, event_name_str, 1.5, 0.0)
        self.process_events()
        plot_widget = self.current_plot_widget()
        marker_id_i = plot_widget.delta_marker_id_list()[0]
        self.assertEqual(plot_widget.delta_label_text(marker_id_i),
                         "Δt = 1 s")
        # Drag the second dot (force at 1.5 s) to force at 2 s.
        self.send_at(plot_widget, "button_press_event", 1.5, 0.0)
        for step_i in range(1, DRAG_STEP_COUNT_I + 1):
            fraction_f = step_i / DRAG_STEP_COUNT_I
            self.send_at(plot_widget, "motion_notify_event",
                         1.5 + 0.5 * fraction_f, fraction_f)
        self.send_at(plot_widget, "button_release_event", 2.0, 1.0)
        self.process_events()
        plot = self.plot_controller.workspace.find_plot(
            plot_widget.plot_id_i)
        self.assertEqual(plot.delta_marker_list[0].first_point_tuple,
                         ("speed", 0.5, 1.0))
        self.assertEqual(plot.delta_marker_list[0].second_point_tuple,
                         ("force", 2.0, 1.0))
        plot_widget = self.current_plot_widget()
        self.assertEqual(plot_widget.delta_label_text(marker_id_i),
                         "Δt = 1.5 s")
        self.main_window.run_undo()
        self.process_events()
        plot = self.plot_controller.workspace.find_plot(
            plot_widget.plot_id_i)
        self.assertEqual(plot.delta_marker_list[0].second_point_tuple,
                         ("force", 1.5, 0.0))
        self.assertEqual(self.box_mock.call_count, 0)


if __name__ == "__main__":
    unittest.main()
