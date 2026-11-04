"""Qt tests for the undocked windows (#205, step 3).

A real MainWindow and MainController are used (the setup of
test_plot_panel). They check the undock button of each tab
(HLFR-00123), the parts of an undocked window (HLFR-00125, HLFR-00134 to
HLFR-00136), docking (HLFR-00124), closing a window (HLFR-00138), the
signal list panels of the windows (HLFR-00127 to HLFR-00130), the
shortcuts in a window (HLFR-00137), the one undo history (HLFR-00132,
HLFR-00133, HLFR-00131), the export of undocked tabs (HLFR-00038) and
the windows of a layout file (HLFR-00139 to HLFR-00141).

Every window is closed in tearDown. No test moves the shared mouse
pointer: mouse and key events are sent to the widgets directly.
"""

import unittest
from unittest import mock

from tests.support import covers, requires_qt
from tests.view.test_plot_panel import PlotPanelTestCase
from tests.view.test_tip_key import send_key


@requires_qt
class UndockedWindowTestCase(PlotPanelTestCase):
    """Helpers for the undocked window tests."""

    def tearDown(self) -> None:
        """Close every undocked window, then the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close_all_undocked_windows()
        self.process_events()
        super().tearDown()

    @property
    def plot_controller(self):
        """Return the plot controller.

        Inputs: none.
        Outputs: the PlotController.
        """
        return self.controller.plot_controller

    def add_tab(self) -> int:
        """Click "+" and return the id of the new tab.

        Inputs: none.
        Outputs: the id of the tab shown afterwards.
        """
        self.panel.add_tab_button.click()
        self.process_events()
        return self.panel.current_tab_id()

    def undock(self, tab_id_i: int):
        """Click the undock button of a tab.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: the UndockedWindow of the tab, or None.
        """
        self.panel.undock_button_of(tab_id_i).click()
        self.process_events()
        return self.main_window.undocked_window(tab_id_i)

    def two_tabs_one_undocked(self):
        """Show the window, add a tab with a plot and undock it.

        Inputs: none.
        Outputs: (first tab id, undocked tab id, UndockedWindow).
        """
        self.main_window.show()
        first_id_i = self.panel.current_tab_id()
        second_id_i = self.add_tab()
        self.main_window.signal_double_click_handler("speed")
        self.process_events()
        window = self.undock(second_id_i)
        return first_id_i, second_id_i, window

    def tab(self, tab_id_i: int):
        """Return a tab of the model.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: the Tab, or None.
        """
        return self.plot_controller.workspace.find_tab(tab_id_i)


class UndockButtonTest(UndockedWindowTestCase):
    """The undock button of the tabs (HLFR-00123)."""

    @covers("LLFR-00977", "LLFR-00979", "LLFR-00978", "HLFR-00123")
    def test_each_docked_tab_has_an_undock_button(self) -> None:
        """An undock button right of the name, with the tip "Undock".

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QTabBar
        self.add_tab()
        tab_bar = self.panel.tab_widget.tabBar()
        for index_i in range(tab_bar.count()):
            tab_id_i = self.panel.tab_id_at_index(index_i)
            button = tab_bar.tabButton(index_i,
                                       QTabBar.ButtonPosition.RightSide)
            self.assertIs(button, self.panel.undock_button_of(tab_id_i))
            self.assertEqual(button.toolTip(), "Undock")
            self.assertFalse(button.icon().isNull())

    @covers("LLFR-00983", "LLFR-00984", "LLFR-00999", "HLFR-00126")
    def test_last_docked_tab_cannot_be_undocked(self) -> None:
        """Disabled with one docked tab; any number of windows else.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.panel.current_tab_id()
        self.assertFalse(self.panel.undock_button_of(first_id_i).isEnabled())
        self.panel.undock_button_of(first_id_i).click()
        self.process_events()
        self.assertIsNone(self.main_window.undocked_window(first_id_i))
        id_list = [self.add_tab() for _ in range(3)]
        for tab_id_i in id_list:
            self.assertIsNotNone(self.undock(tab_id_i))
        self.assertEqual(len(self.main_window.undocked_window_dict), 3)
        self.assertFalse(self.panel.undock_button_of(first_id_i).isEnabled())

    @covers("LLFR-00980", "LLFR-00985", "LLFR-00981", "LLFR-01093",
            "LLFR-01048", "LLFR-01049", "HLFR-00123", "HLFR-00125")
    def test_undock_moves_the_tab_into_a_window(self) -> None:
        """The tab with its plot is in the new window, which has the size
        and place of the plot panel, kept on the screen.

        Inputs: none.
        Outputs: none.
        """
        from model.window_placement import placed_window_tuple
        self.main_window.show()
        self.process_events()
        expected_tuple = placed_window_tuple(
            self.main_window.new_window_tuple(),
            self.main_window.screen_area_list(),
            self.main_window.main_screen_area())
        first_id_i, second_id_i, window = self.two_tabs_one_undocked()
        page = self.panel.page_dict[second_id_i]
        self.assertIs(window.page(), page)
        self.assertEqual(len(page.plot_widget_list), 1)
        self.assertEqual(self.panel.tab_widget.indexOf(page), -1)
        self.assertEqual(window.size().width(), expected_tuple[2])
        self.assertEqual(window.size().height(), expected_tuple[3])
        self.assertTrue(self.tab(second_id_i).undocked_b)

    @covers("LLFR-00982")
    def test_main_window_shows_the_nearest_docked_tab(self) -> None:
        """After the shown tab is undocked, the tab to its left is shown.

        Inputs: none.
        Outputs: none.
        """
        first_id_i, second_id_i, _ = self.two_tabs_one_undocked()
        self.assertEqual(self.panel.current_tab_id(), first_id_i)


class WindowPartsTest(UndockedWindowTestCase):
    """The parts of an undocked window."""

    @covers("LLFR-01026", "LLFR-01027", "LLFR-01028", "LLFR-01031",
            "LLFR-01095", "HLFR-00134", "HLFR-00135")
    def test_title_and_tab_button(self) -> None:
        """Titled with the tab name, which follows a rename; one tab
        button, selected, with no undock button.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QTabBar
        _, second_id_i, window = self.two_tabs_one_undocked()
        name_str = self.tab(second_id_i).name_str
        self.assertEqual(window.windowTitle(), name_str)
        self.assertEqual(window.tab_bar.count(), 1)
        self.assertEqual(window.tab_bar.currentIndex(), 0)
        self.assertEqual(window.tab_bar.tabText(0), name_str)
        self.assertIsNone(window.tab_bar.tabButton(
            0, QTabBar.ButtonPosition.RightSide))
        self.plot_controller.on_rename_tab(second_id_i, "Engine")
        self.assertEqual(window.windowTitle(), "Engine")
        self.assertEqual(window.tab_bar.tabText(0), "Engine")
        self.plot_controller.on_undo()
        self.process_events()
        self.assertEqual(self.main_window.undocked_window(
            second_id_i).windowTitle(), name_str)

    @covers("LLFR-00997", "LLFR-00990", "LLFR-01009", "LLFR-00992",
            "LLFR-01035", "LLFR-01000", "LLFR-00440", "HLFR-00136")
    def test_tab_row_and_panels(self) -> None:
        """Tab button left, signal list and dock buttons right, then the
        plot well and the signal list panel side by side, no top panel.

        Inputs: none.
        Outputs: none.
        """
        from view.top_panel import TopPanel
        _, _, window = self.two_tabs_one_undocked()
        window.resize(700, 500)
        self.process_events()
        self.assertEqual(window.dock_button.toolTip(), "Dock")
        self.assertFalse(window.dock_button.icon().isNull())
        list_x_i = window.signal_list_button.mapTo(window, window.rect()
                                                   .topLeft()).x()
        dock_x_i = window.dock_button.mapTo(window, window.rect()
                                            .topLeft()).x()
        tab_x_i = window.tab_bar.mapTo(window, window.rect().topLeft()).x()
        self.assertLess(tab_x_i, list_x_i)
        self.assertLess(list_x_i, dock_x_i)
        self.assertGreater(dock_x_i + window.dock_button.width(),
                           window.width() - 40)
        self.assertLess(window.tab_bar.mapTo(window, window.rect()
                                             .topLeft()).y(),
                        window.splitter.mapTo(window, window.rect()
                                              .topLeft()).y())
        self.assertIs(window.splitter.widget(0), window.pane_widget)
        self.assertIs(window.splitter.widget(1), window.signal_list_panel)
        self.assertEqual(window.findChildren(TopPanel), [])
        self.assertFalse(window.tab_bar.isMovable())
        self.assertEqual(window.pane_widget.count(), 1)

    @covers("LLFR-01015", "LLFR-01012", "LLFR-01013", "LLFR-01014",
            "LLFR-01011", "LLFR-01016", "LLFR-01018", "HLFR-00129")
    def test_signal_list_button_hides_and_shows_the_panel(self) -> None:
        """Hidden at start; the button shows it at the main panel's
        width (at most half the window), hides it, and both are undone.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, window = self.two_tabs_one_undocked()
        window.resize(900, 500)
        self.process_events()
        self.assertFalse(window.is_panel_shown())
        self.assertFalse(window.signal_list_button.isChecked())
        self.assertEqual(window.signal_list_button.toolTip(),
                         "Show signal list")
        window.signal_list_button.click()
        self.process_events()
        self.assertTrue(window.is_panel_shown())
        self.assertTrue(window.signal_list_button.isChecked())
        self.assertEqual(window.signal_list_button.toolTip(),
                         "Hide signal list")
        expected_i = min(self.main_window.main_panel_width(),
                         window.width() // 2)
        self.assertAlmostEqual(window.panel_width(), expected_i, delta=3)
        window.signal_list_button.click()
        self.process_events()
        self.assertFalse(window.is_panel_shown())
        self.assertEqual(window.pane_widget.width(),
                         window.splitter.width())
        self.plot_controller.on_undo()
        self.process_events()
        window = self.main_window.undocked_window(second_id_i)
        self.assertTrue(window.is_panel_shown())
        self.plot_controller.on_undo()
        self.process_events()
        self.assertFalse(self.main_window.undocked_window(
            second_id_i).is_panel_shown())

    @covers("LLFR-01019", "HLFR-00130")
    def test_main_window_keeps_its_panel(self) -> None:
        """The main window's panel cannot be collapsed or hidden.

        Inputs: none.
        Outputs: none.
        """
        from view.undocked_window import SIGNAL_LIST_BUTTON_OBJECT_NAME_STR
        self.main_window.show()
        self.process_events()
        self.assertFalse(self.main_window.lower_splitter
                         .childrenCollapsible())
        self.assertGreaterEqual(self.main_window.main_panel_width(), 1)
        self.assertTrue(self.main_window.signal_list_panel.isVisible())
        from PyQt6.QtWidgets import QWidget
        self.assertEqual(self.main_window.findChildren(
            QWidget, SIGNAL_LIST_BUTTON_OBJECT_NAME_STR), [])

    @covers("LLFR-00893", "LLFR-00424", "LLFR-00894", "HLFR-00095")
    def test_well_look_and_search_box_alignment(self) -> None:
        """The window's well has the main window's style; its search box
        is level with the plots of its tab.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_panel import build_tab_style_sheet
        _, _, window = self.two_tabs_one_undocked()
        window.signal_list_button.click()
        window.resize(800, 520)
        self.process_events()
        self.process_events()
        self.assertEqual(window.pane_widget.objectName(), "plot_tab_widget")
        self.assertEqual(window.pane_widget.styleSheet(),
                         build_tab_style_sheet())
        window.search_box_aligner.align()
        self.process_events()
        self.assertLessEqual(abs(window.search_box_aligner
                                 .misalignment_px()), 2)


