"""Tests for model.file_loader, model.signal_file and model.errors.

Every test file is created inside a temporary folder (no binary fixtures
are committed). No Qt is needed.
"""

import os
import stat
import tempfile
import unittest
from unittest import mock

import numpy as np
import openpyxl
import scipy.io

from tests.support import covers

from model.errors import (
    OTHER_SIGNAL_CHECK_STR, SAMPLE_COUNT_CHECK_STR, TIME_SIGNAL_CHECK_STR,
    ContentCheckError, FileAccessError, FileOpenError, FileReadError,
    UnsupportedFormatError)
from model.file_loader import SUPPORTED_EXTENSION_TUPLE, load_signal_file
from model.signal_file import TIME_SIGNAL_NAME_STR, SignalFile


class TemporaryFolderTest(unittest.TestCase):
    """Base class that gives each test an empty temporary folder."""

    def setUp(self) -> None:
        """Create the temporary folder.

        Inputs: none.
        Outputs: none.
        """
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

    def path(self, file_name_str: str) -> str:
        """Return the path of a file inside the temporary folder.

        Inputs:
            file_name_str: name of the file.
        Outputs: the absolute path.
        """
        return os.path.join(self.folder.name, file_name_str)

    def write_text(self, file_name_str: str, text_str: str,
                   encoding_str: str = "utf-8") -> str:
        """Write a text file in the temporary folder.

        Inputs:
            file_name_str: name of the file.
            text_str: content of the file.
            encoding_str: text encoding.
        Outputs: the path of the file.
        """
        path_str = self.path(file_name_str)
        with open(path_str, "w", encoding=encoding_str, newline="") as file:
            file.write(text_str)
        return path_str

    def write_bytes(self, file_name_str: str, content_bytes: bytes) -> str:
        """Write a binary file in the temporary folder.

        Inputs:
            file_name_str: name of the file.
            content_bytes: content of the file.
        Outputs: the path of the file.
        """
        path_str = self.path(file_name_str)
        with open(path_str, "wb") as file:
            file.write(content_bytes)
        return path_str

    def write_excel(self, file_name_str: str, sheet_list: list) -> str:
        """Write an .xlsx file with openpyxl.

        Inputs:
            file_name_str: name of the file.
            sheet_list: one list of rows per sheet, in sheet order.
        Outputs: the path of the file.
        """
        workbook = openpyxl.Workbook()
        workbook.remove(workbook.active)
        for sheet_index_i, row_list in enumerate(sheet_list):
            sheet = workbook.create_sheet(f"Sheet{sheet_index_i + 1}")
            for row in row_list:
                sheet.append(row)
        path_str = self.path(file_name_str)
        workbook.save(path_str)
        return path_str

    def write_mat(self, file_name_str: str, variable_dict: dict) -> str:
        """Write a .mat file with scipy.io.savemat.

        Inputs:
            file_name_str: name of the file.
            variable_dict: variable name -> value.
        Outputs: the path of the file.
        """
        path_str = self.path(file_name_str)
        scipy.io.savemat(path_str, variable_dict)
        return path_str

    def assert_read_error(self, path_str: str, *phrase_tuple: str) -> None:
        """Check that loading fails with a FileReadError message.

        Inputs:
            path_str: the file to load.
            phrase_tuple: extra phrases the message must contain.
        Outputs: none.
        """
        with self.assertRaises(FileReadError) as context:
            load_signal_file(path_str)
        message_str = str(context.exception)
        self.assertIn("could not be read", message_str)
        for phrase_str in phrase_tuple:
            self.assertIn(phrase_str, message_str)

    def assert_check_error(self, path_str: str, check_str: str) -> str:
        """Check that loading fails with a ContentCheckError.

        Inputs:
            path_str: the file to load.
            check_str: the expected failed_check_str.
        Outputs: the error message.
        """
        with self.assertRaises(ContentCheckError) as context:
            load_signal_file(path_str)
        self.assertEqual(context.exception.failed_check_str, check_str)
        message_str = str(context.exception)
        self.assertIn("cannot be opened", message_str)
        return message_str


