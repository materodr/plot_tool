"""Tests for the "Delete all ..." actions of the plot controller
(HLFR-00093, LLFR-00412 to LLFR-00417), with a fake view (no Qt).

The fake view and the setup of tests.controller.test_plot_controller are
reused: a real Workspace and a SignalFile whose signal "s<k>" has the
values k * Time, with Time = 0, 1, ..., 10 s. The frequency plots use the
real controllers of tests.controller.test_frequency_plots_controller.
"""

import unittest

from tests.support import covers

from controller.plot_tools import (
    AREA_TOOL_STR, DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR, MARKER_TOOL_STR)
from model.workspace import DELTA_X_KIND_STR, DELTA_Y_KIND_STR
from tests.controller.test_frequency_plots_controller import (
    FrequencyPlotTestCase)
from tests.controller.test_plot_controller import PlotControllerTestCase


class DeleteAllTestCase(PlotControllerTestCase):
    """Shared setup: two tabs; the first holds two time plots, the second
    one time plot, each with pinned tips and delta markers, and the
    workspace holds three flags and two areas."""

    def setUp(self) -> None:
        """Build the plots, tips, delta markers, flags and areas.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.double_click("s1")
        self.double_click("s2")
        self.first_plot_id_i, self.second_plot_id_i = (
            self.current_plot_ids())
        self.handler("add_tab")()
        self.double_click("s3")
        self.third_plot_id_i = self.current_plot_ids()[0]
        self.plot_id_tuple = (self.first_plot_id_i, self.second_plot_id_i,
                              self.third_plot_id_i)
        for plot_id_i, signal_name_str in zip(self.plot_id_tuple,
                                              ("s1", "s2", "s3")):
            factor_f = float(signal_name_str[1:])
            for time_s in (2.0, 5.0):
                self.handler("tip_pin_handler")(
                    plot_id_i, signal_name_str, time_s, factor_f * time_s)
            self.place_delta(plot_id_i, signal_name_str, DELTA_X_TOOL_STR,
                             1.0, 4.0)
            self.place_delta(plot_id_i, signal_name_str, DELTA_Y_TOOL_STR,
                             6.0, 9.0)
        self.choose_tool(MARKER_TOOL_STR)
        for time_s in (1.0, 3.0, 7.0):
            self.handler("marker_place_handler")(self.first_plot_id_i,
                                                 time_s)
        self.choose_tool(AREA_TOOL_STR)
        self.handler("area_create_handler")(self.first_plot_id_i, 1.5, 2.5)
        self.handler("area_create_handler")(self.third_plot_id_i, 6.0, 8.0)

    def handler(self, name_str: str):
        """Return a handler the controller gave the fake view.

        Inputs:
            name_str: the handler name.
        Outputs: the handler function.
        """
        return self.view.handler_dict[name_str]

    def choose_tool(self, tool_str: str) -> None:
        """Report a plot tool change, as the top panel does.

        Inputs:
            tool_str: the new tool name.
        Outputs: none.
        """
        self.handler("plot_tool")(tool_str)

    def place_delta(self, plot_id_i: int, signal_name_str: str,
                    tool_str: str, first_time_s: float,
                    second_time_s: float) -> None:
        """Pick the two points of a delta marker on a curve.

        Inputs:
            plot_id_i: id of the plot.
            signal_name_str: the curve of both points.
            tool_str: DELTA_X_TOOL_STR or DELTA_Y_TOOL_STR.
            first_time_s: time of the first point.
            second_time_s: time of the second point.
        Outputs: none.
        """
        self.choose_tool(tool_str)
        factor_f = float(signal_name_str[1:])
        for time_s in (first_time_s, second_time_s):
            self.handler("delta_point_pick_handler")(
                plot_id_i, signal_name_str, time_s, factor_f * time_s)

    def plot(self, plot_id_i: int):
        """Return a model plot by its id.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: the Plot.
        """
        return self.workspace.find_plot(plot_id_i)

    def tip_count_list(self) -> list:
        """Return the number of pinned tips of every plot, in order.

        Inputs: none.
        Outputs: a list of ints, one per plot of plot_id_tuple.
        """
        return [len(self.plot(plot_id_i).pinned_tip_list)
                for plot_id_i in self.plot_id_tuple]

    def delta_kind_list(self) -> list:
        """Return the kinds of the delta markers of every plot.

        Inputs: none.
        Outputs: a list with a list of kind names per plot.
        """
        return [[delta_marker.kind_str for delta_marker in
                 self.plot(plot_id_i).delta_marker_list]
                for plot_id_i in self.plot_id_tuple]

    def drawn_tip_count_list(self) -> list:
        """Return the number of pinned tips each plot last drew.

        Inputs: none.
        Outputs: a list of ints, one per plot of plot_id_tuple.
        """
        return [len(self.view.drawn_dict[plot_id_i][1])
                for plot_id_i in self.plot_id_tuple]

    def drawn_delta_count_list(self) -> list:
        """Return the number of delta markers each plot last drew.

        Inputs: none.
        Outputs: a list of ints, one per plot of plot_id_tuple.
        """
        return [len(self.view.delta_drawn_dict[plot_id_i])
                for plot_id_i in self.plot_id_tuple]

    def undo_depth(self) -> int:
        """Return how many actions can be undone.

        Inputs: none.
        Outputs: the depth of the undo history.
        """
        return self.controller.undo_history.depth()

    def assert_one_undoable_action(self, action, check_after,
                                   check_before) -> None:
        """Run an action, then check it, undo it and redo it.

        Inputs:
            action: function without arguments that runs the action.
            check_after: function that checks the state after it.
            check_before: function that checks the state before it.
        Outputs: none.
        """
        depth_i = self.undo_depth()
        check_before()
        action()
        check_after()
        # LLFR-00140: one undoable action, whatever the number of items.
        self.assertEqual(self.undo_depth(), depth_i + 1)
        self.handler("undo")()
        check_before()
        self.assertEqual(self.undo_depth(), depth_i)
        # LLFR-00192: redo deletes them all again.
        self.handler("redo")()
        check_after()
        self.assertEqual(self.undo_depth(), depth_i + 1)

    def assert_no_message(self) -> None:
        """Check that no box was shown by the fake view.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.view.full_tab_count_i, 0)
        self.assertEqual(self.view.kind_mismatch_count_i, 0)
        self.assertEqual(self.view.tab_name_taken_list, [])
        self.assertEqual(self.view.color_question_list, [])
        self.assertEqual(self.view.marker_name_question_list, [])
        self.assertEqual(self.view.area_name_question_list, [])


