"""The signals of an opened time-series file.

The time signal is a property of each file (HLFR-00006): the signal
whose name is ``Time`` in any letter case (LLFR-00053, LLFR-00324), or,
when no signal has that name, the signal the user chooses in the time
signal window (HLFR-00070, LLFR-00325, LLFR-00326). Once set, it can't
be changed (HLFR-00072, LLFR-00331).
"""

import numpy as np

# HLFR-00006, LLFR-00053: the name that identifies the time signal,
# compared without regard to uppercase and lowercase letters.
TIME_SIGNAL_NAME_STR = "Time"
# LLFR-00329: the reason the time signal window gives for a signal whose
# samples do not always increase.
NOT_INCREASING_MESSAGE_STR = (
    "The signal on the x-axis must always increase: sample {sample} of "
    "'{name}' is not greater than the sample before it.")


def is_time_signal_name(signal_name_str: str) -> bool:
    """Tell whether a signal name matches the time signal name.

    The whole name must be ``Time`` in any letter case. In HDF5 files a
    signal is named after its dataset path (LLFR-00134), so a dataset in
    a group, such as ``engine/time``, never matches (LLFR-00330).

    Inputs:
        signal_name_str: a signal name.
    Outputs: True when the name is "Time", "time", "TIME" and so on.
    """
    # LLFR-00053: ignore the difference between uppercase and lowercase.
    # LLFR-00330: the path of a dataset in a group has a "/" and so is
    # never equal to "time".
    return (str(signal_name_str).casefold()
            == TIME_SIGNAL_NAME_STR.casefold())


def matching_time_signal_name(signal_name_list: list):
    """Return the name of the signal found as the time signal.

    Inputs:
        signal_name_list: the signal names, in the file's order.
    Outputs: the name, or None when no signal matches (the user must
        then choose the time signal, LLFR-00325).
    """
    # LLFR-00053: every name that matches "Time" in any letter case.
    matching_name_list = [name_str for name_str in signal_name_list
                          if is_time_signal_name(name_str)]
    if not matching_name_list:
        return None
    # LLFR-00324: the name written exactly "Time" wins; otherwise the
    # first match in the file's order. The user is not asked.
    if TIME_SIGNAL_NAME_STR in matching_name_list:
        return TIME_SIGNAL_NAME_STR
    return matching_name_list[0]


def increasing_check_reason(signal_name_str: str, value_array) -> str:
    """Check that a signal can go on the x-axis.

    Inputs:
        signal_name_str: the signal name, for the message.
        value_array: the samples of the signal.
    Outputs: "" when every sample is greater than the sample before it;
        otherwise the reason shown in the time signal window.
    """
    # LLFR-00329: each sample must be greater than the one before it.
    sample_array = np.asarray(value_array, dtype=float)
    not_increasing_array = np.flatnonzero(
        ~(np.diff(sample_array) > 0.0))
    if not_increasing_array.size == 0:
        return ""
    # LLFR-00329: name the first sample (counted from 1) that does not
    # increase.
    return NOT_INCREASING_MESSAGE_STR.format(
        sample=int(not_increasing_array[0]) + 2, name=signal_name_str)


