"""Tests for the plot matrix, the plot swap and the tab move (#205).

They run the plot controller with the fake view of
test_plot_controller: the "Plot matrix" choice of the tab menu
(HLFR-00146, HLFR-00147), the plots per tab and the Full Tab box
(HLFR-00018), the fill order (HLFR-00148), the swap of two plots
(HLFR-00150), the tab drag (HLFR-00143) and the undo and redo of each of
them (HLFR-00040, HLFR-00048).
"""

import unittest

from tests.support import covers
from tests.controller.test_plot_controller import PlotControllerTestCase


class MatrixControllerTestCase(PlotControllerTestCase):
    """Helpers that run the new handlers of the fake view."""

    def choose_matrix(self, row_count_i: int, column_count_i: int,
                      tab_id_i: int = -1) -> None:
        """Run the handler of a square chosen in the matrix picker.

        Inputs:
            row_count_i: rows of the chosen square.
            column_count_i: columns of the chosen square.
            tab_id_i: the tab, or -1 for the current tab.
        Outputs: none.
        """
        if tab_id_i < 0:
            tab_id_i = self.view.current_tab_id()
        self.view.handler_dict["plot_matrix"](tab_id_i, row_count_i,
                                              column_count_i)

    def swap(self, plot_id_i: int, other_plot_id_i: int) -> None:
        """Run the handler of a slot chosen in the position picker.

        Inputs:
            plot_id_i: the plot whose "Position" was chosen.
            other_plot_id_i: the plot of the chosen slot.
        Outputs: none.
        """
        self.view.handler_dict["plot_swap_handler"](plot_id_i,
                                                    other_plot_id_i)

    def move_tab(self, tab_id_i: int, index_i: int) -> None:
        """Run the handler of a tab dropped at a place.

        Inputs:
            tab_id_i: the dragged tab.
            index_i: its place when the button was released.
        Outputs: none.
        """
        self.view.handler_dict["move_tab"](tab_id_i, index_i)

    def add_plots(self, count_i: int) -> None:
        """Double-click signals to create plots in the current tab.

        Inputs:
            count_i: how many plots to create.
        Outputs: none.
        """
        for index_i in range(count_i):
            self.double_click(f"s{index_i % 10 + 1}")

    def undo(self) -> None:
        """Run the Undo handler.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["undo"]()

    def redo(self) -> None:
        """Run the Redo handler.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["redo"]()

    def current_tab(self):
        """Return the current tab of the model.

        Inputs: none.
        Outputs: the Tab.
        """
        return self.workspace.find_tab(self.view.current_tab_id())


class DefaultMatrixViewTest(MatrixControllerTestCase):
    """Every tab shown has its matrix (HLFR-00151)."""

    @covers("LLFR-01122", "HLFR-00151", "LLFR-00024", "LLFR-00026")
    def test_start_and_new_tabs_show_five_by_one(self) -> None:
        """The first tab and a "+" tab are shown with a 5 x 1 matrix.

        Inputs: none.
        Outputs: none.
        """
        first_tab_id_i = self.first_tab_id()
        self.assertEqual(self.view.tab_matrix_dict[first_tab_id_i], (5, 1))
        self.view.handler_dict["add_tab"]()
        new_tab_id_i = self.view.current_tab_id()
        self.assertNotEqual(new_tab_id_i, first_tab_id_i)
        self.assertEqual(self.view.tab_matrix_dict[new_tab_id_i], (5, 1))


