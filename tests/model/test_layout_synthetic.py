"""Tests for synthetic signals in layout files (issue #110).

They check, without Qt, that the entries of the synthetic signals are
written to the layout file (LLFR-00225 item 10, LLFR-00227) and that
loading creates them again in the file's order, with the reasons of
those not created in the load report (LLFR-00237, LLFR-00262), and
that the plots are rebuilt with them (LLFR-00230, LLFR-00231).
"""

import copy
import json
import random
import unittest

import numpy as np

from tests.support import covers
from tests.model.test_synthetic_signals import DataFile

from model.layout_file import (
    LayoutReport, SYNTHETIC_HEADING_STR, build_layout_dict, layout_text,
    parse_layout_text, rebuild_layout)
from model.synthetic_signals import (
    LAYOUT_KEY_STR, SyntheticSignalStore, create_layout_signals,
    entries_text, same_signal)
from model.workspace import DELTA_X_KIND_STR, Workspace

# LLFR-00225 item 10: one entry of every parameter kind, chained.
FILTER_ZERO_TUPLE = (3.0, 4, "zero")


def make_chained_store(data_file: DataFile) -> list:
    """Create synthetic signals of every parameter kind, chained.

    Inputs:
        data_file: the DataFile (100 Hz, 0 to 10 s) whose store is
            filled.
    Outputs: the names of the created signals, in creation order.
    """
    lowpass = data_file.create("lowpass", ["Torque"],
                               (5.0, 2, "first_value"))
    highpass = data_file.create("highpass", [lowpass.name_str],
                                FILTER_ZERO_TUPLE)
    average = data_file.create("movingaverage", [highpass.name_str], 7)
    greater = data_file.create("greater", ["Speed"], 4.5)
    divide = data_file.create("divide", [average.name_str], -2.5)
    product = data_file.create("product", [divide.name_str, "Speed"])
    integral = data_file.create("integral", [product.name_str])
    fft = data_file.create("fft", [lowpass.name_str], (1.5, 3.0))
    return [signal.name_str for signal in
            (lowpass, highpass, average, greater, divide, product,
             integral, fft)]


def load_entries(entry_list, data_file: DataFile) -> tuple:
    """Create the entries in the (emptied) store of a data file.

    Inputs:
        entry_list: the "synthetic_signals" list.
        data_file: the DataFile.
    Outputs: what create_layout_signals returns.
    """
    data_file.store.clear()
    return create_layout_signals(data_file.store, entry_list,
                                 data_file.lookup, data_file.time_array,
                                 data_file.data_name_set())


def valid_entry(name_str="lowpass_Speed", operation_str="lowpass",
                source_list=None, parameter=None) -> dict:
    """Return a layout file entry of a synthetic signal.

    Inputs:
        name_str: its name.
        operation_str: its operation id.
        source_list: its sources (["Speed"] when None).
        parameter: its parameter ({"cutoff": 5, "order": 2, "start":
            "first_value"} when None and operation_str is "lowpass").
    Outputs: the entry dict.
    """
    if parameter is None and operation_str == "lowpass":
        return valid_entry(name_str, operation_str, source_list,
                           {"cutoff": 5.0, "order": 2,
                            "start": "first_value"})
    return {"name": name_str, "operation": operation_str,
            "signals": ["Speed"] if source_list is None else source_list,
            "parameter": parameter}


