"""Tests for holding the Shift key (LLFR-00154 to LLFR-00156) and for the
plot tool keys while typing in a text field (LLFR-00157), with signal
drags and the wheel zoom while Shift or Ctrl is held.

The first class drives the ToolKeyFilter state machine with real Qt key
events and recording callbacks. The second class runs the whole chain:
key and mouse events sent to widgets of a MainWindow with the real
controllers, checking the tool buttons, the window, the controller and
the plots. No modal dialog or menu is ever opened.
"""

import unittest
from unittest import mock

import numpy as np

from tests.support import covers, get_qt_application, requires_qt
from tests.view.test_tip_key import make_key_event, send_key

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR)


@requires_qt
class ShiftKeyFilterTest(unittest.TestCase):
    """The state machine of the filter for the Shift key."""

    def setUp(self) -> None:
        """Create a filter with recording callbacks and target widgets.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QLineEdit, QWidget
        from view.tip_key_filter import MARKER_KEY_I, TIP_KEY_I, ToolKeyFilter
        self.call_list = []
        self.tool_key_filter = ToolKeyFilter(
            {TIP_KEY_I: TIP_TOOL_STR, MARKER_KEY_I: MARKER_TOOL_STR},
            lambda tool_str: self.call_list.append(tool_str),
            lambda: self.call_list.append("release"), (QLineEdit,))
        self.application.installEventFilter(self.tool_key_filter)
        self.widget = QWidget()
        self.line_edit = QLineEdit()

    def tearDown(self) -> None:
        """Remove the filter and delete the widgets.

        Inputs: none.
        Outputs: none.
        """
        self.application.removeEventFilter(self.tool_key_filter)
        self.tool_key_filter.deleteLater()
        self.widget.deleteLater()
        self.line_edit.deleteLater()
        self.application.processEvents()

    def press(self, key_name_str: str, modifier_name_str: str = "NoModifier",
              auto_repeat_b: bool = False, receiver=None) -> None:
        """Send a key press to a widget (the plain widget by default).

        Inputs:
            key_name_str: name of a Qt.Key.
            modifier_name_str: name of a Qt.KeyboardModifier.
            auto_repeat_b: True for an auto-repeated press.
            receiver: the widget that gets the event.
        Outputs: none.
        """
        send_key(receiver or self.widget, "KeyPress", key_name_str,
                 modifier_name_str, auto_repeat_b)

    def release(self, key_name_str: str,
                modifier_name_str: str = "NoModifier",
                auto_repeat_b: bool = False, receiver=None) -> None:
        """Send a key release to a widget (the plain widget by default).

        Inputs:
            key_name_str: name of a Qt.Key.
            modifier_name_str: name of a Qt.KeyboardModifier.
            auto_repeat_b: True for an auto-repeated release.
            receiver: the widget that gets the event.
        Outputs: none.
        """
        send_key(receiver or self.widget, "KeyRelease", key_name_str,
                 modifier_name_str, auto_repeat_b)

    @covers("LLFR-00154", "LLFR-00155")
    def test_shift_alone_activates_marker_and_release_ends(self) -> None:
        """Shift alone activates the marker tool once; release ends it.

        Inputs: none.
        Outputs: none.
        """
        self.press("Key_Shift", "ShiftModifier")
        self.assertEqual(self.call_list, [MARKER_TOOL_STR])
        self.assertTrue(self.tool_key_filter.is_activation_on())
        self.assertEqual(self.tool_key_filter.active_tool(), MARKER_TOOL_STR)
        # Repeated deliveries of the same press change nothing.
        send_key(self.widget, "ShortcutOverride", "Key_Shift",
                 "ShiftModifier")
        self.press("Key_Shift", "ShiftModifier")
        self.assertEqual(self.call_list, [MARKER_TOOL_STR])
        self.release("Key_Shift")
        self.assertEqual(self.call_list, [MARKER_TOOL_STR, "release"])
        self.assertFalse(self.tool_key_filter.is_activation_on())
        self.assertEqual(self.tool_key_filter.active_tool(), NO_TOOL_STR)
        self.assertEqual(self.tool_key_filter.held_key_set, set())
        # A repeated release does nothing more; the next hold works.
        self.release("Key_Shift")
        self.press("Key_Shift")
        self.release("Key_Shift")
        self.assertEqual(self.call_list, [MARKER_TOOL_STR, "release",
                                          MARKER_TOOL_STR, "release"])

    @covers("LLFR-00156", "LLFR-00155")
    def test_other_key_ends_the_activation_at_once(self) -> None:
        """Shift then A ends it at once; it is not renewed while held.

        Inputs: none.
        Outputs: none.
        """
        self.press("Key_Shift", "ShiftModifier")
        self.press("Key_A", "ShiftModifier")
        self.assertEqual(self.call_list, [MARKER_TOOL_STR, "release"])
        self.assertFalse(self.tool_key_filter.is_activation_on())
        self.release("Key_A", "ShiftModifier")
        self.assertEqual(self.call_list, [MARKER_TOOL_STR, "release"])
        self.release("Key_Shift")
        self.assertEqual(self.call_list, [MARKER_TOOL_STR, "release"])
        # Alone again: it activates.
        self.press("Key_Shift", "ShiftModifier")
        self.assertEqual(self.call_list,
                         [MARKER_TOOL_STR, "release", MARKER_TOOL_STR])

    @covers("LLFR-00154")
    def test_shift_not_alone_does_not_activate(self) -> None:
        """Shift with another key or modifier already down does nothing.

        Inputs: none.
        Outputs: none.
        """
        self.press("Key_A")
        self.press("Key_Shift", "ShiftModifier")
        self.release("Key_A", "ShiftModifier")
        self.release("Key_Shift")
        self.assertEqual(self.call_list, [])
        # Alt is down (a modifier other than Shift).
        self.press("Key_Shift", "AltModifier")
        self.release("Key_Shift")
        self.assertEqual(self.call_list, [])
        self.press("Key_Shift", "KeypadModifier")
        self.assertEqual(self.call_list, [MARKER_TOOL_STR])

    @covers("LLFR-00154", "LLFR-00155")
    def test_auto_repeat_is_ignored(self) -> None:
        """Auto-repeated Shift or other keys keep the activation.

        Inputs: none.
        Outputs: none.
        """
        self.press("Key_Shift", "ShiftModifier")
        for _ in range(5):
            self.release("Key_Shift", "ShiftModifier", True)
            self.press("Key_Shift", "ShiftModifier", True)
        self.press("Key_A", "ShiftModifier", True)
        self.assertEqual(self.call_list, [MARKER_TOOL_STR])
        self.assertTrue(self.tool_key_filter.is_activation_on())
        self.release("Key_Shift")
        self.assertEqual(self.call_list, [MARKER_TOOL_STR, "release"])

    @covers("LLFR-00155")
    def test_keyboard_loss_ends_the_activation(self) -> None:
        """Window deactivation and focus going to another window end it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QFocusEvent
        from PyQt6.QtWidgets import QApplication
        self.press("Key_Shift", "ShiftModifier")
        QApplication.sendEvent(self.widget,
                               QEvent(QEvent.Type.WindowDeactivate))
        self.assertEqual(self.call_list, [MARKER_TOOL_STR, "release"])
        self.press("Key_Shift", "ShiftModifier")
        QApplication.sendEvent(self.widget, QFocusEvent(
            QEvent.Type.FocusOut, Qt.FocusReason.MouseFocusReason))
        self.assertTrue(self.tool_key_filter.is_activation_on())
        QApplication.sendEvent(self.widget, QFocusEvent(
            QEvent.Type.FocusOut, Qt.FocusReason.ActiveWindowFocusReason))
        self.assertEqual(self.call_list, [MARKER_TOOL_STR, "release",
                                          MARKER_TOOL_STR, "release"])
        self.assertEqual(self.tool_key_filter.held_key_set, set())

    @covers("LLFR-00150", "LLFR-00156", "LLFR-00148", "LLFR-00154")
    def test_tip_key_and_shift_key_together_leave_no_tool(self) -> None:
        """Each tool key is "another key" for the other: no tool stays.

        Inputs: none.
        Outputs: none.
        """
        # Tip key first, then Shift: Tip ends, Shift activates nothing.
        self.press("Key_Control", "ControlModifier")
        self.press("Key_Shift", "ControlModifier")
        self.assertEqual(self.call_list, [TIP_TOOL_STR, "release"])
        self.release("Key_Shift", "ControlModifier")
        self.release("Key_Control")
        self.assertEqual(self.call_list, [TIP_TOOL_STR, "release"])
        # Shift first, then the Tip key: Shift ends, Tip activates
        # nothing; releasing in the other order changes nothing either.
        self.call_list.clear()
        self.press("Key_Shift", "ShiftModifier")
        self.press("Key_Control", "ShiftModifier")
        self.assertEqual(self.call_list, [MARKER_TOOL_STR, "release"])
        self.release("Key_Shift", "ControlModifier")
        # The Tip key is still held, so it stays known.
        self.assertEqual(self.tool_key_filter.held_key_set,
                         {int(make_key_event(
                             "KeyPress", "Key_Control").key())})
        self.release("Key_Control")
        self.assertEqual(self.call_list, [MARKER_TOOL_STR, "release"])
        self.assertEqual(self.tool_key_filter.held_key_set, set())
        # Each key alone works again afterwards.
        self.call_list.clear()
        self.press("Key_Control", "ControlModifier")
        self.release("Key_Control")
        self.press("Key_Shift", "ShiftModifier")
        self.release("Key_Shift")
        self.assertEqual(self.call_list, [TIP_TOOL_STR, "release",
                                          MARKER_TOOL_STR, "release"])

    @covers("LLFR-00157", "LLFR-00154", "LLFR-00148")
    def test_no_activation_while_a_text_field_has_focus(self) -> None:
        """Tool keys sent to a text field, or while one has the focus,
        activate nothing; the held keys are still tracked.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        from view import tip_key_filter as tip_key_filter_module
        for key_name_str, modifier_name_str in (
                ("Key_Shift", "ShiftModifier"),
                ("Key_Control", "ControlModifier")):
            self.press(key_name_str, modifier_name_str,
                       receiver=self.line_edit)
            self.assertEqual(self.call_list, [])
            self.release(key_name_str, receiver=self.line_edit)
        self.assertEqual(self.tool_key_filter.held_key_set, set())
        # The key goes to another widget, but the focus is in a text
        # field (as the application reports it).
        with mock.patch.object(tip_key_filter_module.QApplication,
                               "focusWidget", return_value=self.line_edit):
            self.press("Key_Shift", "ShiftModifier")
            self.assertEqual(self.call_list, [])
            self.release("Key_Shift")
        self.assertIsNot(QApplication.focusWidget(), self.line_edit)
        self.press("Key_Shift", "ShiftModifier")
        self.assertEqual(self.call_list, [MARKER_TOOL_STR])

    @covers("LLFR-00157", "LLFR-00155", "LLFR-00149")
    def test_focus_into_a_text_field_ends_the_activation(self) -> None:
        """A text field getting the focus while a tool key is held ends
        the activation; another widget getting it does not.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QFocusEvent
        from PyQt6.QtWidgets import QApplication
        for key_name_str, modifier_name_str, tool_str in (
                ("Key_Shift", "ShiftModifier", MARKER_TOOL_STR),
                ("Key_Control", "ControlModifier", TIP_TOOL_STR)):
            self.call_list.clear()
            self.press(key_name_str, modifier_name_str)
            QApplication.sendEvent(self.widget, QFocusEvent(
                QEvent.Type.FocusIn, Qt.FocusReason.MouseFocusReason))
            self.assertEqual(self.call_list, [tool_str])
            QApplication.sendEvent(self.line_edit, QFocusEvent(
                QEvent.Type.FocusIn, Qt.FocusReason.TabFocusReason))
            self.assertEqual(self.call_list, [tool_str, "release"])
            self.assertFalse(self.tool_key_filter.is_activation_on())
            # The later release changes nothing.
            self.release(key_name_str)
            self.assertEqual(self.call_list, [tool_str, "release"])

    @covers("LLFR-00156", "LLFR-00157")
    def test_filter_never_consumes_an_event(self) -> None:
        """eventFilter returns False for Shift, typed and focus events.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QFocusEvent
        for watched, event in (
                (self.widget, make_key_event("KeyPress", "Key_Shift",
                                             "ShiftModifier")),
                (self.widget, make_key_event("KeyPress", "Key_A",
                                             "ShiftModifier")),
                (self.line_edit, make_key_event("KeyPress", "Key_Shift",
                                                "ShiftModifier")),
                (self.line_edit, QFocusEvent(
                    QEvent.Type.FocusIn, Qt.FocusReason.TabFocusReason)),
                (self.widget, make_key_event("KeyRelease", "Key_Shift"))):
            self.assertFalse(
                self.tool_key_filter.eventFilter(watched, event))


@requires_qt
class ShiftKeyWindowTestCase(unittest.TestCase):
    """Base class: a shown main window with the real controllers, a file
    and two plots, and helpers for keys and mouse events."""

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
        # LLFR-00011: the signal list shows the names, for the drags.
        self.controller.signal_list_controller.on_file_opened(
            signal_file, False)
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
        self.main_window.tool_key_filter.handle_keyboard_lost()
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

    def press_shift(self, receiver=None) -> None:
        """Press Shift on a widget (the window by default).

        Inputs:
            receiver: the widget that gets the key event.
        Outputs: none.
        """
        send_key(receiver or self.main_window, "KeyPress", "Key_Shift",
                 "ShiftModifier")

    def release_shift(self, receiver=None) -> None:
        """Release Shift on a widget (the window by default).

        Inputs:
            receiver: the widget that gets the key event.
        Outputs: none.
        """
        send_key(receiver or self.main_window, "KeyRelease", "Key_Shift")

    def activate_window(self) -> None:
        """Make the window active, so that focus changes are delivered.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        self.main_window.activateWindow()
        self.assertTrue(QTest.qWaitForWindowActive(self.main_window))

    def send_mouse(self, plot_widget, event_type_name_str: str,
                   time_s: float, button_name_str: str,
                   buttons_name_str: str) -> None:
        """Send a Qt mouse event with Shift down to a plot's canvas.

        Inputs:
            plot_widget: the PlotWidget.
            event_type_name_str: "MouseButtonPress", "MouseMove" or
                "MouseButtonRelease".
            time_s: the time of the point, in the middle of the y range.
            button_name_str: name of the Qt.MouseButton of the event.
            buttons_name_str: name of the Qt.MouseButton held after it.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        bottom_f, top_f = plot_widget.axes.get_ylim()
        canvas = plot_widget.canvas
        widget_point = plot_widget.data_to_widget_point(
            time_s, (bottom_f + top_f) / 2.0)
        local_point = QPointF(canvas.mapFrom(plot_widget, widget_point))
        mouse_event = QMouseEvent(
            getattr(QEvent.Type, event_type_name_str), local_point,
            QPointF(canvas.mapToGlobal(local_point)),
            getattr(Qt.MouseButton, button_name_str),
            getattr(Qt.MouseButton, buttons_name_str),
            Qt.KeyboardModifier.ShiftModifier)
        self.application.sendEvent(canvas, mouse_event)
        self.application.processEvents()

    def draw_plots(self) -> None:
        """Draw every canvas so that pixel positions are final.

        Inputs: none.
        Outputs: none.
        """
        self.application.processEvents()
        for plot_widget in self.plot_widgets():
            plot_widget.canvas.draw()


@requires_qt
class ShiftKeyMainWindowTest(ShiftKeyWindowTestCase):
    """Holding Shift in the main window with the real controllers."""

    @covers("LLFR-00154", "LLFR-00079", "LLFR-00080")
    def test_holding_shift_activates_the_marker_tool(self) -> None:
        """Shift alone makes Vertical marker the only active tool.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (ZOOM_TOOL_STR, TIP_TOOL_STR):
            self.top_panel.plot_tool_button_dict[tool_str].click()
            self.assert_tool_everywhere(tool_str)
            self.press_shift()
            self.assert_tool_everywhere(MARKER_TOOL_STR)
            self.release_shift()
            self.assert_tool_everywhere(NO_TOOL_STR)
        self.press_shift()
        self.assert_tool_everywhere(MARKER_TOOL_STR)
        from view.toggle_button import ACTIVE_COLOR_STR, NORMAL_COLOR_STR
        self.assertEqual(
            self.top_panel.marker_button.current_background_color_str(),
            ACTIVE_COLOR_STR)
        self.assertEqual(
            self.top_panel.tip_button.current_background_color_str(),
            NORMAL_COLOR_STR)

    @covers("LLFR-00155", "LLFR-00154")
    def test_release_leaves_no_tool_whatever_was_active(self) -> None:
        """Releasing Shift leaves no tool, even when Marker or Zoom was on.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (ZOOM_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR):
            if tool_str != NO_TOOL_STR:
                self.top_panel.plot_tool_button_dict[tool_str].click()
            self.assert_tool_everywhere(tool_str)
            self.press_shift()
            self.assert_tool_everywhere(MARKER_TOOL_STR)
            self.release_shift()
            self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00156", "LLFR-00155")
    def test_other_key_ends_marker_and_still_reaches_its_widget(
            self) -> None:
        """Shift+A ends the marker activation and A still reaches a widget.

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
        self.press_shift(key_recorder)
        self.assert_tool_everywhere(MARKER_TOOL_STR)
        send_key(key_recorder, "KeyPress", "Key_A", "ShiftModifier")
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.assertIn((int(Qt.Key.Key_A.value),
                       Qt.KeyboardModifier.ShiftModifier), received_list)
        send_key(key_recorder, "KeyRelease", "Key_A", "ShiftModifier")
        self.release_shift(key_recorder)
        self.assert_tool_everywhere(NO_TOOL_STR)
        key_recorder.deleteLater()

    @covers("LLFR-00150", "LLFR-00156", "LLFR-00079")
    def test_tip_key_and_shift_together_leave_no_tool(self) -> None:
        """Ctrl then Shift, or Shift then Ctrl: no tool is active.

        Inputs: none.
        Outputs: none.
        """
        send_key(self.main_window, "KeyPress", "Key_Control",
                 "ControlModifier")
        self.assert_tool_everywhere(TIP_TOOL_STR)
        send_key(self.main_window, "KeyPress", "Key_Shift",
                 "ControlModifier")
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.release_shift()
        send_key(self.main_window, "KeyRelease", "Key_Control")
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.press_shift()
        self.assert_tool_everywhere(MARKER_TOOL_STR)
        send_key(self.main_window, "KeyPress", "Key_Control",
                 "ShiftModifier")
        self.assert_tool_everywhere(NO_TOOL_STR)
        send_key(self.main_window, "KeyRelease", "Key_Control")
        self.release_shift()
        self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00157", "LLFR-00154", "LLFR-00148")
    def test_search_box_typing_activates_no_tool(self) -> None:
        """In the search box Shift and Ctrl alone activate nothing, and
        Shift+A types "A".

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.activate_window()
        self.search_box.setFocus()
        self.application.processEvents()
        self.assertIs(self.application.focusWidget(), self.search_box)
        for tool_str in (NO_TOOL_STR, ZOOM_TOOL_STR):
            if tool_str != NO_TOOL_STR:
                self.top_panel.plot_tool_button_dict[tool_str].click()
                self.search_box.setFocus()
            self.search_box.clear()
            QTest.keyPress(self.search_box, Qt.Key.Key_Shift,
                           Qt.KeyboardModifier.ShiftModifier)
            self.assert_tool_everywhere(tool_str)
            QTest.keyClicks(self.search_box, "A",
                            Qt.KeyboardModifier.ShiftModifier)
            QTest.keyRelease(self.search_box, Qt.Key.Key_Shift)
            self.assertEqual(self.search_box.text(), "A")
            self.assert_tool_everywhere(tool_str)
            QTest.keyPress(self.search_box, Qt.Key.Key_Control,
                           Qt.KeyboardModifier.ControlModifier)
            self.assert_tool_everywhere(tool_str)
            QTest.keyRelease(self.search_box, Qt.Key.Key_Control)
            self.assert_tool_everywhere(tool_str)
        # Keys sent to the window while the box has the focus.
        self.press_shift()
        self.assert_tool_everywhere(ZOOM_TOOL_STR)
        self.release_shift()
        self.assert_tool_everywhere(ZOOM_TOOL_STR)

    @covers("LLFR-00157", "LLFR-00155")
    def test_focus_moving_into_the_search_box_ends_the_tool(self) -> None:
        """Shift held on a plot, then the search box focused: no tool.

        Inputs: none.
        Outputs: none.
        """
        self.activate_window()
        canvas = self.plot_widgets()[0].canvas
        canvas.setFocus()
        self.application.processEvents()
        self.press_shift(canvas)
        self.assert_tool_everywhere(MARKER_TOOL_STR)
        self.search_box.setFocus()
        self.application.processEvents()
        self.assertIs(self.application.focusWidget(), self.search_box)
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.release_shift(self.search_box)
        self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00157", "LLFR-00154", "LLFR-00148")
    def test_name_dialog_line_edit_activates_no_tool(self) -> None:
        """In the line edit of a name dialog the tool keys do nothing.

        The dialog is the QInputDialog used for tab and marker names,
        shown without exec so that no modal loop runs.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QInputDialog, QLineEdit
        name_dialog = QInputDialog(self.main_window)
        name_dialog.setInputMode(QInputDialog.InputMode.TextInput)
        name_dialog.setTextValue("")
        name_dialog.show()
        self.application.processEvents()
        line_edit = name_dialog.findChild(QLineEdit)
        self.assertIsNotNone(line_edit)
        QTest.keyPress(line_edit, Qt.Key.Key_Shift,
                       Qt.KeyboardModifier.ShiftModifier)
        self.assert_tool_everywhere(NO_TOOL_STR)
        QTest.keyClicks(line_edit, "AB", Qt.KeyboardModifier.ShiftModifier)
        QTest.keyRelease(line_edit, Qt.Key.Key_Shift)
        QTest.keyPress(line_edit, Qt.Key.Key_Control,
                       Qt.KeyboardModifier.ControlModifier)
        self.assert_tool_everywhere(NO_TOOL_STR)
        QTest.keyRelease(line_edit, Qt.Key.Key_Control)
        self.assertEqual(name_dialog.textValue(), "AB")
        self.assert_tool_everywhere(NO_TOOL_STR)
        name_dialog.reject()
        name_dialog.deleteLater()

    @covers("LLFR-00154", "LLFR-00081", "LLFR-00155")
    def test_shift_click_places_a_marker(self) -> None:
        """Shift held, then a left click with Shift on a plot places a
        marker at the clicked time; the marker stays after the release.

        Inputs: none.
        Outputs: none.
        """
        self.draw_plots()
        plot_widget = self.plot_widgets()[0]
        self.press_shift(plot_widget.canvas)
        self.assert_tool_everywhere(MARKER_TOOL_STR)
        self.send_mouse(plot_widget, "MouseButtonPress", 1.5,
                        "LeftButton", "LeftButton")
        self.send_mouse(plot_widget, "MouseButtonRelease", 1.5,
                        "LeftButton", "NoButton")
        plot_widget = self.plot_widgets()[0]
        self.assertEqual(plot_widget.marker_count(), 1)
        marker_time_s = plot_widget.marker_data_list[0][2]
        self.assertAlmostEqual(marker_time_s, 1.5, delta=0.05)
        self.assert_tool_everywhere(MARKER_TOOL_STR)
        self.release_shift(plot_widget.canvas)
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.assertEqual(self.plot_widgets()[0].marker_count(), 1)

    @covers("LLFR-00154", "LLFR-00086")
    def test_shift_drag_moves_a_marker(self) -> None:
        """Shift held, a marker is dragged with Shift down to a new time.

        Inputs: none.
        Outputs: none.
        """
        self.draw_plots()
        plot_widget = self.plot_widgets()[0]
        self.press_shift(plot_widget.canvas)
        self.send_mouse(plot_widget, "MouseButtonPress", 1.0,
                        "LeftButton", "LeftButton")
        self.send_mouse(plot_widget, "MouseButtonRelease", 1.0,
                        "LeftButton", "NoButton")
        plot_widget = self.plot_widgets()[0]
        self.assertEqual(plot_widget.marker_count(), 1)
        self.draw_plots()
        start_s = plot_widget.marker_data_list[0][2]
        self.send_mouse(plot_widget, "MouseButtonPress", start_s,
                        "LeftButton", "LeftButton")
        for time_s in (1.5, 2.0, 2.5):
            self.send_mouse(plot_widget, "MouseMove", time_s,
                            "NoButton", "LeftButton")
        self.send_mouse(plot_widget, "MouseButtonRelease", 2.5,
                        "LeftButton", "NoButton")
        plot_widget = self.plot_widgets()[0]
        self.assertEqual(plot_widget.marker_count(), 1)
        self.assertAlmostEqual(plot_widget.marker_data_list[0][2], 2.5,
                               delta=0.05)
        self.assert_tool_everywhere(MARKER_TOOL_STR)
        self.release_shift(plot_widget.canvas)
        self.assert_tool_everywhere(NO_TOOL_STR)


