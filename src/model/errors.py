"""Errors of the model.

- FileOpenError and its subclasses: a time-series file cannot be opened.
  ``str(error)`` is the full message that the File Open Error box shows
  to the user (HLFR-00002).
- SyntheticSignalError and its subclasses: a synthetic signal
  (HLFR-00053) cannot be created or renamed. ``str(error)`` is a full
  sentence that the information box, the parameter dialog or the layout
  load report can show to the user as it is.
"""

# LLFR-00012: names of the content checks of HLFR-00008 and HLFR-00009.
TIME_SIGNAL_CHECK_STR = "time signal"
OTHER_SIGNAL_CHECK_STR = "other signal"
SAMPLE_COUNT_CHECK_STR = "sample count"


class FileOpenError(Exception):
    """Base class of the errors that stop a file from being opened.

    Inputs:
        message_str: the full message for the File Open Error box.
    Outputs: an exception whose ``str()`` is message_str.
    """


class FileAccessError(FileOpenError):
    """The file does not exist, is a folder or can't be read (LLFR-00009).

    Inputs:
        message_str: message that says the file could not be accessed.
    Outputs: the exception.
    """


class FileReadError(FileOpenError):
    """The file can't be read or parsed.

    Raised for corrupt files (LLFR-00008), MATLAB v7.3 files
    (LLFR-00064) and missing or non-numeric values (LLFR-00065).

    Inputs:
        message_str: message that says the file could not be read.
    Outputs: the exception.
    """


class UnsupportedFormatError(FileOpenError):
    """The file format is not one of HLFR-00005 (LLFR-00011).

    Inputs:
        message_str: message that says the format is not supported.
    Outputs: the exception.
    """


class ContentCheckError(FileOpenError):
    """The file fails a check of HLFR-00008 or HLFR-00009 (LLFR-00012).

    Inputs:
        message_str: message that says the file cannot be opened and
            which check failed.
        failed_check_str: one of TIME_SIGNAL_CHECK_STR,
            OTHER_SIGNAL_CHECK_STR or SAMPLE_COUNT_CHECK_STR.
    Outputs: the exception, with the attribute failed_check_str.
    """

    def __init__(self, message_str: str, failed_check_str: str) -> None:
        """Store the message and the name of the failed check.

        Inputs:
            message_str: the full message for the File Open Error box.
            failed_check_str: the name of the check that failed.
        Outputs: none.
        """
        # LLFR-00012: the error tells which check failed.
        super().__init__(message_str)
        self.failed_check_str = failed_check_str


class SyntheticSignalError(Exception):
    """Base class of the errors of synthetic signals (HLFR-00053).

    Inputs:
        message_str: a full sentence that tells the user why.
    Outputs: an exception whose ``str()`` is message_str.
    """


class SyntheticOperationError(SyntheticSignalError):
    """The operation cannot be done on the signal (LLFR-00262).

    Raised, for example, when the signal has too few samples for a
    derivative or a filter.

    Inputs:
        message_str: sentence that says why the operation cannot be done.
    Outputs: the exception.
    """


class UnevenTimeStepError(SyntheticOperationError):
    """The time samples are not evenly spaced (LLFR-00247).

    Inputs:
        message_str: sentence that says that the operation needs evenly
            spaced time samples.
    Outputs: the exception.
    """


class TooFewSamplesError(SyntheticOperationError):
    """The FFT time range holds fewer than 8 samples (LLFR-00250).

    Inputs:
        message_str: sentence that says that the time range holds too
            few samples.
    Outputs: the exception.
    """


class SyntheticParameterError(SyntheticSignalError):
    """The parameter of the operation is not allowed.

    Raised for a cutoff frequency out of range (LLFR-00245), a window
    size out of range (LLFR-00269), a constant that is not a number or
    0 for a division (LLFR-00272), or a time range that is not two
    numbers (LLFR-00248).

    Inputs:
        message_str: sentence that says why, and the allowed range.
    Outputs: the exception.
    """


class SyntheticSourceError(SyntheticSignalError):
    """A signal the synthetic signal is computed from can't be used.

    Raised when the signal is missing (LLFR-00262) or is an FFT signal
    (LLFR-00251, LLFR-00275).

    Inputs:
        message_str: sentence that names the signal and says why.
    Outputs: the exception.
    """


class SyntheticNameError(SyntheticSignalError):
    """A name can't be given to a synthetic signal (LLFR-00267).

    Inputs:
        message_str: sentence that says why.
    Outputs: the exception.
    """


class EmptySyntheticNameError(SyntheticNameError):
    """The new name is empty or made only of spaces (LLFR-00267).

    The app keeps the previous name and shows no message.

    Inputs:
        message_str: sentence that says that the name is empty.
    Outputs: the exception.
    """


class SyntheticNameInUseError(SyntheticNameError):
    """The name is already the name of another signal (LLFR-00267).

    Also raised when a layout file entry has the name of a signal of the
    data file (LLFR-00262).

    Inputs:
        message_str: sentence that says that a signal with that name
            already exists.
    Outputs: the exception.
    """


class SyntheticEntryError(SyntheticSignalError):
    """A layout file entry of a synthetic signal is malformed (LLFR-00262).

    Raised when a key is missing or a value has the wrong type.

    Inputs:
        message_str: sentence that says which key is wrong.
    Outputs: the exception.
    """
