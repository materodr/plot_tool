"""Write the signals of the signal list to a new data file (HLFR-00090).

``signal_file_bytes`` turns the signals into the bytes of a CSV, Excel
(.xlsx), MAT or HDF5 file, written so that ``model.file_loader`` reads
them back as the same signals with the same values (LLFR-00402).
``saved_name_list`` gives the names the chosen format can store
(LLFR-00403) with the time signal written as ``Time`` (LLFR-00407).
The bytes are written to the disk by the caller, safely, so a failed
save never damages a file already there (LLFR-00399). No Qt code is
used here (COR-00009).
"""

import csv
import io
import os
import re

import numpy as np

from model.file_loader import hdf5_library
from model.message_lists import list_body_text, list_text
from model.signal_file import TIME_SIGNAL_NAME_STR, is_time_signal_name

# LLFR-00396: the formats of the save dialog (HLFR-00005), each with its
# extensions; the first extension is the one the app adds.
CSV_FORMAT_STR = "csv"
EXCEL_FORMAT_STR = "xlsx"
MAT_FORMAT_STR = "mat"
HDF5_FORMAT_STR = "hdf5"
FORMAT_EXTENSION_DICT = {
    CSV_FORMAT_STR: (".csv",),
    EXCEL_FORMAT_STR: (".xlsx",),
    MAT_FORMAT_STR: (".mat",),
    HDF5_FORMAT_STR: (".h5", ".hdf5"),
}
FORMAT_ORDER_TUPLE = tuple(FORMAT_EXTENSION_DICT)
# LLFR-00396: the text after the data file name in the proposed name.
SIGNALS_NAME_SUFFIX_STR = "_signals"

# LLFR-00400: one Excel sheet holds 16384 columns and 1048576 rows; the
# first row holds the names.
EXCEL_MAXIMUM_SIGNALS_I = 16384
EXCEL_MAXIMUM_SAMPLES_I = 1048575
EXCEL_LIMIT_REASON_STR = (
    "The signals have too many samples or are too many for an Excel "
    "file: an Excel sheet holds at most {signals} signals of at most "
    "{samples} samples, but there are {signal_count} signals of "
    "{sample_count} samples.")

# LLFR-00403 item 1: a MAT variable name has only English letters,
# digits and "_", starts with a letter and has at most 63 characters.
MAT_INVALID_CHARACTER_PATTERN_STR = r"[^A-Za-z0-9_]"
MAT_NAME_PREFIX_STR = "x"
MAT_MAXIMUM_NAME_LENGTH_I = 63
# LLFR-00403 item 2: the name of an HDF5 dataset left with no part.
HDF5_EMPTY_NAME_STR = "signal"
HDF5_SEPARATOR_STR = "/"
HDF5_DROPPED_PART_TUPLE = ("", ".", "..")
# LLFR-00403 item 3: the name of a CSV or Excel column left empty.
TABLE_EMPTY_NAME_STR = "signal"
# LLFR-00408: the reason given for signals with values that are not
# finite numbers.
NON_FINITE_REASON_STR = (
    "These signals have values that are not finite numbers (infinite or "
    "NaN), which a data file cannot hold:")
# LLFR-00241, LLFR-00403: the first number added to a name in use.
FIRST_SUFFIX_NUMBER_I = 2
# LLFR-00399: the reason given when h5py is not installed.
NO_HDF5_LIBRARY_REASON_STR = (
    "HDF5 support is not installed (the h5py library is missing).")


class SignalWriteError(Exception):
    """The signals could not be turned into the bytes of a file.

    Inputs:
        reason_str: why, shown in the error box (LLFR-00399).
    Outputs: the exception; ``str(error)`` is the reason.
    """


def format_extension_tuple(format_str: str) -> tuple:
    """Return the extensions of a format.

    Inputs:
        format_str: one of FORMAT_ORDER_TUPLE.
    Outputs: a tuple of extensions with their dot, the one the app adds
        first. Raises KeyError for an unknown format.
    """
    # LLFR-00396: the extensions of HLFR-00005.
    return FORMAT_EXTENSION_DICT[format_str]


def format_of_path(path_str: str) -> str:
    """Return the format of a file from its extension.

    Inputs:
        path_str: a file path.
    Outputs: one of FORMAT_ORDER_TUPLE, or "" for another extension.
    """
    # LLFR-00396: the format of the opened data file is chosen first.
    extension_str = os.path.splitext(path_str)[1].lower()
    for format_str, extension_tuple in FORMAT_EXTENSION_DICT.items():
        if extension_str in extension_tuple:
            return format_str
    return ""


