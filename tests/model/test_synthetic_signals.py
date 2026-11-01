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
    """Check synthetic_name."""

    @covers("LLFR-00240", "HLFR-00054")
    def test_operation_underscore_source(self) -> None:
        """Names are <operation>_<source>, built up left to right.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(synthetic_name("integral", ["Speed"], None,
                                        set()), "integral_Speed")
        self.assertEqual(synthetic_name("derivative", ["integral_Speed"],
                                        None, set()),
                         "derivative_integral_Speed")
        self.assertEqual(synthetic_name("movingaverage", ["a b"], None,
                                        set()), "movingaverage_a b")

    @covers("LLFR-00240", "HLFR-00054")
    def test_product_names_both_signals(self) -> None:
        """A product is named product_<first>_<second>.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(synthetic_name("product", ["Speed", "Torque"],
                                        None, set()),
                         "product_Speed_Torque")
        self.assertEqual(synthetic_name("product", ["Speed", "Speed"],
                                        None, set()),
                         "product_Speed_Speed")

    @covers("LLFR-00240", "LLFR-00043", "HLFR-00054", "HLFR-00057")
    def test_fft_name_shows_the_time_range(self) -> None:
        """FFT names end with _<start>s_to_<end>s in the tip format.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(synthetic_name("fft", ["lowpass_Speed"],
                                        (1.5, 3.0), set()),
                         "fft_lowpass_Speed_1.5s_to_3s")
        self.assertEqual(synthetic_name("fft", ["Speed"],
                                        (0.1 + 0.2, 12.3456789), set()),
                         "fft_Speed_0.3s_to_12.3457s")
        self.assertNotEqual(
            synthetic_name("fft", ["Speed"], (0.0, 1.0), set()),
            synthetic_name("fft", ["Speed"], (0.0, 2.0), set()))

    @covers("LLFR-00241")
    def test_used_name_gets_the_smallest_free_number(self) -> None:
        """A used name gets _2, _3, ... the smallest unused number.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(synthetic_name("lowpass", ["Speed"], None,
                                        {"lowpass_Speed"}),
                         "lowpass_Speed_2")
        self.assertEqual(synthetic_name(
            "lowpass", ["Speed"], None,
            {"lowpass_Speed", "lowpass_Speed_2", "lowpass_Speed_4"}),
            "lowpass_Speed_3")
        self.assertEqual(synthetic_name("lowpass", ["Speed"], None,
                                        {"lowpass_Speed_2"}),
                         "lowpass_Speed")


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
                                           ["integral_Speed"])
        self.assertEqual(self.data_file.store.names(),
                         ["integral_Speed", "derivative_integral_Speed"])
        time_array = self.data_file.time_array
        np.testing.assert_allclose(integral.value_array,
                                   time_array ** 2 + time_array)
        np.testing.assert_allclose(derivative.value_array[1:-1],
                                   2.0 * time_array[1:-1] + 1.0)
        self.assertEqual(integral.source_name_list, ["Speed"])
        self.assertIsNone(integral.parameter)
        self.assertIsNone(integral.frequency_array)
        self.assertFalse(integral.is_fft_b)
        self.assertIs(self.data_file.store.get("integral_Speed"), integral)
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
        """Filtering twice gives lowpass_Speed and lowpass_Speed_2.

        Inputs: none.
        Outputs: none.
        """
        self.data_file.create("lowpass", ["Speed"], (1.0, 2, "zero"))
        second = self.data_file.create("lowpass", ["Speed"],
                                       (2.0, 2, "first_value"))
        self.assertEqual(second.name_str, "lowpass_Speed_2")
        self.assertEqual(second.parameter, (2.0, 2, "first_value"))

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
        signal = self.data_file.create("product", ["Speed", "add_Speed"])
        self.assertEqual(signal.name_str, "product_Speed_add_Speed")
        speed_array = self.data_file.signal_dict["Speed"]
        np.testing.assert_allclose(signal.value_array,
                                   speed_array * (speed_array + 1.0))
        self.assertEqual(signal.source_name_list, ["Speed", "add_Speed"])
        square = self.data_file.create("product", ["Speed", "Speed"])
        np.testing.assert_allclose(square.value_array, speed_array ** 2)

    @covers("LLFR-00248", "LLFR-00249", "LLFR-00240", "HLFR-00057",
            "HLFR-00058")
    def test_fft_signal_holds_its_frequencies(self) -> None:
        """An FFT signal holds frequencies and its time range.

        Inputs: none.
        Outputs: none.
        """
        signal = self.data_file.create("fft", ["Torque"], (1.0, 2.99))
        self.assertEqual(signal.name_str, "fft_Torque_1s_to_2.99s")
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
                         ["integral_Speed", "movingaverage_Speed"])

    @covers("LLFR-00252")
    def test_clear_removes_every_signal(self) -> None:
        """clear removes every synthetic signal.

        Inputs: none.
        Outputs: none.
        """
        self.data_file.create("integral", ["Speed"])
        self.data_file.create("max", ["integral_Speed"])
        self.data_file.store.clear()
        self.assertEqual(self.data_file.store.names(), [])
        self.assertFalse(self.data_file.store.contains("integral_Speed"))
        with self.assertRaises(KeyError):
            self.data_file.store.get("integral_Speed")
        again = self.data_file.create("integral", ["Speed"])
        self.assertEqual(again.name_str, "integral_Speed")


