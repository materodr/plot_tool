"""File controller: opens and closes the data files (HLFR-00004).

Several data files can be open at the same time (HLFR-00113). Opening a
file adds it to the open files, with no question (HLFR-00117), and each
file gets a number (HLFR-00114) and a prefix for its signal names
(HLFR-00115); the files are kept in a model.data_files.DataFileSet.
Closing a file, or all files (HLFR-00118, HLFR-00119), removes them from
the set and tells the listeners, which remove the signals, the synthetic
signals and the curves.

It talks to the view only through plain method calls (no Qt code), so
it can be tested with a fake view (COR-00003, COR-00009). The view must
offer ``ask_open_file_path(start_folder_str)`` (a path, "" when
cancelled, or a list of paths), ``show_file_open_error``,
``show_open_files_limit_notification``,
``show_refused_files_notification``, ``ask_time_signal_name``,
``finish_open_file_button``, ``show_loading_indication()``,
``hide_loading_indication()``, and, for the file menu of the signal
list (LLFR-00919), ``ask_close_file(question_str)`` and
``ask_close_all_files(question_str)``, which return True when the user
proceeds (LLFR-00920, LLFR-00930).

``show_loading_indication`` shows the busy pointer and the loading title
of the main window, and ``hide_loading_indication`` restores the normal
pointer and the normal title (LLFR-00418, LLFR-00560, LLFR-00562).

``ask_time_signal_name(prompt_str, name_list, search_function,
no_match_text_str, check_function, file_name_str=...)`` shows the time
signal window (LLFR-00325) for the file named file_name_str (its name
with its extension, without its folder, LLFR-00953) and returns the
confirmed name, or None when the user cancels.
``search_function(text_str)`` returns the names that match the search
box text, in the order to show them; ``check_function(name_str)``
returns the reason a name can't be the time signal ("" when it can), and
the window stays open while there is one (LLFR-00329).
"""

import os
import sys

from model.data_files import DataFileSet, selection_order_list
from model.errors import FileOpenError
from model.file_loader import load_signal_file
from model.signal_file import increasing_check_reason
from model.signal_search import NO_MATCH_TEXT_STR, search_signals

# LLFR-00325: the text of the time signal window.
TIME_SIGNAL_PROMPT_STR = "Choose the signal that goes on the x-axis"

# PCR-00025: start of the message shown when the loader fails in an
# unexpected way, so the app reports it instead of crashing.
UNEXPECTED_ERROR_MESSAGE_STR = (
    "The file '{name}' could not be read because of an unexpected "
    "error: {error}")
# LLFR-00892: the box shown in place of the dialog with 10 files open.
OPEN_FILES_LIMIT_MESSAGE_STR = (
    "10 files are already open. Close one of them to make room for "
    "another file.")
# LLFR-00894, LLFR-00950, LLFR-00952: the lines of the box that lists
# the refused files.
ALREADY_OPEN_REASON_STR = "{name}: already open as file{number}."
LIMIT_REASON_STR = "{name}: not opened, because 10 files are already open."
# LLFR-00951: the entries of the File Open Error box are separated by
# an empty line.
ENTRY_SEPARATOR_STR = "\n\n"
# LLFR-00920: the question asked before one data file is closed. The
# third point depends on whether other files are left.
CLOSE_FILE_QUESTION_STR = "Do you want to close {row}?"
CLOSE_FILE_SIGNALS_POINT_STR = (
    "Its signals and the synthetic signals computed from them will be "
    "removed from the signal list and from the plots.")
CLOSE_TABS_POINT_STR = "The tabs left with no plot will be closed."
CLOSE_FILE_MARKERS_POINT_STR = (
    "The flags and areas outside the time range of the files left will "
    "be deleted.")
CLOSE_LAST_FILE_MARKERS_POINT_STR = (
    "Every flag and every area will be deleted, because no file is left.")
CLOSE_HISTORY_POINT_STR = "The undo and redo history will be cleared."
# LLFR-00930: the question asked once before every data file is closed.
CLOSE_ALL_FILES_QUESTION_STR = "Do you want to close all the files?"
CLOSE_ALL_FILES_POINT_STR = "All the open data files will be closed."
CLOSE_ALL_SIGNALS_POINT_STR = (
    "Their signals and synthetic signals will be removed from the signal "
    "list and from the plots.")
# LLFR-00920, LLFR-00930: each point of a question on its own line.
QUESTION_POINT_FORMAT_STR = "- {point}"
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


def question_text(question_str: str, point_list: list) -> str:
    """Return the text of a question with the points it says.

    Inputs:
        question_str: the question, for example "Do you want to close
            file1_run.csv?".
        point_list: the sentences that say what proceeding does.
    Outputs: the question, an empty line and one "- " line per point.
    """
    # LLFR-00920, LLFR-00930: the consequences, one per line.
    point_text_str = "\n".join(
        QUESTION_POINT_FORMAT_STR.format(point=point_str)
        for point_str in point_list)
    return f"{question_str}\n\n{point_text_str}"


