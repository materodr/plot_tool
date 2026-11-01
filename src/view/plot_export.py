"""Export of the plots: tabs to a PDF file, current tab to the clipboard.

HLFR-00038, HLFR-00039. Both use an image of a tab page taken with
``QWidget.grab``, so the PDF pages and the copied image show the plots
exactly as on screen: time range, curves, legends above the axes, grid,
vertical markers and pinned tips (LLFR-00129, LLFR-00133).

PDF layout (LLFR-00129): one landscape A4 page per tab that holds at
least one plot, in tab order, with a margin of PAGE_MARGIN_MM_F on each
side. The tab name is written at the top of the page in bold, and the
image of the tab fills the rest of the page, scaled to fit and keeping
its aspect ratio. A tab that is not the current one is shown for a
moment, so that it is laid out at the size of the visible tab page
before its image is taken; the current tab is selected again
afterwards, even after an error.

Print quality (LLFR-00129): the screen grab only gives the page its
layout and background. Each plot's matplotlib figure is rendered again,
at the same size in inches and so with the same look, at a resolution
that gives at least TARGET_FIGURE_DPI_F dots per inch on the page, and
drawn over its place in the grab.

The PDF is made in memory and then written with
``file_writing.write_file_safely``, which never damages a file that was
already there (LLFR-00131).
"""

import io

from PyQt6.QtCore import (
    QBuffer, QIODevice, QMarginsF, QPoint, QPointF, QRectF, Qt)
from PyQt6.QtGui import (
    QFont, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter)
from PyQt6.QtWidgets import QApplication

from view.file_writing import write_file_safely
from view.tab_page import TabPage

# LLFR-00129: page size, orientation, margins and resolution of the PDF.
PAGE_MARGIN_MM_F = 10.0
PDF_RESOLUTION_I = 300
PDF_TITLE_STR = "plot_tool plots"
TITLE_FONT_POINT_SIZE_F = 14.0
# LLFR-00129: space between the tab name and the plots, in title line
# heights.
TITLE_GAP_RATIO_F = 0.5
# LLFR-00129: width of the paintable area of a landscape A4 page.
MILLIMETERS_PER_INCH_F = 25.4
A4_LONG_SIDE_MM_F = 297.0
PAINT_WIDTH_INCHES_F = ((A4_LONG_SIDE_MM_F - 2.0 * PAGE_MARGIN_MM_F)
                        / MILLIMETERS_PER_INCH_F)
# LLFR-00129: resolution of the plots on the page, and an upper bound
# that keeps the images small for very narrow tabs.
TARGET_FIGURE_DPI_F = 300.0
MAXIMUM_FIGURE_DPI_F = 1200.0
FIGURE_IMAGE_FORMAT_STR = "png"
# LLFR-00131: reasons given when the file could not be written.
PDF_RENDER_FAILED_STR = "The PDF document could not be created."
# LLFR-00133: reason given when no image could be made.
COPY_FAILED_REASON_STR = "The image of the plots could not be created."


def tab_page_list(tab_widget) -> list:
    """Return the tab pages of a tab widget, from left to right.

    Inputs:
        tab_widget: the QTabWidget of the plot panel.
    Outputs: a list of TabPage, in tab order.
    """
    # LLFR-00129: the pages are exported in tab order.
    page_list = []
    for tab_index_i in range(tab_widget.count()):
        page = tab_widget.widget(tab_index_i)
        if isinstance(page, TabPage):
            page_list.append(page)
    return page_list


def exportable_page_list(tab_widget) -> list:
    """Return the tab pages that hold at least one plot, in tab order.

    Inputs:
        tab_widget: the QTabWidget of the plot panel.
    Outputs: a list of TabPage.
    """
    # LLFR-00129, LLFR-00145: only tabs with a plot get a PDF page.
    return [page for page in tab_page_list(tab_widget)
            if page.plot_widget_list]


def grab_page_image(page):
    """Return an image of a tab page as it is shown on screen.

    Inputs:
        page: a visible TabPage.
    Outputs: a QImage of the page with all its plots.
    """
    # LLFR-00129, LLFR-00133: every plot is drawn with its current
    # state before the page is grabbed, so nothing pending is missed.
    for plot_widget in page.plot_widget_list:
        plot_widget.canvas.draw()
    return page.grab().toImage()


