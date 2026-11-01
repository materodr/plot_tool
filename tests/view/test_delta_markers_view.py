"""Tests for the Delta X and Delta Y markers in the view (HLFR-00043/44).

The plot widget tests drive the same matplotlib callbacks that real
mouse events reach and replace ``execute_menu`` so no modal menu is
ever opened. The top panel and end-to-end tests use a real MainWindow
and MainController with patched dialogs.
"""

import os
import tempfile
import unittest
from unittest import mock

import numpy as np

from tests.support import button_name, covers, get_qt_application
from tests.support import button_tip_line_list, requires_qt

from controller.plot_tools import (
    DELTA_TOOL_TUPLE, DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR, MARKER_TOOL_STR,
    NO_TOOL_STR, PLOT_TOOL_TUPLE, TIP_TOOL_STR, ZOOM_TOOL_STR)
from model.curve_colors import MARKER_COLOR_STR
from model.workspace import DELTA_X_KIND_STR, DELTA_Y_KIND_STR
from tests.view.test_markers_view import (
    LEFT_BUTTON_I, RIGHT_BUTTON_I, MarkerWidgetTestCase, all_menu_actions,
    recorder, send_mouse_event)

# Display pixels allowed between where an item is and where it should be.
POSITION_TOLERANCE_PX_F = 1.5
FILE_TEXT_STR = (
    "Time,speed,force\n"
    "0,0,1\n0.5,1,0\n1,2,-1\n1.5,3,0\n2,4,1\n")


def to_hex_str(color) -> str:
    """Return a matplotlib color as a lower-case "#rrggbb" string.

    Inputs:
        color: any matplotlib color.
    Outputs: the hex string.
    """
    from matplotlib.colors import to_hex
    return to_hex(color)


