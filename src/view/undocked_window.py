"""Undocked windows: tabs in a window of their own (HLFR-00123).

An UndockedWindow holds one or more tabs (HLFR-00125) and shows,
side by side (LLFR-01035):
- its plot panel: the tab row (LLFR-00997) above the tab page it shows,
  which is in a plot well of the same look as the main window's
  (LLFR-00893). The tab row holds one tab per tab of the window, from
  the left edge (LLFR-01028), also when it holds one tab: the shown tab
  with the look of the selected tab of the main window, the others with
  the look of its other tabs (LLFR-01095). Each tab has its dock button
  inside it (LLFR-00990), in place of the undock button (LLFR-01031). A
  click on a tab shows it (LLFR-01114), and the window's title is the
  shown tab's name (LLFR-01026, LLFR-01027);
- to its right, the signal list panel (LLFR-01000), with a border that
  can be dragged (LLFR-00073). Its "Signals" title row is level with
  the tab row.

The signal list button (LLFR-01009) works like the sidebar button of
Firefox, mirrored to the right side. It is a button of the window, not
of a tab: it floats at the window's top-right corner, always at the same
place (LLFR-01099). While the panel is shown, that place is the right
end of the panel's title row, level with the word "Signals"
(LLFR-01098), and the button shows a round, pale highlight
(LLFR-01014). While the panel is hidden, the plot panel takes the whole
width, and the tab row keeps room at its right end for the button
(LLFR-00997). The title row is at least as high as the button
(LLFR-01100).

A tab can be dragged along the tab row to reorder the window's tabs
(LLFR-01122), onto the tab row of the main window to dock it there
(LLFR-01108), or onto another undocked window to move it there
(LLFR-01117); a drop anywhere else changes nothing (LLFR-01032).
MainWindow decides from the drop point.

There is no top panel (HLFR-00136): the main window keeps the plot tool
buttons, and the keyboard shortcuts of the main window are given to
every undocked window by MainWindow (LLFR-01036).

The window is top-level, with no parent, so that it is never kept above
the main window (LLFR-00986). A close by the user (the system's close
button or close shortcut) goes to the close handler, which deletes all
the window's tabs (LLFR-01038); a close by the app (a dock of its last
tab, an undo, a layout load or the main window closing) only closes the
window.

The tab pages themselves are created and kept by the PlotPanel, the
registry of every tab and plot; the window only shows them.
"""

from functools import partial

from PyQt6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QTabBar, QToolButton, QVBoxLayout, QWidget)

from model.workspace import first_panel_width_i
from view import icon_shapes, icons, theme
from view.panel_splitter import PanelSplitter
from view.plot_panel import (
    PlotTabWidget, TAB_BAR_OBJECT_NAME_STR, build_tab_style_sheet,
    escape_tab_text)
from view.search_box_alignment import SearchBoxAligner
from view.signal_list_panel import SignalListPanel
from view.window_buttons import WINDOW_BUTTON_ICON_SIZE_I, build_dock_button

# LLFR-01011: the texts of the signal list button tip.
HIDE_SIGNAL_LIST_TIP_STR = "Hide signal list"
SHOW_SIGNAL_LIST_TIP_STR = "Show signal list"
# LLFR-00997: object names of the parts of the tab row.
WINDOW_TAB_ROW_OBJECT_NAME_STR = "window_tab_row"
SIGNAL_LIST_BUTTON_OBJECT_NAME_STR = "signal_list_button"
WINDOW_PLOT_COLUMN_OBJECT_NAME_STR = "window_plot_column"
# LLFR-01100: the tab row, and so the "Signals" title row level with it,
# is at least as high as the signal list button plus the space between
# the title row and the list, plus the border by which the plot well
# rises into the tab row (LLFR-00893), since the list top is level with
# the well's top edge (LLFR-00894).
TAB_ROW_MINIMUM_HEIGHT_I = (theme.SIDEBAR_BUTTON_SIZE_I
                            + theme.SIGNAL_PANEL_SPACING_I
                            + theme.TAB_BORDER_WIDTH_I)


def signal_list_button_style_sheet() -> str:
    """Return the style sheet of the signal list button.

    Inputs: none.
    Outputs: a style sheet that draws the button as a circle with no
        border: transparent in its normal state, a paler circle on
        hover and a pale circle while active (LLFR-01014).
    """
    # LLFR-01014: the round, pale highlight of Firefox's sidebar button.
    radius_i = theme.SIDEBAR_BUTTON_SIZE_I // 2
    selector_str = f"QToolButton#{SIGNAL_LIST_BUTTON_OBJECT_NAME_STR}"
    return (f"{selector_str} {{ border: none; padding: 0px; "
            f"border-radius: {radius_i}px; "
            f"background-color: transparent; }}\n"
            f"{selector_str}:hover {{ background-color: "
            f"{theme.SIDEBAR_BUTTON_HOVER_COLOR_STR}; }}\n"
            f"{selector_str}:checked {{ background-color: "
            f"{theme.SIDEBAR_BUTTON_ACTIVE_COLOR_STR}; }}\n")


