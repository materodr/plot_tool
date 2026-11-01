"""Tests for the delta markers of the workspace model (HLFR-00043/44).

No Qt is needed: the model is plain Python.
"""

import math
import random
import unittest

from tests.support import covers

from model.workspace import (
    DELTA_X_KIND_STR, DELTA_Y_KIND_STR, DeltaMarker, Workspace)


class DeltaMarkerModelTestCase(unittest.TestCase):
    """Shared setup: one plot with the curves "a" and "b"."""

    def setUp(self) -> None:
        """Create a workspace with one plot holding two curves.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace(random.Random(3))
        tab_id_i = self.workspace.tab_list[0].tab_id_i
        self.plot = self.workspace.add_plot(tab_id_i)
        self.plot.add_curve("a")
        self.plot.add_curve("b")


class DeltaMarkerTest(DeltaMarkerModelTestCase):
    """Placing, measuring and removing delta markers."""

    @covers("LLFR-00164", "LLFR-00168", "LLFR-00170")
    def test_add_keeps_kind_and_exact_points(self) -> None:
        """A new marker keeps its kind and both points as given.

        Inputs: none.
        Outputs: none.
        """
        delta_marker = self.plot.add_delta_marker(
            DELTA_X_KIND_STR, ("a", 1.0, 2.0), ("b", 4.0, -1.5))
        self.assertIsInstance(delta_marker, DeltaMarker)
        self.assertEqual(delta_marker.kind_str, DELTA_X_KIND_STR)
        self.assertEqual(delta_marker.first_point_tuple, ("a", 1.0, 2.0))
        self.assertEqual(delta_marker.second_point_tuple, ("b", 4.0, -1.5))
        self.assertEqual(self.plot.delta_marker_list, [delta_marker])

    @covers("LLFR-00169", "LLFR-00171")
    def test_delta_is_second_minus_first_and_signed(self) -> None:
        """Delta X measures time, Delta Y value; both keep the sign.

        Inputs: none.
        Outputs: none.
        """
        delta_x = self.plot.add_delta_marker(
            DELTA_X_KIND_STR, ("a", 5.0, 2.0), ("b", 1.5, 9.0))
        delta_y = self.plot.add_delta_marker(
            DELTA_Y_KIND_STR, ("a", 5.0, 2.0), ("b", 1.5, 9.0))
        self.assertEqual(delta_x.delta_f(), -3.5)
        self.assertEqual(delta_y.delta_f(), 7.0)
        reverse_y = self.plot.add_delta_marker(
            DELTA_Y_KIND_STR, ("b", 1.5, 9.0), ("a", 5.0, 2.0))
        self.assertEqual(reverse_y.delta_f(), -7.0)

    @covers("LLFR-00164")
    def test_both_points_may_be_on_the_same_curve(self) -> None:
        """Two points of one curve make a valid marker.

        Inputs: none.
        Outputs: none.
        """
        delta_marker = self.plot.add_delta_marker(
            DELTA_Y_KIND_STR, ("a", 1.0, 1.0), ("a", 2.0, 4.0))
        self.assertEqual(delta_marker.delta_f(), 3.0)

    @covers("LLFR-00164")
    def test_invalid_markers_are_refused(self) -> None:
        """Unknown kinds, signals or non-finite points raise ValueError.

        Inputs: none.
        Outputs: none.
        """
        bad_call_list = [
            ("z", ("a", 1.0, 1.0), ("b", 2.0, 2.0)),
            (DELTA_X_KIND_STR, ("missing", 1.0, 1.0), ("b", 2.0, 2.0)),
            (DELTA_X_KIND_STR, ("a", 1.0, 1.0), ("missing", 2.0, 2.0)),
            (DELTA_X_KIND_STR, ("a", math.nan, 1.0), ("b", 2.0, 2.0)),
            (DELTA_Y_KIND_STR, ("a", 1.0, math.inf), ("b", 2.0, 2.0)),
            (DELTA_Y_KIND_STR, ("a", 1.0), ("b", 2.0, 2.0)),
        ]
        for kind_str, first_tuple, second_tuple in bad_call_list:
            with self.subTest(kind=kind_str, first=first_tuple,
                              second=second_tuple):
                with self.assertRaises(ValueError):
                    self.plot.add_delta_marker(kind_str, first_tuple,
                                               second_tuple)
        self.assertEqual(self.plot.delta_marker_list, [])

    @covers("LLFR-00174")
    def test_any_number_of_markers_of_both_kinds(self) -> None:
        """Fifty Delta X and fifty Delta Y markers live side by side.

        Inputs: none.
        Outputs: none.
        """
        for index_i in range(50):
            self.plot.add_delta_marker(
                DELTA_X_KIND_STR, ("a", 0.0, 0.0), ("b", index_i, 1.0))
            self.plot.add_delta_marker(
                DELTA_Y_KIND_STR, ("b", 0.0, 0.0), ("a", 1.0, index_i))
        self.assertEqual(len(self.plot.delta_marker_list), 100)
        id_list = [delta_marker.delta_marker_id_i
                   for delta_marker in self.plot.delta_marker_list]
        self.assertEqual(len(set(id_list)), 100)

    @covers("LLFR-00176")
    def test_remove_by_id(self) -> None:
        """Removing one marker leaves the others; unknown ids are False.

        Inputs: none.
        Outputs: none.
        """
        first = self.plot.add_delta_marker(
            DELTA_X_KIND_STR, ("a", 0.0, 0.0), ("b", 1.0, 1.0))
        second = self.plot.add_delta_marker(
            DELTA_Y_KIND_STR, ("a", 0.0, 0.0), ("b", 1.0, 1.0))
        self.assertTrue(self.plot.remove_delta_marker(
            first.delta_marker_id_i))
        self.assertEqual(self.plot.delta_marker_list, [second])
        self.assertFalse(self.plot.remove_delta_marker(
            first.delta_marker_id_i))
        self.assertFalse(self.plot.remove_delta_marker(9999))

    @covers("LLFR-00176")
    def test_ids_are_unique_across_plots_and_never_reused(self) -> None:
        """Ids are shared with vertical markers and only grow.

        Inputs: none.
        Outputs: none.
        """
        other_plot = self.workspace.add_plot(
            self.workspace.tab_list[0].tab_id_i)
        other_plot.add_curve("a")
        first = self.plot.add_delta_marker(
            DELTA_X_KIND_STR, ("a", 0.0, 0.0), ("b", 1.0, 1.0))
        vertical_marker = self.plot.add_marker(2.0)
        self.plot.remove_delta_marker(first.delta_marker_id_i)
        second = other_plot.add_delta_marker(
            DELTA_X_KIND_STR, ("a", 0.0, 0.0), ("a", 1.0, 1.0))
        id_list = [first.delta_marker_id_i, vertical_marker.marker_id_i,
                   second.delta_marker_id_i]
        self.assertEqual(id_list, sorted(set(id_list)))

    @covers("LLFR-00178", "LLFR-00039")
    def test_removing_a_curve_removes_its_delta_markers(self) -> None:
        """Markers with a point on the removed curve go, others stay.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_curve("c")
        on_a = self.plot.add_delta_marker(
            DELTA_X_KIND_STR, ("a", 0.0, 0.0), ("b", 1.0, 1.0))
        second_on_a = self.plot.add_delta_marker(
            DELTA_Y_KIND_STR, ("c", 0.0, 0.0), ("a", 1.0, 1.0))
        not_on_a = self.plot.add_delta_marker(
            DELTA_Y_KIND_STR, ("b", 0.0, 0.0), ("c", 1.0, 1.0))
        self.assertTrue(self.plot.remove_curve("a"))
        self.assertEqual(self.plot.delta_marker_list, [not_on_a])
        self.assertNotIn(on_a, self.plot.delta_marker_list)
        self.assertNotIn(second_on_a, self.plot.delta_marker_list)
        self.assertEqual(self.plot.remove_delta_markers_of_signal("b"), 1)
        self.assertEqual(self.plot.remove_delta_markers_of_signal("b"), 0)

    @covers("LLFR-00140", "LLFR-00178", "LLFR-00138")
    def test_snapshot_restores_delta_markers(self) -> None:
        """A snapshot sees delta markers and brings removed ones back.

        Inputs: none.
        Outputs: none.
        """
        before_snapshot = self.workspace.snapshot()
        self.plot.add_delta_marker(
            DELTA_X_KIND_STR, ("a", 0.0, 0.0), ("b", 1.0, 1.0))
        # LLFR-00140: placing a delta marker is a change.
        self.assertFalse(self.workspace.is_unchanged_since(before_snapshot))
        with_marker_snapshot = self.workspace.snapshot()
        self.workspace.remove_curve(self.plot.plot_id_i, "a")
        self.assertEqual(
            self.workspace.find_plot(self.plot.plot_id_i).delta_marker_list,
            [])
        # LLFR-00140 Note: undoing the curve removal brings it back.
        self.workspace.restore(with_marker_snapshot)
        restored_plot = self.workspace.find_plot(self.plot.plot_id_i)
        self.assertTrue(restored_plot.has_signal("a"))
        self.assertEqual(len(restored_plot.delta_marker_list), 1)
        self.assertEqual(restored_plot.delta_marker_list[0]
                         .first_point_tuple, ("a", 0.0, 0.0))
        # The snapshot is a copy: changing the restored marker list does
        # not change the snapshot.
        restored_plot.delta_marker_list.clear()
        self.workspace.restore(with_marker_snapshot)
        self.assertEqual(len(self.workspace.find_plot(
            self.plot.plot_id_i).delta_marker_list), 1)


if __name__ == "__main__":
    unittest.main()
