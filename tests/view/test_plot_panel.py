"""Tests for the plot panel tabs and tab pages (HLFR-00014 to 00019).

A real MainWindow and MainController are used, so the tab state comes
from the real plot controller. Dialogs and menus are never executed:
QInputDialog.getText is patched and menu actions are triggered directly.
"""

import unittest
from unittest import mock

import numpy as np

from tests.support import covers, get_qt_application, requires_qt

PANEL_WIDTH_I = 800
PANEL_HEIGHT_I = 700
# LLFR-00025: allowed gap between the last tab and the "+" button.
BUTTON_GAP_TOLERANCE_I = 6


@requires_qt
class PlotPanelTestCase(unittest.TestCase):
    """Shared setup: main window, controllers and an opened file."""

    def setUp(self) -> None:
        """Create the window and controllers and "open" a file.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from controller.main_controller import MainController
        from model.signal_file import SignalFile
        from view.main_window import MainWindow
        self.main_window = MainWindow()
        self.main_window.resize(PANEL_WIDTH_I + 300, PANEL_HEIGHT_I + 100)
        self.controller = MainController(self.main_window)
        self.controller.start()
        time_array = np.linspace(0.0, 4.0, 41)
        self.signal_file = SignalFile("memory.csv", {
            "Time": time_array, "speed": time_array * 2.0,
            "force": np.sin(time_array), "angle": np.cos(time_array)})
        self.controller.plot_controller.on_file_opened(self.signal_file,
                                                       False)
        self.panel = self.main_window.plot_panel
        self.process_events()

    def tearDown(self) -> None:
        """Close the window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.process_events()

    def process_events(self) -> None:
        """Let Qt run pending layouts, timers and deletions.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QCoreApplication, QEvent
        for _ in range(3):
            self.application.processEvents()
            QCoreApplication.sendPostedEvents(
                None, QEvent.Type.DeferredDelete.value)
        self.application.processEvents()

    def current_page(self):
        """Return the TabPage of the current tab.

        Inputs: none.
        Outputs: the TabPage.
        """
        return self.panel.page_dict[self.panel.current_tab_id()]

    def menu_action(self, menu, text_str: str):
        """Return the action of a menu with the given text.

        Inputs:
            menu: a QMenu.
            text_str: the action text.
        Outputs: the QAction, or None.
        """
        for action in menu.actions():
            if action.text() == text_str:
                return action
        return None


class TabTest(PlotPanelTestCase):
    """Tabs, the "+" button and the tab menu."""

    @covers("LLFR-00024", "HLFR-00014")
    def test_one_tab_at_start(self) -> None:
        """The panel starts with exactly one tab, "Tab 1".

        Inputs: none.
        Outputs: none.
        """
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        fresh_window = MainWindow()
        MainController(fresh_window)
        self.assertEqual(fresh_window.plot_panel.tab_widget.count(), 1)
        self.assertEqual(fresh_window.tab_name_list(), ["Tab 1"])
        fresh_window.deleteLater()
        self.assertEqual(self.panel.tab_widget.count(), 1)

    def assert_button_beside_last_tab(self) -> None:
        """Check the "+" button is right after the last tab, same row.

        Inputs: none.
        Outputs: none.
        """
        tab_widget = self.panel.tab_widget
        tab_bar = tab_widget.tabBar()
        last_rect = tab_bar.tabRect(tab_bar.count() - 1)
        top_left = tab_bar.mapTo(tab_widget, last_rect.topLeft())
        last_right_i = top_left.x() + last_rect.width()
        button_geometry = self.panel.add_tab_button.geometry()
        self.assertTrue(self.panel.add_tab_button.isVisible())
        self.assertGreaterEqual(button_geometry.x(), last_right_i)
        self.assertLessEqual(button_geometry.x() - last_right_i,
                             BUTTON_GAP_TOLERANCE_I)
        # Same row: the button overlaps the tab vertically.
        self.assertLess(button_geometry.y(),
                        top_left.y() + last_rect.height())
        self.assertGreater(button_geometry.y() + button_geometry.height(),
                           top_left.y())
        self.assertEqual(self.panel.add_tab_button.text(), "+")

    @covers("LLFR-00025", "LLFR-00026", "HLFR-00015")
    def test_add_button_is_beside_last_tab_and_adds_tabs(self) -> None:
        """"+" sits beside the last tab, adds a tab and follows it.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.show()
        self.process_events()
        self.assert_button_beside_last_tab()
        far_right_i = self.panel.tab_widget.width() - 60
        self.assertLess(self.panel.add_tab_button.x(), far_right_i)
        self.panel.add_tab_button.click()
        self.process_events()
        self.assertEqual(self.panel.tab_name_list(), ["Tab 1", "Tab 2"])
        self.assertEqual(self.panel.tab_widget.currentIndex(), 1)
        self.assert_button_beside_last_tab()
        self.panel.add_tab_button.click()
        self.process_events()
        self.assertEqual(self.panel.tab_widget.count(), 3)
        self.assert_button_beside_last_tab()

    @covers("LLFR-00025", "LLFR-00030")
    def test_add_button_follows_rename_and_delete(self) -> None:
        """The button stays beside the last tab after rename and delete.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.show()
        self.panel.add_tab_button.click()
        self.panel.add_tab_button.click()
        self.process_events()
        last_tab_id_i = self.panel.current_tab_id()
        self.main_window.rename_tab_view(last_tab_id_i,
                                         "A much longer tab name")
        self.process_events()
        self.assert_button_beside_last_tab()
        self.panel.request_delete_tab(last_tab_id_i)
        self.process_events()
        self.assertEqual(self.panel.tab_widget.count(), 2)
        self.assert_button_beside_last_tab()

    @covers("LLFR-00027", "LLFR-00029", "LLFR-00066", "HLFR-00016")
    def test_tab_menu_options_and_last_tab(self) -> None:
        """The tab menu has Delete and Rename; Delete is off on one tab.

        Inputs: none.
        Outputs: none.
        """
        menu = self.panel.build_tab_menu(0)
        self.assertEqual([action.text() for action in menu.actions()],
                         ["Delete", "Rename"])
        self.assertFalse(self.menu_action(menu, "Delete").isEnabled())
        self.assertTrue(self.menu_action(menu, "Rename").isEnabled())
        self.menu_action(menu, "Delete").trigger()
        self.assertEqual(self.panel.tab_widget.count(), 1)
        self.panel.add_tab_button.click()
        menu = self.panel.build_tab_menu(0)
        self.assertTrue(self.menu_action(menu, "Delete").isEnabled())

    @covers("LLFR-00028", "LLFR-00066", "HLFR-00016")
    def test_delete_tab_removes_it_and_its_plots(self) -> None:
        """Delete removes the clicked tab and its plots.

        Inputs: none.
        Outputs: none.
        """
        self.panel.add_tab_button.click()
        second_tab_id_i = self.panel.current_tab_id()
        self.main_window.signal_double_click_handler("speed")
        plot_id_i = self.panel.plot_id_list(second_tab_id_i)[0]
        self.menu_action(self.panel.build_tab_menu(1), "Delete").trigger()
        self.process_events()
        self.assertEqual(self.panel.tab_name_list(), ["Tab 1"])
        self.assertIsNone(self.panel.plot_view(plot_id_i))
        menu = self.panel.build_tab_menu(0)
        self.assertFalse(self.menu_action(menu, "Delete").isEnabled())

    @covers("LLFR-00028")
    def test_delete_uses_the_clicked_tab(self) -> None:
        """Delete on the first tab removes the first, not the current.

        Inputs: none.
        Outputs: none.
        """
        self.panel.add_tab_button.click()
        self.panel.add_tab_button.click()
        self.menu_action(self.panel.build_tab_menu(0), "Delete").trigger()
        self.assertEqual(self.panel.tab_name_list(), ["Tab 2", "Tab 3"])

    @covers("LLFR-00030", "HLFR-00017")
    def test_rename_asks_for_name_and_shows_it(self) -> None:
        """Rename opens the dialog with the old name and shows the new.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QInputDialog
        with mock.patch.object(QInputDialog, "getText",
                               return_value=("Forces & speeds", True)
                               ) as dialog_mock:
            self.menu_action(self.panel.build_tab_menu(0),
                             "Rename").trigger()
        self.assertEqual(dialog_mock.call_count, 1)
        self.assertIn("Tab 1", dialog_mock.call_args.args)
        self.assertEqual(self.panel.tab_name_list(), ["Forces & speeds"])
        self.assertEqual(self.panel.tab_widget.tabText(0),
                         "Forces && speeds")
        self.assertEqual(self.controller.plot_controller.workspace
                         .tab_list[0].name_str, "Forces & speeds")

    @covers("LLFR-00067", "LLFR-00030", "HLFR-00017")
    def test_blank_or_cancelled_rename_keeps_name(self) -> None:
        """Blank names and Cancel keep the old name, with no message.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        with mock.patch.object(QMessageBox, "exec") as box_mock:
            for answer_tuple in (("", True), ("   ", True),
                                 ("New", False)):
                with mock.patch.object(QInputDialog, "getText",
                                       return_value=answer_tuple):
                    self.menu_action(self.panel.build_tab_menu(0),
                                     "Rename").trigger()
                self.assertEqual(self.panel.tab_name_list(), ["Tab 1"])
        self.assertEqual(box_mock.call_count, 0)

    @covers("LLFR-00027", "LLFR-00029")
    def test_right_click_off_a_tab_shows_no_menu(self) -> None:
        """A right-click on the tab bar outside the tabs does nothing.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        from PyQt6.QtWidgets import QMenu
        self.main_window.show()
        self.process_events()
        tab_bar = self.panel.tab_widget.tabBar()
        with mock.patch.object(QMenu, "exec") as exec_mock:
            self.panel.show_tab_menu(QPoint(tab_bar.width() + 50, 2))
            self.assertEqual(exec_mock.call_count, 0)
            self.panel.show_tab_menu(tab_bar.tabRect(0).center())
            self.assertEqual(exec_mock.call_count, 1)


