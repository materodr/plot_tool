"""Tests of the text of the boxes that list several items.

The shared helper of src/model/message_lists.py numbers the items
(LLFR-00980), leaves a blank line between them (LLFR-00982), keeps the
sentence above the list (LLFR-00983), leaves one item alone unnumbered
(LLFR-00984), indents the sub-lines of an item (LLFR-00985), aligns the
numbers (LLFR-00986) and numbers the load report under each heading
(LLFR-00987, LLFR-00988, LLFR-00989). The boxes of LLFR-00981 that are
built in the model use it: the load report, the changed names and the
signals with values that are not finite numbers.
"""

import unittest

from tests.support import covers

from model import file_writer, layout_file
from model import message_lists
from model.message_lists import (
    FIGURE_SPACE_STR, PUNCTUATION_SPACE_STR, display_line_count,
    has_hanging_line_b, is_long_list_text, list_body_text, list_line_list,
    list_text, number_prefix, sections_text, sub_line_indent)


class ListTextTest(unittest.TestCase):
    """The format of one list, with or without a sentence above it."""

    @covers("LLFR-00980", "LLFR-00982")
    def test_two_items_are_numbered_one_blank_line_apart(self) -> None:
        """Two or more items get "1.", "2."... and one blank line.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(list_body_text(["first", "second"]),
                         "1. first\n\n2. second")
        self.assertEqual(list_body_text(["a", "b", "c"]),
                         "1. a\n\n2. b\n\n3. c")
        # LLFR-00982: exactly one blank line, never two.
        self.assertNotIn("\n\n\n", list_body_text(["a", "b", "c"]))

    @covers("LLFR-00984")
    def test_one_item_has_no_number(self) -> None:
        """One item alone is shown as it is; no item gives "".

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(list_body_text(["only one"]), "only one")
        self.assertEqual(list_text(["only one"], "Heading:"),
                         "Heading:\n\nonly one")
        self.assertEqual(list_body_text([]), "")
        # A line of its own that looks like a number stays as it is.
        self.assertEqual(list_body_text(["1. x"]), "1. x")

    @covers("LLFR-00983")
    def test_sentence_above_the_list(self) -> None:
        """The sentence comes first, then one blank line, then the list.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(list_text(["a", "b"], "Do you want to go on?"),
                         "Do you want to go on?\n\n1. a\n\n2. b")
        self.assertEqual(list_text(["a", "b"]), "1. a\n\n2. b")
        self.assertEqual(list_text([], "Only the sentence."),
                         "Only the sentence.")

    @covers("LLFR-00985")
    def test_sub_lines_stay_under_their_number(self) -> None:
        """The lines after the first are indented by the number's width.

        Inputs: none.
        Outputs: none.
        """
        text_str = list_body_text(["first\n  - detail", "second"])
        indent_str = PUNCTUATION_SPACE_STR + " "
        self.assertEqual(text_str, f"1. first\n{FIGURE_SPACE_STR}"
                         f"{indent_str}  - detail\n\n2. second")
        # LLFR-00985: the indent is as wide as "1. ": one digit, the
        # period and the space.
        self.assertEqual(len(sub_line_indent(1)), len(number_prefix(1, 1)))
        self.assertEqual(len(sub_line_indent(2)), len(number_prefix(10, 2)))
        # LLFR-00984: one item alone keeps its lines as they are.
        self.assertEqual(list_body_text(["a\nb"]), "a\nb")

    @covers("LLFR-00986")
    def test_numbers_are_aligned_from_ten_items(self) -> None:
        """With 10 items or more, the short numbers are padded on their
        left with figure spaces, so that every text starts at the same
        place.

        Inputs: none.
        Outputs: none.
        """
        item_list = [f"item {index_i}" for index_i in range(1, 12)]
        line_list = [line_str for line_str in
                     list_body_text(item_list).split("\n") if line_str]
        self.assertEqual(len(line_list), 11)
        self.assertEqual(line_list[0], FIGURE_SPACE_STR + "1. item 1")
        self.assertEqual(line_list[8], FIGURE_SPACE_STR + "9. item 9")
        self.assertEqual(line_list[9], "10. item 10")
        self.assertEqual(line_list[10], "11. item 11")
        # Every text starts after the same number of characters, and a
        # figure space is as wide as a digit.
        self.assertEqual({line_str.index("item") for line_str in line_list},
                         {4})
        # Below 10 items, no padding is needed.
        self.assertFalse(list_body_text(["a", "b"]).startswith(
            FIGURE_SPACE_STR))

    @covers("LLFR-00980", "LLFR-00984")
    def test_forced_numbering(self) -> None:
        """The caller can force the numbering of a short list.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(list_body_text(["a"], numbered_b=True), "1. a")
        self.assertEqual(list_body_text(["a", "b"], numbered_b=False),
                         "a\n\nb")


