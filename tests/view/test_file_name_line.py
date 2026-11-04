"""Tests for the file name rows of the signal list (HLFR-00079).

The shortening itself (view.elided_text) needs no Qt and is tested on
its own; the panel tests need PyQt6 and run in CI. Each open data file
has its own file name row, followed by its signals (LLFR-00362,
LLFR-00938, LLFR-00939), and a right-click on a row opens the file menu
(LLFR-00647, LLFR-00923).
"""

import os
import tempfile
import unittest

from tests.support import expand_all_files
from tests.support import covers, get_qt_application, requires_qt

from view.elided_text import (
    ELLIPSIS_TEXT_STR, is_elided, middle_elided_text)

NAME_LIST = ["Time", "Engine_Speed", "Pressure"]
LONG_NAME_STR = ("a_very_long_measurement_file_name_recorded_on_the_"
                 "test_bench_number_twelve_2026_11_02.xlsx")


def character_width(text_str: str) -> int:
    """Measure a text as 10 pixels per character.

    Inputs:
        text_str: the text.
    Outputs: its width in pixels.
    """
    return 10 * len(text_str)


class MiddleElidedTextTest(unittest.TestCase):
    """The name is shortened in the middle with "..." (LLFR-00362)."""

    @covers("LLFR-00362", "LLFR-00648")
    def test_name_that_fits_is_whole(self) -> None:
        """A name that fits, exactly or with room, is not changed.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(middle_elided_text("run.csv", 70, character_width),
                         "run.csv")
        self.assertEqual(middle_elided_text("run.csv", 500,
                                            character_width), "run.csv")
        self.assertEqual(middle_elided_text("", 0, character_width), "")
        self.assertFalse(is_elided("run.csv", "run.csv"))

    @covers("LLFR-00362", "LLFR-00648")
    def test_long_name_keeps_start_and_extension(self) -> None:
        """A long name keeps its start and end around "...".

        Inputs: none.
        Outputs: none.
        """
        shown_str = middle_elided_text("measurement_2026.csv", 100,
                                       character_width)
        self.assertEqual(shown_str, "meas...csv")
        self.assertTrue(is_elided(shown_str, "measurement_2026.csv"))
        self.assertEqual(ELLIPSIS_TEXT_STR, "...")

    @covers("LLFR-00362", "LLFR-00648")
    def test_longest_text_that_fits(self) -> None:
        """The shortened text is the longest that fits, for every width.

        Inputs: none.
        Outputs: none.
        """
        name_str = LONG_NAME_STR
        for width_i in range(30, character_width(name_str)):
            with self.subTest(width_i=width_i):
                shown_str = middle_elided_text(name_str, width_i,
                                               character_width)
                self.assertLessEqual(character_width(shown_str), width_i)
                self.assertIn(ELLIPSIS_TEXT_STR, shown_str)
                start_str, end_str = shown_str.split(ELLIPSIS_TEXT_STR)
                self.assertTrue(name_str.startswith(start_str))
                self.assertTrue(name_str.endswith(end_str))
                # Half of the kept characters at each side.
                self.assertIn(len(start_str) - len(end_str), (0, 1))
                # One more character would not fit.
                self.assertGreater(character_width(shown_str) + 10,
                                   width_i)

    @covers("LLFR-00362", "LLFR-00648")
    def test_too_narrow_for_any_character(self) -> None:
        """Only "..." is left when no character fits next to it.

        Inputs: none.
        Outputs: none.
        """
        for width_i in (0, 10, 35):
            with self.subTest(width_i=width_i):
                self.assertEqual(middle_elided_text("signals.csv", width_i,
                                                    character_width),
                                 ELLIPSIS_TEXT_STR)


FIRST_ROW_STR = "file1_bench.csv"
SECOND_ROW_STR = "file2_other.mat"
FIRST_SIGNAL_LIST = ["file1_Time", "file1_Engine_Speed", "file1_Pressure"]
SECOND_SIGNAL_LIST = ["file2_Time", "file2_Force"]
GROUP_LIST = [(1, FIRST_ROW_STR, FIRST_SIGNAL_LIST, ""),
              (2, SECOND_ROW_STR, SECOND_SIGNAL_LIST, "")]


class FileRowPanelTestCase(unittest.TestCase):
    """A shown signal list panel with the rows of two data files."""

    def setUp(self) -> None:
        """Create and show a panel with two file groups.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.signal_list_panel import SignalListPanel
        self.panel = SignalListPanel()
        self.panel.resize(250, 400)
        self.panel.show()
        self.panel.set_time_signal_names(["file1_Time", "file2_Time"])
        self.panel.show_signal_groups(GROUP_LIST)
        self.widget = self.panel.signal_list_widget
        self.widget.doItemsLayout()
        self.application.processEvents()
        self.plot_request_list = []
        self.panel.selected_signals_plot_requested.connect(
            self.plot_request_list.append)
        self.double_clicked_list = []
        self.panel.signal_double_clicked.connect(
            self.double_clicked_list.append)
        self.menu_list = []
        self.chosen_text_str = ""
        self.panel.execute_menu = self.record_menu
        self.close_file_list = []
        self.close_all_count_list = []
        self.panel.close_file_requested.connect(self.close_file_list.append)
        self.panel.close_all_files_requested.connect(
            lambda: self.close_all_count_list.append(1))

    def tearDown(self) -> None:
        """Close and delete the panel.

        Inputs: none.
        Outputs: none.
        """
        self.panel.close()
        self.panel.deleteLater()
        self.application.processEvents()

    def record_menu(self, menu, global_point):
        """Record a menu and choose the option of chosen_text_str.

        Inputs:
            menu: the QMenu that would be shown.
            global_point: where it would be shown.
        Outputs: the action whose text is chosen_text_str, or None.
        """
        self.menu_list.append([action.text() for action in menu.actions()
                               if not action.isSeparator()])
        for action in menu.actions():
            if action.text() == self.chosen_text_str:
                return action
        return None

    def item_of(self, text_str: str):
        """Return the row of the list with a text.

        Inputs:
            text_str: the text of the row.
        Outputs: the QListWidgetItem.
        """
        for item in self.widget.row_items():
            if item.text() == text_str:
                return item
        raise AssertionError(text_str)

    def click(self, text_str: str, modifier_name_str: str = "NoModifier",
              double_b: bool = False) -> None:
        """Left-click (or double-click) a row, with an optional modifier.

        Inputs:
            text_str: the text of the row.
            modifier_name_str: name of a Qt.KeyboardModifier.
            double_b: True for a double-click.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        point = self.widget.visualItemRect(self.item_of(text_str)).center()
        modifier = getattr(Qt.KeyboardModifier, modifier_name_str)
        if double_b:
            # As a user does: a click, then the double-click.
            QTest.mouseClick(self.widget.viewport(),
                             Qt.MouseButton.LeftButton, modifier, point)
            QTest.mouseDClick(self.widget.viewport(),
                              Qt.MouseButton.LeftButton, modifier, point)
        else:
            QTest.mouseClick(self.widget.viewport(),
                             Qt.MouseButton.LeftButton, modifier, point)
        self.application.processEvents()

    def right_click(self, text_str: str) -> None:
        """Right-click a row and let the pending menu be shown.

        Inputs:
            text_str: the text of the row.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        point = self.widget.visualItemRect(self.item_of(text_str)).center()
        self.panel.request_signal_menu(QPoint(point))
        self.application.processEvents()