class StoreDeleteTest(unittest.TestCase):
    """Check dependents and the delete cascade."""

    def setUp(self) -> None:
        """Create a chain and a branch of synthetic signals.

        Signals, in creation order:
        integral_Speed, add_Torque, derivative_integral_Speed,
        product_add_Torque_derivative_integral_Speed, max_Speed,
        fft_derivative_integral_Speed_0s_to_10s.

        Inputs: none.
        Outputs: none.
        """
        self.data_file = DataFile()
        self.data_file.create("integral", ["Speed"])
        self.data_file.create("add", ["Torque"], 1.0)
        self.data_file.create("derivative", ["integral_Speed"])
        self.data_file.create("product", ["add_Torque",
                                          "derivative_integral_Speed"])
        self.data_file.create("max", ["Speed"])
        self.data_file.create("fft", ["derivative_integral_Speed"],
                              (0.0, 10.0))

    @covers("LLFR-00255")
    def test_dependents_direct_and_indirect_in_order(self) -> None:
        """dependents lists direct and indirect dependents in order.

        Inputs: none.
        Outputs: none.
        """
        store = self.data_file.store
        self.assertEqual(store.dependents("integral_Speed"), [
            "derivative_integral_Speed",
            "product_add_Torque_derivative_integral_Speed",
            "fft_derivative_integral_Speed_0s_to_10s"])
        self.assertEqual(store.dependents("add_Torque"), [
            "product_add_Torque_derivative_integral_Speed"])
        self.assertEqual(store.dependents("max_Speed"), [])
        self.assertEqual(store.dependents("Speed"), [
            "integral_Speed", "derivative_integral_Speed",
            "product_add_Torque_derivative_integral_Speed", "max_Speed",
            "fft_derivative_integral_Speed_0s_to_10s"])

    @covers("LLFR-00255", "HLFR-00059")
    def test_delete_removes_the_signal_and_its_dependents(self) -> None:
        """delete removes the signal and every dependent, and lists them.

        Inputs: none.
        Outputs: none.
        """
        store = self.data_file.store
        removed_list = store.delete("integral_Speed")
        self.assertEqual(removed_list, [
            "integral_Speed", "derivative_integral_Speed",
            "product_add_Torque_derivative_integral_Speed",
            "fft_derivative_integral_Speed_0s_to_10s"])
        self.assertEqual(store.names(), ["add_Torque", "max_Speed"])
        self.assertEqual(store.delete("max_Speed"), ["max_Speed"])
        self.assertEqual(store.names(), ["add_Torque"])
        with self.assertRaises(KeyError):
            store.delete("Speed")
        with self.assertRaises(KeyError):
            store.delete("integral_Speed")


