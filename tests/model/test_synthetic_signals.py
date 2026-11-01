"""Tests for the synthetic signal names and store (model.synthetic_signals).
"""

import json
import unittest

import numpy as np

from tests.support import covers

from model.errors import (
    EmptySyntheticNameError, SyntheticEntryError, SyntheticNameInUseError,
    SyntheticOperationError, SyntheticParameterError, SyntheticSignalError,
    SyntheticSourceError, TooFewSamplesError, UnevenTimeStepError)
from model.synthetic_signals import (
    LAYOUT_KEY_STR, SyntheticSignal, SyntheticSignalStore, entries_text,
    synthetic_name)


class DataFile:
    """A small data file with a store, as the controller will hold them.

    Inputs:
        time_array: the time signal, in seconds (default 0 to 10 s at
            100 Hz).
    Outputs: the object, with signal_dict, store and helper methods.
    """

    def __init__(self, time_array=None) -> None:
        """Create the signals Time, Speed and Torque and an empty store.

        Inputs:
            time_array: the time samples, or None for the default.
        Outputs: none.
        """
        if time_array is None:
            time_array = np.arange(1001) / 100.0
        self.time_array = np.asarray(time_array, dtype=float)
        self.signal_dict = {
            "Time": self.time_array,
            "Speed": 2.0 * self.time_array + 1.0,
            "Torque": np.sin(2.0 * np.pi * self.time_array),
        }
        self.store = SyntheticSignalStore()

    def data_name_set(self) -> set:
        """Return the names of the data file signals.

        Inputs: none.
        Outputs: the set of names.
        """
        return set(self.signal_dict)

    def lookup(self, name_str: str):
        """Return the samples of a data file or synthetic signal.

        Inputs:
            name_str: the signal name.
        Outputs: its samples.
        """
        if name_str in self.signal_dict:
            return self.signal_dict[name_str]
        return self.store.get(name_str).value_array

    def create(self, operation_str: str, source_name_list: list,
               parameter=None) -> SyntheticSignal:
        """Create a synthetic signal in the store.

        Inputs:
            operation_str: the operation id.
            source_name_list: the source names.
            parameter: the operation's parameter.
        Outputs: the new SyntheticSignal.
        """
        return self.store.create(operation_str, source_name_list,
                                 parameter, self.lookup, self.time_array,
                                 self.data_name_set())

    def create_from_entry(self, entry_dict) -> SyntheticSignal:
        """Create a synthetic signal from a layout file entry.

        Inputs:
            entry_dict: the entry.
        Outputs: the new SyntheticSignal.
        """
        return self.store.create_from_entry(
            entry_dict, self.lookup, self.time_array,
            self.data_name_set())


