"""Tests for synthetic signals, Save signals and layouts with several
data files (issue #190, step 3).

The whole app's controllers (MainController) run with a fake view, as
in test_synthetic_controller and test_layout_synthetic_controller; the
Save signals flow runs with the real DataFileSet, the real store and the
real writer, as in test_save_signals_controller. No Qt is needed.
"""

import json
import os
import random
import tempfile
import unittest

import numpy as np

from tests.support import covers, expand_all_files
from tests.controller.test_layout_synthetic_controller import FakeAppWindow
from tests.controller.test_save_signals_controller import (
    FakeFileController, FakeSaveSignalsView, FakeSyntheticController)
from tests.controller.test_synthetic_controller import SAMPLE_COUNT_I

from controller.main_controller import MainController
from controller.save_signals_controller import SaveSignalsController
from controller.synthetic_controller import (
    CREATE_TITLE_STR, FFT_NEEDS_TIME_PLOT_STR)
from model import synthetic_operations as operations
from model.data_files import DataFileSet, prefix_number
from model.errors import SyntheticSourceError
from model.file_loader import load_signal_file
from model.file_writer import CSV_FORMAT_STR
from model.layout_file import (
    LAYOUT_FORMAT_STR, LAYOUT_VERSION_I, read_layout_file)
from model.signal_file import SignalFile
from model.synthetic_signals import LAYOUT_KEY_STR, ordered_signal_names

# The sample files of PCR-00032 whose time signals differ only by
# rounding (LLFR-00977).
GOOD_FOLDER_STR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "user_tests", "good")
GOOD_EXCEL_PATH_STR = os.path.join(GOOD_FOLDER_STR, "signals.xlsx")
GOOD_MAT_PATH_STR = os.path.join(GOOD_FOLDER_STR, "signals.mat")


def make_file(time_array=None, offset_f: float = 0.0,
              path_str: str = "a.csv") -> SignalFile:
    """Build a SignalFile with Time, Speed and Torque.

    Inputs:
        time_array: the time samples; 0 to 9.9 s every 0.1 s when None.
        offset_f: added to Speed, so that two files have other values.
        path_str: the path of the file.
    Outputs: the SignalFile.
    """
    if time_array is None:
        time_array = np.arange(SAMPLE_COUNT_I) * 0.1
    time_array = np.asarray(time_array, dtype=float)
    return SignalFile(path_str, {
        "Time": time_array,
        "Speed": np.sin(time_array) + offset_f,
        "Torque": time_array * 2.0})


class SeveralFilesTestCase(unittest.TestCase):
    """Shared setup: the app's controllers and a folder."""

    def setUp(self) -> None:
        """Create the controllers with no data file open.

        Inputs: none.
        Outputs: none.
        """
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.start_app()

    def tearDown(self) -> None:
        """Remove the temporary folder.

        Inputs: none.
        Outputs: none.
        """
        self.temporary_folder.cleanup()

    def start_app(self) -> None:
        """Start the app again, with no data file open.

        Inputs: none.
        Outputs: none.
        """
        self.view = FakeAppWindow()
        self.main_controller = MainController(self.view)
        self.plot_controller = self.main_controller.plot_controller
        self.plot_controller.workspace.random_generator = random.Random(3)
        self.workspace = self.plot_controller.workspace
        self.file_controller = self.main_controller.file_controller
        self.controller = self.main_controller.synthetic_controller
        self.store = self.controller.store

    def open_file(self, signal_file: SignalFile, path_str: str) -> None:
        """Open a file as the next data file.

        Inputs:
            signal_file: the file the loader returns.
            path_str: the path the dialog returns.
        Outputs: none.
        """
        self.file_controller.load_function = lambda path: signal_file
        self.view.open_path_str = path_str
        self.file_controller.open_file_requested()
        # LLFR-01001: the files are collapsed after an open; these tests
        # read the shown signals.
        expand_all_files(self.main_controller)

    def create(self, name_str: str, operation_str: str) -> None:
        """Choose an operation in the menu of a signal.

        Inputs:
            name_str: the right-clicked signal.
            operation_str: the operation id.
        Outputs: none.
        """
        self.view.signal_menu_handler_dict["create"](name_str, operation_str)

    def path(self, name_str: str) -> str:
        """Return a path in the temporary folder.

        Inputs:
            name_str: the file name.
        Outputs: the path.
        """
        return os.path.join(self.temporary_folder.name, name_str)