class StoreRenameTest(unittest.TestCase):
    """Check renaming synthetic signals."""

    def setUp(self) -> None:
        """Create integral_Speed and derivative_integral_Speed.

        Inputs: none.
        Outputs: none.
        """
        self.data_file = DataFile()
        self.data_file.create("integral", ["Speed"])
        self.data_file.create("derivative", ["integral_Speed"])
        self.data_file.create("product", ["integral_Speed",
                                          "integral_Speed"])

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
        self.assertEqual(self.rename("integral_Speed", "  Distance "),
                         "Distance")
        store = self.data_file.store
        self.assertEqual(store.names(), [
            "Distance", "derivative_integral_Speed",
            "product_integral_Speed_integral_Speed"])
        self.assertEqual(store.get("derivative_integral_Speed")
                         .source_name_list, ["Distance"])
        self.assertEqual(store.get("product_integral_Speed_integral_Speed")
                         .source_name_list, ["Distance", "Distance"])
        self.assertEqual(store.dependents("Distance"), [
            "derivative_integral_Speed",
            "product_integral_Speed_integral_Speed"])

    @covers("LLFR-00266", "LLFR-00240")
    def test_new_signals_use_the_new_name(self) -> None:
        """Signals created after the rename use the new name.

        Inputs: none.
        Outputs: none.
        """
        self.rename("integral_Speed", "Distance")
        signal = self.data_file.create("max", ["Distance"])
        self.assertEqual(signal.name_str, "max_Distance")
        with self.assertRaises(SyntheticSourceError):
            self.data_file.create("max", ["integral_Speed"])

    @covers("LLFR-00267")
    def test_empty_name_is_rejected_silently(self) -> None:
        """An empty or blank name raises EmptySyntheticNameError.

        Inputs: none.
        Outputs: none.
        """
        for name_str in ("", "   ", "\t"):
            with self.assertRaises(EmptySyntheticNameError):
                self.rename("integral_Speed", name_str)
        self.assertIn("integral_Speed", self.data_file.store.names())

    @covers("LLFR-00267")
    def test_name_in_use_is_rejected(self) -> None:
        """A data file or synthetic name in use raises NameInUseError.

        Inputs: none.
        Outputs: none.
        """
        for name_str in ("Speed", " Time ", "derivative_integral_Speed"):
            with self.assertRaises(SyntheticNameInUseError) as context:
                self.rename("integral_Speed", name_str)
            self.assertIn("already exists", str(context.exception))
        self.assertEqual(self.data_file.store.get(
            "derivative_integral_Speed").source_name_list,
            ["integral_Speed"])
        # LLFR-00267: names are compared exactly.
        self.assertEqual(self.rename("integral_Speed", "speed"), "speed")

    @covers("LLFR-00267")
    def test_own_name_is_not_a_conflict(self) -> None:
        """Entering the signal's own name changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.rename("integral_Speed", " integral_Speed"),
                         "integral_Speed")
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
        self.data_file.create("greaterorequal", ["lowpass_Speed"],
                              0.1 + 0.2)
        self.data_file.create("product", ["lowpass_Speed",
                                          "movingaverage_Torque"])
        self.data_file.create("fft", ["lowpass_Speed"], (0.1 + 0.2, 3.0))
        self.data_file.create("integral", ["Torque"])

    @covers("LLFR-00225", "LLFR-00227", "LLFR-00283", "HLFR-00056")
    def test_layout_entries_hold_name_operation_signals_parameter(
            self) -> None:
        """Each entry holds the current name, operation, signals, param.

        Inputs: none.
        Outputs: none.
        """
        self.data_file.store.rename("lowpass_Speed", "Smooth",
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
                         ["Smooth", "movingaverage_Torque"])
        self.assertIsNone(entry_list[3]["parameter"])
        # LLFR-00283: the FFT signal is not in the layout file.
        self.assertEqual(len(entry_list), 5)
        self.assertNotIn("fft", [entry["operation"]
                                 for entry in entry_list])
        self.assertEqual(entry_list[4]["name"], "integral_Torque")
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
            "product_lowpass_Speed_movingaverage_Torque")]
        self.assertEqual(name_list, [
            "lowpass_Speed", "movingaverage_Torque",
            "product_lowpass_Speed_movingaverage_Torque"])
        self.assertEqual([entry["name"] for entry in
                          store.equation_entries("integral_Torque")],
                         ["integral_Torque"])
        text_str = store.equation_text("greaterorequal_lowpass_Speed")
        self.assertEqual(json.loads(text_str),
                         store.equation_entries(
                             "greaterorequal_lowpass_Speed"))
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
        store.rename("lowpass_Speed", "Smooth",
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
        for name_str in ("lowpass_Speed", "highpass_Speed"):
            np.testing.assert_array_equal(
                new_file.store.get(name_str).value_array,
                source_file.store.get(name_str).value_array)
        self.assertEqual(new_file.store.get("lowpass_Speed").parameter,
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
