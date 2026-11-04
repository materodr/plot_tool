"""The data files open at the same time (HLFR-00113 to HLFR-00117).

Each file opened with the Open file button is a data file (HLFR-00049).
Up to 10 can be open at once (LLFR-00891). Each one gets a number when
it is opened: 1 more than the highest number given since the app started
(LLFR-00896); a closed file's number is never given again (LLFR-00898),
and a file that is not opened takes no number (LLFR-00899).

Every signal of a data file is named, everywhere in the app, with the
prefix ``file<N>_`` in front of its name in the file (LLFR-00901,
LLFR-00902), for example ``file1_Speed``. The time signal of each file
is found by its name in the file, before the prefix is added
(LLFR-00905), and each signal is drawn against the time signal of its
own file (LLFR-00908).

``DataFileSet`` offers the same reading methods as one SignalFile
(``signal_dict``, ``signal_name_list``, ``signal_array``,
``time_array_for_signal``, ``time_range_tuple``), for the prefixed names
of every open file, so that the controllers work in the same way with
one file or several.
"""

import os
import re

import numpy as np

# LLFR-00891: the most data files open at the same time.
MAXIMUM_DATA_FILES_I = 10
# LLFR-00901: the prefix of every signal name of data file N.
FILE_PREFIX_FORMAT_STR = "file{number}_"
# LLFR-00901, LLFR-00945, LLFR-00966: a name that starts with a prefix.
FILE_PREFIX_PATTERN = re.compile(r"file([0-9]+)_")
# LLFR-00967: one data file in the description of the PDF pages and of
# the copied image, and the separator between two of them.
FILE_DESCRIPTION_FORMAT_STR = "file{number} = {name}"
FILE_DESCRIPTION_SEPARATOR_STR = ", "


def prefix_number(name_str: str):
    """Return the file number of the prefix a name starts with.

    Inputs:
        name_str: a signal name.
    Outputs: N when the name starts with ``file<N>_`` (LLFR-00901), or
        None when it starts with no prefix.
    """
    # LLFR-00901, LLFR-00945: `file`, a number and `_` at the start.
    match = FILE_PREFIX_PATTERN.match(str(name_str))
    if match is None:
        return None
    return int(match.group(1))


def without_prefix(name_str: str) -> str:
    """Return a name without the prefix it starts with.

    Inputs:
        name_str: a signal name.
    Outputs: the name after its ``file<N>_`` prefix, or the name itself
        when it starts with no prefix.
    """
    # LLFR-00904, LLFR-00941, LLFR-00966: the part after the prefix.
    match = FILE_PREFIX_PATTERN.match(str(name_str))
    if match is None:
        return str(name_str)
    return str(name_str)[match.end():]


def file_prefix(number_i: int) -> str:
    """Return the prefix of the signal names of a data file.

    Inputs:
        number_i: the number of the data file (LLFR-00896).
    Outputs: ``file<N>_``, for example "file1_".
    """
    # LLFR-00901: `file`, the file's number and `_`.
    return FILE_PREFIX_FORMAT_STR.format(number=int(number_i))


def prefixed_name(number_i: int, name_str: str) -> str:
    """Return the name a signal of a data file has in the app.

    Inputs:
        number_i: the number of the data file.
        name_str: the signal's name in the file.
    Outputs: the prefixed name, for example "file1_Speed".
    """
    # LLFR-00901, LLFR-00902: also while only one file is open.
    return file_prefix(number_i) + str(name_str)


def same_file_b(first_path_str: str, second_path_str: str) -> bool:
    """Tell whether two paths lead to the same file on disk.

    Inputs:
        first_path_str: a path.
        second_path_str: another path.
    Outputs: True when both lead to the same file, for example through
        a symbolic link; for a path that does not exist, when both give
        the same absolute path once links are followed.
    """
    # LLFR-00894 Note: two paths name the same file when they lead to
    # the same file on disk.
    try:
        return os.path.samefile(first_path_str, second_path_str)
    except (OSError, ValueError, TypeError):
        pass
    try:
        return (os.path.normcase(os.path.realpath(str(first_path_str)))
                == os.path.normcase(os.path.realpath(str(second_path_str))))
    except (OSError, ValueError):
        return False


def finite_range_tuple(time_array) -> tuple:
    """Return the first and last finite time of a time signal.

    Inputs:
        time_array: the time samples, in seconds.
    Outputs: (lowest_s, highest_s), or () when no sample is finite.
    """
    # LLFR-00912: from the first to the last time sample of a file.
    sample_array = np.asarray(time_array, dtype=float)
    sample_array = sample_array[np.isfinite(sample_array)]
    if sample_array.size == 0:
        return ()
    return (float(np.min(sample_array)), float(np.max(sample_array)))