class NameTest(unittest.TestCase):
    """Check synthetic_name against the table of LLFR-00240."""

    @covers("LLFR-00240", "LLFR-00268", "LLFR-00284", "HLFR-00054")
    def test_operations_without_a_parameter(self) -> None:
        """Integral to Absolute value are <abbreviation>_<signal>.

        Inputs: none.
        Outputs: none.
        """
        for operation_str, name_str in (
                ("integral", "int_Speed"), ("derivative", "der_Speed"),
                ("max", "max_Speed"), ("min", "min_Speed"),
                ("abs", "abs_Speed")):
            with self.subTest(operation=operation_str):
                self.assertEqual(synthetic_name(operation_str, ["Speed"],
                                                None, set()), name_str)

    @covers("LLFR-00240", "LLFR-00043", "LLFR-00044", "HLFR-00054")
    def test_constant_operations(self) -> None:
        """Arithmetic and comparisons are <abbr>_<constant>_<signal>.

        Inputs: none.
        Outputs: none.
        """
        for operation_str, constant_f, name_str in (
                ("add", 2.5, "add_2.5_Speed"),
                ("subtract", 3.0, "sub_3_Speed"),
                ("multiply", 0.5, "mul_0.5_Speed"),
                ("divide", -4.0, "div_-4_Speed"),
                ("greater", 2.5, "gt_2.5_Speed"),
                ("less", -0.25, "lt_-0.25_Speed"),
                ("greaterorequal", 0.0, "ge_0_Speed"),
                ("lessorequal", 1.0, "le_1_Speed"),
                ("add", -2, "add_-2_Speed")):
            with self.subTest(operation=operation_str, constant=constant_f):
                self.assertEqual(synthetic_name(operation_str, ["Speed"],
                                                constant_f, set()),
                                 name_str)

    @covers("LLFR-00240", "LLFR-00044", "HLFR-00054")
    def test_numbers_are_plain_tokens_in_the_data_tip_format(
            self) -> None:
        """Large, small and long constants use the data tip format.

        Inputs: none.
        Outputs: none.
        """
        for constant_f, name_str in (
                (1e6, "add_1e+06_Speed"), (-1e6, "add_-1e+06_Speed"),
                (1.5e-7, "add_1.5e-07_Speed"),
                (0.1 + 0.2, "add_0.3_Speed"),
                (123456789.0, "add_1.23457e+08_Speed"),
                (3.14159265, "add_3.14159_Speed")):
            with self.subTest(constant=constant_f):
                found_str = synthetic_name("add", ["Speed"], constant_f,
                                           set())
                self.assertEqual(found_str, name_str)
                self.assertNotIn(" ", found_str)
        for parameter in ((1e-5, 2, "zero"), (12345.678, 8, "zero")):
            with self.subTest(parameter=parameter):
                self.assertNotIn(" ", synthetic_name(
                    "lowpass", ["Speed"], parameter, set()))
        self.assertEqual(synthetic_name("lowpass", ["Speed"],
                                        (12345.678, 8, "zero"), set()),
                         "lpf_12345.7Hz_order8_Speed")
        self.assertEqual(synthetic_name("fft", ["Speed"],
                                        (-1e-7, 2e6), set()),
                         "fft_-1e-07s_to_2e+06s_Speed")

    @covers("LLFR-00240", "LLFR-00246", "HLFR-00054")
    def test_filter_names_hold_cutoff_and_order_not_start(self) -> None:
        """Filters are <abbr>_<cutoff>Hz_order<order>_<signal>.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(synthetic_name("lowpass", ["Speed"],
                                        (5.0, 2, "first_value"), set()),
                         "lpf_5Hz_order2_Speed")
        self.assertEqual(synthetic_name("lowpass", ["Speed"],
                                        (5.0, 2, "zero"), set()),
                         "lpf_5Hz_order2_Speed")
        self.assertEqual(synthetic_name("highpass", ["Speed"],
                                        (0.25, 8, "zero"), set()),
                         "hpf_0.25Hz_order8_Speed")

    @covers("LLFR-00240", "HLFR-00054")
    def test_moving_average_name_holds_the_window(self) -> None:
        """A moving average is mavg_<window>samples_<signal>.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(synthetic_name("movingaverage", ["Speed"], 10,
                                        set()), "mavg_10samples_Speed")
        self.assertEqual(synthetic_name("movingaverage", ["a b"], 2,
                                        set()), "mavg_2samples_a b")

    @covers("LLFR-00240", "LLFR-00264", "HLFR-00054")
    def test_chains_build_up_from_left_to_right(self) -> None:
        """A synthetic source is used with its whole name.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(synthetic_name("derivative", ["int_Speed"],
                                        None, set()), "der_int_Speed")
        self.assertEqual(synthetic_name("abs", ["der_int_Speed"], None,
                                        set()), "abs_der_int_Speed")

    @covers("LLFR-00240", "LLFR-00275", "HLFR-00054")
    def test_product_names_both_signals(self) -> None:
        """A product is named <first>_prod_<second>.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(synthetic_name("product", ["Speed", "Torque"],
                                        None, set()),
                         "Speed_prod_Torque")
        self.assertEqual(synthetic_name("product", ["Speed", "Speed"],
                                        None, set()),
                         "Speed_prod_Speed")
        self.assertEqual(synthetic_name("product", ["int_Speed",
                                                    "Torque"],
                                        None, set()),
                         "int_Speed_prod_Torque")

    @covers("LLFR-00240", "LLFR-00043", "HLFR-00054", "HLFR-00057")
    def test_fft_name_shows_the_time_range(self) -> None:
        """FFT names are fft_<start>s_to_<end>s_<signal>.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(synthetic_name("fft", ["Speed"], (1.5, 3.0),
                                        set()),
                         "fft_1.5s_to_3s_Speed")
        self.assertEqual(synthetic_name("fft", ["lpf_5Hz_order2_Speed"],
                                        (1.5, 3.0), set()),
                         "fft_1.5s_to_3s_lpf_5Hz_order2_Speed")
        self.assertEqual(synthetic_name("fft", ["Speed"],
                                        (0.1 + 0.2, 12.3456789), set()),
                         "fft_0.3s_to_12.3457s_Speed")
        self.assertNotEqual(
            synthetic_name("fft", ["Speed"], (0.0, 1.0), set()),
            synthetic_name("fft", ["Speed"], (0.0, 2.0), set()))

    @covers("LLFR-00241")
    def test_used_name_gets_the_smallest_free_number(self) -> None:
        """A used name gets _2, _3, ... the smallest unused number.

        Inputs: none.
        Outputs: none.
        """
        filter_tuple = (5.0, 2, "first_value")
        self.assertEqual(synthetic_name("lowpass", ["Speed"], filter_tuple,
                                        {"lpf_5Hz_order2_Speed"}),
                         "lpf_5Hz_order2_Speed_2")
        self.assertEqual(synthetic_name(
            "lowpass", ["Speed"], filter_tuple,
            {"lpf_5Hz_order2_Speed", "lpf_5Hz_order2_Speed_2",
             "lpf_5Hz_order2_Speed_4"}),
            "lpf_5Hz_order2_Speed_3")
        self.assertEqual(synthetic_name("lowpass", ["Speed"], filter_tuple,
                                        {"lpf_5Hz_order2_Speed_2"}),
                         "lpf_5Hz_order2_Speed")


class StoreCreateTest(unittest.TestCase):
    """Check creating synthetic signals in the store."""

    def setUp(self) -> None:
        """Create a data file with an empty store.

        Inputs: none.
        Outputs: none.
        """
        self.data_file = DataFile()

    @covers("LLFR-00242", "LLFR-00243", "LLFR-00264", "HLFR-00053")
    def test_create_computes_names_and_appends(self) -> None:
        """create computes the samples, names and appends in order.

        Inputs: none.
        Outputs: none.
        """
        integral = self.data_file.create("integral", ["Speed"])
        derivative = self.data_file.create("derivative",
                                           ["int_Speed"])
        self.assertEqual(self.data_file.store.names(),
                         ["int_Speed", "der_int_Speed"])
        time_array = self.data_file.time_array
        np.testing.assert_allclose(integral.value_array,
                                   time_array ** 2 + time_array)
        np.testing.assert_allclose(derivative.value_array[1:-1],
                                   2.0 * time_array[1:-1] + 1.0)
        self.assertEqual(integral.source_name_list, ["Speed"])
        self.assertIsNone(integral.parameter)
        self.assertIsNone(integral.frequency_array)
        self.assertFalse(integral.is_fft_b)
        self.assertIs(self.data_file.store.get("int_Speed"), integral)
        self.assertEqual(integral.operation.label_str, "Integral")

    @covers("LLFR-00253", "HLFR-00055")
    def test_create_never_changes_the_data_signals(self) -> None:
        """The data file signals are unchanged after every operation.

        Inputs: none.
        Outputs: none.
        """
        copy_dict = {name_str: values_array.copy() for name_str,
                     values_array in self.data_file.signal_dict.items()}
        for operation_str, parameter in (
                ("integral", None), ("derivative", None),
                ("lowpass", (5.0, 2, "first_value")),
                ("highpass", (5.0, 3, "zero")),
                ("movingaverage", 4), ("max", None), ("min", None),
                ("greater", 1.0), ("add", 2.0), ("divide", 2.0),
                ("fft", (0.0, 10.0))):
            self.data_file.create(operation_str, ["Speed"], parameter)
        self.data_file.create("product", ["Speed", "Torque"])
        for name_str, values_array in copy_dict.items():
            np.testing.assert_array_equal(
                self.data_file.signal_dict[name_str], values_array)
        self.assertEqual(set(self.data_file.signal_dict),
                         {"Time", "Speed", "Torque"})

    @covers("LLFR-00241")
    def test_same_operation_twice_gets_a_number(self) -> None:
        """Two filters that differ only in their start get _2.

        Inputs: none.
        Outputs: none.
        """
        first = self.data_file.create("lowpass", ["Speed"],
                                      (1.0, 2, "zero"))
        second = self.data_file.create("lowpass", ["Speed"],
                                       (1.0, 2, "first_value"))
        self.assertEqual(first.name_str, "lpf_1Hz_order2_Speed")
        self.assertEqual(second.name_str, "lpf_1Hz_order2_Speed_2")
        self.assertEqual(second.parameter, (1.0, 2, "first_value"))
        third = self.data_file.create("lowpass", ["Speed"],
                                      (2.0, 2, "first_value"))
        self.assertEqual(third.name_str, "lpf_2Hz_order2_Speed")

    @covers("LLFR-00241")
    def test_name_is_unique_against_data_file_names(self) -> None:
        """A data file signal named like the new signal is avoided.

        Inputs: none.
        Outputs: none.
        """
        self.data_file.signal_dict["max_Speed"] = np.zeros(1001)
        signal = self.data_file.create("max", ["Speed"])
        self.assertEqual(signal.name_str, "max_Speed_2")
        np.testing.assert_allclose(signal.value_array, 21.0)

    @covers("LLFR-00275", "LLFR-00276")
    def test_product_with_a_synthetic_second_signal(self) -> None:
        """A product can use a synthetic signal and itself as second.

        Inputs: none.
        Outputs: none.
        """
        self.data_file.create("add", ["Speed"], 1.0)
        signal = self.data_file.create("product", ["Speed", "add_1_Speed"])
        self.assertEqual(signal.name_str, "Speed_prod_add_1_Speed")
        speed_array = self.data_file.signal_dict["Speed"]
        np.testing.assert_allclose(signal.value_array,
                                   speed_array * (speed_array + 1.0))
        self.assertEqual(signal.source_name_list, ["Speed", "add_1_Speed"])
        square = self.data_file.create("product", ["Speed", "Speed"])
        np.testing.assert_allclose(square.value_array, speed_array ** 2)

    @covers("LLFR-00240", "LLFR-00241")
    def test_integral_of_a_product_and_product_of_an_integral(
            self) -> None:
        """int_Speed_prod_Torque made twice in two ways gets _2.

        Inputs: none.
        Outputs: none.
        """
        product = self.data_file.create("product", ["Speed", "Torque"])
        self.assertEqual(product.name_str, "Speed_prod_Torque")
        first = self.data_file.create("integral", ["Speed_prod_Torque"])
        self.assertEqual(first.name_str, "int_Speed_prod_Torque")
        self.data_file.create("integral", ["Speed"])
        second = self.data_file.create("product", ["int_Speed", "Torque"])
        self.assertEqual(second.name_str, "int_Speed_prod_Torque_2")
        self.assertEqual(second.source_name_list, ["int_Speed", "Torque"])
        self.assertEqual(first.source_name_list, ["Speed_prod_Torque"])

    @covers("LLFR-00284", "LLFR-00240", "LLFR-00264", "HLFR-00053")
    def test_absolute_value_signal(self) -> None:
        """abs_<signal> holds the absolute value and can be chained.

        Inputs: none.
        Outputs: none.
        """
        signal = self.data_file.create("abs", ["Torque"])
        self.assertEqual(signal.name_str, "abs_Torque")
        np.testing.assert_allclose(
            signal.value_array, np.abs(self.data_file.signal_dict["Torque"]))
        self.assertTrue(np.all(signal.value_array >= 0.0))
        self.assertIsNone(signal.parameter)
        self.assertEqual(signal.operation.menu_label_str,
                         "Absolute value (abs)")
        chained = self.data_file.create("abs", ["abs_Torque"])
        self.assertEqual(chained.name_str, "abs_abs_Torque")
        np.testing.assert_allclose(chained.value_array, signal.value_array)
        integral = self.data_file.create("integral", ["abs_Torque"])
        self.assertEqual(integral.name_str, "int_abs_Torque")
        with self.assertRaises(SyntheticParameterError):
            self.data_file.create("abs", ["Speed"], 2.0)
        fft_name_str = self.data_file.create("fft", ["Speed"],
                                             (0.0, 1.0)).name_str
        with self.assertRaises(SyntheticSourceError):
            self.data_file.create("abs", [fft_name_str])
        entry_dict = self.data_file.store.layout_entry(signal)
        self.assertEqual(entry_dict, {"name": "abs_Torque",
                                      "operation": "abs",
                                      "signals": ["Torque"],
                                      "parameter": None})

    @covers("LLFR-00248", "LLFR-00249", "LLFR-00240", "HLFR-00057",
            "HLFR-00058")
    def test_fft_signal_holds_its_frequencies(self) -> None:
        """An FFT signal holds frequencies and its time range.

        Inputs: none.
        Outputs: none.
        """
        signal = self.data_file.create("fft", ["Torque"], (1.0, 2.99))
        self.assertEqual(signal.name_str, "fft_1s_to_2.99s_Torque")
        self.assertTrue(signal.is_fft_b)
        self.assertEqual(signal.parameter, (1.0, 2.99))
        self.assertEqual(signal.frequency_array.size,
                         signal.value_array.size)
        peak_i = int(np.argmax(signal.value_array))
        self.assertAlmostEqual(signal.frequency_array[peak_i], 1.0)
        self.assertLess(abs(signal.value_array[peak_i] - 1.0), 0.05)
        self.assertTrue(self.data_file.store.is_fft(signal.name_str))
        self.assertFalse(self.data_file.store.is_fft("Torque"))

    @covers("LLFR-00251", "LLFR-00275")
    def test_fft_signal_cannot_be_a_source(self) -> None:
        """No operation, not even a product, can use an FFT signal.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.data_file.create("fft", ["Speed"],
                                             (0.0, 1.0)).name_str
        with self.assertRaises(SyntheticSourceError):
            self.data_file.create("integral", [fft_name_str])
        with self.assertRaises(SyntheticSourceError):
            self.data_file.create("product", ["Speed", fft_name_str])
        with self.assertRaises(SyntheticSourceError):
            self.data_file.create("fft", [fft_name_str], (0.0, 1.0))
        self.assertEqual(self.data_file.store.names(), [fft_name_str])

    @covers("LLFR-00262")
    def test_missing_source_and_wrong_source_count(self) -> None:
        """A missing source or a wrong number of sources is rejected.

        Inputs: none.
        Outputs: none.
        """
        with self.assertRaises(SyntheticSourceError) as context:
            self.data_file.create("integral", ["Pressure"])
        self.assertIn("Pressure", str(context.exception))
        with self.assertRaises(SyntheticEntryError):
            self.data_file.create("product", ["Speed"])
        with self.assertRaises(SyntheticEntryError):
            self.data_file.create("integral", ["Speed", "Torque"])
        with self.assertRaises(SyntheticOperationError):
            self.data_file.create("square", ["Speed"])

    @covers("LLFR-00245", "LLFR-00247", "LLFR-00250", "LLFR-00269",
            "LLFR-00272")
    def test_failed_creation_leaves_the_store_unchanged(self) -> None:
        """Every rejected creation raises and adds nothing.

        Inputs: none.
        Outputs: none.
        """
        case_list = [
            ("lowpass", (50.0, 2, "zero"), SyntheticParameterError),
            ("highpass", (0.0, 2, "zero"), SyntheticParameterError),
            ("highpass", (1.0, 2, "late"), SyntheticParameterError),
            ("highpass", (1.0, 2), SyntheticParameterError),
            ("highpass", (1.0, 9, "zero"), SyntheticParameterError),
            ("lowpass", 1.0, SyntheticParameterError),
            ("movingaverage", 1, SyntheticParameterError),
            ("movingaverage", 1002, SyntheticParameterError),
            ("divide", 0.0, SyntheticParameterError),
            ("greater", "a", SyntheticParameterError),
            ("integral", 3.0, SyntheticParameterError),
            ("fft", (0.0, 0.05), TooFewSamplesError),
        ]
        for operation_str, parameter, error_type in case_list:
            with self.assertRaises(error_type):
                self.data_file.create(operation_str, ["Speed"], parameter)
        self.assertEqual(self.data_file.store.names(), [])
        uneven_time_array = self.data_file.time_array.copy()
        uneven_time_array[500:] += 0.005
        uneven_file = DataFile(uneven_time_array)
        for operation_str, parameter in (("lowpass", (1.0, 2, "zero")),
                                         ("highpass",
                                          (1.0, 2, "first_value")),
                                         ("fft", (0.0, 10.0))):
            with self.assertRaises(UnevenTimeStepError):
                uneven_file.create(operation_str, ["Speed"], parameter)
        uneven_file.create("integral", ["Speed"])
        uneven_file.create("movingaverage", ["Speed"], 3)
        self.assertEqual(uneven_file.store.names(),
                         ["int_Speed", "mavg_3samples_Speed"])

    @covers("LLFR-00252")
    def test_clear_removes_every_signal(self) -> None:
        """clear removes every synthetic signal.

        Inputs: none.
        Outputs: none.
        """
        self.data_file.create("integral", ["Speed"])
        self.data_file.create("max", ["int_Speed"])
        self.data_file.store.clear()
        self.assertEqual(self.data_file.store.names(), [])
        self.assertFalse(self.data_file.store.contains("int_Speed"))
        with self.assertRaises(KeyError):
            self.data_file.store.get("int_Speed")
        again = self.data_file.create("integral", ["Speed"])
        self.assertEqual(again.name_str, "int_Speed")


