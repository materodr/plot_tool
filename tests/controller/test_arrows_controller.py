"""Tests for the arrow handlers of the plot controller (issue #155).

The fake view and the setup of tests.controller.test_plot_controller
are reused: a real Workspace, a SignalFile built in the test and a view
that records every call (no Qt needed). Covers drawing an arrow
(LLFR-00372), moving, rotating and stretching it (LLFR-00376,
LLFR-00377), its color with the shared picker (LLFR-00379, LLFR-00389,
LLFR-00390), its deletion (LLFR-00380), the undo and redo of each action
(LLFR-00140, LLFR-00138, LLFR-00192), arrows on their own plot only
(LLFR-00375), on frequency plots, and the layout files (LLFR-00226).
"""

import unittest

from tests.support import covers

from controller.plot_tools import ARROW_TOOL_STR, NO_TOOL_STR
from tests.controller.test_plot_controller import PlotControllerTestCase
from model.workspace import FREQUENCY_PLOT_KIND_STR


class ArrowControllerTestCase(PlotControllerTestCase):
    """Shared setup: one plot with s1, Arrow tool active."""

    def setUp(self) -> None:
        """Open the file, plot s1 and activate the Arrow tool.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.double_click("s1")
        self.plot_id_i = self.current_plot_ids()[0]
        self.view.handler_dict["plot_tool"](ARROW_TOOL_STR)

    def handler(self, name_str: str):
        """Return a plot handler set by the controller.

        Inputs:
            name_str: the handler name, for example
                "arrow_create_handler".
        Outputs: the function.
        """
        return self.view.handler_dict[name_str]

    def create(self, end_tuple: tuple = (1.0, 2.0, 3.0, 4.0),
               plot_id_i: int = None) -> None:
        """Report an arrow drawn on a plot.

        Inputs:
            end_tuple: (start_time_s, start_value_f, end_time_s,
                end_value_f).
            plot_id_i: the plot (default: the plot of the setup).
        Outputs: none.
        """
        if plot_id_i is None:
            plot_id_i = self.plot_id_i
        self.handler("arrow_create_handler")(plot_id_i, *end_tuple)

    def drawn(self, plot_id_i: int = None) -> list:
        """Return the arrows last drawn in a plot.

        Inputs:
            plot_id_i: the plot (default: the plot of the setup).
        Outputs: the list of (start_time_s, start_value_f, end_time_s,
            end_value_f, color_str).
        """
        if plot_id_i is None:
            plot_id_i = self.plot_id_i
        return [tuple(arrow_tuple) for arrow_tuple in
                self.view.arrow_drawn_dict.get(plot_id_i, [])]

    def undo_depth(self) -> int:
        """Return how many states the undo history keeps.

        Inputs: none.
        Outputs: the number of saved snapshots.
        """
        return len(self.controller.undo_history.saved_snapshot_list())

    def undo(self) -> None:
        """Run the Undo handler.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["undo"]()

    def redo(self) -> None:
        """Run the Redo handler.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["redo"]()


class CreateArrowTest(ArrowControllerTestCase):
    """Drawing an arrow (LLFR-00372, LLFR-00373)."""

    @covers("LLFR-00372", "LLFR-00373", "LLFR-00140", "LLFR-00138",
            "LLFR-00192", "HLFR-00081")
    def test_create_is_drawn_and_undoable(self) -> None:
        """A drawn arrow is kept in the default color and drawn on its
        plot; Undo removes it and Redo brings it back.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.undo_depth()
        self.create((1.0, 2.0, 3.0, 4.0))
        self.assertEqual(self.drawn(), [(1.0, 2.0, 3.0, 4.0, "#ff8000")])
        self.assertEqual(self.undo_depth(), depth_i + 1)
        self.undo()
        self.assertEqual(self.drawn(), [])
        self.redo()
        self.assertEqual(self.drawn(), [(1.0, 2.0, 3.0, 4.0, "#ff8000")])

    @covers("LLFR-00372")
    def test_bad_requests_create_nothing(self) -> None:
        """An unknown plot, values that are not finite or two equal ends
        create nothing and record nothing.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.undo_depth()
        self.create((1.0, 2.0, 3.0, 4.0), plot_id_i=999)
        for end_tuple in ((float("nan"), 2.0, 3.0, 4.0),
                          (1.0, 2.0, 1.0, 2.0), ("x", 2.0, 3.0, 4.0)):
            self.create(end_tuple)
        self.assertEqual(self.drawn(), [])
        self.assertEqual(
            self.workspace.find_plot(self.plot_id_i).arrow_list, [])
        self.assertEqual(self.undo_depth(), depth_i)

    @covers("LLFR-00375", "LLFR-00049")
    def test_arrows_only_on_their_plot_and_removed_with_it(self) -> None:
        """An arrow is drawn only on its plot; deleting the plot removes
        it, and undoing the deletion brings it back.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s2")
        other_plot_id_i = self.current_plot_ids()[1]
        self.create((1.0, 2.0, 3.0, 4.0))
        self.assertEqual(self.drawn(other_plot_id_i), [])
        self.handler("plot_delete_handler")(self.plot_id_i)
        self.assertIsNone(self.workspace.find_plot(self.plot_id_i))
        self.assertEqual(
            self.workspace.find_plot(other_plot_id_i).arrow_list, [])
        self.undo()
        self.assertEqual(len(
            self.workspace.find_plot(self.plot_id_i).arrow_list), 1)
        self.assertEqual(self.drawn(), [(1.0, 2.0, 3.0, 4.0, "#ff8000")])

    @covers("LLFR-00371", "LLFR-00372", "LLFR-00256")
    def test_arrow_on_a_frequency_plot(self) -> None:
        """A frequency plot holds arrows like a time plot, with its x
        values in Hz.

        Inputs: none.
        Outputs: none.
        """
        frequency_plot = self.workspace.add_plot(
            self.first_tab_id(), FREQUENCY_PLOT_KIND_STR)
        self.create((5.0, 0.1, 20.0, 0.4),
                    plot_id_i=frequency_plot.plot_id_i)
        self.assertEqual(self.drawn(frequency_plot.plot_id_i),
                         [(5.0, 0.1, 20.0, 0.4, "#ff8000")])
        self.handler("arrow_change_handler")(
            frequency_plot.plot_id_i, 0, 6.0, 0.1, 30.0, 0.4)
        self.assertEqual(frequency_plot.arrow_list[0].end_time_s, 30.0)


