"""Application-wide filter that turns keys into hold-to-use plot tool keys.

Four keys work this way:
    - the Tip key keeps the Tip tool active while it is held alone
      (LLFR-00148); releasing it leaves no plot tool active (LLFR-00149);
      pressing any other key while it is held ends the activation at
      once (LLFR-00150);
    - the Shift key does the same for the Vertical marker tool
      (LLFR-00154, LLFR-00155, LLFR-00156);
    - the X key does the same for the Delta X tool (LLFR-00197,
      LLFR-00198, LLFR-00199);
    - the Y key does the same for the Delta Y tool (LLFR-00200,
      LLFR-00201, LLFR-00202).
Besides these tool keys, the filter knows action keys: a key that runs
a function once when it is pressed alone. The Z key is one: it resets
the zoom (LLFR-00207).
No key activates a tool or runs an action while the keyboard focus is
in a text field (LLFR-00157), so that letters, capital letters and
shortcuts can be typed there.

The Tip key:
    The Tip key is ``Qt.Key.Key_Control``. On Windows and Linux this is the
    Ctrl key. On macOS, Qt reports the Command key as ``Key_Control`` (and
    ``ControlModifier``) and the physical Control key as ``Key_Meta``,
    unless the attribute ``Qt.ApplicationAttribute.AA_MacDontSwapCtrlAndMeta``
    is set, which plot_tool never does. So ``Key_Control`` is the Command
    key on macOS and the Ctrl key elsewhere, as LLFR-00148 asks.

Rules:
    - "Alone" means that, when a tool key is pressed, no other key is
      held and no modifier other than the key's own one is down. A key
      pressed while a tool key is held ends the activation; it is not
      renewed until the tool key is released and pressed again.
    - The tool keys count as "another key" for each other: with one
      held, pressing another ends the first activation, and the second
      key is not alone, so it activates nothing. No plot tool is then
      active.
    - An action key runs its function only when it is pressed alone:
      no other key held and no modifier but the keypad flag (so Ctrl+Z
      and Cmd+Z stay Undo, LLFR-00137). Pressed while a tool key is
      held, it ends that activation like any other key (LLFR-00150,
      LLFR-00156, LLFR-00199, LLFR-00202) and, not being alone, runs
      nothing. Whether the action may run at that moment (for example
      not during a mouse drag) is decided by the function itself.
    - Auto-repeat key events are ignored, so a held key never restarts
      an activation or runs an action again.
    - Releasing a tool key also forgets every other held key except the
      modifier tool keys (Tip key, Shift), because macOS can drop the
      release of a key pressed together with Cmd. The letter tool keys
      (X, Y) are forgotten too, since Cmd+X and Cmd+Y (Redo) can lose
      their release like any other letter.
    - When the app or its window loses the keyboard (application state
      change to not active, ``WindowDeactivate``, or ``FocusOut`` with
      ``ActiveWindowFocusReason``) the activation ends as on a release,
      and the record of held keys is cleared, since their release events
      will never arrive. A ``FocusOut`` with another reason only moves
      the focus inside the window (for example a click on a plot) and
      is ignored, so it does not interrupt the tool.
    - A tool or action key pressed while a text field has the keyboard
      focus (the
      receiver of the key or ``QApplication.focusWidget()`` is one of
      the text field classes given to the filter) does nothing. When a
      text field gets the focus (``FocusIn``) while an activation is on,
      the activation ends as on a release.
    - ``cancel_activation`` ends the temporary state WITHOUT calling the
      release callback. MainWindow calls it whenever the plot tool changes
      for any reason other than this filter (a mouse click on a tool
      button), so the user's click is kept and the later release of the
      tool key changes nothing.
    - The filter never consumes an event: every key, including the key
      combinations of LLFR-00150 and LLFR-00156 (e.g. Ctrl+Z, Shift+A)
      and every key typed in a text box, still reaches its normal handler.
      Mouse events are not looked at, so Shift+click and Shift+drag on a
      plot work as plain clicks and drags of the Vertical marker tool.

Qt delivers one key press several times to an application event filter
(a ``ShortcutOverride`` first, then the ``KeyPress`` to the window and to
each widget it propagates through). Every handler below is idempotent,
so these repeated deliveries change nothing.
"""

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QFocusEvent, QGuiApplication, QKeyEvent
from PyQt6.QtWidgets import QApplication

from controller.plot_tools import NO_TOOL_STR

