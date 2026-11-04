"""Tests for the fast file dialogs (HLFR-00091, LLFR-00406).

Each file dialog of the app is built once, prepared in steps after the
main window is shown, and reused; no dialog is shown without a click
(issue #165). The tests click each button as the user does and measure
the time from the click to the dialog being shown on screen; the
dialog's ``exec`` is replaced by one that shows it, notes the time,
hides it and cancels, so no modal loop is left open.
"""

import os
import tempfile
import time
import unittest
from unittest import mock

from tests.support import button_name, covers, get_qt_application, requires_qt

# LLFR-00406: the limit from the click to the dialog being shown.
DIALOG_LIMIT_S = 0.65
# LLFR-00406: how long the tests wait at most for the preparation.
PREPARE_TIMEOUT_S = 10.0
FILE_TEXT_STR = "Time,speed,force\n0,1,5\n1,2,6\n2,3,7\n"
OPEN_FILTER_LIST = ["Time series files (*.csv *.xlsx *.mat *.h5 *.hdf5)",
                    "All files (*)"]
LAYOUT_FILTER_LIST = ["Layout files (*.json)"]
PDF_FILTER_LIST = ["PDF files (*.pdf)"]
SIGNALS_FILTER_LIST = ["CSV files (*.csv)", "Excel files (*.xlsx)",
                       "MAT files (*.mat)", "HDF5 files (*.h5 *.hdf5)"]
KEY_LIST = ["open_file", "save_layout", "load_layout", "save_pdf",
            "save_signals"]


