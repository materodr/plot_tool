"""Tests for the trigonometric operations, the statistics and the
signals from scratch of the model (issue #260).

Covers HLFR-00163 (LLFR-01305, LLFR-01306), HLFR-00164 (LLFR-00271,
LLFR-01307, LLFR-01309, LLFR-01310, LLFR-01312) and HLFR-00162
(LLFR-01291, LLFR-01294 to LLFR-01302, LLFR-01304), with the names
(LLFR-00240, LLFR-00569) and the layout file entries (LLFR-00225).
"""

import json
import unittest

import numpy as np

from tests.support import covers

from model import synthetic_operations as operations
from model.errors import SyntheticSignalError
from model.synthetic_signals import SyntheticSignalStore, entries_text

TIME_ARRAY = np.linspace(0.0, 4.0, 41)
SIGNAL_DICT = {"file1_Time": TIME_ARRAY, "file1_Speed": TIME_ARRAY * 2.0,
               "file1_Angle": np.array([0.0, 30.0, 90.0, 180.0, 270.0,
                                        -90.0, 45.0, 450.0] + [60.0] * 33)}


class StoreTestCase(unittest.TestCase):
    """A store over one data file."""

    def setUp(self) -> None:
        """Create an empty store.

        Inputs: none.
        Outputs: none.
        """
        self.store = SyntheticSignalStore()

    def lookup(self, name_str: str):
        """Return the samples of a signal.

        Inputs:
            name_str: a data file or synthetic signal name.
        Outputs: its array.
        """
        if name_str in SIGNAL_DICT:
            return SIGNAL_DICT[name_str]
        return self.store.get(name_str).value_array

    def create(self, operation_str: str, source_str: str, parameter):
        """Create a synthetic signal.

        Inputs:
            operation_str: the operation id.
            source_str: its source.
            parameter: its parameter.
        Outputs: the SyntheticSignal.
        """
        return self.store.create(operation_str, [source_str], parameter,
                                 self.lookup, TIME_ARRAY, set(SIGNAL_DICT))


class TrigonometricTest(StoreTestCase):
    """Sine, Cosine and Tangent in degrees."""

    @covers("LLFR-01305", "LLFR-00240", "LLFR-00268", "HLFR-00163")
    def test_values_are_taken_as_degrees(self) -> None:
        """sind, cosd and tand of degrees, named with the abbreviation.

        Inputs: none.
        Outputs: none.
        """
        angle_array = SIGNAL_DICT["file1_Angle"]
        sine = self.create(operations.SINE_DEGREES_STR, "file1_Angle", None)
        cosine = self.create(operations.COSINE_DEGREES_STR, "file1_Angle",
                             None)
        tangent = self.create(operations.TANGENT_DEGREES_STR, "file1_Angle",
                              None)
        self.assertEqual(sine.name_str, "file1_sind_Angle")
        self.assertEqual(cosine.name_str, "file1_cosd_Angle")
        self.assertEqual(tangent.name_str, "file1_tand_Angle")
        np.testing.assert_allclose(sine.value_array[:3], [0.0, 0.5, 1.0],
                                   atol=1e-12)
        np.testing.assert_allclose(cosine.value_array[[0, 3]], [1.0, -1.0],
                                   atol=1e-12)
        np.testing.assert_allclose(tangent.value_array[[0, 6]], [0.0, 1.0],
                                   atol=1e-12)
        self.assertEqual(sine.value_array.size, angle_array.size)
        self.assertIsNone(self.store.layout_entry(sine)["parameter"])

    @covers("LLFR-01306", "HLFR-00163")
    def test_tangent_has_gaps_at_odd_multiples_of_90(self) -> None:
        """90, 270, -90 and 450 degrees give NaN; 180 does not.

        Inputs: none.
        Outputs: none.
        """
        tangent_array = operations.tangent_degrees(SIGNAL_DICT["file1_Angle"])
        self.assertTrue(np.all(np.isnan(tangent_array[[2, 4, 5, 7]])))
        self.assertFalse(np.isnan(tangent_array[3]))
        self.assertEqual(int(np.count_nonzero(np.isnan(tangent_array))), 4)