# LLFR-00148: the Tip key (Command on macOS, Ctrl elsewhere; see above).
TIP_KEY_I = int(Qt.Key.Key_Control.value)
# LLFR-00154: the key that holds the Vertical marker tool.
MARKER_KEY_I = int(Qt.Key.Key_Shift.value)
# LLFR-00197: the key that holds the Delta X tool.
DELTA_X_KEY_I = int(Qt.Key.Key_X.value)
# LLFR-00200: the key that holds the Delta Y tool.
DELTA_Y_KEY_I = int(Qt.Key.Key_Y.value)
# LLFR-00207: the key that resets the zoom.
RESET_ZOOM_KEY_I = int(Qt.Key.Key_Z.value)
# LLFR-00148, LLFR-00154: the modifier each tool key sets by itself; with
# the keypad flag, the only modifiers allowed while the key is "alone".
# LLFR-00197, LLFR-00200, LLFR-00207: a letter key sets none.
OWN_MODIFIER_DICT = {
    TIP_KEY_I: int(Qt.KeyboardModifier.ControlModifier.value),
    MARKER_KEY_I: int(Qt.KeyboardModifier.ShiftModifier.value)}
KEYPAD_MODIFIER_I = int(Qt.KeyboardModifier.KeypadModifier.value)
# LLFR-00148, LLFR-00149: no activation is on.
NO_KEY_I = 0
# LLFR-00148, LLFR-00150: the key events the filter looks at.
KEY_PRESS_TYPE_TUPLE = (QEvent.Type.KeyPress, QEvent.Type.ShortcutOverride)


def application_is_active() -> bool:
    """Tell whether the application has the keyboard.

    Inputs: none.
    Outputs: True while the application state is ApplicationActive.
    """
    # LLFR-00149, LLFR-00155: an inactive application can no longer see
    # the release.
    return (QGuiApplication.applicationState()
            == Qt.ApplicationState.ApplicationActive)


def modifier_value_i(event) -> int:
    """Return the keyboard modifiers of a key event as an int.

    Inputs:
        event: a QKeyEvent.
    Outputs: the modifier flags, as an int.
    """
    # LLFR-00148, LLFR-00154: PyQt6 flags convert to int through
    # ``.value``.
    modifiers = event.modifiers()
    return int(getattr(modifiers, "value", modifiers))


