"""Tests for reading HDF5 files in model.file_loader.

The HDF5 files are written inside a temporary folder with h5py (no
binary fixtures are committed). Tests that need h5py are skipped when it
is not installed; CI runs tests/build_test_matrix.py with --require-h5py,
and test_h5py_is_installed_in_ci fails there without it, so they can't be
skipped silently in CI. The other tests replace h5py with a fake module
and run everywhere.
"""

import os
import tempfile
import types
import unittest
from unittest import mock

import numpy as np

from tests.support import H5PY_AVAILABLE_B, covers, requires_h5py

import model.file_loader as file_loader
from model.errors import (
    OTHER_SIGNAL_CHECK_STR, SAMPLE_COUNT_CHECK_STR, TIME_SIGNAL_CHECK_STR,
    ContentCheckError, FileAccessError, FileReadError,
    UnsupportedFormatError)
from model.file_loader import SUPPORTED_EXTENSION_TUPLE, load_signal_file
from model.signal_file import TIME_SIGNAL_NAME_STR

if H5PY_AVAILABLE_B:
    import h5py

SAMPLE_COUNT_I = 6


class Hdf5FolderTest(unittest.TestCase):
    """Base class that gives each test an empty temporary folder."""

    def setUp(self) -> None:
        """Create the temporary folder.

        Inputs: none.
        Outputs: none.
        """
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

    def path(self, file_name_str: str) -> str:
        """Return the path of a file inside the temporary folder.

        Inputs:
            file_name_str: name of the file.
        Outputs: the absolute path.
        """
        return os.path.join(self.folder.name, file_name_str)

    def write_hdf5(self, file_name_str: str, dataset_dict: dict) -> str:
        """Write an HDF5 file with one dataset per entry.

        Inputs:
            file_name_str: name of the file.
            dataset_dict: dataset path (groups separated by "/") -> data
                given to h5py's create_dataset.
        Outputs: the path of the file.
        """
        path_str = self.path(file_name_str)
        with h5py.File(path_str, "w") as hdf5_file:
            for dataset_path_str, data in dataset_dict.items():
                hdf5_file.create_dataset(dataset_path_str, data=data)
        return path_str

    def write_bytes(self, file_name_str: str, content_bytes: bytes) -> str:
        """Write a binary file in the temporary folder.

        Inputs:
            file_name_str: name of the file.
            content_bytes: content of the file.
        Outputs: the path of the file.
        """
        path_str = self.path(file_name_str)
        with open(path_str, "wb") as binary_file:
            binary_file.write(content_bytes)
        return path_str

    def time_array(self) -> np.ndarray:
        """Return a time signal of SAMPLE_COUNT_I samples.

        Inputs: none.
        Outputs: float64 array 0, 0.1, 0.2, ...
        """
        return np.arange(SAMPLE_COUNT_I) * 0.1

    def assert_content_check(self, path_str: str, check_str: str) -> None:
        """Assert that opening a file fails the given content check.

        Inputs:
            path_str: path of the file.
            check_str: expected ContentCheckError.failed_check_str.
        Outputs: none.
        """
        with self.assertRaises(ContentCheckError) as context:
            load_signal_file(path_str)
        self.assertEqual(context.exception.failed_check_str, check_str)
        self.assertIn("cannot be opened", str(context.exception))


class H5pyInstalledTest(unittest.TestCase):
    """CI guard: the HDF5 tests must run in GitHub Actions."""

    @covers("LLFR-00134", "HLFR-00005")
    def test_h5py_is_installed_in_ci(self) -> None:
        """In GitHub Actions h5py is installed, so no HDF5 test skips.

        Inputs: none.
        Outputs: none.
        """
        if os.environ.get("GITHUB_ACTIONS") != "true":
            self.skipTest("only checked in GitHub Actions")
        self.assertTrue(H5PY_AVAILABLE_B,
                        "h5py must be installed in CI (requirements.txt)")


