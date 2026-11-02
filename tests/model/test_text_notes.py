"""Tests for the text notes of the workspace model (issue #130).

No Qt is needed: the notes are plain model data, kept per plot and in
the undo snapshots.
"""

import random
import unittest

from tests.support import covers

from model.layout_file import build_layout_dict, layout_text
from model.workspace import (
    FREQUENCY_PLOT_KIND_STR, TextNote, Workspace, text_note_text)


class TextNoteModelTestCase(unittest.TestCase):
    """Shared setup: a workspace with one time plot that draws s1."""

    def setUp(self) -> None:
        """Create the workspace and the plot.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace(random.Random(1))
        self.tab = self.workspace.tab_list[0]
        self.plot = self.workspace.add_plot(self.tab.tab_id_i)
        self.plot.add_curve("s1")


class CreateTextNoteTest(TextNoteModelTestCase):
    """Creating text notes (LLFR-00333, LLFR-00334, LLFR-00340)."""

    @covers("LLFR-00334", "LLFR-00340")
    def test_note_keeps_its_text_and_place(self) -> None:
        """A note keeps the trimmed text and the clicked values.

        Inputs: none.
        Outputs: none.
        """
        text_note = self.plot.add_text_note("  peak here ", 2.5, -1.25)
        self.assertEqual(text_note, TextNote("peak here", 2.5, -1.25))
        self.assertEqual(self.plot.text_note_list, [text_note])

    @covers("LLFR-00334")
    def test_blank_text_creates_nothing(self) -> None:
        """An empty text or one made only of spaces writes no note.

        Inputs: none.
        Outputs: none.
        """
        for text_str in ("", "   ", "\t "):
            self.assertIsNone(self.plot.add_text_note(text_str, 1.0, 1.0))
        self.assertEqual(self.plot.text_note_list, [])
        self.assertEqual(text_note_text("  a b  "), "a b")

    @covers("LLFR-00340")
    def test_any_number_of_notes_and_same_place(self) -> None:
        """A plot holds any number of notes, even at the same place.

        Inputs: none.
        Outputs: none.
        """
        for index_i in range(25):
            self.plot.add_text_note(f"note {index_i}", 1.0, 1.0)
        self.assertEqual(len(self.plot.text_note_list), 25)
        self.assertEqual(self.plot.text_note_list[-1].text_str, "note 24")

    @covers("LLFR-00333")
    def test_place_must_be_finite(self) -> None:
        """A place that is not a finite number is refused.

        Inputs: none.
        Outputs: none.
        """
        for place_tuple in ((float("nan"), 1.0), (1.0, float("inf"))):
            with self.assertRaises(ValueError):
                self.plot.add_text_note("x", *place_tuple)
        self.assertEqual(self.plot.text_note_list, [])

    @covers("LLFR-00333", "LLFR-00340")
    def test_note_on_a_frequency_plot(self) -> None:
        """A frequency plot holds notes too, at a frequency in Hz.

        Inputs: none.
        Outputs: none.
        """
        frequency_plot = self.workspace.add_plot(
            self.tab.tab_id_i, FREQUENCY_PLOT_KIND_STR)
        frequency_plot.add_curve("fft_s1")
        frequency_plot.add_text_note("50 Hz line", 50.0, 0.2)
        self.assertEqual(frequency_plot.text_note_list[0].time_s, 50.0)
        # LLFR-00340: the note belongs to that plot only.
        self.assertEqual(self.plot.text_note_list, [])


class ChangeTextNoteTest(TextNoteModelTestCase):
    """Editing, moving and deleting notes (LLFR-00339, LLFR-00342,
    LLFR-00343)."""

    def setUp(self) -> None:
        """Add two notes to the plot.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.plot.add_text_note("first", 1.0, 2.0)
        self.plot.add_text_note("second", 3.0, 4.0)

    @covers("LLFR-00342")
    def test_edit_changes_the_text(self) -> None:
        """Edit gives the note the new trimmed text.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(self.plot.edit_text_note(1, " changed "))
        self.assertEqual(self.plot.text_note_list[1].text_str, "changed")
        self.assertEqual(self.plot.text_note_list[0].text_str, "first")

    @covers("LLFR-00342")
    def test_blank_edit_keeps_the_previous_text(self) -> None:
        """A blank text, the same text or a bad index change nothing.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(self.plot.edit_text_note(0, "   "))
        self.assertFalse(self.plot.edit_text_note(0, "first"))
        self.assertFalse(self.plot.edit_text_note(5, "other"))
        self.assertFalse(self.plot.edit_text_note(-1, "other"))
        self.assertEqual([note.text_str for note in
                          self.plot.text_note_list], ["first", "second"])

    @covers("LLFR-00339")
    def test_move_attaches_to_new_values(self) -> None:
        """A move attaches the note to the values of the drop place.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(self.plot.move_text_note(0, 7.5, -3.0))
        self.assertEqual(self.plot.text_note_list[0],
                         TextNote("first", 7.5, -3.0))
        # The same place, or an unknown note, is not a move.
        self.assertFalse(self.plot.move_text_note(0, 7.5, -3.0))
        self.assertFalse(self.plot.move_text_note(9, 1.0, 1.0))
        with self.assertRaises(ValueError):
            self.plot.move_text_note(0, float("nan"), 1.0)

    @covers("LLFR-00343")
    def test_delete_removes_only_that_note(self) -> None:
        """Delete removes the chosen note and keeps the others.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(self.plot.remove_text_note(0))
        self.assertEqual([note.text_str for note in
                          self.plot.text_note_list], ["second"])
        self.assertFalse(self.plot.remove_text_note(3))

    @covers("LLFR-00340")
    def test_removing_a_curve_keeps_the_notes(self) -> None:
        """Notes belong to the plot, not to a curve.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_curve("s2")
        self.plot.remove_curve("s1")
        self.assertEqual(len(self.plot.text_note_list), 2)

    @covers("LLFR-00340", "LLFR-00049")
    def test_notes_go_with_their_plot(self) -> None:
        """Deleting the plot removes its notes from the workspace.

        Inputs: none.
        Outputs: none.
        """
        self.workspace.delete_plot(self.plot.plot_id_i)
        self.assertEqual(
            [plot for tab in self.workspace.tab_list
             for plot in tab.plot_list], [])


class TextNoteUndoStateTest(TextNoteModelTestCase):
    """Text notes in the undo snapshots (LLFR-00138, LLFR-00140)."""

    @covers("LLFR-00140", "LLFR-00138")
    def test_each_change_is_seen_and_restored(self) -> None:
        """Every note change changes the state; restore brings it back.

        Inputs: none.
        Outputs: none.
        """
        snapshot = self.workspace.snapshot()
        self.plot.add_text_note("a", 1.0, 1.0)
        self.assertFalse(self.workspace.is_unchanged_since(snapshot))
        written_snapshot = self.workspace.snapshot()
        live_plot = self.workspace.find_plot(self.plot.plot_id_i)
        for change in (lambda: live_plot.edit_text_note(0, "b"),
                       lambda: live_plot.move_text_note(0, 2.0, 2.0),
                       lambda: live_plot.remove_text_note(0)):
            self.workspace.restore(written_snapshot)
            live_plot = self.workspace.find_plot(self.plot.plot_id_i)
            change()
            self.assertFalse(
                self.workspace.is_unchanged_since(written_snapshot))
        self.workspace.restore(snapshot)
        restored_plot = self.workspace.find_plot(self.plot.plot_id_i)
        self.assertEqual(restored_plot.text_note_list, [])
        self.workspace.restore(written_snapshot)
        restored_plot = self.workspace.find_plot(self.plot.plot_id_i)
        self.assertEqual(restored_plot.text_note_list,
                         [TextNote("a", 1.0, 1.0)])

    @covers("LLFR-00138")
    def test_snapshot_is_not_changed_by_later_edits(self) -> None:
        """A snapshot shares no note with the live workspace.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_text_note("a", 1.0, 1.0)
        snapshot = self.workspace.snapshot()
        self.plot.edit_text_note(0, "b")
        self.workspace.restore(snapshot)
        restored_plot = self.workspace.find_plot(self.plot.plot_id_i)
        self.assertEqual(restored_plot.text_note_list[0].text_str, "a")


class TextNoteLayoutTest(TextNoteModelTestCase):
    """Text notes are not saved in layout files (LLFR-00226)."""

    @covers("LLFR-00226")
    def test_layout_file_holds_no_text_note(self) -> None:
        """Neither the text nor a key for the notes is written.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_text_note("secret remark", 1.234567, 2.0)
        layout_dict = build_layout_dict(
            self.workspace, self.tab.tab_id_i, (0.0, 10.0), False)
        text_str = layout_text(layout_dict)
        self.assertNotIn("secret remark", text_str)
        self.assertNotIn("note", text_str.lower())
        self.assertNotIn("1.234567", text_str)


if __name__ == "__main__":
    unittest.main()
