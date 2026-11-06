"""Tests for model.data_files: the open data files (HLFR-00113)."""

import os
import tempfile
import unittest

import numpy as np

from tests.support import covers

from model.data_files import (
    MAXIMUM_DATA_FILES_I, DataFileSet, file_prefix,
    identical_time_signals_b, prefixed_name, same_file_b,
    selection_order_list)
from model.file_loader import load_signal_file
from model.signal_file import SignalFile
from model.synthetic_signals import ordered_signal_names

# The sample files of COR-00023.
GOOD_FOLDER_STR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "user_tests", "good")


def make_file(path_str: str, start_s: float = 0.0,
              end_s: float = 2.0) -> SignalFile:
    """Build a SignalFile with Time and Speed.

    Inputs:
        path_str: the path of the file.
        start_s: the first time sample.
        end_s: the last time sample.
    Outputs: the SignalFile, with three samples.
    """
    time_array = np.linspace(start_s, end_s, 3)
    return SignalFile(path_str, {"Time": time_array,
                                 "Speed": time_array * 2.0})


class PrefixTest(unittest.TestCase):
    """The prefix of the signal names (HLFR-00115)."""

    @covers("LLFR-00905", "LLFR-00906", "HLFR-00115")
    def test_prefix_of_a_file_number(self) -> None:
        """file<N>_ goes in front of the name in the file.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(file_prefix(1), "file1_")
        self.assertEqual(file_prefix(12), "file12_")
        self.assertEqual(prefixed_name(3, "Speed"), "file3_Speed")
        data_files = DataFileSet()
        data_file = data_files.add(make_file("/d/a.csv"))
        self.assertEqual(data_file.signal_name_list,
                         ["file1_Time", "file1_Speed"])
        self.assertEqual(data_file.plain_name("file1_Speed"), "Speed")
        self.assertEqual(data_file.plain_name("other"), "other")
        self.assertEqual(data_file.file_name_row_str, "file1_a.csv")

    @covers("LLFR-00909", "LLFR-00053", "HLFR-00006")
    def test_time_signal_found_before_the_prefix(self) -> None:
        """The time signal is found by its name in the file.

        Inputs: none.
        Outputs: none.
        """
        signal_file = SignalFile("/d/a.csv", {
            "speed": np.arange(3.0), "TIME": np.arange(3.0)})
        data_file = DataFileSet().add(signal_file)
        self.assertEqual(data_file.time_signal_name_str, "file1_TIME")
        np.testing.assert_array_equal(data_file.time_array, np.arange(3.0))


class NumberTest(unittest.TestCase):
    """The file numbers (HLFR-00114)."""

    @covers("LLFR-00900", "LLFR-00901", "LLFR-00902", "LLFR-00904",
            "LLFR-00938", "HLFR-00114")
    def test_numbers_are_never_given_again(self) -> None:
        """Numbers grow; closed numbers stay used up.

        Inputs: none.
        Outputs: none.
        """
        data_files = DataFileSet()
        self.assertEqual(data_files.next_number_i, 1)
        for name_str in ("a", "b", "c"):
            data_files.add(make_file(f"/d/{name_str}.csv"))
        self.assertEqual(data_files.remove(2).number_i, 2)
        self.assertIsNone(data_files.remove(2))
        self.assertEqual([data_file.number_i
                          for data_file in data_files.file_list], [1, 3])
        self.assertEqual(data_files.add(make_file("/d/d.csv")).number_i, 4)
        self.assertEqual(len(data_files.remove_all()), 3)
        self.assertEqual(len(data_files), 0)
        self.assertEqual(data_files.add(make_file("/d/e.csv")).number_i, 5)

    @covers("LLFR-00895", "LLFR-00896", "HLFR-00113")
    def test_at_most_ten_files(self) -> None:
        """The eleventh file cannot be added.

        Inputs: none.
        Outputs: none.
        """
        data_files = DataFileSet()
        for index_i in range(MAXIMUM_DATA_FILES_I):
            self.assertFalse(data_files.is_full_b)
            data_files.add(make_file(f"/d/{index_i}.csv"))
        self.assertTrue(data_files.is_full_b)
        with self.assertRaises(ValueError):
            data_files.add(make_file("/d/extra.csv"))
        self.assertEqual(data_files.next_number_i, 11)


class SignalsTest(unittest.TestCase):
    """The signals of several files (HLFR-00116)."""

    @covers("LLFR-00912", "LLFR-00916", "LLFR-00938", "LLFR-00939",
            "LLFR-00332", "HLFR-00116")
    def test_signals_and_times_of_every_file(self) -> None:
        """Each signal keeps the time of its file; the range covers all.

        Inputs: none.
        Outputs: none.
        """
        data_files = DataFileSet()
        self.assertEqual(data_files.time_range_tuple(), ())
        data_files.add(make_file("/d/a.csv", 0.0, 2.0))
        data_files.add(make_file("/d/b.csv", 5.0, 9.0))
        self.assertEqual(data_files.signal_name_list, [
            "file1_Time", "file1_Speed", "file2_Time", "file2_Speed"])
        self.assertEqual(list(data_files.signal_dict),
                         data_files.signal_name_list)
        self.assertEqual(data_files.time_signal_name_list,
                         ["file1_Time", "file2_Time"])
        np.testing.assert_array_equal(
            data_files.time_array_for_signal("file2_Speed"),
            [5.0, 7.0, 9.0])
        np.testing.assert_array_equal(
            data_files.signal_array("file2_Speed"), [10.0, 14.0, 18.0])
        self.assertEqual(data_files.time_range_tuple(), (0.0, 9.0))
        self.assertEqual(data_files.file_of_signal("file1_Time").number_i, 1)
        self.assertIsNone(data_files.file_of_signal("Speed"))
        with self.assertRaises(KeyError):
            data_files.signal_array("Speed")
        with self.assertRaises(KeyError):
            data_files.time_array_for_signal("Speed")
        self.assertEqual(data_files.path_str, "/d/a.csv")
        self.assertEqual(data_files.path_list, ["/d/a.csv", "/d/b.csv"])
        self.assertEqual(data_files.time_signal_name_str, "file1_Time")


class SameFileTest(unittest.TestCase):
    """The same file on disk (LLFR-00898)."""

    @covers("LLFR-00898")
    def test_paths_of_the_same_file(self) -> None:
        """A link, or another spelling of the path, is the same file.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as folder_str:
            path_str = os.path.join(folder_str, "a.csv")
            with open(path_str, "w", encoding="utf-8") as file:
                file.write("x")
            other_str = os.path.join(folder_str, "b.csv")
            with open(other_str, "w", encoding="utf-8") as file:
                file.write("x")
            self.assertTrue(same_file_b(
                path_str, os.path.join(folder_str, ".", "a.csv")))
            self.assertFalse(same_file_b(path_str, other_str))
            link_str = os.path.join(folder_str, "link.csv")
            try:
                os.symlink(path_str, link_str)
            except (OSError, NotImplementedError):
                link_str = ""
            if link_str:
                self.assertTrue(same_file_b(path_str, link_str))
            data_files = DataFileSet()
            data_files.add(make_file(path_str))
            self.assertEqual(data_files.open_number(path_str), 1)
            self.assertIsNone(data_files.open_number(other_str))
        self.assertTrue(same_file_b("/no/such/x.csv",
                                    "/no/such/../such/x.csv"))
        self.assertFalse(same_file_b("/no/such/x.csv", "/no/such/y.csv"))


