"""Qt tests for the plot matrix, the pickers, the swap and the tab drag.

A real MainWindow and MainController are used (the setup of
test_plot_panel). They check the layout of the plots in the plot matrix
(HLFR-00147, HLFR-00148), the matrix picker of the tab menu
(HLFR-00145, HLFR-00146), the position picker of the plot menu
(HLFR-00149), the drag of a tab (HLFR-00142) and the undo of each of
them (HLFR-00040). No picker or menu is left open: pickers are shown
only where a test closes them, and show_picker is patched elsewhere.
"""

import unittest
from unittest import mock

from tests.support import covers, requires_qt
from tests.view.test_plot_panel import PlotPanelTestCase

# The tolerance, in pixels, of the sizes and places laid out by Qt.
LAYOUT_TOLERANCE_I = 3


@requires_qt
class PlotMatrixViewTestCase(PlotPanelTestCase):
    """Helpers for the plot matrix tests."""

    def add_plots(self, count_i: int) -> list:
        """Double-click signals to add plots to the current tab.

        Inputs:
            count_i: how many plots to add.
        Outputs: the plot widgets of the current tab, in fill order.
        """
        name_list = ["speed", "force", "angle", "Time"]
        for index_i in range(count_i):
            self.main_window.signal_double_click_handler(
                name_list[index_i % len(name_list)])
        self.main_window.show()
        self.process_events()
        return list(self.current_page().plot_widget_list)

    def choose_matrix(self, row_count_i: int, column_count_i: int) -> None:
        """Give the current tab a plot matrix through the controller.

        Inputs:
            row_count_i: number of rows.
            column_count_i: number of columns.
        Outputs: none.
        """
        self.controller.plot_controller.on_plot_matrix(
            self.panel.current_tab_id(), row_count_i, column_count_i)
        self.process_events()

    def model_plot_ids(self) -> list:
        """Return the plot ids of the current tab in the model.

        Inputs: none.
        Outputs: a list of int, in fill order.
        """
        workspace = self.controller.plot_controller.workspace
        tab = workspace.find_tab(self.panel.current_tab_id())
        return [plot.plot_id_i for plot in tab.plot_list]

    def undo(self) -> None:
        """Run the undo of the plot controller.

        Inputs: none.
        Outputs: none.
        """
        self.controller.plot_controller.on_undo()
        self.process_events()

    def send_picker_mouse(self, picker, type_name_str: str, row_i: int,
                          column_i: int) -> None:
        """Send a mouse event at the center of a square of a picker.

        Inputs:
            picker: the SquarePicker.
            type_name_str: "MouseMove" or "MouseButtonRelease".
            row_i: row of the square, from 1.
            column_i: column of the square, from 1.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        center = picker.square_rect(row_i, column_i).center()
        local_point = QPointF(center)
        released_b = type_name_str == "MouseButtonRelease"
        event = QMouseEvent(
            getattr(QEvent.Type, type_name_str), local_point,
            QPointF(picker.mapToGlobal(center)),
            Qt.MouseButton.LeftButton if released_b
            else Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
        self.application.sendEvent(picker, event)
        self.process_events()


class MatrixLayoutTest(PlotMatrixViewTestCase):
    """The plots laid out in the plot matrix (HLFR-00147, HLFR-00148)."""

    @covers("LLFR-01073", "LLFR-01075", "LLFR-01076", "LLFR-00069",
            "HLFR-00147", "HLFR-00148")
    def test_three_plots_in_a_two_by_two_matrix(self) -> None:
        """Row 1 holds plots 1 and 2 side by side; plot 3 stretches over
        the whole width of row 2; both rows have the same height.

        Inputs: none.
        Outputs: none.
        """
        self.choose_matrix(2, 2)
        first, second, third = self.add_plots(3)
        page = self.current_page()
        self.assertEqual(page.plot_slot_tuple(third), (1, 0))
        self.assertAlmostEqual(first.y(), second.y(),
                               delta=LAYOUT_TOLERANCE_I)
        self.assertLessEqual(first.x() + first.width(), second.x())
        self.assertAlmostEqual(first.width(), second.width(),
                               delta=LAYOUT_TOLERANCE_I)
        self.assertLessEqual(first.y() + first.height(), third.y())
        self.assertAlmostEqual(third.x(), first.x(),
                               delta=LAYOUT_TOLERANCE_I)
        self.assertAlmostEqual(third.x() + third.width(),
                               second.x() + second.width(),
                               delta=LAYOUT_TOLERANCE_I)
        self.assertAlmostEqual(first.height(), third.height(),
                               delta=LAYOUT_TOLERANCE_I)
        self.assertEqual(len(page.row_layout_list), 2)

    @covers("LLFR-01075", "LLFR-01076", "HLFR-00148")
    def test_only_rows_in_use_share_the_height(self) -> None:
        """Two plots in a 5 x 5 matrix use one row and the whole height.

        Inputs: none.
        Outputs: none.
        """
        self.choose_matrix(5, 5)
        first, second = self.add_plots(2)
        page = self.current_page()
        self.assertEqual(len(page.row_layout_list), 1)
        self.assertAlmostEqual(first.y(), second.y(),
                               delta=LAYOUT_TOLERANCE_I)
        self.assertGreater(first.height(), page.height() * 0.8)
        self.assertAlmostEqual(first.width() + second.width(),
                               page.width(),
                               delta=LAYOUT_TOLERANCE_I * 4)

    @covers("LLFR-01067", "LLFR-01065", "LLFR-00069", "LLFR-01087")
    def test_matrix_change_lays_the_same_plots_out_again(self) -> None:
        """Three stacked plots become one row in a 1 x 3 matrix, keeping
        their widgets and order.

        Inputs: none.
        Outputs: none.
        """
        plot_widget_list = self.add_plots(3)
        # LLFR-01087, LLFR-00069: the default 5 x 1 stacks them.
        x_set = {widget.x() for widget in plot_widget_list}
        self.assertEqual(len(x_set), 1)
        self.choose_matrix(1, 3)
        self.assertEqual(self.current_page().plot_widget_list,
                         plot_widget_list)
        y_set = {widget.y() for widget in plot_widget_list}
        self.assertEqual(len(y_set), 1)
        for left, right in zip(plot_widget_list, plot_widget_list[1:]):
            self.assertLessEqual(left.x() + left.width(), right.x())

    @covers("LLFR-00050", "LLFR-01073", "HLFR-00019")
    def test_deletion_moves_the_later_plots_back(self) -> None:
        """Deleting plot 1 of a 2 x 2 tab moves plot 3 up into row 1.

        Inputs: none.
        Outputs: none.
        """
        self.choose_matrix(2, 2)
        first, second, third = self.add_plots(3)
        first.plot_delete_requested.emit()
        self.process_events()
        page = self.current_page()
        self.assertEqual(page.plot_widget_list, [second, third])
        self.assertEqual(page.plot_slot_tuple(third), (0, 1))
        self.assertEqual(len(page.row_layout_list), 1)
        self.assertAlmostEqual(second.y(), third.y(),
                               delta=LAYOUT_TOLERANCE_I)

    @covers("LLFR-01066", "HLFR-00145")
    def test_each_tab_keeps_its_own_matrix(self) -> None:
        """A matrix change of one tab leaves the other page at 5 x 1.

        Inputs: none.
        Outputs: none.
        """
        first_tab_id_i = self.panel.current_tab_id()
        self.panel.request_add_tab()
        self.process_events()
        second_tab_id_i = self.panel.current_tab_id()
        self.choose_matrix(3, 4)
        self.assertEqual((self.panel.page_dict[second_tab_id_i].row_count_i,
                          self.panel.page_dict[second_tab_id_i]
                          .column_count_i), (3, 4))
        self.assertEqual((self.panel.page_dict[first_tab_id_i].row_count_i,
                          self.panel.page_dict[first_tab_id_i]
                          .column_count_i), (5, 1))


class MatrixPickerTest(PlotMatrixViewTestCase):
    """The matrix picker of the tab menu (HLFR-00145, HLFR-00146)."""

    def highlighted_set(self, picker) -> set:
        """Return the highlighted squares of a picker.

        Inputs:
            picker: the MatrixPicker.
        Outputs: a set of (row_i, column_i), from 1.
        """
        return {(row_i, column_i)
                for row_i in range(1, picker.row_count_i + 1)
                for column_i in range(1, picker.column_count_i + 1)
                if picker.is_square_highlighted(row_i, column_i)}

    @covers("LLFR-01064", "LLFR-01071", "HLFR-00145")
    def test_current_matrix_mark_stays_visible_over_pale_squares(
            self) -> None:
        """With 5 plots in the 5 x 1 matrix, rows 1 to 4 of column 1 are
        pale and still marked: the mark is a border drawn on top of the
        pale fill.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor
        from view.matrix_picker import (
            MARKED_COLOR_STR, PALE_COLOR_STR, SQUARE_BORDER_COLOR_STR)
        self.add_plots(5)
        picker = self.panel.build_matrix_picker(self.panel.current_tab_id())
        image = picker.grab().toImage()
        for row_i in range(1, 6):
            with self.subTest(row_i=row_i):
                self.assertTrue(picker.is_square_marked(row_i, 1))
                self.assertEqual(picker.square_border_color_str(row_i, 1),
                                 MARKED_COLOR_STR)
                rect = picker.square_rect(row_i, 1)
                ratio_f = max(image.devicePixelRatio(), 1.0)
                border_color = image.pixelColor(
                    int((rect.left() + 1) * ratio_f),
                    int(rect.center().y() * ratio_f))
                self.assertEqual(border_color.name(),
                                 QColor(MARKED_COLOR_STR).name())
        # LLFR-01071: rows 1 to 4 are pale under the mark.
        for row_i in range(1, 5):
            self.assertFalse(picker.is_square_enabled(row_i, 1))
            self.assertEqual(picker.square_fill_color_str(row_i, 1),
                             PALE_COLOR_STR)
        self.assertFalse(picker.is_square_marked(1, 2))
        self.assertEqual(picker.square_border_color_str(1, 6),
                         SQUARE_BORDER_COLOR_STR)
        picker.deleteLater()

    def open_picker_from_menu(self):
        """Choose "Plot matrix" in the tab menu, with show_picker patched.

        Inputs: none.
        Outputs: the MatrixPicker that would have been shown.
        """
        shown_list = []
        with mock.patch.object(
                self.panel, "show_picker",
                side_effect=lambda picker, point: shown_list.append(
                    picker)):
            menu = self.panel.build_tab_menu(0)
            self.menu_action(menu, "Plot matrix").trigger()
            self.process_events()
            menu.deleteLater()
        self.assertEqual(len(shown_list), 1)
        return shown_list[0]

    @covers("LLFR-01061", "LLFR-01062", "LLFR-01064", "HLFR-00145")
    def test_menu_opens_a_ten_by_ten_picker_with_the_current_matrix(
            self) -> None:
        """"Plot matrix" opens a 10 x 10 picker that marks the 5 x 1
        squares of the tab's matrix.

        Inputs: none.
        Outputs: none.
        """
        from view.matrix_picker import MatrixPicker
        picker = self.open_picker_from_menu()
        self.assertIsInstance(picker, MatrixPicker)
        self.assertEqual((picker.row_count_i, picker.column_count_i),
                         (10, 10))
        marked_set = {(row_i, column_i)
                      for row_i in range(1, 11)
                      for column_i in range(1, 11)
                      if picker.is_square_marked(row_i, column_i)}
        self.assertEqual(marked_set, {(row_i, 1) for row_i in range(1, 6)})
        self.assertEqual(picker.size_text(), "5 × 1")
        picker.deleteLater()

    @covers("LLFR-01063", "LLFR-01096", "HLFR-00145")
    def test_hover_highlights_the_rectangle_and_shows_its_size(
            self) -> None:
        """The pointer over the square of row 2 and column 3 highlights
        rows 1 to 2 and columns 1 to 3 and shows "2 × 3".

        Inputs: none.
        Outputs: none.
        """
        picker = self.panel.build_matrix_picker(self.panel.current_tab_id())
        picker.show()
        self.process_events()
        self.send_picker_mouse(picker, "MouseMove", 2, 3)
        self.assertEqual(picker.hover_tuple, (2, 3))
        highlighted_set = {(row_i, column_i)
                           for row_i in range(1, 11)
                           for column_i in range(1, 11)
                           if picker.is_square_highlighted(row_i, column_i)}
        self.assertEqual(highlighted_set,
                         {(row_i, column_i) for row_i in (1, 2)
                          for column_i in (1, 2, 3)})
        self.assertEqual(picker.size_text(), "2 × 3")
        # The picker paints without error with a highlight.
        picker.grab()
        picker.close()
        self.process_events()

    @covers("LLFR-01065", "LLFR-01068", "HLFR-00145")
    def test_click_on_a_square_gives_the_matrix_and_closes(self) -> None:
        """A click on the square of row 3 and column 2 gives the tab a
        3 x 2 matrix, closes the picker, and an undo gives 5 x 1 back.

        Inputs: none.
        Outputs: none.
        """
        self.add_plots(2)
        picker = self.panel.build_matrix_picker(self.panel.current_tab_id())
        picker.show()
        self.process_events()
        self.send_picker_mouse(picker, "MouseButtonRelease", 3, 2)
        self.assertEqual(picker.chosen_tuple, (3, 2))
        page = self.current_page()
        self.assertEqual((page.row_count_i, page.column_count_i), (3, 2))
        self.assertTrue(self.main_window.top_panel.undo_button.isEnabled())
        self.undo()
        page = self.current_page()
        self.assertEqual((page.row_count_i, page.column_count_i), (5, 1))
        self.assertEqual(len(page.plot_widget_list), 2)

    @covers("LLFR-01071", "LLFR-01072", "LLFR-01063", "LLFR-01096",
            "HLFR-00146")
    def test_pale_squares_do_nothing(self) -> None:
        """With 5 plots, the squares of fewer than 5 slots are pale and a
        click on one leaves the picker open and the matrix unchanged.

        Inputs: none.
        Outputs: none.
        """
        self.add_plots(5)
        picker = self.panel.build_matrix_picker(self.panel.current_tab_id())
        self.assertFalse(picker.is_square_enabled(2, 2))
        self.assertFalse(picker.is_square_enabled(1, 4))
        self.assertTrue(picker.is_square_enabled(1, 5))
        self.assertTrue(picker.is_square_enabled(3, 2))
        picker.show()
        self.process_events()
        # LLFR-01071: a hovered pale size is not highlighted and its size
        # is not shown; the text keeps the current matrix.
        self.send_picker_mouse(picker, "MouseMove", 2, 2)
        self.assertEqual(picker.hover_tuple, (2, 2))
        self.assertEqual(self.highlighted_set(picker), set())
        self.assertEqual(picker.size_text(), "5 \u00d7 1")
        # LLFR-01063: an enabled size still highlights its rectangle.
        self.send_picker_mouse(picker, "MouseMove", 3, 2)
        self.assertEqual(self.highlighted_set(picker),
                         {(row_i, column_i) for row_i in (1, 2, 3)
                          for column_i in (1, 2)})
        self.assertEqual(picker.size_text(), "3 \u00d7 2")
        self.send_picker_mouse(picker, "MouseButtonRelease", 2, 2)
        self.assertTrue(picker.isVisible())
        self.assertEqual(picker.chosen_tuple, ())
        page = self.current_page()
        self.assertEqual((page.row_count_i, page.column_count_i), (5, 1))
        picker.grab()
        picker.close()
        self.process_events()

    @covers("LLFR-01070", "HLFR-00145")
    def test_escape_closes_without_a_choice(self) -> None:
        """Esc closes the matrix picker and leaves the matrix unchanged.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QKeyEvent
        picker = self.panel.build_matrix_picker(self.panel.current_tab_id())
        picker.show()
        self.process_events()
        self.application.sendEvent(picker, QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_Escape,
            Qt.KeyboardModifier.NoModifier))
        self.process_events()
        self.assertFalse(picker.chosen_tuple)
        page = self.current_page()
        self.assertEqual((page.row_count_i, page.column_count_i), (5, 1))
        self.assertFalse(self.main_window.top_panel.undo_button.isEnabled())

    @covers("LLFR-01069")
    def test_current_matrix_closes_with_no_undo_step(self) -> None:
        """A click on the square of the current 5 x 1 matrix closes the
        picker and records nothing.

        Inputs: none.
        Outputs: none.
        """
        picker = self.panel.build_matrix_picker(self.panel.current_tab_id())
        picker.show()
        self.process_events()
        self.send_picker_mouse(picker, "MouseButtonRelease", 5, 1)
        self.assertEqual(picker.chosen_tuple, (5, 1))
        self.assertFalse(self.main_window.top_panel.undo_button.isEnabled())


class PositionPickerTest(PlotMatrixViewTestCase):
    """Moving a plot with the position picker (HLFR-00149)."""

    @covers("LLFR-01079", "LLFR-01080", "LLFR-01081", "LLFR-01082",
            "HLFR-00149")
    def test_picker_has_the_matrix_and_its_occupied_slots(self) -> None:
        """For 3 plots in a 2 x 2 tab, the picker of plot 2 is 2 x 2,
        with slot (2, 2) pale and slot (1, 2) marked.

        Inputs: none.
        Outputs: none.
        """
        from view.matrix_picker import PositionPicker
        self.choose_matrix(2, 2)
        second = self.add_plots(3)[1]
        shown_list = []
        with mock.patch.object(
                self.panel, "show_picker",
                side_effect=lambda picker, point: shown_list.append(
                    picker)):
            second.plot_position_requested.emit()
            self.process_events()
        self.assertEqual(len(shown_list), 1)
        picker = shown_list[0]
        self.assertIsInstance(picker, PositionPicker)
        self.assertEqual((picker.row_count_i, picker.column_count_i),
                         (2, 2))
        self.assertTrue(picker.is_square_enabled(1, 1))
        self.assertTrue(picker.is_square_enabled(2, 1))
        self.assertFalse(picker.is_square_enabled(2, 2))
        self.assertTrue(picker.is_square_marked(1, 2))
        self.assertFalse(picker.is_square_marked(1, 1))
        self.assertFalse(picker.choose_square(2, 2))
        picker.grab()
        picker.deleteLater()

    @covers("LLFR-01083", "LLFR-01084", "LLFR-01085", "HLFR-00149")
    def test_choosing_a_slot_swaps_and_undo_swaps_back(self) -> None:
        """Choosing slot (2, 1) for plot 2 swaps it with plot 3; the
        widgets keep their curves; an undo gives the old order back.

        Inputs: none.
        Outputs: none.
        """
        self.choose_matrix(2, 2)
        first, second, third = self.add_plots(3)
        id_list = [first.plot_id_i, second.plot_id_i, third.plot_id_i]
        picker = self.panel.build_position_picker(second.plot_id_i)
        picker.show()
        self.process_events()
        self.send_picker_mouse(picker, "MouseButtonRelease", 2, 1)
        page = self.current_page()
        self.assertEqual(page.plot_widget_list, [first, third, second])
        self.assertEqual(self.model_plot_ids(),
                         [id_list[0], id_list[2], id_list[1]])
        self.assertEqual(page.plot_slot_tuple(second), (1, 0))
        self.assertLessEqual(first.y() + first.height(), second.y())
        # LLFR-01084: the moved plot keeps its curve.
        self.assertEqual(list(second.curve_width_dict), ["force"])
        self.undo()
        self.assertEqual(self.model_plot_ids(), id_list)
        self.assertEqual([widget.plot_id_i for widget
                          in self.current_page().plot_widget_list], id_list)

    @covers("LLFR-01086", "LLFR-01070")
    def test_own_slot_and_escape_change_nothing(self) -> None:
        """The plot's own slot closes the picker with no swap and no
        undo step; Esc closes it too.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QKeyEvent
        first, second = self.add_plots(2)
        undo_depth_i = (self.controller.plot_controller.undo_history
                        .depth())
        picker = self.panel.build_position_picker(first.plot_id_i)
        picker.show()
        self.process_events()
        self.send_picker_mouse(picker, "MouseButtonRelease", 1, 1)
        self.assertEqual(picker.chosen_tuple, (1, 1))
        self.assertEqual(self.current_page().plot_widget_list,
                         [first, second])
        picker = self.panel.build_position_picker(first.plot_id_i)
        picker.show()
        self.process_events()
        self.application.sendEvent(picker, QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_Escape,
            Qt.KeyboardModifier.NoModifier))
        self.process_events()
        self.assertEqual(self.current_page().plot_widget_list,
                         [first, second])
        self.assertEqual(
            self.controller.plot_controller.undo_history.depth(),
            undo_depth_i)