class SignalFile:
    """An opened time-series file.

    Inputs:
        path_str: path of the file the signals were read from.
        signal_dict: signal name -> 1-D numpy float64 array, in the order
            the signals appear in the file.
        time_signal_name_str: the time signal; None finds it by its name
            (matching_time_signal_name), and stays None when no signal
            matches, until choose_time_signal is called.
    Outputs: the object, with the attributes path_str, signal_dict and
        time_signal_name_str.
    """

    def __init__(self, path_str: str, signal_dict: dict,
                 time_signal_name_str: str = None) -> None:
        """Store the file path, its signals and its time signal.

        Inputs:
            path_str: path of the file.
            signal_dict: signal name -> 1-D numpy float64 array.
            time_signal_name_str: the time signal, or None to find it
                by its name.
        Outputs: none. Raises KeyError for a time signal name that is
            not a signal of the file.
        """
        # LLFR-00059, LLFR-00062: one entry per signal read from the file.
        self.path_str = path_str
        self.signal_dict = signal_dict
        # HLFR-00006, LLFR-00053, LLFR-00324: found by its name.
        if time_signal_name_str is None:
            time_signal_name_str = matching_time_signal_name(
                list(signal_dict))
        elif time_signal_name_str not in signal_dict:
            raise KeyError(time_signal_name_str)
        self.time_signal_name_str = time_signal_name_str

    @property
    def needs_time_signal_choice_b(self) -> bool:
        """Tell whether the user must choose the time signal.

        Inputs: none.
        Outputs: True when no signal matches the time signal name.
        """
        # HLFR-00070, LLFR-00325: the window is shown only then.
        return self.time_signal_name_str is None

    def choose_time_signal(self, signal_name_str: str) -> str:
        """Use the signal chosen by the user as the time signal.

        Inputs:
            signal_name_str: the name confirmed in the time signal
                window.
        Outputs: "" when the signal is now the time signal; otherwise
            the reason it can't be (LLFR-00329). Raises ValueError when
            the file already has a time signal (LLFR-00331) and KeyError
            for an unknown name.
        """
        # LLFR-00331: the time signal is never changed once set.
        if self.time_signal_name_str is not None:
            raise ValueError("the time signal is already set")
        # LLFR-00329: the chosen signal must always increase.
        reason_str = increasing_check_reason(
            signal_name_str, self.signal_dict[signal_name_str])
        if reason_str:
            return reason_str
        # LLFR-00326: the chosen signal is the time signal from now on.
        self.time_signal_name_str = signal_name_str
        return ""

    @property
    def signal_name_list(self) -> list:
        """Return the names of all signals, in file order.

        Inputs: none.
        Outputs: a list of names that includes the time signal.
        """
        # LLFR-00054, LLFR-00326: the list includes the time signal.
        return list(self.signal_dict)

    @property
    def time_array(self):
        """Return the values of the time signal.

        Inputs: none.
        Outputs: a numpy float64 array of time values in seconds.
            Raises KeyError while no time signal is set.
        """
        # HLFR-00006, HLFR-00007, LLFR-00326: the time signal, found by
        # its name or chosen by the user, holds seconds.
        if self.time_signal_name_str is None:
            raise KeyError("no time signal")
        return self.signal_dict[self.time_signal_name_str]

    def time_array_for_signal(self, signal_name_str: str):
        """Return the time signal a signal of this file is drawn against.

        Inputs:
            signal_name_str: name of a signal of the file.
        Outputs: the time signal of the file (LLFR-00908). Raises
            KeyError for an unknown name.
        """
        # LLFR-00908: every signal of a file uses the time of its file;
        # the same reading method as model.data_files.DataFileSet.
        if signal_name_str not in self.signal_dict:
            raise KeyError(signal_name_str)
        return self.time_array

    def time_range_tuple(self) -> tuple:
        """Return the time range of the file.

        Inputs: none.
        Outputs: (first time, last time) in seconds, or () when no
            sample is finite or no time signal is set.
        """
        # LLFR-00912: from the first to the last time sample.
        if self.time_signal_name_str is None:
            return ()
        sample_array = np.asarray(self.time_array, dtype=float)
        sample_array = sample_array[np.isfinite(sample_array)]
        if sample_array.size == 0:
            return ()
        return (float(np.min(sample_array)), float(np.max(sample_array)))

    @property
    def time_signal_name_list(self) -> list:
        """Return the names of the time signals, as DataFileSet does.

        Inputs: none.
        Outputs: [the time signal name], or [] when none is set.
        """
        # LLFR-00332: the time signal of the file.
        if self.time_signal_name_str is None:
            return []
        return [self.time_signal_name_str]

    @property
    def path_list(self) -> list:
        """Return the paths of the file, as DataFileSet does.

        Inputs: none.
        Outputs: [path_str].
        """
        # LLFR-00397: the path of the open data file.
        return [self.path_str]

    def signal_array(self, signal_name_str: str):
        """Return the values of one signal.

        Inputs:
            signal_name_str: name of the signal, as in signal_name_list.
        Outputs: a numpy float64 array. Raises KeyError for an unknown
            name.
        """
        # LLFR-00055: any signal, including the time signal, can be
        # plotted.
        return self.signal_dict[signal_name_str]
