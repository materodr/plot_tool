"""Layout controller: saves and loads layout files (HLFR-00049 to
HLFR-00052).

It runs the flows started by the Save layout and Load layout buttons of
the top panel. It talks to the view only through plain method calls
(no Qt code), so it can be tested with a fake view (COR-00003,
COR-00009). The view must offer:

- ``set_layout_handlers(save_handler, load_handler)``;
- ``set_layout_buttons_enabled(enabled_b)``;
- ``ask_layout_save_path(start_folder_str)``: the chosen path, "" when
  cancelled; the dialog itself asks before replacing the file it
  returns (LLFR-00223);
- ``ask_layout_load_path(start_folder_str)``: the chosen path, "" when
  cancelled;
- ``ask_replace_existing_file(path_str)``: True to replace the file;
- ``save_layout_bytes(path_str, content_bytes)``: a tuple (saved_b,
  reason_str), written safely (temporary file, then replace);
- ``panel_width_tuple()``: (plot panel width, signal list panel width)
  in pixels; ``set_panel_widths(plot_width_i, list_width_i)``;
- ``show_layout_save_error(reason_str)``,
  ``show_layout_load_error(message_str)`` and
  ``show_layout_report(report_text_str)``;
- ``finish_save_layout_button()``, ``finish_load_layout_button()``;
- optionally ``ask_layout_save_options()``: the choices of the dialog of
  LLFR-01212, as a dict with the keys of LAYOUT_OPTION_KEY_TUPLE, or
  None when the user cancels (LLFR-01214). A view without it saves with
  the first values of LLFR-01213.

Data files (HLFR-00155, HLFR-00156): a layout saved with the names of the
open data files holds their numbers and paths (LLFR-01217). Loading it
opens the files that are not open yet, through the file controller's
``open_paths`` (LLFR-01218), reuses the open ones (LLFR-01219), reads the
signal names with the numbers the files have now (LLFR-01220) and lists
the files it could not open in the load report (LLFR-01221, LLFR-01222).

Dialog folder (LLFR-00220): until a layout file is saved or loaded
successfully, the dialogs show the folder the Open file dialog would
show at that moment (the file controller's ``dialog_folder_str``,
LLFR-00204); after that, the folder of the last layout file saved or
loaded successfully.
"""

import os

from model.layout_file import (
    DATA_FILES_KEY_STR, FILE_NOT_FOUND_REASON_STR, FILE_NOT_OPENED_REASON_STR,
    LayoutFileError, data_file_candidate_list, data_file_entries_of,
    data_file_entry_list, ensure_layout_suffix, file_number_dict,
    layout_bytes, layout_with_save_options, read_layout_file,
    renumber_layout_names)

# LLFR-01212, LLFR-01213: the choices of the save options dialog and
# their first values.
MARKERS_OPTION_KEY_STR = "markers"
ALL_TABS_OPTION_KEY_STR = "all_tabs"
DATA_FILES_OPTION_KEY_STR = "data_files"
LAYOUT_OPTION_KEY_TUPLE = (MARKERS_OPTION_KEY_STR, ALL_TABS_OPTION_KEY_STR,
                           DATA_FILES_OPTION_KEY_STR)
DEFAULT_LAYOUT_OPTION_DICT = {MARKERS_OPTION_KEY_STR: True,
                              ALL_TABS_OPTION_KEY_STR: True,
                              DATA_FILES_OPTION_KEY_STR: False}

# PCR-00025: shown when loading fails in an unexpected way, so the app
# reports it instead of crashing.
UNEXPECTED_LOAD_ERROR_STR = (
    "The file '{path}' could not be read as a layout file because of an "
    "unexpected error: {error}")


