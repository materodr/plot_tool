"""Tests for the sample files in tests/user_tests (PCR-00032).

Every file format of HLFR-00005 must have at least one file in
tests/user_tests/good that the app opens. The HDF5 check needs h5py and
runs in CI (tests/build_test_matrix.py --require-h5py); the files are
written by tests/user_tests/make_user_test_files.py.
"""

import os
import unittest

from tests.support import REPOSITORY_ROOT_STR, covers, requires_h5py

from model.errors import FileReadError
from model.file_loader import SUPPORTED_EXTENSION_TUPLE, load_signal_file

USER_TESTS_FOLDER_STR = os.path.join(REPOSITORY_ROOT_STR, "tests",
                                     "user_tests")
GOOD_FOLDER_STR = os.path.join(USER_TESTS_FOLDER_STR, "good")
BAD_FOLDER_STR = os.path.join(USER_TESTS_FOLDER_STR, "bad")
# HLFR-00005: the extensions of each file format.
FORMAT_EXTENSION_DICT = {
    "CSV": (".csv",),
    "Excel": (".xlsx",),
    "MATLAB": (".mat",),
    "HDF5": (".h5", ".hdf5"),
}


def good_files_of_format(format_str: str) -> list:
    """List the files of one format in tests/user_tests/good.

    Inputs:
        format_str: a key of FORMAT_EXTENSION_DICT.
    Outputs: a sorted list of file paths whose extension (any letter
        case) belongs to the format.
    """
    extension_tuple = FORMAT_EXTENSION_DICT[format_str]
    return sorted(
        os.path.join(GOOD_FOLDER_STR, file_name_str)
        for file_name_str in os.listdir(GOOD_FOLDER_STR)
        if os.path.splitext(file_name_str)[1].lower() in extension_tuple)


class SampleFileTest(unittest.TestCase):
    """The good sample files open, one format at a time."""

    def assert_format_has_good_file(self, format_str: str) -> None:
        """Assert that a format has a good sample file and all open.

        Inputs:
            format_str: a key of FORMAT_EXTENSION_DICT.
        Outputs: none.
        """
        path_list = good_files_of_format(format_str)
        self.assertTrue(path_list,
                        f"no {format_str} file in tests/user_tests/good")
        for path_str in path_list:
            with self.subTest(file_name_str=os.path.basename(path_str)):
                signal_file = load_signal_file(path_str)
                self.assertGreaterEqual(len(signal_file.signal_name_list), 2)
                # HLFR-00006, HLFR-00070: the time signal is found by its
                # name, or one of the signals can be chosen as it.
                if signal_file.needs_time_signal_choice_b:
                    self.assertTrue(any(
                        signal_file.choose_time_signal(name_str) == ""
                        for name_str in signal_file.signal_name_list))
                self.assertIn(signal_file.time_signal_name_str,
                              signal_file.signal_name_list)

    @covers("PCR-00032", "HLFR-00005")
    def test_formats_cover_supported_extensions(self) -> None:
        """The formats checked here are exactly the supported extensions.

        Inputs: none.
        Outputs: none.
        """
        extension_list = [
            extension_str
            for extension_tuple in FORMAT_EXTENSION_DICT.values()
            for extension_str in extension_tuple]
        self.assertEqual(sorted(extension_list),
                         sorted(SUPPORTED_EXTENSION_TUPLE))

    @covers("PCR-00032", "HLFR-00005", "LLFR-00059", "LLFR-00061")
    def test_csv_sample_files_open(self) -> None:
        """There is a CSV sample file and every one opens.

        Inputs: none.
        Outputs: none.
        """
        self.assert_format_has_good_file("CSV")

    @covers("PCR-00032", "HLFR-00005", "LLFR-00059", "LLFR-00060")
    def test_excel_sample_files_open(self) -> None:
        """There is an Excel sample file and every one opens.

        Inputs: none.
        Outputs: none.
        """
        self.assert_format_has_good_file("Excel")

    @covers("PCR-00032", "HLFR-00005", "LLFR-00062", "LLFR-00063")
    def test_matlab_sample_files_open(self) -> None:
        """There is a MATLAB sample file and every one opens.

        Inputs: none.
        Outputs: none.
        """
        self.assert_format_has_good_file("MATLAB")

    @requires_h5py
    @covers("PCR-00032", "HLFR-00005", "LLFR-00134", "LLFR-00135")
    def test_hdf5_sample_files_open(self) -> None:
        """There is an HDF5 sample file and every one opens.

        Inputs: none.
        Outputs: none.
        """
        self.assert_format_has_good_file("HDF5")

    @requires_h5py
    @covers("LLFR-00134", "LLFR-00135")
    def test_hdf5_sample_content(self) -> None:
        """signals.h5 has grouped signals and no ignored dataset.

        Inputs: none.
        Outputs: none.
        """
        signal_file = load_signal_file(os.path.join(GOOD_FOLDER_STR,
                                                    "signals.h5"))
        name_list = signal_file.signal_name_list
        self.assertEqual(len(name_list), 12)
        for name_str in ("Time", "Ramp", "waves/Sine_3Hz",
                         "waves/decaying/Damped_sine", "sensors/Pressure",
                         "events/Step_at_5s"):
            self.assertIn(name_str, name_list)
        for name_str in ("matrix_2d", "description", "events/flags",
                         "sensors/calibration_gain"):
            self.assertNotIn(name_str, name_list)

    @requires_h5py
    @covers("LLFR-00008")
    def test_hdf5_bad_sample_files_are_refused(self) -> None:
        """The bad HDF5 sample file is refused with a File Open Error.

        Inputs: none.
        Outputs: none.
        """
        with self.assertRaises(FileReadError):
            load_signal_file(os.path.join(BAD_FOLDER_STR, "corrupt.h5"))

    @requires_h5py
    @covers("LLFR-00330", "LLFR-00325", "HLFR-00070")
    def test_hdf5_time_in_group_sample_file(self) -> None:
        """time_in_group.h5 asks for the time signal; run/Time is usable.

        Inputs: none.
        Outputs: none.
        """
        signal_file = load_signal_file(os.path.join(GOOD_FOLDER_STR,
                                                    "time_in_group.h5"))
        self.assertTrue(signal_file.needs_time_signal_choice_b)
        self.assertEqual(signal_file.choose_time_signal("run/Time"), "")

    @covers("LLFR-00053", "LLFR-00325", "LLFR-00329", "HLFR-00070")
    def test_time_signal_sample_files(self) -> None:
        """lowercase_time.csv finds "time"; the other file asks for it.

        Inputs: none.
        Outputs: none.
        """
        signal_file = load_signal_file(os.path.join(GOOD_FOLDER_STR,
                                                    "lowercase_time.csv"))
        self.assertEqual(signal_file.time_signal_name_str, "time")
        signal_file = load_signal_file(os.path.join(
            GOOD_FOLDER_STR, "time_signal_to_choose.csv"))
        self.assertTrue(signal_file.needs_time_signal_choice_b)
        self.assertIn("must always increase",
                      signal_file.choose_time_signal("Sine_1Hz"))
        self.assertEqual(signal_file.choose_time_signal("t_s"), "")


if __name__ == "__main__":
    unittest.main()
