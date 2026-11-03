"""Tests for the file name row of the signal list (HLFR-00079).

The shortening itself (view.elided_text) needs no Qt and is tested on
its own; the panel tests need PyQt6 and run in CI.
"""

import os
import tempfile
import unittest

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

    @covers("LLFR-00362")
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

    @covers("LLFR-00362")
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

    @covers("LLFR-00362")
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

    @covers("LLFR-00362")
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


@requires_qt
class FileNameLinePanelTest(unittest.TestCase):
    """The list's first row shows the file name (LLFR-00362/00363)."""

    def setUp(self) -> None:
        """Create and show a signal list panel with signal names.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.signal_list_panel import SignalListPanel
        self.panel = SignalListPanel()
        self.panel.resize(250, 400)
        self.panel.show()
        self.panel.show_signal_names(NAME_LIST)
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close and delete the panel.

        Inputs: none.
        Outputs: none.
        """
        self.panel.close()
        self.panel.deleteLater()
        self.application.processEvents()

    def resize_panel(self, width_i: int) -> None:
        """Give the panel a new width and let Qt lay it out.

        Inputs:
            width_i: the new width of the panel, in pixels.
        Outputs: none.
        """
        self.panel.resize(width_i, 400)
        self.application.processEvents()

    @covers("LLFR-00363", "HLFR-00079")
    def test_hidden_before_any_file(self) -> None:
        """No row is shown while no file is open; the list starts at top.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QLabel
        label = self.panel.file_name_label
        list_widget = self.panel.signal_list_widget
        self.assertIs(self.panel.findChild(QLabel, "file_name_label"),
                      label)
        self.assertFalse(label.isVisible())
        self.assertEqual(label.text(), "")
        self.assertEqual(label.toolTip(), "")
        self.assertEqual(self.panel.file_name(), "")
        # The first signal row is at the top of the list area.
        self.assertEqual(list_widget.viewportMargins().top(), 0)
        self.assertEqual(list_widget.visualItemRect(
            list_widget.item(0)).top(), 0)
        # An empty name hides the row again.
        self.panel.show_file_name("run.csv")
        self.assertTrue(label.isVisible())
        self.panel.show_file_name("")
        self.application.processEvents()
        self.assertFalse(label.isVisible())
        self.assertEqual(list_widget.viewportMargins().top(), 0)

    @covers("LLFR-00362", "HLFR-00079")
    def test_first_row_of_the_list(self) -> None:
        """The row is in the list, above the first signal, in bold.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.panel.show_file_name("bench.csv")
        self.application.processEvents()
        label = self.panel.file_name_label
        list_widget = self.panel.signal_list_widget
        viewport = list_widget.viewport()
        self.assertTrue(label.isVisible())
        self.assertIs(label.parentWidget(), list_widget)
        self.assertTrue(label.font().bold())
        self.assertFalse(list_widget.item(0).font().bold())
        # Inside the list's frame, directly above the signal rows and
        # as wide as them.
        self.assertGreaterEqual(label.geometry().top(), 0)
        self.assertEqual(label.geometry().bottom() + 1,
                         viewport.geometry().top())
        self.assertEqual(label.geometry().left(),
                         viewport.geometry().left())
        self.assertEqual(label.width(), viewport.width())
        self.assertGreaterEqual(label.height(),
                                label.fontMetrics().height())
        first_row_top_i = viewport.mapTo(
            list_widget, QPoint(0, list_widget.visualItemRect(
                list_widget.item(0)).top())).y()
        self.assertGreaterEqual(first_row_top_i, label.geometry().bottom())
        # The list is still placed between the title and the search box
        # (LLFR-00094).
        layout = self.panel.panel_layout
        self.assertEqual(layout.indexOf(self.panel.search_box),
                         layout.indexOf(list_widget) + 1)
        self.assertEqual(layout.indexOf(label), -1)

    @covers("LLFR-00362", "LLFR-00363")
    def test_shows_and_replaces_the_name(self) -> None:
        """A short name is shown whole, without a tip, and replaced.

        Inputs: none.
        Outputs: none.
        """
        self.panel.show_file_name("signals.csv")
        label = self.panel.file_name_label
        self.assertEqual(label.text(), "signals.csv")
        self.assertEqual(label.toolTip(), "")
        self.assertEqual(self.panel.file_name(), "signals.csv")
        self.panel.show_file_name("signals.h5")
        self.assertEqual(label.text(), "signals.h5")
        self.assertEqual(self.panel.file_name(), "signals.h5")

    @covers("LLFR-00362")
    def test_long_name_is_shortened_with_tip(self) -> None:
        """A name wider than the panel is shortened and has a tip.

        Inputs: none.
        Outputs: none.
        """
        label = self.panel.file_name_label
        self.panel.show_file_name(LONG_NAME_STR)
        self.application.processEvents()
        shown_str = label.text()
        self.assertNotEqual(shown_str, LONG_NAME_STR)
        self.assertIn("...", shown_str)
        start_str, end_str = shown_str.split("...")
        self.assertTrue(LONG_NAME_STR.startswith(start_str))
        self.assertTrue(LONG_NAME_STR.endswith(end_str))
        self.assertTrue(end_str.endswith(".xlsx"))
        self.assertLessEqual(
            label.fontMetrics().horizontalAdvance(shown_str),
            label.contentsRect().width())
        self.assertEqual(label.toolTip(), LONG_NAME_STR)
        # The long name does not widen the panel.
        self.assertLessEqual(self.panel.width(), 250)
        self.assertEqual(self.panel.file_name(), LONG_NAME_STR)

    @covers("LLFR-00362")
    def test_shortening_follows_the_width(self) -> None:
        """Widening shows the whole name; narrowing shortens it again.

        Inputs: none.
        Outputs: none.
        """
        label = self.panel.file_name_label
        self.panel.show_file_name(LONG_NAME_STR)
        self.resize_panel(150)
        narrow_str = label.text()
        self.assertIn("...", narrow_str)
        self.resize_panel(2000)
        self.assertEqual(label.text(), LONG_NAME_STR)
        self.assertEqual(label.toolTip(), "")
        self.resize_panel(300)
        wider_str = label.text()
        self.assertIn("...", wider_str)
        self.assertGreater(len(wider_str), len(narrow_str))
        self.assertEqual(label.toolTip(), LONG_NAME_STR)

    @covers("LLFR-00362", "LLFR-00095")
    def test_row_is_not_a_signal(self) -> None:
        """The name is not an item: not listed, selected or dragged.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        self.panel.show_file_name("Engine.csv")
        label = self.panel.file_name_label
        list_widget = self.panel.signal_list_widget
        self.assertEqual(self.panel.signal_name_list(), NAME_LIST)
        self.assertEqual(list_widget.count(), len(NAME_LIST))
        list_widget.selectAll()
        self.assertEqual(self.panel.selected_signal_names(), NAME_LIST)
        self.assertNotIn("Engine.csv", self.panel.selected_signal_names())
        # The row can't be selected, edited, focused or dropped on.
        self.assertEqual(label.textInteractionFlags(),
                         Qt.TextInteractionFlag.NoTextInteraction)
        self.assertEqual(label.focusPolicy(), Qt.FocusPolicy.NoFocus)
        self.assertFalse(label.acceptDrops())
        # A drag from the list never carries the file name.
        mime_data = list_widget.mimeData(list_widget.selectedItems())
        self.assertNotIn("Engine.csv", mime_data.text())
        # The search filters the signals only; the row keeps its name.
        self.panel.show_signal_names(["Engine_Speed"])
        self.assertEqual(label.text(), "Engine.csv")
        self.assertTrue(label.isVisible())

    @covers("LLFR-00362")
    def test_line_has_no_menu(self) -> None:
        """A right-click on the line opens no menu.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtGui import QContextMenuEvent
        label = self.panel.file_name_label
        self.panel.show_file_name("signals.csv")
        self.assertEqual(label.contextMenuPolicy(),
                         Qt.ContextMenuPolicy.PreventContextMenu)
        shown_menu_list = []
        self.panel.execute_menu = (
            lambda menu, point: shown_menu_list.append(menu))
        event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse,
                                  QPoint(5, 5))
        self.application.sendEvent(label, event)
        self.application.processEvents()
        self.assertEqual(shown_menu_list, [])
        self.assertEqual(self.panel.pending_menu_tuple, ())


