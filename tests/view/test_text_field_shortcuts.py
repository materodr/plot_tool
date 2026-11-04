"""Qt tests for Ctrl+P and Ctrl+F in text fields and name dialogs (#244).

A real MainWindow and MainController are used (the setup of
test_undocked_windows_view). They check that the PDF and search
shortcuts leave a text field first, clearing its selection and taking
its typed text (LLFR-01178, LLFR-01182, LLFR-01179), that they close a
name dialog with the typed name and then run (LLFR-01177), that Ctrl+F in the
window's own search box selects its text (LLFR-01180), and that the
dialogs that create a signal are left alone (LLFR-01181).

No modal dialog is ever opened: QInputDialog.getText is replaced by a
function that shows a QInputDialog without exec and sends it the keys.
"""

import unittest
from unittest import mock

from tests.support import covers, requires_qt
from tests.view.test_undocked_windows_view import UndockedWindowTestCase


def key_event(key_name_str: str, type_name_str: str = "KeyPress"):
    """Build a Ctrl+<key> key event (Cmd+<key> on macOS).

    Inputs:
        key_name_str: the letter, for example "P".
        type_name_str: the QEvent.Type name, KeyPress or ShortcutOverride.
    Outputs: a QKeyEvent.
    """
    from PyQt6.QtCore import QEvent, Qt
    from PyQt6.QtGui import QKeyEvent
    return QKeyEvent(getattr(QEvent.Type, type_name_str),
                     getattr(Qt.Key, "Key_" + key_name_str),
                     Qt.KeyboardModifier.ControlModifier)


def fake_get_text(key_name_str: str, typed_str: str, call_list: list):
    """Return a stand-in for QInputDialog.getText that presses a key.

    Inputs:
        key_name_str: the letter pressed with Ctrl in the dialog, or ""
            to press nothing and click OK.
        typed_str: the text the user typed in the dialog's field.
        call_list: gets the arguments of each call.
    Outputs: a function with the arguments and result of getText. It
        shows a real QInputDialog without exec, types the text, sends
        the key to its field (so the application event filters see it)
        and returns the dialog's text and whether it was accepted.
    """

    def get_text(parent, title_str, label_str, echo_mode, text_str):
        """Show the dialog, type, press the key and close it.

        Inputs:
            parent, title_str, label_str, echo_mode, text_str: as for
                QInputDialog.getText.
        Outputs: (text, accepted_b).
        """
        from PyQt6.QtWidgets import (
            QApplication, QDialog, QInputDialog, QLineEdit)
        call_list.append((parent, title_str, label_str, text_str))
        dialog = QInputDialog(parent)
        dialog.setInputMode(QInputDialog.InputMode.TextInput)
        dialog.setTextValue(text_str)
        dialog.show()
        dialog.setTextValue(typed_str)
        field = dialog.findChild(QLineEdit)
        if key_name_str:
            QApplication.sendEvent(field, key_event(key_name_str,
                                                    "ShortcutOverride"))
            QApplication.sendEvent(field, key_event(key_name_str))
        else:
            dialog.accept()
        accepted_b = dialog.result() == QDialog.DialogCode.Accepted.value
        result_tuple = (dialog.textValue(), accepted_b)
        dialog.hide()
        dialog.deleteLater()
        return result_tuple

    return get_text


