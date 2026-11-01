"""Tests for the X, Y and Z keys (LLFR-00197 to LLFR-00202, LLFR-00207)
and for these keys while typing in a text field (LLFR-00157).

The first class drives the ToolKeyFilter state machine with real Qt key
events and recording callbacks. The other classes run the whole chain:
key and mouse events sent to widgets of a MainWindow with the real
controllers, checking the tool buttons, the window, the controller and
the plots. No modal dialog or menu is ever left open.
"""

import unittest

import numpy as np

from tests.support import covers, get_qt_application, requires_qt
from tests.view.test_shift_key import ShiftKeyWindowTestCase
from tests.view.test_tip_key import make_key_event, send_key

from controller.plot_tools import (
    DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR,
    TIP_TOOL_STR, ZOOM_TOOL_STR)

# The file of ShiftKeyWindowTestCase: 0 s to 4 s.
FULL_RANGE_TUPLE = (0.0, 4.0)
# A zoomed range inside it.
ZOOMED_RANGE_TUPLE = (0.5, 2.5)


@requires_qt
class XyzKeyFilterTest(unittest.TestCase):
    """The state machine of the filter for the X, Y and Z keys."""

    def setUp(self) -> None:
        """Create a filter with recording callbacks and target widgets.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QLineEdit, QWidget
        from view.tip_key_filter import (
            DELTA_X_KEY_I, DELTA_Y_KEY_I, MARKER_KEY_I, RESET_ZOOM_KEY_I,
            TIP_KEY_I, ToolKeyFilter)
        self.call_list = []
        self.tool_key_filter = ToolKeyFilter(
            {TIP_KEY_I: TIP_TOOL_STR, MARKER_KEY_I: MARKER_TOOL_STR,
             DELTA_X_KEY_I: DELTA_X_TOOL_STR,
             DELTA_Y_KEY_I: DELTA_Y_TOOL_STR},
            lambda tool_str: self.call_list.append(tool_str),
            lambda: self.call_list.append("release"), (QLineEdit,), None,
            {RESET_ZOOM_KEY_I: lambda: self.call_list.append("reset")})
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
        """Send a key press (with its ShortcutOverride) to a widget.

        Inputs:
            key_name_str: name of a Qt.Key.
            modifier_name_str: name of a Qt.KeyboardModifier.
            auto_repeat_b: True for an auto-repeated press.
            receiver: the widget that gets the event (plain widget by
                default).
        Outputs: none.
        """
        for event_name_str in ("ShortcutOverride", "KeyPress"):
            send_key(receiver or self.widget, event_name_str, key_name_str,
                     modifier_name_str, auto_repeat_b)

    def release(self, key_name_str: str, auto_repeat_b: bool = False,
                receiver=None) -> None:
        """Send a key release to a widget.

        Inputs:
            key_name_str: name of a Qt.Key.
            auto_repeat_b: True for an auto-repeated release.
            receiver: the widget that gets the event.
        Outputs: none.
        """
        send_key(receiver or self.widget, "KeyRelease", key_name_str,
                 "NoModifier", auto_repeat_b)

    @covers("LLFR-00197", "LLFR-00198", "LLFR-00200", "LLFR-00201")
    def test_x_and_y_alone_activate_and_release_ends(self) -> None:
        """X alone holds Delta X, Y alone holds Delta Y; each release
        ends the activation once, even with repeated deliveries.

        Inputs: none.
        Outputs: none.
        """
        for key_name_str, tool_str in (("Key_X", DELTA_X_TOOL_STR),
                                       ("Key_Y", DELTA_Y_TOOL_STR)):
            self.call_list.clear()
            self.press(key_name_str)
            self.press(key_name_str)
            self.assertEqual(self.call_list, [tool_str])
            self.assertTrue(self.tool_key_filter.is_activation_on())
            self.assertEqual(self.tool_key_filter.active_tool(), tool_str)
            self.release(key_name_str)
            self.release(key_name_str)
            self.assertEqual(self.call_list, [tool_str, "release"])
            self.assertFalse(self.tool_key_filter.is_activation_on())

    @covers("LLFR-00199", "LLFR-00202")
    def test_other_key_ends_the_activation_at_once(self) -> None:
        """Another key while X or Y is held ends the activation; it is
        not renewed until the key is pressed again alone.

        Inputs: none.
        Outputs: none.
        """
        for key_name_str, tool_str in (("Key_X", DELTA_X_TOOL_STR),
                                       ("Key_Y", DELTA_Y_TOOL_STR)):
            for other_key_name_str in ("Key_A", "Key_Shift", "Key_Control",
                                       "Key_Z", "Key_X", "Key_Y"):
                if other_key_name_str == key_name_str:
                    continue
                self.call_list.clear()
                self.press(key_name_str)
                self.press(other_key_name_str)
                self.assertEqual(self.call_list, [tool_str, "release"],
                                 other_key_name_str)
                self.release(other_key_name_str)
                self.assertFalse(self.tool_key_filter.is_activation_on())
                self.release(key_name_str)
                self.assertEqual(self.call_list, [tool_str, "release"])
                self.press(key_name_str)
                self.assertEqual(self.call_list[-1], tool_str)
                self.release(key_name_str)

    @covers("LLFR-00197", "LLFR-00200")
    def test_x_and_y_not_alone_do_not_activate(self) -> None:
        """X or Y with a modifier (Ctrl+X, Shift+Y) or with another key
        held activates nothing.

        Inputs: none.
        Outputs: none.
        """
        for key_name_str in ("Key_X", "Key_Y"):
            for modifier_name_str in ("ControlModifier", "ShiftModifier",
                                      "AltModifier", "MetaModifier"):
                self.press(key_name_str, modifier_name_str)
                self.release(key_name_str)
            self.press("Key_A")
            self.press(key_name_str)
            self.release(key_name_str)
            self.release("Key_A")
        self.assertEqual(self.call_list, [])

    @covers("LLFR-00197", "LLFR-00200", "LLFR-00207")
    def test_auto_repeat_restarts_nothing(self) -> None:
        """Auto-repeated presses and releases of X, Y and Z change
        nothing: the hold goes on, and Z resets only once.

        Inputs: none.
        Outputs: none.
        """
        for key_name_str, tool_str in (("Key_X", DELTA_X_TOOL_STR),
                                       ("Key_Y", DELTA_Y_TOOL_STR)):
            self.call_list.clear()
            self.press(key_name_str)
            for _ in range(3):
                self.release(key_name_str, auto_repeat_b=True)
                self.press(key_name_str, auto_repeat_b=True)
            self.assertEqual(self.call_list, [tool_str])
            self.assertTrue(self.tool_key_filter.is_activation_on())
            self.release(key_name_str)
            self.assertEqual(self.call_list, [tool_str, "release"])
        self.call_list.clear()
        self.press("Key_Z")
        for _ in range(3):
            self.release("Key_Z", auto_repeat_b=True)
            self.press("Key_Z", auto_repeat_b=True)
        self.release("Key_Z")
        self.assertEqual(self.call_list, ["reset"])

    @covers("LLFR-00207")
    def test_z_alone_runs_its_action_once(self) -> None:
        """Z alone runs the reset once per press (ShortcutOverride and
        KeyPress count once); Z with a modifier or another key runs
        nothing, so Ctrl+Z stays Undo.

        Inputs: none.
        Outputs: none.
        """
        self.press("Key_Z")
        self.release("Key_Z")
        self.assertEqual(self.call_list, ["reset"])
        self.press("Key_Z", "KeypadModifier")
        self.release("Key_Z")
        self.assertEqual(self.call_list, ["reset", "reset"])
        self.call_list.clear()
        for modifier_name_str in ("ControlModifier", "ShiftModifier",
                                  "AltModifier", "MetaModifier"):
            self.press("Key_Z", modifier_name_str)
            self.release("Key_Z")
        self.press("Key_A")
        self.press("Key_Z")
        self.release("Key_Z")
        self.release("Key_A")
        self.assertEqual(self.call_list, [])
        self.assertFalse(self.tool_key_filter.is_activation_on())

    @covers("LLFR-00207", "LLFR-00199", "LLFR-00150", "LLFR-00156")
    def test_z_while_a_tool_key_is_held_ends_it_and_does_not_reset(
            self) -> None:
        """Z pressed while X, Y, the Tip key or Shift is held ends that
        hold (other-key rule) and, not being alone, does not reset.

        Inputs: none.
        Outputs: none.
        """
        for key_name_str, modifier_name_str, tool_str in (
                ("Key_X", "NoModifier", DELTA_X_TOOL_STR),
                ("Key_Y", "NoModifier", DELTA_Y_TOOL_STR),
                ("Key_Control", "ControlModifier", TIP_TOOL_STR),
                ("Key_Shift", "ShiftModifier", MARKER_TOOL_STR)):
            self.call_list.clear()
            self.press(key_name_str, modifier_name_str)
            self.press("Key_Z")
            self.assertEqual(self.call_list, [tool_str, "release"])
            self.release("Key_Z")
            self.release(key_name_str)
            self.assertEqual(self.call_list, [tool_str, "release"])

    @covers("LLFR-00157", "LLFR-00197", "LLFR-00200", "LLFR-00207")
    def test_nothing_while_a_text_field_has_focus(self) -> None:
        """X, Y and Z sent to a text field, or with the focus in one, do
        nothing, and the events reach the field.

        Inputs: none.
        Outputs: none.
        """
        for key_name_str in ("Key_X", "Key_Y", "Key_Z"):
            self.press(key_name_str, receiver=self.line_edit)
            self.release(key_name_str, receiver=self.line_edit)
        self.assertEqual(self.call_list, [])
        from unittest import mock
        from PyQt6.QtWidgets import QApplication
        with mock.patch.object(QApplication, "focusWidget",
                               return_value=self.line_edit):
            for key_name_str in ("Key_X", "Key_Y", "Key_Z"):
                self.press(key_name_str)
                self.release(key_name_str)
        self.assertEqual(self.call_list, [])

    @covers("LLFR-00157", "LLFR-00198", "LLFR-00201")
    def test_focus_into_a_text_field_ends_x_and_y(self) -> None:
        """A text field getting the focus while X or Y is held ends the
        activation.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QFocusEvent
        for key_name_str, tool_str in (("Key_X", DELTA_X_TOOL_STR),
                                       ("Key_Y", DELTA_Y_TOOL_STR)):
            self.call_list.clear()
            self.press(key_name_str)
            self.application.sendEvent(self.line_edit, QFocusEvent(
                QEvent.Type.FocusIn, Qt.FocusReason.MouseFocusReason))
            self.assertEqual(self.call_list, [tool_str, "release"])
            self.release(key_name_str, receiver=self.line_edit)
            self.assertEqual(self.call_list, [tool_str, "release"])

    @covers("LLFR-00199", "LLFR-00202", "LLFR-00207")
    def test_filter_never_consumes_an_event(self) -> None:
        """The filter lets every X, Y and Z event through.

        Inputs: none.
        Outputs: none.
        """
        for event_name_str, key_name_str in (
                ("KeyPress", "Key_X"), ("KeyPress", "Key_Z"),
                ("KeyRelease", "Key_Z"), ("KeyRelease", "Key_X"),
                ("ShortcutOverride", "Key_Y"), ("KeyRelease", "Key_Y")):
            self.assertFalse(self.tool_key_filter.eventFilter(
                self.widget, make_key_event(event_name_str, key_name_str)))


