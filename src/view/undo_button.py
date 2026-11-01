"""Undo button: an action button that looks paler while it is disabled.

The Undo button runs a one-off action like any ActionButton (LLFR-00001,
LLFR-00003). When no action is left to undo it is disabled and drawn in
paler colors, so the user sees that a click does nothing (LLFR-00141).
"""

from PyQt6.QtCore import QEvent

from view import theme
from view.action_button import ActionButton

# LLFR-00141: paler background, text and border of the disabled button,
# defined in view.theme.
DISABLED_COLOR_STR = theme.DISABLED_COLOR_STR
DISABLED_TEXT_COLOR_STR = theme.DISABLED_TEXT_COLOR_STR
DISABLED_BORDER_COLOR_STR = theme.DISABLED_BORDER_COLOR_STR


class UndoButton(ActionButton):
    """Action button with a paler look while disabled (LLFR-00141).

    Inputs:
        text_str: the text shown on the button, e.g. "Undo".
        parent: optional parent widget.
    """

    def __init__(self, text_str: str, parent=None) -> None:
        """Create an enabled, inactive Undo button.

        Inputs:
            text_str: the text shown on the button.
            parent: optional parent widget.
        Outputs: none.
        """
        # LLFR-00136: the button of the top panel.
        super().__init__(text_str, parent=parent)

    def current_background_color_str(self) -> str:
        """Return the background color in use for the current state.

        Inputs: none.
        Outputs: DISABLED_COLOR_STR while disabled, else the active or
            normal color of ToggleButton.
        """
        # LLFR-00141: paler while nothing can be undone.
        if not self.isEnabled():
            return DISABLED_COLOR_STR
        # LLFR-00001, LLFR-00003: the usual colors otherwise.
        return super().current_background_color_str()

    def _apply_style(self, *_ignored_tuple) -> None:
        """Set the stylesheet of the state plus the disabled rule.

        Inputs:
            _ignored_tuple: the arguments of the triggering signal.
        Outputs: none.
        """
        # LLFR-00001, LLFR-00003, LLFR-00141: one stylesheet for every
        # state; the :disabled rule overrides the colors when disabled.
        self.setStyleSheet(theme.toggle_button_style_sheet(
            self.objectName(), self.isChecked(),
            self.segment_position_str, disabled_rule_b=True))

    def changeEvent(self, event) -> None:
        """Restyle when the button is enabled or disabled.

        Inputs:
            event: the QEvent of the change.
        Outputs: none.
        """
        # LLFR-00141: the :disabled rule takes effect on a repolish.
        super().changeEvent(event)
        if event.type() == QEvent.Type.EnabledChange:
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
