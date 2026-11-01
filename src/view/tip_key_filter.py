"""Application-wide filter that turns the Tip key into a hold-to-tip key.

While the user holds the Tip key alone, the Tip tool is active
(LLFR-00148); releasing the key leaves no plot tool active (LLFR-00149);
pressing any other key while the Tip key is held ends the activation at
once (LLFR-00150).

The Tip key:
    The Tip key is ``Qt.Key.Key_Control``. On Windows and Linux this is the
    Ctrl key. On macOS, Qt reports the Command key as ``Key_Control`` (and
    ``ControlModifier``) and the physical Control key as ``Key_Meta``,
    unless the attribute ``Qt.ApplicationAttribute.AA_MacDontSwapCtrlAndMeta``
    is set, which plot_tool never does. So ``Key_Control`` is the Command
    key on macOS and the Ctrl key elsewhere, as LLFR-00148 asks.

Rules:
    - "Alone" means that, when the Tip key is pressed, no other key is
      held and no modifier other than Ctrl is down. A key pressed while
      the Tip key is held ends the activation; it is not renewed until
      the Tip key is released and pressed again.
    - Auto-repeat key events are ignored.
    - Releasing the Tip key also forgets every other held key, because
      macOS can drop the release of a key pressed together with Cmd.
    - When the app or its window loses the keyboard (application state
      change to not active, ``WindowDeactivate``, or ``FocusOut`` with
      ``ActiveWindowFocusReason``) the activation ends as on a release,
      and the record of held keys is cleared, since their release events
      will never arrive. A ``FocusOut`` with another reason only moves
      the focus inside the window (for example a click on a plot) and
      is ignored, so it does not interrupt the tip.
    - ``cancel_activation`` ends the temporary state WITHOUT calling the
      release callback. MainWindow calls it whenever the plot tool changes
      for any reason other than this filter (a mouse click on a tool
      button), so the user's click is kept and the later release of the
      Tip key changes nothing.
    - The filter never consumes an event: every key, including the key
      combination of LLFR-00150 (e.g. Ctrl+Z) and every key typed in a
      text box, still reaches its normal handler.

Qt delivers one key press several times to an application event filter
(a ``ShortcutOverride`` first, then the ``KeyPress`` to the window and to
each widget it propagates through). Every handler below is idempotent,
so these repeated deliveries change nothing.
"""

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QFocusEvent, QGuiApplication, QKeyEvent

# LLFR-00148: the Tip key (Command on macOS, Ctrl elsewhere; see above).
TIP_KEY_I = int(Qt.Key.Key_Control.value)
# LLFR-00148: modifiers that may be down while the Tip key is "alone".
ALLOWED_MODIFIER_MASK_I = int(
    Qt.KeyboardModifier.ControlModifier.value
    | Qt.KeyboardModifier.KeypadModifier.value)
# LLFR-00148, LLFR-00150: the key events the filter looks at.
KEY_PRESS_TYPE_TUPLE = (QEvent.Type.KeyPress, QEvent.Type.ShortcutOverride)


def application_is_active() -> bool:
    """Tell whether the application has the keyboard.

    Inputs: none.
    Outputs: True while the application state is ApplicationActive.
    """
    # LLFR-00149: an inactive application can no longer see the release.
    return (QGuiApplication.applicationState()
            == Qt.ApplicationState.ApplicationActive)


def modifier_value_i(event) -> int:
    """Return the keyboard modifiers of a key event as an int.

    Inputs:
        event: a QKeyEvent.
    Outputs: the modifier flags, as an int.
    """
    # LLFR-00148: PyQt6 flags convert to int through ``.value``.
    modifiers = event.modifiers()
    return int(getattr(modifiers, "value", modifiers))


