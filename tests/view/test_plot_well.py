"""Tests for the plot container of the plot panel (HLFR-00001).

Covers LLFR-00893: the container that holds the plots below the tab row
(the plot well, the pane of the tab widget) has the rounded corners,
border width and border color of the signal list, with its top-left
corner square where the first tab joins it; and LLFR-00894: the top edge
of the signal list is at the height of the top edge of that container,
at any window size and panel widths. The checks read the pixels of a
real, shown MainWindow with the real controllers. No modal dialog or
menu is ever opened.
"""

import unittest

import numpy as np

from tests.support import covers, get_qt_application, requires_qt

# A pixel channel may differ by this much after antialiasing.
CHANNEL_TOLERANCE_I = 3
# Window sizes (width, height) of the checks.
WINDOW_SIZE_LIST = [(1200, 800), (800, 560)]
# Rounds of Qt event processing allowed for the layouts to settle.
SETTLE_ROUNDS_I = 30


def colors_close_b(first_str: str, second_str: str) -> bool:
    """Tell whether two "#rrggbb" colors differ by at most the tolerance.

    Inputs:
        first_str: one color.
        second_str: the other color.
    Outputs: True when every channel differs by at most
        CHANNEL_TOLERANCE_I.
    """
    return all(
        abs(int(first_str[start_i:start_i + 2], 16)
            - int(second_str[start_i:start_i + 2], 16))
        <= CHANNEL_TOLERANCE_I
        for start_i in (1, 3, 5))