class SectionsTextTest(unittest.TestCase):
    """The load report numbers the items under each of its headings."""

    @covers("LLFR-00987", "LLFR-00988", "LLFR-00989", "LLFR-00983")
    def test_each_heading_starts_at_one(self) -> None:
        """Each heading has its own numbers, from 1, and one blank line
        separates the sections.

        Inputs: none.
        Outputs: none.
        """
        text_str = sections_text([("First:", ["a", "b"]), ("Empty:", []),
                                  ("Second:", ["c"])])
        # LLFR-00988: three items in all, so the lone "c" is "1.".
        self.assertEqual(text_str,
                         "First:\n\n1. a\n\n2. b\n\nSecond:\n\n1. c")
        self.assertNotIn("Empty:", text_str)

    @covers("LLFR-00988", "LLFR-00984")
    def test_one_item_in_all_has_no_number(self) -> None:
        """A report of one item in all has no number.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(sections_text([("First:", []),
                                        ("Second:", ["c"])]),
                         "Second:\n\nc")
        self.assertEqual(sections_text([]), "")


class ModelBoxTextTest(unittest.TestCase):
    """The boxes of LLFR-00981 whose text the model builds."""

    @covers("LLFR-00981", "LLFR-00987", "LLFR-00988", "LLFR-00989",
            "LLFR-00237")
    def test_load_report_format(self) -> None:
        """The load report: headings, numbered entries, blank lines.

        Inputs: none.
        Outputs: none.
        """
        report = layout_file.LayoutReport()
        report.add_missing_signal("file1_Gone")
        report.add_missing_signal("file1_Lost")
        report.add_renamed('Tab "Tab 1" → "Tab 2"')
        report.add_time_range("The time range was limited.")
        self.assertEqual(report.text(), "\n\n".join([
            layout_file.RENAMED_HEADING_STR,
            '1. Tab "Tab 1" → "Tab 2"',
            layout_file.MISSING_HEADING_STR, "1. file1_Gone",
            "2. file1_Lost",
            layout_file.TIME_RANGE_HEADING_STR,
            "1. The time range was limited."]))
        alone_report = layout_file.LayoutReport()
        alone_report.add_missing_signal("file1_Gone")
        self.assertEqual(alone_report.text(),
                         layout_file.MISSING_HEADING_STR + "\n\nfile1_Gone")

    @covers("LLFR-00981", "LLFR-00980", "LLFR-00982", "LLFR-00984",
            "LLFR-00404")
    def test_changed_names_format(self) -> None:
        """The changed names: numbered when two or more.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(file_writer.changed_names_text(
            [("file1_Speed", "Speed_1"), ("file2_Speed", "Speed_2")]),
            "1. file1_Speed → Speed_1\n\n2. file2_Speed → Speed_2")
        self.assertEqual(file_writer.changed_names_text(
            [("file1_t", "Time")]), "file1_t → Time")

    @covers("LLFR-00981", "LLFR-00980", "LLFR-00983", "LLFR-00984",
            "LLFR-00559")
    def test_non_finite_signals_format(self) -> None:
        """The signals with values that are not finite numbers: the
        sentence, a blank line and the signals.

        Inputs: none.
        Outputs: none.
        """
        heading_str = file_writer.NON_FINITE_REASON_STR
        self.assertEqual(file_writer.non_finite_reason(["big", "gap"]),
                         f"{heading_str}\n\n1. 'big'\n\n2. 'gap'")
        self.assertEqual(file_writer.non_finite_reason(["big"]),
                         f"{heading_str}\n\n'big'")


