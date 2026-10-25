"""Open a time-series file and check its content.

``load_signal_file`` reads CSV, Excel (.xlsx) and MATLAB (.mat) files
(HLFR-00005) into a SignalFile. When the file can't be opened it raises
one of the FileOpenError subclasses of ``model.errors``, whose message is
the text of the File Open Error box (HLFR-00002). No Qt code is used here
(COR-00009).
"""

import io
import math
import os
import re

import numpy as np
import pandas as pd
import scipy.io

from model.errors import (
    OTHER_SIGNAL_CHECK_STR, SAMPLE_COUNT_CHECK_STR, TIME_SIGNAL_CHECK_STR,
    ContentCheckError, FileAccessError, FileReadError,
    UnsupportedFormatError)
from model.signal_file import TIME_SIGNAL_NAME_STR, SignalFile

# HLFR-00005: the file formats the app opens, by extension.
SUPPORTED_EXTENSION_TUPLE = (".csv", ".xlsx", ".mat")

# LLFR-00065: a sample written as text must be a plain finite number,
# such as "-2", "3.5", ".5" or "1e-3" (no "nan", "inf" or "1_000").
NUMBER_PATTERN_STR = r"[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?"

# LLFR-00061: (separator, decimal mark) of the two CSV styles.
COMMA_STYLE_TUPLE = (",", ".")
# LLFR-00009: operating system errors that mean the file can't be
# accessed; other errors raised by a parser mean it can't be read.
ACCESS_ERROR_TUPLE = (FileNotFoundError, PermissionError, IsADirectoryError)
SEMICOLON_STYLE_TUPLE = (";", ",")


def load_signal_file(path_str: str) -> SignalFile:
    """Open a time-series file and return its signals.

    Inputs:
        path_str: path of the file to open.
    Outputs: a SignalFile with one float64 array per signal. Raises
        UnsupportedFormatError (LLFR-00011), FileAccessError
        (LLFR-00009), FileReadError (LLFR-00008, LLFR-00064, LLFR-00065)
        or ContentCheckError (LLFR-00012); never any other exception.
    """
    # LLFR-00011: check the format first, without touching the file.
    file_name_str = os.path.basename(path_str)
    extension_str = os.path.splitext(path_str)[1].lower()
    if extension_str not in SUPPORTED_EXTENSION_TUPLE:
        raise UnsupportedFormatError(
            f"The file '{file_name_str}' can't be opened because its "
            "file format is not supported. "
            f"Supported formats: {', '.join(SUPPORTED_EXTENSION_TUPLE)}.")
    # LLFR-00009: the file must exist, be a file and be readable.
    check_file_access(path_str)
    # LLFR-00059, LLFR-00062: read the signals in the file's format.
    reader_dict = {".csv": read_csv_signals, ".xlsx": read_excel_signals,
                   ".mat": read_mat_signals}
    try:
        signal_dict = reader_dict[extension_str](path_str)
    except OSError as error:
        # LLFR-00009: the file disappeared or became unreadable meanwhile.
        raise access_error(file_name_str, error_reason(error)) from error
    # HLFR-00008, HLFR-00009, LLFR-00012: check the content.
    check_signal_content(file_name_str, signal_dict)
    return SignalFile(path_str, signal_dict)


def access_error(file_name_str: str, reason_str: str) -> FileAccessError:
    """Build the error for a file that could not be accessed.

    Inputs:
        file_name_str: name of the file, shown in the message.
        reason_str: why the file could not be accessed.
    Outputs: a FileAccessError with the message for the error box.
    """
    # LLFR-00009: the message says the file could not be accessed.
    return FileAccessError(
        f"The file '{file_name_str}' could not be accessed: {reason_str}.")


def read_error(file_name_str: str, reason_str: str) -> FileReadError:
    """Build the error for a file that could not be read.

    Inputs:
        file_name_str: name of the file, shown in the message.
        reason_str: short reason, such as which value is not a number.
    Outputs: a FileReadError with the message for the error box.
    """
    # LLFR-00008, LLFR-00064, LLFR-00065: say the file could not be read.
    return FileReadError(
        f"The file '{file_name_str}' could not be read: {reason_str}.")


def error_reason(error: OSError) -> str:
    """Return a short reason for an operating system error.

    Inputs:
        error: the OSError raised while opening the file.
    Outputs: "file not found", "permission denied" or the system text.
    """
    # LLFR-00009: name the reason the file could not be accessed.
    if isinstance(error, FileNotFoundError):
        return "file not found"
    if isinstance(error, PermissionError):
        return "permission denied"
    if isinstance(error, IsADirectoryError):
        return "the path is a folder, not a file"
    return error.strerror or str(error)


