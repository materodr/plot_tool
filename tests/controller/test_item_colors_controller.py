"""Tests for the flag colors and the text note style handlers of the plot
controller (issue #152): HLFR-00086 to HLFR-00089.

The fake view of tests.controller.test_plot_controller answers the shared
color picker (``ask_color``) from ``color_answer_list`` and records the
color each question started at, so no Qt is needed.
"""

import unittest

from tests.support import covers

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, TEXT_TOOL_STR, ZOOM_TOOL_STR)
from tests.controller.test_plot_controller import PlotControllerTestCase

from model.workspace import (
    DEFAULT_FLAG_COLOR_STR, DEFAULT_TEXT_NOTE_BORDER_COLOR_STR,
    DEFAULT_TEXT_NOTE_COLOR_STR)


class ItemColorControllerTestCase(PlotControllerTestCase):
    """Shared setup: a plot of s1 in a first tab, a plot of s2 in a second
    tab, one flag and one text note in the first plot."""

    def setUp(self) -> None:
        """Open the file, plot in two tabs, place a flag and a note.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.double_click("s1")
        self.plot_id_i = self.current_plot_ids()[0]
        first_tab_id_i = self.view.current_tab_id()
        self.view.handler_dict["add_tab"]()
        self.double_click("s2")
        self.other_plot_id_i = self.current_plot_ids()[0]
        self.view.set_current_tab(first_tab_id_i)
        self.view.handler_dict["plot_tool"](MARKER_TOOL_STR)
        self.view.handler_dict["marker_place_handler"](self.plot_id_i, 1.0)
        self.flag_id_i = self.workspace.marker_list[0].marker_id_i
        self.view.handler_dict["plot_tool"](TEXT_TOOL_STR)
        self.view.handler_dict["text_note_create_handler"](
            self.plot_id_i, "Peak", 2.0, 3.0)
        self.view.handler_dict["plot_tool"](NO_TOOL_STR)

    def undo_depth(self) -> int:
        """Return how many actions can be undone.

        Inputs: none.
        Outputs: the depth of the undo history.
        """
        return self.controller.undo_history.depth()

    def drawn_flag_colors(self, plot_id_i: int) -> list:
        """Return the colors of the flags last drawn in a plot.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: a list of "#rrggbb", in placing order.
        """
        return [marker_tuple[3]
                for marker_tuple in self.view.marker_drawn_dict[plot_id_i]]

    def drawn_note_style(self) -> tuple:
        """Return the style of the first note last drawn in the plot.

        Inputs: none.
        Outputs: (size_i, border_color_str, text_color_str).
        """
        return tuple(self.view.text_note_drawn_dict[self.plot_id_i][0][3:6])


class FlagColorControllerTest(ItemColorControllerTestCase):
    """"Color" in the flag menu (LLFR-00391, LLFR-00392)."""

    @covers("LLFR-00392", "LLFR-00205", "LLFR-00388", "LLFR-00389",
            "LLFR-00390", "LLFR-00140", "LLFR-00664", "LLFR-00809",
            "LLFR-00813")
    def test_confirmed_color_on_every_plot_of_every_tab(self) -> None:
        """The picker starts at the flag's color; the confirmed color is
        drawn on every time plot, the other tab included, as one
        undoable action.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.drawn_flag_colors(self.plot_id_i),
                         [DEFAULT_FLAG_COLOR_STR])
        depth_i = self.undo_depth()
        self.view.color_answer_list = ["#1F77B4"]
        self.view.handler_dict["marker_color_handler"](
            self.other_plot_id_i, self.flag_id_i)
        self.assertEqual(self.view.color_question_list,
                         [DEFAULT_FLAG_COLOR_STR])
        self.assertEqual(self.undo_depth(), depth_i + 1)
        for plot_id_i in (self.plot_id_i, self.other_plot_id_i):
            self.assertEqual(self.drawn_flag_colors(plot_id_i),
                             ["#1f77b4"])
        # A plot created later draws the flag in its color too.
        self.double_click("s1")
        self.assertEqual(
            self.drawn_flag_colors(self.current_plot_ids()[-1]),
            ["#1f77b4"])

    @covers("LLFR-00390", "LLFR-00140", "LLFR-00811", "LLFR-00812")
    def test_cancel_or_same_color_changes_nothing(self) -> None:
        """A cancelled picker, the flag's own color (in any case) or
        unknown ids add no undoable action and draw nothing new.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.undo_depth()
        call_count_i = len(self.view.call_list)
        color_handler = self.view.handler_dict["marker_color_handler"]
        self.view.color_answer_list = [None, DEFAULT_FLAG_COLOR_STR.upper()]
        color_handler(self.plot_id_i, self.flag_id_i)
        color_handler(self.plot_id_i, self.flag_id_i)
        color_handler(999, self.flag_id_i)
        color_handler(self.plot_id_i, 999)
        self.assertEqual(len(self.view.color_question_list), 2)
        self.assertEqual(self.undo_depth(), depth_i)
        self.assertEqual(self.workspace.marker_list[0].color_str,
                         DEFAULT_FLAG_COLOR_STR)
        self.assertNotIn("set_markers", [
            call_tuple[0] for call_tuple
            in self.view.call_list[call_count_i:]])

    @covers("LLFR-00392", "LLFR-00138", "LLFR-00192", "LLFR-00140")
    def test_undo_and_redo_of_a_color_change(self) -> None:
        """Undo brings the old color back on every plot, redo the new.

        Inputs: none.
        Outputs: none.
        """
        self.view.color_answer_list = ["#00aa00"]
        self.view.handler_dict["marker_color_handler"](
            self.plot_id_i, self.flag_id_i)
        self.view.handler_dict["undo"]()
        for plot_id_i in (self.plot_id_i, self.other_plot_id_i):
            self.assertEqual(self.drawn_flag_colors(plot_id_i),
                             [DEFAULT_FLAG_COLOR_STR])
        self.view.handler_dict["redo"]()
        for plot_id_i in (self.plot_id_i, self.other_plot_id_i):
            self.assertEqual(self.drawn_flag_colors(plot_id_i),
                             ["#00aa00"])

    @covers("LLFR-00392", "LLFR-00391")
    def test_color_with_any_plot_tool(self) -> None:
        """The flag menu's "Color" works whatever plot tool is active.

        Inputs: none.
        Outputs: none.
        """
        for index_i, tool_str in enumerate(
                (ZOOM_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR)):
            with self.subTest(tool=tool_str):
                self.view.handler_dict["plot_tool"](tool_str)
                color_str = f"#0000{index_i + 10:02x}"
                self.view.color_answer_list = [color_str]
                self.view.handler_dict["marker_color_handler"](
                    self.plot_id_i, self.flag_id_i)
                self.assertEqual(self.drawn_flag_colors(self.plot_id_i),
                                 [color_str])


class TextNoteStyleControllerTest(ItemColorControllerTestCase):
    """Size, border color and text color of a note (LLFR-00385 to
    LLFR-00387)."""

    @covers("LLFR-00336", "LLFR-00385", "LLFR-00740", "LLFR-00803")
    def test_new_note_is_drawn_with_the_default_style(self) -> None:
        """A new note is drawn at 12 points in #24303b with an orange
        #ff8000 border.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(DEFAULT_TEXT_NOTE_BORDER_COLOR_STR, "#ff8000")
        self.assertEqual(self.drawn_note_style(),
                         (12, DEFAULT_TEXT_NOTE_BORDER_COLOR_STR,
                          DEFAULT_TEXT_NOTE_COLOR_STR))

    @covers("LLFR-00385", "LLFR-00140", "LLFR-00138", "LLFR-00192",
            "LLFR-00802")
    def test_size_change_is_undoable(self) -> None:
        """A preset size is drawn and is one undoable action; the same
        size, another value or unknown ids record nothing.

        Inputs: none.
        Outputs: none.
        """
        size_handler = self.view.handler_dict["text_note_size_handler"]
        depth_i = self.undo_depth()
        size_handler(self.plot_id_i, 0, 12)
        size_handler(self.plot_id_i, 0, 13)
        size_handler(self.plot_id_i, 4, 20)
        size_handler(999, 0, 20)
        self.assertEqual(self.undo_depth(), depth_i)
        size_handler(self.plot_id_i, 0, 24)
        self.assertEqual(self.undo_depth(), depth_i + 1)
        self.assertEqual(self.drawn_note_style()[0], 24)
        self.view.handler_dict["undo"]()
        self.assertEqual(self.drawn_note_style()[0], 12)
        self.view.handler_dict["redo"]()
        self.assertEqual(self.drawn_note_style()[0], 24)

    @covers("LLFR-00387", "LLFR-00388", "LLFR-00389", "LLFR-00390",
            "LLFR-00140", "LLFR-00809", "LLFR-00808")
    def test_border_and_text_colors_from_the_picker(self) -> None:
        """"Border color" and "Text color" open the picker at the
        border's and the text's own color and change only that part.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.undo_depth()
        self.view.color_answer_list = ["#FF0000"]
        self.view.handler_dict["text_note_border_color_handler"](
            self.plot_id_i, 0)
        self.assertEqual(self.drawn_note_style(),
                         (12, "#ff0000", DEFAULT_TEXT_NOTE_COLOR_STR))
        self.view.color_answer_list = ["#0000ff"]
        self.view.handler_dict["text_note_text_color_handler"](
            self.plot_id_i, 0)
        self.assertEqual(self.drawn_note_style(),
                         (12, "#ff0000", "#0000ff"))
        self.assertEqual(self.undo_depth(), depth_i + 2)
        # The picker starts at the current color of each part.
        self.view.handler_dict["text_note_border_color_handler"](
            self.plot_id_i, 0)
        self.view.handler_dict["text_note_text_color_handler"](
            self.plot_id_i, 0)
        self.assertEqual(self.view.color_question_list, [
            DEFAULT_TEXT_NOTE_BORDER_COLOR_STR, DEFAULT_TEXT_NOTE_COLOR_STR,
            "#ff0000", "#0000ff"])
        self.view.handler_dict["undo"]()
        self.assertEqual(self.drawn_note_style(),
                         (12, "#ff0000", DEFAULT_TEXT_NOTE_COLOR_STR))
        self.view.handler_dict["undo"]()
        self.assertEqual(self.drawn_note_style(),
                         (12, DEFAULT_TEXT_NOTE_BORDER_COLOR_STR,
                          DEFAULT_TEXT_NOTE_COLOR_STR))

    @covers("LLFR-00390", "LLFR-00387", "LLFR-00140", "LLFR-00811",
            "LLFR-00812")
    def test_cancel_or_same_color_records_nothing(self) -> None:
        """A cancelled picker, the part's own color or unknown ids
        change nothing and add no undoable action.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.undo_depth()
        self.view.color_answer_list = [None, "#FF8000", None, "#24303B"]
        for handler_name_str in ("text_note_border_color_handler",
                                 "text_note_text_color_handler"):
            handler = self.view.handler_dict[handler_name_str]
            handler(self.plot_id_i, 0)
            handler(self.plot_id_i, 0)
            handler(self.plot_id_i, 7)
            handler(999, 0)
        self.assertEqual(len(self.view.color_question_list), 4)
        self.assertEqual(self.undo_depth(), depth_i)
        self.assertEqual(self.drawn_note_style(),
                         (12, DEFAULT_TEXT_NOTE_BORDER_COLOR_STR,
                          DEFAULT_TEXT_NOTE_COLOR_STR))

    @covers("LLFR-00342", "LLFR-00385", "LLFR-00387", "LLFR-00748")
    def test_edit_keeps_the_size_and_colors(self) -> None:
        """Editing the text keeps the chosen size and colors.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["text_note_size_handler"](
            self.plot_id_i, 0, 8)
        self.view.color_answer_list = ["#aa00aa", "#00aaaa"]
        self.view.handler_dict["text_note_border_color_handler"](
            self.plot_id_i, 0)
        self.view.handler_dict["text_note_text_color_handler"](
            self.plot_id_i, 0)
        self.view.handler_dict["text_note_edit_handler"](
            self.plot_id_i, 0, "Edited")
        self.assertEqual(
            self.view.text_note_drawn_dict[self.plot_id_i][0][:6],
            ("Edited", 2.0, 3.0, 8, "#aa00aa", "#00aaaa"))


if __name__ == "__main__":
    unittest.main()