class XyzKeyWindowTestCase(ShiftKeyWindowTestCase):
    """Base class: the window of ShiftKeyWindowTestCase, with helpers for
    the X, Y and Z keys and the time ranges of every plot."""

    def press_key(self, key_name_str: str, receiver=None,
                  modifier_name_str: str = "NoModifier",
                  auto_repeat_b: bool = False) -> None:
        """Press a key on a widget (the window by default), as Qt does:
        a ShortcutOverride, then the KeyPress.

        Inputs:
            key_name_str: name of a Qt.Key.
            receiver: the widget that gets the key events.
            modifier_name_str: name of a Qt.KeyboardModifier.
            auto_repeat_b: True for an auto-repeated press.
        Outputs: none.
        """
        for event_name_str in ("ShortcutOverride", "KeyPress"):
            send_key(receiver or self.main_window, event_name_str,
                     key_name_str, modifier_name_str, auto_repeat_b)
        self.application.processEvents()

    def release_key(self, key_name_str: str, receiver=None,
                    auto_repeat_b: bool = False) -> None:
        """Release a key on a widget (the window by default).

        Inputs:
            key_name_str: name of a Qt.Key.
            receiver: the widget that gets the key event.
            auto_repeat_b: True for an auto-repeated release.
        Outputs: none.
        """
        send_key(receiver or self.main_window, "KeyRelease", key_name_str,
                 "NoModifier", auto_repeat_b)
        self.application.processEvents()

    def all_plot_widgets(self) -> list:
        """Return the plot widgets of every tab.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        return list(self.main_window.plot_panel.plot_widget_dict.values())

    def zoom_in(self) -> None:
        """Zoom the first plot to ZOOMED_RANGE_TUPLE; all plots follow.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widgets()[0].zoom_to_range(*ZOOMED_RANGE_TUPLE)
        self.application.processEvents()
        self.assert_every_range(ZOOMED_RANGE_TUPLE)

    def assert_every_range(self, range_tuple: tuple) -> None:
        """Check the time range of every plot in every tab.

        Inputs:
            range_tuple: the expected (start_s, end_s).
        Outputs: none.
        """
        plot_widget_list = self.all_plot_widgets()
        self.assertTrue(plot_widget_list)
        for plot_widget in plot_widget_list:
            start_s, end_s = plot_widget.time_range_tuple()
            self.assertAlmostEqual(start_s, range_tuple[0], places=6)
            self.assertAlmostEqual(end_s, range_tuple[1], places=6)


