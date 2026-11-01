"""Synthetic signal controller: the signal list menu (HLFR-00053).

It runs the options of the menu shown by a right-click on a signal name
in the signal list panel: "Create synthetic signal" with its operations
(LLFR-00239, LLFR-00268), "Copy name" (LLFR-00277), and, for synthetic
signals, "Rename" (LLFR-00265), "Delete signal" (LLFR-00254) and "Copy
equation" (LLFR-00278). It keeps the SyntheticSignalStore of the open
data file; the synthetic signals live only in memory (LLFR-00253).

It talks to the view only through plain method calls with plain values,
so it can be tested with a fake view (COR-00003, COR-00009). The view
must offer:

- ``set_synthetic_operation_groups(group_list)``: the menu groups, as a
  list of (group label, list of (operation id, operation label));
- ``set_signal_menu_handlers(operation_handler, copy_name_handler,
  rename_handler, delete_handler, copy_equation_handler)``;
- ``ask_synthetic_parameter(title_str, prompt_str, field_list,
  check_function, choice_tuple)``: a dialog with one text field per
  (label, starting text) of field_list and, when choice_tuple is not
  empty, one choice (label, list of (choice id, choice label), the id
  chosen at first); it keeps itself open while
  ``check_function(value_list)`` returns a reason ("" when the values
  are allowed), where value_list holds the texts of the fields and
  then the chosen id; returns that value_list when accepted, or None
  when cancelled;
- ``ask_second_signal(title_str, prompt_str, name_list,
  selected_name_str, search_function, no_match_text_str)``: the chosen
  name, or None when cancelled; the dialog has a search box, and
  ``search_function(text_str)`` returns the names of name_list that
  match the typed text, in the order to show them (LLFR-00285);
  no_match_text_str is shown when it returns none;
- ``ask_delete_synthetic_signal(name_str, dependent_name_list)``: True
  when the user proceeds;
- ``ask_synthetic_signal_name(current_name_str)``: the typed name, or
  None when cancelled;
- ``show_signal_information(title_str, message_str)``: an information
  box;
- ``copy_text_to_clipboard(text_str)``.
"""

from model import synthetic_operations as operations
from model.errors import (
    EmptySyntheticNameError, SyntheticNameInUseError, SyntheticSignalError)
from model.number_format import format_signal_value
from model.layout_file import RENAMED_SIGNAL_LINE_STR
from model.signal_search import NO_MATCH_TEXT_STR, search_signals
from model.synthetic_signals import (
    LayoutSignalLoader, SyntheticSignalStore)

# LLFR-00247, LLFR-00250: title of the information boxes of a creation.
CREATE_TITLE_STR = "Create synthetic signal"
# LLFR-00267: title of the information box of a name already in use.
RENAME_TITLE_STR = "Rename signal"
# LLFR-00245: prompt and fields of the filter dialog.
FILTER_PROMPT_STR = (
    "Cutoff frequency, in Hz: greater than {lowest} Hz and less than "
    "{highest} Hz (half the sampling rate).\n"
    "Filter order: a whole number from {smallest} to {largest}.")
CUTOFF_FIELD_LABEL_STR = "Cutoff frequency (Hz):"
ORDER_FIELD_LABEL_STR = "Filter order:"
# LLFR-00245, LLFR-00246: the choice of how the filter starts.
FILTER_START_LABEL_STR = "Filter start:"
FILTER_START_CHOICE_LIST = [
    (operations.FILTER_START_FIRST_VALUE_STR, "From the first value"),
    (operations.FILTER_START_ZERO_STR, "From zero")]
# LLFR-00269: prompt of the window size dialog.
WINDOW_PROMPT_STR = (
    "Window size, as a whole number of samples.\n"
    "Allowed: from {smallest} to {largest} samples.")
WINDOW_FIELD_LABEL_STR = "Window size (samples):"
# LLFR-00272: prompts of the constant dialog.
CONSTANT_PROMPT_STR = "The constant number."
DIVIDE_CONSTANT_PROMPT_STR = "The constant number, not 0."
CONSTANT_FIELD_LABEL_STR = "Constant:"
# LLFR-00237, LLFR-00262: the lines of the layout load report.
NOT_CREATED_LINE_STR = "{label}: {reason}"
# LLFR-00275: prompt of the second signal dialog.
SECOND_SIGNAL_PROMPT_STR = "Multiply '{name}' by the signal:"


