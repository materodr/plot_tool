"""Qt tests for the undocked windows (#205, step 3).

A real MainWindow and MainController are used (the setup of
test_plot_panel). They check the undock button of each tab
(HLFR-00124), the parts of an undocked window (HLFR-00126, HLFR-00135 to
HLFR-00137), docking (HLFR-00125), closing a window (HLFR-00139), the
signal list panels of the windows (HLFR-00128 to HLFR-00131), the
shortcuts in a window (HLFR-00138), the one undo history (HLFR-00133,
HLFR-00134, HLFR-00132), the export of undocked tabs (HLFR-00038) and
the windows of a layout file (HLFR-00140 to HLFR-00142).

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
        return self.main_window.window_of_tab(tab_id_i)

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

    def user_close(self, window) -> None:
        """Close a window as the system's close button does.

        Inputs:
            window: the UndockedWindow.
        Outputs: none. The close event is spontaneous, as one sent by
            the window system.
        """
        event = mock.Mock()
        event.spontaneous.return_value = True
        window.closeEvent(event)
        event.ignore.assert_called_once_with()
        self.process_events()

    def tab(self, tab_id_i: int):
        """Return a tab of the model.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: the Tab, or None.
        """
        return self.plot_controller.workspace.find_tab(tab_id_i)


class UndockButtonTest(UndockedWindowTestCase):
    """The undock button of the tabs (HLFR-00124)."""

    @covers("LLFR-01012", "LLFR-01014", "LLFR-01013", "HLFR-00124")
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

    @covers("LLFR-01018", "LLFR-01019", "LLFR-01034", "LLFR-01155",
            "HLFR-00127")
    def test_last_docked_tab_cannot_be_undocked(self) -> None:
        """No undock button at all with one docked tab, and no room for
        one; any number of windows else.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QTabBar
        tab_bar = self.panel.tab_widget.tabBar()
        first_id_i = self.panel.current_tab_id()
        self.assertIsNone(tab_bar.tabButton(
            0, QTabBar.ButtonPosition.RightSide))
        self.assertFalse(self.panel.undock_button_of(first_id_i).isVisible())
        alone_width_i = tab_bar.tabRect(0).width()
        self.panel.request_undock(first_id_i)
        self.process_events()
        self.assertIsNone(self.main_window.window_of_tab(first_id_i))
        id_list = [self.add_tab() for _ in range(3)]
        self.assertIs(tab_bar.tabButton(0, QTabBar.ButtonPosition.RightSide),
                      self.panel.undock_button_of(first_id_i))
        # LLFR-01155: the tab grows to make room for its button.
        self.assertGreater(tab_bar.tabRect(0).width(), alone_width_i)
        for tab_id_i in id_list:
            self.assertIsNotNone(self.undock(tab_id_i))
        self.assertEqual(len(self.main_window.undocked_window_dict), 3)
        self.assertIsNone(tab_bar.tabButton(
            0, QTabBar.ButtonPosition.RightSide))

    @covers("LLFR-01015", "LLFR-01020", "LLFR-01016", "LLFR-01128",
            "LLFR-01083", "LLFR-01084", "HLFR-00124", "HLFR-00126")
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

    @covers("LLFR-01017")
    def test_main_window_shows_the_nearest_docked_tab(self) -> None:
        """After the shown tab is undocked, the tab to its left is shown.

        Inputs: none.
        Outputs: none.
        """
        first_id_i, second_id_i, _ = self.two_tabs_one_undocked()
        self.assertEqual(self.panel.current_tab_id(), first_id_i)