@requires_qt
class XyKeyMainWindowTest(XyzKeyWindowTestCase):
    """Holding X or Y in the main window with the real controllers."""

    @covers("LLFR-00197", "LLFR-00198", "LLFR-00200", "LLFR-00201",
            "LLFR-00079", "LLFR-00161", "LLFR-00162")
    def test_hold_activates_and_release_leaves_no_tool(self) -> None:
        """X or Y alone makes its delta tool the only active tool,
        whatever tool was active; the release leaves no tool active.

        Inputs: none.
        Outputs: none.
        """
        for key_name_str, tool_str in (("Key_X", DELTA_X_TOOL_STR),
                                       ("Key_Y", DELTA_Y_TOOL_STR)):
            for previous_tool_str in (NO_TOOL_STR, ZOOM_TOOL_STR,
                                      TIP_TOOL_STR, MARKER_TOOL_STR,
                                      DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR):
                self.assert_tool_everywhere(NO_TOOL_STR)
                if previous_tool_str != NO_TOOL_STR:
                    self.top_panel.plot_tool_button_dict[
                        previous_tool_str].click()
                self.assert_tool_everywhere(previous_tool_str)
                self.press_key(key_name_str, self.plot_widgets()[0].canvas)
                self.assert_tool_everywhere(tool_str)
                self.release_key(key_name_str,
                                 self.plot_widgets()[0].canvas)
                self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00199", "LLFR-00202")
    def test_other_key_ends_the_hold(self) -> None:
        """Another key while X or Y is held leaves no tool active, also
        after both keys are released.

        Inputs: none.
        Outputs: none.
        """
        for key_name_str, tool_str in (("Key_X", DELTA_X_TOOL_STR),
                                       ("Key_Y", DELTA_Y_TOOL_STR)):
            other_tool_key_name_str = ("Key_Y" if key_name_str == "Key_X"
                                       else "Key_X")
            for other_key_name_str in ("Key_A", "Key_Shift",
                                       other_tool_key_name_str):
                self.press_key(key_name_str)
                self.assert_tool_everywhere(tool_str)
                self.press_key(other_key_name_str)
                self.assert_tool_everywhere(NO_TOOL_STR)
                self.release_key(other_key_name_str)
                self.release_key(key_name_str)
                self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00197", "LLFR-00200")
    def test_auto_repeat_keeps_the_hold(self) -> None:
        """Auto-repeat events while X or Y is held keep the tool active.

        Inputs: none.
        Outputs: none.
        """
        for key_name_str, tool_str in (("Key_X", DELTA_X_TOOL_STR),
                                       ("Key_Y", DELTA_Y_TOOL_STR)):
            self.press_key(key_name_str)
            for _ in range(3):
                self.release_key(key_name_str, auto_repeat_b=True)
                self.press_key(key_name_str, auto_repeat_b=True)
                self.assert_tool_everywhere(tool_str)
            self.release_key(key_name_str)
            self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00167", "LLFR-00198", "LLFR-00201", "LLFR-00163")
    def test_release_discards_the_pending_first_point(self) -> None:
        """A first point picked while X or Y is held is discarded, with
        its dot, when the key is released or another key is pressed.

        Inputs: none.
        Outputs: none.
        """
        plot_controller = self.controller.plot_controller
        plot_widget = self.plot_widgets()[0]
        plot_id_i = plot_widget.plot_id_i
        for key_name_str, end_key_name_str in (
                ("Key_X", ""), ("Key_Y", ""), ("Key_X", "Key_A"),
                ("Key_Y", "Key_A")):
            self.press_key(key_name_str)
            plot_controller.on_delta_point_pick(plot_id_i, "speed", 1.0,
                                                2.0)
            self.application.processEvents()
            self.assertEqual(plot_controller.pending_delta_tuple[0],
                             plot_id_i)
            self.assertTrue(self.main_window.plot_view(
                plot_id_i).delta_first_point_tuple)
            if end_key_name_str:
                self.press_key(end_key_name_str)
                self.assertEqual(plot_controller.pending_delta_tuple, ())
                self.release_key(end_key_name_str)
            self.release_key(key_name_str)
            self.assert_tool_everywhere(NO_TOOL_STR)
            self.assertEqual(plot_controller.pending_delta_tuple, ())
            self.assertEqual(self.main_window.plot_view(
                plot_id_i).delta_first_point_tuple, ())

    @covers("LLFR-00197", "LLFR-00164", "LLFR-00168")
    def test_measure_while_holding_x(self) -> None:
        """Two picks while X is held place a Delta X marker that stays
        after the release.

        Inputs: none.
        Outputs: none.
        """
        plot_controller = self.controller.plot_controller
        plot_id_i = self.plot_widgets()[0].plot_id_i
        self.press_key("Key_X")
        plot_controller.on_delta_point_pick(plot_id_i, "speed", 1.0, 2.0)
        plot_controller.on_delta_point_pick(plot_id_i, "force", 2.0,
                                            float(np.sin(2.0)))
        self.application.processEvents()
        self.release_key("Key_X")
        self.assertEqual(
            len(self.main_window.plot_view(plot_id_i)
                .delta_marker_id_list()), 1)
        self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00157", "LLFR-00197", "LLFR-00200", "LLFR-00207")
    def test_typing_x_y_z_in_the_search_box(self) -> None:
        """In the search box x, y and z are typed as letters and change
        neither the tool nor the zoom.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        self.activate_window()
        self.zoom_in()
        self.top_panel.plot_tool_button_dict[ZOOM_TOOL_STR].click()
        self.search_box.setFocus()
        self.application.processEvents()
        self.assertIs(self.application.focusWidget(), self.search_box)
        QTest.keyClicks(self.search_box, "xyzZYX")
        self.application.processEvents()
        self.assertEqual(self.search_box.text(), "xyzZYX")
        self.assert_tool_everywhere(ZOOM_TOOL_STR)
        self.assert_every_range(ZOOMED_RANGE_TUPLE)
        # Keys sent to the window while the box has the focus.
        for key_name_str in ("Key_X", "Key_Y", "Key_Z"):
            self.press_key(key_name_str)
            self.assert_tool_everywhere(ZOOM_TOOL_STR)
            self.release_key(key_name_str)
        self.assert_every_range(ZOOMED_RANGE_TUPLE)
        self.assertFalse(self.top_panel.reset_zoom_button.is_active())

    @covers("LLFR-00157", "LLFR-00197", "LLFR-00207")
    def test_typing_in_a_name_dialog(self) -> None:
        """In the line edit of a name dialog x and z are typed and change
        neither the tool nor the zoom.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QInputDialog, QLineEdit
        self.zoom_in()
        name_dialog = QInputDialog(self.main_window)
        name_dialog.setInputMode(QInputDialog.InputMode.TextInput)
        name_dialog.setTextValue("")
        name_dialog.show()
        self.application.processEvents()
        line_edit = name_dialog.findChild(QLineEdit)
        self.assertIsNotNone(line_edit)
        QTest.keyClicks(line_edit, "xz")
        self.assertEqual(name_dialog.textValue(), "xz")
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.assert_every_range(ZOOMED_RANGE_TUPLE)
        name_dialog.reject()
        name_dialog.deleteLater()
        self.application.processEvents()


