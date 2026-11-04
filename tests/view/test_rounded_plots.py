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

    @covers("LLFR-00890", "LLFR-00892")
    def test_copied_image_has_rounded_corners(self) -> None:
        """The image that the Copy button copies shows the plot with its
        rounded corners and border, and the screen keeps its rounded
        corners in the plot well color afterwards.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        from view import plot_export, theme
        page_image = plot_export.grab_page_image(self.page)
        ratio_f = page_image.devicePixelRatio()
        canvas = self.plot_widget.canvas
        top_left = canvas.mapTo(self.page, QPoint(0, 0))
        left_i = int(round(top_left.x() * ratio_f))
        top_i = int(round(top_left.y() * ratio_f))
        middle_x_i = left_i + int(canvas.width() * ratio_f) // 2
        # The corner pixel is cut away: it is neither the white figure
        # (square corners) nor the border; the top edge is the border.
        self.assertFalse(colors_close_b(
            pixel_name(page_image, left_i, top_i),
            theme.PLOT_BACKGROUND_COLOR_STR))
        self.assertTrue(colors_close_b(
            pixel_name(page_image, middle_x_i, top_i),
            theme.PLOT_BORDER_COLOR_STR))
        self.assertFalse(colors_close_b(
            pixel_name(page_image, left_i, top_i),
            theme.PLOT_BORDER_COLOR_STR))
        self.application.processEvents()
        self.assertTrue(colors_close_b(
            pixel_name(self.canvas_image(), 0, 0),
            theme.PLOT_WELL_COLOR_STR))


# A PDF image object is "/Subtype /Image".
IMAGE_OBJECT_PATTERN_BYTES = rb"/Subtype\s*/Image"
# The window color of a dark system theme.
DARK_WINDOW_COLOR_STR = "#202124"


@requires_qt
class RoundedExportTest(unittest.TestCase):
    """The PDF page and the copied image show the plots with rounded
    corners (LLFR-00891, LLFR-00892)."""

    def setUp(self) -> None:
        """Show a tab widget with one tab page that holds two plots.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QTabWidget
        from view.plot_widget import PlotWidget
        from view.tab_page import TabPage
        self.tab_widget = QTabWidget()
        self.page = TabPage(1, "Tab 1")
        self.tab_widget.addTab(self.page, "Tab 1")
        time_array = np.linspace(0.0, 10.0, 101)
        for plot_id_i in (1, 2):
            plot_widget = PlotWidget(plot_id_i)
            self.page.add_plot_widget(plot_widget)
            plot_widget.set_curves(
                [("speed", time_array, np.sin(time_array), "#0000ff", 1)])
        self.tab_widget.resize(WIDGET_WIDTH_I, 2 * WIDGET_HEIGHT_I)
        self.tab_widget.show()
        self.application.processEvents()
        for plot_widget in self.page.plot_widget_list:
            plot_widget.canvas.draw()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close and delete the tab widget.

        Inputs: none.
        Outputs: none.
        """
        self.tab_widget.close()
        self.tab_widget.deleteLater()
        self.application.processEvents()

    def canvas_rect_list(self) -> list:
        """Return the place of each plot canvas in the tab page.

        Inputs: none.
        Outputs: a list of tuples (left, top, width, height) in logical
            pixels, from top to bottom.
        """
        from PyQt6.QtCore import QPoint
        rect_list = []
        for plot_widget in self.page.plot_widget_list:
            canvas = plot_widget.canvas
            top_left = canvas.mapTo(self.page, QPoint(0, 0))
            rect_list.append((top_left.x(), top_left.y(), canvas.width(),
                              canvas.height()))
        return rect_list

    def copied_image(self, description_str: str = ""):
        """Copy the current tab as the Copy button does and read the
        image back from the clipboard.

        Inputs:
            description_str: the description of the data files, shown
                in a strip above the plots (LLFR-00972); "" for none.
        Outputs: the QImage on the clipboard.
        """
        from PyQt6.QtWidgets import QApplication
        from view import plot_export
        copied_b, reason_str = plot_export.copy_current_tab_image(
            self.tab_widget, description_str)
        self.assertTrue(copied_b, reason_str)
        return QApplication.clipboard().image()

    def use_dark_page_palette(self) -> None:
        """Give the tab page a dark window color, as in a dark system
        theme, and repaint it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor, QPalette
        palette = self.page.palette()
        palette.setColor(QPalette.ColorRole.Window,
                         QColor(DARK_WINDOW_COLOR_STR))
        self.page.setPalette(palette)
        self.application.processEvents()

    def assert_copied_corners_match_the_gap(
            self, description_str: str = "") -> str:
        """Copy the tab and check that the four corner pixels of each plot
        have the color of the image background between the two plots.

        Inputs:
            description_str: the description of the data files of the
                strip above the plots (LLFR-00972); "" for no strip.
        Outputs: the "#rrggbb" color of the gap.
        """
        image = self.copied_image(description_str)
        ratio_f = image.width() / max(self.page.width(), 1)
        # LLFR-00972: the strip, when there is one, is added above the
        # plots, so they all start lower by its height.
        strip_i = 0
        if description_str:
            strip_i = image.height() - int(round(self.page.height()
                                                 * ratio_f))
            self.assertGreater(strip_i, 0)
        first_rect, second_rect = self.canvas_rect_list()
        gap_y_f = (first_rect[1] + first_rect[3] + second_rect[1]) / 2.0
        background_str = pixel_name(
            image, int(image.width() / 2), int(gap_y_f * ratio_f) + strip_i)
        for left_i, top_i, width_i, height_i in (first_rect, second_rect):
            first_x_i = int(round(left_i * ratio_f))
            first_y_i = int(round(top_i * ratio_f)) + strip_i
            last_x_i = int(round((left_i + width_i) * ratio_f)) - 1
            last_y_i = (int(round((top_i + height_i) * ratio_f)) - 1
                        + strip_i)
            for x_i, y_i in ((first_x_i, first_y_i), (last_x_i, first_y_i),
                             (first_x_i, last_y_i), (last_x_i, last_y_i)):
                with self.subTest(x=x_i, y=y_i):
                    self.assertTrue(colors_close_b(
                        pixel_name(image, x_i, y_i), background_str))
        return background_str

    @covers("LLFR-00892", "LLFR-00133")
    def test_copied_corners_show_the_image_background(self) -> None:
        """In the copied image, the four corner pixels of each plot have
        the color of the image background between the two plots.

        Inputs: none.
        Outputs: none.
        """
        self.assert_copied_corners_match_the_gap()

    @covers("LLFR-00892", "LLFR-00133")
    def test_copied_corners_with_a_dark_palette(self) -> None:
        """With a dark window color, the corners of the copied plots are
        dark like the image background between the plots.

        Inputs: none.
        Outputs: none.
        """
        self.use_dark_page_palette()
        background_str = self.assert_copied_corners_match_the_gap()
        self.assertTrue(colors_close_b(background_str,
                                       DARK_WINDOW_COLOR_STR))

    @covers("LLFR-00892", "LLFR-00972", "LLFR-00133")
    def test_copied_corners_below_the_description_strip(self) -> None:
        """With the strip of the data files above the plots, each plot
        keeps its rounded corners, in the image background color, below
        the strip.

        Inputs: none.
        Outputs: none.
        """
        self.assert_copied_corners_match_the_gap(
            "file1 = run_A.csv, file2 = run_B.mat")

    @covers("LLFR-00892", "LLFR-00133")
    def test_copied_plots_have_the_screen_border(self) -> None:
        """In the copied image, each plot has the 1 pixel border of the
        screen, which starts at the corner radius, and the image keeps
        the size of the tab page.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        image = self.copied_image()
        ratio_f = image.width() / max(self.page.width(), 1)
        self.assertAlmostEqual(image.height() / ratio_f,
                               self.page.height(), delta=1)
        radius_i = theme.PLOT_CORNER_RADIUS_I
        for left_i, top_i, width_i, height_i in self.canvas_rect_list():
            middle_x_i = int(round((left_i + width_i / 2.0) * ratio_f))
            top_row_i = int(round(top_i * ratio_f))
            # The middle of the top edge is the border, the next pixel
            # in is the white figure.
            self.assertTrue(colors_close_b(
                pixel_name(image, middle_x_i, top_row_i),
                theme.PLOT_BORDER_COLOR_STR))
            self.assertTrue(colors_close_b(
                pixel_name(image, middle_x_i,
                           top_row_i + int(round(ratio_f))),
                theme.PLOT_BACKGROUND_COLOR_STR))
            # The straight border starts at the radius.
            self.assertTrue(colors_close_b(
                pixel_name(image, int(round((left_i + radius_i) * ratio_f)),
                           top_row_i),
                theme.PLOT_BORDER_COLOR_STR))
        # The screen keeps its corners in the plot well color.
        self.application.processEvents()
        canvas_image = self.page.plot_widget_list[0].canvas.grab().toImage()
        self.assertTrue(colors_close_b(pixel_name(canvas_image, 0, 0),
                                       theme.PLOT_WELL_COLOR_STR))

    def rendered_pdf_page(self) -> tuple:
        """Paint the PDF page of the tab on an image of the page's size,
        with the same painting code as the PDF writer.

        Inputs: none.
        Outputs: a tuple (QImage of the page, list of (QRectF, QImage)
            of the plots drawn on it).
        """
        from PyQt6.QtCore import QBuffer, QIODevice
        from PyQt6.QtGui import QColor, QImage, QPainter
        from view import plot_export
        snapshot_list = plot_export.grab_exportable_images(self.tab_widget)
        self.assertEqual(len(snapshot_list), 1)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        writer = plot_export.build_pdf_writer(buffer)
        page_width_i = writer.width()
        page_height_i = writer.height()
        buffer.close()
        page_image = QImage(page_width_i, page_height_i,
                            QImage.Format.Format_ARGB32)
        page_image.fill(QColor("#ffffff"))
        painter = QPainter(page_image)
        try:
            drawn_list = plot_export.paint_pdf_page(
                painter, snapshot_list[0], page_width_i, page_height_i)
        finally:
            painter.end()
        return (page_image, drawn_list)

    def assert_pdf_corners_show_the_paper(self) -> str:
        """Paint the PDF page and check that the four corners of each plot
        have the color of the paper just above the first plot, in the gap
        below the tab name.

        Inputs: none.
        Outputs: the "#rrggbb" color of the page between the two plots.
        """
        from view import theme
        page_image, drawn_list = self.rendered_pdf_page()
        self.assertEqual(len(drawn_list), 2)
        first_rect = drawn_list[0][0]
        second_rect = drawn_list[1][0]
        paper_str = pixel_name(page_image, int(first_rect.left()) + 2,
                               int(first_rect.top()) - 3)
        self.assertTrue(colors_close_b(paper_str,
                                       theme.PDF_PAPER_COLOR_STR))
        for target_rect, _ in drawn_list:
            first_x_i = int(target_rect.left()) + 2
            first_y_i = int(target_rect.top()) + 2
            last_x_i = int(target_rect.right()) - 2
            last_y_i = int(target_rect.bottom()) - 2
            for x_i, y_i in ((first_x_i, first_y_i), (last_x_i, first_y_i),
                             (first_x_i, last_y_i), (last_x_i, last_y_i)):
                with self.subTest(x=x_i, y=y_i):
                    self.assertTrue(colors_close_b(
                        pixel_name(page_image, x_i, y_i), paper_str))
        gap_y_f = (first_rect.bottom() + second_rect.top()) / 2.0
        return pixel_name(page_image, int(first_rect.center().x()),
                          int(gap_y_f))

    @covers("LLFR-00891", "LLFR-00129")
    def test_pdf_corners_show_the_page_background(self) -> None:
        """On the PDF page, the corners of each plot have the color of the
        white paper next to the plot.

        Inputs: none.
        Outputs: none.
        """
        self.assert_pdf_corners_show_the_paper()

    @covers("LLFR-00891", "LLFR-00129")
    def test_pdf_corners_with_a_dark_palette(self) -> None:
        """With a dark window color, the gap between the plots on the PDF
        page is dark, and the corners of the plots are still the white
        paper.

        Inputs: none.
        Outputs: none.
        """
        self.use_dark_page_palette()
        gap_str = self.assert_pdf_corners_show_the_paper()
        self.assertTrue(colors_close_b(gap_str, DARK_WINDOW_COLOR_STR))

    @covers("LLFR-00891", "LLFR-00129")
    def test_pdf_border_is_scaled_to_the_page(self) -> None:
        """On the PDF page, the border and the radius are those of the
        screen, scaled like the plot: the border is as many page pixels
        wide as the scale, and the straight border starts at the scaled
        radius.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        page_image, drawn_list = self.rendered_pdf_page()
        canvas_width_i = self.canvas_rect_list()[0][2]
        for target_rect, _ in drawn_list:
            scale_f = target_rect.width() / canvas_width_i
            self.assertGreater(scale_f, 2.0)
            border_f = theme.PLOT_BORDER_WIDTH_I * scale_f
            radius_f = theme.PLOT_CORNER_RADIUS_I * scale_f
            middle_x_i = int(target_rect.center().x())
            border_y_i = int(target_rect.top() + border_f / 2.0)
            self.assertTrue(colors_close_b(
                pixel_name(page_image, middle_x_i, border_y_i),
                theme.PLOT_BORDER_COLOR_STR))
            # Just inside the scaled border is the white figure.
            self.assertTrue(colors_close_b(
                pixel_name(page_image, middle_x_i,
                           int(target_rect.top() + 2.0 * border_f + 1.0)),
                theme.PLOT_BACKGROUND_COLOR_STR))
            # At the scaled radius the top row is the straight border;
            # halfway along the curve it is not yet.
            self.assertTrue(colors_close_b(
                pixel_name(page_image,
                           int(target_rect.left() + radius_f + 1.0),
                           border_y_i),
                theme.PLOT_BORDER_COLOR_STR))
            self.assertFalse(colors_close_b(
                pixel_name(page_image,
                           int(target_rect.left() + radius_f / 4.0),
                           border_y_i),
                theme.PLOT_BORDER_COLOR_STR))

    @covers("LLFR-00891", "LLFR-00129")
    def test_pdf_corners_add_no_image(self) -> None:
        """The corners and borders are vector paths: the PDF holds as many
        images as it does when they are not painted.

        Inputs: none.
        Outputs: none.
        """
        import re
        from unittest import mock
        from view import plot_export
        snapshot_list = plot_export.grab_exportable_images(self.tab_widget)
        rounded_bytes = plot_export.build_pdf_bytes(snapshot_list)
        with mock.patch.object(plot_export, "paint_rounded_frame",
                               new=lambda *argument_tuple: None):
            square_bytes = plot_export.build_pdf_bytes(snapshot_list)
        self.assertEqual(
            len(re.findall(IMAGE_OBJECT_PATTERN_BYTES, rounded_bytes)),
            len(re.findall(IMAGE_OBJECT_PATTERN_BYTES, square_bytes)))
        self.assertNotEqual(rounded_bytes, square_bytes)


if __name__ == "__main__":
    unittest.main()
