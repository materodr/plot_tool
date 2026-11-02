"""Tests for the fast file dialogs (HLFR-00091, LLFR-00406).

Each file dialog of the app is built once, prepared after the main
window is shown, and reused. The tests click each button as the user
does and measure the time from the click to the dialog being shown on
screen; the dialog's ``exec`` is replaced by one that shows it, notes
the time, hides it and cancels, so no modal loop is left open.
"""

import os
import tempfile
import time
import unittest
from unittest import mock

from tests.support import button_name, covers, get_qt_application, requires_qt

# LLFR-00406: the limit from the click to the dialog being shown.
DIALOG_LIMIT_S = 0.3
FILE_TEXT_STR = "Time,speed,force\n0,1,5\n1,2,6\n2,3,7\n"
OPEN_FILTER_LIST = ["Time series files (*.csv *.xlsx *.mat *.h5 *.hdf5)",
                    "All files (*)"]
LAYOUT_FILTER_LIST = ["Layout files (*.json)"]
PDF_FILTER_LIST = ["PDF files (*.pdf)"]


@requires_qt
class FileDialogTimingTest(unittest.TestCase):
    """Every file dialog appears within 0.3 s of its click."""

    def setUp(self) -> None:
        """Start the app as src/main.py does, with a data file at hand.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QDialog, QFileDialog
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.dialog_class = QDialog
        self.file_dialog_class = QFileDialog
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        self.folder_str = os.path.realpath(self.temporary_folder.name)
        self.data_path_str = os.path.join(self.folder_str, "data.csv")
        with open(self.data_path_str, "w", encoding="utf-8") as data_file:
            data_file.write(FILE_TEXT_STR)
        self.main_window = MainWindow()
        self.controller = MainController(self.main_window)
        self.controller.start()
        # LLFR-00406: as src/main.py, once the window is shown.
        self.main_window.schedule_file_dialog_preparation()
        self.pool = self.main_window.file_dialog_pool
        self.shown_list = []
        self.top_panel = self.main_window.top_panel
        self.top_panel.execute_export_menu = self.choose_pdf_option

    def tearDown(self) -> None:
        """Close the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def process_events(self) -> None:
        """Let the deferred work of the window run.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(3):
            self.application.processEvents()

    def choose_pdf_option(self, menu):
        """Stand-in for the modal Export menu: choose the PDF option.

        Inputs:
            menu: the QMenu the Export button would show.
        Outputs: the "Save all tabs as PDF" action.
        """
        for action in menu.actions():
            if action.text() == "Save all tabs as PDF":
                return action
        return None

    def watch_dialog(self, key_str: str) -> None:
        """Replace a pooled dialog's exec to time its showing.

        Inputs:
            key_str: the key of the dialog in the pool.
        Outputs: none. Each exec shows the dialog, records (key, dialog,
            time.perf_counter(), visible, folder, filters) in
            shown_list, hides it and cancels.
        """
        dialog = self.pool.dialog(key_str)

        def timed_exec() -> int:
            """Show the dialog, note when, and cancel it.

            Inputs: none.
            Outputs: the int value of QDialog.DialogCode.Rejected.
            """
            dialog.show()
            self.application.processEvents()
            self.shown_list.append((
                key_str, dialog, time.perf_counter(), dialog.isVisible(),
                os.path.realpath(dialog.directory().absolutePath()),
                dialog.nameFilters()))
            dialog.hide()
            return self.dialog_class.DialogCode.Rejected.value

        dialog.exec = timed_exec

    def click_and_time(self, button) -> tuple:
        """Click a top panel button and measure until its dialog shows.

        Inputs:
            button: the button to click.
        Outputs: the record of watch_dialog, with the seconds from the
            click to the dialog being shown instead of the time.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        shown_count_i = len(self.shown_list)
        start_s = time.perf_counter()
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        deadline_s = start_s + 5.0
        while (len(self.shown_list) == shown_count_i
               and time.perf_counter() < deadline_s):
            self.application.processEvents()
        self.assertEqual(len(self.shown_list), shown_count_i + 1,
                         f"{button_name(button)} showed no dialog")
        key_str, dialog, shown_s, visible_b, folder_str, filter_list = (
            self.shown_list[-1])
        self.process_events()
        return (key_str, dialog, shown_s - start_s, visible_b, folder_str,
                filter_list)

    def open_data_file(self) -> None:
        """Open the data file, answering the Open file dialog.

        Inputs: none.
        Outputs: none.
        """
        with mock.patch.object(self.main_window, "run_open_file_dialog",
                               return_value=self.data_path_str):
            self.controller.file_controller.open_file_requested()
        self.process_events()

    @covers("LLFR-00406", "HLFR-00091")
    def test_dialogs_are_prepared_after_the_window_is_shown(self) -> None:
        """The four dialogs are built once the event loop has run.

        Inputs: none.
        Outputs: none.
        """
        key_list = ["open_file", "save_layout", "load_layout", "save_pdf"]
        self.assertEqual(self.pool.key_list(), key_list)
        # Not built before the event loop runs, so the window is not
        # delayed by them.
        self.assertFalse(self.pool.prepared_b)
        self.process_events()
        self.assertTrue(self.pool.prepared_b)
        for key_str in key_list:
            with self.subTest(key_str=key_str):
                self.assertTrue(self.pool.is_built(key_str))
                self.assertIsInstance(self.pool.dialog(key_str),
                                      self.file_dialog_class)
                self.assertFalse(self.pool.dialog(key_str).isVisible())

    @covers("LLFR-00406", "HLFR-00091", "LLFR-00005", "LLFR-00219",
            "LLFR-00221", "LLFR-00128", "LLFR-00204", "LLFR-00220")
    def test_every_dialog_appears_quickly(self) -> None:
        """First and second click of each dialog: shown within 0.3 s.

        Inputs: none.
        Outputs: none.
        """
        from controller.file_controller import first_start_folder_str
        self.process_events()
        for key_str in self.pool.key_list():
            self.watch_dialog(key_str)
        top_panel = self.top_panel
        # The Open file dialog, first click after the start, in the
        # folder of the app (LLFR-00204).
        record_list = [self.click_and_time(top_panel.open_file_button)]
        self.assertEqual(record_list[0][4],
                         os.path.realpath(first_start_folder_str()))
        self.open_data_file()
        self.main_window.signal_double_click_handler("speed")
        self.process_events()
        for button in (top_panel.save_layout_button,
                       top_panel.load_layout_button,
                       top_panel.export_button):
            record_list.append(self.click_and_time(button))
        for button in (top_panel.open_file_button,
                       top_panel.save_layout_button,
                       top_panel.load_layout_button,
                       top_panel.export_button):
            record_list.append(self.click_and_time(button))
        key_list = [record[0] for record in record_list]
        self.assertEqual(key_list, ["open_file", "save_layout",
                                    "load_layout", "save_pdf"] * 2)
        for click_i, record in enumerate(record_list):
            key_str, dialog, elapsed_s, visible_b = record[:4]
            with self.subTest(key_str=key_str, click_i=click_i):
                self.assertTrue(visible_b)
                self.assertLessEqual(elapsed_s, DIALOG_LIMIT_S)
                # LLFR-00406: the same dialog on every click.
                self.assertIs(dialog, self.pool.dialog(key_str))
        # LLFR-00204, LLFR-00220: after the open, the folder of the data
        # file, for the Open file and both layout dialogs.
        for record in record_list[1:]:
            if record[0] != "save_pdf":
                self.assertEqual(record[4], self.folder_str)
        # The filters are those of the dialogs before (LLFR-00005,
        # LLFR-00221, LLFR-00128).
        filter_dict = {record[0]: record[5] for record in record_list}
        self.assertEqual(filter_dict, {
            "open_file": OPEN_FILTER_LIST,
            "save_layout": LAYOUT_FILTER_LIST,
            "load_layout": LAYOUT_FILTER_LIST,
            "save_pdf": PDF_FILTER_LIST})
        # Every button is back to normal after the cancel (LLFR-00003),
        # once its minimum active time has passed.
        deadline_s = time.perf_counter() + 1.0
        while time.perf_counter() < deadline_s:
            self.application.processEvents()
            time.sleep(0.01)
        for button in (top_panel.open_file_button,
                       top_panel.save_layout_button,
                       top_panel.load_layout_button,
                       top_panel.export_button):
            self.assertFalse(button.is_active(), button_name(button))

    @covers("LLFR-00406", "LLFR-00005", "LLFR-00219", "LLFR-00221",
            "LLFR-00128")
    def test_dialog_modes_are_unchanged(self) -> None:
        """Open and save modes, suffixes and overwrite questions.

        Inputs: none.
        Outputs: none.
        """
        file_dialog_class = self.file_dialog_class
        self.process_events()
        open_dialog = self.pool.dialog("open_file")
        self.assertEqual(open_dialog.acceptMode(),
                         file_dialog_class.AcceptMode.AcceptOpen)
        self.assertEqual(open_dialog.fileMode(),
                         file_dialog_class.FileMode.ExistingFile)
        self.assertEqual(open_dialog.windowTitle(), "Open file")
        load_dialog = self.pool.dialog("load_layout")
        self.assertEqual(load_dialog.acceptMode(),
                         file_dialog_class.AcceptMode.AcceptOpen)
        self.assertEqual(load_dialog.fileMode(),
                         file_dialog_class.FileMode.ExistingFile)
        for key_str, suffix_str in (("save_layout", "json"),
                                    ("save_pdf", "pdf")):
            with self.subTest(key_str=key_str):
                dialog = self.pool.dialog(key_str)
                self.assertEqual(dialog.acceptMode(),
                                 file_dialog_class.AcceptMode.AcceptSave)
                self.assertEqual(dialog.defaultSuffix(), suffix_str)
                self.assertFalse(dialog.testOption(
                    file_dialog_class.Option.DontConfirmOverwrite))

    @covers("LLFR-00406", "LLFR-00219", "LLFR-00222")
    def test_reused_dialog_starts_clean(self) -> None:
        """A reused dialog has no old name and its first filter chosen.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QLineEdit
        self.process_events()
        dialog = self.pool.dialog("open_file")
        dialog.selectNameFilter(OPEN_FILTER_LIST[1])
        name_field = dialog.findChild(QLineEdit, "fileNameEdit")
        if name_field is not None:
            name_field.setText("typed_before_cancel.csv")
        prepared_dialog = self.pool.prepared_dialog("open_file",
                                                    self.folder_str)
        self.assertIs(prepared_dialog, dialog)
        self.assertEqual(dialog.selectedNameFilter(), OPEN_FILTER_LIST[0])
        if name_field is not None:
            self.assertEqual(name_field.text(), "")
        self.assertEqual(os.path.realpath(dialog.directory().absolutePath()),
                         self.folder_str)
        # "" keeps the folder the dialog shows.
        self.pool.prepared_dialog("open_file", "")
        self.assertEqual(os.path.realpath(dialog.directory().absolutePath()),
                         self.folder_str)

    @covers("LLFR-00406", "LLFR-00006", "LLFR-00007")
    def test_accepted_and_cancelled_answers(self) -> None:
        """The path of an accepted dialog, "" for a cancelled one.

        Inputs: none.
        Outputs: none.
        """
        from view import file_dialogs
        self.process_events()
        dialog = self.pool.dialog("open_file")
        accepted_i = self.dialog_class.DialogCode.Accepted.value
        rejected_i = self.dialog_class.DialogCode.Rejected.value
        with mock.patch.object(dialog, "exec", return_value=accepted_i), \
                mock.patch.object(dialog, "selectedFiles",
                                  return_value=[self.data_path_str]):
            self.assertEqual(file_dialogs.run_file_dialog(dialog),
                             self.data_path_str)
        with mock.patch.object(dialog, "exec", return_value=accepted_i), \
                mock.patch.object(dialog, "selectedFiles", return_value=[]):
            self.assertEqual(file_dialogs.run_file_dialog(dialog), "")
        with mock.patch.object(self.file_dialog_class, "exec",
                               return_value=rejected_i):
            self.assertEqual(self.main_window.ask_open_file_path(
                self.folder_str), "")
            self.assertEqual(self.main_window.ask_layout_save_path(
                self.folder_str), "")
            self.assertEqual(self.main_window.ask_pdf_save_path(), "")

    @covers("LLFR-00406")
    def test_dialog_built_again_after_deletion(self) -> None:
        """A pooled dialog deleted by Qt is built again on its next use.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6 import sip
        self.process_events()
        dialog = self.pool.dialog("save_pdf")
        sip.delete(dialog)
        self.assertFalse(self.pool.is_built("save_pdf"))
        new_dialog = self.pool.prepared_dialog("save_pdf")
        self.assertFalse(sip.isdeleted(new_dialog))
        self.assertEqual(new_dialog.nameFilters(), PDF_FILTER_LIST)

    @covers("LLFR-00406")
    def test_pooled_dialogs_are_qt_dialogs(self) -> None:
        """Every pooled dialog is Qt's own dialog, which shows fast.

        Inputs: none.
        Outputs: none.
        """
        from view import file_dialogs
        native_option = self.file_dialog_class.Option.DontUseNativeDialog
        self.process_events()
        for key_str in self.pool.key_list():
            with self.subTest(key_str=key_str):
                self.assertTrue(self.pool.dialog(key_str).testOption(
                    native_option))
        self.assertGreaterEqual(self.pool.prepare_duration_s, 0.0)
        # Any factory registered later gets the same dialog kind, so
        # another dialog (for example Save signals) is fast too.
        pool = file_dialogs.FileDialogPool()
        pool.register("other", lambda: self.file_dialog_class(
            self.main_window, "Other", "", "Data files (*.csv)"))
        self.assertFalse(pool.is_built("other"))
        pool.prepare_all()
        self.assertTrue(pool.prepared_b)
        self.assertTrue(pool.dialog("other").testOption(native_option))
        self.assertEqual(pool.dialog("other").nameFilters(),
                         ["Data files (*.csv)"])


if __name__ == "__main__":
    unittest.main()
