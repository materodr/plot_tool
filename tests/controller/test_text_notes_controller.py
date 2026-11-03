"""Tests for the text note handlers of the plot controller (issue #130).

The fake view and the setup of tests.controller.test_plot_controller
are reused: a real Workspace, a SignalFile built in the test and a view
that records every call (no Qt needed). The layout tests reuse the setup
of tests.controller.test_layout_controller.
"""

import unittest

from tests.support import covers

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, TEXT_TOOL_STR, ZOOM_TOOL_STR)
from tests.controller.test_layout_controller import LayoutControllerTestCase
from tests.controller.test_plot_controller import PlotControllerTestCase


class TextNoteControllerTestCase(PlotControllerTestCase):
    """Shared setup: one plot with s1, Text tool active."""

    def setUp(self) -> None:
        """Open the file, plot s1 and activate the Text tool.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.double_click("s1")
        self.plot_id_i = self.current_plot_ids()[0]
        self.view.handler_dict["plot_tool"](TEXT_TOOL_STR)

    def create(self, text_str: str, time_s: float = 2.0,
               value_f: float = 3.0, plot_id_i: int = None) -> None:
        """Report a text confirmed in the text field.

        Inputs:
            text_str: the typed text.
            time_s: x value of the clicked point.
            value_f: y value of the clicked point.
            plot_id_i: the plot (default: the plot of the setup).
        Outputs: none.
        """
        if plot_id_i is None:
            plot_id_i = self.plot_id_i
        self.view.handler_dict["text_note_create_handler"](
            plot_id_i, text_str, time_s, value_f)

    def drawn(self, plot_id_i: int = None) -> list:
        """Return the notes last drawn in a plot.

        Inputs:
            plot_id_i: the plot (default: the plot of the setup).
        Outputs: the list of (text_str, time_s, value_f), without the
            size and colors (tests/controller/test_text_note_style.py).
        """
        if plot_id_i is None:
            plot_id_i = self.plot_id_i
        return [tuple(note_tuple[:3]) for note_tuple in
                self.view.text_note_drawn_dict.get(plot_id_i, [])]

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


class CreateTextNoteTest(TextNoteControllerTestCase):
    """Writing a note (LLFR-00333, LLFR-00334, LLFR-00340)."""

    @covers("LLFR-00334", "LLFR-00140")
    def test_confirmed_text_is_drawn(self) -> None:
        """A confirmed text becomes a note drawn at the clicked place.

        Inputs: none.
        Outputs: none.
        """
        self.create("Engine start", 2.0, 3.0)
        self.assertEqual(self.drawn(), [("Engine start", 2.0, 3.0)])
        # LLFR-00140: one more undo step.
        self.undo()
        self.assertEqual(self.drawn(), [])

    @covers("LLFR-00334")
    def test_blank_text_writes_nothing_silently(self) -> None:
        """An empty or blank text creates no note and no undo step.

        Inputs: none.
        Outputs: none.
        """
        call_count_i = len(self.view.call_list)
        depth_i = self.undo_depth()
        self.create("")
        self.create("    ")
        self.assertEqual(self.drawn(), [])
        self.assertEqual(self.undo_depth(), depth_i)
        # No message box (or any other call) was made.
        self.assertEqual(len(self.view.call_list), call_count_i)

    @covers("LLFR-00333")
    def test_tool_deactivated_while_typing_still_writes(self) -> None:
        """A text confirmed after the Text tool was deactivated counts.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["plot_tool"](NO_TOOL_STR)
        self.create("still written")
        self.view.handler_dict["plot_tool"](ZOOM_TOOL_STR)
        self.create("again")
        self.assertEqual([note[0] for note in self.drawn()],
                         ["still written", "again"])

    @covers("LLFR-00333")
    def test_unknown_plot_or_bad_place_is_ignored(self) -> None:
        """A note for a plot that is gone or at no place is not written.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.undo_depth()
        self.create("x", plot_id_i=999)
        self.create("x", float("nan"), 1.0)
        self.view.handler_dict["text_note_create_handler"](
            self.plot_id_i, "x", "not a number", 1.0)
        self.assertEqual(self.drawn(), [])
        self.assertEqual(self.undo_depth(), depth_i)

    @covers("LLFR-00340")
    def test_note_only_on_its_plot(self) -> None:
        """A note is drawn only on the plot where it was written.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s2")
        other_plot_id_i = self.current_plot_ids()[1]
        self.create("on the first plot")
        self.assertEqual(self.drawn(other_plot_id_i), [])
        self.assertEqual(len(self.drawn()), 1)
        # A redraw of the other plot does not bring the note there.
        self.drop(other_plot_id_i, "s3")
        self.assertEqual(self.drawn(other_plot_id_i), [])

    @covers("LLFR-00340")
    def test_any_number_of_notes(self) -> None:
        """A plot holds many notes, all drawn in writing order.

        Inputs: none.
        Outputs: none.
        """
        for index_i in range(12):
            self.create(f"n{index_i}", float(index_i), 1.0)
        self.assertEqual([note[0] for note in self.drawn()],
                         [f"n{index_i}" for index_i in range(12)])

    @covers("LLFR-00337")
    def test_redraw_of_the_plot_keeps_the_notes(self) -> None:
        """Adding a curve or a zoom keeps the notes at their values.

        Inputs: none.
        Outputs: none.
        """
        self.create("kept", 4.0, 5.0)
        self.drop(self.plot_id_i, "s2")
        self.view.handler_dict["time_range_handler"](self.plot_id_i, 3.0,
                                                     6.0)
        self.assertEqual(self.drawn(), [("kept", 4.0, 5.0)])