class CsvLoadingTest(TemporaryFolderTest):
    """CSV layout and style detection (LLFR-00059, LLFR-00061)."""

    @covers("LLFR-00059", "LLFR-00061", "HLFR-00005")
    def test_comma_style_columns_are_signals(self) -> None:
        """A ","/"." CSV gives one signal per column, names from row 1.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text(
            "data.csv", "Time,Speed,Force\n0,-1.5,1e3\n0.5,2,-2.5E-2\n"
            "1,3.25,.5\n")
        signal_file = load_signal_file(path_str)
        self.assertIsInstance(signal_file, SignalFile)
        self.assertEqual(signal_file.path_str, path_str)
        self.assertEqual(signal_file.signal_name_list,
                         ["Time", "Speed", "Force"])
        np.testing.assert_array_equal(signal_file.signal_array("Speed"),
                                      [-1.5, 2.0, 3.25])
        np.testing.assert_array_equal(signal_file.signal_array("Force"),
                                      [1000.0, -0.025, 0.5])
        for name_str in signal_file.signal_name_list:
            self.assertEqual(signal_file.signal_array(name_str).dtype,
                             np.float64)
            self.assertEqual(signal_file.signal_array(name_str).ndim, 1)

    @covers("LLFR-00061", "LLFR-00059", "HLFR-00005")
    def test_semicolon_style_uses_comma_decimal_mark(self) -> None:
        """A ";"/"," CSV is detected and read with "," as decimal mark.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text(
            "data.csv", "Time;Speed\n0;-1,5\n0,5;2,25e1\n1;3\n")
        signal_file = load_signal_file(path_str)
        self.assertEqual(signal_file.signal_name_list, ["Time", "Speed"])
        np.testing.assert_array_equal(signal_file.time_array,
                                      [0.0, 0.5, 1.0])
        np.testing.assert_array_equal(signal_file.signal_array("Speed"),
                                      [-1.5, 22.5, 3.0])

    @covers("LLFR-00061", "LLFR-00065")
    def test_semicolon_style_rejects_dot_decimal(self) -> None:
        """In the ";" style a "." number is not valid and is reported.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text("data.csv", "Time;Speed\n0;1.5\n")
        self.assert_read_error(path_str, "'1.5'", "Speed", "row 2")

    @covers("LLFR-00061", "LLFR-00059")
    def test_quoted_names_with_separators(self) -> None:
        """Quoted names may contain the other style's separator.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text(
            "data.csv", '"Time";"Speed, front";"Force"\n0;1,5;2\n1;2;3\n')
        signal_file = load_signal_file(path_str)
        self.assertEqual(signal_file.signal_name_list,
                         ["Time", "Speed, front", "Force"])
        np.testing.assert_array_equal(
            signal_file.signal_array("Speed, front"), [1.5, 2.0])

    @covers("LLFR-00059")
    def test_bom_spaces_and_trailing_blank_lines(self) -> None:
        """BOM, spaces around names and empty end lines are ignored.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text(
            "data.csv", " Time , Speed \r\n0,1\r\n1, 2 \r\n\r\n\r\n",
            encoding_str="utf-8-sig")
        signal_file = load_signal_file(path_str)
        self.assertEqual(signal_file.signal_name_list, ["Time", "Speed"])
        np.testing.assert_array_equal(signal_file.signal_array("Speed"),
                                      [1.0, 2.0])

    @covers("LLFR-00059", "HLFR-00005")
    def test_uppercase_extension_is_supported(self) -> None:
        """The extension check ignores case (".CSV" is a CSV file).

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text("DATA.CSV", "Time,A\n0,1\n")
        self.assertEqual(load_signal_file(path_str).signal_name_list,
                         ["Time", "A"])