class PlotWellStyleTest(unittest.TestCase):
    """The style sheet gives the plot well the signal list's corners."""

    @covers("LLFR-00893", "LLFR-00107")
    def test_well_rule_uses_the_signal_list_tokens(self) -> None:
        """The pane rule holds the signal list's border and radius on
        three corners, a square top-left corner, and the tab and "+"
        rules keep their shared shape block.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        self.assertEqual(theme.PLOT_WELL_RADIUS_I,
                         theme.SIGNAL_LIST_RADIUS_I)
        self.assertEqual(theme.PLOT_WELL_BORDER_WIDTH_I,
                         theme.SIGNAL_LIST_BORDER_WIDTH_I)
        self.assertEqual(theme.PLOT_WELL_BORDER_COLOR_STR,
                         theme.SIGNAL_LIST_BORDER_COLOR_STR)
        style_sheet_str = theme.tab_style_sheet("tabs", "bar", "plus")
        rule_start_i = style_sheet_str.index("QTabWidget#tabs::pane {")
        rule_str = style_sheet_str[
            rule_start_i:style_sheet_str.index("}", rule_start_i)]
        radius_str = f"{theme.SIGNAL_LIST_RADIUS_I}px"
        for value_str in (
                f"border: {theme.SIGNAL_LIST_BORDER_WIDTH_I}px solid "
                f"{theme.SIGNAL_LIST_BORDER_COLOR_STR}",
                "border-top-left-radius: 0px",
                f"border-top-right-radius: {radius_str}",
                f"border-bottom-left-radius: {radius_str}",
                f"border-bottom-right-radius: {radius_str}"):
            with self.subTest(value_str=value_str):
                self.assertIn(value_str, rule_str)
        for selector_str in ("QTabBar#bar::tab:!selected",
                             "QToolButton#plus"):
            with self.subTest(selector_str=selector_str):
                start_i = style_sheet_str.index(selector_str + " {")
                self.assertIn(theme.SHARED_TAB_SHAPE_STR, style_sheet_str[
                    start_i:style_sheet_str.index("}", start_i)])


@requires_qt
class PlotWellViewTest(unittest.TestCase):
    """The shown plot well is rounded and level with the signal list."""

    def setUp(self) -> None:
        """Create and show a window with a file and one plot.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from controller.main_controller import MainController
        from model.signal_file import SignalFile
        from view.main_window import MainWindow
        self.main_window = MainWindow()
        self.main_window.resize(*WINDOW_SIZE_LIST[0])
        self.controller = MainController(self.main_window)
        time_array = np.linspace(0.0, 4.0, 41)
        self.plot_controller = self.controller.plot_controller
        self.plot_controller.on_file_opened(SignalFile("memory.csv", {
            "Time": time_array, "speed": time_array * 2.0}), False)
        self.main_window.show()
        self.settle()
        self.plot_controller.on_signal_double_clicked("speed")
        self.settle()

    def tearDown(self) -> None:
        """Close the window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def settle(self) -> None:
        """Let Qt run the pending layouts, resizes and timers.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(SETTLE_ROUNDS_I):
            self.application.processEvents()

    def well_rect_in_window(self):
        """Return the plot well's rectangle in window coordinates.

        Inputs: none.
        Outputs: a QRect of the pane, border included.
        """
        tab_widget = self.main_window.plot_panel.tab_widget
        pane_rect = tab_widget.pane_rect()
        return pane_rect.translated(
            tab_widget.mapTo(self.main_window, pane_rect.topLeft())
            - pane_rect.topLeft())

    def window_pixel_reader(self):
        """Return a function that reads a pixel of the grabbed window.

        Inputs: none.
        Outputs: a function (x_i, y_i) -> "#rrggbb", in window
            coordinates.
        """
        image = self.main_window.grab().toImage()
        ratio_f = image.devicePixelRatio()

        def pixel_name(x_i: int, y_i: int) -> str:
            """Return the color name of one pixel of the window.

            Inputs:
                x_i, y_i: the point, in window coordinates.
            Outputs: the "#rrggbb" name of the pixel.
            """
            return image.pixelColor(int(x_i * ratio_f),
                                    int(y_i * ratio_f)).name()
        return pixel_name

    def global_top_y(self, widget, local_y_i: int = 0) -> int:
        """Return the screen y of a line of a widget.

        Inputs:
            widget: a QWidget.
            local_y_i: the line's y in the widget's coordinates.
        Outputs: the global y, in pixels.
        """
        from PyQt6.QtCore import QPoint
        return int(widget.mapToGlobal(QPoint(0, local_y_i)).y())

    @covers("LLFR-00893", "HLFR-00001")
    def test_corner_pixels_of_the_well(self) -> None:
        """Top-right, bottom-left and bottom-right corners are cut away
        over the signal list radius and show the window; the top-left
        corner is square; the edges have the signal list's border.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        well_rect = self.well_rect_in_window()
        self.assertGreater(well_rect.width(), 4 * theme.PLOT_WELL_RADIUS_I)
        pixel_name = self.window_pixel_reader()
        window_str = theme.WINDOW_COLOR_STR
        border_str = theme.SIGNAL_LIST_BORDER_COLOR_STR
        radius_i = theme.SIGNAL_LIST_RADIUS_I
        left_i = well_rect.left()
        right_i = well_rect.right()
        top_i = well_rect.top()
        bottom_i = well_rect.bottom()
        # Rounded corners: the corner pixel and its neighbour along the
        # edge are outside the rounding; past the radius is the border.
        rounded_list = [
            ((right_i, top_i), (right_i, top_i + 1),
             (right_i, top_i + radius_i + 1)),
            ((left_i, bottom_i), (left_i, bottom_i - 1),
             (left_i, bottom_i - radius_i - 1)),
            ((right_i, bottom_i), (right_i, bottom_i - 1),
             (right_i, bottom_i - radius_i - 1))]
        for corner_tuple, beside_tuple, border_tuple in rounded_list:
            with self.subTest(corner=corner_tuple):
                self.assertTrue(colors_close_b(
                    pixel_name(*corner_tuple), window_str))
                self.assertTrue(colors_close_b(
                    pixel_name(*beside_tuple), window_str))
                self.assertTrue(colors_close_b(
                    pixel_name(*border_tuple), border_str))
        # Square top-left corner, under the first tab: the left border
        # starts right below the tab row.
        for offset_i in (1, 2):
            with self.subTest(top_left_offset_i=offset_i):
                self.assertTrue(colors_close_b(
                    pixel_name(left_i, top_i + offset_i), border_str))
        # The middle of each edge has the 1 pixel border of the signal
        # list, with the plot well right inside it.
        self.assertEqual(theme.PLOT_WELL_BORDER_WIDTH_I, 1)
        middle_x_i = (left_i + right_i) // 2
        middle_y_i = (top_i + bottom_i) // 2
        for edge_tuple, inside_tuple in (
                ((right_i, middle_y_i), (right_i - 1, middle_y_i)),
                ((left_i, middle_y_i), (left_i + 1, middle_y_i)),
                ((middle_x_i, bottom_i), (middle_x_i, bottom_i - 1))):
            with self.subTest(edge=edge_tuple):
                self.assertTrue(colors_close_b(
                    pixel_name(*edge_tuple), border_str))
                self.assertTrue(colors_close_b(
                    pixel_name(*inside_tuple), theme.PLOT_WELL_COLOR_STR))
        # The signal list box has the same cut corner.
        list_widget = self.main_window.signal_list_panel.signal_list_widget
        list_corner = list_widget.mapTo(self.main_window,
                                        list_widget.rect().topRight())
        self.assertTrue(colors_close_b(
            pixel_name(list_corner.x(), list_corner.y()), window_str))

    @covers("LLFR-00893", "LLFR-00890")
    def test_plot_stays_inside_the_well_border(self) -> None:
        """The rounded plot is kept off the well's border and corners.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        tab_widget = self.main_window.plot_panel.tab_widget
        plot_widget = tab_widget.currentWidget().plot_widget_list[0]
        pane_rect = tab_widget.pane_rect()
        plot_rect = plot_widget.rect().translated(
            plot_widget.mapTo(tab_widget, plot_widget.rect().topLeft()))
        inset_i = theme.PLOT_WELL_BORDER_WIDTH_I
        self.assertTrue(pane_rect.adjusted(
            inset_i, inset_i, -inset_i, -inset_i).contains(plot_rect))
        self.assertGreaterEqual(plot_rect.left() - pane_rect.left(),
                                inset_i + theme.PLOT_WELL_PADDING_I)
        self.assertGreaterEqual(pane_rect.right() - plot_rect.right(),
                                inset_i + theme.PLOT_WELL_PADDING_I)

    @covers("LLFR-00894", "LLFR-00424", "HLFR-00001", "HLFR-00026")
    def test_list_top_level_with_the_well_top(self) -> None:
        """At two window sizes and two panel widths, the signal list box
        starts at the global y of the plot well's top edge, the edges
        are drawn there, and the search box still ends with the plot.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        window = self.main_window
        tab_widget = window.plot_panel.tab_widget
        list_widget = window.signal_list_panel.signal_list_widget
        search_box = window.signal_list_panel.search_box
        plot_widget = tab_widget.currentWidget().plot_widget_list[0]
        for width_i, height_i in WINDOW_SIZE_LIST:
            window.resize(width_i, height_i)
            self.settle()
            total_width_i = sum(window.lower_splitter.sizes())
            for list_share_f in (0.25, 0.4):
                list_width_i = int(total_width_i * list_share_f)
                window.lower_splitter.setSizes(
                    [total_width_i - list_width_i, list_width_i])
                self.settle()
                with self.subTest(size=(width_i, height_i),
                                  list_share_f=list_share_f):
                    well_top_i = self.global_top_y(
                        tab_widget, tab_widget.pane_rect().top())
                    self.assertEqual(self.global_top_y(list_widget),
                                     well_top_i)
                    # The visible edges: a border row with the window
                    # above it, on both panels.
                    pixel_name = self.window_pixel_reader()
                    well_rect = self.well_rect_in_window()
                    edge_x_i = (well_rect.right()
                                - theme.PLOT_WELL_RADIUS_I - 4)
                    self.assertTrue(colors_close_b(
                        pixel_name(edge_x_i, well_rect.top()),
                        theme.SIGNAL_LIST_BORDER_COLOR_STR))
                    self.assertTrue(colors_close_b(
                        pixel_name(edge_x_i, well_rect.top() - 1),
                        theme.WINDOW_COLOR_STR))
                    list_top_left = list_widget.mapTo(
                        window, list_widget.rect().topLeft())
                    list_x_i = list_top_left.x() + list_widget.width() // 2
                    self.assertEqual(list_top_left.y(), well_rect.top())
                    self.assertFalse(colors_close_b(
                        pixel_name(list_x_i, list_top_left.y()),
                        theme.WINDOW_COLOR_STR))
                    self.assertTrue(colors_close_b(
                        pixel_name(list_x_i, list_top_left.y() - 1),
                        theme.WINDOW_COLOR_STR))
                    # LLFR-00424: the bottom alignment still holds.
                    self.assertLessEqual(abs(
                        self.global_top_y(search_box, search_box.height())
                        - self.global_top_y(plot_widget,
                                            plot_widget.height())), 1)


if __name__ == "__main__":
    unittest.main()
