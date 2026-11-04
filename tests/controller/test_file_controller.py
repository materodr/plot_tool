"""Tests for the open and close flows of FileController (no Qt needed).

Several data files can be open at once (HLFR-00113); opening adds a
file with the next number (HLFR-00114, HLFR-00117), every signal is
named with the prefix of its file (HLFR-00115), and a file can be
closed, or all of them (HLFR-00118, HLFR-00119).
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

from tests.support import REPOSITORY_ROOT_STR, covers

from controller.file_controller import (
    ALREADY_OPEN_REASON_STR, LIMIT_REASON_STR, OPEN_FILES_LIMIT_MESSAGE_STR,
    REPOSITORY_FOLDER_STR, TIME_SIGNAL_PROMPT_STR, FileController,
    first_start_folder_str)
from model.data_files import MAXIMUM_DATA_FILES_I
from model.errors import (
    SAMPLE_COUNT_CHECK_STR, SIGNAL_COUNT_CHECK_STR, ContentCheckError,
    FileAccessError, FileReadError, UnsupportedFormatError)
from model.file_loader import load_signal_file
from model.signal_file import SignalFile

# LLFR-00418: the calls around every read of a selected file.
LOADING_CALL_LIST = ["show_loading_indication", "hide_loading_indication"]

FIRST_PATH_STR = "/data/first.csv"
SECOND_PATH_STR = "/data/second.csv"


def build_signal_file(path_str: str, name_list: list) -> SignalFile:
    """Build a SignalFile with a Time signal and the given other names.

    Inputs:
        path_str: the path stored in the SignalFile.
        name_list: names of the signals after Time.
    Outputs: a SignalFile with three samples per signal.
    """
    signal_dict = {"Time": np.array([0.0, 1.0, 2.0])}
    for index_i, name_str in enumerate(name_list):
        signal_dict[name_str] = np.array([1.0, 2.0, 3.0]) * (index_i + 1)
    return SignalFile(path_str, signal_dict)


def build_no_time_file(path_str: str) -> SignalFile:
    """Build a SignalFile with no signal named "Time".

    Inputs:
        path_str: the path stored in the SignalFile.
    Outputs: a SignalFile with "Down" (decreasing), "t_s" (increasing)
        and "Flat" (not always increasing), three samples each.
    """
    return SignalFile(path_str, {
        "Down": np.array([3.0, 2.0, 1.0]),
        "t_s": np.array([0.0, 0.5, 1.5]),
        "Flat": np.array([1.0, 1.0, 2.0])})


class FakeView:
    """Stand-in for MainWindow that records every facade call.

    Inputs:
        path_list: answers of successive ask_open_file_path calls: a
            path, "" (the dialog was cancelled) or a list of paths.
        time_answer_list: lists of names "confirmed" by successive
            ask_time_signal_name calls; each name is checked with the
            window's check function like the real window does, and the
            first accepted one is returned; an empty list cancels.
    """

    def __init__(self, path_list: list, time_answer_list=None) -> None:
        """Store the scripted answers and start with no calls.

        Inputs:
            path_list: the scripted dialog results.
            time_answer_list: the scripted time signal window answers.
        Outputs: none.
        """
        self.path_list = list(path_list)
        self.time_answer_list = list(time_answer_list or [])
        self.time_window_list = []
        self.time_window_file_name_list = []
        self.time_reason_list = []
        self.call_list = []
        self.error_message_list = []
        self.refused_message_list = []
        self.limit_message_list = []
        self.start_folder_list = []
        self.loading_shown_b = False

    def ask_open_file_path(self, start_folder_str: str):
        """Record the call and return the next scripted answer.

        Inputs:
            start_folder_str: the folder the dialog would show.
        Outputs: the next answer of path_list.
        """
        self.call_list.append("ask_open_file_path")
        self.start_folder_list.append(start_folder_str)
        return self.path_list.pop(0)

    def show_file_open_error(self, message_str: str) -> None:
        """Record the error message.

        Inputs:
            message_str: the message of the File Open Error box.
        Outputs: none.
        """
        self.call_list.append("show_file_open_error")
        self.error_message_list.append(message_str)

    def show_refused_files_notification(self, message_str: str) -> None:
        """Record the box of the refused files.

        Inputs:
            message_str: one line per refused file.
        Outputs: none.
        """
        self.call_list.append("show_refused_files_notification")
        self.refused_message_list.append(message_str)

    def show_open_files_limit_notification(self, message_str: str) -> None:
        """Record the box of an Open file click with 10 files open.

        Inputs:
            message_str: the sentence of the box.
        Outputs: none.
        """
        self.call_list.append("show_open_files_limit_notification")
        self.limit_message_list.append(message_str)

    def ask_time_signal_name(self, prompt_str: str, name_list: list,
                             search_function, no_match_text_str: str,
                             check_function, file_name_str: str = ""):
        """Record the window and return the first accepted answer.

        Inputs:
            prompt_str: the text of the window.
            name_list: the names listed.
            search_function: text -> matching names.
            no_match_text_str: the text shown when nothing matches.
            check_function: name -> reason ("" when accepted).
            file_name_str: the name of the file the window is for
                (LLFR-00957).
        Outputs: the first scripted name that check_function accepts,
            or None (cancel) when none is.
        """
        self.call_list.append("ask_time_signal_name")
        self.time_window_file_name_list.append(file_name_str)
        self.time_window_list.append(
            (prompt_str, list(name_list), search_function,
             no_match_text_str))
        for name_str in self.time_answer_list.pop(0):
            reason_str = check_function(name_str)
            if not reason_str:
                return name_str
            self.time_reason_list.append(reason_str)
        return None

    def finish_open_file_button(self) -> None:
        """Record that the Open file button was finished.

        Inputs: none.
        Outputs: none.
        """
        self.call_list.append("finish_open_file_button")

    def show_loading_indication(self) -> None:
        """Record that the busy pointer and the loading title were shown.

        Inputs: none.
        Outputs: none.
        """
        self.call_list.append("show_loading_indication")
        self.loading_shown_b = True

    def hide_loading_indication(self) -> None:
        """Record that the loading indication was removed.

        Inputs: none.
        Outputs: none.
        """
        self.call_list.append("hide_loading_indication")
        self.loading_shown_b = False


class ScriptedLoader:
    """Load function that returns or raises scripted results.

    Inputs:
        result_dict: path -> SignalFile to return or exception to raise.
    """

    def __init__(self, result_dict: dict) -> None:
        """Store the results and start with no loaded paths.

        Inputs:
            result_dict: path -> SignalFile or exception.
        Outputs: none.
        """
        self.result_dict = result_dict
        self.loaded_path_list = []

    def __call__(self, path_str: str) -> SignalFile:
        """Return or raise the scripted result for path_str.

        Inputs:
            path_str: the path to open.
        Outputs: the scripted SignalFile; raises the scripted exception.
        """
        self.loaded_path_list.append(path_str)
        result = self.result_dict[path_str]
        if isinstance(result, Exception):
            raise result
        return result


# LLFR-00008, LLFR-00009, LLFR-00011, LLFR-00012: one error per kind.
ERROR_CASE_LIST = [
    ("LLFR-00008", FileReadError("The file 'x.csv' could not be read.")),
    ("LLFR-00009",
     FileAccessError("The file 'x.csv' could not be accessed.")),
    ("LLFR-00011",
     UnsupportedFormatError("The file format is not supported.")),
    ("LLFR-00012", ContentCheckError("Fewer than two signals.",
                                     SIGNAL_COUNT_CHECK_STR)),
    ("LLFR-00012", ContentCheckError("Different sample counts.",
                                     SAMPLE_COUNT_CHECK_STR)),
]


class FileControllerTestCase(unittest.TestCase):
    """Shared helpers: a controller with a scripted loader."""

    def setUp(self) -> None:
        """Prepare two valid files and a listener call recorder.

        Inputs: none.
        Outputs: none.
        """
        self.first_file = build_signal_file(FIRST_PATH_STR, ["a", "b"])
        self.second_file = build_signal_file(SECOND_PATH_STR, ["c"])
        self.listener_call_list = []
        self.closed_call_list = []

    def record_listener(self, data_files, data_file) -> None:
        """Record one call of a file-opened listener.

        Inputs:
            data_files: the DataFileSet of the open files.
            data_file: the DataFile just added.
        Outputs: none.
        """
        self.listener_call_list.append(
            (data_file.number_i, data_file.signal_file,
             list(data_files.signal_name_list)))

    def record_closed(self, data_files, closed_file_list: list) -> None:
        """Record one call of a files-closed listener.

        Inputs:
            data_files: the DataFileSet of the files left.
            closed_file_list: the closed DataFile objects.
        Outputs: none.
        """
        self.closed_call_list.append(
            ([data_file.number_i for data_file in closed_file_list],
             [data_file.number_i for data_file in data_files.file_list]))

    def build_controller(self, view, result_dict: dict) -> FileController:
        """Build a FileController with a scripted loader and listeners.

        Inputs:
            view: the fake view.
            result_dict: path -> SignalFile or exception.
        Outputs: the FileController.
        """
        self.loader = ScriptedLoader(result_dict)
        controller = FileController(view, self.loader, "/start")
        controller.add_file_opened_listener(self.record_listener)
        controller.add_files_closed_listener(self.record_closed)
        return controller

    def open_first_file(self, view, result_dict: dict) -> FileController:
        """Build a controller and open FIRST_PATH_STR with it.

        Inputs:
            view: the fake view; its first path must be FIRST_PATH_STR.
            result_dict: path -> SignalFile or exception.
        Outputs: the FileController with the first file open; the
            recorded calls are cleared.
        """
        result_dict = dict(result_dict)
        result_dict[FIRST_PATH_STR] = self.first_file
        controller = self.build_controller(view, result_dict)
        controller.open_file_requested()
        self.assertEqual(self.numbers(controller), [1])
        view.call_list.clear()
        self.listener_call_list.clear()
        return controller

    def numbers(self, controller) -> list:
        """Return the numbers of the open data files.

        Inputs:
            controller: the FileController.
        Outputs: the numbers, in order.
        """
        return [data_file.number_i
                for data_file in controller.data_files.file_list]

    def assert_first_file_kept(self, controller, view) -> None:
        """Check that only the first file is open, unchanged.

        Inputs:
            controller: the FileController.
            view: the fake view.
        Outputs: none.
        """
        # LLFR-00010: no change for the file that did not open; no
        # listener ran, so the plots, the signal list, the synthetic
        # signals and the history are unchanged too.
        self.assertEqual(self.numbers(controller), [1])
        self.assertIs(controller.data_files.file_list[0].signal_file,
                      self.first_file)
        self.assertEqual(self.listener_call_list, [])
        self.assertEqual(controller.dialog_folder_str, "/data")
        self.assertFalse(view.loading_shown_b)
        self.assertEqual(controller.data_files.next_number_i, 2)


class OpenFileTest(FileControllerTestCase):
    """Opening data files (HLFR-00004, HLFR-00113, HLFR-00117)."""

    @covers("LLFR-00005", "LLFR-00006", "LLFR-00003", "LLFR-00328",
            "LLFR-00418", "LLFR-00900", "LLFR-00905", "LLFR-00906",
            "LLFR-00920", "HLFR-00114", "HLFR-00115")
    def test_first_file_is_opened_as_file_1(self) -> None:
        """The first valid file opens as file 1, with prefixed names.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR])
        controller = self.build_controller(
            view, {FIRST_PATH_STR: self.first_file})
        self.assertIsNone(controller.current_file)
        controller.open_file_requested()
        self.assertEqual(self.loader.loaded_path_list, [FIRST_PATH_STR])
        self.assertIs(controller.current_file, controller.data_files)
        self.assertEqual(self.numbers(controller), [1])
        self.assertEqual(controller.data_files.signal_name_list,
                         ["file1_Time", "file1_a", "file1_b"])
        self.assertEqual(view.call_list, [
            "ask_open_file_path", *LOADING_CALL_LIST,
            "finish_open_file_button"])
        self.assertEqual(self.listener_call_list, [
            (1, self.first_file, ["file1_Time", "file1_a", "file1_b"])])

    @covers("LLFR-00922", "LLFR-00920", "LLFR-00921", "LLFR-00900",
            "LLFR-00901", "LLFR-00895", "HLFR-00117", "HLFR-00113")
    def test_second_file_is_added_with_no_question(self) -> None:
        """A second file is read at once and added as file 2.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR, SECOND_PATH_STR])
        controller = self.open_first_file(
            view, {SECOND_PATH_STR: self.second_file})
        first_data_file = controller.data_files.file_list[0]
        controller.open_file_requested()
        self.assertEqual(view.call_list, [
            "ask_open_file_path", *LOADING_CALL_LIST,
            "finish_open_file_button"])
        self.assertEqual(self.numbers(controller), [1, 2])
        self.assertIs(controller.data_files.file_list[0], first_data_file)
        self.assertEqual(controller.data_files.signal_name_list, [
            "file1_Time", "file1_a", "file1_b", "file2_Time", "file2_c"])
        self.assertEqual(self.listener_call_list[0][:2],
                         (2, self.second_file))

    @covers("LLFR-00007", "LLFR-00003")
    def test_cancel_changes_nothing(self) -> None:
        """Cancelling the dialog keeps the open files and reads nothing.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR, "", []])
        controller = self.open_first_file(view, {})
        controller.open_file_requested()
        controller.open_file_requested()
        self.assert_first_file_kept(controller, view)
        self.assertEqual(self.loader.loaded_path_list, [FIRST_PATH_STR])
        self.assertEqual(view.call_list, [
            "ask_open_file_path", "finish_open_file_button"] * 2)

    @covers("LLFR-00008", "LLFR-00009", "LLFR-00011", "LLFR-00012",
            "LLFR-00010", "LLFR-00510", "LLFR-00511", "LLFR-00955",
            "LLFR-00903", "LLFR-00651", "HLFR-00101", "LLFR-00418")
    def test_each_error_shows_its_message_and_keeps_the_files(
            self) -> None:
        """Every FileOpenError shows its reason; nothing else changes.

        Inputs: none.
        Outputs: none.
        """
        for requirement_str, error in ERROR_CASE_LIST:
            with self.subTest(requirement_str=requirement_str,
                              error=str(error)):
                self.listener_call_list.clear()
                view = FakeView([FIRST_PATH_STR, SECOND_PATH_STR])
                controller = self.open_first_file(
                    view, {SECOND_PATH_STR: error})
                controller.open_file_requested()
                self.assertEqual(view.error_message_list, [str(error)])
                # LLFR-00418: the indication is gone before the box.
                self.assertEqual(view.call_list, [
                    "ask_open_file_path", *LOADING_CALL_LIST,
                    "show_file_open_error", "finish_open_file_button"])
                self.assert_first_file_kept(controller, view)

    @covers("LLFR-00973", "LLFR-00008", "LLFR-00010", "LLFR-00003")
    def test_unexpected_error_is_reported_not_raised(self) -> None:
        """An unexpected loader exception is a reading error of the file.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR, SECOND_PATH_STR])
        controller = self.open_first_file(
            view, {SECOND_PATH_STR: ValueError("strange failure")})
        controller.open_file_requested()
        self.assertEqual(len(view.error_message_list), 1)
        message_str = view.error_message_list[0]
        self.assertIn("could not be read", message_str)
        self.assertIn("strange failure", message_str)
        # LLFR-00955: the file by its name, without its folder.
        self.assertIn("second.csv", message_str)
        self.assertNotIn("/data/", message_str)
        self.assert_first_file_kept(controller, view)

    @covers("LLFR-00973", "LLFR-00953", "LLFR-00955")
    def test_unexpected_error_after_the_read_goes_on(self) -> None:
        """An error in the time signal window is listed; the next file
        of the selection is still opened.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([[SECOND_PATH_STR, FIRST_PATH_STR]])

        def broken_window(*argument_tuple, **argument_dict):
            """Raise as a broken window would.

            Inputs:
                argument_tuple, argument_dict: ignored.
            Outputs: none; always raises RuntimeError.
            """
            raise RuntimeError("window failure")

        view.ask_time_signal_name = broken_window
        controller = self.build_controller(view, {
            FIRST_PATH_STR: self.first_file,
            SECOND_PATH_STR: build_no_time_file(SECOND_PATH_STR)})
        controller.open_file_requested()
        self.assertEqual(self.numbers(controller), [1])
        self.assertIs(controller.data_files.file_list[0].signal_file,
                      self.first_file)
        self.assertEqual(len(view.error_message_list), 1)
        self.assertIn("window failure", view.error_message_list[0])
        self.assertIn("second.csv", view.error_message_list[0])

    @covers("LLFR-00898", "LLFR-00899", "LLFR-00956", "LLFR-00903",
            "LLFR-00010", "LLFR-00651", "HLFR-00113")
    def test_file_already_open_is_refused_before_it_is_read(self) -> None:
        """The same file again is listed as already open, and not read.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR, "/data/../data/first.csv"])
        controller = self.open_first_file(view, {})
        controller.open_file_requested()
        self.assertEqual(self.loader.loaded_path_list, [FIRST_PATH_STR])
        self.assertEqual(view.refused_message_list, [
            ALREADY_OPEN_REASON_STR.format(name="first.csv", number=1)])
        self.assertEqual(view.refused_message_list,
                         ["first.csv: already open as file1."])
        self.assertEqual(view.error_message_list, [])
        self.assertEqual(view.call_list, [
            "ask_open_file_path", "show_refused_files_notification",
            "finish_open_file_button"])
        self.assert_first_file_kept(controller, view)

    @covers("LLFR-00898", "LLFR-00899")
    def test_link_to_an_open_file_is_refused(self) -> None:
        """A symbolic link to an open file names the same file.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as folder_str:
            path_str = os.path.join(folder_str, "run.csv")
            with open(path_str, "w", encoding="utf-8") as file:
                file.write("Time,speed\n0,1\n1,2\n")
            link_path_str = os.path.join(folder_str, "link.csv")
            try:
                os.symlink(path_str, link_path_str)
            except (OSError, NotImplementedError):
                self.skipTest("symbolic links are not available")
            view = FakeView([path_str, link_path_str])
            controller = FileController(view, load_signal_file, "/start")
            controller.open_file_requested()
            controller.open_file_requested()
        self.assertEqual(self.numbers(controller), [1])
        self.assertEqual(view.refused_message_list,
                         ["link.csv: already open as file1."])

    @covers("LLFR-00896", "LLFR-00897", "LLFR-00895", "LLFR-00005",
            "LLFR-00003", "HLFR-00113")
    def test_ten_open_files_show_the_limit_box(self) -> None:
        """With 10 files open, a click shows a box in place of the dialog.

        Inputs: none.
        Outputs: none.
        """
        path_list = [f"/data/run{index_i}.csv"
                     for index_i in range(MAXIMUM_DATA_FILES_I)]
        view = FakeView([path_list])
        controller = self.build_controller(view, {
            path_str: build_signal_file(path_str, ["a"])
            for path_str in path_list})
        controller.open_file_requested()
        self.assertEqual(len(controller.data_files), 10)
        self.assertTrue(controller.data_files.is_full_b)
        view.call_list.clear()
        self.listener_call_list.clear()
        controller.open_file_requested()
        self.assertEqual(view.call_list, [
            "show_open_files_limit_notification",
            "finish_open_file_button"])
        self.assertEqual(view.limit_message_list,
                         [OPEN_FILES_LIMIT_MESSAGE_STR])
        self.assertIn("10 files are already open",
                      OPEN_FILES_LIMIT_MESSAGE_STR)
        self.assertIn("Close one of them", OPEN_FILES_LIMIT_MESSAGE_STR)
        self.assertEqual(self.numbers(controller), list(range(1, 11)))
        self.assertEqual(self.listener_call_list, [])
        # LLFR-00895: a closed file makes room for another one.
        controller.close_file(4)
        view.path_list = ["/data/extra.csv"]
        self.loader.result_dict["/data/extra.csv"] = build_signal_file(
            "/data/extra.csv", ["z"])
        controller.open_file_requested()
        self.assertEqual(self.numbers(controller)[-1], 11)
        self.assertEqual(len(controller.data_files), 10)

    @covers("LLFR-00954", "LLFR-00956", "LLFR-00898", "LLFR-00953",
            "LLFR-00903", "HLFR-00122")
    def test_selected_files_beyond_ten_are_refused(self) -> None:
        """The limit is checked first, then whether a file is open.

        Inputs: none.
        Outputs: none.
        """
        path_list = [f"/data/a{index_i}.csv" for index_i in range(9)]
        result_dict = {path_str: build_signal_file(path_str, ["a"])
                       for path_str in path_list}
        result_dict["/data/b1.csv"] = build_signal_file("/data/b1.csv",
                                                        ["b"])
        result_dict["/data/b2.csv"] = build_signal_file("/data/b2.csv",
                                                        ["b"])
        view = FakeView([path_list, ["/data/b2.csv", "/data/a0.csv",
                                     "/data/b1.csv"]])
        controller = self.build_controller(view, result_dict)
        controller.open_file_requested()
        view.call_list.clear()
        controller.open_file_requested()
        # LLFR-00952: a0 comes first; it is already open and refused for
        # that; b1 opens as the tenth file; b2 is refused for the limit.
        self.assertEqual(len(controller.data_files), 10)
        self.assertEqual(controller.data_files.file_list[-1].path_str,
                         "/data/b1.csv")
        self.assertEqual(view.refused_message_list, ["\n".join([
            "a0.csv: already open as file1.",
            LIMIT_REASON_STR.format(name="b2.csv")])])
        self.assertIn("10 files are already open",
                      view.refused_message_list[0])
        self.assertNotIn("/data/b2.csv", self.loader.loaded_path_list)
        self.assertEqual(view.call_list[-2:], [
            "show_refused_files_notification", "finish_open_file_button"])
        # LLFR-00898 Note: with 10 files open, an open file is refused
        # for the limit.
        controller.open_paths(["/data/a1.csv"])
        self.assertEqual(view.refused_message_list[-1],
                         LIMIT_REASON_STR.format(name="a1.csv"))

    @covers("LLFR-00952", "LLFR-00974", "LLFR-00006", "LLFR-00900",
            "HLFR-00122")
    def test_selected_files_open_in_the_order_of_their_names(self) -> None:
        """Characters, not numbers, and case only to break a tie.

        Inputs: none.
        Outputs: none.
        """
        path_list = ["/z/run2.csv", "/a/Run10.csv", "/y/b.csv", "/x/B.csv"]
        view = FakeView([path_list])
        controller = self.build_controller(view, {
            path_str: build_signal_file(path_str, ["s"])
            for path_str in path_list})
        controller.open_file_requested()
        self.assertEqual(self.loader.loaded_path_list, [
            "/x/B.csv", "/y/b.csv", "/a/Run10.csv", "/z/run2.csv"])
        self.assertEqual(
            [(data_file.number_i, data_file.file_name_str)
             for data_file in controller.data_files.file_list],
            [(1, "B.csv"), (2, "b.csv"), (3, "Run10.csv"), (4, "run2.csv")])
        # LLFR-00447: the folder of the last file opened.
        self.assertEqual(controller.dialog_folder_str, "/z")

    @covers("LLFR-00953", "LLFR-00955", "LLFR-00956", "LLFR-00903",
            "LLFR-00327", "LLFR-00509", "HLFR-00122")
    def test_selection_goes_on_and_shows_one_box_of_each_kind(
            self) -> None:
        """Errors, a cancelled window and refusals do not stop the rest.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR, [
            "/d/a_broken.csv", "/d/b_no_time.csv", FIRST_PATH_STR,
            "/d/c_crash.csv", SECOND_PATH_STR]], [[]])
        controller = self.open_first_file(view, {
            "/d/a_broken.csv": FileReadError("a_broken.csv is broken."),
            "/d/b_no_time.csv": build_no_time_file("/d/b_no_time.csv"),
            "/d/c_crash.csv": RuntimeError("boom"),
            SECOND_PATH_STR: self.second_file})
        controller.open_file_requested()
        # LLFR-00903: the cancelled and failed files used no number.
        self.assertEqual(self.numbers(controller), [1, 2])
        self.assertIs(controller.data_files.file_list[1].signal_file,
                      self.second_file)
        self.assertEqual(len(view.error_message_list), 1)
        error_str = view.error_message_list[0]
        self.assertIn("a_broken.csv is broken.", error_str)
        self.assertIn("boom", error_str)
        self.assertLess(error_str.index("a_broken"), error_str.index("boom"))
        self.assertNotIn("/d/", error_str)
        self.assertEqual(view.refused_message_list,
                         ["first.csv: already open as file1."])
        # LLFR-00955, LLFR-00956: one box of each kind, after the last
        # file, the errors first.
        self.assertEqual(view.call_list[-3:], [
            "show_file_open_error", "show_refused_files_notification",
            "finish_open_file_button"])
        self.assertEqual(view.call_list.count("ask_time_signal_name"), 1)

    @covers("LLFR-00900", "LLFR-00901", "LLFR-00902", "LLFR-00904",
            "LLFR-00931", "HLFR-00114", "HLFR-00118", "HLFR-00119")
    def test_numbers_are_never_given_again(self) -> None:
        """Closed numbers stay used up, also after Close all files.

        Inputs: none.
        Outputs: none.
        """
        path_list = ["/d/a.csv", "/d/b.csv", "/d/c.csv"]
        result_dict = {path_str: build_signal_file(path_str, ["s"])
                       for path_str in path_list + ["/d/d.csv"]}
        view = FakeView([path_list, ["/d/d.csv"], ["/d/b.csv"]])
        controller = self.build_controller(view, result_dict)
        controller.open_file_requested()
        third_data_file = controller.data_files.file_list[2]
        self.assertTrue(controller.close_file(2))
        self.assertEqual(self.numbers(controller), [1, 3])
        self.assertIs(controller.data_files.file_list[1], third_data_file)
        self.assertEqual(third_data_file.signal_name_list,
                         ["file3_Time", "file3_s"])
        self.assertEqual(self.closed_call_list, [([2], [1, 3])])
        controller.open_file_requested()
        self.assertEqual(self.numbers(controller), [1, 3, 4])
        # LLFR-00904: after Close all files, numbering goes on.
        self.assertEqual(
            [data_file.number_i
             for data_file in controller.close_all_files()], [1, 3, 4])
        self.assertEqual(self.closed_call_list[-1], ([1, 3, 4], []))
        self.assertIsNone(controller.current_file)
        controller.open_file_requested()
        self.assertEqual(self.numbers(controller), [5])

    @covers("LLFR-00926", "LLFR-00936")
    def test_closing_nothing_tells_nobody(self) -> None:
        """An unknown number, or no file open, closes nothing.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR])
        controller = self.open_first_file(view, {})
        self.assertFalse(controller.close_file(7))
        self.assertEqual(self.closed_call_list, [])
        controller.close_all_files()
        self.assertEqual(controller.close_all_files(), [])
        self.assertEqual(len(self.closed_call_list), 1)

    @covers("LLFR-00003", "LLFR-00071", "LLFR-00441")
    def test_listener_error_is_an_unexpected_error(self) -> None:
        """A listener that raises after the file was added: the file
        stays open, the other files are taken, no File Open Error box,
        and the error goes on to the unexpected error box.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([[FIRST_PATH_STR, SECOND_PATH_STR]])
        controller = self.build_controller(
            view, {FIRST_PATH_STR: self.first_file,
                   SECOND_PATH_STR: self.second_file})

        def failing_listener(data_files, data_file) -> None:
            """Raise as a broken listener would.

            Inputs:
                data_files: ignored.
                data_file: ignored.
            Outputs: none; always raises RuntimeError.
            """
            raise RuntimeError("listener failure")

        controller.add_file_opened_listener(failing_listener)
        with self.assertRaisesRegex(RuntimeError, "listener failure"):
            controller.open_file_requested()
        self.assertEqual(view.call_list[-1], "finish_open_file_button")
        self.assertEqual(view.error_message_list, [])
        self.assertEqual(self.numbers(controller), [1, 2])
        self.assertEqual(len(self.listener_call_list), 2)

    @covers("LLFR-00920")
    def test_every_listener_is_notified_in_order(self) -> None:
        """All registered listeners receive the added file in order.

        Inputs: none.
        Outputs: none.
        """
        order_list = []
        view = FakeView([FIRST_PATH_STR])
        controller = self.build_controller(
            view, {FIRST_PATH_STR: self.first_file})
        controller.add_file_opened_listener(
            lambda data_files, data_file: order_list.append(
                ("second", data_file.number_i)))
        controller.open_file_requested()
        self.assertEqual(len(self.listener_call_list), 1)
        self.assertEqual(order_list, [("second", 1)])

    @covers("LLFR-00006")
    def test_default_load_function_is_load_signal_file(self) -> None:
        """Without a load function the real loader is used.

        Inputs: none.
        Outputs: none.
        """
        controller = FileController(FakeView([]))
        self.assertIs(controller.load_function, load_signal_file)


class StartFolderTest(unittest.TestCase):
    """Check the folder shown by the file selection dialog (LLFR-00204)."""

    @covers("LLFR-00204", "LLFR-00005", "LLFR-00446")
    def test_from_source_the_repository_folder(self) -> None:
        """Run from source, the first folder is the repository folder.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(os.path.realpath(REPOSITORY_FOLDER_STR),
                         os.path.realpath(REPOSITORY_ROOT_STR))
        self.assertTrue(os.path.isdir(os.path.join(REPOSITORY_FOLDER_STR,
                                                   "src", "controller")))
        self.assertEqual(first_start_folder_str(frozen_b=False),
                         os.path.abspath(REPOSITORY_FOLDER_STR))
        self.assertEqual(
            first_start_folder_str(False, "/ignored/python", "/repo"),
            "/repo")

    @covers("LLFR-00204")
    def test_frozen_executable_folder(self) -> None:
        """A build that is not a macOS bundle uses the executable's folder.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(
            first_start_folder_str(True, "/opt/bin/plot_tool/plot_tool"),
            "/opt/bin/plot_tool")
        self.assertEqual(
            first_start_folder_str(True, "/opt/MacOS/plot_tool"),
            "/opt/MacOS")
        self.assertEqual(
            first_start_folder_str(True, "/opt/x.app/MacOS/plot_tool"),
            "/opt/x.app/MacOS")

    @covers("LLFR-00204")
    def test_frozen_macos_bundle_uses_the_folder_of_the_app(self) -> None:
        """Inside plot_tool.app the folder holding the bundle is used.

        Inputs: none.
        Outputs: none.
        """
        executable_path_str = (
            "/Users/me/Apps/bin/plot_tool.app/Contents/MacOS/plot_tool")
        self.assertEqual(first_start_folder_str(True, executable_path_str),
                         "/Users/me/Apps/bin")

    @covers("LLFR-00204", "LLFR-00446")
    def test_defaults_read_sys(self) -> None:
        """Without arguments the folder comes from sys.frozen.

        Inputs: none.
        Outputs: none.
        """
        with mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "executable",
                                  "/apps/plot_tool.app/Contents/MacOS/x"):
            self.assertEqual(first_start_folder_str(), "/apps")
        if not getattr(sys, "frozen", False):
            self.assertEqual(first_start_folder_str(),
                             os.path.abspath(REPOSITORY_FOLDER_STR))
        controller = FileController(FakeView([]))
        self.assertEqual(controller.dialog_folder_str,
                         first_start_folder_str())

    @covers("LLFR-00204", "LLFR-00005", "LLFR-00007", "LLFR-00010",
            "LLFR-00447", "LLFR-00898")
    def test_folder_follows_only_successful_opens(self) -> None:
        """Cancel, failed and refused opens keep the folder.

        Inputs: none.
        Outputs: none.
        """
        first_file = build_signal_file("/data/a/first.csv", ["a"])
        second_file = build_signal_file("/data/b/second.csv", ["b"])
        loader = ScriptedLoader({
            "/data/a/first.csv": first_file,
            "/data/bad/broken.csv": FileReadError("could not be read"),
            "/data/crash/crash.csv": RuntimeError("boom"),
            "/data/b/second.csv": second_file,
        })
        view = FakeView(["", "/data/a/first.csv", "",
                         "/data/bad/broken.csv", "/data/crash/crash.csv",
                         "/data/b/second.csv", "/data/b/second.csv",
                         ""])
        controller = FileController(view, loader, "/start")
        for _ in range(8):
            controller.open_file_requested()
        self.assertEqual(view.start_folder_list, [
            "/start", "/start", "/data/a", "/data/a", "/data/a",
            "/data/a", "/data/b", "/data/b"])
        self.assertEqual(controller.data_files.path_list,
                         ["/data/a/first.csv", "/data/b/second.csv"])

    @covers("LLFR-00447", "LLFR-00980", "LLFR-00951", "LLFR-00952",
            "LLFR-00953", "HLFR-00122")
    def test_folder_after_several_files_at_once(self) -> None:
        """The last selected file that opened, in the opening order.

        Inputs: none.
        Outputs: none.
        """
        loader = ScriptedLoader({
            "/data/x/a_first.csv": build_signal_file(
                "/data/x/a_first.csv", ["a"]),
            "/data/y/b_second.csv": build_signal_file(
                "/data/y/b_second.csv", ["b"]),
            "/data/z/c_broken.csv": FileReadError("could not be read"),
            "/data/w/d_fourth.csv": build_signal_file(
                "/data/w/d_fourth.csv", ["d"]),
            "/data/v/e_broken.csv": FileReadError("could not be read"),
        })
        # The dialog gives the files in another order than their names
        # (LLFR-00952); the last name that opens decides the folder.
        view = FakeView([
            ["/data/y/b_second.csv", "/data/z/c_broken.csv",
             "/data/x/a_first.csv"],
            ["/data/v/e_broken.csv", "/data/w/d_fourth.csv"],
            ["/data/v/e_broken.csv"],
            ""])
        controller = FileController(view, loader, "/start")
        for _ in range(4):
            controller.open_file_requested()
        self.assertEqual(view.start_folder_list, [
            "/start", "/data/y", "/data/w", "/data/w"])
        self.assertEqual(controller.dialog_folder_str, "/data/w")


class FileControllerRealLoaderTest(unittest.TestCase):
    """Check the flow with the real load_signal_file on temp files."""

    def setUp(self) -> None:
        """Create a temporary folder with CSV files.

        Inputs: none.
        Outputs: none.
        """
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        self.valid_path_str = self.write_file(
            "valid.csv", "Time,speed,force\n0,1,2\n0.5,3,4\n")
        self.other_path_str = self.write_file(
            "other.csv", "Time,pressure\n0,1\n1,2\n")
        self.no_time_path_str = self.write_file(
            "one_signal.csv", "speed\n0\n1\n")
        self.bad_value_path_str = self.write_file(
            "bad_value.csv", "Time,speed\n0,1\n1,abc\n")
        self.text_path_str = self.write_file("notes.txt", "hello")
        self.missing_path_str = os.path.join(
            self.temporary_folder.name, "missing.csv")

    def write_file(self, name_str: str, content_str: str) -> str:
        """Write a text file in the temporary folder.

        Inputs:
            name_str: file name.
            content_str: file content.
        Outputs: the full path of the file.
        """
        path_str = os.path.join(self.temporary_folder.name, name_str)
        with open(path_str, "w", encoding="utf-8") as file:
            file.write(content_str)
        return path_str

    @covers("LLFR-00006", "LLFR-00054", "LLFR-00008", "LLFR-00009",
            "LLFR-00010", "LLFR-00011", "LLFR-00012", "LLFR-00955",
            "LLFR-00909", "LLFR-00920", "HLFR-00101", "HLFR-00122")
    def test_real_messages_reach_the_view_in_one_box(self) -> None:
        """Real files open, or fail with the loader's messages, listed
        in one box for one selection.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([[self.valid_path_str, self.no_time_path_str,
                          self.bad_value_path_str, self.text_path_str,
                          self.missing_path_str, self.other_path_str]])
        controller = FileController(view)
        controller.open_file_requested()
        self.assertEqual(len(view.error_message_list), 1)
        error_str = view.error_message_list[0]
        self.assertIn("one_signal.csv", error_str)
        self.assertIn("at least two signals", error_str)
        self.assertIn("could not be read", error_str)
        self.assertIn("abc", error_str)
        self.assertIn("not supported", error_str)
        self.assertIn("could not be accessed", error_str)
        # LLFR-00952: other.csv comes before valid.csv.
        self.assertEqual(controller.data_files.signal_name_list, [
            "file1_Time", "file1_pressure", "file2_Time", "file2_speed",
            "file2_force"])
        # LLFR-00909: "Time" was found by its name in each file.
        self.assertEqual(controller.data_files.time_signal_name_list,
                         ["file1_Time", "file2_Time"])
        self.assertEqual(view.call_list.count("finish_open_file_button"),
                         1)
        self.assertNotIn("ask_time_signal_name", view.call_list)

    @covers("LLFR-00325", "LLFR-00326", "LLFR-00328", "LLFR-00329",
            "LLFR-00068", "HLFR-00070", "HLFR-00007", "LLFR-00507",
            "LLFR-00910")
    def test_real_file_without_time_asks_for_it(self) -> None:
        """A real CSV whose x column is "t_s" opens after the choice.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_file(
            "x_axis.csv", "speed,t_s,force\n5,0,2\n4,0.5,4\n3,2,1\n")
        view = FakeView([path_str], [["speed", "force", "t_s"]])
        controller = FileController(view)
        controller.open_file_requested()
        self.assertEqual(view.call_list, [
            "ask_open_file_path", *LOADING_CALL_LIST,
            "ask_time_signal_name", "finish_open_file_button"])
        # LLFR-00910: the window lists the names in the file.
        self.assertEqual(view.time_window_list[0][1],
                         ["speed", "t_s", "force"])
        self.assertEqual(len(view.time_reason_list), 2)
        for reason_str in view.time_reason_list:
            self.assertIn("must always increase", reason_str)
        data_file = controller.data_files.file_list[0]
        self.assertEqual(data_file.time_signal_name_str, "file1_t_s")
        np.testing.assert_array_equal(data_file.time_array,
                                      [0.0, 0.5, 2.0])
        self.assertEqual(data_file.signal_name_list,
                         ["file1_speed", "file1_t_s", "file1_force"])


class LoadingStateView(FakeView):
    """FakeView that also records whether the indication was shown.

    Inputs: as FakeView.
    Attributes:
        state_list: (call name, loading_shown_b) for every box and
            window the controller showed.
    """

    def __init__(self, *argument_tuple) -> None:
        """Start like FakeView with no recorded state.

        Inputs:
            argument_tuple: the FakeView arguments.
        Outputs: none.
        """
        super().__init__(*argument_tuple)
        self.state_list = []

    def show_file_open_error(self, message_str: str) -> None:
        """Record the indication state, then record the error.

        Inputs:
            message_str: the message of the File Open Error box.
        Outputs: none.
        """
        self.state_list.append(("show_file_open_error",
                                self.loading_shown_b))
        super().show_file_open_error(message_str)

    def ask_time_signal_name(self, *argument_tuple, **argument_dict):
        """Record the indication state, then answer as FakeView.

        Inputs:
            argument_tuple: the window arguments.
            argument_dict: the keyword arguments (file_name_str).
        Outputs: the scripted answer.
        """
        self.state_list.append(("ask_time_signal_name",
                                self.loading_shown_b))
        return super().ask_time_signal_name(*argument_tuple,
                                            **argument_dict)


class OpeningOrderTest(FileControllerTestCase):
    """The order of LLFR-00328 and the indication of LLFR-00418."""

    def build_controller(self, view, result_dict: dict) -> FileController:
        """Build a controller whose loader records the indication state.

        Inputs:
            view: the LoadingStateView.
            result_dict: path -> SignalFile or exception.
        Outputs: the FileController with no file open yet.
        """
        controller = super().build_controller(view, result_dict)
        scripted_loader = self.loader

        def recording_loader(path_str: str) -> SignalFile:
            """Record the indication state, then load as scripted.

            Inputs:
                path_str: the path to open.
            Outputs: the scripted SignalFile; raises the scripted error.
            """
            view.state_list.append(("load", view.loading_shown_b))
            return scripted_loader(path_str)

        controller.load_function = recording_loader
        return controller

    def open_first_file(self, view, result_dict: dict) -> FileController:
        """Open FIRST_PATH_STR, then clear the recorded states too.

        Inputs:
            view: the LoadingStateView; its first path is FIRST_PATH_STR.
            result_dict: the results of the other paths.
        Outputs: the FileController with the first file open.
        """
        controller = super().open_first_file(view, result_dict)
        view.state_list.clear()
        return controller

    @covers("LLFR-00418", "LLFR-00328", "LLFR-00006", "LLFR-00560")
    def test_first_file_read_under_the_indication(self) -> None:
        """The first file is read while the loading indication is shown.

        Inputs: none.
        Outputs: none.
        """
        view = LoadingStateView([FIRST_PATH_STR])
        controller = self.build_controller(
            view, {FIRST_PATH_STR: self.first_file})
        controller.open_file_requested()
        self.assertEqual(view.state_list, [("load", True)])
        self.assertEqual(view.call_list.count("show_loading_indication"), 1)
        self.assertFalse(view.loading_shown_b)
        self.assertEqual(self.numbers(controller), [1])

    @covers("LLFR-00418", "LLFR-00560", "LLFR-00922", "LLFR-00328",
            "HLFR-00117")
    def test_added_file_read_under_the_indication(self) -> None:
        """With a file open, the next one is read at once, with the
        indication, and no question comes before.

        Inputs: none.
        Outputs: none.
        """
        view = LoadingStateView([FIRST_PATH_STR, SECOND_PATH_STR])
        controller = self.open_first_file(
            view, {SECOND_PATH_STR: self.second_file})
        controller.open_file_requested()
        self.assertEqual(view.state_list, [("load", True)])
        self.assertEqual(view.call_list, [
            "ask_open_file_path", *LOADING_CALL_LIST,
            "finish_open_file_button"])
        self.assertEqual(self.numbers(controller), [1, 2])

    @covers("LLFR-00008", "LLFR-00009", "LLFR-00011", "LLFR-00012",
            "LLFR-00010", "LLFR-00328", "LLFR-00418", "LLFR-00510",
            "LLFR-00511", "LLFR-00561", "LLFR-00562", "LLFR-00973")
    def test_error_box_after_the_indication(self) -> None:
        """Every File Open Error is shown after the indication is gone.

        Inputs: none.
        Outputs: none.
        """
        for requirement_str, error in ERROR_CASE_LIST + [
                ("LLFR-00973", RuntimeError("boom"))]:
            with self.subTest(requirement_str=requirement_str,
                              error=str(error)):
                view = LoadingStateView([FIRST_PATH_STR, SECOND_PATH_STR])
                controller = self.open_first_file(
                    view, {SECOND_PATH_STR: error})
                controller.open_file_requested()
                self.assertEqual(view.state_list, [
                    ("load", True), ("show_file_open_error", False)])
                self.assertEqual(len(view.error_message_list), 1)
                self.assertIn(str(error), view.error_message_list[0])
                self.assertEqual(view.call_list[-1],
                                 "finish_open_file_button")
                self.assert_first_file_kept(controller, view)

    @covers("LLFR-00011", "LLFR-00328", "LLFR-00418", "LLFR-00010",
            "LLFR-00510")
    def test_unsupported_format_with_a_file_open(self) -> None:
        """A real .txt file gives the unsupported format box.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as folder_str:
            text_path_str = os.path.join(folder_str, "notes.txt")
            with open(text_path_str, "w", encoding="utf-8") as file:
                file.write("hello")
            view = LoadingStateView([FIRST_PATH_STR, text_path_str])
            controller = self.open_first_file(view, {})

            def real_loader(path_str: str) -> SignalFile:
                """Use the real loader for the text file.

                Inputs:
                    path_str: the path to open.
                Outputs: the loaded SignalFile; raises FileOpenError.
                """
                view.state_list.append(("load", view.loading_shown_b))
                return load_signal_file(path_str)

            controller.load_function = real_loader
            controller.open_file_requested()
        self.assertEqual(view.state_list, [
            ("load", True), ("show_file_open_error", False)])
        self.assertIn("not supported", view.error_message_list[0])
        self.assert_first_file_kept(controller, view)

    @covers("LLFR-00327", "LLFR-00328", "LLFR-00418", "LLFR-00010",
            "LLFR-00325", "LLFR-00508", "LLFR-00509", "LLFR-00512",
            "LLFR-00513", "LLFR-00562", "LLFR-00903")
    def test_time_window_cancelled(self) -> None:
        """Read under the indication, window without it, cancel.

        Inputs: none.
        Outputs: none.
        """
        view = LoadingStateView([FIRST_PATH_STR, SECOND_PATH_STR], [[]])
        controller = self.open_first_file(
            view, {SECOND_PATH_STR: build_no_time_file(SECOND_PATH_STR)})
        controller.open_file_requested()
        self.assertEqual(view.state_list, [
            ("load", True), ("ask_time_signal_name", False)])
        self.assertEqual(view.error_message_list, [])
        self.assertEqual(view.refused_message_list, [])
        self.assert_first_file_kept(controller, view)

    @covers("LLFR-00326", "LLFR-00328", "LLFR-00418", "LLFR-00507",
            "LLFR-00920")
    def test_time_window_confirmed(self) -> None:
        """Read, window, then only now the file is added.

        Inputs: none.
        Outputs: none.
        """
        no_time_file = build_no_time_file(SECOND_PATH_STR)
        view = LoadingStateView([FIRST_PATH_STR, SECOND_PATH_STR],
                                [["t_s"]])
        controller = self.open_first_file(view,
                                          {SECOND_PATH_STR: no_time_file})
        controller.open_file_requested()
        self.assertEqual(view.state_list, [
            ("load", True), ("ask_time_signal_name", False)])
        self.assertEqual(self.numbers(controller), [1, 2])
        self.assertEqual(self.listener_call_list[0][:2], (2, no_time_file))
        self.assertEqual(controller.data_files.file_list[1]
                         .time_signal_name_str, "file2_t_s")

    @covers("LLFR-00418", "LLFR-00561", "LLFR-00562")
    def test_indication_removed_when_reading_is_interrupted(self) -> None:
        """Even an exception that is not caught removes the indication.

        Inputs: none.
        Outputs: none.
        """
        view = LoadingStateView([FIRST_PATH_STR])
        controller = self.build_controller(view, {})

        def interrupted_loader(path_str: str) -> SignalFile:
            """Raise as an interrupted read would.

            Inputs:
                path_str: ignored.
            Outputs: none; always raises KeyboardInterrupt.
            """
            raise KeyboardInterrupt()

        controller.load_function = interrupted_loader
        with self.assertRaises(KeyboardInterrupt):
            controller.open_file_requested()
        self.assertFalse(view.loading_shown_b)
        self.assertEqual(view.call_list[-2:], [
            "hide_loading_indication", "finish_open_file_button"])
        self.assertIsNone(controller.current_file)