@requires_qt
class ShiftDragDropTest(ShiftKeyWindowTestCase):
    """Dragging a signal with Shift or Ctrl held copies it to the plot."""

    def send_drag_to_plot(self, plot_widget, mime_data, possible_actions,
                          modifier_name_str: str):
        """Send drag-enter, drag-move and drop events to a plot widget.

        Inputs:
            plot_widget: the PlotWidget the signal is dropped on.
            mime_data: the QMimeData of the drag.
            possible_actions: the Qt.DropAction flags of the drag.
            modifier_name_str: name of the Qt.KeyboardModifier held.
        Outputs: the drop action the plot chose, or IgnoreAction when it
            did not accept the drop.
        """
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
        center_point = plot_widget.rect().center()
        modifiers = getattr(Qt.KeyboardModifier, modifier_name_str)
        no_button = Qt.MouseButton.NoButton
        # Qt itself proposes the action from the modifiers (a move with
        # Shift on Linux and Windows).
        enter_event = QDragEnterEvent(center_point, possible_actions,
                                      mime_data, no_button, modifiers)
        self.application.sendEvent(plot_widget, enter_event)
        self.assertTrue(enter_event.isAccepted())
        self.assertEqual(enter_event.dropAction(),
                         Qt.DropAction.CopyAction)
        move_event = QDragMoveEvent(center_point, possible_actions,
                                    mime_data, no_button, modifiers)
        self.application.sendEvent(plot_widget, move_event)
        self.assertTrue(move_event.isAccepted())
        self.assertEqual(move_event.dropAction(), Qt.DropAction.CopyAction)
        drop_event = QDropEvent(QPointF(center_point), possible_actions,
                                mime_data, no_button, modifiers)
        self.application.sendEvent(plot_widget, drop_event)
        self.application.processEvents()
        if not drop_event.isAccepted():
            return Qt.DropAction.IgnoreAction
        return drop_event.dropAction()

    def signal_list_names(self) -> list:
        """Return the names shown in the signal list, in order.

        Inputs: none.
        Outputs: a list of str.
        """
        list_widget = self.main_window.signal_list_panel.signal_list_widget
        return [list_widget.item(row_i).text()
                for row_i in range(list_widget.count())]

    def drag_from_list(self, signal_name_str: str,
                       modifier_name_str: str) -> list:
        """Drag a signal from the list onto the first plot.

        Qt's own drag loop (QAbstractItemView.startDrag) cannot run in a
        test, so it is replaced by a stand-in that does what Qt does: it
        drags the list's data with the actions the list offers, and,
        when the drop ends as a move, removes the dragged row.

        Inputs:
            signal_name_str: the signal to drag.
            modifier_name_str: name of the Qt.KeyboardModifier held.
        Outputs: the list of action flags the list offered to Qt.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QListWidget
        list_widget = self.main_window.signal_list_panel.signal_list_widget
        item = list_widget.findItems(signal_name_str,
                                     Qt.MatchFlag.MatchExactly)[0]
        list_widget.setCurrentItem(item)
        plot_widget = self.plot_widgets()[0]
        offered_list = []
        test_case = self

        def qt_start_drag(widget, supported_actions) -> None:
            """Stand-in for Qt's startDrag (see drag_from_list).

            Inputs:
                widget: the list widget.
                supported_actions: the Qt.DropAction flags offered.
            Outputs: none.
            """
            offered_list.append(supported_actions)
            mime_data = widget.mimeData(widget.selectedItems())
            result_action = test_case.send_drag_to_plot(
                plot_widget, mime_data, supported_actions,
                modifier_name_str)
            if result_action == Qt.DropAction.MoveAction:
                widget.takeItem(widget.currentRow())

        with mock.patch.object(QListWidget, "startDrag", qt_start_drag):
            list_widget.startDrag(Qt.DropAction.CopyAction
                                  | Qt.DropAction.MoveAction)
        return offered_list

    @covers("LLFR-00021", "LLFR-00154", "LLFR-00148")
    def test_drag_with_shift_or_ctrl_copies_the_signal(self) -> None:
        """With Shift, Ctrl or nothing held, a dragged signal is drawn in
        the plot and the signal list keeps every name.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        name_list = self.signal_list_names()
        self.assertEqual(name_list, ["Time", "speed", "force"])
        for signal_name_str, modifier_name_str in (
                ("force", "ShiftModifier"), ("Time", "ControlModifier"),
                ("speed", "NoModifier")):
            offered_list = self.drag_from_list(signal_name_str,
                                               modifier_name_str)
            self.assertEqual(offered_list, [Qt.DropAction.CopyAction])
            curve_name_list = [curve_tuple[0] for curve_tuple in
                               self.plot_widgets()[0].curve_data_list]
            self.assertIn(signal_name_str, curve_name_list)
            self.assertEqual(self.signal_list_names(), name_list)

    @covers("LLFR-00021", "LLFR-00154")
    def test_plot_turns_a_proposed_move_into_a_copy(self) -> None:
        """A drag that allows a move, with Shift or Ctrl held, still ends
        as a copy on the plot.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        list_widget = self.main_window.signal_list_panel.signal_list_widget
        for row_i, modifier_name_str in ((2, "ShiftModifier"),
                                         (0, "ControlModifier")):
            mime_data = list_widget.mimeData([list_widget.item(row_i)])
            plot_widget = self.plot_widgets()[0]
            self.assertEqual(self.send_drag_to_plot(
                plot_widget, mime_data,
                Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
                modifier_name_str), Qt.DropAction.CopyAction)
        curve_name_list = [curve_tuple[0] for curve_tuple in
                           self.plot_widgets()[0].curve_data_list]
        self.assertIn("force", curve_name_list)
        self.assertIn("Time", curve_name_list)
        self.assertEqual(self.signal_list_names(),
                         ["Time", "speed", "force"])

    @covers("LLFR-00021")
    def test_list_offers_only_a_copy(self) -> None:
        """The signal list's drags and drops are copies only.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        list_widget = self.main_window.signal_list_panel.signal_list_widget
        self.assertEqual(list_widget.defaultDropAction(),
                         Qt.DropAction.CopyAction)
        self.assertEqual(list_widget.supportedDropActions(),
                         Qt.DropAction.CopyAction)