class Hdf5WithoutLibraryTest(Hdf5FolderTest):
    """HDF5 behaviour that is checked with a fake or missing h5py."""

    @covers("HLFR-00005", "LLFR-00011")
    def test_hdf5_extensions_are_supported(self) -> None:
        """.h5 and .hdf5 are supported extensions, in any letter case.

        Inputs: none.
        Outputs: none.
        """
        self.assertIn(".h5", SUPPORTED_EXTENSION_TUPLE)
        self.assertIn(".hdf5", SUPPORTED_EXTENSION_TUPLE)
        for file_name_str in ("data.h5", "data.hdf5", "DATA.H5",
                              "Data.HDF5", "data.Hdf5"):
            with self.subTest(file_name_str=file_name_str):
                path_str = self.write_bytes(file_name_str, b"not hdf5")
                # Whether h5py is there or not, it is not a format error.
                with self.assertRaises(FileReadError):
                    load_signal_file(path_str)

    @covers("LLFR-00011", "HLFR-00002")
    def test_unsupported_message_lists_hdf5(self) -> None:
        """The unsupported format message names the HDF5 extensions.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_bytes("data.he5", b"x")
        with self.assertRaises(UnsupportedFormatError) as context:
            load_signal_file(path_str)
        self.assertIn(".h5", str(context.exception))
        self.assertIn(".hdf5", str(context.exception))

    @covers("LLFR-00134", "LLFR-00008", "HLFR-00002")
    def test_missing_h5py_gives_read_error(self) -> None:
        """Without h5py an HDF5 file can't be read, and the box says why.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_bytes("data.h5", b"\x89HDF\r\n\x1a\n")
        with mock.patch.object(file_loader, "h5py", None):
            with self.assertRaises(FileReadError) as context:
                load_signal_file(path_str)
        message_str = str(context.exception)
        self.assertIn("could not be read", message_str)
        self.assertIn("HDF5 support is not installed", message_str)
        self.assertIn("data.h5", message_str)

    @covers("LLFR-00008", "HLFR-00002")
    def test_plain_os_error_of_h5py_is_a_read_error(self) -> None:
        """h5py's OSError for a non-HDF5 file is a read error.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_bytes("data.h5", b"plain text")
        fake_h5py = types.SimpleNamespace(
            File=mock.Mock(side_effect=OSError(
                "Unable to open file (file signature not found)")),
            Dataset=type("Dataset", (), {}))
        with mock.patch.object(file_loader, "h5py", fake_h5py):
            with self.assertRaises(FileReadError) as context:
                load_signal_file(path_str)
        self.assertIn("could not be read", str(context.exception))
        self.assertIn("empty or corrupt", str(context.exception))

    @covers("LLFR-00009", "HLFR-00002")
    def test_access_errors_stay_access_errors(self) -> None:
        """Missing files and permission errors are access errors.

        Inputs: none.
        Outputs: none.
        """
        for file_name_str in ("missing.h5", "missing.hdf5"):
            with self.subTest(file_name_str=file_name_str):
                with self.assertRaises(FileAccessError) as context:
                    load_signal_file(self.path(file_name_str))
                self.assertIn("file not found", str(context.exception))
        path_str = self.write_bytes("locked.h5", b"x")
        fake_h5py = types.SimpleNamespace(
            File=mock.Mock(side_effect=PermissionError(13, "denied")),
            Dataset=type("Dataset", (), {}))
        with mock.patch.object(file_loader, "h5py", fake_h5py):
            with self.assertRaises(FileAccessError) as context:
                load_signal_file(path_str)
        self.assertIn("permission denied", str(context.exception))

    @covers("LLFR-00008", "HLFR-00002")
    def test_unexpected_h5py_error_is_a_read_error(self) -> None:
        """Any other h5py error while reading is a read error.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_bytes("data.h5", b"x")
        fake_h5py = types.SimpleNamespace(
            File=mock.Mock(side_effect=RuntimeError("bad chunk")),
            Dataset=type("Dataset", (), {}))
        with mock.patch.object(file_loader, "h5py", fake_h5py):
            with self.assertRaises(FileReadError):
                load_signal_file(path_str)


