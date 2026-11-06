"""Controller tests of the text background (#270, HLFR-00167).

A fake view (no Qt) records what the controller asks of it. The tests
follow the owner's answers of 2026-11-06 in #270, batches 1 to 3: one
choice for every plot, kept in the settings, undoable and redoable,
kept when the undo history is cleared and when a layout is loaded, and
never written to a layout file.
"""

import json
import unittest

from tests.support import covers
from tests.controller.test_plot_controller import PlotControllerTestCase

from model.text_background import (
    AUTO_CONTRAST_STR, DEFAULT_TEXT_BACKGROUND_STR, TEXT_BACKGROUND_TEXT_DICT,
    TEXT_BACKGROUND_TUPLE, TRANSPARENT_STR, cleaned_text_background)


class TextBackgroundModelTest(unittest.TestCase):
    """The two choices and the value read from the settings."""

    @covers("LLFR-01418", "LLFR-01425", "HLFR-00167")
    def test_choices_and_default(self) -> None:
        """"Transparent" then "Auto contrast"; anything else gives "Auto
        contrast".

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(TEXT_BACKGROUND_TUPLE,
                         (TRANSPARENT_STR, AUTO_CONTRAST_STR))
        self.assertEqual([TEXT_BACKGROUND_TEXT_DICT[choice_str]
                          for choice_str in TEXT_BACKGROUND_TUPLE],
                         ["Transparent", "Auto contrast"])
        self.assertEqual(DEFAULT_TEXT_BACKGROUND_STR, AUTO_CONTRAST_STR)
        for stored_value in (None, "", "black", 1, ["transparent"]):
            with self.subTest(stored_value=stored_value):
                self.assertEqual(cleaned_text_background(stored_value),
                                 AUTO_CONTRAST_STR)
        self.assertEqual(cleaned_text_background(" Transparent "),
                         TRANSPARENT_STR)


class TextBackgroundControllerTest(PlotControllerTestCase):
    """The controller keeps the choice and passes it to the view."""

    def choose(self, choice_str: str) -> None:
        """Choose an entry of the "Text background" submenu of a plot.

        Inputs:
            choice_str: one of TEXT_BACKGROUND_TUPLE.
        Outputs: none.
        """
        self.view.handler_dict["text_background_handler"](1, choice_str)

    @covers("LLFR-01425", "LLFR-01426", "HLFR-00167")
    def test_start_uses_the_remembered_choice(self) -> None:
        """At start, the view gets the choice kept in the settings, and
        "Auto contrast" when none is kept.

        Inputs: none.
        Outputs: none.
        """
        from controller.plot_controller import PlotController
        from model.workspace import Workspace
        from tests.controller.test_plot_controller import (
            FakeFileController, FakePlotView)
        self.assertEqual(self.view.text_background_list[0],
                         AUTO_CONTRAST_STR)
        view = FakePlotView()
        view.remembered_text_background_str = TRANSPARENT_STR
        workspace = Workspace()
        PlotController(view, FakeFileController(), workspace)
        self.assertEqual(view.text_background_list, [TRANSPARENT_STR])
        self.assertEqual(workspace.text_background_str, TRANSPARENT_STR)

    @covers("LLFR-01420", "LLFR-01427", "LLFR-00140", "LLFR-00138",
            "LLFR-00192", "HLFR-00167", "HLFR-00040", "HLFR-00048")
    def test_change_is_undoable_and_redoable(self) -> None:
        """A change is one undoable action; undo puts back the previous
        choice in the view (which keeps it in the settings) and redo
        applies it again; the current choice is no action.

        Inputs: none.
        Outputs: none.
        """
        self.view.text_background_list = []
        undo_count_i = self.controller.undo_history.depth()
        self.choose(AUTO_CONTRAST_STR)
        self.assertEqual(self.view.text_background_list, [])
        self.assertEqual(self.controller.undo_history.depth(),
                         undo_count_i)
        self.choose(TRANSPARENT_STR)
        self.assertEqual(self.workspace.text_background_str,
                         TRANSPARENT_STR)
        self.assertEqual(self.view.text_background_list, [TRANSPARENT_STR])
        self.assertEqual(self.controller.undo_history.depth(),
                         undo_count_i + 1)
        self.controller.on_undo()
        self.assertEqual(self.workspace.text_background_str,
                         AUTO_CONTRAST_STR)
        self.assertEqual(self.view.text_background_list[-1],
                         AUTO_CONTRAST_STR)
        self.controller.on_redo()
        self.assertEqual(self.workspace.text_background_str,
                         TRANSPARENT_STR)
        self.assertEqual(self.view.text_background_list[-1],
                         TRANSPARENT_STR)

    @covers("LLFR-01428", "LLFR-00930", "HLFR-00167")
    def test_cleared_history_keeps_the_choice(self) -> None:
        """Closing the data files clears the undo history and keeps the
        choice.

        Inputs: none.
        Outputs: none.
        """
        self.choose(TRANSPARENT_STR)
        self.close_all_files()
        self.assertFalse(self.controller.undo_history.can_undo())
        self.assertEqual(self.workspace.text_background_str,
                         TRANSPARENT_STR)
        self.assertEqual(self.view.text_background_list[-1],
                         TRANSPARENT_STR)

    @covers("LLFR-01429", "LLFR-00226", "HLFR-00167", "HLFR-00050",
            "HLFR-00049")
    def test_layout_neither_holds_nor_changes_the_choice(self) -> None:
        """The layout file holds no text background, and loading a
        layout keeps the current choice.

        Inputs: none.
        Outputs: none.
        """
        self.double_click(self.signal_file.signal_name_list[1])
        self.choose(TRANSPARENT_STR)
        layout_dict = self.controller.layout_dict()
        layout_text_str = json.dumps(layout_dict)
        self.assertNotIn("background", layout_text_str)
        self.assertNotIn(TRANSPARENT_STR, layout_text_str)
        self.controller.load_layout(layout_dict)
        self.assertEqual(self.workspace.text_background_str,
                         TRANSPARENT_STR)
        self.assertEqual(self.view.text_background_list[-1],
                         TRANSPARENT_STR)


if __name__ == "__main__":
    unittest.main()
