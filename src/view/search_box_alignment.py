"""Signal list panel aligned with the plot panel (HLFR-00095, HLFR-00001).

The bottom edge of the search box of the signal list panel is kept at
the height of the bottom edge of the lowest plot of the current tab,
including its x-axis numbers and label, which are drawn inside the plot
widget (LLFR-00424). When the tab holds no plot, the bottom edge of the
tab page, where a plot would end, is used (LLFR-00652).

The two panels sit side by side in the same splitter, so their bottoms
are close but not equal: the plot well of the tab widget has a border
and, on some platforms, a margin. The aligner measures the difference
after every change of geometry (window or panel resize, tab change, a
plot added or removed) and gives it to the signal list panel as the
space below its search box. The measure is deferred to the next turn of
the event loop, so the layouts have their final geometry by then.

The same aligner keeps the top edge of the signal list box at the height
of the top edge of the plot well, the pane just below the tab row
(LLFR-00894). The two stacks above those edges are unrelated: the
"Signals" title and the panel spacing on one side, the tab row (its
padding, the selected tab's top line and the pane's overlap with the
tabs) on the other, and their heights depend on the font. The aligner
measures the difference and changes the height of the title row by it.
"""

from functools import partial

from PyQt6.QtCore import QEvent, QObject, QPoint, QTimer

# LLFR-00424: the events after which the geometry may have changed.
WATCHED_EVENT_TYPE_TUPLE = (
    QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show,
    QEvent.Type.LayoutRequest)


def top_edge_global_y(widget, local_top_i: int = 0) -> int:
    """Return the screen y of a line of a widget.

    Inputs:
        widget: a QWidget.
        local_top_i: the y of the line in the widget's coordinates.
    Outputs: the global y, in pixels, of that line.
    """
    # LLFR-00894: both panels are compared in the same coordinates.
    return int(widget.mapToGlobal(QPoint(0, local_top_i)).y())


def bottom_edge_global_y(widget) -> int:
    """Return the screen y of the line just below a widget.

    Inputs:
        widget: a QWidget.
    Outputs: the global y, in pixels, of the widget's bottom edge (its
        top plus its height).
    """
    # LLFR-00424: both panels are compared in the same coordinates.
    return int(widget.mapToGlobal(QPoint(0, widget.height())).y())


