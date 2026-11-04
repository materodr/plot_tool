"""Tests for the plot matrix of a tab, the plot swap and the tab order.

They check the model of HLFR-00145 to HLFR-00150, HLFR-00018 as
changed by #205, HLFR-00149 and HLFR-00142: the default 5 x 1 matrix,
the limit of rows times columns, the fill order, the matrices that are
too small, the swap of two plots and the move of a tab, and that each
of these is part of the state that an undo restores.
"""

import random
import unittest

from tests.support import covers

from model.workspace import (
    DEFAULT_MATRIX_COLUMNS_I, DEFAULT_MATRIX_ROWS_I, MAXIMUM_MATRIX_SIZE_I,
    MAXIMUM_PLOTS_PER_TAB_I, Workspace, is_matrix_size, matrix_row_list,
    matrix_slot_tuple)


def new_workspace() -> Workspace:
    """Return a workspace with a seeded random generator.

    Inputs: none.
    Outputs: a new Workspace with one empty tab.
    """
    return Workspace(random.Random(205))


def add_plots(workspace: Workspace, tab, count_i: int) -> list:
    """Add plots, each with one curve, to a tab.

    Inputs:
        workspace: the Workspace.
        tab: the Tab to fill.
        count_i: how many plots to add.
    Outputs: the new Plot objects, in order.
    """
    plot_list = []
    for index_i in range(count_i):
        plot = workspace.add_plot(tab.tab_id_i)
        plot.add_curve(f"Signal {index_i}")
        plot_list.append(plot)
    return plot_list


class DefaultMatrixTest(unittest.TestCase):
    """The default plot matrix of a new tab (HLFR-00150)."""

    @covers("LLFR-01087", "HLFR-00150", "LLFR-00024", "LLFR-00026")
    def test_every_new_tab_is_five_by_one(self) -> None:
        """The tab at start and each added tab have a 5 x 1 matrix.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        self.assertEqual((DEFAULT_MATRIX_ROWS_I, DEFAULT_MATRIX_COLUMNS_I),
                         (5, 1))
        first_tab = workspace.tab_list[0]
        second_tab = workspace.add_tab()
        named_tab = workspace.add_named_tab("Saved")
        for tab in (first_tab, second_tab, named_tab):
            self.assertEqual((tab.row_count_i, tab.column_count_i), (5, 1))
            self.assertEqual(tab.slot_count(), 5)
        self.assertEqual(MAXIMUM_PLOTS_PER_TAB_I, 5)

    @covers("LLFR-01087", "HLFR-00150")
    def test_reset_gives_the_default_matrix_again(self) -> None:
        """After a reset the first tab has the 5 x 1 matrix again.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        workspace.set_plot_matrix(workspace.tab_list[0].tab_id_i, 3, 3)
        workspace.reset()
        tab = workspace.tab_list[0]
        self.assertEqual((tab.row_count_i, tab.column_count_i), (5, 1))