class ToolKeyFilter(QObject):
    """Event filter that keeps a plot tool active while its key is held.

    Install it on ``QApplication.instance()`` so it sees every key event.

    Inputs:
        key_tool_dict: dict from a tool key code (TIP_KEY_I, MARKER_KEY_I,
            DELTA_X_KEY_I, DELTA_Y_KEY_I) to the name of the plot tool it
            holds (controller.plot_tools).
        on_tool_key_activate: function taking a tool name, called when a
            tool key is pressed alone (LLFR-00148, LLFR-00154,
            LLFR-00197, LLFR-00200).
        on_tool_key_release: function without arguments, called when an
            activation ends: release of the key (LLFR-00149, LLFR-00155),
            another key pressed (LLFR-00150, LLFR-00156), a text field
            focused (LLFR-00157) or the keyboard lost.
        text_field_widget_tuple: tuple of the widget classes that are
            text fields (LLFR-00157).
        parent: optional parent QObject (its lifetime bounds the filter).
        key_action_dict: optional dict from an action key code (e.g.
            RESET_ZOOM_KEY_I) to a function without arguments, called
            once when that key is pressed alone (LLFR-00207).
    Attributes:
        held_key_set: the keys (int codes) currently down, tool keys
            included.
        active_key_i: the tool key whose activation is on, NO_KEY_I when
            none is.
    """

    def __init__(self, key_tool_dict: dict, on_tool_key_activate,
                 on_tool_key_release, text_field_widget_tuple: tuple,
                 parent=None, key_action_dict: dict = None) -> None:
        """Create the filter with its keys, callbacks and text fields.

        Inputs:
            key_tool_dict: see the class docstring.
            on_tool_key_activate: see the class docstring.
            on_tool_key_release: see the class docstring.
            text_field_widget_tuple: see the class docstring.
            parent: optional parent QObject.
            key_action_dict: see the class docstring.
        Outputs: none.
        """
        super().__init__(parent)
        # LLFR-00148, LLFR-00154: which key holds which tool, and what to
        # do on activation and its end.
        self.key_tool_dict = dict(key_tool_dict)
        self.on_tool_key_activate = on_tool_key_activate
        self.on_tool_key_release = on_tool_key_release
        # LLFR-00207: the keys that run a function when pressed alone.
        self.key_action_dict = dict(key_action_dict or {})
        # LLFR-00157: the widgets in which the tool keys do nothing.
        self.text_field_widget_tuple = tuple(text_field_widget_tuple)
        self.held_key_set = set()
        self.active_key_i = NO_KEY_I

    def is_activation_on(self) -> bool:
        """Tell whether a tool key is holding its tool active.

        Inputs: none.
        Outputs: True during an activation of LLFR-00148 or LLFR-00154.
        """
        # LLFR-00148, LLFR-00154: the temporary state.
        return self.active_key_i != NO_KEY_I

    def active_tool(self) -> str:
        """Return the tool held active by a tool key.

        Inputs: none.
        Outputs: the tool name, NO_TOOL_STR when no activation is on.
        """
        # LLFR-00148, LLFR-00154: the tool of the held key.
        return self.key_tool_dict.get(self.active_key_i, NO_TOOL_STR)

    def cancel_activation(self) -> None:
        """End the temporary state without calling the release callback.

        Called when the user changes the plot tool in another way (a
        click on a tool button) while a tool key is held, so that the
        release of the key does not override that choice.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00079, LLFR-00149, LLFR-00155: the user's click wins; the
        # release that follows changes nothing.
        self.active_key_i = NO_KEY_I

    def is_text_field(self, widget) -> bool:
        """Tell whether a widget is a text field.

        Inputs:
            widget: a QObject, or None.
        Outputs: True when it is an instance of a text field class.
        """
        # LLFR-00157: the search box and the name fields are QLineEdit.
        return isinstance(widget, self.text_field_widget_tuple)

    def handle_key_press(self, key_i: int, modifier_mask_i: int,
                         auto_repeat_b: bool,
                         text_field_focused_b: bool = False) -> None:
        """React to a key being pressed.

        Inputs:
            key_i: the Qt key code.
            modifier_mask_i: the keyboard modifiers of the event, as an int.
            auto_repeat_b: True for an auto-repeated press.
            text_field_focused_b: True when a text field has the keyboard
                focus.
        Outputs: none. May call one of the callbacks.
        """
        # LLFR-00148, LLFR-00154: auto-repeat presses are not new presses.
        if auto_repeat_b:
            return
        if key_i in self.held_key_set:
            # LLFR-00148, LLFR-00154: a repeated delivery of the press
            # that started the activation, or the extra Ctrl press some
            # senders add, changes nothing. LLFR-00150, LLFR-00156: any
            # other key ends the activation, even one whose release was
            # never seen.
            if key_i != self.active_key_i:
                self._end_activation()
            return
        other_key_held_b = bool(self.held_key_set)
        self.held_key_set.add(key_i)
        # LLFR-00150, LLFR-00156, LLFR-00199, LLFR-00202: a new key, also
        # an unknown one, an action key or another tool key, ends a
        # running activation; the event itself is never consumed.
        self._end_activation()
        if key_i in self.key_action_dict:
            # LLFR-00207: an action key runs only when pressed alone,
            # without any modifier (Ctrl+Z stays Undo), and LLFR-00157:
            # not while the user types in a text field.
            other_modifier_b = bool(modifier_mask_i & ~KEYPAD_MODIFIER_I)
            if not (other_key_held_b or other_modifier_b
                    or text_field_focused_b):
                self.key_action_dict[key_i]()
            return
        tool_str = self.key_tool_dict.get(key_i, NO_TOOL_STR)
        if tool_str == NO_TOOL_STR:
            return
        allowed_modifier_mask_i = (OWN_MODIFIER_DICT.get(key_i, 0)
                                   | KEYPAD_MODIFIER_I)
        other_modifier_b = bool(modifier_mask_i & ~allowed_modifier_mask_i)
        if other_key_held_b or other_modifier_b:
            # LLFR-00148, LLFR-00154: the tool key is not pressed alone.
            return
        if text_field_focused_b:
            # LLFR-00157: typing in a text field activates no tool.
            return
        self.active_key_i = key_i
        self.on_tool_key_activate(tool_str)

    def handle_key_release(self, key_i: int, auto_repeat_b: bool) -> None:
        """React to a key being released.

        Inputs:
            key_i: the Qt key code.
            auto_repeat_b: True for an auto-repeated release.
        Outputs: none. May call the release callback.
        """
        # LLFR-00148, LLFR-00154: auto-repeat releases do not end the
        # hold.
        if auto_repeat_b:
            return
        self.held_key_set.discard(key_i)
        if key_i not in self.key_tool_dict:
            return
        # LLFR-00148, LLFR-00197, LLFR-00200, LLFR-00207: macOS may never
        # send the release of a key pressed together with Cmd (e.g. the Z
        # of Cmd+Z or the Y of Cmd+Y), so every held key except the
        # modifier tool keys is forgotten here; otherwise such a key
        # would stay "held" and block the next tool or action key press
        # alone. Letter tool keys (X, Y) are no exception.
        self.held_key_set.intersection_update(OWN_MODIFIER_DICT)
        # LLFR-00149, LLFR-00155: releasing the tool key ends its
        # activation.
        if key_i == self.active_key_i:
            self._end_activation()

    def handle_keyboard_lost(self) -> None:
        """React to the app or its window losing the keyboard.

        Inputs: none.
        Outputs: none. May call the release callback.
        """
        # LLFR-00149, LLFR-00155: the release would never be seen, so end
        # now and forget every held key, so nothing can stay stuck.
        self.held_key_set.clear()
        self._end_activation()

    def handle_text_field_focused(self) -> None:
        """React to a text field getting the keyboard focus.

        Inputs: none.
        Outputs: none. May call the release callback.
        """
        # LLFR-00157: no tool stays held while the user types; the held
        # keys are kept, since their releases will still arrive.
        self._end_activation()

    def eventFilter(self, watched, event) -> bool:
        """Look at every event of the application, consuming none.

        Inputs:
            watched: the object the event is sent to.
            event: the QEvent.
        Outputs: always False, so every event goes on to its receiver.
        """
        # LLFR-00148 to LLFR-00150, LLFR-00154 to LLFR-00157: dispatch the
        # key and focus events. The type is checked first, so that most
        # events cost only a few comparisons and no isinstance call.
        event_type = event.type()
        if event_type in KEY_PRESS_TYPE_TUPLE:
            if isinstance(event, QKeyEvent):
                self.dispatch_key_press(watched, event)
        elif event_type == QEvent.Type.KeyRelease:
            if isinstance(event, QKeyEvent):
                self.handle_key_release(int(event.key()),
                                        bool(event.isAutoRepeat()))
        elif event_type == QEvent.Type.FocusIn:
            # LLFR-00157: the focus moved into a text field.
            if self.is_activation_on() and self.is_text_field(watched):
                self.handle_text_field_focused()
        elif event_type == QEvent.Type.WindowDeactivate:
            # LLFR-00149, LLFR-00155: the window lost the keyboard.
            self.handle_keyboard_lost()
        elif (event_type == QEvent.Type.FocusOut
              and isinstance(event, QFocusEvent)):
            # LLFR-00149, LLFR-00155: only a focus change to another
            # window counts.
            if event.reason() == Qt.FocusReason.ActiveWindowFocusReason:
                self.handle_keyboard_lost()
        elif event_type == QEvent.Type.ApplicationStateChange:
            # LLFR-00149, LLFR-00155: the whole application lost the
            # keyboard.
            if not application_is_active():
                self.handle_keyboard_lost()
        # LLFR-00150, LLFR-00156: never consume, so key combinations and
        # typing still work.
        return False

    def dispatch_key_press(self, watched, event) -> None:
        """Pass a key press event to handle_key_press.

        Inputs:
            watched: the object the event is sent to.
            event: the QKeyEvent (KeyPress or ShortcutOverride).
        Outputs: none.
        """
        # LLFR-00157: the focus is only looked up for a tool or action
        # key, so other keys stay cheap. The receiver is checked too,
        # since a key event goes to the focus widget first.
        key_i = int(event.key())
        text_field_focused_b = (
            (key_i in self.key_tool_dict or key_i in self.key_action_dict)
            and (self.is_text_field(watched)
                 or self.is_text_field(QApplication.focusWidget())))
        # LLFR-00148, LLFR-00150, LLFR-00154, LLFR-00156, LLFR-00197 to
        # LLFR-00202, LLFR-00207.
        self.handle_key_press(key_i, modifier_value_i(event),
                              bool(event.isAutoRepeat()),
                              text_field_focused_b)

    def _end_activation(self) -> None:
        """End a running activation and call the release callback once.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00149, LLFR-00150, LLFR-00155, LLFR-00156: only an
        # activation still on is ended.
        if self.active_key_i == NO_KEY_I:
            return
        self.active_key_i = NO_KEY_I
        self.on_tool_key_release()