class StatisticTest(StoreTestCase):
    """RMS, Mean, Standard deviation, Median, Max and Min."""

    @covers("LLFR-01307", "LLFR-01309", "LLFR-00271", "HLFR-00164")
    def test_whole_signal_statistics(self) -> None:
        """Each statistic of the whole signal, constant at every sample.

        Inputs: none.
        Outputs: none.
        """
        speed_array = SIGNAL_DICT["file1_Speed"]
        expected_dict = {
            operations.RMS_STR: np.sqrt(np.mean(speed_array ** 2)),
            operations.MEAN_STR: np.mean(speed_array),
            operations.STANDARD_DEVIATION_STR: np.std(speed_array),
            operations.MEDIAN_STR: np.median(speed_array),
            operations.MAXIMUM_STR: 8.0, operations.MINIMUM_STR: 0.0}
        for operation_str, expected_f in expected_dict.items():
            with self.subTest(operation=operation_str):
                signal = self.create(operation_str, "file1_Speed", None)
                self.assertEqual(signal.name_str,
                                 f"file1_{operation_str}_Speed")
                np.testing.assert_allclose(
                    signal.value_array, np.full(speed_array.size,
                                                expected_f))
                self.assertIsNone(self.store.layout_entry(signal)
                                  ["parameter"])

    @covers("LLFR-01307", "HLFR-00164")
    def test_population_standard_deviation(self) -> None:
        """The standard deviation divides by the number of samples.

        Inputs: none.
        Outputs: none.
        """
        value_array = np.array([1.0, 3.0])
        result_array = operations.statistic(
            operations.STANDARD_DEVIATION_STR, np.array([0.0, 1.0]),
            value_array, None)
        np.testing.assert_allclose(result_array, [1.0, 1.0])

    @covers("LLFR-01386", "LLFR-01387", "LLFR-01306", "HLFR-00164",
            "HLFR-00163")
    def test_nan_samples_are_left_out(self) -> None:
        """The statistics skip NaN samples, as in a Tangent with gaps;
        a range of NaN samples only gives NaN.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.array([0.0, 1.0, 2.0, 3.0])
        value_array = np.array([1.0, np.nan, 3.0, np.nan])
        expected_dict = {
            operations.RMS_STR: np.sqrt(5.0), operations.MEAN_STR: 2.0,
            operations.STANDARD_DEVIATION_STR: 1.0,
            operations.MEDIAN_STR: 2.0, operations.MAXIMUM_STR: 3.0,
            operations.MINIMUM_STR: 1.0}
        for operation_str, expected_f in expected_dict.items():
            with self.subTest(operation=operation_str):
                np.testing.assert_allclose(
                    operations.statistic(operation_str, time_array,
                                         value_array, None),
                    np.full(4, expected_f))
                # LLFR-01387: only NaN samples within the shown range.
                nan_only_array = operations.statistic(
                    operation_str, time_array, value_array, (0.5, 1.5))
                self.assertEqual(nan_only_array.size, 4)
                self.assertTrue(np.all(np.isnan(nan_only_array)))
        # The tangent of the Angle signal holds NaN gaps (LLFR-01306), and
        # its mean is still a number.
        tangent = self.create(operations.TANGENT_DEGREES_STR, "file1_Angle",
                              None)
        mean = self.create(operations.MEAN_STR, tangent.name_str, None)
        self.assertTrue(np.all(np.isfinite(mean.value_array)))

    @covers("LLFR-01310", "LLFR-00240", "LLFR-00225", "HLFR-00164")
    def test_shown_range_statistics(self) -> None:
        """A range gives the statistic of its samples, its range in the
        name and in the layout entry.

        Inputs: none.
        Outputs: none.
        """
        signal = self.create(operations.RMS_STR, "file1_Speed", (1.5, 3.0))
        self.assertEqual(signal.name_str, "file1_rms_1p5s_to_3s_Speed")
        inside_array = SIGNAL_DICT["file1_Speed"][
            (TIME_ARRAY >= 1.5) & (TIME_ARRAY <= 3.0)]
        np.testing.assert_allclose(signal.value_array[0],
                                   np.sqrt(np.mean(inside_array ** 2)))
        self.assertEqual(signal.value_array.size, TIME_ARRAY.size)
        entry_dict = self.store.layout_entry(signal)
        self.assertEqual(entry_dict["parameter"], {"start": 1.5, "end": 3.0})
        other_store = SyntheticSignalStore()
        rebuilt = other_store.create_from_entry(
            json.loads(json.dumps(entry_dict)), self.lookup, TIME_ARRAY,
            set(SIGNAL_DICT))
        np.testing.assert_allclose(rebuilt.value_array, signal.value_array)
        maximum = self.create(operations.MAXIMUM_STR, "file1_Speed",
                              (1.0, 2.0))
        self.assertEqual(maximum.name_str, "file1_max_1s_to_2s_Speed")
        np.testing.assert_allclose(maximum.value_array[0], 4.0)

    @covers("LLFR-01312", "LLFR-01308", "HLFR-00164")
    def test_empty_or_unusable_ranges_are_refused(self) -> None:
        """No sample in the range, a reversed range or a range that is
        not two numbers creates nothing.

        Inputs: none.
        Outputs: none.
        """
        for range_value in ((5.0, 6.0), (3.0, 1.0), ("a", 1.0), (1.0,)):
            with self.subTest(range_value=range_value):
                with self.assertRaises(SyntheticSignalError):
                    self.create(operations.MEAN_STR, "file1_Speed",
                                range_value)
        self.assertEqual(self.store.names(), [])
        self.assertIsNone(operations.check_statistic_range(()))


class GeneratorTest(StoreTestCase):
    """The signals made from scratch."""

    @covers("LLFR-01294", "LLFR-01295", "LLFR-01296", "LLFR-01297",
            "LLFR-01298", "LLFR-01299", "LLFR-01300", "LLFR-01301",
            "HLFR-00162")
    def test_values_and_names(self) -> None:
        """Each signal has one sample per time sample, its values and its
        name of LLFR-01301.

        Inputs: none.
        Outputs: none.
        """
        case_list = [
            (operations.CONSTANT_SIGNAL_STR, (2.0,), "file1_const_2",
             np.full(TIME_ARRAY.size, 2.0)),
            (operations.STEP_SIGNAL_STR, (1.0, 0.0, 5.0),
             "file1_step_1s_0_to_5", np.where(TIME_ARRAY < 1.0, 0.0, 5.0)),
            (operations.RAMP_SIGNAL_STR, (1.0, 2.0, 0.0),
             "file1_ramp_1s_slope2_from0",
             np.where(TIME_ARRAY < 1.0, 0.0, 2.0 * (TIME_ARRAY - 1.0))),
            (operations.POLYNOMIAL_SIGNAL_STR, (1.0, 0.0, -2.5),
             "file1_poly_a1_b0_c2n5", TIME_ARRAY ** 2 - 2.5),
            (operations.SINE_SIGNAL_STR, (1.0, 2.0, 0.0, 0.0),
             "file1_sin_amp1_2Hz_ph0deg_off0",
             np.sin(2.0 * np.pi * 2.0 * TIME_ARRAY)),
            (operations.COSINE_SIGNAL_STR, (2.0, 0.5, 90.0, 1.0),
             "file1_cos_amp2_0p5Hz_ph90deg_off1",
             1.0 + 2.0 * np.cos(np.pi * TIME_ARRAY + np.pi / 2.0))]
        for operation_str, value_tuple, name_str, expected_array in case_list:
            with self.subTest(operation=operation_str):
                signal = self.create(operation_str, "file1_Time",
                                     value_tuple)
                self.assertEqual(signal.name_str, name_str)
                self.assertEqual(signal.file_number_i, 1)
                np.testing.assert_allclose(signal.value_array,
                                           expected_array, atol=1e-12)

    @covers("LLFR-01302", "HLFR-00162")
    def test_name_in_use_gets_a_number(self) -> None:
        """A second constant of the same value is numbered.

        Inputs: none.
        Outputs: none.
        """
        self.create(operations.CONSTANT_SIGNAL_STR, "file1_Time", (2.0,))
        second = self.create(operations.CONSTANT_SIGNAL_STR, "file1_Time",
                             (2.0,))
        self.assertEqual(second.name_str, "file1_const_2_2")

    @covers("LLFR-01291", "HLFR-00162")
    def test_values_must_be_numbers(self) -> None:
        """A value that is not a number, a missing value or a frequency
        of 0 or less is refused.

        Inputs: none.
        Outputs: none.
        """
        for operation_str, value_tuple in (
                (operations.CONSTANT_SIGNAL_STR, ("x",)),
                (operations.STEP_SIGNAL_STR, (1.0, 2.0)),
                (operations.SINE_SIGNAL_STR, (1.0, 0.0, 0.0, 0.0)),
                (operations.COSINE_SIGNAL_STR, (1.0, -1.0, 0.0, 0.0)),
                (operations.RAMP_SIGNAL_STR, (1.0, float("nan"), 0.0))):
            with self.subTest(operation=operation_str):
                with self.assertRaises(SyntheticSignalError):
                    self.create(operation_str, "file1_Time", value_tuple)
        with self.assertRaises(SyntheticSignalError):
            operations.check_parameter(operations.SINE_SIGNAL_STR,
                                       (1.0, 0.0, 0.0, 0.0), TIME_ARRAY, 41)

    @covers("LLFR-01304", "LLFR-00279", "LLFR-00262", "HLFR-00162",
            "HLFR-00056", "HLFR-00062")
    def test_layout_entry_and_equation(self) -> None:
        """The entry names the time signal and holds the values under
        their keys, and creates the signal again.

        Inputs: none.
        Outputs: none.
        """
        step = self.create(operations.STEP_SIGNAL_STR, "file1_Time",
                           (1.0, 0.0, 5.0))
        entry_dict = self.store.layout_entry(step)
        self.assertEqual(entry_dict, {
            "name": "file1_step_1s_0_to_5", "operation": "step",
            "signals": ["file1_Time"],
            "parameter": {"time": 1.0, "before": 0.0, "after": 5.0}})
        equation_list = json.loads(self.store.equation_text(step.name_str))
        self.assertEqual(equation_list, [entry_dict])
        self.assertEqual(json.loads(entries_text([entry_dict])),
                         [entry_dict])
        other_store = SyntheticSignalStore()
        rebuilt = other_store.create_from_entry(
            entry_dict, self.lookup, TIME_ARRAY, set(SIGNAL_DICT))
        np.testing.assert_allclose(rebuilt.value_array, step.value_array)
        broken_dict = dict(entry_dict, parameter={"time": 1.0})
        with self.assertRaises(SyntheticSignalError):
            SyntheticSignalStore().create_from_entry(
                broken_dict, self.lookup, TIME_ARRAY, set(SIGNAL_DICT))

    @covers("LLFR-01294", "HLFR-00162")
    def test_source_must_be_a_time_signal(self) -> None:
        """With a store that knows the time signals, another signal is
        refused as the source of a signal from scratch.

        Inputs: none.
        Outputs: none.
        """
        self.store.time_name_function = lambda name_str: (
            name_str == "file1_Time")
        with self.assertRaises(SyntheticSignalError):
            self.create(operations.CONSTANT_SIGNAL_STR, "file1_Speed",
                        (1.0,))
        self.create(operations.CONSTANT_SIGNAL_STR, "file1_Time", (1.0,))
        self.assertEqual(self.store.names(), ["file1_const_1"])


if __name__ == "__main__":
    unittest.main()
