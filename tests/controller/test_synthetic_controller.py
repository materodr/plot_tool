"""Tests for the synthetic signal controller with a fake view (no Qt).

The real MainController wires the real File, Plot, SignalList and
Synthetic controllers to a fake main window, so these tests run the
same flows as the app: the signal list menu, the parameter dialogs, the
information boxes, the plots and the undo history.
"""

import json
import math
import os
import random
import tempfile
import unittest

import numpy as np

from tests.support import covers

from tests.controller.test_plot_controller import FakePlotView

from controller.main_controller import MainController
from controller.synthetic_controller import parse_number_text
from model.file_loader import load_signal_file
from model.signal_file import SignalFile
from model.workspace import Workspace

# 100 samples, 0 s to 9.9 s, so the sampling rate is 10 Hz.
SAMPLE_COUNT_I = 100


def make_signal_file(time_array=None) -> SignalFile:
    """Build a SignalFile with Time, Speed and Torque.

    Inputs:
        time_array: optional time samples; 0 to 9.9 s every 0.1 s when
            None.
    Outputs: the SignalFile.
    """
    if time_array is None:
        time_array = np.arange(SAMPLE_COUNT_I) * 0.1
    time_array = np.asarray(time_array, dtype=float)
    return SignalFile("test.csv", {
        "Time": time_array,
        "Speed": np.sin(time_array),
        "Torque": time_array * 2.0})


class FakeSyntheticWindow(FakePlotView):
    """Stand-in for MainWindow with every facade the controllers use.

    The parameter dialog is simulated: each answer of
    parameter_answer_list is None (the user cancels at once) or a list
    of attempts; each attempt is a list of texts, one per field. The
    attempts are tried in order through the check function, as the
    user pressing OK; the first allowed attempt is returned, and when
    none is allowed the user cancels.

    Attributes:
        shown_name_list: the names last shown in the signal list.
        synthetic_name_set, fft_name_set: the kinds last given.
        operation_group_list: the menu groups given by the controller.
        signal_menu_handler_dict: option name -> handler.
        parameter_question_list: (title, prompt, field_list) of every
            parameter dialog.
        parameter_reason_list: the reasons the dialog showed.
        parameter_answer_list: the prepared parameter answers.
        second_signal_question_list: (title, prompt, name_list,
            selected name) of every second signal dialog.
        second_signal_answer_list: the prepared answers (None cancels).
        second_signal_search_list: (search function, no match text) of
            every second signal dialog (LLFR-00285).
        delete_question_list: (name, dependents) of every delete
            question.
        delete_answer_list: the prepared answers (True proceeds).
        name_answer_list: the prepared rename answers (None cancels).
        information_list: (title, message) of every information box.
        clipboard_text_list: every text put on the clipboard.
    """

    def __init__(self) -> None:
        """Start with no file, no answers and no boxes.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        self.shown_name_list = []
        # (old name, new name) given to rename_shown_signal, in order.
        self.renamed_shown_list = []
        self.synthetic_name_set = set()
        self.fft_name_set = set()
        self.operation_group_list = []
        self.signal_menu_handler_dict = {}
        self.parameter_question_list = []
        self.parameter_reason_list = []
        self.parameter_choice_list = []
        self.parameter_answer_list = []
        self.second_signal_question_list = []
        self.second_signal_answer_list = []
        self.second_signal_search_list = []
        self.delete_question_list = []
        self.delete_answer_list = []
        self.name_answer_list = []
        self.name_question_list = []
        self.information_list = []
        self.clipboard_text_list = []
        self.open_path_str = ""
        self.limit_message_list = []
        self.layout_buttons_enabled_b = None
        self.save_signals_enabled_b = None
        self.search_text_handler = None
        self.open_file_handler = None

    # File, search and export facades.

    def set_open_file_handler(self, handler) -> None:
        """Record the Open file handler.

        Inputs:
            handler: function without arguments.
        Outputs: none.
        """
        self.open_file_handler = handler

    def ask_open_file_path(self, start_folder_str: str = "") -> str:
        """Answer the file dialog with the prepared path.

        Inputs:
            start_folder_str: ignored.
        Outputs: the prepared path.
        """
        return self.open_path_str

    def show_open_files_limit_notification(self, message_str: str) -> None:
        """Record the box of an Open file click with 10 files open.

        Inputs:
            message_str: the sentence of the box.
        Outputs: none.
        """
        self.limit_message_list.append(message_str)

    def show_file_open_error(self, message_str: str) -> None:
        """Fail: no file open error is expected.

        Inputs:
            message_str: the message.
        Outputs: none.
        """
        raise AssertionError(message_str)

    def finish_open_file_button(self) -> None:
        """Do nothing.

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

    def set_time_signal_name(self, name_str: str) -> None:
        """Record the time signal shown in green (LLFR-00332).

        Inputs:
            name_str: the time signal name.
        Outputs: none.
        """
        self.time_signal_name_str = name_str

    def set_time_signal_names(self, name_list: list) -> None:
        """Record the time signals shown in green (LLFR-00332).

        Inputs:
            name_list: the time signal of each open data file.
        Outputs: none.
        """
        self.time_signal_name_str = (name_list[0] if name_list
                                     else None)

    def show_refused_files_notification(self, message_str: str) -> None:
        """Fail: no selected file is refused in these tests.

        Inputs:
            message_str: the lines of the refused files.
        Outputs: none. Raises AssertionError.
        """
        raise AssertionError(message_str)

    def show_signal_groups(self, group_list: list) -> None:
        """Record the shown file name rows and names (LLFR-00938).

        Inputs:
            group_list: (file number, row text, names, no-match text)
                per file, in list order.
        Outputs: none. shown_name_list holds every shown name, file
            after file; file_row_list the texts of the rows.
        """
        self.group_list = [tuple(group) for group in group_list]
        self.file_row_list = [row_str for _, row_str, _, _ in group_list
                              if row_str]
        self.shown_name_list = [name_str for _, _, name_list, _
                                in group_list for name_str in name_list]

    def set_signal_kinds(self, synthetic_name_set: set,
                         fft_name_set: set) -> None:
        """Record the synthetic and FFT names.

        Inputs:
            synthetic_name_set: synthetic names (italics).
            fft_name_set: FFT names.
        Outputs: none.
        """
        self.synthetic_name_set = set(synthetic_name_set)
        self.fft_name_set = set(fft_name_set)

    def set_search_text_handler(self, handler) -> None:
        """Record the search handler.

        Inputs:
            handler: function taking the text.
        Outputs: none.
        """
        self.search_text_handler = handler

    def clear_search(self) -> None:
        """Empty the search box, reporting it like a QLineEdit.

        Inputs: none.
        Outputs: none.
        """
        self.search_text_handler("")

    def clear_signal_selection(self) -> None:
        """Do nothing: the fake list keeps no selection.

        Inputs: none.
        Outputs: none.
        """

    def rename_shown_signal(self, old_name_str: str,
                            new_name_str: str) -> None:
        """Record a rename of a shown signal.

        Inputs:
            old_name_str: the previous name.
            new_name_str: the new name.
        Outputs: none.
        """
        self.renamed_shown_list.append((old_name_str, new_name_str))

    def set_export_handlers(self, pdf_export_handler,
                            copy_handler) -> None:
        """Ignore the export handlers.

        Inputs:
            pdf_export_handler: ignored.
            copy_handler: ignored.
        Outputs: none.
        """

    def set_layout_handlers(self, save_handler, load_handler) -> None:
        """Ignore the layout button handlers.

        Inputs:
            save_handler: ignored.
            load_handler: ignored.
        Outputs: none.
        """

    def set_layout_buttons_enabled(self, enabled_b: bool) -> None:
        """Record the layout button state.

        Inputs:
            enabled_b: True when the buttons are enabled.
        Outputs: none.
        """
        self.layout_buttons_enabled_b = enabled_b

    def set_save_signals_handler(self, handler) -> None:
        """Ignore the Save signals handler.

        Inputs:
            handler: ignored.
        Outputs: none.
        """

    def set_save_signals_button_enabled(self, enabled_b: bool) -> None:
        """Record the Save signals button state.

        Inputs:
            enabled_b: True when the button is enabled.
        Outputs: none.
        """
        self.save_signals_enabled_b = enabled_b

    # Synthetic signal facade.

    def set_synthetic_operation_groups(self, group_list: list) -> None:
        """Record the menu groups.

        Inputs:
            group_list: (group label, [(operation id, label)]).
        Outputs: none.
        """
        self.operation_group_list = list(group_list)

    def set_signal_menu_handlers(self, create_handler, copy_name_handler,
                                 rename_handler, delete_handler,
                                 copy_equation_handler) -> None:
        """Record the menu handlers.

        Inputs:
            create_handler: function (name, operation id).
            copy_name_handler: function (name).
            rename_handler: function (name).
            delete_handler: function (name).
            copy_equation_handler: function (name).
        Outputs: none.
        """
        self.signal_menu_handler_dict = {
            "create": create_handler, "copy_name": copy_name_handler,
            "rename": rename_handler, "delete": delete_handler,
            "copy_equation": copy_equation_handler}

    def set_file_menu_handlers(self, close_file_handler,
                               close_all_files_handler) -> None:
        """Record the handlers of the file menu (LLFR-00923).

        Inputs:
            close_file_handler: function (file number).
            close_all_files_handler: function without arguments.
        Outputs: none.
        """
        self.file_menu_handler_tuple = (close_file_handler,
                                        close_all_files_handler)

    def ask_synthetic_parameter(self, title_str: str, prompt_str: str,
                                field_list: list, check_function,
                                choice_tuple: tuple = ()):
        """Simulate the parameter dialog with the next answer.

        An attempt without a choice id gets the choice chosen at first,
        as when the user leaves the radio buttons unchanged.

        Inputs:
            title_str: the window title.
            prompt_str: the question.
            field_list: (label, starting text) per field.
            check_function: value list -> reason.
            choice_tuple: () or (label, [(id, label)], id at first).
        Outputs: the first allowed attempt, or None.
        """
        self.parameter_question_list.append(
            (title_str, prompt_str, list(field_list)))
        self.parameter_choice_list.append(tuple(choice_tuple))
        attempt_list = (self.parameter_answer_list.pop(0)
                        if self.parameter_answer_list else None)
        if attempt_list is None:
            return None
        for text_list in attempt_list:
            text_list = list(text_list)
            if choice_tuple and len(text_list) == len(field_list):
                text_list.append(choice_tuple[2])
            reason_str = check_function(text_list)
            if not reason_str:
                return text_list
            self.parameter_reason_list.append(reason_str)
        return None

    def ask_second_signal(self, title_str: str, prompt_str: str,
                          name_list: list, selected_name_str: str,
                          search_function, no_match_text_str: str):
        """Answer the second signal dialog.

        Inputs:
            title_str: the window title.
            prompt_str: the question.
            name_list: the names to choose from.
            selected_name_str: the name selected at first.
            search_function: text -> matching names (LLFR-00285).
            no_match_text_str: the text shown when nothing matches.
        Outputs: the next prepared answer, or None.
        """
        self.second_signal_question_list.append(
            (title_str, prompt_str, list(name_list), selected_name_str))
        self.second_signal_search_list.append(
            (search_function, no_match_text_str))
        if not self.second_signal_answer_list:
            return None
        return self.second_signal_answer_list.pop(0)

    def ask_delete_synthetic_signal(self, name_str: str,
                                    dependent_name_list: list) -> bool:
        """Answer the delete question.

        Inputs:
            name_str: the signal name.
            dependent_name_list: its dependents.
        Outputs: the next prepared answer, False when none.
        """
        self.delete_question_list.append((name_str,
                                          list(dependent_name_list)))
        if not self.delete_answer_list:
            return False
        return self.delete_answer_list.pop(0)

    def ask_synthetic_signal_name(self, current_name_str: str):
        """Answer the rename dialog.

        Inputs:
            current_name_str: the current name.
        Outputs: the next prepared answer, or None.
        """
        self.name_question_list.append(current_name_str)
        if not self.name_answer_list:
            return None
        return self.name_answer_list.pop(0)

    def show_signal_information(self, title_str: str,
                                message_str: str) -> None:
        """Record an information box.

        Inputs:
            title_str: the title.
            message_str: the message.
        Outputs: none.
        """
        self.information_list.append((title_str, message_str))

    def copy_text_to_clipboard(self, text_str: str) -> None:
        """Record a clipboard text.

        Inputs:
            text_str: the text.
        Outputs: none.
        """
        self.clipboard_text_list.append(text_str)


