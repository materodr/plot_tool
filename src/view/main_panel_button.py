"""The signal list button of the main window (LLFR-01205, HLFR-00131).

The main window gets the same Firefox-style signal list button as the
undocked windows (LLFR-01044 to LLFR-01049, LLFR-01171). It floats at
the top-right corner of the area below the top panel, which holds the
plot panel and the signal list panel, always at the same place
(LLFR-01134): level with the tab row and, while the panel is shown, at
the right end of the panel's "Signals" title row (LLFR-01133). While the
panel is hidden, the plot panel takes the whole width and its tab row
keeps room at its right end for the button (LLFR-01207).

MainPanelButton keeps the button in place and shows or hides the panel
when the controller asks; a click is passed on to the controller, which
keeps it as one undoable action (LLFR-01053).
"""

from PyQt6.QtCore import QEvent, QObject, QPoint

from model.window_placement import fitted_panel_width_i
from view import theme
from view.undocked_window import (
    HIDE_SIGNAL_LIST_TIP_STR, SHOW_SIGNAL_LIST_TIP_STR,
    build_signal_list_button)

# LLFR-01134: the events after which the button is placed again.
PLACE_EVENT_TUPLE = (QEvent.Type.Resize, QEvent.Type.Move,
                     QEvent.Type.Show, QEvent.Type.LayoutRequest)


class MainPanelButton(QObject):
    """Places the main window's signal list button and runs the panel.

    Inputs:
        area_widget: the widget that holds the splitter (the central
            widget of the main window); the button is its child.
        splitter: the PanelSplitter of the plot panel and the signal list
            panel.
        plot_panel: the PlotPanel.
        signal_list_panel: the SignalListPanel of the main window.
    Attributes:
        button: the round, checkable signal list button.
        hidden_width_i: the panel's width when it was hidden.
        toggle_handler: function without arguments, called on a click.
    """

    def __init__(self, area_widget, splitter, plot_panel,
                 signal_list_panel) -> None:
        """Create the button and watch the panels.

        Inputs: see the class docstring.
        Outputs: none.
        """
        super().__init__(area_widget)
        self.area_widget = area_widget
        self.splitter = splitter
        self.plot_panel = plot_panel
        self.signal_list_panel = signal_list_panel
        self.hidden_width_i = 0
        self.toggle_handler = None
        # LLFR-01205, LLFR-01045, LLFR-01049: the same button as in the
        # undocked windows.
        self.button = build_signal_list_button(area_widget)
        self.button.clicked.connect(self.request_toggle)
        # LLFR-01133: the word "Signals" leaves room for the button.
        title_label = signal_list_panel.title_label
        margins = title_label.contentsMargins()
        title_label.setContentsMargins(
            margins.left(), margins.top(),
            theme.SIDEBAR_BUTTON_SIZE_I + theme.TAB_SPACING_I,
            margins.bottom())
        for watched in (area_widget, splitter, plot_panel,
                        plot_panel.tab_widget):
            watched.installEventFilter(self)
        splitter.splitterMoved.connect(lambda *_: self.place())
        self.update_button()

    def eventFilter(self, watched, event) -> bool:
        """Place the button again after a change of geometry.

        Inputs:
            watched: the watched widget.
            event: the QEvent.
        Outputs: False, so the event is handled normally.
        """
        # LLFR-01134: always at the top-right corner of the area.
        if event.type() in PLACE_EVENT_TUPLE:
            self.place()
        return False

    def button_point(self):
        """Return where the button goes in the area widget.

        Inputs: none.
        Outputs: the QPoint of its top-left corner: at the right edge of
            the splitter, centred on the height of the main tab row.
        """
        # LLFR-01205, LLFR-01134: the same place whether the panel is
        # shown or hidden; LLFR-01133: level with the title row.
        size_i = theme.SIDEBAR_BUTTON_SIZE_I
        top_left = self.splitter.mapTo(self.area_widget, QPoint(0, 0))
        row_height_i = max(self.plot_panel.tab_widget.tabBar().height(),
                           size_i)
        return QPoint(top_left.x() + self.splitter.width() - size_i,
                      top_left.y() + (row_height_i - size_i) // 2)

    def place(self) -> None:
        """Move the button to its place, above the panels.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01134.
        self.button.move(self.button_point())
        self.button.raise_()

    def request_toggle(self) -> None:
        """Pass a click on the button to the controller.

        Inputs: none.
        Outputs: none. The button shows the panel's state afterwards.
        """
        # LLFR-01047, LLFR-01048, LLFR-01053.
        if self.toggle_handler is not None:
            self.toggle_handler()
        self.update_button()

    def is_panel_shown(self) -> bool:
        """Tell whether the main window shows its signal list panel.

        Inputs: none.
        Outputs: True when the panel is not hidden.
        """
        # LLFR-01205.
        return not self.signal_list_panel.isHidden()

    def panel_width(self) -> int:
        """Return the width of the panel, or the width it gets back.

        Inputs: none.
        Outputs: the width in pixels while shown; the width it had when
            it was hidden, while hidden (LLFR-01048).
        """
        # LLFR-01048, LLFR-01055: a hidden panel keeps its width.
        if self.is_panel_shown():
            return self.splitter.last_widget_width()
        return self.hidden_width_i

    def set_panel(self, shown_b: bool, width_i: int) -> None:
        """Show or hide the panel at a width.

        Inputs:
            shown_b: True to show it.
            width_i: its width in pixels, 0 to keep the one it had.
        Outputs: none.
        """
        width_i = int(width_i)
        if not shown_b:
            # LLFR-01047: hidden; the plot panel takes the whole width.
            if self.is_panel_shown():
                self.hidden_width_i = (width_i if width_i > 0
                                       else self.panel_width())
                self.signal_list_panel.hide()
            elif width_i > 0:
                self.hidden_width_i = width_i
            self.update_button()
            return
        if width_i < 1:
            width_i = self.hidden_width_i
        if self.is_panel_shown():
            self.update_button()
            return
        # LLFR-01048, LLFR-01195: shown again at its width, leaving the
        # plot panel room.
        self.signal_list_panel.show()
        total_i = max(sum(self.splitter.sizes()), 2)
        if width_i < 1:
            width_i = max(total_i // 5, 1)
        width_i = min(fitted_panel_width_i(width_i, total_i), total_i - 1)
        self.splitter.initial_sizes_set_b = True
        self.splitter.setSizes([total_i - width_i, width_i])
        self.update_button()

    def update_button(self) -> None:
        """Show the panel's state on the button and on the tab row.

        Inputs: none.
        Outputs: none.
        """
        shown_b = self.is_panel_shown()
        # LLFR-01049, LLFR-01171: active while the panel is shown.
        self.button.setChecked(shown_b)
        # LLFR-01046: the button tip.
        tip_str = (HIDE_SIGNAL_LIST_TIP_STR if shown_b
                   else SHOW_SIGNAL_LIST_TIP_STR)
        self.button.setToolTip(tip_str)
        self.button.setAccessibleName(tip_str)
        # LLFR-01207: while hidden, the tab row keeps room for it.
        reserved_i = (0 if shown_b
                      else theme.SIDEBAR_BUTTON_SIZE_I + theme.TAB_SPACING_I)
        self.plot_panel.tab_widget.set_reserved_right_width(reserved_i)
        self.place()