class DeleteAllDataTipsTest(DeleteAllTestCase):
    """The two "Delete all data tips" options (LLFR-00412, LLFR-00413)."""

    @covers("LLFR-00412", "LLFR-00140", "LLFR-00138", "LLFR-00192")
    def test_delete_all_tips_in_this_plot(self) -> None:
        """Every tip of the chosen plot goes, in one undoable action; the
        tips of the other plots, and every other item, stay.

        Inputs: none.
        Outputs: none.
        """
        def check_before() -> None:
            """Check the tips before the deletion."""
            self.assertEqual(self.tip_count_list(), [2, 2, 2])
            self.assertEqual(self.drawn_tip_count_list(), [2, 2, 2])

        def check_after() -> None:
            """Check the tips after the deletion."""
            self.assertEqual(self.tip_count_list(), [2, 0, 2])
            self.assertEqual(self.drawn_tip_count_list(), [2, 0, 2])
            self.assertEqual(self.delta_kind_list(), delta_kind_list)
            self.assertEqual(len(self.workspace.marker_list), 3)
            self.assertEqual(len(self.workspace.area_list), 2)
        delta_kind_list = self.delta_kind_list()
        self.assert_one_undoable_action(
            lambda: self.handler("plot_pinned_tips_delete_handler")(
                self.second_plot_id_i),
            check_after, check_before)
        self.assert_no_message()

    @covers("LLFR-00413", "LLFR-00140", "LLFR-00138", "LLFR-00192")
    def test_delete_all_tips_in_all_plots(self) -> None:
        """Every tip of every plot of every tab goes, also in the hidden
        tab, in one undoable action.

        Inputs: none.
        Outputs: none.
        """
        def check_before() -> None:
            """Check the tips before the deletion."""
            self.assertEqual(self.tip_count_list(), [2, 2, 2])
            self.assertEqual(self.drawn_tip_count_list(), [2, 2, 2])

        def check_after() -> None:
            """Check the tips after the deletion."""
            self.assertEqual(self.tip_count_list(), [0, 0, 0])
            self.assertEqual(self.drawn_tip_count_list(), [0, 0, 0])
            self.assertEqual(self.delta_kind_list(), delta_kind_list)
        delta_kind_list = self.delta_kind_list()
        # The second tab is shown; the first one is hidden.
        self.assert_one_undoable_action(
            lambda: self.handler("all_pinned_tips_delete_handler")(
                self.third_plot_id_i),
            check_after, check_before)
        self.assert_no_message()

    @covers("LLFR-00412", "LLFR-00413", "LLFR-00140")
    def test_nothing_to_delete_and_unknown_plot(self) -> None:
        """With no tip left, or for an unknown plot, nothing changes and
        nothing is recorded for undo.

        Inputs: none.
        Outputs: none.
        """
        self.handler("all_pinned_tips_delete_handler")(self.first_plot_id_i)
        depth_i = self.undo_depth()
        self.handler("plot_pinned_tips_delete_handler")(self.first_plot_id_i)
        self.handler("all_pinned_tips_delete_handler")(self.first_plot_id_i)
        self.assertEqual(self.undo_depth(), depth_i)
        self.handler("undo")()
        self.assertEqual(self.tip_count_list(), [2, 2, 2])
        self.handler("plot_pinned_tips_delete_handler")(999)
        self.handler("all_pinned_tips_delete_handler")(999)
        self.assertEqual(self.tip_count_list(), [2, 2, 2])