class DeltaWidgetTestCase(MarkerWidgetTestCase):
    """A shown plot widget with "Sine" (red) and "Ramp" (blue)."""

    def setUp(self) -> None:
        """Create the widget of MarkerWidgetTestCase and record picks.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.pick_list = recorder(self.plot_widget.delta_point_picked)
        self.delta_delete_list = recorder(
            self.plot_widget.delta_marker_delete_requested)

    def sine_point(self, time_s: float) -> tuple:
        """Return the sample of "Sine" at a time of the time array.

        Inputs:
            time_s: a time of the sample grid (0, 0.1, ..., 10 s).
        Outputs: (signal_name_str, time_s, value_f).
        """
        index_i = int(round(time_s * 10.0))
        return ("Sine", float(self.time_array[index_i]),
                float(self.sine_array[index_i]))

    def ramp_point(self, time_s: float) -> tuple:
        """Return the sample of "Ramp" at a time of the time array.

        Inputs:
            time_s: a time of the sample grid.
        Outputs: (signal_name_str, time_s, value_f).
        """
        index_i = int(round(time_s * 10.0))
        return ("Ramp", float(self.time_array[index_i]),
                float(self.ramp_array[index_i]))

    def set_delta_markers(self, marker_list: list) -> None:
        """Draw delta markers, computing the shown value like the model.

        Inputs:
            marker_list: tuples (id, kind_str, first_point, second_point).
        Outputs: none.
        """
        data_list = []
        for marker_id_i, kind_str, first_tuple, second_tuple in marker_list:
            index_i = 1 if kind_str == DELTA_X_KIND_STR else 2
            data_list.append((marker_id_i, kind_str, first_tuple,
                              second_tuple,
                              second_tuple[index_i] - first_tuple[index_i]))
        self.plot_widget.set_delta_markers(data_list)
        self.draw()

    def left_click(self, time_s: float, value_f: float) -> None:
        """Press and release the left button at a data point.

        Inputs:
            time_s: x value in seconds.
            value_f: y value.
        Outputs: none.
        """
        self.mouse("button_press_event", time_s, value_f)
        self.mouse("button_release_event", time_s, value_f)

    def assert_near(self, first_tuple: tuple, second_tuple: tuple) -> None:
        """Check that two display points are within the tolerance.

        Inputs:
            first_tuple: (x, y) in display pixels.
            second_tuple: (x, y) in display pixels.
        Outputs: none.
        """
        self.assertLessEqual(abs(first_tuple[0] - second_tuple[0]),
                             POSITION_TOLERANCE_PX_F)
        self.assertLessEqual(abs(first_tuple[1] - second_tuple[1]),
                             POSITION_TOLERANCE_PX_F)

    def bracket_vertex_array(self, marker_id_i: int):
        """Return the bracket's vertices as drawn now, in display pixels.

        Inputs:
            marker_id_i: id of the delta marker.
        Outputs: numpy array of shape (N, 2).
        """
        return np.asarray(
            self.plot_widget.delta_bracket_path(marker_id_i).vertices)

    def assert_delta_x_attached(self, marker_id_i: int, first_tuple: tuple,
                                second_tuple: tuple) -> None:
        """Check a Delta X bracket: ends at the times, above, tip up.

        Inputs:
            marker_id_i: id of the delta marker.
            first_tuple: the first point.
            second_tuple: the second point.
        Outputs: none.
        """
        vertex_array = self.bracket_vertex_array(marker_id_i)
        first_px = self.display_tuple(first_tuple[1], first_tuple[2])
        second_px = self.display_tuple(second_tuple[1], second_tuple[2])
        higher_y_px = max(first_px[1], second_px[1])
        # LLFR-00168: the two ends are at the times of the points.
        self.assertAlmostEqual(float(vertex_array[0, 0]),
                               min(first_px[0], second_px[0]), delta=0.5)
        self.assertAlmostEqual(float(vertex_array[-1, 0]),
                               max(first_px[0], second_px[0]), delta=0.5)
        # Just above the higher point: a small gap, not far away.
        end_y_px = float(vertex_array[0, 1])
        self.assertAlmostEqual(float(vertex_array[-1, 1]), end_y_px)
        self.assertGreater(end_y_px, higher_y_px)
        self.assertLess(end_y_px - higher_y_px, 20.0)
        # The middle tip is the highest vertex, in the middle: it
        # points up, away from the points.
        tip_index_i = int(np.argmax(vertex_array[:, 1]))
        self.assertAlmostEqual(float(vertex_array[tip_index_i, 0]),
                               (first_px[0] + second_px[0]) / 2.0,
                               delta=0.5)
        self.assertGreaterEqual(float(np.min(vertex_array[:, 1])),
                                end_y_px - 1e-6)
        self.assertGreater(float(vertex_array[tip_index_i, 1]),
                           end_y_px + 4.0)

    def delta_y_side(self, marker_id_i: int) -> str:
        """Return the side the widget chose for a Delta Y marker now.

        Inputs:
            marker_id_i: id of the delta marker.
        Outputs: "right" or "left".
        """
        bracket = self.plot_widget.delta_artist_tuple(marker_id_i)[0]
        return bracket.side_function(None)

    def assert_delta_y_attached(self, marker_id_i: int, first_tuple: tuple,
                                second_tuple: tuple) -> str:
        """Check a Delta Y bracket: ends at the values, beside a point.

        Inputs:
            marker_id_i: id of the delta marker.
            first_tuple: the first point.
            second_tuple: the second point.
        Outputs: the side the bracket is on, "right" or "left".
        """
        vertex_array = self.bracket_vertex_array(marker_id_i)
        first_px = self.display_tuple(*first_tuple[1:])
        second_px = self.display_tuple(*second_tuple[1:])
        # LLFR-00170: the two ends are at the values of the points.
        self.assertEqual(sorted(np.round(vertex_array[[0, -1], 1], 3)),
                         sorted(np.round([first_px[1], second_px[1]], 3)))
        end_x_px = float(vertex_array[0, 0])
        side_str = self.delta_y_side(marker_id_i)
        if side_str == "right":
            # Just right of the later point, tip pointing right.
            later_x_px = max(first_px[0], second_px[0])
            self.assertGreater(end_x_px, later_x_px)
            self.assertLess(end_x_px - later_x_px, 20.0)
            self.assertGreater(float(np.max(vertex_array[:, 0])),
                               end_x_px + 4.0)
            self.assertGreaterEqual(float(np.min(vertex_array[:, 0])),
                                    end_x_px - 1e-6)
        else:
            # Mirrored: just left of the earlier point, tip left.
            earlier_x_px = min(first_px[0], second_px[0])
            self.assertLess(end_x_px, earlier_x_px)
            self.assertLess(earlier_x_px - end_x_px, 20.0)
            self.assertLess(float(np.min(vertex_array[:, 0])),
                            end_x_px - 4.0)
            self.assertLessEqual(float(np.max(vertex_array[:, 0])),
                                 end_x_px + 1e-6)
        return side_str


class DeltaPickTest(DeltaWidgetTestCase):
    """Clicks with the delta tools report curve samples."""

    @covers("LLFR-00163", "LLFR-00164")
    def test_click_on_a_curve_reports_its_nearest_sample(self) -> None:
        """With Delta X or Delta Y, a click on a curve sends its sample.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in DELTA_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.pick_list.clear()
                self.plot_widget.set_plot_tool(tool_str)
                # A little off the exact sample time, on the curve.
                self.left_click(2.02, float(np.sin(2.02)))
                self.left_click(6.0, 3.6)
                self.assertEqual(self.pick_list, [self.sine_point(2.0),
                                                  self.ramp_point(6.0)])
        # No other request is sent by a delta click.
        self.assertEqual(self.place_list, [])
        self.assertEqual(self.pin_list, [])
        self.assertEqual(self.range_list, [])

    @covers("LLFR-00165")
    def test_click_off_every_curve_reports_nothing(self) -> None:
        """A click on an empty area or outside the axes sends nothing.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        self.left_click(5.0, 1.8)
        send_mouse_event(self.plot_widget, "button_press_event", 2.0, 2.0,
                         LEFT_BUTTON_I)
        self.assertEqual(self.pick_list, [])

    @covers("LLFR-00163", "LLFR-00109")
    def test_other_tools_never_report_a_pick(self) -> None:
        """Tip, Zoom, Vertical marker or no tool never pick a point.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (TIP_TOOL_STR, ZOOM_TOOL_STR, MARKER_TOOL_STR,
                         NO_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.left_click(2.0, float(np.sin(2.0)))
        self.assertEqual(self.pick_list, [])

    @covers("LLFR-00163")
    def test_click_on_a_vertical_marker_over_a_curve_picks(self) -> None:
        """With a delta tool, a vertical marker does not hide the curve.

        Inputs: none.
        Outputs: none.
        """
        self.set_markers([(1, "Marker 1", 2.0)])
        self.plot_widget.set_plot_tool(DELTA_Y_TOOL_STR)
        self.left_click(2.0, float(np.sin(2.0)))
        self.assertEqual(self.pick_list, [self.sine_point(2.0)])
        self.assertEqual(self.move_list, [])

    @covers("LLFR-00153", "LLFR-00163")
    def test_press_on_a_pinned_tip_moves_it_and_never_picks(self) -> None:
        """A press on a pinned tip's point starts moving the tip.

        Inputs: none.
        Outputs: none.
        """
        tip_move_list = recorder(self.plot_widget.pinned_tip_move_requested)
        name_str, time_s, value_f = self.sine_point(3.0)
        self.plot_widget.set_pinned_tips([(name_str, time_s, value_f)])
        self.draw()
        for tool_str in DELTA_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.mouse("button_press_event", time_s, value_f)
                self.assertEqual(self.plot_widget.drag_tip_index_i, 0)
                self.mouse("motion_notify_event", time_s + 1.0, value_f)
                self.mouse("button_release_event", time_s + 1.0, value_f)
                self.assertEqual(self.pick_list, [])
                self.assertEqual(len(tip_move_list), 1)
                tip_move_list.clear()
                self.draw()


class DeltaFirstPointTest(DeltaWidgetTestCase):
    """The dot of a picked first point."""

    @covers("LLFR-00163", "LLFR-00172")
    def test_dot_in_marker_color_at_the_point(self) -> None:
        """The dot is drawn at the point in the reserved marker color.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        point_tuple = self.sine_point(4.0)
        self.plot_widget.set_delta_first_point(point_tuple)
        self.draw()
        dot = self.plot_widget.delta_first_point_artist
        self.assertIsNotNone(dot)
        self.assertTrue(dot.get_visible())
        self.assertIn(dot, self.plot_widget.axes.lines)
        self.assertEqual(to_hex_str(dot.get_markerfacecolor()),
                         MARKER_COLOR_STR)
        self.assertEqual(dot.get_marker(), "o")
        self.assertEqual((float(dot.get_xdata()[0]),
                          float(dot.get_ydata()[0])), point_tuple[1:])
        # LLFR-00172: no curve ever uses the marker color.
        for line in self.plot_widget.curve_line_dict.values():
            self.assertNotEqual(to_hex_str(line.get_color()),
                                MARKER_COLOR_STR)

    @covers("LLFR-00164", "LLFR-00167")
    def test_dot_removed_and_kept_over_redraws(self) -> None:
        """The dot survives a redraw, goes with () or a tool change.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        self.plot_widget.set_delta_first_point(self.sine_point(4.0))
        self.plot_widget.set_curves(self.plot_widget.curve_data_list)
        self.draw()
        dot = self.plot_widget.delta_first_point_artist
        self.assertIn(dot, self.plot_widget.axes.lines)
        self.plot_widget.set_delta_first_point(())
        self.assertIsNone(self.plot_widget.delta_first_point_artist)
        self.assertNotIn(dot, self.plot_widget.axes.lines)
        # LLFR-00167: leaving the delta tools removes it too.
        self.plot_widget.set_delta_first_point(self.sine_point(4.0))
        self.plot_widget.set_plot_tool(DELTA_Y_TOOL_STR)
        self.assertIsNotNone(self.plot_widget.delta_first_point_artist)
        self.plot_widget.set_plot_tool(TIP_TOOL_STR)
        self.assertIsNone(self.plot_widget.delta_first_point_artist)
        self.assertEqual(self.plot_widget.delta_first_point_tuple, ())


class DeltaDrawingTest(DeltaWidgetTestCase):
    """Brackets, dots and values of Delta X and Delta Y markers."""

    @covers("LLFR-00168", "LLFR-00169", "LLFR-00172")
    def test_delta_x_bracket_and_value(self) -> None:
        """Dashed bracket above the higher point, tip up, "Δt = 4 s".

        Inputs: none.
        Outputs: none.
        """
        first_tuple = self.sine_point(2.0)
        second_tuple = self.ramp_point(6.0)
        self.set_delta_markers([(7, DELTA_X_KIND_STR, first_tuple,
                                 second_tuple)])
        self.assertEqual(self.plot_widget.delta_marker_id_list(), [7])
        self.assert_delta_x_attached(7, first_tuple, second_tuple)
        bracket, leader, dots, label = self.plot_widget.delta_artist_tuple(7)
        # LLFR-00172: marker color; LLFR-00168: dashed.
        for patch in (bracket, leader):
            self.assertEqual(to_hex_str(patch.get_edgecolor()),
                             MARKER_COLOR_STR)
            self.assertFalse(patch.get_fill())
        self.assertNotIn(bracket.get_linestyle(), ("-", "solid"))
        self.assertIsNotNone(bracket._dash_pattern[1])
        # LLFR-00168: a dot on each point.
        self.assertEqual(list(dots.get_xdata()), [2.0, 6.0])
        self.assertEqual(to_hex_str(dots.get_markerfacecolor()),
                         MARKER_COLOR_STR)
        # LLFR-00169: the value text, next to (above) the middle tip.
        self.assertEqual(self.plot_widget.delta_label_text(7), "Δt = 4 s")
        self.assertEqual(to_hex_str(label.get_color()), MARKER_COLOR_STR)
        self.assertFalse(label.get_parse_math())
        vertex_array = self.bracket_vertex_array(7)
        tip_px = vertex_array[int(np.argmax(vertex_array[:, 1]))]
        box = self.plot_widget.tip_box_extent(label, self.renderer())
        self.assertAlmostEqual((box.x0 + box.x1) / 2.0, float(tip_px[0]),
                               delta=2.0)
        self.assertGreaterEqual(box.y0, float(tip_px[1]) - 1.0)
        self.assertLess(box.y0 - float(tip_px[1]), 10.0)

    @covers("LLFR-00170", "LLFR-00171", "LLFR-00172")
    def test_delta_y_bracket_and_value(self) -> None:
        """Bracket right of the later point, tip right, "Δy = ...".

        Inputs: none.
        Outputs: none.
        """
        # The later point (6 s) is the first one here.
        first_tuple = self.ramp_point(6.0)
        second_tuple = self.sine_point(3.0)
        self.set_delta_markers([(8, DELTA_Y_KIND_STR, first_tuple,
                                 second_tuple)])
        vertex_array = self.bracket_vertex_array(8)
        first_px = self.display_tuple(*first_tuple[1:])
        second_px = self.display_tuple(*second_tuple[1:])
        # LLFR-00170: the two ends are at the values of the points.
        end_value_list = sorted([float(vertex_array[0, 1]),
                                 float(vertex_array[-1, 1])])
        self.assertAlmostEqual(end_value_list[0],
                               min(first_px[1], second_px[1]), delta=0.5)
        self.assertAlmostEqual(end_value_list[1],
                               max(first_px[1], second_px[1]), delta=0.5)
        # Just right of the later point, tip pointing right.
        end_x_px = float(vertex_array[0, 0])
        self.assertGreater(end_x_px, first_px[0])
        self.assertLess(end_x_px - first_px[0], 20.0)
        self.assertGreaterEqual(float(np.min(vertex_array[:, 0])),
                                end_x_px - 1e-6)
        tip_px = vertex_array[int(np.argmax(vertex_array[:, 0]))]
        self.assertGreater(float(tip_px[0]), end_x_px + 4.0)
        self.assertAlmostEqual(float(tip_px[1]),
                               (first_px[1] + second_px[1]) / 2.0,
                               delta=0.5)
        # LLFR-00171: second minus first, without a unit, tip format.
        expected_f = second_tuple[2] - first_tuple[2]
        self.assertLess(expected_f, 0.0)
        self.assertEqual(self.plot_widget.delta_label_text(8),
                         f"Δy = {expected_f:.6g}")
        label = self.plot_widget.delta_artist_tuple(8)[3]
        box = self.plot_widget.tip_box_extent(label, self.renderer())
        self.assertGreaterEqual(box.x0, float(tip_px[0]) - 1.0)
        self.assertLessEqual(box.y0, float(tip_px[1]))
        self.assertGreaterEqual(box.y1, float(tip_px[1]))

    @covers("LLFR-00173", "LLFR-00168", "LLFR-00170")
    def test_markers_follow_zoom_pan_and_resize(self) -> None:
        """After a zoom, a pan and a resize, both stay at their points.

        Inputs: none.
        Outputs: none.
        """
        x_first, x_second = self.sine_point(3.0), self.ramp_point(5.0)
        y_first, y_second = self.sine_point(4.0), self.sine_point(6.0)
        self.set_delta_markers([
            (1, DELTA_X_KIND_STR, x_first, x_second),
            (2, DELTA_Y_KIND_STR, y_first, y_second)])
        text_tuple = (self.plot_widget.delta_label_text(1),
                      self.plot_widget.delta_label_text(2))
        for change_str in ("zoom", "pan", "resize"):
            with self.subTest(change=change_str):
                if change_str == "zoom":
                    self.plot_widget.wheel_at(
                        self.plot_widget.data_to_widget_point(4.5, 0.0),
                        3.0)
                elif change_str == "pan":
                    self.plot_widget.set_time_range(2.5, 7.5)
                else:
                    self.plot_widget.resize(450, 300)
                self.draw()
                self.assert_delta_x_attached(1, x_first, x_second)
                self.assert_delta_y_attached(2, y_first, y_second)
                # LLFR-00173: the values never change.
                self.assertEqual((self.plot_widget.delta_label_text(1),
                                  self.plot_widget.delta_label_text(2)),
                                 text_tuple)

    @covers("LLFR-00170", "LLFR-00171", "LLFR-00173")
    def test_delta_y_near_the_right_edge_is_mirrored_left(self) -> None:
        """No room right of the later point: bracket and value go left.

        Inputs: none.
        Outputs: none.
        """
        first_tuple = self.sine_point(8.0)
        second_tuple = self.ramp_point(9.9)
        self.set_delta_markers([(4, DELTA_Y_KIND_STR, first_tuple,
                                 second_tuple)])
        self.assertEqual(self.assert_delta_y_attached(4, first_tuple,
                                                      second_tuple), "left")
        bracket, leader, _, label = self.plot_widget.delta_artist_tuple(4)
        axes_box = self.plot_widget.axes.bbox
        vertex_array = self.bracket_vertex_array(4)
        # The whole bracket and its leader lines are inside the plot.
        for point_array in (vertex_array,
                            np.asarray(leader.display_path().vertices)):
            self.assertGreaterEqual(float(np.min(point_array[:, 0])),
                                    axes_box.x0)
            self.assertLessEqual(float(np.max(point_array[:, 0])),
                                 axes_box.x1)
        # LLFR-00171: the value is next to the tip, on its left, inside
        # the plot and not over the bracket.
        tip_px = vertex_array[int(np.argmin(vertex_array[:, 0]))]
        box = self.plot_widget.tip_box_extent(label, self.renderer())
        self.assertGreaterEqual(box.x0, axes_box.x0 - 0.5)
        self.assertLessEqual(box.x1, float(tip_px[0]) + 0.5)
        self.assertLess(float(tip_px[0]) - box.x1, 10.0)
        self.assertLessEqual(box.y0, float(tip_px[1]))
        self.assertGreaterEqual(box.y1, float(tip_px[1]))
        # LLFR-00173: a zoom out that gives room on the right puts both
        # back on the right of the later point.
        self.plot_widget.set_time_range(0.0, 14.0)
        self.draw()
        self.assertEqual(self.assert_delta_y_attached(4, first_tuple,
                                                      second_tuple), "right")
        vertex_array = self.bracket_vertex_array(4)
        tip_px = vertex_array[int(np.argmax(vertex_array[:, 0]))]
        box = self.plot_widget.tip_box_extent(label, self.renderer())
        self.assertGreaterEqual(box.x0, float(tip_px[0]) - 0.5)
        self.assertLessEqual(box.x1, axes_box.x1 + 0.5)
        # Its value never changes.
        self.assertEqual(self.plot_widget.delta_label_text(4),
                         f"Δy = {second_tuple[2] - first_tuple[2]:.6g}")

    @covers("LLFR-00169", "LLFR-00171", "LLFR-00172")
    def test_values_sit_in_a_bordered_tip_box(self) -> None:
        """Both values use an opaque box bordered in the marker color.

        Inputs: none.
        Outputs: none.
        """
        self.set_delta_markers([
            (1, DELTA_X_KIND_STR, self.sine_point(2.0),
             self.ramp_point(6.0)),
            (2, DELTA_Y_KIND_STR, self.sine_point(3.0),
             self.ramp_point(5.0))])
        for marker_id_i in (1, 2):
            with self.subTest(marker=marker_id_i):
                box_patch = self.plot_widget.delta_artist_tuple(
                    marker_id_i)[3].get_bbox_patch()
                self.assertIsNotNone(box_patch)
                self.assertEqual(to_hex_str(box_patch.get_edgecolor()),
                                 MARKER_COLOR_STR)
                self.assertGreater(box_patch.get_linewidth(), 0.0)
                self.assertGreaterEqual(box_patch.get_alpha(), 0.95)

    @covers("LLFR-00168", "LLFR-00076")
    def test_bracket_and_value_fit_above_the_highest_point(self) -> None:
        """At the top of the curves, the y range leaves room above.

        Inputs: none.
        Outputs: none.
        """
        low_before_f, high_before_f = self.plot_widget.axes.get_ylim()
        # The ramp's last sample (4.0 at 10 s) is the highest value.
        first_tuple = self.ramp_point(9.0)
        second_tuple = self.ramp_point(10.0)
        self.set_delta_markers([(3, DELTA_X_KIND_STR, first_tuple,
                                 second_tuple)])
        low_f, high_f = self.plot_widget.axes.get_ylim()
        self.assertEqual(low_f, low_before_f)
        self.assertGreater(high_f, high_before_f)
        axes_box = self.plot_widget.axes.bbox
        vertex_array = self.bracket_vertex_array(3)
        self.assertLessEqual(float(np.max(vertex_array[:, 1])), axes_box.y1)
        label = self.plot_widget.delta_artist_tuple(3)[3]
        box = self.plot_widget.tip_box_extent(label, self.renderer())
        self.assertLessEqual(box.y1, axes_box.y1 + 0.5)
        self.assertGreaterEqual(box.y0,
                                float(np.max(vertex_array[:, 1])) - 1.0)
        # LLFR-00076: every curve is still fully visible.
        self.assertGreaterEqual(high_f, float(np.max(self.ramp_array)))
        # Removing the marker gives the curves' own range back.
        self.set_delta_markers([])
        self.assertEqual(self.plot_widget.axes.get_ylim(),
                         (low_before_f, high_before_f))

    @covers("LLFR-00174")
    def test_many_markers_and_points_out_of_view(self) -> None:
        """Twenty markers are drawn; parts out of view are clipped.

        Inputs: none.
        Outputs: none.
        """
        marker_list = []
        for index_i in range(10):
            marker_list.append((index_i * 2 + 1, DELTA_X_KIND_STR,
                                self.sine_point(float(index_i)),
                                self.ramp_point(float(index_i) + 0.5)))
            marker_list.append((index_i * 2 + 2, DELTA_Y_KIND_STR,
                                self.ramp_point(float(index_i)),
                                self.sine_point(float(index_i) + 0.3)))
        self.set_delta_markers(marker_list)
        self.assertEqual(self.plot_widget.delta_marker_id_list(),
                         list(range(1, 21)))
        self.plot_widget.set_time_range(4.2, 6.0)
        self.draw()
        for marker_id_i in range(1, 21):
            for patch in self.plot_widget.delta_artist_tuple(
                    marker_id_i)[:2]:
                # The rectangular axes patch is applied as a clip box.
                self.assertTrue(patch.get_clip_on())
                self.assertTrue(patch.get_clip_box() is not None
                                or patch.get_clip_path() is not None)
        # Drawing with points out of view raises nothing.
        self.plot_widget.canvas.draw()


class DeltaMenuTest(DeltaWidgetTestCase):
    """The delta marker menu and its priority."""

    def setUp(self) -> None:
        """Draw one Delta X marker from Sine at 2 s to Ramp at 6 s.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.first_tuple = self.sine_point(2.0)
        self.second_tuple = self.ramp_point(6.0)
        self.set_delta_markers([(5, DELTA_X_KIND_STR, self.first_tuple,
                                 self.second_tuple)])

    def tip_data_tuple(self) -> tuple:
        """Return the data point of the bracket's middle tip.

        Inputs: none.
        Outputs: (time_s, value_f).
        """
        vertex_array = self.bracket_vertex_array(5)
        tip_px = vertex_array[int(np.argmax(vertex_array[:, 1]))]
        time_s, value_f = self.plot_widget.axes.transData.inverted(
            ).transform((float(tip_px[0]), float(tip_px[1]) - 1.0))
        return float(time_s), float(value_f)

    @covers("LLFR-00175", "LLFR-00048")
    def test_menu_on_bracket_dot_and_label(self) -> None:
        """Bracket, dot and value all show "Delete", never Delete plot.

        Inputs: none.
        Outputs: none.
        """
        label = self.plot_widget.delta_artist_tuple(5)[3]
        box = self.plot_widget.tip_box_extent(label, self.renderer())
        label_data_tuple = tuple(
            self.plot_widget.axes.transData.inverted().transform(
                ((box.x0 + box.x1) / 2.0, (box.y0 + box.y1) / 2.0)))
        for tool_str in PLOT_TOOL_TUPLE + (NO_TOOL_STR,):
            self.plot_widget.set_plot_tool(tool_str)
            for name_str, data_tuple in (
                    ("bracket", self.tip_data_tuple()),
                    ("label", label_data_tuple),
                    ("dot", self.second_tuple[1:])):
                with self.subTest(tool=tool_str, place=name_str):
                    self.assertEqual(self.menu_texts_at(*data_tuple),
                                     ["Delete"])
        # LLFR-00048: an empty area still offers "Delete plot".
        self.assertEqual(self.menu_texts_at(9.0, -0.5), ["Delete plot"])

    @covers("LLFR-00176")
    def test_delete_requests_the_marker_id_last(self) -> None:
        """"Delete" emits delta_marker_delete_requested with the id.

        Inputs: none.
        Outputs: none.
        """
        shown_list = self.choose_action_text("Delete")
        self.right_click(*self.tip_data_tuple())
        self.assertEqual(shown_list, [["Delete"]])
        self.assertEqual(self.delta_delete_list, [(5,)])
        # A closed menu emits nothing.
        self.choose_action_text("")
        self.right_click(*self.tip_data_tuple())
        self.assertEqual(self.delta_delete_list, [(5,)])

    @covers("LLFR-00177", "LLFR-00038", "LLFR-00040")
    def test_delta_menu_wins_over_the_curve_under_it(self) -> None:
        """On a dot lying on a curve, the delta menu is shown.

        Inputs: none.
        Outputs: none.
        """
        # The first point is a sample of Sine, so the curve is there too.
        self.assertEqual(self.plot_widget.curve_at(
            self.plot_widget.data_to_widget_point(*self.first_tuple[1:])),
            "Sine")
        text_list = self.menu_texts_at(*self.first_tuple[1:])
        self.assertEqual(text_list, ["Delete"])
        self.assertNotIn("Delete signal", text_list)
        self.assertNotIn("Width", text_list)
        # Away from the marker the curve menu is back.
        self.assertEqual(self.menu_texts_at(8.0, float(np.sin(8.0))),
                         ["Delete signal", "Width"])

    @covers("LLFR-00110", "LLFR-00177")
    def test_vertical_marker_and_pinned_tip_come_first(self) -> None:
        """A vertical marker or a pinned tip on the bracket wins.

        Inputs: none.
        Outputs: none.
        """
        time_s, value_f = self.tip_data_tuple()
        self.set_markers([(9, "Marker 1", time_s)])
        self.assertEqual(self.menu_texts_at(time_s, value_f),
                         ["Rename", "Delete"])
        self.set_markers([])
        self.plot_widget.set_pinned_tips([self.second_tuple])
        self.draw()
        self.assertEqual(self.menu_texts_at(*self.second_tuple[1:]),
                         ["Delete"])
        shown_list = self.choose_action_text("Delete")
        tip_delete_list = recorder(
            self.plot_widget.pinned_tip_delete_requested)
        self.right_click(*self.second_tuple[1:])
        self.assertEqual(shown_list, [["Delete"]])
        self.assertEqual(tip_delete_list, [(0,)])
        self.assertEqual(self.delta_delete_list, [])


@requires_qt
class DeltaWindowTestCase(unittest.TestCase):
    """A real window and controller with a CSV opened."""

    def setUp(self) -> None:
        """Create the window and controllers and open a CSV.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        self.folder_str = self.temporary_folder.name
        path_str = os.path.join(self.folder_str, "delta.csv")
        with open(path_str, "w", encoding="utf-8") as file:
            file.write(FILE_TEXT_STR)
        box_patch = mock.patch.object(QMessageBox, "exec", return_value=0)
        self.box_mock = box_patch.start()
        self.addCleanup(box_patch.stop)
        self.main_window = MainWindow()
        self.main_window.resize(1100, 800)
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.main_window.show()
        with mock.patch.object(QFileDialog, "getOpenFileName",
                               return_value=(path_str, "")):
            self.controller.file_controller.open_file_requested()
        self.process_events()
        self.top_panel = self.main_window.top_panel
        self.plot_controller = self.controller.plot_controller

    def tearDown(self) -> None:
        """Close the window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.process_events()

    def process_events(self) -> None:
        """Let Qt run deferred work and draw the plots.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(3):
            self.application.processEvents()
        for plot_widget in (
                self.main_window.plot_panel.plot_widget_dict.values()):
            plot_widget.canvas.draw()

    def click(self, button) -> None:
        """Click a top panel button with the mouse.

        Inputs:
            button: the button.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        self.process_events()

    def plot_speed_and_force(self):
        """Plot speed, drop force on the same plot and return its widget.

        Inputs: none.
        Outputs: the PlotWidget.
        """
        self.main_window.signal_double_click_handler("speed")
        self.process_events()
        plot_id_i = self.main_window.plot_panel.plot_id_list(
            self.main_window.current_tab_id())[0]
        self.plot_controller.on_signal_dropped(plot_id_i, "force")
        self.process_events()
        return self.main_window.plot_view(plot_id_i)


class DeltaButtonTest(DeltaWindowTestCase):
    """The Delta X and Delta Y buttons of the top panel."""

    @covers("LLFR-00161", "LLFR-00162", "LLFR-00158", "LLFR-00181")
    def test_buttons_exist_with_icons_and_names(self) -> None:
        """Icon-only tool buttons named "Delta X" and "Delta Y".

        Inputs: none.
        Outputs: none.
        """
        from view import icon_shapes
        from view.toggle_button import ToggleButton
        for tool_str, button, name_str, icon_str in (
                (DELTA_X_TOOL_STR, self.top_panel.delta_x_button, "Delta X",
                 icon_shapes.DELTA_X_ICON_STR),
                (DELTA_Y_TOOL_STR, self.top_panel.delta_y_button, "Delta Y",
                 icon_shapes.DELTA_Y_ICON_STR)):
            with self.subTest(button=name_str):
                self.assertIsInstance(button, ToggleButton)
                self.assertIs(self.top_panel.plot_tool_button_dict[tool_str],
                              button)
                self.assertEqual(button_name(button), name_str)
                self.assertEqual(button_tip_line_list(button)[0], name_str)
                self.assertEqual(button.text(), "")
                self.assertEqual(button.icon_name_str, icon_str)
                self.assertFalse(button.icon().isNull())
                self.assertTrue(button.isVisible())
                self.assertFalse(button.is_active())
        # In the plot tool group, right after Vertical marker.
        button_list = [self.top_panel.marker_button,
                       self.top_panel.delta_x_button,
                       self.top_panel.delta_y_button,
                       self.top_panel.reset_zoom_button]
        for left_button, right_button in zip(button_list, button_list[1:]):
            self.assertLessEqual(left_button.x() + left_button.width(),
                                 right_button.x())

    @covers("LLFR-00079", "LLFR-00161", "LLFR-00162", "LLFR-00109",
            "LLFR-00002")
    def test_delta_tools_are_exclusive_and_stay_active(self) -> None:
        """Only one tool at a time; the tool stays until clicked again.

        Inputs: none.
        Outputs: none.
        """
        self.click(self.top_panel.delta_x_button)
        self.assertEqual(self.top_panel.active_plot_tool(), DELTA_X_TOOL_STR)
        self.assertEqual(self.plot_controller.plot_tool_str,
                         DELTA_X_TOOL_STR)
        self.click(self.top_panel.delta_y_button)
        self.assertEqual(self.top_panel.active_plot_tool(), DELTA_Y_TOOL_STR)
        self.assertFalse(self.top_panel.delta_x_button.is_active())
        self.click(self.top_panel.tip_button)
        self.assertEqual(self.top_panel.active_plot_tool(), TIP_TOOL_STR)
        self.assertFalse(self.top_panel.delta_y_button.is_active())
        self.click(self.top_panel.delta_y_button)
        self.click(self.top_panel.delta_y_button)
        self.assertEqual(self.top_panel.active_plot_tool(), NO_TOOL_STR)
        self.assertEqual(self.plot_controller.plot_tool_str, NO_TOOL_STR)


class DeltaEndToEndTest(DeltaWindowTestCase):
    """Measure with the real window, undo, and export to PDF."""

    def left_click(self, plot_widget, time_s: float,
                   value_f: float) -> None:
        """Press and release the left button at a data point.

        Inputs:
            plot_widget: the PlotWidget.
            time_s: x value in seconds.
            value_f: y value.
        Outputs: none.
        """
        display_x_px, display_y_px = (
            plot_widget.axes.transData.transform((time_s, value_f)))
        for event_name_str in ("button_press_event", "button_release_event"):
            send_mouse_event(plot_widget, event_name_str,
                             float(display_x_px), float(display_y_px),
                             LEFT_BUTTON_I)
        self.process_events()

    def right_click_choose(self, plot_widget, time_s: float, value_f: float,
                           text_str: str) -> list:
        """Right-click at a data point and choose a menu action.

        Inputs:
            plot_widget: the PlotWidget.
            time_s: x value in seconds.
            value_f: y value.
            text_str: text of the action to choose.
        Outputs: the texts of the menu that was shown.
        """
        shown_list = []

        def fake_execute_menu(menu, global_point):
            """Record the menu and return the chosen action.

            Inputs:
                menu: the QMenu that would be shown.
                global_point: QPoint in screen coordinates.
            Outputs: the matching QAction, or None.
            """
            shown_list.extend(action.text() for action in menu.actions())
            for action in all_menu_actions(menu):
                if action.text() == text_str:
                    return action
            return None

        plot_widget.execute_menu = fake_execute_menu
        display_x_px, display_y_px = (
            plot_widget.axes.transData.transform((time_s, value_f)))
        send_mouse_event(plot_widget, "button_press_event",
                         float(display_x_px), float(display_y_px),
                         RIGHT_BUTTON_I)
        self.process_events()
        return shown_list

    def current_plot_widget(self):
        """Return the only plot widget of the window.

        Inputs: none.
        Outputs: the PlotWidget.
        """
        plot_widget_list = list(
            self.main_window.plot_panel.plot_widget_dict.values())
        self.assertEqual(len(plot_widget_list), 1)
        return plot_widget_list[0]

    @covers("LLFR-00161", "LLFR-00163", "LLFR-00164", "LLFR-00168",
            "LLFR-00169", "LLFR-00138", "LLFR-00140", "LLFR-00109")
    def test_measure_delta_x_between_two_curves_and_undo(self) -> None:
        """speed at 0.5 s then force at 1.5 s gives "Δt = 1 s"; undo.

        Inputs: none.
        Outputs: none.
        """
        plot_widget = self.plot_speed_and_force()
        self.click(self.top_panel.delta_x_button)
        self.left_click(plot_widget, 0.5, 1.0)
        # LLFR-00163: the first point's dot.
        plot_widget = self.current_plot_widget()
        self.assertEqual(plot_widget.delta_first_point_tuple,
                         ("speed", 0.5, 1.0))
        self.left_click(plot_widget, 1.5, 0.0)
        plot_widget = self.current_plot_widget()
        self.assertEqual(plot_widget.delta_first_point_tuple, ())
        self.assertIsNone(plot_widget.delta_first_point_artist)
        id_list = plot_widget.delta_marker_id_list()
        self.assertEqual(len(id_list), 1)
        self.assertEqual(plot_widget.delta_label_text(id_list[0]),
                         "Δt = 1 s")
        self.assertTrue(self.top_panel.delta_x_button.is_active())
        # LLFR-00138: one undo removes the marker.
        self.main_window.run_undo()
        self.process_events()
        self.assertEqual(self.current_plot_widget().delta_marker_id_list(),
                         [])
        self.assertEqual(self.box_mock.call_count, 0)

    @covers("LLFR-00162", "LLFR-00170", "LLFR-00171", "LLFR-00178",
            "LLFR-00176", "LLFR-00140")
    def test_delta_y_curve_removal_and_delete(self) -> None:
        """Delta Y on force; removing force removes it; undo; Delete.

        Inputs: none.
        Outputs: none.
        """
        plot_widget = self.plot_speed_and_force()
        self.click(self.top_panel.delta_y_button)
        self.left_click(plot_widget, 1.0, -1.0)
        self.left_click(self.current_plot_widget(), 2.0, 1.0)
        plot_widget = self.current_plot_widget()
        marker_id_i = plot_widget.delta_marker_id_list()[0]
        self.assertEqual(plot_widget.delta_label_text(marker_id_i),
                         "Δy = 2")
        # LLFR-00178: removing force removes the marker.
        shown_list = self.right_click_choose(plot_widget, 0.5, 0.0,
                                             "Delete signal")
        self.assertIn("Delete signal", shown_list)
        plot_widget = self.current_plot_widget()
        self.assertEqual(plot_widget.delta_marker_id_list(), [])
        self.main_window.run_undo()
        self.process_events()
        plot_widget = self.current_plot_widget()
        self.assertEqual(plot_widget.delta_marker_id_list(), [marker_id_i])
        # LLFR-00176, LLFR-00177: "Delete" on its first dot, which lies
        # on the force curve, removes it.
        shown_list = self.right_click_choose(plot_widget, 1.0, -1.0,
                                             "Delete")
        self.assertEqual(shown_list, ["Delete"])
        self.assertEqual(self.current_plot_widget().delta_marker_id_list(),
                         [])

    @covers("LLFR-00167", "LLFR-00148", "LLFR-00149")
    def test_tip_key_discards_the_first_point(self) -> None:
        """Holding the Tip key deactivates Delta X and its first point.

        Inputs: none.
        Outputs: none.
        """
        plot_widget = self.plot_speed_and_force()
        self.click(self.top_panel.delta_x_button)
        self.left_click(plot_widget, 0.5, 1.0)
        self.assertTrue(self.plot_controller.pending_delta_tuple)
        self.main_window.on_tool_key_activate(TIP_TOOL_STR)
        self.process_events()
        self.assertEqual(self.top_panel.active_plot_tool(), TIP_TOOL_STR)
        self.assertEqual(self.plot_controller.pending_delta_tuple, ())
        self.assertEqual(self.current_plot_widget().delta_first_point_tuple,
                         ())
        self.main_window.on_tool_key_release()
        self.process_events()
        self.assertEqual(self.top_panel.active_plot_tool(), NO_TOOL_STR)

    @covers("LLFR-00129", "LLFR-00172")
    def test_pdf_export_includes_delta_markers(self) -> None:
        """The PDF's plot image holds the marker color only with markers.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor
        from view import plot_export
        plot_widget = self.plot_speed_and_force()
        plot_id_i = plot_widget.plot_id_i
        self.plot_controller.on_plot_tool_changed(DELTA_X_TOOL_STR)
        self.plot_controller.on_delta_point_pick(plot_id_i, "speed", 0.5,
                                                 1.0)
        self.plot_controller.on_delta_point_pick(plot_id_i, "force", 1.5,
                                                 0.0)
        self.plot_controller.on_plot_tool_changed(DELTA_Y_TOOL_STR)
        self.plot_controller.on_delta_point_pick(plot_id_i, "force", 1.0,
                                                 -1.0)
        self.plot_controller.on_delta_point_pick(plot_id_i, "speed", 1.0,
                                                 2.0)
        self.process_events()

        def magenta_count(path_str: str) -> int:
            """Export to a PDF and count marker-colored pixels drawn.

            Inputs:
                path_str: the PDF file to write.
            Outputs: the number of pixels close to the marker color in
                the plot image drawn on the page.
            """
            drawn_list = []
            original_draw = plot_export.draw_page_image

            def recording_draw(*argument_tuple):
                """Draw the page and record the plot images it drew.

                Inputs:
                    argument_tuple: the arguments of draw_page_image.
                Outputs: the list returned by draw_page_image.
                """
                result_list = original_draw(*argument_tuple)
                drawn_list.extend(result_list)
                return result_list

            with mock.patch.object(plot_export, "draw_page_image",
                                   side_effect=recording_draw):
                result_tuple = self.main_window.save_tabs_pdf(path_str)
            self.assertTrue(os.path.exists(path_str), result_tuple)
            image = drawn_list[0][1]
            marker_color = QColor(MARKER_COLOR_STR)
            count_i = 0
            for x_i in range(0, image.width(), 2):
                for y_i in range(0, image.height(), 2):
                    pixel_color = QColor(image.pixel(x_i, y_i))
                    if (abs(pixel_color.red() - marker_color.red()) < 40
                            and abs(pixel_color.green()
                                    - marker_color.green()) < 40
                            and abs(pixel_color.blue()
                                    - marker_color.blue()) < 40):
                        count_i += 1
            return count_i

        with_count_i = magenta_count(os.path.join(self.folder_str,
                                                  "with.pdf"))
        plot = self.plot_controller.workspace.find_plot(plot_id_i)
        for delta_marker in list(plot.delta_marker_list):
            self.plot_controller.on_delta_marker_delete(
                plot_id_i, delta_marker.delta_marker_id_i)
        self.process_events()
        without_count_i = magenta_count(os.path.join(self.folder_str,
                                                     "without.pdf"))
        self.assertGreater(with_count_i, 200)
        self.assertLess(without_count_i, with_count_i / 20)


if __name__ == "__main__":
    unittest.main()
