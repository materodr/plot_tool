"""File controller: runs the open-file flow (HLFR-00004, HLFR-00010).

It talks to the view only through plain method calls (no Qt code), so
it can be tested with a fake view (COR-00003, COR-00009). The view must
offer ``ask_open_file_path``, ``show_file_open_error``,
``ask_replace_file``, ``show_signal_names`` and
``finish_open_file_button``.
"""

from model.errors import FileOpenError
from model.file_loader import load_signal_file

# PCR-00025: start of the message shown when the loader fails in an
# unexpected way, so the app reports it instead of crashing.
UNEXPECTED_ERROR_MESSAGE_STR = (
    "The file '{path}' could not be read because of an unexpected "
    "error: {error}")


class FileController:
    """Opens files chosen by the user and keeps the current file.

    Inputs:
        view: the object that shows dialogs and the signal list.
        load_function: function that takes a path and returns a
            SignalFile or raises FileOpenError; load_signal_file by
            default.
    Attributes:
        current_file: the open SignalFile, or None before the first
            file is opened.
    """

    def __init__(self, view, load_function=load_signal_file) -> None:
        """Store the view and the load function; no file is open yet.

        Inputs:
            view: the view facade.
            load_function: the function that opens a file.
        Outputs: none.
        """
        # LLFR-00006: the function used to open the selected file.
        self.view = view
        self.load_function = load_function
        self.current_file = None
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
        # LLFR-00005: show the file selection dialog.
        path_str = self.view.ask_open_file_path()
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
        # LLFR-00017, LLFR-00054: show the new names, including Time.
        self.view.show_signal_names(signal_file.signal_name_list)
        # LLFR-00015, LLFR-00016: tell the listeners about the new file.
        for listener in list(self.file_opened_listener_list):
            listener(signal_file, replaced_b)
