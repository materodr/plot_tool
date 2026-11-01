"""Tests for the synthetic signal operations (model.synthetic_operations).

Each operation is checked against analytic results.
"""

import math
import subprocess
import sys
import unittest

import numpy as np

from tests.support import REPOSITORY_ROOT_STR, SOURCE_FOLDER_STR, covers

from model import synthetic_operations as operations
from model.errors import (
    SyntheticOperationError, SyntheticParameterError, TooFewSamplesError,
    UnevenTimeStepError)
from model.number_format import format_time_value


def even_time_array(sampling_hz: float, duration_s: float) -> np.ndarray:
    """Return evenly spaced time samples starting at 0.

    Inputs:
        sampling_hz: sampling rate, in Hz.
        duration_s: time of the last sample, in seconds (included).
    Outputs: the time samples, in seconds.
    """
    sample_count_i = int(round(duration_s * sampling_hz)) + 1
    return np.arange(sample_count_i) / sampling_hz


def sine_array(time_array: np.ndarray, frequency_hz: float,
               amplitude_f: float = 1.0) -> np.ndarray:
    """Return a sine wave sampled at the given times.

    Inputs:
        time_array: time samples, in seconds.
        frequency_hz: frequency of the sine, in Hz.
        amplitude_f: amplitude of the sine.
    Outputs: amplitude * sin(2 pi f t).
    """
    return amplitude_f * np.sin(2.0 * np.pi * frequency_hz * time_array)