class SyntheticControllerTestCase(unittest.TestCase):
    """Shared setup: the app's controllers with one opened file."""

    def setUp(self) -> None:
        """Create the controllers and open the test file.

        Inputs: none.
        Outputs: none.
        """
        self.view = FakeSyntheticWindow()
        self.main_controller = MainController(self.view)
        self.main_controller.plot_controller.workspace.random_generator = (
            random.Random(3))
        self.file_controller = self.main_controller.file_controller
        self.plot_controller = self.main_controller.plot_controller
        self.controller = self.main_controller.synthetic_controller
        self.open_file(make_signal_file())

    def open_file(self, signal_file: SignalFile,
                  path_str: str = "test.csv",
                  keep_open_b: bool = False) -> None:
        """Open a SignalFile through the real open-file flow.

        Inputs:
            signal_file: the file the loader returns.
            path_str: the path the dialog returns.
            keep_open_b: False to close the open data files first, so
                that the test works with this one file.
        Outputs: none.
        """
        if not keep_open_b:
            self.file_controller.close_all_files()
        self.file_controller.load_function = lambda path_str: signal_file
        self.view.open_path_str = path_str
        self.file_controller.open_file_requested()

    def create(self, name_str: str, operation_str: str) -> None:
        """Choose an operation in the menu of a signal.

        Inputs:
            name_str: the right-clicked signal.
            operation_str: the operation id.
        Outputs: none.
        """
        self.view.signal_menu_handler_dict["create"](name_str, operation_str)

    def menu(self, option_str: str, name_str: str) -> None:
        """Choose another option of the signal menu.

        Inputs:
            option_str: "copy_name", "rename", "delete" or
                "copy_equation".
            name_str: the right-clicked signal.
        Outputs: none.
        """
        self.view.signal_menu_handler_dict[option_str](name_str)

    def double_click(self, name_str: str) -> None:
        """Double-click a signal name.

        Inputs:
            name_str: the signal name.
        Outputs: none.
        """
        self.view.handler_dict["double_click"](name_str)

    def plot_id_list(self) -> list:
        """Return the ids of every plot of the workspace.

        Inputs: none.
        Outputs: a list of ids, tab by tab.
        """
        return [plot.plot_id_i
                for plot in self.plot_controller.all_plot_list()]

    def store_names(self) -> list:
        """Return the synthetic signal names of the store.

        Inputs: none.
        Outputs: the names, in creation order.
        """
        return self.controller.store.names()