class DeleteAllDeltaMarkersTest(DeleteAllTestCase):
    """The two "Delete all delta markers" options (LLFR-00414,
    LLFR-00415)."""

    @covers("LLFR-00414", "LLFR-00140", "LLFR-00138", "LLFR-00192")
    def test_delete_all_delta_markers_in_this_plot(self) -> None:
        """Every Delta X and Delta Y marker of the chosen plot goes, in
        one undoable action; the other plots keep theirs, and a first
        point picked in another plot stays.

        Inputs: none.
        Outputs: none.
        """
        both_list = [DELTA_X_KIND_STR, DELTA_Y_KIND_STR]
        self.choose_tool(DELTA_X_TOOL_STR)
        self.handler("delta_point_pick_handler")(
            self.third_plot_id_i, "s3", 3.0, 9.0)
        pending_tuple = self.controller.pending_delta_tuple

        def check_before() -> None:
            """Check the delta markers before the deletion."""
            self.assertEqual(self.delta_kind_list(), [both_list] * 3)
            self.assertEqual(self.drawn_delta_count_list(), [2, 2, 2])

        def check_after() -> None:
            """Check the delta markers after the deletion."""
            self.assertEqual(self.delta_kind_list(),
                             [[], both_list, both_list])
            self.assertEqual(self.drawn_delta_count_list(), [0, 2, 2])
            self.assertEqual(self.tip_count_list(), [2, 2, 2])

        def delete_and_check_first_point() -> None:
            """Run the deletion; the first point of plot 3 stays."""
            self.handler("plot_delta_markers_delete_handler")(
                self.first_plot_id_i)
            self.assertEqual(self.controller.pending_delta_tuple,
                             pending_tuple)
            self.assertEqual(
                self.view.delta_first_point_dict[self.third_plot_id_i],
                ("s3", 3.0, 9.0))
        self.assert_one_undoable_action(delete_and_check_first_point,
                                        check_after, check_before)
        self.assert_no_message()

    @covers("LLFR-00414")
    def test_first_point_in_the_same_plot_stays(self) -> None:
        """A first point picked in the plot whose delta markers are all
        deleted is kept, with its dot.

        Inputs: none.
        Outputs: none.
        """
        self.choose_tool(DELTA_Y_TOOL_STR)
        self.handler("delta_point_pick_handler")(
            self.first_plot_id_i, "s1", 3.0, 3.0)
        pending_tuple = self.controller.pending_delta_tuple
        self.assertTrue(pending_tuple)
        self.handler("plot_delta_markers_delete_handler")(
            self.first_plot_id_i)
        self.assertEqual(self.plot(self.first_plot_id_i).delta_marker_list,
                         [])
        self.assertEqual(self.controller.pending_delta_tuple, pending_tuple)
        self.assertEqual(
            self.view.delta_first_point_dict[self.first_plot_id_i],
            ("s1", 3.0, 3.0))
        # The kept first point still places a marker with a second click.
        self.handler("delta_point_pick_handler")(
            self.first_plot_id_i, "s1", 8.0, 8.0)
        self.assertEqual(self.delta_kind_list()[0], [DELTA_Y_KIND_STR])

    @covers("LLFR-00415", "LLFR-00140", "LLFR-00138", "LLFR-00192")
    def test_delete_all_delta_markers_in_all_plots(self) -> None:
        """Every delta marker of every plot of every tab goes, in one
        undoable action; a picked first point stays.

        Inputs: none.
        Outputs: none.
        """
        both_list = [DELTA_X_KIND_STR, DELTA_Y_KIND_STR]
        self.choose_tool(DELTA_X_TOOL_STR)
        self.handler("delta_point_pick_handler")(
            self.second_plot_id_i, "s2", 3.0, 6.0)
        pending_tuple = self.controller.pending_delta_tuple

        def check_before() -> None:
            """Check the delta markers before the deletion."""
            self.assertEqual(self.delta_kind_list(), [both_list] * 3)
            self.assertEqual(self.drawn_delta_count_list(), [2, 2, 2])

        def check_after() -> None:
            """Check the delta markers after the deletion."""
            self.assertEqual(self.delta_kind_list(), [[], [], []])
            self.assertEqual(self.drawn_delta_count_list(), [0, 0, 0])
            self.assertEqual(self.tip_count_list(), [2, 2, 2])
        check_before()
        self.handler("all_delta_markers_delete_handler")(
            self.third_plot_id_i)
        check_after()
        self.assertEqual(self.controller.pending_delta_tuple, pending_tuple)
        self.assertEqual(
            self.view.delta_first_point_dict[self.second_plot_id_i],
            ("s2", 3.0, 6.0))
        self.handler("undo")()
        check_before()
        self.handler("redo")()
        check_after()
        self.assert_no_message()

    @covers("LLFR-00414", "LLFR-00415", "LLFR-00140")
    def test_nothing_to_delete_and_unknown_plot(self) -> None:
        """With no delta marker left, or for an unknown plot, nothing
        changes and nothing is recorded for undo.

        Inputs: none.
        Outputs: none.
        """
        self.handler("all_delta_markers_delete_handler")(
            self.first_plot_id_i)
        depth_i = self.undo_depth()
        self.handler("plot_delta_markers_delete_handler")(
            self.first_plot_id_i)
        self.handler("all_delta_markers_delete_handler")(
            self.first_plot_id_i)
        self.assertEqual(self.undo_depth(), depth_i)
        self.handler("undo")()
        self.handler("plot_delta_markers_delete_handler")(999)
        self.handler("all_delta_markers_delete_handler")(999)
        self.assertEqual(self.drawn_delta_count_list(), [2, 2, 2])


