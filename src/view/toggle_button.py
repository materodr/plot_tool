"""Toggle button that shows whether it is active (HLFR-00003).

The button is checkable: its checked state is its active state. Its look
is set in a single place (``_apply_style``), called whenever the checked
state changes, so the color always follows the state. The colors and the
style sheet come from view.theme; the names below are kept so that the
rest of the view and the tests read the state colors from one place.

A button made with an icon name shows only that icon (LLFR-00158),
drawn by view.icons in the color of the button's state (LLFR-00160),
and keeps its name as its hover tip and accessible name (LLFR-00181).

Colors:
    ACTIVE_COLOR_STR: dark ink background shown while the button is
        active (LLFR-00001), with white text for contrast.
    NORMAL_COLOR_STR: light background shown while the button is not
        active (LLFR-00002, LLFR-00003).
"""

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtWidgets import QPushButton

from view import icons, theme

ACTIVE_COLOR_STR = theme.ACTIVE_COLOR_STR
ACTIVE_TEXT_COLOR_STR = theme.ACTIVE_TEXT_COLOR_STR
NORMAL_COLOR_STR = theme.NORMAL_COLOR_STR
NORMAL_TEXT_COLOR_STR = theme.NORMAL_TEXT_COLOR_STR
BORDER_COLOR_STR = theme.BUTTON_BORDER_COLOR_STR
DEFAULT_OBJECT_NAME_STR = "toggle_button"


class ToggleButton(QPushButton):
    """Button that shows when it is active (HLFR-00003).

    Inputs:
        text_str: the button's name, e.g. "Open file": shown on the
            button when it has no icon, else shown only in its hover tip.
        parent: optional parent widget.
        icon_name_str: a name of view.icon_shapes.ICON_NAME_TUPLE, or ""
            for a button that shows its name as text.
    Attributes:
        button_name_str: the button's name.
        icon_name_str: the icon name, "" for a text button.
        segment_position_str: the button's place in a joined group.
    Signals:
        activated: emitted when a click makes the button active
            (LLFR-00001).
        deactivated: emitted when a second click makes the button
            inactive (LLFR-00002). It is not emitted by ``finish``.
    """

    activated = pyqtSignal()
    deactivated = pyqtSignal()

    def __init__(self, text_str: str, parent=None,
                 icon_name_str: str = "") -> None:
        """Create an inactive, checkable button.

        Inputs:
            text_str: the button's name.
            parent: optional parent widget.
            icon_name_str: the icon to show instead of the name, or "".
        Outputs: none.
        """
        super().__init__(parent)
        self.button_name_str = str(text_str)
        self.icon_name_str = str(icon_name_str)
        # LLFR-00158: the name is the accessible name in every case; an
        # icon button shows only its icon. LLFR-00181: Qt shows the
        # tooltip next to the pointer while it rests on the button and
        # hides it when the pointer leaves.
        self.setAccessibleName(self.button_name_str)
        if self.icon_name_str:
            self.setIcon(icons.icon_for(self.icon_name_str))
            self.setIconSize(QSize(theme.ICON_SIZE_I, theme.ICON_SIZE_I))
            self.setFixedSize(theme.ICON_BUTTON_SIZE_I,
                              theme.ICON_BUTTON_SIZE_I)
            self.setToolTip(self.button_name_str)
        else:
            self.setText(self.button_name_str)
        # LLFR-00001: the checked state is the active state.
        self.setCheckable(True)
        # The stylesheet is scoped by objectName so it does not leak to
        # child widgets; a default name is given when none is set.
        if not self.objectName():
            self.setObjectName(DEFAULT_OBJECT_NAME_STR)
        # Place in a joined group of buttons; only the corners change.
        self.segment_position_str = theme.SEGMENT_SINGLE_STR
        self.toggled.connect(self._apply_style)
        self.objectNameChanged.connect(self._apply_style)
        self.clicked.connect(self._emit_click_signal)
        self._apply_style()

    def button_name(self) -> str:
        """Return the button's name, shown in its hover tip.

        Inputs: none.
        Outputs: the name, e.g. "Open file" (LLFR-00158, LLFR-00181).
        """
        # LLFR-00158: the name a button is "called" by the requirements.
        return self.button_name_str

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

    def set_segment_position(self, segment_position_str: str) -> None:
        """Draw the button as a part of a joined group of buttons.

        Inputs:
            segment_position_str: theme.SEGMENT_SINGLE_STR,
                SEGMENT_FIRST_STR, SEGMENT_MIDDLE_STR or
                SEGMENT_LAST_STR.
        Outputs: none. Only the corners and the shared border change;
            the colors still follow the state.
        """
        # LLFR-00001, LLFR-00079: the exclusive plot tools are drawn as
        # one group; the active one is still shown by its color.
        self.segment_position_str = str(segment_position_str)
        self._apply_style()

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
        # LLFR-00158: an icon button has the square icon-only look.
        self.setStyleSheet(theme.toggle_button_style_sheet(
            self.objectName(), self.isChecked(),
            self.segment_position_str,
            icon_only_b=bool(self.icon_name_str)))

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
