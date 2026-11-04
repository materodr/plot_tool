"""Tests for the names of delta markers and arrows in the plot
controller (issue #183, Part A).

The fake view and the setup of tests.controller.test_plot_controller
are reused: a real Workspace, a SignalFile built in the test and a view
that records every call (no Qt needed). Signal "s<k>" has the values
k * Time, with Time = 0, 1, ..., 10 s.

Covers the default names of new delta markers and arrows (LLFR-00428,
LLFR-00851, LLFR-00852, LLFR-00438, LLFR-00872), their rename through
"Rename" or a double-click on the label (LLFR-00429, LLFR-00853 to
LLFR-00856, LLFR-00439, LLFR-00873 to LLFR-00876), the undo of a rename
(LLFR-00140) and the names given to the view for the labels (LLFR-00427,
LLFR-00436).
"""

import unittest

from tests.support import covers

from controller.plot_tools import (
    ARROW_TOOL_STR, DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR)
from model.curve_colors import MARKER_COLOR_STR
from tests.controller.test_plot_controller import (
    PlotControllerTestCase, make_signal_file)


class LabelControllerTestCase(PlotControllerTestCase):
    """Shared setup: one plot with s1 and s2."""

    def setUp(self) -> None:
        """Open the file and plot s1 and s2 in one plot.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.double_click("s1")
        self.plot_id_i = self.current_plot_ids()[0]
        self.drop(self.plot_id_i, "s2")
        self.plot = self.workspace.find_plot(self.plot_id_i)

    def handler(self, name_str: str):
        """Return a handler set by the controller.

        Inputs:
            name_str: the handler name.
        Outputs: the function.
        """
        return self.view.handler_dict[name_str]

    def set_tool(self, tool_str: str) -> None:
        """Report a plot tool change, as the top panel does.

        Inputs:
            tool_str: the new tool name.
        Outputs: none.
        """
        self.handler("plot_tool")(tool_str)

    def pick(self, signal_name_str: str, time_s: float) -> None:
        """Report a left click on a curve sample with a delta tool.

        Inputs:
            signal_name_str: the clicked curve.
            time_s: time of the sample; its value is read from the file.
        Outputs: none.
        """
        value_f = float(self.signal_file.signal_array(signal_name_str)[
            int(time_s)])
        self.handler("delta_point_pick_handler")(
            self.plot_id_i, signal_name_str, time_s, value_f)

    def place_delta(self, tool_str: str = DELTA_X_TOOL_STR,
                    first_time_s: float = 1.0,
                    second_time_s: float = 4.0) -> None:
        """Place one delta marker on s1 and s2.

        Inputs:
            tool_str: DELTA_X_TOOL_STR or DELTA_Y_TOOL_STR.
            first_time_s: time of the first point, on s1.
            second_time_s: time of the second point, on s2.
        Outputs: none.
        """
        self.set_tool(tool_str)
        self.pick("s1", first_time_s)
        self.pick("s2", second_time_s)

    def delta_names(self) -> list:
        """Return the names of the delta markers last drawn in the plot.

        Inputs: none.
        Outputs: the name of each drawn tuple, in placing order.
        """
        return [drawn_tuple[6] for drawn_tuple
                in self.view.delta_drawn_dict.get(self.plot_id_i, [])]

    def create_arrow(self, end_tuple: tuple = (1.0, 2.0, 3.0, 4.0),
                     plot_id_i: int = None) -> None:
        """Report an arrow drawn with the Arrow tool.

        Inputs:
            end_tuple: (start_time_s, start_value_f, end_time_s,
                end_value_f).
            plot_id_i: the plot (default: the plot of the setup).
        Outputs: none.
        """
        if plot_id_i is None:
            plot_id_i = self.plot_id_i
        self.handler("arrow_create_handler")(plot_id_i, *end_tuple)

    def arrow_names(self, plot_id_i: int = None) -> list:
        """Return the names of the arrows last drawn in a plot.

        Inputs:
            plot_id_i: the plot (default: the plot of the setup).
        Outputs: the name of each drawn tuple, in drawing order.
        """
        if plot_id_i is None:
            plot_id_i = self.plot_id_i
        return [drawn_tuple[5] for drawn_tuple
                in self.view.arrow_drawn_dict.get(plot_id_i, [])]

    def undo(self) -> None:
        """Run the Undo handler.

        Inputs: none.
        Outputs: none.
        """
        self.handler("undo")()

    def redo(self) -> None:
        """Run the Redo handler.

        Inputs: none.
        Outputs: none.
        """
        self.handler("redo")()

    def message_names(self) -> list:
        """Return the names of the message boxes the view was asked for.

        Inputs: none.
        Outputs: the recorded calls whose name starts with "show_".
        """
        return [call_tuple[0] for call_tuple in self.view.call_list
                if call_tuple[0].startswith("show_")]


class DeltaMarkerNameTest(LabelControllerTestCase):
    """Default names of new delta markers (LLFR-00428, LLFR-00851,
    LLFR-00852)."""

    @covers("LLFR-00428", "LLFR-00427", "HLFR-00097")
    def test_new_markers_are_numbered_by_kind(self) -> None:
        """Delta X and Delta Y markers count separately from 1, and the
        view gets each name for the label.

        Inputs: none.
        Outputs: none.
        """
        self.place_delta(DELTA_X_TOOL_STR, 1.0, 4.0)
        self.place_delta(DELTA_X_TOOL_STR, 2.0, 5.0)
        self.place_delta(DELTA_Y_TOOL_STR, 3.0, 6.0)
        self.assertEqual(self.delta_names(),
                         ["Delta X 1", "Delta X 2", "Delta Y 1"])
        self.assertEqual([delta_marker.name_str for delta_marker
                          in self.plot.delta_marker_list],
                         ["Delta X 1", "Delta X 2", "Delta Y 1"])

    @covers("LLFR-00428", "LLFR-00851", "HLFR-00097")
    def test_numbers_not_reused_after_delete_or_undo(self) -> None:
        """A deleted or undone marker's number stays used up; a new
        file restarts the numbering at 1.

        Inputs: none.
        Outputs: none.
        """
        self.place_delta()
        delta_id_i = self.plot.delta_marker_list[0].delta_marker_id_i
        self.handler("delta_marker_delete_handler")(self.plot_id_i,
                                                    delta_id_i)
        self.place_delta()
        self.assertEqual(self.delta_names(), ["Delta X 2"])
        self.undo()
        self.assertEqual(self.delta_names(), [])
        self.place_delta()
        self.assertEqual(self.delta_names(), ["Delta X 3"])
        # LLFR-00428, LLFR-00851: closing and opening files never
        # restarts the numbering.
        self.close_all_files()
        self.file_controller.open(make_signal_file(), None)
        self.double_click("s1")
        self.plot_id_i = self.current_plot_ids()[0]
        self.drop(self.plot_id_i, "s2")
        self.plot = self.workspace.find_plot(self.plot_id_i)
        self.place_delta()
        self.assertEqual(self.delta_names(), ["Delta X 4"])

    @covers("LLFR-00852", "LLFR-00428", "HLFR-00097")
    def test_name_in_use_is_skipped(self) -> None:
        """A number whose name a marker of that kind already has, in any
        plot, is skipped; the other kind does not count.

        Inputs: none.
        Outputs: none.
        """
        self.place_delta(DELTA_Y_TOOL_STR)
        delta_id_i = self.plot.delta_marker_list[0].delta_marker_id_i
        self.view.delta_name_answer_list.append("Delta X 2")
        self.handler("delta_marker_rename_handler")(self.plot_id_i,
                                                    delta_id_i)
        self.place_delta(DELTA_X_TOOL_STR)
        # "Delta X 2" is a Delta Y marker's name: it does not count.
        self.assertEqual(self.delta_names(), ["Delta X 2", "Delta X 1"])
        self.place_delta(DELTA_Y_TOOL_STR)
        self.assertEqual(self.delta_names()[-1], "Delta Y 2")
        x_marker = self.plot.delta_marker_list[1]
        self.view.delta_name_answer_list.append("Delta X 2")
        self.handler("delta_marker_rename_handler")(
            self.plot_id_i, x_marker.delta_marker_id_i)
        self.view.delta_name_answer_list.append("Delta X 3")
        self.handler("delta_marker_rename_handler")(
            self.plot_id_i,
            self.plot.delta_marker_list[0].delta_marker_id_i)
        # The Delta Y marker is now "Delta X 3"; the Delta X marker is
        # "Delta X 2": the next Delta X skips 2 (in use by its kind).
        self.place_delta(DELTA_X_TOOL_STR)
        self.assertEqual(self.delta_names()[-1], "Delta X 3")


class DeltaMarkerRenameTest(LabelControllerTestCase):
    """Renaming a delta marker (LLFR-00429, LLFR-00853 to LLFR-00856)."""

    def setUp(self) -> None:
        """Place one Delta X marker.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.place_delta()
        self.delta_marker = self.plot.delta_marker_list[0]

    def rename(self) -> None:
        """Ask for the rename of the delta marker of the setup.

        Inputs: none.
        Outputs: none.
        """
        self.handler("delta_marker_rename_handler")(
            self.plot_id_i, self.delta_marker.delta_marker_id_i)

    @covers("LLFR-00429", "LLFR-00853", "LLFR-00856", "LLFR-00140",
            "HLFR-00110", "HLFR-00097")
    def test_rename_shows_the_name_and_is_undoable(self) -> None:
        """The dialog starts from the name; the typed name, without its
        spaces, is drawn; the points, value and color stay; undo and
        redo bring the names back.

        Inputs: none.
        Outputs: none.
        """
        drawn_before_tuple = self.view.delta_drawn_dict[self.plot_id_i][0]
        self.view.delta_name_answer_list.append("  Lap time ")
        self.rename()
        self.assertEqual(self.view.delta_name_question_list,
                         ["Delta X 1"])
        self.assertEqual(self.delta_names(), ["Lap time"])
        drawn_tuple = self.view.delta_drawn_dict[self.plot_id_i][0]
        self.assertEqual(drawn_tuple[:6], drawn_before_tuple[:6])
        self.assertEqual(drawn_tuple[5], MARKER_COLOR_STR)
        self.undo()
        self.assertEqual(self.delta_names(), ["Delta X 1"])
        self.redo()
        self.assertEqual(self.delta_names(), ["Lap time"])

    @covers("LLFR-00854", "LLFR-00855", "HLFR-00110")
    def test_blank_name_keeps_the_name_without_a_message(self) -> None:
        """An empty or blank name, or a cancelled dialog, keeps the name,
        shows no message and records nothing.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.controller.undo_history.depth()
        for answer in ("", "   ", None):
            with self.subTest(answer=answer):
                self.view.delta_name_answer_list[:] = (
                    [] if answer is None else [answer])
                self.rename()
                self.assertEqual(self.delta_marker.name_str, "Delta X 1")
        self.assertEqual(self.message_names(), [])
        self.assertEqual(self.controller.undo_history.depth(), depth_i)

    @covers("LLFR-00429", "HLFR-00110")
    def test_unknown_marker_or_plot_asks_nothing(self) -> None:
        """A deleted marker or an unknown plot opens no dialog.

        Inputs: none.
        Outputs: none.
        """
        self.handler("delta_marker_rename_handler")(self.plot_id_i, 999)
        self.handler("delta_marker_rename_handler")(
            999, self.delta_marker.delta_marker_id_i)
        self.assertEqual(self.view.delta_name_question_list, [])


class ArrowNameTest(LabelControllerTestCase):
    """Default names of new arrows (LLFR-00438, LLFR-00872)."""

    def setUp(self) -> None:
        """Activate the Arrow tool.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.set_tool(ARROW_TOOL_STR)

    @covers("LLFR-00438", "LLFR-00436", "HLFR-00100")
    def test_arrows_are_numbered_in_any_plot(self) -> None:
        """"Arrow N" counts across all plots, and the view gets each
        name for the label.

        Inputs: none.
        Outputs: none.
        """
        self.create_arrow()
        self.double_click("s3")
        second_plot_id_i = self.current_plot_ids()[1]
        self.create_arrow(plot_id_i=second_plot_id_i)
        self.create_arrow()
        self.assertEqual(self.arrow_names(), ["Arrow 1", "Arrow 3"])
        self.assertEqual(self.arrow_names(second_plot_id_i), ["Arrow 2"])

    @covers("LLFR-00438", "LLFR-00872", "HLFR-00100")
    def test_numbers_not_reused_after_delete_or_undo(self) -> None:
        """A deleted or undone arrow's number stays used up; an arrow
        that is not drawn uses up none; a new file restarts at 1.

        Inputs: none.
        Outputs: none.
        """
        self.create_arrow()
        self.handler("arrow_delete_handler")(self.plot_id_i, 0)
        self.create_arrow()
        self.undo()
        # Two equal ends draw nothing and use up no number.
        self.create_arrow((1.0, 1.0, 1.0, 1.0))
        self.create_arrow()
        self.assertEqual(self.arrow_names(), ["Arrow 3"])
        # LLFR-00438, LLFR-00872: closing and opening files never
        # restarts the numbering.
        self.close_all_files()
        self.file_controller.open(make_signal_file(), None)
        self.double_click("s1")
        self.plot_id_i = self.current_plot_ids()[0]
        self.create_arrow()
        self.assertEqual(self.arrow_names(), ["Arrow 4"])


