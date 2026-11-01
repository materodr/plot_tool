"""Shared helpers for the plot_tool tests.

- Puts ``src`` on the import path, so tests import ``model``, ``view``
  and ``controller`` as ``src/main.py`` does.
- ``covers`` tags a test with the requirement IDs it checks; the test
  matrix (tests/build_test_matrix.py) is built from these tags.
- ``requires_qt`` skips a test when PyQt6 is not installed, and
  ``get_qt_application`` returns the single offscreen QApplication.
- ``requires_h5py`` skips a test when h5py (HDF5 files) is not installed.
"""

import importlib.util
import os
import sys
import unittest

REPOSITORY_ROOT_STR = os.path.dirname(os.path.dirname(os.path.abspath(
    __file__)))
SOURCE_FOLDER_STR = os.path.join(REPOSITORY_ROOT_STR, "src")
if SOURCE_FOLDER_STR not in sys.path:
    sys.path.insert(0, SOURCE_FOLDER_STR)

QT_AVAILABLE_B = importlib.util.find_spec("PyQt6") is not None
H5PY_AVAILABLE_B = importlib.util.find_spec("h5py") is not None
COVERED_ATTRIBUTE_STR = "covered_requirement_list"


def covers(*requirement_id_tuple: str):
    """Tag a test function with the requirement IDs it checks.

    Inputs:
        requirement_id_tuple: one or more IDs such as ``"LLFR-00012"``.
    Outputs: a decorator that stores the IDs on the test function in the
        attribute named by COVERED_ATTRIBUTE_STR and returns it unchanged.
    """
    def decorate(test_function):
        """Store the IDs on test_function and return it.

        Inputs:
            test_function: the test method being decorated.
        Outputs: the same test method.
        """
        setattr(test_function, COVERED_ATTRIBUTE_STR,
                list(requirement_id_tuple))
        return test_function
    return decorate


requires_qt = unittest.skipUnless(QT_AVAILABLE_B, "PyQt6 is not installed")
requires_h5py = unittest.skipUnless(H5PY_AVAILABLE_B,
                                    "h5py is not installed")


def get_qt_application():
    """Return the QApplication shared by all GUI tests, creating it once.

    Inputs: none.
    Outputs: the QApplication instance, running on the offscreen platform
        unless QT_QPA_PLATFORM is already set.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application
