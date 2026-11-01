"""Tests for the button tips of the top panel (issue #105).

Covers LLFR-00018 (the button is called "Data tip"), LLFR-00181 (the
name on the first line), LLFR-00213 (the shortcut on a second, paler
line), LLFR-00214 (the mouse use of the Zoom tool) and LLFR-00215 (the
texts on macOS and on Windows). The platform check of view.top_panel is
patched so that both systems are tested on any machine.
"""

import colorsys
import unittest
from unittest import mock

from tests.support import (
    button_name, button_tip_line_list, covers, get_qt_application,
    requires_qt)

from view import theme

# LLFR-00215: top panel attribute -> (name, macOS lines, Windows lines).
EXPECTED_TIP_DICT = {
    "undo_button": ("Undo", ["Cmd+Z"], ["Ctrl+Z"]),
    "redo_button": ("Redo", ["Cmd+Y"], ["Ctrl+Y"]),
    "tip_button": ("Data tip", ["Hold Cmd"], ["Hold Ctrl"]),
    "marker_button": ("Vertical marker", ["Hold Shift"], ["Hold Shift"]),
    "delta_x_button": ("Delta X", ["Hold X"], ["Hold X"]),
    "delta_y_button": ("Delta Y", ["Hold Y"], ["Hold Y"]),
    "reset_zoom_button": ("Reset zoom", ["Z"], ["Z"]),
    "zoom_button": ("Zoom",
                    ["Click or drag to zoom in",
                     "Wheel or two-finger swipe to zoom in or out"],
                    ["Click or drag to zoom in",
                     "Wheel or two-finger swipe to zoom in or out"]),
    "open_file_button": ("Open file", [], []),
    "grid_button": ("Grid", [], []),
    "export_button": ("Export", [], []),
    "copy_button": ("Copy", [], []),
}
# LLFR-00215: the buttons whose tip shows only the name.
NAME_ONLY_ATTRIBUTE_TUPLE = ("open_file_button", "grid_button",
                             "export_button", "copy_button")
# LLFR-00213: minimum WCAG contrast of the paler line on the tip
# background, so that it stays readable.
MINIMUM_DETAIL_CONTRAST_F = 4.5


class TipColorTokenTest(unittest.TestCase):
    """LLFR-00213, LLFR-00214: the paler color of the lines below the name."""

    @covers("LLFR-00213", "LLFR-00214")
    def test_detail_color_is_paler_but_readable(self) -> None:
        """The detail color is lighter than the name, still readable.

        Inputs: none.
        Outputs: none.
        """
        self.assertGreater(
            theme.relative_luminance_f(theme.TOOLTIP_DETAIL_COLOR_STR),
            theme.relative_luminance_f(theme.TEXT_COLOR_STR))
        self.assertGreaterEqual(
            theme.contrast_ratio_f(theme.TOOLTIP_DETAIL_COLOR_STR,
                                   theme.SURFACE_COLOR_STR),
            MINIMUM_DETAIL_CONTRAST_F)
        self.assertIn(f"background: {theme.SURFACE_COLOR_STR}",
                      [rule_str for rule_str in
                       theme.application_style_sheet().split("\n")
                       if rule_str.startswith("QToolTip")][0])