class OperationTableTest(unittest.TestCase):
    """Check the operation ids, menu labels and groups."""

    @covers("LLFR-00268")
    def test_groups_and_labels_follow_the_menu_order(self) -> None:
        """The groups and labels are those of LLFR-00268, in order.

        Inputs: none.
        Outputs: none.
        """
        expected_list = [
            ("Calculus", ["Integral", "Derivative"]),
            ("Filters", ["Low-pass filter", "High-pass filter",
                         "Moving average"]),
            ("Statistics", ["Max", "Min"]),
            ("Comparison", ["Greater than", "Less than",
                            "Greater than or equal",
                            "Less than or equal"]),
            ("Arithmetic", ["Add constant", "Subtract constant",
                            "Multiply by constant", "Divide by constant",
                            "Product with signal"]),
            ("Spectrum", ["FFT"]),
        ]
        found_list = [(group_str, [operation.label_str
                                   for operation in operation_list])
                      for group_str, operation_list
                      in operations.operation_group_list()]
        self.assertEqual(found_list, expected_list)
        for group_str, operation_list in operations.operation_group_list():
            for operation in operation_list:
                self.assertEqual(operation.group_str, group_str)

    @covers("LLFR-00240")
    def test_operation_ids_are_the_name_prefixes(self) -> None:
        """The operation ids are exactly the names of LLFR-00240.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(list(operations.OPERATION_DICT), [
            "integral", "derivative", "lowpass", "highpass",
            "movingaverage", "max", "min", "greater", "less",
            "greaterorequal", "lessorequal", "add", "subtract",
            "multiply", "divide", "product", "fft"])

    @covers("LLFR-00245", "LLFR-00269", "LLFR-00272", "LLFR-00275",
            "LLFR-00248")
    def test_parameter_kinds(self) -> None:
        """Each operation asks for the parameter its dialog asks for.

        Inputs: none.
        Outputs: none.
        """
        kind_dict = {operation_str: operation.parameter_kind_str
                     for operation_str, operation
                     in operations.OPERATION_DICT.items()}
        for operation_str in ("integral", "derivative", "max", "min"):
            self.assertEqual(kind_dict[operation_str], "none")
        for operation_str in ("lowpass", "highpass"):
            self.assertEqual(kind_dict[operation_str], "cutoff_hz")
        self.assertEqual(kind_dict["movingaverage"], "window_i")
        for operation_str in ("greater", "less", "greaterorequal",
                              "lessorequal", "add", "subtract",
                              "multiply", "divide"):
            self.assertEqual(kind_dict[operation_str], "constant_f")
        self.assertEqual(kind_dict["product"], "second_signal")
        self.assertEqual(operations.OPERATION_DICT["product"]
                         .source_count_i, 2)
        self.assertEqual(kind_dict["fft"], "time_range")

    @covers("LLFR-00240")
    def test_unknown_operation_is_rejected(self) -> None:
        """An unknown operation id raises SyntheticOperationError.

        Inputs: none.
        Outputs: none.
        """
        with self.assertRaises(SyntheticOperationError):
            operations.find_operation("square")
        with self.assertRaises(SyntheticOperationError):
            operations.find_operation(3)


class CalculusTest(unittest.TestCase):
    """Check Integral and Derivative."""

    @covers("LLFR-00243")
    def test_integral_of_a_constant_is_linear(self) -> None:
        """The integral of 2 is 2 t, and starts at 0.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.array([0.0, 0.5, 1.5, 2.0, 4.0])
        result_array = operations.integral(time_array,
                                           np.full(5, 2.0))
        np.testing.assert_allclose(result_array, 2.0 * time_array)
        self.assertEqual(result_array[0], 0.0)

    @covers("LLFR-00243")
    def test_integral_of_a_line_is_exact(self) -> None:
        """The trapezoidal integral of t from t0 is (t^2 - t0^2) / 2.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.array([1.0, 1.25, 2.0, 3.5, 4.0])
        result_array = operations.integral(time_array, time_array)
        np.testing.assert_allclose(
            result_array, (time_array ** 2 - 1.0) / 2.0)

    @covers("LLFR-00243")
    def test_integral_uses_the_trapezoidal_rule(self) -> None:
        """On t^2 the result is the trapezoidal sum, not the exact one.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.array([0.0, 1.0, 2.0])
        result_array = operations.integral(time_array, time_array ** 2)
        np.testing.assert_allclose(result_array, [0.0, 0.5, 3.0])

    @covers("LLFR-00243")
    def test_integral_of_one_sample_is_zero(self) -> None:
        """A single sample integrates to [0]; the input is not changed.

        Inputs: none.
        Outputs: none.
        """
        value_array = np.array([7.0])
        np.testing.assert_array_equal(
            operations.integral(np.array([3.0]), value_array), [0.0])
        self.assertEqual(value_array[0], 7.0)

    @covers("LLFR-00244")
    def test_derivative_of_t_squared(self) -> None:
        """d(t^2)/dt is exact (2t) inside; one-sided at the ends.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.linspace(0.0, 2.0, 21)
        result_array = operations.derivative(time_array, time_array ** 2)
        np.testing.assert_allclose(result_array[1:-1],
                                   2.0 * time_array[1:-1])
        step_s = time_array[1] - time_array[0]
        self.assertAlmostEqual(result_array[0], step_s)
        self.assertAlmostEqual(result_array[-1],
                               (4.0 - (2.0 - step_s) ** 2) / step_s)

    @covers("LLFR-00244")
    def test_derivative_with_uneven_steps(self) -> None:
        """Uneven steps still give the exact slope of a line.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.array([0.0, 0.1, 0.5, 0.6, 2.0])
        result_array = operations.derivative(time_array,
                                             3.0 * time_array + 1.0)
        np.testing.assert_allclose(result_array, np.full(5, 3.0))

    @covers("LLFR-00244")
    def test_derivative_needs_two_samples(self) -> None:
        """A single sample raises SyntheticOperationError.

        Inputs: none.
        Outputs: none.
        """
        with self.assertRaises(SyntheticOperationError):
            operations.derivative(np.array([0.0]), np.array([1.0]))