class CsvReadErrorTest(TemporaryFolderTest):
    """Bad CSV content gives a read error (LLFR-00008, LLFR-00065)."""

    @covers("LLFR-00065", "HLFR-00002")
    def test_non_numeric_value_names_signal_and_row(self) -> None:
        """A text value is reported with its signal and row.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text("data.csv",
                                   "Time,Speed\n0,1\n1,abc\n2,3\n")
        self.assert_read_error(path_str, "'abc'", "'Speed'", "row 3",
                               "not a number")

    @covers("LLFR-00065")
    def test_empty_cell_is_missing(self) -> None:
        """An empty cell in the middle of a column is a missing value.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text("data.csv", "Time,Speed\n0,\n1,2\n")
        self.assert_read_error(path_str, "'Speed'", "row 2", "empty")

    @covers("LLFR-00065")
    def test_short_row_is_missing_value(self) -> None:
        """A row with fewer values than names has a missing value.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text("data.csv", "Time,A,B\n0,1,2\n1,2\n")
        self.assert_read_error(path_str, "'B'", "row 3")

    @covers("LLFR-00065")
    def test_blank_line_inside_data_is_missing(self) -> None:
        """An empty line between samples is a missing sample.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text("data.csv", "Time,A\n0,1\n\n2,3\n")
        self.assert_read_error(path_str, "row 3", "empty")

    @covers("LLFR-00065")
    def test_nan_and_infinity_text_are_not_numbers(self) -> None:
        """"nan", "inf" and similar text are not finite numbers.

        Inputs: none.
        Outputs: none.
        """
        for text_str in ("nan", "NaN", "inf", "-Infinity", "1_000", "0x1A",
                         "1.2.3", "--1"):
            with self.subTest(text_str=text_str):
                path_str = self.write_text(
                    "data.csv", f"Time,A\n0,{text_str}\n")
                self.assert_read_error(path_str, f"'{text_str}'")

    @covers("LLFR-00008")
    def test_too_many_values_in_a_row(self) -> None:
        """A row with more values than names can't be parsed.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text("data.csv", "Time,A\n0,1\n1,2,3\n")
        self.assert_read_error(path_str)

    @covers("LLFR-00008")
    def test_duplicate_names(self) -> None:
        """Two columns with the same name are reported.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text("data.csv", "Time,A,A\n0,1,2\n")
        self.assert_read_error(path_str, "'A'", "repeated")

    @covers("LLFR-00008")
    def test_empty_name(self) -> None:
        """A column without a name is reported.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text("data.csv", "Time,,B\n0,1,2\n")
        self.assert_read_error(path_str, "column 2")

    @covers("LLFR-00008")
    def test_empty_file_and_header_only(self) -> None:
        """An empty file or a file with only names can't be read.

        Inputs: none.
        Outputs: none.
        """
        self.assert_read_error(self.write_text("empty.csv", ""), "empty")
        self.assert_read_error(self.write_text("blank.csv", "\n\n"),
                               "empty")
        self.assert_read_error(self.write_text("names.csv", "Time,A\n"),
                               "no samples")

    @covers("LLFR-00008")
    def test_binary_content_is_not_utf8(self) -> None:
        """A file that isn't UTF-8 text gives a read error.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_bytes("data.csv",
                                    b"Time,A\n0,\xff\xfe\x00\x81\n")
        self.assert_read_error(path_str, "UTF-8")

    @covers("LLFR-00061", "LLFR-00008")
    def test_single_column_file_is_read(self) -> None:
        """A one-column file is read; it then fails the content check.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text("data.csv", "Time\n0,5\n1\n")
        self.assert_check_error(path_str, OTHER_SIGNAL_CHECK_STR)


class ExcelLoadingTest(TemporaryFolderTest):
    """Excel layout and first sheet (LLFR-00059, LLFR-00060)."""

    @covers("LLFR-00059", "LLFR-00060", "HLFR-00005")
    def test_only_first_sheet_is_read(self) -> None:
        """The first sheet is read; an invalid second sheet is ignored.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_excel("data.xlsx", [
            [["Time", "Speed", "Force"], [0, -1.5, 3], [0.5, 2, 4.25]],
            [["Other"], ["text"], [None]]])
        signal_file = load_signal_file(path_str)
        self.assertEqual(signal_file.signal_name_list,
                         ["Time", "Speed", "Force"])
        np.testing.assert_array_equal(signal_file.time_array, [0.0, 0.5])
        np.testing.assert_array_equal(signal_file.signal_array("Force"),
                                      [3.0, 4.25])
        self.assertEqual(signal_file.signal_array("Speed").dtype,
                         np.float64)

    @covers("LLFR-00060", "LLFR-00012")
    def test_second_sheet_signals_are_not_read(self) -> None:
        """Signals only in the second sheet don't count.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_excel("data.xlsx", [
            [["Speed"], [1], [2]],
            [["Time", "Speed"], [0, 1], [1, 2]]])
        self.assert_check_error(path_str, TIME_SIGNAL_CHECK_STR)

    @covers("LLFR-00065", "HLFR-00002")
    def test_text_cell_is_not_a_number(self) -> None:
        """A text cell is reported with its signal and row.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_excel("data.xlsx", [
            [["Time", "Speed"], [0, 1], [1, "fast"]]])
        self.assert_read_error(path_str, "'fast'", "'Speed'", "row 3")

    @covers("LLFR-00065")
    def test_empty_bool_and_date_cells(self) -> None:
        """Empty, boolean and date cells are not valid samples.

        Inputs: none.
        Outputs: none.
        """
        import datetime
        for bad_value in (None, True, datetime.datetime(2024, 1, 2)):
            with self.subTest(bad_value=bad_value):
                path_str = self.write_excel("data.xlsx", [
                    [["Time", "A", "B"], [0, bad_value, 1], [1, 2, 3]]])
                self.assert_read_error(path_str, "'A'", "row 2")

    @covers("LLFR-00059")
    def test_numeric_text_in_cells_is_accepted(self) -> None:
        """Numbers stored as text in cells are converted.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_excel("data.xlsx", [
            [["Time", "A"], ["0", " 1.5 "], [1, 2]]])
        np.testing.assert_array_equal(
            load_signal_file(path_str).signal_array("A"), [1.5, 2.0])

    @covers("LLFR-00008")
    def test_corrupt_xlsx(self) -> None:
        """A non-zip or truncated .xlsx file gives a read error.

        Inputs: none.
        Outputs: none.
        """
        self.assert_read_error(
            self.write_bytes("text.xlsx", b"Time,A\n0,1\n"), "corrupt")
        self.assert_read_error(self.write_bytes("empty.xlsx", b""))
        good_str = self.write_excel("good.xlsx", [[["Time", "A"], [0, 1]]])
        with open(good_str, "rb") as file:
            content_bytes = file.read()
        self.assert_read_error(
            self.write_bytes("cut.xlsx", content_bytes[:200]))

    @covers("LLFR-00008")
    def test_empty_first_sheet(self) -> None:
        """An empty first sheet can't be read.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_excel("data.xlsx", [[]])
        self.assert_read_error(path_str)


