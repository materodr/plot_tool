"""One-line dialog in which the user types a new name.

The tabs, flags, areas, delta markers, arrows and synthetic signals are
renamed in QInputDialog.getText (LLFR-00030, LLFR-00088, LLFR-00315,
LLFR-00429, LLFR-00439, LLFR-00266). The dialog is a window of its own,
so the shortcuts of the window below it do not reach it. While it is
open, an application event filter catches the app's Ctrl+P and Ctrl+F
(Cmd+P and Cmd+F on macOS) in it: either key accepts the name typed so
far, as the OK button does, and the shortcut's action then runs for the
window the dialog was shown over, once the caller has used the name
(LLFR-01185).
"""

from functools import partial

from PyQt6.QtCore import QEvent, QObject, QTimer
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication, QInputDialog, QLineEdit, QWidget

from view import top_panel

# LLFR-01185: the actions that the shortcuts of the dialog ask for.
PDF_ACTION_STR = "pdf"
SEARCH_ACTION_STR = "search"
# LLFR-01185, LLFR-01139, LLFR-01140: the key sequence of each action,
# the same as the shortcuts of the windows.
ACTION_SEQUENCE_DICT = {
    PDF_ACTION_STR: top_panel.PDF_SHORTCUT_STR,
    SEARCH_ACTION_STR: top_panel.SEARCH_SHORTCUT_STR,
}


def shortcut_action_of(event) -> str:
    """Return the action of a key event, if it is Ctrl+P or Ctrl+F.

    Inputs:
        event: a QKeyEvent.
    Outputs: PDF_ACTION_STR, SEARCH_ACTION_STR, or "" for any other key.
    """
    # LLFR-01185: Ctrl+P and Ctrl+F, Cmd+P and Cmd+F on macOS (Qt names
    # the Command key Ctrl in a portable key sequence).
    pressed_sequence = QKeySequence(event.keyCombination())
    for action_str, sequence_str in ACTION_SEQUENCE_DICT.items():
        if (pressed_sequence.matches(QKeySequence(sequence_str))
                == QKeySequence.SequenceMatch.ExactMatch):
            return action_str
    return ""


class NameDialogShortcutFilter(QObject):
    """Application event filter that ends a name dialog by a shortcut.

    Attributes:
        action_str: the action of the shortcut that accepted a dialog
            (PDF_ACTION_STR or SEARCH_ACTION_STR), or "" when none did.
    """

    def __init__(self) -> None:
        """Start with no shortcut pressed.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        # LLFR-01185: the action to run once the dialog has closed.
        self.action_str = ""

    def eventFilter(self, watched, event) -> bool:
        """Accept the name dialog on Ctrl+P or Ctrl+F.

        Inputs:
            watched: the object the event is sent to.
            event: the QEvent.
        Outputs: True when the event was a shortcut of the dialog and was
            used here, False to let every other event through.
        """
        # LLFR-01185: only the keys of a widget inside a name dialog.
        event_type = event.type()
        if event_type not in (QEvent.Type.ShortcutOverride,
                              QEvent.Type.KeyPress):
            return False
        if not isinstance(watched, QWidget):
            return False
        dialog = watched.window()
        if not isinstance(dialog, QInputDialog):
            return False
        action_str = shortcut_action_of(event)
        if not action_str:
            return False
        if event_type == QEvent.Type.ShortcutOverride:
            # LLFR-01185: the key goes to the dialog as a key press, so
            # that no shortcut of another window takes it.
            event.accept()
            return True
        # LLFR-01185: the text typed so far is taken, as with OK or
        # Enter; the action runs after the dialog has closed.
        self.action_str = action_str
        dialog.accept()
        return True


def ask_name_text(parent, title_str: str, label_str: str, text_str: str,
                  shortcut_handler=None) -> tuple:
    """Show the name dialog and wait for the user's answer.

    Inputs:
        parent: the window the dialog is shown over.
        title_str: the dialog's title.
        label_str: the text above the field.
        text_str: the text the field starts with.
        shortcut_handler: function taking an action string and the
            parent, called once control is back in Qt when Ctrl+P or
            Ctrl+F closed the dialog; None to only close it.
    Outputs: (typed text, accepted_b), as QInputDialog.getText returns.
    """
    # LLFR-01185: the shortcuts are watched only while the dialog is open.
    shortcut_filter = NameDialogShortcutFilter()
    application = QApplication.instance()
    if application is not None:
        application.installEventFilter(shortcut_filter)
    try:
        # LLFR-00030, LLFR-00088, LLFR-00266: the user types the name.
        typed_str, accepted_b = QInputDialog.getText(
            parent, title_str, label_str, QLineEdit.EchoMode.Normal,
            text_str)
    finally:
        if application is not None:
            application.removeEventFilter(shortcut_filter)
    # LLFR-01185: the shortcut's action runs after the caller has used
    # the name (the rename comes first, then for example the PDF dialog
    # opens); the timer fires once the caller has returned to Qt.
    if (accepted_b and shortcut_filter.action_str
            and shortcut_handler is not None):
        QTimer.singleShot(0, partial(shortcut_handler,
                                     shortcut_filter.action_str, parent))
    return str(typed_str), bool(accepted_b)
