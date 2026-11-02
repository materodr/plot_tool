"""File dialogs that are built once and shown quickly (HLFR-00091).

LLFR-00406 asks every file dialog to appear within 0.6 s of the click,
the first click after the start included. The app keeps the system's
own (native) file dialogs. It builds each QFileDialog once, right after
the main window is shown (LLFR-00406, note: "The app may prepare the
dialogs after the main window is shown"), and shows the same object
again on every later click, so no click pays for building and styling
the dialog.

Measured on the macOS build check (issue #154): Qt creates a new system
panel each time it shows a native dialog, so the panel itself takes
about 0.3 to 0.5 s on every click; Qt's own (not native) dialog, reused,
took about 0.1 s, but the owner chose to keep the system's dialogs and
the 0.6 s limit. The first system panel of a process is the slowest, so
on macOS the preparation also shows and closes one open and one save
panel at once (load_system_panels), before the user clicks.

A FileDialogPool keeps these dialogs:

- ``register(key_str, build_function)`` names a dialog and the factory
  function that builds it (a function of no arguments returning a
  QFileDialog, for example ``MainWindow.build_layout_save_dialog``);
- ``prepare_all()`` builds and styles every registered dialog that is
  not built yet, and, on macOS, makes the system load its panels once;
- ``prepared_dialog(key_str, start_folder_str)`` returns the dialog of a
  key, built on first use when it was not prepared, reset for a new
  use: it shows the given folder (LLFR-00204, LLFR-00220), its first
  name filter and, in Qt's own dialog (used where the system has none),
  no file name left from an earlier use;
- ``run_file_dialog(dialog)`` shows a dialog modally and returns the
  chosen path ("" when cancelled).

Any other file dialog is made fast the same way: register its factory
function with a new key and ask for it with prepared_dialog, as the
Save signals dialog does.
"""

import sys
import time

from PyQt6 import sip
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QLineEdit

# LLFR-00406: the name of the field where a file name is typed in Qt's
# own file dialog (used where the system has no file dialog, as in the
# tests).
FILE_NAME_FIELD_NAME_STR = "fileNameEdit"
# LLFR-00406: the platform whose system file panels are slow on their
# first use in a process.
MACOS_PLATFORM_STR = "darwin"


def run_file_dialog(dialog) -> str:
    """Show a file dialog modally and return the chosen path.

    Inputs:
        dialog: a QFileDialog.
    Outputs: the first selected path, or "" when the user cancelled
        (LLFR-00007, LLFR-00130, LLFR-00222).
    """
    # LLFR-00005, LLFR-00128, LLFR-00219, LLFR-00221: the modal dialog.
    if dialog.exec() != QDialog.DialogCode.Accepted.value:
        return ""
    selected_file_list = dialog.selectedFiles()
    if not selected_file_list:
        return ""
    return str(selected_file_list[0])


def reset_for_new_use(dialog, start_folder_str: str) -> None:
    """Make a dialog shown before look as a newly built one.

    Inputs:
        dialog: a QFileDialog.
        start_folder_str: the folder to show; "" keeps the folder the
            dialog shows now (the folder Qt chose when it was built, or
            the one it showed last).
    Outputs: none. The first name filter is chosen and the typed file
        name of an earlier use is cleared.
    """
    # LLFR-00204, LLFR-00220: the folder chosen by the controllers.
    if start_folder_str:
        dialog.setDirectory(start_folder_str)
    # LLFR-00128, LLFR-00219, LLFR-00221: the filters are kept as they
    # were built; the first one is chosen, as in a new dialog.
    name_filter_list = dialog.nameFilters()
    if name_filter_list:
        dialog.selectNameFilter(name_filter_list[0])
    # LLFR-00219, LLFR-00406: a name typed before a cancel is not kept.
    file_name_field = dialog.findChild(QLineEdit, FILE_NAME_FIELD_NAME_STR)
    if file_name_field is not None:
        file_name_field.clear()


