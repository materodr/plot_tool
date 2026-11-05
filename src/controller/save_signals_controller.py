"""Save signals controller: writes the signal list to a new data file
(HLFR-00090).

It runs the flow started by the Save signals button of the top panel.
It talks to the view only through plain method calls (no Qt code), so
it can be tested with a fake view (COR-00003, COR-00009). The view must
offer:

- ``set_save_signals_handler(handler)``;
- ``set_save_signals_button_enabled(enabled_b)``;
- ``ask_signals_save_path(start_folder_str, file_name_str,
  format_str)``: a tuple (path_str, format_str, confirmed_b): the path
  typed in the save file dialog ("" when cancelled), the format chosen
  in it (one of ``model.file_writer.FORMAT_ORDER_TUPLE``), and True
  when the system's dialog itself already asked whether to replace that
  path (LLFR-00397);
- ``ask_replace_existing_file(path_str)``: True to replace the file;
- ``save_signal_bytes(path_str, content_bytes)``: a tuple (saved_b,
  reason_str), written safely (temporary file, then replace);
- ``show_signals_save_error(message_str)``: an error box;
- ``show_changed_signal_names(text_str)``: the information box of the
  changed names;
- ``finish_save_signals_button()``.

Saving reads the signals but changes nothing in the app: the signal
list, the names, the plots, the data file and the undo and redo history
stay as they are (LLFR-00405).
"""

import os

from model.file_writer import (
    SignalWriteError, changed_name_list, changed_names_text,
    ensure_format_extension, excel_limit_reason, format_of_path,
    non_finite_name_list, non_finite_reason, numbered_plain_name_list,
    proposed_file_name, saved_name_list, signal_file_bytes,
    CSV_FORMAT_STR, EXCEL_FORMAT_STR)
from model.data_files import TIME_TOLERANCE_F
from model.synthetic_signals import ordered_signal_names

# LLFR-00397: the text of the error box shown for the opened data file.
DATA_FILE_REFUSED_STR = (
    "The opened data file '{name}' cannot be replaced: the app never "
    "writes to the data file. Choose another name or folder to save the "
    "signals.")
# LLFR-00399, LLFR-00400: the start of the error box text.
SAVE_FAILED_STR = "The signals could not be saved to '{name}'."
# LLFR-00942, LLFR-00977: the error box shown in place of the save file
# dialog, which states the time tolerance, built from TIME_TOLERANCE_F so
# that the text always matches the comparison.
DIFFERENT_TIME_SIGNALS_STR = (
    "The signals of the open data files cannot be saved together: the "
    "files need the same time signals, within a tolerance, to be saved in "
    "one file. The time signals must have the same number of samples, and "
    "the samples at the same position must differ by at most "
    f"{TIME_TOLERANCE_F:g} times the larger of their absolute values, or "
    f"by at most {TIME_TOLERANCE_F:g} s when both are smaller than 1 s in "
    "absolute value. Close the files whose time signal is different, then "
    "save the signals again.")


def same_file(first_path_str: str, second_path_str: str) -> bool:
    """Tell whether two paths name the same file.

    Inputs:
        first_path_str: a path.
        second_path_str: another path.
    Outputs: True when both lead to the same file, including through a
        link or a different letter case on a system that ignores it.
    """
    # LLFR-00397: the opened data file is recognised however its path
    # is written.
    try:
        if os.path.exists(first_path_str) and os.path.exists(
                second_path_str):
            return os.path.samefile(first_path_str, second_path_str)
    except OSError:
        pass
    return (os.path.normcase(os.path.realpath(first_path_str))
            == os.path.normcase(os.path.realpath(second_path_str)))