class SamplingRateTest(unittest.TestCase):
    """Check the sampling rate and the even time step rule."""

    @covers("LLFR-00247")
    def test_rate_is_one_over_the_mean_step(self) -> None:
        """Evenly spaced samples at 0.01 s give 100 Hz.

        Inputs: none.
        Outputs: none.
        """
        self.assertAlmostEqual(
            operations.sampling_rate_hz(even_time_array(100.0, 3.0)),
            100.0)

    @covers("LLFR-00247")
    def test_step_within_one_percent_is_accepted(self) -> None:
        """A step 0.9% off the mean step is accepted.

        Inputs: none.
        Outputs: none.
        """
        step_array = np.full(100, 1.0)
        step_array[50] = 1.009
        time_array = np.concatenate(([0.0], np.cumsum(step_array)))
        rate_hz = operations.sampling_rate_hz(time_array)
        self.assertAlmostEqual(rate_hz, 1.0 / np.mean(step_array))

    @covers("LLFR-00247")
    def test_step_beyond_one_percent_is_rejected(self) -> None:
        """A step 1.1% off the mean step raises UnevenTimeStepError.

        Inputs: none.
        Outputs: none.
        """
        step_array = np.full(100, 1.0)
        step_array[50] = 1.0112
        time_array = np.concatenate(([0.0], np.cumsum(step_array)))
        with self.assertRaises(UnevenTimeStepError) as context:
            operations.sampling_rate_hz(time_array)
        self.assertIn("evenly spaced time samples", str(context.exception))

    @covers("LLFR-00247")
    def test_too_few_or_backward_times_are_rejected(self) -> None:
        """One sample, or a time signal that goes back, raises.

        Inputs: none.
        Outputs: none.
        """
        with self.assertRaises(SyntheticOperationError):
            operations.sampling_rate_hz(np.array([0.0]))
        with self.assertRaises(UnevenTimeStepError):
            operations.sampling_rate_hz(np.array([2.0, 1.0, 0.0]))

    @covers("LLFR-00245")
    def test_allowed_cutoff_range(self) -> None:
        """The cutoff range is (0, fs / 2), both limits excluded.

        Inputs: none.
        Outputs: none.
        """
        time_array = even_time_array(100.0, 1.0)
        self.assertEqual(operations.allowed_cutoff_range_hz(time_array),
                         (0.0, 50.0))
        for cutoff_hz in (0.0, 50.0, -1.0, 60.0, math.nan, math.inf,
                          True, "10", None):
            with self.assertRaises(SyntheticParameterError) as context:
                operations.check_cutoff_hz(cutoff_hz, time_array)
            self.assertIn("50 Hz", str(context.exception))
        self.assertEqual(operations.check_cutoff_hz(49, time_array), 49.0)
        self.assertEqual(operations.check_cutoff_hz(1e-3, time_array),
                         1e-3)

    @covers("LLFR-00245", "LLFR-00247")
    def test_cutoff_check_on_uneven_times_reports_uneven_steps(
            self) -> None:
        """With uneven times the uneven step error comes first.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.array([0.0, 1.0, 3.0, 4.0])
        with self.assertRaises(UnevenTimeStepError):
            operations.check_parameter("lowpass", 0.1, time_array, 4)


class FilterTest(unittest.TestCase):
    """Check the Butterworth Low-pass and High-pass filters."""

    def setUp(self) -> None:
        """Create 10 s of samples at 1 kHz.

        Inputs: none.
        Outputs: none.
        """
        self.time_array = even_time_array(1000.0, 10.0)

    @covers("LLFR-00246")
    def test_lowpass_keeps_a_constant(self) -> None:
        """The low-pass gain at 0 Hz is 1.

        Inputs: none.
        Outputs: none.
        """
        result_array = operations.lowpass(
            self.time_array, np.full(self.time_array.size, 4.0), 5.0)
        np.testing.assert_allclose(result_array, 4.0)

    @covers("LLFR-00246")
    def test_lowpass_removes_a_high_frequency(self) -> None:
        """A 200 Hz sine is cut far below 1% by a 2 Hz low-pass.

        Inputs: none.
        Outputs: none.
        """
        result_array = operations.lowpass(
            self.time_array, sine_array(self.time_array, 200.0), 2.0)
        middle_array = result_array[1000:-1000]
        self.assertLess(np.max(np.abs(middle_array)), 1e-3)

    @covers("LLFR-00246")
    def test_lowpass_gain_at_the_cutoff_and_no_delay(self) -> None:
        """At the cutoff the forward-backward gain is 1/2, with no delay.

        A second-order Butterworth filter has a gain of 1/sqrt(2) at the
        cutoff; applied twice, the gain is 1/2. Forward-backward
        filtering has zero phase, so the filtered sine is exactly half
        the input sine: no time shift.

        Inputs: none.
        Outputs: none.
        """
        input_array = sine_array(self.time_array, 10.0)
        result_array = operations.lowpass(self.time_array, input_array,
                                          10.0)
        np.testing.assert_allclose(result_array[2000:-2000],
                                   0.5 * input_array[2000:-2000],
                                   atol=2e-3)

    @covers("LLFR-00246")
    def test_lowpass_passes_a_low_frequency_without_delay(self) -> None:
        """A 1 Hz sine passes a 50 Hz low-pass unchanged and in phase.

        Inputs: none.
        Outputs: none.
        """
        input_array = sine_array(self.time_array, 1.0, 2.0)
        result_array = operations.lowpass(self.time_array, input_array,
                                          50.0)
        np.testing.assert_allclose(result_array[500:-500],
                                   input_array[500:-500], atol=1e-3)
        self.assertEqual(int(np.argmax(result_array[:1000])),
                         int(np.argmax(input_array[:1000])))

    @covers("LLFR-00246")
    def test_highpass_removes_the_mean(self) -> None:
        """A high-pass removes a constant offset and keeps a fast sine.

        Inputs: none.
        Outputs: none.
        """
        sine_values_array = sine_array(self.time_array, 100.0)
        result_array = operations.highpass(
            self.time_array, sine_values_array + 5.0, 1.0)
        # Away from the ends, where the filter's start-up has died out.
        np.testing.assert_allclose(result_array[3000:-3000],
                                   sine_values_array[3000:-3000],
                                   atol=2e-3)
        constant_array = operations.highpass(
            self.time_array, np.full(self.time_array.size, 5.0), 1.0)
        np.testing.assert_allclose(constant_array, 0.0, atol=1e-9)

    @covers("LLFR-00246")
    def test_highpass_gain_at_the_cutoff_is_one_half(self) -> None:
        """At the cutoff the forward-backward high-pass gain is 1/2.

        Inputs: none.
        Outputs: none.
        """
        input_array = sine_array(self.time_array, 20.0)
        result_array = operations.highpass(self.time_array, input_array,
                                           20.0)
        np.testing.assert_allclose(result_array[2000:-2000],
                                   0.5 * input_array[2000:-2000],
                                   atol=2e-3)

    @covers("LLFR-00246", "LLFR-00245")
    def test_short_signals_are_filtered(self) -> None:
        """Signals of 1 to 7 samples are filtered without an error.

        Inputs: none.
        Outputs: none.
        """
        for sample_count_i in range(2, 8):
            time_array = np.arange(sample_count_i) * 0.1
            result_array = operations.lowpass(
                time_array, np.full(sample_count_i, 3.0), 1.0)
            self.assertEqual(result_array.size, sample_count_i)
            np.testing.assert_allclose(result_array, 3.0)

    @covers("LLFR-00245", "LLFR-00247")
    def test_filters_reject_bad_cutoffs_and_uneven_times(self) -> None:
        """Out-of-range cutoffs and uneven steps raise.

        Inputs: none.
        Outputs: none.
        """
        value_array = np.zeros(self.time_array.size)
        with self.assertRaises(SyntheticParameterError):
            operations.lowpass(self.time_array, value_array, 500.0)
        with self.assertRaises(SyntheticParameterError):
            operations.highpass(self.time_array, value_array, 0.0)
        uneven_time_array = self.time_array.copy()
        uneven_time_array[5:] += 0.0005
        with self.assertRaises(UnevenTimeStepError):
            operations.lowpass(uneven_time_array, value_array, 1.0)
        with self.assertRaises(SyntheticOperationError):
            operations.highpass(np.array([0.0]), np.array([1.0]), 1.0)


class MovingAverageTest(unittest.TestCase):
    """Check the centered moving average."""

    @covers("LLFR-00270")
    def test_odd_window_is_centered_and_shrinks_at_the_ends(self) -> None:
        """Window 3 on 0..5: one sample before and after each sample.

        Inputs: none.
        Outputs: none.
        """
        result_array = operations.moving_average(np.arange(6.0), 3)
        np.testing.assert_allclose(result_array,
                                   [0.5, 1.0, 2.0, 3.0, 4.0, 4.5])

    @covers("LLFR-00270")
    def test_even_window_has_one_more_sample_after(self) -> None:
        """Window 4: one sample before, two after.

        Inputs: none.
        Outputs: none.
        """
        value_array = np.array([1.0, 2.0, 4.0, 8.0, 16.0, 32.0])
        result_array = operations.moving_average(value_array, 4)
        expected_list = [
            (1 + 2 + 4) / 3, (1 + 2 + 4 + 8) / 4, (2 + 4 + 8 + 16) / 4,
            (4 + 8 + 16 + 32) / 4, (8 + 16 + 32) / 3, (16 + 32) / 2]
        np.testing.assert_allclose(result_array, expected_list)

    @covers("LLFR-00270")
    def test_window_two_and_full_window(self) -> None:
        """Window 2 averages a sample with the next; window n is wide.

        Inputs: none.
        Outputs: none.
        """
        value_array = np.array([2.0, 4.0, 8.0, 10.0])
        np.testing.assert_allclose(
            operations.moving_average(value_array, 2),
            [3.0, 6.0, 9.0, 10.0])
        np.testing.assert_allclose(
            operations.moving_average(value_array, 4),
            [14.0 / 3.0, 6.0, 22.0 / 3.0, 9.0])

    @covers("LLFR-00270")
    def test_nan_only_affects_its_windows(self) -> None:
        """A NaN sample gives NaN only in the windows that hold it.

        Inputs: none.
        Outputs: none.
        """
        value_array = np.array([1.0, 1.0, np.nan, 1.0, 1.0, 1.0, 1.0])
        result_array = operations.moving_average(value_array, 3)
        self.assertTrue(np.all(np.isnan(result_array[1:4])))
        np.testing.assert_allclose(result_array[[0, 4, 5, 6]], 1.0)

    @covers("LLFR-00269")
    def test_allowed_window_range(self) -> None:
        """Windows from 2 to n are allowed, whole numbers only.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(operations.allowed_window_range(50), (2, 50))
        for window in (1, 0, 51, 2.5, "3", None, True, math.nan):
            with self.assertRaises(SyntheticParameterError) as context:
                operations.check_window(window, 50)
            self.assertIn("from 2 to 50", str(context.exception))
        self.assertEqual(operations.check_window(2, 50), 2)
        self.assertEqual(operations.check_window(50, 50), 50)
        self.assertEqual(operations.check_window(7.0, 50), 7)
        self.assertIsInstance(operations.check_window(7.0, 50), int)
        with self.assertRaises(SyntheticParameterError):
            operations.moving_average(np.arange(3.0), 4)