class StoreDeleteTest(unittest.TestCase):
    """Check dependents and the delete cascade."""

    def setUp(self) -> None:
        """Create a chain and a branch of synthetic signals.

        Signals, in creation order:
        int_Speed, add_1_Torque, der_int_Speed,
        add_1_Torque_prod_der_int_Speed, max_Speed,
        fft_0s_to_10s_der_int_Speed.

        Inputs: none.
        Outputs: none.
        """
        self.data_file = DataFile()
        self.data_file.create("integral", ["Speed"])
        self.data_file.create("add", ["Torque"], 1.0)
        self.data_file.create("derivative", ["int_Speed"])
        self.data_file.create("product", ["add_1_Torque",
                                          "der_int_Speed"])
        self.data_file.create("max", ["Speed"])
        self.data_file.create("fft", ["der_int_Speed"],
                              (0.0, 10.0))

    @covers("LLFR-00255")
    def test_dependents_direct_and_indirect_in_order(self) -> None:
        """dependents lists direct and indirect dependents in order.

        Inputs: none.
        Outputs: none.
        """
        store = self.data_file.store
        self.assertEqual(store.dependents("int_Speed"), [
            "der_int_Speed",
            "add_1_Torque_prod_der_int_Speed",
            "fft_0s_to_10s_der_int_Speed"])
        self.assertEqual(store.dependents("add_1_Torque"), [
            "add_1_Torque_prod_der_int_Speed"])
        self.assertEqual(store.dependents("max_Speed"), [])
        self.assertEqual(store.dependents("Speed"), [
            "int_Speed", "der_int_Speed",
            "add_1_Torque_prod_der_int_Speed", "max_Speed",
            "fft_0s_to_10s_der_int_Speed"])

    @covers("LLFR-00255", "HLFR-00059")
    def test_delete_removes_the_signal_and_its_dependents(self) -> None:
        """delete removes the signal and every dependent, and lists them.

        Inputs: none.
        Outputs: none.
        """
        store = self.data_file.store
        removed_list = store.delete("int_Speed")
        self.assertEqual(removed_list, [
            "int_Speed", "der_int_Speed",
            "add_1_Torque_prod_der_int_Speed",
            "fft_0s_to_10s_der_int_Speed"])
        self.assertEqual(store.names(), ["add_1_Torque", "max_Speed"])
        self.assertEqual(store.delete("max_Speed"), ["max_Speed"])
        self.assertEqual(store.names(), ["add_1_Torque"])
        with self.assertRaises(KeyError):
            store.delete("Speed")
        with self.assertRaises(KeyError):
            store.delete("int_Speed")


