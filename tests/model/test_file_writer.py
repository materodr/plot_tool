"""Tests for model.file_writer: saving the signals to a data file
(HLFR-00090, issue #153).

Every format is written with the writer and read back with the app's
own loader (model.file_loader), which must find the same signals, with
the names of LLFR-00403 and LLFR-00407, and exactly the same values.
HDF5 files need h5py; those tests are skipped when it is missing.
"""

import os
import tempfile
import unittest
from unittest import mock

import numpy as np

from tests.support import covers, requires_h5py

from model import file_writer
from model.file_loader import load_signal_file
from model.file_writer import (
    CSV_FORMAT_STR, EXCEL_FORMAT_STR, HDF5_FORMAT_STR, MAT_FORMAT_STR,
    SignalWriteError, changed_name_list, changed_names_text,
    ensure_format_extension, excel_limit_reason, format_of_path,
    proposed_file_name, saved_name_list, signal_file_bytes)

# LLFR-00402: values whose text form is easy to get wrong.
TRICKY_VALUE_TUPLE = (1.0 / 3.0, 0.1, 1e-300, -2.5e17, 123456789.12345679,
                      2.0 ** -1074, 1.7976931348623157e308, -7.0, 0.0,
                      0.1 + 0.2, 1.0 - 2.0 ** -53)
EXTENSION_DICT = {CSV_FORMAT_STR: ".csv", EXCEL_FORMAT_STR: ".xlsx",
                  MAT_FORMAT_STR: ".mat", HDF5_FORMAT_STR: ".h5"}
LOCAL_FORMAT_TUPLE = (CSV_FORMAT_STR, EXCEL_FORMAT_STR, MAT_FORMAT_STR)


def sample_signals(sample_count_i: int = 20) -> tuple:
    """Return a time signal and two other signals with tricky values.

    Inputs:
        sample_count_i: the number of samples (at least the number of
            TRICKY_VALUE_TUPLE).
    Outputs: (name_list, array_list), the time signal "Time" first.
    """
    time_array = np.arange(sample_count_i, dtype=np.float64) * 0.001
    random_array = np.random.default_rng(153).normal(
        size=sample_count_i) * 1e3
    tricky_array = np.resize(np.array(TRICKY_VALUE_TUPLE), sample_count_i)
    return (["Time", "random", "tricky"],
            [time_array, random_array, tricky_array])


def save_and_load(folder_str: str, name_list: list, array_list: list,
                  time_name_str: str, format_str: str) -> tuple:
    """Save signals with the writer and open the file with the loader.

    Inputs:
        folder_str: the folder of the file.
        name_list: the names in the app.
        array_list: the samples.
        time_name_str: the time signal.
        format_str: the format.
    Outputs: (saved name list, the SignalFile read back).
    """
    new_name_list = saved_name_list(name_list, time_name_str, format_str)
    path_str = os.path.join(folder_str,
                            "saved" + EXTENSION_DICT[format_str])
    with open(path_str, "wb") as output_file:
        output_file.write(signal_file_bytes(new_name_list, array_list,
                                            format_str))
    return new_name_list, load_signal_file(path_str)


