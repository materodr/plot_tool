"""GUI tests for the Redo button and its shortcut (HLFR-00048).

They use a real MainWindow with the real controllers (the setup of the
undo GUI tests). Dialogs are patched, so no modal window is left open.
"""

import unittest
from unittest import mock

from tests.support import button_name, covers, requires_qt
from tests.view.test_undo import UndoWindowTestCase


@requires_qt
class RedoWindowTestCase(UndoWindowTestCase):
    """Undo setup plus helpers for the Redo button and Ctrl+Y."""

    def setUp(self) -> None:
        """Create the window as for undo and keep the Redo button.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.redo_button = self.top_panel.redo_button

    def click_redo(self) -> None:
        """Click the Redo button with the mouse.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.mouseClick(self.redo_button, Qt.MouseButton.LeftButton)
        self.application.processEvents()

    def press_ctrl_y(self, widget=None) -> None:
        """Press Ctrl+Y (Cmd+Y on macOS) on a widget.

        Inputs:
            widget: the widget that gets the keys (default: the plot
                panel).
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.keyClick(widget or self.plot_panel, Qt.Key.Key_Y,
                       Qt.KeyboardModifier.ControlModifier)
        self.application.processEvents()

    def wait_until_inactive(self, button) -> None:
        """Wait until a button has returned from its active color.

        Inputs:
            button: an ActionButton.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        for _ in range(30):
            if not button.is_active():
                return
            QTest.qWait(100)


