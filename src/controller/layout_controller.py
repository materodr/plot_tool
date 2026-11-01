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
- ``finish_save_layout_button()``, ``finish_load_layout_button()``.

Dialog folder (LLFR-00220): until a layout file is saved or loaded
successfully, the dialogs show the folder the Open file dialog would
show at that moment (the file controller's ``dialog_folder_str``,
LLFR-00204); after that, the folder of the last layout file saved or
loaded successfully.
"""

import os

from model.layout_file import (
    LayoutFileError, ensure_layout_suffix, layout_bytes, read_layout_file)

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

    def on_file_opened(self, signal_file, replaced_b: bool) -> None:
        """Enable the layout buttons once a data file is open.

        Inputs:
            signal_file: the SignalFile that was opened.
            replaced_b: True when it replaced another file.
        Outputs: none.
        """
        # LLFR-00218: enabled after a successful open.
        self.data_file_open_b = signal_file is not None
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
        # LLFR-00224: written safely; a failure is reported.
        saved_b, reason_str = self.view.save_layout_bytes(
            layout_path_str, layout_bytes(layout_dict))
        if not saved_b:
            self.view.show_layout_save_error(reason_str)
            return
        # LLFR-00220: the next dialog shows this folder.
        self.remember_folder(layout_path_str)

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
        # PCR-00025: the synthetic signals can be put back.
        restore_function = None
        if self.synthetic_signal_snapshot_function is not None:
            restore_function = self.synthetic_signal_snapshot_function()
        # LLFR-00229 to LLFR-00235, LLFR-00238, LLFR-00262: rebuild the
        # layout, with the synthetic signals of the file.
        try:
            result = self.plot_controller.load_layout(
                layout_dict, self.synthetic_signal_builder)
        except Exception as error:
            # PCR-00025, LLFR-00236: the plot controller put the layout
            # back as it was, and the synthetic signals are put back.
            if restore_function is not None:
                restore_function()
            self.view.show_layout_load_error(
                UNEXPECTED_LOAD_ERROR_STR.format(path=path_str, error=error))
            return
        if result is None:
            return
        # LLFR-00220: the next dialog shows this folder.
        self.remember_folder(path_str)
        # LLFR-00230: the file's panel widths.
        if result.panel_width_tuple:
            self.view.set_panel_widths(*result.panel_width_tuple)
        # LLFR-00237: one information box when something was not
        # rebuilt as saved, none otherwise.
        if not result.report.is_empty():
            self.view.show_layout_report(result.report.text())