class ChangeArrowTest(ArrowControllerTestCase):
    """Moving, rotating and stretching an arrow (LLFR-00376,
    LLFR-00377)."""

    def setUp(self) -> None:
        """Draw one arrow.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.create((1.0, 2.0, 3.0, 4.0))

    @covers("LLFR-00376", "LLFR-00377", "LLFR-00140", "LLFR-00138",
            "LLFR-00192", "LLFR-00382", "HLFR-00082", "HLFR-00083",
            "HLFR-00085")
    def test_change_is_undoable_with_the_tool_or_none(self) -> None:
        """New ends are kept and drawn as one undoable action, also with
        no tool active; Undo and Redo go back and forth.

        Inputs: none.
        Outputs: none.
        """
        for tool_str, end_tuple in (
                (ARROW_TOOL_STR, (2.0, 3.0, 4.0, 5.0)),
                (NO_TOOL_STR, (2.0, 3.0, 2.0, 8.0))):
            with self.subTest(tool=tool_str):
                self.view.handler_dict["plot_tool"](tool_str)
                before_list = self.drawn()
                depth_i = self.undo_depth()
                self.handler("arrow_change_handler")(
                    self.plot_id_i, 0, *end_tuple)
                self.assertEqual(self.drawn(),
                                 [end_tuple + ("#ff8000",)])
                self.assertEqual(self.undo_depth(), depth_i + 1)
                self.undo()
                self.assertEqual(self.drawn(), before_list)
                self.redo()
                self.assertEqual(self.drawn(),
                                 [end_tuple + ("#ff8000",)])

    @covers("LLFR-00376", "LLFR-00377", "LLFR-00140")
    def test_same_or_bad_ends_record_nothing(self) -> None:
        """The same ends, an unknown arrow or plot, or bad ends change
        nothing and add no undoable action; the view is told where the
        arrow is.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.undo_depth()
        change = self.handler("arrow_change_handler")
        change(self.plot_id_i, 0, 1.0, 2.0, 3.0, 4.0)
        change(self.plot_id_i, 5, 0.0, 0.0, 1.0, 1.0)
        change(999, 0, 0.0, 0.0, 1.0, 1.0)
        change(self.plot_id_i, 0, 1.0, 1.0, 1.0, 1.0)
        change(self.plot_id_i, 0, float("inf"), 1.0, 1.0, 2.0)
        self.assertEqual(self.undo_depth(), depth_i)
        self.assertEqual(self.drawn(), [(1.0, 2.0, 3.0, 4.0, "#ff8000")])