@requires_qt
class NameDialogShortcutTest(UndockedWindowTestCase):
    """Ctrl+P and Ctrl+F in the dialogs that rename (LLFR-01177)."""

    @covers("LLFR-01177", "HLFR-00038", "HLFR-00033")
    def test_filter_accepts_the_dialog_on_ctrl_p_and_ctrl_f(self) -> None:
        """The filter takes Ctrl+P and Ctrl+F in a QInputDialog: the
        override is taken so no other shortcut gets the key, the press
        accepts the dialog with the typed text; other keys and fields
        outside a QInputDialog are let through.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QDialog, QInputDialog, QLineEdit
        from view.name_dialog import (
            PDF_ACTION_STR, SEARCH_ACTION_STR, NameDialogShortcutFilter)
        for key_str, action_str in (("P", PDF_ACTION_STR),
                                    ("F", SEARCH_ACTION_STR)):
            dialog = QInputDialog(self.main_window)
            dialog.setInputMode(QInputDialog.InputMode.TextInput)
            dialog.show()
            dialog.setTextValue("typed so far")
            field = dialog.findChild(QLineEdit)
            shortcut_filter = NameDialogShortcutFilter()
            other_event = key_event("A")
            self.assertFalse(shortcut_filter.eventFilter(field, other_event))
            override_event = key_event(key_str, "ShortcutOverride")
            override_event.ignore()
            self.assertTrue(shortcut_filter.eventFilter(field,
                                                        override_event))
            self.assertTrue(override_event.isAccepted())
            self.assertTrue(dialog.isVisible())
            self.assertEqual(shortcut_filter.action_str, "")
            self.assertTrue(shortcut_filter.eventFilter(field,
                                                        key_event(key_str)))
            self.assertEqual(shortcut_filter.action_str, action_str)
            self.assertEqual(dialog.result(),
                             QDialog.DialogCode.Accepted.value)
            self.assertEqual(dialog.textValue(), "typed so far")
            dialog.deleteLater()
        # A text field of a window is not a name dialog.
        search_box = self.main_window.signal_list_panel.search_box
        self.assertFalse(NameDialogShortcutFilter().eventFilter(
            search_box, key_event("P")))

    @covers("LLFR-01177", "LLFR-01139", "LLFR-00030", "HLFR-00038",
            "HLFR-00017")
    def test_tab_rename_takes_the_name_then_saves_the_pdf(self) -> None:
        """Ctrl+P in the tab rename dialog renames the tab with the text
        typed so far, and only then runs "Save all tabs as PDF", once.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication, QInputDialog
        self.main_window.show()
        tab_id_i = self.panel.current_tab_id()
        name_at_export_list = []
        self.main_window.pdf_export_handler = (
            lambda: name_at_export_list.append(self.tab(tab_id_i).name_str))
        call_list = []
        with mock.patch.object(QInputDialog, "getText", side_effect=(
                fake_get_text("P", "Typed name", call_list))):
            self.panel.request_rename_tab(tab_id_i)
            self.assertEqual(self.tab(tab_id_i).name_str, "Typed name")
            self.assertEqual(name_at_export_list, [])
            self.process_events()
            QApplication.processEvents()
        self.assertEqual(len(call_list), 1)
        self.assertEqual(name_at_export_list, ["Typed name"])

    @covers("LLFR-01177", "LLFR-01140", "LLFR-01141", "LLFR-00088",
            "HLFR-00033", "HLFR-00138")
    def test_name_dialog_over_a_window_searches_in_that_window(
            self) -> None:
        """Ctrl+F in a name dialog shown over an undocked window returns
        the typed name, then puts the focus in that window's search box,
        showing its hidden panel first; over the main window, in the main
        search box.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QInputDialog
        _, second_id_i, window = self.two_tabs_one_undocked()
        self.main_window.signal_list_panel.search_box.setText("spe")
        self.process_events()
        self.assertFalse(window.is_panel_shown())
        call_list = []
        with mock.patch.object(self.main_window, "dialog_parent",
                               return_value=window), \
                mock.patch.object(QInputDialog, "getText", side_effect=(
                    fake_get_text("F", "Flag A", call_list))):
            typed_str = self.main_window.ask_name("Rename", "Name:", "x")
            self.process_events()
        self.assertEqual(typed_str, "Flag A")
        self.assertIs(call_list[0][0], window)
        window = self.main_window.window_of_tab(second_id_i)
        self.assertTrue(window.is_panel_shown())
        box = window.signal_list_panel.search_box
        self.assertIs(window.focusWidget(), box)
        self.assertEqual(box.selectedText(), "spe")
        # Over the main window, the main window's search box.
        self.main_window.run_name_dialog_shortcut("search", self.main_window)
        self.process_events()
        main_box = self.main_window.signal_list_panel.search_box
        self.assertIs(self.main_window.focusWidget(), main_box)

    @covers("LLFR-01177", "LLFR-01139", "HLFR-00038")
    def test_no_action_without_the_shortcut(self) -> None:
        """A name dialog closed with OK or cancelled runs no shortcut
        action.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QInputDialog
        self.main_window.show()
        handler = mock.Mock()
        self.main_window.pdf_export_handler = handler
        with mock.patch.object(QInputDialog, "getText", side_effect=(
                fake_get_text("", "New", []))):
            self.assertEqual(self.main_window.ask_name("T", "L", "x"),
                             "New")
            self.process_events()
        with mock.patch.object(QInputDialog, "getText",
                               return_value=("ignored", False)):
            self.assertIsNone(self.main_window.ask_name("T", "L", "x"))
            self.process_events()
        handler.assert_not_called()


