"""Tests for the visual theme (view/theme.py).

The theme only changes how the interface looks. These tests protect the
looks that requirements fix: active and normal button colors
(LLFR-00001 to LLFR-00003), the paler disabled Undo button (LLFR-00141),
the "+" button styled like an unselected tab (LLFR-00107), the curve
palette and the dashed magenta markers (LLFR-00144, LLFR-00083,
LLFR-00143), legend and tip colors (LLFR-00037, LLFR-00151). They also
check that the style lives in one place: the application style sheet is
set once, and no view file other than theme.py holds a color literal.
"""

import io
import os
import re
import tokenize
import unittest

import numpy as np

from tests.support import (
    REPOSITORY_ROOT_STR, covers, get_qt_application, requires_qt)

from model.curve_colors import MARKER_COLOR_STR, PALETTE_COLOR_TUPLE
from view import theme

VIEW_FOLDER_STR = os.path.join(REPOSITORY_ROOT_STR, "src", "view")
# Files of src/view allowed to hold "#rrggbb" literals.
COLOR_LITERAL_FILE_SET = {"theme.py"}
COLOR_LITERAL_PATTERN_STR = r"#[0-9a-fA-F]{6}\b"
MINIMUM_CONTRAST_RATIO_F = 3.0


def string_literal_list(path_str: str) -> list:
    """Return the string literals of a Python file (comments excluded).

    Inputs:
        path_str: the path of the .py file.
    Outputs: a list of the source text of every string token.
    """
    with open(path_str, encoding="utf-8") as source_file:
        source_str = source_file.read()
    token_list = tokenize.generate_tokens(io.StringIO(source_str).readline)
    string_type_set = {tokenize.STRING}
    # Python 3.12 splits f-strings into several token types.
    for name_str in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
        if hasattr(tokenize, name_str):
            string_type_set.add(getattr(tokenize, name_str))
    return [token.string for token in token_list
            if token.type in string_type_set]


