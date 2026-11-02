"""One-line text field in which the user writes a text note.

The field is a QLineEdit, so the window treats it as a text field: while
it has the keyboard focus, the plot tool keys, the Z key, Undo and Redo
do not act on the workspace (LLFR-00157, LLFR-00195, LLFR-00196). The
plot widget shows it at the clicked point (LLFR-00333) and decides what
the text becomes; the field only reports how the typing ended.
"""

from PyQt6.QtCore import QEvent, QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication, QLineEdit, QWidget

from view import theme

# LLFR-00334: the keys that confirm the text (Return and the keypad's
# Enter act the same).
CONFIRM_KEY_TUPLE = (Qt.Key.Key_Return, Qt.Key.Key_Enter)
# LLFR-00335: the key that cancels the text.
CANCEL_KEY = Qt.Key.Key_Escape
# LLFR-00333: name of the widget property that marks the widgets whose
# press keeps the field open (the plot tool buttons of the top panel).
KEEPS_TEXT_NOTE_OPEN_PROPERTY_STR = "keepsTextNoteOpen"
# LLFR-00334: the mouse presses that may confirm the field.
MOUSE_PRESS_EVENT_TUPLE = (QEvent.Type.MouseButtonPress,
                           QEvent.Type.MouseButtonDblClick)
# LLFR-00334: the focus losses that confirm the text: the user moved
# the focus with the mouse or the keyboard. A popup or another window
# taking the focus for a moment (the field gets it back afterwards) does
# not, nor does the app moving the focus by itself, for example while
# an undo rebuilds the plots (LLFR-00342: an Edit field must then write
# nothing). Mouse presses are also caught by OutsidePressFilter.
CONFIRM_FOCUS_REASON_TUPLE = (Qt.FocusReason.MouseFocusReason,
                              Qt.FocusReason.TabFocusReason,
                              Qt.FocusReason.BacktabFocusReason,
                              Qt.FocusReason.ShortcutFocusReason)


def text_note_editor_style_sheet() -> str:
    """Return the style sheet of the text note field.

    Inputs: none.
    Outputs: a Qt style sheet with dark text on a light box, like the
        text note it writes (LLFR-00336).
    """
    # LLFR-00336: the field looks like the note it becomes.
    return (f"QLineEdit {{ color: {theme.TEXT_NOTE_TEXT_COLOR_STR}; "
            f"background: {theme.TEXT_NOTE_BACKGROUND_COLOR_STR}; "
            f"border: 1px solid {theme.FOCUS_COLOR_STR}; "
            f"border-radius: 3px; padding: 1px 4px; }}")


def keeps_text_note_open(widget) -> bool:
    """Tell whether a press on a widget keeps a text note field open.

    Inputs:
        widget: the pressed widget, or None.
    Outputs: True when the widget, or a widget that holds it, has the
        property KEEPS_TEXT_NOTE_OPEN_PROPERTY_STR set to True.
    """
    # LLFR-00333: the plot tool buttons may be clicked while typing.
    while isinstance(widget, QWidget):
        if widget.property(KEEPS_TEXT_NOTE_OPEN_PROPERTY_STR) is True:
            return True
        widget = widget.parentWidget()
    return False


