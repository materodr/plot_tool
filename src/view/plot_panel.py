"""Plot panel: the tabs that hold the plots (HLFR-00014).

The panel shows a QTabWidget whose pages are TabPage widgets, each with
its PlotWidgets. The tabs are aligned to the left (LLFR-00106). A "+"
button sits directly beside the last tab (LLFR-00025), or at the right
end of the tab row when the tabs overflow and the tab bar scrolls, and
it is styled like an unselected tab, only narrower (LLFR-00107). A
right-click on a tab opens a menu with "Delete", "Rename" and "Plot
matrix" (LLFR-00027, LLFR-00029, LLFR-01061); "Plot matrix" opens the
matrix picker of view.matrix_picker (LLFR-01062). "Position" in the
plot menu and the area menu of a plot opens the position picker of its
tab (LLFR-01079), and the chosen slot goes to the controller as a swap
(LLFR-01083).

The tabs can be dragged along the tab row (LLFR-01051): Qt's movable
tab bar moves the tab with the pointer, the others making room, and
keeps it in the row when the pointer leaves it (LLFR-01053). When the
left button is released, the tab's new place goes to the controller,
which keeps it as one undoable action (LLFR-01052, LLFR-01054); a tab
released at its starting place reports nothing (LLFR-01055). A tab
released outside the main window goes back to its starting place and
is undocked at the drop point instead, like a browser tab (LLFR-01107),
unless it is the last docked tab (LLFR-01109).

It offers a plain-Python facade (ids of the model, names, bools; no Qt
types), used through MainWindow by the plot controller (COR-00009).
Tabs and plots are always found by id, never by index.
"""

from functools import partial

from PyQt6.QtCore import QEvent, QPoint, QRect, QTimer, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QApplication, QInputDialog, QLineEdit, QMenu, QStyle,
    QStyleOptionTabWidgetFrame, QTabBar, QTabWidget, QToolButton,
    QVBoxLayout, QWidget)

from model.workspace import TIME_PLOT_KIND_STR
from view import theme
from view.matrix_picker import (
    MatrixPicker, PositionPicker, add_picker_submenu)
from view.plot_widget import PlotWidget
from view.tab_page import TabPage
from view.window_buttons import (
    DOCK_BUTTON_OBJECT_NAME_STR, UNDOCK_BUTTON_OBJECT_NAME_STR,
    build_undock_button)

# LLFR-00977, LLFR-00990: the object names of the buttons inside tabs.
TAB_ICON_BUTTON_NAME_TUPLE = (UNDOCK_BUTTON_OBJECT_NAME_STR,
                              DOCK_BUTTON_OBJECT_NAME_STR)

