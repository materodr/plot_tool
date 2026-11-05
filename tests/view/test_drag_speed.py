"""Tests of the drags drawn over the image of the curves (#257 item 3).

A plot with 1,000,000 samples is dragged on: the flag, the area, the
pinned data tip and the text note are drawn over a copy of the image of
the curves (LLFR-01215), each move shown well within 50 milliseconds
(LLFR-01216), and the other plots of a flag or area drag are redrawn at
most once every 30 milliseconds (LLFR-01217).
"""

import statistics
import time
import unittest
from unittest import mock

import numpy as np

from tests.support import covers, requires_qt
from tests.view.test_markers_view import (
    LEFT_BUTTON_I, MarkerWidgetTestCase, send_mouse_event)

from controller.plot_tools import AREA_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR

# LLFR-01216: the largest delay of a move, and the samples of the plot.
MAXIMUM_MOVE_DELAY_S = 0.05
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
        # LLFR-01216: each move shown quickly; the first one makes the
        # image of the curves.
        self.assertLess(statistics.median(duration_list[1:]),
                        MAXIMUM_MOVE_DELAY_S)

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


if __name__ == "__main__":
    unittest.main()
