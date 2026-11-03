"""Tests for the open-file flow of FileController (no Qt needed)."""

import os
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

from tests.support import REPOSITORY_ROOT_STR, covers

from controller.file_controller import (
    REPOSITORY_FOLDER_STR, TIME_SIGNAL_PROMPT_STR, FileController,
    first_start_folder_str)
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


class FakeView:
    """Stand-in for MainWindow that records every facade call.

    Inputs:
        path_list: paths returned by successive ask_open_file_path calls
            ("" means the dialog was cancelled).
        replace_answer_list: answers returned by successive
            ask_replace_file calls.
        time_answer_list: lists of names "confirmed" by successive
            ask_time_signal_name calls; each name is checked with the
            window's check function like the real window does, and the
            first accepted one is returned; an empty list cancels.
    """

    def __init__(self, path_list: list, replace_answer_list=None,
                 time_answer_list=None) -> None:
        """Store the scripted answers and start with no calls.

        Inputs:
            path_list: the scripted dialog results.
            replace_answer_list: the scripted confirmation answers.
            time_answer_list: the scripted time signal window answers.
        Outputs: none.
        """
        self.path_list = list(path_list)
        self.replace_answer_list = list(replace_answer_list or [])
        self.time_answer_list = list(time_answer_list or [])
        self.time_window_list = []
        self.time_reason_list = []
        self.time_signal_name_list = []
        self.call_list = []
        self.error_message_list = []
        self.shown_name_list = []
        self.start_folder_list = []
        self.loading_text_list = []
        self.loading_shown_b = False

    def ask_open_file_path(self, start_folder_str: str) -> str:
        """Record the call and return the next scripted path.

        Inputs:
            start_folder_str: the folder the dialog would show.
        Outputs: the next path of path_list.
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

    def ask_replace_file(self) -> bool:
        """Record the call and return the next scripted answer.

        Inputs: none.
        Outputs: the next answer of replace_answer_list.
        """
        self.call_list.append("ask_replace_file")
        return self.replace_answer_list.pop(0)

    def ask_time_signal_name(self, prompt_str: str, name_list: list,
                             search_function, no_match_text_str: str,
                             check_function):
        """Record the window and return the first accepted answer.

        Inputs:
            prompt_str: the text of the window.
            name_list: the names listed.
            search_function: text -> matching names.
            no_match_text_str: the text shown when nothing matches.
            check_function: name -> reason ("" when accepted).
        Outputs: the first scripted name that check_function accepts,
            or None (cancel) when none is.
        """
        self.call_list.append("ask_time_signal_name")
        self.time_window_list.append(
            (prompt_str, list(name_list), search_function,
             no_match_text_str))
        for name_str in self.time_answer_list.pop(0):
            reason_str = check_function(name_str)
            if not reason_str:
                return name_str
            self.time_reason_list.append(reason_str)
        return None

    def set_time_signal_name(self, name_str: str) -> None:
        """Record the time signal given to the signal list.

        Inputs:
            name_str: the time signal name.
        Outputs: none.
        """
        self.time_signal_name_list.append(name_str)

    def show_signal_names(self, signal_name_list: list) -> None:
        """Record the names shown in the signal list.

        Inputs:
            signal_name_list: the names to show.
        Outputs: none.
        """
        self.call_list.append("show_signal_names")
        self.shown_name_list = list(signal_name_list)

    def finish_open_file_button(self) -> None:
        """Record that the Open file button was finished.

        Inputs: none.
        Outputs: none.
        """
        self.call_list.append("finish_open_file_button")

    def show_loading_indication(self, text_str: str) -> None:
        """Record that the busy pointer and the status text were shown.

        Inputs:
            text_str: the status line text.
        Outputs: none.
        """
        self.call_list.append("show_loading_indication")
        self.loading_text_list.append(text_str)
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


class FileControllerTest(unittest.TestCase):
    """Check the open-file flow with a fake view and fake loaders."""

    def setUp(self) -> None:
        """Prepare two valid files and a listener call recorder.

        Inputs: none.
        Outputs: none.
        """
        self.first_file = build_signal_file(FIRST_PATH_STR, ["a", "b"])
        self.second_file = build_signal_file(SECOND_PATH_STR, ["c"])
        self.listener_call_list = []

    def record_listener(self, signal_file, replaced_b: bool) -> None:
        """Record one call of a file-opened listener.

        Inputs:
            signal_file: the opened SignalFile.
            replaced_b: whether it replaced another file.
        Outputs: none.
        """
        self.listener_call_list.append((signal_file, replaced_b))

    def build_controller(self, view, result_dict: dict) -> FileController:
        """Build a FileController with a scripted loader and listener.

        Inputs:
            view: the fake view.
            result_dict: path -> SignalFile or exception.
        Outputs: the FileController.
        """
        self.loader = ScriptedLoader(result_dict)
        controller = FileController(view, self.loader)
        controller.add_file_opened_listener(self.record_listener)
        return controller

    def open_first_file(self, view, result_dict: dict) -> FileController:
        """Build a controller and open FIRST_PATH_STR with it.

        Inputs:
            view: the fake view; its first path must be FIRST_PATH_STR.
            result_dict: path -> SignalFile or exception.
        Outputs: the FileController with the first file open.
        """
        result_dict = dict(result_dict)
        result_dict[FIRST_PATH_STR] = self.first_file
        controller = self.build_controller(view, result_dict)
        controller.open_file_requested()
        self.assertIs(controller.current_file, self.first_file)
        view.call_list.clear()
        self.listener_call_list.clear()
        return controller

    @covers("LLFR-00005", "LLFR-00006", "LLFR-00054", "LLFR-00003",
            "LLFR-00328", "LLFR-00418")
    def test_first_file_is_opened_and_shown(self) -> None:
        """The first valid file opens without confirmation.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR])
        controller = self.build_controller(
            view, {FIRST_PATH_STR: self.first_file})
        self.assertIsNone(controller.current_file)
        controller.open_file_requested()
        self.assertEqual(self.loader.loaded_path_list, [FIRST_PATH_STR])
        self.assertIs(controller.current_file, self.first_file)
        self.assertEqual(view.shown_name_list, ["Time", "a", "b"])
        # LLFR-00418: the indication is shown for the first file too.
        self.assertEqual(view.call_list, [
            "ask_open_file_path", *LOADING_CALL_LIST, "show_signal_names",
            "finish_open_file_button"])
        self.assertEqual(view.loading_text_list, ["Loading..."])
        self.assertEqual(self.listener_call_list,
                         [(self.first_file, False)])

    @covers("HLFR-00010")
    def test_first_file_does_not_ask_for_confirmation(self) -> None:
        """No replace confirmation is asked when no file is open.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR])
        controller = self.build_controller(
            view, {FIRST_PATH_STR: self.first_file})
        controller.open_file_requested()
        self.assertNotIn("ask_replace_file", view.call_list)

    @covers("LLFR-00007", "LLFR-00003")
    def test_cancel_before_any_file_changes_nothing(self) -> None:
        """Cancelling the dialog with no file open loads nothing.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([""])
        controller = self.build_controller(view, {})
        controller.open_file_requested()
        self.assertIsNone(controller.current_file)
        self.assertEqual(self.loader.loaded_path_list, [])
        self.assertEqual(view.call_list, [
            "ask_open_file_path", "finish_open_file_button"])
        self.assertEqual(self.listener_call_list, [])

    @covers("LLFR-00007", "LLFR-00003")
    def test_cancel_keeps_open_file_and_list(self) -> None:
        """Cancelling the dialog keeps the open file and its list.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR, ""])
        controller = self.open_first_file(view, {})
        controller.open_file_requested()
        self.assertIs(controller.current_file, self.first_file)
        self.assertEqual(view.shown_name_list, ["Time", "a", "b"])
        self.assertEqual(view.call_list, [
            "ask_open_file_path", "finish_open_file_button"])
        self.assertEqual(self.listener_call_list, [])

    @covers("LLFR-00008", "LLFR-00009", "LLFR-00011", "LLFR-00012",
            "LLFR-00003", "LLFR-00418")
    def test_each_error_shows_its_message(self) -> None:
        """Every FileOpenError shows the error box with its message.

        Inputs: none.
        Outputs: none.
        """
        for requirement_str, error in ERROR_CASE_LIST:
            with self.subTest(requirement_str=requirement_str,
                              error=str(error)):
                self.listener_call_list.clear()
                view = FakeView([SECOND_PATH_STR])
                controller = self.build_controller(
                    view, {SECOND_PATH_STR: error})
                controller.open_file_requested()
                self.assertEqual(view.error_message_list, [str(error)])
                self.assertIsNone(controller.current_file)
                # LLFR-00418: the indication is gone before the box.
                self.assertEqual(view.call_list, [
                    "ask_open_file_path", *LOADING_CALL_LIST,
                    "show_file_open_error", "finish_open_file_button"])
                self.assertEqual(self.listener_call_list, [])

    @covers("LLFR-00010", "LLFR-00008", "LLFR-00009", "LLFR-00011",
            "LLFR-00012", "HLFR-00010", "LLFR-00013", "LLFR-00328",
            "LLFR-00418", "LLFR-00363")
    def test_failed_open_keeps_previous_file(self) -> None:
        """Proceeding, then a failed read, keeps the previous file.

        The confirmation comes first, then the read with the
        indication, then the error box; nothing is replaced.

        Inputs: none.
        Outputs: none.
        """
        for requirement_str, error in ERROR_CASE_LIST:
            with self.subTest(requirement_str=requirement_str,
                              error=str(error)):
                view = FakeView([FIRST_PATH_STR, SECOND_PATH_STR], [True])
                controller = self.open_first_file(
                    view, {SECOND_PATH_STR: error})
                controller.open_file_requested()
                self.assertIs(controller.current_file, self.first_file)
                self.assertEqual(view.shown_name_list, ["Time", "a", "b"])
                self.assertEqual(view.call_list, [
                    "ask_open_file_path", "ask_replace_file",
                    *LOADING_CALL_LIST, "show_file_open_error",
                    "finish_open_file_button"])
                self.assertFalse(view.loading_shown_b)
                self.assertEqual(view.error_message_list, [str(error)])
                self.assertEqual(self.listener_call_list, [])

    @covers("LLFR-00008", "LLFR-00010", "LLFR-00003")
    def test_unexpected_error_is_reported_not_raised(self) -> None:
        """An unexpected loader exception shows an error box, no crash.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR, SECOND_PATH_STR], [True])
        controller = self.open_first_file(
            view, {SECOND_PATH_STR: ValueError("strange failure")})
        controller.open_file_requested()
        self.assertIs(controller.current_file, self.first_file)
        self.assertEqual(len(view.error_message_list), 1)
        message_str = view.error_message_list[0]
        self.assertIn("could not be read", message_str)
        self.assertIn("strange failure", message_str)
        self.assertIn(SECOND_PATH_STR, message_str)
        # LLFR-00418: the indication is removed before the box.
        self.assertEqual(view.call_list, [
            "ask_open_file_path", "ask_replace_file", *LOADING_CALL_LIST,
            "show_file_open_error", "finish_open_file_button"])
        self.assertEqual(self.listener_call_list, [])

    @covers("LLFR-00013", "LLFR-00017", "LLFR-00054", "HLFR-00010",
            "LLFR-00328", "LLFR-00418")
    def test_replace_accepted_opens_new_file(self) -> None:
        """Yes in the confirmation replaces the file and its list.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR, SECOND_PATH_STR], [True])
        controller = self.open_first_file(
            view, {SECOND_PATH_STR: self.second_file})
        controller.open_file_requested()
        self.assertIs(controller.current_file, self.second_file)
        self.assertEqual(view.shown_name_list, ["Time", "c"])
        self.assertEqual(view.call_list, [
            "ask_open_file_path", "ask_replace_file", *LOADING_CALL_LIST,
            "show_signal_names", "finish_open_file_button"])
        self.assertEqual(self.listener_call_list,
                         [(self.second_file, True)])

    @covers("LLFR-00014", "HLFR-00010", "LLFR-00003", "LLFR-00010",
            "LLFR-00328", "LLFR-00418")
    def test_replace_declined_keeps_current_file(self) -> None:
        """No in the confirmation keeps the file; nothing is read.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR, SECOND_PATH_STR], [False])
        controller = self.open_first_file(
            view, {SECOND_PATH_STR: self.second_file})
        controller.open_file_requested()
        self.assertIs(controller.current_file, self.first_file)
        self.assertEqual(view.shown_name_list, ["Time", "a", "b"])
        self.assertEqual(view.call_list, [
            "ask_open_file_path", "ask_replace_file",
            "finish_open_file_button"])
        # LLFR-00014: the selected file is not read, no indication.
        self.assertEqual(self.loader.loaded_path_list, [FIRST_PATH_STR])
        self.assertEqual(view.loading_text_list, ["Loading..."])
        self.assertEqual(self.listener_call_list, [])

    @covers("LLFR-00013", "LLFR-00017", "HLFR-00010")
    def test_reopening_same_path_asks_and_replaces(self) -> None:
        """Opening a file while one is open always asks, even same path.

        Inputs: none.
        Outputs: none.
        """
        reloaded_file = build_signal_file(FIRST_PATH_STR, ["a", "b", "z"])
        view = FakeView([FIRST_PATH_STR, FIRST_PATH_STR], [True])
        controller = self.build_controller(view, {})
        self.loader.result_dict[FIRST_PATH_STR] = self.first_file
        controller.open_file_requested()
        self.loader.result_dict[FIRST_PATH_STR] = reloaded_file
        controller.open_file_requested()
        self.assertEqual(view.call_list.count("ask_replace_file"), 1)
        self.assertIs(controller.current_file, reloaded_file)
        self.assertEqual(view.shown_name_list, ["Time", "a", "b", "z"])

    @covers("LLFR-00013", "LLFR-00014", "LLFR-00017")
    def test_decline_then_accept_sequence(self) -> None:
        """A declined replace does not stop a later accepted one.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR, SECOND_PATH_STR, SECOND_PATH_STR],
                        [False, True])
        controller = self.open_first_file(
            view, {SECOND_PATH_STR: self.second_file})
        controller.open_file_requested()
        self.assertIs(controller.current_file, self.first_file)
        controller.open_file_requested()
        self.assertIs(controller.current_file, self.second_file)
        self.assertEqual(view.shown_name_list, ["Time", "c"])
        self.assertEqual(self.listener_call_list,
                         [(self.second_file, True)])

    @covers("LLFR-00003")
    def test_button_finished_when_view_raises(self) -> None:
        """The button is finished even if a view call raises.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR])

        def failing_show(signal_name_list: list) -> None:
            """Raise as a broken view would.

            Inputs:
                signal_name_list: ignored.
            Outputs: none; always raises RuntimeError.
            """
            view.call_list.append("show_signal_names")
            raise RuntimeError("view failure")

        view.show_signal_names = failing_show
        controller = self.build_controller(
            view, {FIRST_PATH_STR: self.first_file})
        with self.assertRaises(RuntimeError):
            controller.open_file_requested()
        self.assertEqual(view.call_list[-1], "finish_open_file_button")

    @covers("LLFR-00013")
    def test_every_listener_is_notified(self) -> None:
        """All registered listeners receive the opened file in order.

        Inputs: none.
        Outputs: none.
        """
        order_list = []
        view = FakeView([FIRST_PATH_STR])
        controller = self.build_controller(
            view, {FIRST_PATH_STR: self.first_file})
        controller.add_file_opened_listener(
            lambda signal_file, replaced_b: order_list.append(
                ("second", signal_file, replaced_b)))
        controller.open_file_requested()
        self.assertEqual(self.listener_call_list,
                         [(self.first_file, False)])
        self.assertEqual(order_list, [("second", self.first_file, False)])

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

    @covers("LLFR-00204", "LLFR-00005")
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

    @covers("LLFR-00204")
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
            "LLFR-00014")
    def test_folder_follows_only_successful_opens(self) -> None:
        """Cancel, failed open and declined replace keep the folder.

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
                         ""], [True, True, False, True])
        controller = FileController(view, loader, "/start")
        for _ in range(8):
            controller.open_file_requested()
        self.assertEqual(view.start_folder_list, [
            "/start", "/start", "/data/a", "/data/a", "/data/a",
            "/data/a", "/data/a", "/data/b"])
        self.assertIs(controller.current_file, second_file)


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
            "LLFR-00010", "LLFR-00011", "LLFR-00012", "LLFR-00013",
            "LLFR-00014", "LLFR-00017", "HLFR-00010")
    def test_real_messages_reach_the_view(self) -> None:
        """Real files open, fail with the loader's messages, or replace.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([self.valid_path_str, self.no_time_path_str,
                         self.bad_value_path_str, self.text_path_str,
                         self.missing_path_str, self.other_path_str,
                         self.other_path_str],
                        [True, True, True, True, False, True])
        controller = FileController(view)
        controller.open_file_requested()
        self.assertEqual(view.shown_name_list, ["Time", "speed", "force"])
        for _ in range(4):
            controller.open_file_requested()
        self.assertEqual(len(view.error_message_list), 4)
        no_time_str, bad_value_str, text_str, missing_str = (
            view.error_message_list)
        self.assertIn("one_signal.csv", no_time_str)
        self.assertIn("at least two signals", no_time_str)
        self.assertIn("could not be read", bad_value_str)
        self.assertIn("abc", bad_value_str)
        self.assertIn("not supported", text_str)
        self.assertIn("could not be accessed", missing_str)
        self.assertEqual(view.shown_name_list, ["Time", "speed", "force"])
        # HLFR-00010: each failed file was confirmed before being read.
        self.assertEqual(view.call_list.count("ask_replace_file"), 4)
        controller.open_file_requested()
        self.assertEqual(controller.current_file.path_str,
                         self.valid_path_str)
        controller.open_file_requested()
        self.assertEqual(controller.current_file.path_str,
                         self.other_path_str)
        self.assertEqual(view.shown_name_list, ["Time", "pressure"])
        self.assertEqual(view.call_list.count("finish_open_file_button"),
                         7)
        self.assertNotIn("ask_time_signal_name", view.call_list)
        self.assertEqual(view.time_signal_name_list, ["Time", "Time"])

    @covers("LLFR-00325", "LLFR-00326", "LLFR-00328", "LLFR-00329",
            "LLFR-00068", "HLFR-00070", "HLFR-00007")
    def test_real_file_without_time_asks_for_it(self) -> None:
        """A real CSV whose x column is "t_s" opens after the choice.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_file(
            "x_axis.csv", "speed,t_s,force\n5,0,2\n4,0.5,4\n3,2,1\n")
        view = FakeView([path_str], [], [["speed", "force", "t_s"]])
        controller = FileController(view)
        controller.open_file_requested()
        self.assertEqual(view.call_list, [
            "ask_open_file_path", *LOADING_CALL_LIST,
            "ask_time_signal_name", "show_signal_names",
            "finish_open_file_button"])
        self.assertEqual(len(view.time_reason_list), 2)
        for reason_str in view.time_reason_list:
            self.assertIn("must always increase", reason_str)
        self.assertEqual(controller.current_file.time_signal_name_str,
                         "t_s")
        np.testing.assert_array_equal(controller.current_file.time_array,
                                      [0.0, 0.5, 2.0])
        self.assertEqual(view.shown_name_list, ["speed", "t_s", "force"])
        self.assertEqual(view.time_signal_name_list, ["t_s"])


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


class LoadingStateView(FakeView):
    """FakeView that also records whether the indication was shown.

    Inputs: as FakeView.
    Attributes:
        state_list: (call name, loading_shown_b) for every dialog, box
            and window the controller showed.
    """

    def __init__(self, *argument_tuple) -> None:
        """Start like FakeView with no recorded state.

        Inputs:
            argument_tuple: the FakeView arguments.
        Outputs: none.
        """
        super().__init__(*argument_tuple)
        self.state_list = []

    def ask_replace_file(self) -> bool:
        """Record the indication state, then answer as FakeView.

        Inputs: none.
        Outputs: the next scripted answer.
        """
        self.state_list.append(("ask_replace_file", self.loading_shown_b))
        return super().ask_replace_file()

    def show_file_open_error(self, message_str: str) -> None:
        """Record the indication state, then record the error.

        Inputs:
            message_str: the message of the File Open Error box.
        Outputs: none.
        """
        self.state_list.append(("show_file_open_error",
                                self.loading_shown_b))
        super().show_file_open_error(message_str)

    def ask_time_signal_name(self, *argument_tuple):
        """Record the indication state, then answer as FakeView.

        Inputs:
            argument_tuple: the window arguments.
        Outputs: the scripted answer.
        """
        self.state_list.append(("ask_time_signal_name",
                                self.loading_shown_b))
        return super().ask_time_signal_name(*argument_tuple)


class OpeningOrderTest(unittest.TestCase):
    """The order of LLFR-00328 and the indication of LLFR-00418."""

    def setUp(self) -> None:
        """Prepare a file with Time, one without, and a recorder.

        Inputs: none.
        Outputs: none.
        """
        self.first_file = build_signal_file(FIRST_PATH_STR, ["a", "b"])
        self.second_file = build_signal_file(SECOND_PATH_STR, ["c"])
        self.listener_call_list = []

    def build_controller(self, view, result_dict: dict) -> FileController:
        """Build a controller whose loader records the indication state.

        Inputs:
            view: the LoadingStateView.
            result_dict: path -> SignalFile or exception.
        Outputs: the FileController with the first file not yet open.
        """
        scripted_loader = ScriptedLoader(result_dict)

        def recording_loader(path_str: str) -> SignalFile:
            """Record the indication state, then load as scripted.

            Inputs:
                path_str: the path to open.
            Outputs: the scripted SignalFile; raises the scripted error.
            """
            view.state_list.append(("load", view.loading_shown_b))
            return scripted_loader(path_str)

        self.loader = scripted_loader
        controller = FileController(view, recording_loader, "/start")
        controller.add_file_opened_listener(
            lambda signal_file, replaced_b: self.listener_call_list.append(
                (signal_file, replaced_b)))
        return controller

    def open_first(self, view, result_dict: dict) -> FileController:
        """Build a controller and open FIRST_PATH_STR, then reset logs.

        Inputs:
            view: the LoadingStateView; its first path is FIRST_PATH_STR.
            result_dict: the results of the other paths.
        Outputs: the FileController with the first file open.
        """
        result_dict = dict(result_dict)
        result_dict[FIRST_PATH_STR] = self.first_file
        controller = self.build_controller(view, result_dict)
        controller.open_file_requested()
        self.assertIs(controller.current_file, self.first_file)
        view.call_list.clear()
        view.state_list.clear()
        view.loading_text_list.clear()
        self.listener_call_list.clear()
        return controller

    def assert_previous_file_kept(self, controller, view) -> None:
        """Check that the first file, its list and folder are unchanged.

        Inputs:
            controller: the FileController.
            view: the LoadingStateView.
        Outputs: none.
        """
        # LLFR-00010: the previous file, its list and, since no listener
        # ran, its plots, synthetic signals, undo history and file name
        # row (LLFR-00363) are unchanged.
        self.assertIs(controller.current_file, self.first_file)
        self.assertEqual(view.shown_name_list, ["Time", "a", "b"])
        self.assertEqual(view.time_signal_name_list, ["Time"])
        self.assertNotIn("show_signal_names", view.call_list)
        self.assertEqual(self.listener_call_list, [])
        self.assertEqual(controller.dialog_folder_str, "/data")
        self.assertFalse(view.loading_shown_b)

    @covers("LLFR-00418", "LLFR-00328", "LLFR-00006")
    def test_first_file_read_under_the_indication(self) -> None:
        """The first file is read while "Loading..." is shown.

        Inputs: none.
        Outputs: none.
        """
        view = LoadingStateView([FIRST_PATH_STR])
        controller = self.build_controller(
            view, {FIRST_PATH_STR: self.first_file})
        controller.open_file_requested()
        self.assertEqual(view.state_list, [("load", True)])
        self.assertEqual(view.loading_text_list, ["Loading..."])
        self.assertFalse(view.loading_shown_b)
        self.assertNotIn("ask_replace_file", view.call_list)
        self.assertIs(controller.current_file, self.first_file)

    @covers("LLFR-00418", "LLFR-00328", "LLFR-00013", "HLFR-00010")
    def test_replace_accepted_order(self) -> None:
        """Confirmation without indication, then the read under it.

        Inputs: none.
        Outputs: none.
        """
        view = LoadingStateView([FIRST_PATH_STR, SECOND_PATH_STR], [True])
        controller = self.open_first(
            view, {SECOND_PATH_STR: self.second_file})
        controller.open_file_requested()
        self.assertEqual(view.state_list, [("ask_replace_file", False),
                                           ("load", True)])
        self.assertEqual(view.call_list, [
            "ask_open_file_path", "ask_replace_file", *LOADING_CALL_LIST,
            "show_signal_names", "finish_open_file_button"])
        self.assertIs(controller.current_file, self.second_file)
        self.assertEqual(self.listener_call_list, [(self.second_file, True)])

    @covers("LLFR-00014", "LLFR-00328", "LLFR-00418", "LLFR-00010")
    def test_replace_declined_order(self) -> None:
        """Declined: the file is not read and no indication is shown.

        Inputs: none.
        Outputs: none.
        """
        view = LoadingStateView([FIRST_PATH_STR, SECOND_PATH_STR], [False])
        controller = self.open_first(
            view, {SECOND_PATH_STR: self.second_file})
        controller.open_file_requested()
        self.assertEqual(view.state_list, [("ask_replace_file", False)])
        self.assertEqual(view.loading_text_list, [])
        self.assertEqual(self.loader.loaded_path_list, [FIRST_PATH_STR])
        self.assertEqual(view.error_message_list, [])
        self.assert_previous_file_kept(controller, view)

    @covers("LLFR-00008", "LLFR-00009", "LLFR-00011", "LLFR-00012",
            "LLFR-00010", "LLFR-00013", "LLFR-00328", "LLFR-00418")
    def test_error_after_proceeding_order(self) -> None:
        """Every File Open Error after Yes: box after the indication.

        Inputs: none.
        Outputs: none.
        """
        for requirement_str, error in ERROR_CASE_LIST + [
                ("LLFR-00008", RuntimeError("boom"))]:
            with self.subTest(requirement_str=requirement_str,
                              error=str(error)):
                view = LoadingStateView([FIRST_PATH_STR, SECOND_PATH_STR],
                                        [True])
                controller = self.open_first(view, {SECOND_PATH_STR: error})
                controller.open_file_requested()
                self.assertEqual(view.state_list, [
                    ("ask_replace_file", False), ("load", True),
                    ("show_file_open_error", False)])
                self.assertEqual(len(view.error_message_list), 1)
                self.assertIn(str(error), view.error_message_list[0])
                self.assertEqual(view.call_list[-1],
                                 "finish_open_file_button")
                self.assert_previous_file_kept(controller, view)

    @covers("LLFR-00011", "LLFR-00328", "LLFR-00418", "LLFR-00010")
    def test_unsupported_format_after_proceeding(self) -> None:
        """A real .txt file after Yes gives the unsupported format box.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as folder_str:
            text_path_str = os.path.join(folder_str, "notes.txt")
            with open(text_path_str, "w", encoding="utf-8") as file:
                file.write("hello")
            view = LoadingStateView([FIRST_PATH_STR, text_path_str], [True])
            controller = self.open_first(view, {})
            self.loader.result_dict[text_path_str] = None

            def real_or_scripted(path_str: str) -> SignalFile:
                """Use the real loader for the text file.

                Inputs:
                    path_str: the path to open.
                Outputs: the loaded SignalFile; raises FileOpenError.
                """
                view.state_list.append(("load", view.loading_shown_b))
                return load_signal_file(path_str)

            controller.load_function = real_or_scripted
            controller.open_file_requested()
        self.assertEqual(view.state_list, [
            ("ask_replace_file", False), ("load", True),
            ("show_file_open_error", False)])
        self.assertIn("not supported", view.error_message_list[0])
        self.assert_previous_file_kept(controller, view)

    @covers("LLFR-00327", "LLFR-00328", "LLFR-00418", "LLFR-00010",
            "LLFR-00325")
    def test_time_window_cancelled_after_proceeding(self) -> None:
        """Yes, read under the indication, window without it, cancel.

        Inputs: none.
        Outputs: none.
        """
        view = LoadingStateView([FIRST_PATH_STR, SECOND_PATH_STR], [True],
                                [[]])
        controller = self.open_first(
            view, {SECOND_PATH_STR: build_no_time_file(SECOND_PATH_STR)})
        controller.open_file_requested()
        self.assertEqual(view.state_list, [
            ("ask_replace_file", False), ("load", True),
            ("ask_time_signal_name", False)])
        self.assertEqual(view.error_message_list, [])
        self.assert_previous_file_kept(controller, view)

    @covers("LLFR-00326", "LLFR-00328", "LLFR-00418", "LLFR-00013")
    def test_time_window_confirmed_after_proceeding(self) -> None:
        """Yes, read, window, then only now the file is replaced.

        Inputs: none.
        Outputs: none.
        """
        no_time_file = build_no_time_file(SECOND_PATH_STR)
        view = LoadingStateView([FIRST_PATH_STR, SECOND_PATH_STR], [True],
                                [["t_s"]])
        controller = self.open_first(view, {SECOND_PATH_STR: no_time_file})
        controller.open_file_requested()
        self.assertEqual(view.state_list, [
            ("ask_replace_file", False), ("load", True),
            ("ask_time_signal_name", False)])
        self.assertEqual(view.call_list[-2:], [
            "show_signal_names", "finish_open_file_button"])
        self.assertIs(controller.current_file, no_time_file)
        self.assertEqual(self.listener_call_list, [(no_time_file, True)])

    @covers("LLFR-00418")
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


