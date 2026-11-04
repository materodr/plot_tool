"""Plot canvas with rounded corners, like the signal list (LLFR-00890).

A matplotlib canvas paints its whole rectangle, so a style sheet cannot
round it. This canvas lets matplotlib paint as usual, then paints, on
top, the four corners outside a rounded rectangle in the color of the
plot well behind the plots, and a hairline border along the rounded
rectangle. The radius, border width and border color are those of the
signal list (theme.PLOT_CORNER_RADIUS_I, theme.PLOT_BORDER_WIDTH_I,
theme.PLOT_BORDER_COLOR_STR).

Only Qt paints the corners: the figure, its size and the position of
everything it draws (curves, legend, axes, labels, markers, data tips)
are unchanged.

The copied image (LLFR-00892) is grabbed with the corners painted in the
background color of the grabbed tab page (``corners_in_color``), so they
match the image around the plots. The PDF export (LLFR-00891) draws each
plot's matplotlib image, which Qt never paints, and then paints the same
corners and border over it as vector paths with ``paint_rounded_frame``,
scaled to the page.
"""

from contextlib import contextmanager

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen

from view import theme


def rounded_rectangle_path(frame_rect, radius_f: float):
    """Return the rounded rectangle that fills a rectangle.

    Inputs:
        frame_rect: QRectF of the plot, in the painter's coordinates.
        radius_f: corner radius, in the painter's coordinates.
    Outputs: a QPainterPath of the rectangle with corners rounded by the
        radius, limited to half the shorter side.
    """
    # LLFR-00890, LLFR-00891, LLFR-00892: the radius of the signal
    # list's corners.
    radius_f = max(0.0, min(radius_f, frame_rect.width() / 2.0,
                            frame_rect.height() / 2.0))
    path = QPainterPath()
    path.addRoundedRect(QRectF(frame_rect), radius_f, radius_f)
    return path


def corner_path(frame_rect, radius_f: float):
    """Return the four corner pieces outside the rounded rectangle.

    Inputs:
        frame_rect: QRectF of the plot, in the painter's coordinates.
        radius_f: corner radius, in the painter's coordinates.
    Outputs: a QPainterPath of the parts of the rectangle that are
        outside rounded_rectangle_path.
    """
    # LLFR-00890: the corners show the background, as if cut away.
    full_path = QPainterPath()
    full_path.addRect(QRectF(frame_rect))
    return full_path.subtracted(rounded_rectangle_path(frame_rect, radius_f))


def paint_rounded_frame(painter, frame_rect, scale_f: float = 1.0,
                        corner_color_str: str = theme.PLOT_CORNER_COLOR_STR
                        ) -> None:
    """Paint the cut corners and the border of a rounded plot.

    Inputs:
        painter: an active QPainter on the canvas, an image or a PDF.
        frame_rect: QRectF of the plot, in the painter's coordinates.
        scale_f: painter units per logical screen pixel; 1 on screen,
            more on a PDF page, so the radius and the border width keep
            their on-screen share of the plot.
        corner_color_str: color shown by the corners outside the
            rounding: the background behind the plot.
    Outputs: none. The corners outside the rounded rectangle are filled
        with the corner color, and the border is stroked inside the
        rectangle, both antialiased, as vector paths. The painter's
        state is restored afterwards.
    """
    # LLFR-00890, LLFR-00891, LLFR-00892: same radius, border width and
    # border color as the signal list, scaled to the target.
    radius_f = float(theme.PLOT_CORNER_RADIUS_I) * scale_f
    border_width_f = float(theme.PLOT_BORDER_WIDTH_I) * scale_f
    painter.save()
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillPath(corner_path(frame_rect, radius_f),
                         QColor(corner_color_str))
        if border_width_f <= 0.0:
            return
        # LLFR-00890: the pen is centred on the path, so the border path
        # is moved in by half the width to keep the whole border inside.
        half_width_f = border_width_f / 2.0
        inner_radius_f = max(radius_f - half_width_f, 0.0)
        border_path = QPainterPath()
        border_path.addRoundedRect(
            QRectF(frame_rect.x() + half_width_f,
                   frame_rect.y() + half_width_f,
                   max(frame_rect.width() - border_width_f, 0.0),
                   max(frame_rect.height() - border_width_f, 0.0)),
            inner_radius_f, inner_radius_f)
        pen = QPen(QColor(theme.PLOT_BORDER_COLOR_STR))
        pen.setWidthF(border_width_f)
        painter.setPen(pen)
        painter.drawPath(border_path)
    finally:
        painter.restore()


class RoundedFigureCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas of a plot, shown with rounded corners.

    Inputs:
        figure: the matplotlib Figure to show.
    Attributes:
        corner_color_str: color of the corners outside the rounding
            (LLFR-00890): the plot well on screen, the tab page's
            background while the page is grabbed (corners_in_color).
    """

    def __init__(self, figure) -> None:
        """Create the canvas of a figure.

        Inputs:
            figure: the matplotlib Figure to show.
        Outputs: none.
        """
        super().__init__(figure)
        # LLFR-00890: the corners show the plot well behind the plots.
        self.corner_color_str = theme.PLOT_CORNER_COLOR_STR

    def paintEvent(self, event) -> None:
        """Paint the figure, then the rounded corners and the border.

        Inputs:
            event: the QPaintEvent. Qt clips the painting to its region,
                so a blit of part of the figure repaints only the
                corners inside that part.
        Outputs: none.
        """
        # LLFR-00890: matplotlib paints the figure as before.
        super().paintEvent(event)
        painter = QPainter(self)
        try:
            paint_rounded_frame(
                painter, QRectF(0.0, 0.0, float(self.width()),
                                float(self.height())),
                1.0, self.corner_color_str)
        finally:
            painter.end()


@contextmanager
def corners_in_color(canvas_list: list, corner_color_str: str):
    """Paint the corners of the given canvases in a color inside a block.

    Inputs:
        canvas_list: canvases; those that are not RoundedFigureCanvas
            are left alone.
        corner_color_str: color of the corners inside the block.
    Outputs: a context manager. Inside it the canvases paint their
        corners in the given color; afterwards they paint them in the
        plot well color again and are repainted.
    """
    # LLFR-00892: in the copied image the corners show the background of
    # the image around the plots.
    rounded_list = [canvas for canvas in canvas_list
                    if hasattr(canvas, "corner_color_str")]
    for canvas in rounded_list:
        canvas.corner_color_str = corner_color_str
    try:
        yield
    finally:
        for canvas in rounded_list:
            canvas.corner_color_str = theme.PLOT_CORNER_COLOR_STR
            canvas.update()
