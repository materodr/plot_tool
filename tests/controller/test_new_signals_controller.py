"""Tests for the new synthetic signals of the synthetic controller
(issue #260).

Covers "Create signal" of a file menu (HLFR-00162: LLFR-01278 to
LLFR-01284, LLFR-01292), the range dialog of the statistics
(HLFR-00164: LLFR-01297 to LLFR-01302) and the trigonometric operations
(HLFR-00163: LLFR-01294), with the fake window of
tests.controller.test_synthetic_controller.
"""

import random
import unittest

import numpy as np

from tests.support import covers

from controller.main_controller import MainController
from tests.controller.test_synthetic_controller import (
    FakeSyntheticWindow, SyntheticControllerTestCase, make_signal_file)


class FakeScratchWindow(FakeSyntheticWindow):
    """The fake window, with the "Create signal" option of the file menu.

    Inputs: none.
    """

    def set_generator_operations(self, operation_list: list) -> None:
        """Record the options of "Create signal".

        Inputs:
            operation_list: (operation id, label) in menu order.
        Outputs: none.
        """
        self.generator_operation_list = list(operation_list)

    def set_create_signal_handler(self, handler) -> None:
        """Record the handler of "Create signal".

        Inputs:
            handler: function taking (file number, operation id).
        Outputs: none.
        """
        self.create_signal_handler = handler


class NewSignalTestCase(SyntheticControllerTestCase):
    """The controllers with the fake window that has "Create signal"."""

    def setUp(self) -> None:
        """Create the controllers and open the test file.

        Inputs: none.
        Outputs: none.
        """
        self.view = FakeScratchWindow()
        self.main_controller = MainController(self.view)
        self.main_controller.plot_controller.workspace.random_generator = (
            random.Random(3))
        self.file_controller = self.main_controller.file_controller
        self.plot_controller = self.main_controller.plot_controller
        self.controller = self.main_controller.synthetic_controller
        self.open_file(make_signal_file())

    def store_names(self) -> list:
        """Return the names of the synthetic signals.

        Inputs: none.
        Outputs: the names, in creation order.
        """
        return self.controller.store.names()


