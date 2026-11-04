"""Tests for the message boxes (HLFR-00002, LLFR-00032, LLFR-00952).

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

    @covers("LLFR-00211", "LLFR-00657")
    def test_tab_name_taken_box_content(self) -> None:
        """The tab name box is information and names the taken name.

        Inputs: none.
        Outputs: none.
        """
        box = self.message_module.build_tab_name_taken_box(
            self.parent_widget, "Engine")
        self.assertEqual(box.icon(),
                         self.message_box_class.Icon.Information)
        self.assertNotEqual(box.icon(),
                            self.message_box_class.Icon.Critical)
        self.assertEqual(box.windowTitle(), "Rename Tab")
        self.assertIn("'Engine'", box.text())
        self.assertIn("already exists", box.text())
        self.assertEqual(self.button_value_set(box),
                         {self.message_box_class.StandardButton.Ok.value})

    @covers("LLFR-00211", "LLFR-00657")
    def test_show_tab_name_taken_notification_runs_box(self) -> None:
        """``show_tab_name_taken_notification`` runs the information box.

        Inputs: none.
        Outputs: none.
        """
        ok_value_i = self.message_box_class.StandardButton.Ok.value
        with self.patch_exec(ok_value_i):
            self.message_module.show_tab_name_taken_notification(
                self.parent_widget, "Tab 1")
        self.assertEqual(len(self.shown_box_list), 1)
        shown_box = self.shown_box_list[0]
        self.assertEqual(shown_box.icon(),
                         self.message_box_class.Icon.Information)
        self.assertEqual(
            shown_box.text(),
            self.message_module.TAB_NAME_TAKEN_MESSAGE_STR.format(
                name="Tab 1"))

    @covers("LLFR-00892")
    def test_open_files_limit_box_content(self) -> None:
        """The limit box is an information box with OK.

        Inputs: none.
        Outputs: none.
        """
        standard_button_class = self.message_box_class.StandardButton
        box = self.message_module.build_open_files_limit_box(
            self.parent_widget, "10 files are already open.")
        self.assertEqual(box.icon(), self.message_box_class.Icon.Information)
        self.assertEqual(box.windowTitle(),
                         self.message_module.OPEN_FILES_LIMIT_TITLE_STR)
        self.assertEqual(box.text(), "10 files are already open.")
        self.assertEqual(self.button_value_set(box),
                         {standard_button_class.Ok.value})

    @covers("LLFR-00952")
    def test_refused_files_box_content(self) -> None:
        """The box of the refused files is an information box with OK.

        Inputs: none.
        Outputs: none.
        """
        standard_button_class = self.message_box_class.StandardButton
        box = self.message_module.build_refused_files_box(
            self.parent_widget, "a.csv: already open as file1.")
        self.assertEqual(box.icon(), self.message_box_class.Icon.Information)
        self.assertEqual(box.windowTitle(),
                         self.message_module.REFUSED_FILES_TITLE_STR)
        self.assertEqual(box.text(), "a.csv: already open as file1.")
        self.assertEqual(self.button_value_set(box),
                         {standard_button_class.Ok.value})

    def close_open_boxes(self) -> None:
        """Reject any open message box, so a failing test never hangs.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, self.message_box_class):
                widget.reject()


@requires_qt
class CloseFilesBoxTest(unittest.TestCase):
    """The questions of the file menu (LLFR-00920, LLFR-00930)."""

    def setUp(self) -> None:
        """Start Qt.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()

    @covers("LLFR-00920", "LLFR-00921", "HLFR-00118")
    def test_close_file_box(self) -> None:
        """The question of the file controller, with Yes and No.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        from controller.file_controller import close_file_question
        from view import message_boxes
        question_str = close_file_question("file2_run_B.mat", False)
        box = message_boxes.build_close_file_box(None, question_str)
        self.assertEqual(box.windowTitle(), "Close file")
        self.assertEqual(box.text(), question_str)
        self.assertIn("file2_run_B.mat", box.text())
        self.assertEqual(box.icon(), QMessageBox.Icon.Question)
        self.assertEqual(box.standardButtons(),
                         QMessageBox.StandardButton.Yes
                         | QMessageBox.StandardButton.No)
        self.assertIs(box.defaultButton(),
                      box.button(QMessageBox.StandardButton.No))
        box.deleteLater()
        for answer, expected_b in (
                (QMessageBox.StandardButton.Yes.value, True),
                (QMessageBox.StandardButton.No.value, False)):
            with self.subTest(expected_b=expected_b), mock.patch.object(
                    QMessageBox, "exec", return_value=answer):
                self.assertIs(message_boxes.ask_close_file(
                    None, question_str), expected_b)

    @covers("LLFR-00930", "LLFR-00931", "HLFR-00119")
    def test_close_all_files_box(self) -> None:
        """One question for every file, with Yes and No.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        from controller.file_controller import close_all_files_question
        from view import message_boxes
        question_str = close_all_files_question()
        box = message_boxes.build_close_all_files_box(None, question_str)
        self.assertEqual(box.windowTitle(), "Close all files")
        self.assertEqual(box.text(), question_str)
        self.assertIn("Every flag and every area will be deleted",
                      box.text())
        box.deleteLater()
        with mock.patch.object(QMessageBox, "exec",
                               return_value=QMessageBox.StandardButton.No):
            self.assertFalse(message_boxes.ask_close_all_files(
                None, question_str))
        with mock.patch.object(QMessageBox, "exec",
                               return_value=QMessageBox.StandardButton.Yes):
            self.assertTrue(message_boxes.ask_close_all_files(
                None, question_str))

    @covers("LLFR-00920", "LLFR-00930")
    def test_main_window_asks_with_the_boxes(self) -> None:
        """The main window facade returns the user's answer.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        from view.main_window import MainWindow
        window = MainWindow()
        self.addCleanup(window.deleteLater)
        record_list = []

        def fake_exec(box) -> int:
            """Record the box and answer Yes.

            Inputs:
                box: the QMessageBox.
            Outputs: Yes.
            """
            record_list.append((box.windowTitle(), box.text()))
            return QMessageBox.StandardButton.Yes.value

        with mock.patch.object(QMessageBox, "exec", new=fake_exec):
            self.assertTrue(window.ask_close_file("Close file1_a.csv?"))
            self.assertTrue(window.ask_close_all_files("Close all?"))
        self.assertEqual(record_list, [("Close file", "Close file1_a.csv?"),
                                       ("Close all files", "Close all?")])


if __name__ == "__main__":
    unittest.main()
