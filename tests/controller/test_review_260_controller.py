"""Reviewer's tests of issue #260 for the synthetic controller (no Qt).

Covers, with the fake window of tests.controller.test_synthetic_controller
and the real controllers, the two ranges of the FFT and their names
(HLFR-00057: LLFR-01308, LLFR-01392, LLFR-00968, LLFR-00240), the
statistics that leave NaN samples out, also of a Tangent with gaps
(HLFR-00164, HLFR-00163: LLFR-01386, LLFR-01387, LLFR-01306), the names
of the statistics of the shown range and of the whole signal (LLFR-00240,
LLFR-01310) and that a shown range keeps its values after a later zoom.
"""

import random
import unittest

import numpy as np

from tests.support import covers

from controller.main_controller import MainController
from model.signal_file import SignalFile
from tests.controller.test_synthetic_controller import (
    FakeSyntheticWindow, SyntheticControllerTestCase)

# 100 samples, 0 s to 9.9 s every 0.1 s.
SAMPLE_COUNT_I = 100
# The statistics of LLFR-01307 and LLFR-00271, by their operation ids.
STATISTIC_ID_TUPLE = ("max", "min", "rms", "mean", "std", "median")


def angle_signal_file() -> SignalFile:
    """Build a file whose Angle signal hits the odd multiples of 90.

    Inputs: none.
    Outputs: a SignalFile with Time (0 to 9.9 s) and Angle (0, 45, 90,
        ... degrees), so that the Tangent of Angle is NaN at every
        second sample of four (90, 270, 450, ...).
    """
    time_array = np.arange(SAMPLE_COUNT_I) * 0.1
    return SignalFile("angles.csv", {
        "Time": time_array,
        "Angle": np.arange(SAMPLE_COUNT_I) * 45.0,
        "Speed": np.sin(time_array)})


def expected_tangent_array() -> np.ndarray:
    """Return the Tangent of the Angle signal of angle_signal_file.

    Inputs: none.
    Outputs: the tangents, NaN at the odd multiples of 90 degrees.
    """
    angle_array = np.arange(SAMPLE_COUNT_I) * 45.0
    tangent_array = np.tan(np.deg2rad(angle_array))
    tangent_array[np.remainder(angle_array - 90.0, 180.0) == 0.0] = np.nan
    return tangent_array


class ReviewControllerTestCase(SyntheticControllerTestCase):
    """The shared setup, with the file of angle_signal_file open."""

    def setUp(self) -> None:
        """Create the controllers and open the angle file as file 1.

        Inputs: none.
        Outputs: none.
        """
        self.view = FakeSyntheticWindow()
        self.main_controller = MainController(self.view)
        self.main_controller.plot_controller.workspace.random_generator = (
            random.Random(3))
        self.file_controller = self.main_controller.file_controller
        self.plot_controller = self.main_controller.plot_controller
        self.controller = self.main_controller.synthetic_controller
        self.open_file(angle_signal_file(), "angles.csv")

    def zoom_to(self, start_s: float, end_s: float) -> None:
        """Plot Speed in a time plot and show a time range.

        Inputs:
            start_s: start of the shown range, in seconds.
            end_s: end of the shown range, in seconds.
        Outputs: none.
        """
        if not self.plot_controller.time_plot_list():
            self.double_click("file1_Speed")
        plot_id_i = self.plot_controller.time_plot_list()[0].plot_id_i
        self.view.handler_dict["time_range_handler"](plot_id_i, start_s,
                                                     end_s)

    def value_of(self, name_str: str) -> np.ndarray:
        """Return the samples of a synthetic signal.

        Inputs:
            name_str: its name.
        Outputs: its value array.
        """
        return np.asarray(self.controller.store.get(name_str).value_array,
                          dtype=float)