def proposed_file_name(data_path_str: str) -> str:
    """Return the name the save dialog proposes.

    Inputs:
        data_path_str: the path of the opened data file.
    Outputs: its name without the extension, then "_signals" and its
        extension, for example "run1_signals.csv" for "run1.csv".
    """
    # LLFR-00396: the data file name, "_signals" and its extension.
    stem_str, extension_str = os.path.splitext(
        os.path.basename(data_path_str))
    return f"{stem_str}{SIGNALS_NAME_SUFFIX_STR}{extension_str}"


def ensure_format_extension(path_str: str, format_str: str) -> str:
    """Add the extension of the chosen format when the name lacks one.

    Inputs:
        path_str: the path chosen in the save dialog.
        format_str: the format chosen in the dialog.
    Outputs: path_str when it ends with an extension of the format (in
        any letter case), else path_str with the format's first
        extension added (".csv", ".xlsx", ".mat" or ".h5").
    """
    # LLFR-00396: "run1" becomes "run1.csv"; "run1.txt" becomes
    # "run1.txt.csv" because ".txt" is not an extension of CSV.
    extension_tuple = format_extension_tuple(format_str)
    if path_str.lower().endswith(extension_tuple):
        return path_str
    return path_str + extension_tuple[0]


def excel_limit_reason(signal_count_i: int, sample_count_i: int) -> str:
    """Tell whether the signals fit in one Excel sheet.

    Inputs:
        signal_count_i: the number of signals to save.
        sample_count_i: the number of samples of each signal.
    Outputs: "" when they fit, else the reason for the error box.
    """
    # LLFR-00400: at most 16384 signals of at most 1048575 samples.
    if (signal_count_i <= EXCEL_MAXIMUM_SIGNALS_I
            and sample_count_i <= EXCEL_MAXIMUM_SAMPLES_I):
        return ""
    return EXCEL_LIMIT_REASON_STR.format(
        signals=EXCEL_MAXIMUM_SIGNALS_I, samples=EXCEL_MAXIMUM_SAMPLES_I,
        signal_count=signal_count_i, sample_count=sample_count_i)


# ----------------------------------------------------------------------
# Names (LLFR-00403, LLFR-00407)
# ----------------------------------------------------------------------

def mat_name(name_str: str) -> str:
    """Return a name a MAT file can store as a variable name.

    Inputs:
        name_str: a signal name.
    Outputs: the name with every character other than an English
        letter, a digit or "_" replaced by "_", "x" added when it does
        not start with a letter, cut to 63 characters.
    """
    # LLFR-00403 item 1: the three rules, in this order.
    valid_str = re.sub(MAT_INVALID_CHARACTER_PATTERN_STR, "_", name_str)
    if not re.match(r"[A-Za-z]", valid_str):
        valid_str = MAT_NAME_PREFIX_STR + valid_str
    return valid_str[:MAT_MAXIMUM_NAME_LENGTH_I]


def hdf5_name(name_str: str) -> str:
    """Return a name an HDF5 file can store as a dataset path.

    Inputs:
        name_str: a signal name; each "/" separates a group.
    Outputs: the name without empty parts, "." and ".." parts, or a "/"
        at its start or end; "signal" when no part is left.
    """
    # LLFR-00403 item 2: only the parts that name a group or a dataset.
    part_list = [part_str for part_str in name_str.split(HDF5_SEPARATOR_STR)
                 if part_str not in HDF5_DROPPED_PART_TUPLE]
    if not part_list:
        return HDF5_EMPTY_NAME_STR
    return HDF5_SEPARATOR_STR.join(part_list)


def table_name(name_str: str) -> str:
    """Return a name a CSV or Excel file reads back unchanged.

    Inputs:
        name_str: a signal name.
    Outputs: the name without blank characters at its start and end,
        which the loader removes (LLFR-00059); "signal" when nothing is
        left.
    """
    # LLFR-00403 item 3: " a " is read back as "a", so it is saved so.
    stripped_str = name_str.strip()
    return stripped_str or TABLE_EMPTY_NAME_STR