@requires_qt
class FileDialogTimingTest(unittest.TestCase):
    """Every file dialog appears within 0.65 s of its click."""

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
        """Let the deferred work of the window run, the preparation too.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(3):
            self.application.processEvents()
        self.wait_until_prepared(self.pool)

    def wait_until_prepared(self, pool) -> None:
        """Run the event loop until a pool's preparation has finished.

        Inputs:
            pool: a FileDialogPool whose preparation was scheduled.
        Outputs: none.
        """
        deadline_s = time.perf_counter() + PREPARE_TIMEOUT_S
        while not pool.prepared_b and time.perf_counter() < deadline_s:
            self.application.processEvents()
            time.sleep(0.005)

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

    @covers("LLFR-00406", "HLFR-00091", "LLFR-00188")
    def test_dialogs_are_prepared_after_the_window_is_shown(self) -> None:
        """The five dialogs (KEY_LIST) are built in steps, after a delay.

        Inputs: none.
        Outputs: none.
        """
        key_list = KEY_LIST
        self.assertEqual(self.pool.key_list(), key_list)
        # Not built before the event loop runs, nor in its first turns,
        # so the window is drawn and answers first.
        self.assertFalse(self.pool.prepared_b)
        self.application.processEvents()
        self.assertFalse(self.pool.prepared_b)
        self.assertEqual(self.pool.step_count_i, 0)
        self.wait_until_prepared(self.pool)
        self.assertTrue(self.pool.prepared_b)
        # One step per dialog (and the panel warm-up on macOS only).
        self.assertEqual(self.pool.step_count_i, len(key_list))
        self.assertGreaterEqual(self.pool.prepare_duration_s,
                                self.pool.longest_step_s)
        for key_str in key_list:
            with self.subTest(key_str=key_str):
                self.assertTrue(self.pool.is_built(key_str))
                self.assertIsInstance(self.pool.dialog(key_str),
                                      self.file_dialog_class)
                self.assertFalse(self.pool.dialog(key_str).isVisible())

    @covers("LLFR-00406", "LLFR-00188")
    def test_one_preparation_step_per_turn(self) -> None:
        """Each turn of the event loop runs at most one step.

        Inputs: none.
        Outputs: none.
        """
        from view import file_dialogs
        pool = file_dialogs.FileDialogPool("linux")
        call_list = []
        for key_str in ("first", "second", "third"):
            pool.register(key_str, lambda key_str=key_str: (
                call_list.append(key_str)
                or self.main_window.build_open_file_dialog("")))
        pool.schedule_preparation(self.main_window, 0)
        self.assertEqual(call_list, [])
        pool.run_next_step()
        self.assertEqual(call_list, ["first"])
        self.assertFalse(pool.prepared_b)
        # The next step is left to the next turn of the event loop.
        self.assertTrue(pool.step_timer.isActive())
        self.wait_until_prepared(pool)
        self.assertEqual(call_list, ["first", "second", "third"])
        self.assertEqual(pool.step_count_i, 3)
        self.assertTrue(pool.prepared_b)
        # A dialog built before its step (a click during the
        # preparation) is not built again.
        other_pool = file_dialogs.FileDialogPool("linux")
        other_list = []
        other_pool.register("open", lambda: (
            other_list.append("open")
            or self.main_window.build_open_file_dialog("")))
        other_pool.schedule_preparation(self.main_window, 0)
        clicked_dialog = other_pool.prepared_dialog("open")
        self.wait_until_prepared(other_pool)
        self.assertEqual(other_list, ["open"])
        self.assertIs(other_pool.dialog("open"), clicked_dialog)

    @covers("LLFR-00406")
    def test_failing_step_does_not_stop_the_preparation(self) -> None:
        """A step that raises is reported and the next steps still run.

        Inputs: none.
        Outputs: none.
        """
        from view import file_dialogs
        pool = file_dialogs.FileDialogPool("linux")
        built_list = []

        def broken_build():
            """Fail as a broken dialog factory would.

            Inputs: none.
            Outputs: none; always raises.
            """
            raise RuntimeError("broken dialog")

        pool.register("broken", broken_build)
        pool.register("open", lambda: (
            built_list.append("open")
            or self.main_window.build_open_file_dialog("")))
        with mock.patch("sys.stderr") as error_stream:
            pool.schedule_preparation(self.main_window, 0)
            self.wait_until_prepared(pool)
        self.assertTrue(pool.prepared_b)
        self.assertEqual(built_list, ["open"])
        self.assertTrue(pool.is_built("open"))
        self.assertFalse(pool.is_built("broken"))
        self.assertEqual(pool.failed_step_count_i, 1)
        self.assertEqual(pool.step_count_i, 1)
        self.assertTrue(error_stream.write.called)

    @covers("LLFR-00406", "LLFR-00184", "LLFR-00186")
    def test_no_dialog_is_shown_without_a_click(self) -> None:
        """Starting the app and preparing the dialogs shows no dialog.

        The startup of src/main.py runs with every way to show a file
        dialog watched; nothing may be shown until the Open file
        button is clicked (issue #165).

        Inputs: none.
        Outputs: none.
        """
        import sys
        import main
        from view import splash_screen
        file_dialog_class = self.file_dialog_class
        call_list = []

        def watched(name_str: str):
            """Return a stand-in that records a way to show a dialog.

            Inputs:
                name_str: the name of the QFileDialog method.
            Outputs: the stand-in, which cancels like a closed dialog.
            """
            def record(dialog, *argument_tuple):
                """Record the call instead of showing the dialog.

                Inputs:
                    dialog: the QFileDialog.
                    argument_tuple: the arguments of the call.
                Outputs: the int value of QDialog.DialogCode.Rejected.
                """
                if name_str != "setVisible" or argument_tuple[:1] != (
                        False,):
                    call_list.append((name_str, dialog.windowTitle()))
                return self.dialog_class.DialogCode.Rejected.value
            return record

        patch_list = [mock.patch.object(file_dialog_class, name_str,
                                        watched(name_str), create=True)
                      for name_str in ("exec", "open", "show",
                                       "setVisible")]
        for patcher in patch_list:
            patcher.start()
            self.addCleanup(patcher.stop)
        splash = splash_screen.show_splash(self.application)
        self.addCleanup(splash.deleteLater)
        window_tuple = main.start_main_window(self.application, splash)
        self.addCleanup(setattr, sys, "excepthook", sys.__excepthook__)
        main_window = window_tuple[0]
        self.addCleanup(main_window.deleteLater)
        self.addCleanup(main_window.close)
        main_window.schedule_file_dialog_preparation()
        pool = main_window.file_dialog_pool
        self.wait_until_prepared(pool)
        self.assertTrue(pool.prepared_b)
        self.assertTrue(main_window.isVisible())
        self.assertEqual(call_list, [])
        for key_str in pool.key_list():
            self.assertFalse(pool.dialog(key_str).isVisible())
        # The click shows the Open file dialog, and only then.
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.mouseClick(main_window.top_panel.open_file_button,
                         Qt.MouseButton.LeftButton)
        deadline_s = time.perf_counter() + 2.0
        while not call_list and time.perf_counter() < deadline_s:
            self.application.processEvents()
        self.assertEqual(call_list, [("exec", "Open file")])

    @covers("LLFR-00406", "HLFR-00091", "LLFR-00005", "LLFR-00219",
            "LLFR-00221", "LLFR-00128", "LLFR-00204", "LLFR-00220",
            "LLFR-00396")
    def test_every_dialog_appears_quickly(self) -> None:
        """First and second click of each dialog: shown within 0.65 s.

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
        self.main_window.signal_double_click_handler("file1_speed")
        self.process_events()
        for button in (top_panel.save_layout_button,
                       top_panel.load_layout_button,
                       top_panel.export_button,
                       top_panel.save_signals_button):
            record_list.append(self.click_and_time(button))
        for button in (top_panel.open_file_button,
                       top_panel.save_layout_button,
                       top_panel.load_layout_button,
                       top_panel.export_button,
                       top_panel.save_signals_button):
            record_list.append(self.click_and_time(button))
        key_list = [record[0] for record in record_list]
        self.assertEqual(key_list, KEY_LIST * 2)
        for click_i, record in enumerate(record_list):
            key_str, dialog, elapsed_s, visible_b = record[:4]
            with self.subTest(key_str=key_str, click_i=click_i):
                self.assertTrue(visible_b)
                self.assertLessEqual(elapsed_s, DIALOG_LIMIT_S)
                # LLFR-00406: the same dialog on every click.
                self.assertIs(dialog, self.pool.dialog(key_str))
        # LLFR-00204, LLFR-00220, LLFR-00396: after the open, the
        # folder of the data file, for the Open file, both layout and the
        # Save signals dialogs.
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
            "save_pdf": PDF_FILTER_LIST,
            "save_signals": SIGNALS_FILTER_LIST})
        # LLFR-00396: the Save signals dialog proposes the CSV format
        # and the name of the data file, on every use.
        signals_dialog = self.pool.dialog("save_signals")
        self.assertEqual(signals_dialog.selectedNameFilter(),
                         SIGNALS_FILTER_LIST[0])
        self.assertEqual(
            os.path.basename(signals_dialog.selectedFiles()[0]),
            "data_signals.csv")
        # Every button is back to normal after the cancel (LLFR-00003),
        # once its minimum active time has passed.
        deadline_s = time.perf_counter() + 1.0
        while time.perf_counter() < deadline_s:
            self.application.processEvents()
            time.sleep(0.01)
        for button in (top_panel.open_file_button,
                       top_panel.save_layout_button,
                       top_panel.load_layout_button,
                       top_panel.export_button,
                       top_panel.save_signals_button):
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
        # LLFR-00951: several files at once.
        self.assertEqual(open_dialog.fileMode(),
                         file_dialog_class.FileMode.ExistingFiles)
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

    @covers("LLFR-00406", "LLFR-00006", "LLFR-00007", "LLFR-00951")
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
        # LLFR-00951: the Open file dialog gives every selected file.
        with mock.patch.object(dialog, "exec", return_value=accepted_i), \
                mock.patch.object(dialog, "selectedFiles",
                                  return_value=["/d/b.csv", "/d/a.csv"]):
            self.assertEqual(file_dialogs.run_file_dialog_paths(dialog),
                             ["/d/b.csv", "/d/a.csv"])
        with mock.patch.object(dialog, "exec", return_value=rejected_i):
            self.assertEqual(file_dialogs.run_file_dialog_paths(dialog), [])
        with mock.patch.object(self.file_dialog_class, "exec",
                               return_value=rejected_i):
            self.assertEqual(self.main_window.ask_open_file_path(
                self.folder_str), [])
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
    def test_pooled_dialogs_stay_system_dialogs(self) -> None:
        """The pool keeps the system's own dialogs, also for new keys.

        Inputs: none.
        Outputs: none.
        """
        from view import file_dialogs
        native_option = self.file_dialog_class.Option.DontUseNativeDialog
        self.process_events()
        for key_str in self.pool.key_list():
            with self.subTest(key_str=key_str):
                self.assertFalse(self.pool.dialog(key_str).testOption(
                    native_option))
        self.assertGreaterEqual(self.pool.prepare_duration_s, 0.0)
        # Any factory registered later is prepared the same way.
        pool = file_dialogs.FileDialogPool()
        pool.register("other", lambda: self.file_dialog_class(
            self.main_window, "Other", "", "Data files (*.csv)"))
        self.assertFalse(pool.is_built("other"))
        pool.prepare_all()
        self.assertTrue(pool.prepared_b)
        self.assertTrue(pool.is_built("other"))
        self.assertFalse(pool.dialog("other").testOption(native_option))
        self.assertEqual(pool.dialog("other").nameFilters(),
                         ["Data files (*.csv)"])

    @covers("LLFR-00406")
    def test_macos_panels_warmed_up_without_showing(self) -> None:
        """On macOS the panels are warmed up first, and nothing is shown.

        Inputs: none.
        Outputs: none.
        """
        from view import file_dialogs
        warm_up_list = []
        pool = file_dialogs.FileDialogPool(
            "darwin", lambda panel_tuple, platform_str: warm_up_list.append(
                (panel_tuple, platform_str)) or "warmed")
        shown_list = []
        for key_str in ("open", "save_a", "save_b"):
            dialog = self.main_window.build_open_file_dialog("")
            if key_str != "open":
                dialog.setAcceptMode(
                    self.file_dialog_class.AcceptMode.AcceptSave)
            dialog.setVisible = shown_list.append
            dialog.show = lambda: shown_list.append(True)
            dialog.open = lambda: shown_list.append(True)
            pool.register(key_str, lambda dialog=dialog: dialog)
        # One warm-up step per kind of panel, first, then one per dialog.
        step_list = pool.preparation_step_list()
        self.assertEqual(len(step_list), 5)
        step_list[0]()
        self.assertEqual(warm_up_list,
                         [((b"NSOpenPanel", b"openPanel"), "darwin")])
        self.assertFalse(any(pool.is_built(key_str)
                             for key_str in pool.key_list()))
        step_list[1]()
        self.assertEqual(warm_up_list[1],
                         ((b"NSSavePanel", b"savePanel"), "darwin"))
        self.assertFalse(any(pool.is_built(key_str)
                             for key_str in pool.key_list()))
        pool.prepare_all()
        self.assertTrue(pool.prepared_b)
        self.assertEqual(pool.panel_state_str(),
                         "warmed,warmed,warmed,warmed")
        self.assertEqual(pool.step_count_i, 5)
        self.assertEqual(len(pool.step_duration_list), 5)
        # LLFR-00406, issue #165: no dialog is shown by the preparation.
        self.assertEqual(shown_list, [])
        # Elsewhere there is no warm-up step.
        other_list = []
        other_pool = file_dialogs.FileDialogPool(
            "linux", lambda panel_tuple, platform_str: other_list.append(
                platform_str))
        other_pool.register("open", lambda: self.main_window
                            .build_open_file_dialog(""))
        self.assertEqual(len(other_pool.preparation_step_list()), 1)
        other_pool.prepare_all()
        self.assertEqual(other_list, [])
        self.assertEqual(other_pool.panel_state_str(), "none")
        # The real warm-up does nothing outside macOS.
        for platform_str in ("linux", "win32"):
            for panel_tuple in file_dialogs.SYSTEM_PANEL_TUPLE:
                self.assertEqual(file_dialogs.warm_up_system_panel(
                    panel_tuple, platform_str), "skipped")
        self.assertEqual(file_dialogs.KEPT_PANEL_LIST, [])


