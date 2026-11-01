"""Top panel: holds the controls for opening a file and the plot tools."""

from PyQt6 import sip
from PyQt6.QtCore import QPoint, QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QMenu, QWidget

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR)
from view.toggle_button import ToggleButton

OPEN_FILE_TEXT_STR = "Open file"
TIP_TEXT_STR = "Tip"
ZOOM_TEXT_STR = "Zoom"
MARKER_TEXT_STR = "Vertical marker"
# LLFR-00126, LLFR-00127, LLFR-00132: the export buttons and the menu.
EXPORT_TEXT_STR = "Export"
SAVE_PDF_TEXT_STR = "Save all tabs as PDF"
COPY_TEXT_STR = "Copy"


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
        export_button: the "Export" ToggleButton (LLFR-00126).
        copy_button: the "Copy" ToggleButton (LLFR-00132).
    """

    plot_tool_changed = pyqtSignal(str)
    pdf_export_requested = pyqtSignal()
    copy_requested = pyqtSignal()

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
        # LLFR-00126, LLFR-00132: the Export and Copy buttons; they are
        # active while their function runs (LLFR-00001, LLFR-00003).
        self.export_button = ToggleButton(EXPORT_TEXT_STR)
        self.export_button.setObjectName("export_button")
        self.copy_button = ToggleButton(COPY_TEXT_STR)
        self.copy_button.setObjectName("copy_button")
        self.button_layout.addWidget(self.export_button)
        self.button_layout.addWidget(self.copy_button)
        # LLFR-00127, LLFR-00133: the menu and the copy run once control
        # is back in Qt, so the active color is painted first.
        self.export_button.activated.connect(
            lambda: QTimer.singleShot(0, self.show_pending_export_menu))
        self.copy_button.activated.connect(
            lambda: QTimer.singleShot(0, self.emit_pending_copy))
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

    def build_export_menu(self) -> QMenu:
        """Build the menu shown by the Export button.

        Inputs: none.
        Outputs: a QMenu (not shown) with the "Save all tabs as PDF"
            action.
        """
        # LLFR-00127: the Export menu has the PDF option.
        menu = QMenu(self)
        menu.addAction(SAVE_PDF_TEXT_STR)
        return menu

    def execute_export_menu(self, menu):
        """Run the Export menu modally below the Export button.

        Inputs:
            menu: the QMenu built by build_export_menu.
        Outputs: the chosen QAction, or None when the menu was closed
            without a choice. Tests replace this method to choose an
            action without a real modal menu.
        """
        # LLFR-00127: the menu opens below the button.
        below_button_point = self.export_button.mapToGlobal(
            QPoint(0, self.export_button.height()))
        return menu.exec(below_button_point)

    def show_export_menu(self) -> None:
        """Show the Export menu and report the chosen option.

        Inputs: none.
        Outputs: none. Emits pdf_export_requested when "Save all tabs as
            PDF" was chosen; otherwise the Export button returns to its
            normal color.
        """
        # LLFR-00127: show the menu and read the choice.
        menu = self.build_export_menu()
        chosen_action = self.execute_export_menu(menu)
        chosen_text_str = (chosen_action.text() if chosen_action is not None
                           else "")
        sip.delete(menu)
        if chosen_text_str == SAVE_PDF_TEXT_STR:
            # LLFR-00128: the controller asks for the file and saves it,
            # then returns the button to normal.
            self.pdf_export_requested.emit()
            return
        # LLFR-00003: the menu was closed without a choice, so the
        # function of the button has finished.
        self.export_button.finish()

    def show_pending_export_menu(self) -> None:
        """Show the Export menu asked for by a click on the button.

        Inputs: none.
        Outputs: none. Does nothing if the panel was deleted meanwhile.
        """
        # LLFR-00127: deferred, so the click handling has finished.
        if sip.isdeleted(self):
            return
        self.show_export_menu()

    def emit_pending_copy(self) -> None:
        """Report the click on the Copy button.

        Inputs: none.
        Outputs: none. Emits copy_requested unless the panel was deleted
            meanwhile.
        """
        # LLFR-00133: the copy runs after the active color is shown.
        if sip.isdeleted(self):
            return
        self.copy_requested.emit()
