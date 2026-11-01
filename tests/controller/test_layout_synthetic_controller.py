"""Tests for synthetic signals in the layout flows (issue #110).

The whole app's controllers (MainController) run with a fake view that
offers the layout, plot and synthetic signal facades. Saving writes the
synthetic signals (LLFR-00225 item 10); loading removes the current
ones and creates those of the file before the plots are rebuilt
(LLFR-00262), lists them in the signal list (LLFR-00242) and reports
what could not be created (LLFR-00237). No Qt is needed.
"""

import json
import os
import random
import tempfile
import unittest
from unittest import mock

import numpy as np

from tests.support import covers
from tests.controller.test_layout_controller import FakeLayoutView
from tests.controller.test_synthetic_controller import (
    FakeSyntheticWindow, make_signal_file)

from controller.main_controller import MainController
from model.layout_file import (
    REMOVED_HEADING_STR, SYNTHETIC_HEADING_STR, read_layout_file)
from model.synthetic_signals import LAYOUT_KEY_STR


class FakeAppWindow(FakeLayoutView, FakeSyntheticWindow):
    """The fake view of the whole app: layout and synthetic facades."""


class LayoutSyntheticTestCase(unittest.TestCase):
    """Shared setup: the app's controllers, a folder and a data file."""

    def setUp(self) -> None:
        """Create the controllers and open the test file.

        Inputs: none.
        Outputs: none.
        """
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.view = FakeAppWindow()
        self.main_controller = MainController(self.view)
        self.plot_controller = self.main_controller.plot_controller
        self.plot_controller.workspace.random_generator = random.Random(3)
        self.workspace = self.plot_controller.workspace
        self.synthetic_controller = (
            self.main_controller.synthetic_controller)
        self.store = self.synthetic_controller.store
        self.open_file()

    def tearDown(self) -> None:
        """Remove the temporary folder.

        Inputs: none.
        Outputs: none.
        """
        self.temporary_folder.cleanup()

    def open_file(self) -> None:
        """Open (or reopen) the test data file (10 Hz, 0 to 9.9 s).

        Inputs: none.
        Outputs: none.
        """
        file_controller = self.main_controller.file_controller
        file_controller.load_function = (
            lambda path_str: make_signal_file())
        self.view.open_path_str = "test.csv"
        file_controller.open_file_requested()

    def path(self, name_str: str) -> str:
        """Return a path in the temporary folder.

        Inputs:
            name_str: the file name.
        Outputs: the path.
        """
        return os.path.join(self.temporary_folder.name, name_str)

    def create(self, operation_str: str, source_name_list: list,
               parameter=None) -> str:
        """Create a synthetic signal and show it in the signal list.

        Inputs:
            operation_str: the operation id.
            source_name_list: the sources.
            parameter: the parameter.
        Outputs: the name of the new signal.
        """
        signal = self.store.create(
            operation_str, source_name_list, parameter,
            self.synthetic_controller.signal_lookup,
            self.synthetic_controller.signal_file.time_array,
            self.synthetic_controller.data_name_set())
        self.synthetic_controller.show_synthetic_signals()
        return signal.name_str

    def build_synthetic_layout(self) -> list:
        """Create chained synthetic signals and plot some of them.

        Plot 1: lowpass (with a data tip) and Speed; plot 2: the
        moving average of the high-pass and the product (with a Delta
        X marker on the product).

        Inputs: none.
        Outputs: the names of the synthetic signals, in creation order.
        """
        name_list = [
            self.create("lowpass", ["Speed"], (1.0, 2, "first_value"))]
        name_list.append(self.create("highpass", [name_list[0]],
                                     (2.0, 3, "zero")))
        name_list.append(self.create("movingaverage", [name_list[1]], 4))
        name_list.append(self.create("greaterorequal", ["Torque"], 3.0))
        name_list.append(self.create("product",
                                     [name_list[0], "Torque"]))
        name_list.append(self.create("fft", ["Speed"], (1.0, 8.0)))
        handler_dict = self.view.handler_dict
        handler_dict["double_click"](name_list[0])
        first_plot = self.workspace.tab_list[0].plot_list[0]
        handler_dict["signal_drop_handler"](first_plot.plot_id_i, "Speed")
        lowpass_array = self.store.get(name_list[0]).value_array
        handler_dict["tip_pin_handler"](first_plot.plot_id_i,
                                        name_list[0], 2.0,
                                        float(lowpass_array[20]))
        handler_dict["double_click"](name_list[2])
        second_plot = self.workspace.tab_list[0].plot_list[1]
        handler_dict["signal_drop_handler"](second_plot.plot_id_i,
                                            name_list[4])
        product_array = self.store.get(name_list[4]).value_array
        handler_dict["plot_tool"]("delta_x")
        handler_dict["delta_point_pick_handler"](
            second_plot.plot_id_i, name_list[4], 1.0,
            float(product_array[10]))
        handler_dict["delta_point_pick_handler"](
            second_plot.plot_id_i, name_list[4], 5.0,
            float(product_array[50]))
        handler_dict["plot_tool"]("")
        return name_list

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

    def read_text(self, path_str: str) -> str:
        """Return the text of a file.

        Inputs:
            path_str: the file.
        Outputs: its UTF-8 text.
        """
        with open(path_str, encoding="utf-8") as input_file:
            return input_file.read()

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
        Outputs: a list (tab name, list of curve name lists).
        """
        return [(tab.name_str,
                 [[curve.signal_name_str for curve in plot.curve_list]
                  for plot in tab.plot_list])
                for tab in self.workspace.tab_list]


class SaveTest(LayoutSyntheticTestCase):
    """Save layout writes the synthetic signals (LLFR-00225)."""

    @covers("LLFR-00225", "LLFR-00227")
    def test_saved_file_holds_the_synthetic_signals(self) -> None:
        """Every synthetic signal is saved, in creation order."""
        name_list = self.build_synthetic_layout()
        layout_dict = read_layout_file(self.save("layout.json"))
        entry_list = layout_dict[LAYOUT_KEY_STR]
        self.assertEqual([entry["name"] for entry in entry_list],
                         name_list)
        self.assertEqual(entry_list, self.store.layout_entries())
        self.assertEqual(entry_list[1]["parameter"],
                         {"cutoff": 2.0, "order": 3, "start": "zero"})
        self.assertEqual(entry_list[5]["parameter"],
                         {"start": 1.0, "end": 8.0})


class LoadTest(LayoutSyntheticTestCase):
    """Load layout creates the synthetic signals (LLFR-00262)."""

    @covers("LLFR-00262", "LLFR-00230", "LLFR-00242", "LLFR-00225")
    def test_round_trip_after_reopening_the_file(self) -> None:
        """The signals, curves, tips and deltas are rebuilt."""
        name_list = self.build_synthetic_layout()
        old_value_dict = {name_str: self.store.get(name_str).value_array
                          for name_str in name_list}
        old_curve_list = self.curve_names()
        path_str = self.save("layout.json")
        saved_text_str = self.read_text(path_str)
        # LLFR-00252: reopening the file removes the synthetic signals.
        self.open_file()
        self.assertEqual(self.store.names(), [])
        self.load(path_str)
        self.assertEqual(self.view.load_error_list, [])
        self.assertEqual(self.view.report_list, [])
        self.assertEqual(self.store.names(), name_list)
        for name_str in name_list:
            np.testing.assert_array_equal(
                self.store.get(name_str).value_array,
                old_value_dict[name_str])
        self.assertEqual(self.curve_names(), old_curve_list)
        plot_list = self.workspace.tab_list[0].plot_list
        self.assertEqual(len(plot_list[0].pinned_tip_list), 1)
        self.assertEqual(len(plot_list[1].delta_marker_list), 1)
        # LLFR-00242: listed after the data signals, in italics, the
        # FFT signal told apart.
        self.assertEqual(self.view.shown_name_list[-len(name_list):],
                         name_list)
        self.assertEqual(self.view.synthetic_name_set, set(name_list))
        self.assertEqual(self.view.fft_name_set, {name_list[5]})
        # Saving again writes the same file.
        self.assertEqual(
            self.read_text(self.save("again.json")),
            saved_text_str)

    @covers("LLFR-00262", "LLFR-00279")
    def test_copied_equation_pasted_in_a_layout(self) -> None:
        """A copied equation pasted in a layout file is created."""
        name_list = self.build_synthetic_layout()
        self.view.signal_menu_handler_dict["copy_equation"](name_list[2])
        equation_list = json.loads(self.view.clipboard_text_list[-1])
        path_str = self.save("layout.json")
        self.open_file()
        layout_dict = read_layout_file(path_str)
        layout_dict[LAYOUT_KEY_STR] = equation_list
        layout_dict["tabs"][0]["plots"] = [
            {"curves": [{"signal": name_list[2], "color": "#0000ff",
                         "width": 2}]}]
        self.load(self.write_layout("pasted.json", layout_dict))
        self.assertEqual(self.view.report_list, [])
        self.assertEqual(self.store.names(), name_list[:3])
        self.assertEqual(self.curve_names(),
                         [("Tab 1", [[name_list[2]]])])

    @covers("LLFR-00262", "LLFR-00231", "LLFR-00237")
    def test_signals_not_created_are_reported(self) -> None:
        """Not created signals are named with the reason, and their
        curves are treated as missing signals."""
        name_list = self.build_synthetic_layout()
        path_str = self.save("layout.json")
        layout_dict = read_layout_file(path_str)
        entry_list = layout_dict[LAYOUT_KEY_STR]
        entry_list[0]["parameter"]["order"] = 12
        entry_list[3]["name"] = "Torque"
        self.open_file()
        self.load(self.write_layout("edited.json", layout_dict))
        # Only the FFT of Speed is created: the others need lowpass.
        self.assertEqual(self.store.names(), [name_list[5]])
        self.assertEqual(self.view.synthetic_name_set, {name_list[5]})
        self.assertEqual(len(self.view.report_list), 1)
        report_str = self.view.report_list[0]
        self.assertIn(SYNTHETIC_HEADING_STR, report_str)
        self.assertIn(f"  - {name_list[0]}: ", report_str)
        self.assertIn("order", report_str)
        self.assertIn(f"  - {name_list[1]}: The signal "
                      f"\"{name_list[0]}\" it is computed from was not "
                      f"created.", report_str)
        self.assertIn("  - Torque: \"Torque\" is the name of a signal "
                      "of the data file.", report_str)
        self.assertIn("Signals not in the data file:", report_str)
        # LLFR-00231: plot 2 lost every curve and was not created.
        self.assertEqual(self.curve_names(), [("Tab 1", [["Speed"]])])
        self.assertIn("Data tip at 2 s", report_str)
        self.assertIn("Delta X marker between 1 s and 5 s", report_str)

    @covers("LLFR-00262", "LLFR-00237")
    def test_fft_range_limited_is_reported(self) -> None:
        """An FFT range beyond the file is limited and reported."""
        self.build_synthetic_layout()
        layout_dict = read_layout_file(self.save("layout.json"))
        layout_dict[LAYOUT_KEY_STR][5]["parameter"] = {"start": -3.0,
                                                       "end": 50.0}
        self.open_file()
        self.load(self.write_layout("edited.json", layout_dict))
        fft_signal = self.store.get("fft_Speed_1s_to_8s")
        self.assertEqual(fft_signal.parameter, (0.0, 9.9))
        self.assertIn("Values replaced:", self.view.report_list[0])
        self.assertIn("Time range of the FFT signal fft_Speed_1s_to_8s, "
                      "-3 s to 50 s: limited to the time range of the "
                      "data file, 0 s to 9.9 s.", self.view.report_list[0])

    @covers("LLFR-00262", "LLFR-00238")
    def test_undo_history_cleared(self) -> None:
        """Loading clears the undo history, as LLFR-00238 says."""
        self.build_synthetic_layout()
        path_str = self.save("layout.json")
        self.assertTrue(self.plot_controller.undo_history.can_undo())
        self.load(path_str)
        self.assertFalse(self.plot_controller.undo_history.can_undo())


class KeptTabsTest(LayoutSyntheticTestCase):
    """The current synthetic signals are removed (LLFR-00262) while
    the current tabs are kept (LLFR-00229)."""

    @covers("LLFR-00262", "LLFR-00229")
    def test_same_signals_keep_the_kept_curves(self) -> None:
        """Loading the same signals keeps the curves of kept tabs."""
        name_list = self.build_synthetic_layout()
        old_curve_list = self.curve_names()
        self.load(self.save("layout.json"))
        self.assertEqual(self.view.report_list, [])
        self.assertEqual(self.store.names(), name_list)
        curve_list = self.curve_names()
        self.assertEqual(curve_list[0], old_curve_list[0])
        self.assertEqual(curve_list[1][1], old_curve_list[0][1])
        self.assertEqual(len(self.workspace.tab_list[0].plot_list[0]
                             .pinned_tip_list), 1)

    @covers("LLFR-00262", "LLFR-00229", "LLFR-00237", "LLFR-00051")
    def test_changed_signals_lose_their_kept_curves(self) -> None:
        """A changed or dropped synthetic signal leaves the kept tabs."""
        name_list = self.build_synthetic_layout()
        layout_dict = read_layout_file(self.save("layout.json"))
        # The low-pass gets another order: it and the signals computed
        # from it change; the moving average is left out of the file.
        layout_dict[LAYOUT_KEY_STR][0]["parameter"]["order"] = 4
        del layout_dict[LAYOUT_KEY_STR][2]
        layout_dict["tabs"] = []
        self.load(self.write_layout("edited.json", layout_dict))
        self.assertEqual(self.store.names(),
                         [name_list[index_i]
                          for index_i in (0, 1, 3, 4, 5)])
        # Plot 1 keeps Speed; plot 2 (moving average and product) is
        # deleted, being left with no curve.
        self.assertEqual(self.curve_names(), [("Tab 1", [["Speed"]])])
        self.assertEqual(self.workspace.tab_list[0].plot_list[0]
                         .pinned_tip_list, [])
        report_str = self.view.report_list[0]
        self.assertIn(REMOVED_HEADING_STR, report_str)
        for name_str, plot_i in ((name_list[0], 1), (name_list[2], 2),
                                 (name_list[4], 2)):
            self.assertIn(f"Curve of {name_str} in plot {plot_i} of tab "
                          f"\"Tab 1\": removed", report_str)
        # The views show the model again.
        tab_id_i = self.workspace.tab_list[0].tab_id_i
        self.assertEqual(
            self.view.plot_id_list(tab_id_i),
            [plot.plot_id_i
             for plot in self.workspace.tab_list[0].plot_list])

    @covers("LLFR-00262", "LLFR-00229")
    def test_all_kept_plots_removed_replaces_the_tabs(self) -> None:
        """With no plot left, the file's tabs replace the current ones."""
        self.build_synthetic_layout()
        layout_dict = read_layout_file(self.save("layout.json"))
        layout_dict[LAYOUT_KEY_STR] = []
        layout_dict["tabs"] = [{"name": "Other", "plots": [
            {"curves": [{"signal": "Torque", "color": "#0000ff",
                         "width": 1}]}]}]
        self.view.handler_dict["curve_delete_handler"](
            self.workspace.tab_list[0].plot_list[0].plot_id_i, "Speed")
        self.load(self.write_layout("edited.json", layout_dict))
        self.assertEqual(self.store.names(), [])
        self.assertEqual(self.curve_names(), [("Other", [["Torque"]])])


