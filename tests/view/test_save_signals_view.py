"""GUI tests of the Save signals button (issue #153, HLFR-00090).

A real MainWindow and MainController are used. The save file dialog and
the message boxes are patched, so no modal dialog is ever left open.
"""

import os
import tempfile
import unittest
from unittest import mock

from tests.support import (
    button_name, button_tip_line_list, covers, get_qt_application,
    requires_qt)
from tests.support import OPEN_FILE_DIALOG_TARGET_STR

DATA_FILE_TEXT_STR = (
    "time,speed,force\n"
    "0,0,1\n0.5,1,0\n1,2,-1\n1.5,3,0\n2,4,1\n")


@requires_qt
class SaveSignalsViewTest(unittest.TestCase):
    """The button, its dialog and its boxes."""

    def setUp(self) -> None:
        """Create a main window with its controller, no file open.

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
        self.folder_str = self.temporary_folder.name
        self.data_path_str = os.path.join(self.folder_str, "run1.csv")
        with open(self.data_path_str, "w", encoding="utf-8") as data_file:
            data_file.write(DATA_FILE_TEXT_STR)
        self.main_window = MainWindow()
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.application.processEvents()
        self.top_panel = self.main_window.top_panel
        self.box_record_list = []
        box_patch = mock.patch.object(
            QMessageBox, "exec", new=lambda box: self.fake_exec(box))
        box_patch.start()
        self.addCleanup(box_patch.stop)
        self.changed_names_list = []
        self.main_window.show_changed_signal_names = (
            self.changed_names_list.append)

    def tearDown(self) -> None:
        """Close the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def fake_exec(self, box) -> int:
        """Stand-in for QMessageBox.exec: record the box, answer Yes.

        Inputs:
            box: the QMessageBox being shown.
        Outputs: the int value of Yes.
        """
        self.box_record_list.append((box.windowTitle(), box.icon(),
                                     box.text()))
        return self.message_box_class.StandardButton.Yes.value

    def open_data_file(self) -> None:
        """Open run1.csv through the open-file flow.

        Inputs: none.
        Outputs: none.
        """
        with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                        return_value=self.data_path_str):
            self.controller.file_controller.open_file_requested()
        self.application.processEvents()

    def click_with_dialog_answer(self, answer_tuple: tuple):
        """Click Save signals; the patched dialog returns an answer.

        Inputs:
            answer_tuple: (path, filter) returned by the dialog.
        Outputs: the mock of MainWindow.run_signals_save_dialog.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        with mock.patch.object(self.main_window, "run_signals_save_dialog",
                               return_value=answer_tuple) as dialog_mock:
            QTest.mouseClick(self.top_panel.save_signals_button,
                             Qt.MouseButton.LeftButton)
            for _ in range(5):
                self.application.processEvents()
        return dialog_mock

    @covers("LLFR-00394", "LLFR-00347", "LLFR-00158", "LLFR-00159",
            "LLFR-00181", "LLFR-00215", "LLFR-00465")
    def test_button_right_of_copy_with_icon_and_name(self) -> None:
        """Save signals is directly right of Copy, the last of its group,
        shows only its icon and its plain name in the button tip.

        Inputs: none.
        Outputs: none.
        """
        from view import icon_shapes, icons
        from view.undo_button import UndoButton
        button = self.top_panel.save_signals_button
        button_list = self.top_panel.button_list()
        copy_index_i = button_list.index(self.top_panel.copy_button)
        self.assertIs(button_list[copy_index_i + 1], button)
        self.assertEqual(self.top_panel.button_group_list[3],
                         [self.top_panel.export_button,
                          self.top_panel.copy_button, button])
        self.assertIsInstance(button, UndoButton)
        self.assertEqual(button_name(button), "Save signals")
        self.assertEqual(button.text(), "")
        self.assertFalse(button.icon().isNull())
        self.assertEqual(button_tip_line_list(button), ["Save signals"])
        self.assertEqual(button.toolTip(), "Save signals")
        self.assertIn(icon_shapes.SAVE_SIGNALS_ICON_STR,
                      icon_shapes.ICON_NAME_TUPLE)
        self.assertFalse(icons.icon_for(
            icon_shapes.SAVE_SIGNALS_ICON_STR).isNull())

    @covers("LLFR-00395", "LLFR-00160", "LLFR-00350", "LLFR-00531")
    def test_disabled_without_a_data_file(self) -> None:
        """Disabled and paler before a file is open, a click does
        nothing; enabled after a file is opened.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        button = self.top_panel.save_signals_button
        self.assertFalse(button.isEnabled())
        self.assertEqual(button.current_background_color_str(),
                         theme.DISABLED_COLOR_STR)
        dialog_mock = self.click_with_dialog_answer(("", ""))
        dialog_mock.assert_not_called()
        self.assertFalse(button.is_active())
        self.open_data_file()
        self.assertTrue(button.isEnabled())

    @covers("LLFR-00396", "LLFR-00397", "LLFR-00532", "LLFR-00536")
    def test_dialog_with_format_filters(self) -> None:
        """The dialog saves, offers the four formats, opens in the folder
        with the proposed name and format, and leaves the replace
        question to the app.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QFileDialog
        from view.main_window import SIGNALS_FILTER_DICT
        dialog = self.main_window.build_signals_save_dialog(
            self.folder_str, "run1_signals.mat", "mat")
        self.assertEqual(dialog.acceptMode(),
                         QFileDialog.AcceptMode.AcceptSave)
        self.assertEqual(dialog.nameFilters(),
                         list(SIGNALS_FILTER_DICT.values()))
        self.assertEqual(dialog.nameFilters(), [
            "CSV files (*.csv)", "Excel files (*.xlsx)",
            "MAT files (*.mat)", "HDF5 files (*.h5 *.hdf5)"])
        self.assertEqual(dialog.selectedNameFilter(), "MAT files (*.mat)")
        self.assertEqual(os.path.realpath(dialog.directory().absolutePath()),
                         os.path.realpath(self.folder_str))
        self.assertTrue(dialog.testOption(
            QFileDialog.Option.DontConfirmOverwrite))
        dialog.deleteLater()
        # The chosen filter gives the format.
        with mock.patch.object(
                self.main_window, "run_signals_save_dialog",
                return_value=("/x/out", "HDF5 files (*.h5 *.hdf5)")):
            path_str, format_str, _ = self.main_window.ask_signals_save_path(
                self.folder_str, "run1_signals.csv", "csv")
        self.assertEqual((path_str, format_str), ("/x/out", "hdf5"))
        with mock.patch.object(self.main_window, "run_signals_save_dialog",
                               return_value=("", "")):
            self.assertEqual(self.main_window.ask_signals_save_path(
                self.folder_str, "run1_signals.csv", "csv")[0], "")

    @covers("LLFR-00396", "LLFR-00401", "LLFR-00402", "LLFR-00404",
            "LLFR-00407", "LLFR-00406", "LLFR-00532", "LLFR-00558")
    def test_click_saves_the_file(self) -> None:
        """A click opens the dialog with run1_signals.csv and the CSV
        filter; the file is written and the renamed time signal listed.

        Inputs: none.
        Outputs: none.
        """
        from model.file_loader import load_signal_file
        self.open_data_file()
        target_str = os.path.join(self.folder_str, "copy")
        dialog_mock = self.click_with_dialog_answer(
            (target_str, "Excel files (*.xlsx)"))
        # LLFR-00396, LLFR-00406: the reused dialog was shown in the
        # folder of the data file, with its name and the CSV format.
        dialog = dialog_mock.call_args.args[0]
        self.assertIs(dialog,
                      self.main_window.file_dialog_pool.dialog(
                          "save_signals"))
        self.assertEqual(
            os.path.realpath(dialog.directory().absolutePath()),
            os.path.realpath(self.folder_str))
        self.assertEqual(dialog.selectedNameFilter(), "CSV files (*.csv)")
        self.assertEqual(os.path.basename(dialog.selectedFiles()[0]),
                         "run1_signals.csv")
        saved_file = load_signal_file(target_str + ".xlsx")
        # LLFR-00941: the names are saved without the prefix.
        self.assertEqual(saved_file.signal_name_list,
                         ["Time", "speed", "force"])
        self.assertEqual(self.changed_names_list, ["time → Time"])
        # LLFR-00003: normal again once the save is done and the minimum
        # active time of an action button has passed.
        from PyQt6.QtTest import QTest
        from view.action_button import MINIMUM_ACTIVE_TIME_MS_I
        QTest.qWait(MINIMUM_ACTIVE_TIME_MS_I + 200)
        self.assertFalse(self.top_panel.save_signals_button.is_active())

    @covers("LLFR-00397", "LLFR-00399", "LLFR-00534")
    def test_error_boxes(self) -> None:
        """The opened data file is refused, and a write failure shows
        the error box; both are critical boxes.

        Inputs: none.
        Outputs: none.
        """
        self.open_data_file()
        self.click_with_dialog_answer((self.data_path_str,
                                       "CSV files (*.csv)"))
        self.assertEqual(len(self.box_record_list), 1)
        title_str, icon, text_str = self.box_record_list[0]
        self.assertEqual(icon, self.message_box_class.Icon.Critical)
        self.assertIn("cannot be replaced", text_str)
        self.box_record_list.clear()
        missing_str = os.path.join(self.folder_str, "missing", "out.csv")
        self.click_with_dialog_answer((missing_str, "CSV files (*.csv)"))
        self.assertEqual(len(self.box_record_list), 1)
        self.assertEqual(self.box_record_list[0][1],
                         self.message_box_class.Icon.Critical)
        self.assertIn("could not be saved", self.box_record_list[0][2])

    @covers("LLFR-00408", "LLFR-00559")
    def test_non_finite_values_show_a_critical_box(self) -> None:
        """A synthetic signal with an infinite value: a critical box that
        names it, and no Excel file afterwards.

        Inputs: none.
        Outputs: none.
        """
        import numpy as np
        from model import synthetic_operations as operations
        from model.synthetic_signals import SyntheticSignal
        self.open_data_file()
        self.controller.synthetic_controller.store.signal_list.append(
            SyntheticSignal("mul_1e308_file1_speed", operations.MULTIPLY_STR,
                            ["file1_speed"], 1e308,
                            np.array([0.0, np.inf, np.inf, np.inf, np.inf])))
        target_str = os.path.join(self.folder_str, "bad.xlsx")
        self.click_with_dialog_answer((target_str, "Excel files (*.xlsx)"))
        self.assertEqual(len(self.box_record_list), 1)
        self.assertEqual(self.box_record_list[0][1],
                         self.message_box_class.Icon.Critical)
        self.assertIn("mul_1e308_file1_speed", self.box_record_list[0][2])
        self.assertFalse(os.path.exists(target_str))
        self.assertEqual(self.changed_names_list, [])

    @covers("LLFR-00404", "LLFR-00885")
    def test_changed_names_box_is_scrollable_information(self) -> None:
        """The changed names box is an information box with a long list
        that can be scrolled.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QPlainTextEdit
        from view import message_boxes
        text_str = "\n".join(f"a.{index_i} → a_{index_i}"
                             for index_i in range(200))
        dialog = message_boxes.build_changed_names_box(self.main_window,
                                                       text_str)
        self.assertEqual(dialog.windowTitle(),
                         message_boxes.CHANGED_NAMES_TITLE_STR)
        field = dialog.findChild(
            QPlainTextEdit, message_boxes.CHANGED_NAMES_TEXT_OBJECT_NAME_STR)
        self.assertTrue(field.isReadOnly())
        self.assertEqual(field.toPlainText(), text_str)
        dialog.show()
        self.application.processEvents()
        self.assertGreater(field.verticalScrollBar().maximum(), 0)
        dialog.close()
        dialog.deleteLater()

    @covers("LLFR-00405", "LLFR-00556")
    def test_saving_keeps_plots_and_undo_history(self) -> None:
        """Saving leaves the plots, the signal list and the undo and redo
        history as they were.

        Inputs: none.
        Outputs: none.
        """
        self.open_data_file()
        plot_controller = self.controller.plot_controller
        plot_controller.on_signal_double_clicked("file1_speed")
        plot_controller.on_signal_double_clicked("file1_force")
        plot_controller.on_undo()
        self.application.processEvents()
        undo_depth_i = plot_controller.undo_history.depth()
        redo_depth_i = plot_controller.undo_history.redo_depth()
        plot_count_i = len(plot_controller.workspace.tab_list[0].plot_list)
        undo_enabled_b = self.top_panel.undo_button.isEnabled()
        redo_enabled_b = self.top_panel.redo_button.isEnabled()
        self.click_with_dialog_answer((
            os.path.join(self.folder_str, "out.mat"), "MAT files (*.mat)"))
        self.assertTrue(os.path.exists(os.path.join(self.folder_str,
                                                    "out.mat")))
        self.assertEqual(plot_controller.undo_history.depth(), undo_depth_i)
        self.assertEqual(plot_controller.undo_history.redo_depth(),
                         redo_depth_i)
        self.assertEqual(
            len(plot_controller.workspace.tab_list[0].plot_list),
            plot_count_i)
        self.assertEqual(self.top_panel.undo_button.isEnabled(),
                         undo_enabled_b)
        self.assertEqual(self.top_panel.redo_button.isEnabled(),
                         redo_enabled_b)
        self.assertEqual(
            self.controller.synthetic_controller.signal_list_name_list(),
            ["file1_time", "file1_speed", "file1_force"])


if __name__ == "__main__":
    unittest.main()