@requires_h5py
class Hdf5SignalTest(Hdf5FolderTest):
    """Which HDF5 datasets are signals and how they are named."""

    @covers("LLFR-00134", "HLFR-00005")
    def test_signals_in_groups_are_named_by_path(self) -> None:
        """Datasets in groups are signals named by their path.

        Inputs: none.
        Outputs: none.
        """
        time_array = self.time_array()
        path_str = self.write_hdf5("groups.h5", {
            "Time": time_array,
            "speed": time_array * 2,
            "engine/speed": time_array * 3,
            "engine/oil/temperature": time_array * 4,
        })
        signal_file = load_signal_file(path_str)
        self.assertEqual(set(signal_file.signal_name_list),
                         {"Time", "speed", "engine/speed",
                          "engine/oil/temperature"})
        np.testing.assert_array_equal(
            signal_file.signal_dict["engine/oil/temperature"],
            time_array * 4)
        np.testing.assert_array_equal(
            signal_file.signal_dict["engine/speed"], time_array * 3)
        for name_str in signal_file.signal_name_list:
            self.assertFalse(name_str.startswith("/"))

    @covers("LLFR-00134")
    def test_signal_order_is_visit_order(self) -> None:
        """Signals keep h5py's visit order: by name, groups recursively.

        Inputs: none.
        Outputs: none.
        """
        time_array = self.time_array()
        path_str = self.write_hdf5("order.h5", {
            "zeta": time_array, "Time": time_array, "alpha": time_array,
            "beta/b": time_array, "beta/a": time_array,
        })
        signal_file = load_signal_file(path_str)
        self.assertEqual(signal_file.signal_name_list,
                         ["Time", "alpha", "beta/a", "beta/b", "zeta"])

    @covers("LLFR-00134")
    def test_row_and_column_vectors(self) -> None:
        """(N,), (1, N) and (N, 1) datasets are signals of N samples.

        Inputs: none.
        Outputs: none.
        """
        time_array = self.time_array()
        path_str = self.write_hdf5("vectors.h5", {
            "Time": time_array,
            "row": time_array.reshape(1, -1),
            "column": time_array.reshape(-1, 1),
        })
        signal_file = load_signal_file(path_str)
        for name_str in ("row", "column"):
            with self.subTest(name_str=name_str):
                signal_array = signal_file.signal_dict[name_str]
                self.assertEqual(signal_array.shape, (SAMPLE_COUNT_I,))
                np.testing.assert_array_equal(signal_array, time_array)

    @covers("LLFR-00134")
    def test_numeric_types_become_float64(self) -> None:
        """Integer, unsigned and float32 datasets are read as float64.

        Inputs: none.
        Outputs: none.
        """
        time_array = self.time_array()
        path_str = self.write_hdf5("types.h5", {
            "Time": time_array.astype(np.float32),
            "int8": np.arange(SAMPLE_COUNT_I, dtype=np.int8) - 3,
            "int64": np.arange(SAMPLE_COUNT_I, dtype=np.int64) * 10 ** 9,
            "uint16": np.arange(SAMPLE_COUNT_I, dtype=np.uint16),
            "float16": np.ones(SAMPLE_COUNT_I, dtype=np.float16),
        })
        signal_file = load_signal_file(path_str)
        for name_str, signal_array in signal_file.signal_dict.items():
            with self.subTest(name_str=name_str):
                self.assertEqual(signal_array.dtype, np.float64)
        np.testing.assert_array_equal(signal_file.signal_dict["int8"],
                                      np.arange(SAMPLE_COUNT_I) - 3.0)
        self.assertEqual(signal_file.signal_dict["int64"][-1], 5.0e9)

    @covers("LLFR-00134")
    def test_single_sample_signals(self) -> None:
        """A dataset of shape (1,) is a one-sample signal.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_hdf5("one.h5", {
            "Time": np.array([0.5]), "value": np.array([2.0])})
        signal_file = load_signal_file(path_str)
        np.testing.assert_array_equal(signal_file.signal_dict["value"],
                                      [2.0])

    @covers("LLFR-00134", "LLFR-00053", "HLFR-00006")
    def test_time_signal_is_top_level_time(self) -> None:
        """Only the top-level "Time" is the time signal.

        Inputs: none.
        Outputs: none.
        """
        time_array = self.time_array()
        path_str = self.write_hdf5("time.h5", {
            "Time": time_array, "engine/Time": time_array + 100,
            "engine/speed": time_array})
        signal_file = load_signal_file(path_str)
        np.testing.assert_array_equal(
            signal_file.signal_dict[TIME_SIGNAL_NAME_STR], time_array)
        np.testing.assert_array_equal(
            signal_file.signal_dict["engine/Time"], time_array + 100)

    @covers("LLFR-00053", "LLFR-00134", "LLFR-00012", "HLFR-00008")
    def test_time_in_a_group_or_other_case_is_not_time(self) -> None:
        """"time", "TIME" and "group/Time" are not the time signal.

        Inputs: none.
        Outputs: none.
        """
        time_array = self.time_array()
        for time_path_str in ("time", "TIME", "group/Time", "Time/Time"):
            with self.subTest(time_path_str=time_path_str):
                path_str = self.write_hdf5("no_time.h5", {
                    time_path_str: time_array, "signal": time_array})
                self.assert_content_check(path_str, TIME_SIGNAL_CHECK_STR)

    @covers("LLFR-00134", "HLFR-00005")
    def test_hdf5_extension_and_letter_case(self) -> None:
        """.h5, .hdf5, .H5 and .HDF5 files are all read as HDF5.

        Inputs: none.
        Outputs: none.
        """
        time_array = self.time_array()
        for file_name_str in ("data.h5", "data.hdf5", "DATA.H5",
                              "Data.HDF5"):
            with self.subTest(file_name_str=file_name_str):
                path_str = self.write_hdf5(file_name_str, {
                    "Time": time_array, "A": time_array})
                signal_file = load_signal_file(path_str)
                self.assertEqual(signal_file.signal_name_list,
                                 ["A", "Time"])

    @covers("LLFR-00134", "LLFR-00065")
    def test_nan_and_infinite_values_are_read_errors(self) -> None:
        """A NaN or infinite sample in a signal makes the file unreadable.

        Inputs: none.
        Outputs: none.
        """
        for bad_value_f in (np.nan, np.inf, -np.inf):
            with self.subTest(bad_value_f=bad_value_f):
                signal_array = np.ones(SAMPLE_COUNT_I)
                signal_array[3] = bad_value_f
                path_str = self.write_hdf5("bad.h5", {
                    "Time": self.time_array(), "group/A": signal_array})
                with self.assertRaises(FileReadError) as context:
                    load_signal_file(path_str)
                message_str = str(context.exception)
                self.assertIn("could not be read", message_str)
                self.assertIn("'group/A' sample 4", message_str)

    @covers("LLFR-00135", "LLFR-00134")
    def test_nan_in_an_ignored_dataset_is_ignored(self) -> None:
        """NaN values in a 2-D dataset don't matter: it is not read.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_hdf5("matrix_nan.h5", {
            "Time": self.time_array(), "A": self.time_array(),
            "matrix": np.full((2, 2), np.nan)})
        signal_file = load_signal_file(path_str)
        self.assertEqual(signal_file.signal_name_list, ["A", "Time"])


