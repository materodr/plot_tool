"""Tests for the Esc key, which switches off the active plot tool
(HLFR-00032, HLFR-00085: LLFR-00370, with LLFR-00157 and the "other key"
rules of the tool keys).

The first class drives the ToolKeyFilter state machine with real Qt key
events and recording callbacks. The second runs the whole chain: key
and mouse events sent to widgets of a MainWindow with the real
controllers. Every menu and dialog opened is closed by the test.
"""

import unittest

from tests.support import covers, get_qt_application, requires_qt
from tests.view.test_tip_key import send_key
from tests.view.test_xyz_keys import XyzKeyWindowTestCase

from controller.plot_tools import (
    AREA_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR, PLOT_TOOL_TUPLE,
    TEXT_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR)


@requires_qt
class EscapeKeyFilterTest(unittest.TestCase):
    """The Esc key in the state machine of the key filter."""

    def setUp(self) -> None:
        """Create a filter with recording callbacks and target widgets.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QLineEdit, QWidget
        from view.tip_key_filter import (
            AREA_KEY_I, ESCAPE_KEY_I, MARKER_KEY_I, TIP_KEY_I, ToolKeyFilter)
        self.call_list = []
        self.tool_key_filter = ToolKeyFilter(
            {TIP_KEY_I: TIP_TOOL_STR, MARKER_KEY_I: MARKER_TOOL_STR,
             AREA_KEY_I: AREA_TOOL_STR},
            lambda tool_str: self.call_list.append(tool_str),
            lambda: self.call_list.append("release"), (QLineEdit,), None,
            {ESCAPE_KEY_I: lambda: self.call_list.append("escape")})
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
              receiver=None, auto_repeat_b: bool = False) -> None:
        """Send a key press (with its ShortcutOverride) to a widget.

        Inputs:
            key_name_str: name of a Qt.Key.
            modifier_name_str: name of a Qt.KeyboardModifier.
            receiver: the widget that gets the event (plain widget by
                default).
            auto_repeat_b: True for an auto-repeated press.
        Outputs: none.
        """
        for event_name_str in ("ShortcutOverride", "KeyPress"):
            send_key(receiver or self.widget, event_name_str, key_name_str,
                     modifier_name_str, auto_repeat_b)

    def release(self, key_name_str: str, receiver=None) -> None:
        """Send a key release to a widget.

        Inputs:
            key_name_str: name of a Qt.Key.
            receiver: the widget that gets the event.
        Outputs: none.
        """
        send_key(receiver or self.widget, "KeyRelease", key_name_str)

    @covers("LLFR-00370")
    def test_escape_alone_runs_its_action_once(self) -> None:
        """Esc alone runs the action once per press (ShortcutOverride and
        KeyPress count once, auto-repeat not at all); Esc with a
        modifier runs nothing.

        Inputs: none.
        Outputs: none.
        """
        self.press("Key_Escape")
        self.press("Key_Escape", auto_repeat_b=True)
        self.release("Key_Escape")
        self.assertEqual(self.call_list, ["escape"])
        self.call_list.clear()
        for modifier_name_str in ("ControlModifier", "ShiftModifier",
                                  "AltModifier", "MetaModifier"):
            self.press("Key_Escape", modifier_name_str)
            self.release("Key_Escape")
        self.assertEqual(self.call_list, [])

    @covers("LLFR-00370", "LLFR-00150", "LLFR-00156", "LLFR-00289")
    def test_escape_while_a_tool_key_is_held_ends_the_hold(self) -> None:
        """Esc pressed while the Tip key, Shift or V is held ends that
        hold as another key does, and runs nothing more, so no plot tool
        is active afterwards.

        Inputs: none.
        Outputs: none.
        """
        for key_name_str, modifier_name_str, tool_str in (
                ("Key_Control", "ControlModifier", TIP_TOOL_STR),
                ("Key_Shift", "ShiftModifier", MARKER_TOOL_STR),
                ("Key_V", "NoModifier", AREA_TOOL_STR)):
            with self.subTest(key=key_name_str):
                self.call_list.clear()
                self.press(key_name_str, modifier_name_str)
                self.press("Key_Escape", modifier_name_str)
                self.assertEqual(self.call_list, [tool_str, "release"])
                self.release("Key_Escape")
                self.release(key_name_str)
                self.assertEqual(self.call_list, [tool_str, "release"])
                self.assertFalse(self.tool_key_filter.is_activation_on())

    @covers("LLFR-00370", "LLFR-00157", "LLFR-00335", "LLFR-00528",
            "LLFR-00529")
    def test_nothing_while_a_text_field_has_focus(self) -> None:
        """Esc sent to a text field, or with the focus in one, runs
        nothing, and the event reaches the field.

        Inputs: none.
        Outputs: none.
        """
        self.press("Key_Escape", receiver=self.line_edit)
        self.release("Key_Escape", receiver=self.line_edit)
        from unittest import mock
        from PyQt6.QtWidgets import QApplication
        with mock.patch.object(QApplication, "focusWidget",
                               return_value=self.line_edit):
            self.press("Key_Escape")
            self.release("Key_Escape")
        self.assertEqual(self.call_list, [])
        from tests.view.test_tip_key import make_key_event
        self.assertFalse(self.tool_key_filter.eventFilter(
            self.widget, make_key_event("KeyPress", "Key_Escape")))


@requires_qt
class EscapeKeyMainWindowTest(XyzKeyWindowTestCase):
    """The Esc key in the main window with the real controllers."""

    def press_escape(self, receiver=None) -> None:
        """Press and release Esc alone on a widget (the window by
        default).

        Inputs:
            receiver: the widget that gets the key events.
        Outputs: none.
        """
        self.press_key("Key_Escape", receiver)
        self.release_key("Key_Escape", receiver)

    @covers("LLFR-00370", "LLFR-00382", "LLFR-00002", "LLFR-00140")
    def test_escape_switches_off_every_tool(self) -> None:
        """With each plot tool active from its button, Esc leaves no tool
        active: every button normal, in the window, the controller and
        every plot, and adds nothing to the undo history.

        Inputs: none.
        Outputs: none.
        """
        undo_history = self.controller.plot_controller.undo_history
        depth_i = undo_history.depth()
        for tool_str in PLOT_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.top_panel.plot_tool_button_dict[tool_str].click()
                self.application.processEvents()
                self.assert_tool_everywhere(tool_str)
                self.press_escape()
                self.assert_tool_everywhere(NO_TOOL_STR)
        self.assertEqual(undo_history.depth(), depth_i)

    @covers("LLFR-00370", "LLFR-00526", "LLFR-00527")
    def test_escape_with_no_tool_does_nothing(self) -> None:
        """With no tool active, Esc changes nothing and shows no box.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.press_escape()
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.assertIsNone(QApplication.activeModalWidget())
        self.assertIsNone(QApplication.activePopupWidget())

    @covers("LLFR-00370", "LLFR-00155", "LLFR-00156", "LLFR-00288",
            "LLFR-00289")
    def test_escape_while_a_tool_key_is_held(self) -> None:
        """Esc while Shift or V holds its tool ends the hold: no tool is
        active, also after the key is released.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.plot_tool_button_dict[ZOOM_TOOL_STR].click()
        self.application.processEvents()
        self.press_shift()
        self.assert_tool_everywhere(MARKER_TOOL_STR)
        self.press_key("Key_Escape", modifier_name_str="ShiftModifier")
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.release_key("Key_Escape")
        self.release_shift()
        self.assert_tool_everywhere(NO_TOOL_STR)
        # LLFR-00287: V holds the vertical area tool (#260, answer 7).
        self.press_key("Key_V")
        self.assert_tool_everywhere(AREA_TOOL_STR)
        self.press_escape()
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.release_key("Key_V")
        self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00370", "LLFR-00157", "LLFR-00529")
    def test_escape_in_the_search_box_keeps_the_tool(self) -> None:
        """Esc in the search box keeps the active tool.

        Inputs: none.
        Outputs: none.
        """
        self.activate_window()
        self.top_panel.plot_tool_button_dict[ZOOM_TOOL_STR].click()
        self.search_box.setFocus()
        self.application.processEvents()
        self.assertIs(self.application.focusWidget(), self.search_box)
        self.press_escape(self.search_box)
        self.assert_tool_everywhere(ZOOM_TOOL_STR)
        # Sent to the window while the box has the focus.
        self.press_escape()
        self.assert_tool_everywhere(ZOOM_TOOL_STR)

    @covers("LLFR-00370", "LLFR-00335", "LLFR-00333", "LLFR-00157",
            "LLFR-00528", "LLFR-00529")
    def test_escape_in_a_text_note_field_cancels_it_only(self) -> None:
        """With the Text tool, Esc in the open text field removes the
        field and keeps the Text tool; a second Esc, out of the field,
        switches the tool off.

        Inputs: none.
        Outputs: none.
        """
        self.activate_window()
        self.top_panel.plot_tool_button_dict[TEXT_TOOL_STR].click()
        self.draw_plots()
        plot_widget = self.plot_widgets()[0]
        plot_widget.text_click_at(plot_widget.data_to_widget_point(
            1.0, sum(plot_widget.axes.get_ylim()) / 2.0))
        self.application.processEvents()
        self.assertTrue(plot_widget.text_note_editor_open_b)
        editor = self.application.focusWidget()
        self.assertIsNotNone(editor)
        self.press_escape(editor)
        self.application.processEvents()
        self.assertFalse(plot_widget.text_note_editor_open_b)
        self.assertEqual(plot_widget.text_note_count(), 0)
        self.assert_tool_everywhere(TEXT_TOOL_STR)
        self.press_escape()
        self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00370", "LLFR-00528", "LLFR-00529")
    def test_escape_in_a_menu_or_a_dialog_keeps_the_tool(self) -> None:
        """Esc sent to an open menu or modal dialog keeps the active
        tool; once they are closed, Esc switches it off.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        from PyQt6.QtWidgets import QApplication, QDialog, QMenu
        self.top_panel.plot_tool_button_dict[ZOOM_TOOL_STR].click()
        self.application.processEvents()
        menu = QMenu(self.main_window)
        menu.addAction("Item")
        menu.popup(self.main_window.mapToGlobal(QPoint(50, 50)))
        self.application.processEvents()
        if QApplication.activePopupWidget() is menu:
            self.press_escape(menu)
            self.assert_tool_everywhere(ZOOM_TOOL_STR)
        menu.close()
        menu.deleteLater()
        self.application.processEvents()
        dialog = QDialog(self.main_window)
        dialog.setModal(True)
        dialog.show()
        self.application.processEvents()
        self.assertIs(QApplication.activeModalWidget(), dialog)
        self.press_escape(dialog)
        self.assert_tool_everywhere(ZOOM_TOOL_STR)
        dialog.reject()
        dialog.deleteLater()
        self.application.processEvents()
        self.press_escape()
        self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00370", "LLFR-00207", "LLFR-00086", "LLFR-00530")
    def test_escape_does_nothing_during_a_drag(self) -> None:
        """Esc while a flag is held with the mouse keeps the Flag tool;
        after the release it switches the tool off.

        Inputs: none.
        Outputs: none.
        """
        plot_controller = self.controller.plot_controller
        plot_controller.workspace.add_marker(1.5)
        plot_controller.show_markers()
        self.top_panel.plot_tool_button_dict[MARKER_TOOL_STR].click()
        self.draw_plots()
        plot_widget = self.plot_widgets()[0]
        self.send_mouse(plot_widget, "MouseButtonPress", 1.5,
                        "LeftButton", "LeftButton")
        self.send_mouse(plot_widget, "MouseMove", 1.8, "NoButton",
                        "LeftButton")
        self.assertTrue(self.main_window.is_mouse_drag_in_progress())
        self.press_escape(plot_widget.canvas)
        self.assert_tool_everywhere(MARKER_TOOL_STR)
        self.assertTrue(self.main_window.is_mouse_drag_in_progress())
        self.send_mouse(plot_widget, "MouseButtonRelease", 1.8,
                        "LeftButton", "NoButton")
        self.assertFalse(self.main_window.is_mouse_drag_in_progress())
        self.assertAlmostEqual(
            plot_controller.workspace.marker_list[0].time_s, 1.8,
            delta=0.03)
        self.press_escape()
        self.assert_tool_everywhere(NO_TOOL_STR)


if __name__ == "__main__":
    unittest.main()
