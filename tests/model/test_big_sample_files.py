"""Tests of the big sample files of the build (PCR-00073).

The generator of tests/user_tests/make_user_test_files.py is run with a
short time signal, so that the test is quick, and every file it writes
must open in the app with the same samples. The sizes of the real files
are checked from the generator's constants.
"""

import importlib.util
import os
import subprocess
import tempfile
import unittest

import numpy as np

from tests.support import REPOSITORY_ROOT_STR, covers

from model.file_loader import load_signal_file

GENERATOR_PATH_STR = os.path.join(REPOSITORY_ROOT_STR, "tests", "user_tests",
                                  "make_user_test_files.py")


def load_generator():
    """Import make_user_test_files.py as a module without running it.

    Inputs: none.
    Outputs: the module object.
    """
    specification = importlib.util.spec_from_file_location(
        "make_user_test_files", GENERATOR_PATH_STR)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class BigSampleFileTest(unittest.TestCase):
    """The big files open and hold the same samples in every format."""

    @covers("PCR-00073", "HLFR-00005")
    def test_short_big_files_open_with_the_same_samples(self) -> None:
        """With 2 s at 0.01 s and 100 signals, each file opens with 101
        signals of 201 samples, the Excel file too, and the samples
        match the generator's formula.

        Inputs: none.
        Outputs: none.
        """
        generator = load_generator()
        with tempfile.TemporaryDirectory() as folder_str:
            path_list = generator.write_big_files(folder_str, 2.0, 0.01, 100)
            name_list = [os.path.basename(path_str) for path_str
                         in path_list]
            self.assertEqual(name_list[:4], ["big_comma.csv",
                                             "big_semicolon.csv",
                                             "big.xlsx", "big.mat"])
            expected_array = generator.big_chunk_array(0, 201, 0.01, 100)
            for path_str in path_list:
                with self.subTest(path_str=os.path.basename(path_str)):
                    signal_file = load_signal_file(path_str)
                    self.assertEqual(signal_file.signal_name_list,
                                     generator.big_signal_name_list(100))
                    time_array = np.asarray(
                        signal_file.signal_dict["Time"], dtype=float)
                    self.assertEqual(time_array.size, 201)
                    self.assertAlmostEqual(time_array[-1], 2.0)
                    np.testing.assert_allclose(
                        np.asarray(signal_file.signal_dict["Signal_042"],
                                   dtype=float),
                        expected_array[:, 42], rtol=1e-5, atol=1e-5)

    @covers("PCR-00073")
    def test_sizes_of_the_real_files(self) -> None:
        """4 hours every 0.01 s give 1,440,001 samples; the Excel file
        holds the 1,048,575 that fit below its row of names; a MAT
        variable of that size stays below the 2**31 bytes of MAT 5.

        Inputs: none.
        Outputs: none.
        """
        generator = load_generator()
        self.assertEqual(generator.big_sample_count(), 1440001)
        self.assertEqual(generator.BIG_SIGNAL_COUNT_I, 100)
        self.assertEqual(generator.EXCEL_MAXIMUM_ROW_COUNT_I - 1, 1048575)
        self.assertLess(generator.big_sample_count() * 8, 2 ** 31)
        self.assertEqual(generator.excel_column_name(0), "A")
        self.assertEqual(generator.excel_column_name(100), "CW")

    @covers("PCR-00073")
    def test_big_folder_is_never_committed(self) -> None:
        """tests/user_tests/big is ignored by git.

        Inputs: none.
        Outputs: none.
        """
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "-q",
             "tests/user_tests/big/big.csv"],
            cwd=REPOSITORY_ROOT_STR, check=False)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