class SaveEntriesTest(unittest.TestCase):
    """The layout file holds the synthetic signals (LLFR-00225)."""

    @covers("LLFR-00225", "LLFR-00227")
    def test_layout_file_holds_every_parameter_kind(self) -> None:
        """Each entry holds name, operation, sources and parameter."""
        data_file = DataFile()
        name_list = make_chained_store(data_file)
        layout_dict = build_layout_dict(
            Workspace(random.Random(1)), 0, (0.0, 10.0), False, (),
            data_file.store.layout_entries())
        text_str = layout_text(layout_dict)
        entry_list = json.loads(text_str)[LAYOUT_KEY_STR]
        self.assertEqual([entry["name"] for entry in entry_list],
                         name_list)
        self.assertEqual(entry_list[0]["parameter"],
                         {"cutoff": 5.0, "order": 2,
                          "start": "first_value"})
        self.assertEqual(entry_list[1]["parameter"],
                         {"cutoff": 3.0, "order": 4, "start": "zero"})
        self.assertEqual(entry_list[1]["signals"], [name_list[0]])
        self.assertEqual(entry_list[2]["parameter"], 7)
        self.assertEqual(entry_list[3]["parameter"], 4.5)
        self.assertEqual(entry_list[4]["parameter"], -2.5)
        self.assertEqual(entry_list[5]["signals"], [name_list[4], "Speed"])
        self.assertIsNone(entry_list[5]["parameter"])
        self.assertIsNone(entry_list[6]["parameter"])
        self.assertEqual(entry_list[7]["parameter"],
                         {"start": 1.5, "end": 3.0})
        # LLFR-00227: indented by 2 spaces, each value on its own line.
        self.assertIn('\n      "operation": "lowpass",\n', text_str)

    @covers("LLFR-00225")
    def test_renamed_signals_are_saved_with_current_names(self) -> None:
        """A renamed source is saved under its current name."""
        data_file = DataFile()
        name_list = make_chained_store(data_file)
        data_file.store.rename(name_list[0], "smooth",
                               data_file.data_name_set())
        entry_list = data_file.store.layout_entries()
        self.assertEqual(entry_list[0]["name"], "smooth")
        self.assertEqual(entry_list[1]["signals"], ["smooth"])
        self.assertEqual(entry_list[7]["signals"], ["smooth"])


