"""Tests for the vertical marker handlers of the plot controller.

The fake view and the setup of tests.controller.test_plot_controller
are reused: a real Workspace, a SignalFile built in the test and a view
that records every call (no Qt needed).
"""

import unittest

from tests.support import covers

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR)
from tests.controller.test_plot_controller import PlotControllerTestCase


class MarkerControllerTestCase(PlotControllerTestCase):
    """Shared setup: one plot with s1 and the Vertical marker tool on."""

    def setUp(self) -> None:
        """Open the file, plot s1 and activate the Vertical marker tool.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.double_click("s1")
        self.plot_id_i = self.current_plot_ids()[0]
        self.plot = self.workspace.find_plot(self.plot_id_i)
        self.view.handler_dict["plot_tool"](MARKER_TOOL_STR)

    def place(self, time_s: float, plot_id_i: int = None) -> None:
        """Run the place handler as a click in the plot does.

        Inputs:
            time_s: clicked time, in seconds.
            plot_id_i: id of the plot (default: the plot of the setup).
        Outputs: none.
        """
        if plot_id_i is None:
            plot_id_i = self.plot_id_i
        self.view.handler_dict["marker_place_handler"](plot_id_i, time_s)

    def drawn_markers(self) -> list:
        """Return the markers last drawn in the plot of the setup.

        Inputs: none.
        Outputs: a list of tuples (marker_id_i, name_str, time_s).
        """
        return self.view.marker_drawn_dict[self.plot_id_i]

    def drawn_names(self) -> list:
        """Return the names of the markers last drawn in the plot.

        Inputs: none.
        Outputs: a list of str in placing order.
        """
        return [marker_tuple[1] for marker_tuple in self.drawn_markers()]

    def marker_id(self, name_str: str) -> int:
        """Return the id of a drawn marker by its name.

        Inputs:
            name_str: the marker's name.
        Outputs: the marker id.
        """
        for marker_id_i, drawn_name_str, _ in self.drawn_markers():
            if drawn_name_str == name_str:
                return marker_id_i
        raise AssertionError(f"no marker named {name_str!r}")

    def draw_count(self) -> int:
        """Return how many times the markers of the setup's plot were drawn.

        Inputs: none.
        Outputs: the number of draw_plot calls for that plot plus the
            number of set_markers calls (which draw on every plot).
        """
        return sum(1 for call_tuple in self.view.call_list
                   if call_tuple == ("draw_plot", self.plot_id_i)
                   or call_tuple[0] == "set_markers")

    def add_plot_in_new_tab(self, signal_name_str: str) -> int:
        """Add a tab and plot a signal there.

        Inputs:
            signal_name_str: the signal to plot.
        Outputs: the id of the new plot.
        """
        self.view.handler_dict["add_tab"]()
        self.double_click(signal_name_str)
        return self.current_plot_ids()[0]

    def marker_names_of(self, plot_id_i: int) -> list:
        """Return the names of the markers last drawn in a plot.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: a list of str in placing order.
        """
        return [marker_tuple[1]
                for marker_tuple in self.view.marker_drawn_dict[plot_id_i]]


class PlaceMarkerTest(MarkerControllerTestCase):
    """Placing markers by click (LLFR-00081, LLFR-00085, LLFR-00111)."""

    @covers("LLFR-00081", "LLFR-00085")
    def test_place_draws_marker_at_clicked_time(self) -> None:
        """Each click draws a new "Marker N" at the clicked time.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.drawn_markers(), [])
        self.place(2.5)
        self.place(7.25)
        self.assertEqual(self.drawn_names(), ["Marker 1", "Marker 2"])
        self.assertEqual([marker_tuple[2]
                          for marker_tuple in self.drawn_markers()],
                         [2.5, 7.25])
        self.assertEqual(len({marker_tuple[0]
                              for marker_tuple in self.drawn_markers()}), 2)
        # The curves are drawn on the same path as the markers.
        self.assertEqual(self.view.drawn_names(self.plot_id_i), ["s1"])

    @covers("LLFR-00085", "LLFR-00205")
    def test_numbers_are_shared_by_all_plots(self) -> None:
        """The numbering counts across plots; every plot shows them all.

        Inputs: none.
        Outputs: none.
        """
        self.place(1.0)
        self.place(2.0)
        self.double_click("s2")
        second_plot_id_i = self.current_plot_ids()[1]
        # LLFR-00205: the new plot shows the markers placed before it.
        self.assertEqual(self.marker_names_of(second_plot_id_i),
                         ["Marker 1", "Marker 2"])
        self.place(3.0, second_plot_id_i)
        for plot_id_i in (self.plot_id_i, second_plot_id_i):
            self.assertEqual(self.marker_names_of(plot_id_i),
                             ["Marker 1", "Marker 2", "Marker 3"])
        self.assertEqual(len(self.workspace.marker_list), 3)

    @covers("LLFR-00111", "LLFR-00085", "LLFR-00091")
    def test_deleted_number_is_not_reused(self) -> None:
        """After deleting Marker 2, the next marker is Marker 3.

        Inputs: none.
        Outputs: none.
        """
        self.place(1.0)
        self.place(2.0)
        self.view.handler_dict["marker_delete_handler"](
            self.plot_id_i, self.marker_id("Marker 2"))
        self.assertEqual(self.drawn_names(), ["Marker 1"])
        self.place(3.0)
        self.assertEqual(self.drawn_names(), ["Marker 1", "Marker 3"])

    @covers("LLFR-00109", "LLFR-00081")
    def test_tool_stays_active_after_placing(self) -> None:
        """Placing markers never changes the active tool.

        Inputs: none.
        Outputs: none.
        """
        tool_call_count_i = self.view.method_names().count("set_plot_tool")
        for time_s in (1.0, 2.0, 3.0):
            self.place(time_s)
        self.assertEqual(self.controller.plot_tool_str, MARKER_TOOL_STR)
        self.assertEqual(self.view.plot_tool_str, MARKER_TOOL_STR)
        self.assertEqual(self.view.method_names().count("set_plot_tool"),
                         tool_call_count_i)
        self.assertEqual(len(self.drawn_markers()), 3)

    @covers("LLFR-00081")
    def test_place_needs_the_marker_tool(self) -> None:
        """With another tool or none, a place request is ignored.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (NO_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.view.handler_dict["plot_tool"](tool_str)
                draw_count_i = self.draw_count()
                self.place(4.0)
                self.assertEqual(self.draw_count(), draw_count_i)
                self.assertEqual(self.workspace.marker_list, [])

    @covers("LLFR-00081", "LLFR-00070")
    def test_place_keeps_the_time_range(self) -> None:
        """Placing a marker in a zoomed plot keeps the zoom.

        Inputs: none.
        Outputs: none.
        """
        self.view.set_plot_time_range(self.plot_id_i, 2.0, 4.0)
        self.view.handler_dict["time_range_handler"](self.plot_id_i,
                                                     2.0, 4.0)
        self.place(3.0)
        self.assertEqual(self.view.range_dict[self.plot_id_i], (2.0, 4.0))

    @covers("LLFR-00081")
    def test_unknown_plot_or_bad_time_is_ignored(self) -> None:
        """Unknown plot ids and non-finite times change nothing.

        Inputs: none.
        Outputs: none.
        """
        draw_count_i = self.draw_count()
        self.place(1.0, 999)
        self.place(float("nan"))
        self.place(float("inf"))
        self.assertEqual(self.draw_count(), draw_count_i)
        self.assertEqual(self.workspace.marker_list, [])
        self.assertNotIn(999, self.view.marker_drawn_dict)


class MoveMarkerTest(MarkerControllerTestCase):
    """Moving a marker after a drag (LLFR-00086)."""

    @covers("LLFR-00086", "LLFR-00092")
    def test_move_leaves_marker_at_release_time(self) -> None:
        """The marker is redrawn at the released time, same name and id.

        Inputs: none.
        Outputs: none.
        """
        self.place(2.0)
        marker_id_i = self.marker_id("Marker 1")
        self.view.handler_dict["marker_move_handler"](self.plot_id_i,
                                                      marker_id_i, 6.5)
        self.assertEqual(self.drawn_markers(),
                         [(marker_id_i, "Marker 1", 6.5)])
        self.assertEqual(self.workspace.find_marker(marker_id_i).time_s, 6.5)
        self.assertEqual(self.controller.plot_tool_str, MARKER_TOOL_STR)

    @covers("LLFR-00086")
    def test_move_needs_the_marker_tool(self) -> None:
        """With another tool active, a move request is ignored.

        Inputs: none.
        Outputs: none.
        """
        self.place(2.0)
        marker_id_i = self.marker_id("Marker 1")
        self.view.handler_dict["plot_tool"](ZOOM_TOOL_STR)
        self.view.handler_dict["marker_move_handler"](self.plot_id_i,
                                                      marker_id_i, 6.5)
        self.assertEqual(self.workspace.find_marker(marker_id_i).time_s, 2.0)

    @covers("LLFR-00086")
    def test_move_with_unknown_ids_is_ignored(self) -> None:
        """Unknown plot or marker ids and bad times change nothing.

        Inputs: none.
        Outputs: none.
        """
        self.place(2.0)
        marker_id_i = self.marker_id("Marker 1")
        draw_count_i = self.draw_count()
        move_handler = self.view.handler_dict["marker_move_handler"]
        move_handler(999, marker_id_i, 5.0)
        move_handler(self.plot_id_i, 999, 5.0)
        move_handler(self.plot_id_i, marker_id_i, float("nan"))
        self.assertEqual(self.draw_count(), draw_count_i)
        self.assertEqual(self.workspace.find_marker(marker_id_i).time_s, 2.0)

    @covers("LLFR-00086", "LLFR-00205")
    def test_move_on_another_plot_moves_it_everywhere(self) -> None:
        """A marker dragged on any plot moves on every plot of every tab.

        Inputs: none.
        Outputs: none.
        """
        self.place(2.0)
        marker_id_i = self.marker_id("Marker 1")
        self.double_click("s2")
        second_plot_id_i = self.current_plot_ids()[1]
        other_tab_plot_id_i = self.add_plot_in_new_tab("s1")
        self.view.handler_dict["marker_move_handler"](second_plot_id_i,
                                                      marker_id_i, 5.0)
        self.assertEqual(self.workspace.find_marker(marker_id_i).time_s, 5.0)
        for plot_id_i in (self.plot_id_i, second_plot_id_i,
                          other_tab_plot_id_i):
            self.assertEqual(self.view.marker_drawn_dict[plot_id_i],
                             [(marker_id_i, "Marker 1", 5.0)])


class RenameMarkerTest(MarkerControllerTestCase):
    """Renaming a marker (LLFR-00088, LLFR-00089, LLFR-00112)."""

    def rename(self, marker_id_i: int, *answer_tuple) -> None:
        """Run the rename handler with prepared dialog answers.

        Inputs:
            marker_id_i: id of the marker.
            answer_tuple: what the dialog returns (None for cancel).
        Outputs: none.
        """
        self.view.marker_name_answer_list = list(answer_tuple)
        self.view.handler_dict["marker_rename_handler"](self.plot_id_i,
                                                        marker_id_i)

    @covers("LLFR-00088", "LLFR-00112")
    def test_rename_asks_with_current_name_and_redraws(self) -> None:
        """The dialog starts from the current name; the label changes.

        Inputs: none.
        Outputs: none.
        """
        self.place(2.0)
        marker_id_i = self.marker_id("Marker 1")
        self.rename(marker_id_i, "  Start $x$  ")
        self.assertEqual(self.view.marker_name_question_list, ["Marker 1"])
        self.assertEqual(self.drawn_markers(),
                         [(marker_id_i, "Start $x$", 2.0)])
        # A second rename starts from the new name.
        self.rename(marker_id_i, "Stop")
        self.assertEqual(self.view.marker_name_question_list,
                         ["Marker 1", "Start $x$"])
        self.assertEqual(self.drawn_names(), ["Stop"])

    @covers("LLFR-00089")
    def test_blank_name_keeps_old_name_without_message(self) -> None:
        """Empty or space-only names keep the name and draw nothing.

        Inputs: none.
        Outputs: none.
        """
        self.place(2.0)
        marker_id_i = self.marker_id("Marker 1")
        for blank_name_str in ("", "   ", "\t"):
            with self.subTest(name=blank_name_str):
                call_count_i = len(self.view.call_list)
                self.rename(marker_id_i, blank_name_str)
                new_call_list = self.view.call_list[call_count_i:]
                # Only the question itself: no redraw, no box.
                self.assertEqual(new_call_list,
                                 [("ask_marker_name", "Marker 1")])
                self.assertEqual(
                    self.workspace.find_marker(marker_id_i).name_str,
                    "Marker 1")
        self.assertEqual(self.view.full_tab_count_i, 0)

    @covers("LLFR-00088", "LLFR-00089")
    def test_cancelled_dialog_changes_nothing(self) -> None:
        """Cancelling the dialog keeps the name and draws nothing.

        Inputs: none.
        Outputs: none.
        """
        self.place(2.0)
        marker_id_i = self.marker_id("Marker 1")
        draw_count_i = self.draw_count()
        self.rename(marker_id_i, None)
        self.assertEqual(self.draw_count(), draw_count_i)
        self.assertEqual(self.drawn_names(), ["Marker 1"])

    @covers("LLFR-00088")
    def test_rename_works_with_any_tool(self) -> None:
        """The marker menu acts whatever plot tool is active.

        Inputs: none.
        Outputs: none.
        """
        self.place(2.0)
        marker_id_i = self.marker_id("Marker 1")
        self.view.handler_dict["plot_tool"](NO_TOOL_STR)
        self.rename(marker_id_i, "Peak")
        self.assertEqual(self.drawn_names(), ["Peak"])

    @covers("LLFR-00088")
    def test_rename_with_unknown_ids_asks_nothing(self) -> None:
        """Unknown plot or marker ids never open the dialog.

        Inputs: none.
        Outputs: none.
        """
        self.place(2.0)
        self.view.marker_name_answer_list = ["New"]
        rename_handler = self.view.handler_dict["marker_rename_handler"]
        rename_handler(999, self.marker_id("Marker 1"))
        rename_handler(self.plot_id_i, 999)
        self.assertEqual(self.view.marker_name_question_list, [])
        self.assertEqual(self.drawn_names(), ["Marker 1"])

    @covers("LLFR-00088")
    def test_plot_deleted_while_asking_is_safe(self) -> None:
        """A plot that disappears while the dialog is open is ignored.

        Inputs: none.
        Outputs: none.
        """
        self.place(2.0)
        marker_id_i = self.marker_id("Marker 1")

        def delete_plot_and_answer(current_name_str: str):
            """Delete the plot as if it happened during the dialog.

            Inputs:
                current_name_str: the name the dialog starts with.
            Outputs: the typed name.
            """
            self.view.handler_dict["plot_delete_handler"](self.plot_id_i)
            return "Late"

        self.view.ask_marker_name = delete_plot_and_answer
        self.view.handler_dict["marker_rename_handler"](self.plot_id_i,
                                                        marker_id_i)
        self.assertIsNone(self.workspace.find_plot(self.plot_id_i))


class DeleteMarkerTest(MarkerControllerTestCase):
    """Deleting a marker (LLFR-00091)."""

    @covers("LLFR-00091")
    def test_delete_removes_only_that_marker(self) -> None:
        """Delete removes the chosen marker and redraws the others.

        Inputs: none.
        Outputs: none.
        """
        self.place(1.0)
        self.place(2.0)
        self.place(3.0)
        self.view.handler_dict["marker_delete_handler"](
            self.plot_id_i, self.marker_id("Marker 2"))
        self.assertEqual(self.drawn_names(), ["Marker 1", "Marker 3"])
        self.assertEqual([marker.name_str
                          for marker in self.workspace.marker_list],
                         ["Marker 1", "Marker 3"])
        # The plot itself stays, with its curve.
        self.assertEqual(self.view.drawn_names(self.plot_id_i), ["s1"])

    @covers("LLFR-00091")
    def test_delete_works_with_any_tool(self) -> None:
        """The marker menu's Delete acts whatever plot tool is active.

        Inputs: none.
        Outputs: none.
        """
        self.place(1.0)
        self.view.handler_dict["plot_tool"](TIP_TOOL_STR)
        self.view.handler_dict["marker_delete_handler"](
            self.plot_id_i, self.marker_id("Marker 1"))
        self.assertEqual(self.drawn_markers(), [])

    @covers("LLFR-00091")
    def test_delete_with_unknown_ids_is_ignored(self) -> None:
        """Unknown ids, or a marker deleted twice, change nothing.

        Inputs: none.
        Outputs: none.
        """
        self.place(1.0)
        marker_id_i = self.marker_id("Marker 1")
        delete_handler = self.view.handler_dict["marker_delete_handler"]
        delete_handler(self.plot_id_i, marker_id_i)
        draw_count_i = self.draw_count()
        delete_handler(self.plot_id_i, marker_id_i)
        delete_handler(999, marker_id_i)
        delete_handler(self.plot_id_i, 999)
        self.assertEqual(self.draw_count(), draw_count_i)

    @covers("LLFR-00091", "LLFR-00015")
    def test_markers_are_cleared_on_file_replace(self) -> None:
        """Opening a new file closes the plots and their markers.

        Inputs: none.
        Outputs: none.
        """
        self.place(1.0)
        marker_id_i = self.marker_id("Marker 1")
        old_plot_id_i = self.plot_id_i
        self.file_controller.open(self.signal_file, True)
        self.assertIsNone(self.workspace.find_plot(old_plot_id_i))
        # Requests for the old plot are ignored.
        self.view.handler_dict["marker_delete_handler"](old_plot_id_i,
                                                        marker_id_i)
        self.place(1.0, old_plot_id_i)
        self.double_click("s1")
        new_plot_id_i = self.current_plot_ids()[0]
        self.assertEqual(self.view.marker_drawn_dict[new_plot_id_i], [])


class SharedMarkersTest(MarkerControllerTestCase):
    """Markers shown on every plot of every tab (LLFR-00205)."""

    def undo(self) -> None:
        """Run the Undo handler, as the Undo button does.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["undo"]()

    def marker_tuple_list(self) -> list:
        """Return the markers of the model as plain tuples.

        Inputs: none.
        Outputs: a list of (marker_id_i, name_str, time_s).
        """
        return [(marker.marker_id_i, marker.name_str, marker.time_s)
                for marker in self.workspace.marker_list]

    @covers("LLFR-00081", "LLFR-00205")
    def test_place_on_one_plot_shows_on_plots_of_other_tabs(self) -> None:
        """A click on plot A places one marker, shown on plot B too.

        Inputs: none.
        Outputs: none.
        """
        first_tab_id_i = self.view.current_tab_id()
        other_plot_id_i = self.add_plot_in_new_tab("s2")
        self.view.set_current_tab(first_tab_id_i)
        self.place(4.0)
        self.assertEqual(len(self.workspace.marker_list), 1)
        expected_list = self.marker_tuple_list()
        self.assertEqual(self.view.marker_drawn_dict[self.plot_id_i],
                         expected_list)
        self.assertEqual(self.view.marker_drawn_dict[other_plot_id_i],
                         expected_list)
        # Placing from the other tab's plot shows it on the first one.
        self.place(6.0, other_plot_id_i)
        self.assertEqual(self.marker_names_of(self.plot_id_i),
                         ["Marker 1", "Marker 2"])

    @covers("LLFR-00205", "LLFR-00084", "LLFR-00092")
    def test_new_plots_show_the_existing_markers(self) -> None:
        """Plots created after the markers, in any tab, draw them.

        Inputs: none.
        Outputs: none.
        """
        self.place(1.0)
        self.place(2.0)
        expected_list = self.marker_tuple_list()
        new_tab_plot_id_i = self.add_plot_in_new_tab("s1")
        self.assertEqual(self.view.marker_drawn_dict[new_tab_plot_id_i],
                         expected_list)
        self.double_click("s2")
        second_plot_id_i = self.current_plot_ids()[1]
        self.assertEqual(self.view.marker_drawn_dict[second_plot_id_i],
                         expected_list)

    @covers("LLFR-00088", "LLFR-00112", "LLFR-00205")
    def test_rename_on_one_plot_renames_everywhere(self) -> None:
        """A rename chosen on plot B changes the label on plot A.

        Inputs: none.
        Outputs: none.
        """
        self.place(1.0)
        other_plot_id_i = self.add_plot_in_new_tab("s2")
        self.view.marker_name_answer_list = ["Start"]
        self.view.handler_dict["marker_rename_handler"](
            other_plot_id_i, self.marker_id("Marker 1"))
        self.assertEqual(self.marker_names_of(self.plot_id_i), ["Start"])
        self.assertEqual(self.marker_names_of(other_plot_id_i), ["Start"])

    @covers("LLFR-00091", "LLFR-00205")
    def test_delete_on_one_plot_deletes_everywhere(self) -> None:
        """Delete chosen on plot B removes the marker from every plot.

        Inputs: none.
        Outputs: none.
        """
        self.place(1.0)
        self.place(2.0)
        other_plot_id_i = self.add_plot_in_new_tab("s2")
        self.view.handler_dict["marker_delete_handler"](
            other_plot_id_i, self.marker_id("Marker 1"))
        self.assertEqual(self.marker_names_of(self.plot_id_i),
                         ["Marker 2"])
        self.assertEqual(self.marker_names_of(other_plot_id_i),
                         ["Marker 2"])
        self.assertEqual([marker.name_str
                          for marker in self.workspace.marker_list],
                         ["Marker 2"])

    @covers("LLFR-00140", "LLFR-00205", "LLFR-00081", "LLFR-00086",
            "LLFR-00088", "LLFR-00091")
    def test_each_marker_action_is_one_undo_step(self) -> None:
        """Place, move, rename and delete are each one undo, everywhere.

        Inputs: none.
        Outputs: none.
        """
        other_plot_id_i = self.add_plot_in_new_tab("s2")
        depth_i = self.controller.undo_history.depth()
        self.place(1.0, other_plot_id_i)
        marker_id_i = self.marker_id("Marker 1")
        self.view.handler_dict["marker_move_handler"](self.plot_id_i,
                                                      marker_id_i, 3.0)
        self.view.marker_name_answer_list = ["Peak"]
        self.view.handler_dict["marker_rename_handler"](self.plot_id_i,
                                                        marker_id_i)
        self.view.handler_dict["marker_delete_handler"](other_plot_id_i,
                                                        marker_id_i)
        self.assertEqual(self.controller.undo_history.depth(),
                         depth_i + 4)
        expected_state_list = [[(marker_id_i, "Peak", 3.0)],
                               [(marker_id_i, "Marker 1", 3.0)],
                               [(marker_id_i, "Marker 1", 1.0)], []]
        for expected_list in expected_state_list:
            self.undo()
            self.assertEqual(self.marker_tuple_list(), expected_list)
            # The rebuilt views show the restored markers on every plot.
            for plot_id_i in (self.plot_id_i, other_plot_id_i):
                self.assertEqual(self.view.marker_drawn_dict[plot_id_i],
                                 expected_list)
        self.assertEqual(self.controller.undo_history.depth(), depth_i)

    @covers("LLFR-00111", "LLFR-00085")
    def test_undone_placement_does_not_free_its_number(self) -> None:
        """After undoing "Marker 2", the next marker is "Marker 3".

        Inputs: none.
        Outputs: none.
        """
        self.place(1.0)
        self.place(2.0)
        self.undo()
        self.assertEqual(self.drawn_names(), ["Marker 1"])
        self.place(3.0)
        self.assertEqual(self.drawn_names(), ["Marker 1", "Marker 3"])

    @covers("LLFR-00205", "LLFR-00049", "LLFR-00140")
    def test_deleting_the_last_plot_deletes_markers_undoably(self) -> None:
        """The last plot takes the markers along; undo brings both back.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s2")
        second_plot_id_i = self.current_plot_ids()[1]
        self.place(1.0)
        self.place(2.0)
        saved_list = self.marker_tuple_list()
        # Deleting a plot that is not the last one keeps the markers.
        self.view.handler_dict["plot_delete_handler"](second_plot_id_i)
        self.assertEqual(self.marker_tuple_list(), saved_list)
        depth_i = self.controller.undo_history.depth()
        self.view.handler_dict["plot_delete_handler"](self.plot_id_i)
        self.assertEqual(self.workspace.marker_list, [])
        # One undoable action for the plot and its markers.
        self.assertEqual(self.controller.undo_history.depth(), depth_i + 1)
        self.undo()
        self.assertIsNotNone(self.workspace.find_plot(self.plot_id_i))
        self.assertEqual(self.marker_tuple_list(), saved_list)
        self.assertEqual(self.view.marker_drawn_dict[self.plot_id_i],
                         saved_list)
        # LLFR-00111: the numbers are still not reused.
        self.place(3.0)
        self.assertEqual(self.drawn_names()[-1], "Marker 3")

    @covers("LLFR-00205", "LLFR-00051", "LLFR-00140")
    def test_removing_the_last_curve_deletes_markers_undoably(self) -> None:
        """Removing the last curve of the last plot deletes the markers.

        Inputs: none.
        Outputs: none.
        """
        self.place(1.0)
        saved_list = self.marker_tuple_list()
        self.view.handler_dict["curve_delete_handler"](self.plot_id_i, "s1")
        self.assertIsNone(self.workspace.find_plot(self.plot_id_i))
        self.assertEqual(self.workspace.marker_list, [])
        self.undo()
        self.assertEqual(self.marker_tuple_list(), saved_list)
        self.assertEqual(self.view.marker_drawn_dict[self.plot_id_i],
                         saved_list)

    @covers("LLFR-00205", "LLFR-00028", "LLFR-00140")
    def test_deleting_the_tab_of_the_last_plots_deletes_markers(self) -> None:
        """A tab delete that leaves no plot deletes the markers undoably.

        Inputs: none.
        Outputs: none.
        """
        first_tab_id_i = self.view.current_tab_id()
        self.place(1.0)
        saved_list = self.marker_tuple_list()
        empty_tab_plot_id_i = self.add_plot_in_new_tab("s2")
        second_tab_id_i = self.view.current_tab_id()
        # Deleting a tab while plots remain elsewhere keeps the markers.
        self.view.handler_dict["delete_tab"](second_tab_id_i)
        self.assertIsNone(self.workspace.find_plot(empty_tab_plot_id_i))
        self.assertEqual(self.marker_tuple_list(), saved_list)
        # Now the first tab holds the last plot: delete it from a new tab.
        self.view.handler_dict["add_tab"]()
        self.view.handler_dict["delete_tab"](first_tab_id_i)
        self.assertEqual(self.workspace.marker_list, [])
        self.undo()
        self.assertEqual(self.marker_tuple_list(), saved_list)
        self.assertEqual(self.view.marker_drawn_dict[self.plot_id_i],
                         saved_list)

    @covers("LLFR-00205", "LLFR-00085", "LLFR-00111", "LLFR-00015")
    def test_file_open_clears_markers_and_restarts_numbering(self) -> None:
        """A file open deletes the markers and restarts at "Marker 1".

        Inputs: none.
        Outputs: none.
        """
        self.place(1.0)
        self.place(2.0)
        self.file_controller.open(self.signal_file, True)
        self.assertEqual(self.workspace.marker_list, [])
        # LLFR-00142: not undoable; the history is empty.
        self.assertFalse(self.controller.undo_history.can_undo())
        self.view.handler_dict["plot_tool"](MARKER_TOOL_STR)
        self.double_click("s1")
        new_plot_id_i = self.current_plot_ids()[0]
        self.assertEqual(self.view.marker_drawn_dict[new_plot_id_i], [])
        self.place(1.5, new_plot_id_i)
        self.assertEqual(self.marker_names_of(new_plot_id_i), ["Marker 1"])


if __name__ == "__main__":
    unittest.main()