class RedoButtonTest(RedoWindowTestCase):
    """The Redo button of the top panel."""

    @covers("LLFR-00190", "LLFR-00158", "LLFR-00181")
    def test_button_is_directly_right_of_undo(self) -> None:
        """A "Redo" button, icon only, right next to the Undo button.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QPushButton
        from view import theme
        from view.undo_button import UndoButton
        self.assertIsInstance(self.redo_button, QPushButton)
        self.assertIsInstance(self.redo_button, UndoButton)
        self.assertEqual(button_name(self.redo_button), "Redo")
        self.assertEqual(self.redo_button.toolTip(), "Redo")
        self.assertEqual(self.redo_button.accessibleName(), "Redo")
        self.assertEqual(self.redo_button.text(), "")
        self.assertFalse(self.redo_button.icon().isNull())
        self.assertIs(self.redo_button.parentWidget(), self.top_panel)
        self.assertTrue(self.redo_button.isVisible())
        # LLFR-00190: the next button after Undo, with only the small
        # gap of a group between them.
        button_list = self.top_panel.button_list()
        undo_index_i = button_list.index(self.top_panel.undo_button)
        self.assertIs(button_list[undo_index_i + 1], self.redo_button)
        undo_right_i = (self.top_panel.undo_button.x()
                        + self.top_panel.undo_button.width())
        self.assertGreater(self.redo_button.x(), undo_right_i - 1)
        self.assertLessEqual(self.redo_button.x() - undo_right_i,
                             theme.TOOLBAR_BUTTON_GAP_I)
        self.assertEqual(self.redo_button.y(),
                         self.top_panel.undo_button.y())
        self.assertEqual(self.redo_button.size(),
                         self.top_panel.undo_button.size())

    @covers("LLFR-00159", "LLFR-00160")
    def test_icon_differs_from_undo_in_every_state(self) -> None:
        """The Redo icon is not the Undo icon, enabled or disabled.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QIcon
        from tests.view.test_icons import image_digest_str
        for mode in (QIcon.Mode.Normal, QIcon.Mode.Disabled):
            with self.subTest(mode=mode):
                redo_image = self.redo_button.icon().pixmap(
                    QSize(24, 24), mode).toImage()
                undo_image = self.top_panel.undo_button.icon().pixmap(
                    QSize(24, 24), mode).toImage()
                self.assertNotEqual(image_digest_str(redo_image),
                                    image_digest_str(undo_image))
                # LLFR-00160: the icon is drawn in this state.
                self.assertFalse(redo_image.isNull())
                self.assertGreater(len(set(
                    redo_image.pixel(x_i, y_i) for x_i in range(24)
                    for y_i in range(24))), 1)

    @covers("LLFR-00194", "LLFR-00160")
    def test_disabled_and_paler_until_an_undo(self) -> None:
        """With nothing to redo, the button is disabled and paler.

        Inputs: none.
        Outputs: none.
        """
        from view.toggle_button import NORMAL_COLOR_STR
        from view.undo_button import DISABLED_COLOR_STR
        self.assertFalse(self.redo_button.isEnabled())
        self.assertFalse(self.main_window.is_redo_enabled())
        self.assertEqual(self.redo_button.current_background_color_str(),
                         DISABLED_COLOR_STR)
        self.assertIn(":disabled", self.redo_button.styleSheet())
        disabled_image = self.redo_button.grab().toImage()
        self.main_window.signal_double_click_handler("speed")
        self.assertFalse(self.redo_button.isEnabled())
        self.click_undo()
        self.assertTrue(self.redo_button.isEnabled())
        self.wait_until_inactive(self.top_panel.undo_button)
        self.application.processEvents()
        enabled_image = self.redo_button.grab().toImage()
        self.assertEqual(self.redo_button.current_background_color_str(),
                         NORMAL_COLOR_STR)
        point_tuple = (4, disabled_image.height() // 2)
        self.assertGreater(
            disabled_image.pixelColor(*point_tuple).lightness(),
            enabled_image.pixelColor(*point_tuple).lightness())

    @covers("LLFR-00192", "LLFR-00194", "LLFR-00001", "LLFR-00003")
    def test_click_redoes_the_undone_action(self) -> None:
        """Undo two plots, redo them one by one with the button.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.signal_double_click_handler("speed")
        self.main_window.signal_double_click_handler("force")
        full_state = self.state()
        first_id_i, second_id_i = self.current_plot_ids()
        self.click_undo()
        self.wait_until_inactive(self.top_panel.undo_button)
        self.click_undo()
        self.assertEqual(self.current_plot_ids(), [])
        self.assertFalse(self.top_panel.undo_button.isEnabled())
        self.click_redo()
        self.assertEqual(self.current_plot_ids(), [first_id_i])
        self.assertTrue(self.top_panel.undo_button.isEnabled())
        self.assertTrue(self.redo_button.isEnabled())
        self.wait_until_inactive(self.redo_button)
        self.click_redo()
        self.assertEqual(self.current_plot_ids(), [first_id_i, second_id_i])
        self.assertEqual(self.state(), full_state)
        self.assertEqual(
            [entry[0] for entry in self.plot_panel.plot_view(
                second_id_i).legend_entry_list()], ["force"])
        # LLFR-00194: nothing is left to redo; LLFR-00003: the button is
        # not left active.
        self.wait_until_inactive(self.redo_button)
        self.assertFalse(self.redo_button.isEnabled())
        self.assertFalse(self.redo_button.is_active())

    @covers("LLFR-00194")
    def test_disabled_button_does_nothing(self) -> None:
        """Clicks on the disabled button change nothing.

        Inputs: none.
        Outputs: none.
        """
        handler = mock.Mock()
        self.main_window.set_redo_handler(handler)
        self.click_redo()
        self.redo_button.click()
        self.main_window.run_redo()
        handler.assert_not_called()
        self.assertFalse(self.redo_button.is_active())

    @covers("LLFR-00193", "LLFR-00194")
    def test_new_action_disables_redo(self) -> None:
        """An action after an undo leaves nothing to redo.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.signal_double_click_handler("speed")
        self.click_undo()
        self.assertTrue(self.redo_button.isEnabled())
        self.main_window.signal_double_click_handler("force")
        self.assertFalse(self.redo_button.isEnabled())


class RedoShortcutTest(RedoWindowTestCase):
    """Ctrl+Y (Cmd+Y on macOS) runs the Redo button's action."""

    @covers("LLFR-00191", "LLFR-00192")
    def test_ctrl_y_redoes(self) -> None:
        """Ctrl+Y redoes the most recently undone action.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QKeySequence
        self.assertEqual(self.main_window.redo_shortcut.key(),
                         QKeySequence("Ctrl+Y"))
        self.main_window.signal_double_click_handler("speed")
        self.main_window.signal_double_click_handler("force")
        self.press_ctrl_z()
        self.press_ctrl_z()
        self.assertEqual(self.current_plot_ids(), [])
        self.press_ctrl_y()
        self.assertEqual(len(self.current_plot_ids()), 1)
        self.press_ctrl_y(self.top_panel)
        self.assertEqual(len(self.current_plot_ids()), 2)
        self.assertFalse(self.redo_button.isEnabled())

    @covers("LLFR-00194", "LLFR-00191")
    def test_ctrl_y_does_nothing_when_nothing_to_redo(self) -> None:
        """With nothing to redo, Ctrl+Y changes nothing.

        Inputs: none.
        Outputs: none.
        """
        handler = mock.Mock()
        self.main_window.set_redo_handler(handler)
        self.main_window.signal_double_click_handler("speed")
        state = self.state()
        self.press_ctrl_y()
        handler.assert_not_called()
        self.assertEqual(self.state(), state)

    @covers("LLFR-00195", "LLFR-00196", "LLFR-00157")
    def test_shortcuts_in_the_search_box_leave_the_workspace(self) -> None:
        """In the search box, Ctrl+Z and Ctrl+Y do not undo or redo.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        self.main_window.signal_double_click_handler("speed")
        self.main_window.signal_double_click_handler("force")
        self.press_ctrl_z()
        self.assertTrue(self.redo_button.isEnabled())
        state = self.state()
        search_box = self.main_window.signal_list_panel.search_box
        search_box.setFocus()
        self.application.processEvents()
        QTest.keyClicks(search_box, "spe")
        self.assertIs(self.application.focusWidget(), search_box)
        self.press_ctrl_y(search_box)
        self.assertEqual(self.state(), state)
        self.press_ctrl_z(search_box)
        self.assertEqual(self.state(), state)
        self.press_ctrl_y(search_box)
        self.assertEqual(self.state(), state)
        self.assertTrue(self.redo_button.isEnabled())
        self.assertTrue(self.top_panel.undo_button.isEnabled())
        # The window's handlers also ignore a focused text field.
        self.main_window._on_redo_shortcut()
        self.main_window._on_undo_shortcut()
        self.assertEqual(self.state(), state)
        # Out of the text field, Ctrl+Y redoes again.
        self.top_panel.open_file_button.setFocus()
        self.application.processEvents()
        self.press_ctrl_y()
        self.assertEqual(len(self.current_plot_ids()), 2)

    @covers("LLFR-00195", "LLFR-00196")
    def test_shortcuts_in_a_name_editor_leave_the_workspace(self) -> None:
        """In a line edit of a dialog, the shortcuts do nothing either.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QLineEdit
        self.main_window.signal_double_click_handler("speed")
        self.main_window.signal_double_click_handler("force")
        self.press_ctrl_z()
        state = self.state()
        name_editor = QLineEdit(self.main_window)
        name_editor.show()
        name_editor.setFocus()
        self.application.processEvents()
        self.assertTrue(self.main_window.text_field_has_focus())
        self.press_ctrl_y(name_editor)
        self.press_ctrl_z(name_editor)
        self.main_window._on_redo_shortcut()
        self.main_window._on_undo_shortcut()
        self.assertEqual(self.state(), state)
        name_editor.deleteLater()
        self.application.processEvents()

    @covers("LLFR-00150", "LLFR-00191", "LLFR-00192")
    def test_ctrl_y_ends_tip_and_runs_redo(self) -> None:
        """Ctrl held, then Y: the Tip activation ends and redo runs.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from controller.plot_tools import NO_TOOL_STR, TIP_TOOL_STR
        self.main_window.signal_double_click_handler("speed")
        self.main_window.signal_double_click_handler("force")
        self.press_ctrl_z()
        self.assertEqual(len(self.current_plot_ids()), 1)
        widget = self.plot_panel
        QTest.keyPress(widget, Qt.Key.Key_Control)
        self.application.processEvents()
        self.assertEqual(self.top_panel.active_plot_tool(), TIP_TOOL_STR)
        QTest.keyClick(widget, Qt.Key.Key_Y,
                       Qt.KeyboardModifier.ControlModifier)
        self.application.processEvents()
        # LLFR-00192: the second plot is back; LLFR-00150: no tool is
        # active, also in the plots rebuilt by the redo.
        self.assertEqual(len(self.current_plot_ids()), 2)
        self.assertEqual(self.top_panel.active_plot_tool(), NO_TOOL_STR)
        for plot_id_i in self.current_plot_ids():
            self.assertEqual(
                self.plot_panel.plot_view(plot_id_i).plot_tool_str,
                NO_TOOL_STR)
        QTest.keyRelease(widget, Qt.Key.Key_Control)
        self.application.processEvents()
        self.assertEqual(self.top_panel.active_plot_tool(), NO_TOOL_STR)


if __name__ == "__main__":
    unittest.main()