class ListLinesTest(unittest.TestCase):
    """The lines of a list text, read back for the hanging indents."""

    @covers("LLFR-01176", "LLFR-00980", "LLFR-00985", "LLFR-00986")
    def test_lines_split_into_indent_number_and_text(self) -> None:
        """Each line gives its blank indent, its number and its text.

        Inputs: none.
        Outputs: none.
        """
        item_list = ["first\nsecond line"] + [f"item {index_i}"
                                              for index_i in range(2, 11)]
        text_str = list_text(item_list, "Heading:")
        line_list = list_line_list(text_str)
        self.assertEqual(line_list[0], ("", "", "Heading:"))
        self.assertEqual(line_list[1], ("", "", ""))
        # LLFR-00986: " 1. " is padded by one figure space.
        self.assertEqual(line_list[2], (FIGURE_SPACE_STR, "1. ", "first"))
        # LLFR-00985: the sub-line is indented, with no number.
        self.assertEqual(line_list[3], (sub_line_indent(2), "",
                                        "second line"))
        self.assertEqual(line_list[-1], ("", "10. ", "item 10"))
        # The plain text is read back exactly.
        self.assertEqual("\n".join(
            indent_str + number_str + rest_str
            for indent_str, number_str, rest_str in line_list), text_str)

    @covers("LLFR-01176", "LLFR-01178", "LLFR-00985")
    def test_list_inside_an_item(self) -> None:
        """A numbered list inside an item keeps both indents.

        Inputs: none.
        Outputs: none.
        """
        inner_str = list_text(["'A' has 3 samples.", "'B' has 4 samples."],
                              "Different counts:")
        text_str = list_body_text([inner_str, "b.csv: gone."])
        line_list = list_line_list(text_str)
        self.assertEqual(line_list[0], ("", "1. ", "Different counts:"))
        # LLFR-00982: the blank line inside the item stays blank.
        self.assertEqual(line_list[1], ("", "", ""))
        self.assertEqual(line_list[2], (sub_line_indent(1), "1. ",
                                        "'A' has 3 samples."))
        self.assertEqual(line_list[4], (sub_line_indent(1), "2. ",
                                        "'B' has 4 samples."))
        self.assertEqual(line_list[6], ("", "2. ", "b.csv: gone."))

    @covers("LLFR-01176", "LLFR-00984")
    def test_hanging_lines_only_with_an_indent_or_number(self) -> None:
        """A text with no indented or numbered line has no hanging line.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(has_hanging_line_b("a.csv: could not be read."))
        self.assertFalse(has_hanging_line_b("One.\n\nTwo."))
        self.assertTrue(has_hanging_line_b(list_body_text(["a", "b"])))
        self.assertTrue(has_hanging_line_b("x\n" + PUNCTUATION_SPACE_STR
                                           + "y"))

    @covers("LLFR-01177")
    def test_long_text_rule(self) -> None:
        """More than 15 lines, a long line counting per 80 characters.

        Inputs: none.
        Outputs: none.
        """
        limit_i = message_lists.LONG_BOX_LINE_COUNT_I
        width_i = message_lists.LONG_LINE_CHARACTERS_I
        self.assertEqual(limit_i, 15)
        self.assertEqual(width_i, 80)
        self.assertEqual(display_line_count("a\n\nb"), 3)
        self.assertEqual(display_line_count("x" * width_i), 1)
        self.assertEqual(display_line_count("x" * (width_i + 1)), 2)
        fifteen_str = "\n".join(["line"] * limit_i)
        self.assertFalse(is_long_list_text(fifteen_str))
        self.assertTrue(is_long_list_text(fifteen_str + "\nline"))
        # Two items with a blank line between them: 8 items are 15
        # lines, 9 items are 17.
        self.assertFalse(is_long_list_text(list_body_text(["i"] * 8)))
        self.assertTrue(is_long_list_text(list_body_text(["i"] * 9)))
        # One long line of 15 * 80 + 1 characters.
        self.assertTrue(is_long_list_text("x" * (limit_i * width_i + 1)))
        self.assertFalse(is_long_list_text("x" * (limit_i * width_i)))


if __name__ == "__main__":
    unittest.main()
