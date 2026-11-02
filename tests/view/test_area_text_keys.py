"""Tests for the A and T keys (LLFR-00287 to LLFR-00289, LLFR-00321 to
LLFR-00323) and for these keys while typing in a text field
(LLFR-00157).

The keys are sent to a MainWindow with the real controllers and the
real ToolKeyFilter, so the tests also check that the window gives the
filter the A and T keys. The Area and Text tools themselves do nothing
on the plots yet (issues #129 and #130); activating them must not
change the plots or raise. No modal dialog is ever left open.
"""

import unittest

from tests.support import covers, requires_qt
from tests.view.test_xyz_keys import (
    FULL_RANGE_TUPLE, ZOOMED_RANGE_TUPLE, XyzKeyWindowTestCase)

from controller.plot_tools import (
    AREA_TOOL_STR, DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR, MARKER_TOOL_STR,
    NO_TOOL_STR, TEXT_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR)

# LLFR-00287, LLFR-00321: each key and the tool it holds.
KEY_TOOL_TUPLE = (("Key_A", AREA_TOOL_STR), ("Key_T", TEXT_TOOL_STR))
# LLFR-00288, LLFR-00322: every state the tool can be in before a press.
PREVIOUS_TOOL_TUPLE = (NO_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR,
                       MARKER_TOOL_STR, DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR,
                       AREA_TOOL_STR, TEXT_TOOL_STR)