class FftRangeChoiceTest(ReviewControllerTestCase):
    """The FFT asks for the whole signal or the shown range."""

    @covers("LLFR-01308", "LLFR-01381", "LLFR-01392", "LLFR-00968",
            "LLFR-00240", "LLFR-00248", "HLFR-00057")
    def test_whole_signal_ignores_the_zoom(self) -> None:
        """While the plots show 1.5 s to 3 s, "Whole signal" (chosen at
        first) gives the FFT of the whole file, named with the whole
        range, and "Shown x-axis range" the FFT of the shown range.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_to(1.5, 3.0)
        # LLFR-01381: the dialog opens with "Whole signal" chosen.
        self.view.parameter_answer_list = [[[]]]
        self.create("file1_Speed", "fft")
        self.assertEqual(self.view.parameter_choice_list[-1], (
            "Range:", [("whole", "Whole signal"),
                       ("shown", "Shown x-axis range")], "whole"))
        self.assertEqual(self.store_names(), ["file1_fft_0s_to_9p9s_Speed"])
        self.assertEqual(self.controller.store.get(
            "file1_fft_0s_to_9p9s_Speed").parameter, (0.0, 9.9))
        # LLFR-00968: the shown range, in the name too.
        self.view.parameter_answer_list = [[["shown"]]]
        self.create("file1_Speed", "fft")
        self.assertEqual(self.store_names(), [
            "file1_fft_0s_to_9p9s_Speed", "file1_fft_1p5s_to_3s_Speed"])
        self.assertEqual(self.controller.store.get(
            "file1_fft_1p5s_to_3s_Speed").parameter, (1.5, 3.0))
        self.assertEqual(self.view.information_list, [])

    @covers("LLFR-01311", "LLFR-01382", "LLFR-01392", "LLFR-00592",
            "HLFR-00057")
    def test_shown_then_whole_with_no_time_plot(self) -> None:
        """With no time plot, "Shown x-axis range" keeps the dialog open
        with the reason, and "Whole signal" then creates the FFT.

        Inputs: none.
        Outputs: none.
        """
        self.view.parameter_answer_list = [[["shown"], ["whole"]]]
        self.create("file1_Speed", "fft", time_plot_b=False)
        self.assertEqual(len(self.view.parameter_reason_list), 1)
        self.assertIn("time plot", self.view.parameter_reason_list[0])
        self.assertEqual(self.store_names(), ["file1_fft_0s_to_9p9s_Speed"])
        self.assertEqual(self.plot_controller.time_plot_list(), [])


class StatisticNanTest(ReviewControllerTestCase):
    """The statistics of a Tangent with gaps."""

    @covers("LLFR-01386", "LLFR-01306", "LLFR-01309", "LLFR-01307",
            "LLFR-00271", "HLFR-00164", "HLFR-00163")
    def test_whole_signal_statistics_skip_the_gaps(self) -> None:
        """Every statistic of the whole Tangent of Angle leaves its NaN
        samples out and is a number at every time sample.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Angle", "tand")
        self.assertEqual(self.store_names(), ["file1_tand_Angle"])
        tangent_array = expected_tangent_array()
        np.testing.assert_allclose(self.value_of("file1_tand_Angle"),
                                   tangent_array, equal_nan=True)
        number_array = tangent_array[~np.isnan(tangent_array)]
        expected_dict = {
            "max": np.max(number_array), "min": np.min(number_array),
            "rms": np.sqrt(np.mean(np.square(number_array))),
            "mean": np.mean(number_array),
            "std": np.std(number_array, ddof=0),
            "median": np.median(number_array)}
        for operation_str in STATISTIC_ID_TUPLE:
            with self.subTest(operation=operation_str):
                self.create("file1_tand_Angle", operation_str)
                name_str = f"file1_{operation_str}_tand_Angle"
                self.assertIn(name_str, self.store_names())
                value_array = self.value_of(name_str)
                self.assertEqual(value_array.size, SAMPLE_COUNT_I)
                self.assertFalse(np.isnan(value_array).any())
                np.testing.assert_allclose(
                    value_array,
                    np.full(SAMPLE_COUNT_I, expected_dict[operation_str]))

    @covers("LLFR-01387", "LLFR-01312", "LLFR-01310", "HLFR-00164")
    def test_shown_range_of_nan_samples_only(self) -> None:
        """A shown range that holds only a NaN sample of the signal is
        not an empty range: the dialog closes and the statistic is NaN
        at every time sample.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Angle", "tand")
        # The one sample from 0.15 s to 0.25 s is 0.2 s, at 90 degrees.
        self.zoom_to(0.15, 0.25)
        start_s, end_s = self.plot_controller.time_plot_range_tuple()
        time_array = np.arange(SAMPLE_COUNT_I) * 0.1
        inside_array = expected_tangent_array()[
            (time_array >= start_s) & (time_array <= end_s)]
        self.assertGreater(inside_array.size, 0)
        self.assertTrue(np.isnan(inside_array).all())
        self.view.parameter_answer_list = [[["shown"]]]
        self.create("file1_tand_Angle", "mean")
        self.assertEqual(self.view.parameter_reason_list, [])
        self.assertEqual(self.view.information_list, [])
        self.assertEqual(len(self.store_names()), 2)
        value_array = self.value_of(self.store_names()[-1])
        self.assertEqual(value_array.size, SAMPLE_COUNT_I)
        self.assertTrue(np.isnan(value_array).all())


class StatisticNameTest(ReviewControllerTestCase):
    """The names and values of the statistics of each range."""

    @covers("LLFR-00240", "LLFR-01309", "LLFR-01310", "LLFR-01307",
            "HLFR-00164", "HLFR-00054")
    def test_names_of_both_ranges(self) -> None:
        """A statistic of the whole signal has no range in its name; one
        of the shown range has `<start>s_to_<end>s` after its
        abbreviation, and keeps its values after a later zoom.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_to(1.5, 3.0)
        self.view.parameter_answer_list = [[[]]]
        self.create("file1_Speed", "max")
        self.view.parameter_answer_list = [[["shown"]]]
        self.create("file1_Speed", "rms")
        self.assertEqual(self.store_names(), [
            "file1_max_Speed", "file1_rms_1p5s_to_3s_Speed"])
        time_array = np.arange(SAMPLE_COUNT_I) * 0.1
        speed_array = np.sin(time_array)
        np.testing.assert_allclose(self.value_of("file1_max_Speed"),
                                   np.full(SAMPLE_COUNT_I,
                                           np.max(speed_array)))
        inside_array = speed_array[(time_array >= 1.5)
                                   & (time_array <= 3.0)]
        expected_f = float(np.sqrt(np.mean(np.square(inside_array))))
        np.testing.assert_allclose(
            self.value_of("file1_rms_1p5s_to_3s_Speed"),
            np.full(SAMPLE_COUNT_I, expected_f))
        # LLFR-01310 Note: a later zoom leaves the signal unchanged.
        self.zoom_to(5.0, 9.0)
        np.testing.assert_allclose(
            self.value_of("file1_rms_1p5s_to_3s_Speed"),
            np.full(SAMPLE_COUNT_I, expected_f))
        self.assertEqual(self.controller.store.get(
            "file1_rms_1p5s_to_3s_Speed").parameter, (1.5, 3.0))


if __name__ == "__main__":
    unittest.main()
