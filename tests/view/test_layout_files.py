"""GUI tests of the layout files (issue #107, HLFR-00049 to HLFR-00052).

A real MainWindow and MainController are used. The file dialogs, the
message boxes and the report box are patched, so no modal dialog is
ever left open.
"""

import json
import os
import re
import tempfile
import unittest
from unittest import mock

from tests.support import button_name, covers, get_qt_application, requires_qt
from tests.support import OPEN_FILE_DIALOG_TARGET_STR

FIRST_FILE_TEXT_STR = (
    "Time,speed,force,power\n"
    "0,0,1,5\n0.5,1,0,6\n1,2,-1,7\n1.5,3,0,8\n2,4,1,9\n")
# The second data file has no "force" signal.
SECOND_FILE_TEXT_STR = (
    "Time,speed,power\n"
    "0,0,5\n0.5,1,6\n1,2,7\n1.5,3,8\n2,4,9\n")


@requires_qt
class LayoutButtonTest(unittest.TestCase):
    """The two layout buttons of the top panel (LLFR-00216 to 00218)."""

    def setUp(self) -> None:
        """Create a main window with its controller, no file open.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.main_window = MainWindow()
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.application.processEvents()
        self.top_panel = self.main_window.top_panel

    def tearDown(self) -> None:
        """Close the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    @covers("LLFR-00216", "LLFR-00217", "LLFR-00158", "LLFR-00181",
            "LLFR-00215", "LLFR-00465")
    def test_buttons_in_order_with_icons_and_names(self) -> None:
        """Save layout right of Open file, Load layout right of it; icon
        only, the name alone in the button tip.

        Inputs: none.
        Outputs: none.
        """
        from view.undo_button import UndoButton
        button_list = self.top_panel.button_list()
        open_index_i = button_list.index(self.top_panel.open_file_button)
        save_button = self.top_panel.save_layout_button
        load_button = self.top_panel.load_layout_button
        self.assertIs(button_list[open_index_i + 1], save_button)
        self.assertIs(button_list[open_index_i + 2], load_button)
        previous_button = self.top_panel.open_file_button
        for button, name_str in ((save_button, "Save layout"),
                                 (load_button, "Load layout")):
            with self.subTest(button=name_str):
                self.assertIsInstance(button, UndoButton)
                self.assertEqual(button_name(button), name_str)
                self.assertEqual(button.toolTip(), name_str)
                self.assertEqual(button.text(), "")
                self.assertFalse(button.icon().isNull())
                self.assertTrue(button.isVisible())
                previous_right_i = (previous_button.x()
                                    + previous_button.width())
                # LLFR-00348: joined to the button on its left.
                self.assertEqual(button.x(), previous_right_i)
                self.assertEqual(button.y(), previous_button.y())
                previous_button = button

    @covers("LLFR-00218", "LLFR-00160", "LLFR-00466")
    def test_disabled_and_paler_without_a_data_file(self) -> None:
        """Both buttons are disabled before a file is open, and a click
        does nothing.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from view import theme
        for button in (self.top_panel.save_layout_button,
                       self.top_panel.load_layout_button):
            with self.subTest(button=button_name(button)):
                self.assertFalse(button.isEnabled())
                self.assertEqual(button.current_background_color_str(),
                                 theme.DISABLED_COLOR_STR)
                with mock.patch.object(self.main_window,
                                       "run_layout_dialog") as dialog_mock:
                    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                    for _ in range(3):
                        self.application.processEvents()
                dialog_mock.assert_not_called()
                self.assertFalse(button.is_active())

    @covers("LLFR-00218")
    def test_enabled_after_a_file_is_opened(self) -> None:
        """A successful open enables both buttons.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QFileDialog
        with tempfile.TemporaryDirectory() as folder_str:
            path_str = os.path.join(folder_str, "data.csv")
            with open(path_str, "w", encoding="utf-8") as data_file:
                data_file.write(FIRST_FILE_TEXT_STR)
            with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                            return_value=path_str):
                self.controller.file_controller.open_file_requested()
        self.assertTrue(self.top_panel.save_layout_button.isEnabled())
        self.assertTrue(self.top_panel.load_layout_button.isEnabled())


