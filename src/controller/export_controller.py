"""Export controller: saves the plots to PDF and copies them as an image.

It runs the flows started by the Export and Copy buttons of the top
panel (HLFR-00038, HLFR-00039). It talks to the view only through plain
method calls (no Qt code), so it can be tested with a fake view
(COR-00003, COR-00009). The view must offer:

- ``exportable_tab_count()``: number of tabs that hold a plot;
- ``current_tab_plot_count()``: number of plots in the current tab;
- ``ask_pdf_save_path()``: the chosen path, "" when cancelled;
- ``save_tabs_pdf(path_str)``: a tuple (saved_b, reason_str);
- ``copy_current_tab_image()``: a tuple (copied_b, reason_str);
- ``show_nothing_to_export()``, ``show_nothing_to_copy()``;
- ``show_export_error(reason_str)``, ``show_copy_error(reason_str)``;
- ``finish_export_button()``, ``finish_copy_button()``.
"""

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
    """Runs the "Save all tabs as PDF" and "Copy" flows.

    Inputs:
        view: the view facade described in the module docstring.
    Attributes:
        view: the view facade.
    """

    def __init__(self, view) -> None:
        """Store the view.

        Inputs:
            view: the view facade.
        Outputs: none.
        """
        # LLFR-00127, LLFR-00132: the view calls this controller when
        # the menu option or the Copy button is chosen.
        self.view = view

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
        path_str = self.view.ask_pdf_save_path()
        # LLFR-00130: a cancelled dialog saves nothing.
        if not path_str:
            return
        # LLFR-00129: one page per tab that holds a plot.
        saved_b, reason_str = self.view.save_tabs_pdf(
            ensure_pdf_suffix(path_str))
        # LLFR-00131: the user is told when the file was not written.
        if not saved_b:
            self.view.show_export_error(reason_str)

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
        copied_b, reason_str = self.view.copy_current_tab_image()
        if not copied_b:
            # LLFR-00133: a failed copy is reported (HLFR-00002).
            self.view.show_copy_error(reason_str)
