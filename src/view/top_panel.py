"""Top panel: holds the controls for opening a file and the plot tools.

Every button shows only its icon (LLFR-00158, LLFR-00159); its name,
for example "Open file", is its hover tip (LLFR-00181) and accessible
name, so a button "called" X in the requirements is the button whose
name is X.
"""

from PyQt6 import sip
from PyQt6.QtCore import QPoint, QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QMenu, QWidget

from controller.plot_tools import (
    DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR,
    TIP_TOOL_STR, ZOOM_TOOL_STR)
from view import icon_shapes, theme
from view.action_button import ActionButton
from view.toggle_button import ToggleButton
from view.undo_button import UndoButton

OPEN_FILE_TEXT_STR = "Open file"
TIP_TEXT_STR = "Tip"
ZOOM_TEXT_STR = "Zoom"
MARKER_TEXT_STR = "Vertical marker"
# LLFR-00161, LLFR-00162: the delta marker tool buttons.
DELTA_X_TEXT_STR = "Delta X"
DELTA_Y_TEXT_STR = "Delta Y"
RESET_ZOOM_TEXT_STR = "Reset zoom"
GRID_TEXT_STR = "Grid"
# LLFR-00126, LLFR-00127, LLFR-00132: the export buttons and the menu.
EXPORT_TEXT_STR = "Export"
SAVE_PDF_TEXT_STR = "Save all tabs as PDF"
COPY_TEXT_STR = "Copy"
UNDO_TEXT_STR = "Undo"
# LLFR-00190: the Redo button, right of the Undo button.
REDO_TEXT_STR = "Redo"
# LLFR-00159: the icon of each button, by button name.
BUTTON_ICON_DICT = {
    OPEN_FILE_TEXT_STR: icon_shapes.OPEN_FILE_ICON_STR,
    TIP_TEXT_STR: icon_shapes.TIP_ICON_STR,
    ZOOM_TEXT_STR: icon_shapes.ZOOM_ICON_STR,
    MARKER_TEXT_STR: icon_shapes.MARKER_ICON_STR,
    DELTA_X_TEXT_STR: icon_shapes.DELTA_X_ICON_STR,
    DELTA_Y_TEXT_STR: icon_shapes.DELTA_Y_ICON_STR,
    RESET_ZOOM_TEXT_STR: icon_shapes.RESET_ZOOM_ICON_STR,
    GRID_TEXT_STR: icon_shapes.GRID_ICON_STR,
    EXPORT_TEXT_STR: icon_shapes.EXPORT_ICON_STR,
    COPY_TEXT_STR: icon_shapes.COPY_ICON_STR,
    UNDO_TEXT_STR: icon_shapes.UNDO_ICON_STR,
    REDO_TEXT_STR: icon_shapes.REDO_ICON_STR,
}