def selection_order_list(path_list: list) -> list:
    """Return selected paths in the order the app takes them.

    Inputs:
        path_list: the paths selected in the file selection dialog.
    Outputs: the paths sorted by their file names without the folders,
        in character order that ignores uppercase and lowercase letters
        (LLFR-00948); names that differ only in case keep the order of
        an exact comparison (LLFR-00970).
    """
    # LLFR-00948: characters, not numbers, so run10 comes before run2.
    # LLFR-00970: the exact comparison breaks the tie of a case-only
    # difference.
    return sorted(
        (str(path_str) for path_str in path_list),
        key=lambda path_str: (os.path.basename(path_str).casefold(),
                              os.path.basename(path_str)))


class DataFile:
    """One open data file with its number (HLFR-00114).

    Inputs:
        number_i: the number given when it was opened (LLFR-00896).
        signal_file: the SignalFile read from the file, with the names
            of the file and its time signal set.
        path_str: the path the file was selected with; None takes the
            path of signal_file.
    Attributes:
        number_i: the file number, kept while it is open (LLFR-00897).
        signal_file: the SignalFile with the names in the file.
        prefix_str: ``file<N>_``.
        path_str: the path of the file.
        signal_dict: prefixed name -> samples, in the file's order.
        time_signal_name_str: the prefixed name of its time signal.
    """

    def __init__(self, number_i: int, signal_file,
                 path_str: str = None) -> None:
        """Name the signals of the file with its prefix.

        Inputs: see the class docstring.
        Outputs: none. Raises KeyError when the file has no time signal.
        """
        # LLFR-00896, LLFR-00897: the number given at the open.
        self.number_i = int(number_i)
        self.signal_file = signal_file
        self.prefix_str = file_prefix(self.number_i)
        if path_str is None:
            path_str = signal_file.path_str
        self.path_str = str(path_str)
        # LLFR-00901, LLFR-00903: the prefixed names are the names of the
        # signals everywhere in the app, in the file's order.
        self.signal_dict = {
            self.prefix_str + str(name_str): value_array
            for name_str, value_array in signal_file.signal_dict.items()}
        # LLFR-00905: the time signal was found by its name in the file
        # (or chosen, LLFR-00326); it keeps the prefix in the app.
        if signal_file.time_signal_name_str is None:
            raise KeyError("no time signal")
        self.time_signal_name_str = (self.prefix_str
                                     + signal_file.time_signal_name_str)

    @property
    def file_name_str(self) -> str:
        """Return the name of the file, with its extension.

        Inputs: none.
        Outputs: the name without its folder, for example "run_A.csv".
        """
        # LLFR-00362: the folder is left out, the extension is kept.
        return os.path.basename(self.path_str)

    @property
    def file_name_row_str(self) -> str:
        """Return the text of the file name row of this file.

        Inputs: none.
        Outputs: ``file<N>_<file name>``, for example
            "file1_run_A.csv".
        """
        # LLFR-00362: `file`, the number, `_` and the file name.
        return self.prefix_str + self.file_name_str

    @property
    def signal_name_list(self) -> list:
        """Return the prefixed names of the file's signals.

        Inputs: none.
        Outputs: the names in the file's order, the time signal included
            (LLFR-00054).
        """
        # LLFR-00054, LLFR-00935: every signal, in the file's order.
        return list(self.signal_dict)

    @property
    def time_array(self):
        """Return the time signal of the file.

        Inputs: none.
        Outputs: the numpy array of its times, in seconds.
        """
        # HLFR-00006, HLFR-00007, LLFR-00908: the times of this file.
        return self.signal_dict[self.time_signal_name_str]

    def time_range_tuple(self) -> tuple:
        """Return the time range of the file.

        Inputs: none.
        Outputs: (first time, last time) in seconds, or ().
        """
        # LLFR-00912: from the first to the last time sample.
        return finite_range_tuple(self.time_array)

    def plain_name(self, signal_name_str: str) -> str:
        """Return a signal's name in the file, without the prefix.

        Inputs:
            signal_name_str: a prefixed name of this file.
        Outputs: the name in the file; the name itself when it does not
            start with this file's prefix.
        """
        # LLFR-00906: the name in the file, before the prefix is added.
        if str(signal_name_str).startswith(self.prefix_str):
            return str(signal_name_str)[len(self.prefix_str):]
        return str(signal_name_str)