def format_name(name_str: str, format_str: str) -> str:
    """Return the name the format can store, before names are unique.

    Inputs:
        name_str: a signal name.
        format_str: one of FORMAT_ORDER_TUPLE.
    Outputs: the stored name (LLFR-00403 items 1 to 3).
    """
    # LLFR-00403: the rule of each format.
    if format_str == MAT_FORMAT_STR:
        return mat_name(name_str)
    if format_str == HDF5_FORMAT_STR:
        return hdf5_name(name_str)
    return table_name(name_str)


def numbered_name(base_name_str: str, number_i: int,
                  format_str: str) -> str:
    """Return a name with an underscore and a number added.

    Inputs:
        base_name_str: the name before the number.
        number_i: the number, from 2 up.
        format_str: the format; a MAT name is shortened so that the
            whole name keeps at most 63 characters.
    Outputs: "<base>_<number>".
    """
    # LLFR-00241, LLFR-00403: the number goes at the end; a MAT name
    # stays within 63 characters.
    suffix_str = f"_{number_i}"
    if format_str == MAT_FORMAT_STR:
        kept_length_i = MAT_MAXIMUM_NAME_LENGTH_I - len(suffix_str)
        return base_name_str[:kept_length_i] + suffix_str
    return base_name_str + suffix_str


def group_name_set(name_list: list) -> set:
    """Return the HDF5 groups that a list of dataset paths needs.

    Inputs:
        name_list: dataset paths such as "engine/speed".
    Outputs: every proper leading part, such as "engine".
    """
    # LLFR-00403 item 2: "engine/speed" needs the group "engine".
    group_set = set()
    for name_str in name_list:
        part_list = name_str.split(HDF5_SEPARATOR_STR)
        for part_count_i in range(1, len(part_list)):
            group_set.add(HDF5_SEPARATOR_STR.join(part_list[:part_count_i]))
    return group_set


def free_name(base_name_str: str, format_str: str, taken_set: set) -> str:
    """Return the first numbered name that is not taken.

    Inputs:
        base_name_str: the wanted name, already taken.
        format_str: the format (MAT names keep 63 characters).
        taken_set: the names that may not be used.
    Outputs: "<base>_N" with the smallest N from 2 up that is free.
    """
    # LLFR-00241, LLFR-00403, LLFR-00407: the smallest number from 2 up.
    number_i = FIRST_SUFFIX_NUMBER_I
    while numbered_name(base_name_str, number_i, format_str) in taken_set:
        number_i += 1
    return numbered_name(base_name_str, number_i, format_str)


def move_out_of_time_group(name_list: list, time_index_i: int) -> list:
    """Give another first part to names placed in a group "Time".

    The time signal must be the dataset "Time" (LLFR-00407), so no HDF5
    group may be named "Time": the first part of such a name gets a
    number, as in LLFR-00241, for example "Time/x" becomes "Time_2/x".

    Inputs:
        name_list: the HDF5 names, in list order.
        time_index_i: the index of the time signal, or -1.
    Outputs: the names, with those first parts changed.
    """
    # LLFR-00403 item 2, LLFR-00407: "Time" is a dataset, not a group.
    prefix_str = TIME_SIGNAL_NAME_STR + HDF5_SEPARATOR_STR
    if time_index_i < 0 or not any(
            name_str.startswith(prefix_str) for name_str in name_list):
        return name_list
    first_part_set = {name_str.split(HDF5_SEPARATOR_STR)[0]
                      for name_str in name_list}
    new_first_part_str = free_name(TIME_SIGNAL_NAME_STR, HDF5_FORMAT_STR,
                                   first_part_set)
    return [new_first_part_str + name_str[len(TIME_SIGNAL_NAME_STR):]
            if index_i != time_index_i and name_str.startswith(prefix_str)
            else name_str
            for index_i, name_str in enumerate(name_list)]


