"""Export controller: exports the plots and copies them as an image.

It runs the flows started by the Export and Copy buttons of the top
panel and by Ctrl+P (HLFR-00038, HLFR-00039): the Export window, then
the PDF, Word or PNG export of the format chosen in it. It talks to
the view only through plain method calls (no Qt code), so it can be
tested with a fake view (COR-00003, COR-00009). The view must offer:

- ``exportable_tab_count()``: number of tabs that hold a plot;
- ``ask_export_format()``: shows the Export window and returns the
  format clicked, one of model.export_files.EXPORT_FORMAT_TUPLE, or ""
  when it was closed with no format (LLFR-00127, LLFR-01403,
  LLFR-01404);
- ``current_tab_plot_count()``: number of plots in the current tab;
- ``ask_pdf_save_path(start_folder_str)``: the chosen path, "" when
  cancelled; the dialog shows start_folder_str (LLFR-01179,
  LLFR-01180);
- ``ask_replace_existing_file(path_str)``: True to replace the file;
- ``save_tabs_pdf(path_str, description_str)``: a tuple (saved_b,
  reason_str); each page shows description_str below the tab's name
  (LLFR-00971);
- ``copy_current_tab_image(description_str)``: a tuple (copied_b,
  reason_str); the image has a strip with description_str above the
  plots (LLFR-00972);
- ``window_tab_plot_count(tab_id_i)``, ``copy_window_tab_image(
  description_str, tab_id_i)`` and ``show_nothing_to_copy_in(tab_id_i)``:
  the same for the tab shown in a window, -1 for the main window
  (LLFR-01136, LLFR-01138);
- ``show_nothing_to_export()``, ``show_nothing_to_copy()``;
- ``show_export_error(reason_str)``, ``show_copy_error(reason_str)``;
- ``finish_export_button()``, ``finish_copy_button()``;
- for the Word and PNG exports (LLFR-01229): ``ask_docx_save_path(
  start_folder_str)``, ``save_tabs_docx(path_str, description_str)``,
  ``ask_png_folder(start_folder_str)``, ``exportable_tab_name_list()``,
  ``ask_replace_existing_files(folder_str, file_name_list)`` and
  ``save_tab_png_files(folder_str, file_name_list, description_str)``.

The three exports share one dialog folder (LLFR-01243): the folder of the
last file that any of them saved successfully, or, before the first, the
folder the Open file dialog would show (LLFR-01179, LLFR-01180).
"""

import os

from model.export_files import (
    DOCX_FORMAT_STR, PDF_FORMAT_STR, PNG_FORMAT_STR, ensure_docx_suffix,
    png_file_name_list)

# LLFR-00128: the extension of the saved file.
PDF_SUFFIX_STR = ".pdf"


def ensure_pdf_suffix(path_str: str) -> str:
    """Return the path with ``.pdf`` added when it has another ending.

    Inputs:
        path_str: the path typed or chosen in the save file dialog.
    Outputs: path_str when it already ends with ``.pdf`` (in any case),
        otherwise path_str followed by ``.pdf``.
    """
    # LLFR-00128: the saved file is always a .pdf file.
    if path_str.lower().endswith(PDF_SUFFIX_STR):
        return path_str
    return path_str + PDF_SUFFIX_STR