class TimeSignalWindowTest(FileControllerTestCase):
    """The time signal window in the open-file flow (HLFR-00070)."""

    def setUp(self) -> None:
        """Prepare a file with Time and a file without.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.no_time_file = build_no_time_file(SECOND_PATH_STR)

    @covers("LLFR-00325", "LLFR-00326", "HLFR-00070", "LLFR-00054",
            "LLFR-00910", "LLFR-00957")
    def test_window_shown_when_no_time_signal(self) -> None:
        """The window lists every signal; the choice is the time signal.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([SECOND_PATH_STR], [["t_s"]])
        controller = self.build_controller(
            view, {SECOND_PATH_STR: self.no_time_file})
        controller.open_file_requested()
        self.assertEqual(len(view.time_window_list), 1)
        prompt_str, name_list, search_function, no_match_str = (
            view.time_window_list[0])
        self.assertEqual(prompt_str,
                         "Choose the signal that goes on the x-axis")
        self.assertEqual(prompt_str, TIME_SIGNAL_PROMPT_STR)
        self.assertEqual(name_list, ["Down", "t_s", "Flat"])
        self.assertEqual(no_match_str, "No matching signals")
        self.assertEqual(self.no_time_file.time_signal_name_str, "t_s")
        np.testing.assert_array_equal(self.no_time_file.time_array,
                                      [0.0, 0.5, 1.5])
        self.assertEqual(controller.data_files.signal_name_list,
                         ["file1_Down", "file1_t_s", "file1_Flat"])
        self.assertEqual(controller.data_files.time_signal_name_list,
                         ["file1_t_s"])
        # LLFR-00957: the window names its file, without its folder.
        self.assertEqual(view.time_window_file_name_list,
                         [os.path.basename(SECOND_PATH_STR)])
        self.assertNotIn(os.sep, view.time_window_file_name_list[0])

    @covers("LLFR-00325", "LLFR-00285", "LLFR-00098", "LLFR-00101",
            "LLFR-00102", "LLFR-00618")
    def test_window_search_uses_signal_list_rules(self) -> None:
        """The window's search finds names like the signal list search.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([SECOND_PATH_STR], [[]])
        controller = self.build_controller(
            view, {SECOND_PATH_STR: self.no_time_file})
        controller.open_file_requested()
        search_function = view.time_window_list[0][2]
        self.assertEqual(search_function(""), ["Down", "t_s", "Flat"])
        self.assertEqual(search_function("   "), ["Down", "t_s", "Flat"])
        self.assertEqual(search_function("TS"), ["t_s"])
        self.assertEqual(search_function("flta"), ["Flat"])
        self.assertEqual(search_function("zzzz"), [])

    @covers("LLFR-00329", "LLFR-00326")
    def test_non_increasing_signal_is_refused(self) -> None:
        """A signal that does not always increase keeps the window open.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([SECOND_PATH_STR], [["Down", "Flat", "t_s"]])
        controller = self.build_controller(
            view, {SECOND_PATH_STR: self.no_time_file})
        controller.open_file_requested()
        self.assertEqual(len(view.time_reason_list), 2)
        self.assertIn("'Down'", view.time_reason_list[0])
        self.assertIn("'Flat'", view.time_reason_list[1])
        for reason_str in view.time_reason_list:
            self.assertIn("must always increase", reason_str)
        self.assertEqual(controller.data_files.time_signal_name_list,
                         ["file1_t_s"])

    @covers("LLFR-00329", "LLFR-00903")
    def test_unchecked_bad_answer_never_becomes_time(self) -> None:
        """A window that returns a refused name opens nothing.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([SECOND_PATH_STR])
        view.ask_time_signal_name = lambda *argument_tuple: "Down"
        controller = self.build_controller(
            view, {SECOND_PATH_STR: self.no_time_file})
        controller.open_file_requested()
        self.assertIsNone(controller.current_file)
        self.assertIsNone(self.no_time_file.time_signal_name_str)
        self.assertEqual(self.listener_call_list, [])
        self.assertEqual(controller.data_files.next_number_i, 1)

    @covers("LLFR-00327", "HLFR-00070", "LLFR-00003", "LLFR-00010",
            "LLFR-00328", "LLFR-00418", "LLFR-00508", "LLFR-00512",
            "LLFR-00651", "LLFR-00922")
    def test_cancel_keeps_the_open_files(self) -> None:
        """Read with no question, then a cancelled window opens nothing.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR, SECOND_PATH_STR], [[]])
        controller = self.open_first_file(
            view, {SECOND_PATH_STR: self.no_time_file})
        controller.open_file_requested()
        self.assertEqual(view.error_message_list, [])
        self.assertEqual(view.call_list, [
            "ask_open_file_path", *LOADING_CALL_LIST,
            "ask_time_signal_name", "finish_open_file_button"])
        self.assert_first_file_kept(controller, view)

    @covers("LLFR-00328", "LLFR-00012", "HLFR-00008", "LLFR-00418")
    def test_failed_check_never_shows_the_window(self) -> None:
        """A file that fails the content checks never shows the window.

        Inputs: none.
        Outputs: none.
        """
        error = ContentCheckError("Fewer than two signals.",
                                  SIGNAL_COUNT_CHECK_STR)
        view = FakeView([SECOND_PATH_STR])
        controller = self.build_controller(view, {SECOND_PATH_STR: error})
        controller.open_file_requested()
        self.assertEqual(view.call_list, [
            "ask_open_file_path", *LOADING_CALL_LIST,
            "show_file_open_error", "finish_open_file_button"])

    @covers("LLFR-00331", "LLFR-00324", "HLFR-00072", "HLFR-00070",
            "LLFR-00505", "LLFR-00515", "LLFR-00909")
    def test_file_with_time_never_shows_the_window(self) -> None:
        """Opening, closing and opening again a file with a Time match
        asks nothing.

        Inputs: none.
        Outputs: none.
        """
        lowercase_file = SignalFile(SECOND_PATH_STR, {
            "a": np.arange(3.0), "TIME": np.arange(3.0),
            "time": np.arange(3.0)})
        view = FakeView([FIRST_PATH_STR, SECOND_PATH_STR, FIRST_PATH_STR])
        controller = self.build_controller(
            view, {FIRST_PATH_STR: self.first_file,
                   SECOND_PATH_STR: lowercase_file})
        controller.open_file_requested()
        controller.open_file_requested()
        controller.close_file(1)
        controller.open_file_requested()
        self.assertNotIn("ask_time_signal_name", view.call_list)
        self.assertEqual(controller.data_files.time_signal_name_list,
                         ["file2_TIME", "file3_Time"])


if __name__ == "__main__":
    unittest.main()
