"""Signal list controller: filters the signal list by the search box.

It talks to the view only through plain method calls (no Qt code), so
it can be tested with a fake view (COR-00003, COR-00009). The view must
offer ``set_search_text_handler``, ``show_signal_groups``,
``clear_search``, ``set_signal_kinds``, ``clear_signal_selection``,
``rename_shown_signal`` and ``set_time_signal_names``, and may offer
``set_file_toggle_handler`` and ``select_only_signal`` (the main window
does; fake views of tests that don't click the icons or select may leave
them out).

The list shows the signals of every open data file, with their prefixed
names (LLFR-00905), file after file in the order of their numbers
(LLFR-00938), each file starting with its file name row,
``file<N>_<file name>`` in bold (LLFR-00362), followed by its signals
and then its own synthetic signals in creation order (LLFR-00939,
LLFR-00242, LLFR-00940); the SyntheticController gives the names of the
synthetic signals with ``set_synthetic_signals``. The FileController
calls its listeners only after a successful open, so a failed, cancelled
or refused open leaves the list unchanged (LLFR-00651).

``show_signal_groups(group_list)`` gets one tuple per group, in list
order: (file number or None, file name row text or "", shown signal
names, no-match text or ""). The search is done per file, so the
matches stay below their own file name row, which the search never
hides (LLFR-00102, LLFR-00639, LLFR-00640), and "No matching signals"
is shown below the row of each file with no match (LLFR-00097,
LLFR-00641). While no file is open, the list is empty (LLFR-00363,
LLFR-00937).

Each file name row can hide and show again the signals of its file, like
a folder of a folder tree (HLFR-00123): before each
``show_signal_groups``, ``set_collapsed_file_numbers`` (when the view
offers it) gives the numbers of the collapsed files, whose rows show the
``[+]`` icon and no signal below them (LLFR-00994 to LLFR-00998).
Every open file is collapsed each time a file is opened (LLFR-01001).
Creating a synthetic signal from the signal menu expands its file and
selects the new signal (``reveal_new_signal``, LLFR-01193, LLFR-01194);
a layout load changes neither.
While the search box holds text, every file is expanded to show its
matches, and a click on an icon then hides or shows the matches only
until the search is cleared, when each file goes back to the state it
had before the search (LLFR-01002 to LLFR-01004). This state is kept
only here: it is not part of a layout file (LLFR-00226) or of the undo
history (LLFR-01008).

The time signal of each file is its first signal, right below its file
name row, also among the matches of a search (LLFR-01009,
LLFR-01010).
"""

import os

from model.signal_search import NO_MATCH_TEXT_STR, search_prefixed_signals
from model.synthetic_signals import ordered_signal_names


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


def is_blank_text(text_str: str) -> bool:
    """Tell whether a search text is empty or holds only spaces.

    Inputs:
        text_str: the text of the search box.
    Outputs: True when nothing but spaces is typed (LLFR-00096).
    """
    # LLFR-00096, LLFR-01002: such a text is no search.
    return str(text_str).strip() == ""


