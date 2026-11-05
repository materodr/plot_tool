"""Top panel: holds the controls for opening a file and the plot tools.

Every button shows only its icon (LLFR-00158, LLFR-00159); its name,
for example "Open file", is the first line of its button tip
(LLFR-00181) and its accessible name, so a button "called" X in the
requirements is the button whose name is X. Below the name, the button
tip shows the button's keyboard shortcut (LLFR-00213) or how its tool
is used with the mouse (LLFR-00214), in a paler color, with the texts
of LLFR-00215, built from BUTTON_TIP_SHORTCUT_DICT.

At its right end the panel shows the credit text "Designed by
materodr" (LLFR-00364), with only "materodr" underlined (LLFR-00889),
which is not a button: it lets every mouse event through and is hidden
when it does not fit beside the buttons.
"""

import html
import sys

from PyQt6 import sip
from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMenu, QWidget

from controller.plot_tools import (
    ARROW_TOOL_STR, AREA_TOOL_STR, DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR,
    MARKER_TOOL_STR, NO_TOOL_STR, PAN_TOOL_STR, TEXT_TOOL_STR, TIP_TOOL_STR,
    ZOOM_TOOL_STR)
from view import icon_shapes, theme
from view.action_button import ActionButton
from view.tip_key_filter import (
    ARROW_KEY_I, AREA_KEY_I, DELTA_X_KEY_I, DELTA_Y_KEY_I, MARKER_KEY_I,
    RESET_ZOOM_KEY_I, TEXT_KEY_I, TIP_KEY_I, ZOOM_KEY_I)
from view.text_note_editor import KEEPS_TEXT_NOTE_OPEN_PROPERTY_STR
from view.toggle_button import ToggleButton
from view.undo_button import UndoButton

OPEN_FILE_TEXT_STR = "Open file"
# LLFR-00216, LLFR-00217: the layout buttons, right of Open file.
SAVE_LAYOUT_TEXT_STR = "Save layout"
LOAD_LAYOUT_TEXT_STR = "Load layout"
# LLFR-00018: the button of the data tip tool (HLFR-00024).
TIP_TEXT_STR = "Data tip"
ZOOM_TEXT_STR = "Zoom"
# LLFR-00355: the button of the Pan tool, right of Zoom (LLFR-00347).
PAN_TEXT_STR = "Pan"
# LLFR-00080: the name of the Flag button (the code calls a flag a
# "marker").
MARKER_TEXT_STR = "Flag"
# LLFR-00161, LLFR-00162: the delta marker tool buttons.
DELTA_X_TEXT_STR = "Delta X"
DELTA_Y_TEXT_STR = "Delta Y"
# LLFR-00286, LLFR-00320: the Area and Text tool buttons.
AREA_TEXT_STR = "Area"
TEXT_TEXT_STR = "Text"
# LLFR-00366: the Arrow tool button.
ARROW_TEXT_STR = "Arrow"
RESET_ZOOM_TEXT_STR = "Reset zoom"
GRID_TEXT_STR = "Grid"
# LLFR-00126, LLFR-00127, LLFR-00132: the export buttons and the menu.
EXPORT_TEXT_STR = "Export"
SAVE_PDF_TEXT_STR = "Save all tabs as PDF"
# LLFR-01223: the Word and PNG options, below the PDF option.
SAVE_DOCX_TEXT_STR = "Save all tabs as Word document (.docx)"
SAVE_PNG_TEXT_STR = "Save each tab as PNG"
COPY_TEXT_STR = "Copy"
# LLFR-00394: the Save signals button, right of Copy.
SAVE_SIGNALS_TEXT_STR = "Save signals"
UNDO_TEXT_STR = "Undo"
# LLFR-00190: the Redo button, right of the Undo button.
REDO_TEXT_STR = "Redo"
# LLFR-00358: the Report a bug button, alone in the last group.
REPORT_BUG_TEXT_STR = "Report a bug"
# LLFR-00359: the page of the repository's "New issue" button.
REPORT_BUG_URL_STR = "https://github.com/materodr/plot_tool/issues/new/choose"
# LLFR-00364: the credit text and the objectName of its label.
CREDIT_LEAD_TEXT_STR = "Designed by "
CREDIT_NAME_TEXT_STR = "materodr"
CREDIT_TEXT_STR = CREDIT_LEAD_TEXT_STR + CREDIT_NAME_TEXT_STR
# LLFR-00889: the same text as rich text, with only the name underlined.
CREDIT_RICH_TEXT_STR = (html.escape(CREDIT_LEAD_TEXT_STR)
                        + "<u>" + html.escape(CREDIT_NAME_TEXT_STR) + "</u>")
