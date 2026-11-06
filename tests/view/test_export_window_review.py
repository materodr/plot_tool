"""Reviewer's tests of the Export window of #268 (HLFR-00038).

They check, with a real MainWindow and MainController, cases that the
implementer's tests reach only in part: Ctrl+P with no plot and during
a drag, Enter on the remembered default button after the settings are
read again, and the one value shared by the Export button and Ctrl+P.
The behaviour follows the owner's answers of 2026-11-06 in #268. The
set-up is that of tests.view.test_export_copy.ExportCopyTest, so the
message boxes, the Export window and the settings are patched.
"""

import unittest
from unittest import mock

from tests.support import covers, requires_qt
from tests.view import test_export_copy

NOTHING_TO_EXPORT_TEXT_STR = "There are no plots to export."


@requires_qt
class ExportWindowReviewTest(unittest.TestCase):
    """The Export window opened by Ctrl+P and by the Export button."""

    # The set-up of the end-to-end export tests, without their tests.
    # (imported as a module, so that its tests are not run twice).
    setUp = test_export_copy.ExportCopyTest.setUp
    tearDown = test_export_copy.ExportCopyTest.tearDown
    fake_exec = test_export_copy.ExportCopyTest.fake_exec
    fake_run_export_window = (
        test_export_copy.ExportCopyTest.fake_run_export_window)
    plot_signal = test_export_copy.ExportCopyTest.plot_signal
    click = test_export_copy.ExportCopyTest.click

    def press_export_shortcut(self) -> None:
        """Press Ctrl+P (Cmd+P) in the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.export_shortcut.activated.emit()
        for _ in range(3):
            self.application.processEvents()

    @covers("LLFR-01407", "LLFR-00145", "LLFR-01139", "HLFR-00038")
    def test_shortcut_with_no_plots_shows_the_box_without_the_window(
            self) -> None:
        """Ctrl+P with no plot in any tab shows the nothing-to-export box
        at once and no Export window (the owner's answer of 2026-11-06
        in #268, item 4: "for both the button and Ctrl+P").

        Inputs: none.
        Outputs: none.
        """
        self.format_choice_str = "pdf"
        self.press_export_shortcut()
        self.assertEqual(self.window_record_list, [])
        self.assertEqual([record[2] for record in self.box_record_list],
                         [NOTHING_TO_EXPORT_TEXT_STR])

    @covers("LLFR-01172", "LLFR-01139", "HLFR-00038")
    def test_shortcut_during_a_drag_opens_no_window(self) -> None:
        """Ctrl+P while the mouse is dragged opens no Export window and
        shows no box (the owner's answer of 2026-11-06 in #268, item 5).

        Inputs: none.
        Outputs: none.
        """
        self.plot_signal("file1_speed")
        with mock.patch.object(self.main_window, "is_mouse_drag_in_progress",
                               return_value=True):
            self.press_export_shortcut()
        self.assertEqual(self.window_record_list, [])
        self.assertEqual(self.box_record_list, [])
        # After the drag, Ctrl+P opens the window again.
        self.press_export_shortcut()
        self.assertEqual(len(self.window_record_list), 1)

    @covers("LLFR-01405", "LLFR-01406", "LLFR-01403", "LLFR-01230",
            "HLFR-00038")
    def test_enter_runs_the_remembered_format_after_a_reload(self) -> None:
        """A format kept in the settings file is the default button of a
        window built after the settings are read again, as after a new
        launch, and Enter in that window runs that format's export (the
        owner's answer of 2026-11-06 in #268, item 2).

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QSettings, Qt
        from PyQt6.QtTest import QTest
        from view import export_window
        self.plot_signal("file1_speed")
        # The value written by an earlier run of the app.
        settings = QSettings(export_window.settings_file_path_str,
                             QSettings.Format.IniFormat)
        settings.setValue(export_window.EXPORT_FORMAT_KEY_STR, "docx")
        settings.sync()
        default_list = []

        def press_enter(dialog) -> str:
            """Show the window without a modal loop and press Enter.

            Inputs:
                dialog: the ExportWindow.
            Outputs: the format that Enter chose.
            """
            dialog.setModal(False)
            dialog.show()
            self.application.processEvents()
            default_list.append(dialog.default_format())
            QTest.keyClick(dialog, Qt.Key.Key_Return)
            self.application.processEvents()
            return dialog.chosen_format_str

        self.main_window.run_export_window = press_enter
        dialog_title_list = []

        def cancel_dialog(dialog) -> str:
            """Record the save dialog of the export and cancel it.

            Inputs:
                dialog: the QFileDialog that would be shown.
            Outputs: "" (cancelled).
            """
            dialog_title_list.append(dialog.windowTitle())
            return ""

        self.main_window.run_export_dialog = cancel_dialog
        self.press_export_shortcut()
        self.assertEqual(default_list, ["docx"])
        # LLFR-01230: Enter clicked "Word .docx (all tabs)", whose save
        # dialog then opened; nothing else was shown.
        self.assertEqual(len(dialog_title_list), 1)
        self.assertEqual(self.box_record_list, [])
        self.assertEqual(export_window.remembered_export_format(), "docx")

    @covers("LLFR-01406", "LLFR-01405", "LLFR-01416", "LLFR-01139",
            "HLFR-00038")
    def test_button_and_shortcut_share_the_last_format(self) -> None:
        """The format clicked in the window of Ctrl+P is the default of
        the window of the Export button, and back (the owner's answer of
        2026-11-06 in #268, item 2: "One value, shared by the Export
        button and Ctrl+P").

        Inputs: none.
        Outputs: none.
        """
        self.plot_signal("file1_speed")
        self.main_window.run_export_dialog = lambda dialog: ""
        self.format_choice_str = "png"
        self.press_export_shortcut()
        self.format_choice_str = "docx"
        self.click(self.top_panel.export_button)
        self.format_choice_str = ""
        self.press_export_shortcut()
        self.assertEqual([record[2] for record in self.window_record_list],
                         ["pdf", "png", "docx"])


if __name__ == "__main__":
    unittest.main()