def lay_out_page_like(page, reference_size) -> None:
    """Give a tab page the size of the visible tab page and lay it out.

    Inputs:
        page: the TabPage, already made the current tab.
        reference_size: QSize of the tab page that was visible.
    Outputs: none.
    """
    # LLFR-00129: the plots of every tab are exported at the size the
    # visible tab shows them.
    QApplication.processEvents()
    if page.size() != reference_size and not reference_size.isEmpty():
        page.resize(reference_size)
    page.page_layout.activate()
    QApplication.processEvents()


def render_figure_image(figure, dpi_f: float):
    """Render a matplotlib figure to an image at a given resolution.

    Inputs:
        figure: the matplotlib Figure of a plot.
        dpi_f: dots per inch of the rendered image.
    Outputs: a QImage of the whole figure, with the same size in inches
        and so the same layout as on screen. The figure is drawn again
        on its canvas afterwards, at its screen resolution.
    """
    # LLFR-00129: time range, curves, legend, grid, vertical markers,
    # delta markers and pinned tips are drawn as on screen, only with
    # more pixels (the delta brackets are computed again at this
    # resolution when they are drawn).
    image_buffer = io.BytesIO()
    screen_dpi_f = float(figure.dpi)
    try:
        figure.savefig(image_buffer, format=FIGURE_IMAGE_FORMAT_STR,
                       dpi=dpi_f)
    finally:
        # LLFR-00129: savefig renders on the plot's own canvas and leaves
        # its screen image empty, so the plot is drawn again at its
        # screen resolution and stays visible after the export, even
        # after an error.
        if float(figure.dpi) != screen_dpi_f:
            figure.set_dpi(screen_dpi_f)
        figure.canvas.draw()
    return QImage.fromData(image_buffer.getvalue(),
                           FIGURE_IMAGE_FORMAT_STR.upper())


def figure_export_dpi_f(figure, canvas_width_px: float,
                        page_width_px: float) -> float:
    """Return the resolution at which a plot is rendered for the PDF.

    Inputs:
        figure: the matplotlib Figure of the plot.
        canvas_width_px: width of the plot's canvas, in logical pixels.
        page_width_px: width of the tab page, in logical pixels.
    Outputs: dots per inch that give the figure at least
        TARGET_FIGURE_DPI_F on the page, where the tab is at most
        PAINT_WIDTH_INCHES_F wide; never less than the screen's and
        never more than MAXIMUM_FIGURE_DPI_F.
    """
    # LLFR-00129: the plots stay sharp when the PDF is printed.
    figure_width_inches_f = max(float(figure.get_size_inches()[0]), 1e-6)
    page_share_f = canvas_width_px / max(page_width_px, 1.0)
    on_page_inches_f = PAINT_WIDTH_INCHES_F * page_share_f
    dpi_f = TARGET_FIGURE_DPI_F * on_page_inches_f / figure_width_inches_f
    return min(max(dpi_f, float(figure.dpi)), MAXIMUM_FIGURE_DPI_F)


def plot_image_list(page) -> list:
    """Return a sharp image of each plot of a page and its place.

    Inputs:
        page: a visible TabPage, already laid out.
    Outputs: a list of tuples (QRectF of the canvas in the page's
        logical pixels, QImage of the figure).
    """
    # LLFR-00129: every plot of the tab, at its on-screen position.
    page_width_px = float(page.width())
    entry_list = []
    for plot_widget in page.plot_widget_list:
        canvas = plot_widget.canvas
        top_left = canvas.mapTo(page, QPoint(0, 0))
        canvas_rect = QRectF(float(top_left.x()), float(top_left.y()),
                             float(canvas.width()), float(canvas.height()))
        dpi_f = figure_export_dpi_f(plot_widget.figure,
                                    float(canvas.width()), page_width_px)
        entry_list.append(
            (canvas_rect, render_figure_image(plot_widget.figure, dpi_f)))
    return entry_list


