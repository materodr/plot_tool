"""Tests for the panel widths and the tab row layout.

Covers the resizable border between the plot panel and the signal list
panel (HLFR-00026: LLFR-00072, LLFR-00073) and the tab row of the plot
panel (LLFR-00025, LLFR-00106, LLFR-00107). A real MainWindow and
MainController are used and shown offscreen at fixed sizes.
"""

import unittest

from tests.support import covers, get_qt_application, requires_qt

# LLFR-00072: window sizes at which the start widths are checked.
WINDOW_SIZE_LIST = [(1200, 800), (800, 600), (1600, 900)]
# LLFR-00072: rounding of the splitter sizes, in pixels.
WIDTH_TOLERANCE_I = 3
# LLFR-00106: allowed distance of the first tab from the left edge.
LEFT_EDGE_TOLERANCE_I = 2
# LLFR-00025: allowed gap between the last tab and the "+" button.
BUTTON_GAP_TOLERANCE_I = 6
# LLFR-00025: enough tabs to overflow a narrow plot panel.
OVERFLOW_TAB_COUNT_I = 25


@requires_qt
class LayoutTestCase(unittest.TestCase):
    """Shared setup: a main window with its controllers, not yet shown."""

    def setUp(self) -> None:
        """Create the window and controllers.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        self.window_list = []
        self.main_window = self.create_window(1200, 800)
        self.panel = self.main_window.plot_panel

    def tearDown(self) -> None:
        """Close every window made by the test.

        Inputs: none.
        Outputs: none.
        """
        for main_window in self.window_list:
            main_window.close()
            main_window.deleteLater()
        self.process_events()

    def create_window(self, width_i: int, height_i: int):
        """Create a main window with controllers at a given size.

        Inputs:
            width_i: window width, in pixels.
            height_i: window height, in pixels.
        Outputs: the MainWindow (not shown).
        """
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        main_window = MainWindow()
        main_window.resize(width_i, height_i)
        main_window.controller = MainController(main_window)
        self.window_list.append(main_window)
        return main_window

    def process_events(self) -> None:
        """Let Qt run pending layouts, timers and deletions.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QCoreApplication, QEvent
        for _ in range(4):
            self.application.processEvents()
            QCoreApplication.sendPostedEvents(
                None, QEvent.Type.DeferredDelete.value)
        self.application.processEvents()

    def show_window(self, main_window) -> None:
        """Show a window and let it lay out.

        Inputs:
            main_window: the MainWindow.
        Outputs: none.
        """
        main_window.show()
        self.process_events()

    def width_tuple(self, main_window) -> tuple:
        """Return the widths of the plot panel and the signal list panel.

        Inputs:
            main_window: the MainWindow.
        Outputs: a tuple (plot_width_i, signal_list_width_i).
        """
        return (main_window.plot_panel.width(),
                main_window.signal_list_panel.width())