class MatLoadingTest(TemporaryFolderTest):
    """MAT signals and ignored variables (LLFR-00062 to LLFR-00064)."""

    @covers("LLFR-00062", "LLFR-00063", "HLFR-00005")
    def test_vectors_are_signals_others_ignored(self) -> None:
        """Row and column vectors are signals; other variables are not.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_mat("data.mat", {
            "Time": np.array([0.0, 1.0, 2.0]),
            "Row": np.array([[1, 2, 3]], dtype=np.int16),
            "Column": np.array([[4.5], [5.5], [6.5]], dtype=np.float32),
            "Matrix": np.ones((3, 3)),
            "Label": "abc",
            "Settings": {"gain": 2.0},
            "Complex": np.array([1 + 2j, 3, 4]),
            "Empty": np.array([]),
        })
        signal_file = load_signal_file(path_str)
        self.assertEqual(signal_file.signal_name_list,
                         ["Time", "Row", "Column"])
        np.testing.assert_array_equal(signal_file.signal_array("Row"),
                                      [1.0, 2.0, 3.0])
        np.testing.assert_array_equal(signal_file.signal_array("Column"),
                                      [4.5, 5.5, 6.5])
        for name_str in signal_file.signal_name_list:
            self.assertEqual(signal_file.signal_array(name_str).dtype,
                             np.float64)
            self.assertEqual(signal_file.signal_array(name_str).shape, (3,))

    @covers("LLFR-00063", "HLFR-00009")
    def test_ignored_variables_skip_sample_count_check(self) -> None:
        """Ignored variables of other lengths don't fail HLFR-00009.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_mat("data.mat", {
            "Time": np.arange(4.0), "A": np.arange(4.0),
            "Matrix": np.ones((2, 7)), "Note": "hello world"})
        self.assertEqual(load_signal_file(path_str).signal_name_list,
                         ["Time", "A"])

    @covers("LLFR-00062")
    def test_single_sample_signals(self) -> None:
        """A 1x1 numeric variable is a signal with one sample.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_mat("data.mat", {"Time": 0.0, "A": 5})
        signal_file = load_signal_file(path_str)
        np.testing.assert_array_equal(signal_file.signal_array("A"), [5.0])

    @covers("LLFR-00063", "LLFR-00012", "HLFR-00009")
    def test_unequal_lengths_fail_sample_count_check(self) -> None:
        """MAT signals of different lengths fail HLFR-00009.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_mat("data.mat", {
            "Time": np.arange(5.0), "A": np.arange(5.0),
            "B": np.arange(3.0)})
        message_str = self.assert_check_error(path_str,
                                              SAMPLE_COUNT_CHECK_STR)
        self.assertIn("'Time' has 5", message_str)
        self.assertIn("'B' has 3", message_str)
        self.assertNotIn("'A' has", message_str)

    @covers("LLFR-00064", "HLFR-00002")
    def test_v73_file_is_not_supported(self) -> None:
        """A v7.3 MAT file gives a read error saying so.

        Inputs: none.
        Outputs: none.
        """
        # A 128-byte MAT header whose version field is 0x0200 (v7.3).
        header_bytes = (b"MATLAB 7.3 MAT-file".ljust(116, b" ")
                        + bytes(8) + b"\x00\x02IM")
        path_str = self.write_bytes("data.mat", header_bytes + bytes(512))
        with self.assertRaises(NotImplementedError):
            scipy.io.loadmat(path_str)
        self.assert_read_error(path_str, "MATLAB v7.3 files are not "
                                         "supported")

    @covers("LLFR-00008")
    def test_corrupt_mat(self) -> None:
        """Empty, text or truncated MAT files give a read error.

        Inputs: none.
        Outputs: none.
        """
        self.assert_read_error(self.write_bytes("empty.mat", b""))
        self.assert_read_error(
            self.write_bytes("text.mat", b"Time,A\n0,1\n" * 20))
        good_str = self.write_mat("good.mat", {"Time": np.arange(100.0),
                                               "A": np.arange(100.0)})
        with open(good_str, "rb") as file:
            content_bytes = file.read()
        self.assert_read_error(
            self.write_bytes("cut.mat", content_bytes[:300]))

    @covers("LLFR-00008", "LLFR-00065")
    def test_nan_and_infinity_in_mat_signal(self) -> None:
        """NaN or infinite samples in a MAT signal give a read error.

        Inputs: none.
        Outputs: none.
        """
        for bad_f in (np.nan, np.inf):
            with self.subTest(bad_f=bad_f):
                path_str = self.write_mat("data.mat", {
                    "Time": np.arange(3.0),
                    "A": np.array([1.0, bad_f, 3.0])})
                self.assert_read_error(path_str, "'A'", "sample 2")


