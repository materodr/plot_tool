"""Tests for the signal list controller with a fake view (no Qt needed).

The real search function (model.signal_search.search_signals) is used,
so the shown lists are the ones the app shows.
"""

import os
import unittest

import numpy as np

from tests.support import covers

from controller.file_controller import FileController
from controller.signal_list_controller import (
    SignalListController, file_name_from_path)
from model.data_files import DataFileSet
from model.signal_file import SignalFile
from model.signal_search import NO_MATCH_TEXT_STR

FIRST_NAME_LIST = [
    "Time", "Engine_Speed", "Pressure", "Sine_3Hz",
    "mateus_soares_rodrigues 2025", "mateus_soares_rodrigues 2026"]
SECOND_NAME_LIST = ["Time", "pressure_out", "voltage"]


def make_signal_file(name_list: list) -> SignalFile:
    """Build a SignalFile whose signals have the given names.

    Inputs:
        name_list: the signal names, in file order (with "Time").
    Outputs: the SignalFile; every signal has 3 samples.
    """
    signal_dict = {name_str: np.arange(3, dtype=float)
                   for name_str in name_list}
    return SignalFile("test.csv", signal_dict)


class FakeFileController:
    """Stand-in for FileController that keeps the listeners."""

    def __init__(self) -> None:
        """Start with no listeners.

        Inputs: none.
        Outputs: none.
        """
        self.listener_list = []

    def add_file_opened_listener(self, listener) -> None:
        """Record a file-opened listener.

        Inputs:
            listener: function taking (signal_file, replaced_b).
        Outputs: none.
        """
        self.listener_list.append(listener)

    def open(self, signal_file, replaced_b: bool) -> None:
        """Call every listener as the real controller does.

        Inputs:
            signal_file: the SignalFile to report as opened.
            replaced_b: True when it replaces another file.
        Outputs: none.
        """
        for listener in self.listener_list:
            listener(signal_file, replaced_b)


class FakeSignalListView:
    """Stand-in for MainWindow with the signal list facade.

    Like the real search box, clear_search reports the change of text
    to the handler when the box had text.

    Attributes:
        search_text_str: the text in the fake search box.
        shown_name_list: the names last shown in the list.
        no_match_tuple: last (visible_b, message_str) given to
            show_no_match_message, or () before any call.
        call_list: the names of the facade calls, in order.
        synthetic_name_set: the names last given as synthetic signals.
        fft_name_set: the names last given as FFT signals.
        file_name_str: the name last shown in the file name line.
        file_name_call_count_i: how many times the line was set.
    """

    def __init__(self) -> None:
        """Start with an empty box, an empty list and no handler.

        Inputs: none.
        Outputs: none.
        """
        self.search_text_handler = None
        self.search_text_str = ""
        self.shown_name_list = []
        self.no_match_tuple = ()
        self.call_list = []
        self.synthetic_name_set = set()
        self.fft_name_set = set()
        self.selection_clear_count_i = 0
        self.file_name_str = ""
        self.file_name_call_count_i = 0
        self.group_list = []
        self.file_row_list = []
        self.no_match_row_list = []

    def set_time_signal_names(self, name_list: list) -> None:
        """Record the time signal names (LLFR-00332).

        Not added to call_list, so that the call order tests of the
        search are not affected.

        Inputs:
            name_list: the time signal of each open data file.
        Outputs: none.
        """
        self.time_signal_name_list = list(name_list)

    def set_search_text_handler(self, handler) -> None:
        """Record the search box handler.

        Inputs:
            handler: function taking the new text.
        Outputs: none.
        """
        self.search_text_handler = handler

    def type_text(self, text_str: str) -> None:
        """Put a text in the box and report it, as typing does.

        Inputs:
            text_str: the new text of the box.
        Outputs: none.
        """
        if text_str == self.search_text_str:
            return
        self.search_text_str = text_str
        self.search_text_handler(text_str)

    def show_signal_groups(self, group_list: list) -> None:
        """Record the groups shown in the list, as the real list does.

        Inputs:
            group_list: (file number, row text, names, no-match text)
                per group, in list order.
        Outputs: none. shown_name_list holds every shown name, file
            after file; file_row_list the texts of the file name rows;
            no_match_row_list the rows below which "No matching
            signals" is shown; no_match_tuple (shown_b, text).
        """
        self.call_list.append("show_signal_groups")
        self.group_list = [tuple(group) for group in group_list]
        self.shown_name_list = [name_str for _, _, name_list, _
                                in group_list for name_str in name_list]
        self.file_row_list = [row_str for _, row_str, _, _ in group_list
                              if row_str]
        self.no_match_row_list = [row_str for _, row_str, _, no_match_str
                                  in group_list if no_match_str]
        no_match_text_list = [no_match_str for _, _, _, no_match_str
                              in group_list if no_match_str]
        self.no_match_tuple = (bool(no_match_text_list), NO_MATCH_TEXT_STR)
        self.file_name_str = ", ".join(self.file_row_list)
        self.file_name_call_count_i += 1

    def set_signal_kinds(self, synthetic_name_set: set,
                         fft_name_set: set) -> None:
        """Record which names are synthetic and which are FFT signals.

        Not added to call_list, so that the call order tests of the
        search are not affected.

        Inputs:
            synthetic_name_set: the synthetic signal names (italics).
            fft_name_set: the FFT signal names among them.
        Outputs: none.
        """
        self.synthetic_name_set = set(synthetic_name_set)
        self.fft_name_set = set(fft_name_set)

    def no_match_shown(self) -> bool:
        """Tell whether the no-match message is shown.

        Inputs: none.
        Outputs: True when the last call showed the message.
        """
        return bool(self.no_match_tuple) and self.no_match_tuple[0]

    def clear_search(self) -> None:
        """Empty the box, reporting the change like a QLineEdit.

        Inputs: none.
        Outputs: none.
        """
        self.call_list.append("clear_search")
        self.type_text("")

    def clear_signal_selection(self) -> None:
        """Record that the selection of the list was cleared.

        Not added to call_list, so that the call order tests of the
        search are not affected.

        Inputs: none.
        Outputs: none.
        """
        self.selection_clear_count_i += 1

    def rename_shown_signal(self, old_name_str: str,
                            new_name_str: str) -> None:
        """Rename a shown name in place, as the real list does.

        Inputs:
            old_name_str: the previous name.
            new_name_str: the new name.
        Outputs: none.
        """
        self.shown_name_list = [
            new_name_str if name_str == old_name_str else name_str
            for name_str in self.shown_name_list]


