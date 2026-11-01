"""Tests for the undo history and the workspace snapshots (HLFR-00040)."""

import random
import unittest

from tests.support import covers

from model.undo_history import MAXIMUM_UNDO_DEPTH_I, UndoHistory
from model.workspace import Workspace


class UndoHistoryTest(unittest.TestCase):
    """The bounded stack of saved states."""

    @covers("LLFR-00139", "LLFR-00141")
    def test_starts_empty(self) -> None:
        """A new history has nothing to undo and refuses to pop.

        Inputs: none.
        Outputs: none.
        """
        history = UndoHistory()
        self.assertEqual(MAXIMUM_UNDO_DEPTH_I, 5)
        self.assertEqual(history.maximum_depth_i, 5)
        self.assertFalse(history.can_undo())
        self.assertEqual(history.depth(), 0)
        with self.assertRaises(IndexError):
            history.pop()

    @covers("LLFR-00138", "LLFR-00139")
    def test_pop_returns_most_recent_first(self) -> None:
        """States come back in reverse order of recording.

        Inputs: none.
        Outputs: none.
        """
        history = UndoHistory()
        for state_str in ("a", "b", "c"):
            history.record(state_str)
        self.assertTrue(history.can_undo())
        self.assertEqual([history.pop() for _ in range(3)], ["c", "b", "a"])
        self.assertFalse(history.can_undo())

    @covers("LLFR-00139")
    def test_keeps_only_the_five_most_recent(self) -> None:
        """After 7 records only the last 5 can be undone, oldest dropped.

        Inputs: none.
        Outputs: none.
        """
        history = UndoHistory()
        for index_i in range(7):
            history.record(index_i)
            self.assertLessEqual(history.depth(), 5)
        self.assertEqual(history.depth(), 5)
        popped_list = []
        while history.can_undo():
            popped_list.append(history.pop())
        self.assertEqual(popped_list, [6, 5, 4, 3, 2])

    @covers("LLFR-00139")
    def test_recording_after_undo_continues(self) -> None:
        """A record after some undos adds on top of what is left.

        Inputs: none.
        Outputs: none.
        """
        history = UndoHistory(maximum_depth_i=3)
        for state_str in ("a", "b", "c"):
            history.record(state_str)
        history.pop()
        history.record("d")
        history.record("e")
        self.assertEqual(history.depth(), 3)
        self.assertEqual([history.pop() for _ in range(3)], ["e", "d", "b"])

    @covers("LLFR-00142", "LLFR-00141")
    def test_clear_forgets_everything(self) -> None:
        """clear() leaves nothing to undo.

        Inputs: none.
        Outputs: none.
        """
        history = UndoHistory()
        history.record("a")
        history.record("b")
        history.clear()
        self.assertFalse(history.can_undo())
        self.assertEqual(history.depth(), 0)

    @covers("LLFR-00139")
    def test_depth_must_be_positive(self) -> None:
        """A depth below 1 is refused.

        Inputs: none.
        Outputs: none.
        """
        with self.assertRaises(ValueError):
            UndoHistory(0)