class ContentCheckTest(TemporaryFolderTest):
    """Content checks (HLFR-00006, HLFR-00008, HLFR-00009, LLFR-00012)."""

    @covers("LLFR-00012", "HLFR-00008", "HLFR-00006", "HLFR-00002")
    def test_no_time_signal(self) -> None:
        """A file without "Time" fails the time signal check.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text("data.csv", "Clock,A\n0,1\n")
        message_str = self.assert_check_error(path_str,
                                              TIME_SIGNAL_CHECK_STR)
        self.assertIn("no time signal named 'Time'", message_str)

    @covers("LLFR-00053", "LLFR-00012", "HLFR-00006")
    def test_time_name_is_case_sensitive(self) -> None:
        """"time" and "TIME" are not the time signal, in every format.

        Inputs: none.
        Outputs: none.
        """
        for name_str in ("time", "TIME", "Time ", " time"):
            with self.subTest(name_str=name_str):
                path_str = self.write_text(
                    "data.csv", f"{name_str},A\n0,1\n")
                if name_str.strip() == "Time":
                    load_signal_file(path_str)
                else:
                    self.assert_check_error(path_str, TIME_SIGNAL_CHECK_STR)
        self.assert_check_error(
            self.write_mat("data.mat", {"time": np.arange(3.0),
                                        "A": np.arange(3.0)}),
            TIME_SIGNAL_CHECK_STR)
        self.assert_check_error(
            self.write_excel("data.xlsx", [[["TIME", "A"], [0, 1]]]),
            TIME_SIGNAL_CHECK_STR)

    @covers("LLFR-00053", "LLFR-00054", "HLFR-00006")
    def test_lowercase_time_is_an_ordinary_signal(self) -> None:
        """With "Time" present, "time" is an ordinary signal.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text("data.csv",
                                   "time,Time,TIME\n5,0,7\n6,1,8\n")
        signal_file = load_signal_file(path_str)
        self.assertEqual(signal_file.signal_name_list,
                         ["time", "Time", "TIME"])
        np.testing.assert_array_equal(signal_file.time_array, [0.0, 1.0])
        np.testing.assert_array_equal(signal_file.signal_array("time"),
                                      [5.0, 6.0])

    @covers("LLFR-00012", "HLFR-00008")
    def test_only_time_signal(self) -> None:
        """A file with only "Time" fails the other signal check.

        Inputs: none.
        Outputs: none.
        """
        message_str = self.assert_check_error(
            self.write_mat("data.mat", {"Time": np.arange(3.0),
                                        "M": np.ones((3, 3))}),
            OTHER_SIGNAL_CHECK_STR)
        self.assertIn("no signal other than 'Time'", message_str)
        self.assert_check_error(
            self.write_excel("data.xlsx", [[["Time"], [0], [1]]]),
            OTHER_SIGNAL_CHECK_STR)

    @covers("LLFR-00012", "HLFR-00008")
    def test_mat_without_signals(self) -> None:
        """A MAT file with no 1-D numeric variable has no time signal.

        Inputs: none.
        Outputs: none.
        """
        self.assert_check_error(
            self.write_mat("data.mat", {"Note": "text"}),
            TIME_SIGNAL_CHECK_STR)

    @covers("LLFR-00012", "HLFR-00008", "HLFR-00009")
    def test_check_order(self) -> None:
        """Time is checked first, then other signals, then counts.

        Inputs: none.
        Outputs: none.
        """
        self.assert_check_error(
            self.write_mat("a.mat", {"A": np.arange(2.0),
                                     "B": np.arange(3.0)}),
            TIME_SIGNAL_CHECK_STR)
        self.assert_check_error(
            self.write_mat("b.mat", {"Time": np.arange(2.0)}),
            OTHER_SIGNAL_CHECK_STR)

    @covers("HLFR-00007", "HLFR-00006", "LLFR-00054")
    def test_signal_file_interface(self) -> None:
        """SignalFile gives names incl. Time, time in seconds, arrays.

        Inputs: none.
        Outputs: none.
        """
        signal_dict = {"A": np.array([1.0, 2.0]),
                       "Time": np.array([0.0, 0.5])}
        signal_file = SignalFile("x.csv", signal_dict)
        self.assertEqual(TIME_SIGNAL_NAME_STR, "Time")
        self.assertEqual(signal_file.signal_name_list, ["A", "Time"])
        np.testing.assert_array_equal(signal_file.time_array, [0.0, 0.5])
        np.testing.assert_array_equal(signal_file.signal_array("Time"),
                                      [0.0, 0.5])
        with self.assertRaises(KeyError):
            signal_file.signal_array("Missing")