def build_signal_list_button(parent=None):
    """Return the signal list button of an undocked window.

    Inputs:
        parent: the parent widget, the window.
    Outputs: a round, checkable QToolButton with the signal list icon,
        whose icon stays dark while checked.
    """
    # LLFR-01009, LLFR-01010: the button and its picture; LLFR-01014:
    # checked (active) while the panel is shown, with a pale highlight,
    # so the icon keeps its normal dark color.
    button = QToolButton(parent)
    button.setObjectName(SIGNAL_LIST_BUTTON_OBJECT_NAME_STR)
    button.setCheckable(True)
    button.setIcon(icons.icon_for(icon_shapes.SIGNAL_LIST_ICON_STR,
                                  active_color_str=theme.ICON_COLOR_STR))
    button.setIconSize(QSize(WINDOW_BUTTON_ICON_SIZE_I,
                             WINDOW_BUTTON_ICON_SIZE_I))
    button.setFixedSize(theme.SIDEBAR_BUTTON_SIZE_I,
                        theme.SIDEBAR_BUTTON_SIZE_I)
    button.setStyleSheet(signal_list_button_style_sheet())
    # LLFR-00137: a click does not take the focus from the plots.
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return button


class WindowPaneWidget(PlotTabWidget):
    """The plot well of an undocked window, holding its one tab page.

    It is a PlotTabWidget, so that the well has the look of the main
    window's (LLFR-00893), but its own tab bar and "+" button are
    hidden: the tab button is in the window's tab row (LLFR-00997).

    Inputs:
        parent: optional parent widget.
    """

    def __init__(self, parent=None) -> None:
        """Create the well with no tab bar and no "+" button.

        Inputs:
            parent: optional parent widget.
        Outputs: none.
        """
        super().__init__(parent)
        # LLFR-00997: no "+" button in an undocked window.
        self.add_tab_button.hide()
        # LLFR-01028: the tab button is in the tab row above the well.
        self.tabBar().setMovable(False)
        self.setTabBarAutoHide(True)
        self.tabBar().hide()

    def reposition_add_button(self) -> None:
        """Keep the hidden tab bar hidden after a layout change.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00997: Qt shows the tab bar again when a tab is added.
        if getattr(self, "reposition_timer", None) is None:
            return
        self.tabBar().hide()
        self.add_tab_button.hide()


class UndockedWindow(QWidget):
    """A window that holds one or more undocked tabs (HLFR-00125).

    Inputs:
        window_id_i: id of the window in the model.
        plot_panel: the PlotPanel of the main window, which keeps the tab
            pages and runs the tab menu (LLFR-01029).
    Attributes:
        window_id_i: id of the window.
        tab_bar: the movable QTabBar with one tab per tab of the window
            (LLFR-01028, LLFR-01122), each with its dock button inside
            (LLFR-00990).
        dock_button_dict: tab id -> its TabIconButton.
        signal_list_button: the round QToolButton that hides and shows
            the signal list panel (LLFR-01009), checked while it is
            shown; a child of the window outside every layout.
        tab_row: the row of the tabs.
        button_space: the room kept at the right end of the tab row for
            the signal list button while the panel is hidden.
        plot_column: the plot panel: the tab row above the well.
        pane_widget: the WindowPaneWidget that holds the tab pages, in
            the order of the tab bar, showing the current one.
        signal_list_panel: the window's own SignalListPanel (LLFR-01000).
        splitter: the PanelSplitter between the well and the panel.
        search_box_aligner: the SearchBoxAligner of this window
            (LLFR-00424, LLFR-00894).
        hidden_panel_width_i: the panel's width when it was hidden, 0
            while it was never shown (LLFR-01013, LLFR-01016).
        closing_by_app_b: True while the app itself closes the window.
        close_handler: function taking the window id, called when the
            user closes the window (LLFR-01038).
        dock_handler: function taking a tab id, for the dock buttons.
        panel_toggle_handler: function taking the window id, for the
            signal list button.
        tab_drop_handler: function taking the window, the tab id, the
            tab's place at the press and the x and y of the screen point
            where a dragged tab was released (LLFR-01108, LLFR-01116,
            LLFR-01117, LLFR-01122).
        drag_start_point: the screen QPoint of a left press on a tab, or
            None.
        pressed_tab_id_i: the tab of that press, -1 for none.
        pressed_tab_index_i: its place at the press.
        tab_button_drag_b: True once the pointer moved far enough with
            the button held for the press to be a drag.
        panel_width_handler: function taking the window id and the
            panel widths at the press and the release of a border drag.
    """

    def __init__(self, window_id_i: int, plot_panel) -> None:
        """Create the window, its tab row and its two panels.

        Inputs:
            window_id_i: id of the window.
            plot_panel: the PlotPanel of the main window.
        Outputs: none.
        """
        # LLFR-00986: a window of its own, not kept above the main
        # window, so with no parent.
        super().__init__(None, Qt.WindowType.Window)
        self.window_id_i = int(window_id_i)
        self.plot_panel = plot_panel
        self.closing_by_app_b = False
        self.close_handler = None
        self.dock_handler = None
        self.panel_toggle_handler = None
        self.panel_width_handler = None
        # LLFR-01108, LLFR-01116, LLFR-01117, LLFR-01122: where a dragged
        # tab is released decides what happens to it.
        self.tab_drop_handler = None
        self.drag_start_point = None
        self.pressed_tab_id_i = -1
        self.pressed_tab_index_i = -1
        self.tab_button_drag_b = False
        self.dock_button_dict = {}
        # LLFR-01016: the width of the main window's panel, for a panel
        # shown with no width of its own.
        self.main_panel_width_function = None
        self.hidden_panel_width_i = 0
        # LLFR-00182: the app icon in the title bar.
        self.setWindowIcon(icons.app_icon())
        # LLFR-01095: the tabs have the look of the main window's tabs;
        # the same style sheet, on the whole window.
        self.setStyleSheet(build_tab_style_sheet())
        # LLFR-00997, LLFR-01028: the tab row.
        self.tab_bar = QTabBar()
        self.tab_bar.setObjectName(TAB_BAR_OBJECT_NAME_STR)
        self.tab_bar.setExpanding(False)
        self.tab_bar.setDrawBase(False)
        self.tab_bar.setElideMode(Qt.TextElideMode.ElideNone)
        self.tab_bar.setUsesScrollButtons(True)
        # LLFR-01122: a tab is dragged along the tab row, the others
        # moving aside.
        self.tab_bar.setMovable(True)
        # LLFR-01121: a removed shown tab gives way to the tab on its
        # left, or else on its right.
        self.tab_bar.setSelectionBehaviorOnRemove(
            QTabBar.SelectionBehavior.SelectLeftTab)
        # LLFR-01114, LLFR-01026, LLFR-01027: a click on a tab shows it,
        # and the title follows.
        self.tab_bar.currentChanged.connect(self.show_current_page)
        self.tab_bar.tabMoved.connect(self.move_page)
        # LLFR-01029: a right-click opens the tab menu.
        self.tab_bar.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_bar.customContextMenuRequested.connect(self.show_tab_menu)
        # LLFR-01030: a left double-click renames, as in LLFR-00421.
        self.tab_bar.installEventFilter(self)
        self.tab_row = QWidget()
        self.tab_row.setObjectName(WINDOW_TAB_ROW_OBJECT_NAME_STR)
        # LLFR-01100: high enough for the title row level with it.
        self.tab_row.setMinimumHeight(TAB_ROW_MINIMUM_HEIGHT_I)
        row_layout = QHBoxLayout(self.tab_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(theme.TAB_SPACING_I)
        # LLFR-01028: the tabs from the left edge.
        row_layout.addWidget(self.tab_bar, 1, Qt.AlignmentFlag.AlignBottom)
        # LLFR-00997: while the panel is hidden, the room of the signal
        # list button at the right end.
        self.button_space = QWidget()
        self.button_space.setFixedSize(theme.SIDEBAR_BUTTON_SIZE_I, 1)
        row_layout.addWidget(self.button_space)
        # LLFR-01035: the plot panel, the tab row above the well.
        self.pane_widget = WindowPaneWidget()
        self.plot_column = QWidget()
        self.plot_column.setObjectName(WINDOW_PLOT_COLUMN_OBJECT_NAME_STR)
        column_layout = QVBoxLayout(self.plot_column)
        column_layout.setContentsMargins(0, 0, 0, 0)
        # LLFR-01028, LLFR-00893: the tabs join the well below.
        column_layout.setSpacing(0)
        column_layout.addWidget(self.tab_row)
        column_layout.addWidget(self.pane_widget, 1)
        self.signal_list_panel = SignalListPanel()
        # LLFR-01098, LLFR-01100: the word "Signals" is centred on the
        # height of the tab row, where the signal list button is: the
        # title row is the tab row less the space above the list, so the
        # text is pushed down by that space; on the right it leaves room
        # for the button.
        self.signal_list_panel.title_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.signal_list_panel.title_label.setContentsMargins(
            0, theme.SIGNAL_PANEL_SPACING_I,
            theme.SIDEBAR_BUTTON_SIZE_I + theme.TAB_SPACING_I, 0)
        self.splitter = PanelSplitter()
        self.splitter.addWidget(self.plot_column)
        self.splitter.addWidget(self.signal_list_panel)
        # LLFR-01021: a window resize gives the room to the plots, so
        # the panel keeps the width the user chose.
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setHandleWidth(theme.SPLITTER_HANDLE_WIDTH_I)
        # LLFR-01013: the widths are set by the window, not at first
        # show.
        self.splitter.initial_sizes_set_b = True
        # LLFR-01020: a drag of the border is reported.
        self.splitter.drag_finished_handler = self.report_panel_drag
        window_layout = QVBoxLayout(self)
        window_layout.setContentsMargins(
            theme.WINDOW_MARGIN_I, theme.WINDOW_TOP_MARGIN_I,
            theme.WINDOW_MARGIN_I, theme.WINDOW_MARGIN_I)
        window_layout.setSpacing(0)
        # LLFR-01035: the title row of the panel starts at the top of
        # the tab row, both at the top of the splitter.
        window_layout.addWidget(self.splitter, 1)
        # LLFR-01009, LLFR-01010, LLFR-01014: the signal list button,
        # checked while the panel is shown; LLFR-01099: placed by the
        # window at its top-right corner, outside every layout.
        self.signal_list_button = build_signal_list_button(self)
        self.signal_list_button.clicked.connect(self.request_panel_toggle)
        self.tab_row.installEventFilter(self)
        # LLFR-00424, LLFR-00652, LLFR-00894: the search box and the list
        # level with the plots of the tab this window shows.
        self.search_box_aligner = SearchBoxAligner(
            self.pane_widget, self.signal_list_panel, self,
            tab_widget=self.pane_widget)
        # LLFR-01015: the panel starts hidden.
        self.signal_list_panel.hide()
        self.update_signal_list_button()
        self.place_signal_list_button()
        # LLFR-01038: the system's close shortcut (Cmd+W on macOS, Ctrl+W
        # or Ctrl+F4 on Windows; Alt+F4 is the system's own close).
        self.close_shortcut = QShortcut(QKeySequence.StandardKey.Close, self)
        self.close_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self.close_shortcut.activated.connect(self.request_user_close)

    # ----------------------------------------------------------------
    # Tabs and title
    # ----------------------------------------------------------------

    def page_list(self) -> list:
        """Return the tab pages of the window, in the tab row's order.

        Inputs: none.
        Outputs: a list of TabPage.
        """
        # LLFR-01028, LLFR-01056: the order of the tab row.
        return [self.pane_widget.widget(index_i)
                for index_i in range(self.pane_widget.count())]

    def tab_id_list(self) -> list:
        """Return the ids of the tabs of the window, in order.

        Inputs: none.
        Outputs: a list of int.
        """
        # LLFR-01028: the tabs of the tab row.
        return [page.tab_id_i for page in self.page_list()]

    def page(self):
        """Return the tab page the window shows.

        Inputs: none.
        Outputs: the TabPage, or None when the window holds no tab.
        """
        # LLFR-01026, LLFR-01101: the tab the window shows.
        index_i = self.tab_bar.currentIndex()
        if index_i < 0:
            return None
        return self.pane_widget.widget(index_i)

    def shown_tab_id(self) -> int:
        """Return the id of the tab the window shows.

        Inputs: none.
        Outputs: the tab id, or -1 when the window holds no tab.
        """
        # LLFR-01003, LLFR-01101: plots and copies use the shown tab.
        page = self.page()
        return -1 if page is None else page.tab_id_i

    def set_pages(self, page_list: list, shown_tab_id_i: int = -1) -> None:
        """Show exactly these tab pages in the window, in this order.

        Inputs:
            page_list: the TabPage of each tab of the window, in order.
            shown_tab_id_i: the tab the window shows; -1 to keep the
                shown tab when it is still there, else the first.
        Outputs: none.
        """
        page_list = [page for page in page_list if page is not None]
        if self.page_list() != page_list:
            # LLFR-01028: one tab per page, each with its dock button.
            keep_id_i = (shown_tab_id_i if shown_tab_id_i >= 0
                         else self.shown_tab_id())
            self.tab_bar.blockSignals(True)
            try:
                while self.tab_bar.count() > 0:
                    self.tab_bar.removeTab(0)
                while self.pane_widget.count() > 0:
                    self.pane_widget.removeTab(0)
                for button in self.dock_button_dict.values():
                    button.deleteLater()
                self.dock_button_dict = {}
                for page in page_list:
                    self.add_tab_of(page)
            finally:
                self.tab_bar.blockSignals(False)
            if shown_tab_id_i < 0:
                shown_tab_id_i = keep_id_i
        self.show_tab(shown_tab_id_i)

    def add_tab_of(self, page) -> None:
        """Add a tab for a page at the end of the tab row.

        Inputs:
            page: the TabPage.
        Outputs: none.
        """
        # LLFR-01028: the tab, with the tab's name.
        index_i = self.tab_bar.addTab(escape_tab_text(page.name_str))
        self.pane_widget.addTab(page, "")
        # LLFR-00990, LLFR-01031: its dock button inside the tab.
        dock_button = build_dock_button()
        dock_button.button.clicked.connect(partial(self.request_dock,
                                                   page.tab_id_i))
        self.dock_button_dict[page.tab_id_i] = dock_button
        self.tab_bar.setTabButton(index_i, QTabBar.ButtonPosition.RightSide,
                                  dock_button)

    def show_tab(self, tab_id_i: int) -> None:
        """Show one of the window's tabs.

        Inputs:
            tab_id_i: id of the tab; an unknown id shows the first tab.
        Outputs: none.
        """
        # LLFR-01114, LLFR-01123, LLFR-01126: the window shows the tab.
        id_list = self.tab_id_list()
        index_i = id_list.index(tab_id_i) if tab_id_i in id_list else 0
        if not id_list:
            self.update_title()
            return
        if self.tab_bar.currentIndex() != index_i:
            self.tab_bar.setCurrentIndex(index_i)
        self.show_current_page()

    def show_current_page(self, *_) -> None:
        """Show the page of the current tab and its name in the title.

        Inputs: none (the index Qt passes is ignored).
        Outputs: none.
        """
        # LLFR-01114: the page of the clicked tab.
        index_i = self.tab_bar.currentIndex()
        if 0 <= index_i < self.pane_widget.count():
            self.pane_widget.setCurrentIndex(index_i)
            page = self.pane_widget.widget(index_i)
            page.show()
        # LLFR-01112: the dock buttons in the text color of their tab.
        shown_id_i = self.shown_tab_id()
        for tab_id_i, dock_button in self.dock_button_dict.items():
            dock_button.set_selected_look(tab_id_i == shown_id_i)
        # LLFR-01026, LLFR-01027: the title is the shown tab's name.
        self.update_title()

    def move_page(self, from_index_i: int, to_index_i: int) -> None:
        """Keep the pages in the order of the tab row after a drag.

        Inputs:
            from_index_i: where the tab was.
            to_index_i: where it is now.
        Outputs: none.
        """
        # LLFR-01122: the tab bar moved the tab; the page follows.
        self.pane_widget.tabBar().moveTab(from_index_i, to_index_i)
        self.pane_widget.setCurrentIndex(self.tab_bar.currentIndex())

    def update_title(self) -> None:
        """Title the window with the name of the tab it shows.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01026: the shown tab's name, with no other text.
        page = self.page()
        if page is not None:
            self.setWindowTitle(str(page.name_str))

    def refresh_tab_names(self) -> None:
        """Show the current name of every page on its tab.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00030, LLFR-01027: after a rename, an undo or a redo.
        for index_i, page in enumerate(self.page_list()):
            self.tab_bar.setTabText(index_i, escape_tab_text(page.name_str))
        self.update_title()

    def tab_name(self) -> str:
        """Return the title of the window.

        Inputs: none.
        Outputs: the name of the tab it shows.
        """
        # LLFR-01026: the title is the shown tab's name.
        return self.windowTitle()

    def take_page(self, tab_id_i: int):
        """Take the page of one tab out of the window.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: the TabPage, or None when the window does not hold it.
            The window shows another of its tabs (LLFR-01121).
        """
        # LLFR-00993, LLFR-01115: the page goes to another window.
        id_list = self.tab_id_list()
        if tab_id_i not in id_list:
            return None
        index_i = id_list.index(tab_id_i)
        page = self.pane_widget.widget(index_i)
        self.pane_widget.removeTab(index_i)
        dock_button = self.dock_button_dict.pop(tab_id_i, None)
        self.tab_bar.removeTab(index_i)
        if dock_button is not None:
            dock_button.deleteLater()
        self.show_current_page()
        return page

    def take_all_pages(self) -> list:
        """Take every page out of the window.

        Inputs: none.
        Outputs: the TabPages it held.
        """
        # LLFR-00138: the views are shown again from the model.
        return [self.take_page(tab_id_i) for tab_id_i in self.tab_id_list()]

    def dock_button_of(self, tab_id_i: int):
        """Return the dock button inside a tab of the window.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: its TabIconButton, or None.
        """
        # LLFR-00990: one per tab.
        return self.dock_button_dict.get(tab_id_i)

    def tab_index_at(self, x_i: int, y_i: int) -> int:
        """Return where a tab dropped at a desktop point goes.

        Inputs:
            x_i, y_i: the point, in desktop pixels.
        Outputs: the place among the window's tabs, from 0: before the
            first tab whose middle is right of the point, or after the
            last one; -1 when the point is not on the tab row.
        """
        # LLFR-01116: a drop on the tab row goes between the tabs.
        top_left = self.tab_row.mapToGlobal(QPoint(0, 0))
        row_rect = QRect(top_left.x(), top_left.y(), self.tab_row.width(),
                         self.tab_row.height())
        if not row_rect.contains(QPoint(int(x_i), int(y_i))):
            return -1
        for index_i in range(self.tab_bar.count()):
            middle_x_i = self.tab_bar.mapToGlobal(
                self.tab_bar.tabRect(index_i).center()).x()
            if int(x_i) < middle_x_i:
                return index_i
        return self.tab_bar.count()

    def show_tab_menu(self, position) -> None:
        """Show the tab menu for a right-click on a tab.

        Inputs:
            position: the QPoint of the click, in tab bar coordinates.
        Outputs: none.
        """
        # LLFR-01029: the menu of the main window's tabs, acting on the
        # clicked tab; LLFR-01034: "Delete" enabled.
        index_i = self.tab_bar.tabAt(position)
        if index_i < 0:
            return
        self.plot_panel.show_tab_menu_of(
            self.tab_id_list()[index_i], self.tab_bar.mapToGlobal(position),
            True)

    def eventFilter(self, watched, event) -> bool:
        """Follow the tabs and the tab row.

        Inputs:
            watched: the object that received the event.
            event: the QEvent.
        Outputs: False, so the event is handled normally.
        """
        # LLFR-01030: as LLFR-00421; the dialog opens once control is
        # back in Qt.
        if (watched is self.tab_bar
                and event.type() == QEvent.Type.MouseButtonDblClick
                and event.button() == Qt.MouseButton.LeftButton):
            index_i = self.tab_bar.tabAt(event.position().toPoint())
            if index_i >= 0:
                QTimer.singleShot(0, partial(
                    self.plot_panel.request_rename_tab,
                    self.tab_id_list()[index_i]))
        # LLFR-01108, LLFR-01116, LLFR-01117, LLFR-01122: a drag of a tab.
        if watched is self.tab_bar:
            self.follow_tab_drag(event)
        # LLFR-01099: the button stays centred on the tab row.
        if (watched is getattr(self, "tab_row", None)
                and event.type() == QEvent.Type.Resize):
            self.place_signal_list_button()
        return super().eventFilter(watched, event)

    def follow_tab_drag(self, event) -> None:
        """Keep track of a drag of a tab, press to release.

        Inputs:
            event: an event of the tab bar.
        Outputs: none. A drag released anywhere is passed to the
            tab_drop_handler once control is back in Qt, which decides
            from the point (LLFR-01108, LLFR-01116, LLFR-01117,
            LLFR-01122, LLFR-01032); a click is no drag.
        """
        event_type = event.type()
        if (event_type == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton):
            # LLFR-01122: a press on a tab may start a drag.
            index_i = self.tab_bar.tabAt(event.position().toPoint())
            id_list = self.tab_id_list()
            if not 0 <= index_i < len(id_list):
                return
            self.drag_start_point = event.globalPosition().toPoint()
            self.pressed_tab_id_i = id_list[index_i]
            self.pressed_tab_index_i = index_i
            self.tab_button_drag_b = False
        elif (event_type == QEvent.Type.MouseMove
              and self.drag_start_point is not None
              and event.buttons() & Qt.MouseButton.LeftButton):
            moved_i = (event.globalPosition().toPoint()
                       - self.drag_start_point).manhattanLength()
            if (not self.tab_button_drag_b
                    and moved_i >= QApplication.startDragDistance()):
                # LLFR-01122: the press is a drag.
                self.tab_button_drag_b = True
        elif (event_type == QEvent.Type.MouseButtonRelease
              and event.button() == Qt.MouseButton.LeftButton
              and self.drag_start_point is not None):
            dragged_b = self.tab_button_drag_b
            tab_id_i = self.pressed_tab_id_i
            start_index_i = self.pressed_tab_index_i
            self.drag_start_point = None
            self.pressed_tab_id_i = -1
            self.tab_button_drag_b = False
            if dragged_b and self.tab_drop_handler is not None:
                # LLFR-01108: decided once control is back in Qt, so the
                # window is not closed inside its own mouse event.
                drop_point = event.globalPosition().toPoint()
                QTimer.singleShot(0, partial(
                    self.tab_drop_handler, self, tab_id_i, start_index_i,
                    drop_point.x(), drop_point.y()))

    def is_tab_drag_in_progress(self) -> bool:
        """Tell whether the user is dragging a tab of this window.

        Inputs: none.
        Outputs: True from the first move with the button held on a tab
            to the release.
        """
        # LLFR-00454: a tab drag is a mouse drag.
        if self.tab_button_drag_b and not (
                QApplication.mouseButtons() & Qt.MouseButton.LeftButton):
            self.tab_button_drag_b = False
            self.drag_start_point = None
        return self.tab_button_drag_b

    def signal_list_button_point(self):
        """Return where the signal list button goes in the window.

        Inputs: none.
        Outputs: the QPoint of its top-left corner: at the window's
            right margin, centred on the height of the tab row. It does
            not depend on whether the panel is shown (LLFR-01099).
        """
        # LLFR-01009, LLFR-01099: the top-right corner of the window;
        # LLFR-01098: the right end of the title row, level with it.
        margins = self.layout().contentsMargins()
        size_i = theme.SIDEBAR_BUTTON_SIZE_I
        row_height_i = max(self.tab_row.height(),
                           self.tab_row.minimumHeight())
        return QPoint(self.width() - margins.right() - size_i,
                      margins.top() + (row_height_i - size_i) // 2)

    def place_signal_list_button(self) -> None:
        """Move the signal list button to its place, above the panels.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01099: the same place whether the panel is shown or not.
        if getattr(self, "signal_list_button", None) is None:
            return
        self.signal_list_button.move(self.signal_list_button_point())
        self.signal_list_button.raise_()

    def resizeEvent(self, event) -> None:
        """Keep the signal list button at the window's top-right corner.

        Inputs:
            event: the QResizeEvent.
        Outputs: none.
        """
        # LLFR-01009, LLFR-01099.
        super().resizeEvent(event)
        self.place_signal_list_button()

    def showEvent(self, event) -> None:
        """Place the signal list button once the window is laid out.

        Inputs:
            event: the QShowEvent.
        Outputs: none.
        """
        # LLFR-01009, LLFR-01099.
        super().showEvent(event)
        self.place_signal_list_button()

    # ----------------------------------------------------------------
    # Buttons
    # ----------------------------------------------------------------

    def request_dock(self, tab_id_i: int) -> None:
        """Ask the controller to dock a tab of the window.

        Inputs:
            tab_id_i: id of the tab whose dock button was clicked.
        Outputs: none.
        """
        # LLFR-00993: the dock button inside the tab.
        if self.dock_handler is not None:
            self.dock_handler(int(tab_id_i))

    def request_panel_toggle(self) -> None:
        """Ask the controller to hide or show the signal list panel.

        Inputs: none.
        Outputs: none. The button shows the panel's state afterwards,
            whatever the controller did.
        """
        # LLFR-01012, LLFR-01013: the signal list button.
        if self.panel_toggle_handler is not None:
            self.panel_toggle_handler(self.window_id_i)
        self.update_signal_list_button()

    def update_signal_list_button(self) -> None:
        """Show the panel's state on the signal list button.

        Inputs: none.
        Outputs: none.
        """
        shown_b = self.is_panel_shown()
        # LLFR-01014: active while the panel is shown.
        self.signal_list_button.setChecked(shown_b)
        # LLFR-00997: while the panel is hidden, the tab row keeps room
        # for the button at its right end; while it is shown, the button
        # is in the panel's title row (LLFR-01098).
        self.button_space.setVisible(not shown_b)
        self.place_signal_list_button()
        # LLFR-01011: "Hide signal list" or "Show signal list".
        tip_str = (HIDE_SIGNAL_LIST_TIP_STR if shown_b
                   else SHOW_SIGNAL_LIST_TIP_STR)
        self.signal_list_button.setToolTip(tip_str)
        self.signal_list_button.setAccessibleName(tip_str)

    # ----------------------------------------------------------------
    # Signal list panel
    # ----------------------------------------------------------------

    def is_panel_shown(self) -> bool:
        """Tell whether the signal list panel is shown.

        Inputs: none.
        Outputs: True when it is not hidden.
        """
        # LLFR-01012, LLFR-01013.
        return not self.signal_list_panel.isHidden()

    def panel_width(self) -> int:
        """Return the width of the signal list panel.

        Inputs: none.
        Outputs: its width in pixels while shown, or the width it gets
            back while hidden (0 when it was never shown).
        """
        # LLFR-01013: a hidden panel keeps the width it had.
        if self.is_panel_shown():
            return self.splitter.last_widget_width()
        return self.hidden_panel_width_i

    def set_panel(self, shown_b: bool, width_i: int) -> None:
        """Show or hide the signal list panel at a width.

        Inputs:
            shown_b: True to show it.
            width_i: its width in pixels; 0 for the first width
                (LLFR-01016).
        Outputs: none.
        """
        width_i = int(width_i)
        if not shown_b:
            # LLFR-01012: hidden; the plot panel takes the whole width.
            if self.is_panel_shown():
                self.hidden_panel_width_i = (width_i if width_i > 0
                                             else self.panel_width())
                self.signal_list_panel.hide()
            else:
                self.hidden_panel_width_i = width_i
            self.update_signal_list_button()
            return
        if width_i < 1:
            # LLFR-01016: a quarter of the window's width.
            main_width_i = (self.main_panel_width_function()
                            if self.main_panel_width_function is not None
                            else 0)
            width_i = first_panel_width_i(main_width_i, self.width())
        if self.is_panel_shown() and self.panel_width() == width_i:
            self.update_signal_list_button()
            return
        # LLFR-01013: shown at its width.
        self.signal_list_panel.show()
        self.hidden_panel_width_i = width_i
        total_i = max(self.splitter.width() - self.splitter.handleWidth(),
                      width_i + 1)
        self.splitter.setSizes([total_i - width_i, width_i])
        self.update_signal_list_button()

    def report_panel_drag(self, start_width_i: int, end_width_i: int) -> None:
        """Pass a drag of the panel border to the controller.

        Inputs:
            start_width_i: the panel width at the press.
            end_width_i: its width at the release.
        Outputs: none.
        """
        # LLFR-01020: an undoable action when the width changed.
        if self.panel_width_handler is not None:
            self.panel_width_handler(self.window_id_i, start_width_i,
                                     end_width_i)

    # ----------------------------------------------------------------
    # Geometry and closing
    # ----------------------------------------------------------------

    def window_tuple(self) -> tuple:
        """Return the window's position and size.

        Inputs: none.
        Outputs: (x, y, width, height) in desktop pixels, with the
            position of the window's top-left corner (LLFR-01040).
        """
        # LLFR-01040: whole pixels, top-left corner of the window.
        return (int(self.x()), int(self.y()), int(self.width()),
                int(self.height()))

    def set_window_tuple(self, window_tuple: tuple) -> None:
        """Move and resize the window.

        Inputs:
            window_tuple: (x, y, width, height) in desktop pixels, already
                kept on a screen.
        Outputs: none.
        """
        # LLFR-01041, LLFR-01024, LLFR-00981, LLFR-01093.
        x_i, y_i, width_i, height_i = (int(value_i)
                                       for value_i in window_tuple)
        self.resize(max(width_i, 1), max(height_i, 1))
        self.move(x_i, y_i)

    def close_by_app(self) -> None:
        """Close the window without deleting its tabs.

        Inputs: none.
        Outputs: none. The window is deleted later.
        """
        # LLFR-00994, LLFR-00989, LLFR-01045: the app closes it.
        self.closing_by_app_b = True
        self.close()
        self.deleteLater()

    def request_user_close(self) -> None:
        """Delete the tabs because the user asked to close the window.

        Inputs: none.
        Outputs: none. The window stays until the controller has deleted
            the tabs; the deletion runs once control is back in Qt.
        """
        # LLFR-01038: the user's close deletes all the tabs, with no
        # question.
        if self.close_handler is not None:
            QTimer.singleShot(0, lambda: self.close_handler(self.window_id_i))

    def closeEvent(self, event) -> None:
        """Tell a user's close of the window from a close of the app.

        Inputs:
            event: the QCloseEvent.
        Outputs: none.
        """
        if self.closing_by_app_b:
            event.accept()
            return
        if event.spontaneous():
            # LLFR-01038: the system's close button (or Alt+F4) of this
            # window, sent by the window system: its tabs are deleted.
            event.ignore()
            self.request_user_close()
            return
        # LLFR-00989: a close that neither the user nor this window's own
        # actions asked for comes from the app closing every window (for
        # example a quit, which MainWindow also catches first): the
        # window closes and its tabs are kept.
        event.accept()