class FakeFileView(FakeSignalListView):
    """Fake view that also offers what the real FileController needs.

    Attributes:
        path_str: the path the fake file dialog returns.
        time_signal_answer_str: the answer of the time signal window.
    """

    def __init__(self) -> None:
        """Start with no path and no time signal answer.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        self.path_str = ""
        self.time_signal_answer_str = None

    def ask_time_signal_name(self, prompt_str: str, name_list: list,
                             search_function, no_match_text_str: str,
                             check_function, file_name_str: str = ""):
        """Return the prepared answer of the time signal window.

        Inputs:
            prompt_str: the text of the window (unused).
            name_list: the signals of the file (unused).
            search_function: the search of the window (unused).
            no_match_text_str: the no-match text (unused).
            check_function: the check of a chosen name (unused).
            file_name_str: the name of the file the window is for.
        Outputs: the prepared name, or None to cancel (LLFR-00327).
        """
        self.call_list.append("ask_time_signal_name")
        self.time_window_file_name_str = file_name_str
        return self.time_signal_answer_str

    def ask_open_file_path(self, start_folder_str: str) -> str:
        """Return the prepared path.

        Inputs:
            start_folder_str: the folder the dialog would show (unused).
        Outputs: the path.
        """
        return self.path_str

    def set_time_signal_name(self, name_str: str) -> None:
        """Record the time signal shown in green (LLFR-00332).

        Inputs:
            name_str: the time signal name.
        Outputs: none.
        """
        self.time_signal_name_str = name_str

    def show_refused_files_notification(self, message_str: str) -> None:
        """Record the box of the refused files (LLFR-00952).

        Inputs:
            message_str: the lines of the refused files.
        Outputs: none.
        """
        self.call_list.append("show_refused_files_notification")

    def show_open_files_limit_notification(self, message_str: str) -> None:
        """Record the box shown with 10 files open (LLFR-00892).

        Inputs:
            message_str: the sentence of the box.
        Outputs: none.
        """
        self.call_list.append("show_open_files_limit_notification")

    def show_file_open_error(self, message_str: str) -> None:
        """Ignore the error box.

        Inputs:
            message_str: the error text.
        Outputs: none.
        """
        self.call_list.append("show_file_open_error")

    def finish_open_file_button(self) -> None:
        """Ignore the button reset.

        Inputs: none.
        Outputs: none.
        """

    def show_loading_indication(self) -> None:
        """Do nothing (LLFR-00418 is tested in test_file_controller).

        Inputs: none.
        Outputs: none.
        """

    def hide_loading_indication(self) -> None:
        """Do nothing (LLFR-00418 is tested in test_file_controller).

        Inputs: none.
        Outputs: none.
        """


class SignalListControllerTestCase(unittest.TestCase):
    """Shared setup: a controller, a fake view and a fake file source."""

    def setUp(self) -> None:
        """Create the fake view, file controller and the controller.

        Inputs: none.
        Outputs: none.
        """
        self.view = FakeSignalListView()
        self.file_controller = FakeFileController()
        self.controller = SignalListController(self.view,
                                               self.file_controller)

    def open_first_file(self) -> None:
        """Open the file with FIRST_NAME_LIST as the first file.

        Inputs: none.
        Outputs: none.
        """
        self.file_controller.open(make_signal_file(FIRST_NAME_LIST), False)


class WiringTest(SignalListControllerTestCase):
    """Check the connections made by the constructor."""

    @covers("LLFR-00095")
    def test_registers_handler_and_listener(self) -> None:
        """The search handler and the file listener are registered.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.view.search_text_handler,
                         self.controller.on_search_text_changed)
        self.assertEqual(self.file_controller.listener_list,
                         [self.controller.on_file_opened])

    @covers("LLFR-00095")
    def test_custom_search_function_is_used(self) -> None:
        """The injected search function decides the shown names.

        Inputs: none.
        Outputs: none.
        """
        call_list = []

        def reverse_search(name_list: list, text_str: str) -> list:
            """Record the call and return the names reversed.

            Inputs:
                name_list: all names.
                text_str: the typed text.
            Outputs: the names in reverse order.
            """
            call_list.append((list(name_list), text_str))
            return list(reversed(name_list))

        view = FakeSignalListView()
        file_controller = FakeFileController()
        SignalListController(view, file_controller, reverse_search)
        file_controller.open(make_signal_file(["Time", "a"]), False)
        view.type_text("x")
        self.assertEqual(call_list[-1], (["Time", "a"], "x"))
        self.assertEqual(view.shown_name_list, ["a", "Time"])


