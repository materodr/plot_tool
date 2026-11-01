"""Top panel: holds the controls for opening a file and the plot tools."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR)
from view.action_button import ActionButton
from view.toggle_button import ToggleButton

OPEN_FILE_TEXT_STR = "Open file"
TIP_TEXT_STR = "Tip"
ZOOM_TEXT_STR = "Zoom"
MARKER_TEXT_STR = "Vertical marker"
RESET_ZOOM_TEXT_STR = "Reset zoom"
GRID_TEXT_STR = "Grid"


class TopPanel(QWidget):
    """Panel placed above the plot and signal list panels (HLFR-00001).

    Inputs: none.
    Signals:
        plot_tool_changed(str): the active plot tool changed; the value
            is a name of controller.plot_tools, NO_TOOL_STR when no plot
            tool is active any more (LLFR-00079, LLFR-00002).
    Attributes:
        button_layout: horizontal layout that holds the panel's buttons.
        open_file_button: the "Open file" ToggleButton (LLFR-00004).
        tip_button: the "Tip" ToggleButton (LLFR-00018).
        zoom_button: the "Zoom" ToggleButton (LLFR-00077).
        marker_button: the "Vertical marker" ToggleButton (LLFR-00080).
        plot_tool_button_dict: plot tool name -> its ToggleButton.
        reset_zoom_button: the "Reset zoom" ActionButton (LLFR-00114);
            not a plot tool.
        grid_button: the "Grid" ToggleButton (LLFR-00121); not a plot
            tool, it shows whether the grid is shown (LLFR-00124).
    """

    plot_tool_changed = pyqtSignal(str)

    def __init__(self) -> None:
        """Create the panel with its buttons, aligned to the left.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        # LLFR-00058: the top panel exists and is placed by MainWindow.
        self.setObjectName("top_panel")
        self.button_layout = QHBoxLayout(self)
        # LLFR-00004: the "Open file" button; LLFR-00001: it shows when
        # it is active.
        self.open_file_button = ToggleButton(OPEN_FILE_TEXT_STR)
        self.open_file_button.setObjectName("open_file_button")
        # LLFR-00018, LLFR-00077, LLFR-00080: the plot tool buttons,
        # placed after "Open file".
        self.tip_button = ToggleButton(TIP_TEXT_STR)
        self.tip_button.setObjectName("tip_button")
        self.zoom_button = ToggleButton(ZOOM_TEXT_STR)
        self.zoom_button.setObjectName("zoom_button")
        self.marker_button = ToggleButton(MARKER_TEXT_STR)
        self.marker_button.setObjectName("marker_button")
        self.plot_tool_button_dict = {
            TIP_TOOL_STR: self.tip_button,
            ZOOM_TOOL_STR: self.zoom_button,
            MARKER_TOOL_STR: self.marker_button}
        self.button_layout.addWidget(self.open_file_button)
        for tool_str, button in self.plot_tool_button_dict.items():
            self.button_layout.addWidget(button)
            # LLFR-00079: activating a tool button deactivates the others.
            button.activated.connect(
                lambda tool_str=tool_str: self.activate_plot_tool(tool_str))
            # LLFR-00002: a second click leaves no tool active.
            button.deactivated.connect(self.deactivate_plot_tools)
        # LLFR-00114, LLFR-00121: Reset zoom and Grid come after the plot
        # tools. They are not in plot_tool_button_dict, so the plot tools
        # never deactivate them and they never deactivate a plot tool.
        self.reset_zoom_button = ActionButton(RESET_ZOOM_TEXT_STR)
        self.reset_zoom_button.setObjectName("reset_zoom_button")
        self.grid_button = ToggleButton(GRID_TEXT_STR)
        self.grid_button.setObjectName("grid_button")
        self.button_layout.addWidget(self.reset_zoom_button)
        self.button_layout.addWidget(self.grid_button)
        # LLFR-00004, LLFR-00018: the stretch keeps the buttons on the
        # left.
        self.button_layout.addStretch(1)

    def activate_plot_tool(self, tool_str: str) -> None:
        """Make one plot tool the only active one and report it.

        Inputs:
            tool_str: the name of the tool whose button became active.
        Outputs: none. Emits plot_tool_changed(tool_str).
        """
        # LLFR-00079: the other tool buttons go back to normal quietly
        # (finish emits no deactivated), so only the new tool is
        # reported.
        for other_tool_str, button in self.plot_tool_button_dict.items():
            if other_tool_str != tool_str:
                button.finish()
        self.plot_tool_changed.emit(tool_str)

    def deactivate_plot_tools(self) -> None:
        """Report that no plot tool is active any more.

        Inputs: none.
        Outputs: none. Emits plot_tool_changed(NO_TOOL_STR).
        """
        # LLFR-00002, LLFR-00109: the active tool button was clicked
        # again, which is the only way a tool ends by itself.
        self.plot_tool_changed.emit(NO_TOOL_STR)

    def show_plot_tool(self, tool_str: str) -> None:
        """Show one tool button as active and the others as normal.

        Inputs:
            tool_str: the active tool name, or NO_TOOL_STR for none.
        Outputs: none. No signal is emitted.
        """
        # LLFR-00079: the buttons always match the tool in use;
        # setChecked does not emit clicked, so nothing is reported back.
        for other_tool_str, button in self.plot_tool_button_dict.items():
            if other_tool_str == tool_str:
                button.setChecked(True)
            else:
                button.finish()

    def active_plot_tool(self) -> str:
        """Return the tool whose button is active.

        Inputs: none.
        Outputs: the tool name, or NO_TOOL_STR when no tool button is
            active.
        """
        # LLFR-00079: at most one tool button is active.
        for tool_str, button in self.plot_tool_button_dict.items():
            if button.is_active():
                return tool_str
        return NO_TOOL_STR