@requires_qt
class FileRowsTest(FileRowPanelTestCase):
    """One bold file name row per file, above its signals."""

    @covers("LLFR-00363", "LLFR-00937", "HLFR-00079")
    def test_no_row_without_a_file(self) -> None:
        """With no group, the list has no row at all.

        Inputs: none.
        Outputs: none.
        """
        self.panel.show_signal_groups([])
        self.assertEqual(self.panel.row_list(), [])
        self.assertEqual(self.panel.file_row_texts(), [])
        self.assertEqual(self.panel.signal_name_list(), [])

    @covers("LLFR-00362", "LLFR-00938", "LLFR-00939", "LLFR-00639",
            "LLFR-00242", "HLFR-00079", "HLFR-00114", "HLFR-00113",
            "HLFR-00011")
    def test_rows_in_number_order_with_their_signals(self) -> None:
        """Each file's bold row comes first, then its signals.

        Inputs: none.
        Outputs: none.
        """
        from view.signal_list_panel import FILE_ROW_STR, SIGNAL_ROW_STR
        self.panel.set_signal_kinds({"file1_int_Pressure"}, set())
        self.panel.show_signal_groups(
            [(1, FIRST_ROW_STR, FIRST_SIGNAL_LIST + ["file1_int_Pressure"],
              ""), (2, SECOND_ROW_STR, SECOND_SIGNAL_LIST, "")])
        expected_list = ([(FILE_ROW_STR, FIRST_ROW_STR)]
                         + [(SIGNAL_ROW_STR, name_str) for name_str
                            in FIRST_SIGNAL_LIST + ["file1_int_Pressure"]]
                         + [(FILE_ROW_STR, SECOND_ROW_STR)]
                         + [(SIGNAL_ROW_STR, name_str)
                            for name_str in SECOND_SIGNAL_LIST])
        self.assertEqual(self.panel.row_list(), expected_list)
        self.assertEqual(self.panel.file_row_texts(),
                         [FIRST_ROW_STR, SECOND_ROW_STR])
        self.assertTrue(self.item_of(FIRST_ROW_STR).font().bold())
        self.assertTrue(self.item_of(SECOND_ROW_STR).font().bold())
        self.assertFalse(self.item_of("file1_Time").font().bold())
        # LLFR-00242: the synthetic signal of file 1 is in italics, in
        # the group of its file.
        self.assertTrue(self.panel.is_name_italic("file1_int_Pressure"))
        # Rows are laid out from top to bottom in this order.
        top_list = [self.widget.visualItemRect(item).top()
                    for item in self.widget.row_items()]
        self.assertEqual(top_list, sorted(top_list))

    @covers("LLFR-00642", "LLFR-00643", "LLFR-00645", "LLFR-00095",
            "LLFR-00362")
    def test_row_is_not_a_signal(self) -> None:
        """A row is neither selectable, nor dragged, nor listed.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        row_item = self.item_of(FIRST_ROW_STR)
        self.assertFalse(row_item.flags() & Qt.ItemFlag.ItemIsSelectable)
        self.assertFalse(row_item.flags() & Qt.ItemFlag.ItemIsDragEnabled)
        self.assertTrue(row_item.flags() & Qt.ItemFlag.ItemIsEnabled)
        self.assertEqual(self.panel.signal_name_list(),
                         FIRST_SIGNAL_LIST + SECOND_SIGNAL_LIST)
        self.widget.selectAll()
        self.assertEqual(self.panel.selected_signal_names(),
                         FIRST_SIGNAL_LIST + SECOND_SIGNAL_LIST)
        self.assertFalse(row_item.isSelected())
        mime_data = self.widget.mimeData(self.widget.row_items())
        self.assertNotIn(FIRST_ROW_STR, mime_data.text())
        self.assertEqual(mime_data.text().split("\n"),
                         FIRST_SIGNAL_LIST + SECOND_SIGNAL_LIST)
        self.assertEqual(self.widget.mimeData([row_item]).text(), "")

    @covers("LLFR-00648", "LLFR-00649", "LLFR-00362")
    def test_long_row_is_shortened_with_tip(self) -> None:
        """A row wider than the list is shortened and has a tip.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QRect
        from PyQt6.QtWidgets import QStyleOptionViewItem
        long_row_str = "file1_" + LONG_NAME_STR
        self.panel.show_signal_groups([(1, long_row_str, ["file1_Time"],
                                        "")])
        self.panel.resize(180, 400)
        self.application.processEvents()
        row_item = self.item_of(long_row_str)
        shown_str = self.widget.file_row_text(row_item)
        self.assertIn("...", shown_str)
        start_str, end_str = shown_str.split("...")
        self.assertTrue(start_str.startswith("file1_"))
        self.assertTrue(long_row_str.startswith(start_str))
        self.assertTrue(end_str.endswith(".xlsx"))
        self.assertEqual(row_item.toolTip(), long_row_str)
        # The delegate draws the same shortened text.
        option = QStyleOptionViewItem()
        option.rect = QRect(0, 0, self.widget.viewport().width(), 20)
        self.widget.itemDelegate().initStyleOption(
            option, self.widget.indexFromItem(row_item))
        self.assertEqual(option.text, shown_str)
        # A wide list shows the whole text, without a tip.
        self.panel.resize(2000, 400)
        self.application.processEvents()
        self.assertEqual(self.widget.file_row_text(row_item), long_row_str)
        self.assertEqual(row_item.toolTip(), "")
        # A short row has no tip.
        self.panel.resize(250, 400)
        self.panel.show_signal_groups(GROUP_LIST)
        self.assertEqual(self.item_of(FIRST_ROW_STR).toolTip(), "")
        self.assertEqual(
            self.widget.file_row_text(self.item_of(FIRST_ROW_STR)),
            FIRST_ROW_STR)

    @covers("LLFR-00097", "LLFR-00639", "LLFR-00640", "LLFR-00641",
            "LLFR-00565", "LLFR-00102", "HLFR-00033")
    def test_rows_stay_during_any_search(self) -> None:
        """Filtered or no-match groups keep each row in its place.

        Inputs: none.
        Outputs: none.
        """
        from view.signal_list_panel import (
            FILE_ROW_STR, NO_MATCH_ROW_STR, SIGNAL_ROW_STR)
        self.panel.show_signal_groups(
            [(1, FIRST_ROW_STR, [], "No matching signals"),
             (2, SECOND_ROW_STR, ["file2_Force"], "")])
        self.assertEqual(self.panel.row_list(), [
            (FILE_ROW_STR, FIRST_ROW_STR),
            (NO_MATCH_ROW_STR, "No matching signals"),
            (FILE_ROW_STR, SECOND_ROW_STR),
            (SIGNAL_ROW_STR, "file2_Force")])
        self.panel.show_signal_groups(
            [(1, FIRST_ROW_STR, [], "No matching signals"),
             (2, SECOND_ROW_STR, [], "No matching signals")])
        self.assertEqual(self.panel.file_row_texts(),
                         [FIRST_ROW_STR, SECOND_ROW_STR])
        self.assertEqual(self.panel.signal_name_list(), [])
        self.assertEqual(
            [kind_str for kind_str, _ in self.panel.row_list()],
            [FILE_ROW_STR, NO_MATCH_ROW_STR, FILE_ROW_STR,
             NO_MATCH_ROW_STR])

    @covers("LLFR-00332", "LLFR-00638", "LLFR-00291")
    def test_green_time_signals_of_each_file(self) -> None:
        """The time signal of each file is green; a row is not.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        green_str = theme.TIME_SIGNAL_TEXT_COLOR_STR.lower()
        self.assertEqual(self.panel.name_color_str("file1_Time"), green_str)
        self.assertEqual(self.panel.name_color_str("file2_Time"), green_str)
        self.assertNotEqual(self.panel.name_color_str("file2_Force"),
                            green_str)
        # A file name row is not a signal, so it has no signal color.
        self.assertEqual(self.panel.name_color_str(FIRST_ROW_STR), "")
        self.click("file2_Time")
        self.assertEqual(self.panel.name_color_str("file2_Time"), green_str)


@requires_qt
class FileRowMouseTest(FileRowPanelTestCase):
    """The mouse never selects, drags or plots a file name row."""

    @covers("LLFR-00643", "LLFR-00644", "LLFR-00290", "LLFR-00362")
    def test_clicks_never_select_the_row(self) -> None:
        """A click, Cmd/Ctrl + click or Shift + click on it selects none.

        Inputs: none.
        Outputs: none.
        """
        self.click("file1_Engine_Speed")
        current_item = self.widget.currentItem()
        for modifier_name_str in ("NoModifier", "ControlModifier",
                                  "ShiftModifier"):
            with self.subTest(modifier_name_str=modifier_name_str):
                self.click(SECOND_ROW_STR, modifier_name_str)
                self.assertEqual(self.panel.selected_signal_names(),
                                 ["file1_Engine_Speed"])
                self.assertIs(self.widget.currentItem(), current_item)
                self.assertFalse(self.item_of(SECOND_ROW_STR).isSelected())

    @covers("LLFR-00644", "LLFR-00626", "LLFR-00625", "LLFR-00290")
    def test_shift_range_over_two_files_skips_the_row(self) -> None:
        """A Shift range across files holds only signals.

        Inputs: none.
        Outputs: none.
        """
        self.click("file1_Pressure")
        self.click("file2_Force", "ShiftModifier")
        self.assertEqual(self.panel.selected_signal_names(),
                         ["file1_Pressure", "file2_Time", "file2_Force"])
        self.assertEqual(len(self.widget.selectedItems()), 3)
        # A range from the last plain click, upwards across the row.
        self.click("file2_Force")
        self.click("file1_Time", "ShiftModifier")
        self.assertEqual(self.panel.selected_signal_names(),
                         FIRST_SIGNAL_LIST + SECOND_SIGNAL_LIST)
        self.assertFalse(self.item_of(SECOND_ROW_STR).isSelected())
        # Cmd/Ctrl + click still toggles a signal.
        self.click("file2_Time", "ControlModifier")
        self.assertNotIn("file2_Time", self.panel.selected_signal_names())

    @covers("LLFR-00646", "LLFR-00019", "LLFR-00295", "LLFR-00296")
    def test_double_click_and_enter_ignore_the_row(self) -> None:
        """A double-click on a row plots nothing; Enter plots signals.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.click(FIRST_ROW_STR, double_b=True)
        self.assertEqual(self.double_clicked_list, [])
        self.assertEqual(self.panel.selected_signal_names(), [])
        self.panel._emit_signal_double_clicked(self.item_of(FIRST_ROW_STR))
        self.assertEqual(self.double_clicked_list, [])
        self.widget.setFocus()
        QTest.keyClick(self.widget, Qt.Key.Key_Return)
        self.assertEqual(self.plot_request_list, [])
        self.widget.selectAll()
        QTest.keyClick(self.widget, Qt.Key.Key_Return)
        self.assertEqual(self.plot_request_list,
                         [FIRST_SIGNAL_LIST + SECOND_SIGNAL_LIST])
        # A double-click on a signal still plots it.
        self.click("file2_Force", double_b=True)
        self.assertEqual(self.double_clicked_list, ["file2_Force"])

    @covers("LLFR-00645", "LLFR-00021")
    def test_row_is_not_dragged(self) -> None:
        """A press and move on a row starts no drag.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtTest import QTest
        drag_list = []
        original_start_drag = self.widget.startDrag
        self.widget.startDrag = (
            lambda supported_actions: drag_list.append(
                self.widget.pressed_item) or original_start_drag(
                    supported_actions))
        viewport = self.widget.viewport()
        start_point = self.widget.visualItemRect(
            self.item_of(FIRST_ROW_STR)).center()
        QTest.mousePress(viewport, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, start_point)
        for step_i in range(1, 6):
            QTest.mouseMove(viewport, start_point + QPoint(0, 10 * step_i))
            self.application.processEvents()
        QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton,
                           Qt.KeyboardModifier.NoModifier,
                           start_point + QPoint(0, 50))
        self.application.processEvents()
        self.assertIsNone(self.widget.pressed_item)
        self.assertEqual(self.panel.selected_signal_names(), [])
        self.assertTrue(all(item is None for item in drag_list))
        self.assertFalse(self.widget.press_on_other_row_b)


@requires_qt
class FileMenuTest(FileRowPanelTestCase):
    """A right-click on a row opens the file menu (LLFR-00923)."""

    @covers("LLFR-00647", "LLFR-00923", "LLFR-00239", "HLFR-00118",
            "HLFR-00119")
    def test_row_opens_the_file_menu(self) -> None:
        """The file menu, not the signal menu, with its two options.

        Inputs: none.
        Outputs: none.
        """
        self.click("file1_Pressure")
        self.right_click(SECOND_ROW_STR)
        self.assertEqual(self.menu_list, [["Close file", "Close all files"]])
        self.assertEqual(self.panel.pending_menu_tuple, ())
        self.assertEqual(self.panel.pending_file_menu_tuple, ())
        # The selection is kept and nothing is requested.
        self.assertEqual(self.panel.selected_signal_names(),
                         ["file1_Pressure"])
        self.assertEqual(self.close_file_list, [])
        self.assertEqual(self.close_all_count_list, [])
        # A signal still opens the signal menu.
        self.right_click("file2_Force")
        self.assertEqual(len(self.menu_list), 2)
        self.assertIn("Copy name", self.menu_list[1])
        self.assertNotIn("Close file", self.menu_list[1])
        # The no-match row has no menu.
        self.panel.show_signal_groups(
            [(1, FIRST_ROW_STR, [], "No matching signals")])
        self.right_click("No matching signals")
        self.assertEqual(len(self.menu_list), 2)

    @covers("LLFR-00923", "LLFR-00924", "HLFR-00118")
    def test_close_file_asks_for_that_file(self) -> None:
        """"Close file" on the row of file 2 requests file 2.

        Inputs: none.
        Outputs: none.
        """
        self.chosen_text_str = "Close file"
        self.right_click(SECOND_ROW_STR)
        self.assertEqual(self.close_file_list, [2])
        self.right_click(FIRST_ROW_STR)
        self.assertEqual(self.close_file_list, [2, 1])
        self.assertEqual(self.close_all_count_list, [])

    @covers("LLFR-00923", "LLFR-00934", "HLFR-00119")
    def test_close_all_files_from_any_row(self) -> None:
        """"Close all files" is requested once.

        Inputs: none.
        Outputs: none.
        """
        self.chosen_text_str = "Close all files"
        self.right_click(FIRST_ROW_STR)
        self.assertEqual(self.close_all_count_list, [1])
        self.assertEqual(self.close_file_list, [])

    @covers("LLFR-00923")
    def test_built_menu_emits_its_requests(self) -> None:
        """The menu built for tests triggers the same requests.

        Inputs: none.
        Outputs: none.
        """
        menu = self.panel.build_file_menu(3)
        self.assertEqual([action.text() for action in menu.actions()],
                         ["Close file", "Close all files"])
        menu.actions()[0].trigger()
        menu.actions()[1].trigger()
        self.assertEqual(self.close_file_list, [3])
        self.assertEqual(self.close_all_count_list, [1])
        menu.deleteLater()


def write_csv(path_str: str, text_str: str) -> None:
    """Write a CSV data file.

    Inputs:
        path_str: the path.
        text_str: the content.
    Outputs: none.
    """
    with open(path_str, "w", encoding="utf-8") as csv_file:
        csv_file.write(text_str)


@requires_qt
class FileRowsWindowTest(unittest.TestCase):
    """The app shows one row per open file and closes them by menu."""

    def setUp(self) -> None:
        """Start the app and write three data files.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.window = MainWindow()
        self.controller = MainController(self.window)
        self.controller.start()
        self.application.processEvents()
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path_dict = {}
        for name_str, text_str in (
                ("bench run.csv", "Time,Speed\n0,1\n1,2\n2,3\n"),
                ("other.csv", "Time,Force\n0,1\n1,2\n"),
                ("third.csv", "Time,Torque\n0,5\n1,6\n")):
            path_str = os.path.join(self.folder.name, name_str)
            write_csv(path_str, text_str)
            self.path_dict[name_str] = path_str
        self.panel = self.window.signal_list_panel
        self.question_list = []

    def tearDown(self) -> None:
        """Close the window.

        Inputs: none.
        Outputs: none.
        """
        self.window.close()
        self.window.deleteLater()
        self.application.processEvents()

    def open_paths(self, path_value) -> None:
        """Answer the Open file dialog with paths.

        Inputs:
            path_value: a path, a list of paths, or "" to cancel.
        Outputs: none.
        """
        self.window.ask_open_file_path = lambda start_folder_str: path_value
        self.controller.file_controller.open_file_requested()
        self.application.processEvents()
        # LLFR-00984: the files are collapsed after an open; these
        # tests read the shown signals.
        expand_all_files(self.controller)

    def answer_questions(self, answer_b: bool) -> None:
        """Answer the close questions with answer_b and record them.

        Inputs:
            answer_b: True to proceed.
        Outputs: none.
        """
        def answer(question_str: str) -> bool:
            """Record the question and answer it.

            Inputs:
                question_str: the question.
            Outputs: answer_b.
            """
            self.question_list.append(question_str)
            return answer_b
        self.window.ask_close_file = answer
        self.window.ask_close_all_files = answer

    def choose_file_menu(self, row_str: str, option_str: str) -> None:
        """Right-click a file name row and choose an option.

        Inputs:
            row_str: the text of the row.
            option_str: "Close file" or "Close all files".
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint

        def choose(menu, global_point):
            """Return the option of option_str.

            Inputs:
                menu: the file menu.
                global_point: ignored.
            Outputs: the chosen QAction.
            """
            for action in menu.actions():
                if action.text() == option_str:
                    return action
            return None
        self.panel.execute_menu = choose
        widget = self.panel.signal_list_widget
        widget.doItemsLayout()
        item = [item for item in widget.row_items()
                if item.text() == row_str][0]
        self.panel.request_signal_menu(
            QPoint(widget.visualItemRect(item).center()))
        self.application.processEvents()

    @covers("LLFR-00362", "LLFR-00363", "HLFR-00079", "LLFR-00010",
            "LLFR-00650", "LLFR-00651", "LLFR-00898", "LLFR-00937",
            "HLFR-00114", "HLFR-00117", "LLFR-00938")
    def test_open_files_show_their_rows(self) -> None:
        """Opening real CSV files through the app shows their rows.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.panel.file_row_texts(), [])
        self.open_paths(self.path_dict["bench run.csv"])
        self.assertEqual(self.panel.file_row_texts(),
                         ["file1_bench run.csv"])
        # A cancelled dialog keeps the row.
        self.open_paths("")
        self.assertEqual(self.panel.file_row_texts(),
                         ["file1_bench run.csv"])
        # A file that fails to open adds no row (LLFR-00010).
        broken_path_str = os.path.join(self.folder.name, "broken.csv")
        write_csv(broken_path_str, "Time,Speed\n0,1\n1,abc\n")
        error_list = []
        self.window.show_file_open_error = error_list.append
        self.open_paths(broken_path_str)
        self.assertEqual(len(error_list), 1)
        self.assertEqual(self.panel.file_row_texts(),
                         ["file1_bench run.csv"])
        # A file already open adds no row (LLFR-00898).
        refused_list = []
        self.window.show_refused_files_notification = refused_list.append
        self.open_paths(self.path_dict["bench run.csv"])
        self.assertEqual(len(refused_list), 1)
        self.assertEqual(self.panel.file_row_texts(),
                         ["file1_bench run.csv"])
        # Another file adds its row, in its place, with its signals.
        self.open_paths(self.path_dict["other.csv"])
        self.assertEqual(self.panel.file_row_texts(),
                         ["file1_bench run.csv", "file2_other.csv"])
        self.assertEqual(self.panel.signal_name_list(), [
            "file1_Time", "file1_Speed", "file2_Time", "file2_Force"])
        # LLFR-00937: with no file left, no row is shown.
        self.controller.file_controller.close_all_files()
        self.application.processEvents()
        self.assertEqual(self.panel.file_row_texts(), [])
        self.assertEqual(self.panel.row_list(), [])

    @covers("LLFR-00951", "LLFR-00952", "LLFR-00974", "LLFR-00006",
            "HLFR-00122", "LLFR-00938")
    def test_several_selected_files_in_name_order(self) -> None:
        """Files selected together open in the order of their names.

        Inputs: none.
        Outputs: none.
        """
        self.open_paths([self.path_dict["third.csv"],
                         self.path_dict["bench run.csv"],
                         self.path_dict["other.csv"]])
        self.assertEqual(self.panel.file_row_texts(), [
            "file1_bench run.csv", "file2_other.csv", "file3_third.csv"])

    @covers("LLFR-00923", "LLFR-00924", "LLFR-00925", "LLFR-00926",
            "LLFR-00931", "HLFR-00118", "LLFR-00902")
    def test_close_file_from_its_row(self) -> None:
        """The question names the file; No keeps it, Yes closes it.

        Inputs: none.
        Outputs: none.
        """
        self.open_paths([self.path_dict["bench run.csv"],
                         self.path_dict["other.csv"]])
        self.answer_questions(False)
        self.choose_file_menu("file2_other.csv", "Close file")
        self.assertEqual(len(self.question_list), 1)
        self.assertIn("file2_other.csv", self.question_list[0])
        self.assertEqual(self.panel.file_row_texts(),
                         ["file1_bench run.csv", "file2_other.csv"])
        self.answer_questions(True)
        self.choose_file_menu("file2_other.csv", "Close file")
        self.assertEqual(self.panel.file_row_texts(),
                         ["file1_bench run.csv"])
        self.assertEqual(self.panel.signal_name_list(),
                         ["file1_Time", "file1_Speed"])
        # The next file gets the next number (LLFR-00902).
        self.open_paths(self.path_dict["third.csv"])
        self.assertEqual(self.panel.file_row_texts(),
                         ["file1_bench run.csv", "file3_third.csv"])

    @covers("LLFR-00923", "LLFR-00934", "LLFR-00935", "LLFR-00936",
            "LLFR-00937", "HLFR-00119")
    def test_close_all_files_from_a_row(self) -> None:
        """One question; No keeps every file, Yes closes them all.

        Inputs: none.
        Outputs: none.
        """
        self.open_paths([self.path_dict["bench run.csv"],
                         self.path_dict["other.csv"]])
        self.answer_questions(False)
        self.choose_file_menu("file1_bench run.csv", "Close all files")
        self.assertEqual(len(self.question_list), 1)
        self.assertEqual(len(self.panel.file_row_texts()), 2)
        self.answer_questions(True)
        self.choose_file_menu("file1_bench run.csv", "Close all files")
        self.assertEqual(len(self.question_list), 2)
        self.assertEqual(self.panel.row_list(), [])


if __name__ == "__main__":
    unittest.main()
