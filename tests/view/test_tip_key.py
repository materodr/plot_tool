"""Tests for holding the Tip key (LLFR-00148, LLFR-00149, LLFR-00150).

The first class drives the ToolKeyFilter state machine with real Qt key
events and recording callbacks. The Shift key of the same filter is
tested in test_shift_key.py. The second class runs the whole chain:
key events sent to widgets of a MainWindow with the real controllers,
checking the tool buttons, the window, the controller and the plots.
No modal dialog or menu is ever opened.
"""

import unittest
from unittest import mock

import numpy as np

from tests.support import covers, get_qt_application, requires_qt

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR)


def make_key_event(event_type_name_str: str, key_name_str: str,
                   modifier_name_str: str = "NoModifier",
                   auto_repeat_b: bool = False):
    """Build a QKeyEvent.

    Inputs:
        event_type_name_str: name of a QEvent.Type, e.g. "KeyPress".
        key_name_str: name of a Qt.Key, e.g. "Key_Control".
        modifier_name_str: name of a Qt.KeyboardModifier.
        auto_repeat_b: True for an auto-repeated event.
    Outputs: the QKeyEvent.
    """
    from PyQt6.QtCore import QEvent, Qt
    from PyQt6.QtGui import QKeyEvent
    return QKeyEvent(getattr(QEvent.Type, event_type_name_str),
                     int(getattr(Qt.Key, key_name_str).value),
                     getattr(Qt.KeyboardModifier, modifier_name_str),
                     "", auto_repeat_b)


def send_key(receiver, event_type_name_str: str, key_name_str: str,
             modifier_name_str: str = "NoModifier",
             auto_repeat_b: bool = False) -> None:
    """Send one key event to a widget through the application.

    Inputs:
        receiver: the QObject the event is sent to.
        event_type_name_str: name of a QEvent.Type.
        key_name_str: name of a Qt.Key.
        modifier_name_str: name of a Qt.KeyboardModifier.
        auto_repeat_b: True for an auto-repeated event.
    Outputs: none.
    """
    from PyQt6.QtWidgets import QApplication
    QApplication.sendEvent(receiver, make_key_event(
        event_type_name_str, key_name_str, modifier_name_str,
        auto_repeat_b))