def grab_exportable_images(tab_widget) -> list:
    """Return the name and images of every tab that holds a plot.

    The tabs are shown one after the other; the tab that was current is
    selected again at the end, even after an error.

    Inputs:
        tab_widget: the QTabWidget of the plot panel.
    Outputs: a list of tuples (tab name str, QImage of the page, list of
        plot images as returned by plot_image_list), in tab order.
    """
    # LLFR-00129: one page per tab with a plot, in tab order.
    current_page = tab_widget.currentWidget()
    reference_size = (current_page.size() if current_page is not None
                      else tab_widget.size())
    snapshot_list = []
    try:
        for page in exportable_page_list(tab_widget):
            if page is not tab_widget.currentWidget():
                tab_widget.setCurrentWidget(page)
                lay_out_page_like(page, reference_size)
            page_image = grab_page_image(page)
            snapshot_list.append(
                (page.name_str, page_image, plot_image_list(page)))
    finally:
        # LLFR-00129: the user keeps the tab that was shown.
        if current_page is not None:
            tab_widget.setCurrentWidget(current_page)
            QApplication.processEvents()
    return snapshot_list


def build_pdf_writer(device):
    """Create the PDF writer with the page layout of the export.

    Inputs:
        device: the QIODevice the PDF is written to.
    Outputs: a QPdfWriter for landscape A4 pages with PAGE_MARGIN_MM_F
        margins at PDF_RESOLUTION_I dots per inch.
    """
    # LLFR-00129: landscape A4, so a stack of wide plots fits well.
    writer = QPdfWriter(device)
    writer.setTitle(PDF_TITLE_STR)
    writer.setCreator(PDF_TITLE_STR)
    writer.setResolution(PDF_RESOLUTION_I)
    writer.setPageLayout(QPageLayout(
        QPageSize(QPageSize.PageSizeId.A4),
        QPageLayout.Orientation.Landscape,
        QMarginsF(PAGE_MARGIN_MM_F, PAGE_MARGIN_MM_F, PAGE_MARGIN_MM_F,
                  PAGE_MARGIN_MM_F),
        QPageLayout.Unit.Millimeter))
    return writer


def draw_page_title(painter, name_str: str, page_width_i: int) -> int:
    """Write a tab name at the top of the current PDF page.

    Inputs:
        painter: the QPainter drawing on the PDF writer.
        name_str: the tab name.
        page_width_i: width of the paintable page area, in device pixels.
    Outputs: the height, in device pixels, taken by the title and the
        gap below it.
    """
    # LLFR-00129: the tab's name at the top of the page.
    title_font = QFont()
    title_font.setPointSizeF(TITLE_FONT_POINT_SIZE_F)
    title_font.setBold(True)
    painter.setFont(title_font)
    font_metrics = painter.fontMetrics()
    line_height_i = font_metrics.height()
    # The text is cut at the page width, so a long name stays on it.
    shown_name_str = font_metrics.elidedText(
        name_str, Qt.TextElideMode.ElideRight, page_width_i)
    painter.drawText(QPointF(0.0, float(font_metrics.ascent())),
                     shown_name_str)
    return int(line_height_i * (1.0 + TITLE_GAP_RATIO_F))


def draw_page_image(painter, image, top_i: int, page_width_i: int,
                    page_height_i: int, plot_entry_list=()) -> list:
    """Draw a tab image below the title, scaled to fit the page.

    Inputs:
        painter: the QPainter drawing on the PDF writer.
        image: the QImage of the tab page (screen grab).
        top_i: first device pixel row free below the title.
        page_width_i: width of the paintable area, in device pixels.
        page_height_i: height of the paintable area, in device pixels.
        plot_entry_list: tuples (QRectF in the page's logical pixels,
            QImage of the figure) drawn over the grab.
    Outputs: a list of tuples (QRectF on the PDF page in device pixels,
        QImage) of the plot images drawn.
    """
    # LLFR-00129: the plots below the name, as shown on screen, with
    # their aspect ratio kept.
    pixel_ratio_f = max(float(image.devicePixelRatio()), 1e-6)
    logical_width_f = max(image.width() / pixel_ratio_f, 1.0)
    logical_height_f = max(image.height() / pixel_ratio_f, 1.0)
    free_height_i = max(page_height_i - top_i, 1)
    scale_f = min(page_width_i / logical_width_f,
                  free_height_i / logical_height_f)
    left_f = (page_width_i - logical_width_f * scale_f) / 2.0
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.drawImage(QRectF(left_f, float(top_i), logical_width_f * scale_f,
                             logical_height_f * scale_f), image)
    # LLFR-00129: each plot is drawn again from its sharp image.
    drawn_list = []
    for canvas_rect, plot_image in plot_entry_list:
        target_rect = QRectF(left_f + canvas_rect.x() * scale_f,
                             top_i + canvas_rect.y() * scale_f,
                             canvas_rect.width() * scale_f,
                             canvas_rect.height() * scale_f)
        painter.drawImage(target_rect, plot_image)
        drawn_list.append((target_rect, plot_image))
    return drawn_list