@requires_qt
class TextFieldShortcutTest(UndockedWindowTestCase):
    """Ctrl+P and Ctrl+F leave a text field of a window first."""

    @covers("LLFR-01178", "LLFR-01182", "LLFR-01139", "HLFR-00038")
    def test_pdf_shortcut_leaves_the_search_box(self) -> None:
        """Ctrl+P with the focus in the search box clears its selection,
        takes the focus out of it, keeps its text, then runs the export.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        self.main_window.show()
        order_list = []
        box = self.main_window.signal_list_panel.search_box
        box.setText("speed")
        box.setSelection(0, 3)
        self.main_window.pdf_export_handler = (
            lambda: order_list.append(("export", box.hasSelectedText())))
        with mock.patch.object(QApplication, "focusWidget",
                               return_value=box), \
                mock.patch.object(box, "hasFocus", return_value=True), \
                mock.patch.object(box, "clearFocus",
                                  side_effect=lambda: order_list.append(
                                      ("left", None))):
            self.main_window.pdf_shortcut.activated.emit()
        self.assertEqual(order_list, [("left", None), ("export", False)])
        self.assertEqual(box.text(), "speed")

    @covers("LLFR-01179", "LLFR-01178", "LLFR-01182", "LLFR-01139",
            "LLFR-01140", "LLFR-00334", "HLFR-00073", "HLFR-00038",
            "HLFR-00033")
    def test_shortcuts_write_the_text_note_first(self) -> None:
        """Ctrl+P and Ctrl+F in the field of a text note confirm it, as
        Enter does, before the export runs or the focus goes to the
        search box.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        from view.text_note_editor import TextNoteEditor
        _, second_id_i, window = self.two_tabs_one_undocked()
        editor = TextNoteEditor(window)
        editor.show()
        editor.setText("note text")
        editor.selectAll()
        order_list = []
        editor.confirm_requested.connect(
            lambda: order_list.append(("confirm", editor.text(),
                                       editor.hasSelectedText())))
        self.main_window.pdf_export_handler = (
            lambda: order_list.append(("export",)))
        with mock.patch.object(QApplication, "focusWidget",
                               return_value=editor):
            window.pdf_shortcut.activated.emit()
            self.assertEqual(order_list, [("confirm", "note text", False),
                                          ("export",)])
            order_list.clear()
            window.search_shortcut.activated.emit()
            self.process_events()
        self.assertEqual(order_list, [("confirm", "note text", False)])
        window = self.main_window.window_of_tab(second_id_i)
        self.assertIs(window.focusWidget(),
                      window.signal_list_panel.search_box)

    @covers("LLFR-01178", "LLFR-01182", "LLFR-01140", "HLFR-00033",
            "HLFR-00138")
    def test_search_shortcut_leaves_another_search_box(self) -> None:
        """Ctrl+F in an undocked window, with the focus in the main
        window's search box, clears that box's selection and leaves it,
        then focuses the window's own box.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        _, second_id_i, window = self.two_tabs_one_undocked()
        main_box = self.main_window.signal_list_panel.search_box
        main_box.setText("speed")
        main_box.selectAll()
        with mock.patch.object(QApplication, "focusWidget",
                               return_value=main_box):
            window.search_shortcut.activated.emit()
            self.process_events()
        self.assertFalse(main_box.hasSelectedText())
        window = self.main_window.window_of_tab(second_id_i)
        box = window.signal_list_panel.search_box
        self.assertIs(window.focusWidget(), box)
        self.assertEqual(box.selectedText(), "speed")

    @covers("LLFR-01180", "LLFR-01140", "HLFR-00033")
    def test_search_shortcut_in_its_own_search_box(self) -> None:
        """Ctrl+F with the focus already in the window's search box keeps
        the focus there and selects the whole text, without leaving it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        self.main_window.show()
        box = self.main_window.signal_list_panel.search_box
        box.setText("speed")
        box.setSelection(0, 2)
        with mock.patch.object(QApplication, "focusWidget",
                               return_value=box), \
                mock.patch.object(box, "clearFocus") as clear_focus:
            self.main_window.search_shortcut.activated.emit()
            self.process_events()
        clear_focus.assert_not_called()
        self.assertIs(self.main_window.focusWidget(), box)
        self.assertEqual(box.selectedText(), "speed")

    @covers("LLFR-01181", "LLFR-01177", "HLFR-00053", "HLFR-00070")
    def test_signal_dialogs_are_left_alone(self) -> None:
        """The dialogs that create a signal or choose the time signal are
        not name dialogs: Ctrl+P and Ctrl+F in their fields neither
        accept nor close them.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QDialog, QInputDialog, QLineEdit
        from view import synthetic_dialogs
        from view.name_dialog import NameDialogShortcutFilter
        for dialog_class in (synthetic_dialogs.ParameterDialog,
                             synthetic_dialogs.SecondSignalDialog):
            self.assertFalse(issubclass(dialog_class, QInputDialog))
        dialog = QDialog(self.main_window)
        field = QLineEdit(dialog)
        field.setText("2.5")
        dialog.show()
        shortcut_filter = NameDialogShortcutFilter()
        for key_str in ("P", "F"):
            self.assertFalse(shortcut_filter.eventFilter(
                field, key_event(key_str)))
        self.assertTrue(dialog.isVisible())
        self.assertEqual(field.text(), "2.5")
        self.assertEqual(shortcut_filter.action_str, "")
        dialog.hide()
        dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()