@requires_qt
class TipKeyFilterTest(unittest.TestCase):
    """The state machine of the Tip key filter."""

    def setUp(self) -> None:
        """Create a filter with recording callbacks and a target widget.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QLineEdit, QWidget
        from view.tip_key_filter import MARKER_KEY_I, TIP_KEY_I, ToolKeyFilter
        self.call_list = []
        # "activate" for the Tip tool, "activate marker" for the Shift key.
        self.tip_key_filter = ToolKeyFilter(
            {TIP_KEY_I: TIP_TOOL_STR, MARKER_KEY_I: MARKER_TOOL_STR},
            lambda tool_str: self.call_list.append(
                "activate" if tool_str == TIP_TOOL_STR
                else "activate " + tool_str),
            lambda: self.call_list.append("release"), (QLineEdit,))
        self.application.installEventFilter(self.tip_key_filter)
        self.widget = QWidget()

    def tearDown(self) -> None:
        """Remove the filter and delete the widget.

        Inputs: none.
        Outputs: none.
        """
        self.application.removeEventFilter(self.tip_key_filter)
        self.tip_key_filter.deleteLater()
        self.widget.deleteLater()
        self.application.processEvents()

    def press(self, key_name_str: str, modifier_name_str: str = "NoModifier",
              auto_repeat_b: bool = False) -> None:
        """Send a key press to the widget.

        Inputs:
            key_name_str: name of a Qt.Key.
            modifier_name_str: name of a Qt.KeyboardModifier.
            auto_repeat_b: True for an auto-repeated press.
        Outputs: none.
        """
        send_key(self.widget, "KeyPress", key_name_str, modifier_name_str,
                 auto_repeat_b)

    def release(self, key_name_str: str,
                modifier_name_str: str = "NoModifier",
                auto_repeat_b: bool = False) -> None:
        """Send a key release to the widget.

        Inputs:
            key_name_str: name of a Qt.Key.
            modifier_name_str: name of a Qt.KeyboardModifier.
            auto_repeat_b: True for an auto-repeated release.
        Outputs: none.
        """
        send_key(self.widget, "KeyRelease", key_name_str, modifier_name_str,
                 auto_repeat_b)

    @covers("LLFR-00148", "LLFR-00150")
    def test_lost_key_release_does_not_block_the_tip_key(self) -> None:
        """Ctrl, Z, then Ctrl released without the Z release (macOS can
        drop it): the next Ctrl alone activates Tip again.

        Inputs: none.
        Outputs: none.
        """
        self.press("Key_Control", "ControlModifier")
        self.press("Key_Z", "ControlModifier")
        self.assertEqual(self.call_list, ["activate", "release"])
        self.release("Key_Control")
        self.assertEqual(self.tip_key_filter.held_key_set, set())
        self.press("Key_Control", "ControlModifier")
        self.assertEqual(self.call_list, ["activate", "release", "activate"])
        self.assertTrue(self.tip_key_filter.is_activation_on())
        self.release("Key_Control")
        self.assertEqual(self.call_list,
                         ["activate", "release", "activate", "release"])

    @covers("LLFR-00148", "LLFR-00149")
    def test_press_alone_activates_and_release_ends(self) -> None:
        """Ctrl alone activates once; its release ends the activation.

        Inputs: none.
        Outputs: none.
        """
        self.press("Key_Control", "ControlModifier")
        self.assertEqual(self.call_list, ["activate"])
        self.assertTrue(self.tip_key_filter.is_activation_on())
        # A second delivery of the same press (as Qt does while it
        # propagates the event) changes nothing.
        self.press("Key_Control", "ControlModifier")
        self.assertEqual(self.call_list, ["activate"])
        self.release("Key_Control", "ControlModifier")
        self.assertEqual(self.call_list, ["activate", "release"])
        self.assertFalse(self.tip_key_filter.is_activation_on())
        # A repeated release does nothing more.
        self.release("Key_Control")
        self.assertEqual(self.call_list, ["activate", "release"])
        # The next hold works again.
        self.press("Key_Control")
        self.release("Key_Control")
        self.assertEqual(self.call_list,
                         ["activate", "release", "activate", "release"])

    @covers("LLFR-00148")
    def test_shortcut_override_counts_as_a_press(self) -> None:
        """The ShortcutOverride event that precedes a press is handled.

        Inputs: none.
        Outputs: none.
        """
        send_key(self.widget, "ShortcutOverride", "Key_Control",
                 "ControlModifier")
        self.assertEqual(self.call_list, ["activate"])
        send_key(self.widget, "ShortcutOverride", "Key_Z", "ControlModifier")
        self.assertEqual(self.call_list, ["activate", "release"])

    @covers("LLFR-00150", "LLFR-00149")
    def test_other_key_ends_the_activation_at_once(self) -> None:
        """Ctrl then Z ends the activation; the later release does nothing.

        Inputs: none.
        Outputs: none.
        """
        self.press("Key_Control")
        self.press("Key_Z", "ControlModifier")
        self.assertEqual(self.call_list, ["activate", "release"])
        self.assertFalse(self.tip_key_filter.is_activation_on())
        self.release("Key_Z", "ControlModifier")
        # The Tip key is still held, but the activation is not renewed.
        self.assertEqual(self.call_list, ["activate", "release"])
        self.release("Key_Control")
        self.assertEqual(self.call_list, ["activate", "release"])

    @covers("LLFR-00148")
    def test_tip_key_not_alone_does_not_activate(self) -> None:
        """Ctrl pressed while another key or modifier is held does nothing.

        Inputs: none.
        Outputs: none.
        """
        # Another key held before the Tip key.
        self.press("Key_A")
        self.press("Key_Control", "ControlModifier")
        self.release("Key_A", "ControlModifier")
        self.release("Key_Control")
        self.assertEqual(self.call_list, [])
        # Alt held (a modifier other than Ctrl, here without its own
        # key event, as when it was pressed before the window had the
        # keyboard).
        self.press("Key_Control", "AltModifier")
        self.release("Key_Control")
        self.assertEqual(self.call_list, [])
        self.assertEqual(self.tip_key_filter.held_key_set, set())
        # Alone again: it activates.
        self.press("Key_Control")
        self.assertEqual(self.call_list, ["activate"])

    @covers("LLFR-00148", "LLFR-00149")
    def test_auto_repeat_is_ignored(self) -> None:
        """Auto-repeated presses and releases of Ctrl keep the activation.

        Inputs: none.
        Outputs: none.
        """
        self.press("Key_Control")
        for _ in range(5):
            self.release("Key_Control", "ControlModifier", True)
            self.press("Key_Control", "ControlModifier", True)
        self.assertEqual(self.call_list, ["activate"])
        self.assertTrue(self.tip_key_filter.is_activation_on())
        # An auto-repeated other key is not a new key press either.
        self.press("Key_Z", "ControlModifier", True)
        self.assertEqual(self.call_list, ["activate"])
        self.release("Key_Control")
        self.assertEqual(self.call_list, ["activate", "release"])

    @covers("LLFR-00149")
    def test_keyboard_loss_ends_the_activation(self) -> None:
        """Window deactivation and focus leaving the window end the hold.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QFocusEvent
        from PyQt6.QtWidgets import QApplication
        self.press("Key_Control")
        QApplication.sendEvent(self.widget,
                               QEvent(QEvent.Type.WindowDeactivate))
        self.assertEqual(self.call_list, ["activate", "release"])
        # The key is forgotten, so a new press activates again.
        self.press("Key_Control")
        self.assertEqual(self.call_list, ["activate", "release", "activate"])
        # A focus move inside the window (a click on a plot) is ignored.
        QApplication.sendEvent(self.widget, QFocusEvent(
            QEvent.Type.FocusOut, Qt.FocusReason.MouseFocusReason))
        self.assertTrue(self.tip_key_filter.is_activation_on())
        # Focus going to another window ends it.
        QApplication.sendEvent(self.widget, QFocusEvent(
            QEvent.Type.FocusOut, Qt.FocusReason.ActiveWindowFocusReason))
        self.assertEqual(self.call_list,
                         ["activate", "release", "activate", "release"])
        # A key held when the keyboard was lost does not block later.
        self.press("Key_A")
        QApplication.sendEvent(self.widget,
                               QEvent(QEvent.Type.WindowDeactivate))
        self.press("Key_Control")
        self.assertTrue(self.tip_key_filter.is_activation_on())

    @covers("LLFR-00149")
    def test_application_state_change_ends_the_activation(self) -> None:
        """The app becoming inactive ends the hold; staying active not.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent
        from PyQt6.QtWidgets import QApplication
        from view import tip_key_filter as tip_key_filter_module
        self.press("Key_Control")
        with mock.patch.object(tip_key_filter_module,
                               "application_is_active", return_value=True):
            QApplication.sendEvent(self.application,
                                   QEvent(QEvent.Type.ApplicationStateChange))
        self.assertEqual(self.call_list, ["activate"])
        with mock.patch.object(tip_key_filter_module,
                               "application_is_active", return_value=False):
            QApplication.sendEvent(self.application,
                                   QEvent(QEvent.Type.ApplicationStateChange))
        self.assertEqual(self.call_list, ["activate", "release"])

    @covers("LLFR-00149", "LLFR-00079")
    def test_cancel_makes_the_release_do_nothing(self) -> None:
        """After cancel_activation, releasing the Tip key calls nothing.

        Inputs: none.
        Outputs: none.
        """
        self.press("Key_Control")
        self.tip_key_filter.cancel_activation()
        self.assertFalse(self.tip_key_filter.is_activation_on())
        self.release("Key_Control")
        self.assertEqual(self.call_list, ["activate"])

    @covers("LLFR-00150")
    def test_filter_never_consumes_an_event(self) -> None:
        """eventFilter returns False for every key and focus event.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent
        for event in (
                make_key_event("KeyPress", "Key_Control"),
                make_key_event("ShortcutOverride", "Key_Z",
                               "ControlModifier"),
                make_key_event("KeyPress", "Key_Z", "ControlModifier"),
                make_key_event("KeyRelease", "Key_Z", "ControlModifier"),
                make_key_event("KeyRelease", "Key_Control"),
                QEvent(QEvent.Type.WindowDeactivate)):
            self.assertFalse(
                self.tip_key_filter.eventFilter(self.widget, event))


