"""Tests for the type names and menu title texts (issue #260).

Covers the one table of type names (LLFR-01255), the title text
`<type name>: <label>` (LLFR-00426, LLFR-01258, LLFR-01261,
LLFR-01262), the shortening of long labels (LLFR-00850, LLFR-01260,
LLFR-01257) and the label of a text note (LLFR-01256).
"""

import unittest

from tests.support import covers

from model import object_names


class TypeNameTest(unittest.TestCase):
    """The type names of the objects."""

    @covers("LLFR-01255", "HLFR-00096")
    def test_one_name_per_kind(self) -> None:
        """Every kind of the table has the name of LLFR-01255.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(object_names.TYPE_NAME_DICT, {
            "flag": "Flag", "area": "Vert. Area", "delta_x": "Delta X",
            "delta_y": "Delta Y", "arrow": "Arrow", "circle": "Circle",
            "rectangle": "Rectangle", "text_note": "Text",
            "data_tip": "Data Tip", "curve": "Curve", "plot": "Plot",
            "tab": "Tab", "signal": "Signal", "file": "File"})
        with self.assertRaises(KeyError):
            object_names.type_name("shape")

    @covers("LLFR-00426", "LLFR-01258", "LLFR-01261", "LLFR-01262",
            "HLFR-00096")
    def test_title_is_the_type_and_the_label(self) -> None:
        """`<type name>: <label>`, or the type name alone for a plot.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(object_names.menu_title_text("flag", "Marker 1"),
                         "Flag: Marker 1")
        self.assertEqual(object_names.menu_title_text("area", "Warm-up"),
                         "Vert. Area: Warm-up")
        self.assertEqual(object_names.menu_title_text("tab", "Tab 1"),
                         "Tab: Tab 1")
        self.assertEqual(object_names.menu_title_text("file", "file1: a.csv"),
                         "File: file1: a.csv")
        self.assertEqual(object_names.menu_title_text("plot"), "Plot")

    @covers("LLFR-00850", "LLFR-01260", "LLFR-01257", "HLFR-00096")
    def test_long_labels_are_shortened_in_the_middle(self) -> None:
        """A label of up to 40 characters is kept; a longer one becomes
        40 characters with "…" in the middle.

        Inputs: none.
        Outputs: none.
        """
        forty_str = "a" * 40
        self.assertEqual(object_names.shortened_label(forty_str), forty_str)
        self.assertFalse(object_names.is_label_shortened(forty_str))
        long_str = "start_" + "x" * 50 + "_end"
        short_str = object_names.shortened_label(long_str)
        self.assertEqual(len(short_str), 40)
        self.assertEqual(short_str.count("…"), 1)
        self.assertTrue(short_str.startswith("start_"))
        self.assertTrue(short_str.endswith("_end"))
        self.assertTrue(object_names.is_label_shortened(long_str))
        self.assertEqual(object_names.menu_title_text("signal", long_str),
                         "Signal: " + short_str)

    @covers("LLFR-01256", "HLFR-00096")
    def test_text_note_label(self) -> None:
        """The first word and "…", or the one word alone.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(object_names.text_note_label("Peak of the run"),
                         "Peak…")
        self.assertEqual(object_names.text_note_label("Peak"), "Peak")
        self.assertEqual(object_names.text_note_label("  two\nlines "),
                         "two…")
        self.assertEqual(object_names.text_note_label(""), "")


if __name__ == "__main__":
    unittest.main()
