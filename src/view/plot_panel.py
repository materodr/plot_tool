"""Plot panel: the tabs that hold the plots (HLFR-00014).

The panel shows a QTabWidget whose pages are TabPage widgets, each with
its PlotWidgets. The tabs are aligned to the left (LLFR-00106). A "+"
button sits directly beside the last tab (LLFR-00025), or at the right
end of the tab row when the tabs overflow and the tab bar scrolls, and
it is styled like an unselected tab, only narrower (LLFR-00107). A
right-click on a tab opens a menu with "Delete" and
"Rename" (LLFR-00027, LLFR-00029).

It offers a plain-Python facade (ids of the model, names, bools; no Qt
types), used through MainWindow by the plot controller (COR-00009).
Tabs and plots are always found by id, never by index.
"""

from functools import partial

from PyQt6.QtCore import QEvent, QTimer, Qt
from PyQt6.QtWidgets import (
    QApplication, QInputDialog, QLineEdit, QMenu, QTabBar, QTabWidget,
    QToolButton, QVBoxLayout, QWidget)

from model.workspace import TIME_PLOT_KIND_STR
from view import theme
from view.plot_widget import PlotWidget
from view.tab_page import TabPage

ADD_TAB_TEXT_STR = "+"
ADD_TAB_TOOL_TIP_STR = "Add a new tab"
DELETE_TAB_TEXT_STR = "Delete"
RENAME_TAB_TEXT_STR = "Rename"
RENAME_DIALOG_TITLE_STR = "Rename tab"
RENAME_DIALOG_LABEL_STR = "New tab name:"
# LLFR-00025: pixels between the last tab and the "+" button.
ADD_BUTTON_GAP_I = theme.TAB_SPACING_I
# LLFR-00106, LLFR-00107: object names used by the style sheet.
TAB_WIDGET_OBJECT_NAME_STR = "plot_tab_widget"
TAB_BAR_OBJECT_NAME_STR = "plot_tab_bar"
ADD_BUTTON_OBJECT_NAME_STR = "add_tab_button"
# LLFR-00107: the look shared by the unselected tabs and the "+" button,
# so that the two always match (background, border, corner shape). The
# values are design tokens of view.theme.
TAB_BACKGROUND_COLOR_STR = theme.TAB_BACKGROUND_COLOR_STR
TAB_HOVER_COLOR_STR = theme.TAB_HOVER_COLOR_STR
TAB_SELECTED_COLOR_STR = theme.TAB_SELECTED_COLOR_STR
TAB_TEXT_COLOR_STR = theme.TAB_TEXT_COLOR_STR
TAB_BORDER_COLOR_STR = theme.TAB_BORDER_COLOR_STR
TAB_BORDER_WIDTH_I = theme.TAB_BORDER_WIDTH_I
TAB_CORNER_RADIUS_I = theme.TAB_CORNER_RADIUS_I
# LLFR-00107: the tabs are wider than the "+" button.
TAB_MINIMUM_TEXT_WIDTH_I = theme.TAB_MINIMUM_TEXT_WIDTH_I
TAB_HORIZONTAL_PADDING_I = theme.TAB_HORIZONTAL_PADDING_I
TAB_VERTICAL_PADDING_I = theme.TAB_VERTICAL_PADDING_I
TAB_SPACING_I = theme.TAB_SPACING_I
ADD_BUTTON_WIDTH_I = theme.ADD_BUTTON_WIDTH_I
# LLFR-00107: one declaration block for background, border and corners,
# used by both the unselected tab rule and the "+" button rule.
SHARED_TAB_SHAPE_STR = theme.SHARED_TAB_SHAPE_STR
# LLFR-00025: events of the tab bar after which the button is moved.
TAB_BAR_EVENT_TUPLE = (QEvent.Type.Resize, QEvent.Type.Move,
                       QEvent.Type.LayoutRequest, QEvent.Type.Show)