class FailedLoadTest(LayoutSyntheticTestCase):
    """A load that fails keeps the synthetic signals (LLFR-00236)."""

    @covers("LLFR-00236", "LLFR-00262")
    def test_unexpected_failure_restores_the_signals(self) -> None:
        """The synthetic signals and curves are put back."""
        name_list = self.build_synthetic_layout()
        old_curve_list = self.curve_names()
        layout_dict = read_layout_file(self.save("layout.json"))
        layout_dict[LAYOUT_KEY_STR][0]["parameter"]["order"] = 4
        path_str = self.write_layout("edited.json", layout_dict)
        with mock.patch.object(self.workspace, "add_named_tab",
                               side_effect=RuntimeError("broken")), \
                mock.patch.object(self.workspace, "add_tab",
                                  side_effect=RuntimeError("broken")):
            self.load(path_str)
        self.assertEqual(len(self.view.load_error_list), 1)
        self.assertIn("broken", self.view.load_error_list[0])
        self.assertEqual(self.store.names(), name_list)
        self.assertEqual(self.curve_names(), old_curve_list)
        self.assertEqual(self.view.synthetic_name_set, set(name_list))

    @covers("LLFR-00236", "LLFR-00262")
    def test_unreadable_file_keeps_the_signals(self) -> None:
        """A file that is not a layout changes no synthetic signal."""
        name_list = self.build_synthetic_layout()
        path_str = self.path("bad.json")
        with open(path_str, "w", encoding="utf-8") as output_file:
            output_file.write("[1, 2")
        self.load(path_str)
        self.assertEqual(len(self.view.load_error_list), 1)
        self.assertEqual(self.store.names(), name_list)


if __name__ == "__main__":
    unittest.main()