class SearchBoxAligner(QObject):
    """Keep the search box's bottom edge level with the lowest plot.

    Inputs:
        plot_panel: the PlotPanel.
        signal_list_panel: the SignalListPanel.
        parent: the QObject that owns the aligner (the main window).
    Attributes:
        plot_panel: the PlotPanel.
        signal_list_panel: the SignalListPanel.
        align_timer: the single-shot timer of the deferred alignment.
        watched_page_list: the tab pages whose events are watched.
    """

    def __init__(self, plot_panel, signal_list_panel, parent=None) -> None:
        """Watch both panels and align once the event loop runs.

        Inputs:
            plot_panel: the PlotPanel.
            signal_list_panel: the SignalListPanel.
            parent: the QObject that owns the aligner.
        Outputs: none.
        """
        super().__init__(parent)
        # LLFR-00424, LLFR-00652: the two panels to keep level.
        self.plot_panel = plot_panel
        self.signal_list_panel = signal_list_panel
        self.watched_page_list = []
        # LLFR-00424: a child timer, so a pending alignment never runs
        # after the window was deleted.
        self.align_timer = QTimer(self)
        self.align_timer.setSingleShot(True)
        self.align_timer.setInterval(0)
        self.align_timer.timeout.connect(self.align)
        for widget in (plot_panel, plot_panel.tab_widget,
                       signal_list_panel):
            widget.installEventFilter(self)
        # LLFR-00424: another tab may have another lowest plot.
        plot_panel.tab_widget.currentChanged.connect(self.schedule_align)
        self.schedule_align()

    def schedule_align(self, *_ignored_tuple) -> None:
        """Ask for an alignment at the next turn of the event loop.

        Inputs:
            _ignored_tuple: the arguments of a Qt signal, not used.
        Outputs: none.
        """
        # LLFR-00424: many events of one change give one alignment.
        self.align_timer.start()

    def eventFilter(self, watched, event) -> bool:
        """Schedule an alignment after a change of geometry.

        Inputs:
            watched: the object that received the event.
            event: the QEvent.
        Outputs: False, so the event is handled normally.
        """
        # LLFR-00424, LLFR-00652: at any window size, with any plots.
        if event.type() in WATCHED_EVENT_TYPE_TUPLE:
            self.schedule_align()
        return super().eventFilter(watched, event)

    def watch_page(self, page) -> None:
        """Watch a tab page, so a plot added to it or removed realigns.

        Inputs:
            page: a TabPage.
        Outputs: none.
        """
        # LLFR-00424: a new or deleted plot sends LayoutRequest to its
        # page; each page is watched once.
        if page is None or page in self.watched_page_list:
            return
        self.watched_page_list.append(page)
        page.installEventFilter(self)
        page.destroyed.connect(partial(self.forget_page, page))

    def forget_page(self, page, *_ignored_tuple) -> None:
        """Stop tracking a deleted tab page.

        Inputs:
            page: the TabPage that was destroyed.
            _ignored_tuple: the arguments of the destroyed signal.
        Outputs: none.
        """
        # LLFR-00424: a deleted tab no longer counts.
        if page in self.watched_page_list:
            self.watched_page_list.remove(page)

    def target_widget(self):
        """Return the widget whose bottom edge the search box follows.

        Inputs: none.
        Outputs: the lowest visible plot widget of the current tab
            (LLFR-00424), or the current tab page when it holds no plot
            (LLFR-00652), or None when there is no tab page.
        """
        page = self.plot_panel.tab_widget.currentWidget()
        if page is None:
            return None
        self.watch_page(page)
        # LLFR-00424: the plots are stacked from top to bottom
        # (LLFR-00069), so the lowest one ends lowest on the screen.
        plot_widget_list = [
            plot_widget for plot_widget
            in getattr(page, "plot_widget_list", [])
            if not plot_widget.isHidden()]
        if plot_widget_list:
            return max(plot_widget_list, key=bottom_edge_global_y)
        # LLFR-00652: with no plot, a plot would end at the page bottom.
        return page

    def search_box_target_margin(self) -> int:
        """Return the space below the search box that levels it.

        Inputs: none.
        Outputs: the distance in pixels from the bottom edge of the
            lowest plot (or of the empty page) to the bottom of the
            signal list panel, or the current margin when the panels are
            not shown yet.
        """
        panel = self.signal_list_panel
        target = self.target_widget()
        if (target is None or not panel.isVisible()
                or not target.isVisible()):
            return panel.search_box_bottom_margin()
        # LLFR-00424, LLFR-00652: the panel's bottom is where its layout
        # ends; the margin lifts the search box to the plot's bottom.
        return bottom_edge_global_y(panel) - bottom_edge_global_y(target)

    def align(self) -> None:
        """Level the bottom edge of the search box with the lowest plot.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00424, LLFR-00652: the space below the search box.
        self.signal_list_panel.set_search_box_bottom_margin(
            self.search_box_target_margin())
        # LLFR-00894: and the list's top edge level with the plot well.
        self.align_list_top()

    def list_top_offset_px(self) -> int:
        """Return how far the signal list starts below the plot well.

        Inputs: none.
        Outputs: the top edge of the plot well minus the top edge of the
            signal list box, in pixels: positive when the list starts
            higher, negative when it starts lower, 0 when level.
        """
        # LLFR-00894: the pane rectangle Qt paints the plot well in.
        tab_widget = self.plot_panel.tab_widget
        well_top_i = top_edge_global_y(tab_widget,
                                       tab_widget.pane_rect().top())
        list_top_i = top_edge_global_y(
            self.signal_list_panel.signal_list_widget)
        return well_top_i - list_top_i

    def align_list_top(self) -> None:
        """Level the top edge of the signal list with the plot well.

        Inputs: none.
        Outputs: none. The "Signals" title row grows or shrinks by the
            difference, which moves the list's top edge by as much.
        """
        # LLFR-00894: only once both panels are laid out on screen.
        panel = self.signal_list_panel
        if not (panel.isVisible() and self.plot_panel.isVisible()):
            return
        offset_i = self.list_top_offset_px()
        if offset_i != 0:
            panel.set_title_height(panel.title_height() + offset_i)

    def misalignment_px(self) -> int:
        """Return how far the search box ends from the lowest plot.

        Inputs: none.
        Outputs: the bottom edge of the search box minus the bottom edge
            of the target widget, in pixels (0 when they are level).
        """
        # LLFR-00424, LLFR-00652: for checks of the alignment.
        target = self.target_widget()
        if target is None:
            return 0
        return (bottom_edge_global_y(self.signal_list_panel.search_box)
                - bottom_edge_global_y(target))
