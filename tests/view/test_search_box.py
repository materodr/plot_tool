"""Tests for the search box of the signal list panel (HLFR-00033)."""

import unittest

from tests.support import covers, get_qt_application, requires_qt

NAME_LIST = ["Time", "Engine_Speed", "Pressure"]
NO_MATCH_TEXT_STR = "No matching signals"


@requires_qt
class SearchBoxTest(unittest.TestCase):
    """Check the box, its signal and the no-match text."""

    def setUp(self) -> None:
        """Create and show a signal list panel.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.signal_list_panel import SignalListPanel
        self.panel = SignalListPanel()
        self.panel.resize(250, 400)
        self.panel.show()
        self.application.processEvents()
        self.text_list = []
        self.panel.search_text_changed.connect(self.text_list.append)
        self.double_clicked_list = []
        self.panel.signal_double_clicked.connect(
            self.double_clicked_list.append)

    def tearDown(self) -> None:
        """Close and delete the panel.

        Inputs: none.
        Outputs: none.
        """
        self.panel.close()
        self.panel.deleteLater()
        self.application.processEvents()

    @covers("LLFR-00094", "HLFR-00033")
    def test_search_box_exists(self) -> None:
        """The panel has a visible, empty line edit with a hint.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QLineEdit
        search_box = self.panel.search_box
        self.assertIsInstance(search_box, QLineEdit)
        self.assertIs(self.panel.findChild(QLineEdit, "signal_search_box"),
                      search_box)
        self.assertTrue(search_box.isVisible())
        self.assertEqual(search_box.text(), "")
        self.assertIn("search", search_box.placeholderText().lower())
        self.assertTrue(search_box.isClearButtonEnabled())

    @covers("LLFR-00094", "HLFR-00033")
    def test_search_box_directly_below_list(self) -> None:
        """The box is directly under the list, aligned with it, with
        nothing between them.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QWidget
        list_widget = self.panel.signal_list_widget
        search_box = self.panel.search_box
        list_geometry = list_widget.geometry()
        box_geometry = search_box.geometry()
        list_end_i = list_geometry.top() + list_geometry.height()
        self.assertGreaterEqual(box_geometry.top(), list_end_i)
        layout = self.panel.panel_layout
        # Directly below: only the layout spacing separates them.
        self.assertLessEqual(box_geometry.top() - list_end_i,
                             max(layout.spacing(), 0) + 1)
        self.assertLess(abs(box_geometry.left() - list_geometry.left()), 2)
        # Nothing between them in the layout; the search box is the
        # last row.
        self.assertEqual(layout.indexOf(search_box),
                         layout.indexOf(list_widget) + 1)
        self.assertEqual(layout.indexOf(search_box), layout.count() - 1)
        # No other visible widget of the panel lies between them.
        for child in self.panel.findChildren(QWidget):
            if (child in (list_widget, search_box)
                    or child.parentWidget() is not self.panel
                    or not child.isVisible()):
                continue
            child_top_i = child.geometry().top()
            child_end_i = child_top_i + child.geometry().height()
            with self.subTest(child=child.objectName()):
                self.assertFalse(child_top_i < box_geometry.top()
                                 and child_end_i > list_end_i)
        # The list keeps most of the height.
        self.assertGreater(list_geometry.height(), box_geometry.height())

    @covers("LLFR-00095")
    def test_typing_emits_every_change(self) -> None:
        """Every typed character emits the new text.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        self.panel.search_box.setFocus()
        QTest.keyClicks(self.panel.search_box, "pre")
        self.application.processEvents()
        self.assertEqual(self.text_list, ["p", "pr", "pre"])
        self.assertEqual(self.panel.search_text(), "pre")

    @covers("LLFR-00104")
    def test_clear_search_empties_box(self) -> None:
        """clear_search empties the box and reports the change.

        Inputs: none.
        Outputs: none.
        """
        self.panel.search_box.setText("speed")
        self.panel.clear_search()
        self.assertEqual(self.panel.search_box.text(), "")
        self.assertEqual(self.text_list, ["speed", ""])

    @covers("LLFR-00097")
    def test_no_match_message_hidden_at_start(self) -> None:
        """No message is shown before any search.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.panel.no_match_message(), "")
        self.assertEqual(self.panel.row_list(), [])

    @covers("LLFR-00097", "LLFR-00565", "LLFR-00641", "LLFR-00639")
    def test_no_match_message_below_the_file_row(self) -> None:
        """The message is a row below the file name row, then goes.

        Inputs: none.
        Outputs: none.
        """
        from view.signal_list_panel import (
            FILE_ROW_STR, NO_MATCH_ROW_STR, SIGNAL_ROW_STR)
        self.panel.show_signal_groups(
            [(1, "file1_a.csv", [], NO_MATCH_TEXT_STR),
             (2, "file2_b.csv", ["file2_Pressure"], "")])
        self.application.processEvents()
        self.assertEqual(self.panel.row_list(), [
            (FILE_ROW_STR, "file1_a.csv"),
            (NO_MATCH_ROW_STR, NO_MATCH_TEXT_STR),
            (FILE_ROW_STR, "file2_b.csv"),
            (SIGNAL_ROW_STR, "file2_Pressure")])
        self.assertEqual(self.panel.no_match_message(), NO_MATCH_TEXT_STR)
        self.assertEqual(self.panel.signal_name_list(), ["file2_Pressure"])
        # The text lies inside the visible area of the list.
        list_widget = self.panel.signal_list_widget
        no_match_item = list_widget.item(1)
        self.assertTrue(list_widget.viewport().rect().contains(
            list_widget.visualItemRect(no_match_item)))
        self.panel.show_signal_groups(
            [(1, "file1_a.csv", NAME_LIST, ""),
             (2, "file2_b.csv", ["file2_Pressure"], "")])
        self.assertEqual(self.panel.no_match_message(), "")
        self.assertEqual(self.panel.signal_name_list(),
                         NAME_LIST + ["file2_Pressure"])

    @covers("LLFR-00097", "LLFR-00019", "LLFR-00021", "LLFR-00565")
    def test_message_is_not_a_signal(self) -> None:
        """The message row can't be clicked, double-clicked or dragged.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        list_widget = self.panel.signal_list_widget
        self.panel.show_signal_groups(
            [(1, "file1_a.csv", [], NO_MATCH_TEXT_STR)])
        self.application.processEvents()
        no_match_item = list_widget.item(1)
        self.assertEqual(no_match_item.text(), NO_MATCH_TEXT_STR)
        self.assertFalse(no_match_item.flags()
                         & Qt.ItemFlag.ItemIsSelectable)
        self.assertFalse(no_match_item.flags()
                         & Qt.ItemFlag.ItemIsDragEnabled)
        center = list_widget.visualItemRect(no_match_item).center()
        QTest.mouseClick(list_widget.viewport(), Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, center)
        QTest.mouseDClick(list_widget.viewport(), Qt.MouseButton.LeftButton,
                          Qt.KeyboardModifier.NoModifier, center)
        self.application.processEvents()
        self.assertEqual(self.double_clicked_list, [])
        self.assertEqual(list_widget.selectedItems(), [])
        self.assertEqual(self.panel.selected_signal_names(), [])
        mime_data = list_widget.mimeData([no_match_item])
        self.assertEqual(mime_data.text(), "")

    @covers("LLFR-00103", "LLFR-00019", "LLFR-00021")
    def test_filtered_items_keep_real_names(self) -> None:
        """A filtered list still double-clicks and drags real names.

        Inputs: none.
        Outputs: none.
        """
        from view.signal_list_panel import SIGNAL_MIME_TYPE_STR
        list_widget = self.panel.signal_list_widget
        self.panel.show_signal_names(["Pressure", "Engine_Speed"])
        list_widget.itemDoubleClicked.emit(list_widget.item(1))
        self.assertEqual(self.double_clicked_list, ["Engine_Speed"])
        mime_data = list_widget.mimeData([list_widget.item(0)])
        self.assertEqual(mime_data.text(), "Pressure")
        self.assertEqual(
            bytes(mime_data.data(SIGNAL_MIME_TYPE_STR)).decode("utf-8"),
            "Pressure")