def check_file_access(path_str: str) -> None:
    """Check that the path is an existing, readable file.

    Inputs:
        path_str: path of the file.
    Outputs: none. Raises FileAccessError when the check fails.
    """
    # LLFR-00009: missing file, folder or no read permission.
    file_name_str = os.path.basename(path_str)
    if not os.path.exists(path_str):
        raise access_error(file_name_str, "file not found")
    if os.path.isdir(path_str):
        raise access_error(file_name_str, "the path is a folder, not a file")
    if not os.access(path_str, os.R_OK):
        raise access_error(file_name_str, "permission denied")


def detect_csv_style_list(header_line_str: str) -> list:
    """Return the CSV styles to try, from the first line of the file.

    Inputs:
        header_line_str: the first line of the file (the signal names).
    Outputs: a list of (separator, decimal mark) tuples to try in order.
    """
    # LLFR-00061: count the separators that are outside quotes.
    inside_quotes_b = False
    comma_count_i = 0
    semicolon_count_i = 0
    for character_str in header_line_str:
        if character_str == '"':
            inside_quotes_b = not inside_quotes_b
        elif not inside_quotes_b and character_str == ",":
            comma_count_i += 1
        elif not inside_quotes_b and character_str == ";":
            semicolon_count_i += 1
    if comma_count_i > 0:
        return [COMMA_STYLE_TUPLE]
    if semicolon_count_i > 0:
        return [SEMICOLON_STYLE_TUPLE]
    # LLFR-00061: one column; the style can only be told from the data.
    return [COMMA_STYLE_TUPLE, SEMICOLON_STYLE_TUPLE]


def read_csv_signals(path_str: str) -> dict:
    """Read the signals of a CSV file.

    Inputs:
        path_str: path of the .csv file.
    Outputs: a dict signal name -> float64 array, in column order.
        Raises FileReadError when the file can't be parsed.
    """
    # LLFR-00059, LLFR-00061: decode the text (UTF-8, BOM allowed).
    file_name_str = os.path.basename(path_str)
    with open(path_str, "rb") as csv_file:
        content_bytes = csv_file.read()
    try:
        text_str = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise read_error(file_name_str,
                         "the file is not UTF-8 text") from error
    # LLFR-00059: empty lines at the end of the file are ignored.
    text_str = text_str.rstrip("\r\n\t ")
    if not text_str:
        raise read_error(file_name_str, "the file is empty")
    header_line_str = text_str.splitlines()[0]
    style_list = detect_csv_style_list(header_line_str)
    last_error = None
    for separator_str, decimal_str in style_list:
        try:
            # LLFR-00059: read every cell as text, then convert strictly.
            table_df = pd.read_csv(
                io.StringIO(text_str), sep=separator_str, header=None,
                dtype=str, keep_default_na=False, na_filter=False,
                skip_blank_lines=False, engine="c")
            return table_signals(file_name_str, table_df.values.tolist(),
                                 decimal_str)
        except (pd.errors.ParserError, ValueError) as error:
            last_error = error
        except FileReadError as error:
            last_error = error
    if isinstance(last_error, FileReadError):
        raise last_error
    # LLFR-00008: the rows don't fit the columns of the first row.
    raise read_error(
        file_name_str,
        "some rows have more values than there are signal names"
    ) from last_error


def read_excel_signals(path_str: str) -> dict:
    """Read the signals of the first sheet of an Excel file.

    Inputs:
        path_str: path of the .xlsx file.
    Outputs: a dict signal name -> float64 array, in column order.
        Raises FileReadError when the file can't be parsed.
    """
    # LLFR-00060: only the first sheet is read.
    file_name_str = os.path.basename(path_str)
    try:
        table_df = pd.read_excel(path_str, sheet_name=0, header=None,
                                 engine="openpyxl", dtype=object)
    except ACCESS_ERROR_TUPLE:
        raise
    except Exception as error:
        # LLFR-00008: not a valid .xlsx file (corrupt, not a zip, ...).
        raise read_error(file_name_str,
                         "the file is empty or corrupt") from error
    # LLFR-00059: the first row holds the names, the rest the samples.
    row_list = table_df.values.tolist()
    return table_signals(file_name_str, row_list, ".")


