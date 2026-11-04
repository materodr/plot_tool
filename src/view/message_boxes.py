"""Message boxes shown to the user.

- File Open Error box: error box shown when a file cannot be opened
  (HLFR-00002).
- Full Tab Notification box: information box shown when a tab already
  holds the maximum number of plots (LLFR-00032).
- Tab Name Taken box: information box shown when the user renames a
  tab to the name of another tab (LLFR-00211).
- Open Files Limit box: information box shown in place of the file
  selection dialog while 10 data files are open (LLFR-00896).
- Refused Files box: information box that lists the selected files that
  were not opened because they are already open or because 10 files are
  open (LLFR-00956).
- Unexpected Error box: error box shown when an unexpected error
  reaches the event loop, instead of letting the app abort
  (HLFR-00002, PCR-00025).
- Nothing to Export and Nothing to Copy boxes: information boxes shown
  when there is no plot to save or copy (LLFR-00145, LLFR-00146).
- Export Error and Copy Error boxes: error boxes shown when the PDF file
  could not be saved (LLFR-00131) or the image could not be copied.
- Delete Synthetic Signal box: question asked before a synthetic signal
  and the synthetic signals computed from it are deleted (LLFR-00255).
- Signal information box: information box of the synthetic signals,
  for example when the time samples are not evenly spaced (LLFR-00247),
  the FFT time range holds too few samples (LLFR-00250) or a new name
  is already used (LLFR-00267).
- Save Layout Error and Load Layout Error boxes: error boxes shown when
  a layout file could not be saved (LLFR-00224) or read (LLFR-00236).
- Layout Report box: information box that lists what a loaded layout
  could not rebuild as saved, in a scrollable text (LLFR-00237).
- Report a Bug Error box: error box shown when the web browser could not
  open the page of a new issue (LLFR-00361).

Each box is made by a ``build_*`` function, so tests can inspect it
without opening a modal dialog. The ``show_*`` and ``ask_*`` functions
build the box and run it.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox,
    QPlainTextEdit, QStyle, QVBoxLayout)

from model.workspace import MAXIMUM_MATRIX_SIZE_I

FILE_OPEN_ERROR_TITLE_STR = "File Open Error"
FULL_TAB_TITLE_STR = "Full Tab"
# LLFR-00032: a full tab whose plot matrix can still grow.
FULL_TAB_MESSAGE_STR = (
    "This tab is full: its {rows} \u00d7 {columns} plot matrix holds "
    "{slots} plots, so no new plot was created. Use a new tab, or choose "
    "a larger plot matrix for this tab with \"Plot matrix\" in the menu "
    "of the tab.")
# LLFR-01092: a full tab whose plot matrix is already 10 x 10.
FULL_LARGEST_MATRIX_MESSAGE_STR = (
    "This tab is full: its 10 \u00d7 10 plot matrix holds 100 plots, so "
    "no new plot was created. Use a new tab.")

# LLFR-00211: the information box of a rename to another tab's name.
TAB_NAME_TAKEN_TITLE_STR = "Rename Tab"
TAB_NAME_TAKEN_MESSAGE_STR = (
    "A tab named '{name}' already exists. The tab keeps its previous "
    "name. Type a different name.")
# LLFR-00257: the information box of a drop that mixes an FFT signal and
# a time signal in one plot.
PLOT_KIND_MISMATCH_TITLE_STR = "Frequency Plot"
PLOT_KIND_MISMATCH_MESSAGE_STR = (
    "FFT signals and time signals cannot be drawn in the same plot. "
    "Double-click the signal to draw it in a new plot.")
# LLFR-00896, LLFR-00956: the titles of the information boxes of the
# open-file flow.
OPEN_FILES_LIMIT_TITLE_STR = "Open file"
REFUSED_FILES_TITLE_STR = "Files not opened"
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
# LLFR-00224, LLFR-00236: the error boxes of the layout files.
SAVE_LAYOUT_ERROR_TITLE_STR = "Save Layout Error"
SAVE_LAYOUT_ERROR_INTRO_STR = "The layout file could not be saved."
LOAD_LAYOUT_ERROR_TITLE_STR = "Load Layout Error"
# LLFR-00237: the information box of the load report.
LAYOUT_REPORT_TITLE_STR = "Layout Loaded"
LAYOUT_REPORT_INTRO_STR = (
    "The layout was loaded, but some parts of it could not be rebuilt "
    "as saved:")
LAYOUT_REPORT_TEXT_OBJECT_NAME_STR = "layout_report_text"
LAYOUT_REPORT_MINIMUM_WIDTH_I = 560
LAYOUT_REPORT_MINIMUM_HEIGHT_I = 260
LAYOUT_REPORT_ICON_SIZE_I = 32
# LLFR-00397, LLFR-00399, LLFR-00400: the error box of Save signals.
SAVE_SIGNALS_ERROR_TITLE_STR = "Save Signals Error"
# LLFR-00404: the information box that lists the changed names.
CHANGED_NAMES_TITLE_STR = "Signals Saved"
CHANGED_NAMES_INTRO_STR = (
    "The signals were saved. Some names were changed so that the file "
    "format can store them and the time signal is named Time:")
CHANGED_NAMES_TEXT_OBJECT_NAME_STR = "changed_names_text"
# LLFR-00361: the error box shown when the browser cannot be opened.
REPORT_BUG_ERROR_TITLE_STR = "Report a Bug Error"
REPORT_BUG_ERROR_MESSAGE_STR = (
    "The page could not be opened in the web browser. To report a bug, "
    "open this address in a web browser:\n\n{url}")
# LLFR-00128: question asked before an existing .pdf file is replaced.
REPLACE_EXISTING_TITLE_STR = "Replace File"
REPLACE_EXISTING_MESSAGE_STR = (
    "The file '{path}' already exists. Do you want to replace it?")

# LLFR-00255: the question asked before a synthetic signal is deleted.
DELETE_SYNTHETIC_TITLE_STR = "Delete signal"
DELETE_SYNTHETIC_MESSAGE_STR = (
    "Do you want to delete the synthetic signal '{name}'?")
DELETE_DEPENDENTS_MESSAGE_STR = (
    "These synthetic signals are computed from it, directly or through "
    "other synthetic signals, and will be deleted too:")
DELETE_CONSEQUENCE_MESSAGE_STR = (
    "Their curves are removed from every plot, and the undo and redo "
    "history is cleared. This cannot be undone.")
DELETE_ONE_CONSEQUENCE_MESSAGE_STR = (
    "Its curves are removed from every plot, and the undo and redo "
    "history is cleared. This cannot be undone.")


# LLFR-00924, LLFR-00934: the titles of the questions of the file menu.
CLOSE_FILE_TITLE_STR = "Close file"
CLOSE_ALL_FILES_TITLE_STR = "Close all files"


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


def full_tab_message_str(row_count_i: int = 5,
                         column_count_i: int = 1) -> str:
    """Return the text of the Full Tab Notification box.

    Inputs:
        row_count_i: rows of the full tab's plot matrix.
        column_count_i: columns of the full tab's plot matrix.
    Outputs: FULL_TAB_MESSAGE_STR with the matrix filled in, or
        FULL_LARGEST_MATRIX_MESSAGE_STR for a 10 x 10 matrix.
    """
    # LLFR-01092: with a 10 x 10 matrix, only "use a new tab".
    if (row_count_i >= MAXIMUM_MATRIX_SIZE_I
            and column_count_i >= MAXIMUM_MATRIX_SIZE_I):
        return FULL_LARGEST_MATRIX_MESSAGE_STR
    # LLFR-00032: use a new tab or choose a larger plot matrix.
    return FULL_TAB_MESSAGE_STR.format(
        rows=int(row_count_i), columns=int(column_count_i),
        slots=int(row_count_i) * int(column_count_i))


def build_full_tab_box(parent, row_count_i: int = 5,
                       column_count_i: int = 1) -> QMessageBox:
    """Build the Full Tab Notification box.

    Inputs:
        parent: parent widget of the box, or None.
        row_count_i: rows of the full tab's plot matrix.
        column_count_i: columns of the full tab's plot matrix.
    Outputs: a QMessageBox with the information icon (it is not an error
        box), the title FULL_TAB_TITLE_STR, the text of
        full_tab_message_str and an OK button.
    """
    # LLFR-00032, LLFR-01092: information message telling the user to
    # use a new tab or, below 10 x 10, a larger plot matrix.
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(FULL_TAB_TITLE_STR)
    box.setText(full_tab_message_str(row_count_i, column_count_i))
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.setDefaultButton(QMessageBox.StandardButton.Ok)
    return box


def build_tab_name_taken_box(parent, name_str: str) -> QMessageBox:
    """Build the Tab Name Taken box.

    Inputs:
        parent: parent widget of the box, or None.
        name_str: the name the user typed, without surrounding spaces.
    Outputs: a QMessageBox with the information icon (it is not an error
        box), the title TAB_NAME_TAKEN_TITLE_STR, the text
        TAB_NAME_TAKEN_MESSAGE_STR with the name filled in and an OK
        button.
    """
    # LLFR-00211: information message saying that a tab with that name
    # already exists.
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(TAB_NAME_TAKEN_TITLE_STR)
    box.setText(TAB_NAME_TAKEN_MESSAGE_STR.format(name=name_str))
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.setDefaultButton(QMessageBox.StandardButton.Ok)
    return box


def build_plot_kind_mismatch_box(parent) -> QMessageBox:
    """Build the box of a drop that mixes FFT and time signals.

    Inputs:
        parent: parent widget of the box, or None.
    Outputs: a QMessageBox with the information icon (it is not an error
        box), the title PLOT_KIND_MISMATCH_TITLE_STR, the text
        PLOT_KIND_MISMATCH_MESSAGE_STR and an OK button.
    """
    # LLFR-00257: information message saying that FFT signals and time
    # signals cannot be drawn in the same plot.
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(PLOT_KIND_MISMATCH_TITLE_STR)
    box.setText(PLOT_KIND_MISMATCH_MESSAGE_STR)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.setDefaultButton(QMessageBox.StandardButton.Ok)
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


def show_full_tab_notification(parent, row_count_i: int = 5,
                               column_count_i: int = 1) -> None:
    """Show the Full Tab Notification box and wait until it is closed.

    Inputs:
        parent: parent widget of the box, or None.
        row_count_i: rows of the full tab's plot matrix.
        column_count_i: columns of the full tab's plot matrix.
    Outputs: none.
    """
    # LLFR-00032, LLFR-01092: notify that the tab is full.
    build_full_tab_box(parent, row_count_i, column_count_i).exec()


def show_tab_name_taken_notification(parent, name_str: str) -> None:
    """Show the Tab Name Taken box and wait until it is closed.

    Inputs:
        parent: parent widget of the box, or None.
        name_str: the name the user typed, without surrounding spaces.
    Outputs: none.
    """
    # LLFR-00211: notify that another tab already has the name.
    build_tab_name_taken_box(parent, name_str).exec()


def show_plot_kind_mismatch_notification(parent) -> None:
    """Show the box of a drop that mixes FFT and time signals.

    Inputs:
        parent: parent widget of the box, or None.
    Outputs: none.
    """
    # LLFR-00257: the dropped signal was not drawn.
    build_plot_kind_mismatch_box(parent).exec()


def build_open_files_limit_box(parent, message_str: str) -> QMessageBox:
    """Build the box shown at the Open file click with 10 files open.

    Inputs:
        parent: parent widget of the box, or None.
        message_str: the sentence of the box (from the controller).
    Outputs: a QMessageBox with the information icon (not an error box)
        and an OK button.
    """
    # LLFR-00896: an information box in place of the dialog.
    return build_message_box(parent, QMessageBox.Icon.Information,
                             OPEN_FILES_LIMIT_TITLE_STR, message_str)


def build_refused_files_box(parent, message_str: str) -> QMessageBox:
    """Build the box that lists the selected files that were refused.

    Inputs:
        parent: parent widget of the box, or None.
        message_str: one line per refused file, with its reason.
    Outputs: a QMessageBox with the information icon (not an error box)
        and an OK button.
    """
    # LLFR-00956: one information box for the refused files.
    return build_message_box(parent, QMessageBox.Icon.Information,
                             REFUSED_FILES_TITLE_STR, message_str)


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


def build_report_bug_error_box(parent, url_str: str) -> QMessageBox:
    """Build the error box shown when the page could not be opened.

    Inputs:
        parent: parent widget of the box, or None.
        url_str: the address of the page that could not be opened.
    Outputs: a QMessageBox with the critical icon, the title
        REPORT_BUG_ERROR_TITLE_STR and a text saying that the page could
        not be opened, followed by its address, which the user can
        select and copy.
    """
    # LLFR-00361: an error box (HLFR-00002) with the page's address.
    box = build_message_box(parent, QMessageBox.Icon.Critical,
                            REPORT_BUG_ERROR_TITLE_STR,
                            REPORT_BUG_ERROR_MESSAGE_STR.format(url=url_str))
    box.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse)
    return box


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


def delete_synthetic_signal_text(name_str: str,
                                 dependent_name_list: list) -> str:
    """Return the question asked before a synthetic signal is deleted.

    Inputs:
        name_str: the name of the synthetic signal.
        dependent_name_list: the synthetic signals computed from it,
            directly or indirectly, in creation order.
    Outputs: the text of the box, which names every dependent.
    """
    # LLFR-00255: the question names the signals deleted with it.
    text_str = DELETE_SYNTHETIC_MESSAGE_STR.format(name=name_str)
    if not dependent_name_list:
        return f"{text_str}\n\n{DELETE_ONE_CONSEQUENCE_MESSAGE_STR}"
    dependent_text_str = "\n".join(
        f"  - {dependent_name_str}"
        for dependent_name_str in dependent_name_list)
    return (f"{text_str}\n\n{DELETE_DEPENDENTS_MESSAGE_STR}\n"
            f"{dependent_text_str}\n\n{DELETE_CONSEQUENCE_MESSAGE_STR}")


def build_delete_synthetic_signal_box(parent, name_str: str,
                                      dependent_name_list: list
                                      ) -> QMessageBox:
    """Build the question asked before a synthetic signal is deleted.

    Inputs:
        parent: parent widget of the box, or None.
        name_str: the name of the synthetic signal.
        dependent_name_list: the synthetic signals computed from it.
    Outputs: a QMessageBox with the question icon, the title
        DELETE_SYNTHETIC_TITLE_STR, a text naming the signal and its
        dependents, and the buttons Yes and No, where No is the default
        and escape button.
    """
    # LLFR-00255: the user decides whether to proceed.
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(DELETE_SYNTHETIC_TITLE_STR)
    box.setText(delete_synthetic_signal_text(name_str, dependent_name_list))
    box.setStandardButtons(QMessageBox.StandardButton.Yes
                           | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    box.setEscapeButton(QMessageBox.StandardButton.No)
    return box


def ask_delete_synthetic_signal(parent, name_str: str,
                                dependent_name_list: list) -> bool:
    """Ask whether to delete a synthetic signal and its dependents.

    Inputs:
        parent: parent widget of the box, or None.
        name_str: the name of the synthetic signal.
        dependent_name_list: the synthetic signals computed from it.
    Outputs: True when the user chose Yes.
    """
    # LLFR-00255: only Yes deletes.
    result = build_delete_synthetic_signal_box(
        parent, name_str, dependent_name_list).exec()
    if isinstance(result, QMessageBox.StandardButton):
        result_value_i = int(result.value)
    else:
        result_value_i = int(result)
    return result_value_i == QMessageBox.StandardButton.Yes.value


def build_signal_information_box(parent, title_str: str,
                                 message_str: str) -> QMessageBox:
    """Build an information box of the synthetic signals.

    Inputs:
        parent: parent widget of the box, or None.
        title_str: the window title.
        message_str: the sentence that says why.
    Outputs: a QMessageBox with the information icon (not an error box)
        and an OK button.
    """
    # LLFR-00247, LLFR-00250, LLFR-00267: information, not errors.
    return build_message_box(parent, QMessageBox.Icon.Information,
                             title_str, message_str)


def build_layout_save_error_box(parent, reason_str: str) -> QMessageBox:
    """Build the error box shown when a layout file could not be saved.

    Inputs:
        parent: parent widget of the box, or None.
        reason_str: why the file could not be written, or "".
    Outputs: a QMessageBox with the critical icon, the title
        SAVE_LAYOUT_ERROR_TITLE_STR and a text that starts with
        SAVE_LAYOUT_ERROR_INTRO_STR and ends with the reason.
    """
    # LLFR-00224: an error box saying that the layout file could not be
    # saved (HLFR-00002).
    return build_message_box(parent, QMessageBox.Icon.Critical,
                             SAVE_LAYOUT_ERROR_TITLE_STR,
                             join_reason(SAVE_LAYOUT_ERROR_INTRO_STR,
                                         reason_str))


def build_layout_load_error_box(parent, message_str: str) -> QMessageBox:
    """Build the error box shown when a file is not a readable layout.

    Inputs:
        parent: parent widget of the box, or None.
        message_str: the text from the layout controller, which says that
            the file could not be read as a layout file and why.
    Outputs: a QMessageBox with the critical icon and the title
        LOAD_LAYOUT_ERROR_TITLE_STR.
    """
    # LLFR-00236: an error box saying that the file could not be read as
    # a layout file (HLFR-00002).
    return build_message_box(parent, QMessageBox.Icon.Critical,
                             LOAD_LAYOUT_ERROR_TITLE_STR, message_str)


def build_layout_report_box(
        parent, report_text_str: str,
        title_str: str = LAYOUT_REPORT_TITLE_STR,
        intro_str: str = LAYOUT_REPORT_INTRO_STR,
        text_object_name_str: str = LAYOUT_REPORT_TEXT_OBJECT_NAME_STR
) -> QDialog:
    """Build the information box of the layout load report.

    Inputs:
        parent: parent widget of the box, or None.
        report_text_str: the list of what was not rebuilt or changed, one
            entry per line.
        title_str: the window title.
        intro_str: the sentence above the list.
        text_object_name_str: the objectName of the text field.
    Outputs: a QDialog titled title_str with the information icon, the
        text intro_str, the report in a read-only, scrollable text field
        (objectName text_object_name_str) and an OK button.
    """
    # LLFR-00237, LLFR-00404: an information box, not an error box, like
    # the Full Tab Notification box; a long list can be scrolled.
    dialog = QDialog(parent)
    dialog.setWindowTitle(title_str)
    dialog.setMinimumSize(LAYOUT_REPORT_MINIMUM_WIDTH_I,
                          LAYOUT_REPORT_MINIMUM_HEIGHT_I)
    dialog_layout = QVBoxLayout(dialog)
    intro_layout = QHBoxLayout()
    icon_label = QLabel(dialog)
    icon_label.setPixmap(dialog.style().standardIcon(
        QStyle.StandardPixmap.SP_MessageBoxInformation).pixmap(
            LAYOUT_REPORT_ICON_SIZE_I, LAYOUT_REPORT_ICON_SIZE_I))
    intro_label = QLabel(intro_str, dialog)
    intro_label.setWordWrap(True)
    intro_layout.addWidget(icon_label)
    intro_layout.addWidget(intro_label, 1)
    dialog_layout.addLayout(intro_layout)
    report_field = QPlainTextEdit(dialog)
    report_field.setObjectName(text_object_name_str)
    report_field.setReadOnly(True)
    report_field.setPlainText(report_text_str)
    dialog_layout.addWidget(report_field, 1)
    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok,
                                  dialog)
    button_box.accepted.connect(dialog.accept)
    dialog_layout.addWidget(button_box)
    return dialog


def build_signals_save_error_box(parent, message_str: str) -> QMessageBox:
    """Build the error box of the Save signals button.

    Inputs:
        parent: parent widget of the box, or None.
        message_str: the text from the save signals controller, which
            says that the signals could not be saved or that the opened
            data file cannot be replaced, and why.
    Outputs: a QMessageBox with the critical icon and the title
        SAVE_SIGNALS_ERROR_TITLE_STR.
    """
    # LLFR-00397, LLFR-00399, LLFR-00400: an error box (HLFR-00002).
    return build_message_box(parent, QMessageBox.Icon.Critical,
                             SAVE_SIGNALS_ERROR_TITLE_STR, message_str)


def build_changed_names_box(parent, changed_names_text_str: str) -> QDialog:
    """Build the information box that lists the changed signal names.

    Inputs:
        parent: parent widget of the box, or None.
        changed_names_text_str: one "<old name> → <new name>" per line.
    Outputs: a QDialog titled CHANGED_NAMES_TITLE_STR with the
        information icon, the text CHANGED_NAMES_INTRO_STR, the list in a
        read-only, scrollable text field (objectName
        CHANGED_NAMES_TEXT_OBJECT_NAME_STR) and an OK button.
    """
    # LLFR-00404: an information box, scrollable like the layout load
    # report (LLFR-00237).
    return build_layout_report_box(
        parent, changed_names_text_str, CHANGED_NAMES_TITLE_STR,
        CHANGED_NAMES_INTRO_STR, CHANGED_NAMES_TEXT_OBJECT_NAME_STR)


def build_question_box(parent, title_str: str,
                       question_str: str) -> QMessageBox:
    """Build a question box with the buttons Yes and No.

    Inputs:
        parent: parent widget of the box, or None.
        title_str: the window title.
        question_str: the question and what proceeding does.
    Outputs: a QMessageBox with the question icon and the buttons Yes
        and No, where No is the default and escape button.
    """
    # LLFR-00924, LLFR-00934: the user decides whether to proceed.
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title_str)
    box.setText(question_str)
    box.setStandardButtons(QMessageBox.StandardButton.Yes
                           | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    box.setEscapeButton(QMessageBox.StandardButton.No)
    return box


def build_close_file_box(parent, question_str: str) -> QMessageBox:
    """Build the question asked before one data file is closed.

    Inputs:
        parent: parent widget of the box, or None.
        question_str: the question of the file controller, which names
            the file as its file name row shows it.
    Outputs: the question box, titled CLOSE_FILE_TITLE_STR.
    """
    # LLFR-00924: Yes closes the file, No keeps everything (LLFR-00925).
    return build_question_box(parent, CLOSE_FILE_TITLE_STR, question_str)


def build_close_all_files_box(parent, question_str: str) -> QMessageBox:
    """Build the question asked once before every data file is closed.

    Inputs:
        parent: parent widget of the box, or None.
        question_str: the question of the file controller.
    Outputs: the question box, titled CLOSE_ALL_FILES_TITLE_STR.
    """
    # LLFR-00934: one question for all the files (LLFR-00935).
    return build_question_box(parent, CLOSE_ALL_FILES_TITLE_STR,
                              question_str)


def answered_yes(box) -> bool:
    """Run a question box modally and tell whether Yes was chosen.

    Inputs:
        box: a QMessageBox with the buttons Yes and No.
    Outputs: True when the user chose Yes.
    """
    # LLFR-00925, LLFR-00935: anything but Yes declines.
    result = box.exec()
    if isinstance(result, QMessageBox.StandardButton):
        result_value_i = int(result.value)
    else:
        result_value_i = int(result)
    return result_value_i == QMessageBox.StandardButton.Yes.value


def ask_close_file(parent, question_str: str) -> bool:
    """Ask whether to close one data file.

    Inputs:
        parent: parent widget of the box, or None.
        question_str: the question of the file controller.
    Outputs: True when the user chose Yes.
    """
    # LLFR-00924: only Yes closes the file.
    return answered_yes(build_close_file_box(parent, question_str))


def ask_close_all_files(parent, question_str: str) -> bool:
    """Ask once whether to close every data file.

    Inputs:
        parent: parent widget of the box, or None.
        question_str: the question of the file controller.
    Outputs: True when the user chose Yes.
    """
    # LLFR-00934: only Yes closes the files.
    return answered_yes(build_close_all_files_box(parent, question_str))