class MenuWiringTest(SyntheticControllerTestCase):
    """Check what the controller gives the signal list menu."""

    @covers("LLFR-00239", "LLFR-00268")
    def test_operation_groups_in_menu_order(self) -> None:
        """The menu groups and labels follow LLFR-00268, with ids.

        Inputs: none.
        Outputs: none.
        """
        label_group_list = [
            (group_str, [label_str for _, label_str in operation_list])
            for group_str, operation_list in self.view.operation_group_list]
        self.assertEqual(label_group_list, [
            ("Calculus", ["Integral (int)", "Derivative (der)"]),
            ("Filters", ["Low-pass filter (lpf)", "High-pass filter (hpf)",
                         "Moving average (mavg)"]),
            ("Statistics", ["Max (max)", "Min (min)"]),
            ("Comparison", ["Greater than (gt)", "Less than (lt)",
                            "Greater than or equal (ge)",
                            "Less than or equal (le)"]),
            ("Arithmetic", ["Add constant (add)", "Subtract constant (sub)",
                            "Multiply by constant (mul)",
                            "Divide by constant (div)",
                            "Absolute value (abs)",
                            "Product with signal (prod)"]),
            ("Spectrum", ["FFT (fft)"])])
        id_list = [operation_str
                   for _, operation_list in self.view.operation_group_list
                   for operation_str, _ in operation_list]
        self.assertEqual(id_list[:3], ["integral", "derivative", "lowpass"])
        self.assertEqual(id_list[-1], "fft")
        self.assertEqual(id_list[-3:-1], ["abs", "product"])

    @covers("LLFR-00239", "LLFR-00254", "LLFR-00265", "LLFR-00277",
            "LLFR-00278")
    def test_every_menu_option_has_a_handler(self) -> None:
        """Create, copy name, rename, delete and copy equation are set.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(sorted(self.view.signal_menu_handler_dict), [
            "copy_equation", "copy_name", "create", "delete", "rename"])
        self.assertIs(self.plot_controller.synthetic_store,
                      self.controller.store)

    @covers("LLFR-00245", "LLFR-00272")
    def test_parse_number_text(self) -> None:
        """Typed texts become ints, floats, or stay text.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(parse_number_text(" 3 "), 3)
        self.assertIsInstance(parse_number_text("3"), int)
        self.assertEqual(parse_number_text("2.5"), 2.5)
        self.assertEqual(parse_number_text("1e-3"), 0.001)
        self.assertEqual(parse_number_text("abc"), "abc")
        self.assertEqual(parse_number_text(""), "")


