"""Tests for the rounded corners of the plots (LLFR-00890)."""

import unittest

import numpy as np

from tests.support import covers, get_qt_application, requires_qt

WIDGET_WIDTH_I = 600
WIDGET_HEIGHT_I = 400
# A pixel channel may differ by this much after antialiasing.
CHANNEL_TOLERANCE_I = 3


def pixel_name(image, x_i: int, y_i: int) -> str:
    """Return the "#rrggbb" color of one pixel of an image.

    Inputs:
        image: a QImage.
        x_i: column of the pixel.
        y_i: row of the pixel.
    Outputs: the color name.
    """
    from PyQt6.QtGui import QColor
    return QColor(image.pixel(x_i, y_i)).name()


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


@requires_qt
class RoundedPlotTest(unittest.TestCase):
    """A shown plot paints rounded corners and the signal list border."""

    def setUp(self) -> None:
        """Create and show a plot inside a tab page, with one curve.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.plot_widget import PlotWidget
        from view.tab_page import TabPage
        self.page = TabPage(1, "Tab 1")
        self.plot_widget = PlotWidget(3)
        self.page.add_plot_widget(self.plot_widget)
        self.page.resize(WIDGET_WIDTH_I, WIDGET_HEIGHT_I)
        self.page.show()
        time_array = np.linspace(0.0, 10.0, 101)
        self.plot_widget.set_curves(
            [("speed", time_array, np.sin(time_array), "#0000ff", 1)])
        self.application.processEvents()
        self.plot_widget.canvas.draw()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close and delete the page and its plot.

        Inputs: none.
        Outputs: none.
        """
        self.page.close()
        self.page.deleteLater()
        self.application.processEvents()

    def canvas_image(self):
        """Return the canvas as it is painted on screen.

        Inputs: none.
        Outputs: a QImage of the canvas.
        """
        return self.plot_widget.canvas.grab().toImage()

    @covers("LLFR-00890")
    def test_corners_show_the_plot_well(self) -> None:
        """The four corner pixels are cut away: they show the plot well
        color, not the white figure.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        image = self.canvas_image()
        last_x_i = image.width() - 1
        last_y_i = image.height() - 1
        for x_i, y_i in ((0, 0), (last_x_i, 0), (0, last_y_i),
                         (last_x_i, last_y_i)):
            with self.subTest(x=x_i, y=y_i):
                self.assertTrue(colors_close_b(
                    pixel_name(image, x_i, y_i),
                    theme.PLOT_WELL_COLOR_STR))

    @covers("LLFR-00890")
    def test_edges_have_the_signal_list_border(self) -> None:
        """The middle of each edge is drawn in the hairline border color
        of the signal list, and just inside it the figure stays white.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        image = self.canvas_image()
        middle_x_i = image.width() // 2
        middle_y_i = image.height() // 2
        border_point_list = [
            (middle_x_i, 0), (middle_x_i, image.height() - 1),
            (0, middle_y_i), (image.width() - 1, middle_y_i)]
        for x_i, y_i in border_point_list:
            with self.subTest(x=x_i, y=y_i):
                self.assertTrue(colors_close_b(
                    pixel_name(image, x_i, y_i),
                    theme.SIGNAL_LIST_BORDER_COLOR_STR))
        # The border is 1 pixel wide: the next pixel in is the figure.
        self.assertEqual(theme.PLOT_BORDER_WIDTH_I, 1)
        self.assertTrue(colors_close_b(
            pixel_name(image, middle_x_i, 1),
            theme.PLOT_BACKGROUND_COLOR_STR))

    @covers("LLFR-00890")
    def test_corner_follows_the_signal_list_radius(self) -> None:
        """Along the top edge, the corner is cut over the radius of the
        signal list: the border starts at the radius, and the first pixel
        is outside the rounding.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        image = self.canvas_image()
        radius_i = theme.SIGNAL_LIST_RADIUS_I
        self.assertEqual(theme.PLOT_CORNER_RADIUS_I, radius_i)
        self.assertGreaterEqual(radius_i, 4)
        # At the end of the curve, the top row is the straight border.
        self.assertTrue(colors_close_b(
            pixel_name(image, radius_i, 0),
            theme.SIGNAL_LIST_BORDER_COLOR_STR))
        # Inside the curve, the top row is not yet the border.
        self.assertFalse(colors_close_b(
            pixel_name(image, 1, 0), theme.SIGNAL_LIST_BORDER_COLOR_STR))

    @covers("LLFR-00890")
    def test_same_radius_and_border_as_the_signal_list(self) -> None:
        """The signal list's style sheet uses the radius, border width and
        border color that the plots paint.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        style_sheet_str = theme.application_style_sheet()
        rule_str = next(
            line_str for line_str in style_sheet_str.splitlines()
            if line_str.startswith("QListWidget#signal_list_widget {"))
        self.assertIn(
            f"border: {theme.PLOT_BORDER_WIDTH_I}px solid "
            f"{theme.PLOT_BORDER_COLOR_STR};", rule_str)
        self.assertIn(
            f"border-radius: {theme.PLOT_CORNER_RADIUS_I}px;", rule_str)

    @covers("LLFR-00890")
    def test_plot_geometry_unchanged(self) -> None:
        """The canvas still fills the whole plot widget, so the figure and
        everything it draws keep their size and position.

        Inputs: none.
        Outputs: none.
        """
        canvas = self.plot_widget.canvas
        self.assertEqual(canvas.geometry(), self.plot_widget.rect())
        self.assertEqual(int(round(self.plot_widget.figure.bbox.width)),
                         int(round(canvas.width()
                                   * canvas.device_pixel_ratio)))

    @covers("LLFR-00890", "LLFR-00133")
    def test_copied_image_keeps_square_corners(self) -> None:
        """The image of the Copy button shows the plot with its square
        white corners, and the screen gets its rounded corners back.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        from view import plot_export, theme
        page_image = plot_export.grab_page_image(self.page)
        canvas = self.plot_widget.canvas
        top_left = canvas.mapTo(self.page, QPoint(0, 0))
        self.assertTrue(colors_close_b(
            pixel_name(page_image, top_left.x(), top_left.y()),
            theme.PLOT_BACKGROUND_COLOR_STR))
        self.assertTrue(canvas.rounded_corners_b)
        self.application.processEvents()
        self.assertTrue(colors_close_b(
            pixel_name(self.canvas_image(), 0, 0),
            theme.PLOT_WELL_COLOR_STR))


if __name__ == "__main__":
    unittest.main()