class StoreRenameTest(unittest.TestCase):
    """Check renaming synthetic signals."""

    def setUp(self) -> None:
        """Create int_Speed and der_int_Speed.

        Inputs: none.
        Outputs: none.
        """
        self.data_file = DataFile()
        self.data_file.create("integral", ["Speed"])
        self.data_file.create("derivative", ["int_Speed"])
        self.data_file.create("product", ["int_Speed",
                                          "int_Speed"])

    def rename(self, old_name_str: str, new_name_str: str) -> str:
        """Rename a synthetic signal of the data file.

        Inputs:
            old_name_str: its current name.
            new_name_str: the typed name.
        Outputs: the stored name.
        """
        return self.data_file.store.rename(
            old_name_str, new_name_str, self.data_file.data_name_set())

    @covers("LLFR-00266", "HLFR-00060")
    def test_rename_keeps_dependent_names_and_updates_sources(
            self) -> None:
        """Dependents keep their names; their sources follow the rename.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.rename("int_Speed", "  Distance "),
                         "Distance")
        store = self.data_file.store
        self.assertEqual(store.names(), [
            "Distance", "der_int_Speed",
            "int_Speed_prod_int_Speed"])
        self.assertEqual(store.get("der_int_Speed")
                         .source_name_list, ["Distance"])
        self.assertEqual(store.get("int_Speed_prod_int_Speed")
                         .source_name_list, ["Distance", "Distance"])
        self.assertEqual(store.dependents("Distance"), [
            "der_int_Speed",
            "int_Speed_prod_int_Speed"])

    @covers("LLFR-00266", "LLFR-00240")
    def test_new_signals_use_the_new_name(self) -> None:
        """Signals created after the rename use the new name.

        Inputs: none.
        Outputs: none.
        """
        self.rename("int_Speed", "Distance")
        signal = self.data_file.create("max", ["Distance"])
        self.assertEqual(signal.name_str, "max_Distance")
        with self.assertRaises(SyntheticSourceError):
            self.data_file.create("max", ["int_Speed"])

    @covers("LLFR-00267")
    def test_empty_name_is_rejected_silently(self) -> None:
        """An empty or blank name raises EmptySyntheticNameError.

        Inputs: none.
        Outputs: none.
        """
        for name_str in ("", "   ", "\t"):
            with self.assertRaises(EmptySyntheticNameError):
                self.rename("int_Speed", name_str)
        self.assertIn("int_Speed", self.data_file.store.names())

    @covers("LLFR-00267")
    def test_name_in_use_is_rejected(self) -> None:
        """A data file or synthetic name in use raises NameInUseError.

        Inputs: none.
        Outputs: none.
        """
        for name_str in ("Speed", " Time ", "der_int_Speed"):
            with self.assertRaises(SyntheticNameInUseError) as context:
                self.rename("int_Speed", name_str)
            self.assertIn("already exists", str(context.exception))
        self.assertEqual(self.data_file.store.get(
            "der_int_Speed").source_name_list,
            ["int_Speed"])
        # LLFR-00267: names are compared exactly.
        self.assertEqual(self.rename("int_Speed", "speed"), "speed")

    @covers("LLFR-00267")
    def test_own_name_is_not_a_conflict(self) -> None:
        """Entering the signal's own name changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.rename("int_Speed", " int_Speed"),
                         "int_Speed")
        with self.assertRaises(KeyError):
            self.rename("Speed", "Velocity")


