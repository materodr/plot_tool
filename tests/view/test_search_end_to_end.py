"""End-to-end tests of the signal search (HLFR-00033, HLFR-00034).

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

FIRST_NAME_LIST = [
    "Time", "Engine_Speed", "Pressure", "Sine_3Hz",
    "mateus_soares_rodrigues 2025", "mateus_soares_rodrigues 2026"]
FIRST_FILE_TEXT_STR = (
    ",".join(FIRST_NAME_LIST) + "\n"
    "0,10,1,0,5,6\n0.5,20,2,1,5,6\n1,30,3,0,5,6\n")
SECOND_NAME_LIST = ["Time", "voltage", "current"]
SECOND_FILE_TEXT_STR = "Time,voltage,current\n0,1,2\n1,2,3\n"
# LLFR-00905: the names shown in the app have the prefix of their file.
FIRST_SHOWN_LIST = ["file1_" + name_str for name_str in FIRST_NAME_LIST]
SECOND_SHOWN_LIST = ["file2_" + name_str for name_str in SECOND_NAME_LIST]


@requires_qt
class SearchEndToEndTest(unittest.TestCase):
    """Open a file, type in the search box and plot the results."""

    def setUp(self) -> None:
        """Create temp files, the main window and open the first file.

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
        self.panel = self.main_window.signal_list_panel
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
        with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                        return_value=path_str):
            QTest.mouseClick(self.main_window.top_panel.open_file_button,
                             Qt.MouseButton.LeftButton)
            self.application.processEvents()
            # LLFR-00984: the files are collapsed after an open; these
            # tests read the shown signals.
            expand_all_files(self.controller)

    def type_search(self, text_str: str) -> None:
        """Replace the search box text by typing text_str.

        Inputs:
            text_str: the text to type.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        self.panel.search_box.clear()
        self.panel.search_box.setFocus()
        QTest.keyClicks(self.panel.search_box, text_str)
        self.application.processEvents()

    def shown_items(self) -> list:
        """Return the signal items shown, from top to bottom.

        Inputs: none.
        Outputs: a list of QListWidgetItem, without the file name rows.
        """
        from view.signal_list_panel import SIGNAL_ROW_STR
        return self.panel.signal_list_widget.row_items(SIGNAL_ROW_STR)

    def current_plot_widgets(self) -> list:
        """Return the plot widgets of the current tab, top to bottom.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        plot_panel = self.main_window.plot_panel
        return list(plot_panel.page_dict[plot_panel.current_tab_id()]
                    .plot_widget_list)

    def legend_names(self, plot_widget) -> list:
        """Return the names in a plot's legend.

        Inputs:
            plot_widget: the PlotWidget.
        Outputs: a list of str.
        """
        return [entry_tuple[0]
                for entry_tuple in plot_widget.legend_entry_list()]

    def drop_item(self, plot_widget, item) -> None:
        """Drop the drag data of a list item on a plot widget.

        Inputs:
            plot_widget: the PlotWidget to drop on.
            item: the QListWidgetItem being dragged.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint, QPointF, Qt
        from PyQt6.QtGui import QDragEnterEvent, QDropEvent
        list_widget = self.panel.signal_list_widget
        mime_data = list_widget.model().mimeData(
            [list_widget.indexFromItem(item)])
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

    @covers("LLFR-00094", "LLFR-00054", "HLFR-00033")
    def test_file_open_shows_all_names_and_empty_box(self) -> None:
        """After opening, the box is empty and all names are shown.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.panel.search_box.text(), "")
        self.assertEqual(self.panel.signal_name_list(), FIRST_SHOWN_LIST)
        self.assertEqual(self.panel.no_match_message(), "")
        self.assertEqual(self.box_record_list, [])

    @covers("LLFR-00095", "LLFR-00098", "LLFR-00099", "LLFR-00100",
            "LLFR-00101", "LLFR-00105", "HLFR-00033", "HLFR-00034",
            "LLFR-00566", "LLFR-00567")
    def test_requirement_examples(self) -> None:
        """The examples of the requirements filter the list.

        Inputs: none.
        Outputs: none.
        """
        expected_dict = {
            "enginespeed": ["file1_Engine_Speed"],
            "PRESSURE": ["file1_Pressure"],
            "presure": ["file1_Pressure"],
            "sine_2hz": ["file1_Sine_3Hz"],
            "mate so 25": ["file1_mateus_soares_rodrigues 2025"],
            "speed": ["file1_Engine_Speed"],
        }
        for text_str, expected_list in expected_dict.items():
            with self.subTest(text_str=text_str):
                self.type_search(text_str)
                self.assertEqual(self.panel.signal_name_list(),
                                 expected_list)
                self.assertEqual(self.panel.no_match_message(), "")

    @covers("LLFR-00096", "LLFR-00054")
    def test_spaces_and_clear_show_all(self) -> None:
        """Spaces only, or clearing the box, show every name again.

        Inputs: none.
        Outputs: none.
        """
        self.type_search("speed")
        self.type_search("   ")
        self.assertEqual(self.panel.signal_name_list(), FIRST_SHOWN_LIST)
        self.type_search("speed")
        self.panel.search_box.clear()
        self.application.processEvents()
        self.assertEqual(self.panel.signal_name_list(), FIRST_SHOWN_LIST)

    @covers("LLFR-00097", "LLFR-00565", "LLFR-00640", "LLFR-00641")
    def test_no_match_message(self) -> None:
        """No match shows "No matching signals" below the file's row.

        Inputs: none.
        Outputs: none.
        """
        from view.signal_list_panel import FILE_ROW_STR, NO_MATCH_ROW_STR
        self.type_search("xyzw")
        self.assertEqual(self.panel.signal_name_list(), [])
        self.assertEqual(self.panel.no_match_message(),
                         "No matching signals")
        self.assertEqual(self.panel.row_list(), [
            (FILE_ROW_STR, self.panel.file_row_texts()[0]),
            (NO_MATCH_ROW_STR, "No matching signals")])
        self.type_search("pressure")
        self.assertEqual(self.panel.no_match_message(), "")
        self.assertEqual(self.panel.signal_name_list(), ["file1_Pressure"])
        self.assertEqual(self.box_record_list, [])

    @covers("LLFR-00103", "LLFR-00019", "LLFR-00020", "HLFR-00012")
    def test_double_click_filtered_item_plots_it(self) -> None:
        """Double-clicking a search result plots that signal.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.type_search("presure")
        item_list = self.shown_items()
        self.assertEqual([item.text() for item in item_list],
                         ["file1_Pressure"])
        list_widget = self.panel.signal_list_widget
        list_widget.doItemsLayout()
        self.application.processEvents()
        center = list_widget.visualItemRect(item_list[0]).center()
        QTest.mouseClick(list_widget.viewport(), Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, center)
        QTest.mouseDClick(list_widget.viewport(), Qt.MouseButton.LeftButton,
                          Qt.KeyboardModifier.NoModifier, center)
        self.application.processEvents()
        plot_widget_list = self.current_plot_widgets()
        self.assertEqual(len(plot_widget_list), 1)
        self.assertEqual(self.legend_names(plot_widget_list[0]),
                         ["file1_Pressure"])
        # The search stays as typed after plotting.
        self.assertEqual(self.panel.search_box.text(), "presure")

    @covers("LLFR-00103", "LLFR-00021", "HLFR-00013")
    def test_drag_filtered_item_adds_it(self) -> None:
        """Dropping a search result on a plot adds that signal.

        Inputs: none.
        Outputs: none.
        """
        self.type_search("pressure")
        self.panel.signal_list_widget.itemDoubleClicked.emit(
            self.shown_items()[0])
        self.application.processEvents()
        plot_widget = self.current_plot_widgets()[0]
        self.type_search("mate so 25")
        item_list = self.shown_items()
        self.assertEqual([item.text() for item in item_list],
                         ["file1_mateus_soares_rodrigues 2025"])
        self.drop_item(plot_widget, item_list[0])
        self.assertEqual(self.legend_names(plot_widget),
                         ["file1_Pressure",
                          "file1_mateus_soares_rodrigues 2025"])
        self.assertEqual(len(self.current_plot_widgets()), 1)

    @covers("LLFR-00104", "LLFR-00920", "LLFR-00922", "HLFR-00117")
    def test_open_clears_search(self) -> None:
        """Opening a second file clears the box, with no question.

        Inputs: none.
        Outputs: none.
        """
        self.type_search("xyzw")
        self.click_open_file(self.second_path_str)
        self.assertEqual(self.box_record_list, [])
        self.assertEqual(self.panel.search_box.text(), "")
        self.assertEqual(self.panel.signal_name_list(),
                         FIRST_SHOWN_LIST + SECOND_SHOWN_LIST)
        self.assertEqual(self.panel.no_match_message(), "")
        self.type_search("volt")
        self.assertEqual(self.panel.signal_name_list(), ["file2_voltage"])


if __name__ == "__main__":
    unittest.main()