ADD_TAB_TEXT_STR = "+"
ADD_TAB_TOOL_TIP_STR = "Add a new tab"
DELETE_TAB_TEXT_STR = "Delete"
RENAME_TAB_TEXT_STR = "Rename"
# LLFR-01061: the option of the tab menu that opens the matrix picker.
PLOT_MATRIX_TEXT_STR = "Plot matrix"
# LLFR-01051: no tab is pressed for a drag.
NO_TAB_ID_I = -1
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
    # LLFR-00297: the dropped names, one or several, as a list.
    "signals_dropped": "signals_drop_handler",
    "tip_pin_requested": "tip_pin_handler",
    "pinned_tip_delete_requested": "pinned_tip_delete_handler",
    # LLFR-00152: a pinned tip was dragged and released.
    "pinned_tip_move_requested": "pinned_tip_move_handler",
    "time_range_changed": "time_range_handler",
    "marker_place_requested": "marker_place_handler",
    "marker_move_requested": "marker_move_handler",
    "marker_rename_requested": "marker_rename_handler",
    # LLFR-00392: "Color" chosen in a flag's menu.
    "marker_color_requested": "marker_color_handler",
    "marker_delete_requested": "marker_delete_handler",
    # LLFR-00163, LLFR-00164: a curve point picked with a delta tool.
    "delta_point_picked": "delta_point_pick_handler",
    # LLFR-00176: "Delete" chosen on a delta marker.
    "delta_marker_delete_requested": "delta_marker_delete_handler",
    # LLFR-00409: an entry of the "Color" submenu of a delta marker.
    "delta_marker_color_requested": "delta_marker_color_handler",
    # LLFR-00429, LLFR-00420: "Rename" of a delta marker, or a
    # double-click on its label.
    "delta_marker_rename_requested": "delta_marker_rename_handler",
    # LLFR-00304, LLFR-00312, LLFR-00313, LLFR-00315, LLFR-00316: an
    # area created, moved or resized, renamed or deleted.
    "area_create_requested": "area_create_handler",
    "area_change_requested": "area_change_handler",
    "area_rename_requested": "area_rename_handler",
    # LLFR-00351: "Color" chosen in an area's menu.
    "area_color_requested": "area_color_handler",
    "area_delete_requested": "area_delete_handler",
    # LLFR-00334, LLFR-00339, LLFR-00342, LLFR-00343: the text notes.
    "text_note_create_requested": "text_note_create_handler",
    "text_note_move_requested": "text_note_move_handler",
    "text_note_edit_requested": "text_note_edit_handler",
    "text_note_delete_requested": "text_note_delete_handler",
    # LLFR-00385, LLFR-00387: the size and the colors of a text note.
    "text_note_size_requested": "text_note_size_handler",
    "text_note_border_color_requested": "text_note_border_color_handler",
    "text_note_text_color_requested": "text_note_text_color_handler",
    # LLFR-00372, LLFR-00376, LLFR-00377, LLFR-00379, LLFR-00380: an
    # arrow drawn, moved, rotated or stretched, recolored or deleted.
    "arrow_create_requested": "arrow_create_handler",
    "arrow_change_requested": "arrow_change_handler",
    "arrow_color_requested": "arrow_color_handler",
    "arrow_delete_requested": "arrow_delete_handler",
    # LLFR-00439, LLFR-00420: "Rename" of an arrow, or a double-click on
    # its label.
    "arrow_rename_requested": "arrow_rename_handler",
    # LLFR-00412 to LLFR-00417: the "Delete all ..." menu options.
    "plot_pinned_tips_delete_requested": "plot_pinned_tips_delete_handler",
    "all_pinned_tips_delete_requested": "all_pinned_tips_delete_handler",
    "plot_delta_markers_delete_requested":
        "plot_delta_markers_delete_handler",
    "all_delta_markers_delete_requested": "all_delta_markers_delete_handler",
    "all_markers_delete_requested": "all_markers_delete_handler",
    "all_areas_delete_requested": "all_areas_delete_handler",
    # LLFR-00433, LLFR-00794: a point of a delta marker dragged to
    # another sample of its curve.
    "delta_point_move_requested": "delta_point_move_handler",
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
        # LLFR-01051, LLFR-01053: a tab is dragged along the tab row, the
        # other tabs moving aside; Qt keeps it in the row.
        tab_bar.setMovable(True)
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

    def pane_rect(self):
        """Return the rectangle of the plot well, below the tab row.

        Inputs: none.
        Outputs: a QRect, in this widget's coordinates, of the pane that
            Qt paints with the plot well style (LLFR-00893): its border
            included, its top edge under the tab row.
        """
        # LLFR-00893, LLFR-00894: the same rectangle Qt lays out and
        # paints the pane in, with the style sheet's offsets applied.
        option = QStyleOptionTabWidgetFrame()
        self.initStyleOption(option)
        return self.style().subElementRect(
            QStyle.SubElement.SE_TabWidgetTabPane, option, self)

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
        # LLFR-00025: the scroll buttons are tool buttons of the tab bar;
        # LLFR-00977, LLFR-00990: the undock and dock buttons of the tabs
        # are not.
        tab_bar = self.tabBar()
        return any(not scroll_button.isHidden()
                   for scroll_button in tab_bar.findChildren(QToolButton)
                   if scroll_button.objectName()
                   not in TAB_ICON_BUTTON_NAME_TUPLE)

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
        # LLFR-00119, LLFR-00916: the time range of the open data files,
        # given to every plot, the new ones too.
        self.files_time_range_tuple = ()
        self.tab_delete_enabled_b = False
        self.add_tab_handler = None
        self.delete_tab_handler = None
        self.rename_tab_handler = None
        # LLFR-01052, LLFR-01065: the tab move and the matrix choice.
        self.move_tab_handler = None
        self.plot_matrix_handler = None
        # LLFR-01051: the tab pressed for a drag, its place at the press
        # and whether the pointer moved with the button held.
        self.pressed_tab_id_i = NO_TAB_ID_I
        self.pressed_tab_index_i = -1
        self.tab_drag_in_progress_b = False
        # LLFR-01062, LLFR-01079: the picker that is open, if any.
        self.open_picker = None
        # LLFR-00980: the undock button of each docked tab, and the
        # function called with the tab id when one is clicked.
        self.undock_button_dict = {}
        self.undock_handler = None
        # LLFR-01107: the function called with the tab id and the x and
        # y of the drop point when a tab is dropped outside the plot
        # panel.
        self.undock_drop_handler = None
        # LLFR-01115: the function called with the tab id and the x and
        # y of the drop point, which returns True when the point is over
        # an undocked window and the drop went to it; set by MainWindow.
        self.window_drop_function = None
        # LLFR-00203, LLFR-00665: the function that returns the pages
        # the undocked windows show; set by MainWindow.
        self.undocked_shown_page_function = None
        # LLFR-00983: whether the undock buttons are enabled.
        self.undock_enabled_b = False
        self.plot_handler_dict = {}
        # LLFR-00026: the "+" button asks for a new tab.
        self.add_tab_button.clicked.connect(self.request_add_tab)
        # LLFR-00027, LLFR-00029: right-click on a tab opens its menu.
        tab_bar = self.tab_widget.tabBar()
        tab_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tab_bar.customContextMenuRequested.connect(self.show_tab_menu)
        # LLFR-01112: the icon of each tab button has its tab's text
        # color, so it follows the selection.
        self.tab_widget.currentChanged.connect(
            lambda *_: self.refresh_undock_button_looks())
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
        # LLFR-01051 to LLFR-01055: follow a drag of a tab.
        if watched is self.tab_widget.tabBar():
            self.follow_tab_drag_event(event)
        # LLFR-00421: a left double-click on a tab acts as "Rename" in
        # its menu.
        if (event.type() == QEvent.Type.MouseButtonDblClick
                and watched is self.tab_widget.tabBar()
                and event.button() == Qt.MouseButton.LeftButton):
            self.double_click_tab_at(event.position().toPoint())
        return super().eventFilter(watched, event)

    def follow_tab_drag_event(self, event) -> None:
        """Keep track of a tab drag from the press to the release.

        Inputs:
            event: an event of the tab bar.
        Outputs: none. The release reports the tab's new place once Qt
            has finished moving it.
        """
        event_type = event.type()
        if (event_type == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton):
            # LLFR-01051: the press on a tab starts a possible drag.
            tab_index_i = self.tab_widget.tabBar().tabAt(
                event.position().toPoint())
            self.pressed_tab_id_i = self.tab_id_at_index(tab_index_i)
            self.pressed_tab_index_i = tab_index_i
            self.tab_drag_in_progress_b = False
        elif (event_type == QEvent.Type.MouseMove
              and self.pressed_tab_id_i != NO_TAB_ID_I
              and event.buttons() & Qt.MouseButton.LeftButton):
            # LLFR-00454: from the first move, the 0 key does nothing.
            self.tab_drag_in_progress_b = True
        elif (event_type == QEvent.Type.MouseButtonRelease
              and event.button() == Qt.MouseButton.LeftButton
              and self.pressed_tab_id_i != NO_TAB_ID_I):
            # LLFR-01107: where a dragged tab was dropped, in desktop
            # pixels; a click is no drop.
            release_tuple = ()
            if self.tab_drag_in_progress_b:
                release_point = event.globalPosition().toPoint()
                release_tuple = (release_point.x(), release_point.y())
            # LLFR-01052: the place is read once Qt has handled the
            # release.
            QTimer.singleShot(0, partial(
                self.finish_tab_drag, self.pressed_tab_id_i,
                self.pressed_tab_index_i, release_tuple))
            self.pressed_tab_id_i = NO_TAB_ID_I
            self.tab_drag_in_progress_b = False

    def finish_tab_drag(self, tab_id_i: int, start_index_i: int,
                        release_tuple: tuple = ()) -> None:
        """Report where a dragged tab was left.

        Inputs:
            tab_id_i: id of the dragged tab.
            start_index_i: its place when the button was pressed.
            release_tuple: (x, y) of the release in desktop pixels, or
                () for a release that ends no drag.
        Outputs: none. Nothing is reported when the tab is back at its
            starting place (LLFR-01055) or is gone. A tab dropped
            outside the main window is undocked there (LLFR-01107).
        """
        # LLFR-01052, LLFR-01054: a tab left at another place.
        page = self.page_dict.get(tab_id_i)
        if page is None:
            return
        index_i = self.tab_widget.indexOf(page)
        if len(release_tuple) == 2 and self.undock_enabled_b and (
                self.is_window_drop(*release_tuple)
                or not self.is_point_in_plot_panel(*release_tuple)):
            # LLFR-01107, LLFR-01115: the tab leaves from its place in the
            # tab order, so the move Qt made during the drag is taken
            # back first; LLFR-01109: the last docked tab (undock
            # disabled) is kept.
            if index_i >= 0 and index_i != start_index_i:
                self.tab_widget.tabBar().moveTab(index_i, start_index_i)
            # LLFR-01115: on an undocked window, into that window.
            if (self.window_drop_function is not None
                    and self.window_drop_function(tab_id_i,
                                                  *release_tuple)):
                return
            # LLFR-01107: anywhere else outside the plot panel, into a
            # new undocked window at the drop point.
            if self.undock_drop_handler is not None:
                self.undock_drop_handler(tab_id_i, *release_tuple)
            return
        if index_i < 0 or index_i == start_index_i:
            return
        if self.move_tab_handler is not None:
            self.move_tab_handler(tab_id_i, index_i)

    def is_window_drop(self, x_i: int, y_i: int) -> bool:
        """Tell whether a desktop point is over an undocked window.

        Inputs:
            x_i, y_i: the point, in desktop pixels.
        Outputs: True when MainWindow finds an undocked window there.
        """
        # LLFR-01115: a drop on an undocked window moves the tab there.
        is_over_function = getattr(self, "window_at_point_function", None)
        return is_over_function is not None and is_over_function(
            x_i, y_i) is not None

    def is_point_in_plot_panel(self, x_i: int, y_i: int) -> bool:
        """Tell whether a desktop point is on this plot panel.

        Inputs:
            x_i, y_i: the point, in desktop pixels.
        Outputs: True when the point is inside the panel's rectangle.
        """
        # LLFR-01107: a drop outside the plot panel undocks the tab;
        # LLFR-01053: a drop inside it, off the tab row, does not.
        top_left = self.mapToGlobal(QPoint(0, 0))
        return QRect(top_left.x(), top_left.y(), self.width(),
                     self.height()).contains(QPoint(int(x_i), int(y_i)))

    def is_point_in_main_window(self, x_i: int, y_i: int) -> bool:
        """Tell whether a desktop point is on the main window.

        Inputs:
            x_i, y_i: the point, in desktop pixels.
        Outputs: True when the point is inside the frame of the window
            that holds this panel.
        """
        # LLFR-01107: a drop outside the main window undocks the tab;
        # LLFR-01053: a drop inside it, off the tab row, does not.
        return self.window().frameGeometry().contains(QPoint(int(x_i),
                                                             int(y_i)))

    def tab_row_rect(self):
        """Return the tab row of the main window on the desktop.

        Inputs: none.
        Outputs: a QRect in desktop pixels, across the whole width of the
            tab widget, from its top to the bottom of the tab bar.
        """
        # LLFR-01108: the row of the docked tabs and the "+" button.
        tab_widget = self.tab_widget
        tab_bar = tab_widget.tabBar()
        top_left = tab_widget.mapToGlobal(QPoint(0, 0))
        bottom_i = tab_bar.mapToGlobal(QPoint(0, tab_bar.height())).y()
        return QRect(top_left.x(), top_left.y(), tab_widget.width(),
                     max(bottom_i - top_left.y(), 1))

    def docked_drop_index(self, x_i: int, y_i: int) -> int:
        """Return where a tab dropped at a desktop point is docked.

        Inputs:
            x_i, y_i: the point of the drop, in desktop pixels.
        Outputs: the place among the docked tabs, from 0: before the
            first docked tab whose middle is right of the point, or
            after the last one; -1 when the point is not on the tab row
            of the main window, which is then not shown.
        """
        # LLFR-01108, LLFR-01032: only a drop on the main tab row.
        if not self.window().isVisible() or self.window().isMinimized():
            return -1
        if not self.tab_row_rect().contains(QPoint(int(x_i), int(y_i))):
            return -1
        # LLFR-01135: before the first docked tab whose middle is right
        # of the pointer, else after the last one.
        tab_bar = self.tab_widget.tabBar()
        for index_i in range(tab_bar.count()):
            middle_x_i = tab_bar.mapToGlobal(
                tab_bar.tabRect(index_i).center()).x()
            if int(x_i) < middle_x_i:
                return index_i
        return tab_bar.count()

    def is_tab_drag_in_progress(self) -> bool:
        """Tell whether the user is dragging a tab.

        Inputs: none.
        Outputs: True from the first move with the button held on a tab
            to the release. A drag whose release was never seen (for
            example the window lost the mouse) ends as soon as the left
            button is no longer down.
        """
        # LLFR-00454: a tab drag is a mouse drag; a lost release must not
        # keep the 0 key blocked.
        if self.tab_drag_in_progress_b and not self.left_button_down():
            self.tab_drag_in_progress_b = False
            self.pressed_tab_id_i = NO_TAB_ID_I
        return self.tab_drag_in_progress_b

    def left_button_down(self) -> bool:
        """Tell whether the left mouse button is down.

        Inputs: none.
        Outputs: True while the application sees the left button held.
            Tests replace this method, since events they send do not
            change the button state of the application.
        """
        # LLFR-00454: the end of a tab drag whose release was lost.
        return bool(QApplication.mouseButtons()
                    & Qt.MouseButton.LeftButton)

    def double_click_tab_at(self, position) -> None:
        """Rename the tab under a left double-click on the tab bar.

        Inputs:
            position: the QPoint of the double-click, in tab bar
                coordinates.
        Outputs: none. A double-click beside the tabs does nothing. The
            rename dialog opens once control is back in Qt, so it is not
            run inside the mouse event.
        """
        # LLFR-00421: as "Rename" in the tab menu (LLFR-00030), with the
        # same checks of the typed name in the controller.
        tab_id_i = self.tab_id_at_index(
            self.tab_widget.tabBar().tabAt(position))
        if tab_id_i < 0:
            return
        QTimer.singleShot(0, partial(self.request_rename_tab, tab_id_i))

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

    def set_tab_arrangement_handlers(self, move_tab_handler,
                                     plot_matrix_handler) -> None:
        """Set the functions called for a tab move and a matrix choice.

        Inputs:
            move_tab_handler: function taking a tab id and its new place,
                from 0 (LLFR-01052).
            plot_matrix_handler: function taking a tab id, a number of
                rows and a number of columns (LLFR-01065).
        Outputs: none.
        """
        # LLFR-01052, LLFR-01065: the controller decides.
        self.move_tab_handler = move_tab_handler
        self.plot_matrix_handler = plot_matrix_handler

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
        # LLFR-00988: over the window that shows the tab.
        new_name_str, accepted_b = QInputDialog.getText(
            page.window(), RENAME_DIALOG_TITLE_STR, RENAME_DIALOG_LABEL_STR,
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
            one tab), "Rename" and "Plot matrix".
        """
        # LLFR-00027, LLFR-00029, LLFR-01061: the menu of a docked tab.
        return self.build_tab_menu_of(self.tab_id_at_index(tab_index_i),
                                      False)

    def build_tab_menu_of(self, tab_id_i: int, undocked_b: bool,
                          parent=None) -> QMenu:
        """Build the tab menu of a tab, docked or undocked.

        Inputs:
            tab_id_i: id of the tab.
            undocked_b: True for the tab button of an undocked window.
            parent: the parent of the menu; None for this panel.
        Outputs: a QMenu with "Delete", "Rename" and "Plot matrix".
        """
        menu = QMenu(self if parent is None else parent)
        # LLFR-00027, LLFR-00066: "Delete", disabled on the last docked
        # tab; LLFR-01034: always enabled on an undocked tab.
        delete_action = menu.addAction(DELETE_TAB_TEXT_STR)
        delete_action.setEnabled(undocked_b or (
            self.tab_delete_enabled_b and self.tab_widget.count() > 1))
        delete_action.triggered.connect(
            lambda *_: self.request_delete_tab(tab_id_i))
        # LLFR-00029: "Rename".
        rename_action = menu.addAction(RENAME_TAB_TEXT_STR)
        rename_action.triggered.connect(
            lambda *_: self.request_rename_tab(tab_id_i))
        # LLFR-01061: "Plot matrix", directly below "Rename"; LLFR-01062:
        # its picker opens beside the menu as a submenu, with no click.
        add_picker_submenu(menu, PLOT_MATRIX_TEXT_STR, partial(
            self.build_matrix_picker, tab_id_i, embedded_b=True))
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

    def show_tab_menu_of(self, tab_id_i: int, global_point,
                         undocked_b: bool) -> None:
        """Show the tab menu of a tab at a point of the screen.

        Inputs:
            tab_id_i: id of the tab.
            global_point: QPoint in screen coordinates.
            undocked_b: True for the tab button of an undocked window.
        Outputs: none.
        """
        # LLFR-01029: the tab menu on the tab button of a window, over
        # that window (LLFR-00988).
        page = self.page_dict.get(tab_id_i)
        if page is None:
            return
        menu = self.build_tab_menu_of(tab_id_i, undocked_b, page.window())
        menu.exec(global_point)
        menu.deleteLater()

    # ----------------------------------------------------------------
    # Pickers of the plot matrix
    # ----------------------------------------------------------------

    def show_picker(self, picker, global_point) -> None:
        """Show a picker, closing one that is still open.

        Inputs:
            picker: a MatrixPicker or a PositionPicker.
            global_point: QPoint in screen coordinates of its top-left
                corner.
        Outputs: none. Tests replace this method to work with the picker
            without showing it.
        """
        # LLFR-01062, LLFR-01079: one picker at a time; the one shown
        # before is deleted.
        if self.open_picker is not None and self.open_picker is not picker:
            try:
                self.open_picker.close()
                self.open_picker.deleteLater()
            except RuntimeError:
                # LLFR-00988: it was deleted with its undocked window.
                pass
        self.open_picker = picker
        picker.show_at(global_point)

    def build_matrix_picker(self, tab_id_i: int, parent=None,
                            embedded_b: bool = False):
        """Build the matrix picker of a tab.

        Inputs:
            tab_id_i: id of the tab.
            parent: the parent of the picker; None for the window that
                shows the tab.
            embedded_b: True for the picker of the "Plot matrix" submenu
                (LLFR-01062).
        Outputs: a MatrixPicker, or None for an unknown tab.
        """
        # LLFR-00988: over the window that shows the tab.
        # LLFR-01062, LLFR-01064, LLFR-01071: the tab's current matrix
        # and its number of plots.
        page = self.page_dict.get(tab_id_i)
        if page is None:
            return None
        return MatrixPicker(
            page.row_count_i, page.column_count_i,
            len(page.plot_widget_list),
            partial(self.request_matrix_choice, tab_id_i),
            page.window() if parent is None else parent, embedded_b)

    def request_plot_matrix(self, tab_id_i: int,
                            global_point=None) -> None:
        """Open the matrix picker of a tab.

        Inputs:
            tab_id_i: id of the tab.
            global_point: QPoint in screen coordinates where the picker
                opens, or None for the pointer position.
        Outputs: none.
        """
        # LLFR-01062: "Plot matrix" in the tab menu.
        picker = self.build_matrix_picker(tab_id_i)
        if picker is None:
            return
        if global_point is None:
            global_point = QCursor.pos()
        self.show_picker(picker, QPoint(global_point))

    def request_matrix_choice(self, tab_id_i: int, row_count_i: int,
                              column_count_i: int) -> None:
        """Pass the square chosen in the matrix picker to the controller.

        Inputs:
            tab_id_i: id of the tab.
            row_count_i: rows of the chosen square.
            column_count_i: columns of the chosen square.
        Outputs: none.
        """
        # LLFR-01065: the controller gives the tab the plot matrix.
        if self.plot_matrix_handler is not None:
            self.plot_matrix_handler(tab_id_i, row_count_i, column_count_i)

    def page_of_plot(self, plot_id_i: int):
        """Return the tab page that holds a plot.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: the TabPage, or None for an unknown plot.
        """
        # LLFR-01079: the picker has the matrix of the plot's tab.
        plot_widget = self.plot_widget_dict.get(plot_id_i)
        for page in self.page_dict.values():
            if plot_widget is not None and plot_widget in (
                    page.plot_widget_list):
                return page
        return None

    def build_position_picker(self, plot_id_i: int, parent=None,
                              embedded_b: bool = False):
        """Build the position picker of a plot.

        Inputs:
            plot_id_i: id of the plot.
            parent: the parent of the picker; None for the window that
                shows the tab.
            embedded_b: True for the picker of the "Position" submenu
                (LLFR-01079).
        Outputs: a PositionPicker, or None for an unknown plot.
        """
        # LLFR-00988: over the window that shows the tab.
        # LLFR-01079 to LLFR-01082: the tab's matrix, its occupied slots
        # and the plot's own slot.
        page = self.page_of_plot(plot_id_i)
        if page is None:
            return None
        row_index_i, column_index_i = page.plot_slot_tuple(
            self.plot_widget_dict[plot_id_i])
        return PositionPicker(
            page.row_count_i, page.column_count_i,
            len(page.plot_widget_list),
            (row_index_i + 1, column_index_i + 1),
            partial(self.request_position_choice, plot_id_i),
            page.window() if parent is None else parent, embedded_b)

    def request_plot_position(self, plot_id_i: int) -> None:
        """Open the position picker of a plot at the pointer.

        Inputs:
            plot_id_i: id of the plot whose "Position" was chosen.
        Outputs: none.
        """
        # LLFR-01077, LLFR-01078, LLFR-01079.
        picker = self.build_position_picker(plot_id_i)
        if picker is None:
            return
        self.show_picker(picker, QCursor.pos())

    def request_position_choice(self, plot_id_i: int, row_i: int,
                                column_i: int) -> None:
        """Pass the slot chosen in the position picker to the controller.

        Inputs:
            plot_id_i: id of the plot the picker was opened from.
            row_i: row of the chosen slot, from 1.
            column_i: column of the chosen slot, from 1.
        Outputs: none. The controller swaps the two plots (LLFR-01083);
            for the plot's own slot it changes nothing (LLFR-01086).
        """
        page = self.page_of_plot(plot_id_i)
        if page is None:
            return
        other_widget = page.plot_widget_at_slot(row_i - 1, column_i - 1)
        if other_widget is None:
            return
        # LLFR-01083: swap with the plot of the chosen slot.
        handler = self.plot_handler_dict.get("plot_swap_handler")
        if handler is not None:
            handler(plot_id_i, other_widget.plot_id_i)

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
        self.add_page_to_tab_row(page)

    def add_page_to_tab_row(self, page) -> None:
        """Add a tab page after the last docked tab, with its button.

        Inputs:
            page: the TabPage.
        Outputs: none.
        """
        # LLFR-00025, LLFR-00993: after the last docked tab.
        index_i = self.tab_widget.addTab(page, escape_tab_text(
            page.name_str))
        # LLFR-00977: the undock button inside the tab, right of the
        # tab's name; LLFR-00983: none on the last docked tab.
        undock_button = build_undock_button()
        undock_button.button.clicked.connect(partial(self.request_undock,
                                                     page.tab_id_i))
        self.undock_button_dict[page.tab_id_i] = undock_button
        self.place_undock_button(index_i, undock_button)
        self.refresh_undock_button_looks()
        self.tab_widget.schedule_reposition()

    def place_undock_button(self, index_i: int, undock_button) -> None:
        """Show or leave out the undock button of the tab at an index.

        Inputs:
            index_i: index of the tab in the tab row.
            undock_button: its TabIconButton.
        Outputs: none. While the main window holds one docked tab, the
            tab shows no button at all, and its width has no room for
            one (LLFR-00983, LLFR-01120).
        """
        tab_bar = self.tab_widget.tabBar()
        if self.undock_enabled_b:
            # LLFR-00977: inside the tab, right of its name.
            if tab_bar.tabButton(index_i, QTabBar.ButtonPosition.RightSide
                                 ) is not undock_button:
                tab_bar.setTabButton(index_i,
                                     QTabBar.ButtonPosition.RightSide,
                                     undock_button)
            undock_button.show()
            return
        # LLFR-00983: no undock button on the last docked tab.
        if tab_bar.tabButton(index_i,
                             QTabBar.ButtonPosition.RightSide) is not None:
            tab_bar.setTabButton(index_i, QTabBar.ButtonPosition.RightSide,
                                 None)
        undock_button.hide()

    def refresh_undock_button_looks(self) -> None:
        """Draw each undock button in the text color of its tab.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01112: the selected tab has darker text than the others.
        current_page = self.tab_widget.currentWidget()
        for tab_id_i, undock_button in self.undock_button_dict.items():
            try:
                undock_button.set_selected_look(
                    self.page_dict.get(tab_id_i) is current_page)
            except RuntimeError:
                # The button was deleted with its tab.
                continue

    def request_undock(self, tab_id_i: int) -> None:
        """Ask the controller to undock a tab.

        Inputs:
            tab_id_i: id of the tab whose undock button was clicked.
        Outputs: none.
        """
        # LLFR-00980: the undock button; LLFR-00984: a disabled button
        # sends no click.
        if self.undock_handler is not None:
            self.undock_handler(tab_id_i)

    def set_undock_enabled(self, enabled_b: bool) -> None:
        """Enable or disable every undock button.

        Inputs:
            enabled_b: False while the main window holds one docked tab.
        Outputs: none.
        """
        # LLFR-00983: no undock button on the last docked tab.
        self.undock_enabled_b = bool(enabled_b)
        for tab_id_i, undock_button in self.undock_button_dict.items():
            index_i = self.tab_widget.indexOf(self.page_dict.get(tab_id_i))
            if index_i >= 0:
                self.place_undock_button(index_i, undock_button)
        self.tab_widget.schedule_reposition()

    def undock_button_of(self, tab_id_i: int):
        """Return the undock button of a docked tab.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: the QToolButton, or None for an undocked or unknown tab.
        """
        # LLFR-00977: each docked tab has one.
        return self.undock_button_dict.get(tab_id_i)

    def detach_page(self, tab_id_i: int):
        """Take a tab page out of the tab row of the main window.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: the TabPage, kept in page_dict with its plots, or None.
        """
        # LLFR-00980, LLFR-00985: the page moves with all it holds.
        page = self.page_dict.get(tab_id_i)
        if page is None:
            return None
        index_i = self.tab_widget.indexOf(page)
        if index_i >= 0:
            self.tab_widget.removeTab(index_i)
        # LLFR-01031: an undocked tab has no undock button.
        undock_button = self.undock_button_dict.pop(tab_id_i, None)
        if undock_button is not None:
            undock_button.deleteLater()
        self.tab_widget.schedule_reposition()
        return page

    def attach_page(self, tab_id_i: int) -> None:
        """Put a detached tab page back as the last docked tab.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: none.
        """
        # LLFR-00993: directly left of the "+" button.
        page = self.page_dict.get(tab_id_i)
        if page is None or self.tab_widget.indexOf(page) >= 0:
            return
        self.add_page_to_tab_row(page)

    def is_page_docked(self, tab_id_i: int) -> bool:
        """Tell whether a tab page is in the tab row of the main window.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: True for a docked tab.
        """
        # LLFR-00977: the docked tabs of the main window.
        page = self.page_dict.get(tab_id_i)
        return page is not None and self.tab_widget.indexOf(page) >= 0

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
        index_i = self.tab_widget.indexOf(page)
        if index_i >= 0:
            self.tab_widget.removeTab(index_i)
        self.undock_button_dict.pop(tab_id_i, None)
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
        index_i = self.tab_widget.indexOf(page)
        if index_i >= 0:
            self.tab_widget.setTabText(index_i, escape_tab_text(name_str))
        # LLFR-00025: the last tab may have changed its width.
        self.tab_widget.schedule_reposition()

    def clear_tab_views(self) -> None:
        """Remove every tab and plot.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00024, LLFR-00138: every tab and plot is shown again from
        # the model.
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
        # LLFR-00982, LLFR-00995: only a docked tab is shown in the main
        # window.
        if page is not None and self.tab_widget.indexOf(page) >= 0:
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

    def move_tab_view(self, tab_id_i: int, index_i: int) -> None:
        """Move a tab to a place in the tab row.

        Inputs:
            tab_id_i: id of the tab.
            index_i: its new place, from 0.
        Outputs: none. Nothing moves when the tab is already there, as
            after a drag (LLFR-01052).
        """
        # LLFR-01052, LLFR-01056: the order of the model.
        page = self.page_dict.get(tab_id_i)
        if page is None:
            return
        tab_bar = self.tab_widget.tabBar()
        from_index_i = self.tab_widget.indexOf(page)
        index_i = max(0, min(int(index_i), tab_bar.count() - 1))
        if from_index_i >= 0 and from_index_i != index_i:
            tab_bar.moveTab(from_index_i, index_i)
        # LLFR-00025: the "+" button stays right of the last tab.
        self.tab_widget.schedule_reposition()

    def set_tab_matrix_view(self, tab_id_i: int, row_count_i: int,
                            column_count_i: int) -> None:
        """Lay the plots of a tab out in a plot matrix.

        Inputs:
            tab_id_i: id of the tab.
            row_count_i: number of rows.
            column_count_i: number of columns.
        Outputs: none.
        """
        # LLFR-01065, LLFR-01067, LLFR-01073 to LLFR-01076.
        page = self.page_dict.get(tab_id_i)
        if page is not None:
            page.set_plot_matrix(row_count_i, column_count_i)

    def set_plot_order_view(self, tab_id_i: int,
                            plot_id_list: list) -> None:
        """Place the plots of a tab in a new fill order.

        Inputs:
            tab_id_i: id of the tab.
            plot_id_list: the plot ids in fill order.
        Outputs: none.
        """
        # LLFR-01083, LLFR-01084: the same widgets, in other slots.
        page = self.page_dict.get(tab_id_i)
        if page is None:
            return
        page.set_plot_order([self.plot_widget_dict[plot_id_i]
                             for plot_id_i in plot_id_list
                             if plot_id_i in self.plot_widget_dict])

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

    def set_files_time_range(self, range_tuple: tuple) -> None:
        """Give every plot the time range of the open data files.

        Inputs:
            range_tuple: (start_s, end_s), or () while no file is open.
        Outputs: none.
        """
        # LLFR-00119, LLFR-00676, LLFR-00916: the limits of the zooms and
        # pans of every time plot, the plots created later too.
        self.files_time_range_tuple = tuple(range_tuple)
        for plot_widget in self.plot_widget_dict.values():
            plot_widget.set_files_time_range(self.files_time_range_tuple)

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
        # LLFR-00019, LLFR-01074: the new plot takes the next slot.
        page = self.page_dict.get(tab_id_i)
        if page is None or plot_id_i in self.plot_widget_dict:
            return
        # LLFR-00256: a time plot or a frequency plot.
        plot_widget = PlotWidget(plot_id_i, kind_str=kind_str)
        plot_widget.setObjectName(f"plot_widget_{plot_id_i}")
        # LLFR-00119, LLFR-00916: zooms and pans within every open file.
        plot_widget.set_files_time_range(self.files_time_range_tuple)
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
        # LLFR-01127, LLFR-01128: and the previews of a new area and of
        # a time span selection.
        plot_widget.area_preview_changed.connect(partial(
            self.relay_area_preview, plot_id_i))
        plot_widget.span_preview_changed.connect(partial(
            self.relay_span_preview, plot_id_i))
        # LLFR-00310: so does an area that is moved or resized.
        plot_widget.area_drag_moved.connect(partial(
            self.relay_area_drag, plot_id_i))
        # LLFR-01077, LLFR-01078: "Position" opens the position picker,
        # which stays in the view; only the chosen slot goes on.
        plot_widget.plot_position_requested.connect(partial(
            self.request_plot_position, plot_id_i))
        # LLFR-01079: the "Position" option of its menus opens the
        # picker beside the menu as a submenu.
        plot_widget.position_picker_factory = (
            lambda parent, chosen_id_i=plot_id_i: self.build_position_picker(
                chosen_id_i, parent, True))
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
            marker_data_list: tuples (marker_id_i, name_str, time_s,
                color_str), in placing order.
        Outputs: none.
        """
        # LLFR-00081, LLFR-00086, LLFR-00091, LLFR-00112, LLFR-00205: the
        # same markers on every plot; hidden plots draw them when shown.
        for plot_widget in self.plot_widget_dict.values():
            plot_widget.set_markers(marker_data_list)

    def set_areas(self, area_data_list: list) -> None:
        """Draw the shared areas on every time plot of every tab.

        Inputs:
            area_data_list: tuples (area_id_i, name_str, start_s, end_s,
                color_str), in creation order.
        Outputs: none.
        """
        # LLFR-00304, LLFR-00312, LLFR-00315, LLFR-00316, LLFR-00310: the
        # same areas on every plot; hidden plots draw them when shown;
        # LLFR-00311: a frequency plot leaves them out by itself.
        for plot_widget in self.plot_widget_dict.values():
            plot_widget.set_areas(area_data_list)

    def shown_page_list(self) -> list:
        """Return the tab pages shown on the screen.

        Inputs: none.
        Outputs: the tab page shown in the main window, then the tab
            page of every undocked window (the pages that are not in the
            main window's tab row).
        """
        # LLFR-00665, LLFR-00709, LLFR-00203: the tabs that are shown:
        # the main window's current tab and the tab each undocked window
        # shows.
        page_list = []
        current_page = self.tab_widget.currentWidget()
        if isinstance(current_page, TabPage):
            page_list.append(current_page)
        if self.undocked_shown_page_function is not None:
            page_list.extend(page for page
                             in self.undocked_shown_page_function()
                             if isinstance(page, TabPage)
                             and page not in page_list)
        else:
            page_list.extend(page for page in self.page_dict.values()
                             if self.tab_widget.indexOf(page) < 0)
        return page_list

    def shown_plot_widget_list(self, plot_id_i: int) -> list:
        """Return the plot widgets of the shown tabs, but one.

        Inputs:
            plot_id_i: id of the plot to leave out.
        Outputs: a list of PlotWidget of shown_page_list, without the
            plot itself (empty for an unknown plot).
        """
        # LLFR-00665, LLFR-00709: every window that is shown.
        source_widget = self.plot_widget_dict.get(plot_id_i)
        if source_widget is None:
            return []
        return [plot_widget for page in self.shown_page_list()
                for plot_widget in page.plot_widget_list
                if plot_widget is not source_widget]

    def relay_area_drag(self, plot_id_i: int, area_id_i: int,
                        start_s: float, end_s: float) -> None:
        """Show an area dragged on one plot at its span on the others.

        Inputs:
            plot_id_i: id of the plot where the area is dragged.
            area_id_i: id of the dragged area.
            start_s: the start it is shown at, in seconds.
            end_s: the end it is shown at, in seconds.
        Outputs: none.
        """
        # LLFR-00310, LLFR-00709: while dragged, the area follows the
        # pointer on every time plot of every shown tab, in the main
        # window and in every undocked window; LLFR-00710: the plots of
        # the other tabs get the new span when the button is released
        # (controller).
        for plot_widget in self.shown_plot_widget_list(plot_id_i):
            plot_widget.follow_area_drag(area_id_i, start_s, end_s)

    def relay_marker_drag(self, plot_id_i: int, marker_id_i: int,
                          time_s: float) -> None:
        """Show a marker dragged on one plot at its time on the others.

        Inputs:
            plot_id_i: id of the plot where the marker is dragged.
            marker_id_i: id of the dragged marker.
            time_s: the time it is shown at, in seconds.
        Outputs: none.
        """
        # LLFR-00205, LLFR-00665: while dragged, the marker follows the
        # pointer on every plot of every shown tab, in the main window
        # and in every undocked window; LLFR-00666: the plots of the
        # other tabs get the new time when the button is released
        # (controller).
        for plot_widget in self.shown_plot_widget_list(plot_id_i):
            plot_widget.follow_marker_drag(marker_id_i, time_s)

    def relay_marker_preview(self, plot_id_i: int, time_s: float) -> None:
        """Show the marker preview of the hovered plot on the others.

        Inputs:
            plot_id_i: id of the hovered plot.
            time_s: time of the preview in seconds, NaN when it is hidden.
        Outputs: none.
        """
        # LLFR-00203: the preview is shown on every plot of every shown
        # tab, in the main window and in every undocked window; the other
        # tabs need none.
        for plot_widget in self.shown_plot_widget_list(plot_id_i):
            plot_widget.show_marker_preview(time_s)

    def mirror_target_list(self, plot_id_i: int, start_s: float,
                           end_s: float) -> list:
        """Return the plots that show or hide a preview of another plot.

        Inputs:
            plot_id_i: id of the plot where the preview is drawn.
            start_s, end_s: its span; NaN when it is hidden.
        Outputs: the other plots of the shown tabs while it is shown;
            every other plot when it is hidden, so that no plot keeps it
            after the shown tabs changed.
        """
        # LLFR-01127, LLFR-01128: shown in the shown tabs only.
        if start_s == start_s and end_s == end_s:
            return self.shown_plot_widget_list(plot_id_i)
        source_widget = self.plot_widget_dict.get(plot_id_i)
        return [plot_widget for plot_widget in self.plot_widget_dict.values()
                if plot_widget is not source_widget]

    def relay_area_preview(self, plot_id_i: int, start_s: float,
                           end_s: float) -> None:
        """Show the preview of a new area on the other shown plots.

        Inputs:
            plot_id_i: id of the plot where the area is drawn.
            start_s, end_s: the span of the preview, in seconds; NaN to
                hide it.
        Outputs: none.
        """
        # LLFR-01127: the same preview on every other time plot of every
        # shown tab; LLFR-00311: a frequency plot leaves it out itself.
        for plot_widget in self.mirror_target_list(plot_id_i, start_s,
                                                   end_s):
            plot_widget.show_mirror_area_preview(start_s, end_s)

    def relay_span_preview(self, plot_id_i: int, start_s: float,
                           end_s: float) -> None:
        """Show a time span selection on the other shown time plots.

        Inputs:
            plot_id_i: id of the plot where the span is selected.
            start_s, end_s: the two ends of the span, in seconds; NaN to
                hide it.
        Outputs: none.
        """
        # LLFR-01128: the same span on every other time plot of every
        # shown tab; a frequency plot leaves it out itself.
        for plot_widget in self.mirror_target_list(plot_id_i, start_s,
                                                   end_s):
            plot_widget.show_mirror_span(start_s, end_s)

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
            selection is in progress on a plot of any tab, or a tab is
            dragged.
        """
        # LLFR-00454: the 0 key does nothing during a mouse drag, a tab
        # drag included.
        return self.is_tab_drag_in_progress() or any(
            plot_widget.is_mouse_drag_in_progress()
            for plot_widget in self.plot_widget_dict.values())

    def plot_id_list(self, tab_id_i: int) -> list:
        """Return the plot ids of a tab, in fill order.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: a list of int (empty for an unknown tab).
        """
        # LLFR-01073: the fill order of the plot matrix.
        page = self.page_dict.get(tab_id_i)
        if page is None:
            return []
        return [plot_widget.plot_id_i
                for plot_widget in page.plot_widget_list]