class MatrixChoiceTest(MatrixControllerTestCase):
    """Choosing a plot matrix (HLFR-00146, HLFR-00147)."""

    @covers("LLFR-01100", "LLFR-01102", "LLFR-01103", "HLFR-00146")
    def test_choice_changes_the_tab_and_is_undoable(self) -> None:
        """A 2 x 3 choice is shown, kept with the plots and undoable.

        Inputs: none.
        Outputs: none.
        """
        self.add_plots(3)
        plot_id_list = self.current_plot_ids()
        self.choose_matrix(2, 3)
        tab_id_i = self.view.current_tab_id()
        self.assertEqual(self.view.tab_matrix_dict[tab_id_i], (2, 3))
        self.assertEqual(self.current_plot_ids(), plot_id_list)
        self.assertTrue(self.view.undo_enabled_b)
        # LLFR-01103: one undo returns to 5 x 1, one redo to 2 x 3.
        self.undo()
        self.assertEqual(self.view.tab_matrix_dict[tab_id_i], (5, 1))
        self.assertEqual(self.current_plot_ids(), plot_id_list)
        self.redo()
        self.assertEqual(self.view.tab_matrix_dict[tab_id_i], (2, 3))
        self.assertEqual((self.current_tab().row_count_i,
                          self.current_tab().column_count_i), (2, 3))

    @covers("LLFR-01104")
    def test_same_matrix_records_nothing(self) -> None:
        """Choosing 5 x 1 again leaves the undo history empty.

        Inputs: none.
        Outputs: none.
        """
        undo_count_i = self.controller.undo_history.depth()
        self.choose_matrix(5, 1)
        self.assertEqual(self.controller.undo_history.depth(),
                         undo_count_i)
        self.assertFalse(self.view.undo_enabled_b)

    @covers("LLFR-01107", "HLFR-00147")
    def test_too_small_matrix_changes_nothing(self) -> None:
        """With 4 plots, 1 x 3 is refused, with no undo step.

        Inputs: none.
        Outputs: none.
        """
        self.add_plots(4)
        undo_count_i = self.controller.undo_history.depth()
        self.choose_matrix(1, 3)
        tab = self.current_tab()
        self.assertEqual((tab.row_count_i, tab.column_count_i), (5, 1))
        self.assertEqual(self.controller.undo_history.depth(),
                         undo_count_i)

    @covers("LLFR-01101", "HLFR-00146")
    def test_matrix_of_one_tab_only(self) -> None:
        """A matrix change of one tab leaves the other tab unchanged.

        Inputs: none.
        Outputs: none.
        """
        first_tab_id_i = self.first_tab_id()
        self.view.handler_dict["add_tab"]()
        second_tab_id_i = self.view.current_tab_id()
        self.choose_matrix(3, 3, first_tab_id_i)
        self.assertEqual(self.view.tab_matrix_dict[first_tab_id_i], (3, 3))
        self.assertEqual(self.view.tab_matrix_dict[second_tab_id_i], (5, 1))

    @covers("LLFR-01100")
    def test_unknown_tab_is_ignored(self) -> None:
        """A request for a tab that is gone changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.choose_matrix(2, 2, 999)
        self.assertNotIn(999, self.view.tab_matrix_dict)
        self.assertFalse(self.view.undo_enabled_b)


class FullTabTest(MatrixControllerTestCase):
    """The plots per tab and the Full Tab box (HLFR-00018)."""

    @covers("LLFR-00031", "LLFR-00032", "HLFR-00018", "HLFR-00146")
    def test_limit_is_rows_times_columns(self) -> None:
        """A 2 x 2 tab takes 4 plots; the 5th shows the Full Tab box.

        Inputs: none.
        Outputs: none.
        """
        self.choose_matrix(2, 2)
        self.add_plots(4)
        self.assertEqual(len(self.current_plot_ids()), 4)
        self.assertEqual(self.view.full_tab_count_i, 0)
        self.add_plots(1)
        self.assertEqual(len(self.current_plot_ids()), 4)
        self.assertEqual(self.view.full_tab_count_i, 1)
        self.assertEqual(self.view.full_tab_matrix_list, [(2, 2)])

    @covers("LLFR-00031", "LLFR-01127", "HLFR-00018")
    def test_full_ten_by_ten_names_its_matrix(self) -> None:
        """A full 10 x 10 tab gives the box its 10 x 10 matrix.

        Inputs: none.
        Outputs: none.
        """
        self.choose_matrix(10, 10)
        self.add_plots(100)
        self.assertEqual(len(self.current_plot_ids()), 100)
        self.add_plots(1)
        self.assertEqual(len(self.current_plot_ids()), 100)
        self.assertEqual(self.view.full_tab_matrix_list, [(10, 10)])

    @covers("LLFR-00630", "LLFR-00032", "HLFR-00018")
    def test_enter_key_in_a_full_matrix(self) -> None:
        """The Enter key in a full 1 x 2 tab shows the box too.

        Inputs: none.
        Outputs: none.
        """
        self.choose_matrix(1, 2)
        self.add_plots(2)
        self.view.handler_dict["plot_selection"](["s3", "s4"])
        self.assertEqual(len(self.current_plot_ids()), 2)
        self.assertEqual(self.view.full_tab_matrix_list, [(1, 2)])


class SwapControllerTest(MatrixControllerTestCase):
    """Moving a plot by swapping it (HLFR-00150)."""

    @covers("LLFR-01118", "LLFR-01119", "LLFR-01120", "HLFR-00150")
    def test_swap_reorders_and_is_undoable(self) -> None:
        """Plots 1 and 3 swap; undo and redo give each order back.

        Inputs: none.
        Outputs: none.
        """
        self.add_plots(3)
        first_id_i, second_id_i, third_id_i = self.current_plot_ids()
        tab_id_i = self.view.current_tab_id()
        self.swap(first_id_i, third_id_i)
        self.assertEqual(self.current_plot_ids(),
                         [third_id_i, second_id_i, first_id_i])
        self.assertEqual(self.view.plot_order_dict[tab_id_i],
                         [third_id_i, second_id_i, first_id_i])
        # LLFR-01119: each plot keeps its curves.
        self.assertEqual(self.view.drawn_names(first_id_i), ["s1"])
        self.undo()
        self.assertEqual(self.current_plot_ids(),
                         [first_id_i, second_id_i, third_id_i])
        self.assertEqual(self.view.plot_id_list(tab_id_i),
                         [first_id_i, second_id_i, third_id_i])
        self.redo()
        self.assertEqual(self.current_plot_ids(),
                         [third_id_i, second_id_i, first_id_i])
        # LLFR-01108: the rebuilt view adds the plots in fill order.
        self.assertEqual(self.view.plot_id_list(tab_id_i),
                         [third_id_i, second_id_i, first_id_i])

    @covers("LLFR-01121")
    def test_own_slot_records_nothing(self) -> None:
        """Choosing the plot's own slot changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.add_plots(2)
        first_id_i, second_id_i = self.current_plot_ids()
        undo_count_i = self.controller.undo_history.depth()
        self.swap(first_id_i, first_id_i)
        self.assertEqual(self.current_plot_ids(), [first_id_i, second_id_i])
        self.assertEqual(self.controller.undo_history.depth(),
                         undo_count_i)
        self.assertNotIn("set_plot_order_view", self.view.method_names())

    @covers("LLFR-01118")
    def test_unknown_plot_is_ignored(self) -> None:
        """A swap with a plot that is gone changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.add_plots(1)
        (plot_id_i,) = self.current_plot_ids()
        self.swap(plot_id_i, 999)
        self.swap(999, plot_id_i)
        self.assertEqual(self.current_plot_ids(), [plot_id_i])


class TabMoveControllerTest(MatrixControllerTestCase):
    """Reordering the tabs by a drag (HLFR-00143)."""

    def add_two_tabs(self) -> list:
        """Add two tabs with "+".

        Inputs: none.
        Outputs: the ids of the three tabs, in order.
        """
        self.view.handler_dict["add_tab"]()
        self.view.handler_dict["add_tab"]()
        return [tab.tab_id_i for tab in self.workspace.tab_list]

    @covers("LLFR-01087", "LLFR-01089", "LLFR-01091", "HLFR-00143")
    def test_move_is_kept_and_undoable(self) -> None:
        """Tab 1 dropped at place 2 stays there; undo puts it back.

        Inputs: none.
        Outputs: none.
        """
        first_id_i, second_id_i, third_id_i = self.add_two_tabs()
        self.move_tab(first_id_i, 2)
        self.assertEqual([tab.tab_id_i for tab in self.workspace.tab_list],
                         [second_id_i, third_id_i, first_id_i])
        self.assertEqual(list(self.view.tab_dict),
                         [second_id_i, third_id_i, first_id_i])
        self.undo()
        self.assertEqual(list(self.view.tab_dict),
                         [first_id_i, second_id_i, third_id_i])
        self.redo()
        self.assertEqual(list(self.view.tab_dict),
                         [second_id_i, third_id_i, first_id_i])

    @covers("LLFR-01090")
    def test_drag_back_to_its_place_records_nothing(self) -> None:
        """A tab dropped at its own place leaves the history unchanged.

        Inputs: none.
        Outputs: none.
        """
        first_id_i, _, _ = self.add_two_tabs()
        undo_count_i = self.controller.undo_history.depth()
        self.move_tab(first_id_i, 0)
        self.move_tab(999, 1)
        self.assertEqual(self.controller.undo_history.depth(),
                         undo_count_i)
        self.assertNotIn("move_tab_view", self.view.method_names())

    @covers("LLFR-01089", "LLFR-00193")
    def test_move_after_undo_clears_redo(self) -> None:
        """A tab move done after an undo empties the redo history.

        Inputs: none.
        Outputs: none.
        """
        first_id_i, _, _ = self.add_two_tabs()
        self.undo()
        self.assertTrue(self.view.redo_enabled_b)
        self.move_tab(first_id_i, 1)
        self.assertFalse(self.view.redo_enabled_b)


if __name__ == "__main__":
    unittest.main()