class PlotLimitTest(unittest.TestCase):
    """The plots per tab are limited to rows times columns (HLFR-00018)."""

    @covers("LLFR-00031", "HLFR-00018", "HLFR-00145")
    def test_limit_follows_the_matrix(self) -> None:
        """A 2 x 3 tab takes 6 plots and refuses the 7th.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        self.assertTrue(workspace.set_plot_matrix(tab.tab_id_i, 2, 3))
        add_plots(workspace, tab, 6)
        self.assertTrue(tab.is_full())
        self.assertIsNone(workspace.add_plot(tab.tab_id_i))
        self.assertEqual(len(tab.plot_list), 6)

    @covers("LLFR-00031", "HLFR-00018", "LLFR-01092")
    def test_ten_by_ten_holds_a_hundred_plots(self) -> None:
        """The largest matrix holds 100 plots and is the largest one.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        self.assertFalse(tab.has_largest_matrix())
        self.assertTrue(workspace.set_plot_matrix(
            tab.tab_id_i, MAXIMUM_MATRIX_SIZE_I, MAXIMUM_MATRIX_SIZE_I))
        self.assertTrue(tab.has_largest_matrix())
        add_plots(workspace, tab, 100)
        self.assertTrue(tab.is_full())
        self.assertIsNone(workspace.add_plot(tab.tab_id_i))

    @covers("LLFR-00031", "LLFR-01066")
    def test_full_tab_frees_after_a_larger_matrix(self) -> None:
        """A full 5 x 1 tab takes a 6th plot once its matrix is 3 x 2.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        other_tab = workspace.add_tab()
        add_plots(workspace, tab, 5)
        self.assertTrue(tab.is_full())
        self.assertTrue(workspace.set_plot_matrix(tab.tab_id_i, 3, 2))
        self.assertFalse(tab.is_full())
        self.assertIsNotNone(workspace.add_plot(tab.tab_id_i))
        # LLFR-01066: the other tab keeps its own matrix.
        self.assertEqual((other_tab.row_count_i, other_tab.column_count_i),
                         (5, 1))


class MatrixChangeTest(unittest.TestCase):
    """Choosing a plot matrix (HLFR-00145, HLFR-00146)."""

    @covers("LLFR-01065", "LLFR-01067", "HLFR-00145")
    def test_change_keeps_the_plots_in_order(self) -> None:
        """A new matrix keeps every plot, with its curves, in order.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        plot_list = add_plots(workspace, tab, 4)
        plot_list[1].add_pinned_tip("Signal 1", 0.5, 2.0)
        self.assertTrue(workspace.set_plot_matrix(tab.tab_id_i, 2, 2))
        self.assertEqual((tab.row_count_i, tab.column_count_i), (2, 2))
        self.assertEqual(tab.plot_list, plot_list)
        self.assertEqual(len(plot_list[1].pinned_tip_list), 1)
        self.assertEqual(plot_list[2].curve_list[0].signal_name_str,
                         "Signal 2")

    @covers("LLFR-01069")
    def test_same_matrix_changes_nothing(self) -> None:
        """The tab's current matrix is refused as no change.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        state_tuple = workspace.state_tuple()
        self.assertFalse(workspace.set_plot_matrix(tab.tab_id_i, 5, 1))
        self.assertEqual(workspace.state_tuple(), state_tuple)

    @covers("LLFR-01071", "LLFR-01072", "HLFR-00146")
    def test_matrix_too_small_is_refused(self) -> None:
        """With 5 plots, 2 x 2 is refused and 1 x 5 is accepted.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        add_plots(workspace, tab, 5)
        self.assertFalse(tab.can_take_matrix(2, 2))
        self.assertFalse(workspace.set_plot_matrix(tab.tab_id_i, 2, 2))
        self.assertEqual((tab.row_count_i, tab.column_count_i), (5, 1))
        self.assertTrue(tab.can_take_matrix(1, 5))
        self.assertTrue(workspace.set_plot_matrix(tab.tab_id_i, 1, 5))

    @covers("LLFR-01062", "HLFR-00145")
    def test_sizes_outside_one_to_ten_are_refused(self) -> None:
        """Rows or columns of 0, 11, a float or a bool are refused.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab_id_i = workspace.tab_list[0].tab_id_i
        for row_value, column_value in ((0, 1), (1, 11), (2.0, 2),
                                        (True, 2), ("2", 2)):
            self.assertFalse(workspace.set_plot_matrix(
                tab_id_i, row_value, column_value))
        self.assertFalse(workspace.set_plot_matrix(999, 2, 2))
        self.assertTrue(is_matrix_size(1))
        self.assertTrue(is_matrix_size(10))
        self.assertFalse(is_matrix_size(11))

    @covers("LLFR-01068", "LLFR-00140")
    def test_matrix_is_part_of_the_undo_state(self) -> None:
        """A snapshot restores the matrix that the tab had.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab_id_i = workspace.tab_list[0].tab_id_i
        snapshot = workspace.snapshot(tab_id_i)
        workspace.set_plot_matrix(tab_id_i, 3, 4)
        self.assertFalse(workspace.is_unchanged_since(snapshot))
        workspace.restore(snapshot)
        tab = workspace.find_tab(tab_id_i)
        self.assertEqual((tab.row_count_i, tab.column_count_i), (5, 1))
        self.assertTrue(workspace.is_unchanged_since(snapshot))