def close_file_question(row_str: str, last_file_b: bool) -> str:
    """Return the question asked before one data file is closed.

    Inputs:
        row_str: the file as its file name row shows it, for example
            "file1_run_A.csv" (LLFR-00362).
        last_file_b: True when no other data file is open, so that no
            file is left after the close.
    Outputs: the text of the question of LLFR-00920.
    """
    # LLFR-00920: the flags and areas outside the files left, or every
    # flag and area when no file is left.
    markers_point_str = (CLOSE_LAST_FILE_MARKERS_POINT_STR if last_file_b
                         else CLOSE_FILE_MARKERS_POINT_STR)
    return question_text(
        CLOSE_FILE_QUESTION_STR.format(row=row_str),
        [CLOSE_FILE_SIGNALS_POINT_STR, CLOSE_TABS_POINT_STR,
         markers_point_str, CLOSE_HISTORY_POINT_STR])


def close_all_files_question() -> str:
    """Return the question asked before every data file is closed.

    Inputs: none.
    Outputs: the text of the question of LLFR-00930.
    """
    # LLFR-00930: the five points, in the order of the requirement.
    return question_text(
        CLOSE_ALL_FILES_QUESTION_STR,
        [CLOSE_ALL_FILES_POINT_STR, CLOSE_ALL_SIGNALS_POINT_STR,
         CLOSE_TABS_POINT_STR, CLOSE_LAST_FILE_MARKERS_POINT_STR,
         CLOSE_HISTORY_POINT_STR])


