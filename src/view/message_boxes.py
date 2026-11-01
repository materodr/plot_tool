"""Message boxes shown to the user.

- File Open Error box: error box shown when a file cannot be opened
  (HLFR-00002).
- Full Tab Notification box: information box shown when a tab already
  holds the maximum number of plots (LLFR-00032).
- Replace File box: question asked before an open file is replaced
  (HLFR-00010).
- Unexpected Error box: error box shown when an unexpected error
  reaches the event loop, instead of letting the app abort
  (HLFR-00002, PCR-00025).
- Nothing to Export and Nothing to Copy boxes: information boxes shown
  when there is no plot to save or copy (LLFR-00145, LLFR-00146).
- Export Error and Copy Error boxes: error boxes shown when the PDF file
  could not be saved (LLFR-00131) or the image could not be copied.

Each box is made by a ``build_*`` function, so tests can inspect it
without opening a modal dialog. The ``show_*`` and ``ask_*`` functions
build the box and run it.
"""

from PyQt6.QtWidgets import QMessageBox

FILE_OPEN_ERROR_TITLE_STR = "File Open Error"
FULL_TAB_TITLE_STR = "Full Tab"
FULL_TAB_MESSAGE_STR = (
    "This tab already holds the maximum of 5 plots, so no new plot was "
    "created. Add a new tab or delete a plot from this tab."
)
REPLACE_FILE_TITLE_STR = "Replace File"
REPLACE_FILE_MESSAGE_STR = (
    "Another file is already open. Proceeding will close the current "
    "file and all its plots. Do you want to proceed?"
)
UNEXPECTED_ERROR_TITLE_STR = "Error"
UNEXPECTED_ERROR_INTRO_STR = (
    "An unexpected error occurred. The app keeps running, but the last "
    "action may not have finished.")
# LLFR-00145, LLFR-00146: the information boxes of the export.
EXPORT_TITLE_STR = "Export"
NOTHING_TO_EXPORT_MESSAGE_STR = "There are no plots to export."
COPY_TITLE_STR = "Copy"
NOTHING_TO_COPY_MESSAGE_STR = "There are no plots to copy."
# LLFR-00131: the error boxes of the export and of the copy.
EXPORT_ERROR_TITLE_STR = "Export Error"
EXPORT_ERROR_INTRO_STR = "The file could not be saved."
COPY_ERROR_TITLE_STR = "Copy Error"
COPY_ERROR_INTRO_STR = "The plots could not be copied to the clipboard."
# LLFR-00128: question asked before an existing .pdf file is replaced.
REPLACE_EXISTING_TITLE_STR = "Replace File"
REPLACE_EXISTING_MESSAGE_STR = (
    "The file '{path}' already exists. Do you want to replace it?")


def build_file_open_error_box(parent, message_str: str) -> QMessageBox:
    """Build the File Open Error box.

    Inputs:
        parent: parent widget of the box, or None.
        message_str: the description of the error shown to the user.
    Outputs: a QMessageBox with the critical icon, the title
        FILE_OPEN_ERROR_TITLE_STR, the given text and an OK button.
    """
    # LLFR-00008, LLFR-00009, LLFR-00011, LLFR-00012: the File Open
    # Error box is an error box that describes the error (HLFR-00002).
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(FILE_OPEN_ERROR_TITLE_STR)
    box.setText(message_str)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.setDefaultButton(QMessageBox.StandardButton.Ok)
    return box


def build_full_tab_box(parent) -> QMessageBox:
    """Build the Full Tab Notification box.

    Inputs:
        parent: parent widget of the box, or None.
    Outputs: a QMessageBox with the information icon (it is not an error
        box), the title FULL_TAB_TITLE_STR, the text FULL_TAB_MESSAGE_STR
        and an OK button.
    """
    # LLFR-00032: information message telling the user to add a new tab
    # or delete a plot.
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(FULL_TAB_TITLE_STR)
    box.setText(FULL_TAB_MESSAGE_STR)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.setDefaultButton(QMessageBox.StandardButton.Ok)
    return box


