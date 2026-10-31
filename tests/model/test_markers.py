"""Tests for the vertical marker model in the workspace."""

import random
import unittest

from tests.support import covers

from model.workspace import (
    DEFAULT_MARKER_NAME_FORMAT_STR, MarkerIdCounter, Plot, VerticalMarker,
    Workspace)


def new_workspace_with_plot() -> tuple:
    """Return a seeded workspace and one plot that shows a signal.

    Inputs: none.
    Outputs: a tuple (workspace, plot); the plot is in the first tab and
        shows the signal "Speed".
    """
    workspace = Workspace(random.Random(2026))
    plot = workspace.add_plot(workspace.tab_list[0].tab_id_i)
    plot.add_curve("Speed")
    return workspace, plot


def marker_name_list(plot: Plot) -> list:
    """Return the names of the markers of a plot, in creation order.

    Inputs:
        plot: the Plot.
    Outputs: list of the marker names.
    """
    return [marker.name_str for marker in plot.marker_list]


class AddMarkerTest(unittest.TestCase):
    """Check placing markers and their default names."""

    @covers("LLFR-00085", "LLFR-00081", "HLFR-00028")
    def test_first_markers_are_numbered_from_one(self) -> None:
        """Markers are named "Marker 1", "Marker 2", "Marker 3".

        Inputs: none.
        Outputs: none.
        """
        _, plot = new_workspace_with_plot()
        self.assertEqual(plot.marker_list, [])
        self.assertEqual(plot.next_marker_number_i, 1)
        first_marker = plot.add_marker(1.5)
        plot.add_marker(2.5)
        plot.add_marker(0.25)
        self.assertIsInstance(first_marker, VerticalMarker)
        self.assertEqual(marker_name_list(plot),
                         ["Marker 1", "Marker 2", "Marker 3"])
        self.assertEqual([marker.time_s for marker in plot.marker_list],
                         [1.5, 2.5, 0.25])
        self.assertEqual(plot.next_marker_number_i, 4)

    @covers("LLFR-00085")
    def test_name_format_constant(self) -> None:
        """The default name format gives "Marker N".

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(DEFAULT_MARKER_NAME_FORMAT_STR.format(7),
                         "Marker 7")

    @covers("LLFR-00085", "HLFR-00028")
    def test_numbering_is_independent_per_plot(self) -> None:
        """Each plot counts its own markers from 1.

        Inputs: none.
        Outputs: none.
        """
        workspace, first_plot = new_workspace_with_plot()
        second_plot = workspace.add_plot(workspace.tab_list[0].tab_id_i)
        second_plot.add_curve("Speed")
        first_plot.add_marker(1.0)
        first_plot.add_marker(2.0)
        second_plot.add_marker(3.0)
        self.assertEqual(marker_name_list(first_plot),
                         ["Marker 1", "Marker 2"])
        self.assertEqual(marker_name_list(second_plot), ["Marker 1"])

    @covers("LLFR-00081")
    def test_time_is_stored_without_clamping(self) -> None:
        """Times outside the data range and negative times are kept.

        Inputs: none.
        Outputs: none.
        """
        _, plot = new_workspace_with_plot()
        negative_marker = plot.add_marker(-10.0)
        large_marker = plot.add_marker(1.0e9)
        self.assertEqual(negative_marker.time_s, -10.0)
        self.assertEqual(large_marker.time_s, 1.0e9)

    @covers("LLFR-00081", "HLFR-00020")
    def test_markers_are_not_curves(self) -> None:
        """Markers do not add curves or change the next curve color.

        Inputs: none.
        Outputs: none.
        """
        workspace = Workspace(random.Random(1))
        tab_id_i = workspace.tab_list[0].tab_id_i
        plain_plot = workspace.add_plot(tab_id_i)
        marked_plot = workspace.add_plot(tab_id_i)
        plain_plot.add_curve("Speed")
        marked_plot.add_curve("Speed")
        marked_plot.add_marker(1.0)
        marked_plot.add_marker(2.0)
        plain_curve = plain_plot.add_curve("Pressure")
        marked_curve = marked_plot.add_curve("Pressure")
        self.assertEqual(len(marked_plot.curve_list), 2)
        self.assertEqual(marked_curve.color_str, plain_curve.color_str)
        self.assertEqual(marked_plot.drawn_count_i, 2)

    @covers("LLFR-00081")
    def test_standalone_plot_has_its_own_counter(self) -> None:
        """A Plot made without a counter still gives markers ids.

        Inputs: none.
        Outputs: none.
        """
        plot = Plot(1, random.Random(3))
        first_marker = plot.add_marker(0.0)
        second_marker = plot.add_marker(1.0)
        self.assertNotEqual(first_marker.marker_id_i,
                            second_marker.marker_id_i)


class MarkerNumberReuseTest(unittest.TestCase):
    """Check that deleted marker numbers are not reused."""

    @covers("LLFR-00111", "LLFR-00085", "HLFR-00028", "HLFR-00031")
    def test_deleted_middle_number_is_not_reused(self) -> None:
        """Deleting "Marker 2" of three, the next one is "Marker 4".

        Inputs: none.
        Outputs: none.
        """
        _, plot = new_workspace_with_plot()
        plot.add_marker(1.0)
        second_marker = plot.add_marker(2.0)
        plot.add_marker(3.0)
        self.assertTrue(plot.remove_marker(second_marker.marker_id_i))
        new_marker = plot.add_marker(4.0)
        self.assertEqual(new_marker.name_str, "Marker 4")
        self.assertEqual(marker_name_list(plot),
                         ["Marker 1", "Marker 3", "Marker 4"])

    @covers("LLFR-00111", "LLFR-00085")
    def test_deleted_last_number_is_not_reused(self) -> None:
        """Deleting the newest marker, the next one takes a new number.

        Inputs: none.
        Outputs: none.
        """
        _, plot = new_workspace_with_plot()
        plot.add_marker(1.0)
        last_marker = plot.add_marker(2.0)
        plot.remove_marker(last_marker.marker_id_i)
        new_marker = plot.add_marker(5.0)
        self.assertEqual(new_marker.name_str, "Marker 3")

    @covers("LLFR-00111")
    def test_number_not_reused_after_all_markers_deleted(self) -> None:
        """With every marker deleted, numbering still continues.

        Inputs: none.
        Outputs: none.
        """
        _, plot = new_workspace_with_plot()
        only_marker = plot.add_marker(1.0)
        plot.remove_marker(only_marker.marker_id_i)
        self.assertEqual(plot.marker_list, [])
        self.assertEqual(plot.add_marker(2.0).name_str, "Marker 2")

    @covers("LLFR-00111", "LLFR-00112")
    def test_renamed_marker_does_not_free_its_number(self) -> None:
        """Renaming "Marker 1" does not make "Marker 1" a new default.

        Inputs: none.
        Outputs: none.
        """
        _, plot = new_workspace_with_plot()
        first_marker = plot.add_marker(1.0)
        plot.rename_marker(first_marker.marker_id_i, "Start")
        self.assertEqual(plot.add_marker(2.0).name_str, "Marker 2")


class MarkerIdTest(unittest.TestCase):
    """Check that marker ids are unique across the workspace."""

    @covers("LLFR-00081", "LLFR-00091")
    def test_ids_are_unique_across_plots_and_tabs(self) -> None:
        """Markers of different plots and tabs never share an id.

        Inputs: none.
        Outputs: none.
        """
        workspace, first_plot = new_workspace_with_plot()
        second_plot = workspace.add_plot(workspace.tab_list[0].tab_id_i)
        second_plot.add_curve("Speed")
        other_tab = workspace.add_tab()
        third_plot = workspace.add_plot(other_tab.tab_id_i)
        third_plot.add_curve("Speed")
        marker_list = [first_plot.add_marker(1.0),
                       second_plot.add_marker(1.0),
                       third_plot.add_marker(1.0),
                       first_plot.add_marker(2.0)]
        id_list = [marker.marker_id_i for marker in marker_list]
        self.assertEqual(len(set(id_list)), len(id_list))
        self.assertIs(first_plot.marker_id_counter,
                      third_plot.marker_id_counter)

    @covers("LLFR-00091", "LLFR-00111")
    def test_ids_are_not_reused_after_remove(self) -> None:
        """A removed marker's id is not given to a new marker.

        Inputs: none.
        Outputs: none.
        """
        _, plot = new_workspace_with_plot()
        removed_marker = plot.add_marker(1.0)
        plot.remove_marker(removed_marker.marker_id_i)
        new_marker = plot.add_marker(1.0)
        self.assertNotEqual(new_marker.marker_id_i,
                            removed_marker.marker_id_i)

    @covers("LLFR-00081", "LLFR-00015", "LLFR-00016")
    def test_reset_clears_markers_and_ids_keep_counting(self) -> None:
        """reset() removes plots with their markers; ids keep growing.

        Inputs: none.
        Outputs: none.
        """
        workspace, plot = new_workspace_with_plot()
        old_id_set = {plot.add_marker(1.0).marker_id_i,
                      plot.add_marker(2.0).marker_id_i}
        workspace.reset()
        self.assertEqual(workspace.tab_list[0].plot_list, [])
        new_plot = workspace.add_plot(workspace.tab_list[0].tab_id_i)
        new_plot.add_curve("Speed")
        self.assertEqual(new_plot.marker_list, [])
        new_marker = new_plot.add_marker(1.0)
        self.assertNotIn(new_marker.marker_id_i, old_id_set)
        self.assertGreater(new_marker.marker_id_i, max(old_id_set))
        # LLFR-00085: a new plot after reset counts from 1 again.
        self.assertEqual(new_marker.name_str, "Marker 1")

    @covers("LLFR-00081")
    def test_counter_counts_up(self) -> None:
        """MarkerIdCounter returns 1, 2, 3.

        Inputs: none.
        Outputs: none.
        """
        counter = MarkerIdCounter()
        self.assertEqual([counter.take_next_id() for _ in range(3)],
                         [1, 2, 3])


class FindAndMoveMarkerTest(unittest.TestCase):
    """Check finding and moving markers."""

    @covers("LLFR-00086", "HLFR-00029")
    def test_move_changes_time(self) -> None:
        """move_marker sets the new time and keeps the name and id.

        Inputs: none.
        Outputs: none.
        """
        _, plot = new_workspace_with_plot()
        marker = plot.add_marker(1.0)
        other_marker = plot.add_marker(2.0)
        self.assertTrue(plot.move_marker(marker.marker_id_i, 3.75))
        self.assertEqual(marker.time_s, 3.75)
        self.assertEqual(marker.name_str, "Marker 1")
        self.assertEqual(other_marker.time_s, 2.0)
        self.assertIs(plot.find_marker(marker.marker_id_i), marker)

    @covers("LLFR-00086")
    def test_move_unknown_id_returns_false(self) -> None:
        """Moving an id not in the plot changes nothing.

        Inputs: none.
        Outputs: none.
        """
        workspace, plot = new_workspace_with_plot()
        marker = plot.add_marker(1.0)
        other_plot = workspace.add_plot(workspace.tab_list[0].tab_id_i)
        other_plot.add_curve("Speed")
        self.assertFalse(plot.move_marker(marker.marker_id_i + 100, 9.0))
        self.assertFalse(other_plot.move_marker(marker.marker_id_i, 9.0))
        self.assertEqual(marker.time_s, 1.0)

    @covers("LLFR-00086", "LLFR-00088", "LLFR-00091")
    def test_find_marker(self) -> None:
        """find_marker returns the marker, or None for another plot's id.

        Inputs: none.
        Outputs: none.
        """
        workspace, plot = new_workspace_with_plot()
        marker = plot.add_marker(1.0)
        other_plot = workspace.add_plot(workspace.tab_list[0].tab_id_i)
        other_plot.add_curve("Speed")
        other_marker = other_plot.add_marker(1.0)
        self.assertIs(plot.find_marker(marker.marker_id_i), marker)
        self.assertIsNone(plot.find_marker(other_marker.marker_id_i))


class RenameMarkerTest(unittest.TestCase):
    """Check renaming markers."""

    @covers("LLFR-00088", "LLFR-00112", "HLFR-00030")
    def test_rename_stores_stripped_name(self) -> None:
        """A name with surrounding spaces is stored without them.

        Inputs: none.
        Outputs: none.
        """
        _, plot = new_workspace_with_plot()
        marker = plot.add_marker(1.0)
        self.assertTrue(plot.rename_marker(marker.marker_id_i,
                                           "  Valve open \t"))
        self.assertEqual(marker.name_str, "Valve open")
        self.assertEqual(plot.find_marker(marker.marker_id_i).name_str,
                         "Valve open")

    @covers("LLFR-00089", "HLFR-00030")
    def test_blank_names_keep_old_name(self) -> None:
        """Empty, space-only and tab-only names are refused.

        Inputs: none.
        Outputs: none.
        """
        _, plot = new_workspace_with_plot()
        marker = plot.add_marker(1.0)
        for blank_name_str in ("", "   ", "\t", " \t \n"):
            with self.subTest(blank_name_str=blank_name_str):
                self.assertFalse(plot.rename_marker(marker.marker_id_i,
                                                    blank_name_str))
                self.assertEqual(marker.name_str, "Marker 1")

    @covers("LLFR-00088")
    def test_rename_unknown_id_returns_false(self) -> None:
        """Renaming an id not in the plot changes nothing.

        Inputs: none.
        Outputs: none.
        """
        _, plot = new_workspace_with_plot()
        marker = plot.add_marker(1.0)
        self.assertFalse(plot.rename_marker(marker.marker_id_i + 1, "X"))
        self.assertEqual(marker.name_str, "Marker 1")


class RemoveMarkerTest(unittest.TestCase):
    """Check deleting markers and their interaction with plot deletion."""

    @covers("LLFR-00091", "HLFR-00031")
    def test_remove_marker(self) -> None:
        """remove_marker removes only that marker.

        Inputs: none.
        Outputs: none.
        """
        _, plot = new_workspace_with_plot()
        first_marker = plot.add_marker(1.0)
        second_marker = plot.add_marker(2.0)
        self.assertTrue(plot.remove_marker(first_marker.marker_id_i))
        self.assertEqual(plot.marker_list, [second_marker])
        self.assertIsNone(plot.find_marker(first_marker.marker_id_i))

    @covers("LLFR-00091")
    def test_remove_unknown_id_returns_false(self) -> None:
        """Removing an unknown or already removed id returns False.

        Inputs: none.
        Outputs: none.
        """
        _, plot = new_workspace_with_plot()
        marker = plot.add_marker(1.0)
        self.assertFalse(plot.remove_marker(marker.marker_id_i + 50))
        self.assertTrue(plot.remove_marker(marker.marker_id_i))
        self.assertFalse(plot.remove_marker(marker.marker_id_i))
        self.assertEqual(plot.marker_list, [])

    @covers("LLFR-00091", "LLFR-00039")
    def test_removing_markers_keeps_curves(self) -> None:
        """Deleting every marker leaves the plot and its curves.

        Inputs: none.
        Outputs: none.
        """
        workspace, plot = new_workspace_with_plot()
        marker = plot.add_marker(1.0)
        plot.remove_marker(marker.marker_id_i)
        self.assertIs(workspace.find_plot(plot.plot_id_i), plot)
        self.assertEqual(len(plot.curve_list), 1)

    @covers("LLFR-00051", "HLFR-00022", "HLFR-00019")
    def test_plot_with_markers_deleted_when_last_curve_removed(
            self) -> None:
        """Markers do not keep a plot whose last curve is removed.

        Inputs: none.
        Outputs: none.
        """
        workspace, plot = new_workspace_with_plot()
        plot.add_marker(1.0)
        plot.add_marker(2.0)
        self.assertFalse(plot.is_empty())
        self.assertTrue(workspace.remove_curve(plot.plot_id_i, "Speed"))
        self.assertIsNone(workspace.find_plot(plot.plot_id_i))
        self.assertEqual(workspace.tab_list[0].plot_list, [])

    @covers("LLFR-00049")
    def test_delete_plot_removes_its_markers(self) -> None:
        """Deleting a plot leaves other plots' markers untouched.

        Inputs: none.
        Outputs: none.
        """
        workspace, plot = new_workspace_with_plot()
        other_plot = workspace.add_plot(workspace.tab_list[0].tab_id_i)
        other_plot.add_curve("Speed")
        plot.add_marker(1.0)
        kept_marker = other_plot.add_marker(2.0)
        self.assertTrue(workspace.delete_plot(plot.plot_id_i))
        self.assertEqual(other_plot.marker_list, [kept_marker])


if __name__ == "__main__":
    unittest.main()