class CreateEntriesTest(unittest.TestCase):
    """Loading creates the synthetic signals again (LLFR-00262)."""

    @covers("LLFR-00262", "LLFR-00225", "LLFR-00227")
    def test_round_trip_creates_the_same_signals(self) -> None:
        """Saved and loaded signals have the same entries and samples."""
        data_file = DataFile()
        make_chained_store(data_file)
        old_signal_list = list(data_file.store.signal_list)
        text_str = entries_text(data_file.store.layout_entries())
        not_created_list, limited_list = load_entries(
            json.loads(text_str), data_file)
        self.assertEqual(not_created_list, [])
        self.assertEqual(limited_list, [])
        self.assertEqual(data_file.store.names(),
                         [signal.name_str for signal in old_signal_list])
        for old_signal in old_signal_list:
            new_signal = data_file.store.get(old_signal.name_str)
            self.assertTrue(same_signal(old_signal, data_file.store,
                                        new_signal), old_signal.name_str)
            np.testing.assert_array_equal(new_signal.value_array,
                                          old_signal.value_array)

    @covers("LLFR-00262", "LLFR-00279")
    def test_copied_equation_loads(self) -> None:
        """The text of "Copy equation" pasted in a layout loads."""
        data_file = DataFile()
        name_list = make_chained_store(data_file)
        equation_str = data_file.store.equation_text(name_list[6])
        old_value_array = data_file.store.get(name_list[6]).value_array
        layout_str = layout_text(build_layout_dict(
            Workspace(random.Random(1)), 0, (0.0, 10.0), False))
        layout_dict = parse_layout_text(layout_str.replace(
            '"synthetic_signals": []',
            '"synthetic_signals": ' + equation_str))
        not_created_list, _ = load_entries(layout_dict[LAYOUT_KEY_STR],
                                           data_file)
        self.assertEqual(not_created_list, [])
        # LLFR-00279: the signal and its ancestors, in creation order.
        self.assertEqual(data_file.store.names(),
                         [name_list[index_i] for index_i in
                          (0, 1, 2, 4, 5, 6)])
        np.testing.assert_array_equal(
            data_file.store.get(name_list[6]).value_array,
            old_value_array)

    @covers("LLFR-00262", "LLFR-00237")
    def test_missing_source_is_not_created(self) -> None:
        """A missing source stops the signal and its dependents."""
        data_file = DataFile()
        entry_list = [
            valid_entry("lowpass_Pressure", source_list=["Pressure"]),
            valid_entry("integral_x", "integral", ["lowpass_Pressure"]),
            valid_entry("integral_Speed", "integral")]
        not_created_list, _ = load_entries(entry_list, data_file)
        self.assertEqual(data_file.store.names(), ["integral_Speed"])
        self.assertEqual(not_created_list[0][0], "lowpass_Pressure")
        self.assertIn('"Pressure"', not_created_list[0][1])
        self.assertIn("missing", not_created_list[0][1])
        self.assertEqual(not_created_list[1][0], "integral_x")
        self.assertIn('"lowpass_Pressure"', not_created_list[1][1])
        self.assertIn("was not created", not_created_list[1][1])

    @covers("LLFR-00262", "LLFR-00245", "LLFR-00269", "LLFR-00272",
            "LLFR-00237")
    def test_parameters_not_allowed(self) -> None:
        """Parameters outside the dialogs' ranges are reported."""
        data_file = DataFile()
        bad_list = [
            valid_entry("a", parameter={"cutoff": 50.0, "order": 2,
                                        "start": "zero"}),
            valid_entry("b", parameter={"cutoff": 0.0, "order": 2,
                                        "start": "zero"}),
            valid_entry("c", parameter={"cutoff": 5.0, "order": 9,
                                        "start": "zero"}),
            valid_entry("d", parameter={"cutoff": 5.0, "order": 2.5,
                                        "start": "zero"}),
            valid_entry("e", parameter={"cutoff": 5.0, "order": 2,
                                        "start": "middle"}),
            valid_entry("f", parameter={"cutoff": "x", "order": 2,
                                        "start": "zero"}),
            valid_entry("g", parameter={"cutoff": 5.0, "order": 2}),
            valid_entry("h", parameter=5.0),
            valid_entry("i", "movingaverage", parameter=1),
            valid_entry("j", "movingaverage", parameter=1002),
            valid_entry("k", "movingaverage", parameter=2.5),
            valid_entry("l", "divide", parameter=0),
            valid_entry("m", "greater", parameter="big"),
            valid_entry("n", "add", parameter=None),
            valid_entry("o", "integral", parameter=3),
            valid_entry("p", "fft", parameter=[1, 2]),
            valid_entry("q", "fft", parameter={"start": "a", "end": 2}),
        ]
        not_created_list, _ = load_entries(bad_list, data_file)
        self.assertEqual(data_file.store.names(), [])
        self.assertEqual([label_str for label_str, _ in not_created_list],
                         [entry["name"] for entry in bad_list])
        for _, reason_str in not_created_list:
            self.assertTrue(reason_str)
            self.assertNotIn("unexpected", reason_str)

    @covers("LLFR-00262", "LLFR-00247", "LLFR-00237")
    def test_uneven_time_steps(self) -> None:
        """Filters and FFTs need evenly spaced time samples."""
        time_array = np.cumsum(np.r_[0.0, np.tile([0.01, 0.02], 300)])
        data_file = DataFile(time_array)
        entry_list = [
            valid_entry("a"),
            valid_entry("b", "highpass"),
            valid_entry("c", "fft", parameter={"start": 0, "end": 5}),
            valid_entry("d", "integral")]
        entry_list[1]["parameter"] = entry_list[0]["parameter"]
        not_created_list, _ = load_entries(entry_list, data_file)
        self.assertEqual(data_file.store.names(), ["d"])
        self.assertEqual(len(not_created_list), 3)
        for _, reason_str in not_created_list:
            self.assertIn("evenly spaced", reason_str)

    @covers("LLFR-00262", "LLFR-00250", "LLFR-00237")
    def test_too_few_samples_for_an_fft(self) -> None:
        """An FFT range with fewer than 8 samples is reported."""
        data_file = DataFile()
        not_created_list, _ = load_entries(
            [valid_entry("f", "fft", parameter={"start": 1.0,
                                                "end": 1.05})],
            data_file)
        self.assertEqual(data_file.store.names(), [])
        self.assertIn("too few samples", not_created_list[0][1])

    @covers("LLFR-00262", "LLFR-00237")
    def test_fft_range_limited_to_the_data_file(self) -> None:
        """The saved FFT range is limited to the file's time range."""
        data_file = DataFile()
        not_created_list, limited_list = load_entries(
            [valid_entry("fft_Speed_-5s_to_20s", "fft",
                         parameter={"start": -5.0, "end": 20.0}),
             valid_entry("fft_Speed_2s_to_20s", "fft",
                         parameter={"start": 2.0, "end": 20.0}),
             valid_entry("fft_Speed_2s_to_3s", "fft",
                         parameter={"start": 2.0, "end": 3.0})],
            data_file)
        self.assertEqual(not_created_list, [])
        # LLFR-00262: the saved names are kept.
        self.assertEqual(data_file.store.names(),
                         ["fft_Speed_-5s_to_20s", "fft_Speed_2s_to_20s",
                          "fft_Speed_2s_to_3s"])
        self.assertEqual(
            data_file.store.get("fft_Speed_-5s_to_20s").parameter,
            (0.0, 10.0))
        self.assertEqual(limited_list, [
            ("fft_Speed_-5s_to_20s", (-5.0, 20.0), (0.0, 10.0)),
            ("fft_Speed_2s_to_20s", (2.0, 20.0), (2.0, 10.0))])

    @covers("LLFR-00262", "LLFR-00237")
    def test_fft_range_outside_the_data_file(self) -> None:
        """A range entirely outside the file creates no FFT."""
        data_file = DataFile()
        not_created_list, _ = load_entries(
            [valid_entry("f", "fft", parameter={"start": 20.0,
                                                "end": 30.0})],
            data_file)
        self.assertEqual(data_file.store.names(), [])
        self.assertEqual(not_created_list[0][0], "f")
        self.assertTrue(not_created_list[0][1])

    @covers("LLFR-00262", "LLFR-00237")
    def test_name_of_a_data_file_signal(self) -> None:
        """A saved name of a data file signal is not created."""
        data_file = DataFile()
        not_created_list, _ = load_entries(
            [valid_entry("Torque"), valid_entry("integral_x", "integral",
                                                ["Torque"])],
            data_file)
        # LLFR-00262: the dependent uses the data file's Torque.
        self.assertEqual(data_file.store.names(), ["integral_x"])
        self.assertEqual(not_created_list[0][0], "Torque")
        self.assertIn("data file", not_created_list[0][1])

    @covers("LLFR-00262", "LLFR-00237")
    def test_duplicate_names(self) -> None:
        """A second entry with an earlier entry's name is reported."""
        data_file = DataFile()
        not_created_list, _ = load_entries(
            [valid_entry("twice", "integral"),
             valid_entry(" twice ", "derivative")], data_file)
        self.assertEqual(data_file.store.names(), ["twice"])
        self.assertEqual(data_file.store.get("twice").operation_str,
                         "integral")
        self.assertEqual(not_created_list[0][0], "twice")
        self.assertIn("earlier synthetic signal", not_created_list[0][1])

    @covers("LLFR-00262", "LLFR-00237")
    def test_forward_references_and_cycles(self) -> None:
        """A source that comes later in the list is reported."""
        data_file = DataFile()
        entry_list = [
            valid_entry("first", "integral", ["second"]),
            valid_entry("second", "integral", ["Speed"]),
            valid_entry("self", "integral", ["self"]),
            valid_entry("x", "integral", ["y"]),
            valid_entry("y", "integral", ["x"])]
        not_created_list, _ = load_entries(entry_list, data_file)
        self.assertEqual(data_file.store.names(), ["second"])
        reason_dict = dict(not_created_list)
        self.assertIn("comes later", reason_dict["first"])
        self.assertIn('"self"', reason_dict["self"])
        self.assertIn("comes later", reason_dict["x"])
        self.assertIn("was not created", reason_dict["y"])

    @covers("LLFR-00262", "LLFR-00251", "LLFR-00237")
    def test_fft_as_a_source(self) -> None:
        """No synthetic signal is computed from an FFT signal."""
        data_file = DataFile()
        not_created_list, _ = load_entries(
            [valid_entry("f", "fft", parameter={"start": 0, "end": 5}),
             valid_entry("g", "integral", ["f"])], data_file)
        self.assertEqual(data_file.store.names(), ["f"])
        self.assertIn("FFT", not_created_list[0][1])

    @covers("LLFR-00262", "LLFR-00237")
    def test_malformed_entries_never_raise(self) -> None:
        """Hand-edited entries of any type are reported, not raised."""
        data_file = DataFile()
        weird_list = [None, True, 0, -1, 3.5, "x", [], {}, [1, 2],
                      {"a": 1}, float("nan")]
        base_entry = valid_entry("base")
        entry_list = list(weird_list)
        for key_str in ("name", "operation", "signals", "parameter"):
            for weird_value in weird_list:
                entry_list.append(dict(base_entry, **{key_str:
                                                      weird_value}))
            entry_list.append({other_str: value for other_str, value
                               in base_entry.items()
                               if other_str != key_str})
        entry_list.append(dict(base_entry, operation="square_root"))
        entry_list.append(dict(base_entry, signals=["Speed", "Torque"]))
        entry_list.append(valid_entry("p", "product", ["Speed"]))
        for case_value in (entry_list, None, {}, "x", 3):
            not_created_list, _ = load_entries(case_value, data_file)
            for label_str, reason_str in not_created_list:
                self.assertIsInstance(label_str, str)
                self.assertTrue(reason_str)
        # A "parameter" missing from a lowpass entry is reported too.
        names_list = data_file.store.names()
        self.assertEqual(names_list, [])

    @covers("LLFR-00262", "LLFR-00237")
    def test_source_name_that_is_not_a_text(self) -> None:
        """A source that is not a text is reported as such."""
        data_file = DataFile()
        not_created_list, _ = load_entries(
            [valid_entry("a", "integral", [1]),
             valid_entry("b", "integral", ["Speed", "Torque"])],
            data_file)
        self.assertIn("must be texts", not_created_list[0][1])
        self.assertIn("1 signal name(s)", not_created_list[1][1])

    @covers("LLFR-00262")
    def test_unexpected_errors_skip_only_the_entry(self) -> None:
        """An unexpected failure of one entry is reported, not raised."""
        data_file = DataFile()

        def broken_lookup(name_str: str):
            """Fail for Torque only.

            Inputs:
                name_str: the signal name.
            Outputs: its samples.
            """
            if name_str == "Torque":
                raise RuntimeError("disk on fire")
            return data_file.lookup(name_str)

        not_created_list, _ = create_layout_signals(
            data_file.store,
            [valid_entry("a", "integral", ["Torque"]),
             valid_entry("b", "integral")],
            broken_lookup, data_file.time_array, data_file.data_name_set())
        self.assertEqual(data_file.store.names(), ["b"])
        self.assertIn("disk on fire", not_created_list[0][1])