class StatisticsTest(unittest.TestCase):
    """Check Max and Min."""

    @covers("LLFR-00271")
    def test_max_and_min_are_constant_signals(self) -> None:
        """Max and Min hold the largest and smallest sample everywhere.

        Inputs: none.
        Outputs: none.
        """
        value_array = np.array([3.0, -2.0, 7.5, 0.0, 1.0])
        np.testing.assert_array_equal(operations.maximum(value_array),
                                      np.full(5, 7.5))
        np.testing.assert_array_equal(operations.minimum(value_array),
                                      np.full(5, -2.0))

    @covers("LLFR-00271")
    def test_nan_samples_are_ignored(self) -> None:
        """NaN samples are not values; all NaN gives NaN.

        Inputs: none.
        Outputs: none.
        """
        value_array = np.array([np.nan, 2.0, 5.0])
        np.testing.assert_array_equal(operations.maximum(value_array),
                                      np.full(3, 5.0))
        np.testing.assert_array_equal(operations.minimum(value_array),
                                      np.full(3, 2.0))
        self.assertTrue(np.all(np.isnan(
            operations.maximum(np.full(2, np.nan)))))
        self.assertEqual(operations.minimum(np.array([])).size, 0)


class ComparisonTest(unittest.TestCase):
    """Check the four Comparison operations."""

    @covers("LLFR-00273")
    def test_comparisons_give_one_and_zero(self) -> None:
        """Each comparison is 1 where true and 0 elsewhere, at equality too.

        Inputs: none.
        Outputs: none.
        """
        value_array = np.array([1.0, 2.0, 3.0])
        case_list = [
            (operations.greater, [0.0, 0.0, 1.0]),
            (operations.less, [1.0, 0.0, 0.0]),
            (operations.greater_or_equal, [0.0, 1.0, 1.0]),
            (operations.less_or_equal, [1.0, 1.0, 0.0]),
        ]
        for function, expected_list in case_list:
            result_array = function(value_array, 2.0)
            self.assertEqual(result_array.dtype, np.float64)
            np.testing.assert_array_equal(result_array, expected_list)

    @covers("LLFR-00272")
    def test_constant_must_be_a_number(self) -> None:
        """Not a number is rejected; 0 is allowed except for divide.

        Inputs: none.
        Outputs: none.
        """
        for constant in ("2", None, math.nan, math.inf, False, [1.0]):
            with self.assertRaises(SyntheticParameterError):
                operations.check_constant("greater", constant)
        self.assertEqual(operations.check_constant("greater", 0), 0.0)
        self.assertEqual(operations.check_constant("add", -3), -3.0)
        with self.assertRaises(SyntheticParameterError) as context:
            operations.check_constant("divide", 0.0)
        self.assertIn("0", str(context.exception))