def is_empty_cell(cell: object) -> bool:
    """Tell whether a table cell holds no value.

    Inputs:
        cell: a cell value read from a CSV or Excel file.
    Outputs: True for None, NaN or text made only of spaces.
    """
    # LLFR-00065: empty cells are missing samples.
    if cell is None:
        return True
    if isinstance(cell, str):
        return cell.strip() == ""
    if isinstance(cell, float):
        return math.isnan(cell)
    return False


def table_signals(file_name_str: str, row_list: list,
                  decimal_str: str) -> dict:
    """Turn the rows of a CSV or Excel table into signals.

    Inputs:
        file_name_str: name of the file, for error messages.
        row_list: list of rows, each a list of cells; the first row
            holds the signal names.
        decimal_str: decimal mark of numbers written as text.
    Outputs: a dict signal name -> float64 array, in column order.
        Raises FileReadError for bad names or values.
    """
    # LLFR-00059: ignore empty rows at the end and empty trailing columns.
    while row_list and all(is_empty_cell(cell) for cell in row_list[-1]):
        row_list = row_list[:-1]
    if not row_list:
        raise read_error(file_name_str, "the file is empty")
    column_count_i = len(row_list[0])
    while column_count_i > 0 and all(
            is_empty_cell(cell_row_list[column_count_i - 1])
            for cell_row_list in row_list):
        column_count_i -= 1
    if column_count_i == 0:
        raise read_error(file_name_str, "the file is empty")
    # LLFR-00059: the signal names come from the first row.
    name_list = []
    for column_i in range(column_count_i):
        name_cell = row_list[0][column_i]
        if is_empty_cell(name_cell):
            raise read_error(
                file_name_str,
                f"the signal name in column {column_i + 1} is empty")
        name_str = cell_name(name_cell)
        if name_str in name_list:
            raise read_error(
                file_name_str, f"the signal name '{name_str}' is repeated")
        name_list.append(name_str)
    if len(row_list) < 2:
        raise read_error(file_name_str, "the file contains no samples")
    # LLFR-00059, LLFR-00065: each column below the names is a signal.
    signal_dict = {}
    for column_i, name_str in enumerate(name_list):
        value_list = []
        for row_index_i in range(1, len(row_list)):
            cell = row_list[row_index_i][column_i]
            value_list.append(cell_number(
                file_name_str, cell, decimal_str, name_str,
                row_index_i + 1))
        signal_dict[name_str] = np.array(value_list, dtype=np.float64)
    return signal_dict


def cell_name(name_cell: object) -> str:
    """Return the signal name written in a header cell.

    Inputs:
        name_cell: the cell value of the first row (text or number).
    Outputs: the name as text, without spaces around it.
    """
    # LLFR-00059: a name is the header text; an integer number such as
    # 5.0 from Excel becomes "5".
    if isinstance(name_cell, float) and name_cell.is_integer():
        return str(int(name_cell))
    return str(name_cell).strip()


def cell_number(file_name_str: str, cell: object, decimal_str: str,
                signal_name_str: str, row_number_i: int) -> float:
    """Convert one sample cell to a finite float.

    Inputs:
        file_name_str: name of the file, for error messages.
        cell: the cell value (text from CSV; number, text, date or
            bool from Excel).
        decimal_str: decimal mark of numbers written as text.
        signal_name_str: name of the signal, for error messages.
        row_number_i: row of the cell in the file (the names are row 1).
    Outputs: the value as a float. Raises FileReadError when the cell is
        empty or not a finite number.
    """
    # LLFR-00065: empty samples are missing values.
    where_str = f"in signal '{signal_name_str}' row {row_number_i}"
    if is_empty_cell(cell):
        raise read_error(file_name_str, f"the value {where_str} is empty")
    # LLFR-00065: booleans, dates and other objects are not numbers.
    if isinstance(cell, (bool, np.bool_)):
        number_f = math.nan
    elif isinstance(cell, (int, float, np.integer, np.floating)):
        number_f = float(cell)
    elif isinstance(cell, str):
        number_f = text_number(cell.strip(), decimal_str)
    else:
        number_f = math.nan
    if not math.isfinite(number_f):
        raise read_error(
            file_name_str,
            f"the value '{cell}' {where_str} is not a number")
    return number_f


