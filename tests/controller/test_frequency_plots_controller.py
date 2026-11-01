"""Tests for the frequency plots of FFT signals, with a fake view (no Qt).

The real controllers run on the fake main window of the synthetic
signal tests, so an FFT signal is created through the signal list menu
and plotted with the same double-click and drop flows as the app
(HLFR-00058).
"""

import unittest

import numpy as np

from tests.support import covers

from tests.controller.test_synthetic_controller import (
    SyntheticControllerTestCase)

from controller.plot_tools import DELTA_X_TOOL_STR, MARKER_TOOL_STR
from model.curve_colors import PALETTE_COLOR_TUPLE
from model.workspace import (
    FREQUENCY_PLOT_KIND_STR, MAXIMUM_PLOTS_PER_TAB_I, TIME_PLOT_KIND_STR)

# The FFT of the whole test file: 100 samples every 0.1 s, so its
# frequencies go from 0 Hz to 5 Hz.
WHOLE_FFT_NAME_STR = "fft_Speed_0s_to_9.9s"
WHOLE_FFT_HIGHEST_HZ = 5.0


class FrequencyPlotTestCase(SyntheticControllerTestCase):
    """Shared helpers: create FFT signals and find plots."""

    def create_fft(self, signal_name_str: str = "Speed") -> str:
        """Create an FFT signal of a signal over the plots' time range.

        Inputs:
            signal_name_str: the signal to transform.
        Outputs: the name of the new FFT signal.
        """
        self.create(signal_name_str, "fft")
        return self.store_names()[-1]

    def plot(self, plot_id_i: int):
        """Return a model plot by its id.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: the Plot.
        """
        return self.plot_controller.workspace.find_plot(plot_id_i)

    def last_plot_id(self) -> int:
        """Return the id of the most recently created plot.

        Inputs: none.
        Outputs: the plot id.
        """
        return self.plot_id_list()[-1]

    def set_range(self, plot_id_i: int, start_f: float,
                  end_f: float) -> None:
        """Report a zoom or a pan of a plot, as the view does.

        Inputs:
            plot_id_i: id of the plot.
            start_f: start of the new range (s or Hz).
            end_f: end of the new range (s or Hz).
        Outputs: none.
        """
        self.view.handler_dict["time_range_handler"](plot_id_i, start_f,
                                                     end_f)

    def drop(self, plot_id_i: int, signal_name_str: str) -> None:
        """Drop a signal name on a plot.

        Inputs:
            plot_id_i: id of the plot.
            signal_name_str: the dropped signal.
        Outputs: none.
        """
        self.view.handler_dict["signal_drop_handler"](plot_id_i,
                                                      signal_name_str)

    def range_calls(self, plot_id_i: int) -> list:
        """Return the ranges the controller set on a plot, in order.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: a list of (start, end) tuples.
        """
        return [(call_tuple[2], call_tuple[3])
                for call_tuple in self.view.call_list
                if call_tuple[0] == "set_plot_time_range"
                and call_tuple[1] == plot_id_i]


