"""Tests for the plot kinds of the workspace model (HLFR-00058)."""

import random
import unittest

from tests.support import covers

from model.workspace import (
    FREQUENCY_PLOT_KIND_STR, MAXIMUM_PLOTS_PER_TAB_I, PLOT_KIND_TUPLE,
    TIME_PLOT_KIND_STR, WHOLE_FREQUENCY_RANGE_TUPLE, Plot, Workspace)


class PlotKindTest(unittest.TestCase):
    """A plot is a time plot or a frequency plot."""

    def setUp(self) -> None:
        """Create a workspace with one tab.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace(random.Random(1))
        self.tab_id_i = self.workspace.tab_list[0].tab_id_i

    @covers("LLFR-00256", "LLFR-00068")
    def test_plots_are_time_plots_by_default(self) -> None:
        """A plot made without a kind is a time plot.

        Inputs: none.
        Outputs: none.
        """
        plot = self.workspace.add_plot(self.tab_id_i)
        self.assertEqual(plot.kind_str, TIME_PLOT_KIND_STR)
        self.assertFalse(plot.is_frequency_plot())
        self.assertEqual(plot.frequency_range_tuple, ())
        self.assertEqual(PLOT_KIND_TUPLE, ("time", "frequency"))

    @covers("LLFR-00256")
    def test_frequency_plot_and_unknown_kind(self) -> None:
        """A frequency plot can be made; an unknown kind is refused.

        Inputs: none.
        Outputs: none.
        """
        plot = self.workspace.add_plot(self.tab_id_i,
                                       FREQUENCY_PLOT_KIND_STR)
        self.assertTrue(plot.is_frequency_plot())
        self.assertEqual(plot.frequency_range_tuple,
                         WHOLE_FREQUENCY_RANGE_TUPLE)
        with self.assertRaises(ValueError):
            self.workspace.add_plot(self.tab_id_i, "spectrum")
        with self.assertRaises(ValueError):
            Plot(99, random.Random(), None, "spectrum")
        self.assertEqual(len(self.workspace.tab_list[0].plot_list), 1)

    @covers("LLFR-00256", "LLFR-00031", "HLFR-00018")
    def test_frequency_plots_count_towards_the_maximum(self) -> None:
        """Both kinds together fill a tab at the maximum.

        Inputs: none.
        Outputs: none.
        """
        for index_i in range(MAXIMUM_PLOTS_PER_TAB_I):
            kind_str = PLOT_KIND_TUPLE[index_i % 2]
            self.assertIsNotNone(self.workspace.add_plot(self.tab_id_i,
                                                         kind_str))
        self.assertIsNone(self.workspace.add_plot(
            self.tab_id_i, FREQUENCY_PLOT_KIND_STR))
        self.assertIsNone(self.workspace.add_plot(self.tab_id_i))

    @covers("LLFR-00258")
    def test_set_frequency_range(self) -> None:
        """Only a frequency plot keeps a finite, increasing range.

        Inputs: none.
        Outputs: none.
        """
        time_plot = self.workspace.add_plot(self.tab_id_i)
        frequency_plot = self.workspace.add_plot(self.tab_id_i,
                                                 FREQUENCY_PLOT_KIND_STR)
        self.assertFalse(time_plot.set_frequency_range(1.0, 2.0))
        self.assertEqual(time_plot.frequency_range_tuple, ())
        self.assertTrue(frequency_plot.set_frequency_range(1, 2))
        self.assertEqual(frequency_plot.frequency_range_tuple, (1.0, 2.0))
        for start_f, end_f in ((2.0, 2.0), (3.0, 1.0),
                               (float("nan"), 1.0), (0.0, float("inf"))):
            self.assertFalse(frequency_plot.set_frequency_range(start_f,
                                                                end_f))
        self.assertEqual(frequency_plot.frequency_range_tuple, (1.0, 2.0))

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00256")
    def test_undo_state_holds_the_kind_but_not_the_range(self) -> None:
        """The kind is restored by an undo; a zoom is no change.

        Inputs: none.
        Outputs: none.
        """
        frequency_plot = self.workspace.add_plot(self.tab_id_i,
                                                 FREQUENCY_PLOT_KIND_STR)
        frequency_plot.add_curve("fft_Speed_0s_to_1s")
        snapshot = self.workspace.snapshot(self.tab_id_i)
        plot_state_tuple = snapshot.state_tuple[0][0][2][0]
        self.assertEqual(plot_state_tuple[-1], FREQUENCY_PLOT_KIND_STR)
        frequency_plot.set_frequency_range(1.0, 2.0)
        self.assertTrue(self.workspace.is_unchanged_since(snapshot))
        self.workspace.delete_plot(frequency_plot.plot_id_i)
        self.workspace.restore(snapshot)
        restored_plot = self.workspace.find_plot(frequency_plot.plot_id_i)
        self.assertTrue(restored_plot.is_frequency_plot())
        self.assertEqual(restored_plot.curve_list[0].signal_name_str,
                         "fft_Speed_0s_to_1s")

    @covers("LLFR-00205", "LLFR-00259")
    def test_frequency_plots_keep_the_markers(self) -> None:
        """Markers are deleted only when no plot of any kind is left.

        Inputs: none.
        Outputs: none.
        """
        time_plot = self.workspace.add_plot(self.tab_id_i)
        frequency_plot = self.workspace.add_plot(self.tab_id_i,
                                                 FREQUENCY_PLOT_KIND_STR)
        self.workspace.add_marker(1.0)
        self.workspace.delete_plot(time_plot.plot_id_i)
        self.assertTrue(self.workspace.has_plots())
        self.assertEqual(len(self.workspace.marker_list), 1)
        self.workspace.delete_plot(frequency_plot.plot_id_i)
        self.assertEqual(self.workspace.marker_list, [])


if __name__ == "__main__":
    unittest.main()