class FileController:
    """Opens files chosen by the user and keeps the open data files.

    Inputs:
        view: the object that shows dialogs and boxes.
        load_function: function that takes a path and returns a
            SignalFile or raises FileOpenError; load_signal_file by
            default.
        start_folder_str: folder the first file selection dialog shows;
            first_start_folder_str() when None.
    Attributes:
        data_files: the DataFileSet of the open data files.
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
        # LLFR-00891, LLFR-00896: the open data files and their numbers.
        self.data_files = DataFileSet()
        # LLFR-00204: the first dialog shows the folder of the app.
        if start_folder_str is None:
            start_folder_str = first_start_folder_str()
        self.dialog_folder_str = start_folder_str
        self.file_opened_listener_list = []
        self.files_closed_listener_list = []
        # LLFR-00071: the listener errors of the selection being opened.
        self.listener_error_list = []

    @property
    def current_file(self):
        """Return the open data files, or None while none is open.

        Inputs: none.
        Outputs: the DataFileSet when at least one data file is open.
        """
        # LLFR-00218, LLFR-00395: a data file is open or not.
        if len(self.data_files) == 0:
            return None
        return self.data_files

    def add_file_opened_listener(self, listener) -> None:
        """Register a function called after a data file was added.

        Inputs:
            listener: a function taking (data_files, data_file): the
                DataFileSet of the open files and the DataFile just
                added.
        Outputs: none.
        """
        # LLFR-00916, LLFR-00917: the other controllers add the new file
        # and keep everything they show.
        self.file_opened_listener_list.append(listener)

    def add_files_closed_listener(self, listener) -> None:
        """Register a function called after data files were closed.

        Inputs:
            listener: a function taking (data_files, closed_file_list):
                the DataFileSet of the files left and the closed
                DataFile objects.
        Outputs: none.
        """
        # LLFR-00922 to LLFR-00926: the other controllers remove what
        # belonged to the closed files.
        self.files_closed_listener_list.append(listener)

    # ----------------------------------------------------------------
    # Open
    # ----------------------------------------------------------------

    def open_file_requested(self) -> None:
        """Run the open-file flow started by the Open file button.

        Shows the limit box with 10 files open, or else the file
        selection dialog, and opens each selected file in the steps of
        LLFR-00328. The button always returns to normal at the end.

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
        # LLFR-00892, LLFR-00893: with 10 files open, a box in place of
        # the dialog, and nothing changes.
        if self.data_files.is_full_b:
            self.view.show_open_files_limit_notification(
                OPEN_FILES_LIMIT_MESSAGE_STR)
            return
        # LLFR-00005, LLFR-00204, LLFR-00447: the file selection dialog
        # in the folder of the app, or of the last file opened.
        path_value = self.view.ask_open_file_path(self.dialog_folder_str)
        if isinstance(path_value, (list, tuple)):
            path_list = [str(path_str) for path_str in path_value
                         if path_str]
        else:
            path_list = [str(path_value)] if path_value else []
        if not path_list:
            # LLFR-00007: cancelled, keep the files and the list.
            return
        # LLFR-00006: open each selected file.
        self.open_paths(path_list)

    def open_paths(self, path_list: list) -> list:
        """Open selected files one after the other.

        Inputs:
            path_list: the paths selected in the dialog.
        Outputs: the DataFile objects added, in the order they were
            opened. After the last file, one File Open Error box lists
            the files that could not be read (LLFR-00951), and then one
            information box lists the refused files (LLFR-00952).
        """
        # LLFR-00948, LLFR-00970: in the order of the file names.
        error_message_list = []
        refused_line_list = []
        added_file_list = []
        # LLFR-00071: an error of a listener, after the file was added.
        self.listener_error_list = []
        for path_str in selection_order_list(path_list):
            # LLFR-00949: whatever happens to one file, the next one is
            # taken.
            try:
                data_file = self.open_one_path(
                    path_str, error_message_list, refused_line_list)
            except Exception as error:
                # LLFR-00969: an unexpected error is a reading error of
                # that file, listed with a description of the error.
                error_message_list.append(
                    UNEXPECTED_ERROR_MESSAGE_STR.format(
                        name=os.path.basename(path_str), error=error))
                continue
            if data_file is not None:
                added_file_list.append(data_file)
        # LLFR-00951: one File Open Error box for the whole selection.
        if error_message_list:
            self.view.show_file_open_error(
                ENTRY_SEPARATOR_STR.join(error_message_list))
        # LLFR-00952: then one information box for the refused files.
        if refused_line_list:
            self.view.show_refused_files_notification(
                "\n".join(refused_line_list))
        # LLFR-00071: a listener that failed after its file was added is
        # an unexpected error of the app, not a reading error of the
        # file, which stays open; it reaches the unexpected error box.
        if self.listener_error_list:
            raise self.listener_error_list[0]
        return added_file_list

    def open_one_path(self, path_str: str, error_message_list: list,
                      refused_line_list: list):
        """Take one selected file through the steps of LLFR-00328.

        Inputs:
            path_str: the path of the selected file.
            error_message_list: the reasons of the files that could not
                be read; this file's reason is added to it.
            refused_line_list: the lines of the refused files; this
                file's line is added to it.
        Outputs: the added DataFile, or None when the file was not
            opened (LLFR-00010: nothing changed for it).
        """
        file_name_str = os.path.basename(path_str)
        # LLFR-00328 step 1, LLFR-00950: 10 files open, refused.
        if self.data_files.is_full_b:
            refused_line_list.append(LIMIT_REASON_STR.format(
                name=file_name_str))
            return None
        # LLFR-00328 step 2, LLFR-00894, LLFR-00895: the same file on
        # disk is already open, refused before it is read.
        open_number_i = self.data_files.open_number(path_str)
        if open_number_i is not None:
            refused_line_list.append(ALREADY_OPEN_REASON_STR.format(
                name=file_name_str, number=open_number_i))
            return None
        # LLFR-00918, LLFR-00328 step 3: read and check it right away,
        # with no question.
        signal_file, error_message_str = self._read_file(path_str)
        if signal_file is None:
            # LLFR-00510, LLFR-00511: kept for the File Open Error box;
            # the open data files are kept (LLFR-00010).
            error_message_list.append(error_message_str)
            return None
        # LLFR-00328 step 4: the user chooses the time signal when no
        # signal is named "Time".
        if (signal_file.needs_time_signal_choice_b
                and not self._choose_time_signal(signal_file,
                                                 file_name_str)):
            # LLFR-00327, LLFR-00509, LLFR-00512, LLFR-00513: cancelled,
            # nothing is opened and no message is shown.
            return None
        # LLFR-00328 step 5, LLFR-00916, LLFR-00896: only now the file
        # is added, with the next number.
        data_file = self.data_files.add(signal_file, path_str)
        # LLFR-00447: only a successful open moves the dialog folder.
        self.dialog_folder_str = os.path.dirname(os.path.abspath(path_str))
        # LLFR-00917, LLFR-00650: the listeners add the new file and
        # keep everything else.
        for listener in list(self.file_opened_listener_list):
            try:
                listener(self.data_files, data_file)
            except Exception as error:
                # LLFR-00071: the file is open; the error is raised after
                # the boxes of the selection (open_paths).
                getattr(self, "listener_error_list", []).append(error)
        return data_file

    def _read_file(self, path_str: str) -> tuple:
        """Read and check a file while the loading indication is shown.

        Inputs:
            path_str: the path of the selected file.
        Outputs: (signal_file, "") when the file can be opened, or
            (None, message_str) with the text of the File Open Error box
            when it can't.
        """
        # LLFR-00418, LLFR-00560: the busy pointer and the loading title
        # while the file is read and checked, whether or not other files
        # are open.
        self.view.show_loading_indication()
        try:
            # LLFR-00006: try to open the selected file.
            return self.load_function(path_str), ""
        except FileOpenError as error:
            # LLFR-00008, LLFR-00009, LLFR-00011, LLFR-00012: the reason
            # given by the loader, which names the file.
            return None, str(error)
        except Exception as error:
            # LLFR-00969: an unexpected failure is reported as a reading
            # error of the file instead of crashing (PCR-00025).
            return None, UNEXPECTED_ERROR_MESSAGE_STR.format(
                name=os.path.basename(path_str), error=error)
        finally:
            # LLFR-00561, LLFR-00562: reading ended, whatever the result;
            # remove the indication before any box or window is shown.
            self.view.hide_loading_indication()

    def _choose_time_signal(self, signal_file,
                            file_name_str: str = "") -> bool:
        """Ask the user for the time signal of a file.

        Inputs:
            signal_file: the SignalFile just read, with no signal that
                matches the time signal name.
            file_name_str: the name of the file, with its extension and
                without its folder, shown in the window (LLFR-00953).
        Outputs: True when the user confirmed a signal, which is now the
            file's time signal; False when the user cancelled.
        """
        # LLFR-00325, LLFR-00906: every signal of the file, in the
        # file's order, with its name in the file, without a prefix.
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

        # LLFR-00953: the window names the file it is for.
        chosen_name_str = self.view.ask_time_signal_name(
            TIME_SIGNAL_PROMPT_STR, name_list, matching_names,
            NO_MATCH_TEXT_STR, check_name, file_name_str=file_name_str)
        if not chosen_name_str:
            # LLFR-00327: the window was cancelled.
            return False
        # LLFR-00326, LLFR-00329: the chosen signal becomes the time
        # signal; a signal that does not increase is never used, even
        # when a window let it through.
        return signal_file.choose_time_signal(str(chosen_name_str)) == ""

    # ----------------------------------------------------------------
    # Close
    # ----------------------------------------------------------------

    def close_file_requested(self, number_i: int) -> bool:
        """Ask whether to close a data file, and close it if so.

        Called when the user chooses "Close file" in the file menu of
        the file's name row (LLFR-00919).

        Inputs:
            number_i: the number of the data file (LLFR-00896).
        Outputs: True when the user proceeded and the file was closed.
        """
        # LLFR-00920: the question names the file as its row shows it,
        # also when none of its signals is drawn.
        data_file = self.data_files.find(int(number_i))
        if data_file is None:
            return False
        last_file_b = len(self.data_files) == 1
        if not self.view.ask_close_file(close_file_question(
                data_file.file_name_row_str, last_file_b)):
            # LLFR-00921: declined, nothing changes.
            return False
        # LLFR-00922 to LLFR-00929, LLFR-00946: the close itself.
        return self.close_file(number_i)

    def close_all_files_requested(self) -> list:
        """Ask once whether to close every data file, and close them.

        Called when the user chooses "Close all files" in the file menu
        (LLFR-00919).

        Inputs: none.
        Outputs: the closed DataFile objects; [] when the user declined
            or no file was open.
        """
        # LLFR-00930: one question for all the files.
        if len(self.data_files) == 0:
            return []
        if not self.view.ask_close_all_files(close_all_files_question()):
            # LLFR-00931: declined, nothing changes.
            return []
        # LLFR-00932: every file, with no further question.
        return self.close_all_files()

    def close_file(self, number_i: int) -> bool:
        """Close one open data file, after the user proceeded.

        Inputs:
            number_i: the number of the data file (LLFR-00896).
        Outputs: True when the file was open and is now closed. The
            listeners remove its signals, the synthetic signals computed
            from them and their curves (LLFR-00922 to LLFR-00926).
        """
        # LLFR-00922, LLFR-00927: only that file; the others keep their
        # numbers; LLFR-00898: its number stays used up.
        data_file = self.data_files.remove(int(number_i))
        if data_file is None:
            return False
        self.notify_closed([data_file])
        return True

    def close_all_files(self) -> list:
        """Close every open data file, after the user proceeded.

        Inputs: none.
        Outputs: the closed DataFile objects, in number order; [] when
            no file was open.
        """
        # LLFR-00932, LLFR-00900: every file, with no further question;
        # the numbering goes on.
        closed_file_list = self.data_files.remove_all()
        if closed_file_list:
            self.notify_closed(closed_file_list)
        return closed_file_list

    def notify_closed(self, closed_file_list: list) -> None:
        """Tell the listeners that data files were closed.

        Inputs:
            closed_file_list: the closed DataFile objects.
        Outputs: none.
        """
        # LLFR-00922 to LLFR-00926, LLFR-00928 to LLFR-00933: each
        # controller removes what belonged to the closed files.
        for listener in list(self.files_closed_listener_list):
            listener(self.data_files, list(closed_file_list))