class ThemeTokenTestCase(unittest.TestCase):
    """Checks of the design tokens that need no Qt."""

    @covers("LLFR-00001", "LLFR-00002", "LLFR-00003", "HLFR-00003")
    def test_active_and_normal_colors_contrast(self) -> None:
        """Active and normal button backgrounds differ by at least 3:1.

        Inputs: none.
        Outputs: none.
        """
        ratio_f = theme.contrast_ratio_f(theme.ACTIVE_COLOR_STR,
                                         theme.NORMAL_COLOR_STR)
        self.assertGreaterEqual(ratio_f, MINIMUM_CONTRAST_RATIO_F)
        # The text of each state is readable on its background.
        self.assertGreaterEqual(theme.contrast_ratio_f(
            theme.ACTIVE_COLOR_STR, theme.ACTIVE_TEXT_COLOR_STR), 4.5)
        self.assertGreaterEqual(theme.contrast_ratio_f(
            theme.NORMAL_COLOR_STR, theme.NORMAL_TEXT_COLOR_STR), 4.5)
        # Sanity of the ratio function: black on white is 21:1.
        self.assertAlmostEqual(
            theme.contrast_ratio_f("#000000", "#ffffff"), 21.0, places=3)
        self.assertAlmostEqual(
            theme.contrast_ratio_f("#808080", "#808080"), 1.0)

    @covers("LLFR-00001", "LLFR-00002", "LLFR-00003")
    def test_button_style_sheet_follows_the_state(self) -> None:
        """The state style sheets use only their own state's colors.

        Inputs: none.
        Outputs: none.
        """
        for segment_str in (theme.SEGMENT_SINGLE_STR,
                            theme.SEGMENT_FIRST_STR,
                            theme.SEGMENT_MIDDLE_STR,
                            theme.SEGMENT_LAST_STR):
            with self.subTest(segment_str=segment_str):
                active_str = theme.toggle_button_style_sheet(
                    "tip_button", True, segment_str)
                normal_str = theme.toggle_button_style_sheet(
                    "tip_button", False, segment_str)
                self.assertIn("QPushButton#tip_button", active_str)
                self.assertIn(theme.ACTIVE_COLOR_STR, active_str)
                self.assertNotIn(theme.NORMAL_COLOR_STR, active_str)
                self.assertIn(theme.NORMAL_COLOR_STR, normal_str)
                self.assertNotIn(theme.ACTIVE_COLOR_STR, normal_str)
                # Hovering an active button keeps the active color.
                hover_match = re.search(
                    r"#tip_button:hover \{ background-color: (#\w+);",
                    active_str)
                self.assertEqual(hover_match.group(1),
                                 theme.ACTIVE_COLOR_STR)

    @covers("LLFR-00141")
    def test_disabled_colors_are_paler(self) -> None:
        """The disabled background, text and border are all paler.

        Inputs: none.
        Outputs: none.
        """
        luminance = theme.relative_luminance_f
        self.assertGreater(luminance(theme.DISABLED_COLOR_STR),
                           luminance(theme.NORMAL_COLOR_STR))
        self.assertGreater(luminance(theme.DISABLED_TEXT_COLOR_STR),
                           luminance(theme.NORMAL_TEXT_COLOR_STR))
        self.assertGreater(luminance(theme.DISABLED_BORDER_COLOR_STR),
                           luminance(theme.BUTTON_BORDER_COLOR_STR))
        style_sheet_str = theme.toggle_button_style_sheet(
            "undo_button", False, disabled_rule_b=True)
        disabled_rule_str = style_sheet_str[
            style_sheet_str.index("#undo_button:disabled"):]
        for color_str in (theme.DISABLED_COLOR_STR,
                          theme.DISABLED_TEXT_COLOR_STR,
                          theme.DISABLED_BORDER_COLOR_STR):
            self.assertIn(color_str, disabled_rule_str)

    @covers("LLFR-00107", "LLFR-00106")
    def test_tab_and_add_button_share_tokens(self) -> None:
        """The unselected tab and "+" rules hold the same shape block.

        Inputs: none.
        Outputs: none.
        """
        style_sheet_str = theme.tab_style_sheet("tabs", "bar", "plus")
        for selector_str in ("QTabBar#bar::tab:!selected",
                             "QToolButton#plus"):
            with self.subTest(selector_str=selector_str):
                rule_start_i = style_sheet_str.index(selector_str + " {")
                rule_end_i = style_sheet_str.index("}", rule_start_i)
                self.assertIn(theme.SHARED_TAB_SHAPE_STR,
                              style_sheet_str[rule_start_i:rule_end_i])
        for token_str in (theme.TAB_BACKGROUND_COLOR_STR,
                          theme.TAB_BORDER_COLOR_STR,
                          f"{theme.TAB_CORNER_RADIUS_I}px"):
            self.assertIn(token_str, theme.SHARED_TAB_SHAPE_STR)
        self.assertIn("alignment: left", style_sheet_str)
        self.assertLess(theme.ADD_BUTTON_WIDTH_I,
                        theme.TAB_MINIMUM_TEXT_WIDTH_I
                        + 2 * theme.TAB_HORIZONTAL_PADDING_I)

    @covers("LLFR-00001", "LLFR-00107", "LLFR-00141", "HLFR-00003")
    def test_no_color_literals_outside_theme(self) -> None:
        """No view file except theme.py holds a "#rrggbb" literal.

        Inputs: none.
        Outputs: none.
        """
        offender_list = []
        for file_name_str in sorted(os.listdir(VIEW_FOLDER_STR)):
            if (not file_name_str.endswith(".py")
                    or file_name_str in COLOR_LITERAL_FILE_SET):
                continue
            path_str = os.path.join(VIEW_FOLDER_STR, file_name_str)
            for literal_str in string_literal_list(path_str):
                if re.search(COLOR_LITERAL_PATTERN_STR, literal_str):
                    offender_list.append(f"{file_name_str}: {literal_str}")
        self.assertEqual(offender_list, [])

    @covers("LLFR-00033", "LLFR-00144", "LLFR-00083", "LLFR-00143")
    def test_matplotlib_style_leaves_data_colors_alone(self) -> None:
        """The plot style sets no curve colors and no line styles.

        Inputs: none.
        Outputs: none.
        """
        for key_str in theme.MATPLOTLIB_STYLE_DICT:
            with self.subTest(key_str=key_str):
                self.assertNotIn("prop_cycle", key_str)
                self.assertFalse(key_str.startswith("lines."))
        # The requirement colors are not redefined by the theme.
        theme_color_set = {
            value.lower() for name_str, value in vars(theme).items()
            if name_str.endswith("_COLOR_STR")}
        self.assertNotIn(MARKER_COLOR_STR.lower(), theme_color_set)
        self.assertEqual(PALETTE_COLOR_TUPLE[:3],
                         ("#1f77b4", "#000000", "#d62728"))


