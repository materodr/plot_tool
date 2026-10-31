"""Splitter between the plot panel and the signal list panel (HLFR-00026).

The user drags its handle to change the widths of the two panels
(LLFR-00073). When it is first shown, it gives the signal list panel a
fixed fraction of the width and the plot panel the rest (LLFR-00072).
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSplitter

# LLFR-00072: QSplitter stretch factors only share out extra space, so
# the start sizes are set once, when the final width is known.
DEFAULT_LAST_WIDGET_FRACTION_F = 0.25


class PanelSplitter(QSplitter):
    """Horizontal splitter whose last widget starts with a set fraction.

    Inputs:
        last_widget_fraction_f: share of the width, between 0 and 1, that
            the last widget (the signal list panel) gets at first show;
            the other widgets share the rest by their stretch factors.
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

    def initial_size_list(self, total_width_i: int) -> list:
        """Return the start widths of the widgets for a splitter width.

        Inputs:
            total_width_i: width of the splitter, in pixels.
        Outputs: a list of int, one width per widget (handles excluded);
            the last one is last_widget_fraction_f of the widths' sum.
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
        last_width_i = int(round(panel_total_i
                                 * self.last_widget_fraction_f))
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
        self.setSizes(self.initial_size_list(self.width()))

    def showEvent(self, event) -> None:
        """Apply the start widths when the splitter is first shown.

        Inputs:
            event: the QShowEvent.
        Outputs: none.
        """
        # LLFR-00072: the window has laid out the splitter by now.
        super().showEvent(event)
        self.apply_initial_sizes()
