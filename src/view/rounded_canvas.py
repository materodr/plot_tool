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
are unchanged, and so are the figure images of the PDF export
(LLFR-00129), which matplotlib renders without Qt. The copied image
(LLFR-00133) is grabbed with the corners turned off
(``square_corners``), so it keeps its square plots too.
"""

from contextlib import contextmanager

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen

from view import theme


def rounded_rectangle_path(width_f: float, height_f: float,
                           radius_f: float):
    """Return the rounded rectangle that fills a widget of a given size.

    Inputs:
        width_f: width of the widget, in logical pixels.
        height_f: height of the widget, in logical pixels.
        radius_f: corner radius, in logical pixels.
    Outputs: a QPainterPath of the rectangle (0, 0, width, height) with
        corners rounded by the radius, limited to half the shorter side.
    """
    # LLFR-00890: the radius of the signal list's corners.
    radius_f = max(0.0, min(radius_f, width_f / 2.0, height_f / 2.0))
    path = QPainterPath()
    path.addRoundedRect(QRectF(0.0, 0.0, width_f, height_f),
                        radius_f, radius_f)
    return path


def corner_path(width_f: float, height_f: float, radius_f: float):
    """Return the four corner pieces outside the rounded rectangle.

    Inputs:
        width_f: width of the widget, in logical pixels.
        height_f: height of the widget, in logical pixels.
        radius_f: corner radius, in logical pixels.
    Outputs: a QPainterPath of the parts of the widget's rectangle that
        are outside rounded_rectangle_path.
    """
    # LLFR-00890: the corners show the plot well, as if cut away.
    full_path = QPainterPath()
    full_path.addRect(QRectF(0.0, 0.0, width_f, height_f))
    return full_path.subtracted(
        rounded_rectangle_path(width_f, height_f, radius_f))


def paint_rounded_frame(painter, width_f: float, height_f: float) -> None:
    """Paint the cut corners and the border of a rounded plot.

    Inputs:
        painter: an active QPainter on the canvas.
        width_f: width of the canvas, in logical pixels.
        height_f: height of the canvas, in logical pixels.
    Outputs: none. The corners outside the rounded rectangle are filled
        with the plot well color, and the border is stroked inside the
        rectangle, both antialiased.
    """
    # LLFR-00890: same radius, border width and border color as the
    # signal list.
    radius_f = float(theme.PLOT_CORNER_RADIUS_I)
    border_width_f = float(theme.PLOT_BORDER_WIDTH_I)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.fillPath(corner_path(width_f, height_f, radius_f),
                     QColor(theme.PLOT_CORNER_COLOR_STR))
    if border_width_f <= 0.0:
        return
    # LLFR-00890: the pen is centred on the path, so the border path is
    # moved in by half the width to keep the whole border inside.
    half_width_f = border_width_f / 2.0
    border_path = QPainterPath()
    border_path.addRoundedRect(
        QRectF(half_width_f, half_width_f,
               max(width_f - border_width_f, 0.0),
               max(height_f - border_width_f, 0.0)),
        max(radius_f - half_width_f, 0.0),
        max(radius_f - half_width_f, 0.0))
    pen = QPen(QColor(theme.PLOT_BORDER_COLOR_STR))
    pen.setWidthF(border_width_f)
    painter.setPen(pen)
    painter.drawPath(border_path)


class RoundedFigureCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas of a plot, shown with rounded corners.

    Inputs:
        figure: the matplotlib Figure to show.
    Attributes:
        rounded_corners_b: True while the corners and the border are
            painted over the figure (LLFR-00890); False while the copied
            image is grabbed (square_corners).
    """

    def __init__(self, figure) -> None:
        """Create the canvas of a figure.

        Inputs:
            figure: the matplotlib Figure to show.
        Outputs: none.
        """
        super().__init__(figure)
        # LLFR-00890: the plot is shown with rounded corners.
        self.rounded_corners_b = True

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
        if not self.rounded_corners_b:
            return
        painter = QPainter(self)
        try:
            paint_rounded_frame(painter, float(self.width()),
                                float(self.height()))
        finally:
            painter.end()


@contextmanager
def square_corners(canvas_list: list):
    """Paint the given canvases with square corners inside the block.

    Inputs:
        canvas_list: canvases; those that are not RoundedFigureCanvas
            are left alone.
    Outputs: a context manager. Inside it the canvases paint no corners
        and no border; afterwards they paint them again and are
        repainted.
    """
    # LLFR-00890, LLFR-00133: the copied image keeps its square plots.
    rounded_list = [canvas for canvas in canvas_list
                    if getattr(canvas, "rounded_corners_b", False)]
    for canvas in rounded_list:
        canvas.rounded_corners_b = False
    try:
        yield
    finally:
        for canvas in rounded_list:
            canvas.rounded_corners_b = True
            canvas.update()