class ExportController:
    """Runs the flows of the Export window and of "Copy".

    Inputs:
        view: the view facade described in the module docstring.
        description_function: function without arguments that returns
            the description of the open data files, ``file1 = a.csv,
            file2 = b.mat`` (LLFR-00971); None gives "".
        open_folder_function: function without arguments that returns
            the folder the Open file dialog would show now (LLFR-00204,
            LLFR-00447); None gives "".
    Attributes:
        view: the view facade.
        description_function: the function of the description.
        open_folder_function: the function of the Open file folder.
        pdf_folder_str: folder of the last PDF file saved successfully,
            "" before the first one.
    """

    def __init__(self, view, description_function=None,
                 open_folder_function=None) -> None:
        """Store the view and the description of the data files.

        Inputs:
            view: the view facade.
            description_function: see the class docstring.
            open_folder_function: see the class docstring.
        Outputs: none.
        """
        # LLFR-00127, LLFR-00132: the view calls this controller when
        # the Export button, Ctrl+P or the Copy button is used.
        self.view = view
        # LLFR-00971, LLFR-00972: the open data files, at export time.
        self.description_function = description_function
        # LLFR-01179, LLFR-01180: the folders of the PDF dialog.
        self.open_folder_function = open_folder_function
        self.pdf_folder_str = ""

    def dialog_folder(self) -> str:
        """Return the folder the next PDF save dialog shows.

        Inputs: none.
        Outputs: the folder of the last PDF file saved successfully, or
            else the folder the Open file dialog would show now.
        """
        # LLFR-01180: after a PDF was saved, the folder of the last one.
        if self.pdf_folder_str:
            return self.pdf_folder_str
        # LLFR-01179: before, the folder of the last data file opened,
        # or the app's folder before any (LLFR-00204, LLFR-00447).
        if self.open_folder_function is None:
            return ""
        return str(self.open_folder_function() or "")

    def files_description(self) -> str:
        """Return the description of the open data files.

        Inputs: none.
        Outputs: the text of LLFR-00971, or "" without a function.
        """
        # LLFR-00971: all the open data files, in number order.
        if self.description_function is None:
            return ""
        return str(self.description_function() or "")

    def on_export_window_requested(self) -> None:
        """Show the Export window and run the export of the chosen format.

        Inputs: none.
        Outputs: none. With no plot in any tab, only the box of LLFR-00145
            is shown. The Export button always returns to normal at the
            end.
        """
        try:
            # LLFR-01407, LLFR-00145, LLFR-00459, LLFR-01237: nothing to
            # export, so the box and no Export window.
            if self.view.exportable_tab_count() <= 0:
                self.view.show_nothing_to_export()
                return
            # LLFR-00127, LLFR-01139: the Export window.
            format_str = self.view.ask_export_format()
            # LLFR-01403: the export of the format clicked; LLFR-01404: no
            # format, nothing saved and no message.
            export_function = {
                PDF_FORMAT_STR: self._export_pdf,
                DOCX_FORMAT_STR: self._export_docx,
                PNG_FORMAT_STR: self._export_png,
            }.get(format_str)
            if export_function is not None:
                export_function()
        finally:
            # LLFR-00003: the function started by the button finished,
            # whatever happened.
            self.view.finish_export_button()

    def on_export_requested(self) -> None:
        """Save the plots of all tabs to a PDF file chosen by the user.

        Inputs: none.
        Outputs: none. The Export button always returns to normal at
            the end.
        """
        try:
            self._export_pdf()
        finally:
            # LLFR-00003: the function started by the button finished,
            # whatever happened.
            self.view.finish_export_button()

    def on_copy_requested(self) -> None:
        """Put an image of the current tab's plots on the clipboard.

        Inputs: none.
        Outputs: none. The Copy button always returns to normal at the
            end.
        """
        try:
            self._copy_image()
        finally:
            # LLFR-00003: the copy has finished, whatever happened.
            self.view.finish_copy_button()

    def on_copy_shortcut(self, window_tab_id_i: int) -> None:
        """Copy the plots of the tab shown in the window of Ctrl+C.

        Inputs:
            window_tab_id_i: the tab of the undocked window where Ctrl+C
                (Cmd+C) was pressed, or -1 for the main window.
        Outputs: none. The Copy button is not involved.
        """
        # LLFR-01138: with no plot in that tab, the box over its window.
        if self.view.window_tab_plot_count(window_tab_id_i) <= 0:
            self.view.show_nothing_to_copy_in(window_tab_id_i)
            return
        # LLFR-01136: the image of the tab shown in that window, as the
        # Copy button does for the main window (LLFR-00133, LLFR-00972).
        copied_b, reason_str = self.view.copy_window_tab_image(
            self.files_description(), window_tab_id_i)
        if not copied_b:
            # LLFR-00133: a failed copy is reported (HLFR-00002).
            self.view.show_copy_error(reason_str)

    def _export_pdf(self) -> None:
        """Run the steps of the PDF export.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00145: with no plot in any tab, there is nothing to save
        # and the save file dialog is not shown.
        if self.view.exportable_tab_count() <= 0:
            self.view.show_nothing_to_export()
            return
        # LLFR-00128: ask where to save the .pdf file.
        # LLFR-01179, LLFR-01180: in the folder of the PDF dialog.
        path_str = self.view.ask_pdf_save_path(self.dialog_folder())
        # LLFR-00130: a cancelled dialog saves nothing.
        if not path_str:
            return
        # LLFR-00128: the dialog asked about the path it returned; when
        # ".pdf" is added here, an existing file of that name is only
        # replaced after the user agrees.
        pdf_path_str = ensure_pdf_suffix(path_str)
        if (pdf_path_str != path_str and os.path.exists(pdf_path_str)
                and not self.view.ask_replace_existing_file(pdf_path_str)):
            return
        # LLFR-00129: one page per tab that holds a plot.
        # LLFR-00971: the open data files below each tab's name.
        saved_b, reason_str = self.view.save_tabs_pdf(
            pdf_path_str, self.files_description())
        # LLFR-00131: the user is told when the file was not written.
        if not saved_b:
            self.view.show_export_error(reason_str)
            return
        # LLFR-01180: only a successful save moves the dialog folder.
        self.pdf_folder_str = os.path.dirname(os.path.abspath(pdf_path_str))

    def on_docx_export_requested(self) -> None:
        """Save the plots of all tabs to a Word document.

        Inputs: none.
        Outputs: none. The Export button always returns to normal at
            the end.
        """
        try:
            self._export_docx()
        finally:
            # LLFR-00003: the function started by the button finished.
            self.view.finish_export_button()

    def on_png_export_requested(self) -> None:
        """Save one PNG file per tab that holds a plot.

        Inputs: none.
        Outputs: none. The Export button always returns to normal at
            the end.
        """
        try:
            self._export_png()
        finally:
            # LLFR-00003: the function started by the button finished.
            self.view.finish_export_button()

    def _export_docx(self) -> None:
        """Run the steps of the Word export.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01237, LLFR-00145, LLFR-00459: nothing to save, no dialog.
        if self.view.exportable_tab_count() <= 0:
            self.view.show_nothing_to_export()
            return
        # LLFR-01230, LLFR-01243: the dialog in the shared folder.
        path_str = self.view.ask_docx_save_path(self.dialog_folder())
        # LLFR-01241, LLFR-00130: a cancelled dialog saves nothing.
        if not path_str:
            return
        docx_path_str = ensure_docx_suffix(path_str)
        if (docx_path_str != path_str and os.path.exists(docx_path_str)
                and not self.view.ask_replace_existing_file(docx_path_str)):
            return
        # LLFR-01231, LLFR-01232: one page per tab that holds a plot.
        saved_b, reason_str = self.view.save_tabs_docx(
            docx_path_str, self.files_description())
        # LLFR-01242, LLFR-00131: the user is told when it failed.
        if not saved_b:
            self.view.show_export_error(reason_str)
            return
        # LLFR-01243, LLFR-01180: the shared folder moves.
        self.pdf_folder_str = os.path.dirname(os.path.abspath(docx_path_str))

    def _export_png(self) -> None:
        """Run the steps of the PNG export.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01237, LLFR-00145, LLFR-00459: nothing to save, no dialog.
        if self.view.exportable_tab_count() <= 0:
            self.view.show_nothing_to_export()
            return
        # LLFR-01233, LLFR-01243: the folder dialog in the shared folder.
        folder_str = self.view.ask_png_folder(self.dialog_folder())
        # LLFR-01241, LLFR-00130: a cancelled dialog saves nothing.
        if not folder_str:
            return
        # LLFR-01235: one safe, unique name per tab.
        file_name_list = png_file_name_list(
            self.view.exportable_tab_name_list())
        # LLFR-01236, LLFR-01240: one question for the files already
        # there, and no file saved without a Yes.
        existing_name_list = [
            file_name_str for file_name_str in file_name_list
            if os.path.exists(os.path.join(folder_str, file_name_str))]
        if existing_name_list and not self.view.ask_replace_existing_files(
                folder_str, existing_name_list):
            return
        # LLFR-01234: the files.
        saved_b, reason_str = self.view.save_tab_png_files(
            folder_str, file_name_list, self.files_description())
        # LLFR-01242, LLFR-00131: the user is told when one failed.
        if not saved_b:
            self.view.show_export_error(reason_str)
            return
        # LLFR-01243, LLFR-01180: the shared folder moves.
        self.pdf_folder_str = os.path.abspath(folder_str)

    def _copy_image(self) -> None:
        """Run the steps of the copy to the clipboard.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00146: with no plot in the current tab, the clipboard is
        # left as it is.
        if self.view.current_tab_plot_count() <= 0:
            self.view.show_nothing_to_copy()
            return
        # LLFR-00133: copy the plots of the current tab as shown.
        # LLFR-00972: the strip with the open data files above them.
        copied_b, reason_str = self.view.copy_current_tab_image(
            self.files_description())
        if not copied_b:
            # LLFR-00133: a failed copy is reported (HLFR-00002).
            self.view.show_copy_error(reason_str)