@requires_qt
class FileNameRowMouseTest(unittest.TestCase):
    """The file name row is not a signal (LLFR-00362, HLFR-00063)."""

    def setUp(self) -> None:
        """Show a panel with a file name and signals; record requests.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.signal_list_panel import SignalListPanel
        self.panel = SignalListPanel()
        self.panel.resize(250, 400)
        self.panel.show()
        self.panel.set_time_signal_name("Time")
        self.panel.show_signal_names(NAME_LIST)
        self.panel.show_file_name("bench.csv")
        self.widget = self.panel.signal_list_widget
        self.label = self.panel.file_name_label
        self.widget.doItemsLayout()
        self.application.processEvents()
        self.plot_request_list = []
        self.panel.selected_signals_plot_requested.connect(
            self.plot_request_list.append)
        self.double_clicked_list = []
        self.panel.signal_double_clicked.connect(
            self.double_clicked_list.append)
        self.menu_list = []
        self.panel.execute_menu = (
            lambda menu, point: self.menu_list.append(menu))

    def tearDown(self) -> None:
        """Close and delete the panel.

        Inputs: none.
        Outputs: none.
        """
        self.panel.close()
        self.panel.deleteLater()
        self.application.processEvents()

    def click_row(self, row_i: int, modifier_name_str: str = "NoModifier"):
        """Left-click a signal row, with an optional modifier.

        Inputs:
            row_i: the row of the signal (0 is the first signal).
            modifier_name_str: name of a Qt.KeyboardModifier.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        point = self.widget.visualItemRect(self.widget.item(row_i)).center()
        QTest.mouseClick(self.widget.viewport(), Qt.MouseButton.LeftButton,
                         getattr(Qt.KeyboardModifier, modifier_name_str),
                         point)
        self.application.processEvents()

    def click_file_name(self, modifier_name_str: str = "NoModifier"):
        """Left-click the file name row, with an optional modifier.

        Inputs:
            modifier_name_str: name of a Qt.KeyboardModifier.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.mouseClick(self.label, Qt.MouseButton.LeftButton,
                         getattr(Qt.KeyboardModifier, modifier_name_str),
                         self.label.rect().center())
        self.application.processEvents()

    @covers("LLFR-00362", "LLFR-00290")
    def test_clicks_never_select_the_row(self) -> None:
        """A click, Cmd/Ctrl + click or Shift + click on it selects none.

        Inputs: none.
        Outputs: none.
        """
        self.click_row(1)
        self.assertEqual(self.panel.selected_signal_names(), ["Engine_Speed"])
        for modifier_name_str in ("NoModifier", "ControlModifier",
                                  "ShiftModifier"):
            with self.subTest(modifier_name_str=modifier_name_str):
                self.click_file_name(modifier_name_str)
                # The selection of the signals is unchanged.
                self.assertEqual(self.panel.selected_signal_names(),
                                 ["Engine_Speed"])
                self.assertIs(self.widget.currentItem(),
                              self.widget.item(1))

    @covers("LLFR-00362", "LLFR-00290", "LLFR-00291")
    def test_shift_range_starts_at_the_first_signal(self) -> None:
        """A Shift + click range from the top holds only signals.

        Inputs: none.
        Outputs: none.
        """
        self.click_row(2)
        self.click_row(0, "ShiftModifier")
        self.assertEqual(self.panel.selected_signal_names(), NAME_LIST)
        self.assertEqual(len(self.widget.selectedItems()), len(NAME_LIST))
        self.click_row(0)
        self.click_row(2, "ShiftModifier")
        self.assertEqual(self.panel.selected_signal_names(), NAME_LIST)
        # Cmd/Ctrl + click still toggles a signal.
        self.click_row(1, "ControlModifier")
        self.assertEqual(self.panel.selected_signal_names(),
                         ["Time", "Pressure"])

    @covers("LLFR-00362", "LLFR-00019", "LLFR-00295", "LLFR-00296")
    def test_double_click_and_enter_ignore_the_row(self) -> None:
        """A double-click on the row plots nothing; Enter plots signals.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.mouseDClick(self.label, Qt.MouseButton.LeftButton,
                          Qt.KeyboardModifier.NoModifier,
                          self.label.rect().center())
        self.application.processEvents()
        self.assertEqual(self.double_clicked_list, [])
        self.assertEqual(self.panel.selected_signal_names(), [])
        # Enter with only the row clicked: nothing is selected.
        self.click_file_name()
        self.widget.setFocus()
        QTest.keyClick(self.widget, Qt.Key.Key_Return)
        self.assertEqual(self.plot_request_list, [])
        # Enter with every signal selected plots the signals only.
        self.widget.selectAll()
        QTest.keyClick(self.widget, Qt.Key.Key_Return)
        self.assertEqual(self.plot_request_list, [NAME_LIST])
        # The row is outside the list's viewport: no item is under it,
        # so no click on it can reach an item.
        from PyQt6.QtCore import QPoint
        viewport = self.widget.viewport()
        for point in (self.label.rect().topLeft(),
                      self.label.rect().center(),
                      self.label.rect().bottomRight()):
            viewport_point = viewport.mapFrom(self.label, QPoint(point))
            self.assertLess(viewport_point.y(), 0)
            self.assertIsNone(self.widget.itemAt(viewport_point))
        # A double-click on a signal still plots it (LLFR-00019).
        self.widget.itemDoubleClicked.emit(self.widget.item(2))
        self.assertEqual(self.double_clicked_list, ["Pressure"])

    @covers("LLFR-00362", "LLFR-00021")
    def test_row_is_not_dragged(self) -> None:
        """A press and move on the row starts no drag.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtTest import QTest
        drag_list = []
        self.widget.startDrag = (
            lambda supported_actions: drag_list.append(supported_actions))
        start_point = self.label.rect().center()
        QTest.mousePress(self.label, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, start_point)
        for step_i in range(1, 6):
            QTest.mouseMove(self.label,
                            start_point + QPoint(0, 10 * step_i))
            self.application.processEvents()
        QTest.mouseRelease(self.label, Qt.MouseButton.LeftButton,
                           Qt.KeyboardModifier.NoModifier,
                           start_point + QPoint(0, 50))
        self.application.processEvents()
        self.assertEqual(drag_list, [])
        self.assertEqual(self.panel.selected_signal_names(), [])

    @covers("LLFR-00362", "LLFR-00239")
    def test_row_has_no_menu(self) -> None:
        """A right-click on the row opens no menu; a signal still has one.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtGui import QContextMenuEvent
        event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse,
                                  self.label.rect().center(),
                                  self.label.mapToGlobal(
                                      self.label.rect().center()))
        self.application.sendEvent(self.label, event)
        self.application.processEvents()
        self.assertEqual(self.menu_list, [])
        self.assertEqual(self.panel.pending_menu_tuple, ())
        self.assertEqual(self.label.contextMenuPolicy(),
                         Qt.ContextMenuPolicy.PreventContextMenu)
        # The menu of a signal is unchanged.
        point = self.widget.visualItemRect(self.widget.item(1)).center()
        self.panel.request_signal_menu(QPoint(point))
        self.application.processEvents()
        self.assertEqual(len(self.menu_list), 1)

    @covers("LLFR-00362", "LLFR-00097", "LLFR-00095", "LLFR-00096")
    def test_row_stays_first_during_any_search(self) -> None:
        """Filtered, empty or no-match lists keep the row on top.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        viewport = self.widget.viewport()
        for shown_name_list in (["Pressure"], ["Pressure", "Time"], [],
                                NAME_LIST):
            with self.subTest(shown_name_list=shown_name_list):
                self.panel.show_signal_names(shown_name_list)
                no_match_b = not shown_name_list
                self.panel.show_no_match_message(no_match_b,
                                                 "No matching signals")
                self.widget.doItemsLayout()
                self.application.processEvents()
                self.assertTrue(self.label.isVisible())
                self.assertEqual(self.label.text(), "bench.csv")
                self.assertEqual(self.panel.signal_name_list(),
                                 shown_name_list)
                self.assertEqual(self.label.geometry().bottom() + 1,
                                 viewport.geometry().top())
                if shown_name_list:
                    first_top_i = viewport.mapTo(self.widget, QPoint(
                        0, self.widget.visualItemRect(
                            self.widget.item(0)).top())).y()
                    self.assertGreater(first_top_i,
                                       self.label.geometry().bottom())
                else:
                    # LLFR-00097: the text is below the row.
                    no_match_label = self.widget.no_match_label
                    self.assertEqual(self.panel.no_match_message(),
                                     "No matching signals")
                    no_match_top_i = no_match_label.mapTo(
                        self.widget, QPoint(0, 0)).y()
                    self.assertGreater(no_match_top_i,
                                       self.label.geometry().bottom())

    @covers("LLFR-00362", "LLFR-00332", "LLFR-00291")
    def test_green_time_signal_and_selection_kept(self) -> None:
        """The time signal stays green and the signals selectable.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        self.assertEqual(self.panel.name_color_str("Time"),
                         theme.TIME_SIGNAL_TEXT_COLOR_STR.lower())
        self.assertNotEqual(self.panel.name_color_str("Pressure"),
                            theme.TIME_SIGNAL_TEXT_COLOR_STR.lower())
        self.click_row(0)
        self.assertEqual(self.panel.selected_signal_names(), ["Time"])
        self.assertTrue(self.widget.item(0).isSelected())
        self.assertEqual(self.panel.name_color_str("Time"),
                         theme.TIME_SIGNAL_TEXT_COLOR_STR.lower())

    @covers("LLFR-00362")
    def test_long_name_in_a_narrow_list(self) -> None:
        """A long name is shortened to the row's width, with a tip.

        Inputs: none.
        Outputs: none.
        """
        self.panel.show_file_name(LONG_NAME_STR)
        self.panel.resize(180, 400)
        self.application.processEvents()
        shown_str = self.label.text()
        self.assertIn("...", shown_str)
        self.assertTrue(shown_str.endswith("xlsx"))
        self.assertLessEqual(
            self.label.fontMetrics().horizontalAdvance(shown_str),
            self.label.contentsRect().width())
        self.assertEqual(self.label.toolTip(), LONG_NAME_STR)
        self.assertEqual(self.label.width(),
                         self.widget.viewport().width())