def build_replace_file_box(parent) -> QMessageBox:
    """Build the Replace File confirmation box.

    Inputs:
        parent: parent widget of the box, or None.
    Outputs: a QMessageBox with the question icon, the title
        REPLACE_FILE_TITLE_STR, the text REPLACE_FILE_MESSAGE_STR and the
        buttons Yes and No, where No is the default and escape button.
    """
    # LLFR-00013, LLFR-00014: ask whether to proceed, stating that
    # proceeding closes the current file (HLFR-00010).
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(REPLACE_FILE_TITLE_STR)
    box.setText(REPLACE_FILE_MESSAGE_STR)
    box.setStandardButtons(QMessageBox.StandardButton.Yes
                           | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    box.setEscapeButton(QMessageBox.StandardButton.No)
    return box


def show_file_open_error(parent, message_str: str) -> None:
    """Show the File Open Error box and wait until the user closes it.

    Inputs:
        parent: parent widget of the box, or None.
        message_str: the description of the error shown to the user.
    Outputs: none.
    """
    # LLFR-00008, LLFR-00009, LLFR-00011, LLFR-00012: notify the error.
    build_file_open_error_box(parent, message_str).exec()


def show_full_tab_notification(parent) -> None:
    """Show the Full Tab Notification box and wait until it is closed.

    Inputs:
        parent: parent widget of the box, or None.
    Outputs: none.
    """
    # LLFR-00032: notify that the tab is full.
    build_full_tab_box(parent).exec()


def ask_replace_file(parent) -> bool:
    """Ask the user whether to replace the open file.

    Inputs:
        parent: parent widget of the box, or None.
    Outputs: True when the user chose Yes, False otherwise (No, or the
        box closed without choosing).
    """
    # LLFR-00013: Yes means the user proceeds.
    # LLFR-00014: any other answer keeps the current file open.
    result = build_replace_file_box(parent).exec()
    # exec() returns an int in PyQt6; accept a StandardButton as well.
    if isinstance(result, QMessageBox.StandardButton):
        result_value_i = int(result.value)
    else:
        result_value_i = int(result)
    return result_value_i == QMessageBox.StandardButton.Yes.value


def build_unexpected_error_box(parent, message_str: str) -> QMessageBox:
    """Build the box shown for an unexpected error.

    Inputs:
        parent: parent widget of the box, or None.
        message_str: the description of the error.
    Outputs: a QMessageBox with the critical icon, the title
        UNEXPECTED_ERROR_TITLE_STR, a text that starts with
        UNEXPECTED_ERROR_INTRO_STR and ends with message_str, and an OK
        button.
    """
    # LLFR-00071: an error box titled "Error" that describes the error
    # (HLFR-00002).
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(UNEXPECTED_ERROR_TITLE_STR)
    box.setText(f"{UNEXPECTED_ERROR_INTRO_STR}\n\n{message_str}")
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.setDefaultButton(QMessageBox.StandardButton.Ok)
    return box


def show_unexpected_error(parent, message_str: str) -> None:
    """Show the unexpected error box and wait until it is closed.

    Inputs:
        parent: parent widget of the box, or None.
        message_str: the description of the error.
    Outputs: none.
    """
    # LLFR-00071: notify the error instead of aborting (HLFR-00002).
    build_unexpected_error_box(parent, message_str).exec()


def build_message_box(parent, icon, title_str: str,
                      message_str: str) -> QMessageBox:
    """Build a box with one OK button.

    Inputs:
        parent: parent widget of the box, or None.
        icon: the QMessageBox.Icon of the box.
        title_str: the window title.
        message_str: the text of the box.
    Outputs: the QMessageBox, not shown.
    """
    # LLFR-00131, LLFR-00145, LLFR-00146: the boxes of the export.
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title_str)
    box.setText(message_str)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.setDefaultButton(QMessageBox.StandardButton.Ok)
    return box


def join_reason(intro_str: str, reason_str: str) -> str:
    """Return an error text followed by its reason, when there is one.

    Inputs:
        intro_str: the first sentence of the error text.
        reason_str: why the action failed, or "".
    Outputs: the text shown in the error box.
    """
    # LLFR-00131: the box says that the file could not be saved and why.
    if reason_str:
        return f"{intro_str}\n\n{reason_str}"
    return intro_str


