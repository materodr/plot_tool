"""Main window of plot_tool, holding the three panels (HLFR-00001)."""

import sys
from functools import partial

from PyQt6 import sip
from PyQt6.QtCore import QEvent, QEventLoop, QObject, QPoint, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractSpinBox, QApplication, QDialog, QFileDialog, QLineEdit,
    QMainWindow, QPlainTextEdit, QTextEdit, QVBoxLayout,
    QWidget)

from controller.plot_tools import (
    ARROW_TOOL_STR, AREA_TOOL_STR, DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR,
    MARKER_TOOL_STR, NO_TOOL_STR, TEXT_TOOL_STR, TIP_TOOL_STR,
    ZOOM_TOOL_STR)
from model import file_writer
from model.window_placement import (
    fitted_panel_width_i, new_window_tuple, placed_window_tuple)
from model.workspace import TIME_PLOT_KIND_STR
from view import (
    color_picker, file_dialogs, file_writing, icons, message_boxes,
    name_dialog, plot_export, synthetic_dialogs, theme)
from view.panel_splitter import PanelSplitter
from view.plot_panel import PlotPanel
from view.search_box_alignment import SearchBoxAligner
from view.signal_list_panel import SignalListPanel
from view.tip_key_filter import (
    ARROW_KEY_I, AREA_KEY_I, DELTA_X_KEY_I, DELTA_Y_KEY_I, ESCAPE_KEY_I,
    MARKER_KEY_I, RESET_ZOOM_KEY_I, TEXT_KEY_I, TIP_KEY_I, ZOOM_KEY_I,
    ToolKeyFilter)
from view import top_panel
from view.top_panel import TopPanel
from view.undocked_window import UndockedWindow


# LLFR-00005: title and filter of the file selection dialog. "All files"
# lets the user pick an unsupported file, which then gets the error of
# LLFR-00011.
OPEN_FILE_DIALOG_TITLE_STR = "Open file"
OPEN_FILE_FILTER_STR = ("Time series files (*.csv *.xlsx *.mat *.h5 *.hdf5)"
                        ";;All files (*)")
# LLFR-00088: title and label of the flag rename dialog.
RENAME_MARKER_DIALOG_TITLE_STR = "Rename flag"
RENAME_MARKER_DIALOG_LABEL_STR = "New flag name:"
# LLFR-00315: the dialog that renames an area.
RENAME_AREA_DIALOG_TITLE_STR = "Rename area"
RENAME_AREA_DIALOG_LABEL_STR = "New area name:"
# LLFR-00429: the dialog that renames a delta marker.
RENAME_DELTA_DIALOG_TITLE_STR = "Rename delta marker"
RENAME_DELTA_DIALOG_LABEL_STR = "New delta marker name:"
# LLFR-00439: the dialog that renames an arrow.
RENAME_ARROW_DIALOG_TITLE_STR = "Rename arrow"
RENAME_ARROW_DIALOG_LABEL_STR = "New arrow name:"
# LLFR-00266: title and label of the synthetic signal rename dialog.
RENAME_SIGNAL_DIALOG_TITLE_STR = "Rename signal"
RENAME_SIGNAL_DIALOG_LABEL_STR = "New signal name:"
# LLFR-00128: title and filter of the PDF save file dialog.
SAVE_PDF_DIALOG_TITLE_STR = "Save all tabs as PDF"
SAVE_PDF_FILTER_STR = "PDF files (*.pdf)"
# LLFR-00128: added by the dialog to a name typed without an extension,
# so that its overwrite question names the file really written.
SAVE_PDF_DEFAULT_SUFFIX_STR = "pdf"
# LLFR-00219, LLFR-00221: titles and filter of the layout dialogs.
SAVE_LAYOUT_DIALOG_TITLE_STR = "Save layout"
LOAD_LAYOUT_DIALOG_TITLE_STR = "Load layout"
LAYOUT_FILTER_STR = "Layout files (*.json)"
# LLFR-00219: added by the dialog to a name typed without an extension,
# so that its overwrite question (LLFR-00223) names the file written.
LAYOUT_DEFAULT_SUFFIX_STR = "json"
# LLFR-00396: title and format filters of the Save signals dialog, one
# filter per format of HLFR-00005.
SAVE_SIGNALS_DIALOG_TITLE_STR = "Save signals"
SIGNALS_FILTER_DICT = {
    file_writer.CSV_FORMAT_STR: "CSV files (*.csv)",
    file_writer.EXCEL_FORMAT_STR: "Excel files (*.xlsx)",
    file_writer.MAT_FORMAT_STR: "MAT files (*.mat)",
    file_writer.HDF5_FORMAT_STR: "HDF5 files (*.h5 *.hdf5)",
}
# LLFR-00196, LLFR-00195: widgets whose own Ctrl+Z (Cmd+Z) and Ctrl+Y
# (Cmd+Y) act on the typed text, so the workspace undo and redo must not
# run while one of them has the focus.
TEXT_INPUT_WIDGET_TUPLE = (QLineEdit, QTextEdit, QPlainTextEdit,
                           QAbstractSpinBox)
# LLFR-00191: the Redo shortcut. "Ctrl" is the Command key on macOS in a
# portable key sequence, so this is Ctrl+Y on Windows and Cmd+Y on
# macOS (StandardKey.Redo would be Shift+Cmd+Z on macOS). It is kept
# with the button tip texts in view.top_panel, so that the shortcut and
# its button tip change together (LLFR-00215, LLFR-00883).
REDO_SHORTCUT_STR = top_panel.REDO_SHORTCUT_STR
# LLFR-00406: the names of the file dialogs kept by the dialog pool.
OPEN_FILE_DIALOG_KEY_STR = "open_file"
SAVE_LAYOUT_DIALOG_KEY_STR = "save_layout"
LOAD_LAYOUT_DIALOG_KEY_STR = "load_layout"
SAVE_PDF_DIALOG_KEY_STR = "save_pdf"
SAVE_SIGNALS_DIALOG_KEY_STR = "save_signals"