def numbered_plain_name_list(plain_name_list: list, number_list: list,
                             time_index_i: int) -> list:
    """Give the file number to the plain names that several signals share.

    Inputs:
        plain_name_list: the plain names of the signals to save, in the
            order of the signal list (LLFR-00945).
        number_list: the number of the data file of each signal
            (LLFR-00940), or None.
        time_index_i: the index of the one time signal (LLFR-00944), or
            -1; it keeps its name.
    Outputs: the names, where a plain name of two or more signals other
        than the time signal gets ``_<file number>`` on each of them
        (LLFR-00946), and a name still taken by an earlier signal gets
        ``_2``, ``_3``... (LLFR-00965), all different apart from the
        time signal.
    """
    # LLFR-00946: every signal of a shared plain name gets the number of
    # its own data file.
    count_dict = {}
    for index_i, plain_str in enumerate(plain_name_list):
        if index_i != time_index_i:
            count_dict[plain_str] = count_dict.get(plain_str, 0) + 1
    name_list = []
    for index_i, plain_str in enumerate(plain_name_list):
        number_i = number_list[index_i]
        if (index_i != time_index_i and count_dict[plain_str] > 1
                and number_i is not None):
            name_list.append(f"{plain_str}_{int(number_i)}")
        else:
            name_list.append(plain_str)
    # LLFR-00965: the later of two signals that still share a name gets
    # the smallest number from 2 up that makes it unique.
    taken_set = {name_str for index_i, name_str in enumerate(name_list)
                 if index_i != time_index_i}
    seen_set = set()
    result_list = list(name_list)
    for index_i, name_str in enumerate(name_list):
        if index_i == time_index_i:
            continue
        if name_str in seen_set:
            suffix_i = FIRST_SUFFIX_NUMBER_I
            while f"{name_str}_{suffix_i}" in taken_set:
                suffix_i += 1
            name_str = f"{name_str}_{suffix_i}"
            taken_set.add(name_str)
        seen_set.add(name_str)
        result_list[index_i] = name_str
    return result_list


def saved_name_list(name_list: list, time_name_str: str,
                    format_str: str, time_index_i: int = None) -> list:
    """Return the names under which the signals are saved.

    Inputs:
        name_list: the names of the signals to save, in list order; they
            are unique, apart from the time signal.
        time_name_str: the name of the time signal (HLFR-00006).
        format_str: one of FORMAT_ORDER_TUPLE.
        time_index_i: the index of the time signal in name_list; None
            finds it by time_name_str.
    Outputs: a list of saved names, one per name of name_list, in the
        same order and all different.
    """
    # LLFR-00407: the time signal is always saved as "Time".
    if time_index_i is None:
        time_index_i = (name_list.index(time_name_str)
                        if time_name_str in name_list else -1)
    # LLFR-00403 items 1 and 2: the names the format can store.
    wanted_list = [TIME_SIGNAL_NAME_STR if index_i == time_index_i
                   else format_name(name_str, format_str)
                   for index_i, name_str in enumerate(name_list)]
    if format_str == HDF5_FORMAT_STR:
        wanted_list = move_out_of_time_group(wanted_list, time_index_i)
    # LLFR-00403, LLFR-00407: a name keeps its place when it is the
    # time signal's or was not changed and does not match the time
    # signal name; the others get a number when they are taken.
    keeps_name_list = [
        index_i == time_index_i
        or (wanted_str == name_list[index_i]
            and not is_time_signal_name(wanted_str))
        for index_i, wanted_str in enumerate(wanted_list)]
    taken_set = {wanted_str for wanted_str, keeps_b
                 in zip(wanted_list, keeps_name_list) if keeps_b}
    result_list = list(wanted_list)
    for index_i, wanted_str in enumerate(wanted_list):
        if keeps_name_list[index_i]:
            continue
        # LLFR-00407: another name matching "Time" gets a number, so the
        # file has one time signal; LLFR-00403: so does a changed name
        # that another saved signal has.
        if wanted_str in taken_set or is_time_signal_name(wanted_str):
            wanted_str = free_name(wanted_str, format_str, taken_set)
        result_list[index_i] = wanted_str
        taken_set.add(wanted_str)
    if format_str == HDF5_FORMAT_STR:
        result_list = hdf5_names_without_groups(result_list, time_index_i)
    return result_list


def hdf5_names_without_groups(name_list: list, time_index_i: int) -> list:
    """Give a number to each HDF5 name that is also a group.

    Inputs:
        name_list: unique HDF5 names, in list order.
        time_index_i: the index of the time signal ("Time" is never a
            group, see move_out_of_time_group), or -1.
    Outputs: the names, where a name that is the group of another name
        (for example "engine" with "engine/speed") has "_N" added, with
        the smallest N from 2 up that makes it neither a group nor
        another saved name.
    """
    # LLFR-00403 item 2: a dataset and a group can't share a path.
    # Numbering a name changes only its last part, so the groups the
    # names need stay the same.
    group_set = group_name_set(name_list)
    result_list = list(name_list)
    for index_i, name_str in enumerate(name_list):
        if index_i == time_index_i or name_str not in group_set:
            continue
        taken_set = group_set | set(result_list)
        result_list[index_i] = free_name(name_str, HDF5_FORMAT_STR,
                                         taken_set)
    return result_list