class CreateSignalTest(NewSignalTestCase):
    """The signals made from scratch."""

    @covers("LLFR-01278", "HLFR-00162")
    def test_options_in_menu_order(self) -> None:
        """The view gets the six options, in order.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.view.generator_operation_list, [
            ("constant", "Constant"), ("step", "Step"), ("ramp", "Ramp"),
            ("polynomial", "Polynomial"), ("sine", "Sine"),
            ("cosine", "Cosine")])

    @covers("LLFR-01279", "LLFR-01283", "LLFR-01284", "LLFR-01286",
            "LLFR-01290", "LLFR-01292", "HLFR-00162")
    def test_step_from_the_file_row(self) -> None:
        """The dialog has the fields of a step; the signal is on the time
        base of the file, belongs to it and is listed.

        Inputs: none.
        Outputs: none.
        """
        self.view.parameter_answer_list = [[["1", "0", "5"]]]
        self.view.create_signal_handler(1, "step")
        title_str, _, field_list = self.view.parameter_question_list[0]
        self.assertEqual(title_str, "Step")
        self.assertEqual([label_str for label_str, _ in field_list],
                         ["Step time (s):", "Value before:",
                          "Value after:"])
        self.assertEqual(self.store_names(), ["file1_step_1s_0_to_5"])
        signal = self.controller.store.get("file1_step_1s_0_to_5")
        self.assertEqual(signal.file_number_i, 1)
        self.assertEqual(signal.source_name_list, ["file1_Time"])
        time_array = np.arange(100) * 0.1
        np.testing.assert_allclose(signal.value_array,
                                   np.where(time_array < 1.0, 0.0, 5.0))
        self.assertIn("file1_step_1s_0_to_5",
                      self.controller.signal_list_name_list())

    @covers("LLFR-01279", "HLFR-00162")
    def test_fields_of_every_option(self) -> None:
        """Constant, Ramp, Polynomial, Sine and Cosine ask their values.

        Inputs: none.
        Outputs: none.
        """
        expected_dict = {
            "constant": ["Value:"],
            "ramp": ["Start time (s):", "Slope (per s):", "Start value:"],
            "polynomial": ["a:", "b:", "c:"],
            "sine": ["Amplitude:", "Frequency (Hz):", "Phase (degrees):",
                     "Offset:"],
            "cosine": ["Amplitude:", "Frequency (Hz):", "Phase (degrees):",
                       "Offset:"]}
        for operation_str, label_list in expected_dict.items():
            with self.subTest(operation=operation_str):
                self.view.parameter_question_list = []
                self.view.parameter_answer_list = [None]
                self.view.create_signal_handler(1, operation_str)
                self.assertEqual(
                    [label_str for label_str, _
                     in self.view.parameter_question_list[0][2]],
                    label_list)

    @covers("LLFR-01280", "LLFR-01281", "LLFR-01369", "LLFR-01282",
            "HLFR-00162")
    def test_invalid_values_keep_the_dialog_open(self) -> None:
        """A text that is not a number or a frequency of 0 is refused
        with a reason; a cancel creates nothing.

        Inputs: none.
        Outputs: none.
        """
        self.view.parameter_answer_list = [[["1", "0", "0", "0"],
                                            ["1", "x", "0", "0"],
                                            ["1", "2", "0", "0"]]]
        self.view.create_signal_handler(1, "sine")
        self.assertEqual(len(self.view.parameter_reason_list), 2)
        self.assertIn("frequency", self.view.parameter_reason_list[0])
        self.assertEqual(self.store_names(),
                         ["file1_sin_amp1_2Hz_ph0deg_off0"])
        self.view.parameter_answer_list = [None]
        self.view.create_signal_handler(1, "constant")
        self.view.create_signal_handler(7, "constant")
        self.view.create_signal_handler(1, "integral")
        self.assertEqual(len(self.store_names()), 1)


class StatisticRangeTest(NewSignalTestCase):
    """The range dialog of the statistics."""

    def plot_speed(self) -> None:
        """Plot Speed in a time plot and show 2 s to 4 s.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("file1_Speed")
        plot_id_i = self.plot_controller.time_plot_list()[0].plot_id_i
        self.view.handler_dict["time_range_handler"](plot_id_i, 2.0, 4.0)

    @covers("LLFR-01297", "LLFR-01370", "LLFR-01298", "LLFR-00271",
            "HLFR-00164")
    def test_whole_signal_is_chosen_at_first(self) -> None:
        """The dialog offers both ranges, the whole signal first, and
        creates a constant of the whole signal.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Torque", "mean")
        self.assertEqual(self.view.parameter_choice_list[-1], (
            "Range:", [("whole", "Whole signal"),
                       ("shown", "Shown x-axis range")], "whole"))
        self.assertEqual(self.store_names(), ["file1_mean_Torque"])
        np.testing.assert_allclose(
            self.controller.store.get("file1_mean_Torque").value_array,
            np.full(100, np.mean(np.arange(100) * 0.2)))

    @covers("LLFR-01299", "LLFR-01296", "HLFR-00164")
    def test_shown_range(self) -> None:
        """"Shown x-axis range" uses the samples of the shown range and
        puts it in the name.

        Inputs: none.
        Outputs: none.
        """
        self.plot_speed()
        self.view.parameter_answer_list = [[["shown"]]]
        self.create("file1_Torque", "median")
        self.assertEqual(self.store_names(), ["file1_median_2s_to_4s_Torque"])
        value_array = self.controller.store.get(
            "file1_median_2s_to_4s_Torque").value_array
        np.testing.assert_allclose(value_array, np.full(100, 6.0))

    @covers("LLFR-01300", "LLFR-01371", "LLFR-01301", "LLFR-01302",
            "HLFR-00164")
    def test_shown_range_refused_or_cancelled(self) -> None:
        """With no time plot the dialog says a time plot is needed; a
        cancel creates nothing.

        Inputs: none.
        Outputs: none.
        """
        self.view.parameter_answer_list = [[["shown"], ["whole"]]]
        self.create("file1_Torque", "rms")
        self.assertIn("time plot", self.view.parameter_reason_list[0])
        self.assertEqual(self.store_names(), ["file1_rms_Torque"])
        self.view.parameter_answer_list = [None]
        self.create("file1_Torque", "std")
        self.assertEqual(self.store_names(), ["file1_rms_Torque"])

    @covers("LLFR-01301", "LLFR-01372", "HLFR-00164")
    def test_range_with_no_sample_of_the_signal(self) -> None:
        """A shown range outside the signal's file keeps the dialog
        open with the reason.

        Inputs: none.
        Outputs: none.
        """
        self.plot_speed()
        self.plot_controller.shared_time_range_tuple = (50.0, 60.0)
        self.view.parameter_answer_list = [[["shown"]]]
        self.create("file1_Torque", "max")
        self.assertEqual(len(self.view.parameter_reason_list), 1)
        self.assertIn("no sample", self.view.parameter_reason_list[0])
        self.assertEqual(self.store_names(), [])


class TrigonometricControllerTest(NewSignalTestCase):
    """The trigonometric operations in the menu."""

    @covers("LLFR-01294", "LLFR-00268", "HLFR-00163")
    def test_sine_runs_at_once(self) -> None:
        """Sine of a signal needs no dialog.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Torque", "sind")
        self.assertEqual(self.view.parameter_question_list, [])
        self.assertEqual(self.store_names(), ["file1_sind_Torque"])


if __name__ == "__main__":
    unittest.main()