class SignalListController:
    """Shows in the signal list the signals that match the search text.

    Inputs:
        view: the view facade (MainWindow or a fake).
        file_controller: the FileController; this controller registers
            itself as a file-opened listener.
        search_function: function taking (signal_name_list, text_str)
            and returning the matching names in display order;
            search_prefixed_signals by default (LLFR-00102).
    Attributes:
        all_signal_name_list: every signal name of the opened file, in
            file order ([] before the first file is opened).
        search_text_str: the text currently in the search box.
    """

    def __init__(self, view, file_controller,
                 search_function=search_prefixed_signals) -> None:
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
        # LLFR-00940: the data file of each synthetic signal.
        self.synthetic_file_dict = {}
        self.signal_file = None
        self.search_text_str = ""
        # LLFR-00997, LLFR-01001: the numbers of the files whose signals
        # are hidden while the search box is empty.
        self.collapsed_number_set = set()
        # LLFR-01003: the numbers of the files whose matches the user
        # hid during the current search; emptied when the search starts
        # and ends (LLFR-01004).
        self.search_collapsed_number_set = set()
        view.set_search_text_handler(self.on_search_text_changed)
        # LLFR-00997, LLFR-00998: a click on the icon of a file name row
        # hides or shows the signals of that file.
        set_toggle_handler = getattr(view, "set_file_toggle_handler", None)
        if set_toggle_handler is not None:
            set_toggle_handler(self.toggle_file)
        # LLFR-00104, LLFR-00650: a new file is added to the shown names.
        file_controller.add_file_opened_listener(self.on_file_opened)

    def on_search_text_changed(self, text_str: str) -> None:
        """Re-filter the signal list after the search text changed.

        Inputs:
            text_str: the new text of the search box.
        Outputs: none.
        """
        # LLFR-00095: every change of the text filters the list again.
        # LLFR-01002, LLFR-01004: a search that starts or ends forgets
        # the icon clicks of the search, so that the files are expanded
        # during the search and then back in their earlier state.
        if is_blank_text(text_str) != is_blank_text(self.search_text_str):
            self.search_collapsed_number_set = set()
        self.search_text_str = text_str
        self.show_filtered_names()

    def is_searching(self) -> bool:
        """Tell whether the search box holds text other than spaces.

        Inputs: none.
        Outputs: True while a search filters the list (LLFR-00096).
        """
        # LLFR-01002: the search expands the files.
        return not is_blank_text(self.search_text_str)

    def active_collapsed_set(self) -> set:
        """Return the numbers of the files whose rows are collapsed now.

        Inputs: none.
        Outputs: a set of int: during a search, the files whose matches
            the user hid (LLFR-01003); otherwise the collapsed files
            (LLFR-00997, LLFR-01001).
        """
        # LLFR-01002: during a search, every file is expanded except the
        # ones the user collapsed with the icon during that search.
        if self.is_searching():
            return self.search_collapsed_number_set
        return self.collapsed_number_set

    def is_file_collapsed(self, number_i: int) -> bool:
        """Tell whether the signals of a file are hidden now.

        Inputs:
            number_i: the number of an open data file (LLFR-00900).
        Outputs: True while its row shows the [+] icon (LLFR-00995).
        """
        # LLFR-00994, LLFR-00995: the icon follows this state.
        return int(number_i) in self.active_collapsed_set()

    def toggle_file(self, number_i: int) -> None:
        """Hide or show again the signals of one data file.

        Called when the user clicks the icon of its file name row, or
        presses Left or Right on that row.

        Inputs:
            number_i: the number of the file of the row (LLFR-00900).
        Outputs: none. The list is shown again; a signal that this hides
            is no longer selected (LLFR-01005). The undo and redo history
            is left unchanged (LLFR-01008).
        """
        # LLFR-00997, LLFR-00998: [-] hides the signals, [+] shows them;
        # LLFR-01003: during a search, only for that search. LLFR-01008:
        # no snapshot is taken, so the undo and redo history stays.
        number_i = int(number_i)
        collapsed_set = self.active_collapsed_set()
        if number_i in collapsed_set:
            collapsed_set.discard(number_i)
        else:
            collapsed_set.add(number_i)
        self.show_filtered_names()

    def reveal_new_signal(self, signal_name_str: str,
                          file_number_value) -> None:
        """Show and select a synthetic signal the user just created.

        Inputs:
            signal_name_str: the name of the new synthetic signal, which
                set_synthetic_signals already lists.
            file_number_value: the number of its data file (LLFR-00940),
                or None.
        Outputs: none. Its file is expanded, also for the state the
            file gets back after a search (LLFR-01004), and the new
            signal becomes the only selected signal of every panel
            (LLFR-01036). The undo and redo history is left unchanged
            (LLFR-01008).
        """
        # LLFR-01193: a collapsed file of the new signal is expanded, in
        # the state shown now and in the state outside a search.
        if file_number_value is not None:
            number_i = int(file_number_value)
            self.collapsed_number_set.discard(number_i)
            self.search_collapsed_number_set.discard(number_i)
        self.show_filtered_names()
        # LLFR-01194: the new signal is selected, alone; fake views of
        # tests that don't select may leave the method out.
        select_signal = getattr(self.view, "select_only_signal", None)
        if select_signal is not None:
            select_signal(signal_name_str)

    def set_synthetic_signals(self, synthetic_name_list: list,
                              fft_name_set: set,
                              file_number_dict: dict = None) -> None:
        """Show the current synthetic signals after the data signals.

        Inputs:
            synthetic_name_list: the synthetic signal names, in creation
                order.
            fft_name_set: the names of the FFT signals among them.
            file_number_dict: synthetic signal name -> number of its
                data file (LLFR-00940); None lists them after every file.
        Outputs: none. The list is filtered again by the search text.
        """
        # LLFR-00242, LLFR-00939: after the signals of their own data
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
            followed by its synthetic signals (LLFR-00938, LLFR-00939).
        """
        # LLFR-00242, LLFR-00939: each file's synthetic signals after
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
        self.search_collapsed_number_set = set()
        # LLFR-01001: every open file, the new one and the ones already
        # open, is shown collapsed, with no signal row.
        self.collapsed_number_set = {
            int(data_file.number_i) for data_file
            in getattr(signal_file, "file_list", [])}
        self.view.clear_search()
        # LLFR-00921: the signals and synthetic signals of the other
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
        # LLFR-00926, LLFR-00937: the closed files' signals leave the
        # list; LLFR-00292: so they are no longer selected. LLFR-00997:
        # the files left keep their expanded or collapsed state.
        closed_number_set = {int(data_file.number_i)
                             for data_file in closed_file_list}
        self.collapsed_number_set -= closed_number_set
        self.search_collapsed_number_set -= closed_number_set
        self.show_open_files(data_files)

    def show_open_files(self, signal_file) -> None:
        """Show the file name rows and the signals of the open files.

        Inputs:
            signal_file: the DataFileSet of the open data files (or one
                SignalFile).
        Outputs: none.
        """
        # LLFR-00332: every time signal in green.
        self.view.set_time_signal_names(
            list(signal_file.time_signal_name_list))
        # LLFR-00054, LLFR-00938, LLFR-00939: every signal of every open
        # file, the time signals included.
        self.all_signal_name_list = list(signal_file.signal_name_list)
        self.signal_file = signal_file
        # LLFR-00096: an empty box shows every signal.
        self.show_filtered_names()

    def signal_groups(self) -> list:
        """Return the groups of the signal list, before the search.

        Inputs: none.
        Outputs: a list of tuples (file number or None, file name row
            text or "", every name of the group in list order, True for
            the group of a data file): one group per open data file, in
            the order of the numbers, with its signals and its synthetic
            signals (LLFR-00938, LLFR-00939, LLFR-00242); [] while no
            file is open (LLFR-00363). One SignalFile given without a
            DataFileSet (as some tests do) is one group with no row.
        """
        # LLFR-00363, LLFR-00937: no row and no signal without a file.
        if self.signal_file is None:
            return []
        file_list = list(getattr(self.signal_file, "file_list", []))
        if not file_list:
            # LLFR-00363: no data file of a DataFileSet, so no row; the
            # names of one SignalFile are shown as one group.
            name_list = self.signal_name_list()
            if not name_list:
                return []
            return [(None, "", name_list, True)]
        group_list = []
        placed_name_set = set()
        for data_file in file_list:
            # LLFR-00939, LLFR-00940: the file's signals, then its own
            # synthetic signals in creation order.
            own_synthetic_list = [
                name_str for name_str in self.synthetic_name_list
                if self.synthetic_file_dict.get(name_str)
                == data_file.number_i]
            placed_name_set.update(own_synthetic_list)
            # LLFR-01009: the time signal first, below the file name row.
            group_list.append((
                data_file.number_i, data_file.file_name_row_str,
                list(data_file.listed_signal_name_list)
                + own_synthetic_list, True))
        # LLFR-00242: a synthetic signal of no open file (none in the
        # app) would come last, with no file name row.
        other_name_list = [name_str for name_str in self.synthetic_name_list
                           if name_str not in placed_name_set]
        if other_name_list:
            group_list.append((None, "", other_name_list, False))
        return group_list

    def time_name_of_file(self, number_value) -> str:
        """Return the time signal of one open data file.

        Inputs:
            number_value: the number of the file, or None.
        Outputs: its prefixed name, or "" when there is no such file.
        """
        # LLFR-01009, LLFR-01010: the row kept first below the file row.
        for data_file in getattr(self.signal_file, "file_list", []):
            if data_file.number_i == number_value:
                return str(data_file.time_signal_name_str)
        return ""

    def show_filtered_names(self) -> None:
        """Show the names that match the current text, file after file.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00096: an empty or spaces-only text gives all names.
        blank_text_b = is_blank_text(self.search_text_str)
        shown_group_list = []
        for number_i, row_str, name_list, file_b in self.signal_groups():
            # LLFR-00997, LLFR-01001, LLFR-01003: a collapsed file shows
            # its row with the [+] icon and nothing below it, so that its
            # signals are no longer selected (LLFR-01005).
            if row_str and number_i is not None and (
                    self.is_file_collapsed(number_i)):
                shown_group_list.append((number_i, row_str, [], ""))
                continue
            # LLFR-00095, LLFR-00102: the matches of each file, below
            # its own file name row, in the three groups formed within
            # the file. LLFR-00242: synthetic signals are searched like
            # the others.
            shown_name_list = list(self.search_function(
                name_list, self.search_text_str))
            # LLFR-01010: a matching time signal stays the first signal
            # of its file, whatever group of LLFR-00102 it is in.
            time_name_str = self.time_name_of_file(number_i)
            if time_name_str in shown_name_list:
                shown_name_list.remove(time_name_str)
                shown_name_list.insert(0, time_name_str)
            # LLFR-00097, LLFR-00641: "No matching signals" below the
            # row of a file none of whose signals matches the text.
            no_match_str = ""
            if not shown_name_list and not blank_text_b and file_b:
                no_match_str = NO_MATCH_TEXT_STR
            if not row_str and not shown_name_list and not no_match_str:
                # A group with no row shows nothing when nothing matches.
                continue
            # LLFR-00994, LLFR-01002: an expanded file, with the [-] icon.
            shown_group_list.append(
                (number_i, row_str, shown_name_list, no_match_str))
        # LLFR-00242, LLFR-00251: which names are synthetic (italics)
        # and which are FFT signals, before the names are shown.
        self.view.set_signal_kinds(set(self.synthetic_name_list),
                                   set(self.fft_name_set))
        # LLFR-00994, LLFR-00995: which file name rows show [+]; fake
        # views of tests that don't draw the icons may leave it out.
        set_collapsed = getattr(self.view, "set_collapsed_file_numbers",
                                None)
        if set_collapsed is not None:
            set_collapsed(set(self.active_collapsed_set()))
        # LLFR-00639, LLFR-00640: every file name row stays, above the
        # shown signals of its file.
        self.view.show_signal_groups(shown_group_list)
