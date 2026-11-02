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
# LLFR-00005: what a test patches to answer the Open file dialog without
# a modal dialog: ``mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
# return_value=path_str)`` ("" cancels). The mock is called with the
# QFileDialog that would be shown.
OPEN_FILE_DIALOG_TARGET_STR = (
    "view.main_window.MainWindow.run_open_file_dialog")
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
        install_file_dialog_guard()
    return application


def install_file_dialog_guard() -> None:
    """Make a file dialog that a test forgot to answer return at once.

    A real modal QFileDialog would wait forever for a user in CI. A test
    must answer it (patch the window's run_..._dialog method, the
    dialog's ``exec``, or OPEN_FILE_DIALOG_TARGET_STR); when it does
    not, the guard prints a warning and the dialog is cancelled, so the
    test fails on its checks instead of hanging.

    Inputs: none.
    Outputs: none. QFileDialog.exec is replaced for the test run.
    """
    from PyQt6.QtWidgets import QDialog, QFileDialog

    def cancel_unanswered_dialog(dialog) -> int:
        """Report and cancel a file dialog that no test answered.

        Inputs:
            dialog: the QFileDialog a test tried to show.
        Outputs: the int value of QDialog.DialogCode.Rejected.
        """
        print(f"warning: a test showed the file dialog "
              f"'{dialog.windowTitle()}' without answering it; it was "
              f"cancelled", file=sys.stderr)
        return QDialog.DialogCode.Rejected.value

    QFileDialog.exec = cancel_unanswered_dialog


def button_name(button) -> str:
    """Return the name a top panel button is called by.

    The top panel buttons show only an icon (LLFR-00158); the name the
    requirements call a button by ("Open file", "Data tip", ...) is the
    first line of its button tip (LLFR-00181), also set as its
    accessible name. Tests find and check buttons by this name, never by
    ``text()``.

    Inputs:
        button: a QPushButton of the top panel.
    Outputs: the button's accessible name.
    """
    return button.accessibleName()


def button_tip_line_list(button) -> list:
    """Return the lines of a top panel button's tip, as plain text.

    The tip is the button's name alone, as plain text, or rich text with
    the name on the first line and the shortcut or mouse use below it
    (LLFR-00181, LLFR-00213, LLFR-00214).

    Inputs:
        button: a QPushButton of the top panel.
    Outputs: a list of str, one per line of the tip, the name first.
    """
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QTextDocument
    tip_str = button.toolTip()
    if not Qt.mightBeRichText(tip_str):
        return tip_str.split("\n")
    document = QTextDocument()
    document.setHtml(tip_str)
    return document.toPlainText().split("\n")
