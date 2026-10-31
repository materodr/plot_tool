"""End-to-end tests of the open-file flow (HLFR-00004, HLFR-00010).

A real MainWindow and MainController are used. The file dialog and the
message boxes are patched, so no modal dialog is ever left open.
"""

import os
import tempfile
import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt


@requires_qt
class OpenFileEndToEndTest(unittest.TestCase):
    """Click the Open file button and check the whole flow."""

    def setUp(self) -> None:
        """Create temp files, the main window and the main controller.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QMessageBox
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.message_box_class = QMessageBox
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        self.first_path_str = self.write_file(
            "first.csv", "Time,speed,force\n0,1,2\n0.5,3,4\n")
        self.second_path_str = self.write_file(
            "second.csv", "Time,pressure\n0,1\n1,2\n")
        self.bad_path_str = self.write_file(
            "bad.csv", "Time,speed\n0,1\n1,abc\n")
        self.text_path_str = self.write_file("notes.txt", "hello")
        self.main_window = MainWindow()
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.application.processEvents()
        self.box_record_list = []
        self.replace_answer_list = []

    def tearDown(self) -> None:
        """Close the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def write_file(self, name_str: str, content_str: str) -> str:
        """Write a text file in the temporary folder.

        Inputs:
            name_str: file name.
            content_str: file content.
        Outputs: the full path of the file.
        """
        path_str = os.path.join(self.temporary_folder.name, name_str)
        with open(path_str, "w", encoding="utf-8") as file:
            file.write(content_str)
        return path_str

    def fake_exec(self, box) -> int:
        """Stand-in for QMessageBox.exec that records the box.

        Inputs:
            box: the QMessageBox being shown.
        Outputs: the next scripted answer for a question box (Yes or No
            as an int), otherwise the value of the OK button.
        """
        self.box_record_list.append(
            (box.windowTitle(), box.icon(), box.text()))
        standard_button = self.message_box_class.StandardButton
        if box.icon() == self.message_box_class.Icon.Question:
            if self.replace_answer_list.pop(0):
                return standard_button.Yes.value
            return standard_button.No.value
        return standard_button.Ok.value

    def click_open_file(self, path_str: str) -> mock.MagicMock:
        """Click Open file with the dialog returning path_str.

        Inputs:
            path_str: the path the patched dialog returns ("" cancels).
        Outputs: the mock that replaced QFileDialog.getOpenFileName.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QFileDialog
        with mock.patch.object(
                QFileDialog, "getOpenFileName",
                return_value=(path_str, "")) as dialog_mock, \
                mock.patch.object(self.message_box_class, "exec",
                                  new=lambda box: self.fake_exec(box)):
            QTest.mouseClick(self.main_window.top_panel.open_file_button,
                             Qt.MouseButton.LeftButton)
            self.application.processEvents()
        return dialog_mock

    def shown_name_list(self) -> list:
        """Return the names in the signal list panel.

        Inputs: none.
        Outputs: a list of str.
        """
        return self.main_window.signal_list_panel.signal_name_list()

    def assert_button_finished(self) -> None:
        """Check that the Open file button is back to normal.

        Inputs: none.
        Outputs: none.
        """
        from view.toggle_button import NORMAL_COLOR_STR
        button = self.main_window.top_panel.open_file_button
        self.assertFalse(button.is_active())
        self.assertEqual(button.current_background_color_str(),
                         NORMAL_COLOR_STR)

    @covers("LLFR-00005", "LLFR-00006", "LLFR-00054", "LLFR-00003",
            "LLFR-00004")
    def test_open_valid_file_shows_signal_names(self) -> None:
        """Clicking Open file shows the dialog and lists the signals.

        Inputs: none.
        Outputs: none.
        """
        dialog_mock = self.click_open_file(self.first_path_str)
        self.assertEqual(dialog_mock.call_count, 1)
        filter_str = dialog_mock.call_args.args[3]
        for pattern_str in ("*.csv", "*.xlsx", "*.mat", "*)"):
            self.assertIn(pattern_str, filter_str)
        self.assertEqual(self.shown_name_list(),
                         ["Time", "speed", "force"])
        self.assertEqual(self.box_record_list, [])
        self.assert_button_finished()
        self.assertEqual(self.controller.file_controller.current_file
                         .path_str, self.first_path_str)

    @covers("LLFR-00007", "LLFR-00003")
    def test_cancel_keeps_everything(self) -> None:
        """Cancelling the dialog keeps the open file and its list.

        Inputs: none.
        Outputs: none.
        """
        self.click_open_file(self.first_path_str)
        self.click_open_file("")
        self.assertEqual(self.shown_name_list(),
                         ["Time", "speed", "force"])
        self.assertEqual(self.box_record_list, [])
        self.assert_button_finished()

    @covers("LLFR-00008", "LLFR-00010", "LLFR-00011", "LLFR-00003")
    def test_bad_files_show_error_and_keep_list(self) -> None:
        """Bad files show the File Open Error box; the list is kept.

        Inputs: none.
        Outputs: none.
        """
        from view.message_boxes import FILE_OPEN_ERROR_TITLE_STR
        self.click_open_file(self.first_path_str)
        self.click_open_file(self.bad_path_str)
        self.assert_button_finished()
        self.click_open_file(self.text_path_str)
        self.assert_button_finished()
        self.assertEqual(len(self.box_record_list), 2)
        for title_str, icon, _ in self.box_record_list:
            self.assertEqual(title_str, FILE_OPEN_ERROR_TITLE_STR)
            self.assertEqual(icon, self.message_box_class.Icon.Critical)
        self.assertIn("could not be read", self.box_record_list[0][2])
        self.assertIn("bad.csv", self.box_record_list[0][2])
        self.assertIn("not supported", self.box_record_list[1][2])
        self.assertEqual(self.shown_name_list(),
                         ["Time", "speed", "force"])

    @covers("LLFR-00009", "LLFR-00010")
    def test_missing_file_shows_access_error(self) -> None:
        """A path that does not exist shows the access error.

        Inputs: none.
        Outputs: none.
        """
        self.click_open_file(os.path.join(self.temporary_folder.name,
                                          "missing.csv"))
        self.assertEqual(len(self.box_record_list), 1)
        self.assertIn("could not be accessed", self.box_record_list[0][2])
        self.assertEqual(self.shown_name_list(), [])
        self.assert_button_finished()

    @covers("LLFR-00013", "LLFR-00017", "HLFR-00010")
    def test_replace_yes_shows_new_file(self) -> None:
        """Yes in the Replace File box shows only the new names.

        Inputs: none.
        Outputs: none.
        """
        from view.message_boxes import REPLACE_FILE_TITLE_STR
        self.click_open_file(self.first_path_str)
        self.replace_answer_list = [True]
        self.click_open_file(self.second_path_str)
        self.assertEqual(len(self.box_record_list), 1)
        self.assertEqual(self.box_record_list[0][0], REPLACE_FILE_TITLE_STR)
        self.assertEqual(self.shown_name_list(), ["Time", "pressure"])
        self.assert_button_finished()

    @covers("LLFR-00014", "HLFR-00010", "LLFR-00003")
    def test_replace_no_keeps_current_file(self) -> None:
        """No in the Replace File box keeps the current names.

        Inputs: none.
        Outputs: none.
        """
        self.click_open_file(self.first_path_str)
        self.replace_answer_list = [False]
        self.click_open_file(self.second_path_str)
        self.assertEqual(len(self.box_record_list), 1)
        self.assertEqual(self.shown_name_list(),
                         ["Time", "speed", "force"])
        self.assertEqual(self.controller.file_controller.current_file
                         .path_str, self.first_path_str)
        self.assert_button_finished()

    @covers("HLFR-00010", "LLFR-00010")
    def test_bad_file_after_open_does_not_ask_replace(self) -> None:
        """A file that can't be opened never shows the Replace File box.

        Inputs: none.
        Outputs: none.
        """
        from view.message_boxes import FILE_OPEN_ERROR_TITLE_STR
        self.click_open_file(self.first_path_str)
        self.click_open_file(self.bad_path_str)
        self.assertEqual([record[0] for record in self.box_record_list],
                         [FILE_OPEN_ERROR_TITLE_STR])


@requires_qt
class MainWindowFacadeTest(unittest.TestCase):
    """Check the facade methods of MainWindow not used by the flow."""

    def setUp(self) -> None:
        """Create a main window.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.main_window import MainWindow
        self.main_window = MainWindow()
        self.main_window.show()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    @covers("LLFR-00018", "LLFR-00001", "LLFR-00002")
    def test_tip_handler_receives_state(self) -> None:
        """The plot tool handler gets "tip", then "" on deactivation.

        Inputs: none.
        Outputs: none.
        """
        state_list = []
        self.main_window.set_plot_tool_handler(state_list.append)
        tip_button = self.main_window.top_panel.tip_button
        tip_button.click()
        tip_button.click()
        self.assertEqual(state_list, ["tip", ""])

    @covers("LLFR-00019")
    def test_double_click_handler_receives_name(self) -> None:
        """The double-click handler gets the double-clicked name.

        Inputs: none.
        Outputs: none.
        """
        name_list = []
        self.main_window.set_signal_double_click_handler(name_list.append)
        self.main_window.show_signal_names(["Time", "speed"])
        widget = self.main_window.signal_list_panel.signal_list_widget
        widget.itemDoubleClicked.emit(widget.item(1))
        self.assertEqual(name_list, ["speed"])

    @covers("LLFR-00003", "LLFR-00005")
    def test_open_file_without_handler_finishes_button(self) -> None:
        """Without a handler the Open file button returns to normal.

        Inputs: none.
        Outputs: none.
        """
        button = self.main_window.top_panel.open_file_button
        button.click()
        self.assertFalse(button.is_active())

    @covers("LLFR-00007")
    def test_cancelled_dialog_returns_empty_path(self) -> None:
        """ask_open_file_path returns "" when the dialog is cancelled.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QFileDialog
        with mock.patch.object(QFileDialog, "getOpenFileName",
                               return_value=("", "")):
            self.assertEqual(self.main_window.ask_open_file_path(), "")


if __name__ == "__main__":
    unittest.main()