class FileDialogPool:
    """The app's file dialogs, each built once and reused (LLFR-00406).

    Inputs:
        platform_str: the platform name (sys.platform by default); on
            macOS prepare_all also loads the system's file panels.
    Attributes:
        build_function_dict: key -> factory function of the dialog.
        dialog_dict: key -> the QFileDialog built for it.
        prepared_b: True once prepare_all has run.
        prepare_duration_s: how long prepare_all took, in seconds.
        system_panels_loaded_b: True once load_system_panels has run.
    """

    def __init__(self, platform_str: str = sys.platform) -> None:
        """Create an empty pool.

        Inputs:
            platform_str: the platform name, as sys.platform.
        Outputs: none.
        """
        # LLFR-00406: no dialog is built before prepare_all or first use.
        self.platform_str = str(platform_str)
        self.system_panels_loaded_b = False
        self.build_function_dict = {}
        self.dialog_dict = {}
        self.prepared_b = False
        self.prepare_duration_s = 0.0

    def register(self, key_str: str, build_function) -> None:
        """Name a dialog and the function that builds it.

        Inputs:
            key_str: the name of the dialog, for example "open_file".
            build_function: function without arguments that returns a
                new QFileDialog, not shown.
        Outputs: none.
        """
        # LLFR-00406: every file dialog of the app is kept here.
        self.build_function_dict[str(key_str)] = build_function

    def key_list(self) -> list:
        """Return the names of the registered dialogs.

        Inputs: none.
        Outputs: a list of str, in the order they were registered.
        """
        # LLFR-00406: the dialogs prepared after the window is shown.
        return list(self.build_function_dict)

    def is_built(self, key_str: str) -> bool:
        """Tell whether the dialog of a key exists.

        Inputs:
            key_str: a registered name.
        Outputs: True when its QFileDialog was built and not deleted.
        """
        # LLFR-00406: a dialog deleted with its parent is built again.
        dialog = self.dialog_dict.get(key_str)
        return dialog is not None and not sip.isdeleted(dialog)

    def dialog(self, key_str: str):
        """Return the dialog of a key, building it on first use.

        Inputs:
            key_str: a registered name.
        Outputs: the QFileDialog; the same object on every call.
        """
        # LLFR-00406: built once, then shown again on every click.
        if not self.is_built(key_str):
            self.dialog_dict[key_str] = self.build_function_dict[key_str]()
        return self.dialog_dict[key_str]

    def prepared_dialog(self, key_str: str, start_folder_str: str = ""):
        """Return the dialog of a key, ready to be shown.

        Inputs:
            key_str: a registered name.
            start_folder_str: the folder the dialog must show; "" keeps
                its current folder.
        Outputs: the QFileDialog, reset as by reset_for_new_use.
        """
        # LLFR-00406, LLFR-00204, LLFR-00220: the same dialog, in the
        # folder the controller chose.
        dialog = self.dialog(key_str)
        reset_for_new_use(dialog, start_folder_str)
        return dialog

    def prepare_all(self) -> None:
        """Build and style every registered dialog not built yet.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00406: after the main window is shown, so that the first
        # click shows a dialog that is already built and styled.
        start_s = time.perf_counter()
        for key_str in self.key_list():
            self.dialog(key_str).ensurePolished()
        if self.platform_str == MACOS_PLATFORM_STR:
            self.load_system_panels()
        self.prepared_b = True
        self.prepare_duration_s = time.perf_counter() - start_s

    def load_system_panels(self) -> None:
        """Make macOS load its open and save panels once.

        Inputs: none.
        Outputs: none. One dialog of each kind (open and save) is shown
            and closed in the same step of the event loop, before the
            screen is drawn again, and the main window gets the keyboard
            focus back.
        """
        # LLFR-00406: the first system panel of a process is the slowest
        # (measured on the macOS build check: about 0.6 s for the first
        # Open file dialog without this step, 0.4 to 0.5 s with it);
        # showing one here moves that wait to the start, while the user
        # looks at the new window.
        if self.system_panels_loaded_b:
            return
        self.system_panels_loaded_b = True
        shown_mode_set = set()
        for key_str in self.key_list():
            dialog = self.dialog(key_str)
            accept_mode = dialog.acceptMode()
            if accept_mode in shown_mode_set:
                continue
            shown_mode_set.add(accept_mode)
            dialog.setVisible(True)
            dialog.setVisible(False)
            parent = dialog.parentWidget()
            if parent is not None:
                # LLFR-00406: the main window keeps the keyboard focus.
                QTimer.singleShot(0, parent.activateWindow)
