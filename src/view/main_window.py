"""Main window of plot_tool, holding the three panels (HLFR-00001)."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog, QMainWindow, QSplitter, QVBoxLayout, QWidget)

from view import message_boxes
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
    PLOT_PANEL_STRETCH_I = 4
    SIGNAL_LIST_STRETCH_I = 1

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
        # panel, and the user can drag the divider between them.
        self.lower_splitter = QSplitter(Qt.Orientation.Horizontal)
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
