"""File controller: runs the open-file flow (HLFR-00004, HLFR-00010).

It talks to the view only through plain method calls (no Qt code), so
it can be tested with a fake view (COR-00003, COR-00009). The view must
offer ``ask_open_file_path(start_folder_str)``, ``show_file_open_error``,
``ask_replace_file``, ``show_signal_names`` and
``finish_open_file_button``.
"""

import os
import sys

from model.errors import FileOpenError
from model.file_loader import load_signal_file

# PCR-00025: start of the message shown when the loader fails in an
# unexpected way, so the app reports it instead of crashing.
UNEXPECTED_ERROR_MESSAGE_STR = (
    "The file '{path}' could not be read because of an unexpected "
    "error: {error}")
# LLFR-00204: suffix of a macOS app bundle folder (plot_tool.app).
APP_BUNDLE_SUFFIX_STR = ".app"
# LLFR-00204: folders between the bundle and its executable
# (plot_tool.app/Contents/MacOS/plot_tool).
BUNDLE_CONTENTS_NAME_STR = "Contents"
BUNDLE_MACOS_NAME_STR = "MacOS"
# LLFR-00204: the repository folder, parent of the src folder that
# holds this controller package, used when the app runs from source.
REPOSITORY_FOLDER_STR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))


def first_start_folder_str(frozen_b: bool = None,
                           executable_path_str: str = None,
                           repository_folder_str: str = None) -> str:
    """Return the folder the first file selection dialog shows.

    For the PyInstaller build (COR-00007) this is the folder that holds
    the executable. On macOS the executable sits inside the app bundle,
    in ``plot_tool.app/Contents/MacOS``; the folder that holds the
    bundle is returned instead, which is the folder the user sees in
    Finder. When the app runs from source, it is the repository folder.

    Inputs:
        frozen_b: whether the app runs from a PyInstaller build; read
            from sys.frozen when None.
        executable_path_str: path of the running executable; read from
            sys.executable when None.
        repository_folder_str: the repository folder;
            REPOSITORY_FOLDER_STR when None.
    Outputs: the absolute path of the folder.
    """
    # LLFR-00204: the first dialog shows the folder of the app.
    if frozen_b is None:
        frozen_b = bool(getattr(sys, "frozen", False))
    if not frozen_b:
        # LLFR-00204: run from source, the repository folder.
        if repository_folder_str is None:
            repository_folder_str = REPOSITORY_FOLDER_STR
        return os.path.abspath(repository_folder_str)
    if executable_path_str is None:
        executable_path_str = sys.executable
    executable_folder_str = os.path.dirname(
        os.path.abspath(executable_path_str))
    # LLFR-00204: on macOS, the folder that holds plot_tool.app, not
    # Contents/MacOS inside it.
    contents_folder_str = os.path.dirname(executable_folder_str)
    bundle_folder_str = os.path.dirname(contents_folder_str)
    if (os.path.basename(executable_folder_str) == BUNDLE_MACOS_NAME_STR
            and os.path.basename(contents_folder_str)
            == BUNDLE_CONTENTS_NAME_STR
            and bundle_folder_str.endswith(APP_BUNDLE_SUFFIX_STR)):
        return os.path.dirname(bundle_folder_str)
    # LLFR-00204: Windows (and any other build), the executable's folder.
    return executable_folder_str


class FileController:
    """Opens files chosen by the user and keeps the current file.

    Inputs:
        view: the object that shows dialogs and the signal list.
        load_function: function that takes a path and returns a
            SignalFile or raises FileOpenError; load_signal_file by
            default.
        start_folder_str: folder the first file selection dialog shows;
            first_start_folder_str() when None.
    Attributes:
        current_file: the open SignalFile, or None before the first
            file is opened.
        dialog_folder_str: folder the next file selection dialog shows.
    """

    def __init__(self, view, load_function=load_signal_file,
                 start_folder_str: str = None) -> None:
        """Store the view and the load function; no file is open yet.

        Inputs:
            view: the view facade.
            load_function: the function that opens a file.
            start_folder_str: folder of the first dialog, or None for
                the folder of the app (first_start_folder_str).
        Outputs: none.
        """
        # LLFR-00006: the function used to open the selected file.
        self.view = view
        self.load_function = load_function
        self.current_file = None
        # LLFR-00204: the first dialog shows the folder of the app.
        if start_folder_str is None:
            start_folder_str = first_start_folder_str()
        self.dialog_folder_str = start_folder_str
        self.file_opened_listener_list = []

    def add_file_opened_listener(self, listener) -> None:
        """Register a function called after a file has been opened.

        Inputs:
            listener: a function taking (signal_file, replaced_b), where
                replaced_b is True when the new file replaced another.
        Outputs: none.
        """
        # LLFR-00015, LLFR-00016: the plot controller resets the tabs
        # and plots when a file is replaced.
        self.file_opened_listener_list.append(listener)

    def open_file_requested(self) -> None:
        """Run the open-file flow started by the Open file button.

        Asks for a path, opens the file, asks for confirmation when
        another file is open, and shows the new signal names. The
        button always returns to normal at the end.

        Inputs: none.
        Outputs: none.
        """
        try:
            self._open_file()
        finally:
            # LLFR-00003: the function started by the button finished,
            # whatever happened.
            self.view.finish_open_file_button()

    def _open_file(self) -> None:
        """Run the steps of the open-file flow.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00005, LLFR-00204: show the file selection dialog in the
        # folder of the app, or of the last file opened successfully.
        path_str = self.view.ask_open_file_path(self.dialog_folder_str)
        if not path_str:
            # LLFR-00007: cancelled, keep the file and the list.
            return
        # LLFR-00006: try to open the selected file.
        try:
            signal_file = self.load_function(path_str)
        except FileOpenError as error:
            # LLFR-00008, LLFR-00009, LLFR-00011, LLFR-00012: show the
            # File Open Error box. LLFR-00010: keep the previous file.
            self.view.show_file_open_error(str(error))
            return
        except Exception as error:
            # LLFR-00008, LLFR-00010: an unexpected failure is reported
            # as an unreadable file instead of crashing (PCR-00025).
            self.view.show_file_open_error(
                UNEXPECTED_ERROR_MESSAGE_STR.format(path=path_str,
                                                    error=error))
            return
        # HLFR-00010: ask only when the new file can be opened and
        # another file is open.
        replaced_b = self.current_file is not None
        if replaced_b and not self.view.ask_replace_file():
            # LLFR-00014: declined, keep the current file open.
            return
        # LLFR-00013: close the current file and open the selected one.
        self.current_file = signal_file
        # LLFR-00204: only a successful open moves the dialog folder;
        # a cancel, a failed open or a declined replace keeps it.
        self.dialog_folder_str = os.path.dirname(os.path.abspath(path_str))
        # LLFR-00017, LLFR-00054: show the new names, including Time.
        self.view.show_signal_names(signal_file.signal_name_list)
        # LLFR-00015, LLFR-00016: tell the listeners about the new file.
        for listener in list(self.file_opened_listener_list):
            listener(signal_file, replaced_b)