class ArithmeticTest(unittest.TestCase):
    """Check the Arithmetic operations."""

    @covers("LLFR-00274")
    def test_arithmetic_with_a_constant(self) -> None:
        """add, subtract, multiply and divide act on every sample.

        Inputs: none.
        Outputs: none.
        """
        value_array = np.array([1.0, -2.0, 4.0])
        np.testing.assert_allclose(operations.add(value_array, 1.5),
                                   [2.5, -0.5, 5.5])
        np.testing.assert_allclose(operations.subtract(value_array, 1.5),
                                   [-0.5, -3.5, 2.5])
        np.testing.assert_allclose(operations.multiply(value_array, -2),
                                   [-2.0, 4.0, -8.0])
        np.testing.assert_allclose(operations.divide(value_array, 4),
                                   [0.25, -0.5, 1.0])
        np.testing.assert_array_equal(value_array, [1.0, -2.0, 4.0])

    @covers("LLFR-00272", "LLFR-00274")
    def test_divide_by_zero_is_rejected(self) -> None:
        """Dividing by 0 raises SyntheticParameterError.

        Inputs: none.
        Outputs: none.
        """
        with self.assertRaises(SyntheticParameterError):
            operations.divide(np.array([1.0]), 0)
        with self.assertRaises(SyntheticParameterError):
            operations.divide(np.array([1.0]), -0.0)

    @covers("LLFR-00276")
    def test_product_of_two_signals(self) -> None:
        """The product multiplies samples at the same time sample.

        Inputs: none.
        Outputs: none.
        """
        np.testing.assert_allclose(
            operations.product(np.array([1.0, 2.0, 3.0]),
                               np.array([4.0, -1.0, 0.5])),
            [4.0, -2.0, 1.5])
        np.testing.assert_allclose(
            operations.product(np.array([3.0, -2.0]),
                               np.array([3.0, -2.0])), [9.0, 4.0])
        with self.assertRaises(SyntheticOperationError):
            operations.product(np.ones(2), np.ones(3))