class TipKeyFilter(QObject):
    """Event filter that keeps the Tip tool active while the Tip key is held.

    Install it on ``QApplication.instance()`` so it sees every key event.

    Inputs:
        on_tip_key_activate: function without arguments, called when the
            Tip key is pressed alone (LLFR-00148).
        on_tip_key_release: function without arguments, called when an
            activation ends: release of the Tip key (LLFR-00149), another
            key pressed (LLFR-00150) or the keyboard lost.
        parent: optional parent QObject (its lifetime bounds the filter).
    Attributes:
        tip_key_held_b: True while the Tip key is down.
        activation_b: True while the temporary Tip activation is on.
        held_key_set: the other keys (int codes) currently down.
    """

    def __init__(self, on_tip_key_activate, on_tip_key_release,
                 parent=None) -> None:
        """Create the filter with its two callbacks.

        Inputs:
            on_tip_key_activate: see the class docstring.
            on_tip_key_release: see the class docstring.
            parent: optional parent QObject.
        Outputs: none.
        """
        super().__init__(parent)
        # LLFR-00148, LLFR-00149: what to do on activation and its end.
        self.on_tip_key_activate = on_tip_key_activate
        self.on_tip_key_release = on_tip_key_release
        self.tip_key_held_b = False
        self.activation_b = False
        self.held_key_set = set()

    def is_activation_on(self) -> bool:
        """Tell whether the Tip key is holding the Tip tool active.

        Inputs: none.
        Outputs: True during an activation of LLFR-00148.
        """
        # LLFR-00148: the temporary state.
        return self.activation_b

    def cancel_activation(self) -> None:
        """End the temporary state without calling the release callback.

        Called when the user changes the plot tool in another way (a
        click on a tool button) while the Tip key is held, so that the
        release of the key does not override that choice.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00079, LLFR-00149: the user's click wins; the release that
        # follows changes nothing.
        self.activation_b = False

    def handle_key_press(self, key_i: int, modifier_mask_i: int,
                         auto_repeat_b: bool) -> None:
        """React to a key being pressed.

        Inputs:
            key_i: the Qt key code.
            modifier_mask_i: the keyboard modifiers of the event, as an int.
            auto_repeat_b: True for an auto-repeated press.
        Outputs: none. May call one of the callbacks.
        """
        # LLFR-00148: auto-repeat presses are not new presses.
        if auto_repeat_b:
            return
        if key_i == TIP_KEY_I:
            # LLFR-00148: a repeated delivery of the same press, or the
            # extra Ctrl press some senders add, changes nothing.
            if self.tip_key_held_b:
                return
            self.tip_key_held_b = True
            other_modifier_b = bool(
                modifier_mask_i & ~ALLOWED_MODIFIER_MASK_I)
            if self.held_key_set or other_modifier_b:
                # LLFR-00148: the Tip key is not pressed alone.
                return
            self.activation_b = True
            self.on_tip_key_activate()
            return
        # LLFR-00150: any other key, also an unknown one, ends the
        # activation; the event itself is never consumed.
        self.held_key_set.add(key_i)
        self._end_activation()

    def handle_key_release(self, key_i: int, auto_repeat_b: bool) -> None:
        """React to a key being released.

        Inputs:
            key_i: the Qt key code.
            auto_repeat_b: True for an auto-repeated release.
        Outputs: none. May call the release callback.
        """
        # LLFR-00148: auto-repeat releases do not end the hold.
        if auto_repeat_b:
            return
        if key_i == TIP_KEY_I:
            # LLFR-00149: releasing the Tip key ends the activation.
            self.tip_key_held_b = False
            # LLFR-00148: macOS may never send the release of a key
            # pressed together with Cmd (e.g. the Z of Cmd+Z), so the
            # held keys are forgotten here; otherwise such a key would
            # stay "held" and block the next Tip key press alone.
            self.held_key_set.clear()
            self._end_activation()
            return
        # LLFR-00148: the other key is no longer held.
        self.held_key_set.discard(key_i)

    def handle_keyboard_lost(self) -> None:
        """React to the app or its window losing the keyboard.

        Inputs: none.
        Outputs: none. May call the release callback.
        """
        # LLFR-00149: the release would never be seen, so end now and
        # forget every held key, so nothing can stay stuck.
        self.tip_key_held_b = False
        self.held_key_set.clear()
        self._end_activation()

    def eventFilter(self, watched, event) -> bool:
        """Look at every event of the application, consuming none.

        Inputs:
            watched: the object the event is sent to.
            event: the QEvent.
        Outputs: always False, so every event goes on to its receiver.
        """
        # LLFR-00148, LLFR-00149, LLFR-00150: dispatch the key events.
        # The type is checked first, so that most events cost only one
        # comparison and no isinstance call.
        event_type = event.type()
        if event_type in KEY_PRESS_TYPE_TUPLE:
            if isinstance(event, QKeyEvent):
                self.handle_key_press(int(event.key()),
                                      modifier_value_i(event),
                                      bool(event.isAutoRepeat()))
        elif event_type == QEvent.Type.KeyRelease:
            if isinstance(event, QKeyEvent):
                self.handle_key_release(int(event.key()),
                                        bool(event.isAutoRepeat()))
        elif event_type == QEvent.Type.WindowDeactivate:
            # LLFR-00149: the window lost the keyboard.
            self.handle_keyboard_lost()
        elif (event_type == QEvent.Type.FocusOut
              and isinstance(event, QFocusEvent)):
            # LLFR-00149: only a focus change to another window counts.
            if event.reason() == Qt.FocusReason.ActiveWindowFocusReason:
                self.handle_keyboard_lost()
        elif event_type == QEvent.Type.ApplicationStateChange:
            # LLFR-00149: the whole application lost the keyboard.
            if not application_is_active():
                self.handle_keyboard_lost()
        # LLFR-00150: never consume, so key combinations still work.
        return False

    def _end_activation(self) -> None:
        """End a running activation and call the release callback once.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00149, LLFR-00150: only an activation still on is ended.
        if not self.activation_b:
            return
        self.activation_b = False
        self.on_tip_key_release()
