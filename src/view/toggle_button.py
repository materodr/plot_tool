"""Toggle button that shows whether it is active (HLFR-00003).

The button is checkable: its checked state is its active state. Its look
is set in a single place (``_apply_style``), called whenever the checked
state changes, so the color always follows the state.

Colors:
    ACTIVE_COLOR_STR: dark green background shown while the button is
        active (LLFR-00001), with white text for contrast.
    NORMAL_COLOR_STR: light grey background shown while the button is
        not active (LLFR-00002, LLFR-00003).
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QPushButton

ACTIVE_COLOR_STR = "#2e7d32"
ACTIVE_TEXT_COLOR_STR = "#ffffff"
NORMAL_COLOR_STR = "#e0e0e0"
NORMAL_TEXT_COLOR_STR = "#000000"
BORDER_COLOR_STR = "#9e9e9e"
DEFAULT_OBJECT_NAME_STR = "toggle_button"

# The same border and padding are used in both states, so the button
# keeps its size when it changes color.
STYLE_TEMPLATE_STR = (
    "QPushButton#{object_name} {{"
    " background-color: {background};"
    " color: {text};"
    " border: 1px solid " + BORDER_COLOR_STR + ";"
    " border-radius: 3px;"
    " padding: 4px 12px;"
    " }}"
)


class ToggleButton(QPushButton):
    """Button that shows when it is active (HLFR-00003).

    Inputs:
        text_str: the text shown on the button, e.g. "Open file".
        parent: optional parent widget.
    Signals:
        activated: emitted when a click makes the button active
            (LLFR-00001).
        deactivated: emitted when a second click makes the button
            inactive (LLFR-00002). It is not emitted by ``finish``.
    """

    activated = pyqtSignal()
    deactivated = pyqtSignal()

    def __init__(self, text_str: str, parent=None) -> None:
        """Create an inactive, checkable button.

        Inputs:
            text_str: the text shown on the button.
            parent: optional parent widget.
        Outputs: none.
        """
        super().__init__(text_str, parent)
        # LLFR-00001: the checked state is the active state.
        self.setCheckable(True)
        # The stylesheet is scoped by objectName so it does not leak to
        # child widgets; a default name is given when none is set.
        if not self.objectName():
            self.setObjectName(DEFAULT_OBJECT_NAME_STR)
        self.toggled.connect(self._apply_style)
        self.objectNameChanged.connect(self._apply_style)
        self.clicked.connect(self._emit_click_signal)
        self._apply_style()

    def is_active(self) -> bool:
        """Tell whether the button is active.

        Inputs: none.
        Outputs: True while the button is active (checked).
        """
        # LLFR-00001, LLFR-00002, LLFR-00003: active means checked.
        return self.isChecked()

    def finish(self) -> None:
        """Return the button to its normal color without emitting a signal.

        Called when the function started by the button has finished.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00003: setChecked does not emit ``clicked``, so neither
        # ``activated`` nor ``deactivated`` is emitted here.
        self.setChecked(False)

    def current_background_color_str(self) -> str:
        """Return the background color in use for the current state.

        Inputs: none.
        Outputs: ACTIVE_COLOR_STR while active, otherwise NORMAL_COLOR_STR.
        """
        # LLFR-00001, LLFR-00002, LLFR-00003: color follows the state.
        if self.isChecked():
            return ACTIVE_COLOR_STR
        return NORMAL_COLOR_STR

    def _apply_style(self, *_ignored_tuple) -> None:
        """Set the stylesheet that matches the current state.

        Inputs:
            _ignored_tuple: the arguments of the signal that triggered
                the call (checked state or new object name), not used.
        Outputs: none.
        """
        # LLFR-00001, LLFR-00002, LLFR-00003: the only place where the
        # look of the button is set.
        if self.isChecked():
            text_color_str = ACTIVE_TEXT_COLOR_STR
        else:
            text_color_str = NORMAL_TEXT_COLOR_STR
        self.setStyleSheet(STYLE_TEMPLATE_STR.format(
            object_name=self.objectName(),
            background=self.current_background_color_str(),
            text=text_color_str))

    def _emit_click_signal(self, checked_b: bool) -> None:
        """Emit ``activated`` or ``deactivated`` after a user click.

        Inputs:
            checked_b: the checked state after the click.
        Outputs: none.
        """
        # LLFR-00001: a click on an inactive button activates it.
        # LLFR-00002: a click on an active button deactivates it.
        if checked_b:
            self.activated.emit()
        else:
            self.deactivated.emit()
