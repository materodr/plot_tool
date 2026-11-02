"""Tests for the file name line of the signal list panel (HLFR-00079).

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
    """The panel's first line shows the file name (LLFR-00362/00363)."""

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
    def test_empty_before_any_file(self) -> None:
        """The line exists, is visible and empty, with no tip.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QLabel
        label = self.panel.file_name_label
        self.assertIs(self.panel.findChild(QLabel, "file_name_label"),
                      label)
        self.assertTrue(label.isVisible())
        self.assertEqual(label.text(), "")
        self.assertEqual(label.toolTip(), "")
        self.assertEqual(self.panel.file_name(), "")
        # The empty line keeps the height of one line of text.
        self.assertGreaterEqual(label.height(),
                                label.fontMetrics().height())

    @covers("LLFR-00362", "HLFR-00079")
    def test_first_line_above_the_list(self) -> None:
        """The line is the first item of the panel, above the list.

        Inputs: none.
        Outputs: none.
        """
        layout = self.panel.panel_layout
        label = self.panel.file_name_label
        list_widget = self.panel.signal_list_widget
        self.assertEqual(layout.indexOf(label), 0)
        self.assertLess(layout.indexOf(label),
                        layout.indexOf(list_widget))
        self.assertLessEqual(label.geometry().bottom(),
                             list_widget.geometry().top())
        # LLFR-00094: the search box stays directly below the list.
        self.assertEqual(layout.indexOf(self.panel.search_box),
                         layout.indexOf(list_widget) + 1)

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
    def test_line_is_not_a_signal(self) -> None:
        """The name is not an item: not listed, selected or searched.

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
        # The line can't be selected, edited, focused or dropped on.
        self.assertEqual(label.textInteractionFlags(),
                         Qt.TextInteractionFlag.NoTextInteraction)
        self.assertEqual(label.focusPolicy(), Qt.FocusPolicy.NoFocus)
        self.assertFalse(label.acceptDrops())
        # A drag from the list never carries the file name.
        mime_data = list_widget.mimeData(list_widget.selectedItems())
        self.assertNotIn("Engine.csv", mime_data.text())
        # The search filters the list only; the line keeps its name.
        self.panel.show_signal_names(["Engine_Speed"])
        self.assertEqual(label.text(), "Engine.csv")

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
class FileNameLineWindowTest(unittest.TestCase):
    """The main window passes the opened file's name to the line."""

    @covers("LLFR-00362", "LLFR-00363", "HLFR-00079")
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
            # A cancelled dialog keeps the name.
            window.ask_open_file_path = lambda start_folder_str: ""
            controller.file_controller.open_file_requested()
            self.assertEqual(window.signal_list_panel.file_name(),
                             "bench run.csv")
        window.close()
        window.deleteLater()
        application.processEvents()


if __name__ == "__main__":
    unittest.main()