def text_number(text_str: str, decimal_str: str) -> float:
    """Convert a number written as text, strictly.

    Inputs:
        text_str: the text of one sample.
        decimal_str: the decimal mark of the CSV style, "." or ",".
    Outputs: the number, or NaN when the text is not a plain number
        written with that decimal mark.
    """
    # LLFR-00061: in the ";" style "," is the decimal mark and "." is
    # not allowed; in the "," style only "." is a decimal mark.
    other_mark_str = "." if decimal_str == "," else ","
    if other_mark_str in text_str:
        return math.nan
    text_str = text_str.replace(decimal_str, ".")
    # LLFR-00065: only plain finite numbers are samples.
    if not re.fullmatch(NUMBER_PATTERN_STR, text_str):
        return math.nan
    return float(text_str)


def read_mat_signals(path_str: str) -> dict:
    """Read the signals of a MATLAB file.

    Inputs:
        path_str: path of the .mat file.
    Outputs: a dict variable name -> float64 array, in file order, with
        only the one-dimensional numeric variables. Raises FileReadError
        for v7.3, corrupt files and missing (NaN) or infinite values.
    """
    file_name_str = os.path.basename(path_str)
    try:
        variable_dict = scipy.io.loadmat(path_str)
    except NotImplementedError as error:
        # LLFR-00064: v7.3 files need an extra library (COR-00011).
        raise read_error(file_name_str,
                         "MATLAB v7.3 files are not supported") from error
    except ACCESS_ERROR_TUPLE:
        raise
    except Exception as error:
        # LLFR-00008: corrupt or not a MATLAB file.
        raise read_error(file_name_str,
                         "the file is empty or corrupt") from error
    signal_dict = {}
    for name_str, value in variable_dict.items():
        # LLFR-00063: skip the file header entries and non-signals.
        if name_str.startswith("__") or not is_mat_signal(value):
            continue
        # LLFR-00062: a 1xN or Nx1 numeric array is one signal.
        signal_array = np.asarray(value, dtype=np.float64).reshape(-1)
        if not np.all(np.isfinite(signal_array)):
            bad_index_i = int(np.flatnonzero(~np.isfinite(signal_array))[0])
            raise read_error(
                file_name_str,
                f"the value of signal '{name_str}' sample "
                f"{bad_index_i + 1} is missing or not a finite number")
        signal_dict[name_str] = signal_array
    return signal_dict


def is_mat_signal(value: object) -> bool:
    """Tell whether a MAT variable is a one-dimensional numeric array.

    Inputs:
        value: a variable returned by scipy.io.loadmat.
    Outputs: True for a non-empty int, uint or float array of shape
        (N,), (1, N) or (N, 1); False for anything else (matrices, text,
        structs, cells, complex or boolean values).
    """
    # LLFR-00062, LLFR-00063: only 1-D numeric arrays are signals.
    if not isinstance(value, np.ndarray) or value.dtype.kind not in "iuf":
        return False
    if value.size < 1:
        return False
    return value.ndim == 1 or (value.ndim == 2 and min(value.shape) == 1)


def check_signal_content(file_name_str: str, signal_dict: dict) -> None:
    """Check the content rules of HLFR-00008 and HLFR-00009.

    Inputs:
        file_name_str: name of the file, for error messages.
        signal_dict: signal name -> float64 array.
    Outputs: none. Raises ContentCheckError naming the failed check.
    """
    # HLFR-00008, LLFR-00053: "Time" (case-sensitive) must exist.
    prefix_str = f"The file '{file_name_str}' cannot be opened because"
    if TIME_SIGNAL_NAME_STR not in signal_dict:
        raise ContentCheckError(
            f"{prefix_str} it has no time signal named "
            f"'{TIME_SIGNAL_NAME_STR}' (the name is case-sensitive).",
            TIME_SIGNAL_CHECK_STR)
    # HLFR-00008, LLFR-00012: at least one signal besides "Time".
    if len(signal_dict) < 2:
        raise ContentCheckError(
            f"{prefix_str} it has no signal other than "
            f"'{TIME_SIGNAL_NAME_STR}'.", OTHER_SIGNAL_CHECK_STR)
    # HLFR-00009, LLFR-00012: every signal has as many samples as "Time".
    time_count_i = len(signal_dict[TIME_SIGNAL_NAME_STR])
    different_list = [
        f"'{name_str}' has {len(signal_array)}"
        for name_str, signal_array in signal_dict.items()
        if len(signal_array) != time_count_i]
    if different_list:
        raise ContentCheckError(
            f"{prefix_str} its signals have different sample counts: "
            f"'{TIME_SIGNAL_NAME_STR}' has {time_count_i} samples, but "
            f"{', '.join(different_list)}.", SAMPLE_COUNT_CHECK_STR)
