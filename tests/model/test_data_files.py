"""Tests for model.data_files: the open data files (HLFR-00113)."""

import os
import tempfile
import unittest

import numpy as np

from tests.support import covers

from model.data_files import (
    MAXIMUM_DATA_FILES_I, DataFileSet, file_prefix, prefixed_name,
    same_file_b, selection_order_list)
from model.signal_file import SignalFile


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

    @covers("LLFR-00901", "LLFR-00902", "HLFR-00115")
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

    @covers("LLFR-00905", "LLFR-00053", "HLFR-00006")
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

    @covers("LLFR-00896", "LLFR-00897", "LLFR-00898", "LLFR-00900",
            "LLFR-00934", "HLFR-00114")
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

    @covers("LLFR-00891", "LLFR-00892", "HLFR-00113")
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

    @covers("LLFR-00908", "LLFR-00912", "LLFR-00934", "LLFR-00935",
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
    """The same file on disk (LLFR-00894)."""

    @covers("LLFR-00894")
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
    """The order of the selected files (LLFR-00948, LLFR-00970)."""

    @covers("LLFR-00948", "LLFR-00970", "HLFR-00122")
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


if __name__ == "__main__":
    unittest.main()


class DescriptionTest(unittest.TestCase):
    """The description of the open files (LLFR-00967, LLFR-00968)."""

    @covers("LLFR-00967", "LLFR-00968", "HLFR-00038", "HLFR-00039",
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