@requires_qt
class ThemeWidgetTestCase(unittest.TestCase):
    """Checks of the theme on real widgets."""

    def setUp(self) -> None:
        """Get the shared QApplication.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()

    @covers("LLFR-00058", "HLFR-00003")
    def test_style_sheet_is_applied_to_the_application(self) -> None:
        """Creating the main window sets the theme style sheet app-wide.

        Inputs: none.
        Outputs: none.
        """
        from view.main_window import MainWindow
        main_window = MainWindow()
        self.addCleanup(main_window.deleteLater)
        self.assertEqual(self.application.styleSheet(),
                         theme.application_style_sheet())
        # A second window leaves the same style sheet in place.
        second_window = MainWindow()
        self.addCleanup(second_window.deleteLater)
        self.assertEqual(self.application.styleSheet(),
                         theme.application_style_sheet())

    @covers("LLFR-00107")
    def test_plot_panel_uses_theme_tokens(self) -> None:
        """The plot panel's tab constants are the theme's tokens.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_panel
        self.assertEqual(plot_panel.SHARED_TAB_SHAPE_STR,
                         theme.SHARED_TAB_SHAPE_STR)
        self.assertEqual(plot_panel.TAB_BACKGROUND_COLOR_STR,
                         theme.TAB_BACKGROUND_COLOR_STR)
        self.assertEqual(plot_panel.build_tab_style_sheet(),
                         theme.tab_style_sheet(
                             plot_panel.TAB_WIDGET_OBJECT_NAME_STR,
                             plot_panel.TAB_BAR_OBJECT_NAME_STR,
                             plot_panel.ADD_BUTTON_OBJECT_NAME_STR))

    @covers("LLFR-00001", "LLFR-00079")
    def test_joined_tool_buttons_show_the_active_color(self) -> None:
        """Each joined plot tool button paints the active color.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor
        from view.top_panel import TopPanel
        top_panel = TopPanel()
        self.addCleanup(top_panel.deleteLater)
        top_panel.resize(900, 60)
        top_panel.show()
        self.application.processEvents()
        segment_list = [button.segment_position_str for button in
                        top_panel.plot_tool_button_dict.values()]
        self.assertEqual(segment_list, [theme.SEGMENT_FIRST_STR,
                                        theme.SEGMENT_MIDDLE_STR,
                                        theme.SEGMENT_LAST_STR])
        for button in top_panel.plot_tool_button_dict.values():
            with self.subTest(button=button.text()):
                button.setChecked(True)
                self.application.processEvents()
                image = button.grab().toImage()
                self.assertEqual(
                    QColor(image.pixel(image.width() // 2, 4)).name(),
                    theme.ACTIVE_COLOR_STR)
                button.finish()
                self.application.processEvents()
                image = button.grab().toImage()
                self.assertEqual(
                    QColor(image.pixel(image.width() // 2, 4)).name(),
                    theme.NORMAL_COLOR_STR)
        # The tools sit side by side with no gap between them.
        button_list = list(top_panel.plot_tool_button_dict.values())
        for left_button, right_button in zip(button_list, button_list[1:]):
            self.assertEqual(left_button.geometry().right() + 1,
                             right_button.geometry().left())

    @covers("LLFR-00144", "LLFR-00037", "LLFR-00083", "LLFR-00143",
            "LLFR-00151")
    def test_plot_keeps_requirement_colors(self) -> None:
        """Curves, legend, markers and tips keep the requirement looks.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_hex
        from view.plot_widget import PlotWidget
        plot_widget = PlotWidget(1)
        self.addCleanup(plot_widget.deleteLater)
        plot_widget.resize(600, 400)
        plot_widget.show()
        self.application.processEvents()
        time_array = np.linspace(0.0, 1.0, 11)
        name_list = ["first", "second", "third"]
        plot_widget.set_curves([
            (name_str, time_array, time_array * index_i,
             PALETTE_COLOR_TUPLE[index_i], 1)
            for index_i, name_str in enumerate(name_list)])
        plot_widget.set_markers([(1, "Marker 1", 0.5)])
        plot_widget.set_pinned_tips([("second", 0.5, 0.5)])
        plot_widget.canvas.draw()
        line_color_list = [to_hex(plot_widget.curve_line_dict[name_str]
                                  .get_color())
                           for name_str in name_list]
        self.assertEqual(line_color_list, list(PALETTE_COLOR_TUPLE[:3]))
        self.assertEqual(plot_widget.legend_entry_list(),
                         list(zip(name_list, PALETTE_COLOR_TUPLE[:3])))
        line, label, time_text = plot_widget.marker_artist_tuple(1)
        self.assertEqual(to_hex(line.get_color()), MARKER_COLOR_STR)
        self.assertEqual(to_hex(label.get_color()), MARKER_COLOR_STR)
        self.assertNotEqual(line.get_linestyle(), "-")
        annotation = plot_widget.pinned_tip_annotation(0)
        self.assertEqual(
            to_hex(annotation.get_bbox_patch().get_edgecolor()),
            PALETTE_COLOR_TUPLE[1])
        self.assertEqual(annotation.arrow_patch.get_linestyle(), "--")
        # The theme's light spines and grid are in use.
        self.assertFalse(plot_widget.axes.spines["top"].get_visible())
        self.assertEqual(
            to_hex(plot_widget.axes.spines["bottom"].get_edgecolor()),
            theme.PLOT_SPINE_COLOR_STR)


if __name__ == "__main__":
    unittest.main()