class CreateTest(SyntheticControllerTestCase):
    """Check the creation of synthetic signals from the menu."""

    @covers("LLFR-00239", "LLFR-00240", "LLFR-00242", "LLFR-00243",
            "LLFR-00568")
    def test_integral_is_listed_after_the_data_signals(self) -> None:
        """Integral creates int_Speed, listed last and in italics.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.assertEqual(self.store_names(), ["file1_int_Speed"])
        self.assertEqual(self.view.shown_name_list,
                         ["file1_Time", "file1_Speed", "file1_Torque",
                          "file1_int_Speed"])
        self.assertEqual(self.view.synthetic_name_set, {"file1_int_Speed"})
        self.assertEqual(self.view.fft_name_set, set())
        # No dialog for an operation without a parameter.
        self.assertEqual(self.view.parameter_question_list, [])
        values_array = self.controller.store.get(
            "file1_int_Speed").value_array
        self.assertEqual(values_array[0], 0.0)
        self.assertEqual(values_array.size, SAMPLE_COUNT_I)

    @covers("LLFR-00242", "LLFR-00264", "LLFR-00240")
    def test_creation_order_and_synthetic_sources(self) -> None:
        """Signals from synthetic signals build up their names.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.create("file1_int_Speed", "derivative")
        self.create("file1_Torque", "max")
        self.create("file1_Time", "min")
        self.assertEqual(self.view.shown_name_list, [
            "file1_Time", "file1_Speed", "file1_Torque", "file1_int_Speed",
            "file1_der_int_Speed", "file1_max_Torque", "file1_min_Time"])
        self.assertEqual(self.view.synthetic_name_set, {
            "file1_int_Speed", "file1_der_int_Speed", "file1_max_Torque",
            "file1_min_Time"})
        np.testing.assert_allclose(
            self.controller.store.get("file1_max_Torque").value_array, 19.8)

    @covers("LLFR-00242", "LLFR-00095", "LLFR-00578")
    def test_synthetic_signals_are_searched(self) -> None:
        """The search finds synthetic signals like data signals.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.view.search_text_handler("int_")
        self.assertEqual(self.view.shown_name_list, ["file1_int_Speed"])
        self.create("file1_Torque", "integral")
        self.assertEqual(self.view.shown_name_list,
                         ["file1_int_Speed", "file1_int_Torque"])
        self.view.search_text_handler("")
        self.assertEqual(self.view.shown_name_list[-2:],
                         ["file1_int_Speed", "file1_int_Torque"])

    @covers("LLFR-00245", "LLFR-00246", "LLFR-00241", "LLFR-00577",
            "LLFR-00581", "LLFR-00582", "LLFR-00583", "LLFR-00584",
            "LLFR-00585", "LLFR-00586", "LLFR-00588")
    def test_filter_dialog_states_ranges_and_keeps_open(self) -> None:
        """The filter dialog asks for cutoff and order and checks them.

        Inputs: none.
        Outputs: none.
        """
        self.view.parameter_answer_list = [[
            ["abc", "2"], ["0", "2"], ["5", "2"], ["7", "2"],
            ["1.5", "0"], ["1.5", "9"], ["1.5", "2.5"], ["1.5", "x"],
            ["1.5", "4"]]]
        self.create("file1_Speed", "lowpass")
        title_str, prompt_str, field_list = (
            self.view.parameter_question_list[0])
        self.assertEqual(title_str, "Low-pass filter")
        self.assertIn("greater than 0 Hz and less than 5 Hz", prompt_str)
        self.assertIn("from 1 to 8", prompt_str)
        # LLFR-00245: two fields, the order starting at 2.
        self.assertEqual(field_list, [("Cutoff frequency (Hz):", ""),
                                      ("Filter order:", "2")])
        reason_list = self.view.parameter_reason_list
        self.assertEqual(len(reason_list), 8)
        for reason_str in reason_list[:4]:
            self.assertIn("greater than 0 Hz and less than 5 Hz",
                          reason_str)
        for reason_str in reason_list[4:]:
            self.assertIn("order must be a whole number from 1 to 8",
                          reason_str)
        self.assertEqual(self.store_names(), ["file1_lpf_1p5Hz_order4_Speed"])
        self.assertEqual(self.controller.store.get(
            "file1_lpf_1p5Hz_order4_Speed").parameter, (1.5, 4, "first_value"))
        # LLFR-00245: the start choice, "From the first value" at first.
        self.assertEqual(self.view.parameter_choice_list[0], (
            "Filter start:", [("first_value", "From the first value"),
                              ("zero", "From zero")], "first_value"))
        # LLFR-00241, LLFR-00240: the same filter with another start
        # gets "_2", since the start is not part of the name.
        self.view.parameter_answer_list = [[["1.5", "4", "zero"]]]
        self.create("file1_Speed", "lowpass")
        self.assertEqual(self.store_names(),
                         ["file1_lpf_1p5Hz_order4_Speed",
                          "file1_lpf_1p5Hz_order4_Speed_2"])
        self.assertEqual(self.controller.store.get(
            "file1_lpf_1p5Hz_order4_Speed_2").parameter, (1.5, 4, "zero"))

    @covers("LLFR-00245", "LLFR-00246", "LLFR-00587", "LLFR-00589")
    def test_highpass_and_cancelled_filter(self) -> None:
        """A cancelled dialog creates nothing; highpass is created.

        Inputs: none.
        Outputs: none.
        """
        self.view.parameter_answer_list = [None, [["9", "2"]],
                                           [["1", "1", "zero"]]]
        self.create("file1_Speed", "lowpass")
        self.create("file1_Speed", "highpass")
        self.assertEqual(self.store_names(), [])
        self.create("file1_Speed", "highpass")
        self.assertEqual(self.store_names(), ["file1_hpf_1Hz_order1_Speed"])
        # LLFR-00246: the start chosen in the dialog is used.
        signal = self.controller.store.get("file1_hpf_1Hz_order1_Speed")
        self.assertEqual(signal.parameter, (1.0, 1, "zero"))
        from model import synthetic_operations
        np.testing.assert_allclose(signal.value_array,
                                   synthetic_operations.highpass(
                                       make_signal_file().time_array,
                                       make_signal_file().signal_array(
                                           "Speed"), 1.0, 1, "zero"))
        self.assertEqual(self.view.parameter_question_list[1][0],
                         "High-pass filter")
        self.assertEqual(self.view.information_list, [])

    @covers("LLFR-00247", "LLFR-00590", "LLFR-00591")
    def test_uneven_time_steps_show_a_box_before_any_dialog(self) -> None:
        """Filters and FFT on uneven steps show an information box.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.arange(SAMPLE_COUNT_I) * 0.1
        time_array[50:] += 0.02
        self.open_file(make_signal_file(time_array))
        for operation_str in ("lowpass", "highpass", "fft"):
            self.create("file2_Speed", operation_str)
        self.assertEqual(self.view.parameter_question_list, [])
        self.assertEqual(len(self.view.information_list), 3)
        for title_str, message_str in self.view.information_list:
            self.assertEqual(title_str, "Create synthetic signal")
            self.assertIn("evenly spaced time samples", message_str)
        self.assertEqual(self.store_names(), [])
        # LLFR-00247: the other operations still work.
        self.create("file2_Speed", "integral")
        self.assertEqual(self.store_names(), ["file2_int_Speed"])

    @covers("LLFR-00269", "LLFR-00270", "LLFR-00608", "LLFR-00609",
            "LLFR-00610", "LLFR-00611")
    def test_moving_average_window_dialog(self) -> None:
        """The window dialog states 2 to n and refuses other values.

        Inputs: none.
        Outputs: none.
        """
        self.view.parameter_answer_list = [
            None, [["1"], ["2.5"], ["x"], ["101"], [""], ["5"]]]
        self.create("file1_Speed", "movingaverage")
        self.assertEqual(self.store_names(), [])
        self.create("file1_Speed", "movingaverage")
        title_str, prompt_str, field_list = (
            self.view.parameter_question_list[1])
        self.assertEqual(title_str, "Moving average")
        self.assertIn("from 2 to 100 samples", prompt_str)
        self.assertEqual(len(field_list), 1)
        self.assertEqual(self.view.parameter_choice_list[1], ())
        self.assertEqual(len(self.view.parameter_reason_list), 5)
        for reason_str in self.view.parameter_reason_list:
            self.assertIn("whole number of samples from 2 to 100",
                          reason_str)
        self.assertEqual(self.store_names(), ["file1_mavg_5samples_Speed"])
        self.assertEqual(self.controller.store.get(
            "file1_mavg_5samples_Speed").parameter, 5)

    @covers("LLFR-00269")
    def test_signal_too_short_for_a_moving_average(self) -> None:
        """A one-sample file shows a box instead of the window dialog.

        Inputs: none.
        Outputs: none.
        """
        self.open_file(make_signal_file([0.0]))
        self.create("file2_Speed", "movingaverage")
        self.assertEqual(self.view.parameter_question_list, [])
        self.assertEqual(len(self.view.information_list), 1)
        self.assertEqual(self.store_names(), [])

    @covers("LLFR-00272", "LLFR-00273", "LLFR-00274", "LLFR-00613",
            "LLFR-00614", "LLFR-00615", "LLFR-00616")
    def test_constant_dialog(self) -> None:
        """Constants must be numbers, not 0 for a division.

        Inputs: none.
        Outputs: none.
        """
        self.view.parameter_answer_list = [
            [["abc"], ["nan"], ["0.5"]], [["0"], ["4"]], None,
            [["3"]], [["-1"]]]
        self.create("file1_Torque", "greater")
        self.create("file1_Torque", "divide")
        self.create("file1_Torque", "subtract")
        self.create("file1_Torque", "multiply")
        self.create("file1_Torque", "lessorequal")
        reason_list = self.view.parameter_reason_list
        self.assertEqual(reason_list, [
            "The constant must be a number.",
            "The constant must be a number.",
            "The constant must not be 0 for a division."])
        self.assertIn("not 0", self.view.parameter_question_list[1][1])
        self.assertEqual(self.view.parameter_question_list[0][2],
                         [("Constant:", "")])
        self.assertEqual(self.store_names(), [
            "file1_gt_0p5_Torque", "file1_div_4_Torque", "file1_mul_3_Torque",
            "file1_le_1n0_Torque"])
        store = self.controller.store
        torque_array = make_signal_file().signal_array("Torque")
        np.testing.assert_allclose(store.get(
            "file1_gt_0p5_Torque").value_array,
                                   (torque_array > 0.5).astype(float))
        np.testing.assert_allclose(store.get("file1_div_4_Torque").value_array,
                                   torque_array / 4.0)
        np.testing.assert_allclose(
            store.get("file1_mul_3_Torque").value_array, torque_array * 3.0)
        np.testing.assert_allclose(
            store.get("file1_le_1n0_Torque").value_array,
            (torque_array <= -1.0).astype(float))

    @covers("LLFR-00275", "LLFR-00276", "LLFR-00240", "LLFR-00617")
    def test_product_second_signal_dialog(self) -> None:
        """The second signal list has every non-FFT signal.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "fft")
        self.create("file1_Speed", "integral")
        self.view.second_signal_answer_list = [None, "file1_Torque",
                                               "file1_Speed"]
        self.create("file1_Speed", "product")
        self.assertEqual(self.store_names(),
                         ["file1_fft_0s_to_9p9s_Speed", "file1_int_Speed"])
        title_str, prompt_str, name_list, selected_name_str = (
            self.view.second_signal_question_list[0])
        self.assertEqual(title_str, "Product with signal")
        self.assertIn("file1_Speed", prompt_str)
        self.assertEqual(name_list, ["file1_Time", "file1_Speed",
                                     "file1_Torque",
                                     "file1_int_Speed"])
        self.assertEqual(selected_name_str, "file1_Speed")
        self.create("file1_Speed", "product")
        self.create("file1_Speed", "product")
        self.assertEqual(self.store_names()[-2:],
                         ["file1_Speed_prod_file1_Torque",
                          "file1_Speed_prod_file1_Speed"])
        speed_array = make_signal_file().signal_array("Speed")
        np.testing.assert_allclose(
            self.controller.store.get(
                "file1_Speed_prod_file1_Torque").value_array,
            speed_array * make_signal_file().signal_array("Torque"))

    @covers("LLFR-00284", "LLFR-00272", "LLFR-00240", "LLFR-00264",
            "LLFR-00251")
    def test_absolute_value_needs_no_dialog(self) -> None:
        """Absolute value is created at once, chained, not on an FFT.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Torque", "abs")
        self.assertEqual(self.store_names(), ["file1_abs_Torque"])
        self.assertEqual(self.view.parameter_question_list, [])
        self.assertEqual(self.view.second_signal_question_list, [])
        self.assertEqual(self.view.information_list, [])
        torque_array = make_signal_file().signal_array("Torque")
        np.testing.assert_allclose(
            self.controller.store.get("file1_abs_Torque").value_array,
            np.abs(torque_array))
        self.assertIn("file1_abs_Torque", self.view.synthetic_name_set)
        self.create("file1_abs_Torque", "integral")
        self.create("file1_int_abs_Torque", "abs")
        self.assertEqual(self.store_names(), [
            "file1_abs_Torque", "file1_int_abs_Torque",
            "file1_abs_int_abs_Torque"])
        self.create("file1_Speed", "fft")
        fft_name_str = self.store_names()[-1]
        self.create(fft_name_str, "abs")
        self.assertEqual(self.store_names()[-1], fft_name_str)
        self.assertEqual(self.controller.layout_entries()[0], {
            "name": "file1_abs_Torque", "operation": "abs",
            "signals": ["file1_Torque"], "parameter": None})

    @covers("LLFR-00240", "LLFR-00241", "LLFR-00275")
    def test_product_names_and_the_name_collision(self) -> None:
        """Products are <first>_prod_<prefixed second>; a collision gets _2.

        Inputs: none.
        Outputs: none.
        """
        self.view.second_signal_answer_list = ["file1_Torque", "file1_Torque"]
        self.create("file1_Speed", "product")
        self.create("file1_Speed_prod_file1_Torque", "integral")
        self.create("file1_Speed", "integral")
        self.create("file1_int_Speed", "product")
        self.assertEqual(self.store_names(), [
            "file1_Speed_prod_file1_Torque",
            "file1_int_Speed_prod_file1_Torque", "file1_int_Speed",
            "file1_int_Speed_prod_file1_Torque_2"])
        self.assertEqual(self.controller.store.get(
            "file1_int_Speed_prod_file1_Torque_2").source_name_list,
            ["file1_int_Speed", "file1_Torque"])

    @covers("LLFR-00285", "LLFR-00275", "LLFR-00095", "LLFR-00096",
            "LLFR-00097", "LLFR-00102", "LLFR-00105", "LLFR-00098",
            "LLFR-00100", "LLFR-00101", "LLFR-00618", "LLFR-00619",
            "LLFR-00620", "LLFR-00621")
    def test_second_signal_dialog_search(self) -> None:
        """The dialog searches its own signals as the panel searches.

        Inputs: none.
        Outputs: none.
        """
        from model.signal_search import search_prefixed_signals
        self.create("file1_Speed", "fft")
        self.create("file1_Speed", "integral")
        self.create("file1_Torque", "integral")
        self.view.second_signal_answer_list = [None]
        self.create("file1_Speed", "product")
        search_function, no_match_text_str = (
            self.view.second_signal_search_list[0])
        self.assertEqual(no_match_text_str, "No matching signals")
        name_list = self.view.second_signal_question_list[0][2]
        self.assertEqual(name_list, ["file1_Time", "file1_Speed",
                                     "file1_Torque",
                                     "file1_int_Speed", "file1_int_Torque"])
        # LLFR-00096: an empty or blank search shows every signal.
        self.assertEqual(search_function(""), name_list)
        self.assertEqual(search_function("   "), name_list)
        for text_str in ("speed", "INT", "int tor", "Torqe", "s int",
                         "fft", "zzz", "int_sp", "t"):
            with self.subTest(text=text_str):
                # LLFR-00285: the same result and order as the panel.
                self.assertEqual(search_function(text_str),
                                 search_prefixed_signals(name_list,
                                                         text_str))
        self.assertEqual(search_function("speed"), ["file1_Speed",
                                                    "file1_int_Speed"])
        self.assertEqual(search_function("int tor"), ["file1_int_Torque"])
        self.assertEqual(search_function("Torqe"),
                         ["file1_Torque", "file1_int_Torque"])
        # LLFR-00275: the FFT signal is never found.
        self.assertEqual(search_function("fft"), [])
        self.assertEqual(search_function("zzz"), [])
        self.assertEqual(self.store_names(), [
            "file1_fft_0s_to_9p9s_Speed", "file1_int_Speed",
            "file1_int_Torque"])

    @covers("LLFR-00285", "LLFR-00102", "LLFR-00618")
    def test_second_signal_dialog_ranks_without_the_prefix(self) -> None:
        """The "starts with" group leaves the file prefix out.

        Inputs: none.
        Outputs: none.
        """
        from model.signal_search import search_signals
        time_array = np.arange(SAMPLE_COUNT_I) * 0.1
        # A new app, so that the file is file 1 (file numbers are not
        # reused after a close).
        self.view = FakeSyntheticWindow()
        self.main_controller = MainController(self.view)
        self.file_controller = self.main_controller.file_controller
        self.controller = self.main_controller.synthetic_controller
        self.open_file(SignalFile("test.csv", {
            "Time": time_array,
            "MaxSpeed": np.cos(time_array),
            "Speed": np.sin(time_array)}))
        self.view.second_signal_answer_list = [None]
        self.create("file1_Speed", "product")
        search_function, _ = self.view.second_signal_search_list[-1]
        name_list = self.view.second_signal_question_list[-1][2]
        self.assertEqual(name_list, ["file1_Time", "file1_MaxSpeed",
                                     "file1_Speed"])
        # LLFR-00102: "file1_Speed" starts with "speed" once its prefix
        # is left out, so it comes before "file1_MaxSpeed".
        self.assertEqual(search_function("speed"),
                         ["file1_Speed", "file1_MaxSpeed"])
        # The ranking without that rule keeps the file order.
        self.assertEqual(search_signals(name_list, "speed"),
                         ["file1_MaxSpeed", "file1_Speed"])

    @covers("LLFR-00248", "LLFR-00240", "LLFR-00249", "LLFR-00592")
    def test_fft_uses_the_whole_file_without_time_plots(self) -> None:
        """With no plot, the FFT range is the file's whole range.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "fft")
        signal = self.controller.store.get("file1_fft_0s_to_9p9s_Speed")
        self.assertEqual(signal.parameter, (0.0, 9.9))
        self.assertEqual(signal.value_array.size, SAMPLE_COUNT_I // 2 + 1)
        self.assertEqual(self.view.fft_name_set,
                         {"file1_fft_0s_to_9p9s_Speed"})
        self.assertEqual(self.view.parameter_question_list, [])

    @covers("LLFR-00248", "LLFR-00240", "LLFR-00070", "LLFR-00593")
    def test_fft_uses_the_shared_range_of_the_time_plots(self) -> None:
        """The FFT range is the zoomed range shared by the plots.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("file1_Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["time_range_handler"](plot_id_i, 1.5, 3.0)
        self.create("file1_Torque", "fft")
        self.assertEqual(self.store_names(), ["file1_fft_1p5s_to_3s_Torque"])
        # LLFR-00248: a later change of the range changes nothing.
        self.view.handler_dict["time_range_handler"](plot_id_i, 0.0, 9.0)
        self.assertEqual(self.controller.store.get(
            "file1_fft_1p5s_to_3s_Torque").parameter, (1.5, 3.0))
        # LLFR-00241: the same range again gets "_2"; a reset range is
        # the whole file again.
        self.view.handler_dict["time_range_handler"](plot_id_i, 1.5, 3.0)
        self.create("file1_Torque", "fft")
        self.view.handler_dict["reset_zoom"]()
        self.create("file1_Torque", "fft")
        self.assertEqual(self.store_names(), [
            "file1_fft_1p5s_to_3s_Torque", "file1_fft_1p5s_to_3s_Torque_2",
            "file1_fft_0s_to_9p9s_Torque"])

    @covers("LLFR-00250", "LLFR-00969", "LLFR-00968")
    def test_fft_with_too_few_samples_shows_a_box(self) -> None:
        """A shown range with fewer than 8 samples creates no FFT.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("file1_Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["time_range_handler"](plot_id_i, 1.0, 1.65)
        self.create("file1_Speed", "fft")
        self.assertEqual(self.store_names(), [])
        self.assertEqual(len(self.view.information_list), 1)
        # LLFR-00969: the box asks to move the x-axis.
        self.assertIn("does not hold enough samples",
                      self.view.information_list[0][1])
        self.assertIn("Move the x-axis", self.view.information_list[0][1])
        self.view.handler_dict["time_range_handler"](plot_id_i, 1.0, 1.75)
        self.create("file1_Speed", "fft")
        self.assertEqual(self.store_names(), ["file1_fft_1s_to_1p75s_Speed"])

    @covers("LLFR-00251")
    def test_no_operation_on_fft_signals(self) -> None:
        """An operation requested on an FFT signal does nothing.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "fft")
        fft_name_str = self.store_names()[0]
        self.view.parameter_answer_list = [[["2"]]]
        for operation_str in ("integral", "add", "fft", "product"):
            self.create(fft_name_str, operation_str)
        self.assertEqual(self.store_names(), [fft_name_str])
        self.assertEqual(self.view.parameter_question_list, [])
        self.assertEqual(self.view.second_signal_question_list, [])
        self.assertEqual(self.view.information_list, [])

    @covers("LLFR-00239", "LLFR-00568")
    def test_stale_requests_are_ignored(self) -> None:
        """Unknown signals or operations create nothing.

        Inputs: none.
        Outputs: none.
        """
        self.create("Pressure", "integral")
        self.create("file1_Speed", "cube")
        self.menu("copy_name", "Pressure")
        self.assertEqual(self.store_names(), [])
        self.assertEqual(self.view.clipboard_text_list, [])

    @covers("LLFR-00140", "LLFR-00255")
    def test_creating_is_not_undoable(self) -> None:
        """Creating a synthetic signal records no undo step.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.assertFalse(self.view.undo_enabled_b)
        self.assertFalse(self.plot_controller.undo_history.can_undo())


class PlotSyntheticTest(SyntheticControllerTestCase):
    """Check that synthetic signals are plotted like data signals."""

    @covers("LLFR-00242", "LLFR-00019", "LLFR-00020", "LLFR-00021",
            "LLFR-00579")
    def test_double_click_and_drop_draw_synthetic_signals(self) -> None:
        """Synthetic signals can be double-clicked and dropped.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.create("file1_Torque", "max")
        self.double_click("file1_int_Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["signal_drop_handler"](plot_id_i,
                                                      "file1_max_Torque")
        self.assertEqual(self.view.drawn_names(plot_id_i),
                         ["file1_int_Speed", "file1_max_Torque"])
        curve_list = self.view.drawn_dict[plot_id_i][0]
        np.testing.assert_allclose(
            curve_list[0][2],
            self.controller.store.get("file1_int_Speed").value_array)
        np.testing.assert_allclose(curve_list[1][2], 19.8)

    @covers("LLFR-00263", "LLFR-00039", "LLFR-00049", "LLFR-00028",
            "LLFR-00600")
    def test_removing_curves_keeps_the_synthetic_signal(self) -> None:
        """Curve, plot and tab deletions keep the signal in the list.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.double_click("file1_int_Speed")
        first_plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["curve_delete_handler"](first_plot_id_i,
                                                       "file1_int_Speed")
        self.double_click("file1_int_Speed")
        self.view.handler_dict["plot_delete_handler"](
            self.plot_id_list()[0])
        self.view.handler_dict["add_tab"]()
        self.double_click("file1_int_Speed")
        self.view.handler_dict["delete_tab"](self.view.current_tab_id())
        self.assertEqual(self.plot_id_list(), [])
        self.assertEqual(self.store_names(), ["file1_int_Speed"])
        self.assertIn("file1_int_Speed", self.view.shown_name_list)
        # LLFR-00263: the signal can be plotted again.
        self.double_click("file1_int_Speed")
        self.assertEqual(len(self.plot_id_list()), 1)


class CopyTest(SyntheticControllerTestCase):
    """Check "Copy name" and "Copy equation"."""

    @covers("LLFR-00277", "LLFR-00623")
    def test_copy_name_for_every_kind_of_signal(self) -> None:
        """The name of a data, synthetic or FFT signal is copied.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.create("file1_Speed", "fft")
        for name_str in ("file1_Time", "file1_Speed", "file1_int_Speed",
                         "file1_fft_0s_to_9p9s_Speed"):
            self.menu("copy_name", name_str)
        self.assertEqual(self.view.clipboard_text_list, [
            "file1_Time", "file1_Speed", "file1_int_Speed",
            "file1_fft_0s_to_9p9s_Speed"])

    @covers("LLFR-00278", "LLFR-00279", "LLFR-00225")
    def test_copy_equation_lists_the_signal_and_its_ancestors(
            self) -> None:
        """The equation is the JSON list of the needed entries.

        Inputs: none.
        Outputs: none.
        """
        self.view.parameter_answer_list = [[["2", "3"]]]
        self.create("file1_Speed", "lowpass")
        self.create("file1_Torque", "integral")
        self.create("file1_lpf_2Hz_order3_Speed", "derivative")
        self.menu("copy_equation", "file1_der_lpf_2Hz_order3_Speed")
        self.menu("copy_equation", "file1_Speed")
        self.assertEqual(len(self.view.clipboard_text_list), 1)
        text_str = self.view.clipboard_text_list[0]
        self.assertEqual(text_str, self.controller.store.equation_text(
            "file1_der_lpf_2Hz_order3_Speed"))
        self.assertEqual(json.loads(text_str), [
            {"name": "file1_lpf_2Hz_order3_Speed", "operation": "lowpass",
             "signals": ["file1_Speed"],
             "parameter": {"cutoff": 2.0, "order": 3,
                           "start": "first_value"}},
            {"name": "file1_der_lpf_2Hz_order3_Speed",
             "operation": "derivative",
             "signals": ["file1_lpf_2Hz_order3_Speed"], "parameter": None}])
        self.assertTrue(text_str.startswith("[\n  {\n"))


