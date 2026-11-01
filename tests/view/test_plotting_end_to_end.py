"""End-to-end tests of plotting (HLFR-00012, HLFR-00013, HLFR-00018 ...).

A real MainWindow and MainController are used. The file dialog and the
message boxes are patched, so no modal dialog is ever left open.
"""

import os
import tempfile
import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt

FIRST_FILE_TEXT_STR = (
    "Time,speed,force,angle\n"
    "0,0,1,5\n0.5,1,0,4\n1,2,-1,3\n1.5,3,0,2\n2,4,1,1\n")
SECOND_FILE_TEXT_STR = "Time,pressure\n0,1\n1,2\n"


@requires_qt
class PlottingEndToEndTest(unittest.TestCase):
    """Open a file, plot signals and act on the plots."""

    def setUp(self) -> None:
        """Create temp files, the main window and the controller.

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
        self.first_path_str = self.write_file("first.csv",
                                              FIRST_FILE_TEXT_STR)
        self.second_path_str = self.write_file("second.csv",
                                               SECOND_FILE_TEXT_STR)
        self.main_window = MainWindow()
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.application.processEvents()
        self.box_record_list = []
        self.box_patch = mock.patch.object(
            QMessageBox, "exec", new=lambda box: self.fake_exec(box))
        self.box_patch.start()
        self.addCleanup(self.box_patch.stop)
        self.click_open_file(self.first_path_str)

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
        Outputs: Yes for a question box, otherwise OK (int values).
        """
        self.box_record_list.append(
            (box.windowTitle(), box.icon(), box.text()))
        standard_button = self.message_box_class.StandardButton
        if box.icon() == self.message_box_class.Icon.Question:
            return standard_button.Yes.value
        return standard_button.Ok.value

    def click_open_file(self, path_str: str) -> None:
        """Click Open file with the dialog returning path_str.

        Inputs:
            path_str: the path the patched dialog returns.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QFileDialog
        with mock.patch.object(QFileDialog, "getOpenFileName",
                               return_value=(path_str, "")):
            QTest.mouseClick(self.main_window.top_panel.open_file_button,
                             Qt.MouseButton.LeftButton)
            self.application.processEvents()

    def double_click_signal(self, signal_name_str: str) -> None:
        """Double-click a name in the signal list.

        Inputs:
            signal_name_str: the name to double-click.
        Outputs: none.
        """
        list_widget = self.main_window.signal_list_panel.signal_list_widget
        item = list_widget.findItems(signal_name_str,
                                     self.qt_match_exactly())[0]
        list_widget.itemDoubleClicked.emit(item)
        self.application.processEvents()

    def qt_match_exactly(self):
        """Return Qt's exact match flag.

        Inputs: none.
        Outputs: Qt.MatchFlag.MatchExactly.
        """
        from PyQt6.QtCore import Qt
        return Qt.MatchFlag.MatchExactly

    def drop_signal(self, plot_widget, signal_name_str: str) -> None:
        """Drop a signal name on a plot widget, as the signal list does.

        Inputs:
            plot_widget: the PlotWidget to drop on.
            signal_name_str: the dropped name.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint, QPointF, Qt
        from PyQt6.QtGui import QDragEnterEvent, QDropEvent
        list_widget = self.main_window.signal_list_panel.signal_list_widget
        item = list_widget.findItems(signal_name_str,
                                     self.qt_match_exactly())[0]
        mime_data = list_widget.mimeData([item])
        center_point = QPoint(plot_widget.width() // 2,
                              plot_widget.height() // 2)
        action = Qt.DropAction.CopyAction
        enter_event = QDragEnterEvent(center_point, action, mime_data,
                                      Qt.MouseButton.NoButton,
                                      Qt.KeyboardModifier.NoModifier)
        drop_event = QDropEvent(QPointF(center_point), action, mime_data,
                                Qt.MouseButton.NoButton,
                                Qt.KeyboardModifier.NoModifier)
        plot_widget.dragEnterEvent(enter_event)
        self.assertTrue(enter_event.isAccepted())
        plot_widget.dropEvent(drop_event)
        self.application.processEvents()

    def current_plot_widgets(self) -> list:
        """Return the plot widgets of the current tab, top to bottom.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        panel = self.main_window.plot_panel
        return list(panel.page_dict[panel.current_tab_id()]
                    .plot_widget_list)

    def legend_names(self, plot_widget) -> list:
        """Return the names in a plot's legend.

        Inputs:
            plot_widget: the PlotWidget.
        Outputs: a list of str.
        """
        return [entry_tuple[0]
                for entry_tuple in plot_widget.legend_entry_list()]

    @covers("LLFR-00019", "LLFR-00020", "LLFR-00068", "LLFR-00052",
            "LLFR-00033", "HLFR-00012")
    def test_double_click_creates_plot_with_curve(self) -> None:
        """A double-click draws the signal against time in a new plot.

        Inputs: none.
        Outputs: none.
        """
        from model.curve_colors import PALETTE_COLOR_TUPLE
        self.double_click_signal("speed")
        plot_widget_list = self.current_plot_widgets()
        self.assertEqual(len(plot_widget_list), 1)
        plot_widget = plot_widget_list[0]
        self.assertEqual(self.legend_names(plot_widget), ["speed"])
        self.assertEqual(plot_widget.legend_entry_list()[0][1].lower(),
                         PALETTE_COLOR_TUPLE[0])
        line_list = plot_widget.axes.get_lines()
        curve_line_list = [line for line in line_list
                           if line.get_label() == "speed"]
        self.assertEqual(len(curve_line_list), 1)
        self.assertEqual(list(curve_line_list[0].get_xdata()),
                         [0.0, 0.5, 1.0, 1.5, 2.0])
        self.assertEqual(list(curve_line_list[0].get_ydata()),
                         [0.0, 1.0, 2.0, 3.0, 4.0])
        self.assertEqual(plot_widget.curve_line_width("speed"), 1.0)
        self.assertEqual(self.box_record_list, [])

    @covers("LLFR-00055", "HLFR-00012")
    def test_time_signal_can_be_plotted(self) -> None:
        """Double-clicking Time plots it like any other signal.

        Inputs: none.
        Outputs: none.
        """
        self.double_click_signal("Time")
        plot_widget = self.current_plot_widgets()[0]
        self.assertEqual(self.legend_names(plot_widget), ["Time"])

    @covers("LLFR-00031", "LLFR-00032", "HLFR-00018")
    def test_sixth_plot_shows_full_tab_box(self) -> None:
        """Six double-clicks give 5 plots and the Full Tab box.

        Inputs: none.
        Outputs: none.
        """
        from view.message_boxes import FULL_TAB_TITLE_STR
        for name_str in ("speed", "force", "angle", "Time", "speed"):
            self.double_click_signal(name_str)
        self.assertEqual(len(self.current_plot_widgets()), 5)
        self.assertEqual(self.box_record_list, [])
        self.double_click_signal("force")
        self.assertEqual(len(self.current_plot_widgets()), 5)
        self.assertEqual(len(self.box_record_list), 1)
        title_str, icon, text_str = self.box_record_list[0]
        self.assertEqual(title_str, FULL_TAB_TITLE_STR)
        self.assertEqual(icon, self.message_box_class.Icon.Information)
        self.assertIn("tab", text_str.lower())
        self.assertIn("delete a plot", text_str.lower())

    @covers("LLFR-00021", "LLFR-00036", "LLFR-00037", "LLFR-00056",
            "LLFR-00057", "HLFR-00013", "HLFR-00020", "HLFR-00021")
    def test_drop_adds_curve_once(self) -> None:
        """A drop adds a curve; dropping it again changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.double_click_signal("speed")
        plot_widget = self.current_plot_widgets()[0]
        self.drop_signal(plot_widget, "force")
        self.assertEqual(self.legend_names(plot_widget), ["speed", "force"])
        color_list = [entry_tuple[1].lower()
                      for entry_tuple in plot_widget.legend_entry_list()]
        self.assertEqual(len(set(color_list)), 2)
        self.drop_signal(plot_widget, "force")
        self.drop_signal(plot_widget, "speed")
        self.assertEqual(self.legend_names(plot_widget), ["speed", "force"])
        self.assertEqual(len(self.current_plot_widgets()), 1)
        self.assertEqual(self.box_record_list, [])

    @covers("LLFR-00042", "HLFR-00024")
    def test_tip_button_sets_tip_tool(self) -> None:
        """The Tip button turns the Tip tool on and off in every plot.

        Inputs: none.
        Outputs: none.
        """
        self.double_click_signal("speed")
        self.double_click_signal("force")
        tip_button = self.main_window.top_panel.tip_button
        tip_button.click()
        self.assertTrue(all(plot_widget.plot_tool_str == "tip"
                            for plot_widget in self.current_plot_widgets()))
        self.double_click_signal("angle")
        self.assertEqual(self.current_plot_widgets()[2].plot_tool_str, "tip")
        tip_button.click()
        self.assertTrue(all(plot_widget.plot_tool_str == ""
                            for plot_widget in self.current_plot_widgets()))

    @covers("LLFR-00045", "LLFR-00047", "HLFR-00025")
    def test_pin_and_delete_tip(self) -> None:
        """A pin request draws a pinned tip; Delete removes it.

        Inputs: none.
        Outputs: none.
        """
        self.double_click_signal("speed")
        plot_widget = self.current_plot_widgets()[0]
        plot_widget.tip_pin_requested.emit("speed", 1.0, 2.0)
        self.application.processEvents()
        self.assertEqual(plot_widget.pinned_tip_count(), 1)
        plot_widget.pinned_tip_delete_requested.emit(0)
        self.application.processEvents()
        self.assertEqual(plot_widget.pinned_tip_count(), 0)

    @covers("LLFR-00041", "HLFR-00023")
    def test_width_request_redraws_curve(self) -> None:
        """Choosing width 5 draws the curve wider than width 1.

        Inputs: none.
        Outputs: none.
        """
        self.double_click_signal("speed")
        plot_widget = self.current_plot_widgets()[0]
        plot_widget.curve_width_requested.emit("speed", 5)
        self.application.processEvents()
        self.assertGreater(plot_widget.curve_line_width("speed"), 1.0)

    @covers("LLFR-00039", "LLFR-00051", "LLFR-00049", "HLFR-00022",
            "HLFR-00019")
    def test_delete_signals_then_plot_goes(self) -> None:
        """Deleting a curve removes it; the last one removes the plot.

        Inputs: none.
        Outputs: none.
        """
        self.double_click_signal("speed")
        plot_widget = self.current_plot_widgets()[0]
        self.drop_signal(plot_widget, "force")
        plot_widget.curve_delete_requested.emit("speed")
        self.application.processEvents()
        self.assertEqual(self.legend_names(plot_widget), ["force"])
        plot_widget.curve_delete_requested.emit("force")
        self.application.processEvents()
        self.assertEqual(self.current_plot_widgets(), [])
        self.assertEqual(self.box_record_list, [])

    @covers("LLFR-00049", "HLFR-00019")
    def test_delete_plot_request(self) -> None:
        """"Delete plot" removes that plot only.

        Inputs: none.
        Outputs: none.
        """
        self.double_click_signal("speed")
        self.double_click_signal("force")
        first, second = self.current_plot_widgets()
        first.plot_delete_requested.emit()
        self.application.processEvents()
        self.assertEqual(self.current_plot_widgets(), [second])

    @covers("LLFR-00015", "LLFR-00016", "LLFR-00013", "HLFR-00010")
    def test_replacing_file_leaves_one_empty_tab(self) -> None:
        """Opening a second file with Yes closes all tabs and plots.

        Inputs: none.
        Outputs: none.
        """
        from view.message_boxes import REPLACE_FILE_TITLE_STR
        self.double_click_signal("speed")
        self.main_window.plot_panel.add_tab_button.click()
        self.double_click_signal("force")
        self.assertEqual(self.main_window.tab_name_list(),
                         ["Tab 1", "Tab 2"])
        self.click_open_file(self.second_path_str)
        self.assertEqual([record[0] for record in self.box_record_list],
                         [REPLACE_FILE_TITLE_STR])
        self.assertEqual(self.main_window.tab_name_list(), ["Tab 1"])
        self.assertEqual(self.current_plot_widgets(), [])
        self.assertEqual(self.main_window.plot_panel.plot_widget_dict, {})
        self.double_click_signal("pressure")
        self.assertEqual(self.legend_names(self.current_plot_widgets()[0]),
                         ["pressure"])


if __name__ == "__main__":
    unittest.main()