@requires_qt
class LayoutDialogAndBoxTest(unittest.TestCase):
    """The dialogs and boxes of the layout files."""

    def setUp(self) -> None:
        """Create a main window.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.main_window import MainWindow
        self.main_window = MainWindow()

    def tearDown(self) -> None:
        """Close the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    @covers("LLFR-00219", "LLFR-00220", "LLFR-00223", "LLFR-00467")
    def test_save_dialog(self) -> None:
        """A save dialog for .json files that adds the extension and
        starts in the given folder.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QFileDialog
        with tempfile.TemporaryDirectory() as folder_str:
            dialog = self.main_window.build_layout_save_dialog(folder_str)
            self.assertEqual(dialog.acceptMode(),
                             QFileDialog.AcceptMode.AcceptSave)
            self.assertEqual(dialog.defaultSuffix(), "json")
            self.assertTrue(any("*.json" in filter_str
                                for filter_str in dialog.nameFilters()))
            self.assertEqual(os.path.realpath(dialog.directory().path()),
                             os.path.realpath(folder_str))
            self.assertFalse(dialog.testOption(
                QFileDialog.Option.DontConfirmOverwrite))
            dialog.deleteLater()

    @covers("LLFR-00221", "LLFR-00220")
    def test_load_dialog(self) -> None:
        """A file selection dialog that lists the .json files.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QFileDialog
        with tempfile.TemporaryDirectory() as folder_str:
            dialog = self.main_window.build_layout_load_dialog(folder_str)
            self.assertEqual(dialog.acceptMode(),
                             QFileDialog.AcceptMode.AcceptOpen)
            self.assertEqual(dialog.fileMode(),
                             QFileDialog.FileMode.ExistingFile)
            self.assertEqual(dialog.nameFilters(),
                             ["Layout files (*.json)"])
            self.assertEqual(os.path.realpath(dialog.directory().path()),
                             os.path.realpath(folder_str))
            dialog.deleteLater()

    @covers("LLFR-00222")
    def test_cancelled_dialog_returns_nothing(self) -> None:
        """A rejected dialog gives an empty path.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QDialog, QFileDialog
        with mock.patch.object(QFileDialog, "exec",
                               return_value=QDialog.DialogCode.Rejected
                               .value):
            self.assertEqual(self.main_window.ask_layout_save_path(""), "")
            self.assertEqual(self.main_window.ask_layout_load_path(""), "")

    @covers("LLFR-00224", "LLFR-00236", "HLFR-00002")
    def test_error_boxes(self) -> None:
        """Both errors are error boxes that say what failed.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        from view import message_boxes
        save_box = message_boxes.build_layout_save_error_box(
            self.main_window, "Disk full: a.json")
        self.assertEqual(save_box.icon(), QMessageBox.Icon.Critical)
        self.assertIn("layout file could not be saved", save_box.text())
        self.assertIn("Disk full: a.json", save_box.text())
        load_box = message_boxes.build_layout_load_error_box(
            self.main_window, "The file 'b.json' could not be read as a "
            "layout file.")
        self.assertEqual(load_box.icon(), QMessageBox.Icon.Critical)
        self.assertIn("could not be read as a layout file", load_box.text())

    @covers("LLFR-00237", "LLFR-00884")
    def test_report_box_is_scrollable_information(self) -> None:
        """The report is an information box with a scrollable list.

        Inputs: none.
        Outputs: none.
        """
        from view import message_boxes
        report_text_str = "\n".join(f"  - Data tip at {index_i} s: gone."
                                    for index_i in range(200))
        dialog = message_boxes.build_layout_report_box(self.main_window,
                                                       report_text_str)
        self.assertEqual(dialog.windowTitle(),
                         message_boxes.LAYOUT_REPORT_TITLE_STR)
        report_field = dialog.findChild(
            message_boxes.ListTextField,
            message_boxes.LAYOUT_REPORT_TEXT_OBJECT_NAME_STR)
        self.assertTrue(report_field.isReadOnly())
        self.assertEqual(report_field.plain_text(), report_text_str)
        dialog.show()
        self.application.processEvents()
        self.assertGreater(report_field.verticalScrollBar().maximum(), 0)
        dialog.close()
        dialog.deleteLater()

    @covers("LLFR-00224")
    def test_save_writes_safely(self) -> None:
        """The bytes are written; a folder path fails with a reason.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as folder_str:
            path_str = os.path.join(folder_str, "a.json")
            self.assertEqual(self.main_window.save_layout_bytes(
                path_str, b"{}\n"), (True, ""))
            with open(path_str, "rb") as layout_file:
                self.assertEqual(layout_file.read(), b"{}\n")
            saved_b, reason_str = self.main_window.save_layout_bytes(
                folder_str, b"{}\n")
            self.assertFalse(saved_b)
            self.assertIn(folder_str, reason_str)

    @covers("LLFR-00230", "LLFR-00225", "LLFR-00482")
    def test_panel_widths_round_trip(self) -> None:
        """The panel widths can be read and set.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.show()
        self.application.processEvents()
        total_i = sum(self.main_window.panel_width_tuple())
        self.main_window.set_panel_widths(total_i - 400, 400)
        self.application.processEvents()
        self.assertEqual(self.main_window.panel_width_tuple(),
                         (total_i - 400, 400))

    @covers("LLFR-01195", "LLFR-00482", "LLFR-00230",
            "HLFR-00050", "HLFR-00130", "HLFR-00141")
    def test_panel_widths_scaled_and_trimmed(self) -> None:
        """Saved widths are scaled to the room of the panels; a signal
        list panel wider than the window minus 100 pixels is trimmed.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.show()
        self.application.processEvents()
        total_i = sum(self.main_window.panel_width_tuple())
        # The saved share of a room twice as wide.
        self.main_window.set_panel_widths(total_i, total_i)
        self.application.processEvents()
        plot_width_i, list_width_i = self.main_window.panel_width_tuple()
        self.assertEqual(plot_width_i + list_width_i, total_i)
        self.assertAlmostEqual(list_width_i, total_i // 2, delta=2)
        # A signal list panel wider than the window can hold.
        self.main_window.set_panel_widths(1, 16777215)
        self.application.processEvents()
        plot_width_i, list_width_i = self.main_window.panel_width_tuple()
        self.assertEqual(plot_width_i + list_width_i, total_i)
        self.assertGreaterEqual(list_width_i, 1)
        self.assertLessEqual(list_width_i,
                             self.main_window.width() - 100)
        # The plot panel keeps 100 pixels of the room of the panels.
        self.assertGreaterEqual(plot_width_i, 100)


@requires_qt
class LayoutEndToEndTestCase(unittest.TestCase):
    """Helpers: open a CSV, build a layout, save it, open another file
    in a new start of the app, load it."""

    def setUp(self) -> None:
        """Create the files, the window and the controller; open a file.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.file_dialog_class = QFileDialog
        self.message_box_class = QMessageBox
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        self.folder_str = self.temporary_folder.name
        self.first_path_str = self.write_file("first.csv",
                                              FIRST_FILE_TEXT_STR)
        self.second_path_str = self.write_file("second.csv",
                                               SECOND_FILE_TEXT_STR)
        self.box_record_list = []
        box_patch = mock.patch.object(
            QMessageBox, "exec", new=lambda box: self.fake_exec(box))
        box_patch.start()
        self.addCleanup(box_patch.stop)
        self.start_app()
        self.open_data_file(self.first_path_str)

    def start_app(self) -> None:
        """Create the window and the controllers, as at an app start.

        Inputs: none.
        Outputs: none. The first data file opened gets number 1.
        """
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.main_window = MainWindow()
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.application.processEvents()
        self.report_list = []
        self.main_window.show_layout_report = self.report_list.append

    def tearDown(self) -> None:
        """Close the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def write_file(self, name_str: str, text_str: str) -> str:
        """Write a text file in the temporary folder.

        Inputs:
            name_str: the file name.
            text_str: the content.
        Outputs: the path.
        """
        path_str = os.path.join(self.folder_str, name_str)
        with open(path_str, "w", encoding="utf-8") as output_file:
            output_file.write(text_str)
        return path_str

    def fake_exec(self, box) -> int:
        """Stand-in for QMessageBox.exec: record the box, answer Yes.

        Inputs:
            box: the QMessageBox being shown.
        Outputs: the int value of Yes.
        """
        self.box_record_list.append((box.windowTitle(), box.text()))
        return self.message_box_class.StandardButton.Yes.value

    def open_data_file(self, path_str: str) -> None:
        """Open a data file through the open-file flow.

        Inputs:
            path_str: the path of the CSV file.
        Outputs: none.
        """
        with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                        return_value=path_str):
            self.controller.file_controller.open_file_requested()
        self.application.processEvents()

    def click_with_dialog_answer(self, button, answer_path_str: str):
        """Click a layout button; the patched dialog returns a path.

        Inputs:
            button: the Save layout or Load layout button.
            answer_path_str: the path the dialog returns ("" = cancel).
        Outputs: the mock of MainWindow.run_layout_dialog.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        with mock.patch.object(self.main_window, "run_layout_dialog",
                               return_value=answer_path_str) as dialog_mock:
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            for _ in range(5):
                self.application.processEvents()
        return dialog_mock

    def build_layout(self) -> None:
        """Plot signals, pin a tip, place markers, zoom and show the grid.

        Inputs: none.
        Outputs: none.
        """
        from controller.plot_tools import DELTA_Y_TOOL_STR, MARKER_TOOL_STR
        plot_controller = self.controller.plot_controller
        workspace = plot_controller.workspace
        plot_controller.on_rename_tab(workspace.tab_list[0].tab_id_i,
                                      "Drive")
        plot_controller.on_signal_double_clicked("file1_speed")
        plot_id_i = workspace.tab_list[0].plot_list[0].plot_id_i
        plot_controller.on_signal_dropped(plot_id_i, "file1_force")
        plot_controller.on_curve_width(plot_id_i, "file1_speed", 3)
        plot_controller.on_tip_pin(plot_id_i, "file1_force", 1.0, -1.0)
        plot_controller.on_tip_pin(plot_id_i, "file1_speed", 1.5, 3.0)
        plot_controller.on_plot_tool_changed(DELTA_Y_TOOL_STR)
        plot_controller.on_delta_point_pick(plot_id_i, "file1_speed", 0.5, 1.0)
        plot_controller.on_delta_point_pick(plot_id_i, "file1_speed", 2.0, 4.0)
        plot_controller.on_plot_tool_changed(MARKER_TOOL_STR)
        plot_controller.on_marker_place(plot_id_i, 1.0)
        plot_controller.on_signal_double_clicked("file1_power")
        plot_controller.on_add_tab()
        plot_controller.on_signal_double_clicked("file1_force")
        plot_controller.on_grid_toggled(True)
        plot_controller.on_time_range_changed(plot_id_i, 0.5, 1.5)
        self.application.processEvents()