def build_nothing_to_export_box(parent) -> QMessageBox:
    """Build the information box shown when no tab holds a plot.

    Inputs:
        parent: parent widget of the box, or None.
    Outputs: a QMessageBox with the information icon, the title
        EXPORT_TITLE_STR and the text NOTHING_TO_EXPORT_MESSAGE_STR.
    """
    # LLFR-00145: an information box, not an error box.
    return build_message_box(parent, QMessageBox.Icon.Information,
                             EXPORT_TITLE_STR,
                             NOTHING_TO_EXPORT_MESSAGE_STR)


def build_nothing_to_copy_box(parent) -> QMessageBox:
    """Build the information box shown when the current tab has no plot.

    Inputs:
        parent: parent widget of the box, or None.
    Outputs: a QMessageBox with the information icon, the title
        COPY_TITLE_STR and the text NOTHING_TO_COPY_MESSAGE_STR.
    """
    # LLFR-00146: an information box, not an error box.
    return build_message_box(parent, QMessageBox.Icon.Information,
                             COPY_TITLE_STR, NOTHING_TO_COPY_MESSAGE_STR)


def build_export_error_box(parent, reason_str: str) -> QMessageBox:
    """Build the error box shown when the PDF file could not be saved.

    Inputs:
        parent: parent widget of the box, or None.
        reason_str: why the file could not be written, or "".
    Outputs: a QMessageBox with the critical icon, the title
        EXPORT_ERROR_TITLE_STR and a text that starts with
        EXPORT_ERROR_INTRO_STR and ends with the reason.
    """
    # LLFR-00131: an error box saying the file could not be saved
    # (HLFR-00002).
    return build_message_box(parent, QMessageBox.Icon.Critical,
                             EXPORT_ERROR_TITLE_STR,
                             join_reason(EXPORT_ERROR_INTRO_STR,
                                         reason_str))


def build_copy_error_box(parent, reason_str: str) -> QMessageBox:
    """Build the error box shown when the image could not be copied.

    Inputs:
        parent: parent widget of the box, or None.
        reason_str: why the copy failed, or "".
    Outputs: a QMessageBox with the critical icon, the title
        COPY_ERROR_TITLE_STR and a text that starts with
        COPY_ERROR_INTRO_STR.
    """
    # LLFR-00133: a failed copy is notified with an error box
    # (HLFR-00002).
    return build_message_box(parent, QMessageBox.Icon.Critical,
                             COPY_ERROR_TITLE_STR,
                             join_reason(COPY_ERROR_INTRO_STR, reason_str))


def build_replace_existing_file_box(parent, path_str: str) -> QMessageBox:
    """Build the question asked before an existing file is replaced.

    Inputs:
        parent: parent widget of the box, or None.
        path_str: the path of the existing file.
    Outputs: a QMessageBox with the question icon, the title
        REPLACE_EXISTING_TITLE_STR, a text naming the file and the
        buttons Yes and No, where No is the default and escape button.
    """
    # LLFR-00128: the user decides whether the existing file is lost.
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(REPLACE_EXISTING_TITLE_STR)
    box.setText(REPLACE_EXISTING_MESSAGE_STR.format(path=path_str))
    box.setStandardButtons(QMessageBox.StandardButton.Yes
                           | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    box.setEscapeButton(QMessageBox.StandardButton.No)
    return box


def ask_replace_existing_file(parent, path_str: str) -> bool:
    """Ask whether to replace an existing file.

    Inputs:
        parent: parent widget of the box, or None.
        path_str: the path of the existing file.
    Outputs: True when the user chose Yes.
    """
    # LLFR-00128: only Yes replaces the file.
    result = build_replace_existing_file_box(parent, path_str).exec()
    if isinstance(result, QMessageBox.StandardButton):
        result_value_i = int(result.value)
    else:
        result_value_i = int(result)
    return result_value_i == QMessageBox.StandardButton.Yes.value