class DataFileSet:
    """The data files open at the same time, in number order.

    Inputs: none.
    Attributes:
        file_list: the open DataFile objects, in the order of their
            numbers (LLFR-00934).
        highest_number_i: the highest number given since the app
            started, 0 before the first file (LLFR-00896, LLFR-00898).
    """

    def __init__(self) -> None:
        """Start with no data file open.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00896: the first data file opened gets the number 1.
        self.file_list = []
        self.highest_number_i = 0

    # Files --------------------------------------------------------

    def __len__(self) -> int:
        """Return the number of open data files.

        Inputs: none.
        Outputs: the count, from 0 to MAXIMUM_DATA_FILES_I.
        """
        # LLFR-00891: up to 10 files.
        return len(self.file_list)

    @property
    def is_full_b(self) -> bool:
        """Tell whether no other data file can be opened.

        Inputs: none.
        Outputs: True while 10 data files are open (LLFR-00892).
        """
        # LLFR-00891, LLFR-00892, LLFR-00950: the limit of 10 files.
        return len(self.file_list) >= MAXIMUM_DATA_FILES_I

    @property
    def next_number_i(self) -> int:
        """Return the number the next data file opened will get.

        Inputs: none.
        Outputs: 1 more than the highest number given since the start.
        """
        # LLFR-00896, LLFR-00898, LLFR-00900: never a used-up number.
        return self.highest_number_i + 1

    def add(self, signal_file, path_str: str = None) -> DataFile:
        """Open a file as the next data file.

        Inputs:
            signal_file: the SignalFile read and checked, with its time
                signal set.
            path_str: the path the file was selected with; None takes
                the path of signal_file.
        Outputs: the new DataFile. Raises ValueError while 10 data files
            are open, and KeyError when the file has no time signal.
        """
        # LLFR-00891: never more than 10 files.
        if self.is_full_b:
            raise ValueError("10 data files are already open")
        # LLFR-00896, LLFR-00916: the next number; LLFR-00899: it is
        # used up only now, when the file is really opened.
        data_file = DataFile(self.next_number_i, signal_file, path_str)
        self.highest_number_i = data_file.number_i
        # LLFR-00917, LLFR-00934: the files already open are kept, and
        # the new one comes last, since its number is the highest.
        self.file_list.append(data_file)
        return data_file

    def find(self, number_i: int):
        """Return the open data file that has a number.

        Inputs:
            number_i: a file number.
        Outputs: the DataFile, or None when no open file has it.
        """
        # LLFR-00897: the number of an open file does not change.
        for data_file in self.file_list:
            if data_file.number_i == number_i:
                return data_file
        return None

    def remove(self, number_i: int):
        """Close the data file that has a number.

        Inputs:
            number_i: the number of an open data file.
        Outputs: the closed DataFile, or None when no open file has the
            number. The number stays used up (LLFR-00898).
        """
        # LLFR-00922, LLFR-00927: only that file goes; the others keep
        # their numbers.
        data_file = self.find(number_i)
        if data_file is not None:
            self.file_list.remove(data_file)
        return data_file

    def remove_all(self) -> list:
        """Close every open data file.

        Inputs: none.
        Outputs: the closed DataFile objects, in number order. The
            numbering goes on after the highest number (LLFR-00900).
        """
        # LLFR-00932: every file; LLFR-00900: the numbers stay used up.
        closed_file_list = list(self.file_list)
        self.file_list = []
        return closed_file_list

    def open_number(self, path_str: str):
        """Return the number of the open data file of a path.

        Inputs:
            path_str: the path of a selected file.
        Outputs: the number of the open data file that is the same file
            on disk (LLFR-00894), or None when it is not open.
        """
        # LLFR-00894: the same file on disk, also through a link.
        for data_file in self.file_list:
            if same_file_b(path_str, data_file.path_str):
                return data_file.number_i
        return None

    @property
    def path_list(self) -> list:
        """Return the paths of the open data files.

        Inputs: none.
        Outputs: the paths, in number order.
        """
        # LLFR-00397: no open data file is ever written.
        return [data_file.path_str for data_file in self.file_list]

    @property
    def path_str(self) -> str:
        """Return the path of the open data file with the lowest number.

        Inputs: none.
        Outputs: the path, or "" while no file is open.
        """
        # LLFR-00532: the Save signals dialog starts from that file.
        if not self.file_list:
            return ""
        return self.file_list[0].path_str

    @property
    def description_str(self) -> str:
        """Return the description of the open data files.

        Inputs: none.
        Outputs: ``file<N> = <file name>`` for each open data file, in
            the order of the numbers, separated by commas, for example
            "file1 = run_A.csv, file2 = run_B.mat"; "" while no file is
            open.
        """
        # LLFR-00967, LLFR-00968: every open data file, with its file
        # name, its extension and no folder.
        return FILE_DESCRIPTION_SEPARATOR_STR.join(
            FILE_DESCRIPTION_FORMAT_STR.format(
                number=data_file.number_i, name=data_file.file_name_str)
            for data_file in self.file_list)

    # Signals ------------------------------------------------------

    def file_of_signal(self, signal_name_str: str):
        """Return the data file a signal belongs to.

        Inputs:
            signal_name_str: a prefixed signal name.
        Outputs: the DataFile, or None for a name of no open file.
        """
        # LLFR-00908: each signal belongs to one data file.
        for data_file in self.file_list:
            if signal_name_str in data_file.signal_dict:
                return data_file
        return None

    @property
    def signal_dict(self) -> dict:
        """Return the signals of every open data file.

        Inputs: none.
        Outputs: prefixed name -> samples, file after file in number
            order, each in the file's order (LLFR-00934, LLFR-00935).
        """
        # LLFR-00903: the prefixed names are unique across the files.
        combined_dict = {}
        for data_file in self.file_list:
            combined_dict.update(data_file.signal_dict)
        return combined_dict

    @property
    def signal_name_list(self) -> list:
        """Return the prefixed names of every open data file.

        Inputs: none.
        Outputs: the names, file after file in number order.
        """
        # LLFR-00934, LLFR-00935, LLFR-00054: every signal, Time too.
        return [name_str for data_file in self.file_list
                for name_str in data_file.signal_dict]

    @property
    def time_signal_name_list(self) -> list:
        """Return the prefixed names of the time signals.

        Inputs: none.
        Outputs: one name per open data file, in number order.
        """
        # LLFR-00332: the time signal of each open data file.
        return [data_file.time_signal_name_str
                for data_file in self.file_list]

    def signal_array(self, signal_name_str: str):
        """Return the samples of a signal of an open data file.

        Inputs:
            signal_name_str: a prefixed signal name.
        Outputs: its numpy array. Raises KeyError for an unknown name.
        """
        # LLFR-00055: any signal of any open file can be plotted.
        data_file = self.file_of_signal(signal_name_str)
        if data_file is None:
            raise KeyError(signal_name_str)
        return data_file.signal_dict[signal_name_str]

    def time_array_for_signal(self, signal_name_str: str):
        """Return the time signal a signal is drawn against.

        Inputs:
            signal_name_str: a prefixed signal name.
        Outputs: the time signal of the signal's own data file
            (LLFR-00908). Raises KeyError for an unknown name.
        """
        # LLFR-00908, LLFR-00910, LLFR-00911: the times of its own file.
        data_file = self.file_of_signal(signal_name_str)
        if data_file is None:
            raise KeyError(signal_name_str)
        return data_file.time_array

    def time_range_tuple(self) -> tuple:
        """Return the time range of the open data files.

        Inputs: none.
        Outputs: (earliest first time, latest last time) of all the open
            data files, in seconds, or () while no file is open.
        """
        # LLFR-00912, LLFR-00909: the times as stored, with the same
        # origin for every file.
        range_list = [data_file.time_range_tuple()
                      for data_file in self.file_list]
        range_list = [range_tuple for range_tuple in range_list
                      if range_tuple]
        if not range_list:
            return ()
        return (min(range_tuple[0] for range_tuple in range_list),
                max(range_tuple[1] for range_tuple in range_list))

    def same_time_signals_b(self) -> bool:
        """Tell whether every open data file has the same time signal.

        Inputs: none.
        Outputs: True when the time signals of all the open data files
            have the same number of samples and exactly the same value
            at every sample; always True with one file or none.
        """
        # LLFR-00938: the same number of samples and the same values.
        if len(self.file_list) < 2:
            return True
        first_array = np.asarray(self.file_list[0].time_array)
        return all(np.array_equal(first_array,
                                  np.asarray(data_file.time_array))
                   for data_file in self.file_list[1:])

    # The lowest-numbered file, for the Save signals flow ------------

    @property
    def time_signal_name_str(self):
        """Return the time signal of the lowest-numbered data file.

        Inputs: none.
        Outputs: its prefixed name, or None while no file is open.
        """
        # LLFR-00940: the saved file holds that file's time signal.
        if not self.file_list:
            return None
        return self.file_list[0].time_signal_name_str

    @property
    def time_array(self):
        """Return the time signal of the lowest-numbered data file.

        Inputs: none.
        Outputs: its numpy array. Raises KeyError while no file is open.
        """
        # LLFR-00940: the one time signal of a saved file.
        if not self.file_list:
            raise KeyError("no time signal")
        return self.file_list[0].time_array