class WindowPartsTest(UndockedWindowTestCase):
    """The parts of an undocked window."""

    @covers("LLFR-01061", "LLFR-01062", "LLFR-01063", "LLFR-01066",
            "LLFR-01130", "LLFR-01025", "HLFR-00135", "HLFR-00136")
    def test_title_and_tab_button(self) -> None:
        """Titled with the tab name, which follows a rename; a tab row
        of one tab, selected, with its dock button inside it.

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
        self.assertIs(window.tab_bar.tabButton(
            0, QTabBar.ButtonPosition.RightSide),
            window.dock_button_of(second_id_i))
        self.plot_controller.on_rename_tab(second_id_i, "Engine")
        self.assertEqual(window.windowTitle(), "Engine")
        self.assertEqual(window.tab_bar.tabText(0), "Engine")
        self.plot_controller.on_undo()
        self.process_events()
        self.assertEqual(self.main_window.window_of_tab(
            second_id_i).windowTitle(), name_str)

    def x_in_window(self, window, widget) -> int:
        """Return the left edge of a widget in window coordinates.

        Inputs:
            window: the UndockedWindow.
            widget: a widget of the window.
        Outputs: the x of its left edge.
        """
        from PyQt6.QtCore import QPoint
        return widget.mapTo(window, QPoint(0, 0)).x()

    def y_in_window(self, window, widget) -> int:
        """Return the top edge of a widget in window coordinates.

        Inputs:
            window: the UndockedWindow.
            widget: a widget of the window.
        Outputs: the y of its top edge.
        """
        from PyQt6.QtCore import QPoint
        return widget.mapTo(window, QPoint(0, 0)).y()

    @covers("LLFR-01032", "LLFR-01025", "LLFR-01044", "LLFR-01027",
            "LLFR-01026", "LLFR-01070", "LLFR-01035", "LLFR-00440",
            "LLFR-01031", "HLFR-00137", "HLFR-00126")
    def test_tab_row_and_panels(self) -> None:
        """The tab with its dock button inside it in the plot panel's tab
        row, the signal list button at the window's top right; the plot
        panel and the signal list panel side by side, their tops level,
        no top panel.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        from view.top_panel import TopPanel
        _, second_id_i, window = self.two_tabs_one_undocked()
        window.resize(700, 500)
        self.process_events()
        dock_button = window.dock_button_of(second_id_i)
        self.assertEqual(dock_button.toolTip(), "Dock")
        self.assertFalse(dock_button.icon().isNull())
        # LLFR-01025: inside the tab, never in the tab row beside it.
        self.assertIs(dock_button.parentWidget(), window.tab_bar)
        list_x_i = self.x_in_window(window, window.signal_list_button)
        tab_x_i = self.x_in_window(window, window.tab_bar)
        self.assertLess(tab_x_i, list_x_i)
        # LLFR-01044: the signal list button at the top-right corner.
        self.assertEqual(list_x_i + window.signal_list_button.width(),
                         window.width() - theme.WINDOW_MARGIN_I)
        self.assertLess(self.y_in_window(window, window.signal_list_button),
                        self.y_in_window(window, window.pane_widget))
        self.assertIs(window.tab_bar.parentWidget(), window.tab_row)
        self.assertIs(window.signal_list_button.parentWidget(), window)
        # LLFR-01070: the plot panel (tab row above the well) and the
        # signal list panel side by side, level at their tops.
        self.assertIs(window.splitter.widget(0), window.plot_column)
        self.assertIs(window.splitter.widget(1), window.signal_list_panel)
        self.assertLess(self.y_in_window(window, window.tab_row),
                        self.y_in_window(window, window.pane_widget))
        window.signal_list_button.click()
        self.process_events()
        self.assertEqual(self.y_in_window(window, window.tab_row),
                         self.y_in_window(window, window.signal_list_panel))
        self.assertEqual(window.findChildren(TopPanel), [])
        # LLFR-01157: the tabs can be dragged to reorder them.
        self.assertTrue(window.tab_bar.isMovable())
        self.assertEqual(window.pane_widget.count(), 1)

    @covers("LLFR-01050", "LLFR-01047", "LLFR-01048", "LLFR-01049",
            "LLFR-01046", "LLFR-01051", "LLFR-01053", "HLFR-00130")
    def test_signal_list_button_hides_and_shows_the_panel(self) -> None:
        """Hidden at start; the button shows it at 20% of the window's
        width, hides it, and both are undone.

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
        expected_i = int(round(window.width() * 0.20))
        self.assertAlmostEqual(window.panel_width(), expected_i, delta=3)
        window.signal_list_button.click()
        self.process_events()
        self.assertFalse(window.is_panel_shown())
        self.assertEqual(window.plot_column.width(),
                         window.splitter.width())
        self.plot_controller.on_undo()
        self.process_events()
        window = self.main_window.window_of_tab(second_id_i)
        self.assertTrue(window.is_panel_shown())
        self.plot_controller.on_undo()
        self.process_events()
        self.assertFalse(self.main_window.window_of_tab(
            second_id_i).is_panel_shown())

    @covers("LLFR-01211", "LLFR-01212", "LLFR-01047", "LLFR-01048",
            "LLFR-01049", "LLFR-01171", "LLFR-01046", "LLFR-01134",
            "LLFR-01213", "LLFR-01053", "HLFR-00131")
    def test_main_window_signal_list_button(self) -> None:
        """The main window starts with its panel shown and a checked
        signal list button at the top right; a click hides the panel,
        the plot panel takes the width, the tab row keeps room for the
        button, which does not move; a second click shows the panel at
        its width; both are undoable.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        self.main_window.resize(1100, 700)
        self.main_window.show()
        self.process_events()
        main_button = self.main_window.main_panel_button
        button = main_button.button
        self.assertTrue(self.main_window.signal_list_panel.isVisible())
        self.assertTrue(button.isVisible())
        self.assertTrue(button.isChecked())
        self.assertEqual(button.toolTip(), "Hide signal list")
        splitter = self.main_window.lower_splitter
        right_i = splitter.mapTo(self.main_window, splitter.rect()
                                 .topRight()).x()
        place_before = button.mapTo(self.main_window,
                                    button.rect().topLeft())
        self.assertLessEqual(abs(place_before.x() + button.width() - 1
                                 - right_i), 1)
        width_i = self.main_window.main_panel_width()
        self.assertGreater(width_i, 1)
        button.click()
        self.process_events()
        self.assertFalse(self.main_window.signal_list_panel.isVisible())
        self.assertFalse(self.main_window.is_main_panel_shown())
        self.assertFalse(button.isChecked())
        self.assertEqual(button.toolTip(), "Show signal list")
        self.assertGreaterEqual(self.panel.width(), splitter.width() - 1)
        self.assertEqual(self.panel.tab_widget.reserved_right_width_i,
                         theme.SIDEBAR_BUTTON_SIZE_I + theme.TAB_SPACING_I)
        self.assertEqual(button.mapTo(self.main_window,
                                      button.rect().topLeft()),
                         place_before)
        # LLFR-01048: the hidden panel keeps its width.
        self.assertEqual(self.main_window.main_panel_width(), width_i)
        button.click()
        self.process_events()
        self.assertTrue(self.main_window.signal_list_panel.isVisible())
        self.assertEqual(self.main_window.main_panel_width(), width_i)
        self.assertEqual(self.panel.tab_widget.reserved_right_width_i, 0)
        # LLFR-01053: one undo hides it again, another shows it.
        self.plot_controller.on_undo()
        self.process_events()
        self.assertFalse(self.main_window.is_main_panel_shown())
        self.plot_controller.on_undo()
        self.process_events()
        self.assertTrue(self.main_window.is_main_panel_shown())
        self.plot_controller.on_redo()
        self.process_events()
        self.assertFalse(self.main_window.is_main_panel_shown())

    @covers("LLFR-01141", "LLFR-01052", "HLFR-00131", "HLFR-00033")
    def test_search_shortcut_shows_the_main_panel(self) -> None:
        """Ctrl+F (Cmd+F) with the main window's panel hidden shows it
        first and puts the focus in its search box.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.show()
        self.process_events()
        self.main_window.main_panel_button.button.click()
        self.process_events()
        self.assertFalse(self.main_window.is_main_panel_shown())
        self.main_window._on_search_shortcut(-1)
        self.process_events()
        self.assertTrue(self.main_window.is_main_panel_shown())

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
    """The tab button of a window works as a tab (HLFR-00136)."""

    @covers("LLFR-01064", "LLFR-01069", "LLFR-01068", "LLFR-01145",
            "HLFR-00136", "HLFR-00016")
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
        self.assertIsNone(self.main_window.window_of_tab(second_id_i))
        self.plot_controller.on_undo()
        self.process_events()
        self.assertIsNotNone(self.main_window.window_of_tab(second_id_i))

    @covers("LLFR-01065", "LLFR-01067", "HLFR-00136", "HLFR-00017")
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

    @covers("LLFR-01028", "LLFR-01029", "LLFR-01030", "LLFR-01020",
            "HLFR-00125")
    def test_dock_button_puts_the_tab_back(self) -> None:
        """The tab is the last docked tab, shown, and its window closes.

        Inputs: none.
        Outputs: none.
        """
        first_id_i, second_id_i, window = self.two_tabs_one_undocked()
        page = window.page()
        window.dock_button_of(second_id_i).click()
        self.process_events()
        self.assertIsNone(self.main_window.window_of_tab(second_id_i))
        tab_widget = self.panel.tab_widget
        self.assertEqual(tab_widget.indexOf(page), tab_widget.count() - 1)
        self.assertEqual(self.panel.current_tab_id(), second_id_i)
        self.assertEqual(len(page.plot_widget_list), 1)
        self.assertIsNotNone(self.panel.undock_button_of(second_id_i))
        self.plot_controller.on_undo()
        self.process_events()
        self.assertIsNotNone(self.main_window.window_of_tab(second_id_i))

    @covers("LLFR-01073", "LLFR-01074", "LLFR-01059", "LLFR-01129",
            "HLFR-00139", "HLFR-00134")
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
        self.user_close(window)
        self.assertIsNone(self.tab(second_id_i))
        self.assertIsNone(self.main_window.window_of_tab(second_id_i))
        self.plot_controller.on_undo()
        self.process_events()
        window = self.main_window.window_of_tab(second_id_i)
        self.assertEqual((window.x(), window.y()), place_tuple)
        self.assertTrue(window.is_panel_shown())
        self.assertEqual(len(window.page().plot_widget_list), 1)

    @covers("LLFR-01024", "LLFR-01073", "HLFR-00139", "HLFR-00124")
    def test_quit_closes_the_windows_and_keeps_the_tabs(self) -> None:
        """A quit closes every undocked window first, keeps their tabs
        and the undo history, and lets the quit go on.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent
        _, second_id_i, _ = self.two_tabs_one_undocked()
        third_id_i = self.add_tab()
        self.undock(third_id_i)
        history = self.plot_controller.undo_history
        depth_tuple = (history.depth(), history.redo_depth())
        consumed_b = self.main_window.quit_filter.eventFilter(
            self.application, QEvent(QEvent.Type.Quit))
        self.process_events()
        self.assertFalse(consumed_b)
        self.assertEqual(self.main_window.undocked_window_dict, {})
        self.assertIsNotNone(self.tab(second_id_i))
        self.assertIsNotNone(self.tab(third_id_i))
        self.assertTrue(self.tab(second_id_i).undocked_b)
        self.assertEqual((history.depth(), history.redo_depth()),
                         depth_tuple)

    @covers("LLFR-01024", "LLFR-01073")
    def test_close_not_by_the_user_keeps_the_tab(self) -> None:
        """A close that the window system did not send (as Qt's close of
        every window on a quit) closes the window and keeps the tab.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QCloseEvent
        _, second_id_i, window = self.two_tabs_one_undocked()
        event = QCloseEvent()
        self.assertFalse(event.spontaneous())
        window.closeEvent(event)
        self.process_events()
        self.assertTrue(event.isAccepted())
        self.assertIsNotNone(self.tab(second_id_i))
        self.assertTrue(self.plot_controller.undo_history.depth() > 0)

    @covers("LLFR-01073")
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

    @covers("LLFR-01024", "LLFR-01021", "HLFR-00124")
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

    @covers("LLFR-01033", "HLFR-00126", "HLFR-00118")
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
    """The signal list panels of the windows (HLFR-00128, HLFR-00129)."""

    @covers("LLFR-01036", "LLFR-01043", "HLFR-00128", "HLFR-00011")
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

    @covers("LLFR-01041", "LLFR-01042", "LLFR-01052", "LLFR-01043",
            "HLFR-00129")
    def test_search_text_in_every_search_box(self) -> None:
        """Typing in one box puts the text in the others, hidden panels
        included, and leaves the cursor in the typed box.

        Inputs: none.
        Outputs: none.
        """
        _, _, window = self.two_tabs_one_undocked()
        from PyQt6.QtWidgets import QApplication
        main_box = self.main_window.signal_list_panel.search_box
        window_box = window.signal_list_panel.search_box
        window.signal_list_button.click()
        window.activateWindow()
        window_box.setFocus()
        self.process_events()
        focus_before = QApplication.focusWidget()
        window_box.insert("spe")
        window_box.setCursorPosition(1)
        self.process_events()
        self.assertEqual(main_box.text(), "spe")
        self.assertEqual(window_box.cursorPosition(), 1)
        # The keyboard focus stays where it was, in the typed box when
        # the window system gave it the focus.
        self.assertIs(QApplication.focusWidget(), focus_before)
        self.assertFalse(main_box.hasFocus())
        if focus_before is not None:
            self.assertIs(focus_before, window_box)
        main_box.setText("for")
        self.assertEqual(window_box.text(), "for")
        self.assertEqual(window.signal_list_panel.signal_name_list(),
                         self.main_window.signal_list_panel
                         .signal_name_list())
        third_id_i = self.add_tab()
        new_window = self.undock(third_id_i)
        self.assertEqual(new_window.signal_list_panel.search_text(), "for")

    @covers("LLFR-01038", "LLFR-01037", "LLFR-00019", "LLFR-00295",
            "LLFR-01040", "HLFR-00128", "HLFR-00012", "HLFR-00064")
    def test_plots_from_a_window_panel_go_into_its_tab(self) -> None:
        """A double-click and Enter in the window's panel plot in the
        window's tab; each panel has its own selection.

        Inputs: none.
        Outputs: none.
        """
        first_id_i, second_id_i, window = self.two_tabs_one_undocked()
        self.main_window.show_signal_names(["Time", "speed", "force"])
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

    @covers("LLFR-01023", "HLFR-00124", "HLFR-00002")
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
        with mock.patch.object(QApplication, "activeWindow",
                               return_value=self.main_window):
            self.assertIs(self.main_window.dialog_parent(),
                          self.main_window)


class WindowShortcutTest(UndockedWindowTestCase):
    """The shortcuts and the plot tool in a window (HLFR-00138)."""

    @covers("LLFR-01071", "LLFR-01058", "LLFR-01057", "HLFR-00138",
            "HLFR-00133")
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
        window = self.main_window.window_of_tab(second_id_i)
        self.assertIsNotNone(window)
        window.undo_shortcut.activated.emit()
        self.process_events()
        window_redo = self.main_window.undocked_window_dict
        self.assertEqual(window_redo, {})

    @covers("LLFR-01071", "LLFR-01072", "HLFR-00138", "HLFR-00032")
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

    @covers("LLFR-01071", "LLFR-00370", "HLFR-00138")
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

    @covers("LLFR-01071", "LLFR-00207", "HLFR-00138")
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
    """Undo of a panel border drag (HLFR-00132)."""

    @covers("LLFR-01055", "LLFR-00073", "HLFR-00132", "HLFR-00026")
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

    @covers("LLFR-01055", "LLFR-01056", "HLFR-00132")
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
        self.assertAlmostEqual(self.main_window.window_of_tab(
            second_id_i).panel_width(), start_i, delta=2)

    @covers("LLFR-01195", "LLFR-01048", "LLFR-01047", "HLFR-00130")
    def test_panel_shown_again_fits_a_narrower_window(self) -> None:
        """A panel hidden at a width that the window, made narrower
        since, can no longer hold is shown again at most at the
        window's width minus 100 pixels.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, window = self.two_tabs_one_undocked()
        window.resize(900, 500)
        window.signal_list_button.click()
        self.process_events()
        window.set_panel(True, 600)
        self.process_events()
        self.assertAlmostEqual(window.panel_width(), 600, delta=3)
        window.signal_list_button.click()
        self.process_events()
        self.assertFalse(window.is_panel_shown())
        window.resize(500, 500)
        self.process_events()
        window.signal_list_button.click()
        self.process_events()
        window = self.main_window.window_of_tab(second_id_i)
        self.assertTrue(window.is_panel_shown())
        self.assertGreaterEqual(window.panel_width(), 1)
        self.assertLessEqual(window.panel_width(), window.width() - 100)
        # A width the window holds is kept.
        window.set_panel(True, 200)
        self.process_events()
        self.assertAlmostEqual(window.panel_width(), 200, delta=3)


