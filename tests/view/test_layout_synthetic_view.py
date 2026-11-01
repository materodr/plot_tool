"""GUI tests of synthetic signals in layout files (issue #110).

A real MainWindow and MainController are used: synthetic signals are
created from the signal menu, plotted, saved in a layout file and
created again when the layout is loaded (LLFR-00225 item 10,
LLFR-00262). The file dialogs, the message boxes, the parameter
dialogs and the report box are patched, so no modal dialog is ever
left open.
"""

import json
import os
import tempfile
import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt
from tests.view.test_synthetic_signals_view import find_action


@requires_qt
class LayoutSyntheticEndToEndTest(unittest.TestCase):
    """Create synthetic signals, save a layout, reopen, load it."""

    def setUp(self) -> None:
        """Create the window and the controller and open a CSV file.

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
        self.data_path_str = os.path.join(self.folder_str, "data.csv")
        with open(self.data_path_str, "w",
                  encoding="utf-8") as data_file:
            data_file.write("Time,Speed,Torque\n")
            for index_i in range(100):
                data_file.write(
                    f"{index_i * 0.1:.1f},{index_i % 7},{index_i}\n")
        self.main_window = MainWindow()
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.application.processEvents()
        self.box_record_list = []
        box_patch = mock.patch.object(
            QMessageBox, "exec", new=lambda box: self.fake_exec(box))
        box_patch.start()
        self.addCleanup(box_patch.stop)
        self.report_list = []
        self.main_window.show_layout_report = self.report_list.append
        self.dialog_text_list = []
        self.main_window.run_modal_dialog = self.fake_run_dialog
        self.panel = self.main_window.signal_list_panel
        self.open_data_file()

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
        self.box_record_list.append((box.windowTitle(), box.text()))
        return self.message_box_class.StandardButton.Yes.value

    def fake_run_dialog(self, dialog) -> bool:
        """Fill in a parameter dialog with the next texts and press OK.

        Inputs:
            dialog: the dialog the window would run.
        Outputs: True when the dialog accepted the texts.
        """
        from PyQt6.QtWidgets import QDialog
        if not self.dialog_text_list:
            return False
        text_list = self.dialog_text_list.pop(0)
        dialog.set_value_texts(text_list)
        if len(text_list) > len(dialog.value_edit_list):
            dialog.set_choice(text_list[-1])
        dialog.try_accept()
        return dialog.result() == QDialog.DialogCode.Accepted.value

    def open_data_file(self) -> None:
        """Open (or reopen) the CSV file through the open-file flow.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QFileDialog
        with mock.patch.object(QFileDialog, "getOpenFileName",
                               return_value=(self.data_path_str, "")):
            self.controller.file_controller.open_file_requested()
        self.application.processEvents()

    def choose(self, name_str: str, option_str: str) -> None:
        """Right-click a signal name and choose an option of its menu.

        Inputs:
            name_str: the signal name.
            option_str: the text of the option.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.panel.execute_menu = lambda menu, point: find_action(
            menu, option_str)
        self.panel.show_signal_menu(name_str, QPoint(0, 0))
        self.application.processEvents()

    def click_with_dialog_answer(self, button, answer_path_str: str):
        """Click a layout button; the patched dialog returns a path.

        Inputs:
            button: the Save layout or Load layout button.
            answer_path_str: the path the dialog returns.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        with mock.patch.object(self.main_window, "run_layout_dialog",
                               return_value=answer_path_str):
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            for _ in range(5):
                self.application.processEvents()

    def legend_names_of_tab(self) -> list:
        """Return the legend names of every plot of the current tab.

        Inputs: none.
        Outputs: a list of name lists, top to bottom.
        """
        plot_panel = self.main_window.plot_panel
        return [[name_str for name_str, _ in
                 plot_panel.plot_view(plot_id_i).legend_entry_list()]
                for plot_id_i in plot_panel.plot_id_list(
                    plot_panel.current_tab_id())]

    @covers("LLFR-00225", "LLFR-00262", "LLFR-00230", "LLFR-00242",
            "LLFR-00252")
    def test_save_reopen_and_load_synthetic_signals(self) -> None:
        """The synthetic signals and their curves come back."""
        top_panel = self.main_window.top_panel
        self.choose("Speed", "Integral")
        self.dialog_text_list = [["2", "3", "zero"]]
        self.choose("integral_Speed", "Low-pass filter")
        self.dialog_text_list = [["5"]]
        self.choose("Torque", "Moving average")
        name_list = ["integral_Speed", "lowpass_integral_Speed",
                     "movingaverage_Torque"]
        store = self.controller.synthetic_controller.store
        self.assertEqual(store.names(), name_list)
        self.panel.signal_double_clicked.emit("lowpass_integral_Speed")
        self.panel.signal_double_clicked.emit("Torque")
        self.application.processEvents()
        plot_list = self.controller.plot_controller.workspace.tab_list[
            0].plot_list
        self.controller.plot_controller.on_signal_dropped(
            plot_list[1].plot_id_i, "movingaverage_Torque")
        self.application.processEvents()
        legend_list = self.legend_names_of_tab()
        layout_path_str = os.path.join(self.folder_str, "synthetic.json")
        self.click_with_dialog_answer(top_panel.save_layout_button,
                                      layout_path_str)
        with open(layout_path_str, encoding="utf-8") as layout_file:
            entry_list = json.load(layout_file)["synthetic_signals"]
        self.assertEqual([entry["name"] for entry in entry_list],
                         name_list)
        self.assertEqual(entry_list[1]["parameter"],
                         {"cutoff": 2.0, "order": 3, "start": "zero"})
        # LLFR-00252: reopening the data file removes them.
        self.open_data_file()
        self.assertEqual(self.panel.signal_name_list(),
                         ["Time", "Speed", "Torque"])
        self.click_with_dialog_answer(top_panel.load_layout_button,
                                      layout_path_str)
        self.assertEqual(self.report_list, [])
        # LLFR-00242: listed after the data signals, in italics.
        self.assertEqual(self.panel.signal_name_list(),
                         ["Time", "Speed", "Torque"] + name_list)
        for name_str in name_list:
            self.assertTrue(self.panel.is_name_italic(name_str))
        self.assertFalse(self.panel.is_name_italic("Speed"))
        # LLFR-00230: the curves of synthetic signals are drawn again.
        self.assertEqual(self.legend_names_of_tab(), legend_list)
        self.assertEqual(store.get("lowpass_integral_Speed").parameter,
                         (2.0, 3, "zero"))

    @covers("LLFR-00262", "LLFR-00237", "LLFR-00231")
    def test_signal_not_created_is_reported(self) -> None:
        """A hand-edited entry that cannot be created is in the report,
        and its curve is not drawn."""
        top_panel = self.main_window.top_panel
        self.choose("Speed", "Integral")
        self.panel.signal_double_clicked.emit("integral_Speed")
        self.panel.signal_double_clicked.emit("Torque")
        self.application.processEvents()
        layout_path_str = os.path.join(self.folder_str, "edited.json")
        self.click_with_dialog_answer(top_panel.save_layout_button,
                                      layout_path_str)
        with open(layout_path_str, encoding="utf-8") as layout_file:
            layout_dict = json.load(layout_file)
        layout_dict["synthetic_signals"][0]["signals"] = ["Pressure"]
        with open(layout_path_str, "w", encoding="utf-8") as layout_file:
            json.dump(layout_dict, layout_file, indent=2)
        self.open_data_file()
        self.click_with_dialog_answer(top_panel.load_layout_button,
                                      layout_path_str)
        self.assertEqual(self.panel.signal_name_list(),
                         ["Time", "Speed", "Torque"])
        self.assertEqual(self.legend_names_of_tab(), [["Torque"]])
        self.assertEqual(len(self.report_list), 1)
        self.assertIn("Synthetic signals not created:",
                      self.report_list[0])
        self.assertIn("  - integral_Speed: The signal \"Pressure\"",
                      self.report_list[0])
        self.assertIn("  - integral_Speed\n", self.report_list[0] + "\n")


if __name__ == "__main__":
    unittest.main()