class DeleteAllFlagsAndAreasTest(DeleteAllTestCase):
    """"Delete all flags" and "Delete all areas" (LLFR-00416,
    LLFR-00417)."""

    @covers("LLFR-00416", "LLFR-00205", "LLFR-00140", "LLFR-00138",
            "LLFR-00192", "LLFR-00111")
    def test_delete_all_flags(self) -> None:
        """Every flag leaves every time plot of every tab, in one
        undoable action; the flag numbers are not reused.

        Inputs: none.
        Outputs: none.
        """
        def check_before() -> None:
            """Check the flags before the deletion."""
            self.assertEqual([marker.name_str for marker in
                              self.workspace.marker_list],
                             ["Flag 1", "Flag 2", "Flag 3"])
            for plot_id_i in self.plot_id_tuple:
                self.assertEqual(len(self.view.marker_drawn_dict[plot_id_i]),
                                 3)

        def check_after() -> None:
            """Check the flags after the deletion."""
            self.assertEqual(self.workspace.marker_list, [])
            for plot_id_i in self.plot_id_tuple:
                self.assertEqual(self.view.marker_drawn_dict[plot_id_i], [])
            self.assertEqual(len(self.workspace.area_list), 2)
            self.assertEqual(self.tip_count_list(), [2, 2, 2])
        self.assert_one_undoable_action(
            lambda: self.handler("all_markers_delete_handler")(
                self.second_plot_id_i),
            check_after, check_before)
        self.assert_no_message()
        # LLFR-00111: the next flag gets the next number.
        self.choose_tool(MARKER_TOOL_STR)
        self.handler("marker_place_handler")(self.first_plot_id_i, 4.0)
        self.assertEqual(self.workspace.marker_list[0].name_str, "Flag 4")

    @covers("LLFR-00417", "LLFR-00310", "LLFR-00140", "LLFR-00138",
            "LLFR-00192", "LLFR-00309")
    def test_delete_all_areas(self) -> None:
        """Every area leaves every time plot of every tab, in one
        undoable action; the area numbers are not reused.

        Inputs: none.
        Outputs: none.
        """
        def check_before() -> None:
            """Check the areas before the deletion."""
            self.assertEqual([area.name_str for area in
                              self.workspace.area_list],
                             ["Area 1", "Area 2"])
            for plot_id_i in self.plot_id_tuple:
                self.assertEqual(len(self.view.area_drawn_dict[plot_id_i]),
                                 2)

        def check_after() -> None:
            """Check the areas after the deletion."""
            self.assertEqual(self.workspace.area_list, [])
            for plot_id_i in self.plot_id_tuple:
                self.assertEqual(self.view.area_drawn_dict[plot_id_i], [])
            self.assertEqual(len(self.workspace.marker_list), 3)
            self.assertEqual(self.drawn_delta_count_list(), [2, 2, 2])
        self.assert_one_undoable_action(
            lambda: self.handler("all_areas_delete_handler")(
                self.third_plot_id_i),
            check_after, check_before)
        self.assert_no_message()
        # LLFR-00309: the next area gets the next number.
        self.handler("area_create_handler")(self.first_plot_id_i, 4.0, 5.0)
        self.assertEqual(self.workspace.area_list[0].name_str, "Area 3")

    @covers("LLFR-00416", "LLFR-00417", "LLFR-00140")
    def test_nothing_to_delete_and_unknown_plot(self) -> None:
        """With no flag or area left, or for an unknown plot, nothing
        changes and nothing is recorded for undo.

        Inputs: none.
        Outputs: none.
        """
        self.handler("all_markers_delete_handler")(999)
        self.handler("all_areas_delete_handler")(999)
        self.assertEqual(len(self.workspace.marker_list), 3)
        self.assertEqual(len(self.workspace.area_list), 2)
        self.handler("all_markers_delete_handler")(self.first_plot_id_i)
        self.handler("all_areas_delete_handler")(self.first_plot_id_i)
        depth_i = self.undo_depth()
        self.handler("all_markers_delete_handler")(self.first_plot_id_i)
        self.handler("all_areas_delete_handler")(self.first_plot_id_i)
        self.assertEqual(self.undo_depth(), depth_i)