@requires_qt
class ShiftWheelTest(ShiftKeyWindowTestCase):
    """The wheel still zooms while Shift is held (macOS sends it sideways)."""

    def send_wheel(self, angle_x_i: int, angle_y_i: int,
                   modifier_name_str: str) -> tuple:
        """Send a Qt wheel event to the first plot's canvas.

        Inputs:
            angle_x_i: horizontal rotation, in eighths of a degree.
            angle_y_i: vertical rotation, in eighths of a degree.
            modifier_name_str: name of the Qt.KeyboardModifier held.
        Outputs: a tuple (width before, width after) of the time range,
            in seconds.
        """
        from PyQt6.QtCore import QPoint, QPointF, Qt
        from PyQt6.QtGui import QWheelEvent
        self.draw_plots()
        plot_widget = self.plot_widgets()[0]
        start_s, end_s = plot_widget.time_range_tuple()
        canvas = plot_widget.canvas
        local_point = QPointF(canvas.rect().center())
        wheel_event = QWheelEvent(
            local_point, QPointF(canvas.mapToGlobal(local_point)),
            QPoint(0, 0), QPoint(angle_x_i, angle_y_i),
            Qt.MouseButton.NoButton,
            getattr(Qt.KeyboardModifier, modifier_name_str),
            Qt.ScrollPhase.NoScrollPhase, False)
        self.application.sendEvent(canvas, wheel_event)
        self.application.processEvents()
        new_start_s, new_end_s = self.plot_widgets()[0].time_range_tuple()
        return (end_s - start_s, new_end_s - new_start_s)

    @covers("LLFR-00074", "LLFR-00113", "LLFR-00154", "LLFR-00108")
    def test_sideways_shift_wheel_zooms(self) -> None:
        """Shift+wheel reported sideways zooms like the vertical wheel,
        with the marker tool held by Shift.

        Inputs: none.
        Outputs: none.
        """
        self.press_shift()
        self.assert_tool_everywhere(MARKER_TOOL_STR)
        width_before_s, width_after_s = self.send_wheel(
            120, 0, "ShiftModifier")
        self.assertAlmostEqual(width_after_s, width_before_s * 0.95)
        width_before_s, width_after_s = self.send_wheel(
            -120, 0, "ShiftModifier")
        self.assertAlmostEqual(width_after_s, width_before_s / 0.95)
        # The vertical wheel with Shift keeps working too.
        width_before_s, width_after_s = self.send_wheel(
            0, 120, "ShiftModifier")
        self.assertAlmostEqual(width_after_s, width_before_s * 0.95)
        self.release_shift()
        self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00074", "LLFR-00075")
    def test_sideways_wheel_without_shift_does_not_zoom(self) -> None:
        """A sideways wheel without Shift (a tilt or a touchpad swipe) does
        not zoom.

        Inputs: none.
        Outputs: none.
        """
        width_before_s, width_after_s = self.send_wheel(
            120, 0, "NoModifier")
        self.assertAlmostEqual(width_after_s, width_before_s)


if __name__ == "__main__":
    unittest.main()
