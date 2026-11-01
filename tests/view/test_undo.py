"""GUI tests for the Undo button and its shortcut (HLFR-00040).

They use a real MainWindow with the real controllers. Dialogs are
patched, so no modal window is ever left open.
"""

import os
import tempfile
import unittest
from unittest import mock

import numpy as np

from tests.support import covers, get_qt_application, requires_qt


@requires_qt
class UndoWindowTestCase(unittest.TestCase):
    """Shared setup: a shown, active window with a file and no plots."""

    def setUp(self) -> None:
        """Create the window and the controllers and open a file.

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
        self.signal_file = SignalFile("memory.csv", {
            "Time": time_array, "speed": time_array * 2.0,
            "force": np.sin(time_array)})
        self.plot_controller = self.controller.plot_controller
        self.plot_controller.on_file_opened(self.signal_file, False)
        self.top_panel = self.main_window.top_panel
        self.undo_button = self.top_panel.undo_button
        self.plot_panel = self.main_window.plot_panel
        self.main_window.show()
        self.main_window.activateWindow()
        from PyQt6.QtTest import QTest
        self.assertTrue(QTest.qWaitForWindowActive(self.main_window))
        # The workspace undo shortcut needs the focus outside text fields.
        self.top_panel.open_file_button.setFocus()
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

    def state(self) -> tuple:
        """Return the plain-value state of the workspace.

        Inputs: none.
        Outputs: the Workspace.state_tuple().
        """
        return self.plot_controller.workspace.state_tuple()

    def current_plot_ids(self) -> list:
        """Return the plot ids shown in the current tab.

        Inputs: none.
        Outputs: a list of int, top to bottom.
        """
        return self.plot_panel.plot_id_list(self.plot_panel.current_tab_id())

    def click_undo(self) -> None:
        """Click the Undo button with the mouse.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.mouseClick(self.undo_button, Qt.MouseButton.LeftButton)
        self.application.processEvents()

    def press_ctrl_z(self, widget=None) -> None:
        """Press Ctrl+Z (Cmd+Z on macOS) on a widget.

        Inputs:
            widget: the widget that gets the keys (default: the plot
                panel).
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.keyClick(widget or self.plot_panel, Qt.Key.Key_Z,
                       Qt.KeyboardModifier.ControlModifier)
        self.application.processEvents()


class UndoButtonTest(UndoWindowTestCase):
    """The Undo button of the top panel."""

    @covers("LLFR-00136")
    def test_button_is_in_the_top_panel(self) -> None:
        """The top panel holds a button called "Undo", after the others.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QPushButton
        self.assertIsInstance(self.undo_button, QPushButton)
        self.assertEqual(self.undo_button.text(), "Undo")
        self.assertIs(self.undo_button.parentWidget(), self.top_panel)
        self.assertTrue(self.undo_button.isVisible())
        self.assertGreater(self.undo_button.x(),
                           self.top_panel.grid_button.x())

    @covers("LLFR-00141", "LLFR-00136")
    def test_disabled_and_paler_at_start(self) -> None:
        """With nothing to undo, the button is disabled and paler.

        Inputs: none.
        Outputs: none.
        """
        from view.toggle_button import NORMAL_COLOR_STR
        from view.undo_button import (
            DISABLED_COLOR_STR, DISABLED_TEXT_COLOR_STR)
        self.assertFalse(self.undo_button.isEnabled())
        self.assertFalse(self.main_window.is_undo_enabled())
        self.assertEqual(self.undo_button.current_background_color_str(),
                         DISABLED_COLOR_STR)
        self.assertIn(":disabled", self.undo_button.styleSheet())
        self.assertIn(DISABLED_TEXT_COLOR_STR,
                      self.undo_button.styleSheet())
        # The paler look is drawn: a pixel of the disabled button is
        # lighter than the same pixel of the enabled button.
        disabled_image = self.undo_button.grab().toImage()
        self.main_window.signal_double_click_handler("speed")
        self.application.processEvents()
        enabled_image = self.undo_button.grab().toImage()
        self.assertEqual(self.undo_button.current_background_color_str(),
                         NORMAL_COLOR_STR)
        point_tuple = (4, disabled_image.height() // 2)
        self.assertGreater(
            disabled_image.pixelColor(*point_tuple).lightness(),
            enabled_image.pixelColor(*point_tuple).lightness())

    @covers("LLFR-00141", "LLFR-00138")
    def test_enabled_after_an_action_and_disabled_when_all_undone(
            self) -> None:
        """An action enables the button; undoing everything disables it.

        Inputs: none.
        Outputs: none.
        """
        start_state = self.state()
        self.main_window.signal_double_click_handler("speed")
        self.assertTrue(self.undo_button.isEnabled())
        self.main_window.signal_double_click_handler("force")
        self.assertEqual(len(self.current_plot_ids()), 2)
        self.click_undo()
        self.assertTrue(self.undo_button.isEnabled())
        self.assertEqual(len(self.current_plot_ids()), 1)
        self.click_undo()
        self.assertFalse(self.undo_button.isEnabled())
        self.assertEqual(self.current_plot_ids(), [])
        self.assertEqual(self.state(), start_state)

    @covers("LLFR-00141")
    def test_disabled_button_does_nothing(self) -> None:
        """Clicks on the disabled button change nothing.

        Inputs: none.
        Outputs: none.
        """
        handler = mock.Mock()
        self.main_window.set_undo_handler(handler)
        self.click_undo()
        self.undo_button.click()
        self.main_window.run_undo()
        handler.assert_not_called()
        self.assertFalse(self.undo_button.is_active())

    @covers("LLFR-00001", "LLFR-00003", "LLFR-00138")
    def test_click_shows_active_color_then_normal(self) -> None:
        """A click shows the active color briefly, then the button is
        normal again (or paler, when nothing is left to undo).

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        from view.toggle_button import ACTIVE_COLOR_STR, NORMAL_COLOR_STR
        from view.undo_button import DISABLED_COLOR_STR
        self.main_window.signal_double_click_handler("speed")
        self.main_window.signal_double_click_handler("force")
        self.click_undo()
        self.assertTrue(self.undo_button.is_active())
        self.assertEqual(self.undo_button.current_background_color_str(),
                         ACTIVE_COLOR_STR)
        QTest.qWait(450)
        self.assertFalse(self.undo_button.is_active())
        self.assertEqual(self.undo_button.current_background_color_str(),
                         NORMAL_COLOR_STR)
        self.click_undo()
        QTest.qWait(450)
        self.assertFalse(self.undo_button.is_active())
        self.assertEqual(self.undo_button.current_background_color_str(),
                         DISABLED_COLOR_STR)

    @covers("LLFR-00138", "LLFR-00125", "LLFR-00109")
    def test_rebuilt_plots_keep_grid_and_plot_tool(self) -> None:
        """Plots rebuilt by undo show the grid and use the active tool.

        Inputs: none.
        Outputs: none.
        """
        from controller.plot_tools import ZOOM_TOOL_STR
        self.main_window.signal_double_click_handler("speed")
        self.main_window.signal_double_click_handler("force")
        self.top_panel.grid_button.click()
        self.top_panel.zoom_button.click()
        self.click_undo()
        plot_widget = self.plot_panel.plot_view(self.current_plot_ids()[0])
        self.assertEqual(plot_widget.plot_tool_str, ZOOM_TOOL_STR)
        self.assertTrue(plot_widget.grid_shown_b)
        self.assertTrue(self.top_panel.zoom_button.is_active())
        self.assertTrue(self.top_panel.grid_button.is_active())

    @covers("LLFR-00138", "LLFR-00070")
    def test_zoomed_range_is_kept(self) -> None:
        """A plot recreated by undo takes the zoomed range of its tab.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.signal_double_click_handler("speed")
        self.main_window.signal_double_click_handler("force")
        first_id_i, second_id_i = self.current_plot_ids()
        self.plot_panel.plot_view(first_id_i).set_time_range(1.0, 2.0)
        self.plot_controller.on_time_range_changed(first_id_i, 1.0, 2.0)
        self.plot_controller.on_plot_delete(second_id_i)
        self.click_undo()
        self.assertEqual(self.current_plot_ids(), [first_id_i, second_id_i])
        for plot_id_i in (first_id_i, second_id_i):
            start_s, end_s = self.plot_panel.plot_view(
                plot_id_i).time_range_tuple()
            self.assertAlmostEqual(start_s, 1.0)
            self.assertAlmostEqual(end_s, 2.0)


class UndoShortcutTest(UndoWindowTestCase):
    """Ctrl+Z (Cmd+Z on macOS) runs the Undo button's action."""

    @covers("LLFR-00137", "LLFR-00138")
    def test_ctrl_z_undoes(self) -> None:
        """Ctrl+Z undoes the most recent action.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QKeySequence
        self.assertEqual(self.main_window.undo_shortcut.key(),
                         QKeySequence(QKeySequence.StandardKey.Undo))
        self.main_window.signal_double_click_handler("speed")
        self.main_window.signal_double_click_handler("force")
        self.press_ctrl_z()
        self.assertEqual(len(self.current_plot_ids()), 1)
        self.press_ctrl_z(self.top_panel)
        self.assertEqual(self.current_plot_ids(), [])
        self.assertFalse(self.undo_button.isEnabled())

    @covers("LLFR-00141", "LLFR-00137")
    def test_ctrl_z_does_nothing_when_nothing_to_undo(self) -> None:
        """With nothing to undo, Ctrl+Z changes nothing.

        Inputs: none.
        Outputs: none.
        """
        handler = mock.Mock()
        self.main_window.set_undo_handler(handler)
        self.press_ctrl_z()
        handler.assert_not_called()

    @covers("LLFR-00137")
    def test_ctrl_z_in_the_search_box_undoes_the_typing(self) -> None:
        """In the search box, Ctrl+Z undoes the text, not the workspace.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        self.main_window.signal_double_click_handler("speed")
        state = self.state()
        search_box = self.main_window.signal_list_panel.search_box
        search_box.setFocus()
        self.application.processEvents()
        QTest.keyClicks(search_box, "spe")
        self.assertEqual(search_box.text(), "spe")
        self.press_ctrl_z(search_box)
        self.assertNotEqual(search_box.text(), "spe")
        self.assertEqual(self.state(), state)
        self.assertTrue(self.undo_button.isEnabled())
        # The window's handler also ignores a focused text field.
        self.main_window._on_undo_shortcut()
        self.assertEqual(self.state(), state)


@requires_qt
class UndoEndToEndTest(unittest.TestCase):
    """Open a file, act, and undo everything with the Undo button."""

    def setUp(self) -> None:
        """Create the window and a CSV file.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        self.path_str = os.path.join(self.temporary_folder.name, "run.csv")
        with open(self.path_str, "w", encoding="utf-8") as file:
            file.write("Time,speed,force\n0,1,2\n0.5,3,4\n1,5,6\n")
        self.main_window = MainWindow()
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def click(self, button) -> None:
        """Click a button with the mouse.

        Inputs:
            button: the QPushButton.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        self.application.processEvents()

    def open_file(self) -> None:
        """Open the CSV file with the Open file button.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QFileDialog
        with mock.patch.object(QFileDialog, "getOpenFileName",
                               return_value=(self.path_str, "")):
            self.click(self.main_window.top_panel.open_file_button)

    def double_click_signal(self, signal_name_str: str) -> None:
        """Double-click a name in the signal list.

        Inputs:
            signal_name_str: the name to double-click.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        list_widget = self.main_window.signal_list_panel.signal_list_widget
        item = list_widget.findItems(signal_name_str,
                                     Qt.MatchFlag.MatchExactly)[0]
        list_widget.itemDoubleClicked.emit(item)
        self.application.processEvents()

    @covers("LLFR-00138", "LLFR-00140", "LLFR-00141", "LLFR-00136",
            "LLFR-00142")
    def test_open_act_and_undo_everything(self) -> None:
        """Two plots, a marker and a tab rename are undone in 4 clicks.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QInputDialog
        top_panel = self.main_window.top_panel
        plot_panel = self.main_window.plot_panel
        undo_button = top_panel.undo_button
        self.open_file()
        self.assertEqual(self.main_window.signal_list_panel
                         .signal_name_list(), ["Time", "speed", "force"])
        self.assertFalse(undo_button.isEnabled())
        tab_id_i = plot_panel.current_tab_id()
        self.double_click_signal("speed")
        self.double_click_signal("force")
        first_id_i, second_id_i = plot_panel.plot_id_list(tab_id_i)
        self.click(top_panel.marker_button)
        plot_panel.plot_view(first_id_i).marker_place_requested.emit(0.5)
        self.application.processEvents()
        self.assertEqual(plot_panel.plot_view(first_id_i).marker_count(), 1)
        with mock.patch.object(QInputDialog, "getText",
                               return_value=("Mine", True)):
            plot_panel.request_rename_tab(tab_id_i)
        self.assertEqual(self.main_window.tab_name_list(), ["Mine"])
        # Undo the rename, the marker, then each plot.
        self.click(undo_button)
        self.assertEqual(self.main_window.tab_name_list(), ["Tab 1"])
        self.assertEqual(plot_panel.plot_view(first_id_i).marker_count(), 1)
        self.click(undo_button)
        self.assertEqual(plot_panel.plot_view(first_id_i).marker_count(), 0)
        self.assertEqual(plot_panel.plot_id_list(tab_id_i),
                         [first_id_i, second_id_i])
        self.click(undo_button)
        self.assertEqual(plot_panel.plot_id_list(tab_id_i), [first_id_i])
        self.assertEqual(
            [entry[0] for entry in
             plot_panel.plot_view(first_id_i).legend_entry_list()],
            ["speed"])
        self.click(undo_button)
        self.assertEqual(self.main_window.tab_name_list(), ["Tab 1"])
        self.assertEqual(plot_panel.plot_id_list(
            plot_panel.current_tab_id()), [])
        self.assertFalse(undo_button.isEnabled())
        # LLFR-00142: opening the file again leaves nothing to undo.
        self.double_click_signal("speed")
        self.assertTrue(undo_button.isEnabled())
        with mock.patch.object(QInputDialog, "getText"), \
                mock.patch("view.message_boxes.ask_replace_file",
                           return_value=True):
            self.open_file()
        self.assertFalse(undo_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