def non_finite_name_list(name_list: list, array_list: list) -> list:
    """Return the signals that have a value that is not a finite number.

    Inputs:
        name_list: the names of the signals to save.
        array_list: their samples, one array per name.
    Outputs: the names of the signals with an infinite or NaN sample,
        in list order.
    """
    # LLFR-00408: no data file the app opens can hold such values.
    return [name_str for name_str, value_array in zip(name_list, array_list)
            if not np.all(np.isfinite(float_array(value_array)))]


def non_finite_reason(name_list: list) -> str:
    """Return the reason for the error box of LLFR-00408.

    Inputs:
        name_list: the names of the signals with non-finite values.
    Outputs: the sentence followed by the list of the signals.
    """
    # LLFR-00408, LLFR-00559: each signal is named, as one item of the
    # list below the sentence (LLFR-00977, LLFR-00980).
    return list_text([f"'{name_str}'" for name_str in name_list],
                     NON_FINITE_REASON_STR)


def changed_name_list(name_list: list, new_name_list: list) -> list:
    """Return the names that were changed for the saved file.

    Inputs:
        name_list: the names in the app.
        new_name_list: the saved names, in the same order.
    Outputs: a list of (old name, new name) tuples, in list order.
    """
    # LLFR-00404: every changed name, including the time signal's.
    return [(old_str, new_str)
            for old_str, new_str in zip(name_list, new_name_list)
            if old_str != new_str]


def changed_names_text(change_list: list) -> str:
    """Return the text of the box that lists the changed names.

    Inputs:
        change_list: (old name, new name) tuples.
    Outputs: one item "<old name> → <new name>" per change, numbered
        and separated by blank lines when there are two or more
        (LLFR-00977, LLFR-00979).
    """
    # LLFR-00404: each changed name as "<old name> → <new name>".
    return list_body_text([f"{old_str} → {new_str}"
                           for old_str, new_str in change_list])


# ----------------------------------------------------------------------
# File content (LLFR-00402)
# ----------------------------------------------------------------------

def float_array(value_array) -> np.ndarray:
    """Return the samples of a signal as a 1-D float64 array.

    Inputs:
        value_array: the samples (any 1-D numeric array).
    Outputs: a float64 numpy array.
    """
    # LLFR-00402: every value is a 64-bit floating-point number.
    return np.asarray(value_array, dtype=np.float64).reshape(-1)


def csv_bytes(name_list: list, array_list: list) -> bytes:
    """Return the content of a CSV file with the signals.

    Inputs:
        name_list: the saved names, one per column.
        array_list: the samples, one array per name, all as long.
    Outputs: UTF-8 bytes: the names in the first row, then one row per
        sample, "," as separator and "." as decimal mark.
    """
    # LLFR-00402 item 1, LLFR-00059, LLFR-00061: "," and ".", with names
    # quoted when they hold a ",", a quote or a line break.
    text_buffer = io.StringIO()
    csv.writer(text_buffer, lineterminator="\n").writerow(name_list)
    # LLFR-00402: repr writes the shortest text that reads back as the
    # same float64 value.
    column_list = [[repr(value_f) for value_f in float_array(
        value_array).tolist()] for value_array in array_list]
    for row_tuple in zip(*column_list):
        text_buffer.write(",".join(row_tuple))
        text_buffer.write("\n")
    return text_buffer.getvalue().encode("utf-8")


def excel_bytes(name_list: list, array_list: list) -> bytes:
    """Return the content of an Excel file with the signals.

    Inputs:
        name_list: the saved names, one per column.
        array_list: the samples, one array per name, all as long.
    Outputs: the bytes of an .xlsx file with one sheet: the names in
        the first row, then one row per sample.
    """
    # LLFR-00402 item 2, LLFR-00059, LLFR-00060: one sheet only.
    import openpyxl
    from openpyxl.cell import WriteOnlyCell
    workbook = openpyxl.Workbook(write_only=True)
    sheet = workbook.create_sheet()
    # LLFR-00402: every name is written as text, even one that starts
    # with "=" and would otherwise become a formula.
    name_cell_list = []
    for name_str in name_list:
        name_cell = WriteOnlyCell(sheet, value=name_str)
        name_cell.data_type = "s"
        name_cell_list.append(name_cell)
    sheet.append(name_cell_list)
    # LLFR-00402: openpyxl writes a float with 16 significant digits,
    # which does not always read back as the same float64 value; so each
    # number cell gets the shortest exact text (repr) itself.
    column_list = [float_array(value_array).tolist()
                   for value_array in array_list]
    for row_tuple in zip(*column_list):
        row_cell_list = []
        for value_f in row_tuple:
            number_cell = WriteOnlyCell(sheet, value=repr(value_f))
            number_cell.data_type = "n"
            row_cell_list.append(number_cell)
        sheet.append(row_cell_list)
    content_buffer = io.BytesIO()
    workbook.save(content_buffer)
    return content_buffer.getvalue()


