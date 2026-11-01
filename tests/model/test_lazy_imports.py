"""Tests for the lazy imports of the file loaders (issue #67).

pandas, scipy.io and h5py are only imported when a file of their format
is opened, so the app window shows without waiting for them. Each test
runs in a fresh Python process, because the test process has already
imported these libraries.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

from tests.support import (
    REPOSITORY_ROOT_STR, SOURCE_FOLDER_STR, covers, requires_h5py)

# Run in a child process: import the loader, then open each file given
# on the command line, and print which libraries are imported after
# each step as one JSON list.
CHILD_SCRIPT_STR = """
import json, sys
sys.path.insert(0, sys.argv[1])
from model import file_loader
library_tuple = ("pandas", "scipy.io", "h5py")
def imported():
    return {name: name in sys.modules for name in library_tuple}
step_list = [imported()]
for path in sys.argv[2:]:
    file_loader.load_signal_file(path)
    step_list.append(imported())
print(json.dumps(step_list))
"""


def imported_library_list(path_list: list) -> list:
    """Load files in a fresh process and report the imported libraries.

    Inputs:
        path_list: the files to open, in order, after the import.
    Outputs: a list of dicts library name -> imported (bool): one after
        importing model.file_loader, then one after each opened file.
    """
    completed = subprocess.run(
        [sys.executable, "-c", CHILD_SCRIPT_STR, SOURCE_FOLDER_STR]
        + path_list, capture_output=True, text=True, check=True,
        cwd=REPOSITORY_ROOT_STR, timeout=120)
    return json.loads(completed.stdout.strip().splitlines()[-1])


class LazyImportTest(unittest.TestCase):
    """Check that each loader library is imported only when needed."""

    def setUp(self) -> None:
        """Create a folder with one CSV and one MAT file.

        Inputs: none.
        Outputs: none.
        """
        temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_folder.cleanup)
        self.folder_str = temporary_folder.name
        self.csv_path_str = os.path.join(self.folder_str, "data.csv")
        with open(self.csv_path_str, "w", encoding="utf-8") as csv_file:
            csv_file.write("Time,Speed\n0,1\n1,2\n")
        import numpy as np
        import scipy.io
        self.mat_path_str = os.path.join(self.folder_str, "data.mat")
        scipy.io.savemat(self.mat_path_str, {
            "Time": np.array([0.0, 1.0]), "Speed": np.array([1.0, 2.0])})

    @covers("LLFR-00059", "LLFR-00062", "LLFR-00134")
    def test_importing_the_loader_imports_no_reader_library(self) -> None:
        """Importing model.file_loader leaves pandas, scipy.io, h5py out.

        Inputs: none.
        Outputs: none.
        """
        step_list = imported_library_list([])
        self.assertEqual(step_list[0], {"pandas": False, "scipy.io": False,
                                        "h5py": False})

    @covers("LLFR-00059", "LLFR-00062")
    def test_each_format_imports_only_its_library(self) -> None:
        """A CSV file imports pandas only; a MAT file then imports scipy.

        Inputs: none.
        Outputs: none.
        """
        step_list = imported_library_list([self.csv_path_str,
                                           self.mat_path_str])
        self.assertEqual(step_list[1], {"pandas": True, "scipy.io": False,
                                        "h5py": False})
        self.assertTrue(step_list[2]["scipy.io"])
        self.assertFalse(step_list[2]["h5py"])

    @requires_h5py
    @covers("LLFR-00134")
    def test_hdf5_file_imports_h5py(self) -> None:
        """An HDF5 file imports h5py, and still opens.

        Inputs: none.
        Outputs: none.
        """
        import h5py
        import numpy as np
        hdf5_path_str = os.path.join(self.folder_str, "data.h5")
        with h5py.File(hdf5_path_str, "w") as hdf5_file:
            hdf5_file["Time"] = np.array([0.0, 1.0])
            hdf5_file["Speed"] = np.array([1.0, 2.0])
        step_list = imported_library_list([hdf5_path_str])
        self.assertTrue(step_list[1]["h5py"])
        self.assertFalse(step_list[1]["pandas"])

    @covers("LLFR-00134")
    def test_hdf5_library_is_imported_once_and_kept(self) -> None:
        """hdf5_library imports h5py once and keeps the result.

        Inputs: none.
        Outputs: none.
        """
        from unittest import mock
        from model import file_loader
        with mock.patch.object(file_loader, "h5py",
                               file_loader.H5PY_NOT_IMPORTED):
            first_library = file_loader.hdf5_library()
            self.assertIsNot(first_library, file_loader.H5PY_NOT_IMPORTED)
            self.assertIs(file_loader.h5py, first_library)
            self.assertIs(file_loader.hdf5_library(), first_library)
        sentinel_library = object()
        with mock.patch.object(file_loader, "h5py", sentinel_library):
            self.assertIs(file_loader.hdf5_library(), sentinel_library)
        with mock.patch.object(file_loader, "h5py", None):
            self.assertIsNone(file_loader.hdf5_library())


if __name__ == "__main__":
    unittest.main()
