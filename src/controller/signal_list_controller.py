"""Signal list controller: filters the signal list by the search box.

It talks to the view only through plain method calls (no Qt code), so
it can be tested with a fake view (COR-00003, COR-00009). The view must
offer ``set_search_text_handler``, ``show_signal_names``,
``show_no_match_message``, ``clear_search``, ``set_signal_kinds``,
``clear_signal_selection``, ``rename_shown_signal``,
``set_time_signal_names`` and ``show_file_name``.

The list shows the signals of every open data file, with their prefixed
names (LLFR-00901), file after file in the order of their numbers
(LLFR-00934, LLFR-00935), each followed by its own synthetic signals in
creation order (LLFR-00242, LLFR-00936); the SyntheticController gives
the names of the synthetic signals with ``set_synthetic_signals``. The
FileController calls its listeners only after a successful open, so a
failed, cancelled or refused open leaves the list unchanged
(LLFR-00651).

The file name row above the list (LLFR-00362) shows the rows of the open
data files, ``file<N>_<file name>``, separated by commas, until the
signal list shows one row per file (step 4 of issue #190); it is empty
while no file is open (LLFR-00363, LLFR-00933).
"""

import os

from model.signal_search import NO_MATCH_TEXT_STR, search_signals
from model.synthetic_signals import ordered_signal_names

# LLFR-00362: the rows of the open files, in the one row shown for now.
FILE_ROW_SEPARATOR_STR = ", "


def file_name_from_path(path_str: str) -> str:
    """Return the name of a file, with its extension, without its folder.

    Inputs:
        path_str: the path of the file, in the form of the operating
            system the app runs on.
    Outputs: the last part of the path, for example "signals.csv".
    """
    # LLFR-00362: the folder is left out, the extension is kept. The
    # separators of the operating system are used (also the backslash
    # on Windows), so that a backslash in a macOS file name is kept.
    return os.path.basename(str(path_str))


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
        # LLFR-00936: the data file of each synthetic signal.
        self.synthetic_file_dict = {}
        self.signal_file = None
        self.search_text_str = ""
        view.set_search_text_handler(self.on_search_text_changed)
        # LLFR-00104, LLFR-00650: a new file is added to the shown names.
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
                              fft_name_set: set,
                              file_number_dict: dict = None) -> None:
        """Show the current synthetic signals after the data signals.

        Inputs:
            synthetic_name_list: the synthetic signal names, in creation
                order.
            fft_name_set: the names of the FFT signals among them.
            file_number_dict: synthetic signal name -> number of its
                data file (LLFR-00936); None lists them after every file.
        Outputs: none. The list is filtered again by the search text.
        """
        # LLFR-00242, LLFR-00935: after the signals of their own data
        # file, in creation order, in italics, and searchable like the
        # others.
        self.synthetic_name_list = list(synthetic_name_list)
        self.fft_name_set = set(fft_name_set)
        self.synthetic_file_dict = dict(file_number_dict or {})
        self.show_filtered_names()

    def rename_signal(self, old_name_str: str, new_name_str: str) -> None:
        """Rename a shown signal before the list is shown again.

        Inputs:
            old_name_str: the previous name of a synthetic signal.
            new_name_str: its new name.
        Outputs: none. Call set_synthetic_signals afterwards.
        """
        # LLFR-00266, LLFR-00292: the renamed signal is still shown, so
        # it keeps its selection.
        self.view.rename_shown_signal(old_name_str, new_name_str)

    def signal_name_list(self) -> list:
        """Return every name of the signal list, in list order.

        Inputs: none.
        Outputs: file after file, the signals of each data file
            followed by its synthetic signals (LLFR-00934, LLFR-00935).
        """
        # LLFR-00242, LLFR-00935: each file's synthetic signals after
        # its own signals.
        if self.signal_file is None:
            return self.all_signal_name_list + self.synthetic_name_list
        return ordered_signal_names(self.signal_file,
                                    self.synthetic_name_list,
                                    self.synthetic_file_dict)

    def on_file_opened(self, signal_file, added_file=None) -> None:
        """Show the names of the open files after a file was added.

        Called by the FileController after a successful open, so the
        filter applied here gives the final list.

        Inputs:
            signal_file: the DataFileSet of the open data files (or one
                SignalFile).
            added_file: the DataFile just added; not used.
        Outputs: none.
        """
        # LLFR-00104: the search box is cleared when a file is opened.
        # The stored text is reset first, so the change the view reports
        # back already filters the new names.
        self.search_text_str = ""
        self.view.clear_search()
        # LLFR-00917: the signals and synthetic signals of the other
        # files are kept, and so is the selection of the shown signals
        # (LLFR-00292).
        self.show_open_files(signal_file)

    def on_files_closed(self, data_files, closed_file_list: list) -> None:
        """Show the names of the files left after data files were closed.

        Inputs:
            data_files: the DataFileSet of the files left.
            closed_file_list: the closed DataFile objects.
        Outputs: none. The SyntheticController has already removed the
            synthetic signals of the closed files.
        """
        # LLFR-00922, LLFR-00933: the closed files' signals leave the
        # list; LLFR-00292: so they are no longer selected.
        self.show_open_files(data_files)

    def show_open_files(self, signal_file) -> None:
        """Show the file name row and the signals of the open files.

        Inputs:
            signal_file: the DataFileSet of the open data files (or one
                SignalFile).
        Outputs: none.
        """
        # LLFR-00362, LLFR-00363, LLFR-00934: the rows of the open files,
        # in the order of their numbers; none while no file is open.
        file_list = list(getattr(signal_file, "file_list", []))
        if file_list:
            row_str = FILE_ROW_SEPARATOR_STR.join(
                data_file.file_name_row_str for data_file in file_list)
        elif signal_file is not None and getattr(signal_file, "path_str",
                                                 ""):
            row_str = file_name_from_path(signal_file.path_str)
        else:
            row_str = ""
        self.view.show_file_name(row_str)
        # LLFR-00332: every time signal in green.
        self.view.set_time_signal_names(
            list(signal_file.time_signal_name_list))
        # LLFR-00054, LLFR-00934, LLFR-00935: every signal of every open
        # file, the time signals included.
        self.all_signal_name_list = list(signal_file.signal_name_list)
        self.signal_file = signal_file
        # LLFR-00096: an empty box shows every signal.
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
