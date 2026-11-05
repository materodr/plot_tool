"""Tests of the drags drawn over the image of the curves (#257 item 3).

A plot with 1,000,000 samples is dragged on: the flag, the area, the
pinned data tip, the text note and the point of a delta marker are drawn
over a copy of the image of the curves (LLFR-01215), each move after the
first one shown within 50 milliseconds (LLFR-01216), and the other plots
of a flag or area drag are redrawn at least once in every 150
milliseconds and at most once in every 30 milliseconds while the pointer
moves (LLFR-01217).
"""

import time
import unittest
from unittest import mock

import numpy as np

from tests.support import covers, requires_qt
from tests.view.test_markers_view import (
    LEFT_BUTTON_I, MarkerWidgetTestCase, send_mouse_event)

from controller.plot_tools import AREA_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR
from model.workspace import DELTA_X_KIND_STR

# LLFR-01216: the largest delay of a move, and the samples of the plot.
MAXIMUM_MOVE_DELAY_S = 0.05
# LLFR-01217: the longest time between two redraws of the other plots
# while the pointer moves, and how long the test moves it.
MAXIMUM_RELAY_GAP_S = 0.15
RELAY_TEST_DURATION_S = 0.4
BIG_SAMPLE_COUNT_I = 1000000
MOVE_COUNT_I = 30