@requires_qt
class ButtonTipTest(unittest.TestCase):
    """LLFR-00213 to LLFR-00215: the button tips on macOS and Windows."""

    def setUp(self) -> None:
        """Prepare the application and the list of panels to close.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        self.panel_list = []

    def tearDown(self) -> None:
        """Close and delete every panel made by the test.

        Inputs: none.
        Outputs: none.
        """
        for top_panel in self.panel_list:
            top_panel.close()
            top_panel.deleteLater()
        self.application.processEvents()

    def create_panel(self, macos_b: bool):
        """Create a top panel as it is built on macOS or on Windows.

        Inputs:
            macos_b: True to build the panel as on macOS.
        Outputs: the TopPanel.
        """
        from view import top_panel as top_panel_module
        with mock.patch.object(top_panel_module, "running_on_macos",
                               return_value=macos_b):
            top_panel = top_panel_module.TopPanel()
        self.panel_list.append(top_panel)
        return top_panel

    def detail_color_list(self, button) -> list:
        """Return the text color of each line of a button tip.

        Inputs:
            button: a top panel button.
        Outputs: a list with, for each line, the "#rrggbb" color of its
            text, or "" when the line has no color of its own (it then
            takes the tip's text color, theme.TEXT_COLOR_STR).
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QTextDocument
        document = QTextDocument()
        document.setHtml(button.toolTip())
        color_list = []
        block = document.begin()
        while block.isValid():
            brush = block.begin().fragment().charFormat().foreground()
            color_list.append(
                "" if brush.style() == Qt.BrushStyle.NoBrush
                else brush.color().name())
            block = block.next()
        return color_list

    @covers("LLFR-00215", "LLFR-00213", "LLFR-00214", "LLFR-00181")
    def test_tip_texts_on_macos_and_windows(self) -> None:
        """Each button tip has the lines of the table, on both systems.

        Inputs: none.
        Outputs: none.
        """
        for macos_b, column_i in ((True, 1), (False, 2)):
            top_panel = self.create_panel(macos_b)
            for attribute_str, expected_tuple in EXPECTED_TIP_DICT.items():
                button = getattr(top_panel, attribute_str)
                with self.subTest(macos_b=macos_b, button=attribute_str):
                    self.assertEqual(
                        button_tip_line_list(button),
                        [expected_tuple[0]] + expected_tuple[column_i])

    @covers("LLFR-00215", "LLFR-00181")
    def test_name_only_buttons(self) -> None:
        """Open file, Grid, Export and Copy show only their plain name.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        for macos_b in (True, False):
            top_panel = self.create_panel(macos_b)
            for attribute_str in NAME_ONLY_ATTRIBUTE_TUPLE:
                button = getattr(top_panel, attribute_str)
                name_str = EXPECTED_TIP_DICT[attribute_str][0]
                with self.subTest(macos_b=macos_b, button=attribute_str):
                    self.assertEqual(button.toolTip(), name_str)
                    self.assertFalse(Qt.mightBeRichText(button.toolTip()))

    @covers("LLFR-00215")
    def test_unknown_button_shows_only_its_name(self) -> None:
        """A button not in the table (e.g. Save layout) has no detail.

        Inputs: none.
        Outputs: none.
        """
        from view import top_panel as top_panel_module
        for macos_b in (True, False):
            with self.subTest(macos_b=macos_b):
                self.assertEqual(top_panel_module.button_tip_detail_list(
                    "Save layout", macos_b), [])
                self.assertEqual(top_panel_module.button_tip_text_str(
                    "Load layout", macos_b), "Load layout")

    @covers("LLFR-00213", "LLFR-00214")
    def test_lines_below_the_name_are_paler(self) -> None:
        """The name has the tip's color; the lines below the paler one.

        Inputs: none.
        Outputs: none.
        """
        for macos_b in (True, False):
            top_panel = self.create_panel(macos_b)
            for attribute_str, expected_tuple in EXPECTED_TIP_DICT.items():
                if attribute_str in NAME_ONLY_ATTRIBUTE_TUPLE:
                    continue
                button = getattr(top_panel, attribute_str)
                with self.subTest(macos_b=macos_b, button=attribute_str):
                    color_list = self.detail_color_list(button)
                    self.assertEqual(len(color_list),
                                     1 + len(expected_tuple[1]))
                    self.assertEqual(color_list[0], "")
                    for color_str in color_list[1:]:
                        self.assertEqual(
                            color_str,
                            theme.TOOLTIP_DETAIL_COLOR_STR.lower())

    @covers("LLFR-00213", "LLFR-00214", "LLFR-00181")
    def test_tip_shows_on_hover_with_all_lines(self) -> None:
        """The shown tip is the rich tip, and it hides on leave.

        Inputs: none.
        Outputs: none.
        """
        import time
        from PyQt6.QtCore import QEvent, QPoint
        from PyQt6.QtGui import QHelpEvent
        from PyQt6.QtWidgets import QApplication, QToolTip
        top_panel = self.create_panel(False)
        top_panel.show()
        self.application.processEvents()

        def wait_until(condition) -> bool:
            """Process events until condition() is true or 2 s pass.

            Inputs:
                condition: a function without arguments.
            Outputs: the last value of condition().
            """
            end_s = time.monotonic() + 2.0
            while time.monotonic() < end_s:
                self.application.processEvents()
                if condition():
                    return True
                time.sleep(0.01)
            return bool(condition())

        for attribute_str in ("zoom_button", "undo_button"):
            button = getattr(top_panel, attribute_str)
            with self.subTest(button=attribute_str):
                local_point = QPoint(button.width() // 2,
                                     button.height() // 2)
                QApplication.sendEvent(button, QHelpEvent(
                    QEvent.Type.ToolTip, local_point,
                    button.mapToGlobal(local_point)))
                self.assertTrue(wait_until(QToolTip.isVisible))
                self.assertEqual(QToolTip.text(), button.toolTip())
                QApplication.sendEvent(button, QEvent(QEvent.Type.Leave))
                self.assertTrue(wait_until(
                    lambda: not QToolTip.isVisible()))

    @covers("LLFR-00018", "LLFR-00181")
    def test_data_tip_button_name(self) -> None:
        """The Data tip button is called "Data tip" on both systems.

        Inputs: none.
        Outputs: none.
        """
        for macos_b in (True, False):
            top_panel = self.create_panel(macos_b)
            button = top_panel.tip_button
            with self.subTest(macos_b=macos_b):
                self.assertEqual(button_name(button), "Data tip")
                self.assertEqual(button.button_name(), "Data tip")
                self.assertEqual(button_tip_line_list(button)[0],
                                 "Data tip")

    @covers("LLFR-00215", "LLFR-00137", "LLFR-00191")
    def test_texts_follow_the_real_shortcuts(self) -> None:
        """The Undo and Redo tips are built from the window's shortcuts.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QKeySequence
        from view import top_panel as top_panel_module
        from view.main_window import MainWindow
        main_window = MainWindow()
        try:
            portable = QKeySequence.SequenceFormat.PortableText
            self.assertEqual(
                main_window.redo_shortcut.key().toString(portable),
                top_panel_module.button_tip_detail_list("Redo", False)[0])
            self.assertEqual(
                main_window.undo_shortcut.key().toString(portable),
                top_panel_module.button_tip_detail_list("Undo", False)[0])
        finally:
            main_window.close()
            main_window.deleteLater()
            self.application.processEvents()

    @covers("LLFR-00215", "LLFR-00148", "LLFR-00154", "LLFR-00197",
            "LLFR-00200", "LLFR-00207")
    def test_key_names_follow_the_tool_keys(self) -> None:
        """The held and pressed keys are named from the filter's keys.

        Inputs: none.
        Outputs: none.
        """
        from view import tip_key_filter
        from view.top_panel import key_name_str
        for key_i, macos_str, windows_str in (
                (tip_key_filter.TIP_KEY_I, "Cmd", "Ctrl"),
                (tip_key_filter.MARKER_KEY_I, "Shift", "Shift"),
                (tip_key_filter.DELTA_X_KEY_I, "X", "X"),
                (tip_key_filter.DELTA_Y_KEY_I, "Y", "Y"),
                (tip_key_filter.RESET_ZOOM_KEY_I, "Z", "Z")):
            with self.subTest(key_i=key_i):
                self.assertEqual(key_name_str(key_i, True), macos_str)
                self.assertEqual(key_name_str(key_i, False), windows_str)

    @covers("LLFR-00215")
    def test_platform_check(self) -> None:
        """Only macOS gets the macOS texts; Linux gets the Windows ones.

        Inputs: none.
        Outputs: none.
        """
        from view import top_panel as top_panel_module
        for platform_str, expected_b in (("darwin", True), ("win32", False),
                                         ("linux", False)):
            with self.subTest(platform_str=platform_str):
                with mock.patch.object(top_panel_module.sys, "platform",
                                       platform_str):
                    self.assertEqual(top_panel_module.running_on_macos(),
                                     expected_b)


class ResizeBorderColorTokenTest(unittest.TestCase):
    """LLFR-00280: the resize border line is blue and 2 pixels wide."""

    @covers("LLFR-00280")
    def test_border_color_is_blue(self) -> None:
        """The line color has a blue hue and is clearly saturated.

        Inputs: none.
        Outputs: none.
        """
        color_str = theme.RESIZE_BORDER_COLOR_STR.lstrip("#")
        red_f, green_f, blue_f = (int(color_str[index_i:index_i + 2], 16)
                                  / 255.0 for index_i in (0, 2, 4))
        hue_f, _, saturation_f = colorsys.rgb_to_hls(red_f, green_f, blue_f)
        self.assertGreaterEqual(hue_f * 360.0, 195.0)
        self.assertLessEqual(hue_f * 360.0, 245.0)
        self.assertGreater(saturation_f, 0.3)
        self.assertEqual(theme.RESIZE_BORDER_WIDTH_I, 2)


if __name__ == "__main__":
    unittest.main()
