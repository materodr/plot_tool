"""Tests for the delta marker handlers of the plot controller.

The fake view and the setup of tests.controller.test_plot_controller
are reused: a real Workspace, a SignalFile built in the test and a view
that records every call (no Qt needed). Signal "s<k>" has the values
k * Time, with Time = 0, 1, ..., 10 s.
"""

import math
import unittest

from tests.support import covers

from controller.plot_tools import (
    DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR,
    TIP_TOOL_STR, ZOOM_TOOL_STR)
from model.undo_history import MAXIMUM_UNDO_DEPTH_I
from model.workspace import DELTA_X_KIND_STR, DELTA_Y_KIND_STR
from tests.controller.test_plot_controller import (
    PlotControllerTestCase, make_signal_file)


class DeltaControllerTestCase(PlotControllerTestCase):
    """Shared setup: one plot with s1 and s2, Delta X tool active."""

    def setUp(self) -> None:
        """Open the file, plot s1 and s2 and activate Delta X.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.double_click("s1")
        self.plot_id_i = self.current_plot_ids()[0]
        self.drop(self.plot_id_i, "s2")
        self.plot = self.workspace.find_plot(self.plot_id_i)
        self.set_tool(DELTA_X_TOOL_STR)

    def set_tool(self, tool_str: str) -> None:
        """Report a plot tool change, as the top panel does.

        Inputs:
            tool_str: the new tool name.
        Outputs: none.
        """
        self.view.handler_dict["plot_tool"](tool_str)

    def pick(self, signal_name_str: str, time_s: float,
             plot_id_i: int = None) -> None:
        """Report a left click on a curve, at a sample of the signal.

        Inputs:
            signal_name_str: the clicked curve.
            time_s: time of the nearest sample; its value is read from
                the file.
            plot_id_i: the clicked plot (default: the plot of the setup).
        Outputs: none.
        """
        if plot_id_i is None:
            plot_id_i = self.plot_id_i
        value_f = float(self.signal_file.signal_array(signal_name_str)[
            int(time_s)])
        self.view.handler_dict["delta_point_pick_handler"](
            plot_id_i, signal_name_str, time_s, value_f)

    def drawn_delta_list(self, plot_id_i: int = None) -> list:
        """Return the delta markers last drawn in a plot.

        Inputs:
            plot_id_i: the plot (default: the plot of the setup).
        Outputs: the list of drawn tuples.
        """
        if plot_id_i is None:
            plot_id_i = self.plot_id_i
        return self.view.delta_drawn_dict.get(plot_id_i, [])

    def first_point(self, plot_id_i: int = None) -> tuple:
        """Return the dot last shown in a plot, () when none.

        Inputs:
            plot_id_i: the plot (default: the plot of the setup).
        Outputs: the point tuple given to set_delta_first_point.
        """
        if plot_id_i is None:
            plot_id_i = self.plot_id_i
        return self.view.delta_first_point_dict.get(plot_id_i, ())

    def undo(self) -> None:
        """Run the Undo handler.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["undo"]()

    def undo_depth(self) -> int:
        """Return how many actions can be undone.

        Inputs: none.
        Outputs: the depth of the undo history.
        """
        return self.controller.undo_history.depth()


