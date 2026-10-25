"""Tests for the message boxes (HLFR-00002, LLFR-00032, HLFR-00010).

The modal ``exec`` is always patched, so no test waits for a user.
"""

import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt


@requires_qt
class MessageBoxesTest(unittest.TestCase):
    """Check the content of each box and the answers of the dialogs."""

    def setUp(self) -> None:
        """Get the application and import the module under test.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QMessageBox, QWidget
        from view import message_boxes
        self.message_module = message_boxes
        self.message_box_class = QMessageBox
        self.parent_widget = QWidget()

    def tearDown(self) -> None:
        """Delete the parent widget.

        Inputs: none.
        Outputs: none.
        """
        self.parent_widget.deleteLater()
        self.application.processEvents()

    def button_value_set(self, box) -> set:
        """Return the standard buttons of a box as a set of int values.

        Inputs:
            box: a QMessageBox.
        Outputs: a set with the int value of each standard button.
        """
        standard_button_class = self.message_box_class.StandardButton
        return {box.standardButton(button).value
                for button in box.buttons()
                if box.standardButton(button)
                != standard_button_class.NoButton}

    def patch_exec(self, return_value):
        """Patch QMessageBox.exec so it returns at once.

        The boxes that would have been shown are stored in
        ``self.shown_box_list``.

        Inputs:
            return_value: the value exec returns.
        Outputs: the patcher context manager.
        """
        self.shown_box_list = []

        def fake_exec(box):
            """Record the box instead of showing it.

            Inputs:
                box: the QMessageBox whose exec was called.
            Outputs: return_value.
            """
            self.shown_box_list.append(box)
            return return_value

        return mock.patch.object(self.message_box_class, "exec", fake_exec)

    @covers("HLFR-00002")
    def test_file_open_error_box_content(self) -> None:
        """The error box is critical, titled and shows the given message.

        Inputs: none.
        Outputs: none.
        """
        message_str = "The file could not be read: data.csv"
        box = self.message_module.build_file_open_error_box(
            self.parent_widget, message_str)
        self.assertEqual(box.icon(), self.message_box_class.Icon.Critical)
        self.assertEqual(box.windowTitle(), "File Open Error")
        self.assertEqual(self.message_module.FILE_OPEN_ERROR_TITLE_STR,
                         "File Open Error")
        self.assertEqual(box.text(), message_str)
        self.assertEqual(self.button_value_set(box),
                         {self.message_box_class.StandardButton.Ok.value})
        self.assertIs(box.parent(), self.parent_widget)

    @covers("HLFR-00002")
    def test_file_open_error_box_without_parent(self) -> None:
        """The error box can be built without a parent widget.

        Inputs: none.
        Outputs: none.
        """
        box = self.message_module.build_file_open_error_box(
            None, "The file format is not supported.")
        self.assertIsNone(box.parent())
        self.assertEqual(box.text(), "The file format is not supported.")
        box.deleteLater()

    @covers("HLFR-00002")
    def test_show_file_open_error_runs_box(self) -> None:
        """``show_file_open_error`` runs one box with the given message.

        Inputs: none.
        Outputs: none.
        """
        ok_value_i = self.message_box_class.StandardButton.Ok.value
        with self.patch_exec(ok_value_i):
            result = self.message_module.show_file_open_error(
                self.parent_widget, "could not be accessed")
        self.assertIsNone(result)
        self.assertEqual(len(self.shown_box_list), 1)
        shown_box = self.shown_box_list[0]
        self.assertEqual(shown_box.text(), "could not be accessed")
        self.assertEqual(shown_box.icon(),
                         self.message_box_class.Icon.Critical)

    @covers("LLFR-00032")
    def test_full_tab_box_content(self) -> None:
        """The full tab box is information and tells what to do.

        Inputs: none.
        Outputs: none.
        """
        box = self.message_module.build_full_tab_box(self.parent_widget)
        self.assertEqual(box.icon(),
                         self.message_box_class.Icon.Information)
        self.assertNotEqual(box.icon(),
                            self.message_box_class.Icon.Critical)
        self.assertEqual(box.windowTitle(), "Full Tab")
        text_str = box.text().lower()
        self.assertIn("add a new tab", text_str)
        self.assertIn("delete a plot", text_str)
        self.assertIn("5", text_str)
        self.assertEqual(self.button_value_set(box),
                         {self.message_box_class.StandardButton.Ok.value})

    @covers("LLFR-00032")
    def test_show_full_tab_notification_runs_box(self) -> None:
        """``show_full_tab_notification`` runs the information box.

        Inputs: none.
        Outputs: none.
        """
        ok_value_i = self.message_box_class.StandardButton.Ok.value
        with self.patch_exec(ok_value_i):
            self.message_module.show_full_tab_notification(
                self.parent_widget)
        self.assertEqual(len(self.shown_box_list), 1)
        shown_box = self.shown_box_list[0]
        self.assertEqual(shown_box.icon(),
                         self.message_box_class.Icon.Information)
        self.assertEqual(shown_box.text(),
                         self.message_module.FULL_TAB_MESSAGE_STR)

    @covers("HLFR-00010")
    def test_replace_file_box_content(self) -> None:
        """The replace box asks a question with Yes and No, No by default.

        Inputs: none.
        Outputs: none.
        """
        standard_button_class = self.message_box_class.StandardButton
        box = self.message_module.build_replace_file_box(self.parent_widget)
        self.assertEqual(box.icon(), self.message_box_class.Icon.Question)
        self.assertEqual(box.windowTitle(), "Replace File")
        text_str = box.text().lower()
        self.assertIn("close the current file", text_str)
        self.assertIn("proceed", text_str)
        self.assertEqual(self.button_value_set(box),
                         {standard_button_class.Yes.value,
                          standard_button_class.No.value})
        self.assertIs(box.defaultButton(),
                      box.button(standard_button_class.No))
        self.assertIs(box.escapeButton(),
                      box.button(standard_button_class.No))

    @covers("HLFR-00010")
    def test_ask_replace_file_yes_int(self) -> None:
        """Choosing Yes (int return of exec) gives True.

        Inputs: none.
        Outputs: none.
        """
        yes_value_i = self.message_box_class.StandardButton.Yes.value
        with self.patch_exec(yes_value_i):
            answer_b = self.message_module.ask_replace_file(
                self.parent_widget)
        self.assertIs(answer_b, True)
        self.assertEqual(len(self.shown_box_list), 1)
        self.assertEqual(self.shown_box_list[0].windowTitle(),
                         "Replace File")

    @covers("HLFR-00010")
    def test_ask_replace_file_no_int(self) -> None:
        """Choosing No (int return of exec) gives False.

        Inputs: none.
        Outputs: none.
        """
        no_value_i = self.message_box_class.StandardButton.No.value
        with self.patch_exec(no_value_i):
            answer_b = self.message_module.ask_replace_file(
                self.parent_widget)
        self.assertIs(answer_b, False)

    @covers("HLFR-00010")
    def test_ask_replace_file_enum_return(self) -> None:
        """An enum return of exec is understood for Yes and for No.

        Inputs: none.
        Outputs: none.
        """
        standard_button_class = self.message_box_class.StandardButton
        with self.patch_exec(standard_button_class.Yes):
            self.assertIs(self.message_module.ask_replace_file(None), True)
        with self.patch_exec(standard_button_class.No):
            self.assertIs(self.message_module.ask_replace_file(None), False)

    @covers("HLFR-00010")
    def test_ask_replace_file_closed_box(self) -> None:
        """Closing the box without an answer keeps the file (False).

        Inputs: none.
        Outputs: none.
        """
        escape_value_i = self.message_box_class.StandardButton.NoButton.value
        with self.patch_exec(escape_value_i):
            answer_b = self.message_module.ask_replace_file(
                self.parent_widget)
        self.assertIs(answer_b, False)

    @covers("HLFR-00010")
    def test_ask_replace_file_real_yes_click(self) -> None:
        """A real click on Yes, made while the box runs, gives True.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication
        standard_button_class = self.message_box_class.StandardButton

        def click_yes() -> None:
            """Click Yes on the open replace box.

            Inputs: none.
            Outputs: none.
            """
            for widget in QApplication.topLevelWidgets():
                if (isinstance(widget, self.message_box_class)
                        and widget.isVisible()):
                    widget.button(standard_button_class.Yes).click()

        QTimer.singleShot(50, click_yes)
        safety_timer = QTimer()
        safety_timer.setSingleShot(True)
        safety_timer.timeout.connect(self.close_open_boxes)
        safety_timer.start(3000)
        answer_b = self.message_module.ask_replace_file(None)
        safety_timer.stop()
        self.assertIs(answer_b, True)

    def close_open_boxes(self) -> None:
        """Reject any open message box, so a failing test never hangs.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, self.message_box_class):
                widget.reject()


if __name__ == "__main__":
    unittest.main()