class SelectionOrderTest(unittest.TestCase):
    """The order of the selected files (LLFR-00952, LLFR-00974)."""

    @covers("LLFR-00952", "LLFR-00974", "HLFR-00122")
    def test_names_in_character_order(self) -> None:
        """Folders are left out; case only breaks a tie.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(selection_order_list(
            ["/z/run2.csv", "/a/Run10.csv", "/y/b.csv", "/x/B.csv",
             "/w/a.mat"]),
            ["/w/a.mat", "/x/B.csv", "/y/b.csv", "/a/Run10.csv",
             "/z/run2.csv"])


class DescriptionTest(unittest.TestCase):
    """The description of the open files (LLFR-00971, LLFR-00972)."""

    @covers("LLFR-00971", "LLFR-00972", "HLFR-00038", "HLFR-00039",
            "HLFR-00113")
    def test_every_open_file_in_number_order(self) -> None:
        """`file<N> = <name>` for each file, separated by commas.

        Inputs: none.
        Outputs: none.
        """
        data_files = DataFileSet()
        self.assertEqual(data_files.description_str, "")
        data_files.add(make_file(os.path.join("data", "run_A.csv")))
        self.assertEqual(data_files.description_str, "file1 = run_A.csv")
        data_files.add(make_file(os.path.join("other", "run_B.mat")))
        data_files.add(make_file(os.path.join("x", "y", "run C.h5")))
        self.assertEqual(
            data_files.description_str,
            "file1 = run_A.csv, file2 = run_B.mat, file3 = run C.h5")
        # A closed file leaves the description; the numbers are kept.
        data_files.remove(2)
        self.assertEqual(data_files.description_str,
                         "file1 = run_A.csv, file3 = run C.h5")
        data_files.remove_all()
        self.assertEqual(data_files.description_str, "")


class TimeToleranceTest(unittest.TestCase):
    """Identical time signals within a tolerance (HLFR-00120)."""

    def identical(self, first_list: list, second_list: list) -> bool:
        """Compare two time signals both ways.

        Inputs:
            first_list: the samples of the first time signal.
            second_list: the samples of the second one.
        Outputs: the answer of identical_time_signals_b, which must be
            the same in both orders.
        """
        first_b = identical_time_signals_b(np.array(first_list),
                                           np.array(second_list))
        second_b = identical_time_signals_b(np.array(second_list),
                                            np.array(first_list))
        self.assertEqual(first_b, second_b)
        return first_b

    @covers("LLFR-00977", "HLFR-00120")
    def test_relative_tolerance_from_1_up(self) -> None:
        """From 1 up, two samples match within 1e-8 times the larger
        absolute value.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(self.identical([0.0, 1000.0], [0.0, 1000.0]))
        self.assertTrue(self.identical([1000.0], [1000.0 + 0.9e-5]))
        self.assertFalse(self.identical([1000.0], [1000.0 + 1.1e-5]))
        self.assertTrue(self.identical([-2.0], [-2.0 - 1.9e-8]))
        self.assertFalse(self.identical([-2.0], [-2.0 - 2.1e-8]))
        self.assertTrue(self.identical([1.0], [1.0 + 0.9e-8]))
        self.assertFalse(self.identical([1.0], [1.0 + 1.1e-8]))
        # The larger of the two values sets the tolerance.
        self.assertTrue(self.identical([0.9999999995], [1.000000005]))

    @covers("LLFR-00977", "HLFR-00120")
    def test_absolute_tolerance_below_1(self) -> None:
        """When both samples are smaller than 1 in absolute value, they
        match within 1e-8.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(self.identical([0.0], [0.9e-8]))
        self.assertFalse(self.identical([0.0], [1.1e-8]))
        self.assertTrue(self.identical([0.5], [0.5 + 0.9e-8]))
        self.assertFalse(self.identical([0.5], [0.5 + 1.1e-8]))
        self.assertTrue(self.identical([-0.5], [-0.5 - 0.9e-8]))
        self.assertTrue(self.identical([1e-12], [-1e-12]))

    @covers("LLFR-00977", "HLFR-00120")
    def test_number_of_samples(self) -> None:
        """Time signals with different numbers of samples never match.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(self.identical([0.0, 1.0], [0.0, 1.0, 2.0]))
        self.assertFalse(self.identical([0.0], []))
        self.assertTrue(self.identical([], []))

    @covers("LLFR-00978", "LLFR-00977", "HLFR-00120")
    def test_nan_samples(self) -> None:
        """A NaN matches a NaN at the same position, never a number.

        Inputs: none.
        Outputs: none.
        """
        nan_f = float("nan")
        self.assertTrue(self.identical([0.0, nan_f, 2.0],
                                       [0.0, nan_f, 2.0 + 1e-9]))
        self.assertTrue(self.identical([nan_f, nan_f], [nan_f, nan_f]))
        self.assertFalse(self.identical([0.0, nan_f, 2.0],
                                        [0.0, 1.0, 2.0]))
        self.assertFalse(self.identical([0.0, nan_f], [nan_f, 0.0]))
        # A NaN elsewhere does not hide a difference.
        self.assertFalse(self.identical([nan_f, 1.0], [nan_f, 1.1]))

    @covers("LLFR-00977", "HLFR-00120")
    def test_infinite_samples(self) -> None:
        """An infinity matches the same infinity only.

        Inputs: none.
        Outputs: none.
        """
        inf_f = float("inf")
        self.assertTrue(self.identical([0.0, inf_f], [0.0, inf_f]))
        self.assertFalse(self.identical([inf_f], [-inf_f]))
        self.assertFalse(self.identical([inf_f], [1e300]))

    @covers("LLFR-00977", "LLFR-00942", "HLFR-00120", "HLFR-00113")
    def test_excel_and_mat_samples_are_identical(self) -> None:
        """signals.xlsx and signals.mat store the same times with tiny
        rounding differences, and count as identical.

        Inputs: none.
        Outputs: none.
        """
        excel_file = load_signal_file(os.path.join(GOOD_FOLDER_STR,
                                                   "signals.xlsx"))
        mat_file = load_signal_file(os.path.join(GOOD_FOLDER_STR,
                                                 "signals.mat"))
        # The test is meaningful only while the values differ.
        self.assertFalse(np.array_equal(excel_file.time_array,
                                        mat_file.time_array))
        self.assertTrue(identical_time_signals_b(excel_file.time_array,
                                                 mat_file.time_array))
        data_files = DataFileSet()
        data_files.add(excel_file)
        data_files.add(mat_file)
        self.assertTrue(data_files.same_time_signals_b())
        # A third file with one time 1e-6 s later is not identical.
        later_array = np.array(mat_file.time_array, dtype=float)
        later_array[10] += 1e-6
        data_files.add(SignalFile("later.csv", {
            "Time": later_array, "Speed": later_array}))
        self.assertFalse(data_files.same_time_signals_b())