class FillOrderTest(unittest.TestCase):
    """The fill order of the plots (HLFR-00147, HLFR-00148)."""

    @covers("LLFR-01073", "HLFR-00147")
    def test_slots_fill_rows_from_left_to_right(self) -> None:
        """4 plots in a 2 x 3 matrix: row 1 holds 3, row 2 holds 1.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        workspace.set_plot_matrix(tab.tab_id_i, 2, 3)
        plot_list = add_plots(workspace, tab, 4)
        self.assertEqual(
            [tab.plot_slot_tuple(plot.plot_id_i) for plot in plot_list],
            [(0, 0), (0, 1), (0, 2), (1, 0)])
        self.assertEqual(tab.plot_slot_tuple(999), ())
        self.assertEqual(matrix_slot_tuple(7, 3), (2, 1))

    @covers("LLFR-01075", "LLFR-01076", "HLFR-00148")
    def test_rows_in_use(self) -> None:
        """Only the rows that hold a plot are rows of the result.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(matrix_row_list([1, 2, 3, 4], 3), [[1, 2, 3], [4]])
        self.assertEqual(matrix_row_list([1, 2, 3, 4], 2), [[1, 2], [3, 4]])
        self.assertEqual(matrix_row_list([1], 10), [[1]])
        self.assertEqual(matrix_row_list([1, 2], 1), [[1], [2]])
        self.assertEqual(matrix_row_list([], 3), [])

    @covers("LLFR-01074", "LLFR-00050")
    def test_new_plot_takes_the_next_slot(self) -> None:
        """A new plot goes after the last one; a deletion closes the gap.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        workspace.set_plot_matrix(tab.tab_id_i, 2, 2)
        plot_list = add_plots(workspace, tab, 3)
        workspace.delete_plot(plot_list[0].plot_id_i)
        self.assertEqual(tab.plot_slot_tuple(plot_list[1].plot_id_i),
                         (0, 0))
        self.assertEqual(tab.plot_slot_tuple(plot_list[2].plot_id_i),
                         (0, 1))
        new_plot = workspace.add_plot(tab.tab_id_i)
        self.assertEqual(tab.plot_slot_tuple(new_plot.plot_id_i), (1, 0))


class SwapTest(unittest.TestCase):
    """Moving a plot by swapping it with another (HLFR-00149)."""

    @covers("LLFR-01083", "LLFR-01084", "HLFR-00149")
    def test_swap_exchanges_two_slots(self) -> None:
        """Plots 1 and 3 change slots; plot 2 keeps its slot.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        first, second, third = add_plots(workspace, tab, 3)
        third.add_pinned_tip("Signal 2", 0.25, 1.0)
        self.assertTrue(workspace.swap_plots(first.plot_id_i,
                                             third.plot_id_i))
        self.assertEqual(tab.plot_list, [third, second, first])
        self.assertEqual(len(third.pinned_tip_list), 1)
        self.assertEqual(third.curve_list[0].signal_name_str, "Signal 2")

    @covers("LLFR-01086")
    def test_own_slot_changes_nothing(self) -> None:
        """A swap with itself is refused.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        first, second = add_plots(workspace, tab, 2)
        self.assertFalse(workspace.swap_plots(first.plot_id_i,
                                              first.plot_id_i))
        self.assertEqual(tab.plot_list, [first, second])

    @covers("LLFR-01083", "HLFR-00149")
    def test_swap_needs_two_plots_of_one_tab(self) -> None:
        """Plots of different tabs and unknown plots are not swapped.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        first_tab = workspace.tab_list[0]
        second_tab = workspace.add_tab()
        (first,) = add_plots(workspace, first_tab, 1)
        (other,) = add_plots(workspace, second_tab, 1)
        self.assertFalse(workspace.swap_plots(first.plot_id_i,
                                              other.plot_id_i))
        self.assertFalse(workspace.swap_plots(first.plot_id_i, 999))
        self.assertFalse(workspace.swap_plots(999, first.plot_id_i))

    @covers("LLFR-01085", "LLFR-00140")
    def test_swap_is_part_of_the_undo_state(self) -> None:
        """A snapshot from before a swap gives the old order back.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        first, second = add_plots(workspace, tab, 2)
        snapshot = workspace.snapshot(tab.tab_id_i)
        workspace.swap_plots(first.plot_id_i, second.plot_id_i)
        self.assertFalse(workspace.is_unchanged_since(snapshot))
        workspace.restore(snapshot)
        self.assertEqual([plot.plot_id_i
                          for plot in workspace.tab_list[0].plot_list],
                         [first.plot_id_i, second.plot_id_i])


class TabMoveTest(unittest.TestCase):
    """Moving a tab to another place (HLFR-00142)."""

    @covers("LLFR-01052", "LLFR-01056", "HLFR-00142")
    def test_move_puts_the_tab_between_its_neighbors(self) -> None:
        """Tab 1 moved to index 2 goes after Tab 3.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        workspace.add_tab()
        workspace.add_tab()
        workspace.add_tab()
        first_id_i = workspace.tab_list[0].tab_id_i
        self.assertTrue(workspace.move_tab(first_id_i, 2))
        self.assertEqual([tab.name_str for tab in workspace.tab_list],
                         ["Tab 2", "Tab 3", "Tab 1", "Tab 4"])
        # A place past the end is the last place.
        self.assertTrue(workspace.move_tab(first_id_i, 99))
        self.assertEqual(workspace.tab_list[-1].tab_id_i, first_id_i)

    @covers("LLFR-01055")
    def test_move_to_its_own_place_changes_nothing(self) -> None:
        """A tab left at its place, or an unknown tab, is not moved.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        workspace.add_tab()
        state_tuple = workspace.state_tuple()
        self.assertFalse(workspace.move_tab(workspace.tab_list[1].tab_id_i,
                                            1))
        self.assertFalse(workspace.move_tab(999, 0))
        self.assertEqual(workspace.state_tuple(), state_tuple)

    @covers("LLFR-01054", "LLFR-00140")
    def test_tab_order_is_part_of_the_undo_state(self) -> None:
        """A snapshot from before a move gives the old order back.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        workspace.add_tab()
        snapshot = workspace.snapshot()
        workspace.move_tab(workspace.tab_list[1].tab_id_i, 0)
        self.assertFalse(workspace.is_unchanged_since(snapshot))
        workspace.restore(snapshot)
        self.assertEqual([tab.name_str for tab in workspace.tab_list],
                         ["Tab 1", "Tab 2"])


if __name__ == "__main__":
    unittest.main()