class TimeSignalWindowTest(unittest.TestCase):
    """The time signal window in the open-file flow (HLFR-00070)."""

    def setUp(self) -> None:
        """Prepare a file with Time, a file without, and a recorder.

        Inputs: none.
        Outputs: none.
        """
        self.first_file = build_signal_file(FIRST_PATH_STR, ["a", "b"])
        self.no_time_file = build_no_time_file(SECOND_PATH_STR)
        self.listener_call_list = []

    def build_controller(self, view, result_dict: dict) -> FileController:
        """Build a FileController with a scripted loader and listener.

        Inputs:
            view: the fake view.
            result_dict: path -> SignalFile or exception.
        Outputs: the FileController.
        """
        controller = FileController(view, ScriptedLoader(result_dict))
        controller.add_file_opened_listener(
            lambda signal_file, replaced_b: self.listener_call_list.append(
                (signal_file, replaced_b)))
        return controller

    @covers("LLFR-00325", "LLFR-00326", "HLFR-00070", "LLFR-00054")
    def test_window_shown_when_no_time_signal(self) -> None:
        """The window lists every signal; the choice is the time signal.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([SECOND_PATH_STR], [], [["t_s"]])
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
        self.assertIs(controller.current_file, self.no_time_file)
        self.assertEqual(self.no_time_file.time_signal_name_str, "t_s")
        np.testing.assert_array_equal(self.no_time_file.time_array,
                                      [0.0, 0.5, 1.5])
        self.assertEqual(view.shown_name_list, ["Down", "t_s", "Flat"])
        self.assertEqual(view.time_signal_name_list, ["t_s"])
        self.assertEqual(self.listener_call_list,
                         [(self.no_time_file, False)])

    @covers("LLFR-00325", "LLFR-00285", "LLFR-00098", "LLFR-00101",
            "LLFR-00102")
    def test_window_search_uses_signal_list_rules(self) -> None:
        """The window's search finds names like the signal list search.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([SECOND_PATH_STR], [], [[]])
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
        view = FakeView([SECOND_PATH_STR], [], [["Down", "Flat", "t_s"]])
        controller = self.build_controller(
            view, {SECOND_PATH_STR: self.no_time_file})
        controller.open_file_requested()
        self.assertEqual(len(view.time_reason_list), 2)
        self.assertIn("'Down'", view.time_reason_list[0])
        self.assertIn("'Flat'", view.time_reason_list[1])
        for reason_str in view.time_reason_list:
            self.assertIn("must always increase", reason_str)
        self.assertEqual(controller.current_file.time_signal_name_str,
                         "t_s")

    @covers("LLFR-00329")
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

    @covers("LLFR-00327", "HLFR-00070", "LLFR-00003", "LLFR-00010",
            "LLFR-00328", "LLFR-00418", "LLFR-00363")
    def test_cancel_keeps_the_current_file(self) -> None:
        """Proceeding, then cancelling the window, opens nothing.

        Inputs: none.
        Outputs: none.
        """
        view = FakeView([FIRST_PATH_STR, SECOND_PATH_STR], [True], [[]])
        controller = self.build_controller(
            view, {FIRST_PATH_STR: self.first_file,
                   SECOND_PATH_STR: self.no_time_file})
        controller.open_file_requested()
        view.call_list.clear()
        self.listener_call_list.clear()
        controller.open_file_requested()
        self.assertIs(controller.current_file, self.first_file)
        self.assertEqual(view.shown_name_list, ["Time", "a", "b"])
        self.assertEqual(view.error_message_list, [])
        # LLFR-00328, LLFR-00418: confirmation, read with the indication,
        # indication removed, then the window.
        self.assertEqual(view.call_list, [
            "ask_open_file_path", "ask_replace_file", *LOADING_CALL_LIST,
            "ask_time_signal_name", "finish_open_file_button"])
        self.assertEqual(self.listener_call_list, [])
        self.assertEqual(view.replace_answer_list, [])
        # LLFR-00204: the cancelled file does not move the dialog folder.
        self.assertEqual(controller.dialog_folder_str,
                         os.path.dirname(os.path.abspath(FIRST_PATH_STR)))

    @covers("LLFR-00328", "HLFR-00010", "LLFR-00013", "LLFR-00014",
            "LLFR-00418")
    def test_replace_confirmation_comes_before_the_window(self) -> None:
        """The confirmation is asked first; declined, nothing is read.

        Inputs: none.
        Outputs: none.
        """
        for answer_b in (False, True):
            with self.subTest(answer_b=answer_b):
                no_time_file = build_no_time_file(SECOND_PATH_STR)
                view = FakeView([FIRST_PATH_STR, SECOND_PATH_STR],
                                [answer_b], [["t_s"]])
                controller = self.build_controller(
                    view, {FIRST_PATH_STR: self.first_file,
                           SECOND_PATH_STR: no_time_file})
                controller.open_file_requested()
                view.call_list.clear()
                controller.open_file_requested()
                expected_list = ["ask_open_file_path", "ask_replace_file"]
                if answer_b:
                    expected_list += [*LOADING_CALL_LIST,
                                      "ask_time_signal_name",
                                      "show_signal_names"]
                expected_list.append("finish_open_file_button")
                self.assertEqual(view.call_list, expected_list)
                expected_file = no_time_file if answer_b else self.first_file
                self.assertIs(controller.current_file, expected_file)

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

    @covers("LLFR-00331", "LLFR-00324", "HLFR-00072", "HLFR-00070")
    def test_file_with_time_never_shows_the_window(self) -> None:
        """Opening (and reopening) a file with a Time match asks nothing.

        Inputs: none.
        Outputs: none.
        """
        lowercase_file = SignalFile(SECOND_PATH_STR, {
            "a": np.arange(3.0), "TIME": np.arange(3.0),
            "time": np.arange(3.0)})
        view = FakeView([FIRST_PATH_STR, SECOND_PATH_STR, FIRST_PATH_STR],
                        [True, True])
        controller = self.build_controller(
            view, {FIRST_PATH_STR: self.first_file,
                   SECOND_PATH_STR: lowercase_file})
        for _ in range(3):
            controller.open_file_requested()
        self.assertNotIn("ask_time_signal_name", view.call_list)
        self.assertEqual(view.time_signal_name_list,
                         ["Time", "TIME", "Time"])
        self.assertIs(controller.current_file, self.first_file)


if __name__ == "__main__":
    unittest.main()
