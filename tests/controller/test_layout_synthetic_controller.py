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
    SYNTHETIC_HEADING_STR, read_layout_file)
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

    def build_synthetic_layout(self, with_fft_b: bool = False) -> list:
        """Create chained synthetic signals and plot some of them.

        Plot 1: lowpass (with a data tip) and Speed; plot 2: the
        moving average of the high-pass and the product (with a Delta
        X marker on the product); with an FFT, plot 3: a frequency plot
        of the FFT of Speed.

        Inputs:
            with_fft_b: True to also create and plot an FFT signal.
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
        if with_fft_b:
            name_list.append(self.create("fft", ["Speed"], (1.0, 8.0)))
            handler_dict["double_click"](name_list[5])
            self.assertTrue(self.workspace.tab_list[0].plot_list[2]
                            .is_frequency_plot())
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

    @covers("LLFR-00283", "LLFR-00225")
    def test_fft_signals_and_frequency_plots_are_not_saved(self) -> None:
        """The FFT signal and its frequency plot are left out."""
        name_list = self.build_synthetic_layout(with_fft_b=True)
        path_str = self.save("layout.json")
        layout_dict = read_layout_file(path_str)
        self.assertEqual([entry["name"] for entry in
                          layout_dict[LAYOUT_KEY_STR]], name_list[:5])
        self.assertEqual(len(layout_dict["tabs"][0]["plots"]), 2)
        self.assertNotIn(name_list[5], self.read_text(path_str))


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
        self.assertEqual(self.view.fft_name_set, set())
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
        # The signals that need lowpass are not created; the entry
        # named like the data signal Torque is renamed (LLFR-00282).
        self.assertEqual(self.store.names(), ["Torque_2"])
        self.assertEqual(self.store.get("Torque_2").operation_str,
                         "greaterorequal")
        self.assertEqual(self.view.synthetic_name_set, {"Torque_2"})
        self.assertEqual(len(self.view.report_list), 1)
        report_str = self.view.report_list[0]
        self.assertIn(SYNTHETIC_HEADING_STR, report_str)
        self.assertIn(f"  - {name_list[0]}: ", report_str)
        self.assertIn("order", report_str)
        self.assertIn(f"  - {name_list[1]}: The signal "
                      f"\"{name_list[0]}\" it is computed from was not "
                      f"created.", report_str)
        # LLFR-00282, LLFR-00237: the rename is reported.
        self.assertIn('Renamed:\n  - Synthetic signal "Torque" \u2192 '
                      '"Torque_2"', report_str)
        self.assertIn("Signals not in the data file:", report_str)
        # LLFR-00231: plot 2 lost every curve and was not created.
        self.assertEqual(self.curve_names(), [("Tab 1", [["Speed"]])])
        self.assertIn("Data tip at 2 s", report_str)
        self.assertIn("Delta X marker between 1 s and 5 s", report_str)

    @covers("LLFR-00283", "LLFR-00231", "LLFR-00229")
    def test_round_trip_with_an_fft_after_reopening(self) -> None:
        """The FFT signal and its frequency plot do not come back, and
        nothing is reported, since the file does not hold them."""
        name_list = self.build_synthetic_layout(with_fft_b=True)
        path_str = self.save("layout.json")
        self.open_file()
        self.load(path_str)
        self.assertEqual(self.view.report_list, [])
        self.assertEqual(self.store.names(), name_list[:5])
        self.assertEqual(len(self.workspace.tab_list[0].plot_list), 2)

    @covers("LLFR-00283", "LLFR-00262", "LLFR-00237", "LLFR-00231")
    def test_fft_entry_in_a_file_is_reported(self) -> None:
        """A hand-added FFT entry is not created; its curve is missing."""
        self.build_synthetic_layout()
        layout_dict = read_layout_file(self.save("layout.json"))
        layout_dict[LAYOUT_KEY_STR].append({
            "name": "fft_Speed_1s_to_8s", "operation": "fft",
            "signals": ["Speed"], "parameter": {"start": 1.0, "end": 8.0}})
        layout_dict["tabs"][0]["plots"][0]["curves"].append(
            {"signal": "fft_Speed_1s_to_8s", "color": "#00aa00",
             "width": 1})
        self.open_file()
        self.load(self.write_layout("edited.json", layout_dict))
        self.assertNotIn("fft_Speed_1s_to_8s", self.store.names())
        report_str = self.view.report_list[0]
        self.assertIn("  - fft_Speed_1s_to_8s: FFT signals are not "
                      "loaded from layout files.", report_str)
        self.assertIn("Signals not in the data file:\n"
                      "  - fft_Speed_1s_to_8s", report_str)

    @covers("LLFR-00278", "LLFR-00279", "LLFR-00283")
    def test_no_equation_for_an_fft_signal(self) -> None:
        """Copy equation does nothing for an FFT signal."""
        name_list = self.build_synthetic_layout(with_fft_b=True)
        self.view.signal_menu_handler_dict["copy_equation"](name_list[5])
        self.assertEqual(self.view.clipboard_text_list, [])
        self.view.signal_menu_handler_dict["copy_equation"](name_list[0])
        self.assertEqual(len(self.view.clipboard_text_list), 1)

    @covers("LLFR-00262", "LLFR-00238")
    def test_undo_history_cleared(self) -> None:
        """Loading clears the undo history, as LLFR-00238 says."""
        self.build_synthetic_layout()
        path_str = self.save("layout.json")
        self.assertTrue(self.plot_controller.undo_history.can_undo())
        self.load(path_str)
        self.assertFalse(self.plot_controller.undo_history.can_undo())


class SyntheticNameTest(LayoutSyntheticTestCase):
    """New names in layout files, and files with the older names."""

    # LLFR-00240: the names build_synthetic_layout gives its signals.
    NEW_NAME_LIST = [
        "lpf_1Hz_order2_Speed",
        "hpf_2Hz_order3_lpf_1Hz_order2_Speed",
        "mavg_4samples_hpf_2Hz_order3_lpf_1Hz_order2_Speed",
        "ge_3_Torque",
        "lpf_1Hz_order2_Speed_prod_Torque"]
    # The names the same signals had before the abbreviations, as an
    # older layout file holds them.
    OLD_NAME_LIST = [
        "lowpass_Speed",
        "highpass_lowpass_Speed",
        "movingaverage_highpass_lowpass_Speed",
        "greaterorequal_Torque",
        "product_lowpass_Speed_Torque"]

    @covers("LLFR-00240", "LLFR-00225", "LLFR-00262", "LLFR-00230")
    def test_round_trip_with_the_new_names(self) -> None:
        """New names are saved with the unchanged operation ids."""
        name_list = self.build_synthetic_layout()
        self.assertEqual(name_list, self.NEW_NAME_LIST)
        path_str = self.save("layout.json")
        entry_list = read_layout_file(path_str)[LAYOUT_KEY_STR]
        self.assertEqual([entry["name"] for entry in entry_list],
                         self.NEW_NAME_LIST)
        self.assertEqual([entry["operation"] for entry in entry_list],
                         ["lowpass", "highpass", "movingaverage",
                          "greaterorequal", "product"])
        self.assertEqual(entry_list[4]["signals"],
                         ["lpf_1Hz_order2_Speed", "Torque"])
        curve_list = self.curve_names()
        self.open_file()
        self.load(path_str)
        self.assertEqual(self.view.report_list, [])
        self.assertEqual(self.store.names(), self.NEW_NAME_LIST)
        self.assertEqual(self.curve_names(), curve_list)
        # LLFR-00282: loading it again adds nothing.
        self.load(path_str)
        self.assertEqual(self.store.names(), self.NEW_NAME_LIST)

    @covers("LLFR-00262", "LLFR-00225", "LLFR-00240", "LLFR-00282")
    def test_older_file_loads_with_its_saved_names(self) -> None:
        """A file with the older names loads them; new ones are new."""
        self.build_synthetic_layout()
        text_str = self.read_text(self.save("layout.json"))
        value_dict = {name_str: self.store.get(name_str).value_array
                      for name_str in self.NEW_NAME_LIST}
        # The longest names first, since the shorter ones are in them.
        for new_name_str, old_name_str in sorted(
                zip(self.NEW_NAME_LIST, self.OLD_NAME_LIST),
                key=lambda pair_tuple: -len(pair_tuple[0])):
            text_str = text_str.replace(f'"{new_name_str}"',
                                        f'"{old_name_str}"')
        self.assertNotIn("lpf_", text_str)
        old_path_str = self.path("old.json")
        with open(old_path_str, "w", encoding="utf-8") as output_file:
            output_file.write(text_str)
        self.open_file()
        self.load(old_path_str)
        self.assertEqual(self.view.load_error_list, [])
        self.assertEqual(self.view.report_list, [])
        self.assertEqual(self.store.names(), self.OLD_NAME_LIST)
        for new_name_str, old_name_str in zip(self.NEW_NAME_LIST,
                                              self.OLD_NAME_LIST):
            np.testing.assert_array_equal(
                self.store.get(old_name_str).value_array,
                value_dict[new_name_str])
        self.assertEqual(self.curve_names(), [("Tab 1", [
            ["lowpass_Speed", "Speed"],
            ["movingaverage_highpass_lowpass_Speed",
             "product_lowpass_Speed_Torque"]])])
        plot_list = self.workspace.tab_list[0].plot_list
        self.assertEqual(len(plot_list[0].pinned_tip_list), 1)
        self.assertEqual(len(plot_list[1].delta_marker_list), 1)
        # LLFR-00240: a signal created now gets the new name, and the
        # chains of an old name build up from it.
        self.assertEqual(self.create("integral", ["lowpass_Speed"]),
                         "int_lowpass_Speed")
        self.assertEqual(self.create("lowpass", ["Speed"],
                                     (1.0, 2, "zero")),
                         "lpf_1Hz_order2_Speed")
        # The older names are saved as they are.
        entry_list = read_layout_file(self.save("again.json"))[
            LAYOUT_KEY_STR]
        self.assertEqual([entry["name"] for entry in entry_list],
                         self.OLD_NAME_LIST + ["int_lowpass_Speed",
                                               "lpf_1Hz_order2_Speed"])
        # LLFR-00282: loading the older file again adds nothing.
        names_before_list = self.store.names()
        self.load(old_path_str)
        self.assertEqual(self.store.names(), names_before_list)


class KeptTabsTest(LayoutSyntheticTestCase):
    """The current synthetic signals and tabs are kept (LLFR-00229,
    LLFR-00262); the file's signals are reused or renamed (LLFR-00282).
    """

    @covers("LLFR-00282", "LLFR-00262", "LLFR-00229")
    def test_same_layout_twice_adds_nothing(self) -> None:
        """Loading the same layout again reuses every signal."""
        name_list = self.build_synthetic_layout(with_fft_b=True)
        old_curve_list = self.curve_names()
        path_str = self.save("layout.json")
        for load_number_i in range(2):
            self.view.report_list.clear()
            self.load(path_str)
            # LLFR-00237: only the tab name in use is reported; no
            # synthetic signal is renamed.
            self.assertEqual(len(self.view.report_list), 1)
            self.assertTrue(self.view.report_list[0].startswith(
                'Renamed:\n  - Tab "Tab 1" \u2192 "Tab '))
            self.assertNotIn("Synthetic signal", self.view.report_list[0])
            self.assertEqual(self.store.names(), name_list)
            curve_list = self.curve_names()
            # The kept tab, its frequency plot included, is unchanged.
            self.assertEqual(curve_list[0], old_curve_list[0])
            self.assertEqual(curve_list[load_number_i + 1][1],
                             old_curve_list[0][1][:2])
        self.assertEqual(len(self.workspace.tab_list[0].plot_list[0]
                             .pinned_tip_list), 1)
        self.assertEqual(self.view.synthetic_name_set, set(name_list))

    @covers("LLFR-00282", "LLFR-00262", "LLFR-00229", "LLFR-00237")
    def test_changed_signals_get_new_names(self) -> None:
        """A changed recipe creates "_2" signals; the file's curves and
        later entries use them; the kept tabs are unchanged."""
        name_list = self.build_synthetic_layout()
        old_curve_list = self.curve_names()
        layout_dict = read_layout_file(self.save("layout.json"))
        layout_dict[LAYOUT_KEY_STR][0]["parameter"]["order"] = 4
        path_str = self.write_layout("edited.json", layout_dict)
        self.load(path_str)
        renamed_list = [name_list[index_i] + "_2"
                        for index_i in (0, 1, 2, 4)]
        # LLFR-00237: every rename, saved and new name, in one section.
        self.assertEqual(self.view.report_list, ["Renamed:\n" + "\n".join(
            [f'  - Synthetic signal "{name_list[index_i]}" \u2192 '
             f'"{name_list[index_i]}_2"' for index_i in (0, 1, 2, 4)]
            + ['  - Tab "Tab 1" \u2192 "Tab 2"'])])
        self.assertEqual(self.store.names(), name_list + renamed_list)
        curve_list = self.curve_names()
        self.assertEqual(curve_list[0], old_curve_list[0])
        self.assertEqual(curve_list[1][1], [
            [renamed_list[0], "Speed"], [renamed_list[2], renamed_list[3]]])
        new_plot_list = self.workspace.tab_list[1].plot_list
        self.assertEqual(new_plot_list[0].pinned_tip_list[0]
                         .signal_name_str, renamed_list[0])
        self.assertEqual(new_plot_list[1].delta_marker_list[0]
                         .first_point_tuple[0], renamed_list[3])
        self.assertEqual(self.store.get(renamed_list[3]).source_name_list,
                         [renamed_list[0], "Torque"])
        # The same edited file again: nothing new.
        self.load(path_str)
        self.assertEqual(self.store.names(), name_list + renamed_list)
        self.assert_screen_matches_model()

    @covers("LLFR-00282", "LLFR-00262", "LLFR-00229")
    def test_kept_curves_of_signals_left_out_stay(self) -> None:
        """Signals and curves the file does not hold are kept."""
        name_list = self.build_synthetic_layout(with_fft_b=True)
        old_curve_list = self.curve_names()
        layout_dict = read_layout_file(self.save("layout.json"))
        layout_dict[LAYOUT_KEY_STR] = []
        layout_dict["tabs"] = [{"name": "Other", "plots": [
            {"curves": [{"signal": "Torque", "color": "#0000ff",
                         "width": 1}]}]}]
        self.load(self.write_layout("edited.json", layout_dict))
        self.assertEqual(self.view.report_list, [])
        self.assertEqual(self.store.names(), name_list)
        self.assertEqual(self.curve_names(),
                         old_curve_list + [("Other", [["Torque"]])])

    def assert_screen_matches_model(self) -> None:
        """Check that every plot is drawn with its own curves.

        Inputs: none.
        Outputs: none.
        """
        for tab in self.workspace.tab_list:
            for plot in tab.plot_list:
                curve_data_list, _ = self.view.drawn_dict[plot.plot_id_i]
                self.assertEqual(
                    [curve_data[0] for curve_data in curve_data_list],
                    [curve.signal_name_str for curve in plot.curve_list])


class EmptyTabsTest(LayoutSyntheticTestCase):
    """Tabs of the file left with no plot are not created (LLFR-00231)."""

    def file_with_tabs(self, tab_list: list) -> str:
        """Write a layout file with the given tabs.

        Inputs:
            tab_list: the "tabs" entry.
        Outputs: the path.
        """
        layout_dict = read_layout_file(self.save("base.json"))
        layout_dict["tabs"] = tab_list
        return self.write_layout("tabs.json", layout_dict)

    @covers("LLFR-00231", "LLFR-00229", "LLFR-00237")
    def test_shown_tab_is_the_first_created(self) -> None:
        """Empty tabs are skipped; the first created tab is shown."""
        path_str = self.file_with_tabs([
            {"name": "Empty", "plots": []},
            {"name": "Speed tab", "plots": [{"curves": [
                {"signal": "Speed", "color": "#0000ff", "width": 1}]}]}])
        self.load(path_str)
        self.assertEqual(self.view.report_list, [])
        self.assertEqual([tab.name_str for tab in self.workspace.tab_list],
                         ["Speed tab"])
        self.assertEqual(self.view.current_tab_id(),
                         self.workspace.tab_list[0].tab_id_i)

    @covers("LLFR-00231", "LLFR-00229", "LLFR-00066")
    def test_no_tab_with_a_plot_keeps_the_current_tabs(self) -> None:
        """When no tab of the file holds a plot, nothing changes."""
        self.view.handler_dict["add_tab"]()
        tab_id_list = [tab.tab_id_i for tab in self.workspace.tab_list]
        shown_tab_id_i = self.view.current_tab_id()
        self.load(self.file_with_tabs([{"name": "Empty", "plots": []}]))
        self.assertEqual(self.view.report_list, [])
        self.assertEqual([tab.tab_id_i for tab in self.workspace.tab_list],
                         tab_id_list)
        self.assertEqual(self.view.current_tab_id(), shown_tab_id_i)


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

    def assert_screen_matches_model(self) -> None:
        """Check that every plot is drawn with its signals' samples.

        Inputs: none.
        Outputs: none.
        """
        for tab in self.workspace.tab_list:
            self.assertEqual(
                self.view.plot_id_list(tab.tab_id_i),
                [plot.plot_id_i for plot in tab.plot_list])
            for plot in tab.plot_list:
                curve_data_list, _ = self.view.drawn_dict[plot.plot_id_i]
                self.assertEqual(
                    [curve_data[0] for curve_data in curve_data_list],
                    [curve.signal_name_str for curve in plot.curve_list])
                for curve_data in curve_data_list:
                    np.testing.assert_array_equal(
                        curve_data[2],
                        self.plot_controller.signal_values(curve_data[0]))

    def fail_while_rebuilding_tabs(self, layout_dict: dict) -> None:
        """Load a layout while rebuilding its tabs raises an error.

        Inputs:
            layout_dict: the content of the layout file.
        Outputs: none.
        """
        path_str = self.write_layout("failing.json", layout_dict)
        with mock.patch(
                "model.layout_file.LayoutBuilder.rebuild_tabs",
                side_effect=RuntimeError("boom")):
            self.load(path_str)

    def check_failed_load(self, layout_dict: dict) -> None:
        """Check that a failed load leaves model and screen as before.

        Inputs:
            layout_dict: the content of the layout file.
        Outputs: none.
        """
        name_list = self.store.names()
        value_dict = {name_str: self.store.get(name_str).value_array
                      for name_str in name_list}
        old_curve_list = self.curve_names()
        self.fail_while_rebuilding_tabs(layout_dict)
        # LLFR-00236: the box shows the real error.
        self.assertEqual(len(self.view.load_error_list), 1)
        self.assertIn("unexpected error: boom",
                      self.view.load_error_list[0])
        self.assertEqual(self.view.report_list, [])
        self.assertEqual(self.store.names(), name_list)
        for name_str in name_list:
            self.assertIs(self.store.get(name_str).value_array,
                          value_dict[name_str])
        self.assertEqual(self.curve_names(), old_curve_list)
        self.assertEqual(self.view.synthetic_name_set, set(name_list))
        self.assert_screen_matches_model()
        self.assertEqual(len(self.workspace.tab_list[0].plot_list[0]
                             .pinned_tip_list), 1)

    @covers("LLFR-00236", "LLFR-00262")
    def test_failure_with_no_synthetic_signals_in_the_file(self) -> None:
        """A file without synthetic signals fails: all is put back."""
        self.build_synthetic_layout()
        layout_dict = read_layout_file(self.save("layout.json"))
        layout_dict[LAYOUT_KEY_STR] = []
        self.check_failed_load(layout_dict)

    @covers("LLFR-00236", "LLFR-00262")
    def test_failure_with_a_changed_parameter(self) -> None:
        """A file with other samples for the same names fails: the old
        samples are drawn again."""
        self.build_synthetic_layout()
        layout_dict = read_layout_file(self.save("layout.json"))
        layout_dict[LAYOUT_KEY_STR][0]["parameter"]["order"] = 5
        self.check_failed_load(layout_dict)

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
