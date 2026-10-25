"""Exception hook that keeps the app running after an unexpected error.

PyQt6 aborts the whole application when a Python exception escapes a
Qt slot, unless ``sys.excepthook`` has been replaced. This module
installs a hook that prints the traceback to stderr and shows the
Unexpected Error box instead (HLFR-00002, PCR-00025).
"""

import sys
import traceback

from view import message_boxes


def format_error_message(error_type, error) -> str:
    """Return the one-line description of an error shown to the user.

    Inputs:
        error_type: the exception class.
        error: the exception object.
    Outputs: "<class name>: <message>", or only the class name when the
        message is empty.
    """
    # LLFR-00071: the box describes the error.
    type_name_str = getattr(error_type, "__name__", str(error_type))
    message_str = str(error)
    if not message_str:
        return type_name_str
    return f"{type_name_str}: {message_str}"


def make_error_hook(parent, show_function=None, error_stream=None):
    """Build an exception hook that reports errors instead of aborting.

    Inputs:
        parent: parent widget of the error box (the main window).
        show_function: function taking (parent, message_str) that shows
            the box; message_boxes.show_unexpected_error by default.
        error_stream: stream the traceback is written to; sys.stderr
            (looked up at call time) by default.
    Outputs: a function with the signature of sys.excepthook.
    """
    if show_function is None:
        show_function = message_boxes.show_unexpected_error

    def error_hook(error_type, error, error_traceback) -> None:
        """Print the traceback and show the Unexpected Error box.

        Inputs:
            error_type: the exception class.
            error: the exception object.
            error_traceback: the traceback object.
        Outputs: none. It never raises.
        """
        # LLFR-00071: keep a full report for the developer.
        stream = error_stream if error_stream is not None else sys.stderr
        try:
            traceback.print_exception(error_type, error, error_traceback,
                                      file=stream)
        except Exception:
            pass
        # LLFR-00071: tell the user, and keep running.
        try:
            show_function(parent, format_error_message(error_type, error))
        except Exception:
            pass

    return error_hook


def install_error_hook(main_window) -> None:
    """Replace sys.excepthook with the hook of make_error_hook.

    Inputs:
        main_window: the MainWindow, parent of the error box.
    Outputs: none.
    """
    # LLFR-00071: unexpected errors show a box instead of aborting.
    sys.excepthook = make_error_hook(main_window)