class TabButtonMenuTest(UndockedWindowTestCase):
    """The tab button of a window works as a tab (HLFR-00135)."""

    @covers("LLFR-01029", "LLFR-01034", "HLFR-00135", "HLFR-00016")
    def test_tab_menu_with_delete_enabled(self) -> None:
        """The menu of an undocked tab has Delete enabled; Delete deletes
        the tab and closes the window, undoably.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, _ = self.two_tabs_one_undocked()
        menu = self.panel.build_tab_menu_of(second_id_i, True)
        self.assertEqual([action.text() for action in menu.actions()],
                         ["Delete", "Rename", "Plot matrix"])
        self.assertTrue(menu.actions()[0].isEnabled())
        menu.actions()[0].trigger()
        menu.deleteLater()
        self.process_events()
        self.assertIsNone(self.tab(second_id_i))
        self.assertIsNone(self.main_window.undocked_window(second_id_i))
        self.plot_controller.on_undo()
        self.process_events()
        self.assertIsNotNone(self.main_window.undocked_window(second_id_i))

    @covers("LLFR-01030", "LLFR-01032", "HLFR-00135", "HLFR-00017")
    def test_double_click_renames(self) -> None:
        """A left double-click on the tab button asks for a new name.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        _, second_id_i, window = self.two_tabs_one_undocked()
        center = window.tab_bar.tabRect(0).center()
        event = QMouseEvent(
            QEvent.Type.MouseButtonDblClick, QPointF(center),
            QPointF(window.tab_bar.mapToGlobal(center)),
            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier)
        with mock.patch.object(self.panel, "request_rename_tab") as rename:
            self.application.sendEvent(window.tab_bar, event)
            self.process_events()
        rename.assert_called_once_with(second_id_i)


