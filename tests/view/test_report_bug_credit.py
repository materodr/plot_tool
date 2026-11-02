"""Tests for the Report a bug button and the credit text (issue #141).

Covers LLFR-00358 (the Report a bug button), LLFR-00359 (it opens the
"New issue" page), LLFR-00360 (its active color for at least 0.3 s),
LLFR-00361 (the error box when the browser cannot be opened), its icon
and button tip (LLFR-00159, LLFR-00215) and group (LLFR-00347), and
LLFR-00364 (the credit text "designed by materodr"). The browser is
never really opened: QDesktopServices.openUrl is patched.
"""

import os
import tempfile
import time
import unittest
from unittest import mock

from tests.support import (
    button_name, button_tip_line_list, covers, get_qt_application,
    requires_qt)
from tests.support import OPEN_FILE_DIALOG_TARGET_STR

from view import icon_shapes, theme

# LLFR-00359: the page of the repository's "New issue" button.
EXPECTED_URL_STR = "https://github.com/materodr/plot_tool/issues/new/choose"
# LLFR-00364: the credit text.
EXPECTED_CREDIT_STR = "designed by materodr"
# LLFR-00360: the shortest active time of the button.
MINIMUM_ACTIVE_TIME_S = 0.3
MAXIMUM_WAIT_TIME_S = 3.0


class ReportBugDataTest(unittest.TestCase):
    """Checks that need no Qt."""

    @covers("LLFR-00159")
    def test_bug_icon_shape(self) -> None:
        """The bug has a rounded body, a round head, two antennae and
        three legs on each side, all with the icon pen.

        Inputs: none.
        Outputs: none.
        """
        layer_list = icon_shapes.icon_layer_list(
            icon_shapes.REPORT_BUG_ICON_STR)
        letter_list = [command_tuple[0] for layer_tuple in layer_list
                       for command_tuple in layer_tuple[0]]
        self.assertEqual(letter_list.count("R"), 1)
        self.assertEqual(letter_list.count("O"), 1)
        # Wing line, two antennae and six legs: nine straight strokes.
        self.assertEqual(letter_list.count("L"), 9)
        for layer_tuple in layer_list:
            self.assertEqual(layer_tuple[1], icon_shapes.INK_ROLE_STR)
            self.assertEqual(layer_tuple[3], icon_shapes.ICON_STROKE_WIDTH_F)
        leg_list = [layer_tuple[0] for layer_tuple in layer_list[5:]]
        left_leg_list = [leg for leg in leg_list if leg[1][1] < 12.0]
        right_leg_list = [leg for leg in leg_list if leg[1][1] > 12.0]
        self.assertEqual(len(left_leg_list), 3)
        self.assertEqual(len(right_leg_list), 3)

    @covers("LLFR-00364")
    def test_credit_color_is_paler_than_the_normal_text(self) -> None:
        """The credit color is lighter than the panel's normal text, and
        its style sheet has no hover rule.

        Inputs: none.
        Outputs: none.
        """
        self.assertGreater(
            theme.relative_luminance_f(theme.CREDIT_TEXT_COLOR_STR),
            theme.relative_luminance_f(theme.TEXT_COLOR_STR))
        self.assertGreater(
            theme.relative_luminance_f(theme.CREDIT_TEXT_COLOR_STR),
            theme.relative_luminance_f(theme.NORMAL_TEXT_COLOR_STR))
        style_str = theme.credit_label_style_sheet("credit_label")
        self.assertIn(theme.CREDIT_TEXT_COLOR_STR, style_str)
        self.assertNotIn(":hover", style_str)
        self.assertIn("background: transparent", style_str)