class QuitFilter(QObject):
    """Application event filter that sees the app being quit.

    Inputs:
        quit_function: function without arguments, called when the
            application receives the Quit event (Cmd+Q, the Dock's Quit,
            a logout, QCoreApplication.quit()).
        parent: the QObject that owns the filter (the main window).
    """

    def __init__(self, quit_function, parent=None) -> None:
        """Store the function.

        Inputs: see the class docstring.
        Outputs: none.
        """
        super().__init__(parent)
        # LLFR-01024: what the main window does on a quit.
        self.quit_function = quit_function

    def eventFilter(self, watched, event) -> bool:
        """Close the undocked windows before Qt closes every window.

        Inputs:
            watched: the object the event is sent to.
            event: the QEvent.
        Outputs: False, so the quit goes on.
        """
        # LLFR-01024, LLFR-01073: Qt closes the windows in no set order,
        # so the undocked windows are closed by the app first, and none
        # of them takes the quit for the user's close of its tab.
        if (event.type() == QEvent.Type.Quit
                and watched is QApplication.instance()):
            self.quit_function()
        return False


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
        search_box_aligner: the SearchBoxAligner that keeps the bottom
            edge of the search box level with the lowest plot
            (LLFR-00424, LLFR-00652).
    """

    WINDOW_TITLE_STR = "plot_tool"
    # LLFR-00560: the title while a selected file is read and checked.
    LOADING_WINDOW_TITLE_STR = "plot_tool (loading)"
    INITIAL_WIDTH_I = 1200
    INITIAL_HEIGHT_I = 800
    # LLFR-00072: the signal list panel starts at 20% of the width, the
    # plot panel at 80%, and they keep that share (4:1) when the window
    # grows or shrinks.
    PLOT_PANEL_STRETCH_I = 4
    SIGNAL_LIST_STRETCH_I = 1
    SIGNAL_LIST_WIDTH_FRACTION_F = 0.20

    def __init__(self) -> None:
        """Create the panels and arrange them in the window.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        # LLFR-00058: one style sheet and one plot style for the whole
        # application, from view.theme.
        theme.apply_application_theme(QApplication.instance())
        # LLFR-00058: the window holds the three panels of HLFR-00001.
        # LLFR-00563: the normal title outside the reading of a file.
        self.setWindowTitle(self.WINDOW_TITLE_STR)
        # LLFR-00182: the app icon in the title bar and, set on the
        # application, in the Dock and app switcher (macOS) and the
        # taskbar (Windows) when the app is run from source.
        self.setWindowIcon(icons.app_icon())
        if QApplication.instance() is not None:
            QApplication.instance().setWindowIcon(self.windowIcon())
        self.resize(self.INITIAL_WIDTH_I, self.INITIAL_HEIGHT_I)
        self.top_panel = TopPanel()
        self.plot_panel = PlotPanel()
        self.signal_list_panel = SignalListPanel()
        # LLFR-00418: whether the busy pointer of a file read is shown.
        self.loading_cursor_shown_b = False

        # LLFR-00058: the signal list panel is to the right of the plot
        # panel. LLFR-00073: the user can drag the border between them.
        self.lower_splitter = PanelSplitter(
            self.SIGNAL_LIST_WIDTH_FRACTION_F)
        self.lower_splitter.addWidget(self.plot_panel)
        self.lower_splitter.addWidget(self.signal_list_panel)
        self.lower_splitter.setStretchFactor(0, self.PLOT_PANEL_STRETCH_I)
        self.lower_splitter.setStretchFactor(1, self.SIGNAL_LIST_STRETCH_I)
        # LLFR-00073: a comfortable handle to grab between the panels.
        # LLFR-01196: the main window's panel has no signal list button;
        # LLFR-01054: it is never hidden, and its splitter keeps it at
        # least 1 pixel wide, as no child of a PanelSplitter can be
        # collapsed.
        self.lower_splitter.setHandleWidth(theme.SPLITTER_HANDLE_WIDTH_I)

        # LLFR-00058: the top panel is above the other two panels.
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(
            theme.WINDOW_MARGIN_I, theme.WINDOW_TOP_MARGIN_I,
            theme.WINDOW_MARGIN_I, theme.WINDOW_MARGIN_I)
        central_layout.setSpacing(theme.PANEL_SPACING_I)
        central_layout.addWidget(self.top_panel)
        central_layout.addWidget(self.lower_splitter, 1)
        self.setCentralWidget(central_widget)
        # LLFR-00424, LLFR-00652: the bottom edge of the search box
        # follows the bottom edge of the lowest plot of the current tab.
        self.search_box_aligner = SearchBoxAligner(
            self.plot_panel, self.signal_list_panel, self)
        # HLFR-00124, HLFR-00126: window id -> UndockedWindow, and the
        # windows in tab order (LLFR-01091).
        self.undocked_window_dict = {}
        self.undocked_order_list = []
        # LLFR-01015, LLFR-01028, LLFR-01073, LLFR-01047, LLFR-01055:
        # the handlers of the windows, set by the plot controller.
        self.window_handler_dict = {}
        # LLFR-01185: Ctrl+P and Ctrl+F in the tab rename dialog.
        self.plot_panel.name_dialog_shortcut_handler = (
            self.run_name_dialog_shortcut)
        self.plot_panel.undock_handler = (
            lambda tab_id_i: self._run_window_handler("undock_handler",
                                                      tab_id_i))
        # LLFR-01142: a tab dropped outside the plot panel.
        self.plot_panel.undock_drop_handler = (
            lambda tab_id_i, x_i, y_i: self._run_window_handler(
                "undock_drop_handler", tab_id_i, x_i, y_i))
        # LLFR-01150, LLFR-01151: a tab dropped on an undocked window.
        self.plot_panel.window_at_point_function = (
            lambda x_i, y_i: self.window_at_point(x_i, y_i))
        self.plot_panel.window_drop_function = (
            self.request_docked_tab_window_drop)
        # LLFR-00203, LLFR-00665, LLFR-00709: the tabs the undocked
        # windows show.
        self.plot_panel.undocked_shown_page_function = (
            self.undocked_shown_page_list)
        # LLFR-01055: a drag of the main window's panel border.
        self.lower_splitter.drag_finished_handler = (
            lambda start_i, end_i: self._run_window_handler(
                "panel_width_handler", -1, start_i, end_i))
        # LLFR-01036, LLFR-01043: what every signal list panel shows,
        # kept so that a new window's panel shows the same.
        self.signal_list_state_dict = {}

        # LLFR-00406: every file dialog is built once, prepared after
        # the window is shown (prepare_file_dialogs), and reused.
        self.file_dialog_pool = file_dialogs.FileDialogPool()
        self.file_dialog_pool.register(
            OPEN_FILE_DIALOG_KEY_STR, lambda: self.build_open_file_dialog(""))
        self.file_dialog_pool.register(
            SAVE_LAYOUT_DIALOG_KEY_STR,
            lambda: self.build_layout_save_dialog(""))
        self.file_dialog_pool.register(
            LOAD_LAYOUT_DIALOG_KEY_STR,
            lambda: self.build_layout_load_dialog(""))
        self.file_dialog_pool.register(SAVE_PDF_DIALOG_KEY_STR,
                                       self.build_pdf_save_dialog)
        self.file_dialog_pool.register(
            SAVE_SIGNALS_DIALOG_KEY_STR,
            lambda: self.build_signals_save_dialog(
                "", "", file_writer.CSV_FORMAT_STR))

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
        # LLFR-00295: Enter in the signal list plots the selection.
        self.selected_signals_plot_handler = None
        # LLFR-00095: the search text goes to the signal list controller.
        self.search_text_handler = None
        # LLFR-00239, LLFR-00254, LLFR-00265, LLFR-00277, LLFR-00278:
        # the options of the signal menu go to the synthetic controller.
        self.signal_menu_handler_dict = {}
        # LLFR-00019, LLFR-00295, LLFR-00095, LLFR-00239, LLFR-00923:
        # the requests of the main window's panel (tab id -1).
        self.connect_signal_list_panel(self.signal_list_panel, -1)
        # LLFR-00115: the Reset zoom button goes to the plot controller.
        self.reset_zoom_handler = None
        self.top_panel.reset_zoom_button.triggered.connect(
            self._on_reset_zoom_triggered)
        # LLFR-00122, LLFR-00123: the Grid button goes to the plot
        # controller. LLFR-00147: the grid is shown at start (the
        # controller confirms it with set_grid_shown); the choice applies
        # to every plot, now and later (LLFR-00125).
        self.grid_handler = None
        self.grid_shown_b = True
        # LLFR-00124, LLFR-00678: the Grid button shows its active color
        # with it.
        self.top_panel.grid_button.setChecked(self.grid_shown_b)
        self.top_panel.grid_button.activated.connect(
            lambda: self._on_grid_clicked(True))
        self.top_panel.grid_button.deactivated.connect(
            lambda: self._on_grid_clicked(False))
        # LLFR-00127, LLFR-00133: the export controller saves the PDF
        # and copies the image.
        self.pdf_export_handler = None
        self.copy_handler = None
        self.top_panel.pdf_export_requested.connect(
            self._on_pdf_export_requested)
        self.top_panel.copy_requested.connect(self._on_copy_requested)
        # LLFR-00148 to LLFR-00150: holding the Tip key keeps the Tip
        # tool active; LLFR-00154 to LLFR-00156: holding Shift keeps the
        # Vertical marker tool active; LLFR-00197 to LLFR-00202: holding
        # X or Y keeps the Delta X or Delta Y tool active; LLFR-00287,
        # LLFR-00321: holding A or T keeps the Area or Text tool active;
        # LLFR-00367: holding R keeps the Arrow tool active;
        # LLFR-01092: holding Z keeps the Zoom tool active;
        # LLFR-00207, LLFR-01095: 0 alone, of the main keyboard or of
        # the keypad, resets the zoom; LLFR-00370: Esc alone
        # switches off the active plot tool; LLFR-00157: none of them
        # in text fields (any QLineEdit, QTextEdit, QPlainTextEdit or
        # spin box, so also the search boxes of dialogs and windows and
        # the fields of names and text notes).
        # The filter sees the keys of every widget and dialog of the
        # application, and consumes none.
        self.tip_key_changing_tool_b = False
        self.tool_key_filter = ToolKeyFilter(
            {TIP_KEY_I: TIP_TOOL_STR, MARKER_KEY_I: MARKER_TOOL_STR,
             DELTA_X_KEY_I: DELTA_X_TOOL_STR,
             DELTA_Y_KEY_I: DELTA_Y_TOOL_STR,
             AREA_KEY_I: AREA_TOOL_STR, TEXT_KEY_I: TEXT_TOOL_STR,
             ARROW_KEY_I: ARROW_TOOL_STR, ZOOM_KEY_I: ZOOM_TOOL_STR},
            self.on_tool_key_activate, self.on_tool_key_release,
            TEXT_INPUT_WIDGET_TUPLE, self,
            {RESET_ZOOM_KEY_I: self.on_reset_zoom_key,
             ESCAPE_KEY_I: self.on_escape_key})
        # LLFR-00148: the name used before the Shift key was added.
        self.tip_key_filter = self.tool_key_filter
        # LLFR-00302: over the signal list, Cmd/Ctrl and Shift select.
        self.tool_key_filter.set_selection_area_function(
            self.is_pointer_over_signal_list)
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self.tool_key_filter)
        # LLFR-01024: a quit closes every undocked window and keeps their
        # tabs.
        self.quit_filter = QuitFilter(self.close_all_undocked_windows, self)
        if application is not None:
            application.installEventFilter(self.quit_filter)
        # LLFR-00136, LLFR-00138: the Undo button goes to the plot
        # controller. LLFR-00137: so does Ctrl+Z (Cmd+Z on macOS, which
        # QKeySequence.StandardKey.Undo maps to), in this window.
        self.undo_handler = None
        self.top_panel.undo_button.triggered.connect(
            self._on_undo_triggered)
        # LLFR-00190, LLFR-00192: the Redo button goes to the plot
        # controller; LLFR-00191: so does Ctrl+Y (Cmd+Y on macOS).
        self.redo_handler = None
        self.top_panel.redo_button.triggered.connect(
            self._on_redo_triggered)
        # LLFR-01136: the handler of Ctrl+C (Cmd+C), set by the export
        # controller.
        self.copy_shortcut_handler = None
        # LLFR-00137, LLFR-00191, LLFR-01136, LLFR-01139, LLFR-01140: the
        # shortcuts of this window (tab id -1 for the main window).
        shortcut_dict = self.install_window_shortcuts(self, -1)
        self.undo_shortcut = shortcut_dict["undo"]
        self.redo_shortcut = shortcut_dict["redo"]
        self.copy_shortcut = shortcut_dict["copy"]
        self.pdf_shortcut = shortcut_dict["pdf"]
        self.search_shortcut = shortcut_dict["search"]
        # LLFR-00216, LLFR-00217: the layout buttons go to the layout
        # controller.
        self.save_layout_handler = None
        self.load_layout_handler = None
        self.top_panel.save_layout_requested.connect(
            self._on_save_layout_requested)
        self.top_panel.load_layout_requested.connect(
            self._on_load_layout_requested)
        # LLFR-00394: the Save signals button goes to the save signals
        # controller.
        self.save_signals_handler = None
        self.top_panel.save_signals_requested.connect(
            self._on_save_signals_requested)
        # LLFR-00359: the Report a bug button opens the page of a new
        # issue; it needs no controller, since it changes nothing in the
        # model (no file, plot or undo history is touched).
        self.top_panel.report_bug_requested.connect(
            self._on_report_bug_requested)

    def connect_signal_list_panel(self, panel, window_id_i: int) -> None:
        """Connect the requests of a signal list panel to the handlers.

        Inputs:
            panel: a SignalListPanel.
            window_id_i: id of the undocked window of the panel, or -1
                for the main window.
        Outputs: none.
        """
        # LLFR-01037: every panel works as the main window's.
        # LLFR-00019, LLFR-01038: a double-click plots in the tab that
        # the panel's window shows at that moment.
        panel.signal_double_clicked.connect(
            lambda name_str: self._on_signal_double_clicked(
                name_str, self.window_shown_tab_id(window_id_i)))
        # LLFR-00295, LLFR-01038, LLFR-01040: Enter plots the panel's own
        # selection in the tab its window shows.
        panel.selected_signals_plot_requested.connect(
            lambda name_list: self._on_selected_signals_plot_requested(
                name_list, self.window_shown_tab_id(window_id_i)))
        # LLFR-00095, LLFR-01041: the search text, shared by every panel.
        panel.search_text_changed.connect(
            lambda text_str: self._on_search_text_changed(text_str, panel))
        panel.synthetic_operation_requested.connect(
            lambda name_str, operation_str: self._run_signal_menu_handler(
                "create", name_str, operation_str))
        panel.copy_name_requested.connect(
            lambda name_str: self._run_signal_menu_handler(
                "copy_name", name_str))
        panel.rename_signal_requested.connect(
            lambda name_str: self._run_signal_menu_handler(
                "rename", name_str))
        panel.delete_signal_requested.connect(
            lambda name_str: self._run_signal_menu_handler(
                "delete", name_str))
        panel.copy_equation_requested.connect(
            lambda name_str: self._run_signal_menu_handler(
                "copy_equation", name_str))
        # LLFR-00923: the options of the file menu.
        panel.close_file_requested.connect(
            lambda number_i: self._run_signal_menu_handler(
                "close_file", number_i))
        panel.close_all_files_requested.connect(
            lambda: self._run_signal_menu_handler("close_all_files"))
        # LLFR-00997, LLFR-00998: the icons of the file name rows go to
        # the signal list controller; LLFR-01036: a file hidden in one
        # panel is hidden in every panel.
        panel.file_expand_toggled.connect(
            lambda number_i: self._run_signal_menu_handler(
                "toggle_file", number_i))

    def signal_list_panel_list(self) -> list:
        """Return every signal list panel, the main window's first.

        Inputs: none.
        Outputs: a list of SignalListPanel.
        """
        # LLFR-01036: the panels that show the same signal list.
        return [self.signal_list_panel] + [
            window.signal_list_panel
            for window in self.undocked_window_dict.values()]

    def broadcast_signal_list(self, method_name_str: str,
                              *argument_tuple) -> None:
        """Call a method of every signal list panel and keep the call.

        Inputs:
            method_name_str: the name of a SignalListPanel method.
            argument_tuple: its arguments.
        Outputs: none. The last call of each method is kept, so that the
            panel of a window opened later shows the same.
        """
        # LLFR-01036: the same file rows, signals, synthetic signals,
        # letters and colors in every panel, at every moment.
        self.signal_list_state_dict[method_name_str] = argument_tuple
        for panel in self.signal_list_panel_list():
            getattr(panel, method_name_str)(*argument_tuple)

    def fill_signal_list_panel(self, panel) -> None:
        """Give a new panel what the other panels show.

        Inputs:
            panel: the SignalListPanel of a new undocked window.
        Outputs: none.
        """
        # LLFR-01036: the kinds, the operations and the time signals
        # first, then the list that uses them.
        for method_name_str in ("set_operation_groups", "set_signal_kinds",
                                "set_time_signal_name",
                                "set_time_signal_names",
                                "set_collapsed_file_numbers"):
            if method_name_str in self.signal_list_state_dict:
                getattr(panel, method_name_str)(
                    *self.signal_list_state_dict[method_name_str])
        # LLFR-01043: the shared search text, with no new filtering.
        panel.search_box.blockSignals(True)
        panel.search_box.setText(self.signal_list_panel.search_text())
        panel.search_box.blockSignals(False)
        list_call_tuple = self.signal_list_state_dict.get("signal_list")
        if list_call_tuple is not None:
            getattr(panel, list_call_tuple[0])(*list_call_tuple[1])

    def dialog_parent(self):
        """Return the window that boxes of a plot action are shown over.

        Inputs: none.
        Outputs: the active undocked window, or this main window.
        """
        # LLFR-01023: over the undocked window of the action; the boxes
        # of the top panel stay over the main window.
        active_window = QApplication.activeWindow()
        if active_window in self.undocked_window_dict.values():
            return active_window
        return self

    # ----------------------------------------------------------------
    # Undocked windows (HLFR-00124 to HLFR-00139)
    # ----------------------------------------------------------------

    def set_window_handlers(self, **handler_dict) -> None:
        """Set the functions called for the undocked windows.

        Inputs:
            handler_dict: undock_handler, dock_handler,
                window_close_handler and panel_toggle_handler, each
                taking a tab id, and panel_width_handler, taking a tab id
                (-1 for the main window) and the panel widths at the
                press and at the release of a border drag.
        Outputs: none.
        """
        # LLFR-01015, LLFR-01028, LLFR-01073, LLFR-01047, LLFR-01048,
        # LLFR-01055: the plot controller decides.
        self.window_handler_dict.update(handler_dict)

    def _run_window_handler(self, key_str: str, *argument_tuple) -> None:
        """Call a window handler, if it is set.

        Inputs:
            key_str: the handler name.
            argument_tuple: its arguments.
        Outputs: none.
        """
        # LLFR-01015, LLFR-01028, LLFR-01073, LLFR-01055.
        handler = self.window_handler_dict.get(key_str)
        if handler is not None:
            handler(*argument_tuple)

    def screen_area_list(self) -> list:
        """Return the available area of every screen.

        Inputs: none.
        Outputs: a list of (x, y, width, height) in desktop pixels.
        """
        # LLFR-01083, LLFR-01084: where a window can be placed.
        area_list = []
        for screen in QApplication.screens():
            geometry = screen.availableGeometry()
            area_list.append((geometry.x(), geometry.y(), geometry.width(),
                              geometry.height()))
        return area_list

    def main_screen_area(self) -> tuple:
        """Return the available area of the screen of the main window.

        Inputs: none.
        Outputs: (x, y, width, height), or () when unknown.
        """
        # LLFR-01083: a window off-screen goes onto this screen.
        screen = self.screen()
        if screen is None:
            return ()
        geometry = screen.availableGeometry()
        return (geometry.x(), geometry.y(), geometry.width(),
                geometry.height())

    def new_window_tuple(self) -> tuple:
        """Return the window that an undock opens.

        Inputs: none.
        Outputs: (x, y, width, height): the plot panel's size, at its
            position moved 30 pixels right and down, in desktop pixels.
        """
        # LLFR-01016, LLFR-01128: from the main window's plot panel.
        top_left = self.plot_panel.mapToGlobal(QPoint(0, 0))
        return new_window_tuple((top_left.x(), top_left.y(),
                                 self.plot_panel.width(),
                                 self.plot_panel.height()))

    def main_panel_width(self) -> int:
        """Return the width of the main window's signal list panel.

        Inputs: none.
        Outputs: the width in pixels.
        """
        # LLFR-01051, LLFR-01055: the main window's panel.
        return self.lower_splitter.last_widget_width()

    def window_state_dict(self) -> dict:
        """Return the windows and panel widths as shown now.

        Inputs: none.
        Outputs: {"main_panel_width": width of the main window's panel,
            "windows": {window id: (x, y, width, height, panel width)},
            "shown": {window id: id of the tab it shows}}.
        """
        # LLFR-01056, LLFR-01059, LLFR-00225 items 9, 13 and 14;
        # LLFR-01156: the tab each window shows.
        return {"main_panel_width": self.main_panel_width(),
                "windows": {window_id_i: window.window_tuple()
                            + (window.panel_width(),)
                            for window_id_i, window
                            in self.undocked_window_dict.items()},
                "shown": {window_id_i: window.shown_tab_id()
                          for window_id_i, window
                          in self.undocked_window_dict.items()
                          if window.shown_tab_id() >= 0}}

    def build_undocked_window(self, window_id_i: int):
        """Create an undocked window, with its connections.

        Inputs:
            window_id_i: id of the window.
        Outputs: the UndockedWindow, not shown yet.
        """
        window = UndockedWindow(window_id_i, self.plot_panel)
        window.close_handler = (
            lambda closed_id_i: self._run_window_handler(
                "window_close_handler", closed_id_i))
        window.dock_handler = (
            lambda tab_id_i: self._run_window_handler("dock_handler",
                                                      tab_id_i))
        window.panel_toggle_handler = (
            lambda toggled_id_i: self._run_window_handler(
                "panel_toggle_handler", toggled_id_i))
        window.panel_width_handler = (
            lambda changed_id_i, start_i, end_i: self._run_window_handler(
                "panel_width_handler", changed_id_i, start_i, end_i))
        window.main_panel_width_function = self.main_panel_width
        # LLFR-01143, LLFR-01151, LLFR-01152, LLFR-01157: a drag of one
        # of its tabs, dropped somewhere.
        window.tab_drop_handler = self.request_window_tab_drop
        # LLFR-01071: the Undo, Redo, Copy, PDF and search shortcuts in
        # the window too.
        shortcut_dict = self.install_window_shortcuts(window, window_id_i)
        window.undo_shortcut = shortcut_dict["undo"]
        window.redo_shortcut = shortcut_dict["redo"]
        window.copy_shortcut = shortcut_dict["copy"]
        window.pdf_shortcut = shortcut_dict["pdf"]
        window.search_shortcut = shortcut_dict["search"]
        # LLFR-01035, LLFR-01036, LLFR-01037: its own panel, the same
        # list, the same requests.
        self.connect_signal_list_panel(window.signal_list_panel,
                                       window_id_i)
        self.fill_signal_list_panel(window.signal_list_panel)
        return window

    def window_shown_tab_id(self, window_id_i: int) -> int:
        """Return the tab a window shows.

        Inputs:
            window_id_i: id of an undocked window, or -1 for the main
                window.
        Outputs: the tab id, or -1 for the main window or an unknown
            window (the controller then uses the main window's tab).
        """
        # LLFR-01038, LLFR-01136: the tab the window shows when the
        # request is made.
        window = self.undocked_window_dict.get(window_id_i)
        if window is None:
            return -1
        return window.shown_tab_id()

    def install_window_shortcuts(self, window, window_id_i: int) -> dict:
        """Give a window the keyboard shortcuts of the app.

        Inputs:
            window: the MainWindow or an UndockedWindow.
            window_id_i: id of the undocked window, -1 for the main
                window.
        Outputs: {"undo", "redo", "copy", "pdf", "search"} -> the
            QShortcut, each acting while the window is active.
        """
        # LLFR-00137, LLFR-00191: Undo and Redo; LLFR-01136: Copy, of
        # the tab shown in this window; LLFR-01139: Save all tabs as
        # PDF; LLFR-01140: the search box of this window. LLFR-01071:
        # the same in every window.
        sequence_function_dict = {
            "undo": (QKeySequence(top_panel.UNDO_STANDARD_KEY),
                     self._on_undo_shortcut),
            "redo": (QKeySequence(REDO_SHORTCUT_STR),
                     self._on_redo_shortcut),
            "copy": (QKeySequence(top_panel.COPY_SHORTCUT_STR),
                     partial(self._on_copy_shortcut, window_id_i)),
            "pdf": (QKeySequence(top_panel.PDF_SHORTCUT_STR),
                    self._on_pdf_shortcut),
            "search": (QKeySequence(top_panel.SEARCH_SHORTCUT_STR),
                       partial(self._on_search_shortcut, window_id_i)),
        }
        shortcut_dict = {}
        for key_str, (sequence, function) in sequence_function_dict.items():
            shortcut = QShortcut(sequence, window)
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
            shortcut.activated.connect(function)
            shortcut_dict[key_str] = shortcut
        return shortcut_dict

    def dropped_window_tuple(self, x_i: int, y_i: int) -> tuple:
        """Return the window that a drop outside the plot panel opens.

        Inputs:
            x_i, y_i: the point of the drop, in desktop pixels.
        Outputs: (x, y, width, height): the drop point as the top-left
            corner and the size of the plot panel; set_window_tabs keeps
            it on a screen.
        """
        # LLFR-01142, LLFR-01016: at the pointer, the plot panel's size.
        return (int(x_i), int(y_i), int(self.plot_panel.width()),
                int(self.plot_panel.height()))

    def window_at_point(self, x_i: int, y_i: int):
        """Return the undocked window at a desktop point.

        Inputs:
            x_i, y_i: the point, in desktop pixels.
        Outputs: the UndockedWindow shown on top at that point, or None
            when the point is on no undocked window (for example on the
            main window above it, or on no window of the app).
        """
        # LLFR-01150, LLFR-01152: the window the user dropped a tab on.
        top_window = QApplication.topLevelAt(QPoint(int(x_i), int(y_i)))
        for window in self.undocked_window_dict.values():
            if top_window is window and window.isVisible():
                return window
        return None

    def request_docked_tab_window_drop(self, tab_id_i: int, x_i: int,
                                       y_i: int) -> bool:
        """Move a docked tab dropped on an undocked window into it.

        Inputs:
            tab_id_i: id of the dragged docked tab.
            x_i, y_i: the point of the drop, in desktop pixels.
        Outputs: True when the point is on an undocked window, which
            then gets the drop (LLFR-01150, LLFR-01151).
        """
        window = self.window_at_point(x_i, y_i)
        if window is None:
            return False
        # LLFR-01150: after its last tab; LLFR-01151: on its tab row, at
        # the place of the pointer.
        self._run_window_handler("window_drop_handler", tab_id_i,
                                 window.window_id_i,
                                 window.tab_index_at(x_i, y_i))
        return True

    def request_window_tab_drop(self, window, tab_id_i: int,
                                start_index_i: int, x_i: int,
                                y_i: int) -> None:
        """Decide what a tab of an undocked window dropped somewhere does.

        Inputs:
            window: the UndockedWindow the tab was dragged from.
            tab_id_i: id of the dragged tab.
            start_index_i: its place in the window's tab row at the press.
            x_i, y_i: the point of the drop, in desktop pixels.
        Outputs: none.
        """
        if tab_id_i not in window.tab_id_list():
            return
        index_i = window.tab_id_list().index(tab_id_i)
        # LLFR-01143: on the main window's tab row, docked there.
        docked_index_i = self.plot_panel.docked_drop_index(x_i, y_i)
        target_window = self.window_at_point(x_i, y_i)
        if docked_index_i >= 0 and target_window is None:
            self.restore_dragged_tab(window, index_i, start_index_i)
            self._run_window_handler("dock_drop_handler", tab_id_i,
                                     docked_index_i)
            return
        if target_window is window and window.tab_index_at(x_i, y_i) >= 0:
            # LLFR-01166: on its own tab row, left where it was dropped;
            # LLFR-01090: back at its place, nothing.
            if index_i != start_index_i:
                self._run_window_handler("window_tab_move_handler",
                                         tab_id_i, index_i)
            return
        self.restore_dragged_tab(window, index_i, start_index_i)
        if target_window is not None and target_window is not window:
            # LLFR-01152: on another undocked window, moved into it.
            self._run_window_handler(
                "window_drop_handler", tab_id_i, target_window.window_id_i,
                target_window.tab_index_at(x_i, y_i))
        elif target_window is None and self.is_point_outside_app_windows(
                x_i, y_i):
            # LLFR-01167: outside every window of the app, into a new
            # undocked window at the drop point.
            self._run_window_handler("new_window_drop_handler", tab_id_i,
                                     x_i, y_i)
        # LLFR-01067: anywhere else, nothing changes.

    def is_point_outside_app_windows(self, x_i: int, y_i: int) -> bool:
        """Tell whether a desktop point is outside every window of the app.

        Inputs:
            x_i, y_i: the point, in desktop pixels.
        Outputs: True when the point is on neither the main window, while
            it is shown, nor any shown undocked window.
        """
        # LLFR-01167: a drop outside the app opens a new window;
        # LLFR-01067: a drop on a window of the app, off a tab row, does
        # nothing.
        point = QPoint(int(x_i), int(y_i))
        window_list = [self] + list(self.undocked_window_dict.values())
        for window in window_list:
            if (window.isVisible() and not window.isMinimized()
                    and window.frameGeometry().contains(point)):
                return False
        return True

    def restore_dragged_tab(self, window, index_i: int,
                            start_index_i: int) -> None:
        """Put a dragged tab back at its place in its window's tab row.

        Inputs:
            window: the UndockedWindow.
            index_i: where Qt left the tab during the drag.
            start_index_i: its place at the press.
        Outputs: none.
        """
        # LLFR-01067: a tab dropped elsewhere keeps its place; Qt moved
        # it along the row during the drag.
        if index_i != start_index_i and 0 <= start_index_i < (
                window.tab_bar.count()):
            window.tab_bar.moveTab(index_i, start_index_i)

    def request_dock_drop(self, tab_id_i: int, x_i: int, y_i: int) -> None:
        """Dock a tab whose tab button was dropped on the main tab row.

        Inputs:
            tab_id_i: id of the undocked tab.
            x_i, y_i: the point of the drop, in desktop pixels.
        Outputs: none. A drop anywhere else changes nothing
            (LLFR-01067).
        """
        # LLFR-01143: the place between the docked tabs under the
        # pointer; -1 off the tab row of the main window.
        docked_index_i = self.plot_panel.docked_drop_index(x_i, y_i)
        if docked_index_i < 0:
            return
        self._run_window_handler("dock_drop_handler", tab_id_i,
                                 docked_index_i)

    def window_of_tab(self, tab_id_i: int):
        """Return the undocked window that holds a tab.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: the UndockedWindow, or None for a docked or unknown tab.
        """
        # LLFR-01063: each undocked tab is in one window.
        for window in self.undocked_window_dict.values():
            if tab_id_i in window.tab_id_list():
                return window
        return None

    def set_window_tabs(self, window_id_i: int, tab_id_list: list,
                        window_tuple: tuple, panel_shown_b: bool,
                        panel_width_i: int, shown_tab_id_i: int) -> None:
        """Show an undocked window with exactly these tabs.

        Inputs:
            window_id_i: id of the window.
            tab_id_list: its tabs, in order, each already added with
                add_tab_view.
            window_tuple: (x, y, width, height) for a window that is not
                open yet, or () for the window of an undock.
            panel_shown_b: whether its signal list panel is shown.
            panel_width_i: the panel width, 0 for the first width.
            shown_tab_id_i: the tab the window shows.
        Outputs: none. A window that is open already keeps its position
            and size. A tab it held and no longer holds goes back to the
            main window, unless another window takes it.
        """
        window = self.undocked_window_dict.get(window_id_i)
        new_window_b = window is None
        if new_window_b:
            # LLFR-01015: a new window.
            window = self.build_undocked_window(window_id_i)
            self.undocked_window_dict[window_id_i] = window
            if len(window_tuple) != 4:
                window_tuple = self.new_window_tuple()
            # LLFR-01083, LLFR-01084: kept on a screen; LLFR-01085: not
            # reported, as the view never tells the load report.
            window.set_window_tuple(placed_window_tuple(
                window_tuple, self.screen_area_list(),
                self.main_screen_area()))
        page_list = []
        for tab_id_i in tab_id_list:
            page = self.plot_panel.page_dict.get(tab_id_i)
            if page is None:
                continue
            # LLFR-01150, LLFR-01152, LLFR-01015: the page leaves the main
            # window or another undocked window. LLFR-01022, LLFR-01039:
            # it keeps its plot widgets and their connections, so every
            # plot action and every signal drop works as in the main
            # window.
            other_window = self.window_of_tab(tab_id_i)
            if other_window is not None and other_window is not window:
                other_window.take_page(tab_id_i)
            elif other_window is None:
                self.plot_panel.detach_page(tab_id_i)
            page_list.append(page)
        left_id_list = [tab_id_i for tab_id_i in window.tab_id_list()
                        if tab_id_i not in tab_id_list]
        # LLFR-01063: its tabs in their order; LLFR-01061: the tab it
        # shows, with its name as the title.
        window.set_pages(page_list, shown_tab_id_i)
        for tab_id_i in left_id_list:
            # LLFR-01028: a tab that left the window and no other window
            # took is a docked tab again.
            if self.window_of_tab(tab_id_i) is None:
                self.plot_panel.attach_page(tab_id_i)
        # LLFR-01050, LLFR-01078, LLFR-01129: the panel as saved.
        window.set_panel(panel_shown_b, panel_width_i)
        if new_window_b:
            window.show()

    def dock_tab_view(self, tab_id_i: int) -> None:
        """Put a tab of an undocked window back into the main window.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: none. The window stays open until set_undocked_windows
            closes it, if it was its last tab (LLFR-01029).
        """
        window = self.window_of_tab(tab_id_i)
        if window is None:
            return
        # LLFR-01028: the last docked tab; LLFR-01156: the window shows
        # another of its tabs.
        window.take_page(tab_id_i)
        self.plot_panel.attach_page(tab_id_i)

    def set_undocked_windows(self, window_id_list: list) -> None:
        """Close the windows that are not open in the model.

        Inputs:
            window_id_list: the undocked windows, in tab order
                (LLFR-01091).
        Outputs: none.
        """
        # LLFR-01060, LLFR-01080, LLFR-01033, LLFR-01145, LLFR-01029: a
        # window with no tab left, or not in the model, closes.
        for window_id_i in list(self.undocked_window_dict):
            if window_id_i not in window_id_list:
                self.close_window(window_id_i)
        self.undocked_order_list = [
            window_id_i for window_id_i in window_id_list
            if window_id_i in self.undocked_window_dict]

    def close_window(self, window_id_i: int) -> None:
        """Close an undocked window without deleting its tabs.

        Inputs:
            window_id_i: id of the window.
        Outputs: none. Its tabs that still exist go back to the main
            window.
        """
        # LLFR-01029, LLFR-01080: closed by the app.
        window = self.undocked_window_dict.pop(window_id_i, None)
        if window is None:
            return
        for tab_id_i in window.tab_id_list():
            page = window.take_page(tab_id_i)
            if page is not None and self.plot_panel.page_dict.get(
                    tab_id_i) is page:
                # The tab is still shown: it goes back to the main window.
                self.plot_panel.attach_page(tab_id_i)
        window.close_by_app()

    def close_all_undocked_windows(self) -> None:
        """Close every undocked window, keeping their tabs.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01024: the main window closes them all; each page goes
        # back to the plot panel, which still keeps it.
        for window_id_i in list(self.undocked_window_dict):
            self.close_window(window_id_i)
        self.undocked_order_list = []

    def undocked_window(self, window_id_i: int):
        """Return an undocked window by its id.

        Inputs:
            window_id_i: id of the window.
        Outputs: the UndockedWindow, or None.
        """
        # HLFR-00124, LLFR-01031: the windows of the model.
        return self.undocked_window_dict.get(window_id_i)

    def undocked_shown_page_list(self) -> list:
        """Return the tab page each undocked window shows.

        Inputs: none.
        Outputs: a list of TabPage.
        """
        # LLFR-00203, LLFR-00665, LLFR-00709, LLFR-01162, LLFR-01163: the
        # tabs that are shown, besides the main window's.
        return [window.page() for window in self.undocked_window_dict.values()
                if window.page() is not None]

    def set_window_panel(self, window_id_i: int, shown_b: bool,
                         width_i: int) -> None:
        """Show or hide the signal list panel of an undocked window.

        Inputs:
            window_id_i: id of the window.
            shown_b: True to show it.
            width_i: its width in pixels.
        Outputs: none.
        """
        # LLFR-01047, LLFR-01048.
        window = self.undocked_window_dict.get(window_id_i)
        if window is not None:
            window.set_panel(shown_b, width_i)

    def set_main_panel_width(self, width_i: int) -> None:
        """Give the main window's signal list panel a width.

        Inputs:
            width_i: the width in pixels.
        Outputs: none. The plot panel takes the rest.
        """
        # LLFR-01055, LLFR-00138: an undo of a border drag.
        total_i = sum(self.lower_splitter.sizes())
        width_i = max(int(width_i), 1)
        if total_i <= width_i:
            return
        self.lower_splitter.initial_sizes_set_b = True
        self.lower_splitter.setSizes([total_i - width_i, width_i])

    def set_undock_enabled(self, enabled_b: bool) -> None:
        """Enable or disable the undock buttons of the docked tabs.

        Inputs:
            enabled_b: False while the main window holds one docked tab.
        Outputs: none.
        """
        # LLFR-01018, LLFR-01019.
        self.plot_panel.set_undock_enabled(enabled_b)

    def closeEvent(self, event) -> None:
        """Close every undocked window when the main window closes.

        Inputs:
            event: the QCloseEvent.
        Outputs: none. With no visible window left, Qt quits the app.
        """
        # LLFR-01024: every undocked window closes, and the app quits.
        self.close_all_undocked_windows()
        super().closeEvent(event)

    def set_open_file_handler(self, handler) -> None:
        """Set the function called when the Open file button is clicked.

        Inputs:
            handler: a function without arguments, called when the
                Open file button becomes active.
        Outputs: none.
        """
        # LLFR-00005: the controller shows the dialog through ``handler``.
        self.open_file_handler = handler

    def ask_open_file_path(self, start_folder_str: str = "") -> list:
        """Show the file selection dialog and return the chosen paths.

        Inputs:
            start_folder_str: folder the dialog shows when it opens; ""
                lets Qt choose.
        Outputs: the paths of the selected files (LLFR-00951), or []
            when the user cancelled the dialog.
        """
        # LLFR-00005: show the file selection dialog.
        # LLFR-00007: an empty path means the dialog was cancelled.
        # LLFR-00204: the folder is chosen by the file controller.
        # LLFR-00406: the dialog built once, shown again.
        dialog = self.file_dialog_pool.prepared_dialog(
            OPEN_FILE_DIALOG_KEY_STR, start_folder_str)
        path_value = self.run_open_file_dialog(dialog)
        # LLFR-00951: one or several paths; the controller takes them in
        # the order of LLFR-00952.
        if isinstance(path_value, (list, tuple)):
            return [str(path_str) for path_str in path_value if path_str]
        return [str(path_value)] if path_value else []

    def build_open_file_dialog(self, start_folder_str: str) -> QFileDialog:
        """Build the file selection dialog of the Open file button.

        Inputs:
            start_folder_str: the folder the dialog shows; "" lets Qt
                choose.
        Outputs: a QFileDialog, not shown, that selects one or several
            existing files, with the time series filter first and "All
            files".
        """
        # LLFR-00005, LLFR-00011: the same dialog as QFileDialog's
        # getOpenFileNames, with its filters; LLFR-00951: several files
        # can be selected at once.
        dialog = QFileDialog(self, OPEN_FILE_DIALOG_TITLE_STR,
                             start_folder_str, OPEN_FILE_FILTER_STR)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        return dialog

    def run_open_file_dialog(self, dialog) -> list:
        """Run the Open file dialog modally and return the chosen paths.

        Inputs:
            dialog: the QFileDialog of build_open_file_dialog.
        Outputs: the chosen paths, or [] when the user cancelled. Tests
            replace this method to answer without a modal dialog (with
            a path or a list of paths).
        """
        # LLFR-00005, LLFR-00007, LLFR-00951: the modal dialog.
        return file_dialogs.run_file_dialog_paths(dialog)

    def prepare_file_dialogs(self) -> None:
        """Build every file dialog at once, so the first click is fast.

        Inputs: none.
        Outputs: none. No dialog is shown.
        """
        # LLFR-00406: the same steps as schedule_file_dialog_preparation,
        # without waiting.
        self.file_dialog_pool.prepare_all()

    def schedule_file_dialog_preparation(
            self, start_delay_ms_i: int =
            file_dialogs.PREPARE_START_DELAY_MS_I) -> None:
        """Prepare the file dialogs in steps, once the window is shown.

        Inputs:
            start_delay_ms_i: milliseconds before the first step.
        Outputs: none. The steps run one per event-loop turn; none of
            them shows a dialog (issue #165).
        """
        # LLFR-00406, LLFR-00188: after the window is shown, so that
        # preparing the dialogs neither delays the window nor keeps it
        # from answering the user.
        self.file_dialog_pool.schedule_preparation(self, start_delay_ms_i)

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

    def show_loading_indication(self) -> None:
        """Show the busy pointer and the loading title while a file is read.

        Inputs: none.
        Outputs: none. The window is repainted before this returns, so
            the indication is seen while the file is read.
        """
        # LLFR-00418: the busy pointer over the app window. It is set
        # only once, so that hide_loading_indication restores it fully.
        if not self.loading_cursor_shown_b:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.loading_cursor_shown_b = True
        # LLFR-00560: "plot_tool (loading)" in the window title.
        self.setWindowTitle(self.LOADING_WINDOW_TITLE_STR)
        # LLFR-00418, LLFR-00560: repaint now; the file is read in this
        # same event handler, so without this the title would change only
        # after the read. User input waits, so no other action starts
        # meanwhile.
        QApplication.processEvents(
            QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    def hide_loading_indication(self) -> None:
        """Restore the normal pointer and the normal window title.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00561: reading ended; the busy pointer goes away before
        # any File Open Error box or the time signal window.
        if self.loading_cursor_shown_b:
            QApplication.restoreOverrideCursor()
            self.loading_cursor_shown_b = False
        # LLFR-00562, LLFR-00563: the normal title, also before any box
        # or window is shown.
        self.setWindowTitle(self.WINDOW_TITLE_STR)

    def show_open_files_limit_notification(self, message_str: str) -> None:
        """Show the box of an Open file click with 10 files open.

        Inputs:
            message_str: the sentence of the box.
        Outputs: none.
        """
        # LLFR-00896: shown in place of the file selection dialog.
        message_boxes.build_open_files_limit_box(self, message_str).exec()

    def show_refused_files_notification(self, message_str: str) -> None:
        """Show the box that lists the refused selected files.

        Inputs:
            message_str: one line per refused file, with its reason.
        Outputs: none.
        """
        # LLFR-00956: after the File Open Error box, if any.
        message_boxes.build_refused_files_box(self, message_str).exec()

    def show_signal_names(self, signal_name_list: list) -> None:
        """Show signal names in the list, with no file name row.

        Inputs:
            signal_name_list: the signal names, in their order.
        Outputs: none.
        """
        # LLFR-00054, LLFR-00939: the names in their order; LLFR-01036:
        # in every panel.
        self.signal_list_state_dict["signal_list"] = (
            "show_signal_names", (signal_name_list,))
        for panel in self.signal_list_panel_list():
            panel.show_signal_names(signal_name_list)

    def show_signal_groups(self, group_list: list) -> None:
        """Show the file name rows and the signals of the open files.

        Inputs:
            group_list: one tuple (file number, file name row text,
                shown signal names, no-match text or "") per open data
                file, in the order of the numbers.
        Outputs: none.
        """
        # LLFR-00362, LLFR-00938, LLFR-00939, LLFR-00097: the groups of
        # the signal list; LLFR-01036: in every panel.
        self.signal_list_state_dict["signal_list"] = (
            "show_signal_groups", (group_list,))
        for panel in self.signal_list_panel_list():
            panel.show_signal_groups(group_list)

    def set_collapsed_file_numbers(self, number_set: set) -> None:
        """Tell the signal list which files are shown collapsed.

        Inputs:
            number_set: the numbers of the files whose signals are
                hidden.
        Outputs: none. Used by the next show_signal_groups.
        """
        # LLFR-00994, LLFR-00995: [-] or [+] on each file name row;
        # LLFR-01036, LLFR-01175: the same in every panel, also in the
        # panel of a window opened later (broadcast_signal_list keeps it).
        self.broadcast_signal_list("set_collapsed_file_numbers",
                                   set(number_set))

    def set_file_toggle_handler(self, handler) -> None:
        """Set the function called by the icons of the file name rows.

        Inputs:
            handler: function taking a file number.
        Outputs: none.
        """
        # LLFR-00997, LLFR-00998: hide or show the signals of a file.
        self.signal_menu_handler_dict["toggle_file"] = handler

    def set_search_text_handler(self, handler) -> None:
        """Set the function called when the search box text changes.

        Inputs:
            handler: a function taking the new text (str).
        Outputs: none.
        """
        # LLFR-00095: the signal list controller filters the list.
        self.search_text_handler = handler

    def clear_search(self) -> None:
        """Empty the search box of the signal list panel.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00104: the search is cleared when a file is opened; the
        # change reaches every panel (LLFR-01041).
        self.signal_list_panel.clear_search()

    # ----------------------------------------------------------------
    # Signal menu facade, used by the synthetic controller
    # ----------------------------------------------------------------

    def set_synthetic_operation_groups(self, group_list: list) -> None:
        """Set the operations listed by "Create synthetic signal".

        Inputs:
            group_list: list of (group label, list of (operation id,
                operation label)), in menu order.
        Outputs: none.
        """
        # LLFR-00268: the groups and operations of the menu.
        self.broadcast_signal_list("set_operation_groups", group_list)

    def set_signal_kinds(self, synthetic_name_set: set,
                         fft_name_set: set) -> None:
        """Tell the signal list which names are synthetic or FFT signals.

        Inputs:
            synthetic_name_set: the synthetic signal names.
            fft_name_set: the FFT signal names among them.
        Outputs: none.
        """
        # LLFR-00242: italics; LLFR-00251, LLFR-00254, LLFR-00265,
        # LLFR-00278: the options of their menu.
        self.broadcast_signal_list("set_signal_kinds", synthetic_name_set,
                                   fft_name_set)

    def set_signal_menu_handlers(self, create_handler, copy_name_handler,
                                 rename_handler, delete_handler,
                                 copy_equation_handler) -> None:
        """Set the functions called by the options of the signal menu.

        Inputs:
            create_handler: function taking (signal name, operation id).
            copy_name_handler: function taking a signal name.
            rename_handler: function taking a signal name.
            delete_handler: function taking a signal name.
            copy_equation_handler: function taking a signal name.
        Outputs: none.
        """
        # LLFR-00239, LLFR-00254, LLFR-00265, LLFR-00277, LLFR-00278;
        # the handlers of the file menu are kept (LLFR-00923).
        self.signal_menu_handler_dict.update({
            "create": create_handler, "copy_name": copy_name_handler,
            "rename": rename_handler, "delete": delete_handler,
            "copy_equation": copy_equation_handler})

    def set_file_menu_handlers(self, close_file_handler,
                               close_all_files_handler) -> None:
        """Set the functions called by the options of the file menu.

        Inputs:
            close_file_handler: function taking a file number.
            close_all_files_handler: function without arguments.
        Outputs: none.
        """
        # LLFR-00923: "Close file" and "Close all files".
        self.signal_menu_handler_dict["close_file"] = close_file_handler
        self.signal_menu_handler_dict["close_all_files"] = (
            close_all_files_handler)

    def ask_close_file(self, question_str: str) -> bool:
        """Ask whether to close one data file.

        Inputs:
            question_str: the question, with what the close does.
        Outputs: True when the user proceeds.
        """
        # LLFR-00924, LLFR-00925: only Yes closes the file.
        return message_boxes.ask_close_file(self.dialog_parent(), question_str)

    def ask_close_all_files(self, question_str: str) -> bool:
        """Ask once whether to close every data file.

        Inputs:
            question_str: the question, with what the close does.
        Outputs: True when the user proceeds.
        """
        # LLFR-00934, LLFR-00935: only Yes closes the files.
        return message_boxes.ask_close_all_files(self.dialog_parent(),
                                                 question_str)

    def _run_signal_menu_handler(self, key_str: str, *argument_tuple):
        """Pass a signal menu request to its handler.

        Inputs:
            key_str: which option was chosen.
            argument_tuple: the signal name, and the operation id for a
                creation.
        Outputs: none. Ignored when no handler is set.
        """
        # LLFR-00239: the controller runs the chosen option.
        handler = self.signal_menu_handler_dict.get(key_str)
        if handler is not None:
            handler(*argument_tuple)

    def run_modal_dialog(self, dialog) -> bool:
        """Run a synthetic signal dialog modally.

        Inputs:
            dialog: a dialog of view.synthetic_dialogs.
        Outputs: True when it was closed with OK. Tests replace this
            method to fill in the dialog without a modal loop.
        """
        # LLFR-00245, LLFR-00269, LLFR-00272, LLFR-00275: the dialog.
        return synthetic_dialogs.run_dialog(dialog)

    def ask_synthetic_parameter(self, title_str: str, prompt_str: str,
                                field_list: list, check_function,
                                choice_tuple: tuple = ()):
        """Ask for the numbers an operation needs.

        Inputs:
            title_str: the window title (the operation's label).
            prompt_str: the question, with the allowed ranges.
            field_list: (label_str, starting text) per field.
            check_function: value list -> reason ("" when allowed);
                the dialog stays open and shows the reason while there
                is one.
            choice_tuple: () or (label, [(id, label)], id at first),
                for example how a filter starts (LLFR-00245).
        Outputs: the accepted texts, one per field, then the chosen id
            when there is a choice; None when the user cancelled.
        """
        # LLFR-00245, LLFR-00269, LLFR-00272: the parameter dialog.
        dialog = synthetic_dialogs.build_parameter_dialog(
            self.dialog_parent(), title_str, prompt_str, field_list,
            check_function,
            choice_tuple)
        try:
            if not self.run_modal_dialog(dialog):
                return None
            return dialog.value_list()
        finally:
            dialog.deleteLater()

    def ask_second_signal(self, title_str: str, prompt_str: str,
                          name_list: list, selected_name_str: str,
                          search_function=None,
                          no_match_text_str: str = ""):
        """Ask for the second signal of a product.

        Inputs:
            title_str: the window title.
            prompt_str: the question.
            name_list: the names to choose from.
            selected_name_str: the name selected at first.
            search_function: text -> the names of name_list that match
                it, in the order to show them; None shows every name.
            no_match_text_str: the text shown when no name matches.
        Outputs: the chosen name, or None when the user cancelled.
        """
        # LLFR-00275, LLFR-00285: the second signal dialog, with its
        # search box.
        dialog = synthetic_dialogs.build_second_signal_dialog(
            self.dialog_parent(), title_str, prompt_str, name_list,
            selected_name_str,
            search_function, no_match_text_str)
        try:
            if not self.run_modal_dialog(dialog):
                return None
            return dialog.chosen_name()
        finally:
            dialog.deleteLater()

    def ask_time_signal_name(self, prompt_str: str, name_list: list,
                             search_function, no_match_text_str: str,
                             check_function, file_name_str: str = ""):
        """Ask the user for the signal that goes on the x-axis.

        Inputs:
            prompt_str: the text of the window.
            name_list: every signal of the file, in the file's order.
            search_function: text -> the names of name_list that match
                it, in the order to show them.
            no_match_text_str: the text shown when no name matches.
            check_function: name -> the reason it can't be the time
                signal, or "" when it can.
            file_name_str: the name of the file the window is for, with
                its extension and without its folder (LLFR-00957).
        Outputs: the confirmed name, or None when the user cancelled.
        """
        # LLFR-00325, LLFR-00329: the time signal window.
        # LLFR-00957: the window names its file.
        dialog = synthetic_dialogs.build_time_signal_dialog(
            self, prompt_str, name_list, search_function,
            no_match_text_str, check_function, file_name_str)
        try:
            if not self.run_modal_dialog(dialog):
                # LLFR-00327: cancelled.
                return None
            return dialog.chosen_name()
        finally:
            dialog.deleteLater()

    def set_time_signal_names(self, name_list: list) -> None:
        """Tell the signal list which signals are time signals.

        Inputs:
            name_list: the time signal of each open data file.
        Outputs: none. Used by the next show_signal_names.
        """
        # LLFR-00332: the time signal of each open data file in green.
        self.broadcast_signal_list("set_time_signal_names", name_list)

    def set_files_time_range(self, range_tuple: tuple) -> None:
        """Tell every time plot the time range of the open data files.

        Inputs:
            range_tuple: (start_s, end_s), or () while no file is open.
        Outputs: none. Zooms and pans of the time plots stay within it.
        """
        # LLFR-00119, LLFR-00676, LLFR-00916: kept for the plots created
        # later too.
        self.plot_panel.set_files_time_range(tuple(range_tuple))

    def set_time_signal_name(self, name_str: str) -> None:
        """Tell the signal list which signal is the time signal.

        Inputs:
            name_str: the time signal of the opened file.
        Outputs: none. Used by the next show_signal_names.
        """
        # LLFR-00332: the time signal name is shown in green.
        self.broadcast_signal_list("set_time_signal_name", name_str)

    def ask_delete_synthetic_signal(self, name_str: str,
                                    dependent_name_list: list) -> bool:
        """Ask whether to delete a synthetic signal and its dependents.

        Inputs:
            name_str: the synthetic signal name.
            dependent_name_list: the synthetic signals computed from it.
        Outputs: True when the user proceeds.
        """
        # LLFR-00255: the question names the dependents.
        return message_boxes.ask_delete_synthetic_signal(
            self.dialog_parent(), name_str, dependent_name_list)

    def ask_synthetic_signal_name(self, current_name_str: str):
        """Let the user type a new name for a synthetic signal.

        Inputs:
            current_name_str: the part of the signal's name after the
                prefix of its data file, shown in the dialog
                (LLFR-00959).
        Outputs: the typed text (not stripped), or None when cancelled.
        """
        # LLFR-00266, LLFR-00959: the dialog starts from the current
        # name without its prefix.
        # LLFR-01185: Ctrl+P and Ctrl+F in the dialog take the typed name.
        new_name_str, accepted_b = name_dialog.ask_name_text(
            self.dialog_parent(), RENAME_SIGNAL_DIALOG_TITLE_STR,
            RENAME_SIGNAL_DIALOG_LABEL_STR, current_name_str,
            self.run_name_dialog_shortcut)
        if not accepted_b:
            return None
        return str(new_name_str)

    def show_signal_information(self, title_str: str,
                                message_str: str) -> None:
        """Show an information box of the synthetic signals.

        Inputs:
            title_str: the window title.
            message_str: the sentence that says why.
        Outputs: none.
        """
        # LLFR-00247, LLFR-00250, LLFR-00267: an information box.
        message_boxes.build_signal_information_box(
            self.dialog_parent(), title_str, message_str).exec()

    def copy_text_to_clipboard(self, text_str: str) -> None:
        """Put a text on the system clipboard.

        Inputs:
            text_str: the text.
        Outputs: none.
        """
        # LLFR-00277, LLFR-00279: the name or the equation, as text.
        QApplication.clipboard().setText(str(text_str))

    def set_signal_double_click_handler(self, handler) -> None:
        """Set the function called when a signal name is double-clicked.

        Inputs:
            handler: a function taking the signal name (str).
        Outputs: none.
        """
        # LLFR-00019: the plot controller creates a plot through it.
        self.signal_double_click_handler = handler

    def set_selected_signals_plot_handler(self, handler) -> None:
        """Set the function called when Enter plots the selection.

        Inputs:
            handler: a function taking the selected names (list of str),
                in list order.
        Outputs: none.
        """
        # LLFR-00295: the plot controller creates one plot through it.
        self.selected_signals_plot_handler = handler

    def rename_shown_signal(self, old_name_str: str,
                            new_name_str: str) -> None:
        """Give a signal of the signal list its new name.

        Inputs:
            old_name_str: the name shown now.
            new_name_str: the new name.
        Outputs: none.
        """
        # LLFR-00266, LLFR-00292: a renamed signal stays selected.
        for panel in self.signal_list_panel_list():
            panel.rename_shown_signal(old_name_str, new_name_str)

    def select_only_signal(self, signal_name_str: str) -> None:
        """Select one signal of the signal list, alone, in every panel.

        Inputs:
            signal_name_str: the name of a shown signal.
        Outputs: none. A panel that doesn't show the name keeps its
            selection.
        """
        # LLFR-01194: the new synthetic signal is selected; LLFR-01036:
        # every panel shows the same list, so each one selects it.
        for panel in self.signal_list_panel_list():
            panel.select_only_signal(signal_name_str)

    def clear_signal_selection(self) -> None:
        """Deselect every signal of the signal list.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00292: no signal of a previous file stays selected.
        for panel in self.signal_list_panel_list():
            panel.clear_signal_selection()

    def is_pointer_over_signal_list(self) -> bool:
        """Tell whether the mouse pointer is over the signal list panel.

        Inputs: none.
        Outputs: True while the pointer is inside the shown panel, as
            Qt's enter and leave events tell (QWidget.underMouse, which
            is also true while the pointer is over a child of it).
        """
        # LLFR-00302: there the Tip key and Shift select signals, in any
        # window (LLFR-01071).
        return any(panel.isVisible() and panel.underMouse()
                   for panel in self.signal_list_panel_list())

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
        # mouse according to the tool; LLFR-01072: the plots of the
        # undocked windows too, as their pages stay in plot_widget_dict.
        for plot_widget in self.plot_panel.plot_widget_dict.values():
            plot_widget.set_plot_tool(tool_str)

    def current_plot_tool(self) -> str:
        """Return the plot tool applied to the plots.

        Inputs: none.
        Outputs: the tool name, NO_TOOL_STR when none is active.
        """
        # LLFR-00079, LLFR-00109: the tool stays until it is changed.
        return self.plot_tool_str

    def on_tool_key_activate(self, tool_str: str) -> None:
        """Make a tool active because its tool key is held alone.

        Inputs:
            tool_str: TIP_TOOL_STR for the Tip key, MARKER_TOOL_STR for
                the Shift key, DELTA_X_TOOL_STR for X, DELTA_Y_TOOL_STR
                for Y, AREA_TOOL_STR for A, TEXT_TOOL_STR for T and
                ARROW_TOOL_STR for R.
        Outputs: none. The tool change goes the same way as a click on
            the tool's button, so the controller is told of it.
        """
        # LLFR-00148, LLFR-00154, LLFR-00197, LLFR-00200, LLFR-00287,
        # LLFR-00321, LLFR-00367: the tool's button becomes active and
        # the other tool buttons are deactivated as in LLFR-00079.
        self.tip_key_changing_tool_b = True
        try:
            self.top_panel.plot_tool_button_dict[tool_str].setChecked(True)
            self.top_panel.activate_plot_tool(tool_str)
        finally:
            self.tip_key_changing_tool_b = False

    def on_tool_key_release(self) -> None:
        """Leave no plot tool active because a tool key hold ended.

        Inputs: none.
        Outputs: none. The tool change goes the same way as a second
            click on the active tool button.
        """
        # LLFR-00149, LLFR-00150, LLFR-00155, LLFR-00156, LLFR-00157,
        # LLFR-00198, LLFR-00199, LLFR-00201, LLFR-00202, LLFR-00288,
        # LLFR-00289, LLFR-00322, LLFR-00323: no plot tool is
        # active afterwards, whatever tool was active before the tool key
        # was pressed. LLFR-00167: leaving a delta tool discards its
        # first point, as for a click on its button.
        self.tip_key_changing_tool_b = True
        try:
            self.top_panel.show_plot_tool(NO_TOOL_STR)
            self.top_panel.deactivate_plot_tools()
        finally:
            self.tip_key_changing_tool_b = False

    def is_mouse_drag_in_progress(self) -> bool:
        """Tell whether the user is dragging the mouse on a plot.

        Inputs: none.
        Outputs: True during a pan, a drag of an object or a time span
            selection on any plot, or a drag of a tab.
        """
        # LLFR-00454: the 0 key does nothing during a mouse drag, a tab
        # drag included.
        return self.plot_panel.is_mouse_drag_in_progress() or any(
            window.is_tab_drag_in_progress()
            for window in self.undocked_window_dict.values())

    def on_reset_zoom_key(self) -> None:
        """Reset the zoom because the 0 key was pressed alone.

        Inputs: none.
        Outputs: none. Nothing happens during a mouse drag, or while a
            modal dialog or a menu of the application is open.
        """
        # LLFR-00454: during a pan, a drag of an object, a time span
        # selection or a tab drag, 0 does nothing.
        if self.is_mouse_drag_in_progress():
            return
        # LLFR-00207: the zoom is reset in the main window, not behind a
        # message box, a name dialog or an open menu.
        if (QApplication.activeModalWidget() is not None
                or QApplication.activePopupWidget() is not None):
            return
        # LLFR-00207, LLFR-00115, LLFR-00116: exactly as a click on the
        # Reset zoom button, with its active color for at least 0.3 s.
        self.top_panel.reset_zoom_button.click()

    def on_escape_key(self) -> None:
        """Switch off the active plot tool because Esc was pressed alone.

        Inputs: none.
        Outputs: none. Nothing happens while no plot tool is active,
            during a mouse drag, while a modal dialog or a menu of the
            application is open, or while another window of the
            application is the active one.
        """
        # LLFR-00370: with no tool active, Esc does nothing and shows
        # nothing.
        if self.current_plot_tool() == NO_TOOL_STR:
            return
        # LLFR-00370, LLFR-00530: during a mouse drag, Esc does nothing.
        if self.is_mouse_drag_in_progress():
            return
        # LLFR-00370: in a menu or a dialog Esc keeps its own meaning
        # (it closes them) and leaves the plot tool alone. A text field
        # (LLFR-00157) is already left out by the key filter.
        if (QApplication.activeModalWidget() is not None
                or QApplication.activePopupWidget() is not None):
            return
        # LLFR-01071: in the main window and in every undocked window.
        active_window = QApplication.activeWindow()
        if (active_window is not None and active_window is not self
                and active_window not in self.undocked_window_dict.values()):
            return
        # LLFR-00370, LLFR-00002: as a second click on the active tool
        # button: every tool button normal, no plot tool active.
        self.top_panel.show_plot_tool(NO_TOOL_STR)
        self.top_panel.deactivate_plot_tools()

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

    def set_undo_handler(self, handler) -> None:
        """Set the function called by the Undo button and its shortcut.

        Inputs:
            handler: a function without arguments that undoes the most
                recent undoable action.
        Outputs: none.
        """
        # LLFR-00138: the controller restores the previous state.
        self.undo_handler = handler

    def set_undo_enabled(self, enabled_b: bool) -> None:
        """Enable the Undo button, or disable it and show it paler.

        Inputs:
            enabled_b: True while an action can be undone.
        Outputs: none.
        """
        # LLFR-00141: disabled and paler when nothing is left to undo.
        self.top_panel.undo_button.setEnabled(bool(enabled_b))

    def is_undo_enabled(self) -> bool:
        """Tell whether the Undo button is enabled.

        Inputs: none.
        Outputs: True while an action can be undone.
        """
        # LLFR-00141: the state the shortcut follows too.
        return self.top_panel.undo_button.isEnabled()

    def run_undo(self) -> None:
        """Run the undo handler when an action can be undone.

        Inputs: none.
        Outputs: none. Does nothing while the Undo button is disabled.
        """
        # LLFR-00141: with nothing to undo, nothing happens.
        if not self.is_undo_enabled() or self.undo_handler is None:
            return
        # LLFR-00138: reverse the most recent undoable action.
        self.undo_handler()

    def set_redo_handler(self, handler) -> None:
        """Set the function called by the Redo button and its shortcut.

        Inputs:
            handler: a function without arguments that reapplies the
                most recently undone action.
        Outputs: none.
        """
        # LLFR-00192: the controller restores the state after the action.
        self.redo_handler = handler

    def set_redo_enabled(self, enabled_b: bool) -> None:
        """Enable the Redo button, or disable it and show it paler.

        Inputs:
            enabled_b: True while an undone action can be redone.
        Outputs: none.
        """
        # LLFR-00194: disabled and paler when nothing is left to redo.
        self.top_panel.redo_button.setEnabled(bool(enabled_b))

    def is_redo_enabled(self) -> bool:
        """Tell whether the Redo button is enabled.

        Inputs: none.
        Outputs: True while an undone action can be redone.
        """
        # LLFR-00194: the state the shortcut follows too.
        return self.top_panel.redo_button.isEnabled()

    def run_redo(self) -> None:
        """Run the redo handler when an undone action can be redone.

        Inputs: none.
        Outputs: none. Does nothing while the Redo button is disabled.
        """
        # LLFR-00194: with nothing to redo, nothing happens.
        if not self.is_redo_enabled() or self.redo_handler is None:
            return
        # LLFR-00192: reapply the most recently undone action.
        self.redo_handler()

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

    def set_tab_arrangement_handlers(self, move_tab_handler,
                                     plot_matrix_handler) -> None:
        """Set the functions called for a tab move and a matrix choice.

        Inputs:
            move_tab_handler: function taking a tab id and its new place.
            plot_matrix_handler: function taking a tab id, rows and
                columns.
        Outputs: none.
        """
        # LLFR-01087, LLFR-01100: the controller decides.
        self.plot_panel.set_tab_arrangement_handlers(move_tab_handler,
                                                     plot_matrix_handler)

    def move_tab_view(self, tab_id_i: int, index_i: int) -> None:
        """Move a tab to a place in the tab row.

        Inputs:
            tab_id_i: id of the tab.
            index_i: its new place, from 0.
        Outputs: none.
        """
        # LLFR-01087: the tab order of the model.
        self.plot_panel.move_tab_view(tab_id_i, index_i)

    def set_tab_matrix_view(self, tab_id_i: int, row_count_i: int,
                            column_count_i: int) -> None:
        """Lay the plots of a tab out in a plot matrix.

        Inputs:
            tab_id_i: id of the tab.
            row_count_i: number of rows.
            column_count_i: number of columns.
        Outputs: none.
        """
        # LLFR-01100, LLFR-01108 to LLFR-01111.
        self.plot_panel.set_tab_matrix_view(tab_id_i, row_count_i,
                                            column_count_i)

    def set_plot_order_view(self, tab_id_i: int,
                            plot_id_list: list) -> None:
        """Place the plots of a tab in a new fill order.

        Inputs:
            tab_id_i: id of the tab.
            plot_id_list: the plot ids in fill order.
        Outputs: none.
        """
        # LLFR-01118: the plots after a swap.
        self.plot_panel.set_plot_order_view(tab_id_i, plot_id_list)

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
        # LLFR-00028: remove the tab; LLFR-01156: its window shows
        # another of its tabs; LLFR-01145, LLFR-01033: a window left with
        # no tab is closed by set_undocked_windows.
        window = self.window_of_tab(tab_id_i)
        if window is not None:
            window.take_page(tab_id_i)
        self.plot_panel.remove_tab_view(tab_id_i)

    def rename_tab_view(self, tab_id_i: int, name_str: str) -> None:
        """Show a new name on a tab.

        Inputs:
            tab_id_i: id of the tab.
            name_str: the new name.
        Outputs: none.
        """
        # LLFR-00030: show the name chosen by the user; LLFR-01062: in
        # the title of its window too.
        self.plot_panel.rename_tab_view(tab_id_i, name_str)
        window = self.window_of_tab(tab_id_i)
        if window is not None:
            window.refresh_tab_names()

    def clear_tab_views(self) -> None:
        """Remove every tab and plot.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00024, LLFR-00138: the tabs are shown again from the model.
        # LLFR-01059: the windows stay open; set_window_tabs gives them
        # their new pages, and set_undocked_windows closes the others.
        for window in self.undocked_window_dict.values():
            window.take_all_pages()
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

    def add_plot_view(self, tab_id_i: int, plot_id_i: int,
                      kind_str: str = TIME_PLOT_KIND_STR) -> None:
        """Create a plot at the bottom of a tab.

        Inputs:
            tab_id_i: id of the tab.
            plot_id_i: id of the plot in the model.
            kind_str: TIME_PLOT_KIND_STR for a time plot or
                FREQUENCY_PLOT_KIND_STR for a frequency plot (LLFR-00256).
        Outputs: none.
        """
        # LLFR-00019, LLFR-01109: the new plot takes the next slot.
        # LLFR-00256: with frequency or time on its x-axis.
        self.plot_panel.add_plot_view(tab_id_i, plot_id_i, kind_str)
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
                  pinned_tip_list: list, marker_data_list=(),
                  delta_marker_data_list=()) -> None:
        """Draw the curves, tips, vertical and delta markers of a plot.

        Inputs:
            plot_id_i: id of the plot.
            curve_data_list: tuples (signal_name_str, time_array,
                value_array, color_str, width_i).
            pinned_tip_list: tuples (signal_name_str, time_s, value_f,
                label_offset_tuple); see PlotWidget.set_pinned_tips.
            marker_data_list: tuples (marker_id_i, name_str, time_s,
                color_str), the vertical markers shared by every plot
                (LLFR-00205).
            delta_marker_data_list: tuples (delta_marker_id_i, kind_str,
                first_point_tuple, second_point_tuple, delta_f); see
                PlotWidget.set_delta_markers.
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
        # LLFR-00168, LLFR-00170, LLFR-00176: draw the delta markers.
        plot_widget.set_delta_markers(delta_marker_data_list)

    def set_text_notes(self, plot_id_i: int,
                       text_note_data_list: list) -> None:
        """Draw the text notes of a plot.

        Inputs:
            plot_id_i: id of the plot.
            text_note_data_list: tuples (text_str, time_s, value_f,
                size_i, border_color_str, text_color_str); see
                PlotWidget.set_text_notes.
        Outputs: none. An unknown plot id is ignored.
        """
        # LLFR-00337, LLFR-00340: the notes are shown only on their plot.
        plot_widget = self.plot_panel.plot_view(plot_id_i)
        if plot_widget is not None:
            plot_widget.set_text_notes(text_note_data_list)

    def set_arrows(self, plot_id_i: int, arrow_data_list: list) -> None:
        """Draw the arrows of a plot.

        Inputs:
            plot_id_i: id of the plot.
            arrow_data_list: tuples (start_time_s, start_value_f,
                end_time_s, end_value_f, color_str); see
                PlotWidget.set_arrows.
        Outputs: none. An unknown plot id is ignored.
        """
        # LLFR-00375: the arrows are shown only on their plot.
        plot_widget = self.plot_panel.plot_view(plot_id_i)
        if plot_widget is not None:
            plot_widget.set_arrows(arrow_data_list)

    def set_markers(self, marker_data_list: list) -> None:
        """Draw the shared vertical markers on every plot of every tab.

        Inputs:
            marker_data_list: tuples (marker_id_i, name_str, time_s,
                color_str), in placing order.
        Outputs: none. Only the markers are drawn again.
        """
        # LLFR-00205: every marker on every plot, after it was placed,
        # moved, renamed or deleted on any of them.
        self.plot_panel.set_markers(marker_data_list)

    def set_areas(self, area_data_list: list) -> None:
        """Draw the shared areas on every time plot of every tab.

        Inputs:
            area_data_list: tuples (area_id_i, name_str, start_s, end_s,
                color_str), in creation order.
        Outputs: none. Only the areas are drawn again.
        """
        # LLFR-00310: every area on every time plot, after it was
        # created, moved, resized, renamed or deleted on any of them.
        self.plot_panel.set_areas(area_data_list)

    def set_plot_areas(self, plot_id_i: int, area_data_list: list) -> None:
        """Draw the areas of one plot, after the plot was drawn.

        Inputs:
            plot_id_i: id of the plot.
            area_data_list: tuples (area_id_i, name_str, start_s, end_s,
                color_str); empty for a frequency plot (LLFR-00311).
        Outputs: none. An unknown plot id is ignored.
        """
        # LLFR-00310: a time plot created after the areas shows them too.
        plot_widget = self.plot_panel.plot_view(plot_id_i)
        if plot_widget is not None:
            plot_widget.set_areas(area_data_list)

    def ask_area_name(self, current_name_str: str):
        """Let the user type a new name for an area.

        Inputs:
            current_name_str: the area's name, shown in the dialog.
        Outputs: the typed text (not stripped), or None when the user
            cancelled the dialog.
        """
        # LLFR-00315: the dialog starts from the current name; a blank
        # answer is returned as typed, and the controller keeps the old
        # name without a message (LLFR-00720).
        # LLFR-01185: Ctrl+P and Ctrl+F in the dialog take the typed name.
        new_name_str, accepted_b = name_dialog.ask_name_text(
            self.dialog_parent(), RENAME_AREA_DIALOG_TITLE_STR,
            RENAME_AREA_DIALOG_LABEL_STR, current_name_str,
            self.run_name_dialog_shortcut)
        if not accepted_b:
            return None
        return str(new_name_str)

    def ask_delta_marker_name(self, current_name_str: str):
        """Let the user type a new name for a delta marker.

        Inputs:
            current_name_str: the marker's name, shown in the dialog.
        Outputs: the typed text (not stripped), or None when the user
            cancelled the dialog.
        """
        # LLFR-00429: the dialog starts from the current name.
        # LLFR-00854, LLFR-00855: a blank answer is returned as typed;
        # the controller keeps the old name without a message.
        return self.ask_name(RENAME_DELTA_DIALOG_TITLE_STR,
                             RENAME_DELTA_DIALOG_LABEL_STR,
                             current_name_str)

    def ask_arrow_name(self, current_name_str: str):
        """Let the user type a new name for an arrow.

        Inputs:
            current_name_str: the arrow's name, shown in the dialog.
        Outputs: the typed text (not stripped), or None when the user
            cancelled the dialog.
        """
        # LLFR-00439: the dialog starts from the current name.
        # LLFR-00874, LLFR-00875: a blank answer is returned as typed;
        # the controller keeps the old name without a message.
        return self.ask_name(RENAME_ARROW_DIALOG_TITLE_STR,
                             RENAME_ARROW_DIALOG_LABEL_STR,
                             current_name_str)

    def ask_name(self, title_str: str, label_str: str,
                 current_name_str: str):
        """Show a one-line text dialog that starts from a name.

        Inputs:
            title_str: the dialog's title.
            label_str: the text above the field.
            current_name_str: the text the field starts with.
        Outputs: the typed text, or None when the user cancelled.
        """
        # LLFR-00429, LLFR-00439: the same dialog as for flags and areas.
        # LLFR-01185: Ctrl+P and Ctrl+F in the dialog take the typed name.
        new_name_str, accepted_b = name_dialog.ask_name_text(
            self.dialog_parent(), title_str, label_str, current_name_str,
            self.run_name_dialog_shortcut)
        if not accepted_b:
            return None
        return str(new_name_str)

    def set_delta_first_point(self, plot_id_i: int,
                              point_tuple: tuple) -> None:
        """Show or remove the dot of a delta marker's first point.

        Inputs:
            plot_id_i: id of the plot.
            point_tuple: (signal_name_str, time_s, value_f), or () to
                remove the dot.
        Outputs: none. An unknown plot id is ignored.
        """
        # LLFR-00163, LLFR-00164, LLFR-00167: the controller keeps the
        # first point; the plot only draws its dot.
        plot_widget = self.plot_panel.plot_view(plot_id_i)
        if plot_widget is not None:
            plot_widget.set_delta_first_point(point_tuple)

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

    def ask_color(self, current_color_str: str):
        """Let the user choose a color in the shared color picker.

        Inputs:
            current_color_str: the item's current color, "#rrggbb", shown
                as chosen when the picker opens (LLFR-00389).
        Outputs: the confirmed color as "#rrggbb" in lowercase, or None
            when the user cancelled the picker (LLFR-00390).
        """
        # LLFR-00388: the flags, areas, text notes (and arrows) all use
        # this one picker window.
        return color_picker.pick_color(self.dialog_parent(), current_color_str)

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
        # LLFR-01185: Ctrl+P and Ctrl+F in the dialog take the typed name.
        new_name_str, accepted_b = name_dialog.ask_name_text(
            self.dialog_parent(), RENAME_MARKER_DIALOG_TITLE_STR,
            RENAME_MARKER_DIALOG_LABEL_STR, current_name_str,
            self.run_name_dialog_shortcut)
        if not accepted_b:
            return None
        return str(new_name_str)

    def show_full_tab_notification(self, row_count_i: int = 5,
                                   column_count_i: int = 1) -> None:
        """Show the Full Tab Notification box.

        Inputs:
            row_count_i: rows of the full tab's plot matrix.
            column_count_i: columns of the full tab's plot matrix.
        Outputs: none.
        """
        # LLFR-00032, LLFR-01127: the tab is full; use a new tab or,
        # below 10 x 10, a larger plot matrix.
        message_boxes.show_full_tab_notification(self.dialog_parent(),
                                                 row_count_i,
                                                 column_count_i)

    def show_plot_kind_mismatch_notification(self) -> None:
        """Show the box saying FFT and time signals need separate plots.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00257: an FFT signal dropped on a time plot, or another
        # signal dropped on a frequency plot, is not drawn.
        message_boxes.show_plot_kind_mismatch_notification(
            self.dialog_parent())

    def show_tab_name_taken_notification(self, name_str: str) -> None:
        """Show the Tab Name Taken box.

        Inputs:
            name_str: the name the user typed, without surrounding spaces.
        Outputs: none.
        """
        # LLFR-00211: another tab already has the typed name.
        message_boxes.show_tab_name_taken_notification(
            self.dialog_parent(), name_str)

    # ----------------------------------------------------------------
    # Export facade, used by the export controller (plain types only)
    # ----------------------------------------------------------------

    def set_export_handlers(self, pdf_export_handler, copy_handler,
                            copy_shortcut_handler=None) -> None:
        """Set the functions called by the Export menu and Copy button.

        Inputs:
            pdf_export_handler: function without arguments, called when
                "Save all tabs as PDF" is chosen.
            copy_handler: function without arguments, called when the
                Copy button is clicked.
            copy_shortcut_handler: function taking the tab id of the
                window where Ctrl+C (Cmd+C) is pressed, -1 for the main
                window; None to keep none.
        Outputs: none.
        """
        # LLFR-00128, LLFR-00133: the controller runs the flows;
        # LLFR-01136: and the Copy shortcut's.
        self.pdf_export_handler = pdf_export_handler
        self.copy_handler = copy_handler
        self.copy_shortcut_handler = copy_shortcut_handler

    def exportable_tab_count(self) -> int:
        """Return the number of tabs that hold at least one plot.

        Inputs: none.
        Outputs: an int.
        """
        # LLFR-00129, LLFR-00145: the tabs that get a PDF page.
        return len(plot_export.exportable_page_list(
            self.plot_panel.tab_widget, self.undocked_page_list()))

    def current_tab_plot_count(self) -> int:
        """Return the number of plots in the current tab.

        Inputs: none.
        Outputs: an int, 0 when there is no tab.
        """
        # LLFR-00146: a tab without plots has nothing to copy.
        return len(self.plot_panel.plot_id_list(self.current_tab_id()))

    def ask_pdf_save_path(self, start_folder_str: str = "") -> str:
        """Show the save file dialog for a .pdf file.

        Inputs:
            start_folder_str: the folder the dialog shows; "" keeps the
                folder it shows now.
        Outputs: the chosen path, or "" when the user cancelled.
        """
        # LLFR-00128: a save file dialog for a .pdf file.
        # LLFR-00130: an empty path means the dialog was cancelled.
        # LLFR-00406: the dialog built once, shown again, in the folder
        # of LLFR-01179 and LLFR-01180, with no file name of an earlier
        # use (LLFR-01183).
        dialog = self.file_dialog_pool.prepared_dialog(
            SAVE_PDF_DIALOG_KEY_STR, start_folder_str)
        return self.run_pdf_save_dialog(dialog) or ""

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
        return file_dialogs.run_file_dialog(dialog)

    def ask_replace_existing_file(self, path_str: str) -> bool:
        """Ask whether to replace an existing file.

        Inputs:
            path_str: the path of the existing file.
        Outputs: True when the user chose to replace it.
        """
        # LLFR-00128: asked when ".pdf" was added after the dialog and
        # the resulting file already exists.
        return message_boxes.ask_replace_existing_file(self, path_str)

    def save_tabs_pdf(self, path_str: str,
                      description_str: str = "") -> tuple:
        """Save the plots of every tab that holds a plot to a PDF file.

        Inputs:
            path_str: the path of the .pdf file.
            description_str: the description of the open data files,
                written below each tab's name (LLFR-00971).
        Outputs: a tuple (saved_b, reason_str).
        """
        # LLFR-00129, LLFR-00131, LLFR-00971: one page per tab with a
        # plot, with the data files below the tab's name.
        # LLFR-01091: the docked tabs, then the undocked ones.
        return plot_export.save_tabs_pdf(self.plot_panel.tab_widget,
                                         path_str, description_str,
                                         self.undocked_page_list())

    def undocked_page_list(self) -> list:
        """Return the tab pages of the undocked windows, in tab order.

        Inputs: none.
        Outputs: a list of TabPage (LLFR-01091).
        """
        # LLFR-00129, LLFR-01091: after the docked tabs, window by window
        # in the order of the windows, each window's tabs in its order.
        order_list = [window_id_i for window_id_i in self.undocked_order_list
                      if window_id_i in self.undocked_window_dict]
        order_list += [window_id_i for window_id_i in self.undocked_window_dict
                       if window_id_i not in order_list]
        return [page for window_id_i in order_list
                for page in self.undocked_window_dict[window_id_i].page_list()]

    def copy_current_tab_image(self, description_str: str = "") -> tuple:
        """Put an image of the current tab's plots on the clipboard.

        Inputs:
            description_str: the description of the open data files,
                in a strip above the plots (LLFR-00972).
        Outputs: a tuple (copied_b, reason_str).
        """
        # LLFR-00133, LLFR-00972: the plots of the current tab, as on
        # screen, below the strip with the data files.
        return plot_export.copy_current_tab_image(
            self.plot_panel.tab_widget, description_str)

    def window_tab_page(self, tab_id_i: int):
        """Return the tab page shown in a window.

        Inputs:
            tab_id_i: the tab of an undocked window, -1 for the main
                window.
        Outputs: the TabPage, or None.
        """
        # LLFR-01136: the tab shown in the window of the shortcut.
        if tab_id_i < 0:
            return self.plot_panel.tab_widget.currentWidget()
        window = self.window_of_tab(tab_id_i)
        return None if window is None else window.page()

    def window_of(self, tab_id_i: int):
        """Return a window by the tab id of an undocked window.

        Inputs:
            tab_id_i: the tab of an undocked window, -1 for the main
                window.
        Outputs: the UndockedWindow, or this main window.
        """
        # LLFR-01138: the box is shown over the window of the shortcut.
        window = self.window_of_tab(tab_id_i)
        return self if window is None else window

    def window_tab_plot_count(self, tab_id_i: int) -> int:
        """Return the number of plots of the tab shown in a window.

        Inputs:
            tab_id_i: the tab of an undocked window, -1 for the main
                window.
        Outputs: the number of plots, 0 when there is no tab.
        """
        # LLFR-01138: a tab with no plot has nothing to copy.
        page = self.window_tab_page(tab_id_i)
        return len(getattr(page, "plot_widget_list", []))

    def copy_window_tab_image(self, description_str: str,
                              tab_id_i: int) -> tuple:
        """Put an image of the tab shown in a window on the clipboard.

        Inputs:
            description_str: the description of the open data files, in
                a strip above the plots (LLFR-00972).
            tab_id_i: the tab of an undocked window, -1 for the main
                window.
        Outputs: a tuple (copied_b, reason_str).
        """
        # LLFR-01136: as LLFR-00133, for the tab of that window.
        if tab_id_i < 0:
            return self.copy_current_tab_image(description_str)
        window = self.window_of_tab(tab_id_i)
        if window is None:
            return (False, plot_export.COPY_FAILED_REASON_STR)
        return plot_export.copy_current_tab_image(window.pane_widget,
                                                  description_str)

    def show_nothing_to_copy_in(self, tab_id_i: int) -> None:
        """Show the box saying there are no plots to copy over a window.

        Inputs:
            tab_id_i: the tab of an undocked window, -1 for the main
                window.
        Outputs: none.
        """
        # LLFR-01138, LLFR-00146: an information box over that window.
        message_boxes.build_nothing_to_copy_box(
            self.window_of(tab_id_i)).exec()

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

    # ----------------------------------------------------------------
    # Layout facade, used by the layout controller (plain types only)
    # ----------------------------------------------------------------

    def set_layout_handlers(self, save_handler, load_handler) -> None:
        """Set the functions called by the Save and Load layout buttons.

        Inputs:
            save_handler: function without arguments, Save layout.
            load_handler: function without arguments, Load layout.
        Outputs: none.
        """
        # LLFR-00219, LLFR-00221: the controller runs the flows.
        self.save_layout_handler = save_handler
        self.load_layout_handler = load_handler

    def set_layout_buttons_enabled(self, enabled_b: bool) -> None:
        """Enable the two layout buttons, or disable them and show them
        paler.

        Inputs:
            enabled_b: True once a data file is open.
        Outputs: none.
        """
        # LLFR-00218: disabled, paler and doing nothing without a file.
        self.top_panel.save_layout_button.setEnabled(bool(enabled_b))
        self.top_panel.load_layout_button.setEnabled(bool(enabled_b))

    def build_layout_save_dialog(self, start_folder_str: str) -> QFileDialog:
        """Build the save file dialog of a layout file, not shown.

        Inputs:
            start_folder_str: the folder the dialog shows.
        Outputs: a QFileDialog in save mode for .json files that adds
            ".json" to a name typed without an extension and asks before
            replacing the resulting file (LLFR-00223).
        """
        # LLFR-00219, LLFR-00220: the user chooses the folder and types
        # the name; Qt asks before overwriting the file it returns.
        dialog = QFileDialog(self, SAVE_LAYOUT_DIALOG_TITLE_STR,
                             start_folder_str, LAYOUT_FILTER_STR)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setDefaultSuffix(LAYOUT_DEFAULT_SUFFIX_STR)
        return dialog

    def build_layout_load_dialog(self, start_folder_str: str) -> QFileDialog:
        """Build the file selection dialog of a layout file, not shown.

        Inputs:
            start_folder_str: the folder the dialog shows.
        Outputs: a QFileDialog in open mode that lists the .json files.
        """
        # LLFR-00221, LLFR-00220: the user chooses an existing .json file.
        dialog = QFileDialog(self, LOAD_LAYOUT_DIALOG_TITLE_STR,
                             start_folder_str, LAYOUT_FILTER_STR)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        return dialog

    def run_layout_dialog(self, dialog) -> str:
        """Run a layout file dialog modally and return the chosen path.

        Inputs:
            dialog: a QFileDialog built by build_layout_save_dialog or
                build_layout_load_dialog.
        Outputs: the chosen path, or "" when the user cancelled. Tests
            replace this method to answer without a modal dialog.
        """
        # LLFR-00222: a cancelled dialog returns "".
        return file_dialogs.run_file_dialog(dialog)

    def ask_layout_save_path(self, start_folder_str: str = "") -> str:
        """Show the save file dialog of a layout file.

        Inputs:
            start_folder_str: the folder the dialog shows.
        Outputs: the chosen path, or "" when the user cancelled.
        """
        # LLFR-00219, LLFR-00222, LLFR-00223. LLFR-00406: the dialog
        # built once, shown again in the folder of LLFR-00220 and
        # LLFR-00468, with no file name of an earlier use (LLFR-01183).
        dialog = self.file_dialog_pool.prepared_dialog(
            SAVE_LAYOUT_DIALOG_KEY_STR, start_folder_str)
        return self.run_layout_dialog(dialog) or ""

    def ask_layout_load_path(self, start_folder_str: str = "") -> str:
        """Show the file selection dialog of a layout file.

        Inputs:
            start_folder_str: the folder the dialog shows.
        Outputs: the chosen path, or "" when the user cancelled.
        """
        # LLFR-00221, LLFR-00222. LLFR-00406: the dialog built once,
        # shown again in the folder of LLFR-00220 and LLFR-00468, with
        # no file selected at an earlier use (LLFR-01183).
        dialog = self.file_dialog_pool.prepared_dialog(
            LOAD_LAYOUT_DIALOG_KEY_STR, start_folder_str)
        return self.run_layout_dialog(dialog) or ""

    def save_layout_bytes(self, path_str: str,
                          content_bytes: bytes) -> tuple:
        """Write a layout file without risking a file already there.

        Inputs:
            path_str: the path of the layout file.
            content_bytes: its UTF-8 content.
        Outputs: a tuple (saved_b, reason_str).
        """
        # LLFR-00224: written to a temporary file that then replaces the
        # target, so a failed save never damages an existing file.
        return file_writing.write_file_safely(path_str, content_bytes)

    def panel_width_tuple(self) -> tuple:
        """Return the widths of the plot and signal list panels.

        Inputs: none.
        Outputs: (plot panel width, signal list panel width) in pixels.
        """
        # LLFR-00225 item 9: the widths the user dragged to (LLFR-00073).
        size_list = list(self.lower_splitter.sizes())
        if len(size_list) < 2:
            return ()
        return (int(size_list[0]), int(size_list[1]))

    def set_panel_widths(self, plot_width_i: int, list_width_i: int) -> None:
        """Give the plot and signal list panels new widths.

        Inputs:
            plot_width_i: width of the plot panel, in pixels.
            list_width_i: width of the signal list panel, in pixels.
        Outputs: none. The two widths are scaled to the room there is,
            as Qt would scale them, and the signal list panel then leaves
            the plot panel at least 100 pixels of that room, so it is at
            most the window's width minus 100 pixels (LLFR-01195).
        """
        # LLFR-00230: the panel widths of a loaded layout; the start
        # widths of LLFR-00072 must not be applied over them later.
        self.lower_splitter.initial_sizes_set_b = True
        plot_width_i = max(int(plot_width_i), 1)
        list_width_i = max(int(list_width_i), 1)
        room_i = sum(self.lower_splitter.sizes())
        if room_i > 1:
            # LLFR-00230: the saved share of the room the panels have.
            list_width_i = max(int(round(
                room_i * list_width_i / (plot_width_i + list_width_i))), 1)
            # LLFR-01195: the plot panel keeps 100 pixels of the room the
            # panels have, which is narrower than the window, so the
            # window's limit holds too; LLFR-01054: the signal list
            # panel keeps at least 1 pixel.
            list_width_i = min(fitted_panel_width_i(list_width_i, room_i),
                               room_i - 1)
            plot_width_i = room_i - list_width_i
        else:
            # LLFR-01195: the room is not known yet; the window is.
            list_width_i = fitted_panel_width_i(list_width_i, self.width())
        self.lower_splitter.setSizes([plot_width_i, list_width_i])

    def show_layout_save_error(self, reason_str: str) -> None:
        """Show the error box saying that the layout file was not saved.

        Inputs:
            reason_str: why the file could not be written.
        Outputs: none.
        """
        # LLFR-00224: an error box (HLFR-00002).
        message_boxes.build_layout_save_error_box(self, reason_str).exec()

    def show_layout_load_error(self, message_str: str) -> None:
        """Show the error box saying that the file is not a layout file.

        Inputs:
            message_str: the text of the box.
        Outputs: none.
        """
        # LLFR-00236: an error box (HLFR-00002).
        message_boxes.build_layout_load_error_box(self, message_str).exec()

    def show_layout_report(self, report_text_str: str) -> None:
        """Show the information box of the layout load report.

        Inputs:
            report_text_str: what was not rebuilt or was changed.
        Outputs: none.
        """
        # LLFR-00237: one information box, scrollable when long.
        dialog = message_boxes.build_layout_report_box(self,
                                                       report_text_str)
        try:
            dialog.exec()
        finally:
            dialog.deleteLater()

    def finish_save_layout_button(self) -> None:
        """Return the Save layout button to its normal color.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00003: the save has finished.
        self.top_panel.save_layout_button.finish()

    def finish_load_layout_button(self) -> None:
        """Return the Load layout button to its normal color.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00003: the load has finished.
        self.top_panel.load_layout_button.finish()

    def _on_save_layout_requested(self) -> None:
        """Run the save layout handler after the button is clicked.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00219: the controller shows the save dialog.
        if self.save_layout_handler is None:
            # LLFR-00003: nothing to run, so the function is finished.
            self.finish_save_layout_button()
            return
        self.save_layout_handler()

    def _on_load_layout_requested(self) -> None:
        """Run the load layout handler after the button is clicked.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00221: the controller shows the file selection dialog.
        if self.load_layout_handler is None:
            # LLFR-00003: nothing to run, so the function is finished.
            self.finish_load_layout_button()
            return
        self.load_layout_handler()

    # ----------------------------------------------------------------
    # Save signals facade, used by the save signals controller
    # ----------------------------------------------------------------

    def set_save_signals_handler(self, handler) -> None:
        """Set the function called by the Save signals button.

        Inputs:
            handler: function without arguments.
        Outputs: none.
        """
        # LLFR-00396: the controller runs the flow.
        self.save_signals_handler = handler

    def set_save_signals_button_enabled(self, enabled_b: bool) -> None:
        """Enable the Save signals button, or disable it and show it
        paler.

        Inputs:
            enabled_b: True once a data file is open.
        Outputs: none.
        """
        # LLFR-00395: disabled, paler and doing nothing without a file.
        self.top_panel.save_signals_button.setEnabled(bool(enabled_b))

    def build_signals_save_dialog(self, start_folder_str: str,
                                  file_name_str: str,
                                  format_str: str) -> QFileDialog:
        """Build the save file dialog of the Save signals button, not
        shown.

        Inputs:
            start_folder_str: the folder the dialog shows.
            file_name_str: the name proposed in the dialog.
            format_str: the format chosen when the dialog opens.
        Outputs: a QFileDialog in save mode with one filter per format
            (SIGNALS_FILTER_DICT). The dialog does not ask before
            replacing a file, where Qt allows it, so that the app asks
            once (LLFR-00397).
        """
        # LLFR-00396: the folder, the name and the format of the data
        # file; the user may choose any of the four formats.
        dialog = QFileDialog(self, SAVE_SIGNALS_DIALOG_TITLE_STR,
                             start_folder_str,
                             ";;".join(SIGNALS_FILTER_DICT.values()))
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        # LLFR-00397: the app asks about an existing file itself, and
        # never about the opened data file.
        dialog.setOption(QFileDialog.Option.DontConfirmOverwrite, True)
        self.propose_signals_file(dialog, file_name_str, format_str)
        return dialog

    def propose_signals_file(self, dialog, file_name_str: str,
                             format_str: str) -> None:
        """Choose the proposed format and name in the Save signals dialog.

        Inputs:
            dialog: a QFileDialog built by build_signals_save_dialog.
            file_name_str: the name proposed in the dialog; "" for none.
            format_str: the format chosen when the dialog opens.
        Outputs: none.
        """
        # LLFR-00396: the format and the name of the opened data file,
        # set again on every use of the reused dialog (LLFR-00406).
        dialog.selectNameFilter(SIGNALS_FILTER_DICT.get(
            format_str, SIGNALS_FILTER_DICT[file_writer.CSV_FORMAT_STR]))
        if file_name_str:
            dialog.selectFile(file_name_str)

    def run_signals_save_dialog(self, dialog) -> tuple:
        """Run the Save signals dialog modally.

        Inputs:
            dialog: a QFileDialog built by build_signals_save_dialog.
        Outputs: a tuple (path_str, filter_str): the chosen path and the
            chosen filter, or ("", "") when the user cancelled. Tests
            replace this method to answer without a modal dialog.
        """
        # LLFR-00398: a cancelled dialog returns "".
        if dialog.exec() != QDialog.DialogCode.Accepted.value:
            return ("", "")
        selected_file_list = dialog.selectedFiles()
        if not selected_file_list:
            return ("", "")
        return (str(selected_file_list[0]), str(dialog.selectedNameFilter()))

    def signals_dialog_confirms_overwrite(self, dialog) -> bool:
        """Tell whether the system's dialog asks before replacing a file.

        Inputs:
            dialog: a QFileDialog built by build_signals_save_dialog.
        Outputs: True for the native dialog of macOS, which always asks
            (Qt can't turn its question off), even for the opened data
            file, which the app then refuses without asking again
            (LLFR-00397 Note); False otherwise.
        """
        # LLFR-00397: the app must not ask a second time.
        return (sys.platform == "darwin" and not dialog.testOption(
            QFileDialog.Option.DontUseNativeDialog))

    def ask_signals_save_path(self, start_folder_str: str,
                              file_name_str: str, format_str: str) -> tuple:
        """Show the save file dialog of the Save signals button.

        Inputs:
            start_folder_str: the folder the dialog shows.
            file_name_str: the name proposed in the dialog.
            format_str: the format chosen when the dialog opens.
        Outputs: a tuple (path_str, format_str, confirmed_b): the chosen
            path ("" when cancelled), the chosen format, and True when
            the dialog itself asked before replacing an existing file.
        """
        # LLFR-00396, LLFR-00397, LLFR-00398. LLFR-00406: the dialog
        # built once, shown again in the folder of LLFR-01181 and
        # LLFR-01182; the name of LLFR-00532 is proposed after the reset
        # that clears the name of an earlier use (LLFR-01183).
        dialog = self.file_dialog_pool.prepared_dialog(
            SAVE_SIGNALS_DIALOG_KEY_STR, start_folder_str)
        self.propose_signals_file(dialog, file_name_str, format_str)
        path_str, filter_str = self.run_signals_save_dialog(dialog)
        confirmed_b = self.signals_dialog_confirms_overwrite(dialog)
        chosen_format_str = format_str
        for candidate_str, candidate_filter_str in (
                SIGNALS_FILTER_DICT.items()):
            if candidate_filter_str == filter_str:
                chosen_format_str = candidate_str
        return (path_str or "", chosen_format_str, confirmed_b)

    def save_signal_bytes(self, path_str: str,
                          content_bytes: bytes) -> tuple:
        """Write the saved signals without risking a file already there.

        Inputs:
            path_str: the path of the new data file.
            content_bytes: its content.
        Outputs: a tuple (saved_b, reason_str).
        """
        # LLFR-00399: written to a temporary file that then replaces the
        # target, so a failed save never damages an existing file.
        return file_writing.write_file_safely(path_str, content_bytes)

    def show_signals_save_error(self, message_str: str) -> None:
        """Show the error box of the Save signals button.

        Inputs:
            message_str: the text of the box.
        Outputs: none.
        """
        # LLFR-00397, LLFR-00399, LLFR-00400: an error box (HLFR-00002).
        message_boxes.build_signals_save_error_box(self, message_str).exec()

    def show_changed_signal_names(self, text_str: str) -> None:
        """Show the information box that lists the changed names.

        Inputs:
            text_str: one "<old name> → <new name>" per line.
        Outputs: none.
        """
        # LLFR-00404: one information box, scrollable when long.
        dialog = message_boxes.build_changed_names_box(self, text_str)
        try:
            dialog.exec()
        finally:
            dialog.deleteLater()

    def finish_save_signals_button(self) -> None:
        """Return the Save signals button to its normal color.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00003: the save has finished.
        self.top_panel.save_signals_button.finish()

    def _on_save_signals_requested(self) -> None:
        """Run the save signals handler after the button is clicked.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00396: the controller shows the save dialog.
        if self.save_signals_handler is None:
            # LLFR-00003: nothing to run, so the function is finished.
            self.finish_save_signals_button()
            return
        self.save_signals_handler()

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

    def open_web_page(self, url_str: str) -> bool:
        """Ask the system's default web browser to open a page.

        Inputs:
            url_str: the address of the page.
        Outputs: True when the request was made, False when the browser
            could not be opened.
        """
        # LLFR-00359: the default browser of the system, through Qt.
        return bool(QDesktopServices.openUrl(QUrl(url_str)))

    def show_report_bug_error(self, url_str: str) -> None:
        """Show the error box saying that the page could not be opened.

        Inputs:
            url_str: the address of the page.
        Outputs: none.
        """
        # LLFR-00361: an error box with the page's address (HLFR-00002).
        message_boxes.build_report_bug_error_box(self, url_str).exec()

    def _on_report_bug_requested(self) -> None:
        """Open the page of a new issue after Report a bug is clicked.

        Inputs: none.
        Outputs: none. Shows the Report a Bug Error box when the browser
            could not be opened.
        """
        # LLFR-00359: the "New issue" page of the repository; nothing
        # else changes.
        opened_b = self.open_web_page(top_panel.REPORT_BUG_URL_STR)
        # LLFR-00360, LLFR-00003: the request is made, so the button
        # turns normal once it has been active for at least 0.3 s.
        self.top_panel.report_bug_button.finish()
        if not opened_b:
            # LLFR-00361: say so, with the address.
            self.show_report_bug_error(top_panel.REPORT_BUG_URL_STR)

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
        # LLFR-00079, LLFR-00149, LLFR-00155: a tool chosen with the
        # mouse while a tool key is held is kept; the later release
        # changes nothing.
        if not self.tip_key_changing_tool_b:
            self.tool_key_filter.cancel_activation()
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

    def _on_undo_triggered(self) -> None:
        """Run the undo after a click, then let the Undo button finish.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00138: undo the most recent action. LLFR-00001,
        # LLFR-00003: the button shows its active color briefly and is
        # never left active, even when the undo failed.
        try:
            self.run_undo()
        finally:
            self.top_panel.undo_button.finish()

    def _on_undo_shortcut(self) -> None:
        """Run the undo when Ctrl+Z (Cmd+Z on macOS) is pressed.

        Inputs: none.
        Outputs: none. Ignored while a text field has the focus, so that
            Ctrl+Z there undoes the typing instead.
        """
        # LLFR-00137: the shortcut runs the Undo button's action, except
        # in a text field (search box, dialog line edit), whose own
        # Ctrl+Z undoes the typed text (LLFR-00196).
        if self.text_field_has_focus():
            return
        # LLFR-00141: the shortcut does nothing while Undo is disabled.
        # LLFR-01058: the same in every window (LLFR-01071), on the one
        # history of LLFR-01057.
        self.run_undo()

    def _on_copy_shortcut(self, window_id_i: int) -> None:
        """Copy the tab of the window where Ctrl+C (Cmd+C) was pressed.

        Inputs:
            window_id_i: id of the undocked window, -1 for the main
                window.
        Outputs: none. In a text field, its selected text is copied
            instead.
        """
        # LLFR-01137: a text field keeps its own Ctrl+C; it usually takes
        # the key before the shortcut, and is asked to copy here when
        # the shortcut runs all the same.
        if self.text_field_has_focus():
            focus_widget = QApplication.focusWidget()
            if hasattr(focus_widget, "copy"):
                focus_widget.copy()
            return
        # LLFR-01173: during a mouse drag, no image and no box.
        if self.is_mouse_drag_in_progress():
            return
        # LLFR-01136: the image of the tab shown in that window.
        if self.copy_shortcut_handler is not None:
            self.copy_shortcut_handler(self.window_shown_tab_id(window_id_i))

    def _on_pdf_shortcut(self) -> None:
        """Run "Save all tabs as PDF" when Ctrl+P (Cmd+P) is pressed.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01172: during a mouse drag, Ctrl+P does nothing.
        if self.is_mouse_drag_in_progress():
            return
        # LLFR-01186, LLFR-01190, LLFR-01187: a text field is left
        # first, its selection cleared and its typed text accepted.
        self.leave_text_field()
        # LLFR-01139: as the Export menu option, from any window, also
        # in a text field (which gives Ctrl+P no meaning of its own).
        self._on_pdf_export_requested()

    def _on_search_shortcut(self, window_id_i: int) -> None:
        """Put the focus in the search box of a window (Ctrl+F, Cmd+F).

        Inputs:
            window_id_i: id of the undocked window, -1 for the main
                window.
        Outputs: none. Nothing happens during a mouse drag.
        """
        # LLFR-01174: during a mouse drag, Ctrl+F does nothing.
        if self.is_mouse_drag_in_progress():
            return
        # LLFR-01188: in the window's own search box, the focus stays
        # there; LLFR-01186, LLFR-01190, LLFR-01187: another field is left
        # first, its selection cleared and its typed text accepted.
        if QApplication.focusWidget() is not self.search_box_of_window(
                window_id_i):
            self.leave_text_field()
        if window_id_i >= 0:
            window = self.undocked_window_dict.get(window_id_i)
            if window is None:
                return
            if not window.is_panel_shown():
                # LLFR-01141: the hidden panel is shown first, as the
                # signal list button does, as one undoable action.
                self._run_window_handler("panel_show_handler", window_id_i)
            window = self.undocked_window_dict.get(window_id_i)
            if window is None or not window.is_panel_shown():
                return
            panel = window.signal_list_panel
            window.activateWindow()
        else:
            panel = self.signal_list_panel
        # LLFR-01140: the focus in the search box, its text selected.
        panel.search_box.setFocus(Qt.FocusReason.ShortcutFocusReason)
        panel.search_box.selectAll()

    def search_box_of_window(self, window_id_i: int):
        """Return the search box of a window's signal list panel.

        Inputs:
            window_id_i: id of the undocked window, -1 for the main
                window.
        Outputs: the QLineEdit, or None for an unknown window.
        """
        # LLFR-01140, LLFR-01188: the search box that Ctrl+F goes to.
        if window_id_i < 0:
            return self.signal_list_panel.search_box
        window = self.undocked_window_dict.get(window_id_i)
        if window is None:
            return None
        return window.signal_list_panel.search_box

    @staticmethod
    def leave_text_field() -> None:
        """Take the keyboard focus out of the text field that has it.

        Inputs: none.
        Outputs: none. The field's selection is cleared and the text
            typed so far is accepted, as Enter does: a text note field
            writes its note. Nothing happens when no text field has the
            focus.
        """
        focus_widget = QApplication.focusWidget()
        if not isinstance(focus_widget, TEXT_INPUT_WIDGET_TUPLE):
            return
        # LLFR-01190: the selection is cleared first.
        if isinstance(focus_widget, QLineEdit):
            focus_widget.deselect()
        elif isinstance(focus_widget, (QTextEdit, QPlainTextEdit)):
            text_cursor = focus_widget.textCursor()
            text_cursor.clearSelection()
            focus_widget.setTextCursor(text_cursor)
        # LLFR-01187: the typed text is accepted, as Enter does
        # (LLFR-00334). The search box has nothing to accept: its text
        # is applied while it is typed (LLFR-00095).
        confirm_signal = getattr(focus_widget, "confirm_requested", None)
        if confirm_signal is not None:
            confirm_signal.emit()
        # LLFR-01186: the focus leaves the field, unless accepting it
        # already closed it.
        if not sip.isdeleted(focus_widget) and focus_widget.hasFocus():
            focus_widget.clearFocus()

    def run_name_dialog_shortcut(self, action_str: str, parent) -> None:
        """Run Ctrl+P or Ctrl+F pressed in a name dialog, after it closed.

        Inputs:
            action_str: name_dialog.PDF_ACTION_STR or SEARCH_ACTION_STR.
            parent: the window the dialog was shown over.
        Outputs: none.
        """
        # LLFR-01185: the action of the shortcut, for the window the
        # dialog was shown over (the main window when it is unknown).
        window_id_i = -1
        for undocked_id_i, window in self.undocked_window_dict.items():
            if window is parent:
                window_id_i = undocked_id_i
        if action_str == name_dialog.PDF_ACTION_STR:
            self._on_pdf_shortcut()
        elif action_str == name_dialog.SEARCH_ACTION_STR:
            self._on_search_shortcut(window_id_i)

    def _on_redo_triggered(self) -> None:
        """Run the redo after a click, then let the Redo button finish.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00192: redo the most recently undone action. LLFR-00001,
        # LLFR-00003: the button shows its active color briefly and is
        # never left active, even when the redo failed.
        try:
            self.run_redo()
        finally:
            self.top_panel.redo_button.finish()

    def _on_redo_shortcut(self) -> None:
        """Run the redo when Ctrl+Y (Cmd+Y on macOS) is pressed.

        Inputs: none.
        Outputs: none. Ignored while a text field has the focus, so that
            Ctrl+Y there acts on the typing instead.
        """
        # LLFR-00191, LLFR-00195: the shortcut runs the Redo button's
        # action, except in a text field.
        if self.text_field_has_focus():
            return
        # LLFR-00194: the shortcut does nothing while Redo is disabled.
        # LLFR-01058: the same in every window (LLFR-01071), on the one
        # history of LLFR-01057.
        self.run_redo()

    @staticmethod
    def text_field_has_focus() -> bool:
        """Tell whether the keyboard focus is in a text field.

        Inputs: none.
        Outputs: True when the focused widget is one of
            TEXT_INPUT_WIDGET_TUPLE (search box, name editors).
        """
        # LLFR-00157, LLFR-00195, LLFR-00196: the text fields keep their
        # own undo and redo of the typed text.
        return isinstance(QApplication.focusWidget(),
                          TEXT_INPUT_WIDGET_TUPLE)

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

    def _on_search_text_changed(self, text_str: str,
                                source_panel=None) -> None:
        """Share a new search text and pass it to its handler.

        Inputs:
            text_str: the text now in the search box.
            source_panel: the SignalListPanel the text was typed in;
                None for the main window's.
        Outputs: none.
        """
        # LLFR-01041: the same text in every other search box;
        # LLFR-01042: the focus and the cursor stay where the user types;
        # LLFR-01052: hidden panels get it too.
        for panel in self.signal_list_panel_list():
            if panel is source_panel or panel.search_text() == text_str:
                continue
            panel.search_box.blockSignals(True)
            panel.search_box.setText(text_str)
            panel.search_box.blockSignals(False)
        # LLFR-00095: every change re-filters the signal list.
        if self.search_text_handler is not None:
            self.search_text_handler(text_str)

    def _on_selected_signals_plot_requested(self, signal_name_list: list,
                                            tab_id_i: int = -1) -> None:
        """Pass the selected signal names to their handler.

        Inputs:
            signal_name_list: the selected names, in list order.
            tab_id_i: the tab of the undocked window of the panel, or -1
                for the main window.
        Outputs: none.
        """
        # LLFR-00295: the handler creates one plot with every signal;
        # LLFR-01038: in the tab of the panel's window.
        if self.selected_signals_plot_handler is None:
            return
        if tab_id_i < 0:
            self.selected_signals_plot_handler(list(signal_name_list))
        else:
            self.selected_signals_plot_handler(list(signal_name_list),
                                               tab_id_i)

    def _on_signal_double_clicked(self, signal_name_str: str,
                                  tab_id_i: int = -1) -> None:
        """Pass a double-clicked signal name to its handler.

        Inputs:
            signal_name_str: the name that was double-clicked.
            tab_id_i: the tab of the undocked window of the panel, or -1
                for the main window.
        Outputs: none.
        """
        # LLFR-00019: the handler creates a plot with the signal;
        # LLFR-01038: in the tab of the panel's window.
        if self.signal_double_click_handler is None:
            return
        if tab_id_i < 0:
            self.signal_double_click_handler(signal_name_str)
        else:
            self.signal_double_click_handler(signal_name_str, tab_id_i)
