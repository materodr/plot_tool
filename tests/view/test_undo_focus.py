"""GUI tests for fix #64: undo after a click on a plot, and late releases.

1. A click on a plot (or on an empty tab page) takes the keyboard focus
   from the search box, so that Ctrl+Z (Cmd+Z) runs the workspace undo
   (LLFR-00137, LLFR-00138).
2. A marker drag, pinned tip drag or pan in progress on a plot that an
   undo removes is dropped: its late release sends no move request and
   records no undoable action (LLFR-00138, LLFR-00086, LLFR-00152,
   LLFR-00117).
"""

import unittest
from unittest import mock

from tests.support import covers, requires_qt
from tests.view.test_undo import UndoWindowTestCase


@requires_qt
class UndoFocusTest(UndoWindowTestCase):
    """A click on the plot area moves the focus out of the search box."""

    def type_in_search_box(self, text_str: str) -> None:
        """Give the search box the focus and type a text in it.

        Inputs:
            text_str: the text to type.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        search_box = self.main_window.signal_list_panel.search_box
        search_box.setFocus()
        self.application.processEvents()
        QTest.keyClicks(search_box, text_str)
        self.application.processEvents()
        self.assertIs(self.application.focusWidget(), search_box)

    def press_ctrl_z_on_focus(self) -> None:
        """Press Ctrl+Z on the widget that has the keyboard focus.

        Inputs: none.
        Outputs: none.
        """
        self.press_ctrl_z(self.application.focusWidget()
                          or self.plot_panel)

    def assert_focus_not_in_text_field(self) -> None:
        """Check that no text field has the keyboard focus.

        Inputs: none.
        Outputs: none.
        """
        from view.main_window import TEXT_INPUT_WIDGET_TUPLE
        self.assertNotIsInstance(self.application.focusWidget(),
                                 TEXT_INPUT_WIDGET_TUPLE)

    def click_plot(self, plot_id_i: int, button=None) -> None:
        """Click the middle of a plot's canvas with the mouse.

        Inputs:
            plot_id_i: id of the plot.
            button: the Qt mouse button (default: left).
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        canvas = self.plot_panel.plot_view(plot_id_i).canvas
        QTest.mouseClick(canvas, button or Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier,
                         canvas.rect().center())
        self.application.processEvents()

    @covers("LLFR-00137", "LLFR-00138")
    def test_click_on_plot_then_ctrl_z_undoes_the_workspace(self) -> None:
        """Type in the search box, click the plot, Ctrl+Z removes it.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.signal_double_click_handler("speed")
        self.application.processEvents()
        plot_id_i = self.current_plot_ids()[0]
        self.type_in_search_box("sp")
        self.click_plot(plot_id_i)
        canvas = self.plot_panel.plot_view(plot_id_i).canvas
        self.assertIs(self.application.focusWidget(), canvas)
        self.press_ctrl_z_on_focus()
        self.assertEqual(self.current_plot_ids(), [])
        search_box = self.main_window.signal_list_panel.search_box
        self.assertEqual(search_box.text(), "sp")

    @covers("LLFR-00137", "LLFR-00138")
    def test_right_and_middle_press_also_take_the_focus(self) -> None:
        """A right or middle press on the plot also moves the focus.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        self.main_window.signal_double_click_handler("speed")
        self.application.processEvents()
        plot_id_i = self.current_plot_ids()[0]
        canvas = self.plot_panel.plot_view(plot_id_i).canvas
        self.type_in_search_box("sp")
        self.click_plot(plot_id_i, Qt.MouseButton.MiddleButton)
        self.assertIs(self.application.focusWidget(), canvas)
        self.type_in_search_box("e")
        plot_widget = self.plot_panel.plot_view(plot_id_i)
        # The context menu is not opened in the test.
        with mock.patch.object(plot_widget, "request_context_menu"):
            self.click_plot(plot_id_i, Qt.MouseButton.RightButton)
        self.assertIs(self.application.focusWidget(), canvas)
        self.press_ctrl_z_on_focus()
        self.assertEqual(self.current_plot_ids(), [])
        search_box = self.main_window.signal_list_panel.search_box
        self.assertEqual(search_box.text(), "spe")

    @covers("LLFR-00137", "LLFR-00138")
    def test_focus_stays_out_of_text_fields_after_the_undo(self) -> None:
        """After an undo removes the clicked plot, Ctrl+Z still undoes.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.signal_double_click_handler("speed")
        self.main_window.signal_double_click_handler("force")
        self.main_window.signal_double_click_handler("speed")
        self.application.processEvents()
        self.assertEqual(len(self.current_plot_ids()), 3)
        self.type_in_search_box("fo")
        self.click_plot(self.current_plot_ids()[0])
        self.press_ctrl_z_on_focus()
        self.assertEqual(len(self.current_plot_ids()), 2)
        self.assert_focus_not_in_text_field()
        self.press_ctrl_z_on_focus()
        self.assertEqual(len(self.current_plot_ids()), 1)
        self.assert_focus_not_in_text_field()
        search_box = self.main_window.signal_list_panel.search_box
        self.assertEqual(search_box.text(), "fo")

    @covers("LLFR-00137", "LLFR-00138")
    def test_click_on_an_empty_tab_page_takes_the_focus(self) -> None:
        """A click on a tab with no plots also moves the focus.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.plot_controller.on_add_tab()
        self.application.processEvents()
        self.assertEqual(len(self.main_window.tab_name_list()), 2)
        page = self.plot_panel.tab_widget.currentWidget()
        self.type_in_search_box("sp")
        QTest.mouseClick(page, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier,
                         page.rect().center())
        self.application.processEvents()
        self.assertIs(self.application.focusWidget(), page)
        self.press_ctrl_z_on_focus()
        self.assertEqual(len(self.main_window.tab_name_list()), 1)
        self.assert_focus_not_in_text_field()