@requires_qt
class LayoutEndToEndTest(LayoutEndToEndTestCase):
    """Open a CSV, build a layout, save it, open another file in a new
    start of the app, load it."""

    @covers("LLFR-00219", "LLFR-00225", "LLFR-00227", "LLFR-00228",
            "LLFR-00230", "LLFR-00231", "LLFR-00232", "LLFR-00237",
            "LLFR-00238", "LLFR-00229", "LLFR-00221", "LLFR-00003")
    def test_save_start_again_and_load(self) -> None:
        """The saved layout is rebuilt with the second file in a new
        start of the app; the missing signal is reported in one box.

        Inputs: none.
        Outputs: none.
        """
        top_panel = self.main_window.top_panel
        self.build_layout()
        layout_path_str = os.path.join(self.folder_str, "drive")
        dialog_mock = self.click_with_dialog_answer(
            top_panel.save_layout_button, layout_path_str)
        dialog_mock.assert_called_once()
        # LLFR-00003: the save has finished, so the button is not left
        # running (it turns normal once its minimum time has passed).
        self.assertFalse(top_panel.save_layout_button.action_running_b)
        # LLFR-00219: ".json" was added to the name.
        with open(layout_path_str + ".json",
                  encoding="utf-8") as layout_file:
            layout_dict = json.load(layout_file)
        self.assertEqual(layout_dict["format"], "plot_tool layout")
        self.assertEqual([tab["name"] for tab in layout_dict["tabs"]],
                         ["Drive", "Tab 2"])
        self.assertEqual(layout_dict["time_range"],
                         {"start": 0.5, "end": 1.5})
        self.assertNotIn("first.csv", json.dumps(layout_dict))
        # Start the app again and open the second file as file 1:
        # "force" is missing in it.
        self.main_window.close()
        self.main_window.deleteLater()
        self.start_app()
        top_panel = self.main_window.top_panel
        self.open_data_file(self.second_path_str)
        self.assertEqual(self.main_window.tab_name_list(), ["Tab 1"])
        self.click_with_dialog_answer(top_panel.load_layout_button,
                                      layout_path_str + ".json")
        workspace = self.controller.plot_controller.workspace
        # LLFR-00231: the plot with only "force" is gone, and so is its
        # tab, left with no plot.
        self.assertEqual(self.main_window.tab_name_list(), ["Drive"])
        self.assertEqual(len(workspace.tab_list), 1)
        self.assertEqual(len(workspace.tab_list[0].plot_list), 2)
        first_plot = workspace.tab_list[0].plot_list[0]
        self.assertEqual([curve.signal_name_str
                          for curve in first_plot.curve_list], ["file1_speed"])
        self.assertEqual(first_plot.curve_list[0].width_i, 3)
        self.assertEqual([(tip.signal_name_str, tip.time_s)
                          for tip in first_plot.pinned_tip_list],
                         [("file1_speed", 1.5)])
        self.assertEqual(len(first_plot.delta_marker_list), 1)
        # The view shows them, with the saved range and the grid.
        plot_widget = self.main_window.plot_view(first_plot.plot_id_i)
        self.assertEqual(list(plot_widget.curve_line_dict), ["file1_speed"])
        start_s, end_s = self.main_window.plot_time_range(
            first_plot.plot_id_i)
        self.assertAlmostEqual(start_s, 0.5)
        self.assertAlmostEqual(end_s, 1.5)
        self.assertTrue(self.main_window.is_grid_shown())
        self.assertTrue(top_panel.grid_button.is_active())
        self.assertEqual(self.main_window.current_tab_id(),
                         workspace.tab_list[0].tab_id_i)
        self.assertEqual([marker.name_str for marker in
                          workspace.marker_list], ["Flag 1"])
        # LLFR-00237: one report naming "force" once and the lost tip.
        self.assertEqual(len(self.report_list), 1)
        # LLFR-00980, LLFR-00987: a numbered item of its own.
        self.assertEqual(len(re.findall(r"\n\d+\. file1_force\n",
                                        self.report_list[0])), 1)
        self.assertIn("Data tip at 1 s", self.report_list[0])
        # LLFR-00238: nothing to undo or redo after the load.
        self.assertFalse(top_panel.undo_button.isEnabled())
        self.assertFalse(top_panel.redo_button.isEnabled())

    @covers("LLFR-00236", "LLFR-00222", "LLFR-00469", "LLFR-00491")
    def test_unreadable_file_and_cancel_keep_the_layout(self) -> None:
        """A non-layout file shows the error box; cancel does nothing.

        Inputs: none.
        Outputs: none.
        """
        top_panel = self.main_window.top_panel
        self.build_layout()
        workspace = self.controller.plot_controller.workspace
        before_tuple = workspace.state_tuple()
        other_path_str = self.write_file("other.json", '{"a": 1}')
        self.click_with_dialog_answer(top_panel.load_layout_button,
                                      other_path_str)
        self.assertEqual(self.box_record_list[-1][0], "Load Layout Error")
        self.assertIn("could not be read as a layout file",
                      self.box_record_list[-1][1])
        box_count_i = len(self.box_record_list)
        self.click_with_dialog_answer(top_panel.load_layout_button, "")
        self.click_with_dialog_answer(top_panel.save_layout_button, "")
        self.assertEqual(len(self.box_record_list), box_count_i)
        self.assertEqual(workspace.state_tuple(), before_tuple)
        self.assertEqual(self.report_list, [])
        self.assertEqual(os.listdir(self.folder_str).count("other.json"), 1)