@requires_qt
class TipKeyMainWindowTest(unittest.TestCase):
    """Holding the Tip key in the main window with the real controllers."""

    def setUp(self) -> None:
        """Create a window with a file and two plots, and show it.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from controller.main_controller import MainController
        from model.signal_file import SignalFile
        from view.main_window import MainWindow
        self.main_window = MainWindow()
        self.main_window.resize(1100, 800)
        self.controller = MainController(self.main_window)
        self.controller.start()
        time_array = np.linspace(0.0, 4.0, 41)
        signal_file = SignalFile("memory.csv", {
            "Time": time_array, "speed": time_array * 2.0,
            "force": np.sin(time_array)})
        self.controller.plot_controller.on_file_opened(signal_file, False)
        self.top_panel = self.main_window.top_panel
        self.search_box = self.main_window.signal_list_panel.search_box
        self.main_window.show()
        self.main_window.signal_double_click_handler("speed")
        self.main_window.signal_double_click_handler("force")
        for _ in range(3):
            self.application.processEvents()

    def tearDown(self) -> None:
        """Release any held key and close the window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.tip_key_filter.handle_keyboard_lost()
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def plot_widgets(self) -> list:
        """Return the plot widgets of the current tab.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        panel = self.main_window.plot_panel
        return list(panel.page_dict[panel.current_tab_id()]
                    .plot_widget_list)

    def assert_tool_everywhere(self, tool_str: str) -> None:
        """Check the tool of the buttons, window, controller and plots.

        Inputs:
            tool_str: the expected tool, NO_TOOL_STR for none.
        Outputs: none.
        """
        self.assertEqual(self.top_panel.active_plot_tool(), tool_str)
        for other_tool_str, button in (
                self.top_panel.plot_tool_button_dict.items()):
            self.assertEqual(button.is_active(), other_tool_str == tool_str)
        self.assertEqual(self.main_window.current_plot_tool(), tool_str)
        self.assertEqual(self.controller.plot_controller.plot_tool_str,
                         tool_str)
        for plot_widget in self.plot_widgets():
            self.assertEqual(plot_widget.plot_tool_str, tool_str)

    def press_tip_key(self, receiver=None) -> None:
        """Press the Tip key on a widget (the window by default).

        Inputs:
            receiver: the widget that gets the key event.
        Outputs: none.
        """
        send_key(receiver or self.main_window, "KeyPress", "Key_Control",
                 "ControlModifier")

    def release_tip_key(self, receiver=None) -> None:
        """Release the Tip key on a widget (the window by default).

        Inputs:
            receiver: the widget that gets the key event.
        Outputs: none.
        """
        send_key(receiver or self.main_window, "KeyRelease", "Key_Control")

    @covers("LLFR-00148", "LLFR-00079", "LLFR-00018")
    def test_holding_the_tip_key_activates_tip(self) -> None:
        """Ctrl alone makes Tip the only active tool everywhere.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (ZOOM_TOOL_STR, MARKER_TOOL_STR):
            self.top_panel.plot_tool_button_dict[tool_str].click()
            self.assert_tool_everywhere(tool_str)
            self.press_tip_key()
            self.assert_tool_everywhere(TIP_TOOL_STR)
            self.release_tip_key()
            self.assert_tool_everywhere(NO_TOOL_STR)
        # From no tool at all.
        self.press_tip_key()
        self.assert_tool_everywhere(TIP_TOOL_STR)
        from view.toggle_button import ACTIVE_COLOR_STR, NORMAL_COLOR_STR
        self.assertEqual(
            self.top_panel.tip_button.current_background_color_str(),
            ACTIVE_COLOR_STR)
        self.assertEqual(
            self.top_panel.zoom_button.current_background_color_str(),
            NORMAL_COLOR_STR)

    @covers("LLFR-00149", "LLFR-00148")
    def test_release_leaves_no_tool_whatever_was_active(self) -> None:
        """Releasing Ctrl leaves no tool, even when Tip or Zoom was on.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (ZOOM_TOOL_STR, TIP_TOOL_STR, NO_TOOL_STR):
            if tool_str != NO_TOOL_STR:
                self.top_panel.plot_tool_button_dict[tool_str].click()
            self.assert_tool_everywhere(tool_str)
            self.press_tip_key()
            self.assert_tool_everywhere(TIP_TOOL_STR)
            self.release_tip_key()
            self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00150", "LLFR-00149")
    def test_other_key_ends_tip_and_still_reaches_its_handler(self) -> None:
        """Ctrl+K ends the Tip activation and Ctrl+K still reaches a widget.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QWidget

        received_list = []

        class KeyRecorder(QWidget):
            """Widget that records the key presses it receives."""

            def keyPressEvent(self, event) -> None:
                """Record the key and modifiers of a press.

                Inputs:
                    event: the QKeyEvent.
                Outputs: none.
                """
                received_list.append((int(event.key()), event.modifiers()))

        key_recorder = KeyRecorder(self.main_window)
        self.top_panel.zoom_button.click()
        self.press_tip_key(key_recorder)
        self.assert_tool_everywhere(TIP_TOOL_STR)
        # Ctrl+K: a combination with no shortcut, so the widget gets it.
        # Ctrl+Z is the Undo shortcut (test_ctrl_z_ends_tip_and_runs_undo).
        send_key(key_recorder, "KeyPress", "Key_K", "ControlModifier")
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.assertIn((int(Qt.Key.Key_K.value),
                       Qt.KeyboardModifier.ControlModifier), received_list)
        send_key(key_recorder, "KeyRelease", "Key_K", "ControlModifier")
        self.release_tip_key(key_recorder)
        self.assert_tool_everywhere(NO_TOOL_STR)
        key_recorder.deleteLater()

    @covers("LLFR-00150", "LLFR-00137", "LLFR-00138")
    def test_ctrl_z_ends_tip_and_runs_undo(self) -> None:
        """Ctrl held, then Z: the Tip activation ends and undo runs.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.main_window.activateWindow()
        self.assertTrue(QTest.qWaitForWindowActive(self.main_window))
        self.top_panel.open_file_button.setFocus()
        self.assertEqual(len(self.plot_widgets()), 2)
        self.assertTrue(self.top_panel.undo_button.isEnabled())
        widget = self.main_window.plot_panel
        QTest.keyPress(widget, Qt.Key.Key_Control)
        self.assert_tool_everywhere(TIP_TOOL_STR)
        QTest.keyClick(widget, Qt.Key.Key_Z,
                       Qt.KeyboardModifier.ControlModifier)
        self.application.processEvents()
        # LLFR-00138: the second plot is undone; LLFR-00150: no tool is
        # active, also in the plot rebuilt by the undo.
        self.assertEqual(len(self.plot_widgets()), 1)
        self.assert_tool_everywhere(NO_TOOL_STR)
        QTest.keyRelease(widget, Qt.Key.Key_Control)
        self.assert_tool_everywhere(NO_TOOL_STR)
        # The Tip key alone works again afterwards.
        QTest.keyPress(widget, Qt.Key.Key_Control)
        self.assert_tool_everywhere(TIP_TOOL_STR)
        QTest.keyRelease(widget, Qt.Key.Key_Control)
        self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00157", "LLFR-00148")
    def test_not_applied_while_the_search_box_has_focus(self) -> None:
        """In the search box the Tip key activates nothing, and Ctrl+A
        and typing still work there.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.search_box.setFocus()
        QTest.keyClicks(self.search_box, "spe")
        self.assertEqual(self.search_box.text(), "spe")
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.press_tip_key(self.search_box)
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.release_tip_key(self.search_box)
        self.assert_tool_everywhere(NO_TOOL_STR)
        # A tool chosen before is kept: neither press nor release of the
        # Tip key in the box changes it.
        self.top_panel.zoom_button.click()
        self.press_tip_key(self.search_box)
        self.assert_tool_everywhere(ZOOM_TOOL_STR)
        # Ctrl held, then Ctrl+A: the box selects all.
        QTest.keyClick(self.search_box, Qt.Key.Key_A,
                       Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.search_box.selectedText(), "spe")
        self.release_tip_key(self.search_box)
        self.assert_tool_everywhere(ZOOM_TOOL_STR)
        # Typing goes on normally.
        QTest.keyClicks(self.search_box, "ed")
        self.assertEqual(self.search_box.text(), "ed")

    @covers("LLFR-00079", "LLFR-00149")
    def test_mouse_click_while_held_is_respected(self) -> None:
        """A tool clicked while Ctrl is held stays after the release.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        # Another tool clicked while held: it stays.
        self.press_tip_key()
        QTest.mouseClick(self.top_panel.zoom_button,
                         Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.ControlModifier)
        self.assert_tool_everywhere(ZOOM_TOOL_STR)
        self.release_tip_key()
        self.assert_tool_everywhere(ZOOM_TOOL_STR)
        # The Tip button clicked while held turns Tip off, and the
        # release does not change that choice.
        self.top_panel.zoom_button.click()
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.press_tip_key()
        self.assert_tool_everywhere(TIP_TOOL_STR)
        QTest.mouseClick(self.top_panel.tip_button,
                         Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.ControlModifier)
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.release_tip_key()
        self.assert_tool_everywhere(NO_TOOL_STR)
        # Next hold works normally again.
        self.press_tip_key()
        self.assert_tool_everywhere(TIP_TOOL_STR)
        self.release_tip_key()
        self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00149")
    def test_window_deactivation_ends_tip(self) -> None:
        """Losing the window while Ctrl is held leaves no tool active.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent
        from PyQt6.QtWidgets import QApplication
        self.top_panel.marker_button.click()
        self.press_tip_key()
        self.assert_tool_everywhere(TIP_TOOL_STR)
        QApplication.sendEvent(self.main_window,
                               QEvent(QEvent.Type.WindowDeactivate))
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.release_tip_key()
        self.assert_tool_everywhere(NO_TOOL_STR)


if __name__ == "__main__":
    unittest.main()