class FakeSystemPanelDialog:
    """Stand-in for a reused QFileDialog shown as the macOS panel.

    It keeps the options as Qt 6 keeps them for its macOS helper
    (qfiledialog.cpp, helperPrepareShow; qcocoafiledialoghelper.mm,
    createNSOpenSavePanelDelegate): before each show, the "initially
    selected files" become the files selected at the earlier use when
    that list is empty, and are then never replaced except by
    selectFile; the panel opens in the folder of the first of them (the
    path itself when it is a folder), or else in the folder of
    setDirectory.

    Inputs:
        native_b: False when DontUseNativeDialog is set.
    """

    def __init__(self, native_b: bool = True) -> None:
        """Start as a dialog never shown.

        Inputs:
            native_b: whether the system panel may be used.
        Outputs: none.
        """
        self.native_b = native_b
        self.directory_str = ""
        self.initially_selected_list = []
        self.user_selected_list = []
        self.shown_folder_list = []
        self.select_file_list = []

    def testOption(self, option) -> bool:
        """Answer the DontUseNativeDialog option.

        Inputs:
            option: a QFileDialog.Option.
        Outputs: True when the system panel is not used.
        """
        return not self.native_b

    def setDirectory(self, folder_str: str) -> None:
        """Keep the folder of setDirectory.

        Inputs:
            folder_str: the folder.
        Outputs: none.
        """
        self.directory_str = folder_str

    def selectFile(self, path_str: str) -> None:
        """Replace the initially selected files, as Qt does natively.

        Inputs:
            path_str: an absolute path; "" is ignored, as by Qt.
        Outputs: none.
        """
        self.select_file_list.append(path_str)
        if path_str:
            self.initially_selected_list = [path_str]

    def nameFilters(self) -> list:
        """Return no name filter.

        Inputs: none.
        Outputs: an empty list.
        """
        return []

    def findChild(self, *argument_tuple):
        """Return no widget: a system panel has no Qt widgets.

        Inputs:
            argument_tuple: the type and name looked for.
        Outputs: None.
        """
        return None

    def show_panel(self, chosen_list: list) -> list:
        """Show the panel, note its folder and choose files in it.

        Inputs:
            chosen_list: the paths the user selects ([] for a cancel).
        Outputs: chosen_list.
        """
        if not self.initially_selected_list:
            self.initially_selected_list = list(self.user_selected_list)
        if self.initially_selected_list:
            first_str = self.initially_selected_list[0]
            folder_str = (first_str if os.path.isdir(first_str)
                          else os.path.dirname(first_str))
        else:
            folder_str = self.directory_str
        self.shown_folder_list.append(os.path.realpath(folder_str))
        self.user_selected_list = list(chosen_list)
        return list(chosen_list)


