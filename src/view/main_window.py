"""Main window of plot_tool, holding the three panels (HLFR-00001)."""

from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QInputDialog, QLineEdit, QMainWindow, QVBoxLayout,
    QWidget)

from controller.plot_tools import NO_TOOL_STR
from view import message_boxes, plot_export
from view.panel_splitter import PanelSplitter
from view.plot_panel import PlotPanel
from view.signal_list_panel import SignalListPanel
from view.top_panel import TopPanel


# LLFR-00005: title and filter of the file selection dialog. "All files"
# lets the user pick an unsupported file, which then gets the error of
# LLFR-00011.
OPEN_FILE_DIALOG_TITLE_STR = "Open file"
OPEN_FILE_FILTER_STR = "Time series files (*.csv *.xlsx *.mat);;All files (*)"
# LLFR-00088: title and label of the marker rename dialog.
RENAME_MARKER_DIALOG_TITLE_STR = "Rename marker"
RENAME_MARKER_DIALOG_LABEL_STR = "New marker name:"
# LLFR-00128: title and filter of the PDF save file dialog.
SAVE_PDF_DIALOG_TITLE_STR = "Save all tabs as PDF"
SAVE_PDF_FILTER_STR = "PDF files (*.pdf)"
# LLFR-00128: added by the dialog to a name typed without an extension,
# so that its overwrite question names the file really written.
SAVE_PDF_DEFAULT_SUFFIX_STR = "pdf"


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
        # LLFR-00127, LLFR-00133: the export controller saves the PDF
        # and copies the image.
        self.pdf_export_handler = None
        self.copy_handler = None
        self.top_panel.pdf_export_requested.connect(
            self._on_pdf_export_requested)
        self.top_panel.copy_requested.connect(self._on_copy_requested)

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

    # ----------------------------------------------------------------
    # Export facade, used by the export controller (plain types only)
    # ----------------------------------------------------------------

    def set_export_handlers(self, pdf_export_handler,
                            copy_handler) -> None:
        """Set the functions called by the Export menu and Copy button.

        Inputs:
            pdf_export_handler: function without arguments, called when
                "Save all tabs as PDF" is chosen.
            copy_handler: function without arguments, called when the
                Copy button is clicked.
        Outputs: none.
        """
        # LLFR-00128, LLFR-00133: the controller runs the flows.
        self.pdf_export_handler = pdf_export_handler
        self.copy_handler = copy_handler

    def exportable_tab_count(self) -> int:
        """Return the number of tabs that hold at least one plot.

        Inputs: none.
        Outputs: an int.
        """
        # LLFR-00129, LLFR-00145: the tabs that get a PDF page.
        return len(plot_export.exportable_page_list(
            self.plot_panel.tab_widget))

    def current_tab_plot_count(self) -> int:
        """Return the number of plots in the current tab.

        Inputs: none.
        Outputs: an int, 0 when there is no tab.
        """
        # LLFR-00146: a tab without plots has nothing to copy.
        return len(self.plot_panel.plot_id_list(self.current_tab_id()))

    def ask_pdf_save_path(self) -> str:
        """Show the save file dialog for a .pdf file.

        Inputs: none.
        Outputs: the chosen path, or "" when the user cancelled.
        """
        # LLFR-00128: a save file dialog for a .pdf file.
        # LLFR-00130: an empty path means the dialog was cancelled.
        dialog = self.build_pdf_save_dialog()
        try:
            return self.run_pdf_save_dialog(dialog) or ""
        finally:
            dialog.deleteLater()

    def build_pdf_save_dialog(self) -> QFileDialog:
        """Build the save file dialog of the PDF export, not shown.

        Inputs: none.
        Outputs: a QFileDialog in save mode, filtered to .pdf files,
            that adds ".pdf" to a name typed without an extension and
            asks before overwriting the resulting file.
        """
        # LLFR-00128: the dialog is for a .pdf file; the overwrite
        # question is asked by Qt for the name with the suffix.
        dialog = QFileDialog(self, SAVE_PDF_DIALOG_TITLE_STR, "",
                             SAVE_PDF_FILTER_STR)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setDefaultSuffix(SAVE_PDF_DEFAULT_SUFFIX_STR)
        return dialog

    def run_pdf_save_dialog(self, dialog) -> str:
        """Run the PDF save dialog modally and return the chosen path.

        Inputs:
            dialog: the QFileDialog built by build_pdf_save_dialog.
        Outputs: the chosen path, or "" when the user cancelled. Tests
            replace this method to answer without a modal dialog.
        """
        # LLFR-00128, LLFR-00130: the modal dialog.
        if dialog.exec() != QDialog.DialogCode.Accepted.value:
            return ""
        selected_file_list = dialog.selectedFiles()
        if not selected_file_list:
            return ""
        return str(selected_file_list[0])

    def ask_replace_existing_file(self, path_str: str) -> bool:
        """Ask whether to replace an existing file.

        Inputs:
            path_str: the path of the existing file.
        Outputs: True when the user chose to replace it.
        """
        # LLFR-00128: asked when ".pdf" was added after the dialog and
        # the resulting file already exists.
        return message_boxes.ask_replace_existing_file(self, path_str)

    def save_tabs_pdf(self, path_str: str) -> tuple:
        """Save the plots of every tab that holds a plot to a PDF file.

        Inputs:
            path_str: the path of the .pdf file.
        Outputs: a tuple (saved_b, reason_str).
        """
        # LLFR-00129, LLFR-00131: one page per tab with a plot.
        return plot_export.save_tabs_pdf(self.plot_panel.tab_widget,
                                         path_str)

    def copy_current_tab_image(self) -> tuple:
        """Put an image of the current tab's plots on the clipboard.

        Inputs: none.
        Outputs: a tuple (copied_b, reason_str).
        """
        # LLFR-00133: the plots of the current tab, as on screen.
        return plot_export.copy_current_tab_image(
            self.plot_panel.tab_widget)

    def show_nothing_to_export(self) -> None:
        """Show the box saying that there are no plots to export.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00145: an information box.
        message_boxes.build_nothing_to_export_box(self).exec()

    def show_nothing_to_copy(self) -> None:
        """Show the box saying that there are no plots to copy.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00146: an information box.
        message_boxes.build_nothing_to_copy_box(self).exec()

    def show_export_error(self, reason_str: str) -> None:
        """Show the error box saying that the PDF could not be saved.

        Inputs:
            reason_str: why the file could not be written.
        Outputs: none.
        """
        # LLFR-00131: an error box (HLFR-00002).
        message_boxes.build_export_error_box(self, reason_str).exec()

    def show_copy_error(self, reason_str: str) -> None:
        """Show the error box saying that the image could not be copied.

        Inputs:
            reason_str: why the copy failed.
        Outputs: none.
        """
        # LLFR-00133: an error box (HLFR-00002).
        message_boxes.build_copy_error_box(self, reason_str).exec()

    def finish_export_button(self) -> None:
        """Return the Export button to its normal color.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00003: the export has finished.
        self.top_panel.export_button.finish()

    def finish_copy_button(self) -> None:
        """Return the Copy button to its normal color.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00003: the copy has finished.
        self.top_panel.copy_button.finish()

    def _on_pdf_export_requested(self) -> None:
        """Run the PDF export handler after the menu choice.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00128: the controller shows the save file dialog.
        if self.pdf_export_handler is None:
            # LLFR-00003: nothing to run, so the function is finished.
            self.finish_export_button()
            return
        self.pdf_export_handler()

    def _on_copy_requested(self) -> None:
        """Run the copy handler after the Copy button is clicked.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00133: the controller copies the image.
        if self.copy_handler is None:
            # LLFR-00003: nothing to run, so the function is finished.
            self.finish_copy_button()
            return
        self.copy_handler()

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
        # LLFR-00079, LLFR-00002: the controller applies the tool; with
        # no controller the window applies it itself.
        if self.plot_tool_handler is None:
            self.set_plot_tool(tool_str)
            return
        self.plot_tool_handler(tool_str)

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