class SaveSignalsController:
    """Runs the Save signals flow.

    Inputs:
        view: the view facade described in the module docstring.
        file_controller: the FileController; it reports opened files.
        synthetic_controller: the SyntheticController, whose signal file
            and store hold the signals of the signal list.
    Attributes:
        data_file_open_b: True once a data file is open.
        file_controller: the FileController, whose dialog folder is the
            first folder of the dialog (LLFR-01181).
        signals_folder_str: folder of the last signals file saved
            successfully, "" before the first one (LLFR-01182).
    """

    def __init__(self, view, file_controller, synthetic_controller) -> None:
        """Store the parts and connect the button, disabled at first.

        Inputs:
            view: the view facade.
            file_controller: the FileController.
            synthetic_controller: the SyntheticController.
        Outputs: none.
        """
        # LLFR-00394: the button runs this flow.
        self.view = view
        self.synthetic_controller = synthetic_controller
        self.data_file_open_b = False
        # LLFR-01181, LLFR-01182: the folders of the dialog.
        self.file_controller = file_controller
        self.signals_folder_str = ""
        view.set_save_signals_handler(self.on_save_signals_requested)
        # LLFR-00395: disabled while no data file is open.
        view.set_save_signals_button_enabled(False)
        file_controller.add_file_opened_listener(self.on_file_opened)

    def on_file_opened(self, signal_file, added_file=None) -> None:
        """Enable the Save signals button once a data file is open.

        Inputs:
            signal_file: the DataFileSet of the open data files (or one
                SignalFile).
            added_file: the DataFile just added; not used.
        Outputs: none.
        """
        # LLFR-00395: enabled after a successful open.
        self.data_file_open_b = signal_file is not None
        self.view.set_save_signals_button_enabled(self.data_file_open_b)

    def on_files_closed(self, data_files, closed_file_list: list) -> None:
        """Disable the Save signals button when no data file is left.

        Inputs:
            data_files: the DataFileSet of the files left.
            closed_file_list: the closed DataFile objects.
        Outputs: none.
        """
        # LLFR-00395, LLFR-00936: disabled while no data file is open.
        self.data_file_open_b = len(data_files) > 0
        self.view.set_save_signals_button_enabled(self.data_file_open_b)

    def dialog_folder(self, data_path_str: str) -> str:
        """Return the folder the next Save signals dialog shows.

        Inputs:
            data_path_str: the path of the open data file with the
                lowest number, used only when the file controller gives
                no folder.
        Outputs: the folder of the last signals file saved
            successfully, or else the folder the Open file dialog would
            show now.
        """
        # LLFR-01182: after a save, the folder of the last saved file.
        if self.signals_folder_str:
            return self.signals_folder_str
        # LLFR-01181: before, the folder of the last data file opened
        # (LLFR-00447, LLFR-01011), as the Open file dialog would show.
        open_folder_str = str(getattr(self.file_controller,
                                      "dialog_folder_str", "") or "")
        if open_folder_str:
            return open_folder_str
        return os.path.dirname(os.path.abspath(data_path_str))

    def on_save_signals_requested(self) -> None:
        """Save the signals to a file chosen by the user.

        Inputs: none.
        Outputs: none. The button always returns to normal at the end.
        """
        try:
            self.save_signals()
        finally:
            # LLFR-00003: the function started by the button finished.
            self.view.finish_save_signals_button()

    def signal_tuple_list(self) -> list:
        """Return the signals to save.

        Inputs: none.
        Outputs: a list of (name in the app, plain name, file number,
            samples) tuples: every signal of the signal list, in its
            order, except the FFT signals and the time signals of the
            files other than the lowest-numbered one.
        """
        # LLFR-00401, LLFR-00939: file after file, each file's signals
        # then its synthetic signals, without the FFT signals and
        # without a message about them (LLFR-00541).
        signal_file = self.synthetic_controller.signal_file
        store = self.synthetic_controller.store
        data_name_set = set(signal_file.signal_name_list)
        # LLFR-00944: one time signal, the lowest-numbered file's.
        kept_time_str = signal_file.time_signal_name_str
        other_time_set = set(getattr(signal_file, "time_signal_name_list",
                                     [kept_time_str])) - {kept_time_str}
        file_number_dict = {signal.name_str: signal.file_number_i
                            for signal in store.signal_list}
        signal_list = []
        for name_str in ordered_signal_names(signal_file, store.names(),
                                             file_number_dict):
            if name_str in other_time_set:
                continue
            if name_str in data_name_set:
                value_array = signal_file.signal_array(name_str)
            else:
                synthetic_signal = store.get(name_str)
                if synthetic_signal.is_fft_b:
                    continue
                value_array = synthetic_signal.value_array
            # LLFR-00945: the name with every prefix the app put into it
            # removed; LLFR-00946: with the number of its data file.
            signal_list.append((name_str, store.plain_name_of(name_str),
                                store.file_number_of(name_str),
                                value_array))
        return signal_list

    def save_signals(self) -> None:
        """Run the steps of the Save signals flow.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00395: the button does nothing without a data file.
        signal_file = self.synthetic_controller.signal_file
        if not self.data_file_open_b or signal_file is None:
            return
        # LLFR-00942, LLFR-00943: different time signals show an error
        # box in place of the save file dialog, and nothing is written.
        same_time_function = getattr(signal_file, "same_time_signals_b",
                                     None)
        if same_time_function is not None and not same_time_function():
            self.view.show_signals_save_error(DIFFERENT_TIME_SIGNALS_STR)
            return
        # LLFR-01181, LLFR-01182: the folder of the dialog. LLFR-00532:
        # "<name>_signals.<extension>" of the lowest-numbered data file,
        # with its format chosen.
        data_path_str = signal_file.path_str
        data_format_str = format_of_path(data_path_str) or CSV_FORMAT_STR
        path_str, format_str, confirmed_b = self.view.ask_signals_save_path(
            self.dialog_folder(data_path_str),
            proposed_file_name(data_path_str), data_format_str)
        # LLFR-00398: a cancelled dialog saves nothing and says nothing.
        if not path_str:
            return
        # LLFR-00396: the extension of the chosen format is added to a
        # name that does not end with one.
        save_path_str = ensure_format_extension(path_str, format_str)
        file_name_str = os.path.basename(save_path_str)
        # LLFR-00397, LLFR-00253: no open data file is ever written, and
        # the app never asks to replace one (the native macOS dialog may
        # already have asked; the app does not ask again).
        for open_path_str in getattr(signal_file, "path_list",
                                     [data_path_str]):
            if same_file(save_path_str, open_path_str):
                self.view.show_signals_save_error(
                    DATA_FILE_REFUSED_STR.format(
                        name=os.path.basename(open_path_str)))
                return
        # LLFR-00397: ask before replacing a file, unless the system's
        # dialog already asked about this very path. LLFR-00398: "No"
        # saves nothing and says nothing.
        already_asked_b = confirmed_b and save_path_str == path_str
        if (os.path.exists(save_path_str) and not already_asked_b
                and not self.view.ask_replace_existing_file(save_path_str)):
            return
        # LLFR-00401: the signals of the signal list, without the FFTs.
        signal_list = self.signal_tuple_list()
        name_list = [signal_tuple[0] for signal_tuple in signal_list]
        plain_name_list = [signal_tuple[1] for signal_tuple in signal_list]
        array_list = [signal_tuple[3] for signal_tuple in signal_list]
        failed_str = SAVE_FAILED_STR.format(name=file_name_str)
        # LLFR-00400: refused before anything is written.
        if format_str == EXCEL_FORMAT_STR:
            reason_str = excel_limit_reason(len(array_list),
                                            len(signal_file.time_array))
            if reason_str:
                self.view.show_signals_save_error(
                    f"{failed_str}\n\n{reason_str}")
                return
        # LLFR-00408: refused before anything is written, naming the
        # signals with infinite or NaN values (in the app's names).
        bad_name_list = non_finite_name_list(name_list, array_list)
        if bad_name_list:
            self.view.show_signals_save_error(
                f"{failed_str}\n\n{non_finite_reason(bad_name_list)}")
            return
        # LLFR-00947: LLFR-00945, LLFR-00946 and LLFR-00965 first, then
        # LLFR-00403 and LLFR-00407: the names the format can store, with
        # the time signal as "Time".
        time_name_str = signal_file.time_signal_name_str
        time_index_i = (name_list.index(time_name_str)
                        if time_name_str in name_list else -1)
        numbered_list = numbered_plain_name_list(
            plain_name_list, [signal_tuple[2] for signal_tuple
                              in signal_list], time_index_i)
        new_name_list = saved_name_list(
            numbered_list, numbered_list[time_index_i]
            if time_index_i >= 0 else "", format_str, time_index_i)
        # LLFR-00402: the content, then a safe write (LLFR-00399).
        try:
            content_bytes = signal_file_bytes(new_name_list, array_list,
                                              format_str)
        except SignalWriteError as error:
            self.view.show_signals_save_error(f"{failed_str}\n\n{error}")
            return
        saved_b, reason_str = self.view.save_signal_bytes(save_path_str,
                                                          content_bytes)
        if not saved_b:
            self.view.show_signals_save_error(
                f"{failed_str}\n\n{reason_str}" if reason_str
                else failed_str)
            return
        # LLFR-01182: only a successful save moves the dialog folder.
        self.signals_folder_str = os.path.dirname(
            os.path.abspath(save_path_str))
        # LLFR-00404: one box with the changed names, none otherwise;
        # the removal of the prefix alone is not a change (LLFR-00945).
        change_list = [
            (name_str, new_str) for name_str, new_str
            in changed_name_list(name_list, new_name_list)
            if new_str != plain_name_list[name_list.index(name_str)]]
        if change_list:
            self.view.show_changed_signal_names(
                changed_names_text(change_list))
