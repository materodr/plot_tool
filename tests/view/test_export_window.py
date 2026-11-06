"""Qt tests of the Export window (#268, HLFR-00038).

The window is built on its own, with no main window, and never shown
modally: the tests click its buttons and send it keys directly. The
settings that keep the last format are an INI file of the test
(LLFR-01406), so the settings of the user are never read or changed.
The behaviour follows the owner's answers of 2026-11-06 in #268.
"""

import os
import tempfile
import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt


@requires_qt
class ExportWindowTest(unittest.TestCase):
    """The format buttons, the Cancel button and the default button."""

    def setUp(self) -> None:
        """Create the application and isolate the settings.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view import export_window
        self.export_window = export_window
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        self.settings_path_str = os.path.join(self.temporary_folder.name,
                                              "settings.ini")
        settings_patch = mock.patch.object(
            export_window, "settings_file_path_str", self.settings_path_str)
        settings_patch.start()
        self.addCleanup(settings_patch.stop)

    def new_window(self, default_format_str: str = "pdf"):
        """Build an Export window with no parent and show it.

        Inputs:
            default_format_str: the format of the default button.
        Outputs: the ExportWindow, deleted at the end of the test.
        """
        window = self.export_window.ExportWindow(None, default_format_str)
        window.setModal(False)
        window.show()
        self.application.processEvents()
        self.addCleanup(window.deleteLater)
        self.addCleanup(window.close)
        return window

    @covers("LLFR-00127", "LLFR-01229", "LLFR-01402", "HLFR-00038")
    def test_title_buttons_and_their_order(self) -> None:
        """The window is titled "Export" and shows the three large format
        buttons side by side, each with an icon and its text, from left
        to right, and a Cancel button below them.

        Inputs: none.
        Outputs: none.
        """
        window = self.new_window()
        self.assertEqual(window.windowTitle(), "Export")
        button_list = list(window.format_button_dict.values())
        self.assertEqual([button.text() for button in button_list],
                         ["PDF (all tabs)", "Word .docx (all tabs)",
                          "PNG (one file per tab)"])
        self.assertEqual(list(window.format_button_dict),
                         ["pdf", "docx", "png"])
        left_list = [button.mapTo(window, button.rect().topLeft()).x()
                     for button in button_list]
        top_list = [button.mapTo(window, button.rect().topLeft()).y()
                    for button in button_list]
        self.assertEqual(left_list, sorted(left_list))
        self.assertEqual(len(set(left_list)), 3)
        self.assertEqual(len(set(top_list)), 1)
        for button in button_list:
            self.assertFalse(button.icon().isNull())
            self.assertGreaterEqual(button.iconSize().width(), 32)
            self.assertGreaterEqual(
                button.height(),
                self.export_window.FORMAT_BUTTON_MINIMUM_HEIGHT_I)
        cancel_button = window.cancel_button
        self.assertEqual(cancel_button.text(), "Cancel")
        cancel_top_i = cancel_button.mapTo(window, cancel_button.rect()
                                           .topLeft()).y()
        self.assertGreater(cancel_top_i, top_list[0] + button_list[0]
                           .height() - 1)

    @covers("LLFR-01403", "HLFR-00038")
    def test_click_on_a_format_closes_with_that_format(self) -> None:
        """A click on a format button accepts the window with its format.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QDialog
        for format_str in ("pdf", "docx", "png"):
            with self.subTest(format_str=format_str):
                window = self.new_window()
                window.format_button_dict[format_str].click()
                self.application.processEvents()
                self.assertEqual(window.chosen_format_str, format_str)
                self.assertEqual(window.result(),
                                 QDialog.DialogCode.Accepted.value)
                self.assertFalse(window.isVisible())

    @covers("LLFR-01404", "LLFR-01414", "HLFR-00038")
    def test_cancel_esc_and_close_choose_nothing(self) -> None:
        """Cancel, Esc and the close button close the window with no
        format.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QDialog
        for way_str in ("cancel", "esc", "close"):
            with self.subTest(way_str=way_str):
                window = self.new_window("docx")
                if way_str == "cancel":
                    window.cancel_button.click()
                elif way_str == "esc":
                    QTest.keyClick(window, Qt.Key.Key_Escape)
                else:
                    window.close()
                self.application.processEvents()
                self.assertEqual(window.chosen_format_str, "")
                self.assertEqual(window.result(),
                                 QDialog.DialogCode.Rejected.value)
                self.assertFalse(window.isVisible())

    @covers("LLFR-01405", "LLFR-01416", "HLFR-00038")
    def test_default_button_and_enter(self) -> None:
        """The given format is the one default button, which Enter
        clicks; an unknown format gives the PDF.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        for given_str, default_str in (("png", "png"), ("docx", "docx"),
                                       ("pdf", "pdf"), ("other", "pdf"),
                                       ("", "pdf")):
            with self.subTest(given_str=given_str):
                window = self.new_window(given_str)
                self.assertEqual(window.default_format(), default_str)
                default_list = [
                    format_str for format_str, button
                    in window.format_button_dict.items()
                    if button.isDefault()]
                self.assertEqual(default_list, [default_str])
                self.assertFalse(window.cancel_button.isDefault())
                QTest.keyClick(window, Qt.Key.Key_Return)
                self.application.processEvents()
                self.assertEqual(window.chosen_format_str, default_str)

    @covers("LLFR-01406", "LLFR-01405", "HLFR-00038")
    def test_last_format_kept_in_the_settings(self) -> None:
        """The format is written to the settings file and read back, as
        after a new launch; nothing remembered, or an unknown value,
        gives the PDF.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QSettings
        export_window = self.export_window
        self.assertEqual(export_window.remembered_export_format(), "pdf")
        export_window.remember_export_format("docx")
        self.assertTrue(os.path.isfile(self.settings_path_str))
        # A new QSettings on the same file, as on the next launch.
        settings = QSettings(self.settings_path_str,
                             QSettings.Format.IniFormat)
        self.assertEqual(settings.value(export_window.EXPORT_FORMAT_KEY_STR),
                         "docx")
        self.assertEqual(export_window.remembered_export_format(), "docx")
        export_window.remember_export_format("xlsx")
        self.assertEqual(export_window.remembered_export_format(), "docx")
        settings.setValue(export_window.EXPORT_FORMAT_KEY_STR, "garbage")
        settings.sync()
        self.assertEqual(export_window.remembered_export_format(), "pdf")

    @covers("LLFR-01406", "HLFR-00038")
    def test_settings_failure_keeps_the_app_running(self) -> None:
        """Settings that cannot be read give the PDF, and a failed write
        is ignored.

        Inputs: none.
        Outputs: none.
        """
        export_window = self.export_window
        with mock.patch.object(export_window, "open_settings",
                               side_effect=OSError("no settings")):
            self.assertEqual(export_window.remembered_export_format(),
                             "pdf")
            export_window.remember_export_format("png")

    @covers("LLFR-01406", "HLFR-00038")
    def test_main_window_remembers_the_clicked_format(self) -> None:
        """MainWindow.ask_export_format shows the window with the
        remembered default, keeps the clicked format and blocks Ctrl+P
        while the window is open.

        Inputs: none.
        Outputs: none.
        """
        from view.main_window import MainWindow
        main_window = MainWindow()
        self.addCleanup(main_window.deleteLater)
        self.addCleanup(main_window.close)
        self.export_window.remember_export_format("png")
        record_list = []

        def answer(dialog) -> str:
            """Record the window and click "Word .docx (all tabs)".

            Inputs:
                dialog: the ExportWindow.
            Outputs: "docx".
            """
            record_list.append((dialog.default_format(), dialog.parent(),
                                main_window.export_window_open_b))
            return "docx"

        main_window.run_export_window = answer
        self.assertEqual(main_window.ask_export_format(), "docx")
        self.assertEqual(record_list, [("png", main_window, True)])
        self.assertFalse(main_window.export_window_open_b)
        self.assertEqual(self.export_window.remembered_export_format(),
                         "docx")
        main_window.run_export_window = lambda dialog: ""
        self.assertEqual(main_window.ask_export_format(), "")
        self.assertEqual(self.export_window.remembered_export_format(),
                         "docx")


@requires_qt
class ExportWindowIconTest(unittest.TestCase):
    """The icons of the format buttons (LLFR-01410)."""

    @covers("LLFR-01410", "HLFR-00038", "HLFR-00042")
    def test_each_format_has_its_own_drawn_icon(self) -> None:
        """Each of the three icons is drawn on the 24 by 24 grid with the
        pen of the top panel icons, is not a top panel icon, and the
        three drawings differ.

        Inputs: none.
        Outputs: none.
        """
        get_qt_application()
        from view import icon_shapes, icons
        from view.export_window import FORMAT_ICON_DICT
        name_list = list(FORMAT_ICON_DICT.values())
        self.assertEqual(name_list, [icon_shapes.PDF_FORMAT_ICON_STR,
                                     icon_shapes.DOCX_FORMAT_ICON_STR,
                                     icon_shapes.PNG_FORMAT_ICON_STR])
        image_bytes_list = []
        for name_str in name_list:
            self.assertNotIn(name_str, icon_shapes.ICON_NAME_TUPLE)
            layer_list = icon_shapes.icon_layer_list(name_str)
            self.assertTrue(layer_list)
            for layer_tuple in layer_list:
                self.assertIn(layer_tuple[3],
                              (icon_shapes.ICON_STROKE_WIDTH_F, 0.0))
                for command_tuple in layer_tuple[0]:
                    for value_f in command_tuple[1:]:
                        self.assertGreaterEqual(value_f, 0.0)
                        self.assertLessEqual(value_f,
                                             icon_shapes.ICON_GRID_F)
            image = icons.render_icon_image(name_str, "#000000", 48)
            painted_i = sum(
                1 for x_i in range(48) for y_i in range(48)
                if image.pixelColor(x_i, y_i).alpha() > 0)
            self.assertGreater(painted_i, 48)
            image_bytes_list.append(bytes(image.constBits().asstring(
                image.sizeInBytes())))
        self.assertEqual(len(set(image_bytes_list)), 3)


if __name__ == "__main__":
    unittest.main()