class SameSignalTest(unittest.TestCase):
    """Whether a recreated synthetic signal equals the old one."""

    @covers("LLFR-00262", "LLFR-00229")
    def test_same_and_changed_signals(self) -> None:
        """Same entry and samples are equal; any change is not."""
        data_file = DataFile()
        old_signal = data_file.create("lowpass", ["Torque"],
                                      (5.0, 2, "first_value"))
        other_store = SyntheticSignalStore()
        same_entry = data_file.store.layout_entry(old_signal)
        other_file = DataFile()
        other_file.store = other_store
        new_signal = other_file.create_from_entry(same_entry)
        self.assertTrue(same_signal(old_signal, other_store, new_signal))
        changed_entry = copy.deepcopy(same_entry)
        changed_entry["parameter"]["order"] = 3
        changed_entry["name"] = "changed"
        changed_signal = other_file.create_from_entry(changed_entry)
        changed_signal.name_str = old_signal.name_str
        self.assertFalse(same_signal(old_signal, other_store,
                                     changed_signal))
        # Same entry but other samples (the source changed).
        new_signal.value_array = new_signal.value_array + 1.0
        self.assertFalse(same_signal(old_signal, other_store, new_signal))
        fft_signal = data_file.create("fft", ["Torque"], (0.0, 5.0))
        self.assertFalse(same_signal(old_signal, data_file.store,
                                     fft_signal))
        self.assertTrue(same_signal(fft_signal, data_file.store,
                                    fft_signal))


