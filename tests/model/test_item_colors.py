"""Tests for the colors of flags and the style of text notes in the model
(issue #152): HLFR-00086 to HLFR-00089.

No Qt needed: the colors and sizes are plain values of the workspace
model, and every change is part of the undo state.
"""

import random
import unittest

from tests.support import covers

from model.curve_colors import (
    MARKER_COLOR_STR, PALETTE_COLOR_TUPLE, hex_color_or_none)
from model.workspace import (
    DEFAULT_FLAG_COLOR_STR, DEFAULT_TEXT_NOTE_BORDER_COLOR_STR,
    DEFAULT_TEXT_NOTE_COLOR_STR,
    DEFAULT_TEXT_NOTE_SIZE_I, TEXT_NOTE_SIZE_TUPLE, Workspace,
    plot_state_tuple)


class HexColorTest(unittest.TestCase):
    """The "#rrggbb" check shared by the picker, the model and layouts."""

    @covers("LLFR-00388", "LLFR-00319", "LLFR-00393", "LLFR-00727",
            "LLFR-00810", "LLFR-00814")
    def test_six_hexadecimal_digits_in_any_case(self) -> None:
        """A "#rrggbb" text, in uppercase or lowercase, is kept in
        lowercase; every other value gives None.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(hex_color_or_none("#12AB34"), "#12ab34")
        self.assertEqual(hex_color_or_none("#ffffff"), "#ffffff")
        self.assertEqual(hex_color_or_none("#000000"), "#000000")
        for value in ("12ab34", "#12ab3", "#12ab345", "#12ab3g", "#12ab34 ",
                      " #12ab34", "Orange", "", None, 0x12AB34, 1.0,
                      ["#12ab34"], "#12ab34ff"):
            with self.subTest(value=value):
                self.assertIsNone(hex_color_or_none(value))


class WorkspaceTestCase(unittest.TestCase):
    """Shared setup: a workspace with two tabs, each with one plot."""

    def setUp(self) -> None:
        """Create the workspace, the plots and one flag.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace(random.Random(3))
        first_tab = self.workspace.tab_list[0]
        self.plot = self.workspace.add_plot(first_tab.tab_id_i)
        self.plot.add_curve("Speed")
        second_tab = self.workspace.add_tab()
        self.workspace.add_plot(second_tab.tab_id_i).add_curve("Speed")
        self.flag = self.workspace.add_marker(2.0)