@requires_qt
class FastDragTest(MarkerWidgetTestCase):
    """Drags on a plot of 1,000,000 samples."""

    def setUp(self) -> None:
        """Give the widget a curve of 1,000,000 samples and count draws.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        time_array = np.linspace(0.0, 10.0, BIG_SAMPLE_COUNT_I)
        self.plot_widget.set_curves([
            ("Big", time_array, np.sin(time_array * 40.0), "#1f4e9c", 1)])
        self.draw()
        self.full_draw_list = []
        self.first_move_draw_count_i = 0
        self.plot_widget.canvas.mpl_connect(
            "draw_event", lambda event: self.full_draw_list.append(event))

    def drag_and_time(self, start_tuple: tuple, value_f: float) -> list:
        """Press at a point, move MOVE_COUNT_I times and time each move.

        Inputs:
            start_tuple: (time_s, value_f) of the press.
            value_f: the y value of the moves.
        Outputs: the seconds each move took.
        """
        self.mouse("button_press_event", *start_tuple)
        duration_list = []
        for index_i in range(MOVE_COUNT_I):
            time_s = start_tuple[0] + 0.05 * (index_i + 1)
            start_s = time.perf_counter()
            self.mouse("motion_notify_event", time_s, value_f)
            duration_list.append(time.perf_counter() - start_s)
            if index_i == 0:
                self.first_move_draw_count_i = len(self.full_draw_list)
        return duration_list

    def check_fast(self, duration_list: list) -> None:
        """Check the drag drew the curves once and each move quickly.

        Inputs:
            duration_list: the seconds of each move.
        Outputs: none.
        """
        # LLFR-01215: the curves are drawn at the start of the drag
        # only, never at the later moves.
        self.assertEqual(len(self.full_draw_list),
                         self.first_move_draw_count_i)
        self.assertGreaterEqual(self.plot_widget.fast_drag_redraw_count_i,
                                MOVE_COUNT_I - 1)
        # LLFR-01216: each move after the first one shown within 50 ms;
        # the first one makes the image of the curves.
        self.assertLess(max(duration_list[1:]), MAXIMUM_MOVE_DELAY_S)

    @covers("LLFR-01215", "LLFR-01216", "HLFR-00029", "HLFR-00085")
    def test_flag_drag_draws_the_curves_once(self) -> None:
        """A flag dragged 30 times draws the curves once; the release
        draws everything again with the flag as part of the image.

        Inputs: none.
        Outputs: none.
        """
        self.set_markers([(9, "Flag 1", 2.0)])
        self.full_draw_list.clear()
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        duration_list = self.drag_and_time((2.0, 0.0), 0.0)
        self.check_fast(duration_list)
        line = self.plot_widget.marker_artist_tuple(9)[0]
        self.assertTrue(line.get_animated())
        self.mouse("button_release_event", 3.5, 0.0)
        self.assertFalse(line.get_animated())
        self.assertEqual(self.plot_widget.fast_drag_artist_list, [])
        self.assertEqual(len(self.move_list), 1)

    @covers("LLFR-01215", "LLFR-01216", "HLFR-00067", "HLFR-00085")
    def test_area_drag_draws_the_curves_once(self) -> None:
        """An area moved 30 times draws the curves once.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_areas([(4, "Area 1", 1.0, 3.0, "#3a8a3a")])
        self.draw()
        self.full_draw_list.clear()
        self.plot_widget.set_plot_tool(AREA_TOOL_STR)
        duration_list = self.drag_and_time((2.0, 0.0), 0.0)
        self.check_fast(duration_list)
        self.mouse("button_release_event", 3.5, 0.0)
        self.assertEqual(self.plot_widget.fast_drag_artist_list, [])

    @covers("LLFR-01215", "LLFR-01216", "HLFR-00041", "HLFR-00085")
    def test_tip_drag_draws_the_curves_once(self) -> None:
        """A pinned data tip dragged with no tool draws the curves once.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_pinned_tips([("Big", 5.0, float(np.sin(200.0)))])
        self.draw()
        self.full_draw_list.clear()
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        annotation = self.plot_widget.pinned_tip_annotation(0)
        box = self.plot_widget.tip_box_extent(annotation)
        center_tuple = ((box.x0 + box.x1) / 2.0, (box.y0 + box.y1) / 2.0)
        send_mouse_event(self.plot_widget, "button_press_event",
                         *center_tuple, LEFT_BUTTON_I)
        duration_list = []
        for index_i in range(MOVE_COUNT_I):
            start_s = time.perf_counter()
            send_mouse_event(self.plot_widget, "motion_notify_event",
                             center_tuple[0] + 2.0 * (index_i + 1),
                             center_tuple[1], LEFT_BUTTON_I)
            duration_list.append(time.perf_counter() - start_s)
            if index_i == 0:
                self.first_move_draw_count_i = len(self.full_draw_list)
        self.check_fast(duration_list)
        send_mouse_event(self.plot_widget, "button_release_event",
                         center_tuple[0] + 2.0 * MOVE_COUNT_I,
                         center_tuple[1], LEFT_BUTTON_I)
        self.assertEqual(self.plot_widget.fast_drag_artist_list, [])

    @covers("LLFR-01215", "LLFR-01216", "HLFR-00074", "HLFR-00085")
    def test_text_note_drag_draws_the_curves_once(self) -> None:
        """A text note dragged 30 times with no tool draws the curves
        once; the release draws everything again.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_text_notes([("Note", 5.0, 0.5)])
        self.draw()
        self.full_draw_list.clear()
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        box = self.plot_widget.text_note_box_extent(0)
        center_tuple = ((box.x0 + box.x1) / 2.0, (box.y0 + box.y1) / 2.0)
        self.assertEqual(self.plot_widget.text_note_at(
            self.plot_widget.display_to_widget_point(*center_tuple)), 0)
        note_move_list = []
        self.plot_widget.text_note_move_requested.connect(
            lambda *argument_tuple: note_move_list.append(argument_tuple))
        duration_list = self.drag_display_and_time(center_tuple)
        self.assertEqual(self.plot_widget.drag_note_index_i, 0)
        self.check_fast(duration_list)
        send_mouse_event(self.plot_widget, "button_release_event",
                         center_tuple[0] + 2.0 * MOVE_COUNT_I,
                         center_tuple[1], LEFT_BUTTON_I)
        self.assertEqual(self.plot_widget.fast_drag_artist_list, [])
        self.assertEqual(len(note_move_list), 1)

    @covers("LLFR-01215", "LLFR-01216", "HLFR-00099", "HLFR-00085")
    def test_delta_point_drag_draws_the_curves_once(self) -> None:
        """A point of a Delta X marker dragged 30 times with no tool
        draws the curves once, although the marker is drawn again at
        each sample.

        Inputs: none.
        Outputs: none.
        """
        time_array, value_array = self.plot_widget.curve_data_list[0][1:3]
        first_tuple = ("Big", float(time_array[200000]),
                       float(value_array[200000]))
        second_tuple = ("Big", float(time_array[700000]),
                        float(value_array[700000]))
        self.plot_widget.set_delta_markers([
            (3, DELTA_X_KIND_STR, first_tuple, second_tuple,
             second_tuple[1] - first_tuple[1])])
        self.draw()
        self.full_draw_list.clear()
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        dot_tuple = self.display_tuple(*first_tuple[1:])
        self.assertTrue(self.plot_widget.delta_dot_at(
            self.plot_widget.display_to_widget_point(*dot_tuple)))
        point_move_list = []
        self.plot_widget.delta_point_move_requested.connect(
            lambda *argument_tuple: point_move_list.append(argument_tuple))
        # LLFR-00433: the first move of 6 pixels starts the drag.
        duration_list = self.drag_display_and_time(dot_tuple, 6.0)
        self.assertEqual(self.plot_widget.delta_drag_id_i, 3)
        self.check_fast(duration_list)
        send_mouse_event(self.plot_widget, "button_release_event",
                         dot_tuple[0] + 6.0 + 2.0 * MOVE_COUNT_I,
                         dot_tuple[1], LEFT_BUTTON_I)
        self.assertEqual(self.plot_widget.fast_drag_artist_list, [])
        self.assertEqual(len(point_move_list), 1)

    @covers("LLFR-01215", "LLFR-01239", "HLFR-00028", "HLFR-00066")
    def test_markers_and_areas_from_the_model_end_the_session(self) -> None:
        """A plot that followed a drag of another plot draws the flags
        and areas given by the model once: their arrival ends the
        drawing over the kept image.

        Inputs: none.
        Outputs: none.
        """
        self.set_markers([(9, "Flag 1", 2.0)])
        self.plot_widget.set_areas([(4, "Area 1", 4.0, 6.0, "#3a8a3a")])
        self.draw()
        self.plot_widget.follow_marker_drag(9, 2.5)
        self.assertTrue(self.plot_widget.fast_drag_artist_list)
        self.plot_widget.set_markers([(9, "Flag 1", 3.0)])
        self.assertEqual(self.plot_widget.fast_drag_artist_list, [])
        self.assertIsNone(self.plot_widget.fast_drag_background)
        for artist in self.plot_widget.marker_artist_tuple(9):
            self.assertFalse(artist.get_animated())
        self.plot_widget.follow_area_drag(4, 4.5, 6.5)
        self.assertTrue(self.plot_widget.fast_drag_artist_list)
        self.plot_widget.set_areas([(4, "Area 1", 5.0, 7.0, "#3a8a3a")])
        self.assertEqual(self.plot_widget.fast_drag_artist_list, [])
        for artist in self.plot_widget.area_artist_tuple(4):
            self.assertFalse(artist.get_animated())

    def drag_display_and_time(self, start_tuple: tuple,
                              first_step_px_f: float = 2.0) -> list:
        """Press at a display point, move right 30 times and time each.

        Inputs:
            start_tuple: (x, y) of the press, in display pixels.
            first_step_px_f: pixels of the first move to the right; each
                later move adds 2 pixels.
        Outputs: the seconds each move took.
        """
        send_mouse_event(self.plot_widget, "button_press_event",
                         *start_tuple, LEFT_BUTTON_I)
        duration_list = []
        for index_i in range(MOVE_COUNT_I):
            start_s = time.perf_counter()
            send_mouse_event(self.plot_widget, "motion_notify_event",
                             start_tuple[0] + first_step_px_f
                             + 2.0 * index_i,
                             start_tuple[1], LEFT_BUTTON_I)
            duration_list.append(time.perf_counter() - start_s)
            if index_i == 0:
                self.first_move_draw_count_i = len(self.full_draw_list)
        return duration_list

    @covers("LLFR-01215", "HLFR-00029", "HLFR-00041", "HLFR-00074")
    def test_release_away_from_the_last_move_ends_the_session(self) -> None:
        """A release 10 pixels away from the last move draws the object
        there and ends the drawing over the kept image, for a flag, a
        pinned tip and a text note.

        Inputs: none.
        Outputs: none.
        """
        self.set_markers([(9, "Flag 1", 2.0)])
        self.plot_widget.set_pinned_tips([("Big", 5.0, float(np.sin(200.0)))])
        self.plot_widget.set_text_notes([("Note", 8.0, 0.5)])
        self.draw()
        flag_tuple = self.display_tuple(2.0, 0.0)
        tip_box = self.plot_widget.tip_box_extent(
            self.plot_widget.pinned_tip_annotation(0))
        note_box = self.plot_widget.text_note_box_extent(0)
        for name_str, tool_str, start_tuple in (
                ("flag", MARKER_TOOL_STR, flag_tuple),
                ("tip", NO_TOOL_STR, ((tip_box.x0 + tip_box.x1) / 2.0,
                                      (tip_box.y0 + tip_box.y1) / 2.0)),
                ("note", NO_TOOL_STR, ((note_box.x0 + note_box.x1) / 2.0,
                                       (note_box.y0 + note_box.y1) / 2.0))):
            with self.subTest(item=name_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.drag_display_and_time(start_tuple)
                self.assertTrue(self.plot_widget.fast_drag_artist_list)
                send_mouse_event(self.plot_widget, "button_release_event",
                                 start_tuple[0] + 2.0 * MOVE_COUNT_I + 10.0,
                                 start_tuple[1], LEFT_BUTTON_I)
                self.assertEqual(self.plot_widget.fast_drag_artist_list, [])
                self.assertIsNone(self.plot_widget.fast_drag_background)
                self.draw()

    @covers("LLFR-01215")
    def test_lost_release_ends_the_session(self) -> None:
        """With no button held, the session ends by itself and every
        artist is part of full draws again.

        Inputs: none.
        Outputs: none.
        """
        self.set_markers([(9, "Flag 1", 2.0)])
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.mouse("button_press_event", 2.0, 0.0)
        self.mouse("motion_notify_event", 2.5, 0.0)
        self.assertTrue(self.plot_widget.fast_drag_artist_list)
        self.plot_widget.end_fast_drag_if_released()
        self.assertEqual(self.plot_widget.fast_drag_artist_list, [])
        line = self.plot_widget.marker_artist_tuple(9)[0]
        self.assertFalse(line.get_animated())


@requires_qt
class DragRelayTest(unittest.TestCase):
    """The other plots of a drag are redrawn at most every 30 ms."""

    def setUp(self) -> None:
        """Create a plot panel whose plots are replaced by recorders.

        Inputs: none.
        Outputs: none.
        """
        from tests.support import get_qt_application
        self.application = get_qt_application()
        from view.plot_panel import PlotPanel
        self.panel = PlotPanel()
        self.follow_list = []
        follower = mock.Mock()
        follower.follow_marker_drag.side_effect = (
            lambda *argument_tuple: self.follow_list.append(argument_tuple))
        self.panel.shown_plot_widget_list = lambda plot_id_i: [follower]

    def tearDown(self) -> None:
        """Delete the panel.

        Inputs: none.
        Outputs: none.
        """
        self.panel.deleteLater()
        self.application.processEvents()

    @covers("LLFR-01217", "HLFR-00029")
    def test_relays_spaced_and_latest_shown(self) -> None:
        """While the button is held, ten places in a row redraw the
        other plots once, then the latest place after 30 ms; with no
        button held, every place is shown at once.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_panel import DRAG_RELAY_INTERVAL_MS_I
        self.panel.left_button_down = lambda: True
        for index_i in range(10):
            self.panel.relay_marker_drag(1, 7, float(index_i))
        self.assertEqual(self.follow_list, [(7, 0.0)])
        time.sleep(DRAG_RELAY_INTERVAL_MS_I / 1000.0 + 0.02)
        self.application.processEvents()
        self.assertEqual(self.follow_list, [(7, 0.0), (7, 9.0)])
        self.panel.left_button_down = lambda: False
        self.panel.relay_marker_drag(1, 7, 20.0)
        self.panel.relay_marker_drag(1, 7, 21.0)
        self.assertEqual(self.follow_list[-2:], [(7, 20.0), (7, 21.0)])
        # The model's markers make a waiting place out of date.
        self.panel.left_button_down = lambda: True
        self.panel.relay_marker_drag(1, 7, 30.0)
        self.panel.relay_marker_drag(1, 7, 31.0)
        self.panel.set_markers([])
        time.sleep(DRAG_RELAY_INTERVAL_MS_I / 1000.0 + 0.02)
        self.application.processEvents()
        self.assertNotIn((7, 31.0), self.follow_list)

    @covers("LLFR-01217", "HLFR-00029", "HLFR-00067")
    def test_redraw_spacing_while_the_pointer_moves(self) -> None:
        """While the pointer moves every 5 ms for 0.4 s with the button
        held, the other plots are redrawn at least once in every 150 ms
        and never twice within 30 ms, and the last place is shown.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_panel import DRAG_RELAY_INTERVAL_MS_I
        follow_time_list = []
        follower = mock.Mock()
        follower.follow_area_drag.side_effect = (
            lambda *argument_tuple: follow_time_list.append(
                (time.perf_counter(), argument_tuple)))
        self.panel.shown_plot_widget_list = lambda plot_id_i: [follower]
        self.panel.left_button_down = lambda: True
        start_s = time.perf_counter()
        place_i = 0
        while time.perf_counter() - start_s < RELAY_TEST_DURATION_S:
            place_i += 1
            self.panel.relay_area_drag(1, 4, float(place_i),
                                       float(place_i) + 1.0)
            self.application.processEvents()
            time.sleep(0.005)
        moving_end_s = time.perf_counter()
        time.sleep(DRAG_RELAY_INTERVAL_MS_I / 1000.0 + 0.03)
        self.application.processEvents()
        time_list = [time_s for time_s, _ in follow_time_list]
        self.assertGreaterEqual(len(time_list), 3)
        gap_list = [later_s - earlier_s for earlier_s, later_s
                    in zip(time_list, time_list[1:])]
        # At most once in every 30 ms; 1 ms is left for the rounding of
        # the timer to whole milliseconds.
        self.assertGreaterEqual(min(gap_list),
                                DRAG_RELAY_INTERVAL_MS_I / 1000.0 - 0.001)
        # At least once in every 150 ms while the pointer moves.
        moving_time_list = [start_s] + [time_s for time_s in time_list
                                        if time_s <= moving_end_s]
        moving_gap_list = [later_s - earlier_s for earlier_s, later_s
                           in zip(moving_time_list, moving_time_list[1:])]
        self.assertLessEqual(max(moving_gap_list), MAXIMUM_RELAY_GAP_S)
        self.assertLessEqual(moving_end_s - moving_time_list[-1],
                             MAXIMUM_RELAY_GAP_S)
        # The latest place is the one shown last.
        self.assertEqual(follow_time_list[-1][1],
                         (4, float(place_i), float(place_i) + 1.0))


if __name__ == "__main__":
    unittest.main()