class ArrowColorAndDeleteTest(ArrowControllerTestCase):
    """The arrow menu (LLFR-00379, LLFR-00380)."""

    def setUp(self) -> None:
        """Draw two arrows.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.create((1.0, 2.0, 3.0, 4.0))
        self.create((5.0, 6.0, 7.0, 8.0))

    @covers("LLFR-00379", "LLFR-00388", "LLFR-00389", "LLFR-00390",
            "LLFR-00140", "LLFR-00138", "LLFR-00192", "HLFR-00088")
    def test_color_uses_the_shared_picker(self) -> None:
        """"Color" opens the picker at the arrow's color; a confirmed new
        color is drawn as one undoable action; Undo and Redo work.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.undo_depth()
        self.view.color_answer_list = ["#FF0080"]
        self.handler("arrow_color_handler")(self.plot_id_i, 1)
        self.assertEqual(self.view.color_question_list[-1], "#ff8000")
        self.assertEqual(self.drawn()[1][4], "#ff0080")
        self.assertEqual(self.drawn()[0][4], "#ff8000")
        self.assertEqual(self.undo_depth(), depth_i + 1)
        # The picker starts at the new color next time.
        self.handler("arrow_color_handler")(self.plot_id_i, 1)
        self.assertEqual(self.view.color_question_list[-1], "#ff0080")
        self.undo()
        self.assertEqual(self.drawn()[1][4], "#ff8000")
        self.redo()
        self.assertEqual(self.drawn()[1][4], "#ff0080")

    @covers("LLFR-00390", "LLFR-00140")
    def test_cancel_or_same_color_records_nothing(self) -> None:
        """A cancelled picker, the arrow's own color or an unknown arrow
        changes nothing and adds no undoable action.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.undo_depth()
        self.view.color_answer_list = []
        self.handler("arrow_color_handler")(self.plot_id_i, 0)
        self.view.color_answer_list = ["#FF8000"]
        self.handler("arrow_color_handler")(self.plot_id_i, 0)
        question_count_i = len(self.view.color_question_list)
        self.handler("arrow_color_handler")(self.plot_id_i, 7)
        self.handler("arrow_color_handler")(999, 0)
        self.assertEqual(len(self.view.color_question_list),
                         question_count_i)
        self.assertEqual(self.undo_depth(), depth_i)
        self.assertEqual(self.drawn()[0][4], "#ff8000")

    @covers("LLFR-00380", "LLFR-00140", "LLFR-00138", "LLFR-00192",
            "HLFR-00084")
    def test_delete_is_undoable(self) -> None:
        """"Delete" removes only that arrow as one undoable action; an
        unknown arrow removes nothing.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.undo_depth()
        self.handler("arrow_delete_handler")(self.plot_id_i, 0)
        self.assertEqual(self.drawn(), [(5.0, 6.0, 7.0, 8.0, "#ff8000")])
        self.assertEqual(self.undo_depth(), depth_i + 1)
        self.handler("arrow_delete_handler")(self.plot_id_i, 4)
        self.handler("arrow_delete_handler")(999, 0)
        self.assertEqual(self.undo_depth(), depth_i + 1)
        self.undo()
        self.assertEqual(len(self.drawn()), 2)
        self.redo()
        self.assertEqual(len(self.drawn()), 1)

    @covers("LLFR-00226")
    def test_layout_dict_holds_no_arrow(self) -> None:
        """The layout of the controller names no arrow.

        Inputs: none.
        Outputs: none.
        """
        layout_str = repr(self.controller.layout_dict()).lower()
        self.assertNotIn("arrow", layout_str)


if __name__ == "__main__":
    unittest.main()