class DockAndCloseTest(UndockedWindowTestCase):
    """Docking and closing a window."""

    @covers("LLFR-00993", "LLFR-00994", "LLFR-00995", "LLFR-00985",
            "HLFR-00124")
    def test_dock_button_puts_the_tab_back(self) -> None:
        """The tab is the last docked tab, shown, and its window closes.

        Inputs: none.
        Outputs: none.
        """
        first_id_i, second_id_i, window = self.two_tabs_one_undocked()
        page = window.page()
        window.dock_button.click()
        self.process_events()
        self.assertIsNone(self.main_window.undocked_window(second_id_i))
        tab_widget = self.panel.tab_widget
        self.assertEqual(tab_widget.indexOf(page), tab_widget.count() - 1)
        self.assertEqual(self.panel.current_tab_id(), second_id_i)
        self.assertEqual(len(page.plot_widget_list), 1)
        self.assertIsNotNone(self.panel.undock_button_of(second_id_i))
        self.plot_controller.on_undo()
        self.process_events()
        self.assertIsNotNone(self.main_window.undocked_window(second_id_i))

    @covers("LLFR-01038", "LLFR-01039", "LLFR-01024", "LLFR-01094",
            "HLFR-00138", "HLFR-00133")
    def test_system_close_deletes_the_tab(self) -> None:
        """Closing the window deletes the tab; undo opens it again where
        it was, with its panel as it was.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, window = self.two_tabs_one_undocked()
        window.signal_list_button.click()
        window.move(40, 30)
        self.process_events()
        place_tuple = (window.x(), window.y())
        window.close()
        self.process_events()
        self.assertIsNone(self.tab(second_id_i))
        self.assertIsNone(self.main_window.undocked_window(second_id_i))
        self.plot_controller.on_undo()
        self.process_events()
        window = self.main_window.undocked_window(second_id_i)
        self.assertEqual((window.x(), window.y()), place_tuple)
        self.assertTrue(window.is_panel_shown())
        self.assertEqual(len(window.page().plot_widget_list), 1)

    @covers("LLFR-01038")
    def test_close_shortcut_closes_the_window(self) -> None:
        """The system close shortcut of the window closes it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QKeySequence
        _, second_id_i, window = self.two_tabs_one_undocked()
        self.assertEqual(window.close_shortcut.key(),
                         QKeySequence(QKeySequence.StandardKey.Close))
        window.close_shortcut.activated.emit()
        self.process_events()
        self.assertIsNone(self.tab(second_id_i))

    @covers("LLFR-00989", "LLFR-00986", "HLFR-00123")
    def test_main_window_close_closes_every_window(self) -> None:
        """The windows are top-level and close with the main window.

        Inputs: none.
        Outputs: none.
        """
        _, _, window = self.two_tabs_one_undocked()
        self.assertIsNone(window.parent())
        self.assertTrue(window.isWindow())
        self.main_window.close()
        self.process_events()
        self.assertEqual(self.main_window.undocked_window_dict, {})

    @covers("LLFR-00998", "HLFR-00125", "HLFR-00118")
    def test_file_close_that_empties_the_tab_closes_the_window(self) -> None:
        """Closing the data file closes the emptied undocked tab.

        Inputs: none.
        Outputs: none.
        """
        from model.data_files import DataFileSet
        _, second_id_i, _ = self.two_tabs_one_undocked()
        closed_list = list(self.signal_file.signal_name_list)
        self.plot_controller.signal_file = DataFileSet()
        self.plot_controller.close_signals(closed_list)
        self.process_events()
        self.assertIsNone(self.tab(second_id_i))
        self.assertEqual(self.main_window.undocked_window_dict, {})


