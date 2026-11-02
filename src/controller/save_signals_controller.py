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
    proposed_file_name, saved_name_list, signal_file_bytes,
    CSV_FORMAT_STR, EXCEL_FORMAT_STR)

# LLFR-00397: the text of the error box shown for the opened data file.
DATA_FILE_REFUSED_STR = (
    "The opened data file '{name}' cannot be replaced: the app never "
    "writes to the data file. Choose another name or folder to save the "
    "signals.")
# LLFR-00399, LLFR-00400: the start of the error box text.
SAVE_FAILED_STR = "The signals could not be saved to '{name}'."


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
        view.set_save_signals_handler(self.on_save_signals_requested)
        # LLFR-00395: disabled while no data file is open.
        view.set_save_signals_button_enabled(False)
        file_controller.add_file_opened_listener(self.on_file_opened)

    def on_file_opened(self, signal_file, replaced_b: bool) -> None:
        """Enable the Save signals button once a data file is open.

        Inputs:
            signal_file: the SignalFile that was opened.
            replaced_b: True when it replaced another file.
        Outputs: none.
        """
        # LLFR-00395: enabled after a successful open.
        self.data_file_open_b = signal_file is not None
        self.view.set_save_signals_button_enabled(self.data_file_open_b)

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
        Outputs: a list of (name, samples) tuples: every signal of the
            signal list, in its order, except the FFT signals.
        """
        # LLFR-00401: the data file signals, then the synthetic signals
        # in creation order, without the FFT signals and without a
        # message about them.
        signal_file = self.synthetic_controller.signal_file
        store = self.synthetic_controller.store
        signal_list = [(name_str, signal_file.signal_array(name_str))
                       for name_str in signal_file.signal_name_list]
        for name_str in store.names():
            synthetic_signal = store.get(name_str)
            if not synthetic_signal.is_fft_b:
                signal_list.append((name_str, synthetic_signal.value_array))
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
        # LLFR-00396: the dialog opens in the folder of the data file,
        # with "<name>_signals.<extension>" and its format chosen.
        data_path_str = signal_file.path_str
        data_format_str = format_of_path(data_path_str) or CSV_FORMAT_STR
        path_str, format_str, confirmed_b = self.view.ask_signals_save_path(
            os.path.dirname(os.path.abspath(data_path_str)),
            proposed_file_name(data_path_str), data_format_str)
        # LLFR-00398: a cancelled dialog saves nothing and says nothing.
        if not path_str:
            return
        # LLFR-00396: the extension of the chosen format is added to a
        # name that does not end with one.
        save_path_str = ensure_format_extension(path_str, format_str)
        file_name_str = os.path.basename(save_path_str)
        # LLFR-00397, LLFR-00253: the opened data file is never written.
        if same_file(save_path_str, data_path_str):
            self.view.show_signals_save_error(DATA_FILE_REFUSED_STR.format(
                name=os.path.basename(data_path_str)))
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
        name_list = [name_str for name_str, _ in signal_list]
        array_list = [value_array for _, value_array in signal_list]
        failed_str = SAVE_FAILED_STR.format(name=file_name_str)
        # LLFR-00400: refused before anything is written.
        if format_str == EXCEL_FORMAT_STR:
            reason_str = excel_limit_reason(len(array_list),
                                            len(signal_file.time_array))
            if reason_str:
                self.view.show_signals_save_error(
                    f"{failed_str}\n\n{reason_str}")
                return
        # LLFR-00403, LLFR-00407: the names the format can store, with
        # the time signal as "Time".
        new_name_list = saved_name_list(
            name_list, signal_file.time_signal_name_str, format_str)
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
        # LLFR-00404: one box with the changed names, none otherwise.
        change_list = changed_name_list(name_list, new_name_list)
        if change_list:
            self.view.show_changed_signal_names(
                changed_names_text(change_list))
