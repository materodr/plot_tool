"""Main window of plot_tool, holding the three panels (HLFR-00001)."""

from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QInputDialog, QLineEdit, QMainWindow,
    QVBoxLayout, QWidget)

from controller.plot_tools import NO_TOOL_STR, TIP_TOOL_STR
from view import message_boxes
from view.panel_splitter import PanelSplitter
from view.plot_panel import PlotPanel
from view.signal_list_panel import SignalListPanel
from view.tip_key_filter import TipKeyFilter
from view.top_panel import TopPanel


# LLFR-00005: title and filter of the file selection dialog. "All files"
# lets the user pick an unsupported file, which then gets the error of
# LLFR-00011.
OPEN_FILE_DIALOG_TITLE_STR = "Open file"
OPEN_FILE_FILTER_STR = "Time series files (*.csv *.xlsx *.mat);;All files (*)"
# LLFR-00088: title and label of the marker rename dialog.
RENAME_MARKER_DIALOG_TITLE_STR = "Rename marker"
RENAME_MARKER_DIALOG_LABEL_STR = "New marker name:"


class MainWindow(QMainWindow):
    """Top-level window that places the top, plot and signal list panels.

    Besides the panels, it offers controllers a plain-Python facade
    (no Qt types in or out), so controllers can be tested with fake
    views (COR-00009).

    Inputs: none.
    Attributes:
        top_panel: the TopPanel placed above the other two panels.
        plot_panel: the PlotPanel placed on the left, below the top panel.
        signal_list_panel: the SignalListPanel placed on the right of the
            plot panel.
    """

    WINDOW_TITLE_STR = "plot_tool"
    INITIAL_WIDTH_I = 1200
    INITIAL_HEIGHT_I = 800
    # LLFR-00072: the signal list panel starts at 25% of the width and
    # keeps that share (3:1) when the window grows or shrinks.
    PLOT_PANEL_STRETCH_I = 3
    SIGNAL_LIST_STRETCH_I = 1
    SIGNAL_LIST_WIDTH_FRACTION_F = 0.25

    def __init__(self) -> None:
        """Create the panels and arrange them in the window.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        # LLFR-00058: the window holds the three panels of HLFR-00001.
        self.setWindowTitle(self.WINDOW_TITLE_STR)
        self.resize(self.INITIAL_WIDTH_I, self.INITIAL_HEIGHT_I)
        self.top_panel = TopPanel()
        self.plot_panel = PlotPanel()
        self.signal_list_panel = SignalListPanel()

        # LLFR-00058: the signal list panel is to the right of the plot
        # panel. LLFR-00073: the user can drag the border between them.
        self.lower_splitter = PanelSplitter(
            self.SIGNAL_LIST_WIDTH_FRACTION_F)
        self.lower_splitter.addWidget(self.plot_panel)
        self.lower_splitter.addWidget(self.signal_list_panel)
        self.lower_splitter.setStretchFactor(0, self.PLOT_PANEL_STRETCH_I)
        self.lower_splitter.setStretchFactor(1, self.SIGNAL_LIST_STRETCH_I)

        # LLFR-00058: the top panel is above the other two panels.
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.addWidget(self.top_panel)
        central_layout.addWidget(self.lower_splitter, 1)
        self.setCentralWidget(central_widget)

        # LLFR-00005: handlers set by the controllers.
        self.open_file_handler = None
        self.signal_double_click_handler = None
        self.plot_tool_handler = None
        # LLFR-00079: the tool applied to every plot, now and later.
        self.plot_tool_str = NO_TOOL_STR
        self.top_panel.open_file_button.activated.connect(
            self._on_open_file_activated)
        # LLFR-00079, LLFR-00002: the top panel reports the active tool.
        self.top_panel.plot_tool_changed.connect(self._on_plot_tool_changed)
        self.signal_list_panel.signal_double_clicked.connect(
            self._on_signal_double_clicked)
        # LLFR-00095: the search text goes to the signal list controller.
        self.search_text_handler = None
        self.signal_list_panel.search_text_changed.connect(
            self._on_search_text_changed)
        # LLFR-00115: the Reset zoom button goes to the plot controller.
        self.reset_zoom_handler = None
        self.top_panel.reset_zoom_button.triggered.connect(
            self._on_reset_zoom_triggered)
        # LLFR-00122, LLFR-00123: the Grid button goes to the plot
        # controller. LLFR-00147: the grid is hidden at start; the
        # choice applies to every plot, now and later (LLFR-00125).
        self.grid_handler = None
        self.grid_shown_b = False
        self.top_panel.grid_button.activated.connect(
            lambda: self._on_grid_clicked(True))
        self.top_panel.grid_button.deactivated.connect(
            lambda: self._on_grid_clicked(False))
        # LLFR-00148, LLFR-00149, LLFR-00150: holding the Tip key keeps
        # the Tip tool active; the filter sees the keys of every widget
        # and dialog of the application, and consumes none.
        self.tip_key_changing_tool_b = False
        self.tip_key_filter = TipKeyFilter(
            self.on_tip_key_activate, self.on_tip_key_release, self)
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self.tip_key_filter)

    def set_open_file_handler(self, handler) -> None:
        """Set the function called when the Open file button is clicked.

        Inputs:
            handler: a function without arguments, called when the
                Open file button becomes active.
        Outputs: none.
        """
        # LLFR-00005: the controller shows the dialog through ``handler``.
        self.open_file_handler = handler

    def ask_open_file_path(self) -> str:
        """Show the file selection dialog and return the chosen path.

        Inputs: none.
        Outputs: the path of the selected file, or "" when the user
            cancelled the dialog.
        """
        # LLFR-00005: show the file selection dialog.
        # LLFR-00007: an empty path means the dialog was cancelled.
        path_str, _ = QFileDialog.getOpenFileName(
            self, OPEN_FILE_DIALOG_TITLE_STR, "", OPEN_FILE_FILTER_STR)
        return path_str or ""

    def finish_open_file_button(self) -> None:
        """Return the Open file button to its normal color.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00003: the open-file flow has finished.
        self.top_panel.open_file_button.finish()

    def show_file_open_error(self, message_str: str) -> None:
        """Show the File Open Error box with the given message.

        Inputs:
            message_str: the description of the error.
        Outputs: none.
        """
        # LLFR-00008, LLFR-00009, LLFR-00011, LLFR-00012: notify the
        # error (HLFR-00002).
        message_boxes.show_file_open_error(self, message_str)

    def ask_replace_file(self) -> bool:
        """Ask whether to close the open file and open the selected one.

        Inputs: none.
        Outputs: True when the user chose to proceed.
        """
        # LLFR-00013, LLFR-00014: the confirmation of HLFR-00010.
        return message_boxes.ask_replace_file(self)

    def show_signal_names(self, signal_name_list: list) -> None:
        """Show the signal names of the opened file in the signal list.

        Inputs:
            signal_name_list: the signal names, in file order.
        Outputs: none.
        """
        # LLFR-00017, LLFR-00054: replace the shown names.
        self.signal_list_panel.show_signal_names(signal_name_list)

    def set_search_text_handler(self, handler) -> None:
        """Set the function called when the search box text changes.

        Inputs:
            handler: a function taking the new text (str).
        Outputs: none.
        """
        # LLFR-00095: the signal list controller filters the list.
        self.search_text_handler = handler

    def show_no_match_message(self, visible_b: bool,
                              message_str: str) -> None:
        """Show or hide the no-match text in the signal list.

        Inputs:
            visible_b: True when no signal matches the search.
            message_str: the text to show ("No matching signals").
        Outputs: none.
        """
        # LLFR-00097: tell the user that no signal matches.
        self.signal_list_panel.show_no_match_message(visible_b, message_str)

    def clear_search(self) -> None:
        """Empty the search box of the signal list panel.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00104: the search is cleared when the file is replaced.
        self.signal_list_panel.clear_search()

    def set_signal_double_click_handler(self, handler) -> None:
        """Set the function called when a signal name is double-clicked.

        Inputs:
            handler: a function taking the signal name (str).
        Outputs: none.
        """
        # LLFR-00019: the plot controller creates a plot through it.
        self.signal_double_click_handler = handler

    def set_plot_tool_handler(self, handler) -> None:
        """Set the function called when the active plot tool changes.

        Inputs:
            handler: a function taking the new tool name (a str of
                controller.plot_tools), NO_TOOL_STR when no tool is
                active any more.
        Outputs: none.
        """
        # LLFR-00079, LLFR-00002, LLFR-00109: the controller is told of
        # every change of the plot tool.
        self.plot_tool_handler = handler

    def set_plot_tool(self, tool_str: str) -> None:
        """Apply a plot tool to every plot, now and to plots made later.

        Inputs:
            tool_str: the tool name, NO_TOOL_STR for none.
        Outputs: none. The tool buttons are shown to match.
        """
        # LLFR-00079: the buttons always show the tool in use.
        self.plot_tool_str = tool_str
        self.top_panel.show_plot_tool(tool_str)
        # LLFR-00042, LLFR-00045, LLFR-00078: every plot reacts to the
        # mouse according to the tool.
        for plot_widget in self.plot_panel.plot_widget_dict.values():
            plot_widget.set_plot_tool(tool_str)

    def current_plot_tool(self) -> str:
        """Return the plot tool applied to the plots.

        Inputs: none.
        Outputs: the tool name, NO_TOOL_STR when none is active.
        """
        # LLFR-00079, LLFR-00109: the tool stays until it is changed.
        return self.plot_tool_str

    def on_tip_key_activate(self) -> None:
        """Make Tip the active tool because the Tip key is held alone.

        Inputs: none.
        Outputs: none. The tool change goes the same way as a click on
            the Tip button, so the controller is told of it.
        """
        # LLFR-00148: the Tip button becomes active and the other tool
        # buttons are deactivated as in LLFR-00079.
        self.tip_key_changing_tool_b = True
        try:
            self.top_panel.tip_button.setChecked(True)
            self.top_panel.activate_plot_tool(TIP_TOOL_STR)
        finally:
            self.tip_key_changing_tool_b = False

    def on_tip_key_release(self) -> None:
        """Leave no plot tool active because the Tip key hold ended.

        Inputs: none.
        Outputs: none. The tool change goes the same way as a second
            click on the active tool button.
        """
        # LLFR-00149, LLFR-00150: no plot tool is active afterwards,
        # whatever tool was active before the Tip key was pressed.
        self.tip_key_changing_tool_b = True
        try:
            self.top_panel.show_plot_tool(NO_TOOL_STR)
            self.top_panel.deactivate_plot_tools()
        finally:
            self.tip_key_changing_tool_b = False

    def set_reset_zoom_handler(self, handler) -> None:
        """Set the function called when Reset zoom is clicked.

        Inputs:
            handler: a function without arguments that resets the zoom
                of the current tab.
        Outputs: none.
        """
        # LLFR-00115: the controller resets the plots of the current tab.
        self.reset_zoom_handler = handler

    def finish_reset_zoom_button(self) -> None:
        """Tell the Reset zoom button that the reset has finished.

        Inputs: none.
        Outputs: none. The button turns normal once it has been active
            for at least 0.3 s.
        """
        # LLFR-00003, LLFR-00116: normal after the reset and 0.3 s.
        self.top_panel.reset_zoom_button.finish()

    def set_grid_handler(self, handler) -> None:
        """Set the function called when the Grid button is clicked.

        Inputs:
            handler: a function taking True (show the grid) or False
                (hide it).
        Outputs: none.
        """
        # LLFR-00122, LLFR-00123: the controller keeps the grid state.
        self.grid_handler = handler

    def set_grid_shown(self, shown_b: bool) -> None:
        """Show or hide the grid on every plot, now and on later plots.

        Inputs:
            shown_b: True to show the grid, False to hide it.
        Outputs: none. The Grid button is shown to match.
        """
        # LLFR-00124: the Grid button is active while the grid is shown;
        # setChecked emits no click, so nothing is reported back.
        self.grid_shown_b = bool(shown_b)
        self.top_panel.grid_button.setChecked(self.grid_shown_b)
        # LLFR-00122, LLFR-00123: every plot in every tab.
        for plot_widget in self.plot_panel.plot_widget_dict.values():
            plot_widget.set_grid_shown(self.grid_shown_b)

    def is_grid_shown(self) -> bool:
        """Return whether the grid is applied to the plots.

        Inputs: none.
        Outputs: True while the grid is shown.
        """
        # LLFR-00124, LLFR-00125: the state new plots take.
        return self.grid_shown_b

    # ----------------------------------------------------------------
    # Plot panel facade, used by the plot controller (plain types only)
    # ----------------------------------------------------------------

    def set_tab_handlers(self, add_tab_handler, delete_tab_handler,
                         rename_tab_handler) -> None:
        """Set the functions called for the tab requests of the user.

        Inputs:
            add_tab_handler: function without arguments ("+" clicked).
            delete_tab_handler: function taking a tab id.
            rename_tab_handler: function taking a tab id and a name.
        Outputs: none.
        """
        # LLFR-00026, LLFR-00028, LLFR-00030: the controller decides.
        self.plot_panel.set_tab_handlers(add_tab_handler,
                                         delete_tab_handler,
                                         rename_tab_handler)

    def set_plot_handlers(self, **handler_dict) -> None:
        """Set the functions called for the requests made on a plot.

        Inputs:
            handler_dict: handler name -> function; see
                view.plot_panel.PLOT_SIGNAL_HANDLER_DICT.
        Outputs: none.
        """
        # LLFR-00021, LLFR-00039, LLFR-00041, LLFR-00045, LLFR-00047,
        # LLFR-00049, LLFR-00070: plot requests go to the controller.
        self.plot_panel.set_plot_handlers(**handler_dict)

    def add_tab_view(self, tab_id_i: int, name_str: str) -> None:
        """Add a tab after the last one.

        Inputs:
            tab_id_i: id of the tab in the model.
            name_str: name shown on the tab.
        Outputs: none.
        """
        # LLFR-00024, LLFR-00026: show a new tab.
        self.plot_panel.add_tab_view(tab_id_i, name_str)

    def remove_tab_view(self, tab_id_i: int) -> None:
        """Remove a tab and its plots.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: none.
        """
        # LLFR-00028: remove the tab.
        self.plot_panel.remove_tab_view(tab_id_i)

    def rename_tab_view(self, tab_id_i: int, name_str: str) -> None:
        """Show a new name on a tab.

        Inputs:
            tab_id_i: id of the tab.
            name_str: the new name.
        Outputs: none.
        """
        # LLFR-00030: show the name chosen by the user.
        self.plot_panel.rename_tab_view(tab_id_i, name_str)

    def clear_tab_views(self) -> None:
        """Remove every tab and plot.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00015: close all tabs and plots of the previous file.
        self.plot_panel.clear_tab_views()

    def set_current_tab(self, tab_id_i: int) -> None:
        """Select a tab.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: none.
        """
        # LLFR-00026: a new tab becomes the current one.
        self.plot_panel.set_current_tab(tab_id_i)

    def current_tab_id(self) -> int:
        """Return the id of the selected tab.

        Inputs: none.
        Outputs: the tab id, or -1 when there is no tab.
        """
        # LLFR-00019: double-click plots go into the current tab.
        return self.plot_panel.current_tab_id()

    def tab_name_list(self) -> list:
        """Return the names of the tabs, from left to right.

        Inputs: none.
        Outputs: a list of str.
        """
        # LLFR-00024, LLFR-00030: the names shown on the tabs.
        return self.plot_panel.tab_name_list()

    def set_tab_delete_enabled(self, enabled_b: bool) -> None:
        """Enable or disable "Delete" in the tab menu.

        Inputs:
            enabled_b: False when only one tab is left.
        Outputs: none.
        """
        # LLFR-00066: the last tab cannot be deleted.
        self.plot_panel.set_tab_delete_enabled(enabled_b)

    def add_plot_view(self, tab_id_i: int, plot_id_i: int) -> None:
        """Create a plot at the bottom of a tab.

        Inputs:
            tab_id_i: id of the tab.
            plot_id_i: id of the plot in the model.
        Outputs: none.
        """
        # LLFR-00019, LLFR-00069: the new plot goes below the others.
        self.plot_panel.add_plot_view(tab_id_i, plot_id_i)
        # LLFR-00042, LLFR-00078: a new plot starts with the active tool.
        plot_widget = self.plot_panel.plot_view(plot_id_i)
        if plot_widget is not None:
            plot_widget.set_plot_tool(self.plot_tool_str)
            # LLFR-00125: a new plot shows the grid while it is shown.
            plot_widget.set_grid_shown(self.grid_shown_b)

    def remove_plot_view(self, plot_id_i: int) -> None:
        """Remove a plot from its tab.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: none.
        """
        # LLFR-00049, LLFR-00050: the other plots fill the space.
        self.plot_panel.remove_plot_view(plot_id_i)

    def plot_view(self, plot_id_i: int):
        """Return the plot widget of a plot.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: the PlotWidget, or None for an unknown id.
        """
        # LLFR-00020, LLFR-00021: the widget the curves are drawn in.
        return self.plot_panel.plot_view(plot_id_i)

    def draw_plot(self, plot_id_i: int, curve_data_list: list,
                  pinned_tip_list: list, marker_data_list=()) -> None:
        """Draw the curves, pinned tips and vertical markers of a plot.

        Inputs:
            plot_id_i: id of the plot.
            curve_data_list: tuples (signal_name_str, time_array,
                value_array, color_str, width_i).
            pinned_tip_list: tuples (signal_name_str, time_s, value_f).
            marker_data_list: tuples (marker_id_i, name_str, time_s).
        Outputs: none. The plot shows the full time range afterwards.
        """
        # LLFR-00020, LLFR-00021, LLFR-00068: draw against time.
        # LLFR-00045: draw the pinned tips.
        plot_widget = self.plot_panel.plot_view(plot_id_i)
        if plot_widget is None:
            return
        plot_widget.set_curves(curve_data_list)
        plot_widget.set_pinned_tips(pinned_tip_list)
        # LLFR-00081, LLFR-00091, LLFR-00112: draw the markers.
        plot_widget.set_markers(marker_data_list)

    def set_plot_time_range(self, plot_id_i: int, start_s: float,
                            end_s: float) -> None:
        """Show a time range in a plot without reporting it back.

        Inputs:
            plot_id_i: id of the plot.
            start_s: start of the range, in seconds.
            end_s: end of the range, in seconds.
        Outputs: none.
        """
        # LLFR-00070: the plots of a tab share the time range.
        plot_widget = self.plot_panel.plot_view(plot_id_i)
        if plot_widget is not None:
            plot_widget.set_time_range(start_s, end_s)

    def plot_time_range(self, plot_id_i: int) -> tuple:
        """Return the time range shown by a plot.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: a tuple (start_s, end_s), or () for an unknown id.
        """
        # LLFR-00070: the range a new plot of the tab takes.
        plot_widget = self.plot_panel.plot_view(plot_id_i)
        if plot_widget is None:
            return ()
        return plot_widget.time_range_tuple()

    def ask_marker_name(self, current_name_str: str):
        """Let the user type a new name for a vertical marker.

        Inputs:
            current_name_str: the marker's name, shown in the dialog.
        Outputs: the typed text (not stripped), or None when the user
            cancelled the dialog.
        """
        # LLFR-00088: the dialog starts from the current name.
        # LLFR-00089: a blank answer is returned as typed; the
        # controller keeps the old name without a message.
        new_name_str, accepted_b = QInputDialog.getText(
            self, RENAME_MARKER_DIALOG_TITLE_STR,
            RENAME_MARKER_DIALOG_LABEL_STR, QLineEdit.EchoMode.Normal,
            current_name_str)
        if not accepted_b:
            return None
        return str(new_name_str)

    def show_full_tab_notification(self) -> None:
        """Show the Full Tab Notification box.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00032: the tab is full; add a tab or delete a plot.
        message_boxes.show_full_tab_notification(self)

    def _on_open_file_activated(self) -> None:
        """Run the open-file handler after the Open file button is clicked.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00005: start the open-file flow.
        if self.open_file_handler is None:
            # LLFR-00003: nothing to run, so the function is finished.
            self.finish_open_file_button()
            return
        self.open_file_handler()

    def _on_plot_tool_changed(self, tool_str: str) -> None:
        """Pass the plot tool chosen in the top panel to its handler.

        Inputs:
            tool_str: the new tool name, NO_TOOL_STR for none.
        Outputs: none.
        """
        # LLFR-00079, LLFR-00149: a tool chosen with the mouse while the
        # Tip key is held is kept; the later release changes nothing.
        if not self.tip_key_changing_tool_b:
            self.tip_key_filter.cancel_activation()
        # LLFR-00079, LLFR-00002: the controller applies the tool; with
        # no controller the window applies it itself.
        if self.plot_tool_handler is None:
            self.set_plot_tool(tool_str)
            return
        self.plot_tool_handler(tool_str)

    def _on_reset_zoom_triggered(self) -> None:
        """Run the reset zoom handler, then let the button finish.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00115: reset the zoom of the current tab. LLFR-00116: the
        # button finishes when the reset is done, even if it failed, so
        # it is never left active.
        try:
            if self.reset_zoom_handler is not None:
                self.reset_zoom_handler()
        finally:
            self.finish_reset_zoom_button()

    def _on_grid_clicked(self, shown_b: bool) -> None:
        """Pass a click on the Grid button to its handler.

        Inputs:
            shown_b: True when the click asks to show the grid.
        Outputs: none.
        """
        # LLFR-00122, LLFR-00123: the controller applies the grid; with
        # no controller the window applies it itself.
        if self.grid_handler is None:
            self.set_grid_shown(shown_b)
            return
        self.grid_handler(shown_b)

    def _on_search_text_changed(self, text_str: str) -> None:
        """Pass the new search box text to its handler.

        Inputs:
            text_str: the text now in the search box.
        Outputs: none.
        """
        # LLFR-00095: every change re-filters the signal list.
        if self.search_text_handler is not None:
            self.search_text_handler(text_str)

    def _on_signal_double_clicked(self, signal_name_str: str) -> None:
        """Pass a double-clicked signal name to its handler.

        Inputs:
            signal_name_str: the name that was double-clicked.
        Outputs: none.
        """
        # LLFR-00019: the handler creates a plot with the signal.
        if self.signal_double_click_handler is not None:
            self.signal_double_click_handler(signal_name_str)