def parse_number_text(text_str: str):
    """Turn the text typed in a parameter dialog into a number.

    Inputs:
        text_str: the typed text.
    Outputs: a float, or an int when the text is a whole number written
        without a decimal mark; the text itself when it is not a
        number, so that the model's check gives the reason.
    """
    # LLFR-00245, LLFR-00269, LLFR-00272: "not a number" is reported by
    # the parameter check of the model.
    stripped_text_str = str(text_str).strip()
    try:
        return int(stripped_text_str)
    except ValueError:
        pass
    try:
        return float(stripped_text_str)
    except ValueError:
        return stripped_text_str


class SyntheticController:
    """Creates, renames, deletes and copies synthetic signals.

    Inputs:
        view: the view facade (MainWindow or a fake).
        file_controller: the FileController; this controller listens to
            it for opened files (LLFR-00252).
        plot_controller: the PlotController, which draws the curves of
            synthetic signals and gives the time range of the plots.
        signal_list_controller: the SignalListController, which shows
            the synthetic signals in the signal list.
    Attributes:
        store: the SyntheticSignalStore of the open data file.
        signal_file: the open SignalFile, or None before the first one.
    """

    def __init__(self, view, file_controller, plot_controller,
                 signal_list_controller) -> None:
        """Store the parts and connect to the view and the files.

        Inputs:
            view: the view facade.
            file_controller: the FileController that opens files.
            plot_controller: the PlotController.
            signal_list_controller: the SignalListController.
        Outputs: none.
        """
        # LLFR-00253: the synthetic signals exist only in this store.
        self.view = view
        self.plot_controller = plot_controller
        self.signal_list_controller = signal_list_controller
        self.store = SyntheticSignalStore()
        self.signal_file = None
        # LLFR-00242: the plots draw synthetic signals from the store.
        plot_controller.set_synthetic_store(self.store)
        # LLFR-00252: a new data file removes every synthetic signal.
        file_controller.add_file_opened_listener(self.on_file_opened)
        # LLFR-00239, LLFR-00268: the operations of the menu, in groups,
        # each with its abbreviation in parentheses.
        view.set_synthetic_operation_groups([
            (group_str, [(operation.operation_str,
                          operation.menu_label_str)
                         for operation in operation_list])
            for group_str, operation_list
            in operations.operation_group_list()])
        # LLFR-00239, LLFR-00254, LLFR-00265, LLFR-00277, LLFR-00278:
        # the options of the signal menu.
        view.set_signal_menu_handlers(
            self.on_create_requested, self.on_copy_name_requested,
            self.on_rename_requested, self.on_delete_requested,
            self.on_copy_equation_requested)

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def data_name_set(self) -> set:
        """Return the names of the data file signals.

        Inputs: none.
        Outputs: a set of names; empty before the first file.
        """
        # LLFR-00241, LLFR-00267: names are unique in the signal list.
        if self.signal_file is None:
            return set()
        return set(self.signal_file.signal_name_list)

    def signal_list_name_list(self) -> list:
        """Return every signal name of the signal list, in list order.

        Inputs: none.
        Outputs: the data file signals, then the synthetic signals.
        """
        # LLFR-00242: synthetic signals after the data file signals.
        if self.signal_file is None:
            return []
        return list(self.signal_file.signal_name_list) + self.store.names()

    def is_listed(self, signal_name_str: str) -> bool:
        """Tell whether a name is in the signal list.

        Inputs:
            signal_name_str: the name sent by the view.
        Outputs: True for a data file or synthetic signal.
        """
        # LLFR-00239, LLFR-00277: only listed signals have a menu; a
        # stale request from the view is ignored (PCR-00025).
        return signal_name_str in self.signal_list_name_list()

    def signal_lookup(self, signal_name_str: str):
        """Return the samples of any signal of the signal list.

        Inputs:
            signal_name_str: a data file or synthetic signal name.
        Outputs: its numpy array.
        Raises: KeyError for an unknown name.
        """
        # LLFR-00264: synthetic signals are computed from either kind.
        if signal_name_str in self.data_name_set():
            return self.signal_file.signal_array(signal_name_str)
        return self.store.get(signal_name_str).value_array

    def show_synthetic_signals(self) -> None:
        """Show the current synthetic signals in the signal list.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00242: after the data signals, in creation order, in
        # italics; LLFR-00251: the FFT signals are told apart.
        name_list = self.store.names()
        self.signal_list_controller.set_synthetic_signals(
            name_list, {name_str for name_str in name_list
                        if self.store.is_fft(name_str)})

    def show_information(self, title_str: str, message_str: str) -> None:
        """Show an information box.

        Inputs:
            title_str: the title of the box.
            message_str: the sentence the box shows.
        Outputs: none.
        """
        # LLFR-00247, LLFR-00250, LLFR-00267: information, not errors.
        self.view.show_signal_information(title_str, message_str)

    # ----------------------------------------------------------------
    # File
    # ----------------------------------------------------------------

    def on_file_opened(self, signal_file, replaced_b: bool) -> None:
        """Remove every synthetic signal of the previous data file.

        Inputs:
            signal_file: the SignalFile that was opened.
            replaced_b: True when it replaced another file.
        Outputs: none. The SignalListController shows the new list.
        """
        # LLFR-00252: a new data file starts with no synthetic signal.
        self.signal_file = signal_file
        self.store.clear()

    # ----------------------------------------------------------------
    # Create
    # ----------------------------------------------------------------

    def on_create_requested(self, source_name_str: str,
                            operation_str: str) -> None:
        """Create the synthetic signal of an operation chosen in the menu.

        Inputs:
            source_name_str: the right-clicked signal name.
            operation_str: the operation id chosen in the menu.
        Outputs: none. A cancelled dialog creates nothing; an operation
            that cannot be done shows an information box.
        """
        # LLFR-00239, LLFR-00264: any listed signal, data or synthetic.
        if (not self.is_listed(source_name_str)
                or operation_str not in operations.OPERATION_DICT):
            return
        # LLFR-00251: no operation on an FFT signal.
        if self.store.is_fft(source_name_str):
            return
        operation = operations.OPERATION_DICT[operation_str]
        time_array = self.signal_file.time_array
        kind_str = operation.parameter_kind_str
        try:
            # LLFR-00247: filters and FFT need evenly spaced samples,
            # checked before any dialog is shown.
            if kind_str in (operations.FILTER_PARAMETER_STR,
                            operations.TIME_RANGE_PARAMETER_STR):
                operations.sampling_rate_hz(time_array)
            parameter_tuple = self.ask_parameter(operation,
                                                 source_name_str)
            if not parameter_tuple:
                # LLFR-00245, LLFR-00269, LLFR-00272, LLFR-00275: a
                # cancelled dialog creates no signal.
                return
            source_name_list, parameter = parameter_tuple
            # LLFR-00240, LLFR-00241: the store names the new signal.
            self.store.create(operation_str, source_name_list, parameter,
                              self.signal_lookup, time_array,
                              self.data_name_set())
        except SyntheticSignalError as error:
            # LLFR-00247, LLFR-00250: an information box that says why
            # the operation cannot be done; nothing is created.
            self.show_information(CREATE_TITLE_STR, str(error))
            return
        # LLFR-00242: the new signal is listed after the others.
        self.show_synthetic_signals()

    def ask_parameter(self, operation, source_name_str: str) -> tuple:
        """Ask the user for the parameter of an operation.

        Inputs:
            operation: the SyntheticOperation chosen in the menu.
            source_name_str: the right-clicked signal name.
        Outputs: a tuple (source_name_list, parameter) ready for
            SyntheticSignalStore.create, or () when the user cancelled.
        Raises: SyntheticSignalError when the operation cannot be done
            (for example too few samples for an FFT or a moving
            average).
        """
        # LLFR-00239: the operations without a parameter run at once.
        kind_str = operation.parameter_kind_str
        if kind_str == operations.NO_PARAMETER_STR:
            return ([source_name_str], None)
        if kind_str == operations.SECOND_SIGNAL_PARAMETER_STR:
            # LLFR-00275: the second signal of a product.
            second_name_str = self.ask_second_signal(operation,
                                                     source_name_str)
            if second_name_str is None:
                return ()
            return ([source_name_str, second_name_str], None)
        if kind_str == operations.TIME_RANGE_PARAMETER_STR:
            # LLFR-00248: the range shown by the time plots, or the
            # whole file when no time plot exists.
            return ([source_name_str],
                    tuple(self.plot_controller.time_plot_range_tuple()))
        # LLFR-00245, LLFR-00269, LLFR-00272: a dialog with a number.
        parameter = self.ask_number(operation, source_name_str)
        if parameter is None:
            return ()
        return ([source_name_str], parameter)

    def number_dialog(self, operation, sample_count_i: int) -> tuple:
        """Return the prompt and the fields of a parameter dialog.

        Inputs:
            operation: the SyntheticOperation.
            sample_count_i: number of samples of the signal.
        Outputs: a tuple (prompt_str, field_list, choice_tuple): the
            prompt, with the allowed ranges, a list of (label_str,
            starting text) with one field per value, and the choice of
            the filter start (LLFR-00245), () for the other operations.
        Raises: SyntheticSignalError when no value is allowed.
        """
        kind_str = operation.parameter_kind_str
        if kind_str == operations.FILTER_PARAMETER_STR:
            # LLFR-00245: the cutoff, greater than 0 and less than half
            # the sampling rate, in the number format of the data tips,
            # and the order, from 1 to 8, starting at 2.
            lowest_hz, highest_hz = operations.allowed_cutoff_range_hz(
                self.signal_file.time_array)
            smallest_i, largest_i = operations.allowed_filter_order_range()
            return (FILTER_PROMPT_STR.format(
                lowest=format_signal_value(lowest_hz),
                highest=format_signal_value(highest_hz),
                smallest=smallest_i, largest=largest_i),
                [(CUTOFF_FIELD_LABEL_STR, ""),
                 (ORDER_FIELD_LABEL_STR,
                  str(operations.DEFAULT_FILTER_ORDER_I))],
                # LLFR-00245: "From the first value" chosen at first.
                (FILTER_START_LABEL_STR, list(FILTER_START_CHOICE_LIST),
                 operations.DEFAULT_FILTER_START_STR))
        if kind_str == operations.WINDOW_PARAMETER_STR:
            # LLFR-00269: from 2 up to the number of samples.
            smallest_i, largest_i = operations.allowed_window_range(
                sample_count_i)
            if smallest_i > largest_i:
                # LLFR-00269: a signal too short for any window.
                operations.check_window(smallest_i, sample_count_i)
            return (WINDOW_PROMPT_STR.format(smallest=smallest_i,
                                             largest=largest_i),
                    [(WINDOW_FIELD_LABEL_STR, "")], ())
        # LLFR-00272: a constant, not 0 for "Divide by constant".
        if operation.operation_str == operations.DIVIDE_STR:
            return (DIVIDE_CONSTANT_PROMPT_STR,
                    [(CONSTANT_FIELD_LABEL_STR, "")], ())
        return (CONSTANT_PROMPT_STR, [(CONSTANT_FIELD_LABEL_STR, "")], ())

    def ask_number(self, operation, source_name_str: str):
        """Ask for the filter values, the window size or the constant.

        Inputs:
            operation: the SyntheticOperation.
            source_name_str: the right-clicked signal name.
        Outputs: the checked parameter, or None when cancelled.
        Raises: SyntheticSignalError when no value is allowed.
        """
        # LLFR-00245, LLFR-00269, LLFR-00272: the dialog stays open and
        # says why while a value is not allowed.
        time_array = self.signal_file.time_array
        sample_count_i = int(self.signal_lookup(source_name_str).size)
        prompt_str, field_list, choice_tuple = self.number_dialog(
            operation, sample_count_i)

        def parameter_of(text_list) -> object:
            """Return the parameter typed in the dialog, checked.

            Inputs:
                text_list: the texts of the fields, in field order,
                    then the chosen filter start for a filter.
            Outputs: the parameter in the form the store takes.
            Raises: SyntheticSignalError when a value is not allowed.
            """
            # LLFR-00245: (cutoff, order, start); LLFR-00269,
            # LLFR-00272: one number. The model's rules give the reason.
            value_list = [parse_number_text(text_str)
                          for text_str in text_list[:len(field_list)]]
            if operation.parameter_kind_str == (
                    operations.FILTER_PARAMETER_STR):
                # LLFR-00246: the start chosen in the dialog.
                start_list = list(text_list[len(field_list):])[:1] or [
                    operations.DEFAULT_FILTER_START_STR]
                return operations.check_parameter(
                    operation.operation_str,
                    tuple(value_list + start_list), time_array,
                    sample_count_i)
            return operations.check_parameter(
                operation.operation_str,
                value_list[0] if value_list else "", time_array,
                sample_count_i)

        def check_text_list(text_list) -> str:
            """Return why the typed values are not allowed.

            Inputs:
                text_list: the texts of the fields, in field order.
            Outputs: the reason, or "" when the values are allowed.
            """
            # LLFR-00245, LLFR-00269, LLFR-00272: the model's rules.
            try:
                parameter_of(text_list)
            except SyntheticSignalError as error:
                return str(error)
            return ""

        text_list = self.view.ask_synthetic_parameter(
            operation.label_str, prompt_str, field_list, check_text_list,
            choice_tuple)
        if text_list is None:
            return None
        # LLFR-00245, LLFR-00269, LLFR-00272: the accepted values.
        return parameter_of(list(text_list))

    def ask_second_signal(self, operation, source_name_str: str):
        """Ask for the second signal of a Product with signal.

        Inputs:
            operation: the SyntheticOperation "product".
            source_name_str: the right-clicked signal name.
        Outputs: the chosen name, or None when cancelled.
        """
        # LLFR-00275: every signal of the list except the FFT signals,
        # including the right-clicked one.
        name_list = [name_str for name_str in self.signal_list_name_list()
                     if not self.store.is_fft(name_str)]

        def matching_names(text_str: str) -> list:
            """Return the dialog's signals that match the typed text.

            Inputs:
                text_str: the text of the dialog's search box.
            Outputs: the matching names of name_list, in the order of
                the search of the signal list panel.
            """
            # LLFR-00285: the same search, rules and order as the signal
            # list panel (LLFR-00095 to LLFR-00102, LLFR-00105).
            return search_signals(name_list, str(text_str))

        chosen_name_str = self.view.ask_second_signal(
            operation.label_str,
            SECOND_SIGNAL_PROMPT_STR.format(name=source_name_str),
            name_list, source_name_str, matching_names, NO_MATCH_TEXT_STR)
        if chosen_name_str is None or chosen_name_str not in name_list:
            return None
        return str(chosen_name_str)

    # ----------------------------------------------------------------
    # Copy
    # ----------------------------------------------------------------

    def on_copy_name_requested(self, signal_name_str: str) -> None:
        """Put a signal's name on the clipboard.

        Inputs:
            signal_name_str: the right-clicked signal name.
        Outputs: none.
        """
        # LLFR-00277: the name, as text, for every kind of signal.
        if not self.is_listed(signal_name_str):
            return
        self.view.copy_text_to_clipboard(signal_name_str)

    def on_copy_equation_requested(self, signal_name_str: str) -> None:
        """Put a synthetic signal's equation on the clipboard.

        Inputs:
            signal_name_str: the right-clicked synthetic signal name.
        Outputs: none. Ignored for a data file signal or an FFT signal
            (LLFR-00278).
        """
        # LLFR-00279: the JSON list of the layout file entries of the
        # signal and of every synthetic signal it is computed from;
        # LLFR-00278: FFT signals have no equation (LLFR-00283).
        if (not self.store.contains(signal_name_str)
                or self.store.is_fft(signal_name_str)):
            return
        self.view.copy_text_to_clipboard(
            self.store.equation_text(signal_name_str))

    # ----------------------------------------------------------------
    # Rename and delete
    # ----------------------------------------------------------------

    def on_rename_requested(self, signal_name_str: str) -> None:
        """Let the user type a new name for a synthetic signal.

        Inputs:
            signal_name_str: the right-clicked synthetic signal name.
        Outputs: none. Ignored for a data file signal (LLFR-00265).
        """
        # LLFR-00265: only synthetic signals can be renamed.
        if not self.store.contains(signal_name_str):
            return
        # LLFR-00266: the user types the new name.
        typed_name_str = self.view.ask_synthetic_signal_name(
            signal_name_str)
        if typed_name_str is None:
            return
        try:
            new_name_str = self.store.rename(
                signal_name_str, str(typed_name_str), self.data_name_set())
        except EmptySyntheticNameError:
            # LLFR-00267: an empty name keeps the name, with no message.
            return
        except SyntheticNameInUseError as error:
            # LLFR-00267: a name in use keeps the name, and the user is
            # told that a signal with that name already exists.
            self.show_information(RENAME_TITLE_STR, str(error))
            return
        if new_name_str == signal_name_str:
            return
        # LLFR-00266: every legend shows the new name; the dependents
        # keep theirs. Not undoable, and the history is kept.
        self.plot_controller.rename_signal(signal_name_str, new_name_str)
        self.show_synthetic_signals()

    def on_delete_requested(self, signal_name_str: str) -> None:
        """Delete a synthetic signal and the signals computed from it.

        Inputs:
            signal_name_str: the right-clicked synthetic signal name.
        Outputs: none. Ignored for a data file signal (LLFR-00254).
        """
        # LLFR-00254: only synthetic signals can be deleted.
        if not self.store.contains(signal_name_str):
            return
        # LLFR-00255: ask first, naming the direct and indirect
        # dependents.
        dependent_name_list = self.store.dependents(signal_name_str)
        if not self.view.ask_delete_synthetic_signal(signal_name_str,
                                                     dependent_name_list):
            return
        # LLFR-00255: remove them from the list and their curves from
        # every plot, and clear the undo and redo history.
        removed_name_list = self.store.delete(signal_name_str)
        self.plot_controller.remove_signals(removed_name_list)
        self.show_synthetic_signals()

    # ----------------------------------------------------------------
    # Layout files
    # ----------------------------------------------------------------

    def layout_entries(self) -> list:
        """Return the layout file entries of the synthetic signals.

        Inputs: none.
        Outputs: the entries of every synthetic signal, in creation
            order, for the "synthetic_signals" list (LLFR-00225).
        """
        # LLFR-00225 item 10: current names, operation, sources and
        # parameter, in creation order.
        return self.store.layout_entries()

    def load_layout_signals(self, entry_list, report) -> dict:
        """Add the synthetic signals of a layout file.

        Called by the layout builder before the plots are rebuilt. The
        current synthetic signals and their curves are kept (LLFR-00229).

        Inputs:
            entry_list: the "synthetic_signals" list of the file.
            report: the LayoutReport of the load; the signals not
                created and the renamed ones are added to it
                (LLFR-00237).
        Outputs: a dict signal name of the file -> (name of the signal
            drawn for it, its samples), or None when the file's signal
            was not created; it also holds every synthetic signal of
            the signal list that is not an FFT signal under its own name.
        """
        # LLFR-00262, LLFR-00282: create, reuse or rename, in order.
        if self.signal_file is None:
            return {}
        loader = LayoutSignalLoader(
            self.store, self.signal_lookup, self.signal_file.time_array,
            self.data_name_set())
        loader.load(entry_list)
        for label_str, reason_str in loader.not_created_list:
            # LLFR-00237: each signal not created, with the reason.
            report.add_synthetic_signal(NOT_CREATED_LINE_STR.format(
                label=label_str, reason=reason_str))
        for saved_name_str, new_name_str in loader.renamed_list:
            # LLFR-00282, LLFR-00237: each rename, old and new name.
            report.add_renamed(RENAMED_SIGNAL_LINE_STR.format(
                saved=saved_name_str, new=new_name_str))
        # LLFR-00242: the signal list shows the new synthetic signals.
        self.show_synthetic_signals()
        # LLFR-00230, LLFR-00282: what the file's names draw.
        return loader.drawn_name_dict()

    def layout_snapshot(self):
        """Remember the synthetic signals before a layout load.

        Inputs: none.
        Outputs: a function without arguments that puts them back and
            shows them in the signal list, for a load that fails.
        """
        # PCR-00025, LLFR-00236: a failed load keeps the layout, and the
        # synthetic signals, unchanged.
        saved_signal_list = list(self.store.signal_list)

        def restore() -> None:
            """Put back the remembered synthetic signals.

            Inputs: none.
            Outputs: none.
            """
            # LLFR-00236: the synthetic signals of before the load.
            self.store.signal_list = list(saved_signal_list)
            self.show_synthetic_signals()

        return restore