@requires_qt
class ZKeyMainWindowTest(XyzKeyWindowTestCase):
    """The Z key resets the zoom in the main window."""

    def add_tab_with_plot(self) -> None:
        """Add a second tab with a plot, then show the first tab again.

        Inputs: none.
        Outputs: none.
        """
        plot_controller = self.controller.plot_controller
        first_tab_id_i = self.main_window.current_tab_id()
        plot_controller.on_add_tab()
        self.main_window.signal_double_click_handler("speed")
        self.main_window.set_current_tab(first_tab_id_i)
        self.application.processEvents()
        self.assertEqual(len(self.all_plot_widgets()), 3)

    @covers("LLFR-00207", "LLFR-00115", "LLFR-00070")
    def test_z_resets_every_plot_in_every_tab(self) -> None:
        """Z alone sets every plot of every tab to the file's range, from
        any focus widget that is not a text field, with any plot tool.

        Inputs: none.
        Outputs: none.
        """
        self.add_tab_with_plot()
        for receiver, tool_str in (
                (None, NO_TOOL_STR),
                (self.plot_widgets()[0].canvas, ZOOM_TOOL_STR),
                (self.main_window.signal_list_panel, MARKER_TOOL_STR),
                (self.top_panel, DELTA_Y_TOOL_STR)):
            if tool_str != NO_TOOL_STR:
                self.top_panel.plot_tool_button_dict[tool_str].click()
            self.zoom_in()
            self.press_key("Key_Z", receiver)
            self.assert_every_range(FULL_RANGE_TUPLE)
            self.release_key("Key_Z", receiver)
            # LLFR-00109: the plot tool is not changed by the reset.
            self.assert_tool_everywhere(tool_str)
        # A plot created after the reset shows the whole range too.
        self.main_window.signal_double_click_handler("force")
        self.application.processEvents()
        self.assert_every_range(FULL_RANGE_TUPLE)

    @covers("LLFR-00207", "LLFR-00116", "LLFR-00001", "LLFR-00003")
    def test_z_shows_the_reset_zoom_button_feedback(self) -> None:
        """Z makes the Reset zoom button active for at least 0.3 s, then
        normal again, as a click does.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        button = self.top_panel.reset_zoom_button
        self.zoom_in()
        self.assertFalse(button.is_active())
        self.press_key("Key_Z")
        self.release_key("Key_Z")
        self.assert_every_range(FULL_RANGE_TUPLE)
        self.assertTrue(button.is_active())
        QTest.qWait(150)
        self.assertTrue(button.is_active())
        QTest.qWait(400)
        self.assertFalse(button.is_active())

    @covers("LLFR-00207", "LLFR-00137")
    def test_z_with_a_modifier_or_another_key_does_not_reset(self) -> None:
        """Ctrl+Z, Shift+Z and Z with another key held do not reset; Z
        while X is held ends the Delta X hold and does not reset.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_in()
        for modifier_name_str in ("ControlModifier", "ShiftModifier",
                                  "AltModifier"):
            self.press_key("Key_Z", modifier_name_str=modifier_name_str)
            self.release_key("Key_Z")
            self.assert_every_range(ZOOMED_RANGE_TUPLE)
        self.press_key("Key_A")
        self.press_key("Key_Z")
        self.release_key("Key_Z")
        self.release_key("Key_A")
        self.assert_every_range(ZOOMED_RANGE_TUPLE)
        for key_name_str, modifier_name_str, tool_str in (
                ("Key_X", "NoModifier", DELTA_X_TOOL_STR),
                ("Key_Y", "NoModifier", DELTA_Y_TOOL_STR),
                ("Key_Control", "ControlModifier", TIP_TOOL_STR),
                ("Key_Shift", "ShiftModifier", MARKER_TOOL_STR)):
            self.press_key(key_name_str,
                           modifier_name_str=modifier_name_str)
            self.assert_tool_everywhere(tool_str)
            self.press_key("Key_Z")
            self.assert_tool_everywhere(NO_TOOL_STR)
            self.assert_every_range(ZOOMED_RANGE_TUPLE)
            self.release_key("Key_Z")
            self.release_key(key_name_str)
        self.assertFalse(self.top_panel.reset_zoom_button.is_active())
        # After all keys are released, Z alone resets again.
        self.press_key("Key_Z")
        self.release_key("Key_Z")
        self.assert_every_range(FULL_RANGE_TUPLE)

    @covers("LLFR-00207", "LLFR-00117")
    def test_z_does_nothing_during_a_pan(self) -> None:
        """Z while the wheel button is held for a pan does nothing; after
        the release it resets.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.draw_plots()
        self.zoom_in()
        plot_widget = self.plot_widgets()[0]
        widget_point = plot_widget.data_to_widget_point(1.5, 1.0)
        plot_widget.pan_press_at(QPoint(widget_point))
        self.assertTrue(plot_widget.is_mouse_drag_in_progress())
        self.assertTrue(self.main_window.is_mouse_drag_in_progress())
        self.press_key("Key_Z", plot_widget.canvas)
        self.release_key("Key_Z", plot_widget.canvas)
        self.assert_every_range(ZOOMED_RANGE_TUPLE)
        self.assertFalse(self.top_panel.reset_zoom_button.is_active())
        plot_widget.pan_release_at(QPoint(widget_point))
        self.assertFalse(self.main_window.is_mouse_drag_in_progress())
        self.press_key("Key_Z", plot_widget.canvas)
        self.release_key("Key_Z", plot_widget.canvas)
        self.assert_every_range(FULL_RANGE_TUPLE)

    @covers("LLFR-00207", "LLFR-00086")
    def test_z_does_nothing_during_a_marker_drag(self) -> None:
        """Z while a vertical marker is held with the mouse does nothing;
        after the release it resets.

        Inputs: none.
        Outputs: none.
        """
        self.draw_plots()
        self.top_panel.plot_tool_button_dict[MARKER_TOOL_STR].click()
        plot_widget = self.plot_widgets()[0]
        self.send_mouse(plot_widget, "MouseButtonPress", 1.5,
                        "LeftButton", "LeftButton")
        self.send_mouse(plot_widget, "MouseButtonRelease", 1.5,
                        "LeftButton", "NoButton")
        plot_widget = self.plot_widgets()[0]
        self.assertEqual(plot_widget.marker_count(), 1)
        marker_time_s = plot_widget.marker_data_list[0][2]
        self.zoom_in()
        self.draw_plots()
        plot_widget = self.plot_widgets()[0]
        self.send_mouse(plot_widget, "MouseButtonPress", marker_time_s,
                        "LeftButton", "LeftButton")
        self.send_mouse(plot_widget, "MouseMove", marker_time_s + 0.3,
                        "NoButton", "LeftButton")
        self.assertTrue(self.main_window.is_mouse_drag_in_progress())
        self.press_key("Key_Z", plot_widget.canvas)
        self.release_key("Key_Z", plot_widget.canvas)
        self.assert_every_range(ZOOMED_RANGE_TUPLE)
        self.send_mouse(plot_widget, "MouseButtonRelease",
                        marker_time_s + 0.3, "LeftButton", "NoButton")
        self.assertFalse(self.main_window.is_mouse_drag_in_progress())
        self.press_key("Key_Z")
        self.release_key("Key_Z")
        self.assert_every_range(FULL_RANGE_TUPLE)

    @covers("LLFR-00207", "LLFR-00152")
    def test_drag_query_counts_tip_and_time_span_drags(self) -> None:
        """A pinned tip drag and a time span selection count as mouse
        drags, and Z does nothing during them.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import NO_TIP_INDEX_I
        self.zoom_in()
        plot_widget = self.plot_widgets()[0]
        self.assertFalse(self.main_window.is_mouse_drag_in_progress())
        # LLFR-00152: the state set by tip_press_at.
        plot_widget.drag_tip_index_i = 0
        self.assertTrue(self.main_window.is_mouse_drag_in_progress())
        self.press_key("Key_Z")
        self.release_key("Key_Z")
        self.assert_every_range(ZOOMED_RANGE_TUPLE)
        plot_widget.drag_tip_index_i = NO_TIP_INDEX_I
        # LLFR-00208: the flag of the time span selection.
        plot_widget.time_span_drag_b = True
        self.assertTrue(self.main_window.is_mouse_drag_in_progress())
        self.press_key("Key_Z")
        self.release_key("Key_Z")
        self.assert_every_range(ZOOMED_RANGE_TUPLE)
        plot_widget.time_span_drag_b = False
        self.assertFalse(self.main_window.is_mouse_drag_in_progress())
        self.press_key("Key_Z")
        self.release_key("Key_Z")
        self.assert_every_range(FULL_RANGE_TUPLE)

    @covers("LLFR-00207")
    def test_z_does_nothing_behind_a_modal_dialog(self) -> None:
        """Z sent while a modal dialog is open does not reset the zoom.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QDialog
        self.zoom_in()
        dialog = QDialog(self.main_window)
        dialog.setModal(True)
        dialog.show()
        self.application.processEvents()
        self.press_key("Key_Z", dialog)
        self.release_key("Key_Z", dialog)
        self.assert_every_range(ZOOMED_RANGE_TUPLE)
        dialog.reject()
        dialog.deleteLater()
        self.application.processEvents()
        self.press_key("Key_Z")
        self.release_key("Key_Z")
        self.assert_every_range(FULL_RANGE_TUPLE)


if __name__ == "__main__":
    unittest.main()