class SyntheticNameTest(SeveralFilesTestCase):
    """The names start with the prefix of the file (HLFR-00054)."""

    def setUp(self) -> None:
        """Open two files with the same time signal.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.open_file(make_file(), "a.csv")
        self.open_file(make_file(offset_f=1.0), "b.csv")

    @covers("LLFR-00908", "LLFR-00240", "HLFR-00054", "HLFR-00115",
            "LLFR-00940")
    def test_names_start_with_the_prefix_of_the_file(self) -> None:
        """The Integral of file1_Speed is file1_int_Speed, and chains
        build up after the prefix.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.create("file2_Speed", "integral")
        self.create("file1_int_Speed", "derivative")
        self.view.parameter_answer_list = [[["2", "2"]]]
        self.create("file2_Speed", "lowpass")
        self.create("file2_lpf_2Hz_order2_Speed", "integral")
        self.assertEqual(self.store.names(), [
            "file1_int_Speed", "file2_int_Speed", "file1_der_int_Speed",
            "file2_lpf_2Hz_order2_Speed", "file2_int_lpf_2Hz_order2_Speed"])
        # LLFR-00940: each one belongs to the file of its source.
        self.assertEqual([self.store.get(name_str).file_number_i
                          for name_str in self.store.names()],
                         [1, 2, 1, 2, 2])

    @covers("LLFR-00241", "LLFR-00908", "HLFR-00054")
    def test_name_in_use_gets_a_number_after_the_prefix(self) -> None:
        """A second Integral of the same signal gets _2 at the end.

        Inputs: none.
        Outputs: none.
        """
        self.create("file2_Speed", "integral")
        self.create("file2_Speed", "integral")
        self.assertEqual(self.store.names(),
                         ["file2_int_Speed", "file2_int_Speed_2"])
        # LLFR-00945: the number stays in the plain name.
        self.assertEqual(self.store.get("file2_int_Speed_2").saved_name_str,
                         "int_Speed_2")

    @covers("LLFR-00958", "LLFR-00940", "HLFR-00104", "LLFR-00276",
            "LLFR-00240")
    def test_product_names_within_and_across_files(self) -> None:
        """The second signal of a product keeps its prefix, of the same
        file or of another, and the product belongs to the file of the
        right-clicked signal.

        Inputs: none.
        Outputs: none.
        """
        self.view.second_signal_answer_list = ["file1_Torque",
                                               "file2_Torque"]
        self.create("file1_Speed", "product")
        self.create("file1_Speed", "product")
        self.assertEqual(self.store.names(), [
            "file1_Speed_prod_file1_Torque", "file1_Speed_prod_file2_Torque"])
        across = self.store.get("file1_Speed_prod_file2_Torque")
        self.assertEqual(across.file_number_i, 1)
        data_files = self.controller.signal_file
        np.testing.assert_allclose(
            across.value_array,
            data_files.signal_array("file1_Speed")
            * data_files.signal_array("file2_Torque"))
        # LLFR-00945: both are saved as Speed_prod_Torque.
        self.assertEqual(across.saved_name_str, "Speed_prod_Torque")
        self.assertEqual(
            self.store.get("file1_Speed_prod_file1_Torque").saved_name_str,
            "Speed_prod_Torque")
        # LLFR-00958: a synthetic second signal of another file keeps
        # its own prefix too.
        self.create("file2_Speed", "integral")
        self.view.second_signal_answer_list = ["file2_int_Speed"]
        self.create("file1_Torque", "product")
        self.assertEqual(self.store.names()[-1],
                         "file1_Torque_prod_file2_int_Speed")
        self.assertEqual(self.store.get(
            "file1_Torque_prod_file2_int_Speed").saved_name_str,
            "Torque_prod_int_Speed")

    @covers("LLFR-00958", "LLFR-00240", "HLFR-00104", "LLFR-00945",
            "LLFR-00959", "LLFR-00279", "LLFR-00241")
    def test_product_of_one_file_keeps_the_second_prefix(self) -> None:
        """A synthetic second signal of the same file keeps its prefix;
        rename, Copy equation, Save signals and LLFR-00241 use the new
        name.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Torque", "integral")
        self.view.second_signal_answer_list = ["file1_int_Torque",
                                               "file1_int_Torque"]
        self.create("file1_Speed", "product")
        self.create("file1_Speed", "product")
        self.assertEqual(self.store.names(), [
            "file1_int_Torque", "file1_Speed_prod_file1_int_Torque",
            "file1_Speed_prod_file1_int_Torque_2"])
        product = self.store.get("file1_Speed_prod_file1_int_Torque")
        self.assertEqual(product.file_number_i, 1)
        # LLFR-00945: every prefix the app put into the name is removed.
        self.assertEqual(product.saved_name_str, "Speed_prod_int_Torque")
        self.assertEqual(self.store.get(
            "file1_Speed_prod_file1_int_Torque_2").saved_name_str,
            "Speed_prod_int_Torque_2")
        # LLFR-00279: the equation holds the new name.
        self.view.signal_menu_handler_dict["copy_equation"](
            "file1_Speed_prod_file1_int_Torque")
        equation_list = json.loads(self.view.clipboard_text_list[-1])
        self.assertEqual([entry["name"] for entry in equation_list], [
            "file1_int_Torque", "file1_Speed_prod_file1_int_Torque"])
        self.assertEqual(equation_list[1]["signals"],
                         ["file1_Speed", "file1_int_Torque"])
        # LLFR-00959: the rename field shows the part after the prefix
        # of its own file, the second prefix included.
        self.view.name_answer_list = ["Power"]
        self.view.signal_menu_handler_dict["rename"](
            "file1_Speed_prod_file1_int_Torque")
        self.assertEqual(self.view.name_question_list[-1],
                         "Speed_prod_file1_int_Torque")
        self.assertIn("file1_Power", self.store.names())
        # LLFR-00958: a product of the renamed signal uses its new name.
        self.view.second_signal_answer_list = ["file1_Power"]
        self.create("file1_Torque", "product")
        self.assertEqual(self.store.names()[-1],
                         "file1_Torque_prod_file1_Power")

    @covers("LLFR-00939", "LLFR-00242", "LLFR-00940", "LLFR-00938")
    def test_synthetic_signals_listed_after_their_own_file(self) -> None:
        """A synthetic signal of file 2 is listed after file 2's signals,
        one of file 1 after file 1's, whatever the creation order.

        Inputs: none.
        Outputs: none.
        """
        self.create("file2_Speed", "integral")
        self.create("file1_Torque", "max")
        self.create("file2_Torque", "abs")
        self.assertEqual(self.view.shown_name_list, [
            "file1_Time", "file1_Speed", "file1_Torque", "file1_max_Torque",
            "file2_Time", "file2_Speed", "file2_Torque", "file2_int_Speed",
            "file2_abs_Torque"])

    @covers("LLFR-00967", "LLFR-00275", "LLFR-00940", "HLFR-00113")
    def test_second_signal_dialog_is_one_list(self) -> None:
        """The dialog lists, in signal list order and with prefixed
        names, the signals of the files with the same time signal, and
        leaves out a file whose time signal differs and FFT signals.

        Inputs: none.
        Outputs: none.
        """
        self.open_file(make_file(np.arange(SAMPLE_COUNT_I) * 0.2), "c.csv")
        self.create("file2_Speed", "integral")
        self.create("file1_Speed", "integral")
        self.create("file3_Speed", "integral")
        self.create("file1_Speed", "fft")
        self.create("file2_Speed", "product")
        name_list = self.view.second_signal_question_list[-1][2]
        self.assertEqual(name_list, [
            "file1_Time", "file1_Speed", "file1_Torque", "file1_int_Speed",
            "file2_Time", "file2_Speed", "file2_Torque", "file2_int_Speed"])
        # LLFR-00275: file 3 has another time signal, so its product
        # dialog lists only its own signals.
        self.create("file3_Speed", "product")
        self.assertEqual(self.view.second_signal_question_list[-1][2], [
            "file3_Time", "file3_Speed", "file3_Torque", "file3_int_Speed"])

    @covers("LLFR-00959", "LLFR-00975", "LLFR-00976", "LLFR-00267",
            "LLFR-00606", "LLFR-00607", "HLFR-00115", "HLFR-00060")
    def test_rename_keeps_the_prefix(self) -> None:
        """The field shows the part after the prefix, the typed name
        gets the prefix, the empty check is on the typed part and the
        in-use check on the whole name.

        Inputs: none.
        Outputs: none.
        """
        self.create("file2_Speed", "integral")
        self.view.name_answer_list = ["  my  ", "", "Torque", "file1_Torque"]
        self.view.signal_menu_handler_dict["rename"]("file2_int_Speed")
        self.assertEqual(self.view.name_question_list, ["int_Speed"])
        self.assertEqual(self.store.names(), ["file2_my"])
        self.assertIn("file2_my", self.view.shown_name_list)
        self.assertEqual(self.store.get("file2_my").saved_name_str, "my")
        # LLFR-00975: an empty typed part keeps the name, silently.
        self.view.signal_menu_handler_dict["rename"]("file2_my")
        self.assertEqual(self.view.name_question_list[-1], "my")
        self.assertEqual(self.store.names(), ["file2_my"])
        self.assertEqual(self.view.information_list, [])
        # LLFR-00976: "Torque" gives file2_Torque, a data file signal.
        self.view.signal_menu_handler_dict["rename"]("file2_my")
        self.assertEqual(self.store.names(), ["file2_my"])
        self.assertEqual(len(self.view.information_list), 1)
        self.assertIn('"file2_Torque"', self.view.information_list[0][1])
        # LLFR-00959: a typed prefix is part of the typed text.
        self.view.signal_menu_handler_dict["rename"]("file2_my")
        self.assertEqual(self.store.names(), ["file2_file1_Torque"])
        self.assertEqual(
            self.store.get("file2_file1_Torque").saved_name_str,
            "file1_Torque")
        self.assertEqual(self.store.get(
            "file2_file1_Torque").file_number_i, 2)

    @covers("LLFR-00945", "LLFR-00959", "HLFR-00121", "HLFR-00115")
    def test_typed_prefix_of_another_file_is_saved_as_typed(self) -> None:
        """A file-1 signal renamed `file2_x` is saved as `file2_x`.

        The prefix of its own file is removed once; the typed text,
        which starts like another file's prefix, is kept.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.view.name_answer_list = ["file2_x"]
        self.view.signal_menu_handler_dict["rename"]("file1_int_Speed")
        self.assertIn("file1_file2_x", self.store.names())
        signal = self.store.get("file1_file2_x")
        self.assertEqual(signal.file_number_i, 1)
        self.assertEqual(signal.editable_name_str, "file2_x")
        self.assertEqual(signal.saved_name_str, "file2_x")
        # Without the typed text kept, the editable part is used whole.
        signal.plain_name_str = ""
        self.assertEqual(signal.saved_name_str, "file2_x")