class LayoutEntryTest(unittest.TestCase):
    """Check layout file entries, equations and their rebuild."""

    def setUp(self) -> None:
        """Create one signal of each parameter kind.

        Inputs: none.
        Outputs: none.
        """
        self.data_file = DataFile()
        self.data_file.create("lowpass", ["Speed"], (2.5, 4, "zero"))
        self.data_file.create("movingaverage", ["Torque"], 4)
        self.data_file.create("greaterorequal", ["lpf_2.5Hz_order4_Speed"],
                              0.1 + 0.2)
        self.data_file.create("product", ["lpf_2.5Hz_order4_Speed",
                                          "mavg_4samples_Torque"])
        self.data_file.create("fft", ["lpf_2.5Hz_order4_Speed"],
                              (0.1 + 0.2, 3.0))
        self.data_file.create("integral", ["Torque"])

    @covers("LLFR-00225", "LLFR-00227", "LLFR-00283", "HLFR-00056")
    def test_layout_entries_hold_name_operation_signals_parameter(
            self) -> None:
        """Each entry holds the current name, operation, signals, param.

        Inputs: none.
        Outputs: none.
        """
        self.data_file.store.rename("lpf_2.5Hz_order4_Speed", "Smooth",
                                    self.data_file.data_name_set())
        entry_list = self.data_file.store.layout_entries()
        self.assertEqual(entry_list[0], {
            "name": "Smooth", "operation": "lowpass",
            "signals": ["Speed"],
            "parameter": {"cutoff": 2.5, "order": 4,
                          "start": "zero"}})
        self.assertEqual(entry_list[1]["parameter"], 4)
        self.assertIsInstance(entry_list[1]["parameter"], int)
        self.assertEqual(entry_list[2]["signals"], ["Smooth"])
        self.assertEqual(entry_list[3]["signals"],
                         ["Smooth", "mavg_4samples_Torque"])
        self.assertIsNone(entry_list[3]["parameter"])
        # LLFR-00283: the FFT signal is not in the layout file.
        self.assertEqual(len(entry_list), 5)
        self.assertNotIn("fft", [entry["operation"]
                                 for entry in entry_list])
        self.assertEqual(entry_list[4]["name"], "int_Torque")
        self.assertIsNone(entry_list[4]["parameter"])
        self.assertEqual(LAYOUT_KEY_STR, "synthetic_signals")
        # LLFR-00225 item 10: the filter order is a whole number.
        self.assertIsInstance(entry_list[0]["parameter"]["order"], int)

    @covers("LLFR-00227")
    def test_entries_text_is_indented_json_with_exact_times(self) -> None:
        """The JSON text is indented by 2 and reads back exact times.

        Inputs: none.
        Outputs: none.
        """
        text_str = entries_text(self.data_file.store.layout_entries())
        self.assertTrue(text_str.startswith('[\n  {\n    "name": '))
        self.assertIn('"parameter": 0.30000000000000004', text_str)
        read_list = json.loads(text_str)
        self.assertEqual(read_list[2]["parameter"], 0.1 + 0.2)
        self.assertEqual(read_list, self.data_file.store.layout_entries())

    @covers("LLFR-00279", "HLFR-00062")
    def test_equation_entries_hold_the_signal_and_its_ancestors(
            self) -> None:
        """The equation lists the signal and all synthetic ancestors.

        Inputs: none.
        Outputs: none.
        """
        store = self.data_file.store
        name_list = [entry["name"] for entry in store.equation_entries(
            "lpf_2.5Hz_order4_Speed_prod_mavg_4samples_Torque")]
        self.assertEqual(name_list, [
            "lpf_2.5Hz_order4_Speed", "mavg_4samples_Torque",
            "lpf_2.5Hz_order4_Speed_prod_mavg_4samples_Torque"])
        self.assertEqual([entry["name"] for entry in
                          store.equation_entries("int_Torque")],
                         ["int_Torque"])
        text_str = store.equation_text("ge_0.3_lpf_2.5Hz_order4_Speed")
        self.assertEqual(json.loads(text_str),
                         store.equation_entries(
                             "ge_0.3_lpf_2.5Hz_order4_Speed"))
        with self.assertRaises(KeyError):
            store.equation_entries("Speed")

    @covers("LLFR-00262", "LLFR-00279", "HLFR-00056")
    def test_equation_rebuilds_the_same_values(self) -> None:
        """Pasting an equation into a new store rebuilds equal values.

        Inputs: none.
        Outputs: none.
        """
        old_store = self.data_file.store
        # LLFR-00278: FFT signals have no equation (LLFR-00283).
        for name_str in [name_str for name_str in old_store.names()
                         if not old_store.is_fft(name_str)]:
            entry_list = json.loads(old_store.equation_text(name_str))
            new_file = DataFile()
            for entry_dict in entry_list:
                new_file.create_from_entry(entry_dict)
            rebuilt = new_file.store.get(name_str)
            original = old_store.get(name_str)
            np.testing.assert_allclose(rebuilt.value_array,
                                       original.value_array)
            self.assertEqual(rebuilt.parameter, original.parameter)

    @covers("LLFR-00262", "LLFR-00225")
    def test_layout_round_trip_keeps_renamed_names(self) -> None:
        """All entries rebuild with their saved, renamed names.

        Inputs: none.
        Outputs: none.
        """
        store = self.data_file.store
        store.rename("lpf_2.5Hz_order4_Speed", "Smooth",
                     self.data_file.data_name_set())
        text_str = entries_text(store.layout_entries())
        new_file = DataFile()
        for entry_dict in json.loads(text_str):
            new_file.create_from_entry(entry_dict)
        # LLFR-00283: every signal but the FFT signal.
        self.assertEqual(new_file.store.names(),
                         [name_str for name_str in store.names()
                          if not store.is_fft(name_str)])
        self.assertEqual(new_file.store.layout_entries(),
                         store.layout_entries())

    @covers("LLFR-00262", "LLFR-00283")
    def test_fft_entries_are_not_created(self) -> None:
        """An FFT entry is never created from a layout file.

        Inputs: none.
        Outputs: none.
        """
        names_before_list = self.data_file.store.names()
        for parameter in ({"start": 0.0, "end": 5.0}, None, [0, 1]):
            with self.assertRaises(SyntheticEntryError) as context:
                self.data_file.create_from_entry({
                    "name": "my_fft", "operation": "fft",
                    "signals": ["Speed"], "parameter": parameter})
            self.assertEqual(str(context.exception),
                             "FFT signals are not loaded from layout "
                             "files.")
        self.assertEqual(self.data_file.store.names(), names_before_list)

    @covers("LLFR-00262", "LLFR-00237")
    def test_entries_that_cannot_be_rebuilt(self) -> None:
        """Each reason of LLFR-00262 raises with a sentence.

        Inputs: none.
        Outputs: none.
        """
        new_file = DataFile()
        valid_dict = {"name": "x", "operation": "integral",
                      "signals": ["Speed"], "parameter": None}
        case_list = [
            (dict(valid_dict, signals=["Pressure"]), SyntheticSourceError),
            (dict(valid_dict, name="Speed"), SyntheticNameInUseError),
            (dict(valid_dict, operation="lowpass",
                  parameter={"cutoff": 60.0, "order": 2,
                             "start": "zero"}),
             SyntheticParameterError),
            (dict(valid_dict, operation="lowpass",
                  parameter={"cutoff": 1.0, "order": 0,
                             "start": "zero"}),
             SyntheticParameterError),
            (dict(valid_dict, operation="lowpass",
                  parameter={"cutoff": 1.0, "order": 2.5,
                             "start": "zero"}),
             SyntheticParameterError),
            (dict(valid_dict, operation="lowpass",
                  parameter={"cutoff": 1.0, "order": 2,
                             "start": "now"}),
             SyntheticParameterError),
            (dict(valid_dict, operation="lowpass",
                  parameter={"cutoff": 1.0, "order": 2}),
             SyntheticEntryError),
            (dict(valid_dict, operation="lowpass", parameter=1.0),
             SyntheticEntryError),
            (dict(valid_dict, operation="highpass",
                  parameter={"cutoff": 1.0}), SyntheticEntryError),
            (dict(valid_dict, operation="movingaverage", parameter=1.5),
             SyntheticParameterError),
            (dict(valid_dict, operation="divide", parameter=0),
             SyntheticParameterError),
            (dict(valid_dict, operation="greater", parameter="1"),
             SyntheticParameterError),
            (dict(valid_dict, operation="fft",
                  parameter={"start": 0.0, "end": 5.0}),
             SyntheticEntryError),
            (dict(valid_dict, operation="fft", parameter=[0.0, 1.0]),
             SyntheticEntryError),
            (dict(valid_dict, operation="fft", parameter={"start": 0.0}),
             SyntheticEntryError),
            (dict(valid_dict, operation="cube"), SyntheticOperationError),
            (dict(valid_dict, name=""), SyntheticEntryError),
            (dict(valid_dict, name=3), SyntheticEntryError),
            (dict(valid_dict, signals="Speed"), SyntheticEntryError),
            (dict(valid_dict, signals=[1]), SyntheticEntryError),
            ({"name": "x", "signals": ["Speed"]}, SyntheticEntryError),
            (["x", "integral"], SyntheticEntryError),
        ]
        for entry, error_type in case_list:
            with self.assertRaises(error_type, msg=repr(entry)) as context:
                new_file.create_from_entry(entry)
            self.assertIsInstance(context.exception, SyntheticSignalError)
            self.assertTrue(str(context.exception).endswith("."))
        self.assertEqual(new_file.store.names(), [])
        uneven_time_array = np.arange(1001) / 100.0
        uneven_time_array[500:] += 0.005
        uneven_file = DataFile(uneven_time_array)
        with self.assertRaises(UnevenTimeStepError):
            uneven_file.create_from_entry(dict(
                valid_dict, operation="highpass",
                parameter={"cutoff": 1.0, "order": 2, "start": "zero"}))

    @covers("LLFR-00262")
    def test_duplicate_saved_name_and_fft_source(self) -> None:
        """A saved name used twice, or an FFT source, is rejected.

        Inputs: none.
        Outputs: none.
        """
        new_file = DataFile()
        fft_name_str = new_file.create("fft", ["Speed"],
                                       (0.0, 1.0)).name_str
        new_file.create_from_entry({"name": "a", "operation": "max",
                                    "signals": ["Speed"]})
        with self.assertRaises(SyntheticNameInUseError):
            new_file.create_from_entry({"name": "a", "operation": "min",
                                        "signals": ["Speed"]})
        with self.assertRaises(SyntheticSourceError):
            new_file.create_from_entry({"name": "b", "operation": "max",
                                        "signals": [fft_name_str]})
        signal = new_file.create_from_entry({
            "name": "c", "operation": "movingaverage",
            "signals": ["Speed"], "parameter": 3.0})
        self.assertEqual(signal.parameter, 3)
        self.assertEqual(new_file.store.names(), [fft_name_str, "a", "c"])

    @covers("LLFR-00225", "LLFR-00227", "LLFR-00246", "LLFR-00262")
    def test_filter_entries_round_trip_with_both_starts(self) -> None:
        """Cutoff, order and start are saved and rebuilt exactly.

        Inputs: none.
        Outputs: none.
        """
        source_file = DataFile()
        source_file.create("lowpass", ["Speed"], (2.5, 3, "zero"))
        source_file.create("highpass", ["Speed"], (0.5, 1, "first_value"))
        entry_list = json.loads(entries_text(
            source_file.store.layout_entries()))
        self.assertEqual([entry["parameter"] for entry in entry_list], [
            {"cutoff": 2.5, "order": 3, "start": "zero"},
            {"cutoff": 0.5, "order": 1, "start": "first_value"}])
        new_file = DataFile()
        for entry_dict in entry_list:
            new_file.create_from_entry(entry_dict)
        for name_str in ("lpf_2.5Hz_order3_Speed",
                         "hpf_0.5Hz_order1_Speed"):
            np.testing.assert_array_equal(
                new_file.store.get(name_str).value_array,
                source_file.store.get(name_str).value_array)
        self.assertEqual(
            new_file.store.get("lpf_2.5Hz_order3_Speed").parameter,
            (2.5, 3, "zero"))

    @covers("LLFR-00262", "LLFR-00267")
    def test_saved_name_is_kept_without_outer_spaces(self) -> None:
        """A saved name with outer spaces is stored trimmed, as rename.

        Inputs: none.
        Outputs: none.
        """
        new_file = DataFile()
        signal = new_file.create_from_entry({
            "name": "  Smooth speed ", "operation": "lowpass",
            "signals": ["Speed"],
            "parameter": {"cutoff": 2.0, "order": 3.0,
                          "start": "first_value"}})
        self.assertEqual(signal.name_str, "Smooth speed")
        self.assertEqual(signal.parameter, (2.0, 3, "first_value"))
        self.assertEqual(new_file.store.names(), ["Smooth speed"])
        with self.assertRaises(SyntheticNameInUseError):
            new_file.create_from_entry({"name": " Speed ",
                                        "operation": "max",
                                        "signals": ["Speed"]})
        with self.assertRaises(SyntheticNameInUseError):
            new_file.create_from_entry({"name": "Smooth speed  ",
                                        "operation": "max",
                                        "signals": ["Speed"]})


if __name__ == "__main__":
    unittest.main()