class InitialWidthTest(LayoutTestCase):
    """LLFR-00072: the signal list starts at 25% of the width."""

    @covers("LLFR-00072", "HLFR-00026", "HLFR-00001")
    def test_signal_list_takes_a_quarter_at_start(self) -> None:
        """At several window sizes the list gets 25%, the plots the rest.

        Inputs: none.
        Outputs: none.
        """
        for width_i, height_i in WINDOW_SIZE_LIST:
            with self.subTest(width_i=width_i, height_i=height_i):
                main_window = self.create_window(width_i, height_i)
                self.show_window(main_window)
                splitter = main_window.lower_splitter
                plot_width_i, list_width_i = self.width_tuple(main_window)
                panel_total_i = plot_width_i + list_width_i
                # The plot panel takes the rest: the two panels and the
                # handle fill the whole splitter.
                self.assertEqual(panel_total_i + splitter.handleWidth(),
                                 splitter.width())
                self.assertAlmostEqual(list_width_i, panel_total_i * 0.25,
                                       delta=WIDTH_TOLERANCE_I)
                self.assertAlmostEqual(plot_width_i, panel_total_i * 0.75,
                                       delta=WIDTH_TOLERANCE_I)
                # The splitter spans the window, apart from the margins
                # of the central layout, so 25% also holds for the window.
                self.assertAlmostEqual(list_width_i / width_i, 0.25,
                                       delta=0.02)

    @covers("LLFR-00072")
    def test_start_size_list_for_a_given_width(self) -> None:
        """The start sizes split any width 3:1 after the handle.

        Inputs: none.
        Outputs: none.
        """
        splitter = self.main_window.lower_splitter
        handle_width_i = splitter.handleWidth()
        for total_width_i in (400, 1001, 1203):
            with self.subTest(total_width_i=total_width_i):
                size_list = splitter.initial_size_list(total_width_i)
                self.assertEqual(len(size_list), 2)
                self.assertEqual(sum(size_list) + handle_width_i,
                                 total_width_i)
                self.assertAlmostEqual(
                    size_list[1], (total_width_i - handle_width_i) / 4,
                    delta=1)

    @covers("LLFR-00072", "LLFR-00073")
    def test_start_widths_applied_only_once(self) -> None:
        """Hiding and showing the window keeps a width the user chose.

        Inputs: none.
        Outputs: none.
        """
        self.show_window(self.main_window)
        splitter = self.main_window.lower_splitter
        self.assertTrue(splitter.initial_sizes_set_b)
        splitter.moveSplitter(500, 1)
        self.process_events()
        chosen_width_tuple = self.width_tuple(self.main_window)
        self.assertAlmostEqual(chosen_width_tuple[0], 500,
                               delta=WIDTH_TOLERANCE_I)
        self.main_window.hide()
        self.process_events()
        self.show_window(self.main_window)
        self.assertEqual(self.width_tuple(self.main_window),
                         chosen_width_tuple)