class PickPointsTest(DeltaControllerTestCase):
    """Picking the two points of a delta marker."""

    @covers("LLFR-00163", "LLFR-00172")
    def test_first_click_picks_a_point_and_shows_a_dot(self) -> None:
        """The first click keeps the sample and asks for its dot.

        Inputs: none.
        Outputs: none.
        """
        self.pick("s1", 3.0)
        self.assertEqual(self.controller.pending_delta_tuple,
                         (self.plot_id_i, ("s1", 3.0, 3.0)))
        self.assertEqual(self.first_point(), ("s1", 3.0, 3.0))
        # Nothing is placed yet, and nothing is undoable yet.
        self.assertEqual(self.plot.delta_marker_list, [])
        self.assertEqual(self.drawn_delta_list(), [])

    @covers("LLFR-00164", "LLFR-00168", "LLFR-00169")
    def test_second_click_on_another_curve_places_delta_x(self) -> None:
        """s1 at 2 s then s2 at 7 s gives Delta X with +5 s.

        Inputs: none.
        Outputs: none.
        """
        self.pick("s1", 2.0)
        self.pick("s2", 7.0)
        self.assertEqual(self.controller.pending_delta_tuple, ())
        # LLFR-00164: the dot of the first point goes away.
        self.assertEqual(self.first_point(), ())
        self.assertEqual(len(self.plot.delta_marker_list), 1)
        delta_marker = self.plot.delta_marker_list[0]
        self.assertEqual(delta_marker.kind_str, DELTA_X_KIND_STR)
        drawn_tuple = self.drawn_delta_list()[0]
        self.assertEqual(drawn_tuple[1:], (DELTA_X_KIND_STR,
                                           ("s1", 2.0, 2.0),
                                           ("s2", 7.0, 14.0), 5.0))
        # LLFR-00109: the tool stays active.
        self.assertEqual(self.controller.plot_tool_str, DELTA_X_TOOL_STR)

    @covers("LLFR-00164", "LLFR-00170", "LLFR-00171")
    def test_delta_y_on_the_same_curve_is_signed(self) -> None:
        """Delta Y from s2 at 6 s to s2 at 1 s measures 2 - 12 = -10.

        Inputs: none.
        Outputs: none.
        """
        self.set_tool(DELTA_Y_TOOL_STR)
        self.pick("s2", 6.0)
        self.pick("s2", 1.0)
        drawn_tuple = self.drawn_delta_list()[0]
        self.assertEqual(drawn_tuple[1], DELTA_Y_KIND_STR)
        self.assertEqual(drawn_tuple[4], -10.0)
        self.assertEqual(self.plot.delta_marker_list[0].delta_f(), -10.0)

    @covers("LLFR-00169")
    def test_delta_x_backwards_is_negative(self) -> None:
        """Second point before the first: the time difference is < 0.

        Inputs: none.
        Outputs: none.
        """
        self.pick("s2", 9.0)
        self.pick("s1", 4.0)
        self.assertEqual(self.drawn_delta_list()[0][4], -5.0)

    @covers("LLFR-00165")
    def test_click_off_a_curve_keeps_the_first_point(self) -> None:
        """The view reports no click off a curve: the point stays.

        A click that is not on a curve never reaches the controller (the
        view only reports clicks on curves), so the first point is kept
        across any number of such clicks, and no message is shown.

        Inputs: none.
        Outputs: none.
        """
        self.pick("s1", 2.0)
        call_count_i = len(self.view.call_list)
        # A stale or wrong report (signal not in the plot) changes
        # nothing either.
        self.view.handler_dict["delta_point_pick_handler"](
            self.plot_id_i, "s9", 1.0, 9.0)
        self.view.handler_dict["delta_point_pick_handler"](
            self.plot_id_i, "s1", math.nan, 1.0)
        self.assertEqual(len(self.view.call_list), call_count_i)
        self.assertEqual(self.controller.pending_delta_tuple,
                         (self.plot_id_i, ("s1", 2.0, 2.0)))
        self.assertEqual(self.view.full_tab_count_i, 0)
        self.pick("s1", 5.0)
        self.assertEqual(self.drawn_delta_list()[0][4], 3.0)

    @covers("LLFR-00166")
    def test_click_in_another_plot_starts_again_there(self) -> None:
        """A curve in another plot discards the first point and its dot.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s3")
        other_plot_id_i = self.current_plot_ids()[1]
        self.pick("s1", 2.0)
        self.pick("s3", 4.0, other_plot_id_i)
        self.assertEqual(self.first_point(), ())
        self.assertEqual(self.first_point(other_plot_id_i),
                         ("s3", 4.0, 12.0))
        self.assertEqual(self.controller.pending_delta_tuple,
                         (other_plot_id_i, ("s3", 4.0, 12.0)))
        self.assertEqual(self.plot.delta_marker_list, [])
        # The second click in the other plot places the marker there.
        self.pick("s3", 6.0, other_plot_id_i)
        other_plot = self.workspace.find_plot(other_plot_id_i)
        self.assertEqual(len(other_plot.delta_marker_list), 1)
        self.assertEqual(self.drawn_delta_list(other_plot_id_i)[0][4], 2.0)
        self.assertEqual(self.plot.delta_marker_list, [])

    @covers("LLFR-00163", "LLFR-00109")
    def test_picks_are_ignored_without_a_delta_tool(self) -> None:
        """With any other tool or none, a pick report does nothing.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (TIP_TOOL_STR, ZOOM_TOOL_STR, MARKER_TOOL_STR,
                         NO_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.set_tool(tool_str)
                self.pick("s1", 2.0)
                self.pick("s2", 3.0)
                self.assertEqual(self.controller.pending_delta_tuple, ())
                self.assertEqual(self.plot.delta_marker_list, [])

    @covers("LLFR-00163")
    def test_unknown_plot_is_ignored(self) -> None:
        """A pick in a plot id that does not exist changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["delta_point_pick_handler"](
            9999, "s1", 1.0, 1.0)
        self.assertEqual(self.controller.pending_delta_tuple, ())

    @covers("LLFR-00174")
    def test_several_markers_of_both_kinds(self) -> None:
        """Three Delta X and two Delta Y markers stay in one plot.

        Inputs: none.
        Outputs: none.
        """
        for first_s, second_s in ((0.0, 1.0), (2.0, 5.0), (3.0, 9.0)):
            self.pick("s1", first_s)
            self.pick("s2", second_s)
        self.set_tool(DELTA_Y_TOOL_STR)
        for first_s, second_s in ((1.0, 2.0), (8.0, 4.0)):
            self.pick("s2", first_s)
            self.pick("s1", second_s)
        kind_list = [drawn_tuple[1] for drawn_tuple in
                     self.drawn_delta_list()]
        self.assertEqual(kind_list, [DELTA_X_KIND_STR] * 3
                         + [DELTA_Y_KIND_STR] * 2)
        self.assertEqual([drawn_tuple[4] for drawn_tuple in
                          self.drawn_delta_list()],
                         [1.0, 3.0, 6.0, 2.0 - 2.0, 4.0 - 16.0])


class DiscardFirstPointTest(DeltaControllerTestCase):
    """The first point is discarded whenever it can no longer be used."""

    def assert_discarded(self) -> None:
        """Check that no first point is kept and its dot is gone.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.controller.pending_delta_tuple, ())
        self.assertEqual(self.first_point(), ())

    @covers("LLFR-00167", "LLFR-00079")
    def test_any_tool_change_discards_the_first_point(self) -> None:
        """Second click, Delta Y, Tip, Zoom or marker all discard it.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (NO_TOOL_STR, DELTA_Y_TOOL_STR, TIP_TOOL_STR,
                         ZOOM_TOOL_STR, MARKER_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.set_tool(DELTA_X_TOOL_STR)
                self.pick("s1", 2.0)
                self.set_tool(tool_str)
                self.assert_discarded()
        # Starting again with Delta Y after a discard needs two clicks.
        self.set_tool(DELTA_Y_TOOL_STR)
        self.pick("s1", 2.0)
        self.assertEqual(self.plot.delta_marker_list, [])

    @covers("LLFR-00167", "LLFR-00178")
    def test_removing_the_first_points_curve_discards_it(self) -> None:
        """Deleting the curve of the first point discards the point.

        Inputs: none.
        Outputs: none.
        """
        self.pick("s1", 2.0)
        self.view.handler_dict["curve_delete_handler"](self.plot_id_i, "s1")
        self.assert_discarded()

    @covers("LLFR-00167")
    def test_removing_another_curve_keeps_the_first_point(self) -> None:
        """Deleting a curve without the first point keeps it.

        Inputs: none.
        Outputs: none.
        """
        self.pick("s1", 2.0)
        self.view.handler_dict["curve_delete_handler"](self.plot_id_i, "s2")
        self.assertEqual(self.controller.pending_delta_tuple,
                         (self.plot_id_i, ("s1", 2.0, 2.0)))
        self.pick("s1", 4.0)
        self.assertEqual(len(self.plot.delta_marker_list), 1)

    @covers("LLFR-00167", "LLFR-00049")
    def test_deleting_the_plot_or_tab_discards_it(self) -> None:
        """Deleting the plot, or the tab holding it, discards the point.

        Inputs: none.
        Outputs: none.
        """
        self.pick("s1", 2.0)
        self.view.handler_dict["plot_delete_handler"](self.plot_id_i)
        self.assert_discarded()
        # Now in a plot of a second tab that is then deleted.
        self.view.handler_dict["add_tab"]()
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.pick("s1", 2.0, plot_id_i)
        self.assertTrue(self.controller.pending_delta_tuple)
        self.view.handler_dict["delete_tab"](self.view.current_tab_id())
        self.assertEqual(self.controller.pending_delta_tuple, ())
        self.assertEqual(self.first_point(plot_id_i), ())

    @covers("LLFR-00167", "LLFR-00013", "LLFR-00015")
    def test_opening_a_file_discards_it(self) -> None:
        """A replaced file takes its first point with it.

        Inputs: none.
        Outputs: none.
        """
        self.pick("s1", 2.0)
        self.file_controller.open(make_signal_file(3), True)
        self.assert_discarded()

    @covers("LLFR-00167", "LLFR-00138")
    def test_undo_discards_it(self) -> None:
        """An undo rebuilds the views and discards the first point.

        Inputs: none.
        Outputs: none.
        """
        self.pick("s1", 2.0)
        self.undo()
        self.assertEqual(self.controller.pending_delta_tuple, ())
        self.assertIn(("set_delta_first_point", self.plot_id_i, ()),
                      self.view.call_list)


class DeleteAndUndoTest(DeltaControllerTestCase):
    """Deleting delta markers and undoing every delta action."""

    def place(self, first_s: float = 2.0, second_s: float = 7.0) -> int:
        """Place a Delta X marker from s1 to s2 and return its id.

        Inputs:
            first_s: time of the first point.
            second_s: time of the second point.
        Outputs: the id of the new delta marker.
        """
        self.pick("s1", first_s)
        self.pick("s2", second_s)
        return self.plot_of_setup().delta_marker_list[-1].delta_marker_id_i

    def plot_of_setup(self):
        """Return the current model Plot of the setup (after undos).

        Inputs: none.
        Outputs: the Plot, or None when it is gone.
        """
        return self.workspace.find_plot(self.plot_id_i)

    @covers("LLFR-00176")
    def test_delete_removes_only_that_marker(self) -> None:
        """"Delete" removes the chosen marker and redraws the plot.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.place(1.0, 2.0)
        second_id_i = self.place(3.0, 6.0)
        self.view.handler_dict["delta_marker_delete_handler"](
            self.plot_id_i, first_id_i)
        self.assertEqual([drawn_tuple[0] for drawn_tuple in
                          self.drawn_delta_list()], [second_id_i])
        # Unknown ids and plots are ignored.
        self.view.handler_dict["delta_marker_delete_handler"](
            self.plot_id_i, first_id_i)
        self.view.handler_dict["delta_marker_delete_handler"](
            9999, second_id_i)
        self.assertEqual(len(self.plot_of_setup().delta_marker_list), 1)

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00164")
    def test_placing_is_one_undoable_action(self) -> None:
        """Two clicks make one undo step; undo removes the marker.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.undo_depth()
        self.place()
        self.assertEqual(self.undo_depth(), depth_i + 1)
        self.undo()
        self.assertEqual(self.plot_of_setup().delta_marker_list, [])
        self.assertEqual(self.drawn_delta_list(), [])
        # The first click alone is not undoable.
        self.pick("s1", 2.0)
        self.assertEqual(self.undo_depth(), depth_i)

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00176")
    def test_deleting_is_undoable(self) -> None:
        """Undo of "Delete" brings the same marker back.

        Inputs: none.
        Outputs: none.
        """
        delta_marker_id_i = self.place()
        self.view.handler_dict["delta_marker_delete_handler"](
            self.plot_id_i, delta_marker_id_i)
        self.assertEqual(self.plot_of_setup().delta_marker_list, [])
        self.undo()
        self.assertEqual([drawn_tuple[0] for drawn_tuple in
                          self.drawn_delta_list()], [delta_marker_id_i])
        self.assertEqual(self.drawn_delta_list()[0][4], 5.0)

    @covers("LLFR-00178", "LLFR-00140", "LLFR-00138", "LLFR-00039")
    def test_curve_removal_takes_its_markers_and_undo_restores(self) -> None:
        """Removing s2 removes its marker; one undo restores both.

        Inputs: none.
        Outputs: none.
        """
        self.drop(self.plot_id_i, "s3")
        on_s2_id_i = self.place()
        self.set_tool(DELTA_Y_TOOL_STR)
        self.pick("s1", 1.0)
        self.pick("s3", 2.0)
        depth_i = self.undo_depth()
        self.view.handler_dict["curve_delete_handler"](self.plot_id_i, "s2")
        self.assertEqual(self.undo_depth(), depth_i + 1)
        self.assertEqual([drawn_tuple[1] for drawn_tuple in
                          self.drawn_delta_list()], [DELTA_Y_KIND_STR])
        self.undo()
        plot = self.plot_of_setup()
        self.assertTrue(plot.has_signal("s2"))
        self.assertEqual([drawn_tuple[0] for drawn_tuple in
                          self.drawn_delta_list()][0], on_s2_id_i)
        self.assertEqual(len(self.drawn_delta_list()), 2)

    @covers("LLFR-00178", "LLFR-00051", "LLFR-00138")
    def test_last_curve_removal_deletes_plot_and_undo_restores(self) -> None:
        """A marker on the last curve goes with the plot and comes back.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["curve_delete_handler"](self.plot_id_i, "s2")
        self.pick("s1", 2.0)
        self.pick("s1", 5.0)
        self.view.handler_dict["curve_delete_handler"](self.plot_id_i, "s1")
        self.assertIsNone(self.plot_of_setup())
        self.undo()
        self.assertEqual(len(self.plot_of_setup().delta_marker_list), 1)
        self.assertEqual(self.drawn_delta_list()[0][4], 3.0)

    @covers("LLFR-00139", "LLFR-00140")
    def test_twenty_one_placements_keep_twenty_undo_steps(self) -> None:
        """21 placed markers: the 20 latest can be undone, in order.

        Inputs: none.
        Outputs: none.
        """
        self.controller.undo_history.clear()
        for index_i in range(MAXIMUM_UNDO_DEPTH_I + 1):
            self.place(0.0, float(index_i % 10))
        self.assertEqual(self.undo_depth(), MAXIMUM_UNDO_DEPTH_I)
        for left_i in range(MAXIMUM_UNDO_DEPTH_I, 0, -1):
            self.undo()
            self.assertEqual(len(self.plot_of_setup().delta_marker_list),
                             left_i)
        self.assertEqual(len(self.plot_of_setup().delta_marker_list), 1)
        self.assertFalse(self.controller.undo_history.can_undo())


if __name__ == "__main__":
    unittest.main()
