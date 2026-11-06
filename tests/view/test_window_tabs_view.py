"""Qt tests for the owner's tab feedback of 2026-11-04 (#205, step 5).

A real MainWindow and MainController are used (the setup of
test_plot_panel). They check the flat undock and dock buttons inside the
tabs (HLFR-00124, HLFR-00125), undocked windows with several tabs
(HLFR-00126, HLFR-00135, HLFR-00136), moving a tab into an undocked
window (HLFR-00154), the drops outside the plot panel (HLFR-00153), the
previews shown in every window (HLFR-00027, HLFR-00028, HLFR-00066) and
the pickers opened as submenus (HLFR-00146, HLFR-00150).

Every window is closed in tearDown. No test moves the shared mouse
pointer: events are sent to the widgets directly, and the window under a
desktop point is given by patching MainWindow.window_at_point where a
test needs it.
"""

import math
import unittest
from unittest import mock

from tests.support import covers, requires_qt
from tests.view.test_undocked_windows_view import UndockedWindowTestCase


@requires_qt
class WindowTabsViewTestCase(UndockedWindowTestCase):
    """Helpers for windows with several tabs."""

    def window_id(self, tab_id_i: int) -> int:
        """Return the window id of a tab in the model.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: the window id, 0 for a docked tab.
        """
        return self.tab(tab_id_i).window_id_i

    def two_tabs_in_one_window(self):
        """Make tabs 2 and 3 share an undocked window, each with a plot.

        Inputs: none.
        Outputs: (first id, second id, third id, UndockedWindow).
        """
        self.main_window.show()
        first_id_i = self.panel.current_tab_id()
        second_id_i = self.add_tab()
        self.main_window.signal_double_click_handler("speed")
        third_id_i = self.add_tab()
        self.main_window.signal_double_click_handler("force")
        self.process_events()
        window = self.undock(second_id_i)
        self.plot_controller.on_window_drop(third_id_i,
                                            window.window_id_i, -1)
        self.process_events()
        return first_id_i, second_id_i, third_id_i, window

    def tab_rect_on_desktop(self, tab_bar, index_i: int):
        """Return the border box of a tab of a tab bar on the desktop.

        Inputs:
            tab_bar: the QTabBar.
            index_i: the index of the tab.
        Outputs: a QRect: the tab's rectangle without its right margin.
        """
        from PyQt6.QtCore import QRect
        from view import theme
        rect = tab_bar.tabRect(index_i)
        top_left = tab_bar.mapToGlobal(rect.topLeft())
        return QRect(top_left.x(), top_left.y(),
                     rect.width() - theme.TAB_SPACING_I, rect.height())

    def button_rect_on_desktop(self, tab_button):
        """Return the visible button of a TabIconButton on the desktop.

        Inputs:
            tab_button: the TabIconButton.
        Outputs: a QRect.
        """
        from PyQt6.QtCore import QPoint, QRect
        button = tab_button.button
        top_left = button.mapToGlobal(QPoint(0, 0))
        return QRect(top_left.x(), top_left.y(), button.width(),
                     button.height())

    def assert_button_inside(self, tab_bar, index_i: int,
                             tab_button) -> None:
        """Check that a tab button lies inside its tab, with room.

        Inputs:
            tab_bar: the QTabBar.
            index_i: the index of the tab.
            tab_button: its TabIconButton.
        Outputs: none.
        """
        from view import theme
        tab_rect = self.tab_rect_on_desktop(tab_bar, index_i)
        border_i = theme.TAB_BORDER_WIDTH_I
        inner_rect = tab_rect.adjusted(border_i + 2, border_i + 2,
                                       -border_i - 2, -border_i - 2)
        button_rect = self.button_rect_on_desktop(tab_button)
        self.assertTrue(inner_rect.contains(button_rect),
                        f"{button_rect} not inside {inner_rect}")
        # LLFR-01155: the name fits beside the button.
        text_width_i = tab_bar.fontMetrics().horizontalAdvance(
            tab_bar.tabText(index_i))
        self.assertGreaterEqual(button_rect.left() - tab_rect.left(),
                                text_width_i)