class RoundTripTest(unittest.TestCase):
    """Each format reads back as the same signals and values."""

    def assert_same_values(self, expected_array, actual_array) -> None:
        """Check that two signals hold exactly the same float64 values.

        Inputs:
            expected_array: the saved samples.
            actual_array: the samples read back.
        Outputs: none.
        """
        self.assertEqual(actual_array.dtype, np.float64)
        self.assertEqual([repr(value_f) for value_f in
                          np.asarray(expected_array).tolist()],
                         [repr(value_f) for value_f in
                          actual_array.tolist()])

    def check_round_trip(self, format_str: str) -> None:
        """Write and read back the sample signals in one format.

        Inputs:
            format_str: the format.
        Outputs: none.
        """
        name_list, array_list = sample_signals()
        with tempfile.TemporaryDirectory() as folder_str:
            new_name_list, signal_file = save_and_load(
                folder_str, name_list, array_list, "Time", format_str)
        self.assertEqual(new_name_list, name_list)
        self.assertEqual(sorted(signal_file.signal_name_list),
                         sorted(name_list))
        self.assertEqual(signal_file.time_signal_name_str, "Time")
        self.assertFalse(signal_file.needs_time_signal_choice_b)
        for name_str, value_array in zip(name_list, array_list):
            with self.subTest(format=format_str, signal=name_str):
                self.assert_same_values(value_array,
                                        signal_file.signal_array(name_str))
        return signal_file

    @covers("LLFR-00402", "LLFR-00401", "LLFR-00059", "LLFR-00061")
    def test_csv_round_trip(self) -> None:
        """CSV: names in the first row, "," and ".", same order, values
        read back exactly.

        Inputs: none.
        Outputs: none.
        """
        signal_file = self.check_round_trip(CSV_FORMAT_STR)
        self.assertEqual(signal_file.signal_name_list,
                         ["Time", "random", "tricky"])

    @covers("LLFR-00402", "LLFR-00061")
    def test_csv_text_style(self) -> None:
        """The CSV text uses "," as separator and "." as decimal mark.

        Inputs: none.
        Outputs: none.
        """
        content_str = signal_file_bytes(
            ["Time", "a"], [np.array([0.0, 0.5]), np.array([1.25, -3.0])],
            CSV_FORMAT_STR).decode("utf-8")
        self.assertEqual(content_str, "Time,a\n0.0,1.25\n0.5,-3.0\n")

    @covers("LLFR-00402", "LLFR-00401", "LLFR-00059", "LLFR-00060")
    def test_excel_round_trip(self) -> None:
        """Excel: one sheet, same order, values read back exactly.

        Inputs: none.
        Outputs: none.
        """
        import openpyxl
        signal_file = self.check_round_trip(EXCEL_FORMAT_STR)
        self.assertEqual(signal_file.signal_name_list,
                         ["Time", "random", "tricky"])
        name_list, array_list = sample_signals()
        with tempfile.TemporaryDirectory() as folder_str:
            path_str = os.path.join(folder_str, "one_sheet.xlsx")
            with open(path_str, "wb") as output_file:
                output_file.write(signal_file_bytes(
                    name_list, array_list, EXCEL_FORMAT_STR))
            workbook = openpyxl.load_workbook(path_str)
            self.assertEqual(len(workbook.worksheets), 1)
            workbook.close()

    @covers("LLFR-00402", "LLFR-00401", "LLFR-00062", "LLFR-00064")
    def test_mat_round_trip(self) -> None:
        """MAT: version 5 variables, values read back exactly.

        Inputs: none.
        Outputs: none.
        """
        self.check_round_trip(MAT_FORMAT_STR)
        name_list, array_list = sample_signals()
        content_bytes = signal_file_bytes(name_list, array_list,
                                          MAT_FORMAT_STR)
        # LLFR-00064: not a v7.3 (HDF5-based) file.
        self.assertIn(b"MATLAB 5.0 MAT-file", content_bytes[:128])

    @requires_h5py
    @covers("LLFR-00402", "LLFR-00401", "LLFR-00134")
    def test_hdf5_round_trip(self) -> None:
        """HDF5: one 1-D float64 dataset per signal, values read back
        exactly.

        Inputs: none.
        Outputs: none.
        """
        self.check_round_trip(HDF5_FORMAT_STR)

    @covers("LLFR-00402", "LLFR-00403")
    def test_csv_and_excel_names_are_not_changed(self) -> None:
        """Names with ",", quotes, "=", spaces, "/" and other letters are
        written and read back as they are in CSV and Excel.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Time", "a,b", 'say "hi"', "=A1+1", "Engine Speed",
                     "µ/s", "x;y", "5"]
        array_list = [np.arange(4, dtype=np.float64)] + [
            np.arange(4, dtype=np.float64) * (index_i + 1.5)
            for index_i in range(len(name_list) - 1)]
        for format_str in (CSV_FORMAT_STR, EXCEL_FORMAT_STR):
            with tempfile.TemporaryDirectory() as folder_str:
                new_name_list, signal_file = save_and_load(
                    folder_str, name_list, array_list, "Time", format_str)
            with self.subTest(format=format_str):
                self.assertEqual(new_name_list, name_list)
                self.assertEqual(signal_file.signal_name_list, name_list)
                for name_str, value_array in zip(name_list, array_list):
                    self.assert_same_values(
                        value_array, signal_file.signal_array(name_str))

    @covers("LLFR-00402", "LLFR-00403")
    def test_mat_names_read_back(self) -> None:
        """The changed MAT names are the variable names read back.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Time", "engine.speed", "2nd", "_hidden", "L" * 70,
                     "L" * 63 + "x" * 7, "a b", "a_b"]
        array_list = [np.arange(3, dtype=np.float64) * (index_i + 1)
                      for index_i in range(len(name_list))]
        with tempfile.TemporaryDirectory() as folder_str:
            new_name_list, signal_file = save_and_load(
                folder_str, name_list, array_list, "Time", MAT_FORMAT_STR)
        self.assertEqual(new_name_list, [
            "Time", "engine_speed", "x2nd", "x_hidden", "L" * 63,
            "L" * 61 + "_2", "a_b_2", "a_b"])
        self.assertEqual(signal_file.signal_name_list, new_name_list)
        for new_name_str, value_array in zip(new_name_list, array_list):
            self.assert_same_values(value_array,
                                    signal_file.signal_array(new_name_str))

    @requires_h5py
    @covers("LLFR-00402", "LLFR-00403", "LLFR-00134")
    def test_hdf5_names_read_back(self) -> None:
        """HDF5 names with groups are the dataset paths read back.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Time", "engine/speed", "engine", "/lead", "trail/",
                     "a//b", "./x/..", "."]
        array_list = [np.arange(3, dtype=np.float64) * (index_i + 1)
                      for index_i in range(len(name_list))]
        with tempfile.TemporaryDirectory() as folder_str:
            new_name_list, signal_file = save_and_load(
                folder_str, name_list, array_list, "Time", HDF5_FORMAT_STR)
        self.assertEqual(new_name_list, [
            "Time", "engine/speed", "engine_2", "lead", "trail", "a/b",
            "x", "signal"])
        self.assertEqual(sorted(signal_file.signal_name_list),
                         sorted(new_name_list))
        self.assertEqual(signal_file.time_signal_name_str, "Time")
        for new_name_str, value_array in zip(new_name_list, array_list):
            self.assert_same_values(value_array,
                                    signal_file.signal_array(new_name_str))

    @covers("LLFR-00407", "LLFR-00053", "LLFR-00324")
    def test_time_signal_written_as_time(self) -> None:
        """A time signal named "time" is saved as "Time"; "TIME" becomes
        "TIME_2"; the saved file needs no time signal choice.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["time", "TIME", "speed"]
        array_list = [np.arange(5, dtype=np.float64),
                      np.arange(5, dtype=np.float64) * 2.0,
                      np.arange(5, dtype=np.float64) * 3.0]
        for format_str in LOCAL_FORMAT_TUPLE:
            with tempfile.TemporaryDirectory() as folder_str:
                new_name_list, signal_file = save_and_load(
                    folder_str, name_list, array_list, "time", format_str)
            with self.subTest(format=format_str):
                self.assertEqual(new_name_list, ["Time", "TIME_2", "speed"])
                self.assertEqual(signal_file.time_signal_name_str, "Time")
                self.assertFalse(signal_file.needs_time_signal_choice_b)
                self.assert_same_values(array_list[0],
                                        signal_file.time_array)
                self.assert_same_values(
                    array_list[1], signal_file.signal_array("TIME_2"))

    @covers("LLFR-00407", "LLFR-00326")
    def test_chosen_time_signal_written_as_time(self) -> None:
        """A time signal chosen in the window, "t", is saved as "Time" so
        that the saved file opens without the window.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["speed", "t"]
        array_list = [np.array([4.0, 5.0, 6.0]), np.array([0.0, 0.1, 0.2])]
        for format_str in LOCAL_FORMAT_TUPLE:
            with tempfile.TemporaryDirectory() as folder_str:
                new_name_list, signal_file = save_and_load(
                    folder_str, name_list, array_list, "t", format_str)
            with self.subTest(format=format_str):
                self.assertEqual(new_name_list, ["speed", "Time"])
                self.assertEqual(signal_file.time_signal_name_str, "Time")
                self.assert_same_values(array_list[1],
                                        signal_file.time_array)


class WriterRequestTest(unittest.TestCase):
    """Order, blank names and non-finite values (review of PR #158)."""

    @requires_h5py
    @covers("LLFR-00134", "LLFR-00401", "LLFR-00402")
    def test_hdf5_keeps_the_signal_list_order(self) -> None:
        """An HDF5 file of Save signals reopens in the signal-list order,
        also inside a group.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Time", "zeta", "beta", "grp/z", "grp/a", "alpha"]
        array_list = [np.arange(4, dtype=np.float64) * (index_i + 1)
                      for index_i in range(len(name_list))]
        with tempfile.TemporaryDirectory() as folder_str:
            new_name_list, signal_file = save_and_load(
                folder_str, name_list, array_list, "Time", HDF5_FORMAT_STR)
        self.assertEqual(new_name_list, name_list)
        self.assertEqual(signal_file.signal_name_list, name_list)

    @covers("LLFR-00403", "LLFR-00404", "LLFR-00059")
    def test_csv_and_excel_names_without_outer_blanks(self) -> None:
        """" a" and "a" (as in an HDF5 data file) and a name of spaces
        only are saved as "a_2", "a" and "signal" and read back so.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Time", " a", "a", "   ", "b\t", "signal"]
        array_list = [np.arange(3, dtype=np.float64) * (index_i + 1)
                      for index_i in range(len(name_list))]
        expected_list = ["Time", "a_2", "a", "signal_2", "b", "signal"]
        for format_str in (CSV_FORMAT_STR, EXCEL_FORMAT_STR):
            with tempfile.TemporaryDirectory() as folder_str:
                new_name_list, signal_file = save_and_load(
                    folder_str, name_list, array_list, "Time", format_str)
            with self.subTest(format=format_str):
                self.assertEqual(new_name_list, expected_list)
                self.assertEqual(signal_file.signal_name_list,
                                 expected_list)
                np.testing.assert_array_equal(
                    signal_file.signal_array("a_2"), array_list[1])
                self.assertEqual(
                    changed_name_list(name_list, new_name_list),
                    [(" a", "a_2"), ("   ", "signal_2"), ("b\t", "b")])

    @covers("LLFR-00408")
    def test_non_finite_values_are_refused_in_every_format(self) -> None:
        """inf, -inf and NaN samples make every format refuse, naming the
        signals, so no broken file is made (Excel would be corrupt).

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Time", "ok", "big", "gap"]
        array_list = [np.arange(3, dtype=np.float64), np.ones(3),
                      np.array([1.0, np.inf, -np.inf]),
                      np.array([np.nan, 1.0, 2.0])]
        self.assertEqual(file_writer.non_finite_name_list(name_list,
                                                          array_list),
                         ["big", "gap"])
        for format_str in file_writer.FORMAT_ORDER_TUPLE:
            with self.subTest(format=format_str):
                with self.assertRaises(SignalWriteError) as context:
                    signal_file_bytes(name_list, array_list, format_str)
                self.assertIn("'big', 'gap'", str(context.exception))
                self.assertIn("not finite numbers", str(context.exception))
        self.assertEqual(file_writer.non_finite_name_list(
            name_list[:2], array_list[:2]), [])


class NameRuleTest(unittest.TestCase):
    """The name rules of LLFR-00403 and LLFR-00407, without files."""

    @covers("LLFR-00403")
    def test_mat_rules(self) -> None:
        """Invalid characters, the x prefix and the 63-character cut.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(file_writer.mat_name("a-b.c d/e"), "a_b_c_d_e")
        self.assertEqual(file_writer.mat_name("9lives"), "x9lives")
        self.assertEqual(file_writer.mat_name("_x"), "x_x")
        self.assertEqual(file_writer.mat_name("é"), "x_")
        self.assertEqual(file_writer.mat_name("ok_Name2"), "ok_Name2")
        self.assertEqual(len(file_writer.mat_name("a" * 100)), 63)
        self.assertEqual(len(file_writer.mat_name("1" * 100)), 63)
        self.assertTrue(file_writer.mat_name("1" * 100).startswith("x1"))

    @covers("LLFR-00403", "LLFR-00241")
    def test_mat_duplicates_stay_within_63_characters(self) -> None:
        """Changed names that collide get _2, _3..., cut to fit in 63.

        Inputs: none.
        Outputs: none.
        """
        long_str = "s" * 80
        name_list = ["Time", long_str + "a", long_str + "b", long_str + "c",
                     "a.b", "a-b", "a_b_2"]
        new_name_list = saved_name_list(name_list, "Time", MAT_FORMAT_STR)
        self.assertEqual(new_name_list[1:4], [
            "s" * 63, "s" * 61 + "_2", "s" * 61 + "_3"])
        # "a_b_2" was not changed, so it keeps its name; the second
        # changed "a_b" skips it.
        self.assertEqual(new_name_list[4:], ["a_b", "a_b_3", "a_b_2"])
        self.assertEqual(len(set(new_name_list)), len(new_name_list))
        self.assertTrue(all(len(name_str) <= 63
                            for name_str in new_name_list))

    @covers("LLFR-00403")
    def test_hdf5_parts_removed(self) -> None:
        """Empty, "." and ".." parts and outer "/" are removed.

        Inputs: none.
        Outputs: none.
        """
        for name_str, expected_str in (
                ("/a/b/", "a/b"), ("a//b", "a/b"), ("./a/../b", "a/b"),
                ("/", "signal"), ("..", "signal"), ("", "signal"),
                ("a b/c", "a b/c")):
            with self.subTest(name=name_str):
                self.assertEqual(file_writer.hdf5_name(name_str),
                                 expected_str)

    @covers("LLFR-00403")
    def test_hdf5_name_that_is_a_group(self) -> None:
        """"engine" with "engine/speed" becomes "engine_2", or a higher
        number when "engine_2" is taken as a name or a group.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(saved_name_list(
            ["Time", "engine", "engine/speed"], "Time", HDF5_FORMAT_STR),
            ["Time", "engine_2", "engine/speed"])
        self.assertEqual(saved_name_list(
            ["Time", "engine", "engine/speed", "engine_2",
             "engine_3/x"], "Time", HDF5_FORMAT_STR),
            ["Time", "engine_4", "engine/speed", "engine_2", "engine_3/x"])
        # Nested groups: both "a" and "a/b" are groups.
        self.assertEqual(saved_name_list(
            ["Time", "a", "a/b", "a/b/c"], "Time", HDF5_FORMAT_STR),
            ["Time", "a_2", "a/b_2", "a/b/c"])

    @covers("LLFR-00403", "LLFR-00241")
    def test_hdf5_duplicates_after_cleaning(self) -> None:
        """"/x" and "x/" both become "x"; the changed one gets "_2".

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(saved_name_list(
            ["Time", "x", "/x", "x/"], "Time", HDF5_FORMAT_STR),
            ["Time", "x", "x_2", "x_3"])

    @covers("LLFR-00407", "LLFR-00330")
    def test_hdf5_time_in_a_group_is_kept(self) -> None:
        """"grp/time" does not match the time signal name in HDF5 and is
        not renamed; "time" at the top level is.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(saved_name_list(
            ["Time", "grp/time", "time"], "Time", HDF5_FORMAT_STR),
            ["Time", "grp/time", "time_2"])

    @covers("LLFR-00407", "LLFR-00403")
    def test_hdf5_group_named_time(self) -> None:
        """"Time" stays the time dataset; a name in a group "Time" moves
        to "Time_2/...".

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(saved_name_list(
            ["Time", "Time/x", "Time/y"], "Time", HDF5_FORMAT_STR),
            ["Time", "Time_2/x", "Time_2/y"])

    @covers("LLFR-00407")
    def test_other_time_names_get_a_number(self) -> None:
        """Every other name matching "Time" in the format gets a number,
        so that the file has exactly one time signal.

        Inputs: none.
        Outputs: none.
        """
        from model.signal_file import is_time_signal_name
        name_list = ["Time", "TIME", "time", "tImE", "TIME_2", "speed"]
        for format_str in file_writer.FORMAT_ORDER_TUPLE:
            new_name_list = saved_name_list(name_list, "Time", format_str)
            with self.subTest(format=format_str):
                self.assertEqual(new_name_list, [
                    "Time", "TIME_3", "time_2", "tImE_2", "TIME_2",
                    "speed"])
                self.assertEqual(sum(is_time_signal_name(name_str)
                                     for name_str in new_name_list), 1)
        # LLFR-00407: an HDF5 name "time" made from "/time" also matches.
        self.assertEqual(saved_name_list(
            ["t", "/time"], "t", HDF5_FORMAT_STR), ["Time", "time_2"])

    @covers("LLFR-00404")
    def test_changed_names_list(self) -> None:
        """Only changed names are listed, as "<old> → <new>".

        Inputs: none.
        Outputs: none.
        """
        name_list = ["time", "a.b", "c"]
        new_name_list = saved_name_list(name_list, "time", MAT_FORMAT_STR)
        change_list = changed_name_list(name_list, new_name_list)
        self.assertEqual(change_list, [("time", "Time"), ("a.b", "a_b")])
        self.assertEqual(changed_names_text(change_list),
                         "time → Time\na.b → a_b")
        self.assertEqual(changed_name_list(["Time", "c"], ["Time", "c"]),
                         [])


class DialogNameTest(unittest.TestCase):
    """The proposed name, the formats and the added extension."""

    @covers("LLFR-00396")
    def test_proposed_name_and_format(self) -> None:
        """run1.csv proposes run1_signals.csv, in the CSV format.

        Inputs: none.
        Outputs: none.
        """
        for path_str, name_str, format_str in (
                ("/d/run1.csv", "run1_signals.csv", CSV_FORMAT_STR),
                ("/d/run1.XLSX", "run1_signals.XLSX", EXCEL_FORMAT_STR),
                ("/d/a.b.mat", "a.b_signals.mat", MAT_FORMAT_STR),
                ("/d/x.h5", "x_signals.h5", HDF5_FORMAT_STR),
                ("/d/x.hdf5", "x_signals.hdf5", HDF5_FORMAT_STR)):
            with self.subTest(path=path_str):
                self.assertEqual(proposed_file_name(path_str), name_str)
                self.assertEqual(format_of_path(path_str), format_str)
        self.assertEqual(format_of_path("/d/x.txt"), "")

    @covers("LLFR-00396")
    def test_extension_added(self) -> None:
        """An extension of the chosen format is kept; otherwise the
        format's extension is added.

        Inputs: none.
        Outputs: none.
        """
        for path_str, format_str, expected_str in (
                ("/d/out", CSV_FORMAT_STR, "/d/out.csv"),
                ("/d/out.csv", CSV_FORMAT_STR, "/d/out.csv"),
                ("/d/out.CSV", CSV_FORMAT_STR, "/d/out.CSV"),
                ("/d/out.txt", CSV_FORMAT_STR, "/d/out.txt.csv"),
                ("/d/out.csv", EXCEL_FORMAT_STR, "/d/out.csv.xlsx"),
                ("/d/out", MAT_FORMAT_STR, "/d/out.mat"),
                ("/d/out", HDF5_FORMAT_STR, "/d/out.h5"),
                ("/d/out.hdf5", HDF5_FORMAT_STR, "/d/out.hdf5"),
                ("/d/out.h5", HDF5_FORMAT_STR, "/d/out.h5")):
            with self.subTest(path=path_str, format=format_str):
                self.assertEqual(
                    ensure_format_extension(path_str, format_str),
                    expected_str)


class ExcelLimitTest(unittest.TestCase):
    """The size of one Excel sheet (LLFR-00400)."""

    @covers("LLFR-00400")
    def test_limits(self) -> None:
        """16384 signals of 1048575 samples fit; one more does not.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(excel_limit_reason(16384, 1048575), "")
        for signal_count_i, sample_count_i in ((16385, 10),
                                               (2, 1048576)):
            with self.subTest(signals=signal_count_i,
                              samples=sample_count_i):
                reason_str = excel_limit_reason(signal_count_i,
                                                sample_count_i)
                self.assertIn("too many samples or are too many",
                              reason_str)
                self.assertIn("Excel", reason_str)

    @covers("LLFR-00400")
    def test_writer_refuses_too_many_signals(self) -> None:
        """The writer raises instead of writing a sheet that is too big.

        Inputs: none.
        Outputs: none.
        """
        array_list = [np.zeros(2)] * 16385
        name_list = [f"s{index_i}" for index_i in range(16385)]
        with mock.patch("openpyxl.Workbook") as workbook_class:
            with self.assertRaises(SignalWriteError) as context:
                signal_file_bytes(name_list, array_list, EXCEL_FORMAT_STR)
        workbook_class.assert_not_called()
        self.assertIn("Excel", str(context.exception))


class WriteFailureTest(unittest.TestCase):
    """Errors while making the content (LLFR-00399)."""

    @covers("LLFR-00399")
    def test_missing_h5py_is_a_write_error(self) -> None:
        """Without h5py, HDF5 content can't be made; the reason says so.

        Inputs: none.
        Outputs: none.
        """
        with mock.patch.object(file_writer, "hdf5_library",
                               return_value=None):
            with self.assertRaises(SignalWriteError) as context:
                signal_file_bytes(["Time", "a"],
                                  [np.zeros(2), np.zeros(2)],
                                  HDF5_FORMAT_STR)
        self.assertIn("h5py", str(context.exception))

    @covers("LLFR-00399")
    def test_library_error_is_a_write_error(self) -> None:
        """An error of the library becomes a SignalWriteError.

        Inputs: none.
        Outputs: none.
        """
        with mock.patch("scipy.io.savemat",
                        side_effect=ValueError("bad variable")):
            with self.assertRaises(SignalWriteError) as context:
                signal_file_bytes(["Time", "a"],
                                  [np.zeros(2), np.zeros(2)],
                                  MAT_FORMAT_STR)
        self.assertIn("bad variable", str(context.exception))


if __name__ == "__main__":
    unittest.main()