class TimeSignalFirstTest(unittest.TestCase):
    """The time signal is the first signal of its file (LLFR-01009)."""

    @covers("LLFR-01009", "LLFR-00939", "HLFR-00011")
    def test_listed_names_start_with_the_time_signal(self) -> None:
        """The time signal comes first, then the file's order.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.linspace(0.0, 2.0, 3)
        data_files = DataFileSet()
        first_file = data_files.add(SignalFile("a.csv", {
            "Speed": time_array, "Time": time_array, "Force": time_array}))
        second_file = data_files.add(SignalFile("b.csv", {
            "x": time_array, "t_s": time_array}, "t_s"))
        self.assertEqual(first_file.listed_signal_name_list,
                         ["file1_Time", "file1_Speed", "file1_Force"])
        self.assertEqual(second_file.listed_signal_name_list,
                         ["file2_t_s", "file2_x"])
        # The file's own order is kept by signal_name_list.
        self.assertEqual(first_file.signal_name_list,
                         ["file1_Speed", "file1_Time", "file1_Force"])
        # The order of the signal list, with the synthetic signals
        # after their own file's signals.
        self.assertEqual(
            ordered_signal_names(data_files, ["file1_int_Speed"],
                                 {"file1_int_Speed": 1}),
            ["file1_Time", "file1_Speed", "file1_Force", "file1_int_Speed",
             "file2_t_s", "file2_x"])


if __name__ == "__main__":
    unittest.main()