class TabButtonLookTest(WindowTabsViewTestCase):
    """The undock and dock buttons are part of their tab."""

    @covers("LLFR-01147", "LLFR-01148", "LLFR-01154", "LLFR-01155",
            "LLFR-01012", "HLFR-00124")
    def test_undock_button_flat_inside_the_tab(self) -> None:
        """The undock button has no border or background of its own, a
        rounded highlight on hover, its icon in the tab's text color,
        and lies inside its tab beside the name.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        self.main_window.show()
        first_id_i = self.panel.current_tab_id()
        self.add_tab()
        self.process_events()
        tab_bar = self.panel.tab_widget.tabBar()
        for index_i in range(tab_bar.count()):
            tab_id_i = self.panel.tab_id_at_index(index_i)
            tab_button = self.panel.undock_button_of(tab_id_i)
            self.assertTrue(tab_button.isVisible())
            self.assert_button_inside(tab_bar, index_i, tab_button)
            style_str = tab_button.button.styleSheet()
            self.assertIn("border: none", style_str)
            self.assertIn("background: transparent", style_str)
            self.assertIn(":hover", style_str)
            self.assertIn(theme.TAB_BUTTON_HOVER_COLOR_STR, style_str)
            self.assertIn("border-radius", style_str)
        # LLFR-01147: the icon of the selected tab is in its darker text
        # color, the other one in the muted color.
        selected_button = self.panel.undock_button_of(
            self.panel.current_tab_id())
        other_button = self.panel.undock_button_of(first_id_i)
        self.assertEqual(selected_button.icon_color_str(),
                         theme.TAB_SELECTED_TEXT_COLOR_STR)
        self.assertEqual(other_button.icon_color_str(),
                         theme.TAB_TEXT_COLOR_STR)
        self.main_window.set_current_tab(first_id_i)
        self.process_events()
        self.assertEqual(other_button.icon_color_str(),
                         theme.TAB_SELECTED_TEXT_COLOR_STR)

    @covers("LLFR-01147", "LLFR-01154", "LLFR-01155", "LLFR-01025",
            "LLFR-01066", "HLFR-00125")
    def test_dock_buttons_inside_each_tab_of_a_window(self) -> None:
        """Each tab of a window has its own flat dock button inside it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QTabBar
        _, second_id_i, third_id_i, window = self.two_tabs_in_one_window()
        window.resize(900, 500)
        self.process_events()
        for index_i, tab_id_i in enumerate((second_id_i, third_id_i)):
            dock_button = window.dock_button_of(tab_id_i)
            self.assertIs(window.tab_bar.tabButton(
                index_i, QTabBar.ButtonPosition.RightSide), dock_button)
            self.assertEqual(dock_button.toolTip(), "Dock")
            self.assertIn("border: none", dock_button.button.styleSheet())
            self.assert_button_inside(window.tab_bar, index_i, dock_button)
        window.dock_button_of(second_id_i).click()
        self.process_events()
        self.assertFalse(self.tab(second_id_i).undocked_b)
        self.assertIs(self.main_window.window_of_tab(third_id_i), window)