class TabPageTest(PlotPanelTestCase):
    """Plots stacked in a tab page."""

    def add_plots(self, count_i: int) -> list:
        """Double-click signals to add plots to the current tab.

        Inputs:
            count_i: how many plots to add.
        Outputs: the plot widgets of the current tab, top to bottom.
        """
        name_list = ["speed", "force", "angle", "Time", "speed"]
        for name_str in name_list[:count_i]:
            self.main_window.signal_double_click_handler(name_str)
        self.main_window.show()
        self.process_events()
        return list(self.current_page().plot_widget_list)

    @covers("LLFR-00069", "LLFR-00019", "HLFR-00014", "HLFR-00018")
    def test_plots_are_stacked_vertically_in_order(self) -> None:
        """Plots are one below the other, in creation order.

        Inputs: none.
        Outputs: none.
        """
        plot_widget_list = self.add_plots(3)
        self.assertEqual(len(plot_widget_list), 3)
        x_list = [widget.x() for widget in plot_widget_list]
        self.assertEqual(len(set(x_list)), 1)
        for upper, lower in zip(plot_widget_list, plot_widget_list[1:]):
            self.assertLessEqual(upper.y() + upper.height(), lower.y())
            self.assertEqual(upper.width(), lower.width())
        self.assertEqual(
            [widget.plot_id_i for widget in plot_widget_list],
            self.panel.plot_id_list(self.panel.current_tab_id()))

    @covers("LLFR-00050", "LLFR-00049", "HLFR-00019")
    def test_remaining_plots_fill_the_page(self) -> None:
        """After deleting the middle plot, the other two fill the page.

        Inputs: none.
        Outputs: none.
        """
        first, middle, last = self.add_plots(3)
        page = self.current_page()
        page_height_i = page.height()
        old_height_i = first.height()
        middle.plot_delete_requested.emit()
        self.process_events()
        self.assertEqual(page.plot_widget_list, [first, last])
        self.assertIsNone(self.panel.plot_view(middle.plot_id_i))
        spacing_i = max(page.page_layout.spacing(), 0)
        self.assertGreater(first.height(), old_height_i)
        self.assertAlmostEqual(first.height(), last.height(), delta=2)
        self.assertGreaterEqual(first.height() + last.height()
                                + spacing_i + 2, page_height_i)
        self.assertLessEqual(first.y() + first.height(), last.y())

    @covers("LLFR-00022", "LLFR-00023", "HLFR-00013")
    def test_drop_on_empty_page_is_ignored(self) -> None:
        """A signal dropped on the page outside a plot does nothing.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QMimeData, QPoint, QPointF, Qt
        from PyQt6.QtGui import QDragEnterEvent, QDropEvent
        from PyQt6.QtWidgets import QMessageBox
        from view.signal_list_panel import SIGNAL_MIME_TYPE_STR
        self.main_window.show()
        self.process_events()
        page = self.current_page()
        self.assertFalse(page.acceptDrops())
        self.assertFalse(self.panel.acceptDrops())
        self.assertFalse(self.panel.tab_widget.acceptDrops())
        request_list = []
        self.panel.set_plot_handlers(
            signal_drop_handler=lambda *args: request_list.append(args))
        mime_data = QMimeData()
        mime_data.setData(SIGNAL_MIME_TYPE_STR, b"speed")
        center_point = QPoint(page.width() // 2, page.height() // 2)
        action = Qt.DropAction.CopyAction
        enter_event = QDragEnterEvent(center_point, action, mime_data,
                                      Qt.MouseButton.NoButton,
                                      Qt.KeyboardModifier.NoModifier)
        drop_event = QDropEvent(QPointF(center_point), action, mime_data,
                                Qt.MouseButton.NoButton,
                                Qt.KeyboardModifier.NoModifier)
        with mock.patch.object(QMessageBox, "exec") as box_mock:
            page.dragEnterEvent(enter_event)
            page.dropEvent(drop_event)
            self.process_events()
        self.assertFalse(enter_event.isAccepted())
        self.assertEqual(request_list, [])
        self.assertEqual(page.plot_widget_list, [])
        self.assertEqual(self.controller.plot_controller.workspace
                         .tab_list[0].plot_list, [])
        self.assertEqual(box_mock.call_count, 0)

    @covers("LLFR-00042")
    def test_new_plots_start_in_current_tip_mode(self) -> None:
        """Tip mode applies to existing plots and to later ones.

        Inputs: none.
        Outputs: none.
        """
        first = self.add_plots(1)[0]
        self.main_window.set_tip_mode(True)
        self.assertTrue(first.tip_mode_b)
        self.main_window.signal_double_click_handler("force")
        second = self.current_page().plot_widget_list[1]
        self.assertTrue(second.tip_mode_b)
        self.main_window.set_tip_mode(False)
        self.assertFalse(first.tip_mode_b)
        self.assertFalse(second.tip_mode_b)


class FacadeTest(PlotPanelTestCase):
    """Plain facade methods of MainWindow for the plot controller."""

    @covers("LLFR-00070", "LLFR-00068")
    def test_time_range_facade(self) -> None:
        """set_plot_time_range and plot_time_range use the widget.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.signal_double_click_handler("speed")
        plot_id_i = self.panel.plot_id_list(self.panel.current_tab_id())[0]
        start_s, end_s = self.main_window.plot_time_range(plot_id_i)
        self.assertAlmostEqual(start_s, 0.0)
        self.assertAlmostEqual(end_s, 4.0)
        self.main_window.set_plot_time_range(plot_id_i, 1.0, 2.0)
        start_s, end_s = self.main_window.plot_time_range(plot_id_i)
        self.assertAlmostEqual(start_s, 1.0)
        self.assertAlmostEqual(end_s, 2.0)
        self.assertEqual(self.main_window.plot_time_range(999), ())
        self.main_window.set_plot_time_range(999, 1.0, 2.0)
        self.main_window.draw_plot(999, [], [])

    @covers("LLFR-00070", "HLFR-00014")
    def test_zoom_in_one_plot_applies_to_tab(self) -> None:
        """A user zoom in one plot gives the same range to its tab.

        Inputs: none.
        Outputs: none.
        """
        for name_str in ("speed", "force"):
            self.main_window.signal_double_click_handler(name_str)
        first, second = self.current_page().plot_widget_list
        first.time_range_changed.emit(0.5, 1.5)
        start_s, end_s = second.time_range_tuple()
        self.assertAlmostEqual(start_s, 0.5)
        self.assertAlmostEqual(end_s, 1.5)

    @covers("LLFR-00019", "LLFR-00024")
    def test_unknown_ids_are_ignored(self) -> None:
        """Facade calls with unknown ids do not raise.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.add_plot_view(999, 1)
        self.main_window.remove_plot_view(999)
        self.main_window.remove_tab_view(999)
        self.main_window.rename_tab_view(999, "x")
        self.main_window.set_current_tab(999)
        self.panel.request_rename_tab(999)
        self.assertIsNone(self.main_window.plot_view(999))
        self.assertEqual(self.panel.plot_id_list(999), [])
        self.assertEqual(self.panel.tab_id_at_index(42), -1)
        self.main_window.clear_tab_views()
        self.assertEqual(self.main_window.current_tab_id(), -1)
        self.assertEqual(self.main_window.tab_name_list(), [])


if __name__ == "__main__":
    unittest.main()