class DeleteAllOnFrequencyPlotsTest(FrequencyPlotTestCase):
    """"... in all plots" also covers the frequency plots (LLFR-00413,
    LLFR-00415)."""

    def setUp(self) -> None:
        """Make a time plot and a frequency plot, each with a pinned tip
        and a delta marker.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.double_click("Speed")
        self.time_plot_id_i = self.last_plot_id()
        fft_name_str = self.create_fft()
        self.double_click(fft_name_str)
        self.frequency_plot_id_i = self.last_plot_id()
        self.assertTrue(self.plot(self.frequency_plot_id_i)
                        .is_frequency_plot())
        for plot_id_i, signal_name_str in (
                (self.time_plot_id_i, "Speed"),
                (self.frequency_plot_id_i, fft_name_str)):
            self.view.handler_dict["tip_pin_handler"](
                plot_id_i, signal_name_str, 1.0, 1.0)
            self.view.handler_dict["plot_tool"](DELTA_X_TOOL_STR)
            for time_s in (0.5, 2.0):
                self.view.handler_dict["delta_point_pick_handler"](
                    plot_id_i, signal_name_str, time_s, 1.0)
        self.view.handler_dict["plot_tool"](MARKER_TOOL_STR)

    def counts(self, attribute_str: str) -> list:
        """Return the number of items of a kind in both plots.

        Inputs:
            attribute_str: "pinned_tip_list" or "delta_marker_list".
        Outputs: [count in the time plot, count in the frequency plot].
        """
        return [len(getattr(self.plot(plot_id_i), attribute_str))
                for plot_id_i in (self.time_plot_id_i,
                                  self.frequency_plot_id_i)]

    @covers("LLFR-00413", "LLFR-00140")
    def test_all_tips_of_time_and_frequency_plots(self) -> None:
        """Chosen on the frequency plot, the time plot loses its tip too;
        one undo brings both back.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.counts("pinned_tip_list"), [1, 1])
        self.view.handler_dict["all_pinned_tips_delete_handler"](
            self.frequency_plot_id_i)
        self.assertEqual(self.counts("pinned_tip_list"), [0, 0])
        self.assertEqual(self.counts("delta_marker_list"), [1, 1])
        self.view.handler_dict["undo"]()
        self.assertEqual(self.counts("pinned_tip_list"), [1, 1])

    @covers("LLFR-00415", "LLFR-00140")
    def test_all_delta_markers_of_time_and_frequency_plots(self) -> None:
        """Chosen on the time plot, the frequency plot loses its delta
        marker too; one undo brings both back.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.counts("delta_marker_list"), [1, 1])
        self.view.handler_dict["all_delta_markers_delete_handler"](
            self.time_plot_id_i)
        self.assertEqual(self.counts("delta_marker_list"), [0, 0])
        self.assertEqual(self.counts("pinned_tip_list"), [1, 1])
        self.view.handler_dict["undo"]()
        self.assertEqual(self.counts("delta_marker_list"), [1, 1])

    @covers("LLFR-00412", "LLFR-00414")
    def test_this_plot_options_on_a_frequency_plot(self) -> None:
        """The "in this plot" options work on a frequency plot and leave
        the time plot unchanged.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["plot_pinned_tips_delete_handler"](
            self.frequency_plot_id_i)
        self.view.handler_dict["plot_delta_markers_delete_handler"](
            self.frequency_plot_id_i)
        self.assertEqual(self.counts("pinned_tip_list"), [1, 0])
        self.assertEqual(self.counts("delta_marker_list"), [1, 0])


if __name__ == "__main__":
    unittest.main()
