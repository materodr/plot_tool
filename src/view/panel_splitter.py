"""Splitter between the plot panel and the signal list panel (HLFR-00026).

The user drags its handle to change the widths of the two panels
(LLFR-00073). When it is first shown, it gives the signal list panel a
fixed fraction of the app window's width and the plot panel the rest of
the splitter (LLFR-00072).

Its handle (PanelSplitterHandle) is invisible until the user can use
it: while the pointer is over it, and while it is dragged, it draws a
blue vertical line, 2 pixels wide, over its whole height, which is the
height of the two panels (LLFR-00280), and shows the horizontal resize
pointer (LLFR-00281).
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QSplitter, QSplitterHandle

from view import theme

# LLFR-00072: QSplitter stretch factors only share out extra space, so
# the start sizes are set once, when the final width is known.
DEFAULT_LAST_WIDGET_FRACTION_F = 0.25


class PanelSplitterHandle(QSplitterHandle):
    """Splitter handle that shows a blue line while it can be used.

    Inputs:
        orientation: the Qt.Orientation of the splitter.
        parent: the QSplitter the handle belongs to.
    Attributes:
        hovered_b: True while the mouse pointer is over the handle.
        dragging_b: True while the user drags the handle with the left
            mouse button.
    """

    def __init__(self, orientation, parent) -> None:
        """Create the handle, hidden line, resize pointer.

        Inputs:
            orientation: the Qt.Orientation of the splitter.
            parent: the QSplitter.
        Outputs: none.
        """
        super().__init__(orientation, parent)
        # LLFR-00280: the line is hidden until the pointer is over the
        # handle or the handle is dragged.
        self.hovered_b = False
        self.dragging_b = False
        # LLFR-00280: enter and leave events tell when the pointer is
        # over the handle; the handle covers exactly the part of the
        # border where a drag changes the widths (LLFR-00073).
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        # LLFR-00281: the horizontal resize pointer over the handle; the
        # handle grabs the mouse during a drag, so the pointer stays the
        # same until the button is released.
        self.setCursor(Qt.CursorShape.SplitHCursor)

    def highlight_shown(self) -> bool:
        """Tell whether the blue line is drawn.

        Inputs: none.
        Outputs: True while the pointer is over the handle or the
            handle is dragged (LLFR-00280).
        """
        # LLFR-00280: shown on hover and during a drag, hidden otherwise.
        return self.hovered_b or self.dragging_b

    def highlight_column_tuple(self) -> tuple:
        """Return the first and last pixel column of the blue line.

        Inputs: none.
        Outputs: a (first_i, last_i) tuple of int, in handle coordinates;
            the line is theme.RESIZE_BORDER_WIDTH_I pixels wide and
            centered on the handle.
        """
        # LLFR-00280: 2 pixels wide, along the middle of the border.
        line_width_i = min(theme.RESIZE_BORDER_WIDTH_I, self.width())
        first_i = (self.width() - line_width_i) // 2
        return (first_i, first_i + line_width_i - 1)

    def set_highlight_state(self, hovered_b: bool, dragging_b: bool) -> None:
        """Store whether the handle is hovered or dragged and repaint.

        Inputs:
            hovered_b: True while the pointer is over the handle.
            dragging_b: True while the handle is dragged.
        Outputs: none.
        """
        # LLFR-00280: repaint only when the line appears or disappears.
        was_shown_b = self.highlight_shown()
        self.hovered_b = bool(hovered_b)
        self.dragging_b = bool(dragging_b)
        if was_shown_b != self.highlight_shown():
            self.update()

    def pointer_inside(self, event) -> bool:
        """Tell whether a mouse event happened over the handle.

        Inputs:
            event: a QMouseEvent sent to the handle.
        Outputs: True when its position is inside the handle.
        """
        # LLFR-00280: after a drag the pointer may be far from the border.
        return self.rect().contains(event.position().toPoint())

    def enterEvent(self, event) -> None:
        """Show the line when the pointer comes over the handle.

        Inputs:
            event: the QEnterEvent.
        Outputs: none.
        """
        # LLFR-00280, LLFR-00281: the pointer is over the border.
        super().enterEvent(event)
        self.set_highlight_state(True, self.dragging_b)

    def leaveEvent(self, event) -> None:
        """Hide the line when the pointer leaves, unless it is dragged.

        Inputs:
            event: the QEvent of type Leave.
        Outputs: none.
        """
        # LLFR-00280: hidden as soon as the pointer leaves the border,
        # unless a drag is in progress.
        super().leaveEvent(event)
        self.set_highlight_state(False, self.dragging_b)

    def mousePressEvent(self, event) -> None:
        """Start a drag: the line stays shown until the release.

        Inputs:
            event: the QMouseEvent.
        Outputs: none.
        """
        # LLFR-00073: QSplitterHandle moves the border; LLFR-00280: the
        # line is shown during the drag.
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_highlight_state(True, True)

    def mouseReleaseEvent(self, event) -> None:
        """End a drag: keep the line only if the pointer is still over it.

        Inputs:
            event: the QMouseEvent.
        Outputs: none.
        """
        # LLFR-00280: the drag is over; the line stays only while the
        # pointer is still over the handle.
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_highlight_state(self.pointer_inside(event), False)

    def paintEvent(self, event) -> None:
        """Draw the blue line while it is shown, nothing otherwise.

        Inputs:
            event: the QPaintEvent.
        Outputs: none.
        """
        # LLFR-00280: the border is visible only when it can be used.
        if not self.highlight_shown():
            return
        first_i, last_i = self.highlight_column_tuple()
        painter = QPainter(self)
        painter.fillRect(first_i, 0, last_i - first_i + 1, self.height(),
                         QColor(theme.RESIZE_BORDER_COLOR_STR))
        painter.end()


class PanelSplitter(QSplitter):
    """Horizontal splitter whose last widget starts with a set fraction.

    Inputs:
        last_widget_fraction_f: share of the app window's width, between
            0 and 1, that the last widget (the signal list panel) gets at
            first show; the other widgets share the rest of the splitter
            by their stretch factors.
        parent: optional parent widget.
    Attributes:
        last_widget_fraction_f: the share given to the last widget.
        initial_sizes_set_b: True once the start sizes were applied.
    """

    def __init__(self, last_widget_fraction_f: float =
                 DEFAULT_LAST_WIDGET_FRACTION_F, parent=None) -> None:
        """Create the splitter.

        Inputs:
            last_widget_fraction_f: share of the width of the last widget.
            parent: optional parent widget.
        Outputs: none.
        """
        super().__init__(Qt.Orientation.Horizontal, parent)
        # LLFR-00072: start share of the signal list panel.
        self.last_widget_fraction_f = float(last_widget_fraction_f)
        self.initial_sizes_set_b = False
        # LLFR-00073: the handle can be dragged, but no panel can be
        # pushed to zero width (each keeps its minimum width).
        self.setChildrenCollapsible(False)
        self.setOpaqueResize(True)

    def initial_size_list(self, total_width_i: int,
                          window_width_i: int) -> list:
        """Return the start widths of the widgets.

        Inputs:
            total_width_i: width of the splitter, in pixels.
            window_width_i: width of the app window, in pixels.
        Outputs: a list of int, one width per widget (handles excluded);
            the last one is last_widget_fraction_f of window_width_i
            (at most what the splitter has), the others share the rest.
        """
        # LLFR-00072: the last widget gets its fraction, the others the
        # rest, split by their stretch factors (equally when all are 0).
        widget_count_i = self.count()
        if widget_count_i == 0:
            return []
        handle_total_i = self.handleWidth() * (widget_count_i - 1)
        panel_total_i = max(0, total_width_i - handle_total_i)
        if widget_count_i == 1:
            return [panel_total_i]
        # LLFR-00072: the share is of the window's width, not of the
        # splitter's (which lacks the window margins and the handle).
        last_width_i = min(panel_total_i, int(round(
            window_width_i * self.last_widget_fraction_f)))
        rest_width_i = panel_total_i - last_width_i
        stretch_list = [max(0, self.widget(index_i).sizePolicy()
                            .horizontalStretch())
                        for index_i in range(widget_count_i - 1)]
        stretch_total_i = sum(stretch_list)
        if stretch_total_i == 0:
            stretch_list = [1] * (widget_count_i - 1)
            stretch_total_i = widget_count_i - 1
        size_list = [rest_width_i * stretch_i // stretch_total_i
                     for stretch_i in stretch_list]
        # Give the rounding remainder to the first widget.
        size_list[0] += rest_width_i - sum(size_list)
        size_list.append(last_width_i)
        return size_list

    def apply_initial_sizes(self) -> None:
        """Set the start widths of the widgets, once.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00072: done only once, so a width the user dragged to
        # (LLFR-00073) is never reset.
        if self.initial_sizes_set_b or self.count() == 0:
            return
        self.initial_sizes_set_b = True
        self.setSizes(self.initial_size_list(self.width(),
                                             self.window().width()))

    def createHandle(self) -> QSplitterHandle:
        """Return the handle placed between two widgets.

        Inputs: none.
        Outputs: a PanelSplitterHandle (LLFR-00280, LLFR-00281).
        """
        # LLFR-00280, LLFR-00281: the handle with the blue line.
        return PanelSplitterHandle(self.orientation(), self)

    def showEvent(self, event) -> None:
        """Apply the start widths when the splitter is first shown.

        Inputs:
            event: the QShowEvent.
        Outputs: none.
        """
        # LLFR-00072: the window has laid out the splitter by now.
        super().showEvent(event)
        self.apply_initial_sizes()