class DeleteTest(SyntheticControllerTestCase):
    """Check "Delete signal" of a synthetic signal."""

    def build_dependents(self) -> None:
        """Create int_Speed, two levels of dependents and plots.

        Plot 1 draws Speed and der_int_Speed; plot 2 draws
        only int_Speed; plot 3 in a second tab draws
        max_der_int_Speed and Torque.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.create("file1_int_Speed", "derivative")
        self.create("file1_Torque", "integral")
        self.create("file1_der_int_Speed", "max")
        self.double_click("file1_Speed")
        first_plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["signal_drop_handler"](
            first_plot_id_i, "file1_der_int_Speed")
        self.double_click("file1_int_Speed")
        self.view.handler_dict["add_tab"]()
        self.double_click("file1_max_der_int_Speed")
        self.view.handler_dict["signal_drop_handler"](
            self.plot_id_list()[2], "file1_Torque")

    @covers("LLFR-00255")
    def test_confirmation_names_direct_and_indirect_dependents(
            self) -> None:
        """The question names every dependent; No keeps everything.

        Inputs: none.
        Outputs: none.
        """
        self.build_dependents()
        self.view.delete_answer_list = [False]
        self.menu("delete", "file1_int_Speed")
        self.assertEqual(self.view.delete_question_list, [
            ("file1_int_Speed", ["file1_der_int_Speed",
                                 "file1_max_der_int_Speed"])])
        self.assertEqual(len(self.store_names()), 4)
        self.assertEqual(len(self.plot_id_list()), 3)
        self.assertTrue(self.view.undo_enabled_b)

    @covers("LLFR-00255", "LLFR-00051", "LLFR-00050", "LLFR-00597",
            "LLFR-00598", "LLFR-00599")
    def test_delete_removes_signals_curves_and_history(self) -> None:
        """Yes removes the signals, their curves, empty plots, history.

        Inputs: none.
        Outputs: none.
        """
        self.build_dependents()
        first_plot_id_i, second_plot_id_i, third_plot_id_i = (
            self.plot_id_list())
        self.view.handler_dict["undo"]()
        self.view.handler_dict["redo"]()
        self.view.delete_answer_list = [True]
        self.menu("delete", "file1_int_Speed")
        self.assertEqual(self.store_names(), ["file1_int_Torque"])
        self.assertEqual(self.view.shown_name_list,
                         ["file1_Time", "file1_Speed", "file1_Torque",
                          "file1_int_Torque"])
        self.assertEqual(self.view.synthetic_name_set, {"file1_int_Torque"})
        # LLFR-00051: plot 2 had only int_Speed and is deleted.
        self.assertEqual(self.plot_id_list(),
                         [first_plot_id_i, third_plot_id_i])
        self.assertNotIn(second_plot_id_i, self.view.plot_tab_dict)
        self.assertEqual(self.view.drawn_names(first_plot_id_i),
                         ["file1_Speed"])
        self.assertEqual(self.view.drawn_names(third_plot_id_i),
                         ["file1_Torque"])
        # LLFR-00255: the undo and redo history is cleared.
        self.assertFalse(self.view.undo_enabled_b)
        self.assertFalse(self.view.redo_enabled_b)
        self.assertFalse(self.plot_controller.undo_history.can_undo())

    @covers("LLFR-00255", "LLFR-00205", "LLFR-00178", "LLFR-00598",
            "LLFR-00667")
    def test_deleting_the_last_plot_deletes_markers(self) -> None:
        """When every plot goes, the vertical markers go too.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.double_click("file1_int_Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["plot_tool"]("marker")
        self.view.handler_dict["marker_place_handler"](plot_id_i, 2.0)
        self.view.handler_dict["tip_pin_handler"](plot_id_i,
                                                  "file1_int_Speed", 1.0,
                                                  0.5)
        self.assertEqual(len(self.plot_controller.workspace.marker_list), 1)
        self.view.delete_answer_list = [True]
        self.menu("delete", "file1_int_Speed")
        self.assertEqual(self.plot_id_list(), [])
        self.assertEqual(self.plot_controller.workspace.marker_list, [])
        self.assertEqual(self.plot_controller.shared_time_range_tuple, ())
        self.assertEqual(self.store_names(), [])

    @covers("LLFR-00255", "LLFR-00178", "LLFR-00167", "LLFR-00598")
    def test_delete_removes_delta_markers_and_pending_point(self) -> None:
        """Delta markers and a first point on deleted curves go away.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.double_click("file1_Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["signal_drop_handler"](plot_id_i,
                                                      "file1_int_Speed")
        self.view.handler_dict["plot_tool"]("delta_x")
        pick = self.view.handler_dict["delta_point_pick_handler"]
        pick(plot_id_i, "file1_Speed", 1.0, 0.8)
        pick(plot_id_i, "file1_int_Speed", 2.0, 1.0)
        pick(plot_id_i, "file1_int_Speed", 3.0, 1.5)
        self.assertTrue(self.plot_controller.pending_delta_tuple)
        self.view.delete_answer_list = [True]
        self.menu("delete", "file1_int_Speed")
        plot = self.plot_controller.workspace.find_plot(plot_id_i)
        self.assertEqual(plot.delta_marker_list, [])
        self.assertEqual(self.plot_controller.pending_delta_tuple, ())
        self.assertEqual(self.view.delta_first_point_dict[plot_id_i], ())

    @covers("LLFR-00254", "LLFR-00596")
    def test_data_signals_cannot_be_deleted(self) -> None:
        """A delete request on a data file signal does nothing.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("file1_Speed")
        self.view.delete_answer_list = [True]
        self.menu("delete", "file1_Speed")
        self.assertEqual(self.view.delete_question_list, [])
        self.assertEqual(self.view.shown_name_list,
                         ["file1_Time", "file1_Speed", "file1_Torque"])
        self.assertEqual(len(self.plot_id_list()), 1)


class RenameTest(SyntheticControllerTestCase):
    """Check "Rename" of a synthetic signal."""

    @covers("LLFR-00266", "LLFR-00602", "LLFR-00603", "LLFR-00604",
            "LLFR-00605", "LLFR-00959")
    def test_rename_updates_list_legends_and_later_names(self) -> None:
        """The list and the legends show the new name.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.create("file1_int_Speed", "derivative")
        self.double_click("file1_int_Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["signal_drop_handler"](plot_id_i, "file1_Speed")
        self.view.handler_dict["tip_pin_handler"](plot_id_i,
                                                  "file1_int_Speed", 1.0,
                                                  0.5)
        self.view.name_answer_list = ["  Distance  "]
        self.menu("rename", "file1_int_Speed")
        # LLFR-00959: the field shows only the part after the prefix.
        self.assertEqual(self.view.name_question_list, ["int_Speed"])
        self.assertEqual(self.store_names(),
                         ["file1_Distance", "file1_der_int_Speed"])
        self.assertEqual(self.view.shown_name_list, [
            "file1_Time", "file1_Speed", "file1_Torque", "file1_Distance",
            "file1_der_int_Speed"])
        self.assertIn("file1_Distance", self.view.synthetic_name_set)
        # LLFR-00266: the legend of every plot that draws it.
        self.assertEqual(self.view.drawn_names(plot_id_i),
                         ["file1_Distance", "file1_Speed"])
        self.assertEqual(self.view.drawn_dict[plot_id_i][1][0][0],
                         "file1_Distance")
        # LLFR-00266: the dependents keep their names, later ones use
        # the new name.
        self.assertEqual(self.controller.store.get(
            "file1_der_int_Speed").source_name_list, ["file1_Distance"])
        self.create("file1_Distance", "max")
        self.assertEqual(self.store_names()[-1], "file1_max_Distance")
        # The signal can still be plotted under its new name.
        self.double_click("file1_Distance")
        self.assertEqual(self.view.drawn_names(self.plot_id_list()[-1]),
                         ["file1_Distance"])

    @covers("LLFR-00266", "LLFR-00138", "LLFR-00192")
    def test_undo_and_redo_after_a_rename_use_the_new_name(self) -> None:
        """The history is kept and its states use the new name.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.double_click("file1_int_Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["curve_width_handler"](
            plot_id_i, "file1_int_Speed", 3)
        self.view.handler_dict["signal_drop_handler"](plot_id_i,
                                                      "file1_Torque")
        self.view.handler_dict["undo"]()
        self.view.name_answer_list = ["Distance"]
        self.menu("rename", "file1_int_Speed")
        # LLFR-00266: renaming keeps the undo and redo history.
        self.assertTrue(self.view.undo_enabled_b)
        self.assertTrue(self.view.redo_enabled_b)
        self.view.handler_dict["redo"]()
        self.assertEqual(self.view.drawn_names(plot_id_i),
                         ["file1_Distance", "file1_Torque"])
        self.view.handler_dict["undo"]()
        self.view.handler_dict["undo"]()
        self.assertEqual(self.view.drawn_names(plot_id_i), ["file1_Distance"])
        self.assertEqual(self.view.drawn_dict[plot_id_i][0][0][4], 1)
        self.view.handler_dict["undo"]()
        self.assertEqual(self.plot_id_list(), [])
        self.view.handler_dict["redo"]()
        self.assertEqual(self.view.drawn_names(self.plot_id_list()[0]),
                         ["file1_Distance"])
        # Every undone state can be shown: no lookup of the old name.
        self.view.handler_dict["redo"]()
        self.view.handler_dict["redo"]()
        self.assertEqual(self.view.drawn_names(self.plot_id_list()[0]),
                         ["file1_Distance", "file1_Torque"])

    @covers("LLFR-00266", "LLFR-00163")
    def test_rename_keeps_a_pending_delta_point(self) -> None:
        """A first delta point on the renamed curve follows the name.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.double_click("file1_int_Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["plot_tool"]("delta_y")
        pick = self.view.handler_dict["delta_point_pick_handler"]
        pick(plot_id_i, "file1_int_Speed", 1.0, 0.5)
        self.view.name_answer_list = ["Distance"]
        self.menu("rename", "file1_int_Speed")
        self.assertEqual(self.view.delta_first_point_dict[plot_id_i][0],
                         "file1_Distance")
        pick(plot_id_i, "file1_Distance", 2.0, 1.0)
        plot = self.plot_controller.workspace.find_plot(plot_id_i)
        self.assertEqual(len(plot.delta_marker_list), 1)
        self.assertEqual(plot.delta_marker_list[0].first_point_tuple[0],
                         "file1_Distance")

    @covers("LLFR-00267", "LLFR-00606", "LLFR-00607", "LLFR-00975",
            "LLFR-00976")
    def test_invalid_names_keep_the_previous_name(self) -> None:
        """Empty names are silent; names in use show a box.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.create("file1_Torque", "integral")
        # LLFR-00959, LLFR-00975, LLFR-00976: the typed part follows the
        # prefix of the file, and the whole name is checked.
        self.view.name_answer_list = ["   ", "", "Speed", " Torque ",
                                      "int_Torque", None, " int_Speed "]
        for _ in range(7):
            self.menu("rename", "file1_int_Speed")
        self.assertEqual(self.store_names(),
                         ["file1_int_Speed", "file1_int_Torque"])
        self.assertEqual(len(self.view.information_list), 3)
        for title_str, message_str in self.view.information_list:
            self.assertEqual(title_str, "Rename signal")
            self.assertIn("already exists", message_str)
        self.assertIn('"file1_Torque"', self.view.information_list[1][1])

    @covers("LLFR-00265", "LLFR-00601")
    def test_data_signals_cannot_be_renamed(self) -> None:
        """A rename request on a data file signal does nothing.

        Inputs: none.
        Outputs: none.
        """
        self.view.name_answer_list = ["Other"]
        self.menu("rename", "file1_Speed")
        self.menu("copy_equation", "file1_Speed")
        self.assertEqual(self.view.name_question_list, [])
        self.assertEqual(self.view.shown_name_list,
                         ["file1_Time", "file1_Speed", "file1_Torque"])
        self.assertEqual(self.view.clipboard_text_list, [])


class FileTest(SyntheticControllerTestCase):
    """Check the synthetic signals when a data file is opened."""

    @covers("LLFR-00926", "LLFR-00927", "LLFR-00595", "LLFR-00930",
            "HLFR-00118")
    def test_closing_the_file_removes_synthetic_signals(self) -> None:
        """Closing a data file removes the synthetic signals it gave.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.create("file1_int_Speed", "derivative")
        self.double_click("file1_der_int_Speed")
        self.assertTrue(self.file_controller.close_file(1))
        self.assertEqual(self.store_names(), [])
        self.assertEqual(self.view.shown_name_list, [])
        self.assertEqual(self.view.synthetic_name_set, set())
        self.assertEqual(self.plot_id_list(), [])
        self.assertFalse(self.view.undo_enabled_b)
        # A new file gets the next number, and the old names are gone.
        self.open_file(make_signal_file(), keep_open_b=True)
        self.assertEqual(self.view.shown_name_list,
                         ["file2_Time", "file2_Speed", "file2_Torque"])
        self.double_click("file1_der_int_Speed")
        self.assertEqual(self.plot_id_list(), [])
        self.create("file2_Speed", "integral")
        self.assertEqual(self.store_names(), ["file2_int_Speed"])

    @covers("LLFR-00921", "LLFR-00142", "LLFR-00931", "HLFR-00117",
            "HLFR-00113")
    def test_opening_another_file_keeps_synthetic_signals(self) -> None:
        """A second data file keeps the synthetic signals of the first.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.double_click("file1_int_Speed")
        plot_id_list = self.plot_id_list()
        self.open_file(make_signal_file(), "second.csv", keep_open_b=True)
        self.assertEqual(self.store_names(), ["file1_int_Speed"])
        # LLFR-00939, LLFR-00940: the synthetic signal of file 1 is
        # listed after the signals of file 1.
        self.assertEqual(self.view.shown_name_list, [
            "file1_Time", "file1_Speed", "file1_Torque", "file1_int_Speed",
            "file2_Time", "file2_Speed", "file2_Torque"])
        self.assertEqual(self.plot_id_list(), plot_id_list)
        self.assertTrue(self.view.undo_enabled_b)
        # LLFR-00931: closing the second file keeps the first file's.
        self.file_controller.close_file(2)
        self.assertEqual(self.store_names(), ["file1_int_Speed"])
        self.assertEqual(self.plot_id_list(), plot_id_list)

    @covers("LLFR-00926", "LLFR-00940", "HLFR-00118")
    def test_product_of_two_files_goes_with_either_file(self) -> None:
        """A product of signals of two files goes with the second file.

        Inputs: none.
        Outputs: none.
        """
        self.open_file(make_signal_file(), "second.csv", keep_open_b=True)
        self.view.second_signal_answer_list = ["file2_Torque"]
        self.create("file1_Speed", "product")
        self.create("file1_Speed", "integral")
        self.assertEqual(self.store_names(), [
            "file1_Speed_prod_file2_Torque", "file1_int_Speed"])
        self.file_controller.close_file(2)
        self.assertEqual(self.store_names(), ["file1_int_Speed"])

    @covers("LLFR-00275", "LLFR-00941", "LLFR-00912")
    def test_product_lists_only_files_with_the_same_time(self) -> None:
        """The second signal dialog leaves out files of other times.

        Inputs: none.
        Outputs: none.
        """
        self.open_file(make_signal_file(np.arange(SAMPLE_COUNT_I) * 0.2),
                       "slow.csv", keep_open_b=True)
        self.open_file(make_signal_file(), "same.csv", keep_open_b=True)
        self.view.second_signal_answer_list = [None]
        self.create("file1_Speed", "product")
        name_list = self.view.second_signal_question_list[0][2]
        self.assertNotIn("file2_Torque", name_list)
        self.assertIn("file3_Torque", name_list)
        self.assertIn("file1_Torque", name_list)
        # LLFR-00941: an integral of file 2 uses the time of file 2.
        self.create("file2_Speed", "integral")
        slow_file = make_signal_file(np.arange(SAMPLE_COUNT_I) * 0.2)
        from model import synthetic_operations
        np.testing.assert_allclose(
            self.controller.store.get("file2_int_Speed").value_array,
            synthetic_operations.integral(slow_file.time_array,
                                          slow_file.signal_array("Speed")))

    @covers("LLFR-00253", "HLFR-00055", "HLFR-00105", "LLFR-00595")
    def test_data_file_is_never_written(self) -> None:
        """Creating, plotting, renaming and deleting leave the file.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as folder_str:
            path_str = os.path.join(folder_str, "data.csv")
            time_array = np.arange(50) * 0.1
            with open(path_str, "w", encoding="utf-8") as data_file:
                data_file.write("Time,Speed\n")
                for time_s in time_array:
                    data_file.write(f"{time_s:.1f},{math.sin(time_s)}\n")
            with open(path_str, "rb") as data_file:
                original_bytes = data_file.read()
            original_mtime_ns = os.stat(path_str).st_mtime_ns
            self.file_controller.close_all_files()
            self.file_controller.load_function = load_signal_file
            self.view.open_path_str = path_str
            self.file_controller.open_file_requested()
            self.assertEqual(self.view.shown_name_list, ["file2_Time",
                                                         "file2_Speed"])
            self.create("file2_Speed", "integral")
            self.view.parameter_answer_list = [[["1", "2"]]]
            self.create("file2_int_Speed", "lowpass")
            self.double_click("file2_lpf_1Hz_order2_int_Speed")
            self.view.name_answer_list = ["Smooth"]
            self.menu("rename", "file2_lpf_1Hz_order2_int_Speed")
            self.view.delete_answer_list = [True]
            self.menu("delete", "file2_int_Speed")
            with open(path_str, "rb") as data_file:
                self.assertEqual(data_file.read(), original_bytes)
            self.assertEqual(os.stat(path_str).st_mtime_ns,
                             original_mtime_ns)
            self.assertEqual(os.listdir(folder_str), ["data.csv"])
            loaded_file = load_signal_file(path_str)
            self.assertEqual(loaded_file.signal_name_list,
                             ["Time", "Speed"])


class WorkspaceRenameTest(unittest.TestCase):
    """Check the model helpers used by rename and delete."""

    @covers("LLFR-00266", "LLFR-00255", "LLFR-00598", "LLFR-00603")
    def test_workspace_rename_and_remove_signal_curves(self) -> None:
        """Curves, tips and delta points follow a rename; removal works.

        Inputs: none.
        Outputs: none.
        """
        workspace = Workspace(random.Random(1))
        tab_id_i = workspace.tab_list[0].tab_id_i
        plot = workspace.add_plot(tab_id_i)
        plot.add_curve("a")
        plot.add_curve("b")
        plot.add_pinned_tip("a", 1.0, 2.0)
        plot.add_delta_marker("x", ("a", 1.0, 2.0), ("b", 2.0, 3.0))
        other_plot = workspace.add_plot(tab_id_i)
        other_plot.add_curve("a")
        workspace.add_marker(1.0)
        snapshot = workspace.snapshot(tab_id_i)
        self.assertTrue(workspace.rename_signal("a", "z"))
        self.assertFalse(workspace.rename_signal("missing", "y"))
        snapshot.rename_signal("a", "z")
        self.assertTrue(workspace.is_unchanged_since(snapshot))
        self.assertEqual([curve.signal_name_str
                          for curve in plot.curve_list], ["z", "b"])
        self.assertEqual(plot.pinned_tip_list[0].signal_name_str, "z")
        self.assertEqual(plot.delta_marker_list[0].first_point_tuple,
                         ("z", 1.0, 2.0))
        deleted_list = workspace.remove_signal_curves({"z"})
        self.assertEqual(deleted_list, [other_plot.plot_id_i])
        self.assertEqual([curve.signal_name_str
                          for curve in plot.curve_list], ["b"])
        self.assertEqual(plot.delta_marker_list, [])
        self.assertEqual(plot.pinned_tip_list, [])
        self.assertEqual(len(workspace.marker_list), 1)
        self.assertEqual(workspace.remove_signal_curves({"b"}),
                         [plot.plot_id_i])
        self.assertEqual(workspace.marker_list, [])


if __name__ == "__main__":
    unittest.main()