@requires_qt
class UndoDuringDragTest(UndoWindowTestCase):
    """An undo during a drag drops the drag of the removed widget."""

    def setUp(self) -> None:
        """Create a plot of speed and lay it out.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.main_window.signal_double_click_handler("speed")
        self.application.processEvents()
        self.plot_id_i = self.current_plot_ids()[0]

    def old_widget(self):
        """Return the plot widget shown now, drawn and ready for events.

        Inputs: none.
        Outputs: the PlotWidget.
        """
        plot_widget = self.plot_panel.plot_view(self.plot_id_i)
        plot_widget.canvas.draw()
        return plot_widget

    def history_length(self) -> int:
        """Return the number of actions that can be undone.

        Inputs: none.
        Outputs: an int.
        """
        return len(self.plot_controller.undo_history.snapshot_list)

    def undo_without_event_loop(self) -> None:
        """Press Ctrl+Z without running the event loop afterwards.

        Inputs: none.
        Outputs: none. The removed widgets are not deleted yet, as when
            the user still holds the mouse button.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.keyClick(self.top_panel, Qt.Key.Key_Z,
                       Qt.KeyboardModifier.ControlModifier)

    def make_last_action_a_width_change(self) -> None:
        """Record one more action, so the undo keeps the dragged item.

        Inputs: none.
        Outputs: none.
        """
        self.plot_controller.on_curve_width(self.plot_id_i, "speed", 3)
        self.application.processEvents()

    @covers("LLFR-00138", "LLFR-00086")
    def test_late_marker_release_after_undo_moves_nothing(self) -> None:
        """A marker drag released after an undo is not applied.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6 import sip
        from controller.plot_tools import MARKER_TOOL_STR
        self.plot_controller.on_marker_place(self.plot_id_i, 2.0)
        self.make_last_action_a_width_change()
        plot_widget = self.old_widget()
        plot_widget.set_plot_tool(MARKER_TOOL_STR)
        marker_id_i = plot_widget.marker_id_list()[0]
        move_recorder = mock.Mock()
        plot_widget.marker_move_requested.connect(move_recorder)
        plot_widget.press_at(plot_widget.data_to_widget_point(2.0, 4.0))
        self.assertEqual(plot_widget.drag_marker_id_i, marker_id_i)
        plot_widget.drag_to(plot_widget.data_to_widget_point(3.0, 4.0))
        self.assertTrue(plot_widget.drag_moved_b)
        self.undo_without_event_loop()
        self.assertEqual(self.history_length(), 2)
        state = self.state()
        self.assertFalse(sip.isdeleted(plot_widget))
        self.assertIsNot(self.plot_panel.plot_view(self.plot_id_i),
                         plot_widget)
        plot_widget.release_at(plot_widget.data_to_widget_point(3.5, 4.0))
        self.application.processEvents()
        move_recorder.assert_not_called()
        self.assertEqual(self.history_length(), 2)
        self.assertEqual(self.state(), state)
        restored_widget = self.plot_panel.plot_view(self.plot_id_i)
        self.assertAlmostEqual(restored_widget.marker_time_s(marker_id_i),
                               2.0)

    @covers("LLFR-00138", "LLFR-00152")
    def test_late_tip_release_after_undo_moves_nothing(self) -> None:
        """A pinned tip drag released after an undo is not applied.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6 import sip
        from PyQt6.QtCore import QPoint
        self.plot_controller.on_tip_pin(self.plot_id_i, "speed", 2.0, 4.0)
        self.make_last_action_a_width_change()
        plot_widget = self.old_widget()
        move_recorder = mock.Mock()
        plot_widget.pinned_tip_move_requested.connect(move_recorder)
        center_tuple = plot_widget.tip_label_center_tuple(0)
        press_point = plot_widget.display_to_widget_point(*center_tuple)
        plot_widget.press_at(press_point)
        self.assertEqual(plot_widget.drag_tip_index_i, 0)
        plot_widget.tip_drag_to(press_point + QPoint(40, 30))
        self.assertTrue(plot_widget.tip_drag_moved_b)
        self.undo_without_event_loop()
        self.assertEqual(self.history_length(), 2)
        state = self.state()
        self.assertFalse(sip.isdeleted(plot_widget))
        plot_widget.tip_release_at(press_point + QPoint(60, 40))
        self.application.processEvents()
        move_recorder.assert_not_called()
        self.assertEqual(self.history_length(), 2)
        self.assertEqual(self.state(), state)

    @covers("LLFR-00138", "LLFR-00117")
    def test_pan_in_progress_stops_on_undo(self) -> None:
        """A pan on a plot that an undo removes stops and emits nothing.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6 import sip
        self.make_last_action_a_width_change()
        plot_widget = self.old_widget()
        plot_widget.zoom_to_range(1.0, 2.0)
        self.application.processEvents()
        range_recorder = mock.Mock()
        plot_widget.time_range_changed.connect(range_recorder)
        plot_widget.pan_press_at(plot_widget.data_to_widget_point(1.5, 3.0))
        self.assertTrue(plot_widget.panning_b)
        self.undo_without_event_loop()
        self.assertEqual(self.history_length(), 1)
        self.assertFalse(sip.isdeleted(plot_widget))
        self.assertFalse(plot_widget.panning_b)
        plot_widget.pan_release_at(
            plot_widget.data_to_widget_point(1.8, 3.0))
        self.application.processEvents()
        range_recorder.assert_not_called()
        self.assertEqual(self.history_length(), 1)


if __name__ == "__main__":
    unittest.main()