@requires_qt
class ReusedDialogFolderTest(unittest.TestCase):
    """A reused dialog shows the folder asked for (issue #232)."""

    def setUp(self) -> None:
        """Make three folders, each with a data file.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        root_str = os.path.realpath(self.temporary_folder.name)
        self.folder_dict = {}
        self.path_dict = {}
        for name_str in ("start", "a", "b", "c"):
            folder_str = os.path.join(root_str, name_str)
            os.makedirs(folder_str)
            self.folder_dict[name_str] = folder_str
            for file_name_str in (f"{name_str}1.csv", f"{name_str}2.csv"):
                path_str = os.path.join(folder_str, file_name_str)
                with open(path_str, "w", encoding="utf-8") as data_file:
                    data_file.write(FILE_TEXT_STR)
                self.path_dict[file_name_str] = path_str

    @covers("LLFR-00447", "LLFR-00468", "LLFR-00204", "LLFR-00406")
    def test_macos_panel_follows_the_folder_asked_for(self) -> None:
        """The panel opens in each new folder, not the first chosen one.

        Inputs: none.
        Outputs: none.
        """
        from view import file_dialogs
        pool = file_dialogs.FileDialogPool(
            "darwin", lambda panel_tuple, platform_str: "skipped")
        dialog = FakeSystemPanelDialog()
        pool.register("open_file", lambda: dialog)
        folder_dict, path_dict = self.folder_dict, self.path_dict
        for folder_str, chosen_list in (
                (folder_dict["start"], [path_dict["a1.csv"]]),
                (folder_dict["a"], [path_dict["b1.csv"]]),
                (folder_dict["b"], [path_dict["c1.csv"]]),
                (folder_dict["c"], [])):
            pool.prepared_dialog("open_file", folder_str).show_panel(
                chosen_list)
        # Before the fix: start, a, a, a (the folder of the first file
        # chosen in the dialog).
        self.assertEqual(dialog.shown_folder_list, [
            folder_dict["start"], folder_dict["a"], folder_dict["b"],
            folder_dict["c"]])
        # "" keeps the panel as it is (the PDF dialog).
        selected_count_i = len(dialog.select_file_list)
        pool.prepared_dialog("open_file", "")
        self.assertEqual(len(dialog.select_file_list), selected_count_i)

    @covers("LLFR-00447", "LLFR-00204", "LLFR-00406")
    def test_folder_selected_only_on_the_macos_panel(self) -> None:
        """Qt's own dialog and other systems only get setDirectory.

        Inputs: none.
        Outputs: none.
        """
        from view import file_dialogs
        folder_str = self.folder_dict["a"]
        for platform_str, native_b, selected_list in (
                ("darwin", True, [folder_str]), ("darwin", False, []),
                ("linux", True, []), ("win32", True, [])):
            with self.subTest(platform_str=platform_str, native_b=native_b):
                dialog = FakeSystemPanelDialog(native_b)
                self.assertEqual(file_dialogs.uses_system_panel(
                    dialog, platform_str), bool(selected_list))
                file_dialogs.reset_for_new_use(dialog, folder_str,
                                               platform_str)
                self.assertEqual(dialog.select_file_list, selected_list)
                self.assertEqual(dialog.directory_str, folder_str)
        # A real dialog of Qt's own kind keeps working as before.
        from PyQt6.QtWidgets import QFileDialog
        dialog = QFileDialog(None, "Open", "", "Data files (*.csv)")
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        self.assertFalse(file_dialogs.uses_system_panel(dialog, "darwin"))
        for name_str in ("a", "b"):
            file_dialogs.reset_for_new_use(dialog, self.folder_dict[name_str],
                                           "darwin")
            self.assertEqual(
                os.path.realpath(dialog.directory().absolutePath()),
                self.folder_dict[name_str])
        dialog.deleteLater()

    @covers("LLFR-00447", "LLFR-00468", "LLFR-00220", "LLFR-00951",
            "LLFR-00952", "LLFR-00006", "HLFR-00122", "LLFR-00406")
    def test_app_dialogs_follow_the_last_file(self) -> None:
        """Open file, several files at once, then the layout dialogs.

        The app's dialogs are replaced by the macOS panel stand-in and
        each click goes through the controllers, as the user's would.

        Inputs: none.
        Outputs: none.
        """
        from controller.main_controller import MainController
        from view.main_window import (
            LOAD_LAYOUT_DIALOG_KEY_STR, OPEN_FILE_DIALOG_KEY_STR,
            SAVE_LAYOUT_DIALOG_KEY_STR, MainWindow)
        main_window = MainWindow()
        self.addCleanup(main_window.deleteLater)
        self.addCleanup(main_window.close)
        controller = MainController(main_window)
        controller.start()
        controller.file_controller.dialog_folder_str = (
            self.folder_dict["start"])
        pool = main_window.file_dialog_pool
        pool.platform_str = "darwin"
        dialog_dict = {}
        for key_str in (OPEN_FILE_DIALOG_KEY_STR, SAVE_LAYOUT_DIALOG_KEY_STR,
                        LOAD_LAYOUT_DIALOG_KEY_STR):
            dialog_dict[key_str] = FakeSystemPanelDialog()
            pool.dialog_dict[key_str] = dialog_dict[key_str]
        pool.is_built = lambda key_str: key_str in pool.dialog_dict
        answer_list = []
        main_window.run_open_file_dialog = (
            lambda dialog: dialog.show_panel(answer_list.pop(0)))
        main_window.run_layout_dialog = (
            lambda dialog: (dialog.show_panel(answer_list.pop(0)) or [""])[0])
        main_window.show_layout_report = lambda *argument_tuple: None
        folder_dict, path_dict = self.folder_dict, self.path_dict
        # Open file: a1.csv, then b2.csv and b1.csv in one go (opened as
        # b1, b2), then the two files of c with c2.csv gone, so that c1
        # is the last file opened, then a cancel.
        os.remove(path_dict["c2.csv"])
        with mock.patch.object(main_window, "show_file_open_error"), \
                mock.patch.object(main_window,
                                  "show_refused_files_notification",
                                  create=True):
            for chosen_list in ([path_dict["a1.csv"]],
                                [path_dict["b2.csv"], path_dict["b1.csv"]],
                                [path_dict["c1.csv"], path_dict["c2.csv"]],
                                []):
                answer_list.append(chosen_list)
                controller.file_controller.open_file_requested()
                self.application.processEvents()
        open_dialog = dialog_dict[OPEN_FILE_DIALOG_KEY_STR]
        self.assertEqual(open_dialog.shown_folder_list, [
            folder_dict["start"], folder_dict["a"], folder_dict["b"],
            folder_dict["c"]])
        self.assertEqual(
            [os.path.basename(path_str) for path_str in
             controller.file_controller.data_files.path_list],
            ["a1.csv", "b1.csv", "b2.csv", "c1.csv"])
        # Save layout: first in the Open file folder (LLFR-00220), saved
        # to a; Load layout then in a, loaded from b; Save layout then
        # in b (LLFR-00468), cancelled.
        main_window.signal_double_click_handler("file1_speed")
        self.application.processEvents()
        layout_a_str = os.path.join(folder_dict["a"], "view.json")
        layout_b_str = os.path.join(folder_dict["b"], "view.json")
        answer_list.append([layout_a_str])
        controller.layout_controller.on_save_layout_requested()
        self.assertTrue(os.path.exists(layout_a_str))
        with open(layout_a_str, "rb") as source_file, \
                open(layout_b_str, "wb") as target_file:
            target_file.write(source_file.read())
        answer_list.append([layout_b_str])
        controller.layout_controller.on_load_layout_requested()
        answer_list.append([])
        controller.layout_controller.on_save_layout_requested()
        answer_list.append([])
        controller.layout_controller.on_load_layout_requested()
        self.assertEqual(answer_list, [])
        self.assertEqual(
            dialog_dict[SAVE_LAYOUT_DIALOG_KEY_STR].shown_folder_list,
            [folder_dict["c"], folder_dict["b"]])
        self.assertEqual(
            dialog_dict[LOAD_LAYOUT_DIALOG_KEY_STR].shown_folder_list,
            [folder_dict["a"], folder_dict["b"]])


if __name__ == "__main__":
    unittest.main()