@requires_qt
class ReportBugButtonTest(unittest.TestCase):
    """The Report a bug button and the credit text in a top panel."""

    def setUp(self) -> None:
        """Create and show a wide top panel.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.top_panel import TopPanel
        self.top_panel = TopPanel()
        self.top_panel.resize(1200, 40)
        self.top_panel.show()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close the panel.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.close()
        self.top_panel.deleteLater()
        self.application.processEvents()

    @covers("LLFR-00358", "LLFR-00347", "LLFR-00349", "LLFR-00348",
            "LLFR-00158", "LLFR-00159", "LLFR-00215", "LLFR-00181")
    def test_button_alone_in_the_last_group(self) -> None:
        """"Report a bug" is the last button, alone in its group, 16 px
        right of Redo, with only the bug icon and its name as the tip.

        Inputs: none.
        Outputs: none.
        """
        from view.action_button import ActionButton
        from view.top_panel import button_tip_text_str
        button = self.top_panel.report_bug_button
        self.assertIsInstance(button, ActionButton)
        self.assertEqual(button_name(button), "Report a bug")
        self.assertEqual(button.text(), "")
        self.assertEqual(button.icon_name_str,
                         icon_shapes.REPORT_BUG_ICON_STR)
        self.assertFalse(button.icon().isNull())
        self.assertEqual(self.top_panel.button_group_list[-1], [button])
        self.assertIs(self.top_panel.button_list()[-1], button)
        self.assertEqual(button.segment_position_str,
                         theme.SEGMENT_SINGLE_STR)
        redo_button = self.top_panel.redo_button
        self.assertEqual(button.x() - redo_button.geometry().right() - 1,
                         theme.TOOLBAR_GROUP_GAP_I)
        self.assertEqual(button.y(), redo_button.y())
        self.assertTrue(button.isVisible())
        # LLFR-00215: the name alone, on both systems.
        self.assertEqual(button.toolTip(), "Report a bug")
        self.assertEqual(button_tip_line_list(button), ["Report a bug"])
        for macos_b in (True, False):
            self.assertEqual(button_tip_text_str("Report a bug", macos_b),
                             "Report a bug")
        # Not a plot tool.
        self.assertNotIn(button,
                         self.top_panel.plot_tool_button_dict.values())

    @covers("LLFR-00358")
    def test_button_enabled_without_a_data_file(self) -> None:
        """The button is enabled when the panel is created, while the
        layout buttons are still disabled.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(self.top_panel.report_bug_button.isEnabled())
        self.assertFalse(self.top_panel.save_layout_button.isEnabled())

    @covers("LLFR-00360", "LLFR-00001", "LLFR-00359")
    def test_click_shows_active_color_then_asks(self) -> None:
        """A click shows the active color at once and emits
        report_bug_requested once control is back in Qt.

        Inputs: none.
        Outputs: none.
        """
        request_list = []
        self.top_panel.report_bug_requested.connect(
            lambda: request_list.append(
                self.top_panel.report_bug_button.is_active()))
        self.top_panel.report_bug_button.click()
        self.assertTrue(self.top_panel.report_bug_button.is_active())
        self.assertEqual(request_list, [])
        self.application.processEvents()
        self.assertEqual(request_list, [True])

    @covers("LLFR-00364")
    def test_credit_text_at_the_right_end(self) -> None:
        """The credit text is shown at the right end of the panel, right
        of the last button, vertically within the buttons' row.

        Inputs: none.
        Outputs: none.
        """
        label = self.top_panel.credit_label
        self.assertEqual(label.text(), EXPECTED_CREDIT_STR)
        self.assertIs(label.parentWidget(), self.top_panel)
        self.assertTrue(label.isVisible())
        self.assertEqual(label.geometry().right(),
                         self.top_panel.width() - 1)
        last_button = self.top_panel.report_bug_button
        self.assertGreaterEqual(
            label.x() - last_button.geometry().right() - 1,
            theme.CREDIT_MINIMUM_GAP_I)
        self.assertGreaterEqual(label.y(), 0)
        self.assertLessEqual(label.geometry().bottom(),
                             self.top_panel.height() - 1)
        # It follows the right end when the panel grows.
        self.top_panel.resize(1400, 40)
        self.application.processEvents()
        self.assertEqual(label.geometry().right(), 1399)

    @covers("LLFR-00364")
    def test_credit_text_is_pale_and_not_a_button(self) -> None:
        """The text is drawn in the pale credit color, is not a button,
        lets the mouse through and takes no focus.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QPalette
        from PyQt6.QtWidgets import QAbstractButton
        label = self.top_panel.credit_label
        self.assertNotIsInstance(label, QAbstractButton)
        self.assertNotIn(label, self.top_panel.button_list())
        label.ensurePolished()
        self.assertEqual(
            label.palette().color(QPalette.ColorRole.WindowText).name(),
            theme.CREDIT_TEXT_COLOR_STR)
        self.assertTrue(label.testAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents))
        self.assertEqual(label.focusPolicy(), Qt.FocusPolicy.NoFocus)
        self.assertEqual(label.textInteractionFlags(),
                         Qt.TextInteractionFlag.NoTextInteraction)
        self.assertEqual(label.toolTip(), "")
        self.assertNotIn(":hover", label.styleSheet())
        # The mouse finds the panel, not the label, over the text.
        center_point = label.geometry().center()
        self.assertIsNot(self.top_panel.childAt(center_point), label)

    @covers("LLFR-00364", "LLFR-00349")
    def test_credit_hidden_when_narrow_and_buttons_unmoved(self) -> None:
        """When the panel is too narrow, the text is hidden, and the
        buttons keep their places and sizes.

        Inputs: none.
        Outputs: none.
        """
        label = self.top_panel.credit_label
        wide_geometry_list = [button.geometry() for button in
                              self.top_panel.button_list()]
        buttons_right_i = self.top_panel.report_bug_button.geometry().right()
        needed_width_i = (buttons_right_i + 1 + theme.CREDIT_MINIMUM_GAP_I
                          + label.sizeHint().width())
        for width_i in (needed_width_i - 1, buttons_right_i + 40, 300):
            with self.subTest(width=width_i):
                self.top_panel.resize(width_i, 40)
                self.application.processEvents()
                self.assertFalse(label.isVisible())
                self.assertEqual([button.geometry() for button in
                                  self.top_panel.button_list()],
                                 wide_geometry_list)
        self.top_panel.resize(needed_width_i, 40)
        self.application.processEvents()
        self.assertTrue(label.isVisible())
        self.assertGreater(label.x(), buttons_right_i)
        self.assertEqual([button.geometry() for button in
                          self.top_panel.button_list()], wide_geometry_list)


@requires_qt
class ReportBugWindowTest(unittest.TestCase):
    """The Report a bug button in the main window with a real file."""

    def setUp(self) -> None:
        """Create the window and the controllers.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtWidgets import QMessageBox
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.main_window = MainWindow()
        self.main_window.resize(1200, 800)
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.main_window.show()
        self.application.processEvents()
        self.top_panel = self.main_window.top_panel
        self.box_list = []
        box_patch = mock.patch.object(
            QMessageBox, "exec",
            new=lambda box: self.box_list.append(box) or 0)
        box_patch.start()
        self.addCleanup(box_patch.stop)
        # LLFR-00359: the browser is never really opened in a test.
        self.opened_url_list = []
        self.open_result_b = True
        url_patch = mock.patch.object(
            QDesktopServices, "openUrl",
            new=lambda url: self.record_open(url))
        url_patch.start()
        self.addCleanup(url_patch.stop)

    def tearDown(self) -> None:
        """Close the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def record_open(self, url) -> bool:
        """Stand-in for QDesktopServices.openUrl.

        Inputs:
            url: the QUrl to open.
        Outputs: open_result_b, as the real call would report.
        """
        self.opened_url_list.append(
            (url.toString(), self.top_panel.report_bug_button.is_active()))
        return self.open_result_b

    def open_file(self) -> None:
        """Open a small CSV file through the Open file flow.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QFileDialog
        temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_folder.cleanup)
        path_str = os.path.join(temporary_folder.name, "data.csv")
        with open(path_str, "w", encoding="utf-8") as data_file:
            data_file.write("Time,Speed\n")
            for index_i in range(20):
                data_file.write(f"{index_i * 0.1:.1f},{index_i % 7}\n")
        with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                        return_value=path_str):
            self.main_window._on_open_file_activated()
        self.application.processEvents()

    def wait_until_normal(self) -> float:
        """Process events until the button is normal; return the time.

        Inputs: none.
        Outputs: the seconds from the call until the button was normal.
        """
        start_s = time.monotonic()
        button = self.top_panel.report_bug_button
        while (button.is_active()
               and time.monotonic() - start_s < MAXIMUM_WAIT_TIME_S):
            self.application.processEvents()
            time.sleep(0.01)
        return time.monotonic() - start_s

    @covers("LLFR-00359", "LLFR-00360", "LLFR-00358", "LLFR-00003")
    def test_click_opens_the_new_issue_page(self) -> None:
        """A click asks the browser once for the exact page, while the
        button is active, and the button turns normal after >= 0.3 s;
        no box is shown.

        Inputs: none.
        Outputs: none.
        """
        from view.top_panel import REPORT_BUG_URL_STR
        self.assertEqual(REPORT_BUG_URL_STR, EXPECTED_URL_STR)
        button = self.top_panel.report_bug_button
        self.assertTrue(button.isEnabled())
        click_s = time.monotonic()
        button.click()
        self.assertTrue(button.is_active())
        self.wait_until_normal()
        normal_after_s = time.monotonic() - click_s
        self.assertEqual(self.opened_url_list, [(EXPECTED_URL_STR, True)])
        self.assertFalse(button.is_active())
        self.assertGreaterEqual(normal_after_s, MINIMUM_ACTIVE_TIME_S - 0.01)
        self.assertLess(normal_after_s, MAXIMUM_WAIT_TIME_S)
        self.assertEqual(self.box_list, [])

    @covers("LLFR-00359", "LLFR-00358")
    def test_click_with_a_file_changes_nothing_else(self) -> None:
        """With a file open and plotted, the click leaves the signal
        list, the plots, the time range and the undo and redo history
        unchanged.

        Inputs: none.
        Outputs: none.
        """
        self.open_file()
        self.main_window.signal_list_panel.signal_double_clicked.emit(
            "Speed")
        self.application.processEvents()
        self.assertTrue(self.top_panel.report_bug_button.isEnabled())
        plot_panel = self.main_window.plot_panel
        plot_id_list = plot_panel.plot_id_list(plot_panel.current_tab_id())
        self.assertEqual(len(plot_id_list), 1)
        before_tuple = (
            self.main_window.signal_list_panel.signal_name_list(),
            plot_id_list, self.main_window.tab_name_list(),
            plot_panel.plot_view(plot_id_list[0]).time_range_tuple(),
            self.main_window.is_undo_enabled(),
            self.main_window.is_redo_enabled(),
            len(self.controller.plot_controller.undo_history.snapshot_list))
        self.top_panel.report_bug_button.click()
        self.wait_until_normal()
        after_tuple = (
            self.main_window.signal_list_panel.signal_name_list(),
            plot_panel.plot_id_list(plot_panel.current_tab_id()),
            self.main_window.tab_name_list(),
            plot_panel.plot_view(plot_id_list[0]).time_range_tuple(),
            self.main_window.is_undo_enabled(),
            self.main_window.is_redo_enabled(),
            len(self.controller.plot_controller.undo_history.snapshot_list))
        self.assertEqual(after_tuple, before_tuple)
        self.assertEqual(self.opened_url_list, [(EXPECTED_URL_STR, True)])
        self.assertEqual(self.box_list, [])

    @covers("LLFR-00361", "LLFR-00360", "HLFR-00002")
    def test_error_box_when_the_browser_cannot_be_opened(self) -> None:
        """When openUrl fails, an error box says that the page could
        not be opened, with its address, and the button turns normal.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        self.open_result_b = False
        self.top_panel.report_bug_button.click()
        self.wait_until_normal()
        self.assertEqual(len(self.opened_url_list), 1)
        self.assertEqual(len(self.box_list), 1)
        box = self.box_list[0]
        self.assertEqual(box.icon(), QMessageBox.Icon.Critical)
        self.assertIn("could not be opened", box.text())
        self.assertIn(EXPECTED_URL_STR, box.text())
        self.assertFalse(self.top_panel.report_bug_button.is_active())

    @covers("LLFR-00361")
    def test_error_box_builder(self) -> None:
        """The error box has the critical icon, its title, the address
        and one OK button.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        from view import message_boxes
        box = message_boxes.build_report_bug_error_box(None,
                                                       EXPECTED_URL_STR)
        self.assertEqual(box.icon(), QMessageBox.Icon.Critical)
        self.assertEqual(box.windowTitle(),
                         message_boxes.REPORT_BUG_ERROR_TITLE_STR)
        self.assertIn("The page could not be opened", box.text())
        self.assertTrue(box.text().endswith(EXPECTED_URL_STR))
        self.assertEqual(box.standardButtons(),
                         QMessageBox.StandardButton.Ok)
        box.deleteLater()

    @covers("LLFR-00364", "HLFR-00080")
    def test_credit_in_the_upper_right_corner_of_the_window(self) -> None:
        """In the window, the credit text is visible at the right end of
        the top panel, which is at the top of the window.

        Inputs: none.
        Outputs: none.
        """
        label = self.top_panel.credit_label
        self.assertTrue(label.isVisible())
        self.assertEqual(label.text(), EXPECTED_CREDIT_STR)
        label_right_point = label.mapTo(
            self.main_window, label.rect().topRight())
        central_right_i = self.main_window.centralWidget().width()
        self.assertGreater(label_right_point.x(), central_right_i - 30)
        self.assertLess(label_right_point.y(), self.top_panel.height() + 30)


if __name__ == "__main__":
    unittest.main()