@requires_qt
class AreaTextKeyFilterTest(unittest.TestCase):
    """The key constants and the filter of the main window."""

    @covers("LLFR-00287", "LLFR-00321")
    def test_keys_are_the_letters_a_and_t(self) -> None:
        """AREA_KEY_I is Qt's A key and TEXT_KEY_I is Qt's T key.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from view import tip_key_filter
        self.assertEqual(tip_key_filter.AREA_KEY_I,
                         int(Qt.Key.Key_A.value))
        self.assertEqual(tip_key_filter.TEXT_KEY_I,
                         int(Qt.Key.Key_T.value))
        # Letters set no modifier of their own.
        self.assertNotIn(tip_key_filter.AREA_KEY_I,
                         tip_key_filter.OWN_MODIFIER_DICT)
        self.assertNotIn(tip_key_filter.TEXT_KEY_I,
                         tip_key_filter.OWN_MODIFIER_DICT)


@requires_qt
class AreaTextKeyMainWindowTest(XyzKeyWindowTestCase):
    """Holding A or T in the main window with the real controllers."""

    def select_tool(self, tool_str: str) -> None:
        """Make a tool active with a click on its button.

        Inputs:
            tool_str: the tool, NO_TOOL_STR for none.
        Outputs: none.
        """
        if tool_str != NO_TOOL_STR:
            self.top_panel.plot_tool_button_dict[tool_str].click()
            self.application.processEvents()
        self.assert_tool_everywhere(tool_str)

    @covers("LLFR-00287", "LLFR-00288", "LLFR-00321", "LLFR-00322",
            "LLFR-00079", "LLFR-00286", "LLFR-00320")
    def test_hold_activates_and_release_leaves_no_tool(self) -> None:
        """A or T alone makes its tool the only active tool, whatever
        tool was active; the release leaves no tool active.

        Inputs: none.
        Outputs: none.
        """
        canvas = self.plot_widgets()[0].canvas
        for key_name_str, tool_str in KEY_TOOL_TUPLE:
            for previous_tool_str in PREVIOUS_TOOL_TUPLE:
                with self.subTest(key=key_name_str,
                                  previous=previous_tool_str):
                    self.select_tool(previous_tool_str)
                    self.press_key(key_name_str, canvas)
                    self.assert_tool_everywhere(tool_str)
                    self.assertTrue(self.main_window.tool_key_filter
                                    .is_activation_on())
                    self.release_key(key_name_str, canvas)
                    self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00289", "LLFR-00323", "LLFR-00199", "LLFR-00202")
    def test_other_key_ends_the_hold(self) -> None:
        """Another key while A or T is held leaves no tool active, also
        after both keys are released; A and T end each other and the
        other tool keys.

        Inputs: none.
        Outputs: none.
        """
        for key_name_str, tool_str in KEY_TOOL_TUPLE:
            for other_key_name_str in ("Key_B", "Key_Shift", "Key_Control",
                                       "Key_X", "Key_Y", "Key_A", "Key_T",
                                       "Key_Z"):
                if other_key_name_str == key_name_str:
                    continue
                with self.subTest(key=key_name_str,
                                  other=other_key_name_str):
                    self.press_key(key_name_str)
                    self.assert_tool_everywhere(tool_str)
                    self.press_key(other_key_name_str)
                    self.assert_tool_everywhere(NO_TOOL_STR)
                    self.release_key(other_key_name_str)
                    self.release_key(key_name_str)
                    self.assert_tool_everywhere(NO_TOOL_STR)
        # A and T pressed while X or Y is held end that hold too.
        for held_key_name_str, held_tool_str in (
                ("Key_X", DELTA_X_TOOL_STR), ("Key_Y", DELTA_Y_TOOL_STR)):
            for key_name_str, _ in KEY_TOOL_TUPLE:
                self.press_key(held_key_name_str)
                self.assert_tool_everywhere(held_tool_str)
                self.press_key(key_name_str)
                self.assert_tool_everywhere(NO_TOOL_STR)
                self.release_key(key_name_str)
                self.release_key(held_key_name_str)
        # A alone still works afterwards.
        self.press_key("Key_A")
        self.assert_tool_everywhere(AREA_TOOL_STR)
        self.release_key("Key_A")
        self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00287", "LLFR-00321", "LLFR-00150", "LLFR-00156")
    def test_not_alone_does_not_activate(self) -> None:
        """A or T with a modifier (Ctrl+A, Cmd+T, Shift+A, Alt+T) or
        with another key held activates nothing; Ctrl+A ends the Data
        tip hold and Shift+T ends the Vertical marker hold.

        Inputs: none.
        Outputs: none.
        """
        for key_name_str, _ in KEY_TOOL_TUPLE:
            for modifier_name_str in ("ControlModifier", "ShiftModifier",
                                      "AltModifier", "MetaModifier"):
                with self.subTest(key=key_name_str,
                                  modifier=modifier_name_str):
                    self.press_key(key_name_str,
                                   modifier_name_str=modifier_name_str)
                    self.assert_tool_everywhere(NO_TOOL_STR)
                    self.release_key(key_name_str)
            for held_key_name_str, modifier_name_str, held_tool_str in (
                    ("Key_Control", "ControlModifier", TIP_TOOL_STR),
                    ("Key_Shift", "ShiftModifier", MARKER_TOOL_STR)):
                self.press_key(held_key_name_str,
                               modifier_name_str=modifier_name_str)
                self.assert_tool_everywhere(held_tool_str)
                self.press_key(key_name_str,
                               modifier_name_str=modifier_name_str)
                self.assert_tool_everywhere(NO_TOOL_STR)
                self.release_key(key_name_str)
                self.release_key(held_key_name_str)
                self.assert_tool_everywhere(NO_TOOL_STR)
            self.press_key("Key_B")
            self.press_key(key_name_str)
            self.assert_tool_everywhere(NO_TOOL_STR)
            self.release_key(key_name_str)
            self.release_key("Key_B")
        self.assertEqual(self.main_window.tool_key_filter.held_key_set,
                         set())

    @covers("LLFR-00287", "LLFR-00321")
    def test_auto_repeat_keeps_the_hold(self) -> None:
        """Auto-repeat events while A or T is held keep the tool active.

        Inputs: none.
        Outputs: none.
        """
        for key_name_str, tool_str in KEY_TOOL_TUPLE:
            self.press_key(key_name_str)
            for _ in range(3):
                self.release_key(key_name_str, auto_repeat_b=True)
                self.press_key(key_name_str, auto_repeat_b=True)
                self.assert_tool_everywhere(tool_str)
            self.release_key(key_name_str)
            self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00288", "LLFR-00322", "LLFR-00079")
    def test_click_on_a_button_while_held_wins(self) -> None:
        """A click on a tool button while A or T is held keeps the
        clicked tool after the key is released.

        Inputs: none.
        Outputs: none.
        """
        for key_name_str, _ in KEY_TOOL_TUPLE:
            self.press_key(key_name_str)
            self.top_panel.plot_tool_button_dict[ZOOM_TOOL_STR].click()
            self.application.processEvents()
            self.assert_tool_everywhere(ZOOM_TOOL_STR)
            self.release_key(key_name_str)
            self.assert_tool_everywhere(ZOOM_TOOL_STR)
            self.top_panel.plot_tool_button_dict[ZOOM_TOOL_STR].click()
            self.application.processEvents()
            self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00287", "LLFR-00321", "LLFR-00286", "LLFR-00320")
    def test_area_and_text_tools_change_nothing_on_the_plots(self) -> None:
        """With Area or Text active, clicks and drags on a plot raise
        nothing and change neither the time range nor the markers, tips
        and delta markers; the tool stays active (LLFR-00109). (The
        Area drag creates an area, checked in tests/view/
        test_areas_view.py.)

        Inputs: none.
        Outputs: none.
        """
        plot_widget = self.plot_widgets()[0]
        for tool_str in (AREA_TOOL_STR, TEXT_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.select_tool(tool_str)
                for event_list in (
                        [("MouseButtonPress", 0.3, 0.5),
                         ("MouseButtonRelease", 0.3, 0.5)],
                        [("MouseButtonPress", 0.3, 0.5),
                         ("MouseMove", 0.5, 0.5),
                         ("MouseMove", 0.7, 0.5),
                         ("MouseButtonRelease", 0.7, 0.5)]):
                    for event_name_str, x_fraction_f, y_fraction_f in (
                            event_list):
                        self.send_fraction_mouse(
                            plot_widget, event_name_str, x_fraction_f,
                            y_fraction_f)
                    self.application.processEvents()
                self.assert_every_range(FULL_RANGE_TUPLE)
                for each_plot_widget in self.all_plot_widgets():
                    self.assertEqual(each_plot_widget.marker_id_list(), [])
                    self.assertEqual(each_plot_widget.pinned_tip_list, [])
                    self.assertEqual(
                        each_plot_widget.delta_marker_id_list(), [])
                self.assert_tool_everywhere(tool_str)
                # The button of the tool shows its active state.
                self.assertTrue(
                    self.top_panel.plot_tool_button_dict[tool_str]
                    .is_active())
                self.top_panel.plot_tool_button_dict[tool_str].click()
                self.assert_tool_everywhere(NO_TOOL_STR)

    def send_fraction_mouse(self, plot_widget, event_name_str: str,
                            x_fraction_f: float,
                            y_fraction_f: float) -> None:
        """Send a left button mouse event at a place of a plot canvas.

        Inputs:
            plot_widget: the PlotWidget whose canvas gets the event.
            event_name_str: name of a QEvent.Type of a mouse event.
            x_fraction_f: x of the place, as a fraction of the width.
            y_fraction_f: y of the place, as a fraction of the height.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtWidgets import QApplication
        canvas = plot_widget.canvas
        local_point = QPointF(canvas.width() * x_fraction_f,
                              canvas.height() * y_fraction_f)
        event_type = getattr(QEvent.Type, event_name_str)
        buttons = (Qt.MouseButton.NoButton
                   if event_type == QEvent.Type.MouseButtonRelease
                   else Qt.MouseButton.LeftButton)
        button = (Qt.MouseButton.NoButton
                  if event_type == QEvent.Type.MouseMove
                  else Qt.MouseButton.LeftButton)
        QApplication.sendEvent(canvas, QMouseEvent(
            event_type, local_point, canvas.mapToGlobal(local_point),
            button, buttons, Qt.KeyboardModifier.NoModifier))

    @covers("LLFR-00157", "LLFR-00287", "LLFR-00321")
    def test_typing_a_and_t_in_the_search_box(self) -> None:
        """In the search box a, t, A and T are typed as letters and do
        not change the tool, also when sent to the window.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        self.activate_window()
        self.select_tool(ZOOM_TOOL_STR)
        self.search_box.setFocus()
        self.application.processEvents()
        self.assertIs(self.application.focusWidget(), self.search_box)
        QTest.keyClicks(self.search_box, "atAT")
        self.application.processEvents()
        self.assertEqual(self.search_box.text(), "atAT")
        self.assert_tool_everywhere(ZOOM_TOOL_STR)
        for key_name_str, _ in KEY_TOOL_TUPLE:
            self.press_key(key_name_str)
            self.assert_tool_everywhere(ZOOM_TOOL_STR)
            self.release_key(key_name_str)
        self.assert_tool_everywhere(ZOOM_TOOL_STR)

    @covers("LLFR-00157", "LLFR-00287", "LLFR-00321")
    def test_typing_in_name_and_note_fields(self) -> None:
        """In the line edit of a name dialog, and in multi-line text
        fields such as a text note may use, a and t are typed and
        activate no tool.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import (
            QInputDialog, QLineEdit, QPlainTextEdit, QTextEdit)
        name_dialog = QInputDialog(self.main_window)
        name_dialog.setInputMode(QInputDialog.InputMode.TextInput)
        name_dialog.setTextValue("")
        name_dialog.show()
        self.application.processEvents()
        line_edit = name_dialog.findChild(QLineEdit)
        self.assertIsNotNone(line_edit)
        QTest.keyClicks(line_edit, "taTA")
        self.assertEqual(name_dialog.textValue(), "taTA")
        self.assert_tool_everywhere(NO_TOOL_STR)
        name_dialog.reject()
        name_dialog.deleteLater()
        self.application.processEvents()
        for field_class in (QTextEdit, QPlainTextEdit):
            with self.subTest(field=field_class.__name__):
                text_field = field_class(self.main_window)
                text_field.show()
                self.application.processEvents()
                for key_name_str, _ in KEY_TOOL_TUPLE:
                    self.press_key(key_name_str, text_field)
                    self.assert_tool_everywhere(NO_TOOL_STR)
                    self.release_key(key_name_str, text_field)
                text_field.deleteLater()
                self.application.processEvents()

    @covers("LLFR-00157", "LLFR-00288", "LLFR-00322")
    def test_focus_into_a_text_field_ends_the_hold(self) -> None:
        """A text field getting the focus while A or T is held ends the
        activation, leaving no tool active.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QFocusEvent
        for key_name_str, tool_str in KEY_TOOL_TUPLE:
            self.press_key(key_name_str)
            self.assert_tool_everywhere(tool_str)
            self.application.sendEvent(self.search_box, QFocusEvent(
                QEvent.Type.FocusIn, Qt.FocusReason.MouseFocusReason))
            self.application.processEvents()
            self.assert_tool_everywhere(NO_TOOL_STR)
            self.release_key(key_name_str, self.search_box)
            self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00287", "LLFR-00207")
    def test_z_still_resets_after_a_and_t(self) -> None:
        """After A or T is released, Z alone resets the zoom again; Z
        while A or T is held ends the hold and does not reset.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_in()
        for key_name_str, tool_str in KEY_TOOL_TUPLE:
            self.press_key(key_name_str)
            self.assert_tool_everywhere(tool_str)
            self.press_key("Key_Z")
            self.assert_tool_everywhere(NO_TOOL_STR)
            self.assert_every_range(ZOOMED_RANGE_TUPLE)
            self.release_key("Key_Z")
            self.release_key(key_name_str)
        self.press_key("Key_Z")
        self.release_key("Key_Z")
        self.assert_every_range(FULL_RANGE_TUPLE)


if __name__ == "__main__":
    unittest.main()