class OutsidePressFilter(QObject):
    """Application event filter that reports a press outside the field.

    It sees every mouse press of the application while it is installed,
    also on widgets that never take the keyboard focus (the top panel
    background, a disabled button, the splitter handle), and lets every
    event through.

    Inputs:
        editor: the TextNoteEditor whose outside presses are reported.
    Signals:
        outside_pressed(): a mouse button was pressed on a widget that
            is not the field and does not keep it open (LLFR-00334).
    """

    outside_pressed = pyqtSignal()

    def __init__(self, editor) -> None:
        """Keep the field; the filter is not installed yet.

        Inputs:
            editor: the TextNoteEditor.
        Outputs: none.
        """
        super().__init__(editor)
        # LLFR-00334: the field whose outside presses confirm it.
        self.editor = editor
        self.installed_b = False

    def install(self) -> None:
        """Start watching the mouse presses of the application.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00334: only while the field is open.
        application = QApplication.instance()
        if application is None or self.installed_b:
            return
        application.installEventFilter(self)
        self.installed_b = True

    def remove(self) -> None:
        """Stop watching the mouse presses.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00334: a closed field needs no filter.
        application = QApplication.instance()
        if application is not None and self.installed_b:
            application.removeEventFilter(self)
        self.installed_b = False

    def eventFilter(self, watched, event) -> bool:
        """Report a press outside the field, and let the event through.

        Inputs:
            watched: the object the event is sent to.
            event: the QEvent.
        Outputs: False, always.
        """
        # LLFR-00334: a click outside the field, wherever it lands. A
        # press goes to a widget and then to its parents, so only a
        # widget's own press is counted, and only presses on widgets.
        if (event.type() in MOUSE_PRESS_EVENT_TUPLE
                and isinstance(watched, QWidget)
                and watched is not self.editor
                and not self.editor.isAncestorOf(watched)
                and not keeps_text_note_open(watched)):
            self.outside_pressed.emit()
        return False


class TextNoteEditor(QLineEdit):
    """The one-line field of LLFR-00333, with Enter, Esc and focus out.

    Inputs:
        parent: the widget that shows the field (the plot widget).
    Signals:
        confirm_requested(): Return or Enter was pressed, or the field
            lost the keyboard focus, for example because the user clicked
            outside it (LLFR-00334).
        outside_pressed(): while the field is shown, a mouse button was
            pressed on any other widget except those that keep it open
            (LLFR-00334, LLFR-00333).
        cancel_requested(): Esc was pressed (LLFR-00335).
    """

    confirm_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    outside_pressed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        """Create the hidden field.

        Inputs:
            parent: the widget that shows the field.
        Outputs: none.
        """
        super().__init__(parent)
        # LLFR-00333: one line of text, hidden until a click opens it.
        self.setObjectName("text_note_editor")
        self.setStyleSheet(text_note_editor_style_sheet())
        # LLFR-00334: presses outside the field, watched while it shows.
        self.outside_press_filter = OutsidePressFilter(self)
        self.outside_press_filter.outside_pressed.connect(
            self.outside_pressed.emit)
        self.hide()

    def showEvent(self, event) -> None:
        """Start watching the presses outside the field.

        Inputs:
            event: the QShowEvent.
        Outputs: none.
        """
        # LLFR-00334: while the field is shown.
        super().showEvent(event)
        self.outside_press_filter.install()

    def hideEvent(self, event) -> None:
        """Stop watching the presses outside the field.

        Inputs:
            event: the QHideEvent.
        Outputs: none.
        """
        # LLFR-00334: a hidden field confirms nothing.
        self.outside_press_filter.remove()
        super().hideEvent(event)

    def keyPressEvent(self, event) -> None:
        """Confirm on Return or Enter, cancel on Esc, else type.

        Inputs:
            event: the QKeyEvent.
        Outputs: none.
        """
        # LLFR-00334: Enter confirms; LLFR-00335: Esc cancels. Neither
        # key reaches the window (for example the Enter key of the signal
        # list, LLFR-00295).
        if event.key() in CONFIRM_KEY_TUPLE:
            event.accept()
            self.confirm_requested.emit()
            return
        if event.key() == CANCEL_KEY:
            event.accept()
            self.cancel_requested.emit()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event) -> None:
        """Confirm the text when the field loses the keyboard focus.

        Inputs:
            event: the QFocusEvent.
        Outputs: none.
        """
        # LLFR-00334: the user moving the focus elsewhere confirms the
        # field (CONFIRM_FOCUS_REASON_TUPLE). The plot widget ignores
        # this once the field was already closed. LLFR-00333: the focus
        # going to a widget that keeps the field open does not.
        super().focusOutEvent(event)
        if event.reason() not in CONFIRM_FOCUS_REASON_TUPLE:
            return
        if keeps_text_note_open(QApplication.focusWidget()):
            return
        self.confirm_requested.emit()