@requires_h5py
class Hdf5IgnoredDatasetTest(Hdf5FolderTest):
    """Datasets that are not signals, and the content checks."""

    @covers("LLFR-00135")
    def test_non_signal_datasets_are_ignored(self) -> None:
        """Matrices, scalars, text, compound, bool, complex are ignored.

        Inputs: none.
        Outputs: none.
        """
        time_array = self.time_array()
        compound_array = np.zeros(SAMPLE_COUNT_I,
                                  dtype=[("a", "f8"), ("b", "i4")])
        path_str = self.path("mixed.h5")
        with h5py.File(path_str, "w") as hdf5_file:
            hdf5_file.create_dataset("Time", data=time_array)
            hdf5_file.create_dataset("A", data=time_array)
            hdf5_file.create_dataset("matrix", data=np.ones((3, 3)))
            hdf5_file.create_dataset("cube", data=np.ones((2, 3, 1)))
            hdf5_file.create_dataset("group/scalar", data=2.5)
            hdf5_file.create_dataset("text", data="hello")
            hdf5_file.create_dataset(
                "texts", data=["a", "b", "c", "d", "e", "f"],
                dtype=h5py.string_dtype())
            hdf5_file.create_dataset("bytes", data=np.array(
                [b"a"] * SAMPLE_COUNT_I))
            hdf5_file.create_dataset("compound", data=compound_array)
            hdf5_file.create_dataset(
                "flags", data=np.zeros(SAMPLE_COUNT_I, dtype=bool))
            hdf5_file.create_dataset(
                "complex", data=np.ones(SAMPLE_COUNT_I, dtype=complex))
            hdf5_file.create_dataset("empty", data=np.zeros(0))
            hdf5_file.create_dataset("empty_row", data=np.zeros((1, 0)))
            hdf5_file.create_dataset("null", data=h5py.Empty("f8"))
            hdf5_file.create_group("empty_group")
            hdf5_file.attrs["note"] = "attributes are not datasets"
        signal_file = load_signal_file(path_str)
        self.assertEqual(signal_file.signal_name_list, ["A", "Time"])

    @covers("LLFR-00135", "LLFR-00012", "HLFR-00008")
    def test_no_time_signal(self) -> None:
        """A file whose signals have no "Time" fails the time check.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_hdf5("no_time.h5", {
            "A": self.time_array(), "B": self.time_array()})
        self.assert_content_check(path_str, TIME_SIGNAL_CHECK_STR)

    @covers("LLFR-00135", "LLFR-00012", "HLFR-00008")
    def test_time_that_is_not_a_vector_is_not_a_signal(self) -> None:
        """A 2-D or text "Time" dataset is ignored, so there is no time.

        Inputs: none.
        Outputs: none.
        """
        for time_data in (np.ones((SAMPLE_COUNT_I, 2)), "0 1 2", 1.0):
            with self.subTest(time_data=time_data):
                path_str = self.write_hdf5("bad_time.h5", {
                    "Time": time_data, "A": self.time_array()})
                self.assert_content_check(path_str, TIME_SIGNAL_CHECK_STR)

    @covers("LLFR-00135", "LLFR-00012", "HLFR-00008")
    def test_only_time_among_the_signals(self) -> None:
        """Only "Time" plus ignored datasets fails the other signal check.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_hdf5("only_time.h5", {
            "Time": self.time_array(), "matrix": np.ones((3, 3)),
            "group/text": "hello", "scalar": 1.0})
        self.assert_content_check(path_str, OTHER_SIGNAL_CHECK_STR)

    @covers("LLFR-00135", "LLFR-00012", "HLFR-00009")
    def test_different_sample_counts(self) -> None:
        """Signals of different lengths fail the sample count check.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_hdf5("lengths.h5", {
            "Time": self.time_array(), "group/short": np.arange(3.0)})
        with self.assertRaises(ContentCheckError) as context:
            load_signal_file(path_str)
        self.assertEqual(context.exception.failed_check_str,
                         SAMPLE_COUNT_CHECK_STR)
        self.assertIn("'group/short' has 3", str(context.exception))

    @covers("LLFR-00135", "HLFR-00009")
    def test_ignored_datasets_are_not_counted(self) -> None:
        """Ignored datasets of other lengths don't fail the count check.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_hdf5("ignored_lengths.h5", {
            "Time": self.time_array(), "A": self.time_array(),
            "matrix": np.ones((10, 4)),
            "names": np.array([b"x"] * 3)})
        signal_file = load_signal_file(path_str)
        self.assertEqual(signal_file.signal_name_list, ["A", "Time"])


