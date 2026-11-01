"""Action button: a button that runs a one-off action (HLFR-00003).

Unlike a plot tool button, an action button does not stay active: a
click shows the active color while the action runs, for at least a
minimum time so that the user can see it, and the button then returns
to its normal color by itself (LLFR-00001, LLFR-00003, LLFR-00116).

A click while the button is still active runs the action again and
starts the minimum time again; the button never turns normal early.
"""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from view.toggle_button import ToggleButton

# LLFR-00116: the shortest time the active color is shown, in ms.
MINIMUM_ACTIVE_TIME_MS_I = 300


class ActionButton(ToggleButton):
    """Toggle button that turns normal again once its action is done.

    Inputs:
        text_str: the text shown on the button, e.g. "Reset zoom".
        minimum_active_time_ms_i: the shortest time, in milliseconds,
            the button stays active after a click.
        parent: optional parent widget.
    Signals:
        triggered: emitted on every click, after the button became
            active; the receiver runs the action and then calls
            ``finish``.
    Attributes:
        minimum_active_timer: single-shot QTimer of the minimum time.
        action_running_b: True from a click until ``finish`` is called.
    """

    triggered = pyqtSignal()

    def __init__(self, text_str: str,
                 minimum_active_time_ms_i: int = MINIMUM_ACTIVE_TIME_MS_I,
                 parent=None) -> None:
        """Create an inactive action button.

        Inputs:
            text_str: the text shown on the button.
            minimum_active_time_ms_i: the minimum active time in ms.
            parent: optional parent widget.
        Outputs: none.
        """
        super().__init__(text_str, parent)
        # LLFR-00116: the minimum time starts at each click; the timer is
        # a child, so it never fires after the button is deleted.
        self.action_running_b = False
        self.minimum_active_timer = QTimer(self)
        self.minimum_active_timer.setSingleShot(True)
        # A coarse timer may fire up to 5% early; the minimum is a floor.
        self.minimum_active_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.minimum_active_timer.setInterval(int(minimum_active_time_ms_i))
        self.minimum_active_timer.timeout.connect(
            self._on_minimum_time_elapsed)
        # LLFR-00001: every click, also on the active button, is a new
        # start of the action (a second click must not turn it off).
        self.activated.connect(self._on_clicked)
        self.deactivated.connect(self._on_clicked)

    def finish(self) -> None:
        """Mark the action as done; the color returns once allowed.

        Inputs: none.
        Outputs: none. The button turns normal now if the minimum time
            has passed, else when it passes. No signal is emitted.
        """
        # LLFR-00003, LLFR-00116: normal once the action is done and the
        # minimum time has passed, whichever comes last.
        self.action_running_b = False
        if not self.minimum_active_timer.isActive():
            super().finish()

    def _on_clicked(self) -> None:
        """Show the active color, start the minimum time, run the action.

        Inputs: none.
        Outputs: none. Emits triggered.
        """
        # LLFR-00001, LLFR-00116: active from the click on, for at least
        # the minimum time.
        self.setChecked(True)
        self.action_running_b = True
        self.minimum_active_timer.start()
        self.triggered.emit()

    def _on_minimum_time_elapsed(self) -> None:
        """Return to the normal color if the action is already done.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00003, LLFR-00116: the minimum time has passed.
        if not self.action_running_b:
            ToggleButton.finish(self)
