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
        """Return how many times the plot of the setup was drawn.

        Inputs: none.
        Outputs: the number of draw_plot calls for that plot.
        """
        return self.view.call_list.count(("draw_plot", self.plot_id_i))


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

    @covers("LLFR-00085")
    def test_numbers_count_per_plot(self) -> None:
        """A second plot starts its own count at "Marker 1".

        Inputs: none.
        Outputs: none.
        """
        self.place(1.0)
        self.place(2.0)
        self.double_click("s2")
        second_plot_id_i = self.current_plot_ids()[1]
        self.place(3.0, second_plot_id_i)
        self.assertEqual(
            [marker_tuple[1] for marker_tuple
             in self.view.marker_drawn_dict[second_plot_id_i]],
            ["Marker 1"])
        self.assertEqual(self.drawn_names(), ["Marker 1", "Marker 2"])

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
                self.assertEqual(self.plot.marker_list, [])

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
        self.assertEqual(self.plot.marker_list, [])
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
        self.assertEqual(self.plot.find_marker(marker_id_i).time_s, 6.5)
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
        self.assertEqual(self.plot.find_marker(marker_id_i).time_s, 2.0)

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
        self.assertEqual(self.plot.find_marker(marker_id_i).time_s, 2.0)

    @covers("LLFR-00086")
    def test_marker_of_another_plot_is_not_moved(self) -> None:
        """A marker id is only valid in its own plot.

        Inputs: none.
        Outputs: none.
        """
        self.place(2.0)
        marker_id_i = self.marker_id("Marker 1")
        self.double_click("s2")
        second_plot_id_i = self.current_plot_ids()[1]
        self.view.handler_dict["marker_move_handler"](second_plot_id_i,
                                                      marker_id_i, 5.0)
        self.assertEqual(self.plot.find_marker(marker_id_i).time_s, 2.0)
        self.assertEqual(self.view.marker_drawn_dict[second_plot_id_i], [])


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
                self.assertEqual(self.plot.find_marker(marker_id_i).name_str,
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
                          for marker in self.plot.marker_list],
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


if __name__ == "__main__":
    unittest.main()