@requires_qt
class LayoutOptionsViewTest(LayoutEndToEndTestCase):
    """The save options dialog and the data files of a layout
    (LLFR-01218 to LLFR-01228)."""

    @covers("LLFR-01218", "LLFR-01219", "HLFR-00156")
    def test_dialog_choices_and_first_values(self) -> None:
        """The dialog shows the three choices with their first values,
        each time it opens.

        Inputs: none.
        Outputs: none.
        """
        from view.layout_options_dialog import LayoutOptionsDialog
        dialog = LayoutOptionsDialog(self.main_window)
        self.assertEqual(dialog.answer_dict(), {
            "markers": True, "all_tabs": True, "data_files": False})
        self.assertIn("markers", dialog.markers_box.text())
        self.assertEqual(dialog.current_tab_button.text(),
                         "Only the current tab")
        self.assertEqual(dialog.data_files_box.text(),
                         "Include the names of the open data files")
        dialog.current_tab_button.setChecked(True)
        dialog.data_files_box.setChecked(True)
        dialog.markers_box.setChecked(False)
        self.assertEqual(dialog.answer_dict(), {
            "markers": False, "all_tabs": False, "data_files": True})
        dialog.deleteLater()

    @covers("LLFR-01220", "HLFR-00156")
    def test_cancel_shows_no_file_dialog(self) -> None:
        """A cancelled options dialog shows no save file dialog.

        Inputs: none.
        Outputs: none.
        """
        with mock.patch.object(self.main_window,
                               "run_layout_options_dialog",
                               return_value=False):
            dialog_mock = self.click_with_dialog_answer(
                self.main_window.top_panel.save_layout_button,
                os.path.join(self.folder_str, "x.json"))
        self.assertEqual(dialog_mock.call_count, 0)
        self.assertFalse(os.path.exists(os.path.join(self.folder_str,
                                                     "x.json")))

    @covers("LLFR-01223", "LLFR-01224", "LLFR-01226", "HLFR-00156",
            "HLFR-00157")
    def test_layout_with_file_names_opens_its_file(self) -> None:
        """A layout saved with the names of the data files, loaded in a
        new start of the app where another file is open, opens its file
        and draws its curves.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.signal_double_click_handler("file1_speed")
        self.application.processEvents()
        layout_path_str = os.path.join(self.folder_str, "with_files.json")

        def answer_options(dialog) -> bool:
            """Choose the names of the data files.

            Inputs:
                dialog: the LayoutOptionsDialog.
            Outputs: True, as OK.
            """
            dialog.data_files_box.setChecked(True)
            return True

        with mock.patch.object(self.main_window,
                               "run_layout_options_dialog",
                               side_effect=answer_options):
            self.click_with_dialog_answer(
                self.main_window.top_panel.save_layout_button,
                layout_path_str)
        with open(layout_path_str, encoding="utf-8") as layout_file:
            saved_dict = json.load(layout_file)
        self.assertEqual(saved_dict["data_files"][0]["relative_path"],
                         "first.csv")
        self.main_window.close()
        self.start_app()
        self.open_data_file(self.second_path_str)
        self.click_with_dialog_answer(
            self.main_window.top_panel.load_layout_button, layout_path_str)
        data_files = self.controller.file_controller.data_files
        self.assertEqual(
            [os.path.basename(data_file.path_str)
             for data_file in data_files.file_list],
            ["second.csv", "first.csv"])
        workspace = self.controller.plot_controller.workspace
        curve_name_list = [curve.signal_name_str for tab in workspace.tab_list
                           for plot in tab.plot_list
                           for curve in plot.curve_list]
        self.assertIn("file2_speed", curve_name_list)


if __name__ == "__main__":
    unittest.main()