class TimeToleranceProductTest(SeveralFilesTestCase):
    """Product with signal across files whose times match within the
    tolerance (LLFR-00977, LLFR-00978)."""

    def setUp(self) -> None:
        """Open signals.xlsx and signals.mat of tests/user_tests/good.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.open_file(load_signal_file(GOOD_EXCEL_PATH_STR), "a.xlsx")
        self.open_file(load_signal_file(GOOD_MAT_PATH_STR), "b.mat")

    @covers("LLFR-00275", "LLFR-00977", "HLFR-00113", "HLFR-00053")
    def test_dialog_lists_the_file_with_the_rounded_times(self) -> None:
        """The second signal dialog of file 1 lists the signals of file
        2, whose times differ only by rounding, and the product is
        created.

        Inputs: none.
        Outputs: none.
        """
        data_files = self.controller.signal_file
        self.assertFalse(np.array_equal(
            data_files.time_array_for_signal("file1_Ramp"),
            data_files.time_array_for_signal("file2_Ramp")))
        self.view.second_signal_answer_list = ["file2_Ramp"]
        self.create("file1_Ramp", "product")
        name_list = self.view.second_signal_question_list[-1][2]
        self.assertIn("file2_Ramp", name_list)
        self.assertIn("file1_Ramp", name_list)
        self.assertEqual(self.store.names(), ["file1_Ramp_prod_file2_Ramp"])
        np.testing.assert_allclose(
            self.store.get("file1_Ramp_prod_file2_Ramp").value_array,
            data_files.signal_array("file1_Ramp")
            * data_files.signal_array("file2_Ramp"))

    @covers("LLFR-00275", "LLFR-00977", "LLFR-00978", "HLFR-00113")
    def test_dialog_leaves_out_a_time_beyond_the_tolerance(self) -> None:
        """A third file whose time signal has a NaN where the others have
        a number, or one time 1e-6 s later, is not listed.

        Inputs: none.
        Outputs: none.
        """
        mat_file = load_signal_file(GOOD_MAT_PATH_STR)
        nan_array = np.array(mat_file.time_array, dtype=float)
        nan_array[10] = float("nan")
        later_array = np.array(mat_file.time_array, dtype=float)
        later_array[10] += 1e-6
        self.open_file(SignalFile("c.csv", {
            "Time": nan_array, "Speed": later_array}), "c.csv")
        self.open_file(SignalFile("d.csv", {
            "Time": later_array, "Speed": later_array}), "d.csv")
        self.view.second_signal_answer_list = [None, None]
        self.create("file1_Ramp", "product")
        self.create("file3_Speed", "product")
        listed_set = {prefix_number(name_str) for name_str
                      in self.view.second_signal_question_list[0][2]}
        self.assertEqual(listed_set, {1, 2})
        self.assertEqual(self.view.second_signal_question_list[1][2],
                         ["file3_Time", "file3_Speed"])
        self.assertEqual(self.store.names(), [])

    @covers("LLFR-00496", "LLFR-00977", "LLFR-00262", "HLFR-00056")
    def test_layout_product_across_the_rounded_times(self) -> None:
        """A product of a layout file across the two files is created,
        because their time signals are identical within the tolerance.

        Inputs: none.
        Outputs: none.
        """
        data_files = self.controller.signal_file

        def lookup(name_str: str):
            """Return the samples of a data file signal.

            Inputs:
                name_str: a prefixed signal name.
            Outputs: its samples.
            """
            return data_files.signal_array(name_str)

        signal = self.store.create(
            "product", ["file1_Ramp", "file2_Ramp"], None, lookup,
            data_files.time_array_for_signal,
            set(data_files.signal_name_list))
        self.assertEqual(signal.name_str, "file1_Ramp_prod_file2_Ramp")
        later_array = np.array(data_files.time_array_for_signal(
            "file2_Ramp"), dtype=float)
        later_array[10] += 1e-6
        self.open_file(SignalFile("c.csv", {
            "Time": later_array, "Speed": later_array}), "c.csv")
        with self.assertRaises(SyntheticSourceError):
            self.store.create(
                "product", ["file1_Ramp", "file3_Speed"], None, lookup,
                data_files.time_array_for_signal,
                set(data_files.signal_name_list))


class FftRangeTest(SeveralFilesTestCase):
    """The FFT range of a signal's own file (HLFR-00057)."""

    def setUp(self) -> None:
        """Open a file from 0 to 9.9 s and one from 20 to 29.9 s.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.open_file(make_file(), "a.csv")
        self.open_file(make_file(np.arange(SAMPLE_COUNT_I) * 0.1 + 20.0),
                       "b.csv")

    def show_range(self, start_s: float, end_s: float) -> None:
        """Plot file1_Torque and set the shared x-axis range.

        Inputs:
            start_s: the start of the range, in seconds.
            end_s: its end.
        Outputs: none.
        """
        if not self.plot_controller.time_plot_list():
            self.view.handler_dict["double_click"]("file1_Torque")
        plot_id_i = self.plot_controller.all_plot_list()[0].plot_id_i
        self.view.handler_dict["time_range_handler"](plot_id_i, start_s,
                                                     end_s)

    @covers("LLFR-00592", "LLFR-00979", "HLFR-00057", "HLFR-00113")
    def test_no_time_plot_creates_no_fft(self) -> None:
        """With no time plot, no FFT is created for any file, and each
        try shows the box that asks for a time plot.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "fft")
        self.create("file2_Speed", "fft")
        self.assertEqual(self.store.names(), [])
        self.assertEqual(self.view.information_list, [
            (CREATE_TITLE_STR, FFT_NEEDS_TIME_PLOT_STR),
            (CREATE_TITLE_STR, FFT_NEEDS_TIME_PLOT_STR)])

    @covers("LLFR-00968", "LLFR-00248", "LLFR-00240", "HLFR-00057",
            "HLFR-00113")
    def test_whole_shown_range_gives_each_file_its_range(self) -> None:
        """A time plot that shows both files gives each FFT the whole
        time range of its own file.

        Inputs: none.
        Outputs: none.
        """
        self.show_range(0.0, 29.9)
        self.create("file1_Speed", "fft")
        self.create("file2_Speed", "fft")
        self.assertEqual(self.store.names(), [
            "file1_fft_0s_to_9p9s_Speed", "file2_fft_20s_to_29p9s_Speed"])
        self.assertEqual(self.store.get(
            "file2_fft_20s_to_29p9s_Speed").parameter, (20.0, 29.9))

    @covers("LLFR-00968", "LLFR-00248", "LLFR-00240", "HLFR-00057",
            "HLFR-00113")
    def test_shown_range_is_cut_to_the_file(self) -> None:
        """A shown range of 5 s to 25 s gives 5 s to 9.9 s for file 1 and
        20 s to 25 s for file 2.

        Inputs: none.
        Outputs: none.
        """
        self.show_range(5.0, 25.0)
        self.create("file1_Speed", "fft")
        self.create("file2_Speed", "fft")
        self.assertEqual(self.store.names(), [
            "file1_fft_5s_to_9p9s_Speed", "file2_fft_20s_to_25s_Speed"])
        frequency_array = self.store.get(
            "file2_fft_20s_to_25s_Speed").frequency_array
        # LLFR-00248: 51 samples from 20 s to 25 s, at 10 Hz.
        self.assertEqual(frequency_array.size, 51 // 2 + 1)
        self.assertEqual(self.view.information_list, [])

    @covers("LLFR-00969", "LLFR-00250", "HLFR-00057", "HLFR-00113")
    def test_range_outside_the_file_shows_one_box(self) -> None:
        """A shown range with no sample of file 2, or fewer than 8,
        creates no FFT and shows one box that asks to move the x-axis.

        Inputs: none.
        Outputs: none.
        """
        self.show_range(2.0, 8.0)
        self.create("file2_Speed", "fft")
        self.assertEqual(self.store.names(), [])
        self.assertEqual(len(self.view.information_list), 1)
        message_str = self.view.information_list[0][1]
        self.assertIn("does not hold enough samples of 'file2_Speed'",
                      message_str)
        self.assertIn("Move the x-axis", message_str)
        # LLFR-00969: 7 samples of file 2 (20 s to 20.6 s) are too few.
        self.show_range(9.0, 20.6)
        self.create("file2_Speed", "fft")
        self.assertEqual(self.store.names(), [])
        self.assertEqual(len(self.view.information_list), 2)
        self.assertIn("holds 7 of them", self.view.information_list[1][1])
        # 8 samples are enough.
        self.show_range(9.0, 20.7)
        self.create("file2_Speed", "fft")
        self.assertEqual(self.store.names(), ["file2_fft_20s_to_20p7s_Speed"])

    @covers("LLFR-00592", "LLFR-00979", "LLFR-00594")
    def test_short_file_without_time_plot(self) -> None:
        """With no time plot, a file of 7 samples shows the box that asks
        for a time plot, not the box of too few samples.

        Inputs: none.
        Outputs: none.
        """
        self.open_file(make_file(np.arange(7) * 0.1), "c.csv")
        self.create("file3_Speed", "fft")
        self.assertEqual(self.store.names(), [])
        self.assertEqual(self.view.information_list,
                         [(CREATE_TITLE_STR, FFT_NEEDS_TIME_PLOT_STR)])

    @covers("LLFR-00594", "LLFR-00250", "LLFR-00248")
    def test_short_file_with_a_time_plot(self) -> None:
        """With a time plot, a file of 7 samples shows the box of too few
        samples in the time range.

        Inputs: none.
        Outputs: none.
        """
        self.open_file(make_file(np.arange(7) * 0.1), "c.csv")
        self.view.handler_dict["double_click"]("file3_Speed")
        self.create("file3_Speed", "fft")
        self.assertEqual(self.store.names(), [])
        self.assertEqual(len(self.view.information_list), 1)
        self.assertIn("holds 7 of them", self.view.information_list[0][1])


class SaveSeveralFilesTest(unittest.TestCase):
    """Save signals with several data files (HLFR-00120, HLFR-00121)."""

    def setUp(self) -> None:
        """Create the Save signals flow with no data file.

        Inputs: none.
        Outputs: none.
        """
        self.folder = tempfile.TemporaryDirectory()
        self.folder_str = self.folder.name
        self.view = FakeSaveSignalsView()
        self.file_controller = FakeFileController()
        self.synthetic_controller = FakeSyntheticController()
        self.data_files = DataFileSet()
        self.synthetic_controller.signal_file = self.data_files
        self.controller = SaveSignalsController(
            self.view, self.file_controller, self.synthetic_controller)

    def tearDown(self) -> None:
        """Remove the temporary folder.

        Inputs: none.
        Outputs: none.
        """
        self.folder.cleanup()

    def add_file(self, name_str: str, signal_dict: dict,
                 time_name_str: str = "") -> None:
        """Open a data file of the folder.

        Inputs:
            name_str: its file name.
            signal_dict: its signals, Time included.
            time_name_str: the time signal chosen in the window, or ""
                when the file has a signal named Time.
        Outputs: none.
        """
        path_str = os.path.join(self.folder_str, name_str)
        signal_file = SignalFile(path_str, dict(signal_dict))
        if time_name_str:
            signal_file.choose_time_signal(time_name_str)
        self.data_files.add(signal_file)
        self.file_controller.open(self.data_files)

    def create(self, operation_str: str, source_name_list: list,
               parameter=None) -> str:
        """Create a synthetic signal in the store.

        Inputs:
            operation_str: the operation id.
            source_name_list: its sources.
            parameter: its parameter.
        Outputs: the name of the new signal.
        """
        store = self.synthetic_controller.store

        def lookup(name_str: str):
            """Return the samples of a signal.

            Inputs:
                name_str: a signal name.
            Outputs: its samples.
            """
            if store.contains(name_str):
                return store.get(name_str).value_array
            return self.data_files.signal_array(name_str)

        return store.create(
            operation_str, source_name_list, parameter, lookup,
            self.data_files.time_array_for_signal,
            set(self.data_files.signal_name_list)).name_str

    def save(self, name_str: str = "out.csv") -> dict:
        """Click Save signals and save a CSV file.

        Inputs:
            name_str: the file name.
        Outputs: the signals of the saved file, read back.
        """
        path_str = os.path.join(self.folder_str, name_str)
        self.view.dialog_answer_list.append((path_str, CSV_FORMAT_STR,
                                             False))
        self.view.handler()
        return dict(load_signal_file(path_str).signal_dict)

    @covers("LLFR-00942", "LLFR-00943", "HLFR-00120", "LLFR-00396",
            "LLFR-00977")
    def test_different_time_signals_show_an_error_first(self) -> None:
        """Different time signals show an error box in place of the
        dialog, and nothing is written.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.arange(5) * 0.5
        self.add_file("a.csv", {"Time": time_array, "Speed": time_array})
        # Same number of samples, one value different by more than the
        # tolerance of LLFR-00977 (1e-8 times 1.5 s).
        other_array = time_array.copy()
        other_array[3] += 1e-6
        self.add_file("b.csv", {"Time": other_array, "Speed": time_array})
        self.view.dialog_answer_list.append(
            (os.path.join(self.folder_str, "out.csv"), CSV_FORMAT_STR,
             False))
        self.view.handler()
        self.assertEqual(self.view.dialog_call_list, [])
        self.assertEqual(len(self.view.error_list), 1)
        self.assertIn("need the same time signals", self.view.error_list[0])
        self.assertEqual(self.view.written_path_list, [])
        self.assertEqual(sorted(os.listdir(self.folder_str)), [])
        self.assertEqual(self.view.finished_count_i, 1)

    @covers("LLFR-00942", "LLFR-00944", "LLFR-00977", "HLFR-00120")
    def test_excel_and_mat_files_are_saved_together(self) -> None:
        """signals.xlsx and signals.mat, whose times differ only by
        rounding, are saved to one file with the time of file 1.

        Inputs: none.
        Outputs: none.
        """
        for name_str, path_str in (("a.xlsx", GOOD_EXCEL_PATH_STR),
                                   ("b.mat", GOOD_MAT_PATH_STR)):
            signal_file = load_signal_file(path_str)
            self.add_file(name_str, signal_file.signal_dict)
        saved_dict = self.save()
        self.assertEqual(self.view.error_list, [])
        self.assertEqual(list(saved_dict).count("Time"), 1)
        self.assertIn("Ramp_1", saved_dict)
        self.assertIn("Ramp_2", saved_dict)
        np.testing.assert_allclose(
            saved_dict["Time"],
            self.data_files.file_list[0].time_array, rtol=1e-12)

    @covers("LLFR-00942", "LLFR-00978", "HLFR-00120")
    def test_nan_times_at_the_same_place_save_together(self) -> None:
        """A NaN time at the same place in both files does not stop the
        save; a NaN against a number does.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.arange(5) * 0.5
        time_array[2] = float("nan")
        self.add_file("a.csv", {"Time": time_array, "Speed": time_array})
        self.add_file("b.csv", {"Time": time_array.copy(),
                                "Speed": time_array})
        self.assertTrue(self.data_files.same_time_signals_b())
        number_array = np.arange(5) * 0.5
        self.add_file("c.csv", {"Time": number_array,
                                "Speed": number_array})
        self.view.handler()
        self.assertEqual(self.view.dialog_call_list, [])
        self.assertEqual(len(self.view.error_list), 1)

    @covers("LLFR-00942", "HLFR-00120")
    def test_different_sample_counts_show_an_error(self) -> None:
        """A time signal with another number of samples is different.

        Inputs: none.
        Outputs: none.
        """
        self.add_file("a.csv", {"Time": np.arange(5.0),
                                "Speed": np.arange(5.0)})
        self.add_file("b.csv", {"Time": np.arange(6.0),
                                "Speed": np.arange(6.0)})
        self.view.handler()
        self.assertEqual(self.view.dialog_call_list, [])
        self.assertEqual(len(self.view.error_list), 1)

    @covers("LLFR-00944", "LLFR-00945", "LLFR-00946", "LLFR-00401",
            "LLFR-00404", "LLFR-00947", "HLFR-00121", "HLFR-00120",
            "LLFR-00532")
    def test_same_time_signals_save_one_file(self) -> None:
        """One Time, every signal and the synthetic signals under plain
        names, with the file number on the shared ones.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.arange(5) * 0.5
        self.add_file("run1.csv", {"Time": time_array, "Speed": time_array,
                                   "Accel": time_array * 3.0})
        self.add_file("run2.csv", {"time": time_array,
                                   "Speed": time_array * 2.0})
        self.create("integral", ["file1_Speed"])
        self.create("integral", ["file2_Speed"])
        self.create("product", ["file1_Speed", "file2_Speed"])
        saved_dict = self.save()
        self.assertEqual(list(saved_dict), [
            "Time", "Speed_1", "Accel", "int_Speed_1",
            "Speed_prod_Speed", "Speed_2", "int_Speed_2"])
        np.testing.assert_allclose(saved_dict["Time"], time_array)
        np.testing.assert_allclose(saved_dict["Speed_2"], time_array * 2.0)
        np.testing.assert_allclose(saved_dict["Speed_prod_Speed"],
                                   time_array * time_array * 2.0)
        # LLFR-00532: the dialog starts from the lowest-numbered file.
        self.assertEqual(self.view.dialog_call_list[0][:2],
                         (self.folder_str, "run1_signals.csv"))
        # LLFR-00404: the removal of the prefix alone is not listed.
        self.assertEqual(self.view.changed_names_list, [
            "file1_Speed → Speed_1\n"
            "file1_int_Speed → int_Speed_1\n"
            "file2_Speed → Speed_2\n"
            "file2_int_Speed → int_Speed_2"])

    @covers("LLFR-00965", "LLFR-00946", "LLFR-00241", "HLFR-00121")
    def test_name_still_shared_after_the_number(self) -> None:
        """With file1_Speed, file1_Speed_2 and file2_Speed, the later
        Speed_2 becomes Speed_2_2.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.arange(5) * 0.5
        self.add_file("a.csv", {"Time": time_array, "Speed": time_array,
                                "Speed_2": time_array + 1.0})
        self.add_file("b.csv", {"Time": time_array,
                                "Speed": time_array + 2.0})
        saved_dict = self.save()
        self.assertEqual(list(saved_dict),
                         ["Time", "Speed_1", "Speed_2", "Speed_2_2"])
        np.testing.assert_allclose(saved_dict["Speed_2"], time_array + 1.0)
        np.testing.assert_allclose(saved_dict["Speed_2_2"],
                                   time_array + 2.0)
        self.assertIn("file2_Speed → Speed_2_2",
                      self.view.changed_names_list[0])

    @covers("LLFR-00945", "LLFR-00959", "LLFR-00558", "LLFR-00944",
            "HLFR-00121")
    def test_renamed_signal_keeps_the_typed_name(self) -> None:
        """A renamed synthetic signal is saved under the typed text, and
        a time signal not named Time is listed.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.arange(5) * 0.5
        self.add_file("a.csv", {"t": time_array, "Speed": time_array}, "t")
        name_str = self.create("integral", ["file1_Speed"])
        self.synthetic_controller.store.rename(name_str, "file2_x", set(
            self.data_files.signal_name_list))
        saved_dict = self.save()
        self.assertEqual(list(saved_dict), ["Time", "Speed", "file2_x"])
        self.assertEqual(self.view.changed_names_list,
                         ["file1_t → Time"])

    @covers("LLFR-00942", "LLFR-00532", "LLFR-00944")
    def test_lowest_open_file_after_a_close(self) -> None:
        """After file 1 is closed, file 2 gives the dialog values and the
        time signal.

        Inputs: none.
        Outputs: none.
        """
        self.add_file("a.csv", {"Time": np.arange(3.0),
                                "Speed": np.arange(3.0)})
        self.add_file("b.mat", {"Time": np.arange(4.0),
                                "Torque": np.arange(4.0)})
        self.add_file("c.csv", {"Time": np.arange(4.0),
                                "Torque": np.arange(4.0) * 2.0})
        self.data_files.remove(1)
        saved_dict = self.save()
        self.assertEqual(self.view.dialog_call_list[0][1:],
                         ("b_signals.mat", "mat"))
        self.assertEqual(list(saved_dict), ["Time", "Torque_2", "Torque_3"])


class LayoutSeveralFilesTest(SeveralFilesTestCase):
    """Layout files with prefixed names (HLFR-00049 to HLFR-00051)."""

    def setUp(self) -> None:
        """Open two files with the same time signal.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.open_file(make_file(), "a.csv")
        self.open_file(make_file(offset_f=1.0), "b.csv")

    def save(self, name_str: str) -> str:
        """Click Save layout and save to a file of the folder.

        Inputs:
            name_str: the file name.
        Outputs: the path.
        """
        path_str = self.path(name_str)
        self.view.save_answer_list.append(path_str)
        self.view.layout_handler_tuple[0]()
        return path_str

    def load(self, path_str: str) -> None:
        """Click Load layout and choose a file.

        Inputs:
            path_str: the layout file.
        Outputs: none.
        """
        self.view.load_answer_list.append(path_str)
        self.view.layout_handler_tuple[1]()

    def write_layout(self, name_str: str, layout_dict: dict) -> str:
        """Write a layout dict to a file of the folder.

        Inputs:
            name_str: the file name.
            layout_dict: the content.
        Outputs: the path.
        """
        path_str = self.path(name_str)
        with open(path_str, "w", encoding="utf-8") as output_file:
            json.dump(layout_dict, output_file, indent=2)
        return path_str

    def curve_names(self) -> list:
        """Return the curve names of every plot, tab by tab.

        Inputs: none.
        Outputs: a list of curve name lists, plot by plot.
        """
        return [[curve.signal_name_str for curve in plot.curve_list]
                for tab in self.workspace.tab_list
                for plot in tab.plot_list]

    @covers("LLFR-00948", "LLFR-00471", "LLFR-00228", "HLFR-00049",
            "HLFR-00051", "LLFR-00949", "HLFR-00050")
    def test_saved_names_carry_the_prefix(self) -> None:
        """The layout file holds version 3 and prefixed names, and loads
        them back on the files of the same numbers.

        Inputs: none.
        Outputs: none.
        """
        self.create("file2_Speed", "integral")
        self.view.second_signal_answer_list = ["file2_Torque"]
        self.create("file1_Speed", "product")
        self.view.handler_dict["double_click"]("file2_int_Speed")
        plot_id_i = self.plot_controller.all_plot_list()[0].plot_id_i
        self.view.handler_dict["signal_drop_handler"](
            plot_id_i, "file1_Speed_prod_file2_Torque")
        self.view.handler_dict["signal_drop_handler"](plot_id_i,
                                                      "file1_Torque")
        path_str = self.save("layout.json")
        layout_dict = read_layout_file(path_str)
        self.assertEqual(layout_dict["version"], 3)
        self.assertEqual(LAYOUT_VERSION_I, 3)
        self.assertEqual(
            [curve_dict["signal"] for curve_dict
             in layout_dict["tabs"][0]["plots"][0]["curves"]],
            ["file2_int_Speed", "file1_Speed_prod_file2_Torque",
             "file1_Torque"])
        self.assertEqual(layout_dict[LAYOUT_KEY_STR][1]["signals"],
                         ["file1_Speed", "file2_Torque"])
        # Start again with the same two files: everything is rebuilt.
        self.start_app()
        self.open_file(make_file(), "a.csv")
        self.open_file(make_file(offset_f=1.0), "b.csv")
        self.load(path_str)
        self.assertEqual(self.view.report_list, [])
        self.assertEqual(self.store.names(), [
            "file2_int_Speed", "file1_Speed_prod_file2_Torque"])
        self.assertEqual(self.curve_names(), [[
            "file2_int_Speed", "file1_Speed_prod_file2_Torque",
            "file1_Torque"]])

    @covers("LLFR-00262", "LLFR-00958", "LLFR-00945", "LLFR-00237",
            "LLFR-00282", "HLFR-00104", "HLFR-00050")
    def test_older_product_name_still_loads(self) -> None:
        """A layout file saved before LLFR-00958 kept the second prefix
        loads its product under the saved name, with no report.

        Inputs: none.
        Outputs: none.
        """
        self.view.second_signal_answer_list = ["file1_Torque"]
        self.create("file1_Speed", "product")
        self.view.handler_dict["double_click"](
            "file1_Speed_prod_file1_Torque")
        layout_dict = read_layout_file(self.save("layout.json"))
        # The older form: no prefix on a second signal of the same file.
        layout_dict[LAYOUT_KEY_STR][0]["name"] = "file1_Speed_prod_Torque"
        layout_dict["tabs"][0]["plots"][0]["curves"][0]["signal"] = (
            "file1_Speed_prod_Torque")
        old_path_str = self.write_layout("old.json", layout_dict)
        self.start_app()
        self.open_file(make_file(), "a.csv")
        self.open_file(make_file(offset_f=1.0), "b.csv")
        self.load(old_path_str)
        self.assertEqual(self.view.report_list, [])
        self.assertEqual(self.store.names(), ["file1_Speed_prod_Torque"])
        self.assertEqual(self.curve_names(), [["file1_Speed_prod_Torque"]])
        old_product = self.store.get("file1_Speed_prod_Torque")
        data_files = self.controller.signal_file
        np.testing.assert_allclose(
            old_product.value_array,
            data_files.signal_array("file1_Speed")
            * data_files.signal_array("file1_Torque"))
        # LLFR-00945: it is saved as Speed_prod_Torque, as before.
        self.assertEqual(old_product.saved_name_str, "Speed_prod_Torque")
        # LLFR-00282: loading it again adds nothing.
        self.load(old_path_str)
        self.assertEqual(self.store.names(), ["file1_Speed_prod_Torque"])
        # LLFR-00958: a product created now gets the new name.
        self.view.second_signal_answer_list = ["file1_Torque"]
        self.create("file1_Speed", "product")
        self.assertEqual(self.store.names(), [
            "file1_Speed_prod_Torque", "file1_Speed_prod_file1_Torque"])

    @covers("LLFR-00949", "LLFR-00231", "LLFR-00237", "HLFR-00050",
            "HLFR-00052")
    def test_curve_of_a_file_not_open_is_missing(self) -> None:
        """A curve of file 3 when no file 3 is open is a missing signal.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_layout("three.json", {
            "format": LAYOUT_FORMAT_STR, "version": 3,
            "tabs": [{"name": "A", "plots": [{"curves": [
                {"signal": "file3_Speed", "color": "#1f77b4", "width": 1},
                {"signal": "file2_Speed", "color": "#000000",
                 "width": 1}]}]}]})
        self.load(path_str)
        self.assertEqual(self.curve_names(), [["file2_Speed"]])
        self.assertIn("file3_Speed", self.view.report_list[0])

    @covers("LLFR-00963", "LLFR-00964", "LLFR-00472", "HLFR-00050",
            "HLFR-00115")
    def test_older_layout_names_mean_file_1(self) -> None:
        """A version 2 file with names without prefix loads them as
        names of file 1, its synthetic signals included, and the report
        names only a signal still missing, with its prefix.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_layout("old.json", {
            "format": LAYOUT_FORMAT_STR, "version": 2,
            "synthetic_signals": [
                {"name": "int_Speed", "operation": "integral",
                 "signals": ["Speed"], "parameter": None},
                {"name": "der_int_Speed", "operation": "derivative",
                 "signals": ["int_Speed"], "parameter": None}],
            "tabs": [{"name": "A", "plots": [{
                "curves": [
                    {"signal": "der_int_Speed", "color": "#1f77b4",
                     "width": 1},
                    {"signal": "Torque", "color": "#000000", "width": 1},
                    {"signal": "Power", "color": "#aa0000", "width": 1}],
                "data_tips": [{"signal": "Torque", "time": 1.0,
                               "label_position": None}],
                "delta_markers": [{
                    "name": "Delta X 1", "kind": "delta_x",
                    "first_point": {"signal": "Torque", "time": 1.0},
                    "second_point": {"signal": "der_int_Speed",
                                     "time": 2.0},
                    "color": "#ff8000"}]}]}]})
        self.load(path_str)
        self.assertEqual(self.store.names(),
                         ["file1_int_Speed", "file1_der_int_Speed"])
        self.assertEqual(self.store.get("file1_int_Speed").source_name_list,
                         ["file1_Speed"])
        self.assertEqual(self.curve_names(),
                         [["file1_der_int_Speed", "file1_Torque"]])
        plot = self.workspace.tab_list[-1].plot_list[0]
        self.assertEqual(len(plot.pinned_tip_list), 1)
        self.assertEqual(len(plot.delta_marker_list), 1)
        # LLFR-00964: only the signal still missing, with its prefix.
        self.assertEqual(len(self.view.report_list), 1)
        report_str = self.view.report_list[0]
        self.assertIn("file1_Power", report_str)
        self.assertNotIn("Renamed", report_str)
        self.assertNotIn("file1_Torque", report_str)

    @covers("LLFR-00970", "LLFR-00501", "LLFR-00500", "LLFR-00237",
            "LLFR-00499", "HLFR-00050", "HLFR-00052", "HLFR-00115")
    def test_wrong_prefix_is_corrected(self) -> None:
        """`my_int` of file 2 becomes `file2_my_int`, `file1_x` of file 2
        becomes `file2_x`, the curves follow, and the renames are listed.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_layout("prefix.json", {
            "format": LAYOUT_FORMAT_STR, "version": 3,
            "synthetic_signals": [
                {"name": "my_int", "operation": "integral",
                 "signals": ["file2_Speed"], "parameter": None},
                {"name": "file1_x", "operation": "abs",
                 "signals": ["my_int"], "parameter": None},
                {"name": "file1_ok", "operation": "abs",
                 "signals": ["file1_Speed"], "parameter": None}],
            "tabs": [{"name": "A", "plots": [{"curves": [
                {"signal": "my_int", "color": "#1f77b4", "width": 1},
                {"signal": "file1_x", "color": "#000000", "width": 1},
                {"signal": "file1_ok", "color": "#aa0000",
                 "width": 1}]}]}]})
        self.load(path_str)
        self.assertEqual(self.store.names(),
                         ["file2_my_int", "file2_x", "file1_ok"])
        self.assertEqual(self.store.get("file2_x").source_name_list,
                         ["file2_my_int"])
        self.assertEqual(self.curve_names(),
                         [["file2_my_int", "file2_x", "file1_ok"]])
        report_str = self.view.report_list[0]
        self.assertIn("Renamed:", report_str)
        self.assertIn('"my_int" → "file2_my_int"', report_str)
        self.assertIn('"file1_x" → "file2_x"', report_str)
        self.assertNotIn('"file1_ok" →', report_str)
        # LLFR-00499: a corrected name already in use gets a number.
        self.load(self.write_layout("again.json", {
            "format": LAYOUT_FORMAT_STR, "version": 3,
            "synthetic_signals": [
                {"name": "my_int", "operation": "abs",
                 "signals": ["file2_Torque"], "parameter": None}],
            "tabs": [{"name": "B", "plots": [{"curves": [
                {"signal": "my_int", "color": "#1f77b4",
                 "width": 1}]}]}]}))
        self.assertEqual(self.store.names()[-1], "file2_my_int_2")
        self.assertIn('"my_int" → "file2_my_int_2"',
                      self.view.report_list[-1])

    @covers("LLFR-00939", "LLFR-00242")
    def test_model_order_of_the_signal_list(self) -> None:
        """The order helper puts each synthetic signal after its file.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(ordered_signal_names(
            self.controller.signal_file, ["s2", "s1", "s0"],
            {"s2": 2, "s1": 1}), [
            "file1_Time", "file1_Speed", "file1_Torque", "s1",
            "file2_Time", "file2_Speed", "file2_Torque", "s2", "s0"])
        self.assertEqual(operations.MINIMUM_FFT_SAMPLES_I, 8)


if __name__ == "__main__":
    unittest.main()
