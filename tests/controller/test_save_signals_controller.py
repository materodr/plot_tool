"""Tests for the Save signals controller with a fake view (issue #153).

The flow runs with a real SignalFile, a real SyntheticSignalStore and
the real writer; the fake view answers the dialog and the question and
records the boxes. Files are written to a temporary folder and read back
with the app's loader. No Qt is needed.
"""

import os
import tempfile
import unittest

import numpy as np

from tests.support import covers

from controller.save_signals_controller import SaveSignalsController
from model import synthetic_operations as operations
from model.file_loader import load_signal_file
from model.file_writer import (
    CSV_FORMAT_STR, EXCEL_FORMAT_STR, HDF5_FORMAT_STR, MAT_FORMAT_STR)
from model.signal_file import SignalFile
from model.synthetic_signals import SyntheticSignal, SyntheticSignalStore
from view.file_writing import write_file_safely


def read_bytes(path_str: str) -> bytes:
    """Return the content of a file.

    Inputs:
        path_str: the file.
    Outputs: its bytes.
    """
    with open(path_str, "rb") as input_file:
        return input_file.read()


class FakeSaveSignalsView:
    """The view facade of the Save signals flow, recording every call.

    Attributes:
        handler: the function of the Save signals button.
        enabled_list: values given to set_save_signals_button_enabled.
        dialog_answer_list: (path, format, confirmed_b) tuples returned,
            in order, by the dialog; ("", ...) is a cancel.
        dialog_call_list: (folder, name, format) of every dialog.
        replace_answer_b: answer of ask_replace_existing_file.
        replace_question_list: paths asked about.
        error_list: texts of the error boxes.
        changed_names_list: texts of the changed names boxes.
        write_failure_str: when not "", save_signal_bytes fails with it.
        written_path_list: paths given to save_signal_bytes.
        finished_count_i: times the button returned to normal.
    """

    def __init__(self) -> None:
        """Start with no answers and no boxes.

        Inputs: none.
        Outputs: none.
        """
        self.handler = None
        self.enabled_list = []
        self.dialog_answer_list = []
        self.dialog_call_list = []
        self.replace_answer_b = True
        self.replace_question_list = []
        self.error_list = []
        self.changed_names_list = []
        self.write_failure_str = ""
        self.written_path_list = []
        self.finished_count_i = 0

    def set_save_signals_handler(self, handler) -> None:
        """Record the handler of the button.

        Inputs:
            handler: the function without arguments.
        Outputs: none.
        """
        self.handler = handler

    def set_save_signals_button_enabled(self, enabled_b: bool) -> None:
        """Record whether the button is enabled.

        Inputs:
            enabled_b: True when enabled.
        Outputs: none.
        """
        self.enabled_list.append(bool(enabled_b))

    def ask_signals_save_path(self, start_folder_str: str,
                              file_name_str: str, format_str: str) -> tuple:
        """Answer the save dialog with the next prepared answer.

        Inputs:
            start_folder_str: the folder the dialog would show.
            file_name_str: the proposed name.
            format_str: the format chosen at first.
        Outputs: the next answer, a cancel when none is left.
        """
        self.dialog_call_list.append((start_folder_str, file_name_str,
                                      format_str))
        if not self.dialog_answer_list:
            return ("", format_str, False)
        return self.dialog_answer_list.pop(0)

    def ask_replace_existing_file(self, path_str: str) -> bool:
        """Answer the replace question.

        Inputs:
            path_str: the existing file.
        Outputs: replace_answer_b.
        """
        self.replace_question_list.append(path_str)
        return self.replace_answer_b

    def save_signal_bytes(self, path_str: str, content_bytes: bytes) -> tuple:
        """Write the file safely, or fail with write_failure_str.

        Inputs:
            path_str: the target.
            content_bytes: the content.
        Outputs: (saved_b, reason_str).
        """
        self.written_path_list.append(path_str)
        if self.write_failure_str:
            return (False, self.write_failure_str)
        return write_file_safely(path_str, content_bytes)

    def show_signals_save_error(self, message_str: str) -> None:
        """Record an error box.

        Inputs:
            message_str: its text.
        Outputs: none.
        """
        self.error_list.append(message_str)

    def show_changed_signal_names(self, text_str: str) -> None:
        """Record the changed names box.

        Inputs:
            text_str: its text.
        Outputs: none.
        """
        self.changed_names_list.append(text_str)

    def finish_save_signals_button(self) -> None:
        """Count the returns of the button to normal.

        Inputs: none.
        Outputs: none.
        """
        self.finished_count_i += 1