class SeveralTabsWindowTest(WindowTabsViewTestCase):
    """An undocked window with several tabs."""

    @covers("LLFR-01063", "LLFR-01130", "LLFR-01149", "LLFR-01061",
            "LLFR-01062", "LLFR-01158", "HLFR-00126", "HLFR-00135",
            "HLFR-00136", "HLFR-00154")
    def test_tab_row_switch_and_title(self) -> None:
        """Two tabs in the tab row, the moved one shown; a click on the
        other shows it and the title follows.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, third_id_i, window = self.two_tabs_in_one_window()
        self.assertEqual(window.tab_id_list(), [second_id_i, third_id_i])
        self.assertEqual(window.tab_bar.count(), 2)
        self.assertEqual(window.shown_tab_id(), third_id_i)
        self.assertEqual(window.windowTitle(), self.tab(third_id_i).name_str)
        window.tab_bar.setCurrentIndex(0)
        self.process_events()
        self.assertEqual(window.shown_tab_id(), second_id_i)
        self.assertIs(window.pane_widget.currentWidget(),
                      self.panel.page_dict[second_id_i])
        self.assertEqual(window.windowTitle(),
                         self.tab(second_id_i).name_str)
        self.plot_controller.on_rename_tab(second_id_i, "Engine")
        self.process_events()
        self.assertEqual(window.windowTitle(), "Engine")
        self.assertEqual(window.tab_bar.tabText(0), "Engine")

    @covers("LLFR-01064", "LLFR-01065", "LLFR-01069", "HLFR-00136")
    def test_tab_menu_of_the_second_tab(self) -> None:
        """The tab menu acts on the right-clicked tab of the window, and
        its Delete keeps the window with the other tab.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, third_id_i, window = self.two_tabs_in_one_window()
        menu = self.panel.build_tab_menu_of(third_id_i, True)
        delete_action = self.menu_action(menu, "Delete")
        self.assertTrue(delete_action.isEnabled())
        self.assertIsNotNone(self.menu_action(menu, "Plot matrix"))
        delete_action.trigger()
        menu.deleteLater()
        self.process_events()
        self.assertIsNone(self.tab(third_id_i))
        self.assertIs(self.main_window.window_of_tab(second_id_i), window)
        self.assertEqual(window.tab_id_list(), [second_id_i])

    @covers("LLFR-01157", "LLFR-01166", "LLFR-01089", "HLFR-00143")
    def test_drag_in_the_window_tab_row_reorders(self) -> None:
        """A tab moved in the window's tab row and dropped there keeps
        its new place, as one undoable action.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, third_id_i, window = self.two_tabs_in_one_window()
        window.tab_bar.moveTab(1, 0)
        self.process_events()
        self.assertEqual(window.tab_id_list(), [third_id_i, second_id_i])
        row_point = window.tab_bar.mapToGlobal(
            window.tab_bar.tabRect(0).center())
        with mock.patch.object(self.main_window, "window_at_point",
                               return_value=window):
            self.main_window.request_window_tab_drop(
                window, third_id_i, 1, row_point.x(), row_point.y())
        self.process_events()
        self.assertEqual(
            [tab.tab_id_i for tab in self.plot_controller.workspace
             .window_tab_list(window.window_id_i)],
            [third_id_i, second_id_i])
        self.plot_controller.on_undo()
        self.process_events()
        window = self.main_window.window_of_tab(second_id_i)
        self.assertEqual(window.tab_id_list(), [second_id_i, third_id_i])

    @covers("LLFR-01073", "LLFR-01074", "LLFR-01059", "HLFR-00139")
    def test_window_close_deletes_both_tabs(self) -> None:
        """The system close deletes both tabs; one undo opens the window
        again with both.

        Inputs: none.
        Outputs: none.
        """
        first_id_i, second_id_i, third_id_i, window = (
            self.two_tabs_in_one_window())
        self.user_close(window)
        self.assertIsNone(self.tab(second_id_i))
        self.assertIsNone(self.tab(third_id_i))
        self.assertEqual(self.main_window.undocked_window_dict, {})
        self.plot_controller.on_undo()
        self.process_events()
        window = self.main_window.window_of_tab(second_id_i)
        self.assertIsNotNone(window)
        self.assertEqual(window.tab_id_list(), [second_id_i, third_id_i])
        self.assertEqual(self.panel.current_tab_id(), first_id_i)

    @covers("LLFR-00129", "LLFR-01091", "HLFR-00038", "HLFR-00126")
    def test_pdf_order_window_by_window(self) -> None:
        """Docked tabs first, then each window's tabs in its order.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, third_id_i, _ = self.two_tabs_in_one_window()
        fourth_id_i = self.add_tab()
        self.main_window.signal_double_click_handler("angle")
        self.undock(fourth_id_i)
        self.assertEqual([page.tab_id_i for page
                          in self.main_window.undocked_page_list()],
                         [second_id_i, third_id_i, fourth_id_i])

    @covers("LLFR-01136", "LLFR-01038", "HLFR-00039", "HLFR-00128")
    def test_current_tab_rules_use_the_shown_tab(self) -> None:
        """The Copy shortcut and the double-click of a window's panel
        use the tab the window shows.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, third_id_i, window = self.two_tabs_in_one_window()
        copied_list = []
        self.main_window.copy_shortcut_handler = copied_list.append
        window.copy_shortcut.activated.emit()
        window.tab_bar.setCurrentIndex(0)
        self.process_events()
        window.copy_shortcut.activated.emit()
        self.assertEqual(copied_list, [third_id_i, second_id_i])
        plot_count_i = len(self.tab(second_id_i).plot_list)
        window.signal_list_panel.signal_double_clicked.emit("angle")
        self.process_events()
        self.assertEqual(len(self.tab(second_id_i).plot_list),
                         plot_count_i + 1)


class WindowPlusAndSpacingTest(WindowTabsViewTestCase):
    """The "+" button, the left alignment and the spacing of the tabs of
    an undocked window (LLFR-01203, LLFR-00106, LLFR-01204,
    LLFR-01205)."""

    def border_rect(self, tab_bar, index_i: int):
        """Return the border box of a tab, in tab bar coordinates.

        Inputs:
            tab_bar: the QTabBar.
            index_i: the index of the tab.
        Outputs: a QRect without the tab's right margin.
        """
        from PyQt6.QtCore import QRect
        from view import theme
        rect = tab_bar.tabRect(index_i)
        return QRect(rect.x(), rect.y(),
                     rect.width() - theme.TAB_SPACING_I, rect.height())

    @covers("LLFR-00025", "LLFR-01032", "LLFR-01203", "LLFR-00107",
            "HLFR-00015", "HLFR-00126")
    def test_plus_button_adds_a_tab_in_the_window(self) -> None:
        """The window's "+" sits right after its last tab, as high as a
        tab; a click adds a tab at the end of the window, shown there.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        _, second_id_i, third_id_i, window = self.two_tabs_in_one_window()
        window.show()
        self.process_events()
        button = window.add_tab_button
        self.assertTrue(button.isVisible())
        self.assertEqual(button.text(), "+")
        last_rect = self.border_rect(window.tab_bar, 1)
        right_i = window.tab_bar.mapTo(window.tab_row,
                                       last_rect.topRight()).x()
        left_i = button.mapTo(window.tab_row, QPoint(0, 0)).x()
        # LLFR-01205: 2 pixels between the last tab and the "+" button.
        self.assertEqual(left_i - right_i - 1, 2)
        self.assertEqual(button.height(), window.tab_bar.tabRect(0).height())
        button.click()
        self.process_events()
        id_list = window.tab_id_list()
        self.assertEqual(len(id_list), 3)
        self.assertEqual(id_list[:2], [second_id_i, third_id_i])
        self.assertEqual(window.shown_tab_id(), id_list[2])
        self.assertTrue(self.tab(id_list[2]).undocked_b)

    @covers("LLFR-00106", "LLFR-01063", "LLFR-01204", "HLFR-00014",
            "HLFR-00126")
    def test_window_tabs_start_at_the_left_two_pixels_apart(self) -> None:
        """The first tab starts at the left edge of the window's tab row,
        the tabs are 2 pixels apart, and the free room is on the right.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        _, _, _, window = self.two_tabs_in_one_window()
        window.resize(900, 500)
        window.show()
        self.process_events()
        tab_bar = window.tab_bar
        first_left_i = tab_bar.mapTo(window.tab_row,
                                     tab_bar.tabRect(0).topLeft()).x()
        self.assertLessEqual(abs(first_left_i), 1)
        first_rect = self.border_rect(tab_bar, 0)
        second_rect = self.border_rect(tab_bar, 1)
        self.assertEqual(second_rect.x() - (first_rect.x()
                                            + first_rect.width()), 2)
        button_right_i = window.add_tab_button.mapTo(
            window.tab_row, QPoint(window.add_tab_button.width(), 0)).x()
        self.assertLess(button_right_i, window.tab_row.width() // 2)

    def plus_gap_i(self, window) -> int:
        """Return the space between the last tab and the "+" button.

        Inputs:
            window: the UndockedWindow, shown.
        Outputs: the pixels between the right border of the window's last
            tab and the left border of its "+" button.
        """
        from PyQt6.QtCore import QPoint
        last_rect = self.border_rect(window.tab_bar,
                                     window.tab_bar.count() - 1)
        right_i = window.tab_bar.mapTo(window.tab_row,
                                       last_rect.topRight()).x()
        left_i = window.add_tab_button.mapTo(window.tab_row,
                                             QPoint(0, 0)).x()
        return left_i - right_i - 1

    @covers("LLFR-01205", "LLFR-01063", "HLFR-00015", "HLFR-00126")
    def test_plus_button_two_pixels_after_a_single_tab(self) -> None:
        """#269: in an undocked window with only one tab, the "+" button
        is 2 pixels after the tab, as with several tabs; before the fix
        the tab bar took Qt's minimum width of its scroll buttons, wider
        than one tab, and the "+" stood far from it.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.show()
        second_id_i = self.add_tab()
        self.main_window.signal_double_click_handler("speed")
        self.process_events()
        window = self.undock(second_id_i)
        window.resize(900, 500)
        window.show()
        self.process_events()
        self.assertEqual(window.tab_bar.count(), 1)
        # The bug: the gap was the bar's minimum width less the tab's.
        self.assertEqual(self.plus_gap_i(window), 2)
        self.assertLessEqual(window.tab_bar.width(),
                             window.tab_bar.tabRect(0).width())
        # With a second tab and back to one tab, still 2 pixels.
        window.add_tab_button.click()
        self.process_events()
        self.assertEqual(window.tab_bar.count(), 2)
        self.assertEqual(self.plus_gap_i(window), 2)
        third_id_i = window.tab_id_list()[1]
        self.plot_controller.on_rename_tab(third_id_i, "x")
        self.process_events()
        self.assertEqual(self.plus_gap_i(window), 2)
        window.dock_button_dict[third_id_i].button.click()
        self.process_events()
        window = self.main_window.window_of_tab(second_id_i)
        self.assertEqual(window.tab_bar.count(), 1)
        self.assertEqual(self.plus_gap_i(window), 2)
        # A longer name and a shorter name of the single tab.
        for name_str in ("A much longer name for the only tab", "y"):
            with self.subTest(name_str=name_str):
                self.plot_controller.on_rename_tab(second_id_i, name_str)
                self.process_events()
                self.assertEqual(self.plus_gap_i(window), 2)

    @covers("LLFR-01205", "LLFR-01063", "HLFR-00015")
    def test_single_tab_bar_still_scrolls_when_narrow(self) -> None:
        """The bar of one tab asks for no more than its tab, and a tab
        wider than the row still lets the bar shrink to its scroll
        buttons.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.show()
        second_id_i = self.add_tab()
        self.main_window.signal_double_click_handler("speed")
        self.process_events()
        window = self.undock(second_id_i)
        window.show()
        self.process_events()
        tab_bar = window.tab_bar
        self.assertLessEqual(tab_bar.minimumSizeHint().width(),
                             tab_bar.sizeHint().width())
        self.plot_controller.on_rename_tab(second_id_i, "W" * 120)
        self.process_events()
        self.assertLess(tab_bar.minimumSizeHint().width(),
                        tab_bar.sizeHint().width())

    def one_tab_window(self):
        """Undock a new tab with a plot into a window of its own, shown.

        Inputs: none.
        Outputs: (id of the undocked tab, its UndockedWindow).
        """
        self.main_window.show()
        tab_id_i = self.add_tab()
        self.main_window.signal_double_click_handler("speed")
        self.process_events()
        window = self.undock(tab_id_i)
        window.resize(900, 500)
        window.show()
        self.process_events()
        return tab_id_i, window

    @covers("LLFR-01205", "LLFR-01063", "HLFR-00015")
    def test_qt_minimum_of_one_short_tab_is_the_cause(self) -> None:
        """#269, reviewer: Qt's own minimum width of a scrolling tab bar
        with one short tab is wider than the tab, which is what placed
        the "+" far from it; the window's bar no longer asks for it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QTabBar
        tab_id_i, window = self.one_tab_window()
        self.plot_controller.on_rename_tab(tab_id_i, "y")
        self.process_events()
        tab_bar = window.tab_bar
        self.assertTrue(tab_bar.usesScrollButtons())
        # The cause: QTabBar's minimum (the code before the fix).
        qt_minimum_i = QTabBar.minimumSizeHint(tab_bar).width()
        self.assertGreater(qt_minimum_i, tab_bar.sizeHint().width())
        # The fix: no wider than the tab.
        self.assertLessEqual(tab_bar.minimumSizeHint().width(),
                             tab_bar.sizeHint().width())
        self.assertEqual(self.plus_gap_i(window), 2)

    @covers("LLFR-01205", "LLFR-01063", "HLFR-00015", "HLFR-00126")
    def test_plus_two_pixels_after_the_second_tab_is_deleted(self) -> None:
        """#269, reviewer: when one of two tabs of a window is deleted,
        the "+" button is 2 pixels after the tab left.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, third_id_i, window = self.two_tabs_in_one_window()
        window.resize(900, 500)
        window.show()
        self.process_events()
        self.assertEqual(self.plus_gap_i(window), 2)
        self.plot_controller.on_delete_tab(third_id_i)
        self.process_events()
        window = self.main_window.window_of_tab(second_id_i)
        self.assertEqual(window.tab_bar.count(), 1)
        self.assertEqual(self.plus_gap_i(window), 2)

    @covers("LLFR-01205", "LLFR-01063", "LLFR-01032", "HLFR-00015",
            "HLFR-00130")
    def test_single_tab_gap_after_resize_and_panel_toggle(self) -> None:
        """#269, reviewer: with one tab, the "+" button stays 2 pixels
        after it when the window is resized and when its signal list
        panel is hidden and shown again.

        Inputs: none.
        Outputs: none.
        """
        _, window = self.one_tab_window()
        for width_i in (700, 1100):
            with self.subTest(width_i=width_i):
                window.resize(width_i, 500)
                self.process_events()
                self.assertEqual(self.plus_gap_i(window), 2)
        for step_str in ("hidden", "shown"):
            with self.subTest(panel=step_str):
                window.signal_list_button.click()
                self.process_events()
                self.assertEqual(self.plus_gap_i(window), 2)

    @covers("LLFR-01063", "LLFR-01205", "HLFR-00015", "HLFR-00014")
    def test_single_long_tab_wider_than_the_window_scrolls(self) -> None:
        """#269, reviewer: one tab wider than a narrow window still makes
        the bar narrower than its tab, with its scroll buttons shown, and
        the "+" button stays inside the tab row after the bar.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtWidgets import QToolButton
        tab_id_i, window = self.one_tab_window()
        self.plot_controller.on_rename_tab(tab_id_i, "W" * 120)
        window.resize(500, 500)
        self.process_events()
        tab_bar = window.tab_bar
        self.assertLess(tab_bar.width(), tab_bar.tabRect(0).width())
        scroll_button_list = [
            button for button in tab_bar.findChildren(QToolButton)
            if button.arrowType() != Qt.ArrowType.NoArrow]
        self.assertTrue(scroll_button_list)
        self.assertTrue(any(button.isVisible()
                            for button in scroll_button_list))
        bar_right_i = tab_bar.mapTo(
            window.tab_row, QPoint(tab_bar.width(), 0)).x()
        plus_left_i = window.add_tab_button.mapTo(
            window.tab_row, QPoint(0, 0)).x()
        self.assertGreaterEqual(plus_left_i, bar_right_i)
        plus_right_i = plus_left_i + window.add_tab_button.width()
        self.assertLessEqual(plus_right_i, window.tab_row.width())

    @covers("LLFR-01204", "LLFR-01205", "HLFR-00014", "HLFR-00015")
    def test_main_window_tabs_two_pixels_apart(self) -> None:
        """In the main window too, the tabs are 2 pixels apart and the
        "+" button 2 pixels after the last tab.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.main_window.show()
        self.add_tab()
        self.add_tab()
        self.process_events()
        tab_widget = self.panel.tab_widget
        tab_bar = tab_widget.tabBar()
        for index_i in range(1, tab_bar.count()):
            previous_rect = self.border_rect(tab_bar, index_i - 1)
            current_rect = self.border_rect(tab_bar, index_i)
            self.assertEqual(current_rect.x() - (previous_rect.x()
                                                 + previous_rect.width()),
                             2)
        last_rect = self.border_rect(tab_bar, tab_bar.count() - 1)
        right_i = tab_bar.mapTo(tab_widget, last_rect.topRight()).x()
        left_i = tab_widget.add_tab_button.mapTo(tab_widget,
                                                 QPoint(0, 0)).x()
        self.assertEqual(left_i - right_i - 1, 2)


class TabDragPreviewTest(WindowTabsViewTestCase):
    """The image of a dragged tab follows the pointer (LLFR-01208)."""

    def press_move_and_check(self, tab_bar, index_i: int, preview) -> None:
        """Press on a tab, move far with the button held, check the
        image, release and check it is gone.

        Inputs:
            tab_bar: the QTabBar of the tab.
            index_i: the index of the tab.
            preview: the TabDragPreview.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        from tests.view.test_undocked_windows_view import send_mouse
        from view import tab_drag_preview
        start_point = tab_bar.mapToGlobal(tab_bar.tabRect(index_i).center())
        send_mouse(tab_bar, "MouseButtonPress", start_point)
        self.assertFalse(preview.is_shown())
        first_point = start_point + QPoint(40, 60)
        second_point = start_point + QPoint(90, 130)
        send_mouse(tab_bar, "MouseMove", first_point, "LeftButton",
                   "NoButton")
        send_mouse(tab_bar, "MouseMove", second_point, "LeftButton",
                   "NoButton")
        self.process_events()
        self.assertTrue(preview.is_shown())
        self.assertLessEqual(preview.width(),
                             tab_drag_preview.PREVIEW_MAXIMUM_WIDTH_I)
        self.assertGreater(preview.width(), 0)
        self.assertLess(preview.windowOpacity(), 1.0)
        # LLFR-01411: the top-left pixel at the pointer tip (the owner's
        # answer of 2026-11-06 in #268; it was 12 pixels away before).
        self.assertEqual(tab_drag_preview.PREVIEW_OFFSET_I, 0)
        self.assertEqual(preview.pos(), second_point)
        self.assertEqual(preview.geometry().topLeft(), second_point)
        send_mouse(tab_bar, "MouseButtonRelease", second_point, "NoButton")
        self.process_events()
        self.assertFalse(preview.is_shown())

    @covers("LLFR-01208", "LLFR-01411", "HLFR-00143", "HLFR-00153")
    def test_image_follows_a_dragged_docked_tab(self) -> None:
        """A tab of the main window dragged with the left button shows a
        small semi-transparent image, its top-left pixel at the pointer
        tip, until the release.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.show()
        self.add_tab()
        self.main_window.signal_double_click_handler("speed")
        self.process_events()
        tab_bar = self.panel.tab_widget.tabBar()
        self.press_move_and_check(tab_bar, 1, self.panel.tab_drag_preview)

    @covers("LLFR-01208", "LLFR-01411", "HLFR-00143", "HLFR-00154",
            "HLFR-00155")
    def test_image_follows_a_dragged_window_tab(self) -> None:
        """A tab of an undocked window dragged with the left button
        shows the same image until the release.

        Inputs: none.
        Outputs: none.
        """
        _, _, _, window = self.two_tabs_in_one_window()
        window.show()
        self.process_events()
        with mock.patch.object(self.main_window, "request_window_tab_drop"):
            window.tab_drop_handler = lambda *argument_tuple: None
            self.press_move_and_check(window.tab_bar, 0,
                                      self.panel.tab_drag_preview)

    @covers("LLFR-01412", "LLFR-01411", "HLFR-00143")
    def test_image_is_cut_at_the_screen_edge(self) -> None:
        """Near the bottom-right corner of the screen, the image keeps its
        top-left pixel at the pointer tip, so the screen edge cuts it; it
        is never moved to the other side of the pointer.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.main_window.show()
        self.process_events()
        preview = self.panel.tab_drag_preview
        page = self.panel.page_dict[self.panel.current_tab_id()]
        screen_rect = self.main_window.screen().geometry()
        edge_point = screen_rect.bottomRight() - QPoint(10, 10)
        preview.start(page, edge_point)
        self.process_events()
        self.addCleanup(preview.stop)
        self.assertTrue(preview.is_shown())
        self.assertGreater(preview.width(), 10)
        self.assertEqual(preview.pos(), edge_point)
        preview.follow(edge_point + QPoint(5, 5))
        self.assertEqual(preview.pos(), edge_point + QPoint(5, 5))

    @covers("LLFR-01413", "LLFR-01150", "LLFR-01152", "HLFR-00154")
    def test_drop_lookup_leaves_the_image_out(self) -> None:
        """When the system names the image of the dragged tab as the
        window at the drop point (as it can, since the image is at the
        pointer tip), the window below it is used, and the image is shown
        again while the drag goes on.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        _, _, _, window = self.two_tabs_in_one_window()
        window.show()
        self.process_events()
        preview = self.panel.tab_drag_preview
        page = self.panel.page_dict[self.panel.current_tab_id()]
        point = window.mapToGlobal(window.rect().center())
        preview.start(page, point)
        self.addCleanup(preview.stop)
        with mock.patch.object(QApplication, "topLevelAt",
                               side_effect=[preview, window]) as lookup:
            found_window = self.main_window.window_at_point(point.x(),
                                                            point.y())
        self.assertIs(found_window, window)
        self.assertEqual(lookup.call_count, 2)
        self.assertTrue(preview.is_shown())
        # A point on the image over no window gives no window.
        with mock.patch.object(QApplication, "topLevelAt",
                               side_effect=[preview, None]):
            self.assertIsNone(self.main_window.window_at_point(point.x(),
                                                               point.y()))

    @covers("LLFR-01208")
    def test_image_is_scaled_to_200_pixels(self) -> None:
        """preview_pixmap keeps the page's proportions within 200 pixels.

        Inputs: none.
        Outputs: none.
        """
        from view.tab_drag_preview import preview_pixmap
        self.main_window.resize(1200, 800)
        self.main_window.show()
        self.process_events()
        page = self.panel.page_dict[self.panel.current_tab_id()]
        pixmap = preview_pixmap(page)
        self.assertEqual(pixmap.width(), 200)
        self.assertAlmostEqual(pixmap.height() / pixmap.width(),
                               page.height() / page.width(), delta=0.02)


class DropOnWindowViewTest(WindowTabsViewTestCase):
    """Dropping a dragged tab on a window or outside the plot panel."""

    @covers("LLFR-01150", "LLFR-01151", "LLFR-01158", "HLFR-00154")
    def test_docked_tab_dropped_on_a_window(self) -> None:
        """A docked tab dropped on a window's tab row joins it there and
        is shown.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.show()
        first_id_i = self.panel.current_tab_id()
        second_id_i = self.add_tab()
        third_id_i = self.add_tab()
        window = self.undock(second_id_i)
        self.process_events()
        row_point = window.tab_bar.mapToGlobal(
            window.tab_bar.tabRect(0).topLeft())
        with mock.patch.object(self.main_window, "window_at_point",
                               return_value=window):
            index_i = self.panel.tab_widget.indexOf(
                self.panel.page_dict[third_id_i])
            self.panel.finish_tab_drag(third_id_i, index_i,
                                       (row_point.x() + 1,
                                        row_point.y() + 1))
        self.process_events()
        self.assertEqual(window.tab_id_list(), [third_id_i, second_id_i])
        self.assertEqual(window.shown_tab_id(), third_id_i)
        self.assertEqual(self.panel.current_tab_id(), first_id_i)

    @covers("LLFR-01152", "LLFR-01031", "HLFR-00154")
    def test_window_tab_dropped_on_another_window(self) -> None:
        """A window's only tab dropped on another window moves there and
        its own window closes.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.main_window.show()
        second_id_i = self.add_tab()
        third_id_i = self.add_tab()
        first_window = self.undock(second_id_i)
        second_window = self.undock(third_id_i)
        drop_point = second_window.mapToGlobal(QPoint(50, 200))
        with mock.patch.object(self.main_window, "window_at_point",
                               return_value=second_window):
            self.main_window.request_window_tab_drop(
                first_window, second_id_i, 0, drop_point.x(),
                drop_point.y())
        self.process_events()
        self.assertIs(self.main_window.window_of_tab(second_id_i),
                      second_window)
        self.assertEqual(second_window.tab_id_list(),
                         [third_id_i, second_id_i])
        self.assertEqual(len(self.main_window.undocked_window_dict), 1)

    @covers("LLFR-01142", "HLFR-00153")
    def test_drop_on_the_signal_list_panel_undocks(self) -> None:
        """A tab dropped on the main window's signal list panel, outside
        the plot panel, opens a new window.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.main_window.show()
        self.add_tab()
        self.process_events()
        panel = self.main_window.signal_list_panel
        drop_point = panel.mapToGlobal(QPoint(panel.width() // 2,
                                              panel.height() // 2))
        tab_id_i = self.panel.tab_id_at_index(1)
        with mock.patch.object(self.main_window, "window_at_point",
                               return_value=None):
            self.panel.finish_tab_drag(tab_id_i, 1, (drop_point.x(),
                                                     drop_point.y()))
        self.process_events()
        self.assertTrue(self.tab(tab_id_i).undocked_b)
        self.assertIsNotNone(self.main_window.window_of_tab(tab_id_i))


class PreviewsInEveryWindowTest(WindowTabsViewTestCase):
    """The previews of several plots are shown in every shown window."""

    def setUp(self) -> None:
        """Show a tab in the main window and one in a window, with a
        hidden tab in that window.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        (self.first_id_i, second_id_i, third_id_i,
         self.window) = self.two_tabs_in_one_window()
        self.main_window.set_current_tab(self.first_id_i)
        self.main_window.signal_double_click_handler("angle")
        self.process_events()
        self.main_plot = self.panel.page_dict[
            self.first_id_i].plot_widget_list[0]
        # The window shows tab 3; tab 2 is a hidden tab of the window.
        self.shown_plot = self.panel.page_dict[
            third_id_i].plot_widget_list[0]
        self.hidden_plot = self.panel.page_dict[
            second_id_i].plot_widget_list[0]

    @covers("LLFR-00203", "LLFR-00665", "HLFR-00028")
    def test_flag_preview_in_every_shown_window(self) -> None:
        """The flag preview of the main window's plot is shown on the
        plot the window shows, not on its hidden tab.

        Inputs: none.
        Outputs: none.
        """
        with mock.patch.object(self.shown_plot,
                               "show_marker_preview") as shown_preview, \
                mock.patch.object(self.hidden_plot,
                                  "show_marker_preview") as hidden_preview:
            self.main_plot.marker_preview_changed.emit(1.25)
        shown_preview.assert_called_once_with(1.25)
        hidden_preview.assert_not_called()

    @covers("LLFR-01162", "LLFR-00303", "HLFR-00066")
    def test_area_preview_in_every_shown_window(self) -> None:
        """The preview of a new area is shown on the other shown time
        plots, and hidden from every plot afterwards.

        Inputs: none.
        Outputs: none.
        """
        self.window.show()
        self.process_events()
        self.shown_plot.area_preview_changed.emit(1.0, 2.0)
        self.assertEqual(self.main_plot.mirror_area_preview_tuple(),
                         (1.0, 2.0))
        self.assertEqual(self.hidden_plot.mirror_area_preview_tuple(), ())
        self.assertEqual(self.shown_plot.mirror_area_preview_tuple(), ())
        self.shown_plot.area_preview_changed.emit(math.nan, math.nan)
        self.assertEqual(self.main_plot.mirror_area_preview_tuple(), ())

    @covers("LLFR-01163", "LLFR-00208", "HLFR-00027")
    def test_span_selection_in_every_shown_window(self) -> None:
        """A time span selected on the main plot is shown on the plot of
        the window, and hidden afterwards.

        Inputs: none.
        Outputs: none.
        """
        self.main_plot.span_preview_changed.emit(0.5, 1.5)
        self.assertEqual(self.shown_plot.mirror_span_preview_tuple(),
                         (0.5, 1.5))
        self.assertEqual(self.hidden_plot.mirror_span_preview_tuple(), ())
        self.main_plot.span_preview_changed.emit(math.nan, math.nan)
        self.assertEqual(self.shown_plot.mirror_span_preview_tuple(), ())

    @covers("LLFR-01164", "LLFR-01163", "LLFR-01162", "HLFR-00038",
            "HLFR-00039")
    def test_mirror_previews_left_out_of_the_copy(self) -> None:
        """The previews of other plots are drawn by blitting only, so a
        full draw, as for the PDF and the copy, never holds them.

        Inputs: none.
        Outputs: none.
        """
        self.shown_plot.show_mirror_span(0.5, 1.5)
        self.shown_plot.show_mirror_area_preview(0.5, 1.5)
        axes = self.shown_plot.axes
        for artist in (self.shown_plot.span_line,
                       self.shown_plot.area_preview_band):
            self.assertNotIn(artist, axes.get_children())

    @covers("LLFR-01163", "LLFR-00693", "HLFR-00058")
    def test_frequency_plot_shows_no_mirror(self) -> None:
        """A frequency plot never shows the previews of other plots.

        Inputs: none.
        Outputs: none.
        """
        self.shown_plot.frequency_plot_b = True
        try:
            self.shown_plot.show_mirror_span(0.5, 1.5)
            self.shown_plot.show_mirror_area_preview(0.5, 1.5)
            self.assertEqual(self.shown_plot.mirror_span_preview_tuple(), ())
            self.assertEqual(self.shown_plot.mirror_area_preview_tuple(),
                             ())
        finally:
            self.shown_plot.frequency_plot_b = False


class PickerSubmenuTest(WindowTabsViewTestCase):
    """Plot matrix and Position open as submenus beside their menu."""

    def submenu_picker(self, menu, text_str: str):
        """Return the picker of an option's submenu.

        Inputs:
            menu: the QMenu.
            text_str: the option's text.
        Outputs: the SquarePicker in the submenu.
        """
        from PyQt6.QtWidgets import QWidgetAction
        action = self.menu_action(menu, text_str)
        self.assertIsNotNone(action)
        submenu = action.menu()
        self.assertIsNotNone(submenu)
        widget_list = [submenu_action.defaultWidget()
                       for submenu_action in submenu.actions()
                       if isinstance(submenu_action, QWidgetAction)]
        self.assertEqual(len(widget_list), 1)
        return widget_list[0]

    @covers("LLFR-01097", "LLFR-01100", "LLFR-01096", "HLFR-00146")
    def test_plot_matrix_submenu_chooses_and_closes(self) -> None:
        """The picker is in the submenu of "Plot matrix"; a click on a
        square gives the tab that matrix and closes the menus.

        Inputs: none.
        Outputs: none.
        """
        from view.matrix_picker import MatrixPicker
        tab_id_i = self.panel.current_tab_id()
        menu = self.panel.build_tab_menu(0)
        picker = self.submenu_picker(menu, "Plot matrix")
        self.assertIsInstance(picker, MatrixPicker)
        self.assertTrue(picker.embedded_b)
        with mock.patch.object(menu, "close") as menu_close:
            self.assertTrue(picker.choose_square(2, 3))
        self.process_events()
        menu_close.assert_called()
        tab = self.tab(tab_id_i)
        self.assertEqual((tab.row_count_i, tab.column_count_i), (2, 3))
        menu.deleteLater()

    @covers("LLFR-01114", "LLFR-01118", "LLFR-01112", "HLFR-00150")
    def test_position_submenu_swaps_and_closes(self) -> None:
        """The plot menu's "Position" holds the position picker; a click
        on the other plot's slot swaps the two plots.

        Inputs: none.
        Outputs: none.
        """
        from view.matrix_picker import PositionPicker
        self.main_window.show()
        self.main_window.signal_double_click_handler("speed")
        self.main_window.signal_double_click_handler("force")
        self.process_events()
        page = self.panel.page_dict[self.panel.current_tab_id()]
        first_plot, second_plot = page.plot_widget_list
        from PyQt6.QtCore import QPoint
        # The margin of the plot is an empty area: the plot menu.
        menu = first_plot.build_context_menu(QPoint(2, 2))
        picker = self.submenu_picker(menu, "Position")
        self.assertIsInstance(picker, PositionPicker)
        self.assertTrue(picker.choose_square(2, 1))
        self.process_events()
        self.assertEqual([widget.plot_id_i for widget in
                          self.panel.page_dict[
                              self.panel.current_tab_id()].plot_widget_list],
                         [second_plot.plot_id_i, first_plot.plot_id_i])
        menu.deleteLater()


if __name__ == "__main__":
    unittest.main()