CREDIT_LABEL_NAME_STR = "credit_label"
# LLFR-00159: the icon of each button, by button name.
BUTTON_ICON_DICT = {
    OPEN_FILE_TEXT_STR: icon_shapes.OPEN_FILE_ICON_STR,
    SAVE_LAYOUT_TEXT_STR: icon_shapes.SAVE_LAYOUT_ICON_STR,
    LOAD_LAYOUT_TEXT_STR: icon_shapes.LOAD_LAYOUT_ICON_STR,
    TIP_TEXT_STR: icon_shapes.TIP_ICON_STR,
    ZOOM_TEXT_STR: icon_shapes.ZOOM_ICON_STR,
    PAN_TEXT_STR: icon_shapes.PAN_ICON_STR,
    MARKER_TEXT_STR: icon_shapes.MARKER_ICON_STR,
    DELTA_X_TEXT_STR: icon_shapes.DELTA_X_ICON_STR,
    DELTA_Y_TEXT_STR: icon_shapes.DELTA_Y_ICON_STR,
    AREA_TEXT_STR: icon_shapes.AREA_ICON_STR,
    TEXT_TEXT_STR: icon_shapes.TEXT_ICON_STR,
    ARROW_TEXT_STR: icon_shapes.ARROW_ICON_STR,
    RESET_ZOOM_TEXT_STR: icon_shapes.RESET_ZOOM_ICON_STR,
    GRID_TEXT_STR: icon_shapes.GRID_ICON_STR,
    EXPORT_TEXT_STR: icon_shapes.EXPORT_ICON_STR,
    COPY_TEXT_STR: icon_shapes.COPY_ICON_STR,
    SAVE_SIGNALS_TEXT_STR: icon_shapes.SAVE_SIGNALS_ICON_STR,
    UNDO_TEXT_STR: icon_shapes.UNDO_ICON_STR,
    REDO_TEXT_STR: icon_shapes.REDO_ICON_STR,
    REPORT_BUG_TEXT_STR: icon_shapes.REPORT_BUG_ICON_STR,
}

# ----------------------------------------------------------------------
# Button tips (LLFR-00213 to LLFR-00215)
# ----------------------------------------------------------------------
# LLFR-00191: the Redo shortcut; Qt maps Ctrl to the Command key on
# macOS, so the same sequence is Cmd+Y there. MainWindow builds its
# QShortcut from this constant, so the shortcut and its tip text change
# together (LLFR-00215 Note).
REDO_SHORTCUT_STR = "Ctrl+Y"
# LLFR-01136, LLFR-01139, LLFR-01140: the Copy, PDF and search
# shortcuts, Ctrl on Windows and Cmd on macOS, kept here with the button
# tip texts so that a shortcut and its tip change together (LLFR-00215).
COPY_SHORTCUT_STR = "Ctrl+C"
PDF_SHORTCUT_STR = "Ctrl+P"
SEARCH_SHORTCUT_STR = "Ctrl+F"
# LLFR-00137: the Undo shortcut is Qt's standard Undo key (Ctrl+Z, or
# Cmd+Z on macOS); MainWindow builds its QShortcut from it.
UNDO_STANDARD_KEY = QKeySequence.StandardKey.Undo
# LLFR-00215: how the shortcut of each kind is written below the name.
SHORTCUT_SEQUENCE_STR = "sequence"
SHORTCUT_HOLD_STR = "hold"
SHORTCUT_PRESS_STR = "press"
MOUSE_USE_STR = "mouse"
# LLFR-00463: a held key followed by the lines of its mouse use.
SHORTCUT_HOLD_AND_MOUSE_STR = "hold and mouse"
# LLFR-00215: the word "Hold" before a held key (LLFR-00148, LLFR-00154,
# LLFR-00197, LLFR-00200, LLFR-00287, LLFR-00321, LLFR-00367).
HOLD_PREFIX_STR = "Hold "
# LLFR-00148: Qt reports the Command key of macOS as Key_Control, so the
# Data tip key is written "Cmd" on macOS and "Ctrl" elsewhere.
MACOS_COMMAND_NAME_STR = "Cmd"
CONTROL_NAME_STR = "Ctrl"
# LLFR-00154: the name of the Shift key on every operating system.
SHIFT_NAME_STR = "Shift"
# LLFR-00078, LLFR-00208, LLFR-00074, LLFR-00206: how the Zoom tool is
# used with the mouse or the trackpad (LLFR-00214, LLFR-00215).
ZOOM_MOUSE_LINE_TUPLE = ("Click or drag to zoom in",
                         "Wheel or two-finger swipe to zoom in or out")