# LLFR-00021, LLFR-00039, LLFR-00041, LLFR-00045, LLFR-00047,
# LLFR-00049, LLFR-00070, LLFR-00081, LLFR-00086, LLFR-00088,
# LLFR-00091: plot widget signal -> name of its handler.
PLOT_SIGNAL_HANDLER_DICT = {
    "curve_delete_requested": "curve_delete_handler",
    "curve_width_requested": "curve_width_handler",
    "plot_delete_requested": "plot_delete_handler",
    "signal_dropped": "signal_drop_handler",
    "tip_pin_requested": "tip_pin_handler",
    "pinned_tip_delete_requested": "pinned_tip_delete_handler",
    # LLFR-00152: a pinned tip was dragged and released.
    "pinned_tip_move_requested": "pinned_tip_move_handler",
    "time_range_changed": "time_range_handler",
    "marker_place_requested": "marker_place_handler",
    "marker_move_requested": "marker_move_handler",
    "marker_rename_requested": "marker_rename_handler",
    "marker_delete_requested": "marker_delete_handler",
    # LLFR-00163, LLFR-00164: a curve point picked with a delta tool.
    "delta_point_picked": "delta_point_pick_handler",
    # LLFR-00176: "Delete" chosen on a delta marker.
    "delta_marker_delete_requested": "delta_marker_delete_handler",
}


def build_tab_style_sheet() -> str:
    """Return the style sheet of the plot tab widget.

    Inputs: none.
    Outputs: a Qt style sheet that aligns the tab bar to the left
        (LLFR-00106) and gives the unselected tabs and the "+" button the
        same shape block SHARED_TAB_SHAPE_STR (LLFR-00107).
    """
    # LLFR-00106, LLFR-00107: the rules are built by view.theme.
    return theme.tab_style_sheet(TAB_WIDGET_OBJECT_NAME_STR,
                                 TAB_BAR_OBJECT_NAME_STR,
                                 ADD_BUTTON_OBJECT_NAME_STR)


def escape_tab_text(name_str: str) -> str:
    """Return a tab name with "&" doubled, so Qt shows it as typed.

    Inputs:
        name_str: the tab name.
    Outputs: the text to give to QTabWidget.setTabText.
    """
    # LLFR-00030: "&" would otherwise be read as a keyboard shortcut.
    return name_str.replace("&", "&&")