class TabDragTest(PlotMatrixViewTestCase):
    """Reordering the tabs by a drag (HLFR-00142)."""

    def send_tab_bar_mouse(self, type_name_str: str, tab_index_i: int,
                           buttons_held_b: bool) -> None:
        """Pass a mouse event at the center of a tab to the panel.

        Inputs:
            type_name_str: "MouseButtonPress", "MouseMove" or
                "MouseButtonRelease".
            tab_index_i: the tab under the event.
            buttons_held_b: True when the left button is held after it.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        tab_bar = self.panel.tab_widget.tabBar()
        center = tab_bar.tabRect(tab_index_i).center()
        button = (Qt.MouseButton.NoButton if type_name_str == "MouseMove"
                  else Qt.MouseButton.LeftButton)
        buttons = (Qt.MouseButton.LeftButton if buttons_held_b
                   else Qt.MouseButton.NoButton)
        event = QMouseEvent(getattr(QEvent.Type, type_name_str),
                            QPointF(center),
                            QPointF(tab_bar.mapToGlobal(center)), button,
                            buttons, Qt.KeyboardModifier.NoModifier)
        self.panel.follow_tab_drag_event(event)

    def tab_names(self) -> list:
        """Return the names of the tabs in the model, in order.

        Inputs: none.
        Outputs: a list of str.
        """
        return [tab.name_str for tab
                in self.controller.plot_controller.workspace.tab_list]

    def add_tabs(self) -> None:
        """Add two tabs, so that there are Tab 1, Tab 2 and Tab 3.

        Inputs: none.
        Outputs: none.
        """
        self.panel.request_add_tab()
        self.panel.request_add_tab()
        self.main_window.show()
        self.process_events()
        self.assertEqual(self.tab_names(), ["Tab 1", "Tab 2", "Tab 3"])

    @covers("LLFR-01051", "LLFR-01052", "LLFR-01054", "LLFR-01056",
            "LLFR-00454", "HLFR-00142")
    def test_dragged_tab_stays_where_it_is_dropped(self) -> None:
        """Tab 1 dragged to the last place stays there, in the view and
        the model, as one undoable action; the drag counts as a mouse
        drag until the release.

        Inputs: none.
        Outputs: none.
        """
        tab_bar = self.panel.tab_widget.tabBar()
        self.assertTrue(tab_bar.isMovable())
        self.add_tabs()
        with mock.patch.object(self.panel, "left_button_down",
                               return_value=True):
            self.send_tab_bar_mouse("MouseButtonPress", 0, True)
            self.send_tab_bar_mouse("MouseMove", 0, True)
            self.assertTrue(self.main_window.is_mouse_drag_in_progress())
            # Qt moves the tab during the drag.
            tab_bar.moveTab(0, 2)
            self.send_tab_bar_mouse("MouseButtonRelease", 2, False)
            self.process_events()
            self.assertFalse(self.main_window.is_mouse_drag_in_progress())
        self.assertEqual(self.tab_names(), ["Tab 2", "Tab 3", "Tab 1"])
        self.assertEqual(self.main_window.tab_name_list(),
                         ["Tab 2", "Tab 3", "Tab 1"])
        self.undo()
        self.assertEqual(self.tab_names(), ["Tab 1", "Tab 2", "Tab 3"])
        self.assertEqual(self.main_window.tab_name_list(),
                         ["Tab 1", "Tab 2", "Tab 3"])

    @covers("LLFR-01055")
    def test_drag_back_to_its_place_changes_nothing(self) -> None:
        """A tab released at its starting place records no undo step.

        Inputs: none.
        Outputs: none.
        """
        self.add_tabs()
        undo_depth_i = (self.controller.plot_controller.undo_history
                        .depth())
        self.send_tab_bar_mouse("MouseButtonPress", 1, True)
        self.send_tab_bar_mouse("MouseMove", 1, True)
        self.send_tab_bar_mouse("MouseButtonRelease", 1, False)
        self.process_events()
        self.assertEqual(self.tab_names(), ["Tab 1", "Tab 2", "Tab 3"])
        self.assertEqual(
            self.controller.plot_controller.undo_history.depth(),
            undo_depth_i)

    @covers("LLFR-01053", "LLFR-01051", "HLFR-00142")
    def test_tab_dragged_out_of_the_row_stays_in_it(self) -> None:
        """Real mouse events on the tab bar that drag a tab far below the
        tab row leave every tab in the tab row of the main window.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        self.add_tabs()
        tab_bar = self.panel.tab_widget.tabBar()
        start = tab_bar.tabRect(0).center()
        far_point_list = [QPoint(start.x() + 40, start.y() + 300),
                          QPoint(start.x() + 400, start.y() + 600)]
        event_list = [(QEvent.Type.MouseButtonPress, start,
                       Qt.MouseButton.LeftButton,
                       Qt.MouseButton.LeftButton)]
        for point in far_point_list:
            event_list.append((QEvent.Type.MouseMove, point,
                               Qt.MouseButton.NoButton,
                               Qt.MouseButton.LeftButton))
        event_list.append((QEvent.Type.MouseButtonRelease,
                           far_point_list[-1], Qt.MouseButton.LeftButton,
                           Qt.MouseButton.NoButton))
        for event_type, point, button, buttons in event_list:
            self.application.sendEvent(tab_bar, QMouseEvent(
                event_type, QPointF(point),
                QPointF(tab_bar.mapToGlobal(point)), button, buttons,
                Qt.KeyboardModifier.NoModifier))
            self.process_events()
        self.process_events()
        self.assertFalse(self.panel.is_tab_drag_in_progress())
        self.assertEqual(self.panel.tab_widget.count(), 3)
        self.assertEqual(sorted(self.main_window.tab_name_list()),
                         ["Tab 1", "Tab 2", "Tab 3"])
        # The view and the model keep the same order.
        self.assertEqual(self.main_window.tab_name_list(), self.tab_names())
        for page in self.panel.page_dict.values():
            self.assertIs(page.window(), self.main_window)

    @covers("LLFR-01052", "LLFR-01073", "HLFR-00142")
    def test_moved_tab_keeps_its_plots_and_matrix(self) -> None:
        """A moved tab keeps its plots and its plot matrix.

        Inputs: none.
        Outputs: none.
        """
        self.choose_matrix(2, 2)
        plot_widget_list = self.add_plots(3)
        first_tab_id_i = self.panel.current_tab_id()
        self.add_tabs()
        tab_bar = self.panel.tab_widget.tabBar()
        self.send_tab_bar_mouse("MouseButtonPress", 0, True)
        self.send_tab_bar_mouse("MouseMove", 0, True)
        tab_bar.moveTab(0, 1)
        self.send_tab_bar_mouse("MouseButtonRelease", 1, False)
        self.process_events()
        self.assertEqual(self.tab_names(), ["Tab 2", "Tab 1", "Tab 3"])
        page = self.panel.page_dict[first_tab_id_i]
        self.assertEqual(page.plot_widget_list, plot_widget_list)
        self.assertEqual((page.row_count_i, page.column_count_i), (2, 2))


