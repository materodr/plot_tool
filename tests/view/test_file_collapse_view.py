"""Tests for the file name rows that hide and show their signals.

The signal list shows each data file like a folder of a folder tree
(HLFR-00123): its file name row starts with a ``[-]`` icon while its
signals are shown and ``[+]`` while they are hidden. These tests need
PyQt6 and run in CI. The rules of the states (open, search, close) are
also tested without Qt in tests/controller/test_signal_list_controller.
"""

import os
import tempfile
import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt
from tests.support import OPEN_FILE_DIALOG_TARGET_STR

FIRST_ROW_STR = "file1_a.csv"
SECOND_ROW_STR = "file2_b.csv"
# The time signal of a.csv is not its first column (LLFR-00995).
FIRST_TEXT_STR = "Speed,Time,Torque\n0,0,5\n1,1,6\n2,2,7\n"
SECOND_TEXT_STR = "Time,Force\n0,3\n1,4\n2,5\n"
FIRST_SIGNAL_LIST = ["file1_Time", "file1_Speed", "file1_Torque"]
SECOND_SIGNAL_LIST = ["file2_Time", "file2_Force"]


@requires_qt
class ExpandIconPictureTest(unittest.TestCase):
    """The drawing of the [-] and [+] icons (LLFR-00982)."""

    def setUp(self) -> None:
        """Start the Qt application.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()

    def drawn_pixel_set(self, image) -> set:
        """Return the pixels of an image that are drawn.

        Inputs:
            image: a QImage.
        Outputs: a set of (x, y) of the pixels that are not transparent.
        """
        return {(x_i, y_i) for x_i in range(image.width())
                for y_i in range(image.height())
                if image.pixelColor(x_i, y_i).alpha() > 0}

    @covers("LLFR-00982", "LLFR-00980", "LLFR-00981", "HLFR-00123")
    def test_icons_are_brackets_with_a_sign_in_muted_color(self) -> None:
        """Both icons share the brackets and the minus line; [+] adds a
        vertical bar; the lines are in the muted text color.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor
        from view import theme
        from view.signal_list_panel import (
            EXPAND_ICON_PIXEL_RATIO_F, EXPAND_ICON_SIZE_I, expand_icon,
            expand_icon_pixmap)
        minus_image = expand_icon_pixmap(False).toImage()
        plus_image = expand_icon_pixmap(True).toImage()
        side_i = int(EXPAND_ICON_SIZE_I * EXPAND_ICON_PIXEL_RATIO_F)
        self.assertEqual((minus_image.width(), minus_image.height()),
                         (side_i, side_i))
        minus_set = self.drawn_pixel_set(minus_image)
        plus_set = self.drawn_pixel_set(plus_image)
        self.assertTrue(minus_set)
        # [+] is [-] with a vertical bar more.
        self.assertTrue(minus_set < plus_set)
        middle_i = side_i // 2
        # The minus line crosses the middle of both icons.
        self.assertGreater(minus_image.pixelColor(middle_i, middle_i)
                           .alpha(), 0)
        # The vertical bar, above the middle, only in [+].
        bar_y_i = int(4 * EXPAND_ICON_PIXEL_RATIO_F)
        self.assertGreater(plus_image.pixelColor(middle_i, bar_y_i)
                           .alpha(), 0)
        self.assertEqual(minus_image.pixelColor(middle_i, bar_y_i)
                         .alpha(), 0)
        # The brackets: the left and right edges, top to bottom, and a
        # transparent background in the corners.
        for y_i in (side_i // 4, middle_i, 3 * side_i // 4):
            self.assertGreater(
                minus_image.pixelColor(int(EXPAND_ICON_PIXEL_RATIO_F),
                                       y_i).alpha(), 0)
            self.assertGreater(
                minus_image.pixelColor(
                    side_i - 1 - int(EXPAND_ICON_PIXEL_RATIO_F),
                    y_i).alpha(), 0)
        # Between the two brackets, above and below the sign, nothing
        # is drawn.
        for image in (minus_image, plus_image):
            self.assertEqual(image.pixelColor(middle_i, 1).alpha(), 0)
            self.assertEqual(image.pixelColor(middle_i, side_i - 2)
                             .alpha(), 0)
        # The muted text color of the panel.
        muted_color = QColor(theme.MUTED_TEXT_COLOR_STR)
        for image in (minus_image, plus_image):
            for x_i, y_i in self.drawn_pixel_set(image):
                color = image.pixelColor(x_i, y_i)
                if color.alpha() < 250:
                    continue
                distance_f = ((color.red() - muted_color.red()) ** 2
                              + (color.green() - muted_color.green()) ** 2
                              + (color.blue() - muted_color.blue()) ** 2
                              ) ** 0.5
                self.assertLess(distance_f, 30.0, (x_i, y_i))
        self.assertFalse(expand_icon(False).isNull())
        self.assertFalse(expand_icon(True).isNull())


@requires_qt
class FileCollapseEndToEndTest(unittest.TestCase):
    """Two files opened together in the main window."""

    def setUp(self) -> None:
        """Create the window and the controllers and open two files.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        path_list = []
        for name_str, text_str in (("a.csv", FIRST_TEXT_STR),
                                   ("b.csv", SECOND_TEXT_STR)):
            path_str = os.path.join(self.temporary_folder.name, name_str)
            with open(path_str, "w", encoding="utf-8") as data_file:
                data_file.write(text_str)
            path_list.append(path_str)
        self.path_list = path_list
        self.main_window = MainWindow()
        self.main_window.resize(1000, 800)
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.main_window.show()
        self.application.processEvents()
        self.panel = self.main_window.signal_list_panel
        self.widget = self.panel.signal_list_widget
        # LLFR-00951: both files selected in one dialog.
        with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                        return_value=list(path_list)):
            self.controller.file_controller.open_file_requested()
        self.application.processEvents()
        self.widget.doItemsLayout()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def item_of(self, text_str: str):
        """Return the row of the list with a given text.

        Inputs:
            text_str: the text of the row.
        Outputs: the QListWidgetItem.
        """
        for item in self.widget.row_items():
            if item.text() == text_str:
                return item
        self.fail(f"no row {text_str}")
        return None

    def icon_point(self, row_str: str):
        """Return a point on the icon of a file name row.

        Inputs:
            row_str: the text of the file name row.
        Outputs: a QPoint in the viewport's coordinates.
        """
        from PyQt6.QtCore import QPoint
        self.widget.doItemsLayout()
        row_rect = self.widget.visualItemRect(self.item_of(row_str))
        self.assertFalse(row_rect.isEmpty())
        return QPoint(row_rect.left() + 14, row_rect.center().y())

    def text_point(self, row_str: str):
        """Return the center of a row, on its text.

        Inputs:
            row_str: the text of the row.
        Outputs: a QPoint in the viewport's coordinates.
        """
        self.widget.doItemsLayout()
        return self.widget.visualItemRect(self.item_of(row_str)).center()

    def click(self, point, modifier_name_str: str = "NoModifier") -> None:
        """Left-click the list at a point.

        Inputs:
            point: a QPoint in the viewport's coordinates.
            modifier_name_str: the name of a Qt.KeyboardModifier.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.mouseClick(self.widget.viewport(), Qt.MouseButton.LeftButton,
                         getattr(Qt.KeyboardModifier, modifier_name_str),
                         point)
        self.application.processEvents()

    def click_icon(self, row_str: str) -> None:
        """Click the icon of a file name row.

        Inputs:
            row_str: the text of the file name row.
        Outputs: none.
        """
        self.click(self.icon_point(row_str))

    def icons(self) -> list:
        """Return the icon of each file name row, top to bottom.

        Inputs: none.
        Outputs: a list of "[-]" or "[+]".
        """
        return [self.panel.file_row_icon_text(row_str)
                for row_str in self.panel.file_row_texts()]

    @covers("LLFR-00987", "LLFR-00981", "HLFR-00123", "HLFR-00122")
    def test_files_opened_together_are_collapsed(self) -> None:
        """Both rows show [+] and no signal row is shown.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.panel.file_row_texts(),
                         [FIRST_ROW_STR, SECOND_ROW_STR])
        self.assertEqual(self.icons(), ["[+]", "[+]"])
        self.assertEqual(self.panel.signal_name_list(), [])
        self.assertEqual(self.panel.no_match_message(), "")
        for row_str in (FIRST_ROW_STR, SECOND_ROW_STR):
            self.assertFalse(self.item_of(row_str).icon().isNull())

    @covers("LLFR-00983", "LLFR-00984", "LLFR-00980", "LLFR-00981",
            "LLFR-00995", "LLFR-00332", "HLFR-00123", "HLFR-00071")
    def test_icon_click_shows_and_hides_the_signals(self) -> None:
        """[+] shows the signals, the time signal first and green; [-]
        hides them again; the other file is not changed.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor
        from view import theme
        self.click_icon(FIRST_ROW_STR)
        self.assertEqual(self.icons(), ["[-]", "[+]"])
        self.assertEqual(self.panel.signal_name_list(), FIRST_SIGNAL_LIST)
        self.assertEqual(self.panel.row_list()[1],
                         ("signal", "file1_Time"))
        self.assertEqual(self.panel.name_color_str("file1_Time"),
                         QColor(theme.TIME_SIGNAL_TEXT_COLOR_STR).name())
        self.click_icon(SECOND_ROW_STR)
        self.assertEqual(self.icons(), ["[-]", "[-]"])
        self.assertEqual(self.panel.signal_name_list(),
                         FIRST_SIGNAL_LIST + SECOND_SIGNAL_LIST)
        self.click_icon(FIRST_ROW_STR)
        self.assertEqual(self.icons(), ["[+]", "[-]"])
        self.assertEqual(self.panel.signal_name_list(), SECOND_SIGNAL_LIST)
        self.assertEqual(self.panel.file_row_texts(),
                         [FIRST_ROW_STR, SECOND_ROW_STR])

    @covers("LLFR-00983", "LLFR-00984", "LLFR-00646", "HLFR-00123")
    def test_click_on_the_row_text_changes_nothing(self) -> None:
        """Only the icon hides or shows the signals.

        Inputs: none.
        Outputs: none.
        """
        self.click(self.text_point(FIRST_ROW_STR))
        self.assertEqual(self.icons(), ["[+]", "[+]"])
        self.assertEqual(self.panel.signal_name_list(), [])

    @covers("LLFR-00985", "LLFR-00991", "LLFR-00627", "LLFR-00292",
            "HLFR-00123", "HLFR-00063")
    def test_selection_with_the_icons(self) -> None:
        """An icon click selects nothing; hidden signals leave the
        selection and stay unselected when shown again.

        Inputs: none.
        Outputs: none.
        """
        self.click_icon(FIRST_ROW_STR)
        self.click(self.text_point("file1_Speed"))
        self.assertEqual(self.panel.selected_signal_names(),
                         ["file1_Speed"])
        # LLFR-00985: opening the other file keeps the selection.
        self.click_icon(SECOND_ROW_STR)
        self.assertEqual(self.panel.selected_signal_names(),
                         ["file1_Speed"])
        self.click(self.text_point("file2_Force"), "ControlModifier")
        self.assertEqual(self.panel.selected_signal_names(),
                         ["file1_Speed", "file2_Force"])
        # LLFR-00991: the hidden signal leaves the selection.
        self.click_icon(FIRST_ROW_STR)
        self.assertEqual(self.panel.selected_signal_names(),
                         ["file2_Force"])
        # LLFR-00627: shown again, it stays unselected.
        self.click_icon(FIRST_ROW_STR)
        self.assertEqual(self.panel.selected_signal_names(),
                         ["file2_Force"])
        self.assertIn("file1_Speed", self.panel.signal_name_list())

    @covers("LLFR-00986", "LLFR-00645", "HLFR-00123")
    def test_press_on_the_icon_starts_no_drag(self) -> None:
        """A press on the icon followed by moves drags nothing.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtTest import QTest
        drag_list = []
        self.widget.startDrag = drag_list.append
        viewport = self.widget.viewport()
        start_point = self.icon_point(FIRST_ROW_STR)
        QTest.mousePress(viewport, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, start_point)
        self.application.processEvents()
        for step_i in range(1, 6):
            QTest.mouseMove(viewport, start_point + QPoint(10 * step_i,
                                                           12 * step_i))
            self.application.processEvents()
        QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton,
                           Qt.KeyboardModifier.NoModifier,
                           start_point + QPoint(50, 60))
        self.application.processEvents()
        self.assertEqual(drag_list, [])
        self.assertEqual(self.panel.selected_signal_names(), [])
        # The press was a click on the icon.
        self.assertEqual(self.icons(), ["[-]", "[+]"])

    @covers("LLFR-00988", "LLFR-00989", "LLFR-00990", "LLFR-00996",
            "HLFR-00123", "HLFR-00033")
    def test_search_expands_the_files_until_it_is_cleared(self) -> None:
        """A search shows every file with its matches; an icon click
        hides them during the search; clearing restores the states.

        Inputs: none.
        Outputs: none.
        """
        self.click_icon(SECOND_ROW_STR)
        self.panel.search_box.setText("e")
        self.application.processEvents()
        self.assertEqual(self.icons(), ["[-]", "[-]"])
        # LLFR-00996: the matching time signal is first below its row.
        self.assertEqual(self.panel.signal_name_list()[0], "file1_Time")
        self.assertIn("file2_Force", self.panel.signal_name_list())
        self.panel.search_box.setText("torq")
        self.application.processEvents()
        self.assertEqual(self.panel.signal_name_list(), ["file1_Torque"])
        self.assertEqual(self.panel.no_match_message(),
                         "No matching signals")
        # LLFR-00989: hide the matches of file 1 and the no-match text
        # of file 2 during the search.
        self.click_icon(FIRST_ROW_STR)
        self.click_icon(SECOND_ROW_STR)
        self.assertEqual(self.icons(), ["[+]", "[+]"])
        self.assertEqual(self.panel.signal_name_list(), [])
        self.assertEqual(self.panel.no_match_message(), "")
        # LLFR-00990: file 1 collapsed and file 2 expanded, as before.
        self.panel.search_box.setText("")
        self.application.processEvents()
        self.assertEqual(self.icons(), ["[+]", "[-]"])
        self.assertEqual(self.panel.signal_name_list(), SECOND_SIGNAL_LIST)

    @covers("LLFR-00992", "LLFR-00993", "HLFR-00123")
    def test_left_and_right_keys_on_a_file_row(self) -> None:
        """Right expands and Left collapses the current file name row.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QItemSelectionModel, Qt
        from PyQt6.QtTest import QTest
        self.widget.setFocus()
        self.widget.setCurrentItem(
            self.item_of(FIRST_ROW_STR),
            QItemSelectionModel.SelectionFlag.NoUpdate)
        QTest.keyClick(self.widget, Qt.Key.Key_Right)
        self.application.processEvents()
        self.assertEqual(self.icons(), ["[-]", "[+]"])
        self.assertEqual(self.panel.signal_name_list(), FIRST_SIGNAL_LIST)
        # The row stays current, so the keys can be pressed again.
        self.assertEqual(self.widget.currentItem().text(), FIRST_ROW_STR)
        QTest.keyClick(self.widget, Qt.Key.Key_Right)
        self.application.processEvents()
        self.assertEqual(self.icons(), ["[-]", "[+]"])
        QTest.keyClick(self.widget, Qt.Key.Key_Left)
        self.application.processEvents()
        self.assertEqual(self.icons(), ["[+]", "[+]"])
        self.assertEqual(self.panel.signal_name_list(), [])
        QTest.keyClick(self.widget, Qt.Key.Key_Left)
        self.application.processEvents()
        self.assertEqual(self.icons(), ["[+]", "[+]"])
        self.assertEqual(self.panel.selected_signal_names(), [])

    @covers("LLFR-00647", "LLFR-00923", "LLFR-00994", "HLFR-00123",
            "HLFR-00118")
    def test_file_menu_and_history_with_collapsed_rows(self) -> None:
        """A collapsed row still opens the file menu; the icons leave
        the undo history unchanged.

        Inputs: none.
        Outputs: none.
        """
        menu_text_list = []

        def record_menu(menu, global_point):
            """Record the options of a menu and choose none.

            Inputs:
                menu: the QMenu.
                global_point: where it would be shown.
            Outputs: None.
            """
            menu_text_list.append([action.text() for action
                                   in menu.actions()])
            return None

        self.panel.execute_menu = record_menu
        self.panel.request_signal_menu(self.text_point(SECOND_ROW_STR))
        self.application.processEvents()
        self.assertEqual(menu_text_list, [["Close file", "Close all files"]])
        # LLFR-00994: an undoable action, then the icons.
        self.panel.signal_double_clicked.emit("file2_Force")
        self.application.processEvents()
        undo_button = self.main_window.top_panel.undo_button
        history = self.controller.plot_controller.undo_history
        self.assertTrue(undo_button.isEnabled())
        depth_i = history.depth()
        for row_str in (FIRST_ROW_STR, SECOND_ROW_STR, FIRST_ROW_STR):
            self.click_icon(row_str)
        self.assertEqual(history.depth(), depth_i)
        self.assertTrue(undo_button.isEnabled())
        # File 1 was expanded and collapsed again, file 2 expanded.
        self.assertEqual(self.icons(), ["[+]", "[-]"])


if __name__ == "__main__":
    unittest.main()