class FlagColorModelTest(WorkspaceTestCase):
    """The color of a flag (HLFR-00089, LLFR-00083, LLFR-00392)."""

    @covers("LLFR-00083", "LLFR-00392")
    def test_new_flag_gets_the_reserved_marker_color(self) -> None:
        """A placed flag, and a flag of a layout without a usable color,
        gets the reserved marker color, which is not a curve color.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(DEFAULT_FLAG_COLOR_STR, MARKER_COLOR_STR)
        self.assertNotIn(DEFAULT_FLAG_COLOR_STR, PALETTE_COLOR_TUPLE)
        self.assertEqual(self.flag.color_str, DEFAULT_FLAG_COLOR_STR)
        self.assertEqual(self.workspace.add_named_marker(
            "Saved", 3.0).color_str, DEFAULT_FLAG_COLOR_STR)
        self.assertEqual(self.workspace.add_named_marker(
            "Odd", 4.0, "Blue").color_str, DEFAULT_FLAG_COLOR_STR)

    @covers("LLFR-00393", "LLFR-00392", "LLFR-00814")
    def test_flag_of_a_layout_keeps_its_color(self) -> None:
        """A flag added with a "#rrggbb" color keeps it, in lowercase.

        Inputs: none.
        Outputs: none.
        """
        flag = self.workspace.add_named_marker("Saved", 3.0, "#1F77B4")
        self.assertEqual(flag.color_str, "#1f77b4")
        self.assertEqual(self.workspace.marker_state_tuple()[-1],
                         (flag.marker_id_i, "Saved", 3.0, "#1f77b4"))

    @covers("LLFR-00392", "LLFR-00390", "LLFR-00140", "LLFR-00138",
            "LLFR-00205", "LLFR-00083", "LLFR-00664", "LLFR-00811")
    def test_color_change_is_part_of_the_undo_state(self) -> None:
        """Any "#rrggbb" color, a palette color included, changes the
        shared flag; the same color in any case, an unusable value or an
        unknown flag changes nothing; restoring a snapshot brings the
        color back.

        Inputs: none.
        Outputs: none.
        """
        flag_id_i = self.flag.marker_id_i
        snapshot = self.workspace.snapshot()
        self.assertFalse(self.workspace.set_marker_color(
            flag_id_i, DEFAULT_FLAG_COLOR_STR.upper()))
        self.assertFalse(self.workspace.set_marker_color(flag_id_i, "red"))
        self.assertFalse(self.workspace.set_marker_color(999, "#00ff00"))
        self.assertTrue(self.workspace.is_unchanged_since(snapshot))
        self.assertTrue(self.workspace.set_marker_color(
            flag_id_i, PALETTE_COLOR_TUPLE[0].upper()))
        self.assertEqual(self.flag.color_str, PALETTE_COLOR_TUPLE[0])
        self.assertFalse(self.workspace.is_unchanged_since(snapshot))
        self.assertEqual(self.workspace.state_tuple()[1][0][3],
                         PALETTE_COLOR_TUPLE[0])
        # Moving and renaming keep the color.
        self.workspace.move_marker(flag_id_i, 5.0)
        self.workspace.rename_marker(flag_id_i, "Peak")
        self.assertEqual(self.workspace.find_marker(flag_id_i).color_str,
                         PALETTE_COLOR_TUPLE[0])
        self.workspace.restore(snapshot)
        self.assertEqual(self.workspace.find_marker(flag_id_i).color_str,
                         DEFAULT_FLAG_COLOR_STR)


class TextNoteStyleModelTest(WorkspaceTestCase):
    """Size and colors of a text note (HLFR-00086, HLFR-00087)."""

    def setUp(self) -> None:
        """Write one text note in the first plot.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.note = self.plot.add_text_note("Peak", 1.0, 2.0)

    @covers("LLFR-00336", "LLFR-00385", "LLFR-00660", "LLFR-00740",
            "LLFR-00803")
    def test_new_note_has_the_text_color_and_size_12(self) -> None:
        """A new note has #24303b as text color, the orange #ff8000 as
        border color and 12 points.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(DEFAULT_TEXT_NOTE_COLOR_STR, "#24303b")
        self.assertEqual(DEFAULT_TEXT_NOTE_BORDER_COLOR_STR, "#ff8000")
        self.assertEqual(DEFAULT_TEXT_NOTE_SIZE_I, 12)
        self.assertEqual(TEXT_NOTE_SIZE_TUPLE, (8, 10, 12, 16, 20, 24, 32))
        self.assertEqual((self.note.size_i, self.note.border_color_str,
                          self.note.text_color_str),
                         (12, "#ff8000", "#24303b"))

    @covers("LLFR-00385", "LLFR-00386", "LLFR-00140", "LLFR-00802",
            "LLFR-00806")
    def test_size_only_from_the_presets(self) -> None:
        """Each preset size is kept as chosen; another value, the same
        size or an unknown note changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(self.plot.set_text_note_size(0, 12))
        for size_i in TEXT_NOTE_SIZE_TUPLE:
            with self.subTest(size=size_i):
                # Each preset differs from the one chosen before it.
                self.assertTrue(self.plot.set_text_note_size(0, size_i))
                self.assertEqual(self.note.size_i, size_i)
        for size_value in (9, 0, -8, 12.5, "12", True, None):
            with self.subTest(size=size_value):
                self.assertFalse(self.plot.set_text_note_size(0, size_value))
        self.assertFalse(self.plot.set_text_note_size(0, 32))
        self.assertFalse(self.plot.set_text_note_size(5, 8))
        self.assertEqual(self.note.size_i, 32)

    @covers("LLFR-00387", "LLFR-00390", "LLFR-00811", "LLFR-00808")
    def test_border_and_text_colors_change_separately(self) -> None:
        """The border and the text take their own "#rrggbb" color; the
        same color or an unusable value changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(self.plot.set_text_note_border_color(0, "#FF8000"))
        self.assertFalse(self.plot.set_text_note_text_color(0, "#24303b"))
        self.assertFalse(self.plot.set_text_note_border_color(0, "blue"))
        self.assertFalse(self.plot.set_text_note_text_color(3, "#ff0000"))
        self.assertTrue(self.plot.set_text_note_border_color(0, "#FF0000"))
        self.assertEqual((self.note.border_color_str,
                          self.note.text_color_str), ("#ff0000", "#24303b"))
        self.assertTrue(self.plot.set_text_note_text_color(0, "#0000FF"))
        self.assertEqual((self.note.border_color_str,
                          self.note.text_color_str), ("#ff0000", "#0000ff"))

    @covers("LLFR-00342", "LLFR-00748")
    def test_edit_and_move_keep_the_size_and_colors(self) -> None:
        """Editing the text or moving the note keeps its style.

        Inputs: none.
        Outputs: none.
        """
        self.plot.set_text_note_size(0, 20)
        self.plot.set_text_note_border_color(0, "#ff0000")
        self.plot.set_text_note_text_color(0, "#00aa00")
        self.assertTrue(self.plot.edit_text_note(0, "New text"))
        self.assertTrue(self.plot.move_text_note(0, 3.0, 4.0))
        self.assertEqual((self.note.text_str, self.note.size_i,
                          self.note.border_color_str,
                          self.note.text_color_str),
                         ("New text", 20, "#ff0000", "#00aa00"))

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00385", "LLFR-00387")
    def test_style_is_part_of_the_undo_state(self) -> None:
        """A size, border color or text color change changes the plot's
        state, and restoring a snapshot brings the old style back.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(plot_state_tuple(self.plot)[5],
                         (("Peak", 1.0, 2.0, 12, "#ff8000", "#24303b"),))
        for change in (lambda: self.plot.set_text_note_size(0, 8),
                       lambda: self.plot.set_text_note_border_color(
                           0, "#ff0000"),
                       lambda: self.plot.set_text_note_text_color(
                           0, "#ff0000")):
            snapshot = self.workspace.snapshot()
            self.assertTrue(change())
            self.assertFalse(self.workspace.is_unchanged_since(snapshot))
            self.workspace.restore(snapshot)
            self.assertTrue(self.workspace.is_unchanged_since(snapshot))
            self.plot = self.workspace.find_plot(self.plot.plot_id_i)
            change()
            self.note = self.plot.text_note_list[0]
        self.assertEqual((self.note.size_i, self.note.border_color_str,
                          self.note.text_color_str),
                         (8, "#ff0000", "#ff0000"))


if __name__ == "__main__":
    unittest.main()