@requires_qt
class MainWindowSearchFacadeTest(unittest.TestCase):
    """Check the search facade of the main window."""

    def setUp(self) -> None:
        """Create the main window without a controller.

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

    @covers("LLFR-00095", "LLFR-00097", "LLFR-00104")
    def test_facade_passes_text_and_controls_panel(self) -> None:
        """The handler gets the text; the facade drives the panel.

        Inputs: none.
        Outputs: none.
        """
        panel = self.main_window.signal_list_panel
        # No handler yet: typing must not fail.
        panel.search_box.setText("a")
        text_list = []
        self.main_window.set_search_text_handler(text_list.append)
        panel.search_box.setText("ab")
        self.assertEqual(text_list, ["ab"])
        self.main_window.show_signal_groups(
            [(1, "file1_a.csv", [], NO_MATCH_TEXT_STR)])
        self.assertEqual(panel.no_match_message(), NO_MATCH_TEXT_STR)
        self.assertEqual(panel.file_row_texts(), ["file1_a.csv"])
        self.main_window.show_signal_groups(
            [(1, "file1_a.csv", ["file1_Time"], "")])
        self.assertEqual(panel.no_match_message(), "")
        self.main_window.clear_search()
        self.assertEqual(panel.search_box.text(), "")
        self.assertEqual(text_list, ["ab", ""])


if __name__ == "__main__":
    unittest.main()
