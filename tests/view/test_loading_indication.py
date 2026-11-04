"""Tests of the loading indication of the open-file flow (LLFR-00418).

The title of the main window (LLFR-00560, LLFR-00562, LLFR-00563), the
busy pointer of the main window, and the order of the steps of
LLFR-00328 with a real MainWindow and MainController. The file
dialog, the message boxes and the time signal window are patched, so no
modal dialog is left open.
"""

import os
import tempfile
import unittest
from unittest import mock

from tests.support import expand_all_files
from tests.support import (
    OPEN_FILE_DIALOG_TARGET_STR, covers, get_qt_application, requires_qt)

# LLFR-00563: the normal title of the main window.
NORMAL_TITLE_STR = "plot_tool"
# LLFR-00560: the title while a selected file is read and checked.
LOADING_TITLE_STR = "plot_tool (loading)"


def current_cursor_shape():
    """Return the shape of the application's override pointer.

    Inputs: none.
    Outputs: the Qt.CursorShape of the override pointer, or None when
        no override pointer is set (the normal pointer).
    """
    from PyQt6.QtWidgets import QApplication
    cursor = QApplication.overrideCursor()
    if cursor is None:
        return None
    return cursor.shape()


def clear_override_cursors() -> None:
    """Remove every override pointer a failed test may have left.

    Inputs: none.
    Outputs: none.
    """
    from PyQt6.QtWidgets import QApplication
    while QApplication.overrideCursor() is not None:
        QApplication.restoreOverrideCursor()