class WorkspaceSnapshotTest(unittest.TestCase):
    """Snapshot and restore of the workspace."""

    def setUp(self) -> None:
        """Build a workspace with two tabs, plots, curves, tips, markers.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace(random.Random(3))
        first_tab = self.workspace.tab_list[0]
        self.workspace.rename_tab(first_tab.tab_id_i, "Engine")
        self.plot = self.workspace.add_plot(first_tab.tab_id_i)
        self.plot.add_curve("speed")
        self.plot.add_curve("force")
        self.plot.set_curve_width("force", 4)
        pinned_tip = self.plot.add_pinned_tip("speed", 1.0, 2.0)
        self.plot.move_pinned_tip(pinned_tip, (10.0, -5.0))
        self.plot.add_marker(0.5)
        self.plot.add_marker(1.5)
        self.plot.rename_marker(self.plot.marker_list[0].marker_id_i, "Go")
        second_tab = self.workspace.add_tab()
        self.workspace.add_plot(second_tab.tab_id_i).add_curve("speed")

    @covers("LLFR-00138", "LLFR-00140")
    def test_snapshot_is_independent_of_later_changes(self) -> None:
        """Changes after a snapshot do not change it; restore undoes them.

        Inputs: none.
        Outputs: none.
        """
        before_tuple = self.workspace.state_tuple()
        snapshot = self.workspace.snapshot(7)
        self.assertEqual(snapshot.current_tab_id_i, 7)
        self.assertTrue(self.workspace.is_unchanged_since(snapshot))
        # Change every kind of thing.
        self.plot.set_curve_width("speed", 5)
        self.plot.move_pinned_tip(self.plot.pinned_tip_list[0], (1.0, 1.0))
        self.plot.move_marker(self.plot.marker_list[1].marker_id_i, 3.0)
        self.plot.rename_marker(self.plot.marker_list[0].marker_id_i, "X")
        self.plot.add_curve("torque")
        self.workspace.rename_tab(self.workspace.tab_list[0].tab_id_i, "Y")
        self.workspace.delete_tab(self.workspace.tab_list[1].tab_id_i)
        self.assertFalse(self.workspace.is_unchanged_since(snapshot))
        self.assertEqual(snapshot.state_tuple, before_tuple)
        self.workspace.restore(snapshot)
        self.assertEqual(self.workspace.state_tuple(), before_tuple)
        self.assertTrue(self.workspace.is_unchanged_since(snapshot))
        # The snapshot can be restored again; restore copies it.
        self.workspace.tab_list[0].plot_list[0].set_curve_width("speed", 2)
        self.workspace.restore(snapshot)
        self.assertEqual(self.workspace.state_tuple(), before_tuple)

    @covers("LLFR-00140")
    def test_state_holds_every_undoable_detail(self) -> None:
        """The dump holds names, colors, widths, offsets and markers.

        Inputs: none.
        Outputs: none.
        """
        tab_state = self.workspace.state_tuple()[0]
        self.assertEqual(tab_state[1], "Engine")
        plot_state = tab_state[2][0]
        self.assertEqual(plot_state[0], self.plot.plot_id_i)
        self.assertEqual(plot_state[1], 2)
        self.assertEqual(plot_state[2], 3)
        self.assertEqual([curve[2] for curve in plot_state[3]], [1, 4])
        self.assertEqual(plot_state[4][0][3], (10.0, -5.0))
        self.assertEqual([marker[1] for marker in plot_state[5]],
                         ["Go", "Marker 2"])

    @covers("LLFR-00138", "LLFR-00111")
    def test_ids_are_never_reused_after_restore(self) -> None:
        """New tabs, plots and markers after an undo get fresh ids.

        Inputs: none.
        Outputs: none.
        """
        snapshot = self.workspace.snapshot()
        added_tab = self.workspace.add_tab()
        added_plot = self.workspace.add_plot(added_tab.tab_id_i)
        added_marker = self.plot.add_marker(2.0)
        self.workspace.restore(snapshot)
        new_tab = self.workspace.add_tab()
        new_plot = self.workspace.add_plot(new_tab.tab_id_i)
        restored_plot = self.workspace.find_plot(self.plot.plot_id_i)
        new_marker = restored_plot.add_marker(2.0)
        self.assertGreater(new_tab.tab_id_i, added_tab.tab_id_i)
        self.assertGreater(new_plot.plot_id_i, added_plot.plot_id_i)
        self.assertGreater(new_marker.marker_id_i, added_marker.marker_id_i)
        # LLFR-00085: the restored plot names the marker as before the
        # undone action.
        self.assertEqual(new_marker.name_str, "Marker 3")

    @covers("LLFR-00138")
    def test_restored_plots_share_the_generator_and_counter(self) -> None:
        """Restored plots use the workspace's generator and id counter.

        Inputs: none.
        Outputs: none.
        """
        snapshot = self.workspace.snapshot()
        self.workspace.restore(snapshot)
        for tab in self.workspace.tab_list:
            for plot in tab.plot_list:
                self.assertIs(plot.random_generator,
                              self.workspace.random_generator)
                self.assertIs(plot.marker_id_counter,
                              self.workspace.marker_id_counter)
        self.assertIsNot(self.workspace.tab_list[0], snapshot.tab_list[0])


if __name__ == "__main__":
    unittest.main()
