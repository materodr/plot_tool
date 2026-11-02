"""File controller: runs the open-file flow (HLFR-00004, HLFR-00010).

It talks to the view only through plain method calls (no Qt code), so
it can be tested with a fake view (COR-00003, COR-00009). The view must
offer ``ask_open_file_path(start_folder_str)``, ``show_file_open_error``,
``ask_time_signal_name``, ``ask_replace_file``, ``set_time_signal_name``,
``show_signal_names``, ``finish_open_file_button``,
``show_loading_indication(text_str)`` and ``hide_loading_indication()``.

``show_loading_indication`` shows the busy pointer and the text in the
status line of the signal list panel, and ``hide_loading_indication``
restores the normal pointer and empties the status line (LLFR-00418).

``ask_time_signal_name(prompt_str, name_list, search_function,
no_match_text_str, check_function)`` shows the time signal window
(LLFR-00325) and returns the confirmed name, or None when the user
cancels. ``search_function(text_str)`` returns the names that match the
search box text, in the order to show them; ``check_function(name_str)``
returns the reason a name can't be the time signal ("" when it can), and
the window stays open while there is one (LLFR-00329).
"""

import os
import sys

from model.errors import FileOpenError
from model.file_loader import load_signal_file
from model.signal_file import increasing_check_reason
from model.signal_search import NO_MATCH_TEXT_STR, search_signals

# LLFR-00418: the text of the status line while a file is read.
LOADING_TEXT_STR = "Loading..."
# LLFR-00325: the text of the time signal window.
TIME_SIGNAL_PROMPT_STR = "Choose the signal that goes on the x-axis"

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

        Asks for a path, asks for confirmation when another file is
        open, reads the file while the loading indication is shown, and
        shows the new signal names (LLFR-00328). The button always
        returns to normal at the end.

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
        # LLFR-00328 step 1, HLFR-00010: when another file is open, ask
        # right away, before the selected file is read.
        replaced_b = self.current_file is not None
        if replaced_b and not self.view.ask_replace_file():
            # LLFR-00014: declined, keep the current file open, do not
            # read the selected file and show no other message.
            return
        # LLFR-00006, LLFR-00328 step 2: read and check the file.
        signal_file, error_message_str = self._read_file(path_str)
        if signal_file is None:
            # LLFR-00008, LLFR-00009, LLFR-00011, LLFR-00012: show the
            # File Open Error box, after the loading indication is gone
            # (LLFR-00418). LLFR-00010: keep the previous file, its
            # plots, signal list, synthetic signals and undo history.
            self.view.show_file_open_error(error_message_str)
            return
        # LLFR-00328 step 3: the user chooses the time signal when no
        # signal is named "Time".
        if (signal_file.needs_time_signal_choice_b
                and not self._choose_time_signal(signal_file)):
            # LLFR-00327: cancelled, nothing is opened and no message is
            # shown; the current file and its list are kept (LLFR-00010).
            return
        # LLFR-00328 step 4, LLFR-00013: only now close the current
        # file and open the selected one.
        self.current_file = signal_file
        # LLFR-00204: only a successful open moves the dialog folder;
        # a cancel, a failed open or a declined replace keeps it.
        self.dialog_folder_str = os.path.dirname(os.path.abspath(path_str))
        # LLFR-00332: the time signal name is shown in green.
        self.view.set_time_signal_name(signal_file.time_signal_name_str)
        # LLFR-00017, LLFR-00054: show the new names, including the time
        # signal.
        self.view.show_signal_names(signal_file.signal_name_list)
        # LLFR-00015, LLFR-00016: tell the listeners about the new file.
        for listener in list(self.file_opened_listener_list):
            listener(signal_file, replaced_b)

    def _read_file(self, path_str: str) -> tuple:
        """Read and check a file while the loading indication is shown.

        Inputs:
            path_str: the path of the selected file.
        Outputs: (signal_file, "") when the file can be opened, or
            (None, message_str) with the text of the File Open Error box
            when it can't.
        """
        # LLFR-00418: the busy pointer and "Loading..." while the file
        # is read and checked, for the first file as for a replacement.
        self.view.show_loading_indication(LOADING_TEXT_STR)
        try:
            # LLFR-00006: try to open the selected file.
            return self.load_function(path_str), ""
        except FileOpenError as error:
            # LLFR-00008, LLFR-00009, LLFR-00011, LLFR-00012: the reason
            # given by the loader.
            return None, str(error)
        except Exception as error:
            # LLFR-00008, LLFR-00010: an unexpected failure is reported
            # as an unreadable file instead of crashing (PCR-00025).
            return None, UNEXPECTED_ERROR_MESSAGE_STR.format(
                path=path_str, error=error)
        finally:
            # LLFR-00418: reading ended, whatever the result; remove the
            # indication before any box or window is shown.
            self.view.hide_loading_indication()

    def _choose_time_signal(self, signal_file) -> bool:
        """Ask the user for the time signal of a file.

        Inputs:
            signal_file: the SignalFile just read, with no signal that
                matches the time signal name.
        Outputs: True when the user confirmed a signal, which is now the
            file's time signal; False when the user cancelled.
        """
        # LLFR-00325: every signal of the file, in the file's order.
        name_list = list(signal_file.signal_name_list)

        def matching_names(text_str: str) -> list:
            """Return the names that match the search box text.

            Inputs:
                text_str: the text of the window's search box.
            Outputs: the matching names, in the order to show them.
            """
            # LLFR-00325, LLFR-00285: the rules and the order of the
            # signal list panel's search.
            return search_signals(name_list, text_str)

        def check_name(name_str: str) -> str:
            """Return why a signal can't be the time signal.

            Inputs:
                name_str: the name selected in the window.
            Outputs: the reason, or "" when the signal can be used.
            """
            # LLFR-00329: the signal on the x-axis must always increase.
            return increasing_check_reason(
                name_str, signal_file.signal_array(name_str))

        chosen_name_str = self.view.ask_time_signal_name(
            TIME_SIGNAL_PROMPT_STR, name_list, matching_names,
            NO_MATCH_TEXT_STR, check_name)
        if not chosen_name_str:
            # LLFR-00327: the window was cancelled.
            return False
        # LLFR-00326, LLFR-00329: the chosen signal becomes the time
        # signal; a signal that does not increase is never used, even
        # when a window let it through.
        return signal_file.choose_time_signal(str(chosen_name_str)) == ""
