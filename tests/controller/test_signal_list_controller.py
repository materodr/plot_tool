"""Tests for the signal list controller with a fake view (no Qt needed).

The real search function (model.signal_search.search_signals) is used,
so the shown lists are the ones the app shows.
"""

import unittest

import numpy as np

from tests.support import covers

from controller.file_controller import FileController
from controller.signal_list_controller import SignalListController
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

    def show_signal_names(self, signal_name_list: list) -> None:
        """Record the names shown in the list.

        Inputs:
            signal_name_list: the names, in display order.
        Outputs: none.
        """
        self.call_list.append("show_signal_names")
        self.shown_name_list = list(signal_name_list)

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

    def show_no_match_message(self, visible_b: bool,
                              message_str: str) -> None:
        """Record the no-match message state.

        Inputs:
            visible_b: True when the message is shown.
            message_str: the message text.
        Outputs: none.
        """
        self.call_list.append("show_no_match_message")
        self.no_match_tuple = (visible_b, message_str)

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


class FakeFileView(FakeSignalListView):
    """Fake view that also offers what the real FileController needs.

    Attributes:
        path_str: the path the fake file dialog returns.
        replace_answer_b: the answer of the replace confirmation.
    """

    def __init__(self) -> None:
        """Start with no path and a Yes answer.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        self.path_str = ""
        self.replace_answer_b = True

    def ask_open_file_path(self, start_folder_str: str) -> str:
        """Return the prepared path.

        Inputs:
            start_folder_str: the folder the dialog would show (unused).
        Outputs: the path.
        """
        return self.path_str

    def ask_replace_file(self) -> bool:
        """Return the prepared answer.

        Inputs: none.
        Outputs: True to proceed.
        """
        return self.replace_answer_b

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
        # The real FileController shows all names before the listeners.
        self.view.show_signal_names(FIRST_NAME_LIST)
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
            "LLFR-00101", "LLFR-00105", "HLFR-00033", "HLFR-00034")
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
        # One call by the file open, one by the listener, one per key.
        self.assertEqual(self.view.call_list.count("show_signal_names"),
                         1 + 1 + len("press"))

    @covers("LLFR-00102")
    def test_model_order_is_kept(self) -> None:
        """Names are shown in the three groups of the model.

        Inputs: none.
        Outputs: none.
        """
        name_list = ["Time", "outlet_pressure", "pressure_in",
                     "presure_typo", "Pressure"]
        self.view.show_signal_names(name_list)
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

    @covers("LLFR-00097")
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
    """Check the list after a file is opened (LLFR-00017, LLFR-00104)."""

    @covers("LLFR-00054", "LLFR-00096")
    def test_first_open_shows_all_names(self) -> None:
        """With an empty box, the first file shows all its names.

        Inputs: none.
        Outputs: none.
        """
        self.open_first_file()
        self.assertEqual(self.view.shown_name_list, FIRST_NAME_LIST)
        self.assertNotIn("clear_search", self.view.call_list)
        self.assertFalse(self.view.no_match_shown())

    @covers("LLFR-00095")
    def test_first_open_applies_text_typed_before(self) -> None:
        """Text typed before the first file filters the new names.

        Inputs: none.
        Outputs: none.
        """
        self.view.type_text("presure")
        self.open_first_file()
        self.assertEqual(self.view.shown_name_list, ["Pressure"])
        self.assertEqual(self.view.search_text_str, "presure")
        self.assertNotIn("clear_search", self.view.call_list)

    @covers("LLFR-00097")
    def test_first_open_with_no_match_shows_message(self) -> None:
        """A text typed before the first file can give the message.

        Inputs: none.
        Outputs: none.
        """
        self.view.type_text("qqqq")
        self.assertFalse(self.view.no_match_shown())
        self.open_first_file()
        self.assertEqual(self.view.shown_name_list, [])
        self.assertTrue(self.view.no_match_shown())

    @covers("LLFR-00104", "LLFR-00017", "LLFR-00054")
    def test_replace_clears_box_and_shows_new_names(self) -> None:
        """A replace empties the box and shows only the new names.

        Inputs: none.
        Outputs: none.
        """
        self.open_first_file()
        self.view.type_text("xyzw")
        self.assertTrue(self.view.no_match_shown())
        self.view.show_signal_names(SECOND_NAME_LIST)
        self.file_controller.open(make_signal_file(SECOND_NAME_LIST), True)
        self.assertIn("clear_search", self.view.call_list)
        self.assertEqual(self.view.search_text_str, "")
        self.assertEqual(self.controller.search_text_str, "")
        self.assertEqual(self.view.shown_name_list, SECOND_NAME_LIST)
        self.assertFalse(self.view.no_match_shown())
        # The new file is the one searched from now on.
        self.view.type_text("volt")
        self.assertEqual(self.view.shown_name_list, ["voltage"])
        self.view.type_text("engine")
        self.assertEqual(self.view.shown_name_list, [])
        self.assertTrue(self.view.no_match_shown())

    @covers("LLFR-00104", "LLFR-00017")
    def test_replace_with_matching_text_shows_all_new(self) -> None:
        """Even a text that matches the new file is cleared on replace.

        Inputs: none.
        Outputs: none.
        """
        self.open_first_file()
        self.view.type_text("pressure")
        self.file_controller.open(make_signal_file(SECOND_NAME_LIST), True)
        self.assertEqual(self.view.search_text_str, "")
        self.assertEqual(self.view.shown_name_list, SECOND_NAME_LIST)


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

    @covers("LLFR-00095", "LLFR-00017")
    def test_filter_is_final_after_file_controller(self) -> None:
        """The filtered list, not the full list, is shown last.

        Inputs: none.
        Outputs: none.
        """
        self.view.type_text("engine")
        self.open_path("first.csv")
        self.assertEqual(self.view.shown_name_list, ["Engine_Speed"])
        self.assertEqual(self.view.call_list[-2:],
                         ["show_signal_names", "show_no_match_message"])

    @covers("LLFR-00104", "LLFR-00017")
    def test_accepted_replace_clears_search(self) -> None:
        """A replace accepted with Yes clears the box.

        Inputs: none.
        Outputs: none.
        """
        self.open_path("first.csv")
        self.view.type_text("mate so 25")
        self.assertEqual(self.view.shown_name_list,
                         ["mateus_soares_rodrigues 2025"])
        self.open_path("second.csv")
        self.assertEqual(self.view.search_text_str, "")
        self.assertEqual(self.view.shown_name_list, SECOND_NAME_LIST)

    @covers("LLFR-00104", "LLFR-00014")
    def test_declined_replace_keeps_search(self) -> None:
        """A declined replace keeps the text and the filtered list.

        Inputs: none.
        Outputs: none.
        """
        self.open_path("first.csv")
        self.view.type_text("presure")
        self.view.replace_answer_b = False
        self.open_path("second.csv")
        self.assertEqual(self.view.search_text_str, "presure")
        self.assertEqual(self.view.shown_name_list, ["Pressure"])
        self.assertNotIn("clear_search", self.view.call_list)

    @covers("LLFR-00010")
    def test_failed_open_keeps_search(self) -> None:
        """A failed open keeps the text and the filtered list.

        Inputs: none.
        Outputs: none.
        """
        self.open_path("first.csv")
        self.view.type_text("speed")
        self.open_path("missing.csv")
        self.assertIn("show_file_open_error", self.view.call_list)
        self.assertEqual(self.view.search_text_str, "speed")
        self.assertEqual(self.view.shown_name_list, ["Engine_Speed"])


if __name__ == "__main__":
    unittest.main()