class FrequencyPlotCreationTest(FrequencyPlotTestCase):
    """Double-click on an FFT signal (LLFR-00256)."""

    @covers("LLFR-00256", "LLFR-00019", "LLFR-00020", "HLFR-00058",
            "HLFR-00012")
    def test_double_click_creates_a_frequency_plot(self) -> None:
        """An FFT signal gets a frequency plot drawn against frequency.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        self.assertEqual(fft_name_str, WHOLE_FFT_NAME_STR)
        self.double_click(fft_name_str)
        plot_id_i = self.last_plot_id()
        self.assertEqual(self.plot(plot_id_i).kind_str,
                         FREQUENCY_PLOT_KIND_STR)
        self.assertTrue(self.plot(plot_id_i).is_frequency_plot())
        self.assertEqual(self.view.plot_kind_dict[plot_id_i],
                         FREQUENCY_PLOT_KIND_STR)
        self.assertEqual(self.view.drawn_names(plot_id_i), [fft_name_str])
        curve_tuple = self.view.drawn_dict[plot_id_i][0][0]
        fft_signal = self.controller.store.get(fft_name_str)
        np.testing.assert_allclose(curve_tuple[1],
                                   fft_signal.frequency_array)
        np.testing.assert_allclose(curve_tuple[2], fft_signal.value_array)
        self.assertEqual(float(curve_tuple[1][0]), 0.0)
        self.assertAlmostEqual(float(curve_tuple[1][-1]),
                               WHOLE_FFT_HIGHEST_HZ)
        # LLFR-00033: the first curve has the first palette color.
        self.assertEqual(curve_tuple[3], PALETTE_COLOR_TUPLE[0])
        self.assertEqual(self.view.kind_mismatch_count_i, 0)

    @covers("LLFR-00068", "LLFR-00256")
    def test_other_signals_still_get_time_plots(self) -> None:
        """Data and other synthetic signals get time plots, against time.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.double_click("Speed")
        self.double_click("integral_Speed")
        for plot_id_i in self.plot_id_list():
            self.assertEqual(self.plot(plot_id_i).kind_str,
                             TIME_PLOT_KIND_STR)
            self.assertEqual(self.view.plot_kind_dict[plot_id_i],
                             TIME_PLOT_KIND_STR)
            np.testing.assert_allclose(
                self.view.drawn_dict[plot_id_i][0][0][1],
                self.plot_controller.signal_file.time_array)

    @covers("LLFR-00256", "LLFR-00031", "LLFR-00032", "HLFR-00018")
    def test_frequency_plots_count_towards_the_limit(self) -> None:
        """Time and frequency plots together fill a tab at 5 plots.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        self.double_click("Speed")
        for _ in range(MAXIMUM_PLOTS_PER_TAB_I - 1):
            self.double_click(fft_name_str)
        self.assertEqual(len(self.plot_id_list()), MAXIMUM_PLOTS_PER_TAB_I)
        self.assertEqual(self.view.full_tab_count_i, 0)
        # A sixth plot, of either kind, is refused with the Full Tab box.
        self.double_click(fft_name_str)
        self.assertEqual(self.view.full_tab_count_i, 1)
        self.double_click("Torque")
        self.assertEqual(self.view.full_tab_count_i, 2)
        self.assertEqual(len(self.plot_id_list()), MAXIMUM_PLOTS_PER_TAB_I)
        # LLFR-00140: a refused plot records no undo step.
        undo_count_i = len(self.plot_controller.undo_history
                           .saved_snapshot_list())
        self.double_click(fft_name_str)
        self.assertEqual(len(self.plot_controller.undo_history
                             .saved_snapshot_list()), undo_count_i)


class FrequencyPlotDropTest(FrequencyPlotTestCase):
    """Drops that mix FFT and time signals (LLFR-00257)."""

    @covers("LLFR-00257", "HLFR-00013")
    def test_fft_signal_on_a_time_plot_is_refused(self) -> None:
        """An FFT signal dropped on a time plot shows the box only.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        self.double_click("Speed")
        plot_id_i = self.last_plot_id()
        snapshot_count_i = len(
            self.plot_controller.undo_history.saved_snapshot_list())
        self.drop(plot_id_i, fft_name_str)
        self.assertEqual(self.view.kind_mismatch_count_i, 1)
        self.assertEqual(self.view.drawn_names(plot_id_i), ["Speed"])
        self.assertFalse(self.plot(plot_id_i).has_signal(fft_name_str))
        self.assertEqual(len(
            self.plot_controller.undo_history.saved_snapshot_list()),
            snapshot_count_i)

    @covers("LLFR-00257", "HLFR-00013", "LLFR-00055")
    def test_time_signals_on_a_frequency_plot_are_refused(self) -> None:
        """Data, Time and other synthetic signals are refused there.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        self.create("Speed", "integral")
        self.double_click(fft_name_str)
        plot_id_i = self.last_plot_id()
        for name_str in ("Torque", "Time", "integral_Speed"):
            self.drop(plot_id_i, name_str)
        self.assertEqual(self.view.kind_mismatch_count_i, 3)
        self.assertEqual(self.view.drawn_names(plot_id_i), [fft_name_str])
        self.assertEqual(self.plot(plot_id_i).curve_list[0].signal_name_str,
                         fft_name_str)
        self.assertEqual(len(self.plot(plot_id_i).curve_list), 1)

    @covers("LLFR-00257", "LLFR-00021", "LLFR-00056", "LLFR-00057",
            "LLFR-00033")
    def test_another_fft_signal_is_added_to_a_frequency_plot(self) -> None:
        """A second FFT signal joins the frequency plot, in a new color.

        Inputs: none.
        Outputs: none.
        """
        speed_fft_str = self.create_fft("Speed")
        torque_fft_str = self.create_fft("Torque")
        self.double_click(speed_fft_str)
        plot_id_i = self.last_plot_id()
        self.drop(plot_id_i, torque_fft_str)
        self.assertEqual(self.view.drawn_names(plot_id_i),
                         [speed_fft_str, torque_fft_str])
        curve_list = self.view.drawn_dict[plot_id_i][0]
        self.assertEqual([curve_tuple[3] for curve_tuple in curve_list],
                         list(PALETTE_COLOR_TUPLE[:2]))
        np.testing.assert_allclose(
            curve_list[1][1],
            self.controller.store.get(torque_fft_str).frequency_array)
        # LLFR-00056, LLFR-00057: a duplicate drop does nothing, silently.
        self.drop(plot_id_i, torque_fft_str)
        self.assertEqual(len(self.plot(plot_id_i).curve_list), 2)
        self.assertEqual(self.view.kind_mismatch_count_i, 0)


class FrequencyPlotRangeTest(FrequencyPlotTestCase):
    """Each frequency plot has its own x-axis range (LLFR-00258)."""

    @covers("LLFR-00258", "LLFR-00180", "LLFR-00070")
    def test_new_frequency_plot_ignores_the_shared_time_range(self) -> None:
        """A zoomed time range is not applied to a new frequency plot.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        self.double_click("Speed")
        time_plot_id_i = self.last_plot_id()
        self.set_range(time_plot_id_i, 2.0, 4.0)
        self.double_click(fft_name_str)
        frequency_plot_id_i = self.last_plot_id()
        # The view shows the whole frequency range that draw_plot gave
        # it: the controller sets no other range on it.
        self.assertEqual(self.range_calls(frequency_plot_id_i), [])
        self.assertEqual(self.plot(frequency_plot_id_i).frequency_range_tuple,
                         ())
        self.assertEqual(self.view.plot_time_range(frequency_plot_id_i),
                         (0.0, WHOLE_FFT_HIGHEST_HZ))
        # LLFR-00180: a new time plot still takes the shared range.
        self.double_click("Torque")
        self.assertEqual(self.view.plot_time_range(self.last_plot_id()),
                         (2.0, 4.0))

    @covers("LLFR-00258", "LLFR-00070", "LLFR-00074", "LLFR-00117")
    def test_zoom_changes_only_its_own_plot(self) -> None:
        """Time and frequency ranges never follow each other.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        self.double_click("Speed")
        time_plot_id_i = self.last_plot_id()
        self.double_click(fft_name_str)
        first_frequency_id_i = self.last_plot_id()
        self.double_click(fft_name_str)
        second_frequency_id_i = self.last_plot_id()
        self.double_click("Torque")
        other_time_plot_id_i = self.last_plot_id()
        self.view.call_list = []
        # A zoom of a time plot: every time plot, no frequency plot.
        self.set_range(time_plot_id_i, 1.0, 2.0)
        self.assertEqual(self.range_calls(other_time_plot_id_i),
                         [(1.0, 2.0)])
        self.assertEqual(self.range_calls(first_frequency_id_i), [])
        self.assertEqual(self.range_calls(second_frequency_id_i), [])
        # A zoom or pan of a frequency plot: only that plot.
        self.set_range(first_frequency_id_i, 1.0, 3.0)
        self.assertEqual(self.plot(first_frequency_id_i)
                         .frequency_range_tuple, (1.0, 3.0))
        self.assertEqual(self.plot(second_frequency_id_i)
                         .frequency_range_tuple, ())
        for plot_id_i in (time_plot_id_i, other_time_plot_id_i,
                          second_frequency_id_i):
            self.assertNotIn((1.0, 3.0), self.range_calls(plot_id_i))
        self.assertEqual(self.plot_controller.shared_time_range_tuple,
                         (1.0, 2.0))
        # A redraw of the frequency plot keeps its own range.
        self.drop(first_frequency_id_i, self.create_fft("Torque"))
        self.assertEqual(self.view.plot_time_range(first_frequency_id_i),
                         (1.0, 3.0))

    @covers("LLFR-00258", "LLFR-00115", "LLFR-00207", "HLFR-00035")
    def test_reset_zoom_returns_every_plot_to_its_whole_range(self) -> None:
        """Time plots show the file again; frequency plots 0 Hz to max.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        self.double_click("Speed")
        time_plot_id_i = self.last_plot_id()
        self.double_click(fft_name_str)
        frequency_plot_id_i = self.last_plot_id()
        self.set_range(time_plot_id_i, 1.0, 2.0)
        self.set_range(frequency_plot_id_i, 2.0, 3.0)
        self.view.handler_dict["reset_zoom"]()
        self.assertEqual(self.view.plot_time_range(time_plot_id_i),
                         (0.0, 9.9))
        start_hz, end_hz = self.view.plot_time_range(frequency_plot_id_i)
        self.assertEqual(start_hz, 0.0)
        self.assertAlmostEqual(end_hz, WHOLE_FFT_HIGHEST_HZ)
        self.assertEqual(self.plot(frequency_plot_id_i)
                         .frequency_range_tuple, ())
        self.assertEqual(self.plot_controller.shared_time_range_tuple, ())

    @covers("LLFR-00258")
    def test_range_limit_follows_the_highest_frequency(self) -> None:
        """Adding a curve widens the limit; removing it cuts the range.

        Inputs: none.
        Outputs: none.
        """
        # An FFT of 9 samples (0 s to 0.8 s) ends below 5 Hz.
        self.double_click("Speed")
        time_plot_id_i = self.last_plot_id()
        self.set_range(time_plot_id_i, 0.0, 0.8)
        short_fft_str = self.create_fft("Speed")
        self.view.handler_dict["plot_delete_handler"](time_plot_id_i)
        whole_fft_str = self.create_fft("Torque")
        short_highest_hz = float(np.max(
            self.controller.store.get(short_fft_str).frequency_array))
        self.assertLess(short_highest_hz, WHOLE_FFT_HIGHEST_HZ)
        self.double_click(short_fft_str)
        plot_id_i = self.last_plot_id()
        plot = self.plot(plot_id_i)
        self.assertEqual(self.plot_controller.frequency_limit_tuple(plot),
                         (0.0, short_highest_hz))
        self.drop(plot_id_i, whole_fft_str)
        self.assertEqual(self.plot_controller.frequency_limit_tuple(plot),
                         (0.0, WHOLE_FFT_HIGHEST_HZ))
        self.set_range(plot_id_i, 4.0, 5.0)
        # Removing the curve with the highest frequency cuts the range.
        self.view.handler_dict["curve_delete_handler"](plot_id_i,
                                                       whole_fft_str)
        self.assertEqual(plot.frequency_range_tuple,
                         (4.0, short_highest_hz))
        self.assertEqual(self.view.plot_time_range(plot_id_i),
                         (4.0, short_highest_hz))

    @covers("LLFR-00258")
    def test_range_outside_the_limit_shows_the_whole_range(self) -> None:
        """A kept range wholly above the limit falls back to the whole.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("Speed")
        time_plot_id_i = self.last_plot_id()
        self.set_range(time_plot_id_i, 0.0, 0.8)
        short_fft_str = self.create_fft("Speed")
        self.view.handler_dict["plot_delete_handler"](time_plot_id_i)
        whole_fft_str = self.create_fft("Torque")
        self.double_click(short_fft_str)
        plot_id_i = self.last_plot_id()
        self.drop(plot_id_i, whole_fft_str)
        self.set_range(plot_id_i, 4.8, 5.0)
        self.view.handler_dict["curve_delete_handler"](plot_id_i,
                                                       whole_fft_str)
        self.assertEqual(self.plot(plot_id_i).frequency_range_tuple, ())

    @covers("LLFR-00258", "LLFR-00070")
    def test_unusable_frequency_ranges_are_ignored(self) -> None:
        """A range that is not finite or not increasing is not kept.

        Inputs: none.
        Outputs: none.
        """
        self.double_click(self.create_fft())
        plot_id_i = self.last_plot_id()
        self.set_range(plot_id_i, 1.0, float("nan"))
        self.set_range(plot_id_i, 3.0, 2.0)
        self.assertEqual(self.plot(plot_id_i).frequency_range_tuple, ())
        self.assertEqual(self.plot_controller.shared_time_range_tuple, ())

    @covers("LLFR-00180", "LLFR-00070", "LLFR-00258")
    def test_shared_range_is_forgotten_with_the_last_time_plot(
            self) -> None:
        """Frequency plots do not keep the shared time range alive.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        self.double_click("Speed")
        time_plot_id_i = self.last_plot_id()
        self.double_click(fft_name_str)
        self.set_range(time_plot_id_i, 2.0, 4.0)
        self.view.handler_dict["plot_delete_handler"](time_plot_id_i)
        self.assertEqual(self.plot_controller.shared_time_range_tuple, ())
        # LLFR-00180: no other time plot, so the whole time range.
        self.double_click("Torque")
        self.assertEqual(self.view.plot_time_range(self.last_plot_id()),
                         (0.0, 9.9))

    @covers("LLFR-00248", "LLFR-00258", "HLFR-00057")
    def test_fft_range_uses_only_the_time_plots(self) -> None:
        """An FFT made while only frequency plots exist uses the file.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("Speed")
        time_plot_id_i = self.last_plot_id()
        self.set_range(time_plot_id_i, 1.5, 3.0)
        fft_name_str = self.create_fft("Torque")
        self.assertEqual(fft_name_str, "fft_Torque_1.5s_to_3s")
        self.double_click(fft_name_str)
        frequency_plot_id_i = self.last_plot_id()
        # A zoom of the frequency plot is not a time range.
        self.set_range(frequency_plot_id_i, 1.0, 2.0)
        self.assertEqual(self.plot_controller.time_plot_range_tuple(),
                         (1.5, 3.0))
        self.view.handler_dict["plot_delete_handler"](time_plot_id_i)
        self.assertEqual(self.plot_controller.time_plot_range_tuple(),
                         (0.0, 9.9))
        self.assertEqual(self.create_fft("Torque"), "fft_Torque_0s_to_9.9s")


class FrequencyPlotMarkerTest(FrequencyPlotTestCase):
    """Vertical markers and delta markers on frequency plots."""

    def place_marker(self, plot_id_i: int, time_s: float) -> None:
        """Click a plot with the Vertical marker tool.

        Inputs:
            plot_id_i: id of the clicked plot.
            time_s: the clicked time (or frequency).
        Outputs: none.
        """
        self.view.handler_dict["plot_tool"](MARKER_TOOL_STR)
        self.view.handler_dict["marker_place_handler"](plot_id_i, time_s)

    @covers("LLFR-00259", "LLFR-00205", "LLFR-00081", "HLFR-00028")
    def test_no_marker_on_frequency_plots(self) -> None:
        """Frequency plots get no marker and a click places none.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        self.double_click("Speed")
        time_plot_id_i = self.last_plot_id()
        self.double_click(fft_name_str)
        frequency_plot_id_i = self.last_plot_id()
        self.place_marker(frequency_plot_id_i, 2.0)
        self.assertEqual(self.plot_controller.workspace.marker_list, [])
        self.place_marker(time_plot_id_i, 2.0)
        marker_list = self.plot_controller.workspace.marker_list
        self.assertEqual(len(marker_list), 1)
        # LLFR-00205: the time plot shows it; a frequency plot drawn
        # afterwards (or again) gets no marker data.
        self.drop(frequency_plot_id_i, self.create_fft("Torque"))
        self.assertEqual(self.view.marker_drawn_dict[frequency_plot_id_i],
                         [])
        self.double_click(fft_name_str)
        self.assertEqual(self.view.marker_drawn_dict[self.last_plot_id()],
                         [])
        self.view.handler_dict["curve_delete_handler"](time_plot_id_i,
                                                       "Speed")
        # A move reported by a frequency plot is ignored too.
        self.view.handler_dict["marker_move_handler"](
            frequency_plot_id_i, marker_list[0].marker_id_i, 3.0)
        self.assertEqual(marker_list[0].time_s, 2.0)

    @covers("LLFR-00205", "LLFR-00259")
    def test_markers_stay_while_a_frequency_plot_exists(self) -> None:
        """A frequency plot is a plot: the markers are not deleted.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        self.double_click("Speed")
        time_plot_id_i = self.last_plot_id()
        self.double_click(fft_name_str)
        frequency_plot_id_i = self.last_plot_id()
        self.place_marker(time_plot_id_i, 2.0)
        self.view.handler_dict["plot_delete_handler"](time_plot_id_i)
        self.assertEqual(len(self.plot_controller.workspace.marker_list), 1)
        # A new time plot shows the kept marker.
        self.double_click("Torque")
        self.assertEqual(len(self.view.marker_drawn_dict[
            self.last_plot_id()]), 1)
        # With no plot of any kind left, the markers go.
        self.view.handler_dict["plot_delete_handler"](self.last_plot_id())
        self.view.handler_dict["plot_delete_handler"](frequency_plot_id_i)
        self.assertEqual(self.plot_controller.workspace.marker_list, [])

    @covers("LLFR-00261", "LLFR-00163", "LLFR-00164", "HLFR-00043")
    def test_delta_x_on_a_frequency_plot_measures_frequency(self) -> None:
        """The Delta X value of a frequency plot is a difference in Hz.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        self.double_click(fft_name_str)
        plot_id_i = self.last_plot_id()
        self.view.handler_dict["plot_tool"](DELTA_X_TOOL_STR)
        pick_handler = self.view.handler_dict["delta_point_pick_handler"]
        pick_handler(plot_id_i, fft_name_str, 1.5, 0.25)
        pick_handler(plot_id_i, fft_name_str, 0.5, 0.75)
        delta_tuple = self.view.delta_drawn_dict[plot_id_i][0]
        self.assertEqual(delta_tuple[1], "x")
        self.assertEqual(delta_tuple[2], (fft_name_str, 1.5, 0.25))
        self.assertAlmostEqual(delta_tuple[4], -1.0)
        self.assertEqual(self.view.plot_kind_dict[plot_id_i],
                         FREQUENCY_PLOT_KIND_STR)