class WindowPlotActionTest(UndockedWindowTestCase):
    """Plot actions and drops on the plots of a window."""

    @covers("LLFR-01039", "LLFR-01022", "LLFR-00021", "HLFR-00128",
            "HLFR-00013", "HLFR-00124")
    def test_drop_and_delete_on_a_plot_of_a_window(self) -> None:
        """A drop on a window's plot adds the curves; its plot menu
        deletes it; both are undone like in the main window.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, window = self.two_tabs_one_undocked()
        plot_widget = window.page().plot_widget_list[0]
        plot_widget.signals_dropped.emit(["force", "angle"])
        self.process_events()
        plot = self.tab(second_id_i).plot_list[0]
        self.assertEqual([curve.signal_name_str
                          for curve in plot.curve_list],
                         ["speed", "force", "angle"])
        plot_widget.plot_delete_requested.emit()
        self.process_events()
        self.assertEqual(self.tab(second_id_i).plot_list, [])
        self.assertEqual(window.page().plot_widget_list, [])
        self.plot_controller.on_undo()
        self.process_events()
        self.assertEqual(len(self.main_window.window_of_tab(
            second_id_i).page().plot_widget_list), 1)


def send_mouse(receiver, type_name_str: str, global_point,
               buttons_name_str: str = "LeftButton",
               button_name_str: str = "LeftButton") -> None:
    """Send one mouse event to a widget at a desktop point.

    Inputs:
        receiver: the QWidget the event is sent to.
        type_name_str: name of a QEvent.Type, e.g. "MouseButtonPress".
        global_point: the QPoint of the pointer on the desktop.
        buttons_name_str: name of the Qt.MouseButton held.
        button_name_str: name of the Qt.MouseButton that changed.
    Outputs: none. The shared mouse pointer is not moved.
    """
    from PyQt6.QtCore import QEvent, QPointF, Qt
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtWidgets import QApplication
    event = QMouseEvent(
        getattr(QEvent.Type, type_name_str),
        QPointF(receiver.mapFromGlobal(global_point)),
        QPointF(global_point), getattr(Qt.MouseButton, button_name_str),
        getattr(Qt.MouseButton, buttons_name_str),
        Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(receiver, event)


def drag(receiver, start_point, end_point) -> None:
    """Press at one desktop point, move and release at another.

    Inputs:
        receiver: the QWidget that gets the three events.
        start_point: the QPoint of the press.
        end_point: the QPoint of the move and the release.
    Outputs: none.
    """
    from PyQt6.QtCore import QPoint
    send_mouse(receiver, "MouseButtonPress", start_point)
    middle_point = QPoint((start_point.x() + end_point.x()) // 2,
                          (start_point.y() + end_point.y()) // 2)
    for point in (middle_point, end_point):
        send_mouse(receiver, "MouseMove", point, "LeftButton", "NoButton")
    send_mouse(receiver, "MouseButtonRelease", end_point, "NoButton")


class SignalListButtonPlaceTest(UndockedWindowTestCase):
    """The signal list button works like Firefox's sidebar button."""

    def button_rect(self, window):
        """Return the button's rectangle on the desktop.

        Inputs:
            window: the UndockedWindow.
        Outputs: a QRect.
        """
        from PyQt6.QtCore import QPoint, QRect
        button = window.signal_list_button
        return QRect(button.mapToGlobal(QPoint(0, 0)), button.size())

    @covers("LLFR-01134", "LLFR-01044", "HLFR-00130")
    def test_button_never_moves(self) -> None:
        """Hiding and showing the panel, by the button or by undo, leave
        the button at the same place on the screen.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, window = self.two_tabs_one_undocked()
        window.resize(800, 500)
        self.process_events()
        hidden_rect = self.button_rect(window)
        window.signal_list_button.click()
        self.process_events()
        self.assertTrue(window.is_panel_shown())
        self.assertEqual(self.button_rect(window), hidden_rect)
        window.signal_list_button.click()
        self.process_events()
        self.assertEqual(self.button_rect(window), hidden_rect)
        self.plot_controller.on_undo()
        self.process_events()
        window = self.main_window.window_of_tab(second_id_i)
        self.assertTrue(window.is_panel_shown())
        self.assertEqual(self.button_rect(window), hidden_rect)

    @covers("LLFR-01133", "LLFR-01135", "LLFR-00894", "HLFR-00130",
            "HLFR-00128")
    def test_button_in_the_title_row_level_with_signals(self) -> None:
        """While shown, the button is at the right end of the "Signals"
        row, level with the word, which is at least as high as the
        button; the list still starts level with the plots.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        _, _, window = self.two_tabs_one_undocked()
        window.resize(800, 500)
        window.signal_list_button.click()
        self.process_events()
        window.search_box_aligner.align()
        self.process_events()
        panel = window.signal_list_panel
        title = panel.title_label
        button = window.signal_list_button
        self.assertGreaterEqual(title.height(), button.height())
        content_rect = title.contentsRect()
        text_center_y = title.mapToGlobal(QPoint(
            0, content_rect.center().y())).y()
        button_center_y = button.mapToGlobal(QPoint(
            0, button.height() // 2)).y()
        self.assertLessEqual(abs(text_center_y - button_center_y), 3)
        panel_right_x = panel.mapToGlobal(QPoint(panel.width(), 0)).x()
        button_right_x = button.mapToGlobal(QPoint(button.width(), 0)).x()
        self.assertLessEqual(abs(panel_right_x - button_right_x), 1)
        self.assertGreaterEqual(button.mapToGlobal(QPoint(0, 0)).x(),
                                title.mapToGlobal(QPoint(0, 0)).x())
        self.assertLessEqual(
            abs(window.search_box_aligner.list_top_offset_px()), 2)

    @covers("LLFR-01049", "LLFR-01171", "LLFR-01045", "HLFR-00130",
            "HLFR-00003")
    def test_round_pale_highlight_while_shown(self) -> None:
        """Checked with a round, pale highlight and a dark icon while
        the panel is shown; no highlight while it is hidden.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor, QIcon
        from view import theme, undocked_window
        _, _, window = self.two_tabs_one_undocked()
        button = window.signal_list_button
        sheet_str = undocked_window.signal_list_button_style_sheet()
        self.assertIn(f"border-radius: {button.width() // 2}px", sheet_str)
        self.assertIn(theme.SIDEBAR_BUTTON_ACTIVE_COLOR_STR, sheet_str)
        self.assertEqual(button.width(), button.height())
        self.assertFalse(button.isChecked())
        engine_icon = button.icon()
        on_image = engine_icon.pixmap(20, 20, QIcon.Mode.Normal,
                                      QIcon.State.On).toImage()
        off_image = engine_icon.pixmap(20, 20, QIcon.Mode.Normal,
                                       QIcon.State.Off).toImage()
        self.assertEqual(on_image, off_image)
        button.click()
        self.process_events()
        self.assertTrue(button.isChecked())
        image = button.grab().toImage()
        top_middle = QColor(image.pixel(image.width() // 2, 2))
        self.assertEqual(top_middle.name(),
                         theme.SIDEBAR_BUTTON_ACTIVE_COLOR_STR)
        button.click()
        self.process_events()
        self.assertFalse(button.isChecked())
        image = button.grab().toImage()
        top_middle = QColor(image.pixel(image.width() // 2, 2))
        self.assertNotEqual(top_middle.name(),
                            theme.SIDEBAR_BUTTON_ACTIVE_COLOR_STR)

    @covers("LLFR-01032", "LLFR-01025", "HLFR-00126")
    def test_room_for_the_button_while_hidden(self) -> None:
        """While hidden, the tab row keeps room for the signal list
        button at its right end; while shown, the tab row ends at the
        panel.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        _, _, window = self.two_tabs_one_undocked()
        window.resize(800, 500)
        self.process_events()
        self.assertTrue(window.button_space.isVisibleTo(window))
        row_right_x = window.tab_row.mapToGlobal(
            QPoint(window.tab_row.width(), 0)).x()
        button_x = window.signal_list_button.mapToGlobal(QPoint(0, 0)).x()
        self.assertGreaterEqual(row_right_x, button_x)
        window.signal_list_button.click()
        self.process_events()
        self.assertFalse(window.button_space.isVisibleTo(window))
        row_right_x = window.tab_row.mapToGlobal(
            QPoint(window.tab_row.width(), 0)).x()
        panel_x = window.signal_list_panel.mapToGlobal(QPoint(0, 0)).x()
        self.assertLess(row_right_x, panel_x)


class DragUndockDockViewTest(UndockedWindowTestCase):
    """Undock and dock a tab by dragging it, like a browser."""

    def outside_point(self):
        """Return a desktop point right of the main window.

        Inputs: none.
        Outputs: a QPoint outside the main window's frame.
        """
        from PyQt6.QtCore import QPoint
        frame = self.main_window.frameGeometry()
        return QPoint(frame.right() + 60, frame.top() + 40)

    def tab_center(self, index_i: int):
        """Return the desktop point of the middle of a docked tab.

        Inputs:
            index_i: the place of the tab in the main tab row.
        Outputs: a QPoint.
        """
        tab_bar = self.panel.tab_widget.tabBar()
        return tab_bar.mapToGlobal(tab_bar.tabRect(index_i).center())

    @covers("LLFR-01142", "LLFR-01050", "LLFR-01083", "LLFR-01060",
            "HLFR-00153", "HLFR-00124")
    def test_drop_outside_the_main_window_undocks(self) -> None:
        """A tab dragged out of the tab row and dropped outside the main
        window opens in a window at the drop point (kept on a screen),
        with a hidden panel; the other tabs keep their order; undoable.

        Inputs: none.
        Outputs: none.
        """
        from model.window_placement import placed_window_tuple
        self.main_window.show()
        first_id_i = self.panel.current_tab_id()
        second_id_i = self.add_tab()
        third_id_i = self.add_tab()
        self.process_events()
        drop_point = self.outside_point()
        expected_tuple = placed_window_tuple(
            self.main_window.dropped_window_tuple(drop_point.x(),
                                                  drop_point.y()),
            self.main_window.screen_area_list(),
            self.main_window.main_screen_area())
        drag(self.panel.tab_widget.tabBar(), self.tab_center(1),
             drop_point)
        self.process_events()
        window = self.main_window.window_of_tab(second_id_i)
        self.assertIsNotNone(window)
        self.assertFalse(window.is_panel_shown())
        self.assertEqual(window.window_tuple(), tuple(expected_tuple))
        self.assertEqual([self.panel.tab_id_at_index(index_i)
                          for index_i in range(2)],
                         [first_id_i, third_id_i])
        self.plot_controller.on_undo()
        self.process_events()
        self.assertIsNone(self.main_window.window_of_tab(second_id_i))
        self.assertEqual([self.panel.tab_id_at_index(index_i)
                          for index_i in range(3)],
                         [first_id_i, second_id_i, third_id_i])

    @covers("LLFR-01142", "LLFR-01088", "LLFR-01087", "HLFR-00153",
            "HLFR-00143")
    def test_drop_inside_the_main_window_does_not_undock(self) -> None:
        """A drop inside the main window, off the tab row, only moves the
        tab in the row.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.main_window.show()
        self.add_tab()
        self.process_events()
        inside_point = self.panel.mapToGlobal(QPoint(
            self.panel.width() // 2, self.panel.height() // 2))
        tab_id_i = self.panel.tab_id_at_index(1)
        self.panel.finish_tab_drag(tab_id_i, 1, (inside_point.x(),
                                                 inside_point.y()))
        self.process_events()
        self.assertEqual(self.main_window.undocked_window_dict, {})
        self.assertFalse(self.tab(tab_id_i).undocked_b)

    @covers("LLFR-01144", "HLFR-00153")
    def test_last_docked_tab_stays(self) -> None:
        """The last docked tab dropped outside stays docked, with no
        undo record.

        Inputs: none.
        Outputs: none.
        """
        first_id_i, second_id_i, _ = self.two_tabs_one_undocked()
        depth_i = self.plot_controller.undo_history.depth()
        drop_point = self.outside_point()
        self.panel.finish_tab_drag(first_id_i, 0, (drop_point.x(),
                                                   drop_point.y()))
        self.process_events()
        self.assertFalse(self.tab(first_id_i).undocked_b)
        self.assertEqual(list(self.main_window.undocked_window_dict),
                         [self.tab(second_id_i).window_id_i])
        self.assertEqual(self.plot_controller.undo_history.depth(), depth_i)

    @covers("LLFR-01143", "LLFR-01170", "LLFR-01029", "LLFR-01030",
            "LLFR-01060", "HLFR-00155", "HLFR-00125")
    def test_tab_dropped_on_the_tab_row_docks_there(self) -> None:
        """Dragging a window's tab onto the left half of the first
        docked tab docks it first, closes the window and shows it;
        undoable.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        first_id_i, second_id_i, window = self.two_tabs_one_undocked()
        tab_bar = self.panel.tab_widget.tabBar()
        first_rect = tab_bar.tabRect(0)
        drop_point = tab_bar.mapToGlobal(QPoint(first_rect.left() + 3,
                                                first_rect.center().y()))
        self.assertEqual(self.panel.docked_drop_index(drop_point.x(),
                                                      drop_point.y()), 0)
        start_point = window.tab_bar.mapToGlobal(
            window.tab_bar.tabRect(0).center())
        drag(window.tab_bar, start_point, drop_point)
        self.process_events()
        self.assertIsNone(self.main_window.window_of_tab(second_id_i))
        self.assertEqual([self.panel.tab_id_at_index(index_i)
                          for index_i in range(2)],
                         [second_id_i, first_id_i])
        self.assertEqual(self.panel.current_tab_id(), second_id_i)
        self.plot_controller.on_undo()
        self.process_events()
        self.assertIsNotNone(self.main_window.window_of_tab(second_id_i))

    @covers("LLFR-01143", "LLFR-01170", "HLFR-00155")
    def test_drop_index_between_the_tabs(self) -> None:
        """Right of the middle of the last tab, or on the "+" button and
        the empty row, is after the last docked tab.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.main_window.show()
        self.add_tab()
        self.process_events()
        tab_bar = self.panel.tab_widget.tabBar()
        second_rect = tab_bar.tabRect(1)
        point = tab_bar.mapToGlobal(QPoint(second_rect.left() + 2,
                                           second_rect.center().y()))
        self.assertEqual(self.panel.docked_drop_index(point.x(),
                                                      point.y()), 1)
        point = tab_bar.mapToGlobal(QPoint(second_rect.right() - 2,
                                           second_rect.center().y()))
        self.assertEqual(self.panel.docked_drop_index(point.x(),
                                                      point.y()), 2)
        row_rect = self.panel.tab_row_rect()
        point = QPoint(row_rect.right() - 5, row_rect.center().y())
        self.assertEqual(self.panel.docked_drop_index(point.x(),
                                                      point.y()), 2)

    @covers("LLFR-01067", "HLFR-00136", "HLFR-00155")
    def test_tab_button_dropped_elsewhere_changes_nothing(self) -> None:
        """A drop on the plots of the main window, or on the plots of
        its own window, leaves the tab, its window and the history
        unchanged.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        _, second_id_i, window = self.two_tabs_one_undocked()
        depth_i = self.plot_controller.undo_history.depth()
        start_point = window.tab_bar.mapToGlobal(
            window.tab_bar.tabRect(0).center())
        pane = window.pane_widget
        for drop_point in (self.panel.mapToGlobal(QPoint(
                self.panel.width() // 2, self.panel.height() // 2)),
                pane.mapToGlobal(QPoint(pane.width() // 2,
                                        pane.height() // 2))):
            drag(window.tab_bar, start_point, drop_point)
            self.process_events()
            self.assertIs(self.main_window.window_of_tab(second_id_i),
                          window)
            self.assertTrue(self.tab(second_id_i).undocked_b)
            self.assertEqual(self.plot_controller.undo_history.depth(),
                             depth_i)


class DropOutsideTheAppTest(UndockedWindowTestCase):
    """A tab of an undocked window dropped outside every app window."""

    def point_outside_the_app(self):
        """Return a desktop point right of every window of the app.

        Inputs: none.
        Outputs: a QPoint on no window of the app.
        """
        from PyQt6.QtCore import QPoint
        frame_list = [self.main_window.frameGeometry()] + [
            window.frameGeometry()
            for window in self.main_window.undocked_window_dict.values()]
        right_i = max(frame.right() for frame in frame_list)
        top_i = min(frame.top() for frame in frame_list)
        return QPoint(right_i + 60, top_i + 40)

    def drop_outside(self, window, tab_id_i: int):
        """Drop a tab of a window outside the app, as a drag ends.

        Inputs:
            window: the UndockedWindow the tab is dragged from.
            tab_id_i: id of the tab.
        Outputs: the QPoint of the drop.
        """
        drop_point = self.point_outside_the_app()
        self.assertTrue(self.main_window.is_point_outside_app_windows(
            drop_point.x(), drop_point.y()))
        index_i = window.tab_id_list().index(tab_id_i)
        with mock.patch.object(self.main_window, "window_at_point",
                               return_value=None):
            self.main_window.request_window_tab_drop(
                window, tab_id_i, index_i, drop_point.x(), drop_point.y())
        self.process_events()
        return drop_point

    @covers("LLFR-01167", "LLFR-01168", "LLFR-01169", "LLFR-01050",
            "LLFR-01020", "LLFR-01059", "HLFR-00126", "HLFR-00127",
            "HLFR-00040", "HLFR-00048")
    def test_last_tab_dropped_outside_moves_to_a_new_window(self) -> None:
        """The only tab of a window dropped outside the app opens in a new
        window at the drop point, with a hidden panel and its plot; the
        old window closes; one undo brings the old window back, one redo
        the new one.

        Inputs: none.
        Outputs: none.
        """
        from model.window_placement import placed_window_tuple
        _, second_id_i, window = self.two_tabs_one_undocked()
        old_window_id_i = window.window_id_i
        depth_i = self.plot_controller.undo_history.depth()
        drop_point = self.point_outside_the_app()
        # LLFR-01184: the size of the window the tab came from.
        expected_tuple = placed_window_tuple(
            (drop_point.x(), drop_point.y()) + window.window_tuple()[2:],
            self.main_window.screen_area_list(),
            self.main_window.main_screen_area())
        self.drop_outside(window, second_id_i)
        new_window = self.main_window.window_of_tab(second_id_i)
        self.assertIsNotNone(new_window)
        self.assertNotEqual(new_window.window_id_i, old_window_id_i)
        self.assertEqual(list(self.main_window.undocked_window_dict),
                         [new_window.window_id_i])
        self.assertFalse(new_window.is_panel_shown())
        self.assertEqual(new_window.window_tuple(), tuple(expected_tuple))
        self.assertEqual(len(self.tab(second_id_i).plot_list), 1)
        self.assertEqual(self.plot_controller.undo_history.depth(),
                         depth_i + 1)
        self.plot_controller.on_undo()
        self.process_events()
        self.assertEqual(self.tab(second_id_i).window_id_i,
                         old_window_id_i)
        self.assertEqual(list(self.main_window.undocked_window_dict),
                         [old_window_id_i])
        self.plot_controller.on_redo()
        self.process_events()
        self.assertNotEqual(self.tab(second_id_i).window_id_i,
                            old_window_id_i)
        self.assertEqual(len(self.main_window.undocked_window_dict), 1)

    @covers("LLFR-01184", "LLFR-01167", "LLFR-01084", "HLFR-00126",
            "HLFR-00127")
    def test_tab_dropped_outside_keeps_its_window_size(self) -> None:
        """A tab of a window the user resized opens, after a drop outside
        the app, in a window of that size with its top-left corner at the
        drop point (kept on a screen), not the plot panel's size.

        Inputs: none.
        Outputs: none.
        """
        from model.window_placement import placed_window_tuple
        _, second_id_i, window = self.two_tabs_one_undocked()
        panel_size_tuple = (self.main_window.plot_panel.width(),
                            self.main_window.plot_panel.height())
        size_tuple = (max(panel_size_tuple[0] - 120, 300),
                      max(panel_size_tuple[1] - 90, 200))
        window.resize(*size_tuple)
        self.process_events()
        self.assertNotEqual(window.window_tuple()[2:], panel_size_tuple)
        source_size_tuple = window.window_tuple()[2:]
        drop_point = self.point_outside_the_app()
        expected_tuple = placed_window_tuple(
            (drop_point.x(), drop_point.y()) + source_size_tuple,
            self.main_window.screen_area_list(),
            self.main_window.main_screen_area())
        self.drop_outside(window, second_id_i)
        new_window = self.main_window.window_of_tab(second_id_i)
        self.assertIsNotNone(new_window)
        self.assertIsNot(new_window, window)
        self.assertEqual(new_window.window_tuple(), tuple(expected_tuple))

    @covers("LLFR-01167", "LLFR-01168", "LLFR-01156", "HLFR-00126")
    def test_tab_dropped_outside_leaves_the_other_tabs(self) -> None:
        """One of two tabs of a window dropped outside the app gets a
        window of its own; the old window stays open with the other tab.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, window = self.two_tabs_one_undocked()
        third_id_i = self.add_tab()
        self.plot_controller.on_window_drop(third_id_i, window.window_id_i,
                                            -1)
        self.process_events()
        self.assertEqual(window.tab_id_list(), [second_id_i, third_id_i])
        self.drop_outside(window, third_id_i)
        self.assertIs(self.main_window.window_of_tab(second_id_i), window)
        self.assertEqual(window.tab_id_list(), [second_id_i])
        self.assertEqual(window.shown_tab_id(), second_id_i)
        new_window = self.main_window.window_of_tab(third_id_i)
        self.assertIsNotNone(new_window)
        self.assertIsNot(new_window, window)
        self.assertEqual(len(self.main_window.undocked_window_dict), 2)

    @covers("LLFR-01167", "LLFR-01067", "HLFR-00126")
    def test_point_on_an_app_window_is_not_outside(self) -> None:
        """A point on the main window or on an undocked window is not
        outside the app; a point right of them all is.

        Inputs: none.
        Outputs: none.
        """
        _, _, window = self.two_tabs_one_undocked()
        for frame in (self.main_window.frameGeometry(),
                      window.frameGeometry()):
            center = frame.center()
            self.assertFalse(self.main_window.is_point_outside_app_windows(
                center.x(), center.y()))
        point = self.point_outside_the_app()
        self.assertTrue(self.main_window.is_point_outside_app_windows(
            point.x(), point.y()))


class CopyPdfSearchShortcutTest(UndockedWindowTestCase):
    """Ctrl+C, Ctrl+P and Ctrl+F (Cmd on macOS) in every window."""

    @covers("LLFR-01136", "LLFR-01071", "HLFR-00039", "HLFR-00138")
    def test_copy_shortcut_copies_the_tab_of_its_window(self) -> None:
        """Ctrl+C copies the tab shown in the window where it is pressed;
        the Copy button copies the main window's tab.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QKeySequence
        first_id_i, _, window = self.two_tabs_one_undocked()
        self.main_window.signal_double_click_handler("force")
        self.process_events()
        for owner in (self.main_window, window):
            self.assertEqual(owner.copy_shortcut.key(),
                             QKeySequence("Ctrl+C"))
        with mock.patch("view.plot_export.copy_current_tab_image",
                        return_value=(True, "")) as copy:
            window.copy_shortcut.activated.emit()
            self.process_events()
            self.assertIs(copy.call_args[0][0], window.pane_widget)
            self.main_window.copy_shortcut.activated.emit()
            self.process_events()
            self.assertIs(copy.call_args[0][0], self.panel.tab_widget)
            self.main_window.top_panel.copy_button.click()
            self.process_events()
            self.assertIs(copy.call_args[0][0], self.panel.tab_widget)
            self.assertEqual(copy.call_count, 3)

    @covers("LLFR-01138", "LLFR-00146", "HLFR-00039")
    def test_copy_shortcut_with_no_plot_shows_box_over_window(self) -> None:
        """A window whose tab has no plot shows the box over itself.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, window = self.two_tabs_one_undocked()
        self.plot_controller.on_plot_delete(
            self.tab(second_id_i).plot_list[0].plot_id_i)
        self.process_events()
        with mock.patch("view.message_boxes.build_nothing_to_copy_box"
                        ) as box, mock.patch(
                "view.plot_export.copy_current_tab_image") as copy:
            window.copy_shortcut.activated.emit()
            self.process_events()
        self.assertIs(box.call_args[0][0], window)
        copy.assert_not_called()

    @covers("LLFR-01137", "HLFR-00039")
    def test_copy_shortcut_in_a_text_field_copies_text(self) -> None:
        """With the focus in a text field, its selected text is copied,
        not an image.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        _, _, window = self.two_tabs_one_undocked()
        box = self.main_window.signal_list_panel.search_box
        box.setText("speed")
        box.selectAll()
        QApplication.clipboard().setText("before")
        with mock.patch.object(QApplication, "focusWidget",
                               return_value=box), mock.patch(
                "view.plot_export.copy_current_tab_image") as copy:
            self.main_window.copy_shortcut.activated.emit()
            window.copy_shortcut.activated.emit()
            self.process_events()
        copy.assert_not_called()
        self.assertEqual(QApplication.clipboard().text(), "speed")

    @covers("LLFR-01139", "LLFR-01071", "HLFR-00038", "HLFR-00138")
    def test_pdf_shortcut_in_every_window(self) -> None:
        """Ctrl+P starts the export (the Export window, the owner's answer
        of 2026-11-06 in #268) from every window, also with the focus in
        a text field.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QKeySequence
        from PyQt6.QtWidgets import QApplication
        _, _, window = self.two_tabs_one_undocked()
        handler = mock.Mock()
        self.main_window.export_handler = handler
        for owner in (self.main_window, window):
            self.assertEqual(owner.pdf_shortcut.key(),
                             QKeySequence("Ctrl+P"))
            owner.pdf_shortcut.activated.emit()
        with mock.patch.object(
                QApplication, "focusWidget",
                return_value=self.main_window.signal_list_panel.search_box):
            window.pdf_shortcut.activated.emit()
        self.assertEqual(handler.call_count, 3)

    @covers("LLFR-01139", "LLFR-01409", "LLFR-01023", "LLFR-00128",
            "LLFR-00145", "LLFR-01407", "LLFR-00131", "HLFR-00038",
            "HLFR-00124")
    def test_pdf_shortcut_boxes_over_the_window_of_the_key(self) -> None:
        """Ctrl+P in an undocked window shows the Export window, the PDF
        dialog, the nothing-to-export box (with no Export window) and the
        save error box over that window; the dialog goes back to the main
        window afterwards, and the Export button and Ctrl+P in the main
        window use the main window (the owner's answer of 2026-11-06 in
        #268, item 3).

        Inputs: none.
        Outputs: none.
        """
        import os
        import tempfile
        from view import export_window
        _, _, window = self.two_tabs_one_undocked()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        settings_patch = mock.patch.object(
            export_window, "settings_file_path_str",
            os.path.join(folder.name, "settings.ini"))
        settings_patch.start()
        self.addCleanup(settings_patch.stop)
        window_parent_list = []
        parent_list = []

        def answer_window(dialog) -> str:
            """Record the Export window's parent and click the PDF.

            Inputs:
                dialog: the ExportWindow that would be shown.
            Outputs: "pdf".
            """
            window_parent_list.append(dialog.parent())
            return "pdf"

        def answer_dialog(dialog) -> str:
            """Record the dialog's parent and cancel it.

            Inputs:
                dialog: the QFileDialog that would be shown.
            Outputs: "" (cancel).
            """
            parent_list.append(dialog.parent())
            return ""

        self.main_window.run_export_window = answer_window
        self.main_window.run_pdf_save_dialog = answer_dialog
        window.pdf_shortcut.activated.emit()
        self.main_window.pdf_shortcut.activated.emit()
        self.main_window._on_export_requested()
        self.assertEqual(len(window_parent_list), 3)
        self.assertIs(window_parent_list[0], window)
        self.assertIs(window_parent_list[1], self.main_window)
        self.assertIs(window_parent_list[2], self.main_window)
        self.assertEqual(len(parent_list), 3)
        self.assertIs(parent_list[0], window)
        self.assertIs(parent_list[1], self.main_window)
        self.assertIs(parent_list[2], self.main_window)
        from view.main_window import SAVE_PDF_DIALOG_KEY_STR
        self.assertIs(self.main_window.file_dialog_pool.dialog(
            SAVE_PDF_DIALOG_KEY_STR).parent(), self.main_window)
        self.assertIsNone(self.main_window.pdf_shortcut_window)
        # LLFR-01409: the Word and PNG dialogs over the window too.
        dialog_parent_list = []

        def record_export_dialog(dialog) -> str:
            """Record the Word or PNG dialog's parent and cancel it.

            Inputs:
                dialog: the QFileDialog that would be shown.
            Outputs: "" (cancel).
            """
            dialog_parent_list.append(dialog.parent())
            return ""

        self.main_window.run_export_dialog = record_export_dialog
        for format_str in ("docx", "png"):
            self.main_window.run_export_window = (
                lambda dialog, chosen_str=format_str: chosen_str)
            window.pdf_shortcut.activated.emit()
        self.assertEqual(dialog_parent_list, [window, window])
        self.main_window.run_export_window = answer_window
        # LLFR-01407, LLFR-00145: the nothing-to-export box over the
        # window, with no Export window.
        window_parent_list.clear()
        with mock.patch.object(self.main_window, "exportable_tab_count",
                               return_value=0), mock.patch(
                "view.message_boxes.build_nothing_to_export_box") as box:
            window.pdf_shortcut.activated.emit()
            self.main_window._on_export_requested()
        self.assertEqual(window_parent_list, [])
        self.assertIs(box.call_args_list[0].args[0], window)
        self.assertIs(box.call_args_list[1].args[0], self.main_window)
        # LLFR-00131: the save error box over the window.
        path_str = os.path.join(folder.name, "plots.pdf")
        self.main_window.run_pdf_save_dialog = lambda dialog: path_str
        with mock.patch.object(self.main_window, "save_tabs_pdf",
                               return_value=(False, "disk full")), \
                mock.patch("view.message_boxes.build_export_error_box") \
                as error_box:
            window.pdf_shortcut.activated.emit()
        self.assertIs(error_box.call_args.args[0], window)
        self.assertEqual(error_box.call_args.args[1], "disk full")
        self.assertIsNone(self.main_window.pdf_shortcut_window)

    @covers("LLFR-01408", "HLFR-00038", "HLFR-00138")
    def test_pdf_shortcut_ignored_while_the_export_window_is_open(
            self) -> None:
        """While the Export window is open, Ctrl+P in any window opens no
        second one (the owner's answer of 2026-11-06 in #268, item 1).

        Inputs: none.
        Outputs: none.
        """
        import os
        import tempfile
        from view import export_window
        _, _, window = self.two_tabs_one_undocked()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        settings_patch = mock.patch.object(
            export_window, "settings_file_path_str",
            os.path.join(folder.name, "settings.ini"))
        settings_patch.start()
        self.addCleanup(settings_patch.stop)
        shown_list = []

        def press_while_open(dialog) -> str:
            """Press Ctrl+P in both windows while the window is open.

            Inputs:
                dialog: the ExportWindow.
            Outputs: "" (closed with no format).
            """
            shown_list.append(dialog)
            if len(shown_list) == 1:
                self.assertTrue(self.main_window.export_window_open_b)
                self.main_window.pdf_shortcut.activated.emit()
                window.pdf_shortcut.activated.emit()
            return ""

        self.main_window.run_export_window = press_while_open
        window.pdf_shortcut.activated.emit()
        self.assertEqual(len(shown_list), 1)
        self.assertFalse(self.main_window.export_window_open_b)
        # Once it is closed, Ctrl+P opens it again.
        self.main_window.pdf_shortcut.activated.emit()
        self.assertEqual(len(shown_list), 2)

    @covers("LLFR-01140", "LLFR-01141", "LLFR-01053", "LLFR-01071",
            "HLFR-00033", "HLFR-00130", "HLFR-00138")
    def test_search_shortcut_focuses_the_window_search_box(self) -> None:
        """Ctrl+F in a window with a hidden panel shows it (undoably)
        and puts the focus in its search box with the text selected; in
        the main window, in the main search box.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QKeySequence
        _, second_id_i, window = self.two_tabs_one_undocked()
        self.main_window.signal_list_panel.search_box.setText("spe")
        self.process_events()
        self.assertEqual(window.search_shortcut.key(),
                         QKeySequence("Ctrl+F"))
        depth_i = self.plot_controller.undo_history.depth()
        window.search_shortcut.activated.emit()
        self.process_events()
        window = self.main_window.window_of_tab(second_id_i)
        self.assertTrue(window.is_panel_shown())
        self.assertEqual(self.plot_controller.undo_history.depth(),
                         depth_i + 1)
        box = window.signal_list_panel.search_box
        self.assertIs(window.focusWidget(), box)
        self.assertEqual(box.selectedText(), "spe")
        # A second press only moves the focus: nothing to undo.
        window.search_shortcut.activated.emit()
        self.process_events()
        self.assertEqual(self.plot_controller.undo_history.depth(),
                         depth_i + 1)
        self.main_window.search_shortcut.activated.emit()
        self.process_events()
        main_box = self.main_window.signal_list_panel.search_box
        self.assertIs(self.main_window.focusWidget(), main_box)
        self.assertEqual(main_box.selectedText(), "spe")
        self.plot_controller.on_undo()
        self.process_events()
        self.assertFalse(self.main_window.window_of_tab(
            second_id_i).is_panel_shown())


class HiddenSignalsInEveryPanelTest(UndockedWindowTestCase):
    """The [-] and [+] state of the data files is shared by the panels."""

    @covers("LLFR-01175", "LLFR-01036", "LLFR-00997", "LLFR-00995",
            "HLFR-00128", "HLFR-00123")
    def test_hidden_files_in_every_panel(self) -> None:
        """An icon click in a window's panel goes to the same handler as
        in the main panel; the collapsed files are shown with [+] in
        every panel, also in a window opened afterwards.

        Inputs: none.
        Outputs: none.
        """
        _, _, window = self.two_tabs_one_undocked()
        toggled_list = []
        self.main_window.set_file_toggle_handler(toggled_list.append)
        window.signal_list_panel.file_expand_toggled.emit(2)
        self.main_window.signal_list_panel.file_expand_toggled.emit(1)
        self.assertEqual(toggled_list, [2, 1])
        group_list = [(1, "file1_a.csv", ["file1_Time"], ""),
                      (2, "file2_b.csv", [], "")]
        self.main_window.set_collapsed_file_numbers({2})
        self.main_window.show_signal_groups(group_list)
        self.process_events()
        third_id_i = self.add_tab()
        later_window = self.undock(third_id_i)
        for panel in (self.main_window.signal_list_panel,
                      window.signal_list_panel,
                      later_window.signal_list_panel):
            self.assertEqual(panel.file_row_texts(),
                             ["file1_a.csv", "file2_b.csv"])
            self.assertEqual(panel.file_row_icon_text("file1_a.csv"),
                             "[-]")
            self.assertEqual(panel.file_row_icon_text("file2_b.csv"),
                             "[+]")

    @covers("LLFR-01194", "LLFR-01040", "LLFR-01192", "LLFR-01036",
            "LLFR-01037", "HLFR-00128", "HLFR-00123", "HLFR-00053",
            "HLFR-00063")
    def test_selection_and_left_key_in_every_panel(self) -> None:
        """A new signal is selected alone only in the panel whose menu
        created it, and Left on a signal row of a window's panel goes to
        its file name row.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, QItemSelectionModel, Qt
        from PyQt6.QtGui import QKeyEvent
        _, _, window = self.two_tabs_one_undocked()
        group_list = [(1, "file1_a.csv", ["file1_Time", "file1_Speed"], ""),
                      (2, "file2_b.csv", ["file2_Time"], "")]
        self.main_window.set_collapsed_file_numbers(set())
        self.main_window.show_signal_groups(group_list)
        self.process_events()
        panel_list = [self.main_window.signal_list_panel,
                      window.signal_list_panel]
        panel_list[0].signal_list_widget.select_only(
            panel_list[0].signal_list_widget.row_items("signal")[0])
        panel_list[1].signal_list_widget.select_only(
            panel_list[1].signal_list_widget.row_items("signal")[2])
        # A creation started from the window's panel: the controller
        # selects the new signal while the creation runs (LLFR-01194).
        selected_list = []

        def create(name_str: str, operation_str: str) -> None:
            """Stand-in for the synthetic controller's creation.

            Inputs:
                name_str: the right-clicked signal name.
                operation_str: the operation id.
            Outputs: none. The right-clicked name is selected as if it
                were the new signal.
            """
            selected_list.append(self.main_window.creating_panel)
            self.main_window.select_only_signal(name_str)

        with mock.patch.dict(self.main_window.signal_menu_handler_dict,
                             {"create": create}):
            panel_list[1].synthetic_operation_requested.emit(
                "file1_Speed", "integral")
            self.assertEqual(selected_list, [panel_list[1]])
            self.assertEqual(panel_list[1].selected_signal_names(),
                             ["file1_Speed"])
            self.assertEqual(
                panel_list[1].signal_list_widget.currentItem().text(),
                "file1_Speed")
            # LLFR-01040: the main window's panel keeps its selection.
            self.assertEqual(panel_list[0].selected_signal_names(),
                             ["file1_Time"])
            # From the main window's panel, the window's panel keeps
            # its own selection.
            panel_list[0].synthetic_operation_requested.emit(
                "file2_Time", "integral")
            self.assertEqual(selected_list[-1], panel_list[0])
            self.assertEqual(panel_list[0].selected_signal_names(),
                             ["file2_Time"])
            self.assertEqual(panel_list[1].selected_signal_names(),
                             ["file1_Speed"])
        self.assertIsNone(self.main_window.creating_panel)
        # With no creation under way, the main window's panel selects.
        self.main_window.select_only_signal("file1_Speed")
        self.assertEqual(panel_list[0].selected_signal_names(),
                         ["file1_Speed"])
        self.assertEqual(panel_list[1].selected_signal_names(),
                         ["file1_Speed"])
        # A name that the panel doesn't show changes nothing there.
        self.main_window.select_only_signal("file3_x")
        self.assertEqual(panel_list[0].selected_signal_names(),
                         ["file1_Speed"])
        # A handler that fails still ends the creation.
        with mock.patch.dict(self.main_window.signal_menu_handler_dict,
                             {"create": mock.Mock(
                                 side_effect=RuntimeError("test"))}):
            with self.assertRaises(RuntimeError):
                self.main_window._create_from_panel(
                    panel_list[1], "file1_Speed", "integral")
        self.assertIsNone(self.main_window.creating_panel)
        widget = window.signal_list_panel.signal_list_widget
        for item in widget.row_items("signal"):
            if item.text() == "file2_Time":
                widget.setCurrentItem(
                    item, QItemSelectionModel.SelectionFlag.NoUpdate)
        widget.keyPressEvent(QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_Left,
            Qt.KeyboardModifier.NoModifier))
        self.process_events()
        self.assertEqual(widget.currentItem().text(), "file2_b.csv")
        self.assertEqual(window.signal_list_panel.selected_signal_names(),
                         ["file1_Speed"])


class ShortcutsWhileDraggingTest(UndockedWindowTestCase):
    """Ctrl+P, Ctrl+C and Ctrl+F do nothing during a mouse drag."""

    @covers("LLFR-01172", "HLFR-00038")
    def test_pdf_shortcut_ignored_while_dragging(self) -> None:
        """Ctrl+P in any window runs no export while the mouse is
        dragged, and runs it again once the drag is over.

        Inputs: none.
        Outputs: none.
        """
        _, _, window = self.two_tabs_one_undocked()
        handler = mock.Mock()
        self.main_window.export_handler = handler
        with mock.patch.object(self.main_window,
                               "is_mouse_drag_in_progress",
                               return_value=True):
            for owner in (self.main_window, window):
                owner.pdf_shortcut.activated.emit()
        self.assertEqual(handler.call_count, 0)
        window.pdf_shortcut.activated.emit()
        self.assertEqual(handler.call_count, 1)

    @covers("LLFR-01173", "LLFR-01137", "HLFR-00039")
    def test_copy_shortcut_ignored_while_dragging(self) -> None:
        """Ctrl+C copies no image during a drag, while a text field
        still copies its own text.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        _, _, window = self.two_tabs_one_undocked()
        copied_list = []
        self.main_window.copy_shortcut_handler = copied_list.append
        box = self.main_window.signal_list_panel.search_box
        with mock.patch.object(self.main_window,
                               "is_mouse_drag_in_progress",
                               return_value=True):
            for owner in (self.main_window, window):
                owner.copy_shortcut.activated.emit()
            with mock.patch.object(QApplication, "focusWidget",
                                   return_value=box), \
                    mock.patch.object(box, "copy") as box_copy:
                window.copy_shortcut.activated.emit()
        self.assertEqual(copied_list, [])
        box_copy.assert_called_once_with()
        window.copy_shortcut.activated.emit()
        self.assertEqual(len(copied_list), 1)

    @covers("LLFR-01174", "HLFR-00033", "HLFR-00128")
    def test_search_shortcut_ignored_while_dragging(self) -> None:
        """Ctrl+F during a drag shows no hidden panel, records no undo
        and moves no focus.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, window = self.two_tabs_one_undocked()
        depth_i = self.plot_controller.undo_history.depth()
        with mock.patch.object(self.main_window,
                               "is_mouse_drag_in_progress",
                               return_value=True):
            window.search_shortcut.activated.emit()
            self.process_events()
        window = self.main_window.window_of_tab(second_id_i)
        self.assertFalse(window.is_panel_shown())
        self.assertEqual(self.plot_controller.undo_history.depth(),
                         depth_i)
        window.search_shortcut.activated.emit()
        self.process_events()
        window = self.main_window.window_of_tab(second_id_i)
        self.assertTrue(window.is_panel_shown())


class LiveDragInEveryWindowTest(UndockedWindowTestCase):
    """A dragged flag or area moves live in every shown window."""

    def setUp(self) -> None:
        """Main tab with a plot, an undocked tab with a plot, and a
        hidden docked tab with a plot.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.first_id_i, self.second_id_i, self.window = (
            self.two_tabs_one_undocked())
        self.main_window.set_current_tab(self.first_id_i)
        self.main_window.signal_double_click_handler("force")
        self.hidden_id_i = self.add_tab()
        self.main_window.signal_double_click_handler("angle")
        self.main_window.set_current_tab(self.first_id_i)
        self.process_events()
        self.main_plot = self.panel.page_dict[
            self.first_id_i].plot_widget_list[0]
        self.window_plot = self.window.page().plot_widget_list[0]
        self.hidden_plot = self.panel.page_dict[
            self.hidden_id_i].plot_widget_list[0]

    @covers("LLFR-00665", "LLFR-00666", "LLFR-00205", "HLFR-00029")
    def test_flag_follows_in_every_shown_window(self) -> None:
        """A flag dragged in the main window follows in the undocked
        window, and one dragged there follows in the main window; the
        hidden docked tab waits for the release.

        Inputs: none.
        Outputs: none.
        """
        with mock.patch.object(self.window_plot,
                               "follow_marker_drag") as window_follow, \
                mock.patch.object(self.hidden_plot,
                                  "follow_marker_drag") as hidden_follow, \
                mock.patch.object(self.main_plot,
                                  "follow_marker_drag") as main_follow:
            self.main_plot.marker_drag_moved.emit(4, 1.5)
            self.window_plot.marker_drag_moved.emit(4, 2.5)
        window_follow.assert_called_once_with(4, 1.5)
        main_follow.assert_called_once_with(4, 2.5)
        hidden_follow.assert_not_called()

    @covers("LLFR-00709", "LLFR-00710", "LLFR-00310", "HLFR-00067",
            "HLFR-00106")
    def test_area_follows_in_every_shown_window(self) -> None:
        """An area dragged in the undocked window follows in the main
        window's shown tab; the hidden docked tab waits for the release.

        Inputs: none.
        Outputs: none.
        """
        with mock.patch.object(self.main_plot,
                               "follow_area_drag") as main_follow, \
                mock.patch.object(self.hidden_plot,
                                  "follow_area_drag") as hidden_follow, \
                mock.patch.object(self.window_plot,
                                  "follow_area_drag") as window_follow:
            self.window_plot.area_drag_moved.emit(2, 1.0, 2.0)
            self.main_plot.area_drag_moved.emit(2, 1.5, 2.5)
        main_follow.assert_called_once_with(2, 1.0, 2.0)
        window_follow.assert_called_once_with(2, 1.5, 2.5)
        hidden_follow.assert_not_called()


class WindowIconShapeTest(unittest.TestCase):
    """The pictures of the window buttons (no Qt needed)."""

    @covers("LLFR-01013", "LLFR-01026", "LLFR-01045", "HLFR-00124",
            "HLFR-00125", "HLFR-00130")
    def test_undock_dock_and_signal_list_pictures(self) -> None:
        """A square with an arrow out to the top right (undock) or in to
        the bottom left (dock); a rounded rectangle with its right part
        filled.

        Inputs: none.
        Outputs: none.
        """
        from view import icon_shapes
        undock_list = icon_shapes.icon_layer_list(
            icon_shapes.UNDOCK_ICON_STR)
        dock_list = icon_shapes.icon_layer_list(icon_shapes.DOCK_ICON_STR)
        self.assertEqual(undock_list[0], dock_list[0])
        # The undock arrow ends top right, the dock arrow bottom left.
        undock_head_list = undock_list[2][0]
        self.assertEqual(undock_head_list[1][1:], (20.5, 3.5))
        dock_head_list = dock_list[2][0]
        self.assertEqual(dock_head_list[1][1:], (11.0, 13.0))
        list_layer_list = icon_shapes.icon_layer_list(
            icon_shapes.SIGNAL_LIST_ICON_STR)
        fill_list = list_layer_list[0][0]
        outline_command = list_layer_list[1][0][0]
        # The first layer is filled with the icon color, not stroked.
        self.assertEqual(list_layer_list[0][1], icon_shapes.NO_ROLE_STR)
        self.assertEqual(list_layer_list[0][2], icon_shapes.INK_ROLE_STR)
        # The outline is a rounded rectangle.
        self.assertEqual(outline_command[0], "R")
        self.assertGreater(outline_command[5], 0.0)
        outline_left_f = outline_command[1]
        outline_right_f = outline_command[1] + outline_command[3]
        x_list = [command[-2] for command in fill_list
                  if command[0] in ("M", "L", "Q")]
        # The filled part is the right part: it reaches the right edge
        # and starts right of the middle of the rectangle.
        self.assertAlmostEqual(max(x_list), outline_right_f, delta=0.01)
        self.assertGreater(min(x_list),
                           (outline_left_f + outline_right_f) / 2.0)
        self.assertEqual(fill_list[-1], ("Z",))
        for icon_name_str in icon_shapes.WINDOW_ICON_SHAPE_FUNCTION_DICT:
            self.assertNotIn(icon_name_str, icon_shapes.ICON_NAME_TUPLE)


class UndockedExportTest(UndockedWindowTestCase):
    """The PDF holds the undocked tabs after the docked ones."""

    @covers("LLFR-00129", "LLFR-01091", "HLFR-00038")
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
    """The windows of a layout file (HLFR-00140 to HLFR-00142)."""

    @covers("LLFR-01076", "LLFR-01078", "LLFR-01083", "HLFR-00141",
            "HLFR-00142", "HLFR-00140", "HLFR-00050", "HLFR-00049")
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
        # The user closes the window, which deletes all its tabs (here
        # its only tab).
        self.user_close(window)
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

    @covers("LLFR-01195", "LLFR-01078", "LLFR-01085", "HLFR-00141",
            "HLFR-00130", "HLFR-00050", "HLFR-00052")
    def test_saved_panel_wider_than_its_window_is_trimmed(self) -> None:
        """A saved panel width that Qt takes but the window cannot hold
        is trimmed to the window's width minus 100 pixels, so the plot
        panel keeps room, and the load reports nothing.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, window = self.two_tabs_one_undocked()
        window.signal_list_button.click()
        self.process_events()
        layout_dict = self.plot_controller.layout_dict()
        tab_entry = layout_dict["tabs"][-1]
        area_tuple = self.main_window.main_screen_area()
        tab_entry["window"].update({
            "x": area_tuple[0] + 10, "y": area_tuple[1] + 10,
            "width": 600, "height": 400})
        tab_entry["signal_list_panel"] = {"shown": True, "width": 5000}
        self.user_close(window)
        self.assertIsNone(self.tab(second_id_i))
        result = self.plot_controller.load_layout(layout_dict)
        self.process_events()
        self.assertIsNotNone(result)
        self.assertTrue(result.report.is_empty(), result.report.text())
        loaded = next(iter(self.main_window.undocked_window_dict.values()))
        self.assertTrue(loaded.is_panel_shown())
        self.assertGreaterEqual(loaded.panel_width(), 1)
        self.assertLessEqual(loaded.panel_width(), loaded.width() - 100)
        # The plot panel has the rest of the splitter.
        self.assertGreaterEqual(
            loaded.plot_column.width(),
            loaded.splitter.width() - loaded.splitter.handleWidth()
            - loaded.panel_width() - 1)
        self.assertGreater(loaded.plot_column.width(), 0)


if __name__ == "__main__":
    unittest.main()