def mat_bytes(name_list: list, array_list: list) -> bytes:
    """Return the content of a MAT file with the signals.

    Inputs:
        name_list: the saved names, valid MAT variable names.
        array_list: the samples, one array per name.
    Outputs: the bytes of a MATLAB v5 file (not v7.3) with one N×1
        float64 variable per signal.
    """
    # LLFR-00402 item 3, LLFR-00062, LLFR-00064: version 5 format.
    import scipy.io
    variable_dict = {name_str: float_array(value_array).reshape(-1, 1)
                     for name_str, value_array in zip(name_list,
                                                      array_list)}
    content_buffer = io.BytesIO()
    scipy.io.savemat(content_buffer, variable_dict, format="5",
                     oned_as="column")
    return content_buffer.getvalue()


def hdf5_bytes(name_list: list, array_list: list) -> bytes:
    """Return the content of an HDF5 file with the signals.

    Inputs:
        name_list: the saved names, valid dataset paths.
        array_list: the samples, one array per name.
    Outputs: the bytes of an HDF5 file with one 1-D float64 dataset per
        signal, at the path of its name. Raises SignalWriteError when
        h5py is not installed.
    """
    # LLFR-00402 item 4, LLFR-00134: a "/" in a name makes groups.
    h5py_library = hdf5_library()
    if h5py_library is None:
        raise SignalWriteError(NO_HDF5_LIBRARY_REASON_STR)
    content_buffer = io.BytesIO()
    # LLFR-00401: the file keeps the order the datasets were created in.
    with h5py_library.File(content_buffer, "w",
                           track_order=True) as hdf5_file:
        for name_str, value_array in zip(name_list, array_list):
            # LLFR-00134, LLFR-00401: every group also tracks the order,
            # so the loader lists its members in the list order.
            part_list = name_str.split(HDF5_SEPARATOR_STR)
            for part_count_i in range(1, len(part_list)):
                group_path_str = HDF5_SEPARATOR_STR.join(
                    part_list[:part_count_i])
                if group_path_str not in hdf5_file:
                    hdf5_file.create_group(group_path_str, track_order=True)
            hdf5_file.create_dataset(name_str,
                                     data=float_array(value_array))
    return content_buffer.getvalue()


def signal_file_bytes(name_list: list, array_list: list,
                      format_str: str) -> bytes:
    """Return the content of a data file that holds the signals.

    Inputs:
        name_list: the saved names (saved_name_list), in list order.
        array_list: the samples, one array per name, all as long.
        format_str: one of FORMAT_ORDER_TUPLE.
    Outputs: the bytes of the file. Raises SignalWriteError when the
        content can't be made, with the reason for the error box.
    """
    # LLFR-00402: the writer of the chosen format.
    writer_dict = {CSV_FORMAT_STR: csv_bytes, EXCEL_FORMAT_STR: excel_bytes,
                   MAT_FORMAT_STR: mat_bytes, HDF5_FORMAT_STR: hdf5_bytes}
    # LLFR-00408: infinite or NaN values can't be saved.
    bad_name_list = non_finite_name_list(name_list, array_list)
    if bad_name_list:
        raise SignalWriteError(non_finite_reason(bad_name_list))
    # LLFR-00400: an Excel sheet has a fixed size.
    if format_str == EXCEL_FORMAT_STR and array_list:
        reason_str = excel_limit_reason(len(array_list),
                                        len(float_array(array_list[0])))
        if reason_str:
            raise SignalWriteError(reason_str)
    try:
        return writer_dict[format_str](name_list, array_list)
    except SignalWriteError:
        raise
    except Exception as error:
        # LLFR-00399: a library error becomes the reason of the box.
        raise SignalWriteError(str(error) or type(error).__name__) \
            from error