class FftTest(unittest.TestCase):
    """Check the FFT amplitude spectrum."""

    def setUp(self) -> None:
        """Create 2 s of samples at 100 Hz (201 samples, 0 to 2 s).

        Inputs: none.
        Outputs: none.
        """
        self.time_array = even_time_array(100.0, 2.0)

    @covers("LLFR-00249")
    def test_sine_peak_height_and_frequency(self) -> None:
        """A sine of amplitude 3 at 10 Hz peaks at 10 Hz, height ~3.

        Inputs: none.
        Outputs: none.
        """
        time_array = even_time_array(100.0, 1.99)
        value_array = sine_array(time_array, 10.0, 3.0)
        frequency_array, amplitude_array = operations.fft(
            time_array, value_array, 0.0, 1.99)
        peak_i = int(np.argmax(amplitude_array))
        self.assertAlmostEqual(frequency_array[peak_i], 10.0)
        self.assertLess(abs(amplitude_array[peak_i] - 3.0), 0.05 * 3.0)

    @covers("LLFR-00249")
    def test_peak_stays_close_for_any_sine_frequency(self) -> None:
        """Sines between two frequency bins still peak above 0.84 A.

        Inputs: none.
        Outputs: none.
        """
        time_array = even_time_array(100.0, 1.99)
        for frequency_hz in (10.25, 10.5, 17.75):
            _, amplitude_array = operations.fft(
                time_array, sine_array(time_array, frequency_hz, 2.0),
                0.0, 1.99)
            self.assertGreater(np.max(amplitude_array), 0.84 * 2.0)
            self.assertLessEqual(np.max(amplitude_array), 2.0 * 1.001)

    @covers("LLFR-00249")
    def test_frequency_axis_goes_from_zero_to_half_the_rate(self) -> None:
        """The frequencies run from 0 Hz to fs / 2 with step fs / n.

        Inputs: none.
        Outputs: none.
        """
        time_array = even_time_array(100.0, 0.99)
        frequency_array, amplitude_array = operations.fft(
            time_array, np.zeros(time_array.size), 0.0, 0.99)
        self.assertEqual(frequency_array[0], 0.0)
        self.assertAlmostEqual(frequency_array[-1], 50.0)
        self.assertEqual(frequency_array.size, amplitude_array.size)
        np.testing.assert_allclose(np.diff(frequency_array), 1.0)

    @covers("LLFR-00249")
    def test_constant_gives_its_value_at_zero_hz(self) -> None:
        """A constant c has an amplitude c at 0 Hz (not doubled).

        Inputs: none.
        Outputs: none.
        """
        frequency_array, amplitude_array = operations.fft(
            self.time_array, np.full(self.time_array.size, 2.5), 0.0, 2.0)
        self.assertAlmostEqual(amplitude_array[0], 2.5)
        self.assertLess(np.max(amplitude_array[2:]), 1e-9)

    @covers("LLFR-00248", "HLFR-00057")
    def test_only_samples_in_the_range_are_used(self) -> None:
        """Samples outside [start, end] do not change the spectrum.

        Inputs: none.
        Outputs: none.
        """
        value_array = sine_array(self.time_array, 5.0)
        changed_array = value_array.copy()
        changed_array[self.time_array < 0.5] = 100.0
        changed_array[self.time_array > 1.5] = -100.0
        first_tuple = operations.fft(self.time_array, value_array, 0.5,
                                     1.5)
        second_tuple = operations.fft(self.time_array, changed_array, 0.5,
                                      1.5)
        np.testing.assert_allclose(first_tuple[1], second_tuple[1])
        # LLFR-00248: both ends are included: 0.5 s to 1.5 s is 101
        # samples, so 51 frequencies.
        self.assertEqual(first_tuple[0].size, 51)

    @covers("LLFR-00250")
    def test_fewer_than_eight_samples_are_rejected(self) -> None:
        """7 samples raise TooFewSamplesError; 8 samples work.

        Inputs: none.
        Outputs: none.
        """
        value_array = np.ones(self.time_array.size)
        with self.assertRaises(TooFewSamplesError) as context:
            operations.fft(self.time_array, value_array, 0.0, 0.06)
        self.assertIn("too few samples", str(context.exception))
        frequency_array, _ = operations.fft(self.time_array, value_array,
                                            0.0, 0.07)
        self.assertEqual(frequency_array.size, 5)
        with self.assertRaises(TooFewSamplesError):
            operations.fft(self.time_array, value_array, 1.0, 0.5)

    @covers("LLFR-00247", "LLFR-00249")
    def test_uneven_time_steps_are_rejected(self) -> None:
        """An FFT on unevenly spaced samples raises UnevenTimeStepError.

        Inputs: none.
        Outputs: none.
        """
        uneven_time_array = self.time_array.copy()
        uneven_time_array[100:] += 0.002
        with self.assertRaises(UnevenTimeStepError):
            operations.fft(uneven_time_array,
                           np.ones(uneven_time_array.size), 0.0, 2.0)


