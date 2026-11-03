"""Tests of the loading indication of the open-file flow (LLFR-00418).

The status line of the signal list panel, the busy pointer of the main
window, and the order of the steps of LLFR-00328 with a real
MainWindow and MainController. The file dialog, the message boxes and
the time signal window are patched, so no modal dialog is left open.
"""

import os
import tempfile
import unittest
from unittest import mock

from tests.support import (
    OPEN_FILE_DIALOG_TARGET_STR, covers, get_qt_application, requires_qt)


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
class StatusLineTest(unittest.TestCase):
    """The status line at the bottom of the signal list panel."""

    def setUp(self) -> None:
        """Create and show a signal list panel.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.signal_list_panel import SignalListPanel
        self.panel = SignalListPanel()
        self.panel.resize(260, 500)
        self.panel.show()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close the panel.

        Inputs: none.
        Outputs: none.
        """
        self.panel.close()
        self.panel.deleteLater()
        self.application.processEvents()

    @covers("LLFR-00418", "LLFR-00094", "LLFR-00560")
    def test_status_line_below_the_search_box(self) -> None:
        """The status line is the last row, under the search box.

        Inputs: none.
        Outputs: none.
        """
        layout = self.panel.panel_layout
        status_label = self.panel.status_label
        search_box = self.panel.search_box
        self.assertEqual(layout.indexOf(status_label), layout.count() - 1)
        self.assertEqual(layout.indexOf(status_label),
                         layout.indexOf(search_box) + 1)
        self.assertTrue(status_label.isVisible())
        self.assertGreaterEqual(status_label.geometry().top(),
                                search_box.geometry().bottom())
        # LLFR-00418: at the bottom of the panel.
        self.assertLessEqual(status_label.geometry().bottom(),
                             self.panel.height())
        self.assertLess(self.panel.height()
                        - status_label.geometry().bottom(), 20)

    @covers("LLFR-00418", "LLFR-00560", "LLFR-00562", "LLFR-00563")
    def test_status_line_empty_except_while_loading(self) -> None:
        """No text at start; the text is shown and removed on request.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.panel.status_text(), "")
        height_i = self.panel.status_label.height()
        self.assertGreater(height_i, 0)
        self.panel.show_status_text("Loading...")
        self.application.processEvents()
        self.assertEqual(self.panel.status_text(), "Loading...")
        self.assertEqual(self.panel.status_label.text(), "Loading...")
        self.panel.show_status_text("")
        self.application.processEvents()
        self.assertEqual(self.panel.status_text(), "")
        # The empty line keeps its height, so the list does not move.
        self.assertEqual(self.panel.status_label.height(), height_i)


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

    @covers("LLFR-00418", "LLFR-00560", "LLFR-00561")
    def test_show_and_hide_the_indication(self) -> None:
        """Busy pointer and text while shown; normal pointer after.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        panel = self.main_window.signal_list_panel
        self.assertIsNone(current_cursor_shape())
        self.main_window.show_loading_indication("Loading...")
        self.assertEqual(current_cursor_shape(), Qt.CursorShape.WaitCursor)
        self.assertEqual(panel.status_text(), "Loading...")
        self.main_window.hide_loading_indication()
        self.assertIsNone(current_cursor_shape())
        self.assertEqual(panel.status_text(), "")

    @covers("LLFR-00418", "LLFR-00561")
    def test_repeated_calls_restore_the_normal_pointer(self) -> None:
        """Two shows and one hide leave no busy pointer; hide is safe.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.show_loading_indication("Loading...")
        self.main_window.show_loading_indication("Loading...")
        self.main_window.hide_loading_indication()
        self.assertIsNone(current_cursor_shape())
        self.main_window.hide_loading_indication()
        self.assertIsNone(current_cursor_shape())
        self.assertEqual(self.main_window.signal_list_panel.status_text(),
                         "")


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
        # Each entry: (what was shown, override pointer shape, status
        # line text) at the moment it was shown.
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
        """Record the pointer and the status text at this moment.

        Inputs:
            name_str: what is being shown or done.
        Outputs: none.
        """
        self.event_list.append(
            (name_str, current_cursor_shape(), self.panel.status_text()))

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

    @covers("LLFR-00418", "LLFR-00328", "LLFR-00006", "LLFR-00560")
    def test_first_file_shows_the_indication_while_read(self) -> None:
        """The first file is read under the busy pointer and the text.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        self.open_file(self.good_path_str)
        self.assertEqual(self.event_list, [
            ("read", Qt.CursorShape.WaitCursor, "Loading...")])
        self.assertIsNone(current_cursor_shape())
        self.assertEqual(self.panel.status_text(), "")
        self.assertEqual(self.panel.signal_name_list(), ["Time", "speed"])

    @covers("LLFR-00418", "LLFR-00328", "LLFR-00010", "LLFR-00013",
            "LLFR-00008", "LLFR-00363", "HLFR-00010", "HLFR-00101",
            "LLFR-00448", "LLFR-00510", "LLFR-00561", "LLFR-00562",
            "LLFR-00651")
    def test_bad_file_after_a_good_one(self) -> None:
        """Yes, read under the indication, error box without it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        self.open_file(self.good_path_str)
        self.panel.signal_double_clicked.emit("speed")
        self.application.processEvents()
        plot_panel = self.main_window.plot_panel
        plot_id_list = plot_panel.plot_id_list(plot_panel.current_tab_id())
        self.event_list.clear()
        self.replace_answer_list = [True]
        self.open_file(self.bad_path_str)
        self.assertEqual(self.event_list, [
            ("question", None, ""),
            ("read", Qt.CursorShape.WaitCursor, "Loading..."),
            ("error", None, "")])
        self.assertIsNone(current_cursor_shape())
        self.assertEqual(self.panel.status_text(), "")
        # LLFR-00010, LLFR-00363: the good file, its list, its plot and
        # its name row are kept.
        self.assertEqual(self.panel.signal_name_list(), ["Time", "speed"])
        self.assertEqual(self.panel.file_name(), "good.csv")
        self.assertEqual(
            plot_panel.plot_id_list(plot_panel.current_tab_id()),
            plot_id_list)
        self.assertEqual(len(plot_id_list), 1)
        self.assertTrue(self.main_window.top_panel.undo_button.isEnabled())
        self.assertEqual(self.controller.file_controller.current_file
                         .path_str, self.good_path_str)

    @covers("LLFR-00418", "LLFR-00014", "LLFR-00328", "LLFR-00449",
            "LLFR-00450", "LLFR-00564")
    def test_declined_replace_reads_nothing(self) -> None:
        """No in the question: no read, no indication, no other box.

        Inputs: none.
        Outputs: none.
        """
        self.open_file(self.good_path_str)
        self.event_list.clear()
        self.replace_answer_list = [False]
        self.open_file(self.bad_path_str)
        self.assertEqual(self.event_list, [("question", None, "")])
        self.assertEqual(self.panel.status_text(), "")
        self.assertEqual(self.panel.signal_name_list(), ["Time", "speed"])

    @covers("LLFR-00418", "LLFR-00327", "LLFR-00328", "LLFR-00010",
            "LLFR-00325", "LLFR-00561", "LLFR-00562")
    def test_time_window_shown_after_the_indication(self) -> None:
        """Yes, read, then the window without the indication; cancel.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        self.open_file(self.good_path_str)
        self.event_list.clear()
        self.replace_answer_list = [True]
        self.open_file(self.no_time_path_str)
        self.assertEqual(self.event_list, [
            ("question", None, ""),
            ("read", Qt.CursorShape.WaitCursor, "Loading..."),
            ("time window", None, "")])
        self.assertIsNone(current_cursor_shape())
        self.assertEqual(self.panel.signal_name_list(), ["Time", "speed"])
        self.assertEqual(self.panel.file_name(), "good.csv")


if __name__ == "__main__":
    unittest.main()
