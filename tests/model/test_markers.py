"""Tests for the vertical marker model in the workspace.

The vertical markers belong to the workspace and are shared by every
plot of every tab (LLFR-00205).
"""

import random
import unittest

from tests.support import covers

from model.workspace import (
    DEFAULT_MARKER_NAME_FORMAT_STR, MarkerIdCounter, VerticalMarker,
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


def add_plot_in_new_tab(workspace: Workspace):
    """Add a tab with one plot that shows a signal.

    Inputs:
        workspace: the Workspace.
    Outputs: the new Plot.
    """
    tab = workspace.add_tab()
    plot = workspace.add_plot(tab.tab_id_i)
    plot.add_curve("Speed")
    return plot


def marker_name_list(workspace: Workspace) -> list:
    """Return the names of the markers, in creation order.

    Inputs:
        workspace: the Workspace.
    Outputs: list of the marker names.
    """
    return [marker.name_str for marker in workspace.marker_list]


class AddMarkerTest(unittest.TestCase):
    """Check placing markers and their default names."""

    @covers("LLFR-00085", "LLFR-00081", "HLFR-00028")
    def test_first_markers_are_numbered_from_one(self) -> None:
        """Markers are named "Marker 1", "Marker 2", "Marker 3".

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        self.assertEqual(workspace.marker_list, [])
        self.assertEqual(workspace.next_marker_number_i, 1)
        first_marker = workspace.add_marker(1.5)
        workspace.add_marker(2.5)
        workspace.add_marker(0.25)
        self.assertIsInstance(first_marker, VerticalMarker)
        self.assertEqual(marker_name_list(workspace),
                         ["Marker 1", "Marker 2", "Marker 3"])
        self.assertEqual([marker.time_s for marker in workspace.marker_list],
                         [1.5, 2.5, 0.25])
        self.assertEqual(workspace.next_marker_number_i, 4)

    @covers("LLFR-00085")
    def test_name_format_constant(self) -> None:
        """The default name format gives "Marker N".

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(DEFAULT_MARKER_NAME_FORMAT_STR.format(7),
                         "Marker 7")

    @covers("LLFR-00205", "LLFR-00085", "HLFR-00028")
    def test_markers_are_shared_by_every_plot(self) -> None:
        """The plots keep no markers; one shared list and one count.

        Inputs: none.
        Outputs: none.
        """
        workspace, first_plot = new_workspace_with_plot()
        other_tab_plot = add_plot_in_new_tab(workspace)
        workspace.add_marker(1.0)
        workspace.add_marker(2.0)
        third_plot = add_plot_in_new_tab(workspace)
        workspace.add_marker(3.0)
        self.assertEqual(marker_name_list(workspace),
                         ["Marker 1", "Marker 2", "Marker 3"])
        for plot in (first_plot, other_tab_plot, third_plot):
            self.assertFalse(hasattr(plot, "marker_list"))

    @covers("LLFR-00081")
    def test_time_is_stored_without_clamping(self) -> None:
        """Times outside the data range and negative times are kept.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        negative_marker = workspace.add_marker(-10.0)
        large_marker = workspace.add_marker(1.0e9)
        self.assertEqual(negative_marker.time_s, -10.0)
        self.assertEqual(large_marker.time_s, 1.0e9)

    @covers("LLFR-00081", "HLFR-00020")
    def test_markers_are_not_curves(self) -> None:
        """Markers do not add curves or change the next curve color.

        Inputs: none.
        Outputs: none.
        """
        workspace, plot = new_workspace_with_plot()
        first_color_str = plot.curve_list[0].color_str
        workspace.add_marker(1.0)
        workspace.add_marker(2.0)
        self.assertEqual(len(plot.curve_list), 1)
        self.assertEqual(plot.drawn_count_i, 1)
        self.assertNotEqual(plot.add_curve("Pressure").color_str,
                            first_color_str)


class MarkerNumberReuseTest(unittest.TestCase):
    """Check that marker numbers are never reused (LLFR-00111)."""

    @covers("LLFR-00111", "LLFR-00085")
    def test_deleted_middle_number_is_not_reused(self) -> None:
        """After deleting "Marker 2", the next one is "Marker 4".

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        workspace.add_marker(1.0)
        second_marker = workspace.add_marker(2.0)
        workspace.add_marker(3.0)
        self.assertTrue(workspace.remove_marker(second_marker.marker_id_i))
        new_marker = workspace.add_marker(4.0)
        self.assertEqual(new_marker.name_str, "Marker 4")
        self.assertEqual(marker_name_list(workspace),
                         ["Marker 1", "Marker 3", "Marker 4"])

    @covers("LLFR-00111")
    def test_deleted_last_and_only_numbers_are_not_reused(self) -> None:
        """Deleting the last or the only marker does not lower N.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        workspace.add_marker(1.0)
        last_marker = workspace.add_marker(2.0)
        workspace.remove_marker(last_marker.marker_id_i)
        self.assertEqual(workspace.add_marker(5.0).name_str, "Marker 3")
        for marker in list(workspace.marker_list):
            workspace.remove_marker(marker.marker_id_i)
        self.assertEqual(workspace.marker_list, [])
        self.assertEqual(workspace.add_marker(2.0).name_str, "Marker 4")

    @covers("LLFR-00111", "LLFR-00089")
    def test_renamed_marker_keeps_its_number_used(self) -> None:
        """A renamed "Marker 1" still uses up number 1.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        first_marker = workspace.add_marker(1.0)
        workspace.rename_marker(first_marker.marker_id_i, "Start")
        self.assertEqual(workspace.add_marker(2.0).name_str, "Marker 2")

    @covers("LLFR-00111", "LLFR-00138")
    def test_undone_placement_does_not_free_its_number(self) -> None:
        """Restoring a snapshot from before "Marker 2" keeps N at 3.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        workspace.add_marker(1.0)
        snapshot = workspace.snapshot()
        workspace.add_marker(2.0)
        workspace.restore(snapshot)
        self.assertEqual(marker_name_list(workspace), ["Marker 1"])
        self.assertEqual(workspace.add_marker(3.0).name_str, "Marker 3")

    @covers("LLFR-00085", "LLFR-00111", "LLFR-00205", "LLFR-00015")
    def test_reset_clears_markers_and_restarts_numbering(self) -> None:
        """A file open (reset) deletes every marker; N restarts at 1.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        old_id_set = {workspace.add_marker(1.0).marker_id_i,
                      workspace.add_marker(2.0).marker_id_i}
        workspace.reset()
        self.assertEqual(workspace.marker_list, [])
        self.assertEqual(workspace.next_marker_number_i, 1)
        new_plot = workspace.add_plot(workspace.tab_list[0].tab_id_i)
        new_plot.add_curve("Speed")
        new_marker = workspace.add_marker(1.0)
        self.assertEqual(new_marker.name_str, "Marker 1")
        # LLFR-00081: ids still never repeat.
        self.assertNotIn(new_marker.marker_id_i, old_id_set)


class MarkerIdTest(unittest.TestCase):
    """Check that marker ids are unique and never reused."""

    @covers("LLFR-00081", "LLFR-00091")
    def test_ids_are_unique_and_only_grow(self) -> None:
        """Every marker gets its own id; a deleted id is not reused.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        marker_list = [workspace.add_marker(1.0), workspace.add_marker(1.0)]
        workspace.remove_marker(marker_list[1].marker_id_i)
        marker_list.append(workspace.add_marker(1.0))
        id_list = [marker.marker_id_i for marker in marker_list]
        self.assertEqual(id_list, sorted(set(id_list)))

    @covers("LLFR-00081")
    def test_counter_counts_from_one(self) -> None:
        """A new MarkerIdCounter hands out 1, 2, 3.

        Inputs: none.
        Outputs: none.
        """
        counter = MarkerIdCounter()
        self.assertEqual([counter.take_next_id() for _ in range(3)],
                         [1, 2, 3])


class FindAndMoveMarkerTest(unittest.TestCase):
    """Check finding and moving markers (LLFR-00086)."""

    @covers("LLFR-00086", "LLFR-00205")
    def test_move_marker_changes_only_its_time(self) -> None:
        """move_marker sets the new time and keeps the name and id.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        marker = workspace.add_marker(1.0)
        other_marker = workspace.add_marker(2.0)
        self.assertTrue(workspace.move_marker(marker.marker_id_i, 3.75))
        self.assertEqual(marker.time_s, 3.75)
        self.assertEqual(marker.name_str, "Marker 1")
        self.assertEqual(other_marker.time_s, 2.0)
        self.assertIs(workspace.find_marker(marker.marker_id_i), marker)

    @covers("LLFR-00086")
    def test_move_unknown_marker_returns_false(self) -> None:
        """An unknown id moves nothing.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        marker = workspace.add_marker(1.0)
        self.assertFalse(workspace.move_marker(marker.marker_id_i + 100,
                                               9.0))
        self.assertEqual(marker.time_s, 1.0)

    @covers("LLFR-00086")
    def test_find_marker(self) -> None:
        """find_marker returns the marker, or None for an unknown id.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        marker = workspace.add_marker(1.0)
        self.assertIs(workspace.find_marker(marker.marker_id_i), marker)
        self.assertIsNone(workspace.find_marker(marker.marker_id_i + 1))


class RenameMarkerTest(unittest.TestCase):
    """Check renaming markers (LLFR-00088, LLFR-00089, LLFR-00112)."""

    @covers("LLFR-00088", "LLFR-00112")
    def test_rename_strips_spaces(self) -> None:
        """The typed name is kept without surrounding spaces.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        marker = workspace.add_marker(1.0)
        self.assertTrue(workspace.rename_marker(marker.marker_id_i,
                                                "  Start $x$ "))
        self.assertEqual(workspace.find_marker(marker.marker_id_i).name_str,
                         "Start $x$")

    @covers("LLFR-00089")
    def test_blank_name_keeps_previous_name(self) -> None:
        """Empty or space-only names are refused.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        marker = workspace.add_marker(1.0)
        for blank_name_str in ("", "   ", "\t\n"):
            with self.subTest(name=blank_name_str):
                self.assertFalse(workspace.rename_marker(marker.marker_id_i,
                                                         blank_name_str))
                self.assertEqual(marker.name_str, "Marker 1")

    @covers("LLFR-00088")
    def test_rename_unknown_marker_returns_false(self) -> None:
        """An unknown id renames nothing.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        marker = workspace.add_marker(1.0)
        self.assertFalse(workspace.rename_marker(marker.marker_id_i + 1,
                                                 "X"))
        self.assertEqual(marker.name_str, "Marker 1")


class RemoveMarkerTest(unittest.TestCase):
    """Check deleting markers (LLFR-00091, LLFR-00205)."""

    @covers("LLFR-00091")
    def test_remove_marker(self) -> None:
        """remove_marker removes only that marker.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        first_marker = workspace.add_marker(1.0)
        second_marker = workspace.add_marker(2.0)
        self.assertTrue(workspace.remove_marker(first_marker.marker_id_i))
        self.assertEqual(workspace.marker_list, [second_marker])
        self.assertIsNone(workspace.find_marker(first_marker.marker_id_i))

    @covers("LLFR-00091")
    def test_remove_unknown_or_twice_returns_false(self) -> None:
        """Unknown ids and second deletions do nothing.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        marker = workspace.add_marker(1.0)
        self.assertFalse(workspace.remove_marker(marker.marker_id_i + 50))
        self.assertTrue(workspace.remove_marker(marker.marker_id_i))
        self.assertFalse(workspace.remove_marker(marker.marker_id_i))
        self.assertEqual(workspace.marker_list, [])

    @covers("LLFR-00205", "LLFR-00049")
    def test_deleting_the_last_plot_deletes_the_markers(self) -> None:
        """Markers stay while a plot is left, and go with the last one.

        Inputs: none.
        Outputs: none.
        """
        workspace, first_plot = new_workspace_with_plot()
        other_plot = add_plot_in_new_tab(workspace)
        workspace.add_marker(1.0)
        workspace.add_marker(2.0)
        self.assertTrue(workspace.delete_plot(first_plot.plot_id_i))
        self.assertEqual(marker_name_list(workspace),
                         ["Marker 1", "Marker 2"])
        self.assertTrue(workspace.delete_plot(other_plot.plot_id_i))
        self.assertEqual(workspace.marker_list, [])
        # LLFR-00111: only a file open restarts the numbering.
        new_plot = workspace.add_plot(workspace.tab_list[0].tab_id_i)
        new_plot.add_curve("Speed")
        self.assertEqual(workspace.add_marker(1.0).name_str, "Marker 3")

    @covers("LLFR-00205", "LLFR-00051")
    def test_removing_the_last_curve_deletes_the_markers(self) -> None:
        """The last curve of the last plot takes the markers along.

        Inputs: none.
        Outputs: none.
        """
        workspace, plot = new_workspace_with_plot()
        workspace.add_marker(1.0)
        self.assertTrue(workspace.remove_curve(plot.plot_id_i, "Speed"))
        self.assertIsNone(workspace.find_plot(plot.plot_id_i))
        self.assertEqual(workspace.marker_list, [])

    @covers("LLFR-00205", "LLFR-00028")
    def test_deleting_the_tab_of_the_last_plots_deletes_markers(self) -> None:
        """A tab delete deletes the markers only when no plot is left.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        workspace.add_marker(1.0)
        empty_tab = workspace.add_tab()
        self.assertTrue(workspace.delete_tab(empty_tab.tab_id_i))
        self.assertEqual(marker_name_list(workspace), ["Marker 1"])
        first_tab_id_i = workspace.tab_list[0].tab_id_i
        workspace.add_tab()
        self.assertTrue(workspace.delete_tab(first_tab_id_i))
        self.assertEqual(workspace.marker_list, [])

    @covers("LLFR-00205", "LLFR-00138")
    def test_undo_of_the_last_plot_delete_restores_markers(self) -> None:
        """The snapshot holds the markers, so undo brings them back.

        Inputs: none.
        Outputs: none.
        """
        workspace, plot = new_workspace_with_plot()
        workspace.add_marker(1.0)
        workspace.add_marker(2.0)
        before_tuple = workspace.state_tuple()
        snapshot = workspace.snapshot()
        workspace.delete_plot(plot.plot_id_i)
        self.assertFalse(workspace.is_unchanged_since(snapshot))
        workspace.restore(snapshot)
        self.assertEqual(workspace.state_tuple(), before_tuple)
        self.assertEqual(marker_name_list(workspace),
                         ["Marker 1", "Marker 2"])
        # The snapshot is a copy: changing the markers keeps it intact.
        workspace.rename_marker(workspace.marker_list[0].marker_id_i, "X")
        self.assertEqual(snapshot.marker_list[0].name_str, "Marker 1")


class MarkerSnapshotTest(unittest.TestCase):
    """Check that the markers are part of the undo state (LLFR-00140)."""

    @covers("LLFR-00140", "LLFR-00205")
    def test_every_marker_change_changes_the_state(self) -> None:
        """Place, move, rename and delete are seen as changes.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        snapshot = workspace.snapshot()
        marker = workspace.add_marker(1.0)
        self.assertFalse(workspace.is_unchanged_since(snapshot))
        for change in (
                lambda: workspace.move_marker(marker.marker_id_i, 2.0),
                lambda: workspace.rename_marker(marker.marker_id_i, "A"),
                lambda: workspace.remove_marker(marker.marker_id_i)):
            snapshot = workspace.snapshot()
            change()
            self.assertFalse(workspace.is_unchanged_since(snapshot))

    @covers("LLFR-00140")
    def test_refused_changes_are_not_changes(self) -> None:
        """A blank rename or a move to the same time changes nothing.

        Inputs: none.
        Outputs: none.
        """
        workspace, _ = new_workspace_with_plot()
        marker = workspace.add_marker(1.0)
        snapshot = workspace.snapshot()
        workspace.rename_marker(marker.marker_id_i, "  ")
        workspace.move_marker(marker.marker_id_i, 1.0)
        self.assertTrue(workspace.is_unchanged_since(snapshot))


if __name__ == "__main__":
    unittest.main()