class ChangeTextNoteTest(TextNoteControllerTestCase):
    """Moving, editing and deleting a note (LLFR-00339, LLFR-00342,
    LLFR-00343)."""

    def setUp(self) -> None:
        """Write two notes.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.create("first", 1.0, 1.0)
        self.create("second", 2.0, 2.0)

    @covers("LLFR-00339")
    def test_move_with_any_tool(self) -> None:
        """A dropped note takes the values of the drop place, whatever
        tool is active.

        Inputs: none.
        Outputs: none.
        """
        for tool_str, place_tuple in ((NO_TOOL_STR, (5.0, 6.0)),
                                      (MARKER_TOOL_STR, (7.0, 8.0)),
                                      (ZOOM_TOOL_STR, (3.0, 1.5))):
            self.view.handler_dict["plot_tool"](tool_str)
            self.view.handler_dict["text_note_move_handler"](
                self.plot_id_i, 0, *place_tuple)
            self.assertEqual(self.drawn()[0], ("first",) + place_tuple)
        # The move placed no marker.
        self.assertEqual(self.workspace.marker_list, [])

    @covers("LLFR-00339", "LLFR-00140")
    def test_move_to_the_same_place_is_not_recorded(self) -> None:
        """A drop where the note already is changes nothing.

        Inputs: none.
        Outputs: none.
        """
        depth_i = len(self.controller.undo_history.saved_snapshot_list())
        self.view.handler_dict["text_note_move_handler"](
            self.plot_id_i, 1, 2.0, 2.0)
        self.view.handler_dict["text_note_move_handler"](
            self.plot_id_i, 9, 2.0, 2.0)
        self.assertEqual(
            len(self.controller.undo_history.saved_snapshot_list()),
            depth_i)
        self.assertEqual(self.drawn()[1], ("second", 2.0, 2.0))

    @covers("LLFR-00342")
    def test_edit_changes_the_text(self) -> None:
        """Edit gives the note the typed text.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["text_note_edit_handler"](
            self.plot_id_i, 1, "renamed")
        self.assertEqual(self.drawn()[1], ("renamed", 2.0, 2.0))

    @covers("LLFR-00342")
    def test_blank_edit_keeps_the_text_silently(self) -> None:
        """A blank text keeps the previous text, with no message.

        Inputs: none.
        Outputs: none.
        """
        call_count_i = len(self.view.call_list)
        depth_i = len(self.controller.undo_history.saved_snapshot_list())
        self.view.handler_dict["text_note_edit_handler"](
            self.plot_id_i, 0, "   ")
        self.assertEqual(self.drawn()[0], ("first", 1.0, 1.0))
        self.assertEqual(len(self.view.call_list), call_count_i)
        self.assertEqual(
            len(self.controller.undo_history.saved_snapshot_list()),
            depth_i)

    @covers("LLFR-00343")
    def test_delete_removes_the_note(self) -> None:
        """Delete removes the chosen note only.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["text_note_delete_handler"](self.plot_id_i,
                                                           0)
        self.assertEqual(self.drawn(), [("second", 2.0, 2.0)])
        # An unknown note changes nothing.
        self.view.handler_dict["text_note_delete_handler"](self.plot_id_i,
                                                           5)
        self.assertEqual(len(self.drawn()), 1)

    @covers("LLFR-00340", "LLFR-00049")
    def test_notes_removed_with_the_plot(self) -> None:
        """Deleting the plot removes its notes; undo brings them back.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["plot_delete_handler"](self.plot_id_i)
        self.assertEqual(self.current_plot_ids(), [])
        self.undo()
        plot = self.workspace.find_plot(self.plot_id_i)
        self.assertEqual([note.text_str for note in plot.text_note_list],
                         ["first", "second"])
        self.assertEqual(len(self.drawn()), 2)

    @covers("LLFR-00340", "LLFR-00051")
    def test_notes_removed_when_last_curve_goes(self) -> None:
        """Removing the last curve deletes the plot with its notes.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["curve_delete_handler"](self.plot_id_i, "s1")
        self.assertIsNone(self.workspace.find_plot(self.plot_id_i))


class TextNoteUndoRedoTest(TextNoteControllerTestCase):
    """Each note action is undoable and redoable (LLFR-00140,
    LLFR-00138, LLFR-00192)."""

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00192")
    def test_create_move_edit_delete_undo_and_redo(self) -> None:
        """Each action is one undo step, and redo reapplies it.

        Inputs: none.
        Outputs: none.
        """
        handler_dict = self.view.handler_dict
        state_list = [[]]
        self.create("a", 1.0, 1.0)
        state_list.append([("a", 1.0, 1.0)])
        handler_dict["text_note_move_handler"](self.plot_id_i, 0, 4.0, 2.0)
        state_list.append([("a", 4.0, 2.0)])
        handler_dict["text_note_edit_handler"](self.plot_id_i, 0, "b")
        state_list.append([("b", 4.0, 2.0)])
        handler_dict["text_note_delete_handler"](self.plot_id_i, 0)
        state_list.append([])
        for expected_list in reversed(state_list[:-1]):
            self.undo()
            self.assertEqual(self.drawn(), expected_list)
        for expected_list in state_list[1:]:
            self.redo()
            self.assertEqual(self.drawn(), expected_list)
        self.assertFalse(self.view.redo_enabled_b)

    @covers("LLFR-00193")
    def test_new_note_clears_redo(self) -> None:
        """Writing a note after an undo discards the undone actions.

        Inputs: none.
        Outputs: none.
        """
        self.create("a")
        self.undo()
        self.assertTrue(self.view.redo_enabled_b)
        self.create("b")
        self.assertFalse(self.view.redo_enabled_b)


class TextNoteLayoutTest(LayoutControllerTestCase):
    """Text notes and layout files (LLFR-00226, LLFR-00229)."""

    def write_note(self, text_str: str) -> int:
        """Write a note on the first plot of the first tab.

        Inputs:
            text_str: the note text.
        Outputs: the id of the plot.
        """
        plot_id_i = self.workspace.tab_list[0].plot_list[0].plot_id_i
        self.view.handler_dict["text_note_create_handler"](
            plot_id_i, text_str, 2.0, 1.0)
        return plot_id_i

    @covers("LLFR-00226")
    def test_saved_layout_holds_no_note(self) -> None:
        """The saved file does not hold the notes.

        Inputs: none.
        Outputs: none.
        """
        self.build_layout()
        self.write_note("my private remark")
        path_str = self.path("layout.json")
        self.save(path_str)
        with open(path_str, encoding="utf-8") as layout_file:
            text_str = layout_file.read()
        self.assertNotIn("my private remark", text_str)
        self.assertNotIn("note", text_str.lower())

    @covers("LLFR-00229", "LLFR-00226")
    def test_kept_tabs_keep_their_notes(self) -> None:
        """Loading a layout keeps the notes of the current tabs; the new
        tabs have none.

        Inputs: none.
        Outputs: none.
        """
        self.build_layout()
        path_str = self.path("layout.json")
        self.save(path_str)
        plot_id_i = self.write_note("kept note")
        self.load(path_str)
        kept_plot = self.workspace.find_plot(plot_id_i)
        self.assertEqual([note.text_str for note in kept_plot.text_note_list],
                         ["kept note"])
        self.assertEqual([tuple(note_tuple[:3]) for note_tuple in
                          self.view.text_note_drawn_dict[plot_id_i]],
                         [("kept note", 2.0, 1.0)])
        added_plot_list = [plot for tab in self.workspace.tab_list[1:]
                           for plot in tab.plot_list]
        self.assertTrue(added_plot_list)
        for plot in added_plot_list:
            self.assertEqual(plot.text_note_list, [])
            self.assertEqual(
                self.view.text_note_drawn_dict.get(plot.plot_id_i, []), [])


if __name__ == "__main__":
    unittest.main()