@requires_h5py
class Hdf5CorruptFileTest(Hdf5FolderTest):
    """Files with an HDF5 extension that are not valid HDF5."""

    @covers("LLFR-00008", "HLFR-00002")
    def test_corrupt_files_are_read_errors(self) -> None:
        """Text, random bytes, an empty file and a cut HDF5 file fail.

        Inputs: none.
        Outputs: none.
        """
        valid_path_str = self.write_hdf5("valid.h5", {
            "Time": np.arange(1000.0), "A": np.arange(1000.0)})
        with open(valid_path_str, "rb") as binary_file:
            valid_bytes = binary_file.read()
        random_generator = np.random.default_rng(3)
        content_dict = {
            "text.h5": b"Time,A\n0,1\n",
            "random.hdf5": random_generator.bytes(4096),
            "empty.h5": b"",
            "cut.h5": valid_bytes[:len(valid_bytes) // 3],
            "header_only.h5": valid_bytes[:8],
        }
        for file_name_str, content_bytes in content_dict.items():
            with self.subTest(file_name_str=file_name_str):
                path_str = self.write_bytes(file_name_str, content_bytes)
                with self.assertRaises(FileReadError) as context:
                    load_signal_file(path_str)
                self.assertIn("could not be read", str(context.exception))
                self.assertIn(file_name_str, str(context.exception))

    @covers("LLFR-00008", "HLFR-00005")
    def test_hdf5_content_with_csv_extension(self) -> None:
        """An HDF5 file renamed to .csv is read as CSV and fails.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_hdf5("data.csv", {
            "Time": self.time_array(), "A": self.time_array()})
        with self.assertRaises(FileReadError):
            load_signal_file(path_str)


if __name__ == "__main__":
    unittest.main()