class CheckParameterTest(unittest.TestCase):
    """Check the parameter dispatch used by the dialogs."""

    @covers("LLFR-00245", "LLFR-00269", "LLFR-00272", "LLFR-00248")
    def test_check_parameter_by_kind(self) -> None:
        """check_parameter normalizes each kind and rejects bad values.

        Inputs: none.
        Outputs: none.
        """
        time_array = even_time_array(10.0, 1.0)
        self.assertEqual(operations.check_parameter(
            "lowpass", 2, time_array, 11), 2.0)
        self.assertEqual(operations.check_parameter(
            "movingaverage", 3.0, time_array, 11), 3)
        self.assertEqual(operations.check_parameter(
            "subtract", 1, time_array, 11), 1.0)
        self.assertEqual(operations.check_parameter(
            "fft", [0, 1], time_array, 11), (0.0, 1.0))
        self.assertIsNone(operations.check_parameter(
            "integral", None, time_array, 11))
        self.assertIsNone(operations.check_parameter(
            "product", None, time_array, 11))
        for operation_str, parameter in (
                ("integral", 3.0), ("fft", (0.0,)), ("fft", "0 to 1"),
                ("fft", (0.0, math.nan)), ("highpass", 5.0),
                ("movingaverage", 12), ("divide", 0)):
            with self.assertRaises(SyntheticParameterError):
                operations.check_parameter(operation_str, parameter,
                                           time_array, 11)


