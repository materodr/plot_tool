"""Signal list controller: filters the signal list by the search box.

It talks to the view only through plain method calls (no Qt code), so
it can be tested with a fake view (COR-00003, COR-00009). The view must
offer ``set_search_text_handler``, ``show_signal_names``,
``show_no_match_message``, ``clear_search`` and ``set_signal_kinds``.

The list shows the data file signals, then the synthetic signals in
creation order (LLFR-00242); the SyntheticController gives the names of
the synthetic signals with ``set_synthetic_signals``.
"""

from model.signal_search import NO_MATCH_TEXT_STR, search_signals


class SignalListController:
    """Shows in the signal list the signals that match the search text.

    Inputs:
        view: the view facade (MainWindow or a fake).
        file_controller: the FileController; this controller registers
            itself as a file-opened listener.
        search_function: function taking (signal_name_list, text_str)
            and returning the matching names in display order;
            search_signals by default.
    Attributes:
        all_signal_name_list: every signal name of the opened file, in
            file order ([] before the first file is opened).
        search_text_str: the text currently in the search box.
    """

    def __init__(self, view, file_controller,
                 search_function=search_signals) -> None:
        """Store the collaborators and connect to the view and files.

        Inputs:
            view: the view facade.
            file_controller: the FileController that reports new files.
            search_function: the function that finds matching names.
        Outputs: none.
        """
        # LLFR-00095: the search text is filtered with search_function.
        self.view = view
        self.search_function = search_function
        self.all_signal_name_list = []
        # LLFR-00242: the synthetic signals, in creation order, and the
        # FFT signals among them (LLFR-00251).
        self.synthetic_name_list = []
        self.fft_name_set = set()
        self.search_text_str = ""
        view.set_search_text_handler(self.on_search_text_changed)
        # LLFR-00104, LLFR-00017: a new file resets the shown names.
        file_controller.add_file_opened_listener(self.on_file_opened)

    def on_search_text_changed(self, text_str: str) -> None:
        """Re-filter the signal list after the search text changed.

        Inputs:
            text_str: the new text of the search box.
        Outputs: none.
        """
        # LLFR-00095: every change of the text filters the list again.
        self.search_text_str = text_str
        self.show_filtered_names()

    def set_synthetic_signals(self, synthetic_name_list: list,
                              fft_name_set: set) -> None:
        """Show the current synthetic signals after the data signals.

        Inputs:
            synthetic_name_list: the synthetic signal names, in creation
                order.
            fft_name_set: the names of the FFT signals among them.
        Outputs: none. The list is filtered again by the search text.
        """
        # LLFR-00242: after the data file signals, in creation order,
        # in italics, and searchable like the others.
        self.synthetic_name_list = list(synthetic_name_list)
        self.fft_name_set = set(fft_name_set)
        self.show_filtered_names()

    def signal_name_list(self) -> list:
        """Return every name of the signal list, in list order.

        Inputs: none.
        Outputs: the data file signals, then the synthetic signals.
        """
        # LLFR-00242: synthetic signals after the data file signals.
        return self.all_signal_name_list + self.synthetic_name_list

    def on_file_opened(self, signal_file, replaced_b: bool) -> None:
        """Show the names of a newly opened file, filtered by the search.

        Called by the FileController after it has shown all names of the
        new file, so the filter applied here gives the final list.

        Inputs:
            signal_file: the SignalFile that was opened.
            replaced_b: True when the new file replaced another one.
        Outputs: none.
        """
        # LLFR-00054: the full list includes the time signal.
        self.all_signal_name_list = list(signal_file.signal_name_list)
        # LLFR-00252: the synthetic signals of the previous data file
        # are gone.
        self.synthetic_name_list = []
        self.fft_name_set = set()
        if replaced_b:
            # LLFR-00104: the search box is cleared on file replace. The
            # stored text is reset first, so the change the view reports
            # back already filters the new file's names.
            self.search_text_str = ""
            self.view.clear_search()
        # LLFR-00017, LLFR-00096: after a replace the box is empty, so
        # every name of the new file is shown; on the first open the
        # text typed before is applied to the new names.
        self.show_filtered_names()

    def show_filtered_names(self) -> None:
        """Show the names that match the current text, and the message.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00095, LLFR-00102: the matches, in the model's order.
        # LLFR-00096: an empty or spaces-only text gives all names.
        # LLFR-00242: synthetic signals are searched like the others.
        shown_name_list = self.search_function(self.signal_name_list(),
                                               self.search_text_str)
        # LLFR-00242, LLFR-00251: which names are synthetic (italics)
        # and which are FFT signals, before the names are shown.
        self.view.set_signal_kinds(set(self.synthetic_name_list),
                                   set(self.fft_name_set))
        self.view.show_signal_names(shown_name_list)
        # LLFR-00097: the message only appears when a file is open, the
        # text is not blank and nothing matches.
        no_match_b = (not shown_name_list
                      and bool(self.all_signal_name_list)
                      and self.search_text_str.strip() != "")
        self.view.show_no_match_message(no_match_b, NO_MATCH_TEXT_STR)
