"""View tests of the time signal (HLFR-00070, HLFR-00071, HLFR-00072).

- The time signal window (LLFR-00325 to LLFR-00329): its text, its list
  in file order, its search box with the focus, and the check that keeps
  it open for a signal that does not always increase.
- The green time signal name in the signal list (LLFR-00332), also in
  search results and while selected, checked on the drawn pixels.
- End to end: a CSV whose x column is "t_s" is opened, "t_s" is chosen
  and a signal is plotted against it (LLFR-00326, LLFR-00068).

The modal dialogs are never run: MainWindow.run_modal_dialog and
QMessageBox.exec are replaced while a test runs.
"""

import os
import tempfile
import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt

# LLFR-00332: the minimum contrast of the green name.
MINIMUM_CONTRAST_F = 4.5
DATA_TEXT_STR = ("speed,t_s,force\n"
                 "5,0,2\n4,0.5,4\n3,1,1\n2,2,3\n1,4,5\n")


def relative_luminance_f(color_str: str) -> float:
    """Return the WCAG relative luminance of a "#rrggbb" color.

    Inputs:
        color_str: the color.
    Outputs: the luminance, from 0 (black) to 1 (white).
    """
    channel_list = []
    for start_i in (1, 3, 5):
        value_f = int(color_str[start_i:start_i + 2], 16) / 255.0
        if value_f <= 0.03928:
            channel_list.append(value_f / 12.92)
        else:
            channel_list.append(((value_f + 0.055) / 1.055) ** 2.4)
    return (0.2126 * channel_list[0] + 0.7152 * channel_list[1]
            + 0.0722 * channel_list[2])


def contrast_ratio_f(first_color_str: str, second_color_str: str) -> float:
    """Return the WCAG contrast ratio of two colors.

    Inputs:
        first_color_str: a "#rrggbb" color.
        second_color_str: another "#rrggbb" color.
    Outputs: the ratio, from 1 to 21.
    """
    luminance_list = sorted([relative_luminance_f(first_color_str),
                             relative_luminance_f(second_color_str)])
    return (luminance_list[1] + 0.05) / (luminance_list[0] + 0.05)


def is_green_pixel(color) -> bool:
    """Tell whether a drawn pixel belongs to green text.

    Inputs:
        color: a QColor read from a grabbed image.
    Outputs: True when green clearly dominates red and blue, which the
        list's text, background and selection colors never do.
    """
    return (color.green() - color.red() >= 30
            and color.green() - color.blue() >= 15)