class NumberFormatTest(unittest.TestCase):
    """Check the time format shared by the data tips and FFT names."""

    @covers("LLFR-00043", "LLFR-00240")
    def test_view_reuses_the_model_time_format(self) -> None:
        """view.value_text formats times with model.number_format.

        Inputs: none.
        Outputs: none.
        """
        from view import value_text
        self.assertIs(value_text.format_time_value, format_time_value)
        self.assertEqual(format_time_value(1.5), "1.5")
        self.assertEqual(format_time_value(3.0), "3")
        self.assertEqual(format_time_value(0.1 + 0.2), "0.3")


class LazyImportTest(unittest.TestCase):
    """Check that the synthetic signal modules start fast."""

    @covers("LLFR-00189")
    def test_importing_does_not_import_scipy(self) -> None:
        """scipy is imported only when a filter is first created.

        Inputs: none.
        Outputs: none.
        """
        script_str = (
            "import sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "import numpy as np\n"
            "from model import synthetic_signals, synthetic_operations\n"
            "print('scipy' in sys.modules)\n"
            "synthetic_operations.lowpass(np.arange(20.0), np.ones(20),"
            " 0.1)\n"
            "print('scipy' in sys.modules)\n")
        completed = subprocess.run(
            [sys.executable, "-c", script_str, SOURCE_FOLDER_STR],
            capture_output=True, text=True, check=True,
            cwd=REPOSITORY_ROOT_STR, timeout=120)
        self.assertEqual(completed.stdout.split(), ["False", "True"])


if __name__ == "__main__":
    unittest.main()