def new_icon_button(button_class, name_str: str, object_name_str: str):
    """Create a top panel button that shows only its icon.

    Inputs:
        button_class: ToggleButton or one of its subclasses.
        name_str: the button's name, e.g. "Open file".
        object_name_str: the objectName that scopes its style sheet.
    Outputs: the new button, with the icon of BUTTON_ICON_DICT and the
        name as its hover tip and accessible name.
    """
    # LLFR-00158, LLFR-00159, LLFR-00181: icon only, name on hover.
    button = button_class(name_str, icon_name_str=BUTTON_ICON_DICT[name_str])
    button.setObjectName(object_name_str)
    return button


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
        delta_x_button: the "Delta X" ToggleButton (LLFR-00161).
        delta_y_button: the "Delta Y" ToggleButton (LLFR-00162).
        plot_tool_button_dict: plot tool name -> its ToggleButton.
        reset_zoom_button: the "Reset zoom" ActionButton (LLFR-00114);
            not a plot tool.
        grid_button: the "Grid" ToggleButton (LLFR-00121); not a plot
            tool, it shows whether the grid is shown (LLFR-00124).
        export_button: the "Export" ToggleButton (LLFR-00126).
        copy_button: the "Copy" ToggleButton (LLFR-00132).
        undo_button: the "Undo" UndoButton (LLFR-00136); not a plot
            tool, disabled while nothing can be undone (LLFR-00141).
        redo_button: the "Redo" UndoButton (LLFR-00190), directly right
            of the Undo button; disabled while nothing can be redone
            (LLFR-00194).
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
        # LLFR-00058: the window margins frame the panel; the buttons are
        # spaced by explicit gaps, small inside a group of related
        # buttons and wider between groups.
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(0)
        # LLFR-00004: the "Open file" button; LLFR-00001: it shows when
        # it is active. LLFR-00158: each button shows only its icon.
        self.open_file_button = new_icon_button(
            ToggleButton, OPEN_FILE_TEXT_STR, "open_file_button")
        # LLFR-00018, LLFR-00077, LLFR-00080: the plot tool buttons,
        # placed after "Open file".
        self.tip_button = new_icon_button(
            ToggleButton, TIP_TEXT_STR, "tip_button")
        self.zoom_button = new_icon_button(
            ToggleButton, ZOOM_TEXT_STR, "zoom_button")
        self.marker_button = new_icon_button(
            ToggleButton, MARKER_TEXT_STR, "marker_button")
        # LLFR-00161, LLFR-00162: the Delta X and Delta Y tools, after
        # Vertical marker in the same group.
        self.delta_x_button = new_icon_button(
            ToggleButton, DELTA_X_TEXT_STR, "delta_x_button")
        self.delta_y_button = new_icon_button(
            ToggleButton, DELTA_Y_TEXT_STR, "delta_y_button")
        self.plot_tool_button_dict = {
            TIP_TOOL_STR: self.tip_button,
            ZOOM_TOOL_STR: self.zoom_button,
            MARKER_TOOL_STR: self.marker_button,
            DELTA_X_TOOL_STR: self.delta_x_button,
            DELTA_Y_TOOL_STR: self.delta_y_button}
        self.button_layout.addWidget(self.open_file_button)
        self.button_layout.addSpacing(theme.TOOLBAR_GROUP_GAP_I)
        # LLFR-00079: only one plot tool is active at a time, so the
        # five tool buttons are drawn joined, as one group.
        segment_list = ([theme.SEGMENT_FIRST_STR]
                        + [theme.SEGMENT_MIDDLE_STR]
                        * (len(self.plot_tool_button_dict) - 2)
                        + [theme.SEGMENT_LAST_STR])
        for segment_str, (tool_str, button) in zip(
                segment_list, self.plot_tool_button_dict.items()):
            button.set_segment_position(segment_str)
            self.button_layout.addWidget(button)
            # LLFR-00079: activating a tool button deactivates the others.
            button.activated.connect(
                lambda tool_str=tool_str: self.activate_plot_tool(tool_str))
            # LLFR-00002: a second click leaves no tool active.
            button.deactivated.connect(self.deactivate_plot_tools)
        # LLFR-00114, LLFR-00121: Reset zoom and Grid come after the plot
        # tools. They are not in plot_tool_button_dict, so the plot tools
        # never deactivate them and they never deactivate a plot tool.
        self.reset_zoom_button = new_icon_button(
            ActionButton, RESET_ZOOM_TEXT_STR, "reset_zoom_button")
        self.grid_button = new_icon_button(
            ToggleButton, GRID_TEXT_STR, "grid_button")
        self.button_layout.addSpacing(theme.TOOLBAR_GROUP_GAP_I)
        self.button_layout.addWidget(self.reset_zoom_button)
        self.button_layout.addSpacing(theme.TOOLBAR_BUTTON_GAP_I)
        self.button_layout.addWidget(self.grid_button)
        # LLFR-00126, LLFR-00132: the Export and Copy buttons; they are
        # active while their function runs (LLFR-00001, LLFR-00003).
        self.export_button = new_icon_button(
            ToggleButton, EXPORT_TEXT_STR, "export_button")
        self.copy_button = new_icon_button(
            ToggleButton, COPY_TEXT_STR, "copy_button")
        self.button_layout.addSpacing(theme.TOOLBAR_GROUP_GAP_I)
        self.button_layout.addWidget(self.export_button)
        self.button_layout.addSpacing(theme.TOOLBAR_BUTTON_GAP_I)
        self.button_layout.addWidget(self.copy_button)
        # LLFR-00127, LLFR-00133: the menu and the copy run once control
        # is back in Qt, so the active color is painted first.
        self.export_button.activated.connect(
            lambda: QTimer.singleShot(0, self.show_pending_export_menu))
        self.copy_button.activated.connect(
            lambda: QTimer.singleShot(0, self.emit_pending_copy))
        # LLFR-00136: the Undo button; LLFR-00141: disabled until there
        # is an action to undo. Not a plot tool.
        self.undo_button = new_icon_button(
            UndoButton, UNDO_TEXT_STR, "undo_button")
        self.undo_button.setEnabled(False)
        self.button_layout.addSpacing(theme.TOOLBAR_GROUP_GAP_I)
        self.button_layout.addWidget(self.undo_button)
        # LLFR-00190: the Redo button, directly right of Undo in the same
        # group; LLFR-00194: disabled until an action is undone.
        self.redo_button = new_icon_button(
            UndoButton, REDO_TEXT_STR, "redo_button")
        self.redo_button.setEnabled(False)
        self.button_layout.addSpacing(theme.TOOLBAR_BUTTON_GAP_I)
        self.button_layout.addWidget(self.redo_button)
        # LLFR-00004, LLFR-00018: the stretch keeps the buttons on the
        # left.
        self.button_layout.addStretch(1)

    def button_list(self) -> list:
        """Return the buttons of the panel, from left to right.

        Inputs: none.
        Outputs: a list of ToggleButton objects.
        """
        # LLFR-00158, LLFR-00181: every button of the panel.
        return [self.button_layout.itemAt(index_i).widget()
                for index_i in range(self.button_layout.count())
                if self.button_layout.itemAt(index_i).widget() is not None]

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