class WindowSignalListTest(UndockedWindowTestCase):
    """The signal list panels of the windows (HLFR-00127, HLFR-00128)."""

    @covers("LLFR-01001", "LLFR-01008", "HLFR-00127", "HLFR-00011")
    def test_same_list_in_every_panel(self) -> None:
        """A window's panel shows the main panel's rows, now and after
        the list changes.

        Inputs: none.
        Outputs: none.
        """
        _, _, window = self.two_tabs_one_undocked()
        main_panel = self.main_window.signal_list_panel
        self.assertEqual(window.signal_list_panel.row_list(),
                         main_panel.row_list())
        self.main_window.show_signal_names(["a", "b"])
        self.assertEqual(window.signal_list_panel.signal_name_list(),
                         ["a", "b"])

    @covers("LLFR-01006", "LLFR-01007", "LLFR-01017", "LLFR-01008",
            "HLFR-00128")
    def test_search_text_in_every_search_box(self) -> None:
        """Typing in one box puts the text in the others, hidden panels
        included, and leaves the cursor in the typed box.

        Inputs: none.
        Outputs: none.
        """
        _, _, window = self.two_tabs_one_undocked()
        main_box = self.main_window.signal_list_panel.search_box
        window_box = window.signal_list_panel.search_box
        window_box.setText("spe")
        window_box.setCursorPosition(1)
        self.process_events()
        self.assertEqual(main_box.text(), "spe")
        self.assertEqual(window_box.cursorPosition(), 1)
        main_box.setText("for")
        self.assertEqual(window_box.text(), "for")
        self.assertEqual(window.signal_list_panel.signal_name_list(),
                         self.main_window.signal_list_panel
                         .signal_name_list())
        third_id_i = self.add_tab()
        new_window = self.undock(third_id_i)
        self.assertEqual(new_window.signal_list_panel.search_text(), "for")

    @covers("LLFR-01003", "LLFR-01002", "LLFR-00019", "LLFR-00295",
            "LLFR-01005", "HLFR-00127", "HLFR-00012", "HLFR-00064")
    def test_plots_from_a_window_panel_go_into_its_tab(self) -> None:
        """A double-click and Enter in the window's panel plot in the
        window's tab; each panel has its own selection.

        Inputs: none.
        Outputs: none.
        """
        first_id_i, second_id_i, window = self.two_tabs_one_undocked()
        window.signal_list_panel.signal_double_clicked.emit("force")
        window.signal_list_panel.selected_signals_plot_requested.emit(
            ["angle", "speed"])
        self.process_events()
        self.assertEqual(len(self.tab(second_id_i).plot_list), 3)
        self.assertEqual(len(self.tab(first_id_i).plot_list), 0)
        window_list = window.signal_list_panel.signal_list_widget
        main_list = self.main_window.signal_list_panel.signal_list_widget
        window_list.item(1).setSelected(True)
        self.assertEqual(main_list.selectedItems(), [])

    @covers("LLFR-00988", "HLFR-00123", "HLFR-00002")
    def test_boxes_over_the_window_of_the_action(self) -> None:
        """Boxes of an action in a window have that window as parent.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        _, _, window = self.two_tabs_one_undocked()
        with mock.patch.object(QApplication, "activeWindow",
                               return_value=window):
            self.assertIs(self.main_window.dialog_parent(), window)
            with mock.patch("view.message_boxes."
                            "show_full_tab_notification") as box:
                self.main_window.show_full_tab_notification(5, 1)
            self.assertIs(box.call_args[0][0], window)
        self.assertIs(self.main_window.dialog_parent(), self.main_window)


class WindowShortcutTest(UndockedWindowTestCase):
    """The shortcuts and the plot tool in a window (HLFR-00137)."""

    @covers("LLFR-01036", "LLFR-01023", "LLFR-01022", "HLFR-00137",
            "HLFR-00132")
    def test_undo_and_redo_shortcuts_in_a_window(self) -> None:
        """The window's Undo and Redo shortcuts use the one history.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, window = self.two_tabs_one_undocked()
        window.undo_shortcut.activated.emit()
        self.process_events()
        self.assertFalse(self.tab(second_id_i).undocked_b)
        self.main_window.redo_shortcut.activated.emit()
        self.process_events()
        window = self.main_window.undocked_window(second_id_i)
        self.assertIsNotNone(window)
        window.undo_shortcut.activated.emit()
        self.process_events()
        window_redo = self.main_window.undocked_window_dict
        self.assertEqual(window_redo, {})

    @covers("LLFR-01036", "LLFR-01037", "HLFR-00137", "HLFR-00032")
    def test_held_tool_key_in_a_window(self) -> None:
        """Holding X in a window activates Delta X for every plot.

        Inputs: none.
        Outputs: none.
        """
        from controller.plot_tools import DELTA_X_TOOL_STR, NO_TOOL_STR
        _, _, window = self.two_tabs_one_undocked()
        receiver = window.pane_widget
        for event_name_str in ("ShortcutOverride", "KeyPress"):
            send_key(receiver, event_name_str, "Key_X")
        self.process_events()
        self.assertEqual(self.main_window.current_plot_tool(),
                         DELTA_X_TOOL_STR)
        plot_widget = window.page().plot_widget_list[0]
        self.assertEqual(plot_widget.plot_tool_str, DELTA_X_TOOL_STR)
        send_key(receiver, "KeyRelease", "Key_X")
        self.process_events()
        self.assertEqual(self.main_window.current_plot_tool(), NO_TOOL_STR)

    @covers("LLFR-01036", "LLFR-00370", "HLFR-00137")
    def test_escape_in_a_window(self) -> None:
        """Esc switches off the plot tool while a window is active.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        from controller.plot_tools import NO_TOOL_STR, ZOOM_TOOL_STR
        _, _, window = self.two_tabs_one_undocked()
        self.main_window.top_panel.plot_tool_button_dict[
            ZOOM_TOOL_STR].click()
        self.process_events()
        with mock.patch.object(QApplication, "activeWindow",
                               return_value=window):
            self.main_window.on_escape_key()
        self.assertEqual(self.main_window.current_plot_tool(), NO_TOOL_STR)

    @covers("LLFR-01036", "LLFR-00207", "HLFR-00137")
    def test_zero_key_in_a_window(self) -> None:
        """The 0 key pressed in a window resets the zoom.

        Inputs: none.
        Outputs: none.
        """
        _, _, window = self.two_tabs_one_undocked()
        with mock.patch.object(self.main_window,
                               "reset_zoom_handler") as reset:
            for event_name_str in ("ShortcutOverride", "KeyPress"):
                send_key(window.pane_widget, event_name_str, "Key_0")
            send_key(window.pane_widget, "KeyRelease", "Key_0")
            self.process_events()
        self.assertTrue(reset.called)


class PanelWidthUndoTest(UndockedWindowTestCase):
    """Undo of a panel border drag (HLFR-00131)."""

    @covers("LLFR-01020", "LLFR-00073", "HLFR-00131", "HLFR-00026")
    def test_main_window_border_drag_is_undone(self) -> None:
        """A drag of the main border is one undoable action.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.show()
        self.process_events()
        splitter = self.main_window.lower_splitter
        start_i = splitter.last_widget_width()
        splitter.start_drag()
        total_i = sum(splitter.sizes())
        splitter.setSizes([total_i - start_i - 60, start_i + 60])
        splitter.finish_drag()
        self.process_events()
        self.assertTrue(self.plot_controller.undo_history.can_undo())
        self.plot_controller.on_undo()
        self.process_events()
        self.assertAlmostEqual(splitter.last_widget_width(), start_i,
                               delta=2)

    @covers("LLFR-01020", "LLFR-01021", "HLFR-00131")
    def test_window_border_drag_and_resize(self) -> None:
        """A window border drag is undoable; a window resize is not.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, window = self.two_tabs_one_undocked()
        window.resize(900, 500)
        window.signal_list_button.click()
        self.process_events()
        depth_i = self.plot_controller.undo_history.depth()
        window.resize(1000, 520)
        self.process_events()
        self.assertEqual(self.plot_controller.undo_history.depth(), depth_i)
        start_i = window.panel_width()
        window.splitter.start_drag()
        total_i = sum(window.splitter.sizes())
        window.splitter.setSizes([total_i - start_i - 50, start_i + 50])
        window.splitter.finish_drag()
        self.process_events()
        self.assertEqual(self.plot_controller.undo_history.depth(),
                         depth_i + 1)
        self.plot_controller.on_undo()
        self.process_events()
        self.assertAlmostEqual(self.main_window.undocked_window(
            second_id_i).panel_width(), start_i, delta=2)


class UndockedExportTest(UndockedWindowTestCase):
    """The PDF holds the undocked tabs after the docked ones."""

    @covers("LLFR-00129", "LLFR-01056", "HLFR-00038")
    def test_export_order(self) -> None:
        """The pages follow the tab order: docked, then undocked.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.main_window.show()
        first_id_i = self.panel.current_tab_id()
        self.main_window.signal_double_click_handler("speed")
        second_id_i = self.add_tab()
        self.main_window.signal_double_click_handler("force")
        third_id_i = self.add_tab()
        self.main_window.signal_double_click_handler("angle")
        self.process_events()
        self.undock(first_id_i)
        page_list = plot_export.exportable_page_list(
            self.panel.tab_widget, self.main_window.undocked_page_list())
        self.assertEqual([page.tab_id_i for page in page_list],
                         [second_id_i, third_id_i, first_id_i])
        self.assertEqual(self.main_window.exportable_tab_count(), 3)


