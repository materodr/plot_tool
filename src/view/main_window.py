"""Main window of plot_tool, holding the three panels (HLFR-00001)."""

from PyQt6.QtWidgets import (
    QFileDialog, QMainWindow, QVBoxLayout, QWidget)

from view import message_boxes
from view.panel_splitter import PanelSplitter
from view.plot_panel import PlotPanel
from view.signal_list_panel import SignalListPanel
from view.top_panel import TopPanel


# LLFR-00005: title and filter of the file selection dialog. "All files"
# lets the user pick an unsupported file, which then gets the error of
# LLFR-00011.
OPEN_FILE_DIALOG_TITLE_STR = "Open file"
OPEN_FILE_FILTER_STR = "Time series files (*.csv *.xlsx *.mat);;All files (*)"


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
        self.tip_mode_handler = None
        self.top_panel.open_file_button.activated.connect(
            self._on_open_file_activated)
        self.top_panel.tip_button.activated.connect(
            self._on_tip_activated)
        self.top_panel.tip_button.deactivated.connect(
            self._on_tip_deactivated)
        self.signal_list_panel.signal_double_clicked.connect(
            self._on_signal_double_clicked)

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

    def set_signal_double_click_handler(self, handler) -> None:
        """Set the function called when a signal name is double-clicked.

        Inputs:
            handler: a function taking the signal name (str).
        Outputs: none.
        """
        # LLFR-00019: the plot controller creates a plot through it.
        self.signal_double_click_handler = handler

    def set_tip_mode_handler(self, handler) -> None:
        """Set the function called when the Tip button changes state.

        Inputs:
            handler: a function taking True when the Tip button becomes
                active and False when it is deactivated.
        Outputs: none.
        """
        # LLFR-00042: the hover tip is shown while Tip is active.
        self.tip_mode_handler = handler

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
                  pinned_tip_list: list) -> None:
        """Draw the curves and pinned tips of a plot.

        Inputs:
            plot_id_i: id of the plot.
            curve_data_list: tuples (signal_name_str, time_array,
                value_array, color_str, width_i).
            pinned_tip_list: tuples (signal_name_str, time_s, value_f).
        Outputs: none. The plot shows the full time range afterwards.
        """
        # LLFR-00020, LLFR-00021, LLFR-00068: draw against time.
        # LLFR-00045: draw the pinned tips.
        plot_widget = self.plot_panel.plot_view(plot_id_i)
        if plot_widget is None:
            return
        plot_widget.set_curves(curve_data_list)
        plot_widget.set_pinned_tips(pinned_tip_list)

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

    def set_tip_mode(self, enabled_b: bool) -> None:
        """Turn hover tips on or off in every plot, now and later.

        Inputs:
            enabled_b: True while the Tip button is active.
        Outputs: none.
        """
        # LLFR-00042: tips only while the Tip button is active.
        self.plot_panel.set_tip_mode(enabled_b)

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

    def _on_tip_activated(self) -> None:
        """Tell the tip handler that the Tip button became active.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00042: tip mode on.
        if self.tip_mode_handler is not None:
            self.tip_mode_handler(True)

    def _on_tip_deactivated(self) -> None:
        """Tell the tip handler that the Tip button was deactivated.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00002, LLFR-00042: tip mode off.
        if self.tip_mode_handler is not None:
            self.tip_mode_handler(False)

    def _on_signal_double_clicked(self, signal_name_str: str) -> None:
        """Pass a double-clicked signal name to its handler.

        Inputs:
            signal_name_str: the name that was double-clicked.
        Outputs: none.
        """
        # LLFR-00019: the handler creates a plot with the signal.
        if self.signal_double_click_handler is not None:
            self.signal_double_click_handler(signal_name_str)