class ArrowRenameTest(LabelControllerTestCase):
    """Renaming an arrow (LLFR-00439, LLFR-00873 to LLFR-00876)."""

    def setUp(self) -> None:
        """Draw one arrow.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.set_tool(ARROW_TOOL_STR)
        self.create_arrow()

    def rename(self, arrow_index_i: int = 0) -> None:
        """Ask for the rename of an arrow.

        Inputs:
            arrow_index_i: index of the arrow in the plot.
        Outputs: none.
        """
        self.handler("arrow_rename_handler")(self.plot_id_i, arrow_index_i)

    @covers("LLFR-00439", "LLFR-00873", "LLFR-00876", "LLFR-00140",
            "HLFR-00111", "HLFR-00100")
    def test_rename_shows_the_name_and_is_undoable(self) -> None:
        """The dialog starts from the name; the typed name is drawn; the
        ends and the color stay; undo and redo bring the names back.

        Inputs: none.
        Outputs: none.
        """
        self.view.arrow_name_answer_list.append(" Peak ")
        self.rename()
        self.assertEqual(self.view.arrow_name_question_list, ["Arrow 1"])
        self.assertEqual(self.arrow_names(), ["Peak"])
        self.assertEqual(self.view.arrow_drawn_dict[self.plot_id_i][0][:5],
                         (1.0, 2.0, 3.0, 4.0, MARKER_COLOR_STR))
        self.undo()
        self.assertEqual(self.arrow_names(), ["Arrow 1"])
        self.redo()
        self.assertEqual(self.arrow_names(), ["Peak"])

    @covers("LLFR-00874", "LLFR-00875", "HLFR-00111")
    def test_blank_name_keeps_the_name_without_a_message(self) -> None:
        """An empty or blank name, a cancelled dialog or an unknown
        arrow keeps the name, shows no message and records nothing.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.controller.undo_history.depth()
        for answer in ("", "  ", None):
            with self.subTest(answer=answer):
                self.view.arrow_name_answer_list[:] = (
                    [] if answer is None else [answer])
                self.rename()
        self.rename(5)
        self.assertEqual(self.arrow_names(), ["Arrow 1"])
        self.assertEqual(self.message_names(), [])
        self.assertEqual(self.controller.undo_history.depth(), depth_i)
        self.assertEqual(len(self.view.arrow_name_question_list), 3)


if __name__ == "__main__":
    unittest.main()