class LostReleaseTest(PlotMatrixViewTestCase):
    """A tab drag whose release was never seen (LLFR-00454)."""

    @covers("LLFR-00454", "LLFR-00207", "HLFR-00144")
    def test_drag_ends_when_the_left_button_is_up(self) -> None:
        """A tab drag left on by a lost release ends once the left button
        is up, so the 0 key resets the zoom again.

        Inputs: none.
        Outputs: none.
        """
        self.panel.tab_drag_in_progress_b = True
        with mock.patch.object(self.panel, "left_button_down",
                               return_value=True):
            self.assertTrue(self.main_window.is_mouse_drag_in_progress())
        with mock.patch.object(self.panel, "left_button_down",
                               return_value=False):
            self.assertFalse(self.main_window.is_mouse_drag_in_progress())
        self.assertFalse(self.panel.tab_drag_in_progress_b)


class MatrixExportTest(PlotMatrixViewTestCase):
    """The PDF and the copied image follow the plot matrix."""

    @covers("LLFR-00129", "LLFR-00133", "HLFR-00148", "HLFR-00038",
            "HLFR-00039")
    def test_export_images_keep_the_matrix_places(self) -> None:
        """In a 1 x 2 tab the exported plot images are side by side, at
        the places of the screen, and the copied page image is as wide
        as the page.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.choose_matrix(1, 2)
        first, second = self.add_plots(2)
        snapshot_list = plot_export.grab_exportable_images(
            self.panel.tab_widget)
        self.assertEqual(len(snapshot_list), 1)
        _, page_image, entry_list = snapshot_list[0]
        self.assertEqual(len(entry_list), 2)
        (first_rect, _), (second_rect, _) = entry_list
        self.assertAlmostEqual(first_rect.y(), second_rect.y(), delta=1.0)
        self.assertLessEqual(first_rect.x() + first_rect.width(),
                             second_rect.x())
        self.assertFalse(page_image.isNull())
        self.assertGreater(second_rect.x(), page_image.width() / 4.0
                           / max(page_image.devicePixelRatio(), 1.0))


if __name__ == "__main__":
    unittest.main()