class DragBorderTest(LayoutTestCase):
    """LLFR-00073: the border between the panels can be dragged."""

    def drag_handle(self, distance_i: int) -> None:
        """Drag the splitter handle with the left mouse button.

        Inputs:
            distance_i: horizontal distance of the drag, in pixels
                (negative to the left).
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        handle = self.main_window.lower_splitter.handle(1)
        start = QPoint(handle.width() // 2, handle.height() // 2)
        step_count_i = 5
        point_list = [start] + [
            QPoint(start.x() + distance_i * step_i // step_count_i,
                   start.y())
            for step_i in range(1, step_count_i + 1)]
        # The handle moves during the drag, so every global position is
        # taken from where the handle was when the button was pressed.
        global_point_list = [handle.mapToGlobal(point)
                             for point in point_list]
        no_modifier = Qt.KeyboardModifier.NoModifier
        left_button = Qt.MouseButton.LeftButton
        press_event = QMouseEvent(
            QEvent.Type.MouseButtonPress, QPointF(start),
            QPointF(global_point_list[0]), left_button, left_button,
            no_modifier)
        self.application.sendEvent(handle, press_event)
        for global_point in global_point_list[1:]:
            local_point = handle.mapFromGlobal(global_point)
            move_event = QMouseEvent(
                QEvent.Type.MouseMove, QPointF(local_point),
                QPointF(global_point), Qt.MouseButton.NoButton,
                left_button, no_modifier)
            self.application.sendEvent(handle, move_event)
        end = global_point_list[-1]
        release_event = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(handle.mapFromGlobal(end)), QPointF(end), left_button,
            Qt.MouseButton.NoButton, no_modifier)
        self.application.sendEvent(handle, release_event)
        self.process_events()

    @covers("LLFR-00073", "HLFR-00026")
    def test_border_is_a_splitter_handle(self) -> None:
        """The two panels are split by a handle that cannot collapse them.

        Inputs: none.
        Outputs: none.
        """
        self.show_window(self.main_window)
        splitter = self.main_window.lower_splitter
        self.assertEqual(splitter.count(), 2)
        self.assertIs(splitter.widget(0), self.main_window.plot_panel)
        self.assertIs(splitter.widget(1),
                      self.main_window.signal_list_panel)
        self.assertFalse(splitter.childrenCollapsible())
        self.assertTrue(splitter.handle(1).isVisible())
        self.assertGreater(splitter.handleWidth(), 0)

    @covers("LLFR-00073", "HLFR-00026")
    def test_mouse_drag_changes_widths(self) -> None:
        """Dragging the handle left or right moves the border with it.

        Inputs: none.
        Outputs: none.
        """
        self.show_window(self.main_window)
        plot_width_i, list_width_i = self.width_tuple(self.main_window)
        self.drag_handle(-150)
        new_plot_width_i, new_list_width_i = self.width_tuple(
            self.main_window)
        self.assertAlmostEqual(new_plot_width_i, plot_width_i - 150,
                               delta=WIDTH_TOLERANCE_I)
        self.assertAlmostEqual(new_list_width_i, list_width_i + 150,
                               delta=WIDTH_TOLERANCE_I)
        self.drag_handle(250)
        newest_plot_width_i, newest_list_width_i = self.width_tuple(
            self.main_window)
        self.assertAlmostEqual(newest_plot_width_i, new_plot_width_i + 250,
                               delta=WIDTH_TOLERANCE_I)
        self.assertAlmostEqual(newest_list_width_i, new_list_width_i - 250,
                               delta=WIDTH_TOLERANCE_I)

    @covers("LLFR-00073", "HLFR-00026")
    def test_drag_to_the_ends_keeps_both_panels(self) -> None:
        """Dragging past either end never hides a panel.

        Inputs: none.
        Outputs: none.
        """
        self.show_window(self.main_window)
        splitter = self.main_window.lower_splitter
        for distance_i in (-5000, 5000):
            with self.subTest(distance_i=distance_i):
                self.drag_handle(distance_i)
                plot_width_i, list_width_i = self.width_tuple(
                    self.main_window)
                self.assertGreater(plot_width_i, 0)
                self.assertGreater(list_width_i, 0)
                self.assertTrue(self.main_window.plot_panel.isVisible())
                self.assertTrue(
                    self.main_window.signal_list_panel.isVisible())
                self.assertEqual(
                    plot_width_i + list_width_i + splitter.handleWidth(),
                    splitter.width())
        # The same through the splitter's own move method.
        splitter.moveSplitter(0, 1)
        self.process_events()
        self.assertGreater(self.main_window.plot_panel.width(), 0)
        splitter.moveSplitter(splitter.width(), 1)
        self.process_events()
        self.assertGreater(self.main_window.signal_list_panel.width(), 0)

    @covers("LLFR-00073", "LLFR-00025")
    def test_add_button_follows_a_narrower_plot_panel(self) -> None:
        """After a drag, the "+" button is still beside the last tab.

        Inputs: none.
        Outputs: none.
        """
        self.show_window(self.main_window)
        self.drag_handle(-300)
        tab_widget = self.panel.tab_widget
        tab_bar = tab_widget.tabBar()
        last_rect = tab_bar.tabRect(tab_bar.count() - 1)
        last_right_i = tab_bar.mapTo(tab_widget,
                                     last_rect.topRight()).x() + 1
        button_x_i = self.panel.add_tab_button.x()
        self.assertGreaterEqual(button_x_i, last_right_i)
        self.assertLessEqual(button_x_i - last_right_i,
                             BUTTON_GAP_TOLERANCE_I)


class TabRowTest(LayoutTestCase):
    """LLFR-00106, LLFR-00025, LLFR-00107: the tabs and the "+" button."""

    def add_tabs(self, tab_count_i: int) -> None:
        """Click the "+" button a number of times.

        Inputs:
            tab_count_i: number of tabs to add.
        Outputs: none.
        """
        for _ in range(tab_count_i):
            self.panel.add_tab_button.click()
        self.process_events()

    def tab_rect_in_widget(self, tab_index_i: int):
        """Return a tab's rectangle in tab widget coordinates.

        Inputs:
            tab_index_i: index of the tab.
        Outputs: a QRect.
        """
        tab_bar = self.panel.tab_widget.tabBar()
        tab_rect = tab_bar.tabRect(tab_index_i)
        tab_rect.moveTopLeft(tab_bar.mapTo(self.panel.tab_widget,
                                           tab_rect.topLeft()))
        return tab_rect

    def assert_button_in_tab_row(self) -> None:
        """Check the "+" button is visible, inside the panel, on the row.

        Inputs: none.
        Outputs: none.
        """
        tab_widget = self.panel.tab_widget
        button_geometry = self.panel.add_tab_button.geometry()
        first_rect = self.tab_rect_in_widget(0)
        self.assertTrue(self.panel.add_tab_button.isVisible())
        self.assertGreaterEqual(button_geometry.x(), 0)
        self.assertLessEqual(button_geometry.x() + button_geometry.width(),
                             tab_widget.width())
        self.assertEqual(button_geometry.y(), first_rect.y())
        self.assertEqual(button_geometry.height(), first_rect.height())

    def assert_button_beside_last_tab(self) -> None:
        """Check the "+" button is directly right of the last tab.

        Inputs: none.
        Outputs: none.
        """
        tab_bar = self.panel.tab_widget.tabBar()
        last_rect = self.tab_rect_in_widget(tab_bar.count() - 1)
        last_right_i = last_rect.x() + last_rect.width()
        button_x_i = self.panel.add_tab_button.x()
        self.assertGreaterEqual(button_x_i, last_right_i)
        self.assertLessEqual(button_x_i - last_right_i,
                             BUTTON_GAP_TOLERANCE_I)
        self.assert_button_in_tab_row()

    @covers("LLFR-00106", "HLFR-00014")
    def test_first_tab_starts_at_left_edge(self) -> None:
        """The first tab starts at the plot panel's left edge.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.show_window(self.main_window)
        tab_bar = self.panel.tab_widget.tabBar()
        for tab_count_i in (1, 3):
            with self.subTest(tab_count_i=tab_count_i):
                self.add_tabs(tab_count_i - tab_bar.count())
                first_rect = tab_bar.tabRect(0)
                left_i = tab_bar.mapTo(self.panel, first_rect.topLeft()).x()
                self.assertLessEqual(abs(left_i), LEFT_EDGE_TOLERANCE_I)
                # The tab row is at the top edge of the panel.
                top_i = tab_bar.mapTo(self.panel, QPoint(0, 0)).y()
                self.assertLessEqual(abs(top_i), LEFT_EDGE_TOLERANCE_I)
                self.assertFalse(tab_bar.expanding())

    @covers("LLFR-00106", "HLFR-00014")
    def test_tabs_are_packed_from_the_left(self) -> None:
        """Tabs follow each other from the left; free space is right.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_panel import TAB_SPACING_I
        self.show_window(self.main_window)
        self.add_tabs(2)
        tab_bar = self.panel.tab_widget.tabBar()
        for tab_index_i in range(1, tab_bar.count()):
            previous_rect = tab_bar.tabRect(tab_index_i - 1)
            current_rect = tab_bar.tabRect(tab_index_i)
            gap_i = current_rect.x() - (previous_rect.x()
                                        + previous_rect.width())
            self.assertGreaterEqual(gap_i, 0)
            self.assertLessEqual(gap_i, TAB_SPACING_I)
        last_rect = tab_bar.tabRect(tab_bar.count() - 1)
        right_i = tab_bar.mapTo(self.panel, last_rect.topRight()).x()
        self.assertLess(right_i, self.panel.width() // 2)
        self.assertIn("alignment: left",
                      self.panel.tab_widget.styleSheet())

    @covers("LLFR-00025", "HLFR-00015")
    def test_button_beside_last_tab_after_changes(self) -> None:
        """"+" follows the last tab: add, long rename, delete, resize.

        Inputs: none.
        Outputs: none.
        """
        self.show_window(self.main_window)
        self.assert_button_beside_last_tab()
        self.add_tabs(3)
        self.assert_button_beside_last_tab()
        last_tab_id_i = self.panel.current_tab_id()
        self.main_window.rename_tab_view(
            last_tab_id_i, "A much, much longer name for the last tab")
        self.process_events()
        self.assert_button_beside_last_tab()
        self.panel.request_delete_tab(last_tab_id_i)
        self.process_events()
        self.assertEqual(self.panel.tab_widget.count(), 3)
        self.assert_button_beside_last_tab()
        self.main_window.resize(900, 700)
        self.process_events()
        self.assert_button_beside_last_tab()
        self.main_window.resize(1400, 800)
        self.process_events()
        self.assert_button_beside_last_tab()

    @covers("LLFR-00025", "HLFR-00015")
    def test_button_stays_visible_when_tabs_overflow(self) -> None:
        """With too many tabs, "+" sits at the right end of the tab row.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.resize(800, 600)
        self.show_window(self.main_window)
        self.add_tabs(OVERFLOW_TAB_COUNT_I)
        tab_widget = self.panel.tab_widget
        tab_bar = tab_widget.tabBar()
        self.assertTrue(tab_widget.tabs_overflow())
        self.assert_button_in_tab_row()
        # Right after the tab bar (and its scroll buttons), so it covers
        # neither a tab nor a scroll button.
        bar_right_i = tab_bar.geometry().x() + tab_bar.width()
        button_x_i = self.panel.add_tab_button.x()
        self.assertGreaterEqual(button_x_i, bar_right_i)
        self.assertLessEqual(button_x_i - bar_right_i,
                             BUTTON_GAP_TOLERANCE_I)
        # It still adds a tab.
        tab_count_i = tab_widget.count()
        self.panel.add_tab_button.click()
        self.process_events()
        self.assertEqual(tab_widget.count(), tab_count_i + 1)
        self.assert_button_in_tab_row()
        # A wide window fits the tabs again: back beside the last tab.
        self.main_window.resize(4000, 600)
        self.process_events()
        if not tab_widget.tabs_overflow():
            self.assert_button_beside_last_tab()
        # Deleting tabs until they fit also brings it back.
        self.main_window.resize(800, 600)
        self.process_events()
        while tab_widget.count() > 2:
            self.panel.request_delete_tab(self.panel.current_tab_id())
            self.process_events()
        self.assertFalse(tab_widget.tabs_overflow())
        self.assert_button_beside_last_tab()

    @covers("LLFR-00107", "HLFR-00015")
    def test_button_has_tab_height_and_is_narrower(self) -> None:
        """"+" is as tall as an unselected tab and narrower than any tab.

        Inputs: none.
        Outputs: none.
        """
        self.show_window(self.main_window)
        self.add_tabs(2)
        tab_bar = self.panel.tab_widget.tabBar()
        current_index_i = tab_bar.currentIndex()
        unselected_index_i = 0 if current_index_i != 0 else 1
        unselected_rect = tab_bar.tabRect(unselected_index_i)
        button = self.panel.add_tab_button
        self.assertLessEqual(abs(button.height() - unselected_rect.height()),
                             1)
        narrowest_tab_width_i = min(tab_bar.tabRect(index_i).width()
                                    for index_i in range(tab_bar.count()))
        self.assertLess(button.width(), narrowest_tab_width_i)
        # Also with a one-letter tab name.
        self.main_window.rename_tab_view(self.panel.current_tab_id(), "A")
        self.process_events()
        narrowest_tab_width_i = min(tab_bar.tabRect(index_i).width()
                                    for index_i in range(tab_bar.count()))
        self.assertLess(button.width(), narrowest_tab_width_i)

    @covers("LLFR-00107")
    def test_button_and_unselected_tab_share_style_rules(self) -> None:
        """One shape block gives both the background, border and corners.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_panel
        style_sheet_str = self.panel.tab_widget.styleSheet()
        shared_str = plot_panel.SHARED_TAB_SHAPE_STR
        for selector_str in (
                f"QTabBar#{plot_panel.TAB_BAR_OBJECT_NAME_STR}"
                "::tab:!selected",
                f"QToolButton#{plot_panel.ADD_BUTTON_OBJECT_NAME_STR}"):
            with self.subTest(selector_str=selector_str):
                rule_start_i = style_sheet_str.index(selector_str + " {")
                rule_end_i = style_sheet_str.index("}", rule_start_i)
                self.assertIn(shared_str,
                              style_sheet_str[rule_start_i:rule_end_i])
        for value_str in (
                f"background: {plot_panel.TAB_BACKGROUND_COLOR_STR}",
                f"border: {plot_panel.TAB_BORDER_WIDTH_I}px solid "
                f"{plot_panel.TAB_BORDER_COLOR_STR}",
                f"border-top-left-radius: "
                f"{plot_panel.TAB_CORNER_RADIUS_I}px",
                f"border-top-right-radius: "
                f"{plot_panel.TAB_CORNER_RADIUS_I}px"):
            self.assertIn(value_str, shared_str)
        self.assertEqual(self.panel.add_tab_button.objectName(),
                         plot_panel.ADD_BUTTON_OBJECT_NAME_STR)
        self.assertEqual(self.panel.tab_widget.tabBar().objectName(),
                         plot_panel.TAB_BAR_OBJECT_NAME_STR)

    @covers("LLFR-00107")
    def test_button_and_unselected_tab_look_the_same(self) -> None:
        """The drawn background, border and corner pixels match.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor
        from view import plot_panel
        self.show_window(self.main_window)
        self.add_tabs(1)
        tab_widget = self.panel.tab_widget
        tab_bar = tab_widget.tabBar()
        unselected_index_i = 0 if tab_bar.currentIndex() != 0 else 1
        tab_rect = self.tab_rect_in_widget(unselected_index_i)
        button_rect = self.panel.add_tab_button.geometry()
        image = tab_widget.grab().toImage()
        ratio_f = image.devicePixelRatio()

        def pixel_name(x_i: int, y_i: int) -> str:
            """Return the color name of a pixel of the grabbed image.

            Inputs:
                x_i, y_i: the point, in tab widget coordinates.
            Outputs: the "#rrggbb" name of the pixel.
            """
            return image.pixelColor(round(x_i * ratio_f),
                                    round(y_i * ratio_f)).name()

        background_str = QColor(plot_panel.TAB_BACKGROUND_COLOR_STR).name()
        border_str = QColor(plot_panel.TAB_BORDER_COLOR_STR).name()
        for rect in (tab_rect, button_rect):
            middle_y_i = rect.y() + rect.height() // 2
            with self.subTest(rect=rect):
                # Inside, beside the text: the shared background.
                self.assertEqual(pixel_name(rect.x() + 3, middle_y_i),
                                 background_str)
                # Left edge: the shared border.
                self.assertEqual(pixel_name(rect.x(), middle_y_i),
                                 border_str)
        # Rounded top-left corner: the same pixels in both.
        for offset_tuple in ((0, 0), (1, 1), (2, 0), (0, 2)):
            with self.subTest(offset_tuple=offset_tuple):
                self.assertEqual(
                    pixel_name(tab_rect.x() + offset_tuple[0],
                               tab_rect.y() + offset_tuple[1]),
                    pixel_name(button_rect.x() + offset_tuple[0],
                               button_rect.y() + offset_tuple[1]))
        self.assertNotEqual(pixel_name(button_rect.x(), button_rect.y()),
                            border_str)


if __name__ == "__main__":
    unittest.main()