@requires_qt
class MainWindowLoadingTest(unittest.TestCase):
    """The facade methods that show and hide the indication."""

    def setUp(self) -> None:
        """Create and show a main window.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.main_window import MainWindow
        clear_override_cursors()
        self.main_window = MainWindow()
        self.main_window.show()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close the main window and remove any override pointer.

        Inputs: none.
        Outputs: none.
        """
        clear_override_cursors()
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    @covers("LLFR-00563")
    def test_normal_title_at_start(self) -> None:
        """Before any file is read, the title is the normal title.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.main_window.windowTitle(), NORMAL_TITLE_STR)

    @covers("LLFR-00418", "LLFR-00560", "LLFR-00561", "LLFR-00562")
    def test_show_and_hide_the_indication(self) -> None:
        """Busy pointer and loading title while shown; normal pointer and
        normal title after.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        self.assertIsNone(current_cursor_shape())
        self.main_window.show_loading_indication()
        self.assertEqual(current_cursor_shape(), Qt.CursorShape.WaitCursor)
        self.assertEqual(self.main_window.windowTitle(), LOADING_TITLE_STR)
        self.main_window.hide_loading_indication()
        self.assertIsNone(current_cursor_shape())
        self.assertEqual(self.main_window.windowTitle(), NORMAL_TITLE_STR)

    @covers("LLFR-00094", "LLFR-00560")
    def test_signal_list_panel_unchanged_while_loading(self) -> None:
        """The loading indication adds nothing to the signal list panel:
        the search box stays directly below the list, at the same place.

        Inputs: none.
        Outputs: none.
        """
        panel = self.main_window.signal_list_panel
        layout = panel.panel_layout
        count_i = layout.count()
        box_geometry = panel.search_box.geometry()
        self.main_window.show_loading_indication()
        self.addCleanup(self.main_window.hide_loading_indication)
        self.assertEqual(layout.count(), count_i)
        self.assertEqual(layout.indexOf(panel.search_box),
                         layout.indexOf(panel.signal_list_widget) + 1)
        self.assertEqual(panel.search_box.geometry(), box_geometry)

    @covers("LLFR-00418", "LLFR-00561", "LLFR-00562")
    def test_repeated_calls_restore_the_normal_pointer(self) -> None:
        """Two shows and one hide leave no busy pointer; hide is safe.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.show_loading_indication()
        self.main_window.show_loading_indication()
        self.main_window.hide_loading_indication()
        self.assertIsNone(current_cursor_shape())
        self.main_window.hide_loading_indication()
        self.assertIsNone(current_cursor_shape())
        self.assertEqual(self.main_window.windowTitle(), NORMAL_TITLE_STR)


@requires_qt
class LoadingEndToEndTest(unittest.TestCase):
    """Open files with the real app and watch the indication."""

    def setUp(self) -> None:
        """Create files, the main window and the main controller.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QMessageBox
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        clear_override_cursors()
        self.message_box_class = QMessageBox
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        self.good_path_str = self.write_file(
            "good.csv", "Time,speed\n0,1\n0.5,3\n1,2\n")
        self.bad_path_str = self.write_file(
            "bad.csv", "Time,speed\n0,1\n1,abc\n")
        self.no_time_path_str = self.write_file(
            "no_time.csv", "t_s,force\n0,1\n1,2\n2,3\n")
        self.main_window = MainWindow()
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.main_window.show()
        self.application.processEvents()
        self.panel = self.main_window.signal_list_panel
        # Each entry: (what was shown, override pointer shape, window
        # title) at the moment it was shown.
        self.event_list = []
        self.replace_answer_list = []
        file_controller = self.controller.file_controller
        real_load_function = file_controller.load_function

        def recording_load(path_str: str):
            """Record the indication, then read the file for real.

            Inputs:
                path_str: the path to read.
            Outputs: the SignalFile; raises FileOpenError.
            """
            self.record_event("read")
            return real_load_function(path_str)

        file_controller.load_function = recording_load
        self.main_window.run_modal_dialog = self.fake_run_dialog
        box_patch = mock.patch.object(
            QMessageBox, "exec", new=lambda box: self.fake_exec(box))
        box_patch.start()
        self.addCleanup(box_patch.stop)

    def tearDown(self) -> None:
        """Close the main window and remove any override pointer.

        Inputs: none.
        Outputs: none.
        """
        clear_override_cursors()
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
        with open(path_str, "w", encoding="utf-8") as text_file:
            text_file.write(content_str)
        return path_str

    def record_event(self, name_str: str) -> None:
        """Record the pointer and the window title at this moment.

        Inputs:
            name_str: what is being shown or done.
        Outputs: none.
        """
        self.event_list.append(
            (name_str, current_cursor_shape(),
             self.main_window.windowTitle()))

    def fake_exec(self, box) -> int:
        """Stand-in for QMessageBox.exec that records the indication.

        Inputs:
            box: the QMessageBox being shown.
        Outputs: the next scripted answer of a question, otherwise OK.
        """
        standard_button = self.message_box_class.StandardButton
        if box.icon() == self.message_box_class.Icon.Question:
            self.record_event("question")
            if self.replace_answer_list.pop(0):
                return standard_button.Yes.value
            return standard_button.No.value
        self.record_event("error")
        return standard_button.Ok.value

    def fake_run_dialog(self, dialog) -> bool:
        """Stand-in for the time signal window: record, then cancel.

        Inputs:
            dialog: the window the main window would run.
        Outputs: False (cancelled).
        """
        self.record_event("time window")
        return False

    def open_file(self, path_str: str) -> None:
        """Click Open file with the dialog returning path_str.

        Inputs:
            path_str: the path the patched dialog returns.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                        return_value=path_str):
            QTest.mouseClick(self.main_window.top_panel.open_file_button,
                             Qt.MouseButton.LeftButton)
            self.application.processEvents()
            # LLFR-00987: the files are collapsed after an open; these
            # tests read the shown signals.
            expand_all_files(self.controller)

    @covers("LLFR-00418", "LLFR-00328", "LLFR-00006", "LLFR-00560",
            "LLFR-00562", "LLFR-00563")
    def test_first_file_shows_the_indication_while_read(self) -> None:
        """The first file is read under the busy pointer and the loading
        title; the normal title is back once it is open.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        self.open_file(self.good_path_str)
        self.assertEqual(self.event_list, [
            ("read", Qt.CursorShape.WaitCursor, LOADING_TITLE_STR)])
        self.assertIsNone(current_cursor_shape())
        self.assertEqual(self.main_window.windowTitle(), NORMAL_TITLE_STR)
        self.assertEqual(self.panel.signal_name_list(), ["file1_Time",
                                                         "file1_speed"])

    @covers("LLFR-00418", "LLFR-00328", "LLFR-00010", "LLFR-00922",
            "LLFR-00008", "LLFR-00363", "HLFR-00101", "LLFR-00510",
            "LLFR-00561", "LLFR-00562", "LLFR-00651", "LLFR-00560",
            "LLFR-00563")
    def test_bad_file_after_a_good_one(self) -> None:
        """No question, read under the indication, error box without it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        self.open_file(self.good_path_str)
        self.panel.signal_double_clicked.emit("file1_speed")
        self.application.processEvents()
        plot_panel = self.main_window.plot_panel
        plot_id_list = plot_panel.plot_id_list(plot_panel.current_tab_id())
        self.event_list.clear()
        self.open_file(self.bad_path_str)
        self.assertEqual(self.event_list, [
            ("read", Qt.CursorShape.WaitCursor, LOADING_TITLE_STR),
            ("error", None, NORMAL_TITLE_STR)])
        self.assertIsNone(current_cursor_shape())
        self.assertEqual(self.main_window.windowTitle(), NORMAL_TITLE_STR)
        # LLFR-00010, LLFR-00363: the good file, its list, its plot and
        # its name row are kept.
        self.assertEqual(self.panel.signal_name_list(), ["file1_Time",
                                                         "file1_speed"])
        self.assertEqual(self.panel.file_row_texts(), ["file1_good.csv"])
        self.assertEqual(
            plot_panel.plot_id_list(plot_panel.current_tab_id()),
            plot_id_list)
        self.assertEqual(len(plot_id_list), 1)
        self.assertTrue(self.main_window.top_panel.undo_button.isEnabled())
        self.assertEqual(self.controller.file_controller.current_file
                         .path_str, self.good_path_str)

    @covers("LLFR-00418", "LLFR-00898", "LLFR-00328", "LLFR-00563",
            "LLFR-00956")
    def test_file_already_open_is_not_read(self) -> None:
        """The same file again: no read, no indication, one box.

        Inputs: none.
        Outputs: none.
        """
        self.open_file(self.good_path_str)
        self.event_list.clear()
        self.open_file(self.good_path_str)
        self.assertEqual(self.event_list,
                         [("error", None, NORMAL_TITLE_STR)])
        self.assertEqual(self.main_window.windowTitle(), NORMAL_TITLE_STR)
        self.assertEqual(self.panel.signal_name_list(),
                         ["file1_Time", "file1_speed"])

    @covers("LLFR-00418", "LLFR-00327", "LLFR-00328", "LLFR-00010",
            "LLFR-00325", "LLFR-00561", "LLFR-00562", "LLFR-00560",
            "LLFR-00563")
    def test_time_window_shown_after_the_indication(self) -> None:
        """Read, then the window without the indication; cancel.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        self.open_file(self.good_path_str)
        self.event_list.clear()
        self.open_file(self.no_time_path_str)
        self.assertEqual(self.event_list, [
            ("read", Qt.CursorShape.WaitCursor, LOADING_TITLE_STR),
            ("time window", None, NORMAL_TITLE_STR)])
        self.assertIsNone(current_cursor_shape())
        self.assertEqual(self.panel.signal_name_list(), ["file1_Time",
                                                         "file1_speed"])
        self.assertEqual(self.panel.file_row_texts(), ["file1_good.csv"])
        self.assertEqual(self.main_window.windowTitle(), NORMAL_TITLE_STR)

    @covers("LLFR-00560", "LLFR-00562", "LLFR-00563", "LLFR-00561",
            "LLFR-00510", "LLFR-00008")
    def test_bad_first_file_title(self) -> None:
        """A bad first file: loading title while read, normal title in
        the error box and after it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        self.open_file(self.bad_path_str)
        self.assertEqual(self.event_list, [
            ("read", Qt.CursorShape.WaitCursor, LOADING_TITLE_STR),
            ("error", None, NORMAL_TITLE_STR)])
        self.assertEqual(self.main_window.windowTitle(), NORMAL_TITLE_STR)
        self.assertEqual(self.panel.signal_name_list(), [])

    @covers("LLFR-00560", "LLFR-00562", "LLFR-00563", "LLFR-00561",
            "LLFR-00325", "LLFR-00512")
    def test_cancelled_time_window_for_a_first_file_title(self) -> None:
        """A first file with no time signal: loading title while read,
        normal title in the time signal window and after its cancel.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        self.open_file(self.no_time_path_str)
        self.assertEqual(self.event_list, [
            ("read", Qt.CursorShape.WaitCursor, LOADING_TITLE_STR),
            ("time window", None, NORMAL_TITLE_STR)])
        self.assertEqual(self.main_window.windowTitle(), NORMAL_TITLE_STR)
        self.assertEqual(self.panel.signal_name_list(), [])

    @covers("LLFR-00560", "LLFR-00562", "LLFR-00563")
    def test_title_after_two_good_files(self) -> None:
        """Each read of a good file, with or without another file open,
        shows the loading title, and the normal title is back after each.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        other_path_str = self.write_file(
            "other.csv", "Time,force\n0,1\n1,2\n")
        self.open_file(self.good_path_str)
        self.assertEqual(self.main_window.windowTitle(), NORMAL_TITLE_STR)
        self.open_file(other_path_str)
        self.assertEqual(self.event_list, [
            ("read", Qt.CursorShape.WaitCursor, LOADING_TITLE_STR),
            ("read", Qt.CursorShape.WaitCursor, LOADING_TITLE_STR)])
        self.assertEqual(self.main_window.windowTitle(), NORMAL_TITLE_STR)


if __name__ == "__main__":
    unittest.main()