class FakeFileController:
    """Holds the file opened listeners, like the FileController.

    Attributes:
        listener_list: the registered listeners.
    """

    def __init__(self) -> None:
        """Start with no listener.

        Inputs: none.
        Outputs: none.
        """
        self.listener_list = []

    def add_file_opened_listener(self, listener) -> None:
        """Register a listener.

        Inputs:
            listener: function (signal_file, replaced_b).
        Outputs: none.
        """
        self.listener_list.append(listener)

    def open(self, signal_file) -> None:
        """Tell the listeners that a file was opened.

        Inputs:
            signal_file: the SignalFile.
        Outputs: none.
        """
        for listener in self.listener_list:
            listener(signal_file, False)


class FakeSyntheticController:
    """Holds the signal file and the store, like the SyntheticController.

    Attributes:
        signal_file: the open SignalFile or None.
        store: a SyntheticSignalStore.
    """

    def __init__(self) -> None:
        """Start with no file and an empty store.

        Inputs: none.
        Outputs: none.
        """
        self.signal_file = None
        self.store = SyntheticSignalStore()


class SaveSignalsFlowTest(unittest.TestCase):
    """The Save signals flow, from the click to the file."""

    def setUp(self) -> None:
        """Open a data file run1.csv with a synthetic and an FFT signal.

        Inputs: none.
        Outputs: none.
        """
        self.folder = tempfile.TemporaryDirectory()
        self.folder_str = self.folder.name
        self.data_path_str = os.path.join(self.folder_str, "run1.csv")
        with open(self.data_path_str, "w", encoding="utf-8") as data_file:
            data_file.write("time,speed\n0,1.5\n0.5,2.5\n1,3.5\n")
        self.data_bytes = read_bytes(self.data_path_str)
        self.view = FakeSaveSignalsView()
        self.file_controller = FakeFileController()
        self.synthetic_controller = FakeSyntheticController()
        self.controller = SaveSignalsController(
            self.view, self.file_controller, self.synthetic_controller)

    def tearDown(self) -> None:
        """Remove the temporary folder.

        Inputs: none.
        Outputs: none.
        """
        self.folder.cleanup()

    def open_data_file(self) -> SignalFile:
        """Open the data file and add synthetic signals to the store.

        Inputs: none.
        Outputs: the SignalFile.
        """
        signal_file = load_signal_file(self.data_path_str)
        self.synthetic_controller.signal_file = signal_file
        store = self.synthetic_controller.store
        store.signal_list.append(SyntheticSignal(
            "speed.x2", operations.MULTIPLY_STR, ["speed"], 2.0,
            np.array([3.0, 5.0, 7.0])))
        store.signal_list.append(SyntheticSignal(
            "fft_speed", operations.FFT_STR, ["speed"], (0.0, 1.0),
            np.array([1.0, 2.0]), np.array([0.0, 1.0])))
        store.signal_list.append(SyntheticSignal(
            "int_speed", operations.INTEGRAL_STR, ["speed"], None,
            np.array([0.0, 1.0, 2.5])))
        self.file_controller.open(signal_file)
        return signal_file

    def target(self, name_str: str) -> str:
        """Return a path in the temporary folder.

        Inputs:
            name_str: the file name.
        Outputs: the path.
        """
        return os.path.join(self.folder_str, name_str)

    @covers("LLFR-00395", "LLFR-00531")
    def test_disabled_and_inert_without_a_data_file(self) -> None:
        """The button is disabled at first and does nothing; it is
        enabled once a file is open.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.view.enabled_list, [False])
        self.view.handler()
        self.assertEqual(self.view.dialog_call_list, [])
        self.assertEqual(self.view.error_list, [])
        self.assertEqual(self.view.finished_count_i, 1)
        self.open_data_file()
        self.assertEqual(self.view.enabled_list, [False, True])

    @covers("LLFR-01181", "LLFR-01182", "LLFR-00532", "LLFR-00398",
            "LLFR-00399")
    def test_dialog_folder_sequence(self) -> None:
        """The Open file folder until a signals file is saved, then the
        folder of the last one saved; the proposed name stays that of
        the data file; cancels and failures change nothing.

        Inputs: none.
        Outputs: none.
        """
        self.open_data_file()
        # LLFR-01181: the folder the Open file dialog would show (the
        # last data file opened), not the folder of the proposed file.
        self.file_controller.dialog_folder_str = "/data/last_opened"
        first_folder_str = os.path.join(self.folder_str, "first")
        second_folder_str = os.path.join(self.folder_str, "second")
        os.mkdir(first_folder_str)
        os.mkdir(second_folder_str)
        self.view.dialog_answer_list = [
            ("", CSV_FORMAT_STR, False),
            (os.path.join(first_folder_str, "fail.csv"), CSV_FORMAT_STR,
             False)]
        self.view.write_failure_str = "full"
        self.view.handler()
        self.view.handler()
        self.view.write_failure_str = ""
        # LLFR-01182: a successful save moves the folder.
        self.view.dialog_answer_list = [
            (os.path.join(first_folder_str, "out"), CSV_FORMAT_STR, False),
            ("", CSV_FORMAT_STR, False),
            (os.path.join(second_folder_str, "out.csv"), CSV_FORMAT_STR,
             False)]
        self.view.handler()
        self.view.handler()
        self.file_controller.dialog_folder_str = "/data/other"
        self.view.handler()
        self.view.handler()
        self.assertTrue(os.path.exists(os.path.join(first_folder_str,
                                                    "out.csv")))
        self.assertTrue(os.path.exists(os.path.join(second_folder_str,
                                                    "out.csv")))
        self.assertEqual(
            [call_tuple[0] for call_tuple in self.view.dialog_call_list],
            ["/data/last_opened", "/data/last_opened", "/data/last_opened",
             os.path.abspath(first_folder_str),
             os.path.abspath(first_folder_str),
             os.path.abspath(second_folder_str)])
        # LLFR-00532: the proposed name is always the data file's.
        self.assertEqual(
            {call_tuple[1] for call_tuple in self.view.dialog_call_list},
            {"run1_signals.csv"})

    @covers("LLFR-00396", "LLFR-00532")
    def test_dialog_defaults(self) -> None:
        """The dialog opens in the data file's folder, with
        run1_signals.csv and the CSV format.

        Inputs: none.
        Outputs: none.
        """
        self.open_data_file()
        self.view.handler()
        self.assertEqual(self.view.dialog_call_list, [
            (os.path.abspath(self.folder_str), "run1_signals.csv",
             CSV_FORMAT_STR)])

    @covers("LLFR-00396", "LLFR-00401", "LLFR-00402", "LLFR-00407",
            "LLFR-00404", "LLFR-00253", "LLFR-00533", "LLFR-00558")
    def test_saved_file_opens_with_the_same_signals(self) -> None:
        """A name without extension gets ".csv"; the file holds every
        signal but the FFT, in list order, with "time" written as Time,
        and the changed name is listed; the data file is unchanged.

        Inputs: none.
        Outputs: none.
        """
        signal_file = self.open_data_file()
        self.view.dialog_answer_list = [
            (self.target("out"), CSV_FORMAT_STR, False)]
        self.view.handler()
        self.assertEqual(self.view.error_list, [])
        saved_file = load_signal_file(self.target("out.csv"))
        self.assertEqual(saved_file.signal_name_list,
                         ["Time", "speed", "speed.x2", "int_speed"])
        self.assertEqual(saved_file.time_signal_name_str, "Time")
        np.testing.assert_array_equal(saved_file.time_array,
                                      signal_file.time_array)
        np.testing.assert_array_equal(saved_file.signal_array("int_speed"),
                                      [0.0, 1.0, 2.5])
        self.assertEqual(self.view.changed_names_list,
                         ["time → Time"])
        self.assertEqual(read_bytes(self.data_path_str),
                         self.data_bytes)
        self.assertEqual(self.view.finished_count_i, 1)

    @covers("LLFR-00403", "LLFR-00404", "LLFR-00543", "LLFR-00558")
    def test_mat_lists_every_changed_name(self) -> None:
        """MAT: "speed.x2" and the time name change and are listed.

        Inputs: none.
        Outputs: none.
        """
        self.open_data_file()
        self.view.dialog_answer_list = [
            (self.target("out.mat"), MAT_FORMAT_STR, False)]
        self.view.handler()
        self.assertEqual(self.view.changed_names_list, [
            "1. time → Time\n\n2. speed.x2 → speed_x2"])
        saved_file = load_signal_file(self.target("out.mat"))
        self.assertEqual(saved_file.signal_name_list,
                         ["Time", "speed", "speed_x2", "int_speed"])

    @covers("LLFR-00404", "LLFR-00555")
    def test_no_box_when_no_name_changed(self) -> None:
        """With a time signal named Time and valid names, no box.

        Inputs: none.
        Outputs: none.
        """
        with open(self.data_path_str, "w", encoding="utf-8") as data_file:
            data_file.write("Time,speed\n0,1\n1,2\n2,3\n")
        signal_file = load_signal_file(self.data_path_str)
        self.synthetic_controller.signal_file = signal_file
        self.file_controller.open(signal_file)
        self.view.dialog_answer_list = [
            (self.target("ok.xlsx"), EXCEL_FORMAT_STR, False)]
        self.view.handler()
        self.assertEqual(self.view.error_list, [])
        self.assertEqual(self.view.changed_names_list, [])
        self.assertTrue(os.path.exists(self.target("ok.xlsx")))

    @covers("LLFR-00396", "LLFR-00533")
    def test_extension_of_another_format_gets_the_chosen_one(self) -> None:
        """"out.csv" saved as Excel becomes "out.csv.xlsx".

        Inputs: none.
        Outputs: none.
        """
        self.open_data_file()
        self.view.dialog_answer_list = [
            (self.target("out.csv"), EXCEL_FORMAT_STR, False)]
        self.view.handler()
        self.assertEqual(self.view.written_path_list,
                         [self.target("out.csv.xlsx")])
        self.assertFalse(os.path.exists(self.target("out.csv")))

    @covers("LLFR-00398", "LLFR-00539")
    def test_cancelled_dialog(self) -> None:
        """A cancelled dialog saves nothing and shows nothing.

        Inputs: none.
        Outputs: none.
        """
        self.open_data_file()
        before_list = sorted(os.listdir(self.folder_str))
        self.view.handler()
        self.assertEqual(sorted(os.listdir(self.folder_str)), before_list)
        self.assertEqual(self.view.written_path_list, [])
        self.assertEqual(self.view.error_list, [])
        self.assertEqual(self.view.changed_names_list, [])
        self.assertEqual(self.view.replace_question_list, [])
        self.assertEqual(self.view.finished_count_i, 1)

    @covers("LLFR-00397", "LLFR-00398", "LLFR-00536", "LLFR-00537",
            "LLFR-00539")
    def test_replace_question(self) -> None:
        """An existing file is replaced only after "Yes"; "No" saves
        nothing and shows nothing.

        Inputs: none.
        Outputs: none.
        """
        self.open_data_file()
        existing_str = self.target("old.csv")
        with open(existing_str, "w", encoding="utf-8") as existing_file:
            existing_file.write("keep")
        self.view.replace_answer_b = False
        self.view.dialog_answer_list = [
            (existing_str, CSV_FORMAT_STR, False)]
        self.view.handler()
        self.assertEqual(self.view.replace_question_list, [existing_str])
        self.assertEqual(read_bytes(existing_str), b"keep")
        self.assertEqual(self.view.error_list, [])
        self.assertEqual(self.view.changed_names_list, [])
        self.view.replace_answer_b = True
        self.view.dialog_answer_list = [
            (existing_str, CSV_FORMAT_STR, False)]
        self.view.handler()
        self.assertEqual(len(self.view.replace_question_list), 2)
        self.assertIn("speed", load_signal_file(
            existing_str).signal_name_list)

    @covers("LLFR-00397", "LLFR-00536", "LLFR-00538")
    def test_no_second_question_after_the_system_dialog(self) -> None:
        """When the system dialog asked about this path, the app does not
        ask again; when the app added the extension, it asks.

        Inputs: none.
        Outputs: none.
        """
        self.open_data_file()
        for name_str in ("old.csv", "new.csv"):
            with open(self.target(name_str), "w") as existing_file:
                existing_file.write("x")
        self.view.dialog_answer_list = [
            (self.target("old.csv"), CSV_FORMAT_STR, True)]
        self.view.handler()
        self.assertEqual(self.view.replace_question_list, [])
        self.assertIn("speed", load_signal_file(
            self.target("old.csv")).signal_name_list)
        # The dialog asked about "new", not about "new.csv".
        self.view.dialog_answer_list = [
            (self.target("new"), CSV_FORMAT_STR, True)]
        self.view.handler()
        self.assertEqual(self.view.replace_question_list,
                         [self.target("new.csv")])

    @covers("LLFR-00397", "LLFR-00253", "LLFR-00534", "LLFR-00535")
    def test_opened_data_file_is_refused(self) -> None:
        """Choosing the opened data file, even as "run1" or through a
        link, writes nothing, the app never asks to replace it, and the
        error box is shown.

        Inputs: none.
        Outputs: none.
        """
        self.open_data_file()
        link_str = self.target("link.csv")
        os.symlink(self.data_path_str, link_str)
        for answer_str in (self.data_path_str, self.target("run1"),
                           link_str):
            with self.subTest(answer=answer_str):
                self.view.error_list = []
                self.view.dialog_answer_list = [
                    (answer_str, CSV_FORMAT_STR, False)]
                self.view.handler()
                self.assertEqual(len(self.view.error_list), 1)
                self.assertIn("cannot be replaced", self.view.error_list[0])
                self.assertIn("run1.csv", self.view.error_list[0])
        self.assertEqual(self.view.replace_question_list, [])
        self.assertEqual(self.view.written_path_list, [])
        self.assertEqual(read_bytes(self.data_path_str),
                         self.data_bytes)

    @covers("LLFR-00397", "LLFR-00253", "LLFR-00534", "LLFR-00535",
            "LLFR-00538")
    def test_data_file_after_the_system_question(self) -> None:
        """When the system dialog (macOS) already asked about the opened
        data file, the app does not ask again, saves nothing and shows
        the error box.

        Inputs: none.
        Outputs: none.
        """
        self.open_data_file()
        self.view.dialog_answer_list = [
            (self.data_path_str, CSV_FORMAT_STR, True)]
        self.view.handler()
        self.assertEqual(self.view.replace_question_list, [])
        self.assertEqual(self.view.written_path_list, [])
        self.assertEqual(len(self.view.error_list), 1)
        self.assertIn("cannot be replaced", self.view.error_list[0])
        self.assertEqual(read_bytes(self.data_path_str), self.data_bytes)

    @covers("LLFR-00399")
    def test_write_failure_box(self) -> None:
        """A failed write shows an error box saying that the file could
        not be saved, with the reason, and no changed names box.

        Inputs: none.
        Outputs: none.
        """
        self.open_data_file()
        self.view.write_failure_str = "Disk full"
        self.view.dialog_answer_list = [
            (self.target("out.csv"), CSV_FORMAT_STR, False)]
        self.view.handler()
        self.assertEqual(len(self.view.error_list), 1)
        self.assertIn("could not be saved", self.view.error_list[0])
        self.assertIn("Disk full", self.view.error_list[0])
        self.assertEqual(self.view.changed_names_list, [])
        self.assertEqual(self.view.finished_count_i, 1)

    @covers("LLFR-00399")
    def test_missing_folder_is_a_write_failure(self) -> None:
        """A folder that does not exist gives the error box (real safe
        write).

        Inputs: none.
        Outputs: none.
        """
        self.open_data_file()
        self.view.dialog_answer_list = [
            (self.target("missing/out.csv"), CSV_FORMAT_STR, False)]
        self.view.handler()
        self.assertEqual(len(self.view.error_list), 1)
        self.assertIn("could not be saved", self.view.error_list[0])

    @covers("LLFR-00400", "LLFR-00540")
    def test_too_many_samples_for_excel(self) -> None:
        """More than 1048575 samples: no file and an error box.

        Inputs: none.
        Outputs: none.
        """
        sample_count_i = 1048576
        signal_file = SignalFile(self.data_path_str, {
            "Time": np.arange(sample_count_i, dtype=np.float64),
            "a": np.zeros(sample_count_i)})
        self.synthetic_controller.signal_file = signal_file
        self.file_controller.open(signal_file)
        self.view.dialog_answer_list = [
            (self.target("big.xlsx"), EXCEL_FORMAT_STR, False)]
        self.view.handler()
        self.assertEqual(len(self.view.error_list), 1)
        self.assertIn("too many samples or are too many for an Excel file",
                      self.view.error_list[0])
        self.assertEqual(self.view.written_path_list, [])
        self.assertFalse(os.path.exists(self.target("big.xlsx")))

    @covers("LLFR-00408", "LLFR-00559")
    def test_non_finite_values_refused(self) -> None:
        """A synthetic signal with inf or NaN values makes every format
        refuse: no file, one error box naming the signal.

        Inputs: none.
        Outputs: none.
        """
        self.open_data_file()
        self.synthetic_controller.store.signal_list.append(SyntheticSignal(
            "mul_1e308_speed", operations.MULTIPLY_STR, ["speed"], 1e308,
            np.array([np.inf, np.nan, 1.0])))
        for format_str in (CSV_FORMAT_STR, EXCEL_FORMAT_STR,
                           MAT_FORMAT_STR, HDF5_FORMAT_STR):
            with self.subTest(format=format_str):
                self.view.error_list = []
                target_str = self.target(f"bad_{format_str}")
                self.view.dialog_answer_list = [
                    (target_str, format_str, False)]
                self.view.handler()
                self.assertEqual(len(self.view.error_list), 1)
                self.assertIn("could not be saved", self.view.error_list[0])
                self.assertIn("'mul_1e308_speed'", self.view.error_list[0])
                self.assertNotIn("'speed'", self.view.error_list[0])
        self.assertEqual(self.view.written_path_list, [])
        self.assertEqual(self.view.changed_names_list, [])
        self.assertEqual(sorted(os.listdir(self.folder_str)), ["run1.csv"])

    @covers("LLFR-00405", "LLFR-00401", "LLFR-00541")
    def test_nothing_changes_in_the_app(self) -> None:
        """The signal list, the names, the store and the data file stay
        as they were; the FFT signal is left out without a message.

        Inputs: none.
        Outputs: none.
        """
        signal_file = self.open_data_file()
        store = self.synthetic_controller.store
        name_before_list = list(signal_file.signal_name_list)
        store_before_list = store.names()
        time_name_before_str = signal_file.time_signal_name_str
        self.view.dialog_answer_list = [
            (self.target("out.mat"), MAT_FORMAT_STR, False)]
        self.view.handler()
        self.assertEqual(signal_file.signal_name_list, name_before_list)
        self.assertEqual(store.names(), store_before_list)
        self.assertEqual(signal_file.time_signal_name_str,
                         time_name_before_str)
        self.assertIs(self.synthetic_controller.signal_file, signal_file)
        self.assertEqual(read_bytes(self.data_path_str),
                         self.data_bytes)
        self.assertEqual(self.view.error_list, [])
        for text_str in self.view.changed_names_list:
            self.assertNotIn("fft", text_str)
        self.assertNotIn("fft_speed", load_signal_file(
            self.target("out.mat")).signal_name_list)


if __name__ == "__main__":
    unittest.main()
