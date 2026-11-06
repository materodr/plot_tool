"""Reviewer's controller tests of the text background (#270).

Independent of the implementer's tests: a fake view (no Qt) records
what the controller asks of it. The cases follow the owner's answers of
2026-11-06 in #270: batch 2, item 3 (undoable and redoable, undo puts
the previous choice back in the settings, clearing the history keeps
it), batch 2, item 4 (not in layout files, a layout load keeps it) and
batch 1, item 1 (one global choice).
"""

import json
import unittest

from tests.support import covers
from tests.controller.test_plot_controller import (
    PlotControllerTestCase, make_signal_file)

from model.text_background import AUTO_CONTRAST_STR, TRANSPARENT_STR


class TextBackgroundReviewTest(PlotControllerTestCase):
    """The text background through undo, redo, files and layouts."""

    def choose(self, choice_str: str, plot_id_i: int = 1) -> None:
        """Choose an entry of the "Text background" submenu of a plot.

        Inputs:
            choice_str: "transparent" or "auto_contrast".
            plot_id_i: id of the plot whose object menu was used.
        Outputs: none.
        """
        self.view.handler_dict["text_background_handler"](plot_id_i,
                                                          choice_str)

    def shown_choice(self) -> str:
        """Return the last choice the controller gave to the view.

        Inputs: none.
        Outputs: the choice; the view keeps it in the settings
            (LLFR-01426), so this is also the remembered one.
        """
        return self.view.text_background_list[-1]

    @covers("LLFR-01427", "LLFR-00138", "LLFR-00192", "LLFR-01426",
            "HLFR-00167", "HLFR-00040", "HLFR-00048")
    def test_undo_and_redo_mixed_with_other_actions(self) -> None:
        """Two choices between other undoable actions: each undo puts
        back the choice of before its own action only, and the view
        (with the settings) gets that choice each time.

        Inputs: none.
        Outputs: none.
        """
        self.double_click(self.signal_file.signal_name_list[1])
        self.choose(TRANSPARENT_STR)
        self.controller.on_add_tab()
        self.choose(AUTO_CONTRAST_STR)
        self.choose(TRANSPARENT_STR)
        tab_count_i = len(self.workspace.tab_list)
        # Undo the second "Transparent": back to "Auto contrast".
        self.controller.on_undo()
        self.assertEqual(self.workspace.text_background_str,
                         AUTO_CONTRAST_STR)
        self.assertEqual(self.shown_choice(), AUTO_CONTRAST_STR)
        # Undo "Auto contrast": back to "Transparent".
        self.controller.on_undo()
        self.assertEqual(self.workspace.text_background_str,
                         TRANSPARENT_STR)
        self.assertEqual(self.shown_choice(), TRANSPARENT_STR)
        # Undo the new tab: the tab goes, the choice stays.
        self.controller.on_undo()
        self.assertEqual(len(self.workspace.tab_list), tab_count_i - 1)
        self.assertEqual(self.workspace.text_background_str,
                         TRANSPARENT_STR)
        self.assertEqual(self.shown_choice(), TRANSPARENT_STR)
        # Undo the first "Transparent": back to the first-time default.
        self.controller.on_undo()
        self.assertEqual(self.workspace.text_background_str,
                         AUTO_CONTRAST_STR)
        self.assertEqual(self.shown_choice(), AUTO_CONTRAST_STR)
        # Redo everything: the last choice comes back.
        for _ in range(4):
            self.controller.on_redo()
        self.assertEqual(len(self.workspace.tab_list), tab_count_i)
        self.assertEqual(self.workspace.text_background_str,
                         TRANSPARENT_STR)
        self.assertEqual(self.shown_choice(), TRANSPARENT_STR)

    @covers("LLFR-01427", "HLFR-00167")
    def test_current_choice_records_nothing(self) -> None:
        """Choosing the current choice, from any plot, records no undo
        action and gives the view nothing new.

        Inputs: none.
        Outputs: none.
        """
        self.choose(TRANSPARENT_STR)
        depth_i = self.controller.undo_history.depth()
        call_count_i = len(self.view.text_background_list)
        self.choose(TRANSPARENT_STR, plot_id_i=7)
        self.choose(" Transparent ", plot_id_i=2)
        self.assertEqual(self.controller.undo_history.depth(), depth_i)
        self.assertEqual(len(self.view.text_background_list),
                         call_count_i)

    @covers("LLFR-01428", "LLFR-00142", "LLFR-01427", "HLFR-00167")
    def test_file_open_keeps_the_choice_and_its_undo(self) -> None:
        """Opening another data file keeps the history (LLFR-00142) and
        the choice; the change can still be undone afterwards.

        Inputs: none.
        Outputs: none.
        """
        self.choose(TRANSPARENT_STR)
        self.file_controller.open(make_signal_file(4), False)
        self.assertEqual(self.workspace.text_background_str,
                         TRANSPARENT_STR)
        self.assertEqual(self.shown_choice(), TRANSPARENT_STR)
        self.assertTrue(self.controller.undo_history.can_undo())
        self.controller.on_undo()
        self.assertEqual(self.workspace.text_background_str,
                         AUTO_CONTRAST_STR)
        self.assertEqual(self.shown_choice(), AUTO_CONTRAST_STR)

    @covers("LLFR-01429", "LLFR-00226", "LLFR-01428", "LLFR-00238",
            "HLFR-00167", "HLFR-00050")
    def test_layout_saved_with_one_choice_loaded_with_the_other(
            self) -> None:
        """A layout saved with "Transparent" and loaded with "Auto
        contrast" shows auto contrast, and the other way round; the
        layout file holds neither choice, and an undo after the load
        cannot change the choice.

        Inputs: none.
        Outputs: none.
        """
        self.double_click(self.signal_file.signal_name_list[1])
        self.choose(TRANSPARENT_STR)
        transparent_layout_dict = self.controller.layout_dict()
        self.choose(AUTO_CONTRAST_STR)
        auto_layout_dict = self.controller.layout_dict()
        # The two files differ in nothing (LLFR-00226).
        self.assertEqual(json.dumps(transparent_layout_dict,
                                    sort_keys=True),
                         json.dumps(auto_layout_dict, sort_keys=True))
        self.controller.load_layout(transparent_layout_dict)
        self.assertEqual(self.workspace.text_background_str,
                         AUTO_CONTRAST_STR)
        self.assertEqual(self.shown_choice(), AUTO_CONTRAST_STR)
        self.assertFalse(self.controller.undo_history.can_undo())
        self.controller.on_undo()
        self.assertEqual(self.workspace.text_background_str,
                         AUTO_CONTRAST_STR)
        self.choose(TRANSPARENT_STR)
        self.controller.load_layout(auto_layout_dict)
        self.assertEqual(self.workspace.text_background_str,
                         TRANSPARENT_STR)
        self.assertEqual(self.shown_choice(), TRANSPARENT_STR)


if __name__ == "__main__":
    unittest.main()