@requires_qt
class FileNameLineWindowTest(unittest.TestCase):
    """The main window passes the opened file's name to the line."""

    @covers("LLFR-00362", "LLFR-00363", "HLFR-00079", "LLFR-00010",
            "LLFR-00013", "LLFR-00014")
    def test_open_file_shows_its_name(self) -> None:
        """Opening a real CSV file through the app shows its name.

        Inputs: none.
        Outputs: none.
        """
        application = get_qt_application()
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        window = MainWindow()
        controller = MainController(window)
        controller.start()
        application.processEvents()
        with tempfile.TemporaryDirectory() as folder_str:
            path_str = os.path.join(folder_str, "bench run.csv")
            with open(path_str, "w", encoding="utf-8") as csv_file:
                csv_file.write("Time,Speed\n0,1\n1,2\n2,3\n")
            self.assertEqual(window.signal_list_panel.file_name(), "")
            window.ask_open_file_path = lambda start_folder_str: path_str
            controller.file_controller.open_file_requested()
            application.processEvents()
            self.assertEqual(window.signal_list_panel.file_name(),
                             "bench run.csv")
            self.assertTrue(
                window.signal_list_panel.file_name_label.isVisible())
            # A cancelled dialog keeps the name.
            window.ask_open_file_path = lambda start_folder_str: ""
            controller.file_controller.open_file_requested()
            self.assertEqual(window.signal_list_panel.file_name(),
                             "bench run.csv")
            # A file that fails to open keeps the name (LLFR-00010).
            broken_path_str = os.path.join(folder_str, "broken.csv")
            with open(broken_path_str, "w", encoding="utf-8") as csv_file:
                csv_file.write("Time,Speed\n0,1\n1,abc\n")
            error_list = []
            window.show_file_open_error = error_list.append
            # HLFR-00010: the question comes before the read.
            window.ask_replace_file = lambda: True
            window.ask_open_file_path = (
                lambda start_folder_str: broken_path_str)
            controller.file_controller.open_file_requested()
            self.assertEqual(len(error_list), 1)
            self.assertEqual(window.signal_list_panel.file_name(),
                             "bench run.csv")
            # A declined replacement keeps the name (LLFR-00014).
            other_path_str = os.path.join(folder_str, "other.csv")
            with open(other_path_str, "w", encoding="utf-8") as csv_file:
                csv_file.write("Time,Force\n0,1\n1,2\n")
            window.ask_replace_file = lambda: False
            window.ask_open_file_path = (
                lambda start_folder_str: other_path_str)
            controller.file_controller.open_file_requested()
            self.assertEqual(window.signal_list_panel.file_name(),
                             "bench run.csv")
            # An accepted replacement shows the new name (LLFR-00013).
            window.ask_replace_file = lambda: True
            controller.file_controller.open_file_requested()
            application.processEvents()
            self.assertEqual(window.signal_list_panel.file_name(),
                             "other.csv")
            self.assertEqual(window.signal_list_panel.file_name_label.text(),
                             "other.csv")
        window.close()
        window.deleteLater()
        application.processEvents()


if __name__ == "__main__":
    unittest.main()