class FrequencyPlotUndoTest(FrequencyPlotTestCase):
    """Undo and redo of frequency plots (LLFR-00140)."""

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00192", "LLFR-00256")
    def test_undo_and_redo_a_frequency_plot(self) -> None:
        """Creating a frequency plot is undone and redone, kind included.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        self.double_click(fft_name_str)
        plot_id_i = self.last_plot_id()
        self.view.handler_dict["undo"]()
        self.assertEqual(self.plot_id_list(), [])
        self.view.handler_dict["redo"]()
        self.assertEqual(self.plot_id_list(), [plot_id_i])
        self.assertEqual(self.plot(plot_id_i).kind_str,
                         FREQUENCY_PLOT_KIND_STR)
        self.assertEqual(self.view.plot_kind_dict[plot_id_i],
                         FREQUENCY_PLOT_KIND_STR)
        self.assertEqual(self.view.drawn_names(plot_id_i), [fft_name_str])
        # Deleting it is undoable too.
        self.view.handler_dict["plot_delete_handler"](plot_id_i)
        self.view.handler_dict["undo"]()
        self.assertEqual(self.plot(plot_id_i).kind_str,
                         FREQUENCY_PLOT_KIND_STR)

    @covers("LLFR-00140", "LLFR-00258", "LLFR-00138")
    def test_undo_keeps_the_frequency_range(self) -> None:
        """A zoom is not undone: an undo keeps the shown range.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        torque_fft_str = self.create_fft("Torque")
        self.double_click(fft_name_str)
        plot_id_i = self.last_plot_id()
        self.drop(plot_id_i, torque_fft_str)
        self.set_range(plot_id_i, 1.0, 2.0)
        # The zoom alone is not an undo step.
        self.view.handler_dict["undo"]()
        self.assertEqual(self.view.drawn_names(plot_id_i), [fft_name_str])
        self.assertEqual(self.plot(plot_id_i).frequency_range_tuple,
                         (1.0, 2.0))
        self.assertEqual(self.view.plot_time_range(plot_id_i), (1.0, 2.0))
        self.view.handler_dict["redo"]()
        self.assertEqual(self.view.plot_time_range(plot_id_i), (1.0, 2.0))


if __name__ == "__main__":
    unittest.main()
