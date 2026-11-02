"""One-line text field in which the user writes a text note.

The field is a QLineEdit, so the window treats it as a text field: while
it has the keyboard focus, the plot tool keys, the Z key, Undo and Redo
do not act on the workspace (LLFR-00157, LLFR-00195, LLFR-00196). The
plot widget shows it at the clicked point (LLFR-00333) and decides what
the text becomes; the field only reports how the typing ended.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLineEdit

from view import theme

# LLFR-00334: the keys that confirm the text (Return and the keypad's
# Enter act the same).
CONFIRM_KEY_TUPLE = (Qt.Key.Key_Return, Qt.Key.Key_Enter)
# LLFR-00335: the key that cancels the text.
CANCEL_KEY = Qt.Key.Key_Escape
# LLFR-00334: focus losses that do not confirm the text, because the
# field gets the focus back when the popup or the other window closes.
KEEP_OPEN_FOCUS_REASON_TUPLE = (Qt.FocusReason.PopupFocusReason,
                                Qt.FocusReason.ActiveWindowFocusReason)


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


class TextNoteEditor(QLineEdit):
    """The one-line field of LLFR-00333, with Enter, Esc and focus out.

    Inputs:
        parent: the widget that shows the field (the plot widget).
    Signals:
        confirm_requested(): Return or Enter was pressed, or the field
            lost the keyboard focus, for example because the user clicked
            outside it (LLFR-00334).
        cancel_requested(): Esc was pressed (LLFR-00335).
    """

    confirm_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

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
        self.hide()

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
        # LLFR-00334: a click outside the field confirms it. The plot
        # widget ignores this once the field was already closed. A popup
        # or another window taking the focus for a moment (the field
        # gets it back afterwards) is not a click outside the field.
        super().focusOutEvent(event)
        if event.reason() in KEEP_OPEN_FOCUS_REASON_TUPLE:
            return
        self.confirm_requested.emit()