# LLFR-00356: how the Pan tool is used with the mouse (LLFR-00214,
# LLFR-00215). The Pan tool has no hold key.
PAN_MOUSE_LINE_TUPLE = ("Drag on a plot to pan",)
# LLFR-00213 to LLFR-00215: the shortcut or mouse use of each button,
# LLFR-00883: the one table the tips are built from, made from the
# same key constants and shortcuts as the window, so that a changed
# shortcut changes its button tip with it; next to the keys the app
# really uses (view.tip_key_filter and the
# shortcuts above), as (kind, value). A button that is not listed (Open
# file, Grid, Save signals, Save layout, Load layout, Report a bug)
# shows only its name (LLFR-00465).
BUTTON_TIP_SHORTCUT_DICT = {
    UNDO_TEXT_STR: (SHORTCUT_SEQUENCE_STR, UNDO_STANDARD_KEY),
    REDO_TEXT_STR: (SHORTCUT_SEQUENCE_STR, REDO_SHORTCUT_STR),
    # LLFR-00215, LLFR-01136: "Cmd+C" or "Ctrl+C"; LLFR-01139: the
    # Export button's "Save all tabs as PDF" has "Cmd+P" or "Ctrl+P".
    COPY_TEXT_STR: (SHORTCUT_SEQUENCE_STR, COPY_SHORTCUT_STR),
    EXPORT_TEXT_STR: (SHORTCUT_SEQUENCE_STR, PDF_SHORTCUT_STR),
    TIP_TEXT_STR: (SHORTCUT_HOLD_STR, TIP_KEY_I),
    MARKER_TEXT_STR: (SHORTCUT_HOLD_STR, MARKER_KEY_I),
    DELTA_X_TEXT_STR: (SHORTCUT_HOLD_STR, DELTA_X_KEY_I),
    DELTA_Y_TEXT_STR: (SHORTCUT_HOLD_STR, DELTA_Y_KEY_I),
    # LLFR-00287, LLFR-00321: "Hold A" and "Hold T".
    AREA_TEXT_STR: (SHORTCUT_HOLD_STR, AREA_KEY_I),
    TEXT_TEXT_STR: (SHORTCUT_HOLD_STR, TEXT_KEY_I),
    # LLFR-00367: "Hold R".
    ARROW_TEXT_STR: (SHORTCUT_HOLD_STR, ARROW_KEY_I),
    # LLFR-00215, LLFR-00207: "0".
    RESET_ZOOM_TEXT_STR: (SHORTCUT_PRESS_STR, RESET_ZOOM_KEY_I),
    # LLFR-00463, LLFR-01092: "Hold Z", then the two mouse lines.
    ZOOM_TEXT_STR: (SHORTCUT_HOLD_AND_MOUSE_STR,
                    (ZOOM_KEY_I, ZOOM_MOUSE_LINE_TUPLE)),
    PAN_TEXT_STR: (MOUSE_USE_STR, PAN_MOUSE_LINE_TUPLE),
}


def running_on_macos() -> bool:
    """Tell whether the app runs on macOS.

    Inputs: none.
    Outputs: True on macOS; False on Windows and every other system,
        which get the Windows texts of LLFR-00215. Tests replace this
        function to check the texts of both systems.
    """
    # LLFR-00215: the texts differ only between macOS and the others.
    return sys.platform == "darwin"


def key_name_str(key_i: int, macos_b: bool) -> str:
    """Return the name of a single key as the button tips write it.

    Inputs:
        key_i: a Qt.Key value, e.g. TIP_KEY_I.
        macos_b: True for the macOS names.
    Outputs: "Cmd" or "Ctrl" for the Data tip key, "Shift" for Shift,
        the capital letter for a letter key, e.g. "X", and the digit
        for a digit key, e.g. "0".
    """
    # LLFR-00215: the names of the table, derived from the key values.
    if key_i == TIP_KEY_I:
        return MACOS_COMMAND_NAME_STR if macos_b else CONTROL_NAME_STR
    if key_i == MARKER_KEY_I:
        return SHIFT_NAME_STR
    # LLFR-00197, LLFR-00200, LLFR-01092: Qt's letter keys have the
    # code of the capital letter (Qt.Key.Key_X is ord("X")); LLFR-00207:
    # and its digit keys the code of the digit (Qt.Key.Key_0 is ord("0")).
    return chr(key_i)