class LayoutController:
    """Runs the Save layout and Load layout flows.

    Inputs:
        view: the view facade described in the module docstring.
        file_controller: the FileController; its dialog folder is the
            first layout dialog folder, and it reports opened files.
        plot_controller: the PlotController that holds the layout.
    Attributes:
        layout_folder_str: folder of the last layout file saved or
            loaded successfully, "" before the first one.
        data_file_open_b: True once a data file is open.
        synthetic_signal_list_function: function without arguments that
            returns the entries of the synthetic signals to save
            (LLFR-00225 item 10); set by the MainController.
        synthetic_signal_builder: function given to the plot controller
            to create the synthetic signals of a loaded file
            (LLFR-00262), or None to create none.
        synthetic_signal_snapshot_function: function without arguments
            called before a load; it returns a function that puts back
            the synthetic signals of before the load if it fails, or it
            is None.
    """

    def __init__(self, view, file_controller, plot_controller) -> None:
        """Store the parts and connect the buttons, disabled at first.

        Inputs:
            view: the view facade.
            file_controller: the FileController.
            plot_controller: the PlotController.
        Outputs: none.
        """
        # LLFR-00216, LLFR-00217: the two buttons run these flows.
        self.view = view
        self.file_controller = file_controller
        self.plot_controller = plot_controller
        self.layout_folder_str = ""
        self.data_file_open_b = False
        # LLFR-00225 item 10, LLFR-00262: the synthetic signal hooks,
        # connected by the MainController.
        self.synthetic_signal_list_function = list
        self.synthetic_signal_builder = None
        self.synthetic_signal_snapshot_function = None
        view.set_layout_handlers(self.on_save_layout_requested,
                                 self.on_load_layout_requested)
        # LLFR-00218: disabled while no data file is open.
        view.set_layout_buttons_enabled(False)
        file_controller.add_file_opened_listener(self.on_file_opened)

    def on_file_opened(self, signal_file, added_file=None) -> None:
        """Enable the layout buttons once a data file is open.

        Inputs:
            signal_file: the DataFileSet of the open data files (or one
                SignalFile).
            added_file: the DataFile just added; not used.
        Outputs: none.
        """
        # LLFR-00218: enabled after a successful open.
        self.data_file_open_b = signal_file is not None
        self.view.set_layout_buttons_enabled(self.data_file_open_b)

    def on_files_closed(self, data_files, closed_file_list: list) -> None:
        """Disable the layout buttons when no data file is left.

        Inputs:
            data_files: the DataFileSet of the files left.
            closed_file_list: the closed DataFile objects.
        Outputs: none.
        """
        # LLFR-00218, LLFR-00936: disabled while no data file is open.
        self.data_file_open_b = len(data_files) > 0
        self.view.set_layout_buttons_enabled(self.data_file_open_b)

    def dialog_folder(self) -> str:
        """Return the folder the next layout dialog shows.

        Inputs: none.
        Outputs: the folder of the last layout file saved or loaded
            successfully, or else the folder of the Open file dialog.
        """
        # LLFR-00220: the first time, the folder the Open file dialog
        # would show now (LLFR-00204); after that, the last layout's.
        if self.layout_folder_str:
            return self.layout_folder_str
        return str(getattr(self.file_controller, "dialog_folder_str", ""))

    def remember_folder(self, path_str: str) -> None:
        """Keep the folder of a layout file saved or loaded successfully.

        Inputs:
            path_str: the path of the layout file.
        Outputs: none.
        """
        # LLFR-00220: only a success moves the dialog folder.
        self.layout_folder_str = os.path.dirname(os.path.abspath(path_str))

    def on_save_layout_requested(self) -> None:
        """Save the current layout to a layout file chosen by the user.

        Inputs: none.
        Outputs: none. The Save layout button always returns to normal
            at the end.
        """
        try:
            self.save_layout()
        finally:
            # LLFR-00003: the function started by the button finished.
            self.view.finish_save_layout_button()

    def on_load_layout_requested(self) -> None:
        """Load a layout file chosen by the user.

        Inputs: none.
        Outputs: none. The Load layout button always returns to normal
            at the end.
        """
        try:
            self.load_layout()
        finally:
            # LLFR-00003: the function started by the button finished.
            self.view.finish_load_layout_button()

    def save_layout(self) -> None:
        """Run the steps of the Save layout flow.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00218: the button does nothing without a data file.
        if not self.data_file_open_b:
            return
        # LLFR-01212, LLFR-01213: the options first; LLFR-01214: a
        # cancel ends the action here.
        option_dict = self.ask_save_options()
        if option_dict is None:
            return
        # LLFR-00219, LLFR-00220: the save file dialog.
        path_str = self.view.ask_layout_save_path(self.dialog_folder())
        # LLFR-00222: a cancelled dialog saves nothing.
        if not path_str:
            return
        # LLFR-00219: ".json" is added to a name without an extension.
        # LLFR-00223: the dialog asked about the path it returned; when
        # ".json" is added here, an existing file of that name is only
        # replaced after the user agrees.
        layout_path_str = ensure_layout_suffix(path_str)
        if (layout_path_str != path_str and os.path.exists(layout_path_str)
                and not self.view.ask_replace_existing_file(
                    layout_path_str)):
            return
        # LLFR-00225, LLFR-00226, LLFR-00227: the content of the file.
        layout_dict = self.plot_controller.layout_dict(
            tuple(self.view.panel_width_tuple()),
            list(self.synthetic_signal_list_function()))
        # LLFR-01215, LLFR-01216: the markers and the tabs chosen.
        layout_dict = layout_with_save_options(
            layout_dict, option_dict[MARKERS_OPTION_KEY_STR],
            not option_dict[ALL_TABS_OPTION_KEY_STR])
        # LLFR-01217: the open data files, when chosen.
        if option_dict[DATA_FILES_OPTION_KEY_STR]:
            layout_dict[DATA_FILES_KEY_STR] = data_file_entry_list(
                self.numbered_path_list(), layout_path_str)
        # LLFR-00224: written safely; a failure is reported.
        saved_b, reason_str = self.view.save_layout_bytes(
            layout_path_str, layout_bytes(layout_dict))
        if not saved_b:
            self.view.show_layout_save_error(reason_str)
            return
        # LLFR-00220: the next dialog shows this folder.
        self.remember_folder(layout_path_str)

    def ask_save_options(self):
        """Return the choices of the save options dialog.

        Inputs: none.
        Outputs: a dict with the keys of LAYOUT_OPTION_KEY_TUPLE, or None
            when the user cancelled (LLFR-01214).
        """
        # LLFR-01212, LLFR-01213: a view without the dialog saves with
        # the first values.
        ask_function = getattr(self.view, "ask_layout_save_options", None)
        if ask_function is None:
            return dict(DEFAULT_LAYOUT_OPTION_DICT)
        answer_dict = ask_function()
        if answer_dict is None:
            return None
        option_dict = dict(DEFAULT_LAYOUT_OPTION_DICT)
        option_dict.update({key_str: bool(answer_dict[key_str])
                            for key_str in LAYOUT_OPTION_KEY_TUPLE
                            if key_str in answer_dict})
        return option_dict

    def numbered_path_list(self) -> list:
        """Return the number and path of each open data file.

        Inputs: none.
        Outputs: a list of (number, path), in number order.
        """
        # LLFR-01217: the open data files.
        data_files = getattr(self.file_controller, "data_files", None)
        if data_files is None:
            return []
        return sorted((int(data_file.number_i), str(data_file.path_str))
                      for data_file in data_files.file_list)

    def open_layout_files(self, layout_dict: dict, layout_path_str: str):
        """Open the data files of a layout file and renumber its names.

        Inputs:
            layout_dict: the content of the layout file, changed in place
                (LLFR-01220).
            layout_path_str: the path of the layout file.
        Outputs: the lines of the load report for the files that are not
            open (LLFR-01221).
        """
        entry_list = data_file_entries_of(layout_dict)
        if not entry_list:
            return []
        data_files = self.file_controller.data_files
        line_list = []
        found_dict = {}
        to_open_list = []
        for saved_number_i, entry_dict, reason_str in entry_list:
            if saved_number_i is None:
                # LLFR-01221: an entry that cannot be read.
                line_list.append(reason_str)
                continue
            candidate_list = data_file_candidate_list(entry_dict,
                                                      layout_path_str)
            # LLFR-01219: a file already open is used as it is.
            open_number_list = [data_files.open_number(candidate_str)
                                for candidate_str in candidate_list]
            open_number_list = [number_value for number_value
                                in open_number_list
                                if number_value is not None]
            if open_number_list:
                found_dict[saved_number_i] = open_number_list[0]
                continue
            # LLFR-01218: at its path, or else at its relative path.
            existing_list = [candidate_str for candidate_str
                             in candidate_list
                             if os.path.isfile(candidate_str)]
            if not existing_list:
                line_list.append(FILE_NOT_FOUND_REASON_STR.format(
                    path=entry_dict.get("path", "")))
                continue
            to_open_list.append((saved_number_i, entry_dict,
                                 existing_list[0]))
        if to_open_list:
            # LLFR-01218: as the Open file button does, with its limit,
            # its time signal window and its boxes.
            self.file_controller.open_paths(
                [path_str for _, _, path_str in to_open_list])
            for saved_number_i, entry_dict, path_str in to_open_list:
                number_value = data_files.open_number(path_str)
                if number_value is None:
                    # LLFR-01221: refused, failed or cancelled.
                    line_list.append(FILE_NOT_OPENED_REASON_STR.format(
                        path=entry_dict.get("path", "")))
                else:
                    found_dict[saved_number_i] = number_value
        # LLFR-01220, LLFR-01222: the names follow the open files.
        open_number_list = [data_file.number_i
                            for data_file in data_files.file_list]
        number_dict = file_number_dict(
            [saved_number_i for saved_number_i, _, _ in entry_list
             if saved_number_i is not None], found_dict, open_number_list)
        renumber_layout_names(layout_dict, number_dict)
        return line_list

    def load_layout(self) -> None:
        """Run the steps of the Load layout flow.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00218: the button does nothing without a data file.
        if not self.data_file_open_b:
            return
        # LLFR-00221, LLFR-00220: the file selection dialog for .json.
        path_str = self.view.ask_layout_load_path(self.dialog_folder())
        # LLFR-00222: a cancelled dialog loads nothing.
        if not path_str:
            return
        # LLFR-00236: an unreadable file, invalid JSON or another JSON
        # file is reported and the layout is kept.
        try:
            layout_dict = read_layout_file(path_str)
        except LayoutFileError as error:
            self.view.show_layout_load_error(str(error))
            return
        except Exception as error:
            # PCR-00025: reported instead of crashing.
            self.view.show_layout_load_error(
                UNEXPECTED_LOAD_ERROR_STR.format(path=path_str, error=error))
            return
        # LLFR-01218 to LLFR-01222: the data files of the layout first.
        data_file_line_list = self.open_layout_files(layout_dict, path_str)
        # PCR-00025: the synthetic signals can be put back.
        restore_function = None
        if self.synthetic_signal_snapshot_function is not None:
            restore_function = self.synthetic_signal_snapshot_function()
        # LLFR-00229 to LLFR-00235, LLFR-00238, LLFR-00262: rebuild the
        # layout, with the synthetic signals of the file.
        try:
            result = self.plot_controller.load_layout(
                layout_dict, self.synthetic_signal_builder,
                restore_function)
        except Exception as error:
            # PCR-00025, LLFR-00236: the plot controller put the
            # synthetic signals and then the layout back as they were.
            self.view.show_layout_load_error(
                UNEXPECTED_LOAD_ERROR_STR.format(path=path_str, error=error))
            return
        if result is None:
            return
        # LLFR-01221: the files that are not open, in the load report.
        for line_str in data_file_line_list:
            result.report.add_data_file(line_str)
        # LLFR-00220: the next dialog shows this folder.
        self.remember_folder(path_str)
        # LLFR-00230: the file's panel widths.
        if result.panel_width_tuple:
            self.view.set_panel_widths(*result.panel_width_tuple)
        # LLFR-01208: the main window's panel shown or hidden as saved;
        # fake views of tests that never hide it may leave it out.
        set_main_panel = getattr(self.view, "set_main_panel", None)
        if (getattr(result, "main_panel_shown_b", None) is not None
                and set_main_panel is not None):
            width_i = (int(result.panel_width_tuple[1])
                       if len(result.panel_width_tuple) == 2 else 0)
            set_main_panel(result.main_panel_shown_b, width_i)
        # LLFR-00237: one information box when something was not
        # rebuilt as saved, none otherwise.
        if not result.report.is_empty():
            self.view.show_layout_report(result.report.text())