class LayoutWindowsViewTest(UndockedWindowTestCase):
    """The windows of a layout file (HLFR-00139 to HLFR-00141)."""

    @covers("LLFR-01041", "LLFR-01043", "LLFR-01048", "HLFR-00140",
            "HLFR-00141", "HLFR-00139", "HLFR-00050", "HLFR-00049")
    def test_saved_layout_opens_its_windows(self) -> None:
        """Saving and loading opens the undocked tab in a window; a
        window saved off-screen comes back on the screen.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, window = self.two_tabs_one_undocked()
        window.signal_list_button.click()
        window.move(10, 20)
        self.process_events()
        layout_dict = self.plot_controller.layout_dict()
        tab_entry = layout_dict["tabs"][-1]
        self.assertTrue(tab_entry["undocked"])
        self.assertTrue(tab_entry["signal_list_panel"]["shown"])
        # Saved on a screen that is no longer there.
        tab_entry["window"]["x"] = 50000
        tab_entry["window"]["y"] = 50000
        # The user closes the window, which deletes its tab.
        window.close()
        self.process_events()
        self.assertIsNone(self.tab(second_id_i))
        self.plot_controller.load_layout(layout_dict)
        self.process_events()
        self.assertEqual(len(self.main_window.undocked_window_dict), 1)
        loaded = next(iter(self.main_window.undocked_window_dict.values()))
        self.assertTrue(loaded.is_panel_shown())
        area_tuple = self.main_window.main_screen_area()
        self.assertGreaterEqual(loaded.x(), area_tuple[0])
        self.assertLessEqual(loaded.x() + loaded.width(),
                             area_tuple[0] + area_tuple[2])
        self.assertEqual(len(loaded.page().plot_widget_list), 1)


if __name__ == "__main__":
    unittest.main()