class PlotTabWidget(QTabWidget):
    """Tab widget with a "+" button placed directly beside the last tab.

    Inputs:
        parent: optional parent widget.
    Attributes:
        add_tab_button: the "+" QToolButton (LLFR-00025).
    """

    def __init__(self, parent=None) -> None:
        """Create the tab widget and its "+" button.

        Inputs:
            parent: optional parent widget.
        Outputs: none.
        """
        super().__init__(parent)
        self.setObjectName(TAB_WIDGET_OBJECT_NAME_STR)
        # LLFR-00106: left-aligned tabs; when they do not fit, the tab
        # bar scrolls instead of squeezing or centring them.
        tab_bar = QTabBar(self)
        tab_bar.setObjectName(TAB_BAR_OBJECT_NAME_STR)
        tab_bar.setExpanding(False)
        tab_bar.setUsesScrollButtons(True)
        tab_bar.setElideMode(Qt.TextElideMode.ElideNone)
        tab_bar.setDrawBase(False)
        self.setTabBar(tab_bar)
        # setTabBar resets "expanding", so it is set again afterwards.
        tab_bar.setExpanding(False)
        # LLFR-00025: the "+" button is a child of the tab widget and is
        # moved next to the last tab whenever the tabs change.
        self.add_tab_button = QToolButton(self)
        self.add_tab_button.setObjectName(ADD_BUTTON_OBJECT_NAME_STR)
        self.add_tab_button.setText(ADD_TAB_TEXT_STR)
        self.add_tab_button.setToolTip(ADD_TAB_TOOL_TIP_STR)
        # LLFR-00107: narrower than a tab, styled like an unselected tab.
        self.add_tab_button.setFixedWidth(ADD_BUTTON_WIDTH_I)
        self.setStyleSheet(build_tab_style_sheet())
        # LLFR-00025: the tab bar never takes the room at the right end of
        # the tab row where the button goes when the tabs overflow.
        self.limit_tab_bar_width()
        # LLFR-00025: a child timer, so a pending move never runs after
        # the widget was deleted.
        self.reposition_timer = QTimer(self)
        self.reposition_timer.setSingleShot(True)
        self.reposition_timer.setInterval(0)
        self.reposition_timer.timeout.connect(self.reposition_add_button)
        self.tabBar().installEventFilter(self)
        self.reposition_add_button()

    def reposition_add_button(self) -> None:
        """Move the "+" button directly to the right of the last tab.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00025: the button sits on the tab row, right after the
        # last tab (or at the start of the row when there is no tab).
        if getattr(self, "reposition_timer", None) is None:
            # Called by Qt before __init__ finished: nothing to move yet.
            return
        tab_bar = self.tabBar()
        bar_geometry = tab_bar.geometry()
        tab_count_i = tab_bar.count()
        if tab_count_i > 0:
            last_rect = tab_bar.tabRect(tab_count_i - 1)
            right_edge_i = min(last_rect.x() + last_rect.width(),
                               tab_bar.width())
            if self.tabs_overflow():
                # LLFR-00025: with scroll buttons, the button goes to the
                # right end of the tab row, after the scroll buttons, so
                # it never covers them or a tab.
                right_edge_i = tab_bar.width()
            top_i = last_rect.y()
            # LLFR-00107: same height as a tab.
            height_i = last_rect.height()
        else:
            right_edge_i = 0
            top_i = 0
            height_i = max(bar_geometry.height(),
                           self.add_tab_button.sizeHint().height())
        button_width_i = ADD_BUTTON_WIDTH_I
        left_i = bar_geometry.x() + right_edge_i + ADD_BUTTON_GAP_I
        left_i = max(0, min(left_i, self.width() - button_width_i))
        self.add_tab_button.setGeometry(left_i, bar_geometry.y() + top_i,
                                        button_width_i, height_i)
        self.add_tab_button.raise_()

    def limit_tab_bar_width(self) -> None:
        """Keep the tab bar narrow enough to leave room for the button.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00025: a corner widget would not do this, because the
        # style sheet position of the tab bar (LLFR-00106) ignores
        # corner widgets; QWidget.setGeometry respects the maximum width.
        reserved_width_i = ADD_BUTTON_WIDTH_I + 2 * ADD_BUTTON_GAP_I
        self.tabBar().setMaximumWidth(max(0, self.width()
                                          - reserved_width_i))

    def tabs_overflow(self) -> bool:
        """Return whether the tabs are wider than the tab bar.

        Inputs: none.
        Outputs: True when the tab bar shows its scroll buttons.
        """
        # LLFR-00025: the scroll buttons are tool buttons of the tab bar.
        tab_bar = self.tabBar()
        return any(not scroll_button.isHidden()
                   for scroll_button in tab_bar.findChildren(QToolButton))

    def schedule_reposition(self) -> None:
        """Move the "+" button now and again once Qt has laid out.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00025: the tab bar may finish its layout later.
        self.reposition_add_button()
        if getattr(self, "reposition_timer", None) is not None:
            self.reposition_timer.start()

    def tabInserted(self, index_i: int) -> None:
        """Move the "+" button after a tab was added.

        Inputs:
            index_i: index of the new tab.
        Outputs: none.
        """
        # LLFR-00025, LLFR-00026: the button follows the new last tab.
        super().tabInserted(index_i)
        self.schedule_reposition()

    def tabRemoved(self, index_i: int) -> None:
        """Move the "+" button after a tab was removed.

        Inputs:
            index_i: index the removed tab had.
        Outputs: none.
        """
        # LLFR-00025, LLFR-00028: the button follows the last tab.
        super().tabRemoved(index_i)
        self.schedule_reposition()

    def resizeEvent(self, event) -> None:
        """Move the "+" button after the widget was resized.

        Inputs:
            event: the QResizeEvent.
        Outputs: none.
        """
        # LLFR-00025: keep the button beside the last tab, also when the
        # new width makes the tabs overflow (or fit again).
        self.limit_tab_bar_width()
        super().resizeEvent(event)
        self.schedule_reposition()

    def showEvent(self, event) -> None:
        """Move the "+" button when the widget is shown.

        Inputs:
            event: the QShowEvent.
        Outputs: none.
        """
        # LLFR-00025: the final geometry is known once shown.
        super().showEvent(event)
        self.schedule_reposition()

    def eventFilter(self, watched, event) -> bool:
        """Move the "+" button when the tab bar changes its geometry.

        Inputs:
            watched: the object that received the event.
            event: the QEvent.
        Outputs: False, so the event is handled normally.
        """
        # LLFR-00025: the tab bar is resized when a tab is renamed. The
        # filter runs before the tab bar lays out its tabs and scroll
        # buttons, so the button is moved again once that is done.
        if watched is self.tabBar() and event.type() in TAB_BAR_EVENT_TUPLE:
            self.schedule_reposition()
        return super().eventFilter(watched, event)


class PlotPanel(QWidget):
    """Panel placed below the top panel, left of the signal list.

    Inputs: none.
    Attributes:
        panel_layout: vertical layout that holds the tab widget.
        tab_widget: the PlotTabWidget with one TabPage per tab.
        add_tab_button: the "+" button beside the last tab.
        page_dict: tab id -> TabPage.
        plot_widget_dict: plot id -> PlotWidget.
        tab_delete_enabled_b: whether "Delete" is enabled in the tab
            menu (LLFR-00066).
    """

    def __init__(self) -> None:
        """Create the panel with an empty tab widget.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        # LLFR-00058: the plot panel exists and is placed by MainWindow.
        self.setObjectName("plot_panel")
        self.panel_layout = QVBoxLayout(self)
        self.panel_layout.setContentsMargins(0, 0, 0, 0)
        # HLFR-00014: the plots are organized in tabs.
        self.tab_widget = PlotTabWidget()
        self.tab_widget.setObjectName("plot_tab_widget")
        self.panel_layout.addWidget(self.tab_widget)
        self.add_tab_button = self.tab_widget.add_tab_button
        self.page_dict = {}
        self.plot_widget_dict = {}
        self.tab_delete_enabled_b = False
        self.add_tab_handler = None
        self.delete_tab_handler = None
        self.rename_tab_handler = None
        self.plot_handler_dict = {}
        # LLFR-00026: the "+" button asks for a new tab.
        self.add_tab_button.clicked.connect(self.request_add_tab)
        # LLFR-00027, LLFR-00029: right-click on a tab opens its menu.
        tab_bar = self.tab_widget.tabBar()
        tab_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tab_bar.customContextMenuRequested.connect(self.show_tab_menu)
        # LLFR-00137: a press on the tab row or the "+" button takes the
        # keyboard focus from the text fields (see eventFilter).
        tab_bar.installEventFilter(self)
        self.add_tab_button.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        """Move the focus to this panel on a press on the tab row.

        Inputs:
            watched: the object that received the event.
            event: the QEvent.
        Outputs: False, so the event is handled normally.
        """
        # LLFR-00137: the tab bar and the "+" button do not take the
        # focus on click, so without this the focus would stay in the
        # search box (also after the tab menu's dialogs close) and
        # Ctrl+Z (Cmd+Z) would undo the typed text instead of the tab
        # action. The panel shows no focus frame.
        if (event.type() == QEvent.Type.MouseButtonPress
                and watched in (self.tab_widget.tabBar(),
                                self.add_tab_button)):
            self.setFocus(Qt.FocusReason.MouseFocusReason)
        return super().eventFilter(watched, event)

    # ----------------------------------------------------------------
    # Handlers
    # ----------------------------------------------------------------

    def set_tab_handlers(self, add_tab_handler, delete_tab_handler,
                         rename_tab_handler) -> None:
        """Set the functions called for the tab requests of the user.

        Inputs:
            add_tab_handler: function without arguments ("+" clicked).
            delete_tab_handler: function taking a tab id ("Delete").
            rename_tab_handler: function taking a tab id and the typed
                name ("Rename").
        Outputs: none.
        """
        # LLFR-00026, LLFR-00028, LLFR-00030: the controller decides.
        self.add_tab_handler = add_tab_handler
        self.delete_tab_handler = delete_tab_handler
        self.rename_tab_handler = rename_tab_handler

    def set_plot_handlers(self, **handler_dict) -> None:
        """Set the functions called for the requests made on a plot.

        Inputs:
            handler_dict: handler name (the values of
                PLOT_SIGNAL_HANDLER_DICT) -> function. Each function gets
                the plot id first, then the arguments of the signal.
        Outputs: none.
        """
        # LLFR-00021, LLFR-00039, LLFR-00041, LLFR-00045, LLFR-00047,
        # LLFR-00049, LLFR-00070: requests go to the controller.
        self.plot_handler_dict.update(handler_dict)

    def forward_plot_request(self, handler_name_str: str, plot_id_i: int,
                             *argument_tuple) -> None:
        """Call a plot handler with the plot id and the signal arguments.

        Inputs:
            handler_name_str: name of the handler.
            plot_id_i: id of the plot that emitted the request.
            argument_tuple: the arguments of the plot widget's signal.
        Outputs: none.
        """
        # LLFR-00021, LLFR-00039, LLFR-00041, LLFR-00045, LLFR-00047,
        # LLFR-00049, LLFR-00070: add the plot id to every request.
        handler = self.plot_handler_dict.get(handler_name_str)
        if handler is not None:
            handler(plot_id_i, *argument_tuple)

    def request_add_tab(self) -> None:
        """Ask the controller for a new tab.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00026: the "+" button adds a new tab.
        if self.add_tab_handler is not None:
            self.add_tab_handler()

    def request_delete_tab(self, tab_id_i: int) -> None:
        """Ask the controller to delete a tab.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: none.
        """
        # LLFR-00028: "Delete" in the tab menu.
        if self.delete_tab_handler is not None:
            self.delete_tab_handler(tab_id_i)

    def request_rename_tab(self, tab_id_i: int) -> None:
        """Ask the user for a new tab name and pass it to the controller.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: none. Nothing happens when the dialog is cancelled.
        """
        # LLFR-00030: let the user type the new name, starting from the
        # current one.
        page = self.page_dict.get(tab_id_i)
        if page is None:
            return
        new_name_str, accepted_b = QInputDialog.getText(
            self, RENAME_DIALOG_TITLE_STR, RENAME_DIALOG_LABEL_STR,
            QLineEdit.EchoMode.Normal, page.name_str)
        if not accepted_b:
            return
        # LLFR-00067: the controller keeps the old name for a blank one.
        if self.rename_tab_handler is not None:
            self.rename_tab_handler(tab_id_i, str(new_name_str))

    # ----------------------------------------------------------------
    # Tab menu
    # ----------------------------------------------------------------

    def tab_id_at_index(self, tab_index_i: int) -> int:
        """Return the id of the tab at an index of the tab widget.

        Inputs:
            tab_index_i: index of the tab.
        Outputs: the tab id, or -1 when there is no tab there.
        """
        # LLFR-00027, LLFR-00029: the menu acts on the clicked tab.
        page = self.tab_widget.widget(tab_index_i)
        if not isinstance(page, TabPage):
            return -1
        return page.tab_id_i

    def build_tab_menu(self, tab_index_i: int) -> QMenu:
        """Build the menu shown by a right-click on a tab.

        Inputs:
            tab_index_i: index of the clicked tab.
        Outputs: a QMenu with "Delete" (disabled when the panel has only
            one tab) and "Rename".
        """
        tab_id_i = self.tab_id_at_index(tab_index_i)
        menu = QMenu(self)
        # LLFR-00027, LLFR-00066: "Delete", disabled on the last tab.
        delete_action = menu.addAction(DELETE_TAB_TEXT_STR)
        delete_action.setEnabled(self.tab_delete_enabled_b
                                 and self.tab_widget.count() > 1)
        delete_action.triggered.connect(
            lambda *_: self.request_delete_tab(tab_id_i))
        # LLFR-00029: "Rename".
        rename_action = menu.addAction(RENAME_TAB_TEXT_STR)
        rename_action.triggered.connect(
            lambda *_: self.request_rename_tab(tab_id_i))
        return menu

    def show_tab_menu(self, position) -> None:
        """Show the tab menu for a right-click on the tab bar.

        Inputs:
            position: the QPoint of the click, in tab bar coordinates.
        Outputs: none.
        """
        # LLFR-00027, LLFR-00029: only a click on a tab opens the menu.
        tab_bar = self.tab_widget.tabBar()
        tab_index_i = tab_bar.tabAt(position)
        if tab_index_i < 0:
            return
        menu = self.build_tab_menu(tab_index_i)
        menu.exec(tab_bar.mapToGlobal(position))
        menu.deleteLater()

    # ----------------------------------------------------------------
    # Tab facade
    # ----------------------------------------------------------------

    def add_tab_view(self, tab_id_i: int, name_str: str) -> None:
        """Add a tab after the last one.

        Inputs:
            tab_id_i: id of the tab in the model.
            name_str: name shown on the tab.
        Outputs: none.
        """
        # LLFR-00024, LLFR-00026: show the new tab.
        if tab_id_i in self.page_dict:
            return
        page = TabPage(tab_id_i, name_str)
        self.page_dict[tab_id_i] = page
        self.tab_widget.addTab(page, escape_tab_text(name_str))

    def remove_tab_view(self, tab_id_i: int) -> None:
        """Remove a tab and all its plots.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: none.
        """
        # LLFR-00028: remove the tab.
        page = self.page_dict.pop(tab_id_i, None)
        if page is None:
            return
        self.move_focus_out_of(page)
        for plot_widget in list(page.plot_widget_list):
            self.plot_widget_dict.pop(plot_widget.plot_id_i, None)
            # LLFR-00138: no late request from the removed plot.
            plot_widget.retire()
        self.tab_widget.removeTab(self.tab_widget.indexOf(page))
        page.deleteLater()

    def rename_tab_view(self, tab_id_i: int, name_str: str) -> None:
        """Show a new name on a tab.

        Inputs:
            tab_id_i: id of the tab.
            name_str: the new name.
        Outputs: none.
        """
        # LLFR-00030: show the name chosen by the user.
        page = self.page_dict.get(tab_id_i)
        if page is None:
            return
        page.name_str = name_str
        self.tab_widget.setTabText(self.tab_widget.indexOf(page),
                                   escape_tab_text(name_str))
        # LLFR-00025: the last tab may have changed its width.
        self.tab_widget.schedule_reposition()

    def clear_tab_views(self) -> None:
        """Remove every tab and plot.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00015: close all tabs and plots of the previous file.
        for tab_id_i in list(self.page_dict):
            self.remove_tab_view(tab_id_i)

    def set_current_tab(self, tab_id_i: int) -> None:
        """Select a tab.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: none.
        """
        # LLFR-00026: a new tab becomes the current one.
        page = self.page_dict.get(tab_id_i)
        if page is not None:
            self.tab_widget.setCurrentWidget(page)

    def current_tab_id(self) -> int:
        """Return the id of the selected tab.

        Inputs: none.
        Outputs: the tab id, or -1 when there is no tab.
        """
        # LLFR-00019: double-click plots go into the current tab.
        page = self.tab_widget.currentWidget()
        if not isinstance(page, TabPage):
            return -1
        return page.tab_id_i

    def tab_name_list(self) -> list:
        """Return the names of the tabs, from left to right.

        Inputs: none.
        Outputs: a list of str.
        """
        # LLFR-00024, LLFR-00030: the names shown on the tabs.
        return [self.tab_widget.widget(index_i).name_str
                for index_i in range(self.tab_widget.count())]

    def set_tab_delete_enabled(self, enabled_b: bool) -> None:
        """Enable or disable "Delete" in the tab menu.

        Inputs:
            enabled_b: False when only one tab is left.
        Outputs: none.
        """
        # LLFR-00066: the last tab cannot be deleted.
        self.tab_delete_enabled_b = bool(enabled_b)

    # ----------------------------------------------------------------
    # Plot facade
    # ----------------------------------------------------------------

    def add_plot_view(self, tab_id_i: int, plot_id_i: int,
                      kind_str: str = TIME_PLOT_KIND_STR) -> None:
        """Create a plot widget at the bottom of a tab.

        Inputs:
            tab_id_i: id of the tab.
            plot_id_i: id of the plot in the model.
            kind_str: TIME_PLOT_KIND_STR or FREQUENCY_PLOT_KIND_STR
                (LLFR-00256).
        Outputs: none.
        """
        # LLFR-00019, LLFR-00069: the new plot goes below the others.
        page = self.page_dict.get(tab_id_i)
        if page is None or plot_id_i in self.plot_widget_dict:
            return
        # LLFR-00256: a time plot or a frequency plot.
        plot_widget = PlotWidget(plot_id_i, kind_str=kind_str)
        plot_widget.setObjectName(f"plot_widget_{plot_id_i}")
        # LLFR-00042, LLFR-00078, LLFR-00081: the new plot starts with no
        # tool; MainWindow.add_plot_view applies the active plot tool.
        # LLFR-00021, LLFR-00039, LLFR-00041, LLFR-00045, LLFR-00047,
        # LLFR-00049, LLFR-00070: every request carries the plot id.
        for signal_name_str, handler_name_str in (
                PLOT_SIGNAL_HANDLER_DICT.items()):
            getattr(plot_widget, signal_name_str).connect(partial(
                self.forward_plot_request, handler_name_str, plot_id_i))
        # LLFR-00205: a marker dragged on this plot follows the pointer
        # on the other plots of its tab. LLFR-00203: so does the marker
        # preview. These stay in the view: only the release and the
        # click go to the controller.
        plot_widget.marker_drag_moved.connect(partial(
            self.relay_marker_drag, plot_id_i))
        plot_widget.marker_preview_changed.connect(partial(
            self.relay_marker_preview, plot_id_i))
        self.plot_widget_dict[plot_id_i] = plot_widget
        page.add_plot_widget(plot_widget)

    def remove_plot_view(self, plot_id_i: int) -> None:
        """Remove a plot widget from its tab.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: none.
        """
        # LLFR-00049: remove the plot and its curves from the tab.
        plot_widget = self.plot_widget_dict.pop(plot_id_i, None)
        if plot_widget is None:
            return
        # LLFR-00138: no late request from the removed plot.
        self.move_focus_out_of(plot_widget)
        plot_widget.retire()
        # LLFR-00050: the page gives the free space to the other plots.
        for page in self.page_dict.values():
            if page.remove_plot_widget(plot_widget):
                break
        # The widget may be running the menu that asked for this, so it
        # is deleted later by the event loop, not now.
        plot_widget.deleteLater()

    def move_focus_out_of(self, removed_widget) -> None:
        """Keep the keyboard focus off text fields when a widget goes.

        Inputs:
            removed_widget: the tab page or plot widget being removed.
        Outputs: none. When the focus is in that widget, it moves to
            this panel instead of to the next widget of the focus chain,
            which could be the search box.
        """
        # LLFR-00137: after an undo removes the clicked plot, the next
        # Ctrl+Z (Cmd+Z) must still run the workspace undo.
        focus_widget = QApplication.focusWidget()
        if focus_widget is None:
            return
        if (focus_widget is removed_widget
                or removed_widget.isAncestorOf(focus_widget)):
            self.setFocus(Qt.FocusReason.OtherFocusReason)

    def sibling_plot_widget_list(self, plot_id_i: int) -> list:
        """Return the other plot widgets of a plot's tab.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: a list of PlotWidget, top to bottom, without the plot
            itself (empty for an unknown plot).
        """
        # LLFR-00203, LLFR-00205: the plots of the same tab.
        plot_widget = self.plot_widget_dict.get(plot_id_i)
        if plot_widget is None:
            return []
        for page in self.page_dict.values():
            if plot_widget in page.plot_widget_list:
                return [other_widget for other_widget in page.plot_widget_list
                        if other_widget is not plot_widget]
        return []

    def set_markers(self, marker_data_list: list) -> None:
        """Draw the shared vertical markers on every plot of every tab.

        Inputs:
            marker_data_list: tuples (marker_id_i, name_str, time_s), in
                placing order.
        Outputs: none.
        """
        # LLFR-00081, LLFR-00086, LLFR-00091, LLFR-00112, LLFR-00205: the
        # same markers on every plot; hidden plots draw them when shown.
        for plot_widget in self.plot_widget_dict.values():
            plot_widget.set_markers(marker_data_list)

    def relay_marker_drag(self, plot_id_i: int, marker_id_i: int,
                          time_s: float) -> None:
        """Show a marker dragged on one plot at its time on the others.

        Inputs:
            plot_id_i: id of the plot where the marker is dragged.
            marker_id_i: id of the dragged marker.
            time_s: the time it is shown at, in seconds.
        Outputs: none.
        """
        # LLFR-00205: while dragged, the marker follows the pointer on
        # every plot of the current tab; the plots of the other tabs get
        # the new time when the button is released (controller).
        for plot_widget in self.sibling_plot_widget_list(plot_id_i):
            plot_widget.follow_marker_drag(marker_id_i, time_s)

    def relay_marker_preview(self, plot_id_i: int, time_s: float) -> None:
        """Show the marker preview of the hovered plot on the others.

        Inputs:
            plot_id_i: id of the hovered plot.
            time_s: time of the preview in seconds, NaN when it is hidden.
        Outputs: none.
        """
        # LLFR-00203: the preview is shown on every plot of the current
        # tab (the hovered plot is in it); the other tabs need none.
        for plot_widget in self.sibling_plot_widget_list(plot_id_i):
            plot_widget.show_marker_preview(time_s)

    def plot_view(self, plot_id_i: int):
        """Return the plot widget of a plot.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: the PlotWidget, or None for an unknown id.
        """
        # LLFR-00020, LLFR-00021: the widget the controller draws in.
        return self.plot_widget_dict.get(plot_id_i)

    def is_mouse_drag_in_progress(self) -> bool:
        """Tell whether the user is dragging the mouse on any plot.

        Inputs: none.
        Outputs: True while a pan, a marker or tip drag or a time span
            selection is in progress on a plot of any tab.
        """
        # LLFR-00207: the Z key does nothing during a mouse drag.
        return any(plot_widget.is_mouse_drag_in_progress()
                   for plot_widget in self.plot_widget_dict.values())

    def plot_id_list(self, tab_id_i: int) -> list:
        """Return the plot ids of a tab, from top to bottom.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: a list of int (empty for an unknown tab).
        """
        # LLFR-00069: the order in which the plots are stacked.
        page = self.page_dict.get(tab_id_i)
        if page is None:
            return []
        return [plot_widget.plot_id_i
                for plot_widget in page.plot_widget_list]