def key_sequence_name_str(sequence_value, macos_b: bool) -> str:
    """Return the text of a keyboard shortcut, e.g. "Ctrl+Z".

    Inputs:
        sequence_value: a QKeySequence.StandardKey or a portable
            sequence string such as "Ctrl+Y".
        macos_b: True for the macOS text, where Ctrl is Cmd.
    Outputs: the text, e.g. "Cmd+Z" on macOS and "Ctrl+Z" elsewhere.
    """
    # LLFR-00137, LLFR-00191, LLFR-00215: the portable text of the real
    # shortcut, whose Ctrl is the Command key on macOS.
    sequence_str = QKeySequence(sequence_value).toString(
        QKeySequence.SequenceFormat.PortableText)
    if macos_b:
        sequence_str = sequence_str.replace(
            CONTROL_NAME_STR + "+", MACOS_COMMAND_NAME_STR + "+")
    return sequence_str


def button_tip_detail_list(name_str: str, macos_b: bool) -> list:
    """Return the lines shown below a button's name in its button tip.

    Inputs:
        name_str: the button's name, e.g. "Undo".
        macos_b: True for the macOS texts, False for the Windows texts.
    Outputs: a list of str: one shortcut line (LLFR-00213), the
        shortcut and the two mouse use lines of the Zoom button
        (LLFR-00463), the mouse use line of the Pan button (LLFR-00464),
        or an empty list for a button that shows only its name
        (LLFR-00465).
    """
    # LLFR-00215, LLFR-00883: every text comes from
    # BUTTON_TIP_SHORTCUT_DICT, never from a copy of it.
    if name_str not in BUTTON_TIP_SHORTCUT_DICT:
        return []
    kind_str, value = BUTTON_TIP_SHORTCUT_DICT[name_str]
    if kind_str == SHORTCUT_SEQUENCE_STR:
        return [key_sequence_name_str(value, macos_b)]
    if kind_str == SHORTCUT_HOLD_STR:
        return [HOLD_PREFIX_STR + key_name_str(value, macos_b)]
    if kind_str == SHORTCUT_PRESS_STR:
        return [key_name_str(value, macos_b)]
    if kind_str == SHORTCUT_HOLD_AND_MOUSE_STR:
        # LLFR-00463: the Zoom button has both a held key and a mouse
        # use.
        key_i, mouse_line_tuple = value
        return ([HOLD_PREFIX_STR + key_name_str(key_i, macos_b)]
                + list(mouse_line_tuple))
    # LLFR-00214: the Zoom and Pan tools are used with the mouse.
    return list(value)


def button_tip_text_str(name_str: str, macos_b: bool) -> str:
    """Return the button tip of a top panel button.

    Inputs:
        name_str: the button's name.
        macos_b: True for the macOS texts.
    Outputs: the plain name for a button with nothing below its name;
        otherwise rich text with the name on the first line and each
        line of button_tip_detail_list below it, in the paler color
        theme.TOOLTIP_DETAIL_COLOR_STR.
    """
    # LLFR-00181: the name alone, as plain text.
    detail_list = button_tip_detail_list(name_str, macos_b)
    if not detail_list:
        return name_str
    # LLFR-00213, LLFR-00214: one block per line, the lines below the
    # name in the paler color; nowrap keeps each line on one line.
    block_list = [f'<div style="white-space:nowrap">'
                  f'{html.escape(name_str)}</div>']
    for detail_str in detail_list:
        block_list.append(
            f'<div style="white-space:nowrap; color:'
            f'{theme.TOOLTIP_DETAIL_COLOR_STR}">'
            f'{html.escape(detail_str)}</div>')
    return "".join(block_list)


def new_icon_button(button_class, name_str: str, object_name_str: str):
    """Create a top panel button that shows only its icon.

    Inputs:
        button_class: ToggleButton or one of its subclasses.
        name_str: the button's name, e.g. "Open file".
        object_name_str: the objectName that scopes its style sheet.
    Outputs: the new button, with the icon of BUTTON_ICON_DICT, the
        name as its accessible name and the button tip of
        button_tip_text_str.
    """
    # LLFR-00158, LLFR-00159, LLFR-00181: icon only, name on hover.
    button = button_class(name_str, icon_name_str=BUTTON_ICON_DICT[name_str])
    button.setObjectName(object_name_str)
    # LLFR-00213 to LLFR-00215: the shortcut or mouse use below the name,
    # with the texts of the system the app runs on.
    button.setToolTip(button_tip_text_str(name_str, running_on_macos()))
    return button