class FormatAndAccessTest(TemporaryFolderTest):
    """Unsupported formats and access errors (LLFR-00009, LLFR-00011)."""

    @covers("LLFR-00011", "HLFR-00005", "HLFR-00002")
    def test_unsupported_extensions(self) -> None:
        """.txt, .json, .xls and no extension are not supported.

        Inputs: none.
        Outputs: none.
        """
        for file_name_str in ("data.txt", "data.json", "data.xls",
                              "data", "data.csv.bak"):
            with self.subTest(file_name_str=file_name_str):
                path_str = self.write_text(file_name_str, "Time,A\n0,1\n")
                with self.assertRaises(UnsupportedFormatError) as context:
                    load_signal_file(path_str)
                message_str = str(context.exception)
                self.assertIn("format is not supported", message_str)
                for extension_str in SUPPORTED_EXTENSION_TUPLE:
                    self.assertIn(extension_str, message_str)

    @covers("LLFR-00011")
    def test_unsupported_format_checked_before_access(self) -> None:
        """A missing file with a wrong extension is a format error.

        Inputs: none.
        Outputs: none.
        """
        with self.assertRaises(UnsupportedFormatError):
            load_signal_file(self.path("missing.txt"))

    @covers("HLFR-00005")
    def test_supported_extensions(self) -> None:
        """The supported extensions are exactly CSV, XLSX and MAT.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(SUPPORTED_EXTENSION_TUPLE,
                         (".csv", ".xlsx", ".mat"))

    @covers("LLFR-00009", "HLFR-00002")
    def test_missing_file(self) -> None:
        """A missing file can't be accessed: file not found.

        Inputs: none.
        Outputs: none.
        """
        for file_name_str in ("missing.csv", "missing.xlsx", "missing.mat"):
            with self.subTest(file_name_str=file_name_str):
                with self.assertRaises(FileAccessError) as context:
                    load_signal_file(self.path(file_name_str))
                message_str = str(context.exception)
                self.assertIn("could not be accessed", message_str)
                self.assertIn("file not found", message_str)

    @covers("LLFR-00009")
    def test_directory_path(self) -> None:
        """A folder named like a data file can't be accessed.

        Inputs: none.
        Outputs: none.
        """
        folder_str = self.path("folder.csv")
        os.mkdir(folder_str)
        with self.assertRaises(FileAccessError) as context:
            load_signal_file(folder_str)
        self.assertIn("could not be accessed", str(context.exception))
        self.assertIn("folder", str(context.exception))

    @covers("LLFR-00009")
    @unittest.skipIf(os.name == "nt" or (
        hasattr(os, "geteuid") and os.geteuid() == 0),
        "file permissions don't apply to this user")
    def test_no_read_permission(self) -> None:
        """A file without read permission can't be accessed.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text("data.csv", "Time,A\n0,1\n")
        os.chmod(path_str, 0)
        self.addCleanup(os.chmod, path_str, stat.S_IRUSR | stat.S_IWUSR)
        with self.assertRaises(FileAccessError) as context:
            load_signal_file(path_str)
        self.assertIn("could not be accessed", str(context.exception))
        self.assertIn("permission denied", str(context.exception))

    @covers("LLFR-00009")
    def test_permission_denied_while_reading(self) -> None:
        """A permission error raised while reading is an access error.

        This also runs as root, where real permissions can't be removed.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_text("data.csv", "Time,A\n0,1\n")
        with mock.patch("os.access", return_value=False):
            with self.assertRaises(FileAccessError) as context:
                load_signal_file(path_str)
        self.assertIn("permission denied", str(context.exception))
        with mock.patch("builtins.open",
                        side_effect=PermissionError(13, "denied")):
            with self.assertRaises(FileAccessError) as context:
                load_signal_file(path_str)
        self.assertIn("permission denied", str(context.exception))

    @covers("LLFR-00008", "LLFR-00009", "LLFR-00011", "LLFR-00012")
    def test_all_errors_are_file_open_errors(self) -> None:
        """Every error class is a FileOpenError, so one except is enough.

        Inputs: none.
        Outputs: none.
        """
        for error_class in (FileAccessError, FileReadError,
                            UnsupportedFormatError, ContentCheckError):
            self.assertTrue(issubclass(error_class, FileOpenError))
        self.assertEqual(len({TIME_SIGNAL_CHECK_STR, OTHER_SIGNAL_CHECK_STR,
                              SAMPLE_COUNT_CHECK_STR}), 3)


if __name__ == "__main__":
    unittest.main()
