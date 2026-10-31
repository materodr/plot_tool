"""The signals of an opened time-series file."""

# HLFR-00006, LLFR-00053: the time signal is the one named exactly "Time".
TIME_SIGNAL_NAME_STR = "Time"


class SignalFile:
    """An opened time-series file.

    Inputs:
        path_str: path of the file the signals were read from.
        signal_dict: signal name -> 1-D numpy float64 array, in the order
            the signals appear in the file. It must contain the time
            signal TIME_SIGNAL_NAME_STR.
    Outputs: the object, with the attributes path_str and signal_dict.
    """

    def __init__(self, path_str: str, signal_dict: dict) -> None:
        """Store the file path and its signals.

        Inputs:
            path_str: path of the file.
            signal_dict: signal name -> 1-D numpy float64 array.
        Outputs: none.
        """
        # LLFR-00059, LLFR-00062: one entry per signal read from the file.
        self.path_str = path_str
        self.signal_dict = signal_dict

    @property
    def signal_name_list(self) -> list:
        """Return the names of all signals, in file order.

        Inputs: none.
        Outputs: a list of names that includes the time signal.
        """
        # LLFR-00054: the list shown in the signal list includes "Time".
        return list(self.signal_dict)

    @property
    def time_array(self):
        """Return the values of the time signal.

        Inputs: none.
        Outputs: a numpy float64 array of time values in seconds.
        """
        # HLFR-00006, HLFR-00007, LLFR-00053: "Time" holds seconds.
        return self.signal_dict[TIME_SIGNAL_NAME_STR]

    def signal_array(self, signal_name_str: str):
        """Return the values of one signal.

        Inputs:
            signal_name_str: name of the signal, as in signal_name_list.
        Outputs: a numpy float64 array. Raises KeyError for an unknown
            name.
        """
        # LLFR-00055: any signal, including "Time", can be plotted.
        return self.signal_dict[signal_name_str]
