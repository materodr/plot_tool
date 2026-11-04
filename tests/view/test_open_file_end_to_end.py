"""End-to-end tests of the open-file flow (HLFR-00004, HLFR-00117).

A real MainWindow and MainController are used. The file dialog and the
message boxes are patched, so no modal dialog is ever left open.
"""

import os
import tempfile
import unittest
from unittest import mock

from tests.support import expand_all_files
from tests.support import covers, get_qt_application, requires_qt
from tests.support import OPEN_FILE_DIALOG_TARGET_STR


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
        Outputs: the mock that replaced MainWindow.run_open_file_dialog.
            Its ``shown_list`` holds, for each call, the folder (real
            path) and the name filters of the dialog when it was shown.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        shown_list = []

        def answer(dialog) -> str:
            """Record what the dialog shows and answer path_str.

            Inputs:
                dialog: the QFileDialog that would be shown.
            Outputs: path_str.
            """
            shown_list.append((
                os.path.realpath(dialog.directory().absolutePath()),
                dialog.nameFilters()))
            return path_str

        with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                        side_effect=answer) as dialog_mock, \
                mock.patch.object(self.message_box_class, "exec",
                                  new=lambda box: self.fake_exec(box)):
            QTest.mouseClick(self.main_window.top_panel.open_file_button,
                             Qt.MouseButton.LeftButton)
            self.application.processEvents()
            # LLFR-01001: the files are collapsed after an open; these
            # tests read the shown signals.
            expand_all_files(self.controller)
        dialog_mock.shown_list = shown_list
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
        filter_str = ";;".join(dialog_mock.shown_list[0][1])
        for pattern_str in ("*.csv", "*.xlsx", "*.mat", "*.h5", "*.hdf5",
                            "*)"):
            self.assertIn(pattern_str, filter_str)
        self.assertEqual(self.shown_name_list(),
                         ["file1_Time", "file1_speed", "file1_force"])
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
                         ["file1_Time", "file1_speed", "file1_force"])
        self.assertEqual(self.box_record_list, [])
        self.assert_button_finished()

    @covers("LLFR-00008", "LLFR-00010", "LLFR-00011", "LLFR-00003",
            "LLFR-00922", "LLFR-00955")
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
        # LLFR-00922: no question; each time only the error box.
        self.assertEqual([record[0] for record in self.box_record_list], [
            FILE_OPEN_ERROR_TITLE_STR, FILE_OPEN_ERROR_TITLE_STR])
        error_record_list = self.box_record_list
        for _, icon, _ in error_record_list:
            self.assertEqual(icon, self.message_box_class.Icon.Critical)
        self.assertIn("could not be read", error_record_list[0][2])
        self.assertIn("bad.csv", error_record_list[0][2])
        self.assertIn("not supported", error_record_list[1][2])
        self.assertEqual(self.shown_name_list(),
                         ["file1_Time", "file1_speed", "file1_force"])

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

    @covers("LLFR-00920", "LLFR-00921", "LLFR-00922", "LLFR-00650",
            "HLFR-00117", "HLFR-00113")
    def test_second_file_is_added(self) -> None:
        """A second file is added with no box, after the first one.

        Inputs: none.
        Outputs: none.
        """
        self.click_open_file(self.first_path_str)
        self.click_open_file(self.second_path_str)
        self.assertEqual(self.box_record_list, [])
        self.assertEqual(self.shown_name_list(), [
            "file1_Time", "file1_speed", "file1_force", "file2_Time",
            "file2_pressure"])
        # LLFR-00362, LLFR-00938, LLFR-00650: one row per file, in the
        # order of the numbers.
        self.assertEqual(
            self.main_window.signal_list_panel.file_row_texts(),
            ["file1_first.csv", "file2_second.csv"])
        self.assert_button_finished()

    @covers("LLFR-00898", "LLFR-00899", "LLFR-00956", "LLFR-00003",
            "LLFR-00651")
    def test_same_file_is_refused(self) -> None:
        """The same file again shows the information box and keeps the
        open file.

        Inputs: none.
        Outputs: none.
        """
        from view.message_boxes import REFUSED_FILES_TITLE_STR
        self.click_open_file(self.first_path_str)
        self.click_open_file(self.first_path_str)
        self.assertEqual(len(self.box_record_list), 1)
        title_str, icon, text_str = self.box_record_list[0]
        self.assertEqual(title_str, REFUSED_FILES_TITLE_STR)
        self.assertEqual(icon, self.message_box_class.Icon.Information)
        self.assertEqual(text_str, "first.csv: already open as file1.")
        self.assertEqual(self.shown_name_list(),
                         ["file1_Time", "file1_speed", "file1_force"])
        self.assertEqual(len(self.controller.file_controller.data_files), 1)
        self.assert_button_finished()

    @covers("LLFR-00010", "LLFR-00922", "LLFR-00328", "HLFR-00101",
            "LLFR-00511")
    def test_bad_file_after_open_is_read_at_once(self) -> None:
        """With a file open, a bad file is read with no question first.

        Inputs: none.
        Outputs: none.
        """
        from view.message_boxes import FILE_OPEN_ERROR_TITLE_STR
        self.click_open_file(self.first_path_str)
        self.click_open_file(self.bad_path_str)
        self.assertEqual([record[0] for record in self.box_record_list],
                         [FILE_OPEN_ERROR_TITLE_STR])
        self.assertEqual(self.shown_name_list(),
                         ["file1_Time", "file1_speed", "file1_force"])
        self.assertEqual(self.controller.file_controller.current_file
                         .path_str, self.first_path_str)

    @covers("LLFR-00204", "LLFR-00005", "LLFR-00007", "LLFR-00010",
            "LLFR-00447")
    def test_dialog_folder_follows_opened_files(self) -> None:
        """The first dialog shows the app folder, then the last file's.

        Inputs: none.
        Outputs: none.
        """
        from controller.file_controller import first_start_folder_str
        other_folder_str = os.path.join(self.temporary_folder.name, "more")
        os.makedirs(other_folder_str)
        moved_path_str = os.path.join(other_folder_str, "moved.csv")
        with open(moved_path_str, "w", encoding="utf-8") as file:
            file.write("Time,speed\n0,1\n1,2\n")
        broken_folder_str = os.path.join(self.temporary_folder.name,
                                         "broken")
        os.makedirs(broken_folder_str)
        broken_path_str = os.path.join(broken_folder_str, "broken.csv")
        with open(broken_path_str, "w", encoding="utf-8") as file:
            file.write("Time,speed\n0,1\n1,abc\n")
        folder_list = []
        for path_str in ("", self.first_path_str, broken_path_str,
                         moved_path_str, ""):
            self.replace_answer_list.append(True)
            dialog_mock = self.click_open_file(path_str)
            folder_list.append(dialog_mock.shown_list[0][0])
        temporary_folder_str = os.path.dirname(
            os.path.abspath(self.first_path_str))
        self.assertEqual(folder_list, [
            os.path.realpath(folder_str) for folder_str in (
                first_start_folder_str(), first_start_folder_str(),
                temporary_folder_str, temporary_folder_str,
                os.path.abspath(other_folder_str))])


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
        self.main_window.show_signal_names(["file1_Time", "file1_speed"])
        widget = self.main_window.signal_list_panel.signal_list_widget
        widget.itemDoubleClicked.emit(widget.item(1))
        self.assertEqual(name_list, ["file1_speed"])

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
        """ask_open_file_path returns [] when the dialog is cancelled.

        Inputs: none.
        Outputs: none.
        """
        with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                        return_value=""):
            self.assertEqual(self.main_window.ask_open_file_path(), [])
        # The real dialog, cancelled, gives [] too.
        dialog = self.main_window.file_dialog_pool.dialog("open_file")
        with mock.patch.object(dialog, "exec", return_value=0):
            self.assertEqual(self.main_window.ask_open_file_path(), [])

    @covers("LLFR-00204", "LLFR-00005")
    def test_dialog_receives_the_start_folder(self) -> None:
        """ask_open_file_path passes the folder to QFileDialog.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QFileDialog
        temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_folder.cleanup)
        folder_str = temporary_folder.name
        with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                        return_value="/x/y.csv") as dialog_mock:
            self.assertEqual(
                self.main_window.ask_open_file_path(folder_str),
                ["/x/y.csv"])
        dialog = dialog_mock.call_args.args[0]
        self.assertIsInstance(dialog, QFileDialog)
        self.assertEqual(
            os.path.realpath(dialog.directory().absolutePath()),
            os.path.realpath(folder_str))
        self.assertEqual(dialog.acceptMode(),
                         QFileDialog.AcceptMode.AcceptOpen)
        # LLFR-00951: several files can be selected at once.
        self.assertEqual(dialog.fileMode(),
                         QFileDialog.FileMode.ExistingFiles)


if __name__ == "__main__":
    unittest.main()