class RebuildWithSyntheticTest(unittest.TestCase):
    """The plots are rebuilt with the created signals (LLFR-00230)."""

    def builder_for(self, data_file: DataFile):
        """Return a synthetic signal builder for rebuild_layout.

        Inputs:
            data_file: the DataFile whose store is filled.
        Outputs: the builder function.
        """

        def builder(entry_list, report: LayoutReport) -> tuple:
            """Create the entries and report those not created.

            Inputs:
                entry_list: the "synthetic_signals" list.
                report: the LayoutReport.
            Outputs: (time signals dict, FFT names set).
            """
            not_created_list, _ = load_entries(entry_list, data_file)
            for label_str, reason_str in not_created_list:
                report.add_synthetic_signal(f"{label_str}: {reason_str}")
            store = data_file.store
            return ({signal.name_str: signal.value_array
                     for signal in store.signal_list
                     if not signal.is_fft_b},
                    {signal.name_str for signal in store.signal_list
                     if signal.is_fft_b})

        return builder

    @covers("LLFR-00230", "LLFR-00231", "LLFR-00232", "LLFR-00262",
            "LLFR-00237")
    def test_curves_tips_and_deltas_of_synthetic_signals(self) -> None:
        """Synthetic curves, tips and deltas are rebuilt; lost ones are
        reported as missing signals."""
        data_file = DataFile()
        name_list = make_chained_store(data_file)
        workspace = Workspace(random.Random(1))
        tab = workspace.tab_list[0]
        first_plot = workspace.add_plot(tab.tab_id_i)
        first_plot.add_curve(name_list[0])
        first_plot.add_curve("Speed")
        first_plot.add_pinned_tip(name_list[0], 2.0, float(
            data_file.store.get(name_list[0]).value_array[200]))
        second_plot = workspace.add_plot(tab.tab_id_i)
        second_plot.add_curve(name_list[6])
        second_plot.add_curve(name_list[2])
        value_array = data_file.store.get(name_list[6]).value_array
        second_plot.add_delta_marker(
            DELTA_X_KIND_STR, (name_list[6], 1.0, float(value_array[100])),
            (name_list[6], 4.0, float(value_array[400])))
        layout_dict = json.loads(layout_text(build_layout_dict(
            workspace, tab.tab_id_i, (0.0, 10.0), False, (),
            data_file.store.layout_entries())))
        # Round trip: everything is rebuilt, with no report.
        new_workspace = Workspace(random.Random(1))
        result = rebuild_layout(new_workspace, layout_dict,
                                data_file.signal_dict,
                                data_file.time_array,
                                self.builder_for(data_file))
        self.assertTrue(result.report.is_empty(), result.report.text())
        again_dict = build_layout_dict(
            new_workspace, new_workspace.tab_list[0].tab_id_i,
            (0.0, 10.0), False, (), data_file.store.layout_entries())
        self.assertEqual(again_dict, build_layout_dict(
            workspace, tab.tab_id_i, (0.0, 10.0), False, (),
            data_file.store.layout_entries()))
        # The data file's dict is not changed.
        self.assertNotIn(name_list[0], data_file.signal_dict)
        # The first signal is not created: its curve, tip, and every
        # signal computed from it are lost.
        broken_dict = copy.deepcopy(layout_dict)
        broken_dict[LAYOUT_KEY_STR][0]["signals"] = ["Pressure"]
        new_workspace = Workspace(random.Random(1))
        result = rebuild_layout(new_workspace, broken_dict,
                                data_file.signal_dict,
                                data_file.time_array,
                                self.builder_for(data_file))
        self.assertEqual(data_file.store.names(), [name_list[3]])
        plot_list = new_workspace.tab_list[0].plot_list
        # LLFR-00231: the second plot has no curve left: not created.
        self.assertEqual(len(plot_list), 1)
        self.assertEqual([curve.signal_name_str
                          for curve in plot_list[0].curve_list], ["Speed"])
        report_str = result.report.text()
        self.assertIn(SYNTHETIC_HEADING_STR, report_str)
        self.assertIn(f"{name_list[0]}: The signal \"Pressure\"",
                      report_str)
        self.assertIn(f"{name_list[1]}: The signal \"{name_list[0]}\"",
                      report_str)
        # LLFR-00231, LLFR-00237: curves of signals not created are
        # missing signals, each named once.
        self.assertEqual(result.report.missing_signal_list,
                         [name_list[0], name_list[6], name_list[2]])
        self.assertIn("Data tip at 2 s", report_str)
        self.assertIn("Delta X marker between 1 s and 4 s", report_str)

    @covers("LLFR-00230", "LLFR-00251", "LLFR-00237")
    def test_fft_curve_in_a_time_plot_is_not_drawn(self) -> None:
        """A hand-edited FFT curve in a time plot is reported."""
        # TODO(#109): frequency plots are rebuilt from layouts.
        data_file = DataFile()
        name_list = make_chained_store(data_file)
        layout_dict = build_layout_dict(
            Workspace(random.Random(1)), 0, (0.0, 10.0), False, (),
            data_file.store.layout_entries())
        layout_dict["tabs"][0]["plots"] = [{
            "curves": [{"signal": name_list[7], "color": "#0000ff",
                        "width": 1},
                       {"signal": "Speed", "color": "#000000",
                        "width": 1}],
            "data_tips": [{"signal": name_list[7], "time": 1.0,
                           "label_position": None}],
            "delta_markers": []}]
        workspace = Workspace(random.Random(1))
        result = rebuild_layout(workspace, layout_dict,
                                data_file.signal_dict,
                                data_file.time_array,
                                self.builder_for(data_file))
        plot = workspace.tab_list[0].plot_list[0]
        self.assertEqual([curve.signal_name_str
                          for curve in plot.curve_list], ["Speed"])
        report_str = result.report.text()
        self.assertIn("an FFT signal is not drawn in a time plot",
                      report_str)
        self.assertIn(f"the signal {name_list[7]} is not drawn",
                      report_str)
        self.assertEqual(result.report.missing_signal_list, [])

    @covers("LLFR-00235", "LLFR-00237", "LLFR-00262")
    def test_synthetic_signals_that_are_not_a_list(self) -> None:
        """A "synthetic_signals" value that is not a list is reported;
        a missing one is not."""
        data_file = DataFile()
        layout_dict = build_layout_dict(
            Workspace(random.Random(1)), 0, (0.0, 10.0), False)
        for value, reported_b in (({"name": "x"}, True), ("x", True),
                                  (3, True), ([], False)):
            layout_dict[LAYOUT_KEY_STR] = value
            result = rebuild_layout(Workspace(random.Random(1)),
                                    layout_dict, data_file.signal_dict,
                                    data_file.time_array,
                                    self.builder_for(data_file))
            self.assertEqual(
                "\"synthetic_signals\" is not a list"
                in result.report.text(), reported_b, value)
        del layout_dict[LAYOUT_KEY_STR]
        result = rebuild_layout(Workspace(random.Random(1)), layout_dict,
                                data_file.signal_dict,
                                data_file.time_array,
                                self.builder_for(data_file))
        self.assertTrue(result.report.is_empty())

    @covers("LLFR-00230", "LLFR-00262")
    def test_builder_returning_nothing(self) -> None:
        """A builder that returns None adds no signal."""
        data_file = DataFile()
        layout_dict = build_layout_dict(
            Workspace(random.Random(1)), 0, (0.0, 10.0), False)
        result = rebuild_layout(Workspace(random.Random(1)), layout_dict,
                                data_file.signal_dict,
                                data_file.time_array,
                                lambda entry_list, report: None)
        self.assertTrue(result.report.is_empty())


class ReportTest(unittest.TestCase):
    """The load report lists the synthetic signals (LLFR-00237)."""

    @covers("LLFR-00237")
    def test_sections_in_order(self) -> None:
        """Synthetic signals come first, then removed curves."""
        report = LayoutReport()
        self.assertTrue(report.is_empty())
        report.add_removed("Curve of a in plot 1 of tab \"Tab 1\"")
        self.assertFalse(report.is_empty())
        report.add_missing_signal("b")
        report.add_synthetic_signal("a: reason")
        text_str = report.text()
        self.assertLess(text_str.index(SYNTHETIC_HEADING_STR),
                        text_str.index("Removed from the current tabs:"))
        self.assertLess(text_str.index("Removed from the current tabs:"),
                        text_str.index("Signals not in the data file:"))
        self.assertIn("  - a: reason", text_str)


if __name__ == "__main__":
    unittest.main()