def group_segment_list(button_count_i: int) -> list:
    """Return the place of each button in a joined group.

    Inputs:
        button_count_i: the number of buttons of the group.
    Outputs: a list of theme segment names, one per button:
        [SEGMENT_SINGLE_STR] for one button, otherwise
        SEGMENT_FIRST_STR, then SEGMENT_MIDDLE_STR for the inner
        buttons, then SEGMENT_LAST_STR.
    """
    # LLFR-00348: rounded corners only on the outer side of the first
    # and last buttons of a group.
    if button_count_i <= 1:
        return [theme.SEGMENT_SINGLE_STR] * button_count_i
    return ([theme.SEGMENT_FIRST_STR]
            + [theme.SEGMENT_MIDDLE_STR] * (button_count_i - 2)
            + [theme.SEGMENT_LAST_STR])


class TopPanel(QWidget):
    """Panel placed above the plot and signal list panels (HLFR-00001).

    Inputs: none.
    Signals:
        plot_tool_changed(str): the active plot tool changed; the value
            is a name of controller.plot_tools, NO_TOOL_STR when no plot
            tool is active any more (LLFR-00079, LLFR-00002).
        report_bug_requested: the Report a bug button was clicked, once
            its active color is painted (LLFR-00359, LLFR-00360).
    Attributes:
        button_layout: horizontal layout that holds the panel's buttons.
        open_file_button: the "Open file" ToggleButton (LLFR-00004).
        save_layout_button: the "Save layout" UndoButton (LLFR-00216),
            directly right of Open file; disabled while no data file is
            open (LLFR-00218).
        load_layout_button: the "Load layout" UndoButton (LLFR-00217),
            directly right of Save layout; disabled while no data file
            is open (LLFR-00218).
        tip_button: the "Data tip" ToggleButton (LLFR-00018).
        zoom_button: the "Zoom" ToggleButton (LLFR-00077).
        pan_button: the "Pan" ToggleButton (LLFR-00355), right of Zoom.
        marker_button: the "Vertical marker" ToggleButton (LLFR-00080).
        delta_x_button: the "Delta X" ToggleButton (LLFR-00161).
        delta_y_button: the "Delta Y" ToggleButton (LLFR-00162).
        area_button: the "Area" ToggleButton (LLFR-00286).
        text_button: the "Text" ToggleButton (LLFR-00320).
        arrow_button: the "Arrow" ToggleButton (LLFR-00366), right of
            Text.
        plot_tool_button_dict: plot tool name -> its ToggleButton, in
            the order of the buttons (LLFR-00347).
        reset_zoom_button: the "Reset zoom" ActionButton (LLFR-00114);
            not a plot tool.
        grid_button: the "Grid" ToggleButton (LLFR-00121); not a plot
            tool, it shows whether the grid is shown (LLFR-00124).
        export_button: the "Export" ToggleButton (LLFR-00126).
        copy_button: the "Copy" ToggleButton (LLFR-00132).
        save_signals_button: the "Save signals" UndoButton
            (LLFR-00394), directly right of Copy; disabled while no data
            file is open (LLFR-00395).
        undo_button: the "Undo" UndoButton (LLFR-00136); not a plot
            tool, disabled while nothing can be undone (LLFR-00141).
        redo_button: the "Redo" UndoButton (LLFR-00190), directly right
            of the Undo button; disabled while nothing can be redone
            (LLFR-00194).
        report_bug_button: the "Report a bug" ActionButton
            (LLFR-00358), alone in the last group; always enabled.
        button_group_list: the button groups of LLFR-00347, from left
            to right, each a list of its buttons from left to right.
        credit_label: the QLabel with CREDIT_TEXT_STR (LLFR-00364),
            not in the button layout: place_credit_label puts it at the
            right end of the panel, or hides it when it does not fit.
    """

    plot_tool_changed = pyqtSignal(str)
    pdf_export_requested = pyqtSignal()
    # LLFR-01223: the Word and PNG options of the Export menu.
    docx_export_requested = pyqtSignal()
    png_export_requested = pyqtSignal()
    copy_requested = pyqtSignal()
    save_layout_requested = pyqtSignal()
    load_layout_requested = pyqtSignal()
    save_signals_requested = pyqtSignal()
    report_bug_requested = pyqtSignal()

    def __init__(self) -> None:
        """Create the panel with its buttons, aligned to the left.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        # LLFR-00058: the top panel exists and is placed by MainWindow.
        self.setObjectName("top_panel")
        self.button_layout = QHBoxLayout(self)
        # LLFR-00058: the window margins frame the panel.
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        # LLFR-00348: no space inside a group; LLFR-00349 adds the gaps
        # between the groups explicitly.
        self.button_layout.setSpacing(0)
        # LLFR-00004: the "Open file" button; LLFR-00001: it shows when
        # it is active. LLFR-00158: each button shows only its icon.
        self.open_file_button = new_icon_button(
            ToggleButton, OPEN_FILE_TEXT_STR, "open_file_button")
        # LLFR-00216, LLFR-00217: Save layout and Load layout, right of
        # Open file. LLFR-00218: disabled, and paler, until a data file
        # is open.
        self.save_layout_button = new_icon_button(
            UndoButton, SAVE_LAYOUT_TEXT_STR, "save_layout_button")
        self.load_layout_button = new_icon_button(
            UndoButton, LOAD_LAYOUT_TEXT_STR, "load_layout_button")
        self.save_layout_button.setEnabled(False)
        self.load_layout_button.setEnabled(False)
        # LLFR-00018, LLFR-00077, LLFR-00080, LLFR-00161, LLFR-00162,
        # LLFR-00286, LLFR-00320: the plot tool buttons.
        self.tip_button = new_icon_button(
            ToggleButton, TIP_TEXT_STR, "tip_button")
        self.zoom_button = new_icon_button(
            ToggleButton, ZOOM_TEXT_STR, "zoom_button")
        # LLFR-00355: the Pan tool button, exclusive like the others.
        self.pan_button = new_icon_button(
            ToggleButton, PAN_TEXT_STR, "pan_button")
        self.marker_button = new_icon_button(
            ToggleButton, MARKER_TEXT_STR, "marker_button")
        self.delta_x_button = new_icon_button(
            ToggleButton, DELTA_X_TEXT_STR, "delta_x_button")
        self.delta_y_button = new_icon_button(
            ToggleButton, DELTA_Y_TEXT_STR, "delta_y_button")
        self.area_button = new_icon_button(
            ToggleButton, AREA_TEXT_STR, "area_button")
        self.text_button = new_icon_button(
            ToggleButton, TEXT_TEXT_STR, "text_button")
        # LLFR-00366: the Arrow tool button, the last plot tool.
        self.arrow_button = new_icon_button(
            ToggleButton, ARROW_TEXT_STR, "arrow_button")
        # LLFR-00079, LLFR-00347: the plot tools, in the order of their
        # buttons.
        self.plot_tool_button_dict = {
            TIP_TOOL_STR: self.tip_button,
            ZOOM_TOOL_STR: self.zoom_button,
            PAN_TOOL_STR: self.pan_button,
            MARKER_TOOL_STR: self.marker_button,
            DELTA_X_TOOL_STR: self.delta_x_button,
            DELTA_Y_TOOL_STR: self.delta_y_button,
            AREA_TOOL_STR: self.area_button,
            TEXT_TOOL_STR: self.text_button,
            ARROW_TOOL_STR: self.arrow_button}
        for tool_str, button in self.plot_tool_button_dict.items():
            # LLFR-00333: turning a plot tool on or off with its button
            # keeps a text note field open (TextNoteEditor).
            button.setProperty(KEEPS_TEXT_NOTE_OPEN_PROPERTY_STR, True)
            # LLFR-00079: activating a tool button deactivates the others.
            button.activated.connect(
                lambda tool_str=tool_str: self.activate_plot_tool(tool_str))
            # LLFR-00002: a second click leaves no tool active.
            button.deactivated.connect(self.deactivate_plot_tools)
        # LLFR-00114, LLFR-00121: Reset zoom and Grid. They are not in
        # plot_tool_button_dict, so the plot tools never deactivate them
        # and they never deactivate a plot tool.
        self.reset_zoom_button = new_icon_button(
            ActionButton, RESET_ZOOM_TEXT_STR, "reset_zoom_button")
        self.grid_button = new_icon_button(
            ToggleButton, GRID_TEXT_STR, "grid_button")
        # LLFR-00126, LLFR-00132: the Export and Copy buttons; they are
        # active while their function runs (LLFR-00001, LLFR-00003).
        self.export_button = new_icon_button(
            ToggleButton, EXPORT_TEXT_STR, "export_button")
        self.copy_button = new_icon_button(
            ToggleButton, COPY_TEXT_STR, "copy_button")
        # LLFR-00394: the Save signals button, right of Copy.
        # LLFR-00395: disabled, and paler, until a data file is open.
        self.save_signals_button = new_icon_button(
            UndoButton, SAVE_SIGNALS_TEXT_STR, "save_signals_button")
        self.save_signals_button.setEnabled(False)
        # LLFR-00136: the Undo button; LLFR-00141: disabled until there
        # is an action to undo. Not a plot tool. LLFR-00190: the Redo
        # button, directly right of Undo; LLFR-00194: disabled until an
        # action is undone.
        self.undo_button = new_icon_button(
            UndoButton, UNDO_TEXT_STR, "undo_button")
        self.undo_button.setEnabled(False)
        self.redo_button = new_icon_button(
            UndoButton, REDO_TEXT_STR, "redo_button")
        self.redo_button.setEnabled(False)
        # LLFR-00358: the Report a bug button, enabled whether or not a
        # data file is open. LLFR-00360: an ActionButton, so it is active
        # until the page is asked for and at least 0.3 s.
        self.report_bug_button = new_icon_button(
            ActionButton, REPORT_BUG_TEXT_STR, "report_bug_button")
        # LLFR-00347: the groups, from left to right.
        self.button_group_list = [
            [self.open_file_button, self.save_layout_button,
             self.load_layout_button],
            list(self.plot_tool_button_dict.values()),
            [self.reset_zoom_button, self.grid_button],
            [self.export_button, self.copy_button,
             self.save_signals_button],
            [self.undo_button, self.redo_button],
            [self.report_bug_button]]
        for group_index_i, button_group in enumerate(
                self.button_group_list):
            # LLFR-00349: 16 px between one group and the next.
            if group_index_i > 0:
                self.button_layout.addSpacing(theme.TOOLBAR_GROUP_GAP_I)
            # LLFR-00348: the buttons of a group touch and are drawn as
            # one joined block.
            for segment_str, button in zip(
                    group_segment_list(len(button_group)), button_group):
                button.set_segment_position(segment_str)
                self.button_layout.addWidget(button)
        # LLFR-00004, LLFR-00018: the stretch keeps the buttons on the
        # left.
        self.button_layout.addStretch(1)
        # LLFR-00364: the credit text is a child of the panel but not in
        # the layout, so it can never push, squeeze or cover a button;
        # place_credit_label puts it at the right end or hides it. It
        # lets every mouse event through, takes no focus, has no tip and
        # its style sheet has no hover rule, so it never reacts to the
        # mouse.
        # LLFR-00889: the text is rich text so that only the name is
        # underlined; the style sheet color applies to all of it.
        self.credit_label = QLabel(self)
        self.credit_label.setTextFormat(Qt.TextFormat.RichText)
        self.credit_label.setText(CREDIT_RICH_TEXT_STR)
        self.credit_label.setObjectName(CREDIT_LABEL_NAME_STR)
        self.credit_label.setStyleSheet(
            theme.credit_label_style_sheet(CREDIT_LABEL_NAME_STR))
        self.credit_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.credit_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.credit_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction)
        self.credit_label.adjustSize()
        # LLFR-00359, LLFR-00360: the page is asked for once control is
        # back in Qt, so the active color is painted first.
        self.report_bug_button.triggered.connect(
            lambda: QTimer.singleShot(0, self.emit_pending_report_bug))
        # LLFR-00219, LLFR-00221: the dialogs open once control is back
        # in Qt, so the active color is painted first (LLFR-00001).
        self.save_layout_button.triggered.connect(
            lambda: QTimer.singleShot(0, self.emit_pending_save_layout))
        self.load_layout_button.triggered.connect(
            lambda: QTimer.singleShot(0, self.emit_pending_load_layout))
        # LLFR-00396: the save dialog opens once control is back in Qt,
        # so the active color is painted first (LLFR-00001).
        self.save_signals_button.triggered.connect(
            lambda: QTimer.singleShot(0, self.emit_pending_save_signals))
        # LLFR-00127, LLFR-00133: the menu and the copy run once control
        # is back in Qt, so the active color is painted first.
        self.export_button.activated.connect(
            lambda: QTimer.singleShot(0, self.show_pending_export_menu))
        self.copy_button.activated.connect(
            lambda: QTimer.singleShot(0, self.emit_pending_copy))

    def button_list(self) -> list:
        """Return the buttons of the panel, from left to right.

        Inputs: none.
        Outputs: a list of ToggleButton objects.
        """
        # LLFR-00158, LLFR-00181: every button of the panel.
        return [self.button_layout.itemAt(index_i).widget()
                for index_i in range(self.button_layout.count())
                if self.button_layout.itemAt(index_i).widget() is not None]

    def credit_fits_b(self) -> bool:
        """Tell whether the credit text fits beside the buttons.

        Inputs: none.
        Outputs: True when the panel is wide enough for every button,
            the gap theme.CREDIT_MINIMUM_GAP_I and the credit text.
        """
        # LLFR-00364: the width the buttons need, without the stretch,
        # does not depend on the panel's current width.
        buttons_width_i = self.button_layout.sizeHint().width()
        needed_width_i = (buttons_width_i + theme.CREDIT_MINIMUM_GAP_I
                          + self.credit_label.sizeHint().width())
        return self.width() >= needed_width_i

    def place_credit_label(self) -> None:
        """Put the credit text at the right end, or hide it.

        Inputs: none.
        Outputs: none. The label is shown, right-aligned and vertically
            centered on the buttons, when it fits (credit_fits_b), and
            hidden otherwise; the buttons never move.
        """
        # LLFR-00364: at the right end of the panel, in its upper-right
        # corner (HLFR-00080), hidden when the window is too narrow.
        label_size = self.credit_label.sizeHint()
        self.credit_label.resize(label_size)
        self.credit_label.move(
            self.width() - label_size.width(),
            max(0, (self.height() - label_size.height()) // 2))
        self.credit_label.setVisible(self.credit_fits_b())

    def resizeEvent(self, event) -> None:
        """Place the credit text again when the panel is resized.

        Inputs:
            event: the QResizeEvent.
        Outputs: none.
        """
        # LLFR-00364: it follows the right end, or hides when narrow.
        super().resizeEvent(event)
        self.place_credit_label()

    def showEvent(self, event) -> None:
        """Place the credit text when the panel is first shown.

        Inputs:
            event: the QShowEvent.
        Outputs: none.
        """
        # LLFR-00364: placed before the first paint.
        super().showEvent(event)
        self.place_credit_label()

    def emit_pending_report_bug(self) -> None:
        """Report the click on the Report a bug button.

        Inputs: none.
        Outputs: none. Emits report_bug_requested unless the panel was
            deleted meanwhile.
        """
        # LLFR-00359, LLFR-00360: the page is asked for after the active
        # color shows.
        if sip.isdeleted(self):
            return
        self.report_bug_requested.emit()

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
        Outputs: a QMenu (not shown) with the "Save all tabs as PDF",
            "Save all tabs as Word document (.docx)" and "Save each tab as
            PNG" actions, in this order.
        """
        # LLFR-00127: the Export menu has the PDF option; LLFR-01223:
        # then the Word and PNG options.
        menu = QMenu(self)
        for text_str in (SAVE_PDF_TEXT_STR, SAVE_DOCX_TEXT_STR,
                         SAVE_PNG_TEXT_STR):
            menu.addAction(text_str)
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
        # LLFR-01224, LLFR-01227: the Word and PNG exports, likewise.
        if chosen_text_str == SAVE_DOCX_TEXT_STR:
            self.docx_export_requested.emit()
            return
        if chosen_text_str == SAVE_PNG_TEXT_STR:
            self.png_export_requested.emit()
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

    def emit_pending_save_layout(self) -> None:
        """Report the click on the Save layout button.

        Inputs: none.
        Outputs: none. Emits save_layout_requested unless the panel was
            deleted meanwhile.
        """
        # LLFR-00219: the save dialog opens after the active color shows.
        if sip.isdeleted(self):
            return
        self.save_layout_requested.emit()

    def emit_pending_load_layout(self) -> None:
        """Report the click on the Load layout button.

        Inputs: none.
        Outputs: none. Emits load_layout_requested unless the panel was
            deleted meanwhile.
        """
        # LLFR-00221: the file dialog opens after the active color shows.
        if sip.isdeleted(self):
            return
        self.load_layout_requested.emit()

    def emit_pending_save_signals(self) -> None:
        """Report the click on the Save signals button.

        Inputs: none.
        Outputs: none. Emits save_signals_requested unless the panel was
            deleted meanwhile.
        """
        # LLFR-00396: the save dialog opens after the active color shows.
        if sip.isdeleted(self):
            return
        self.save_signals_requested.emit()
