"""Errors raised when a time-series file cannot be opened.

Every error is a FileOpenError, and ``str(error)`` is the full message
that the File Open Error box shows to the user (HLFR-00002).
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
