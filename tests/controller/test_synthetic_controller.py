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
        self.synthetic_name_set = set()
        self.fft_name_set = set()
        self.operation_group_list = []
        self.signal_menu_handler_dict = {}
        self.parameter_question_list = []
        self.parameter_reason_list = []
        self.parameter_answer_list = []
        self.second_signal_question_list = []
        self.second_signal_answer_list = []
        self.delete_question_list = []
        self.delete_answer_list = []
        self.name_answer_list = []
        self.name_question_list = []
        self.information_list = []
        self.clipboard_text_list = []
        self.open_path_str = ""
        self.replace_answer_b = True
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

    def ask_replace_file(self) -> bool:
        """Answer the replace question.

        Inputs: none.
        Outputs: the prepared answer.
        """
        return self.replace_answer_b

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

    def show_signal_names(self, signal_name_list: list) -> None:
        """Record the shown names.

        Inputs:
            signal_name_list: the names, in list order.
        Outputs: none.
        """
        self.shown_name_list = list(signal_name_list)

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

    def show_no_match_message(self, visible_b: bool,
                              message_str: str) -> None:
        """Do nothing.

        Inputs:
            visible_b: ignored.
            message_str: ignored.
        Outputs: none.
        """

    def clear_search(self) -> None:
        """Empty the search box, reporting it like a QLineEdit.

        Inputs: none.
        Outputs: none.
        """
        self.search_text_handler("")

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
        """Ignore the layout button state.

        Inputs:
            enabled_b: ignored.
        Outputs: none.
        """

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

    def ask_synthetic_parameter(self, title_str: str, prompt_str: str,
                                field_list: list, check_function):
        """Simulate the parameter dialog with the next answer.

        Inputs:
            title_str: the window title.
            prompt_str: the question.
            field_list: (label, starting text) per field.
            check_function: list of texts -> reason.
        Outputs: the first allowed attempt, or None.
        """
        self.parameter_question_list.append(
            (title_str, prompt_str, list(field_list)))
        attempt_list = (self.parameter_answer_list.pop(0)
                        if self.parameter_answer_list else None)
        if attempt_list is None:
            return None
        for text_list in attempt_list:
            reason_str = check_function(list(text_list))
            if not reason_str:
                return list(text_list)
            self.parameter_reason_list.append(reason_str)
        return None

    def ask_second_signal(self, title_str: str, prompt_str: str,
                          name_list: list, selected_name_str: str):
        """Answer the second signal dialog.

        Inputs:
            title_str: the window title.
            prompt_str: the question.
            name_list: the names to choose from.
            selected_name_str: the name selected at first.
        Outputs: the next prepared answer, or None.
        """
        self.second_signal_question_list.append(
            (title_str, prompt_str, list(name_list), selected_name_str))
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

    def open_file(self, signal_file: SignalFile) -> None:
        """Open a SignalFile through the real open-file flow.

        Inputs:
            signal_file: the file the loader returns.
        Outputs: none.
        """
        self.file_controller.load_function = lambda path_str: signal_file
        self.view.open_path_str = "test.csv"
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
            ("Calculus", ["Integral", "Derivative"]),
            ("Filters", ["Low-pass filter", "High-pass filter",
                         "Moving average"]),
            ("Statistics", ["Max", "Min"]),
            ("Comparison", ["Greater than", "Less than",
                            "Greater than or equal",
                            "Less than or equal"]),
            ("Arithmetic", ["Add constant", "Subtract constant",
                            "Multiply by constant", "Divide by constant",
                            "Product with signal"]),
            ("Spectrum", ["FFT"])])
        id_list = [operation_str
                   for _, operation_list in self.view.operation_group_list
                   for operation_str, _ in operation_list]
        self.assertEqual(id_list[:3], ["integral", "derivative", "lowpass"])
        self.assertEqual(id_list[-1], "fft")

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

    @covers("LLFR-00239", "LLFR-00240", "LLFR-00242", "LLFR-00243")
    def test_integral_is_listed_after_the_data_signals(self) -> None:
        """Integral creates integral_Speed, listed last and in italics.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.assertEqual(self.store_names(), ["integral_Speed"])
        self.assertEqual(self.view.shown_name_list,
                         ["Time", "Speed", "Torque", "integral_Speed"])
        self.assertEqual(self.view.synthetic_name_set, {"integral_Speed"})
        self.assertEqual(self.view.fft_name_set, set())
        # No dialog for an operation without a parameter.
        self.assertEqual(self.view.parameter_question_list, [])
        values_array = self.controller.store.get(
            "integral_Speed").value_array
        self.assertEqual(values_array[0], 0.0)
        self.assertEqual(values_array.size, SAMPLE_COUNT_I)

    @covers("LLFR-00242", "LLFR-00264", "LLFR-00240")
    def test_creation_order_and_synthetic_sources(self) -> None:
        """Signals from synthetic signals build up their names.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.create("integral_Speed", "derivative")
        self.create("Torque", "max")
        self.create("Time", "min")
        self.assertEqual(self.view.shown_name_list, [
            "Time", "Speed", "Torque", "integral_Speed",
            "derivative_integral_Speed", "max_Torque", "min_Time"])
        self.assertEqual(self.view.synthetic_name_set, {
            "integral_Speed", "derivative_integral_Speed", "max_Torque",
            "min_Time"})
        np.testing.assert_allclose(
            self.controller.store.get("max_Torque").value_array, 19.8)

    @covers("LLFR-00242", "LLFR-00095")
    def test_synthetic_signals_are_searched(self) -> None:
        """The search finds synthetic signals like data signals.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.view.search_text_handler("integ")
        self.assertEqual(self.view.shown_name_list, ["integral_Speed"])
        self.create("Torque", "integral")
        self.assertEqual(self.view.shown_name_list,
                         ["integral_Speed", "integral_Torque"])
        self.view.search_text_handler("")
        self.assertEqual(self.view.shown_name_list[-2:],
                         ["integral_Speed", "integral_Torque"])

    @covers("LLFR-00245", "LLFR-00246", "LLFR-00241")
    def test_filter_dialog_states_ranges_and_keeps_open(self) -> None:
        """The filter dialog asks for cutoff and order and checks them.

        Inputs: none.
        Outputs: none.
        """
        self.view.parameter_answer_list = [[
            ["abc", "2"], ["0", "2"], ["5", "2"], ["7", "2"],
            ["1.5", "0"], ["1.5", "9"], ["1.5", "2.5"], ["1.5", "x"],
            ["1.5", "4"]]]
        self.create("Speed", "lowpass")
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
        self.assertEqual(self.store_names(), ["lowpass_Speed"])
        self.assertEqual(self.controller.store.get(
            "lowpass_Speed").parameter, (1.5, 4))
        # LLFR-00241: the same filter again gets "_2".
        self.view.parameter_answer_list = [[["2", "2"]]]
        self.create("Speed", "lowpass")
        self.assertEqual(self.store_names(),
                         ["lowpass_Speed", "lowpass_Speed_2"])

    @covers("LLFR-00245", "LLFR-00246")
    def test_highpass_and_cancelled_filter(self) -> None:
        """A cancelled dialog creates nothing; highpass is created.

        Inputs: none.
        Outputs: none.
        """
        self.view.parameter_answer_list = [None, [["9", "2"]], [["1", "1"]]]
        self.create("Speed", "lowpass")
        self.create("Speed", "highpass")
        self.assertEqual(self.store_names(), [])
        self.create("Speed", "highpass")
        self.assertEqual(self.store_names(), ["highpass_Speed"])
        self.assertEqual(self.view.parameter_question_list[1][0],
                         "High-pass filter")
        self.assertEqual(self.view.information_list, [])

    @covers("LLFR-00247")
    def test_uneven_time_steps_show_a_box_before_any_dialog(self) -> None:
        """Filters and FFT on uneven steps show an information box.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.arange(SAMPLE_COUNT_I) * 0.1
        time_array[50:] += 0.02
        self.open_file(make_signal_file(time_array))
        for operation_str in ("lowpass", "highpass", "fft"):
            self.create("Speed", operation_str)
        self.assertEqual(self.view.parameter_question_list, [])
        self.assertEqual(len(self.view.information_list), 3)
        for title_str, message_str in self.view.information_list:
            self.assertEqual(title_str, "Create synthetic signal")
            self.assertIn("evenly spaced time samples", message_str)
        self.assertEqual(self.store_names(), [])
        # LLFR-00247: the other operations still work.
        self.create("Speed", "integral")
        self.assertEqual(self.store_names(), ["integral_Speed"])

    @covers("LLFR-00269", "LLFR-00270")
    def test_moving_average_window_dialog(self) -> None:
        """The window dialog states 2 to n and refuses other values.

        Inputs: none.
        Outputs: none.
        """
        self.view.parameter_answer_list = [
            None, [["1"], ["2.5"], ["x"], ["101"], [""], ["5"]]]
        self.create("Speed", "movingaverage")
        self.assertEqual(self.store_names(), [])
        self.create("Speed", "movingaverage")
        title_str, prompt_str, field_list = (
            self.view.parameter_question_list[1])
        self.assertEqual(title_str, "Moving average")
        self.assertIn("from 2 to 100 samples", prompt_str)
        self.assertEqual(len(field_list), 1)
        self.assertEqual(len(self.view.parameter_reason_list), 5)
        for reason_str in self.view.parameter_reason_list:
            self.assertIn("whole number of samples from 2 to 100",
                          reason_str)
        self.assertEqual(self.store_names(), ["movingaverage_Speed"])
        self.assertEqual(self.controller.store.get(
            "movingaverage_Speed").parameter, 5)

    @covers("LLFR-00269")
    def test_signal_too_short_for_a_moving_average(self) -> None:
        """A one-sample file shows a box instead of the window dialog.

        Inputs: none.
        Outputs: none.
        """
        self.open_file(make_signal_file([0.0]))
        self.create("Speed", "movingaverage")
        self.assertEqual(self.view.parameter_question_list, [])
        self.assertEqual(len(self.view.information_list), 1)
        self.assertEqual(self.store_names(), [])

    @covers("LLFR-00272", "LLFR-00273", "LLFR-00274")
    def test_constant_dialog(self) -> None:
        """Constants must be numbers, not 0 for a division.

        Inputs: none.
        Outputs: none.
        """
        self.view.parameter_answer_list = [
            [["abc"], ["nan"], ["0.5"]], [["0"], ["4"]], None,
            [["3"]], [["-1"]]]
        self.create("Torque", "greater")
        self.create("Torque", "divide")
        self.create("Torque", "subtract")
        self.create("Torque", "multiply")
        self.create("Torque", "lessorequal")
        reason_list = self.view.parameter_reason_list
        self.assertEqual(reason_list, [
            "The constant must be a number.",
            "The constant must be a number.",
            "The constant must not be 0 for a division."])
        self.assertIn("not 0", self.view.parameter_question_list[1][1])
        self.assertEqual(self.view.parameter_question_list[0][2],
                         [("Constant:", "")])
        self.assertEqual(self.store_names(), [
            "greater_Torque", "divide_Torque", "multiply_Torque",
            "lessorequal_Torque"])
        store = self.controller.store
        torque_array = make_signal_file().signal_array("Torque")
        np.testing.assert_allclose(store.get("greater_Torque").value_array,
                                   (torque_array > 0.5).astype(float))
        np.testing.assert_allclose(store.get("divide_Torque").value_array,
                                   torque_array / 4.0)
        np.testing.assert_allclose(
            store.get("multiply_Torque").value_array, torque_array * 3.0)
        np.testing.assert_allclose(
            store.get("lessorequal_Torque").value_array,
            (torque_array <= -1.0).astype(float))

    @covers("LLFR-00275", "LLFR-00276", "LLFR-00240")
    def test_product_second_signal_dialog(self) -> None:
        """The second signal list has every non-FFT signal.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "fft")
        self.create("Speed", "integral")
        self.view.second_signal_answer_list = [None, "Torque", "Speed"]
        self.create("Speed", "product")
        self.assertEqual(self.store_names(),
                         ["fft_Speed_0s_to_9.9s", "integral_Speed"])
        title_str, prompt_str, name_list, selected_name_str = (
            self.view.second_signal_question_list[0])
        self.assertEqual(title_str, "Product with signal")
        self.assertIn("Speed", prompt_str)
        self.assertEqual(name_list, ["Time", "Speed", "Torque",
                                     "integral_Speed"])
        self.assertEqual(selected_name_str, "Speed")
        self.create("Speed", "product")
        self.create("Speed", "product")
        self.assertEqual(self.store_names()[-2:],
                         ["product_Speed_Torque", "product_Speed_Speed"])
        speed_array = make_signal_file().signal_array("Speed")
        np.testing.assert_allclose(
            self.controller.store.get("product_Speed_Torque").value_array,
            speed_array * make_signal_file().signal_array("Torque"))

    @covers("LLFR-00248", "LLFR-00240", "LLFR-00249")
    def test_fft_uses_the_whole_file_without_time_plots(self) -> None:
        """With no plot, the FFT range is the file's whole range.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "fft")
        signal = self.controller.store.get("fft_Speed_0s_to_9.9s")
        self.assertEqual(signal.parameter, (0.0, 9.9))
        self.assertEqual(signal.value_array.size, SAMPLE_COUNT_I // 2 + 1)
        self.assertEqual(self.view.fft_name_set, {"fft_Speed_0s_to_9.9s"})
        self.assertEqual(self.view.parameter_question_list, [])

    @covers("LLFR-00248", "LLFR-00240", "LLFR-00070")
    def test_fft_uses_the_shared_range_of_the_time_plots(self) -> None:
        """The FFT range is the zoomed range shared by the plots.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["time_range_handler"](plot_id_i, 1.5, 3.0)
        self.create("Torque", "fft")
        self.assertEqual(self.store_names(), ["fft_Torque_1.5s_to_3s"])
        # LLFR-00248: a later change of the range changes nothing.
        self.view.handler_dict["time_range_handler"](plot_id_i, 0.0, 9.0)
        self.assertEqual(self.controller.store.get(
            "fft_Torque_1.5s_to_3s").parameter, (1.5, 3.0))
        # LLFR-00241: the same range again gets "_2"; a reset range is
        # the whole file again.
        self.view.handler_dict["time_range_handler"](plot_id_i, 1.5, 3.0)
        self.create("Torque", "fft")
        self.view.handler_dict["reset_zoom"]()
        self.create("Torque", "fft")
        self.assertEqual(self.store_names(), [
            "fft_Torque_1.5s_to_3s", "fft_Torque_1.5s_to_3s_2",
            "fft_Torque_0s_to_9.9s"])

    @covers("LLFR-00250")
    def test_fft_with_too_few_samples_shows_a_box(self) -> None:
        """A range with fewer than 8 samples creates no FFT.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["time_range_handler"](plot_id_i, 1.0, 1.65)
        self.create("Speed", "fft")
        self.assertEqual(self.store_names(), [])
        self.assertEqual(len(self.view.information_list), 1)
        self.assertIn("too few samples", self.view.information_list[0][1])
        self.view.handler_dict["time_range_handler"](plot_id_i, 1.0, 1.75)
        self.create("Speed", "fft")
        self.assertEqual(self.store_names(), ["fft_Speed_1s_to_1.75s"])

    @covers("LLFR-00251")
    def test_no_operation_on_fft_signals(self) -> None:
        """An operation requested on an FFT signal does nothing.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "fft")
        fft_name_str = self.store_names()[0]
        self.view.parameter_answer_list = [[["2"]]]
        for operation_str in ("integral", "add", "fft", "product"):
            self.create(fft_name_str, operation_str)
        self.assertEqual(self.store_names(), [fft_name_str])
        self.assertEqual(self.view.parameter_question_list, [])
        self.assertEqual(self.view.second_signal_question_list, [])
        self.assertEqual(self.view.information_list, [])

    @covers("LLFR-00239")
    def test_stale_requests_are_ignored(self) -> None:
        """Unknown signals or operations create nothing.

        Inputs: none.
        Outputs: none.
        """
        self.create("Pressure", "integral")
        self.create("Speed", "cube")
        self.menu("copy_name", "Pressure")
        self.assertEqual(self.store_names(), [])
        self.assertEqual(self.view.clipboard_text_list, [])

    @covers("LLFR-00140", "LLFR-00255")
    def test_creating_is_not_undoable(self) -> None:
        """Creating a synthetic signal records no undo step.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.assertFalse(self.view.undo_enabled_b)
        self.assertFalse(self.plot_controller.undo_history.can_undo())


class PlotSyntheticTest(SyntheticControllerTestCase):
    """Check that synthetic signals are plotted like data signals."""

    @covers("LLFR-00242", "LLFR-00019", "LLFR-00020", "LLFR-00021")
    def test_double_click_and_drop_draw_synthetic_signals(self) -> None:
        """Synthetic signals can be double-clicked and dropped.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.create("Torque", "max")
        self.double_click("integral_Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["signal_drop_handler"](plot_id_i,
                                                      "max_Torque")
        self.assertEqual(self.view.drawn_names(plot_id_i),
                         ["integral_Speed", "max_Torque"])
        curve_list = self.view.drawn_dict[plot_id_i][0]
        np.testing.assert_allclose(
            curve_list[0][2],
            self.controller.store.get("integral_Speed").value_array)
        np.testing.assert_allclose(curve_list[1][2], 19.8)

    @covers("LLFR-00242", "LLFR-00257")
    def test_fft_signals_are_not_plotted_yet(self) -> None:
        """FFT signals: no plot, no curve and no message (until #109).

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "fft")
        fft_name_str = self.store_names()[0]
        self.double_click(fft_name_str)
        self.assertEqual(self.plot_id_list(), [])
        self.double_click("Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["signal_drop_handler"](plot_id_i,
                                                      fft_name_str)
        self.assertEqual(self.view.drawn_names(plot_id_i), ["Speed"])
        self.assertEqual(self.view.full_tab_count_i, 0)
        self.assertEqual(self.view.information_list, [])
        self.assertTrue(self.plot_controller.is_fft_signal_blocked(
            fft_name_str))
        self.assertFalse(self.plot_controller.is_fft_signal_blocked(
            "Speed"))

    @covers("LLFR-00263", "LLFR-00039", "LLFR-00049", "LLFR-00028")
    def test_removing_curves_keeps_the_synthetic_signal(self) -> None:
        """Curve, plot and tab deletions keep the signal in the list.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.double_click("integral_Speed")
        first_plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["curve_delete_handler"](first_plot_id_i,
                                                       "integral_Speed")
        self.double_click("integral_Speed")
        self.view.handler_dict["plot_delete_handler"](
            self.plot_id_list()[0])
        self.view.handler_dict["add_tab"]()
        self.double_click("integral_Speed")
        self.view.handler_dict["delete_tab"](self.view.current_tab_id())
        self.assertEqual(self.plot_id_list(), [])
        self.assertEqual(self.store_names(), ["integral_Speed"])
        self.assertIn("integral_Speed", self.view.shown_name_list)
        # LLFR-00263: the signal can be plotted again.
        self.double_click("integral_Speed")
        self.assertEqual(len(self.plot_id_list()), 1)


class CopyTest(SyntheticControllerTestCase):
    """Check "Copy name" and "Copy equation"."""

    @covers("LLFR-00277")
    def test_copy_name_for_every_kind_of_signal(self) -> None:
        """The name of a data, synthetic or FFT signal is copied.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.create("Speed", "fft")
        for name_str in ("Time", "Speed", "integral_Speed",
                         "fft_Speed_0s_to_9.9s"):
            self.menu("copy_name", name_str)
        self.assertEqual(self.view.clipboard_text_list, [
            "Time", "Speed", "integral_Speed", "fft_Speed_0s_to_9.9s"])

    @covers("LLFR-00278", "LLFR-00279", "LLFR-00225")
    def test_copy_equation_lists_the_signal_and_its_ancestors(
            self) -> None:
        """The equation is the JSON list of the needed entries.

        Inputs: none.
        Outputs: none.
        """
        self.view.parameter_answer_list = [[["2", "3"]]]
        self.create("Speed", "lowpass")
        self.create("Torque", "integral")
        self.create("lowpass_Speed", "derivative")
        self.menu("copy_equation", "derivative_lowpass_Speed")
        self.menu("copy_equation", "Speed")
        self.assertEqual(len(self.view.clipboard_text_list), 1)
        text_str = self.view.clipboard_text_list[0]
        self.assertEqual(text_str, self.controller.store.equation_text(
            "derivative_lowpass_Speed"))
        self.assertEqual(json.loads(text_str), [
            {"name": "lowpass_Speed", "operation": "lowpass",
             "signals": ["Speed"],
             "parameter": {"cutoff": 2.0, "order": 3}},
            {"name": "derivative_lowpass_Speed", "operation": "derivative",
             "signals": ["lowpass_Speed"], "parameter": None}])
        self.assertTrue(text_str.startswith("[\n  {\n"))


class DeleteTest(SyntheticControllerTestCase):
    """Check "Delete signal" of a synthetic signal."""

    def build_dependents(self) -> None:
        """Create integral_Speed, two levels of dependents and plots.

        Plot 1 draws Speed and derivative_integral_Speed; plot 2 draws
        only integral_Speed; plot 3 in a second tab draws
        max_derivative_integral_Speed and Torque.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.create("integral_Speed", "derivative")
        self.create("Torque", "integral")
        self.create("derivative_integral_Speed", "max")
        self.double_click("Speed")
        first_plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["signal_drop_handler"](
            first_plot_id_i, "derivative_integral_Speed")
        self.double_click("integral_Speed")
        self.view.handler_dict["add_tab"]()
        self.double_click("max_derivative_integral_Speed")
        self.view.handler_dict["signal_drop_handler"](
            self.plot_id_list()[2], "Torque")

    @covers("LLFR-00255")
    def test_confirmation_names_direct_and_indirect_dependents(
            self) -> None:
        """The question names every dependent; No keeps everything.

        Inputs: none.
        Outputs: none.
        """
        self.build_dependents()
        self.view.delete_answer_list = [False]
        self.menu("delete", "integral_Speed")
        self.assertEqual(self.view.delete_question_list, [
            ("integral_Speed", ["derivative_integral_Speed",
                                "max_derivative_integral_Speed"])])
        self.assertEqual(len(self.store_names()), 4)
        self.assertEqual(len(self.plot_id_list()), 3)
        self.assertTrue(self.view.undo_enabled_b)

    @covers("LLFR-00255", "LLFR-00051", "LLFR-00050")
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
        self.menu("delete", "integral_Speed")
        self.assertEqual(self.store_names(), ["integral_Torque"])
        self.assertEqual(self.view.shown_name_list,
                         ["Time", "Speed", "Torque", "integral_Torque"])
        self.assertEqual(self.view.synthetic_name_set, {"integral_Torque"})
        # LLFR-00051: plot 2 had only integral_Speed and is deleted.
        self.assertEqual(self.plot_id_list(),
                         [first_plot_id_i, third_plot_id_i])
        self.assertNotIn(second_plot_id_i, self.view.plot_tab_dict)
        self.assertEqual(self.view.drawn_names(first_plot_id_i), ["Speed"])
        self.assertEqual(self.view.drawn_names(third_plot_id_i),
                         ["Torque"])
        # LLFR-00255: the undo and redo history is cleared.
        self.assertFalse(self.view.undo_enabled_b)
        self.assertFalse(self.view.redo_enabled_b)
        self.assertFalse(self.plot_controller.undo_history.can_undo())

    @covers("LLFR-00255", "LLFR-00205", "LLFR-00178")
    def test_deleting_the_last_plot_deletes_markers(self) -> None:
        """When every plot goes, the vertical markers go too.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.double_click("integral_Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["plot_tool"]("marker")
        self.view.handler_dict["marker_place_handler"](plot_id_i, 2.0)
        self.view.handler_dict["tip_pin_handler"](plot_id_i,
                                                  "integral_Speed", 1.0,
                                                  0.5)
        self.assertEqual(len(self.plot_controller.workspace.marker_list), 1)
        self.view.delete_answer_list = [True]
        self.menu("delete", "integral_Speed")
        self.assertEqual(self.plot_id_list(), [])
        self.assertEqual(self.plot_controller.workspace.marker_list, [])
        self.assertEqual(self.plot_controller.shared_time_range_tuple, ())
        self.assertEqual(self.store_names(), [])

    @covers("LLFR-00255", "LLFR-00178", "LLFR-00167")
    def test_delete_removes_delta_markers_and_pending_point(self) -> None:
        """Delta markers and a first point on deleted curves go away.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.double_click("Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["signal_drop_handler"](plot_id_i,
                                                      "integral_Speed")
        self.view.handler_dict["plot_tool"]("delta_x")
        pick = self.view.handler_dict["delta_point_pick_handler"]
        pick(plot_id_i, "Speed", 1.0, 0.8)
        pick(plot_id_i, "integral_Speed", 2.0, 1.0)
        pick(plot_id_i, "integral_Speed", 3.0, 1.5)
        self.assertTrue(self.plot_controller.pending_delta_tuple)
        self.view.delete_answer_list = [True]
        self.menu("delete", "integral_Speed")
        plot = self.plot_controller.workspace.find_plot(plot_id_i)
        self.assertEqual(plot.delta_marker_list, [])
        self.assertEqual(self.plot_controller.pending_delta_tuple, ())
        self.assertEqual(self.view.delta_first_point_dict[plot_id_i], ())

    @covers("LLFR-00254")
    def test_data_signals_cannot_be_deleted(self) -> None:
        """A delete request on a data file signal does nothing.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("Speed")
        self.view.delete_answer_list = [True]
        self.menu("delete", "Speed")
        self.assertEqual(self.view.delete_question_list, [])
        self.assertEqual(self.view.shown_name_list,
                         ["Time", "Speed", "Torque"])
        self.assertEqual(len(self.plot_id_list()), 1)


class RenameTest(SyntheticControllerTestCase):
    """Check "Rename" of a synthetic signal."""

    @covers("LLFR-00266")
    def test_rename_updates_list_legends_and_later_names(self) -> None:
        """The list and the legends show the new name.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.create("integral_Speed", "derivative")
        self.double_click("integral_Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["signal_drop_handler"](plot_id_i, "Speed")
        self.view.handler_dict["tip_pin_handler"](plot_id_i,
                                                  "integral_Speed", 1.0,
                                                  0.5)
        self.view.name_answer_list = ["  Distance  "]
        self.menu("rename", "integral_Speed")
        self.assertEqual(self.view.name_question_list, ["integral_Speed"])
        self.assertEqual(self.store_names(),
                         ["Distance", "derivative_integral_Speed"])
        self.assertEqual(self.view.shown_name_list, [
            "Time", "Speed", "Torque", "Distance",
            "derivative_integral_Speed"])
        self.assertIn("Distance", self.view.synthetic_name_set)
        # LLFR-00266: the legend of every plot that draws it.
        self.assertEqual(self.view.drawn_names(plot_id_i),
                         ["Distance", "Speed"])
        self.assertEqual(self.view.drawn_dict[plot_id_i][1][0][0],
                         "Distance")
        # LLFR-00266: the dependents keep their names, later ones use
        # the new name.
        self.assertEqual(self.controller.store.get(
            "derivative_integral_Speed").source_name_list, ["Distance"])
        self.create("Distance", "max")
        self.assertEqual(self.store_names()[-1], "max_Distance")
        # The signal can still be plotted under its new name.
        self.double_click("Distance")
        self.assertEqual(self.view.drawn_names(self.plot_id_list()[-1]),
                         ["Distance"])

    @covers("LLFR-00266", "LLFR-00138", "LLFR-00192")
    def test_undo_and_redo_after_a_rename_use_the_new_name(self) -> None:
        """The history is kept and its states use the new name.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.double_click("integral_Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["curve_width_handler"](
            plot_id_i, "integral_Speed", 3)
        self.view.handler_dict["signal_drop_handler"](plot_id_i, "Torque")
        self.view.handler_dict["undo"]()
        self.view.name_answer_list = ["Distance"]
        self.menu("rename", "integral_Speed")
        # LLFR-00266: renaming keeps the undo and redo history.
        self.assertTrue(self.view.undo_enabled_b)
        self.assertTrue(self.view.redo_enabled_b)
        self.view.handler_dict["redo"]()
        self.assertEqual(self.view.drawn_names(plot_id_i),
                         ["Distance", "Torque"])
        self.view.handler_dict["undo"]()
        self.view.handler_dict["undo"]()
        self.assertEqual(self.view.drawn_names(plot_id_i), ["Distance"])
        self.assertEqual(self.view.drawn_dict[plot_id_i][0][0][4], 1)
        self.view.handler_dict["undo"]()
        self.assertEqual(self.plot_id_list(), [])
        self.view.handler_dict["redo"]()
        self.assertEqual(self.view.drawn_names(self.plot_id_list()[0]),
                         ["Distance"])
        # Every undone state can be shown: no lookup of the old name.
        self.view.handler_dict["redo"]()
        self.view.handler_dict["redo"]()
        self.assertEqual(self.view.drawn_names(self.plot_id_list()[0]),
                         ["Distance", "Torque"])

    @covers("LLFR-00266", "LLFR-00163")
    def test_rename_keeps_a_pending_delta_point(self) -> None:
        """A first delta point on the renamed curve follows the name.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.double_click("integral_Speed")
        plot_id_i = self.plot_id_list()[0]
        self.view.handler_dict["plot_tool"]("delta_y")
        pick = self.view.handler_dict["delta_point_pick_handler"]
        pick(plot_id_i, "integral_Speed", 1.0, 0.5)
        self.view.name_answer_list = ["Distance"]
        self.menu("rename", "integral_Speed")
        self.assertEqual(self.view.delta_first_point_dict[plot_id_i][0],
                         "Distance")
        pick(plot_id_i, "Distance", 2.0, 1.0)
        plot = self.plot_controller.workspace.find_plot(plot_id_i)
        self.assertEqual(len(plot.delta_marker_list), 1)
        self.assertEqual(plot.delta_marker_list[0].first_point_tuple[0],
                         "Distance")

    @covers("LLFR-00267")
    def test_invalid_names_keep_the_previous_name(self) -> None:
        """Empty names are silent; names in use show a box.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.create("Torque", "integral")
        self.view.name_answer_list = ["   ", "", "Speed", " Torque ",
                                      "integral_Torque", None,
                                      " integral_Speed "]
        for _ in range(7):
            self.menu("rename", "integral_Speed")
        self.assertEqual(self.store_names(),
                         ["integral_Speed", "integral_Torque"])
        self.assertEqual(len(self.view.information_list), 3)
        for title_str, message_str in self.view.information_list:
            self.assertEqual(title_str, "Rename signal")
            self.assertIn("already exists", message_str)
        self.assertIn('"Torque"', self.view.information_list[1][1])

    @covers("LLFR-00265")
    def test_data_signals_cannot_be_renamed(self) -> None:
        """A rename request on a data file signal does nothing.

        Inputs: none.
        Outputs: none.
        """
        self.view.name_answer_list = ["Other"]
        self.menu("rename", "Speed")
        self.menu("copy_equation", "Speed")
        self.assertEqual(self.view.name_question_list, [])
        self.assertEqual(self.view.shown_name_list,
                         ["Time", "Speed", "Torque"])
        self.assertEqual(self.view.clipboard_text_list, [])


class FileTest(SyntheticControllerTestCase):
    """Check the synthetic signals when a data file is opened."""

    @covers("LLFR-00252", "LLFR-00017", "LLFR-00142")
    def test_replacing_the_file_removes_synthetic_signals(self) -> None:
        """A new data file starts with no synthetic signal.

        Inputs: none.
        Outputs: none.
        """
        self.create("Speed", "integral")
        self.double_click("integral_Speed")
        self.view.search_text_handler("integ")
        self.open_file(make_signal_file())
        self.assertEqual(self.store_names(), [])
        self.assertEqual(self.view.shown_name_list,
                         ["Time", "Speed", "Torque"])
        self.assertEqual(self.view.synthetic_name_set, set())
        self.assertEqual(self.plot_id_list(), [])
        self.double_click("integral_Speed")
        self.assertEqual(self.plot_id_list(), [])
        # The same name can be created again from the new file.
        self.create("Speed", "integral")
        self.assertEqual(self.store_names(), ["integral_Speed"])

    @covers("LLFR-00253", "HLFR-00055")
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
            self.file_controller.load_function = load_signal_file
            self.view.open_path_str = path_str
            self.file_controller.open_file_requested()
            self.assertEqual(self.view.shown_name_list, ["Time", "Speed"])
            self.create("Speed", "integral")
            self.view.parameter_answer_list = [[["1", "2"]]]
            self.create("integral_Speed", "lowpass")
            self.double_click("lowpass_integral_Speed")
            self.view.name_answer_list = ["Smooth"]
            self.menu("rename", "lowpass_integral_Speed")
            self.view.delete_answer_list = [True]
            self.menu("delete", "integral_Speed")
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

    @covers("LLFR-00266", "LLFR-00255")
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
