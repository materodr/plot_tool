"""Export of the plots: tabs to a PDF file, current tab to the clipboard.

HLFR-00038, HLFR-00039. Both use an image of a tab page taken with
``QWidget.grab``, so the PDF pages and the copied image show the plots
exactly as on screen: time range, curves, legends above the axes, grid,
vertical markers and pinned tips (LLFR-00129, LLFR-00133).

PDF layout (LLFR-00129): one landscape A4 page per tab that holds at
least one plot, in tab order, with a margin of PAGE_MARGIN_MM_F on each
side. The tab name is written at the top of the page in bold, and the
image of the tab's plots fills the rest of the page, scaled to fit and
keeping its aspect ratio. A tab that is not the current one is shown
for a moment, so that it is laid out at the size of the visible tab
page before its image is taken; the current tab is selected again
afterwards.

The PDF is first written to memory and then to the file in one Python
``write``, so every write error (missing folder, no permission, full
disk) is reported with its reason (LLFR-00131).
"""

import os

from PyQt6.QtCore import QBuffer, QIODevice, QMarginsF, QPointF, QRectF, Qt
from PyQt6.QtGui import QFont, QPageLayout, QPageSize, QPainter, QPdfWriter
from PyQt6.QtWidgets import QApplication

from view.tab_page import TabPage

# LLFR-00129: page size, orientation, margins and resolution of the PDF.
PAGE_MARGIN_MM_F = 10.0
PDF_RESOLUTION_I = 300
PDF_TITLE_STR = "plot_tool plots"
TITLE_FONT_POINT_SIZE_F = 14.0
# LLFR-00129: space between the tab name and the plots, in title line
# heights.
TITLE_GAP_RATIO_F = 0.5
# LLFR-00131: reasons given when the file could not be written.
PDF_RENDER_FAILED_STR = "The PDF document could not be created."
EMPTY_FILE_REASON_STR = "Nothing was written to the file."
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


def grab_exportable_images(tab_widget) -> list:
    """Return the name and image of every tab that holds a plot.

    The tabs are shown one after the other; the tab that was current is
    selected again at the end, even after an error.

    Inputs:
        tab_widget: the QTabWidget of the plot panel.
    Outputs: a list of tuples (tab name str, QImage), in tab order.
    """
    # LLFR-00129: one image per tab with a plot, in tab order.
    current_page = tab_widget.currentWidget()
    reference_size = (current_page.size() if current_page is not None
                      else tab_widget.size())
    titled_image_list = []
    try:
        for page in exportable_page_list(tab_widget):
            if page is not tab_widget.currentWidget():
                tab_widget.setCurrentWidget(page)
                lay_out_page_like(page, reference_size)
            titled_image_list.append((page.name_str, grab_page_image(page)))
    finally:
        # LLFR-00129: the user keeps the tab that was shown.
        if current_page is not None:
            tab_widget.setCurrentWidget(current_page)
            QApplication.processEvents()
    return titled_image_list


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
                    page_height_i: int) -> None:
    """Draw a tab image below the title, scaled to fit the page.

    Inputs:
        painter: the QPainter drawing on the PDF writer.
        image: the QImage of the tab's plots.
        top_i: first device pixel row free below the title.
        page_width_i: width of the paintable area, in device pixels.
        page_height_i: height of the paintable area, in device pixels.
    Outputs: none.
    """
    # LLFR-00129: the plots below the name, as shown on screen, with
    # their aspect ratio kept.
    free_height_i = max(page_height_i - top_i, 1)
    image_width_i = max(image.width(), 1)
    image_height_i = max(image.height(), 1)
    scale_f = min(page_width_i / image_width_i,
                  free_height_i / image_height_i)
    target_width_f = image_width_i * scale_f
    target_height_f = image_height_i * scale_f
    left_f = (page_width_i - target_width_f) / 2.0
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.drawImage(QRectF(left_f, float(top_i), target_width_f,
                             target_height_f), image)


def build_pdf_bytes(titled_image_list: list) -> bytes:
    """Make a PDF document with one page per titled image.

    Inputs:
        titled_image_list: tuples (tab name str, QImage), in page order.
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
        for page_index_i, (name_str, image) in enumerate(titled_image_list):
            if page_index_i > 0 and not writer.newPage():
                raise OSError(PDF_RENDER_FAILED_STR)
            top_i = draw_page_title(painter, name_str, page_width_i)
            draw_page_image(painter, image, top_i, page_width_i,
                            page_height_i)
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


def write_file_bytes(path_str: str, content_bytes: bytes) -> tuple:
    """Write bytes to a file and report whether it worked.

    Inputs:
        path_str: the path of the file.
        content_bytes: the bytes to write.
    Outputs: a tuple (written_b, reason_str); reason_str is "" when the
        file was written. A partly written file is removed.
    """
    # LLFR-00131: every write error is reported with its reason.
    try:
        with open(path_str, "wb") as output_file:
            output_file.write(content_bytes)
    except OSError as error:
        remove_partial_file(path_str)
        return (False, describe_os_error(error))
    # LLFR-00131: the file must exist and hold the whole document.
    if (not os.path.isfile(path_str)
            or os.path.getsize(path_str) != len(content_bytes)
            or not content_bytes):
        return (False, EMPTY_FILE_REASON_STR)
    return (True, "")


def remove_partial_file(path_str: str) -> None:
    """Remove a file left half written by a failed write, if any.

    Inputs:
        path_str: the path of the file.
    Outputs: none. Errors while removing are ignored.
    """
    # LLFR-00131: a failed export leaves no broken PDF behind.
    try:
        if os.path.isfile(path_str):
            os.remove(path_str)
    except OSError:
        pass


def save_tabs_pdf(tab_widget, path_str: str) -> tuple:
    """Save the plots of every tab that holds a plot to a PDF file.

    Inputs:
        tab_widget: the QTabWidget of the plot panel.
        path_str: the path of the .pdf file.
    Outputs: a tuple (saved_b, reason_str); reason_str says why the file
        was not saved, "" when it was.
    """
    # LLFR-00129: grab the tabs, then lay them out on PDF pages.
    titled_image_list = grab_exportable_images(tab_widget)
    try:
        content_bytes = build_pdf_bytes(titled_image_list)
    except OSError as error:
        # LLFR-00131: the document could not be made.
        return (False, describe_os_error(error))
    return write_file_bytes(path_str, content_bytes)


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