class FilterTest(SignalListControllerTestCase):
    """Check the filtering while typing (LLFR-00095 to LLFR-00097)."""

    @covers("LLFR-00095", "LLFR-00098", "LLFR-00099", "LLFR-00100",
            "LLFR-00101", "LLFR-00105", "HLFR-00033", "HLFR-00034",
            "LLFR-00566", "LLFR-00567")
    def test_every_change_filters_again(self) -> None:
        """Each new text shows only the matching names.

        Inputs: none.
        Outputs: none.
        """
        self.open_first_file()
        expected_dict = {
            "e": ["Engine_Speed", "Time", "Pressure", "Sine_3Hz",
                  "mateus_soares_rodrigues 2025",
                  "mateus_soares_rodrigues 2026"],
            "enginespeed": ["Engine_Speed"],
            "ENGINE": ["Engine_Speed"],
            "presure": ["Pressure"],
            "sine_2hz": ["Sine_3Hz"],
            "mate so 25": ["mateus_soares_rodrigues 2025"],
            "26 mateus": ["mateus_soares_rodrigues 2026"],
            "speed": ["Engine_Speed"],
        }
        for text_str, expected_list in expected_dict.items():
            with self.subTest(text_str=text_str):
                self.view.type_text(text_str)
                self.assertEqual(self.view.shown_name_list, expected_list)
                self.assertEqual(self.view.no_match_tuple,
                                 (False, NO_MATCH_TEXT_STR))

    @covers("LLFR-00095")
    def test_each_keystroke_updates_the_list(self) -> None:
        """Typing one character at a time narrows the list each time.

        Inputs: none.
        Outputs: none.
        """
        self.open_first_file()
        shown_count_list = []
        typed_str = ""
        for character_str in "press":
            typed_str += character_str
            self.view.type_text(typed_str)
            shown_count_list.append(list(self.view.shown_name_list))
        self.assertEqual(shown_count_list[0],
                         ["Pressure", "Engine_Speed"])
        # "pres" also matches "...soares..." within one typo.
        self.assertEqual(shown_count_list[3],
                         ["Pressure", "mateus_soares_rodrigues 2025",
                          "mateus_soares_rodrigues 2026"])
        self.assertEqual(shown_count_list[-1], ["Pressure"])
        # One call by the file open (the listener), one per key.
        self.assertEqual(self.view.call_list.count("show_signal_groups"),
                         1 + len("press"))

    @covers("LLFR-00102")
    def test_model_order_is_kept(self) -> None:
        """Names are shown in the three groups of the model.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Time", "outlet_pressure", "pressure_in",
                     "presure_typo", "Pressure"]
        self.file_controller.open(make_signal_file(name_list), False)
        self.view.type_text("pressure")
        # Starts with the word, then contains it, then typo matches.
        self.assertEqual(self.view.shown_name_list,
                         ["pressure_in", "Pressure", "outlet_pressure",
                          "presure_typo"])

    @covers("LLFR-00096", "LLFR-00054")
    def test_empty_or_spaces_shows_all(self) -> None:
        """An empty or spaces-only text shows all names, Time included.

        Inputs: none.
        Outputs: none.
        """
        self.open_first_file()
        for text_str in ("speed", "", "   ", "speed", " "):
            self.view.type_text(text_str)
        self.assertEqual(self.view.shown_name_list, FIRST_NAME_LIST)
        self.assertIn("Time", self.view.shown_name_list)
        self.assertFalse(self.view.no_match_shown())
        self.view.type_text("")
        self.assertEqual(self.view.shown_name_list, FIRST_NAME_LIST)
        self.assertFalse(self.view.no_match_shown())

    @covers("LLFR-00054")
    def test_time_can_be_found(self) -> None:
        """The time signal is found by the search like other names.

        Inputs: none.
        Outputs: none.
        """
        self.open_first_file()
        self.view.type_text("time")
        self.assertEqual(self.view.shown_name_list, ["Time"])

    @covers("LLFR-00097", "LLFR-00565")
    def test_no_match_shows_empty_list_and_message(self) -> None:
        """No match gives an empty list and "No matching signals".

        Inputs: none.
        Outputs: none.
        """
        self.open_first_file()
        self.view.type_text("xyzw")
        self.assertEqual(self.view.shown_name_list, [])
        self.assertEqual(self.view.no_match_tuple,
                         (True, "No matching signals"))
        self.assertEqual(NO_MATCH_TEXT_STR, "No matching signals")

    @covers("LLFR-00097", "LLFR-00096")
    def test_message_hidden_again_on_match_or_empty(self) -> None:
        """The message goes away when the text matches or is empty.

        Inputs: none.
        Outputs: none.
        """
        self.open_first_file()
        self.view.type_text("xyzw")
        self.assertTrue(self.view.no_match_shown())
        self.view.type_text("pressure")
        self.assertFalse(self.view.no_match_shown())
        self.assertEqual(self.view.shown_name_list, ["Pressure"])
        self.view.type_text("qqqq")
        self.assertTrue(self.view.no_match_shown())
        self.view.type_text("")
        self.assertFalse(self.view.no_match_shown())
        self.assertEqual(self.view.shown_name_list, FIRST_NAME_LIST)

    @covers("LLFR-00097")
    def test_no_message_without_file(self) -> None:
        """Before a file is opened the list stays empty, no message.

        Inputs: none.
        Outputs: none.
        """
        self.view.type_text("speed")
        self.assertEqual(self.view.shown_name_list, [])
        self.assertFalse(self.view.no_match_shown())
        self.view.type_text("")
        self.assertEqual(self.view.shown_name_list, [])
        self.assertFalse(self.view.no_match_shown())


class FileOpenedTest(SignalListControllerTestCase):
    """Check the list after a file is opened (LLFR-00104, LLFR-00917)."""

    @covers("LLFR-00054", "LLFR-00096")
    def test_first_open_shows_all_names(self) -> None:
        """With an empty box, the first file shows all its names.

        Inputs: none.
        Outputs: none.
        """
        self.open_first_file()
        self.assertEqual(self.view.shown_name_list, FIRST_NAME_LIST)
        self.assertFalse(self.view.no_match_shown())

    @covers("LLFR-00104", "LLFR-00096")
    def test_first_open_clears_text_typed_before(self) -> None:
        """Text typed before the first file is cleared by the open.

        Inputs: none.
        Outputs: none.
        """
        self.view.type_text("presure")
        self.open_first_file()
        self.assertIn("clear_search", self.view.call_list)
        self.assertEqual(self.view.search_text_str, "")
        self.assertEqual(self.view.shown_name_list, FIRST_NAME_LIST)
        self.assertFalse(self.view.no_match_shown())

    @covers("LLFR-00097", "LLFR-00565")
    def test_text_typed_after_the_open_can_give_the_message(self) -> None:
        """A text that matches nothing gives the message.

        Inputs: none.
        Outputs: none.
        """
        self.open_first_file()
        self.view.type_text("qqqq")
        self.assertEqual(self.view.shown_name_list, [])
        self.assertTrue(self.view.no_match_shown())

    @covers("LLFR-00104", "LLFR-00054", "LLFR-00917")
    def test_open_clears_box_and_keeps_the_names(self) -> None:
        """An open empties the box; the files already open are kept.

        Inputs: none.
        Outputs: none.
        """
        self.open_first_file()
        self.view.type_text("xyzw")
        self.assertTrue(self.view.no_match_shown())
        data_files = DataFileSet()
        data_files.add(make_signal_file(FIRST_NAME_LIST))
        data_file = data_files.add(make_signal_file(SECOND_NAME_LIST))
        self.file_controller.open(data_files, data_file)
        self.assertIn("clear_search", self.view.call_list)
        self.assertEqual(self.view.search_text_str, "")
        self.assertEqual(self.controller.search_text_str, "")
        self.assertEqual(self.view.shown_name_list,
                         data_files.signal_name_list)
        self.assertFalse(self.view.no_match_shown())
        self.view.type_text("volt")
        self.assertEqual(self.view.shown_name_list, ["file2_voltage"])
        self.view.type_text("engine")
        self.assertEqual(self.view.shown_name_list, ["file1_Engine_Speed"])


class WithFileControllerTest(unittest.TestCase):
    """Check the final list with the real FileController."""

    def setUp(self) -> None:
        """Create a real FileController with a fake loader and view.

        Inputs: none.
        Outputs: none.
        """
        self.file_dict = {
            "first.csv": make_signal_file(FIRST_NAME_LIST),
            "second.csv": make_signal_file(SECOND_NAME_LIST),
        }
        self.view = FakeFileView()
        self.file_controller = FileController(self.view,
                                              self.file_dict.__getitem__)
        self.controller = SignalListController(self.view,
                                               self.file_controller)

    def open_path(self, path_str: str) -> None:
        """Run the open-file flow with the dialog returning path_str.

        Inputs:
            path_str: the path the fake dialog returns.
        Outputs: none.
        """
        self.view.path_str = path_str
        self.file_controller.open_file_requested()

    @covers("LLFR-00095", "LLFR-00104", "LLFR-00901", "LLFR-00903",
            "LLFR-00934", "LLFR-00935")
    def test_names_of_every_file_with_their_prefix(self) -> None:
        """The list shows the prefixed names, file after file.

        Inputs: none.
        Outputs: none.
        """
        self.open_path("first.csv")
        self.view.type_text("engine")
        self.assertEqual(self.view.shown_name_list, ["file1_Engine_Speed"])
        self.open_path("second.csv")
        self.assertEqual(self.view.shown_name_list, [
            "file1_" + name_str for name_str in FIRST_NAME_LIST] + [
            "file2_" + name_str for name_str in SECOND_NAME_LIST])
        self.assertEqual(self.view.call_list[-1], "show_signal_groups")
        # LLFR-00934, LLFR-00935: one group per file, in number order,
        # each starting with its file name row.
        self.assertEqual([group[:2] for group in self.view.group_list],
                         [(1, "file1_first.csv"), (2, "file2_second.csv")])
        self.assertEqual(self.view.group_list[1][2], [
            "file2_" + name_str for name_str in SECOND_NAME_LIST])
        self.assertEqual(self.view.time_signal_name_list,
                         ["file1_Time", "file2_Time"])

    @covers("LLFR-00104", "LLFR-00916")
    def test_open_clears_search(self) -> None:
        """Opening another file clears the box.

        Inputs: none.
        Outputs: none.
        """
        self.open_path("first.csv")
        self.view.type_text("mate so 25")
        self.assertEqual(self.view.shown_name_list,
                         ["file1_mateus_soares_rodrigues 2025"])
        self.open_path("second.csv")
        self.assertEqual(self.view.search_text_str, "")
        self.assertEqual(len(self.view.shown_name_list),
                         len(FIRST_NAME_LIST) + len(SECOND_NAME_LIST))

    @covers("LLFR-00010", "LLFR-00894", "LLFR-00895")
    def test_failed_or_refused_open_keeps_search(self) -> None:
        """A failed or refused open keeps the text and the list.

        Inputs: none.
        Outputs: none.
        """
        self.open_path("first.csv")
        self.view.type_text("speed")
        self.open_path("missing.csv")
        self.assertIn("show_file_open_error", self.view.call_list)
        self.open_path("first.csv")
        self.assertIn("show_refused_files_notification", self.view.call_list)
        self.assertEqual(self.view.search_text_str, "speed")
        self.assertEqual(self.view.shown_name_list, ["file1_Engine_Speed"])

    @covers("LLFR-00922", "LLFR-00933", "LLFR-00292", "HLFR-00118",
            "HLFR-00119")
    def test_closed_files_leave_the_list(self) -> None:
        """Closing a file removes its names; closing all empties it.

        Inputs: none.
        Outputs: none.
        """
        self.open_path("first.csv")
        self.open_path("second.csv")
        self.file_controller.add_files_closed_listener(
            self.controller.on_files_closed)
        self.file_controller.close_file(1)
        self.assertEqual(self.view.shown_name_list, [
            "file2_" + name_str for name_str in SECOND_NAME_LIST])
        self.assertEqual(self.view.file_name_str, "file2_second.csv")
        self.file_controller.close_all_files()
        self.assertEqual(self.view.shown_name_list, [])
        self.assertEqual(self.view.file_name_str, "")
        self.assertFalse(self.view.no_match_shown())


def make_named_file(path_str: str, name_list: list) -> SignalFile:
    """Build a SignalFile read from path_str with the given signals.

    Inputs:
        path_str: the path the file was read from.
        name_list: the signal names, in file order.
    Outputs: the SignalFile; every signal has 3 increasing samples.
    """
    signal_dict = {name_str: np.arange(3, dtype=float)
                   for name_str in name_list}
    return SignalFile(path_str, signal_dict)


class FileNameLineTest(unittest.TestCase):
    """The file name line follows the opened file (LLFR-00362/00363)."""

    def setUp(self) -> None:
        """Create a real FileController with a fake loader and view.

        Inputs: none.
        Outputs: none.
        """
        self.first_path_str = os.path.join(
            os.sep, "data", "runs", "first_run.csv")
        self.second_path_str = os.path.join(
            os.sep, "other", "second run.v2.xlsx")
        self.no_time_path_str = os.path.join(
            os.sep, "data", "no_time.mat")
        self.file_dict = {
            self.first_path_str: make_named_file(
                self.first_path_str, FIRST_NAME_LIST),
            self.second_path_str: make_named_file(
                self.second_path_str, SECOND_NAME_LIST),
        }
        self.view = FakeFileView()
        self.file_controller = FileController(self.view, self.load_file)
        self.controller = SignalListController(self.view,
                                               self.file_controller)

    def load_file(self, path_str: str) -> SignalFile:
        """Return the prepared file of a path, as the loader does.

        Inputs:
            path_str: the selected path.
        Outputs: the SignalFile; a new one for the file without a time
            signal, so that each open asks for the time signal again.
            Raises KeyError for an unknown path (a failed open).
        """
        if path_str == self.no_time_path_str:
            return make_named_file(path_str, ["speed", "torque"])
        return self.file_dict[path_str]

    def open_path(self, path_str: str) -> None:
        """Run the open-file flow with the dialog returning path_str.

        Inputs:
            path_str: the path the fake dialog returns ("" cancels).
        Outputs: none.
        """
        self.view.path_str = path_str
        self.file_controller.open_file_requested()

    @covers("LLFR-00363", "HLFR-00079")
    def test_empty_before_any_file(self) -> None:
        """The line is empty while no data file is open.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.view.file_name_str, "")
        self.assertEqual(self.view.file_name_call_count_i, 0)
        self.open_path("")
        self.open_path(os.path.join(os.sep, "missing.csv"))
        self.assertIn("show_file_open_error", self.view.call_list)
        self.assertEqual(self.view.file_name_str, "")
        self.assertEqual(self.view.file_name_call_count_i, 0)

    @covers("LLFR-00362", "LLFR-00363", "HLFR-00079", "LLFR-00650",
            "LLFR-00934")
    def test_rows_after_each_open(self) -> None:
        """The row shows file<N>_ and the name with its extension.

        Inputs: none.
        Outputs: none.
        """
        self.open_path(self.first_path_str)
        self.assertEqual(self.view.file_name_str, "file1_first_run.csv")
        self.open_path(self.second_path_str)
        self.assertEqual(self.view.file_name_str,
                         "file1_first_run.csv, file2_second run.v2.xlsx")
        self.assertEqual(self.view.file_name_call_count_i, 2)
        self.assertNotIn(os.sep, self.view.file_name_str)

    @covers("LLFR-00363", "LLFR-00007", "LLFR-00651")
    def test_unchanged_after_cancelled_dialog(self) -> None:
        """Cancelling the file selection dialog keeps the line.

        Inputs: none.
        Outputs: none.
        """
        self.open_path(self.first_path_str)
        self.open_path("")
        self.assertEqual(self.view.file_name_str, "file1_first_run.csv")
        self.assertEqual(self.view.file_name_call_count_i, 1)

    @covers("LLFR-00363", "LLFR-00010", "LLFR-00651")
    def test_unchanged_after_failed_open(self) -> None:
        """A file that cannot be opened keeps the line.

        Inputs: none.
        Outputs: none.
        """
        self.open_path(self.first_path_str)
        self.open_path(os.path.join(os.sep, "data", "broken.csv"))
        self.assertIn("show_file_open_error", self.view.call_list)
        self.assertEqual(self.view.file_name_str, "file1_first_run.csv")
        self.assertEqual(self.view.file_name_call_count_i, 1)

    @covers("LLFR-00363", "LLFR-00894", "LLFR-00651")
    def test_unchanged_after_refused_open(self) -> None:
        """A file that is already open adds no row.

        Inputs: none.
        Outputs: none.
        """
        self.open_path(self.first_path_str)
        self.open_path(self.first_path_str)
        self.assertEqual(self.view.file_name_str, "file1_first_run.csv")
        self.assertEqual(self.view.file_name_call_count_i, 1)

    @covers("LLFR-00363", "LLFR-00327", "LLFR-00508", "LLFR-00651")
    def test_unchanged_after_cancelled_time_window(self) -> None:
        """Cancelling the time signal window keeps the line.

        Inputs: none.
        Outputs: none.
        """
        self.open_path(self.first_path_str)
        self.view.time_signal_answer_str = None
        self.open_path(self.no_time_path_str)
        self.assertIn("ask_time_signal_name", self.view.call_list)
        self.assertEqual(self.view.file_name_str, "file1_first_run.csv")
        self.assertEqual(self.view.file_name_call_count_i, 1)
        # Choosing a time signal opens the file and shows its row; the
        # cancelled open used no number (LLFR-00899).
        self.view.time_signal_answer_str = "speed"
        self.open_path(self.no_time_path_str)
        self.assertEqual(self.view.file_name_str,
                         "file1_first_run.csv, file2_no_time.mat")

    @covers("LLFR-00362", "LLFR-00095", "LLFR-00640", "LLFR-00642")
    def test_name_is_not_a_signal(self) -> None:
        """The file name is not shown in, or searched with, the list.

        Inputs: none.
        Outputs: none.
        """
        self.open_path(self.first_path_str)
        prefixed_name_list = ["file1_" + name_str
                              for name_str in FIRST_NAME_LIST]
        self.assertNotIn("file1_first_run.csv", self.view.shown_name_list)
        self.assertEqual(self.view.shown_name_list, prefixed_name_list)
        self.view.type_text("first_run")
        self.assertEqual(self.view.shown_name_list, [])
        self.assertTrue(self.view.no_match_shown())
        self.assertEqual(self.controller.signal_name_list(),
                         prefixed_name_list)
        self.assertEqual(self.view.file_name_str, "file1_first_run.csv")

    @covers("LLFR-00362")
    def test_file_name_from_path(self) -> None:
        """Only the last part of a path is kept, with its extension.

        Inputs: none.
        Outputs: none.
        """
        expected_dict = {
            os.path.join("a", "b", "signals.csv"): "signals.csv",
            "signals.h5": "signals.h5",
            os.path.join(os.sep, "x", "archive.tar.hdf5"):
                "archive.tar.hdf5",
            os.path.join("folder", "no_extension"): "no_extension",
        }
        for path_str, expected_str in expected_dict.items():
            with self.subTest(path_str=path_str):
                self.assertEqual(file_name_from_path(path_str),
                                 expected_str)