class TimeSignalThemeTest(unittest.TestCase):
    """The green color token (no Qt needed for the numbers)."""

    @covers("LLFR-00332", "HLFR-00071")
    def test_green_is_readable_on_every_row_background(self) -> None:
        """The green has a 4.5:1 contrast on plain, hover and selected rows.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        green_str = theme.TIME_SIGNAL_TEXT_COLOR_STR
        self.assertTrue(is_green_hex(green_str))
        for background_str in (theme.SURFACE_COLOR_STR,
                               theme.ROW_HOVER_COLOR_STR,
                               theme.ROW_SELECTED_COLOR_STR):
            with self.subTest(background_str=background_str):
                self.assertGreaterEqual(
                    contrast_ratio_f(green_str, background_str),
                    MINIMUM_CONTRAST_F)
        self.assertNotEqual(green_str.lower(), theme.TEXT_COLOR_STR.lower())
        # A text color on the selected row would hide the green.
        self.assertIn("QListWidget#signal_list_widget::item:selected { "
                      f"background: {theme.ROW_SELECTED_COLOR_STR}; }}",
                      theme.application_style_sheet())


def is_green_hex(color_str: str) -> bool:
    """Tell whether a "#rrggbb" color is a green.

    Inputs:
        color_str: the color.
    Outputs: True when its green channel clearly dominates.
    """
    red_i, green_i, blue_i = (int(color_str[start_i:start_i + 2], 16)
                              for start_i in (1, 3, 5))
    return green_i - red_i >= 30 and green_i - blue_i >= 15


@requires_qt
class TimeSignalWindowTest(unittest.TestCase):
    """The time signal window (LLFR-00325, LLFR-00329)."""

    def setUp(self) -> None:
        """Build the window with the controller's search and check.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        import numpy as np
        from controller.file_controller import TIME_SIGNAL_PROMPT_STR
        from model.signal_file import increasing_check_reason
        from model.signal_search import NO_MATCH_TEXT_STR, search_signals
        from view.synthetic_dialogs import build_time_signal_dialog
        self.name_list = ["speed", "t_s", "force", "Engine_Speed"]
        value_dict = {"speed": np.array([5.0, 4.0, 3.0]),
                      "t_s": np.array([0.0, 0.5, 1.0]),
                      "force": np.array([1.0, 1.0, 2.0]),
                      "Engine_Speed": np.array([1.0, 2.0, 3.0])}
        self.search_function = (
            lambda text_str: search_signals(self.name_list, text_str))
        self.dialog = build_time_signal_dialog(
            None, TIME_SIGNAL_PROMPT_STR, self.name_list,
            self.search_function, NO_MATCH_TEXT_STR,
            lambda name_str: increasing_check_reason(
                name_str, value_dict[name_str]))
        self.addCleanup(self.dialog.deleteLater)

    def tearDown(self) -> None:
        """Close the window.

        Inputs: none.
        Outputs: none.
        """
        self.dialog.reject()
        self.application.processEvents()

    @covers("LLFR-00325", "HLFR-00070", "LLFR-00157")
    def test_text_list_and_search_box_with_focus(self) -> None:
        """The window shows its text, every signal and a focused search.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QLineEdit
        from view.main_window import TEXT_INPUT_WIDGET_TUPLE
        self.assertEqual(self.dialog.prompt_label.text(),
                         "Choose the signal that goes on the x-axis")
        self.assertEqual(self.dialog.name_list(), self.name_list)
        self.assertEqual(self.dialog.chosen_name(), "speed")
        dialog_layout = self.dialog.layout()
        widget_list = [dialog_layout.itemAt(index_i).widget()
                       for index_i in range(dialog_layout.count())]
        self.assertLess(widget_list.index(self.dialog.search_box),
                        widget_list.index(self.dialog.signal_list_widget))
        self.assertIsInstance(self.dialog.search_box, QLineEdit)
        self.assertIsInstance(self.dialog.search_box,
                              TEXT_INPUT_WIDGET_TUPLE)
        self.assertTrue(self.dialog.isModal())
        self.dialog.show()
        self.dialog.activateWindow()
        for _ in range(3):
            self.application.processEvents()
        self.assertIs(self.dialog.focusWidget(), self.dialog.search_box)

    @covers("LLFR-00325", "LLFR-00285", "LLFR-00095", "LLFR-00096",
            "LLFR-00097", "LLFR-00102")
    def test_search_filters_the_list(self) -> None:
        """Typing filters the window's list like the signal list panel.

        Inputs: none.
        Outputs: none.
        """
        for text_str in ("speed", "TS", "forse", "e"):
            with self.subTest(text_str=text_str):
                self.dialog.set_search_text(text_str)
                self.assertEqual(self.dialog.name_list(),
                                 self.search_function(text_str))
        self.dialog.set_search_text("speed")
        self.assertEqual(self.dialog.name_list(),
                         ["speed", "Engine_Speed"])
        self.dialog.set_search_text("zzzz")
        self.assertEqual(self.dialog.name_list(), [])
        self.assertEqual(self.dialog.no_match_text(), "No matching signals")
        self.dialog.set_search_text("  ")
        self.assertEqual(self.dialog.name_list(), self.name_list)
        self.assertEqual(self.dialog.no_match_text(), "")

    @covers("LLFR-00329", "LLFR-00326")
    def test_non_increasing_signal_keeps_the_window_open(self) -> None:
        """OK with a signal that does not increase says why and stays.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        self.dialog.show()
        self.application.processEvents()
        self.assertEqual(self.dialog.error_text(), "")
        for name_str in ("speed", "force"):
            with self.subTest(name_str=name_str):
                self.assertTrue(self.dialog.select_name(name_str))
                self.dialog.button_box.button(
                    QDialogButtonBox.StandardButton.Ok).click()
                self.application.processEvents()
                self.assertTrue(self.dialog.isVisible())
                self.assertIn("must always increase",
                              self.dialog.error_text())
                self.assertIn(f"'{name_str}'", self.dialog.error_text())
        self.dialog.set_search_text("t_s")
        QTest.keyClick(self.dialog.search_box, Qt.Key.Key_Return)
        self.application.processEvents()
        self.assertEqual(self.dialog.result(),
                         QDialog.DialogCode.Accepted.value)
        self.assertEqual(self.dialog.chosen_name(), "t_s")
        self.assertEqual(self.dialog.error_text(), "")

    @covers("LLFR-00327")
    def test_cancel_rejects_the_window(self) -> None:
        """Cancel closes the window without a choice.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        self.dialog.button_box.button(
            QDialogButtonBox.StandardButton.Cancel).click()
        self.assertEqual(self.dialog.result(),
                         QDialog.DialogCode.Rejected.value)


@requires_qt
class TimeSignalEndToEndTest(unittest.TestCase):
    """Open files through the real window and controllers."""

    def setUp(self) -> None:
        """Create the data files, the main window and its controller.

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
        self.no_time_path_str = self.write_file("x_axis.csv",
                                                DATA_TEXT_STR)
        self.time_path_str = self.write_file(
            "with_time.csv", "a,TIME,b\n1,0,2\n2,1,3\n")
        self.main_window = MainWindow()
        self.main_window.resize(1200, 800)
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.main_window.show()
        self.application.processEvents()
        self.panel = self.main_window.signal_list_panel
        self.box_record_list = []
        self.replace_answer_list = []
        # Each entry: the names "confirmed" in one time signal window,
        # in order; an empty list cancels.
        self.window_attempt_list = []
        self.window_record_list = []
        self.main_window.run_modal_dialog = self.fake_run_dialog
        box_patch = mock.patch.object(
            QMessageBox, "exec", new=lambda box: self.fake_exec(box))
        box_patch.start()
        self.addCleanup(box_patch.stop)

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
        with open(path_str, "w", encoding="utf-8") as text_file:
            text_file.write(content_str)
        return path_str

    def fake_exec(self, box) -> int:
        """Stand-in for QMessageBox.exec that records the box.

        Inputs:
            box: the QMessageBox being shown.
        Outputs: the next scripted answer of a question, otherwise OK.
        """
        self.box_record_list.append((box.icon(), box.text()))
        standard_button = self.message_box_class.StandardButton
        if box.icon() == self.message_box_class.Icon.Question:
            if self.replace_answer_list.pop(0):
                return standard_button.Yes.value
            return standard_button.No.value
        return standard_button.Ok.value

    def fake_run_dialog(self, dialog) -> bool:
        """Pick names in the time signal window and press OK each time.

        Inputs:
            dialog: the window the main window would run.
        Outputs: True when the window accepted a name.
        """
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        self.window_record_list.append(
            (dialog.windowTitle(), dialog.prompt_label.text(),
             dialog.name_list(), []))
        for name_str in self.window_attempt_list.pop(0):
            self.assertTrue(dialog.select_name(name_str))
            dialog.button_box.button(
                QDialogButtonBox.StandardButton.Ok).click()
            if dialog.result() == QDialog.DialogCode.Accepted.value:
                return True
            self.window_record_list[-1][3].append(dialog.error_text())
        return False

    def open_file(self, path_str: str) -> None:
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

    def plot_widgets(self) -> list:
        """Return the plot widgets of the current tab.

        Inputs: none.
        Outputs: a list of PlotWidget, top to bottom.
        """
        plot_panel = self.main_window.plot_panel
        return list(plot_panel.page_dict[plot_panel.current_tab_id()]
                    .plot_widget_list)

    def double_click_signal(self, name_str: str) -> None:
        """Double-click a name of the signal list.

        Inputs:
            name_str: the name.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        list_widget = self.panel.signal_list_widget
        item = list_widget.findItems(name_str, Qt.MatchFlag.MatchExactly)[0]
        list_widget.itemDoubleClicked.emit(item)
        self.application.processEvents()

    def row_colors(self, name_str: str) -> str:
        """TEMPORARY diagnostic: the most common colors of a row.

        Inputs:
            name_str: a shown name.
        Outputs: a text with the colors.
        """
        import collections
        from PyQt6.QtCore import Qt
        list_widget = self.panel.signal_list_widget
        item = list_widget.findItems(name_str, Qt.MatchFlag.MatchExactly)[0]
        image = list_widget.viewport().grab().toImage()
        row_rect = list_widget.visualItemRect(item)
        counter = collections.Counter()
        for y_i in range(row_rect.top(), row_rect.bottom() + 1):
            for x_i in range(row_rect.left(), row_rect.right() + 1):
                if 0 <= x_i < image.width() and 0 <= y_i < image.height():
                    counter[image.pixelColor(x_i, y_i).name()] += 1
        return (f"{name_str} rect={row_rect} img={image.width()}x"
                f"{image.height()} dpr={image.devicePixelRatio()} "
                f"{counter.most_common(12)} "
                f"fg={item.foreground().color().name()}")

    def green_pixel_count(self, name_str: str) -> int:
        """Count the green pixels drawn in the row of a name.

        Inputs:
            name_str: a shown name.
        Outputs: the number of green pixels in its row.
        """
        from PyQt6.QtCore import Qt
        list_widget = self.panel.signal_list_widget
        item = list_widget.findItems(name_str, Qt.MatchFlag.MatchExactly)[0]
        list_widget.viewport().update()
        self.application.processEvents()
        image = list_widget.viewport().grab().toImage()
        row_rect = list_widget.visualItemRect(item)
        self.assertGreater(row_rect.height(), 0)
        count_i = 0
        for y_i in range(row_rect.top(), row_rect.bottom() + 1):
            for x_i in range(row_rect.left(), row_rect.right() + 1):
                if (0 <= x_i < image.width() and 0 <= y_i < image.height()
                        and is_green_pixel(image.pixelColor(x_i, y_i))):
                    count_i += 1
        return count_i

    @covers("LLFR-00325", "LLFR-00326", "LLFR-00329", "LLFR-00068",
            "LLFR-00055", "LLFR-00054", "HLFR-00070", "HLFR-00007",
            "HLFR-00006")
    def test_choose_t_s_and_plot_against_it(self) -> None:
        """Choosing "t_s" opens the file and puts it on the x-axis.

        Inputs: none.
        Outputs: none.
        """
        from view.synthetic_dialogs import TIME_SIGNAL_TITLE_STR
        self.window_attempt_list.append(["speed", "t_s"])
        self.open_file(self.no_time_path_str)
        self.assertEqual(len(self.window_record_list), 1)
        title_str, prompt_str, name_list, reason_list = (
            self.window_record_list[0])
        self.assertEqual(title_str, TIME_SIGNAL_TITLE_STR)
        self.assertEqual(prompt_str,
                         "Choose the signal that goes on the x-axis")
        self.assertEqual(name_list, ["speed", "t_s", "force"])
        self.assertEqual(len(reason_list), 1)
        self.assertIn("must always increase", reason_list[0])
        self.assertEqual(self.box_record_list, [])
        self.assertEqual(self.panel.signal_name_list(),
                         ["speed", "t_s", "force"])
        self.double_click_signal("force")
        plot_widget = self.plot_widgets()[0]
        force_line = [line for line in plot_widget.axes.get_lines()
                      if line.get_label() == "force"][0]
        self.assertEqual(list(force_line.get_xdata()),
                         [0.0, 0.5, 1.0, 2.0, 4.0])
        self.assertEqual(list(force_line.get_ydata()),
                         [2.0, 4.0, 1.0, 3.0, 5.0])
        start_s, end_s = plot_widget.axes.get_xlim()
        self.assertAlmostEqual(start_s, 0.0)
        self.assertAlmostEqual(end_s, 4.0)
        # LLFR-00055: the chosen time signal is plotted like any other.
        self.double_click_signal("t_s")
        self.assertEqual(len(self.plot_widgets()), 2)
        self.assertEqual(self.box_record_list, [])

    @covers("LLFR-00327", "HLFR-00070")
    def test_cancel_keeps_the_open_file(self) -> None:
        """Cancelling the window keeps the open file and shows nothing.

        Inputs: none.
        Outputs: none.
        """
        self.open_file(self.time_path_str)
        self.double_click_signal("a")
        self.window_attempt_list.append([])
        self.open_file(self.no_time_path_str)
        self.assertEqual(len(self.window_record_list), 1)
        self.assertEqual(self.box_record_list, [])
        self.assertEqual(self.panel.signal_name_list(), ["a", "TIME", "b"])
        self.assertEqual(len(self.plot_widgets()), 1)

    @covers("LLFR-00328", "HLFR-00010")
    def test_window_comes_before_the_replace_question(self) -> None:
        """The window is shown before the replace confirmation.

        Inputs: none.
        Outputs: none.
        """
        self.open_file(self.time_path_str)
        self.window_attempt_list.append(["t_s"])
        self.replace_answer_list.append(False)
        self.open_file(self.no_time_path_str)
        self.assertEqual(len(self.window_record_list), 1)
        self.assertEqual(len(self.box_record_list), 1)
        self.assertEqual(self.box_record_list[0][0],
                         self.message_box_class.Icon.Question)
        self.assertEqual(self.panel.signal_name_list(), ["a", "TIME", "b"])

    @covers("LLFR-00331", "LLFR-00324", "LLFR-00053", "HLFR-00072")
    def test_file_with_time_shows_no_window_and_no_control(self) -> None:
        """A "TIME" match opens directly; no menu changes the time signal.

        Inputs: none.
        Outputs: none.
        """
        self.open_file(self.time_path_str)
        self.assertEqual(self.window_record_list, [])
        self.assertEqual(self.box_record_list, [])
        menu, _ = self.panel.signal_menu_and_requests("TIME")
        text_list = []
        pending_menu_list = [menu]
        while pending_menu_list:
            current_menu = pending_menu_list.pop()
            for action in current_menu.actions():
                text_list.append(action.text().lower())
                if action.menu() is not None:
                    pending_menu_list.append(action.menu())
        for text_str in text_list:
            self.assertNotIn("time signal", text_str)
            self.assertNotIn("x-axis", text_str)
        menu.deleteLater()

    @covers("LLFR-00332", "HLFR-00071")
    def test_time_signal_name_is_green(self) -> None:
        """The time signal is green; other names are not, in every case.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        green_str = theme.TIME_SIGNAL_TEXT_COLOR_STR.lower()
        self.window_attempt_list.append(["t_s"])
        self.open_file(self.no_time_path_str)
        self.assertEqual(self.panel.name_color_str("t_s"), green_str)
        for name_str in ("speed", "force"):
            self.assertNotEqual(self.panel.name_color_str(name_str),
                                green_str)
            self.assertEqual(self.green_pixel_count(name_str), 0,
                             self.row_colors(name_str))
        self.assertGreater(self.green_pixel_count("t_s"), 0,
                           self.row_colors("t_s"))
        # LLFR-00332: also among the search results.
        self.panel.search_box.setText("t s")
        self.application.processEvents()
        self.assertEqual(self.panel.signal_name_list(), ["t_s"])
        self.assertEqual(self.panel.name_color_str("t_s"), green_str)
        self.assertGreater(self.green_pixel_count("t_s"), 0,
                           self.row_colors("t_s"))
        self.panel.search_box.setText("")
        self.application.processEvents()
        # LLFR-00332: also while selected.
        list_widget = self.panel.signal_list_widget
        from PyQt6.QtCore import Qt
        item = list_widget.findItems("t_s", Qt.MatchFlag.MatchExactly)[0]
        list_widget.setCurrentItem(item)
        list_widget.setFocus()
        self.application.processEvents()
        self.assertTrue(item.isSelected())
        self.assertGreater(self.green_pixel_count("t_s"), 0,
                           self.row_colors("t_s"))
        other_item = list_widget.findItems("speed",
                                           Qt.MatchFlag.MatchExactly)[0]
        list_widget.setCurrentItem(other_item)
        self.application.processEvents()
        self.assertTrue(other_item.isSelected())
        self.assertEqual(self.green_pixel_count("speed"), 0,
                         self.row_colors("speed"))
        # HLFR-00071: a time signal found by its name is green too.
        self.replace_answer_list.append(True)
        self.open_file(self.time_path_str)
        self.assertEqual(self.panel.name_color_str("TIME"), green_str)
        self.assertNotEqual(self.panel.name_color_str("a"), green_str)
        self.assertGreater(self.green_pixel_count("TIME"), 0,
                           self.row_colors("TIME"))


if __name__ == "__main__":
    unittest.main()