def build_pdf_bytes(snapshot_list: list) -> bytes:
    """Make a PDF document with one page per tab snapshot.

    Inputs:
        snapshot_list: tuples (tab name str, page QImage, plot image
            list) from grab_exportable_images, in page order.
    Outputs: the bytes of the PDF document.
    Raises:
        OSError: when Qt cannot create the document.
    """
    # LLFR-00129: one page per tab with a plot, in tab order.
    buffer = QBuffer()
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError(PDF_RENDER_FAILED_STR)
    writer = build_pdf_writer(buffer)
    painter = QPainter()
    # LLFR-00131: a painter that cannot start is a failed export.
    if not painter.begin(writer):
        buffer.close()
        raise OSError(PDF_RENDER_FAILED_STR)
    try:
        page_width_i = writer.width()
        page_height_i = writer.height()
        for page_index_i, snapshot_tuple in enumerate(snapshot_list):
            name_str, image, plot_entry_list = snapshot_tuple
            if page_index_i > 0 and not writer.newPage():
                raise OSError(PDF_RENDER_FAILED_STR)
            top_i = draw_page_title(painter, name_str, page_width_i)
            draw_page_image(painter, image, top_i, page_width_i,
                            page_height_i, plot_entry_list)
    finally:
        ended_b = painter.end()
        buffer.close()
    if not ended_b:
        raise OSError(PDF_RENDER_FAILED_STR)
    return bytes(buffer.data().data())


def describe_os_error(error) -> str:
    """Return a readable reason for an operating system error.

    Inputs:
        error: the OSError raised while writing.
    Outputs: the error's text, with the file name when it has one.
    """
    # LLFR-00131: the error box says why the file was not saved.
    reason_str = error.strerror or str(error)
    if error.filename:
        return f"{reason_str}: {error.filename}"
    return reason_str


def save_tabs_pdf(tab_widget, path_str: str) -> tuple:
    """Save the plots of every tab that holds a plot to a PDF file.

    Inputs:
        tab_widget: the QTabWidget of the plot panel.
        path_str: the path of the .pdf file.
    Outputs: a tuple (saved_b, reason_str); reason_str says why the file
        was not saved, "" when it was.
    """
    # LLFR-00129: grab the tabs, then lay them out on PDF pages.
    snapshot_list = grab_exportable_images(tab_widget)
    try:
        content_bytes = build_pdf_bytes(snapshot_list)
    except OSError as error:
        # LLFR-00131: the document could not be made.
        return (False, describe_os_error(error))
    # LLFR-00131: a failed write leaves any existing file untouched.
    return write_file_safely(path_str, content_bytes)


def copy_current_tab_image(tab_widget) -> tuple:
    """Put an image of the current tab's plots on the system clipboard.

    Inputs:
        tab_widget: the QTabWidget of the plot panel.
    Outputs: a tuple (copied_b, reason_str); reason_str is "" when the
        image was copied.
    """
    # LLFR-00133: the plots of the current tab, as shown on screen.
    page = tab_widget.currentWidget()
    if not isinstance(page, TabPage) or not page.plot_widget_list:
        # LLFR-00146: nothing to copy; the clipboard is not changed.
        return (False, COPY_FAILED_REASON_STR)
    image = grab_page_image(page)
    if image.isNull():
        return (False, COPY_FAILED_REASON_STR)
    QApplication.clipboard().setImage(image)
    return (True, "")
