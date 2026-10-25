"""Tests for the top panel buttons (LLFR-00004, LLFR-00018)."""

import unittest

from tests.support import covers, get_qt_application, requires_qt


@requires_qt
class TopPanelTest(unittest.TestCase):
    """Check that the top panel holds the Open file and Tip buttons."""

    def setUp(self) -> None:
        """Create and show a top panel.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.top_panel import TopPanel
        self.top_panel = TopPanel()
        self.top_panel.resize(600, 60)
        self.top_panel.show()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close and delete the panel.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.close()
        self.top_panel.deleteLater()
        self.application.processEvents()

    @covers("LLFR-00004", "LLFR-00001")
    def test_open_file_button_is_a_toggle_button(self) -> None:
        """The panel has a visible, inactive "Open file" ToggleButton.

        Inputs: none.
        Outputs: none.
        """
        from view.toggle_button import ToggleButton
        button = self.top_panel.open_file_button
        self.assertIsInstance(button, ToggleButton)
        self.assertEqual(button.text(), "Open file")
        self.assertTrue(button.isVisible())
        self.assertFalse(button.is_active())
        self.assertIs(button.parentWidget(), self.top_panel)

    @covers("LLFR-00018", "LLFR-00001")
    def test_tip_button_is_a_toggle_button(self) -> None:
        """The panel has a visible, inactive "Tip" ToggleButton.

        Inputs: none.
        Outputs: none.
        """
        from view.toggle_button import ToggleButton
        button = self.top_panel.tip_button
        self.assertIsInstance(button, ToggleButton)
        self.assertEqual(button.text(), "Tip")
        self.assertTrue(button.isVisible())
        self.assertFalse(button.is_active())
        self.assertIs(button.parentWidget(), self.top_panel)

    @covers("LLFR-00004", "LLFR-00018")
    def test_buttons_are_left_aligned_in_order(self) -> None:
        """Open file comes first, Tip next, both on the left side.

        Inputs: none.
        Outputs: none.
        """
        open_x_i = self.top_panel.open_file_button.x()
        tip_x_i = self.top_panel.tip_button.x()
        self.assertLess(open_x_i, tip_x_i)
        self.assertLess(tip_x_i + self.top_panel.tip_button.width(),
                        self.top_panel.width() // 2)

    @covers("LLFR-00001", "LLFR-00002")
    def test_buttons_have_separate_states(self) -> None:
        """Activating or deactivating one button leaves the other alone.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.tip_button.click()
        self.assertTrue(self.top_panel.tip_button.is_active())
        self.assertFalse(self.top_panel.open_file_button.is_active())
        self.assertNotEqual(self.top_panel.tip_button.objectName(),
                            self.top_panel.open_file_button.objectName())
        self.top_panel.open_file_button.click()
        self.top_panel.tip_button.click()
        self.assertFalse(self.top_panel.tip_button.is_active())
        self.assertTrue(self.top_panel.open_file_button.is_active())


if __name__ == "__main__":
    unittest.main()