if __name__ == "__main__":
    unittest.main()


class SearchPerFileTest(unittest.TestCase):
    """The search is done file by file, below each file name row."""

    def setUp(self) -> None:
        """Open three files through a real FileController.

        Inputs: none.
        Outputs: none.
        """
        self.file_dict = {
            "a.csv": make_signal_file(["Time", "MaxSpeed", "Speed"]),
            "b.csv": make_signal_file(["Time", "voltage"]),
            "c.csv": make_signal_file(["Time", "Speed_rear"]),
        }
        self.view = FakeFileView()
        self.file_controller = FileController(self.view,
                                              self.file_dict.__getitem__)
        self.controller = SignalListController(self.view,
                                               self.file_controller)
        for path_str in ("a.csv", "b.csv", "c.csv"):
            self.view.path_str = path_str
            self.file_controller.open_file_requested()

    @covers("LLFR-00362", "LLFR-00934", "LLFR-00935", "LLFR-00650",
            "HLFR-00079", "HLFR-00114", "HLFR-00117")
    def test_one_group_per_file_in_number_order(self) -> None:
        """Each file has its number, its row and its signals.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.view.group_list, [
            (1, "file1_a.csv", ["file1_Time", "file1_MaxSpeed",
                                "file1_Speed"], ""),
            (2, "file2_b.csv", ["file2_Time", "file2_voltage"], ""),
            (3, "file3_c.csv", ["file3_Time", "file3_Speed_rear"], "")])

    @covers("LLFR-00102", "LLFR-00639", "LLFR-00097", "LLFR-00641",
            "LLFR-00640", "HLFR-00034", "HLFR-00033", "HLFR-00113")
    def test_matches_stay_below_their_file(self) -> None:
        """Matches stay under their row; a file with none says so.

        Inputs: none.
        Outputs: none.
        """
        from model.signal_search import NO_MATCH_TEXT_STR
        self.view.type_text("speed")
        # LLFR-00102: "starts with" leaves the prefix out, so Speed
        # comes before MaxSpeed within file 1.
        self.assertEqual(self.view.group_list, [
            (1, "file1_a.csv", ["file1_Speed", "file1_MaxSpeed"], ""),
            (2, "file2_b.csv", [], NO_MATCH_TEXT_STR),
            (3, "file3_c.csv", ["file3_Speed_rear"], "")])
        self.assertEqual(self.view.no_match_row_list, ["file2_b.csv"])
        self.view.type_text("xyzw")
        self.assertEqual(self.view.file_row_list,
                         ["file1_a.csv", "file2_b.csv", "file3_c.csv"])
        self.assertEqual(self.view.no_match_row_list,
                         ["file1_a.csv", "file2_b.csv", "file3_c.csv"])
        self.assertEqual(self.view.shown_name_list, [])
        # Matching uses the full name, prefix included.
        self.view.type_text("e3")
        self.assertEqual(self.view.shown_name_list,
                         ["file3_Time", "file3_Speed_rear"])
        self.view.type_text("   ")
        self.assertEqual(self.view.no_match_row_list, [])

    @covers("LLFR-00104", "LLFR-00916", "HLFR-00117")
    def test_search_cleared_on_every_open(self) -> None:
        """Opening a file empties the box and shows every file again.

        Inputs: none.
        Outputs: none.
        """
        self.file_dict["d.csv"] = make_signal_file(["Time", "x"])
        self.view.type_text("volt")
        self.view.path_str = "d.csv"
        self.file_controller.open_file_requested()
        self.assertEqual(self.view.search_text_str, "")
        self.assertEqual(self.view.file_row_list, [
            "file1_a.csv", "file2_b.csv", "file3_c.csv", "file4_d.csv"])
        self.assertEqual(self.view.no_match_row_list, [])

    @covers("LLFR-00242", "LLFR-00935", "LLFR-00936")
    def test_synthetic_signals_in_the_group_of_their_file(self) -> None:
        """A synthetic signal is listed at the end of its own file.

        Inputs: none.
        Outputs: none.
        """
        self.controller.set_synthetic_signals(
            ["file2_int_voltage", "file1_int_Speed"], set(),
            {"file2_int_voltage": 2, "file1_int_Speed": 1})
        self.assertEqual(self.view.group_list[0][2][-1], "file1_int_Speed")
        self.assertEqual(self.view.group_list[1][2][-1],
                         "file2_int_voltage")
        self.view.type_text("int")
        self.assertEqual(self.view.group_list[2][3], "No matching signals")
        self.assertEqual(self.view.shown_name_list,
                         ["file1_int_Speed", "file2_int_voltage"])

    @covers("LLFR-00922", "LLFR-00933", "LLFR-00363")
    def test_closed_file_leaves_its_group(self) -> None:
        """Close file removes the group; Close all files removes all.

        Inputs: none.
        Outputs: none.
        """
        # The MainController registers this listener in the app.
        self.file_controller.add_files_closed_listener(
            self.controller.on_files_closed)
        self.file_controller.close_file(2)
        self.assertEqual(self.view.file_row_list,
                         ["file1_a.csv", "file3_c.csv"])
        self.file_controller.close_all_files()
        self.assertEqual(self.view.group_list, [])
