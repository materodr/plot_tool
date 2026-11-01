"""Tests for the layout file model (model.layout_file, issue #107).

Covers writing the layout file (LLFR-00225 to LLFR-00228), reading and
validating it (LLFR-00236) and rebuilding its layout in a workspace
(LLFR-00229 to LLFR-00235, LLFR-00237). No Qt is needed.
"""

import json
import os
import random
import tempfile
import unittest

import numpy as np

from tests.support import covers

from model import layout_file
from model.curve_colors import MARKER_COLOR_STR, PALETTE_COLOR_TUPLE
from model.layout_file import (
    LayoutFileError, build_layout_dict, ensure_layout_suffix, layout_bytes,
    layout_text, parse_layout_text, read_layout_file, rebuild_layout)
from model.workspace import DELTA_X_KIND_STR, DELTA_Y_KIND_STR, Workspace


def make_signal_dict(signal_name_list=("Speed", "Torque", "Power"),
                     sample_count_i: int = 101,
                     end_s: float = 10.0) -> dict:
    """Return the signals of a data file: Time and some signals.

    Inputs:
        signal_name_list: the names of the signals besides Time.
        sample_count_i: the number of samples.
        end_s: the last time, the first is 0.
    Outputs: a dict name -> numpy array; signal k has the values
        (k + 1) * Time.
    """
    time_array = np.linspace(0.0, end_s, sample_count_i)
    signal_dict = {"Time": time_array}
    for index_i, name_str in enumerate(signal_name_list):
        signal_dict[name_str] = time_array * (index_i + 1)
    return signal_dict


def make_rich_workspace() -> Workspace:
    """Return a workspace with several tabs, plots, curves and markers.

    Tab "Engine" holds a plot with Speed (width 3) and Torque (a custom
    color) with a moved data tip and an automatic one, a Delta X and a
    Delta Y marker, and a second plot with Power. Tab "Empty" holds no
    plot. Two vertical markers are shared.

    Inputs: none.
    Outputs: the Workspace.
    """
    workspace = Workspace(random.Random(3))
    first_tab = workspace.tab_list[0]
    workspace.rename_tab(first_tab.tab_id_i, "Engine")
    plot = workspace.add_plot(first_tab.tab_id_i)
    plot.add_curve("Speed")
    plot.add_curve("Torque")
    plot.set_curve_width("Speed", 3)
    plot.curve_list[1].color_str = "#123456"
    moved_tip = plot.add_pinned_tip("Speed", 1.5, 1.5)
    plot.move_pinned_tip(moved_tip, (20.25, -7.5))
    plot.add_pinned_tip("Torque", 2.0, 4.0)
    plot.add_delta_marker(DELTA_X_KIND_STR, ("Speed", 1.0, 1.0),
                          ("Torque", 3.0, 6.0))
    plot.add_delta_marker(DELTA_Y_KIND_STR, ("Speed", 0.5, 0.5),
                          ("Speed", 2.5, 2.5))
    second_plot = workspace.add_plot(first_tab.tab_id_i)
    second_plot.add_curve("Power")
    second_tab = workspace.add_tab()
    workspace.rename_tab(second_tab.tab_id_i, "Empty")
    workspace.add_marker(1.0)
    marker = workspace.add_marker(4.25)
    workspace.rename_marker(marker.marker_id_i, "Peak")
    return workspace


def workspace_content(workspace) -> tuple:
    """Return what a workspace shows, without any internal id.

    Inputs:
        workspace: the Workspace.
    Outputs: a tuple of tabs (name, plots (curves, tips, delta markers))
        and of markers (name, time).
    """
    tab_list = []
    for tab in workspace.tab_list:
        plot_list = []
        for plot in tab.plot_list:
            curve_tuple = tuple((curve.signal_name_str, curve.color_str,
                                 curve.width_i) for curve in plot.curve_list)
            tip_tuple = tuple((tip.signal_name_str, tip.time_s, tip.value_f,
                               tuple(tip.label_offset_tuple))
                              for tip in plot.pinned_tip_list)
            delta_tuple = tuple((delta.kind_str, delta.first_point_tuple,
                                 delta.second_point_tuple)
                                for delta in plot.delta_marker_list)
            plot_list.append((curve_tuple, tip_tuple, delta_tuple))
        tab_list.append((tab.name_str, tuple(plot_list)))
    marker_tuple = tuple((marker.name_str, marker.time_s)
                         for marker in workspace.marker_list)
    return tuple(tab_list), marker_tuple


def minimal_layout(tab_list: list, **entry_dict) -> dict:
    """Return the content of a small layout file.

    Inputs:
        tab_list: the "tabs" entry.
        entry_dict: other entries to set or replace.
    Outputs: the dict, as parse_layout_text returns it.
    """
    layout_dict = {"format": "plot_tool layout", "version": 1,
                   "shown_tab": 0, "time_range": None, "grid": False,
                   "panel_widths": None, "vertical_markers": [],
                   "synthetic_signals": [], "tabs": tab_list}
    layout_dict.update(entry_dict)
    return layout_dict


def one_plot_tab(curve_list: list, name_str: str = "Tab A",
                 data_tip_list=(), delta_marker_list=()) -> dict:
    """Return a tab entry with one plot.

    Inputs:
        curve_list: the curve entries of the plot.
        name_str: the tab name.
        data_tip_list: the data tip entries.
        delta_marker_list: the delta marker entries.
    Outputs: the tab entry.
    """
    return {"name": name_str,
            "plots": [{"curves": list(curve_list),
                       "data_tips": list(data_tip_list),
                       "delta_markers": list(delta_marker_list)}]}


def curve(signal_str: str, color_str: str = "#1f77b4",
          width_value=1) -> dict:
    """Return a curve entry.

    Inputs:
        signal_str: the signal name.
        color_str: the color.
        width_value: the width.
    Outputs: the entry.
    """
    return {"signal": signal_str, "color": color_str, "width": width_value}


class LayoutWriteTest(unittest.TestCase):
    """The content and the format of a written layout file."""

    def setUp(self) -> None:
        """Build the rich workspace and its layout file content.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = make_rich_workspace()
        self.layout_dict = build_layout_dict(
            self.workspace, self.workspace.tab_list[1].tab_id_i,
            (0.1, 7.123456789012345), True, (900, 300))
        self.text_str = layout_text(self.layout_dict)

    @covers("LLFR-00225")
    def test_content_lists_every_part_of_the_layout(self) -> None:
        """Tabs, shown tab, plots, curves, range, grid, markers, tips,
        delta markers and panel widths are all in the file.

        Inputs: none.
        Outputs: none.
        """
        layout_dict = json.loads(self.text_str)
        self.assertEqual([tab["name"] for tab in layout_dict["tabs"]],
                         ["Engine", "Empty"])
        self.assertEqual(layout_dict["shown_tab"], 1)
        first_plot_dict, second_plot_dict = layout_dict["tabs"][0]["plots"]
        self.assertEqual(layout_dict["tabs"][1]["plots"], [])
        self.assertEqual(first_plot_dict["curves"], [
            {"signal": "Speed", "color": PALETTE_COLOR_TUPLE[0], "width": 3},
            {"signal": "Torque", "color": "#123456", "width": 1}])
        self.assertEqual(second_plot_dict["curves"][0]["signal"], "Power")
        self.assertEqual(layout_dict["time_range"],
                         {"start": 0.1, "end": 7.123456789012345})
        self.assertIs(layout_dict["grid"], True)
        self.assertEqual(layout_dict["vertical_markers"], [
            {"name": "Marker 1", "time": 1.0},
            {"name": "Peak", "time": 4.25}])
        self.assertEqual(first_plot_dict["data_tips"], [
            {"signal": "Speed", "time": 1.5,
             "label_position": {"right_points": 20.25, "up_points": -7.5}},
            {"signal": "Torque", "time": 2.0, "label_position": None}])
        self.assertEqual(first_plot_dict["delta_markers"], [
            {"kind": "delta_x",
             "first_point": {"signal": "Speed", "time": 1.0},
             "second_point": {"signal": "Torque", "time": 3.0}},
            {"kind": "delta_y",
             "first_point": {"signal": "Speed", "time": 0.5},
             "second_point": {"signal": "Speed", "time": 2.5}}])
        self.assertEqual(layout_dict["panel_widths"],
                         {"plot_panel": 900, "signal_list_panel": 300})
        # LLFR-00225 item 10 (issue #110): the place of the synthetic
        # signals is there, empty.
        self.assertEqual(layout_dict["synthetic_signals"], [])

    @covers("LLFR-00226")
    def test_no_file_path_history_tool_or_search(self) -> None:
        """The file holds no data file name or path and no other state.

        Inputs: none.
        Outputs: none.
        """
        lower_text_str = self.text_str.lower()
        for word_str in ("path", "file_name", ".csv", "undo", "redo",
                         "history", "search", "plot_tool\"", "active"):
            with self.subTest(word=word_str):
                self.assertNotIn(word_str, lower_text_str)
        key_list = list(json.loads(self.text_str))
        self.assertFalse(any("tool" in key_str for key_str in key_list))

    @covers("LLFR-00227", "LLFR-00228")
    def test_json_utf8_indent_and_identification_first(self) -> None:
        """JSON in UTF-8 with 2-space indents; format and version first.

        Inputs: none.
        Outputs: none.
        """
        self.workspace.rename_tab(self.workspace.tab_list[1].tab_id_i,
                                  "Drehmoment üß")
        content_bytes = layout_bytes(build_layout_dict(
            self.workspace, -1, (0.0, 1.0), False, (1, 2)))
        text_str = content_bytes.decode("utf-8")
        self.assertIn("Drehmoment üß", text_str)
        line_list = text_str.splitlines()
        self.assertEqual(line_list[0], "{")
        self.assertEqual(line_list[1], '  "format": "plot_tool layout",')
        self.assertEqual(line_list[2], '  "version": 1,')
        self.assertEqual(list(json.loads(text_str))[:2],
                         ["format", "version"])
        # LLFR-00227: each value on its own line, indented by 2 spaces.
        for line_str in line_list[1:-1]:
            indent_i = len(line_str) - len(line_str.lstrip(" "))
            self.assertEqual(indent_i % 2, 0, line_str)
            self.assertLessEqual(line_str.count(":"), 1, line_str)
        self.assertIn('    {\n      "name": "Engine",', text_str)

    @covers("LLFR-00227")
    def test_times_are_read_back_exactly(self) -> None:
        """Every time is written with enough digits to read it back.

        Inputs: none.
        Outputs: none.
        """
        time_s = 0.1 + 0.2
        self.workspace.add_marker(time_s)
        text_str = layout_text(build_layout_dict(
            self.workspace, -1, (1.0 / 3.0, 2.0 / 3.0), False, ()))
        layout_dict = json.loads(text_str)
        self.assertEqual(layout_dict["vertical_markers"][-1]["time"], time_s)
        self.assertEqual(layout_dict["time_range"]["start"], 1.0 / 3.0)
        self.assertIn(repr(time_s), text_str)
        self.assertIsNone(layout_dict["panel_widths"])

    @covers("LLFR-00225", "LLFR-00227")
    def test_keys_are_english_words(self) -> None:
        """Every key is made of lower-case English words.

        Inputs: none.
        Outputs: none.
        """
        key_set = set()

        def collect(value) -> None:
            """Add the keys of every JSON object in value to key_set.

            Inputs:
                value: a JSON value.
            Outputs: none.
            """
            if isinstance(value, dict):
                key_set.update(value)
                for item in value.values():
                    collect(item)
            elif isinstance(value, list):
                for item in value:
                    collect(item)
        collect(json.loads(self.text_str))
        for key_str in key_set:
            with self.subTest(key=key_str):
                self.assertRegex(key_str, r"^[a-z]+(_[a-z]+)*$")
        for key_str in ("tabs", "plots", "signal", "width", "color"):
            self.assertIn(key_str, key_set)


class LayoutReadTest(unittest.TestCase):
    """Reading a layout file and refusing other files (LLFR-00236)."""

    @covers("LLFR-00236", "LLFR-00228")
    def test_round_trip_through_a_file(self) -> None:
        """A written file is read back as the same content.

        Inputs: none.
        Outputs: none.
        """
        layout_dict = build_layout_dict(make_rich_workspace(), -1,
                                        (0.0, 2.0), False, (10, 20))
        with tempfile.TemporaryDirectory() as folder_str:
            path_str = os.path.join(folder_str, "layout.json")
            with open(path_str, "wb") as output_file:
                output_file.write(layout_bytes(layout_dict))
            self.assertEqual(read_layout_file(path_str), layout_dict)

    @covers("LLFR-00236")
    def test_unreadable_file(self) -> None:
        """A missing file or a folder cannot be read.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as folder_str:
            for path_str in (os.path.join(folder_str, "missing.json"),
                             folder_str):
                with self.subTest(path=path_str):
                    with self.assertRaises(LayoutFileError) as context:
                        read_layout_file(path_str)
                    self.assertIn("could not be read as a layout file",
                                  str(context.exception))

    @covers("LLFR-00236")
    def test_not_utf8_and_not_json(self) -> None:
        """Binary data and broken JSON are refused with a reason.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as folder_str:
            for content_bytes, word_str in (
                    (b"\xff\xfe\x00\x01", "UTF-8"),
                    (b'{"format": "plot_tool layout", "version": 1',
                     "JSON"),
                    (b"", "JSON")):
                path_str = os.path.join(folder_str, "bad.json")
                with open(path_str, "wb") as output_file:
                    output_file.write(content_bytes)
                with self.subTest(content=content_bytes):
                    with self.assertRaises(LayoutFileError) as context:
                        read_layout_file(path_str)
                    self.assertIn(word_str, str(context.exception))
                    self.assertIn(path_str, str(context.exception))

    @covers("LLFR-00236", "LLFR-00228")
    def test_other_json_files_are_refused(self) -> None:
        """JSON without the right format and version is not a layout.

        Inputs: none.
        Outputs: none.
        """
        for text_str in ("[1, 2]", '"text"', "{}",
                         '{"format": "other", "version": 1}',
                         '{"format": "plot_tool layout"}',
                         '{"format": "plot_tool layout", "version": "1"}',
                         '{"format": "plot_tool layout", "version": true}',
                         '{"format": "plot_tool layout", "version": 0}',
                         '{"format": "plot_tool layout", "version": 2}'):
            with self.subTest(text=text_str):
                with self.assertRaises(LayoutFileError):
                    parse_layout_text(text_str, "x.json")
        self.assertEqual(parse_layout_text(
            '{"format": "plot_tool layout", "version": 1}')["version"], 1)
        # LLFR-00228: a hand-edited 1.0 is version 1; 2.0 is too new.
        parse_layout_text('{"format": "plot_tool layout", "version": 1.0}')
        with self.assertRaises(LayoutFileError) as context:
            parse_layout_text(
                '{"format": "plot_tool layout", "version": 2.0}')
        self.assertIn("version 2", str(context.exception))
        with self.assertRaises(LayoutFileError):
            parse_layout_text(
                '{"format": "plot_tool layout", "version": 1.5}')

    @covers("LLFR-00236")
    def test_byte_order_mark_is_accepted(self) -> None:
        """A UTF-8 file saved with a byte order mark is still read.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as folder_str:
            path_str = os.path.join(folder_str, "bom.json")
            with open(path_str, "wb") as output_file:
                output_file.write(
                    b'\xef\xbb\xbf{"format": "plot_tool layout", '
                    b'"version": 1}')
            self.assertEqual(read_layout_file(path_str)["format"],
                             "plot_tool layout")

    @covers("LLFR-00219")
    def test_json_suffix_only_without_extension(self) -> None:
        """".json" is added only to a name with no extension.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(ensure_layout_suffix("/a/b/layout"),
                         "/a/b/layout.json")
        self.assertEqual(ensure_layout_suffix("/a/b.c/layout"),
                         "/a/b.c/layout.json")
        self.assertEqual(ensure_layout_suffix("/a/layout.json"),
                         "/a/layout.json")
        self.assertEqual(ensure_layout_suffix("/a/layout.txt"),
                         "/a/layout.txt")
        self.assertEqual(ensure_layout_suffix("/a/.hidden"),
                         "/a/.hidden.json")


class LayoutRebuildTestCase(unittest.TestCase):
    """Shared helpers: a workspace after a data file was opened."""

    def setUp(self) -> None:
        """Create an empty workspace and the signals of a data file.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace(random.Random(1))
        self.signal_dict = make_signal_dict()

    def rebuild(self, layout_dict: dict, signal_dict: dict = None):
        """Rebuild a layout in the workspace.

        Inputs:
            layout_dict: the content of the layout file.
            signal_dict: the signals of the data file; self.signal_dict
                when None.
        Outputs: the LayoutResult.
        """
        if signal_dict is None:
            signal_dict = self.signal_dict
        return rebuild_layout(self.workspace, layout_dict, signal_dict,
                              signal_dict["Time"])

    def only_plot(self):
        """Return the only plot of the workspace.

        Inputs: none.
        Outputs: the Plot.
        """
        plot_list = [plot for tab in self.workspace.tab_list
                     for plot in tab.plot_list]
        self.assertEqual(len(plot_list), 1)
        return plot_list[0]


class LayoutRoundTripTest(LayoutRebuildTestCase):
    """A saved layout is rebuilt as saved (LLFR-00230)."""

    @covers("LLFR-00230", "LLFR-00225", "LLFR-00229", "LLFR-00237",
            "LLFR-00231")
    def test_round_trip_rebuilds_everything(self) -> None:
        """Tabs, plots, curves, tips, delta and vertical markers, range,
        grid and widths come back as saved, with nothing to report.

        Inputs: none.
        Outputs: none.
        """
        saved_workspace = make_rich_workspace()
        text_str = layout_text(build_layout_dict(
            saved_workspace, -1, (0.5, 7.25), True, (800, 250)))
        result = self.rebuild(parse_layout_text(text_str))
        self.assertTrue(result.report.is_empty(), result.report.text())
        self.assertEqual(result.report.text(), "")
        # LLFR-00231: the saved tab "Empty" holds no plot, so it is not
        # created, and this is not reported.
        saved_tab = saved_workspace.tab_list[1]
        saved_workspace.delete_tab(saved_tab.tab_id_i)
        self.assertEqual(workspace_content(self.workspace),
                         workspace_content(saved_workspace))
        self.assertEqual(result.time_range_tuple, (0.5, 7.25))
        self.assertIs(result.grid_shown_b, True)
        self.assertEqual(result.panel_width_tuple, (800, 250))
        self.assertTrue(result.tabs_replaced_b)
        self.assertEqual(result.first_tab_id_i,
                         self.workspace.tab_list[0].tab_id_i)

    @covers("LLFR-00230", "LLFR-00234")
    def test_whole_range_and_missing_widths(self) -> None:
        """The whole range is given back as (); no widths stay ().

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(minimal_layout(
            [one_plot_tab([curve("Speed")])],
            time_range={"start": 0.0, "end": 10.0}))
        self.assertEqual(result.time_range_tuple, ())
        self.assertEqual(result.panel_width_tuple, ())
        self.assertIs(result.grid_shown_b, False)
        self.assertTrue(result.report.is_empty())


class LayoutTabsTest(LayoutRebuildTestCase):
    """Where the tabs of the file go (LLFR-00229)."""

    @covers("LLFR-00229")
    def test_tabs_replace_current_tabs_without_plots(self) -> None:
        """With no plot in any tab, the file's tabs replace them.

        Inputs: none.
        Outputs: none.
        """
        self.workspace.add_tab()
        result = self.rebuild(minimal_layout(
            [one_plot_tab([curve("Speed")], "Tab 1"),
             {"name": "Second", "plots": []},
             one_plot_tab([curve("Torque")], "Third")]))
        self.assertTrue(result.tabs_replaced_b)
        # LLFR-00231: "Second" holds no plot and is not created.
        self.assertEqual([tab.name_str for tab in self.workspace.tab_list],
                         ["Tab 1", "Third"])
        self.assertEqual(result.first_tab_id_i,
                         self.workspace.tab_list[0].tab_id_i)
        self.assertTrue(result.report.is_empty())

    @covers("LLFR-00235", "LLFR-00237", "LLFR-00229", "LLFR-00210")
    def test_tabs_added_after_tabs_with_plots(self) -> None:
        """Current tabs with a plot are kept; the file's tabs follow.

        Inputs: none.
        Outputs: none.
        """
        first_tab = self.workspace.tab_list[0]
        plot = self.workspace.add_plot(first_tab.tab_id_i)
        plot.add_curve("Power")
        plot.add_pinned_tip("Power", 1.0, 3.0)
        before_tuple = workspace_content(self.workspace)
        result = self.rebuild(minimal_layout(
            [one_plot_tab([curve("Speed")], "Tab 1"),
             one_plot_tab([curve("Torque")], "Other")]))
        self.assertFalse(result.tabs_replaced_b)
        self.assertEqual(workspace_content(self.workspace)[0][0],
                         before_tuple[0][0])
        self.assertEqual([tab.name_str for tab in self.workspace.tab_list],
                         ["Tab 1", "Tab 2", "Other"])
        self.assertEqual(result.first_tab_id_i,
                         self.workspace.tab_list[1].tab_id_i)
        # LLFR-00235, LLFR-00237: the name "Tab 1" of the kept tab was
        # replaced without a report.
        self.assertTrue(result.report.is_empty(), result.report.text())

    @covers("LLFR-00235", "LLFR-00237", "LLFR-00229", "LLFR-00212")
    def test_clash_with_kept_tab_cascades_silently(self) -> None:
        """File tabs "Tab 1" and "Tab 2" after a kept "Tab 1" become
        "Tab 2" and "Tab 3", with nothing to report.

        Inputs: none.
        Outputs: none.
        """
        first_tab = self.workspace.tab_list[0]
        self.workspace.add_plot(first_tab.tab_id_i).add_curve("Power")
        result = self.rebuild(minimal_layout(
            [one_plot_tab([curve("Speed")], "Tab 1"),
             one_plot_tab([curve("Torque")], "Tab 2")]))
        self.assertEqual([tab.name_str for tab in self.workspace.tab_list],
                         ["Tab 1", "Tab 2", "Tab 3"])
        self.assertTrue(result.report.is_empty(), result.report.text())
        self.assertEqual(result.report.text(), "")

    @covers("LLFR-00235", "LLFR-00237", "LLFR-00229", "LLFR-00210",
            "LLFR-00212")
    def test_empty_duplicate_and_wrong_type_tab_names(self) -> None:
        """Empty, non-text or repeated (within the file) tab names get
        default names and are reported; a valid name that a tab of this
        load already has is renamed silently.

        Inputs: none.
        Outputs: none.
        """
        plot_list = [{"curves": [curve("Speed")]}]
        result = self.rebuild(minimal_layout([
            {"name": "  ", "plots": plot_list},
            {"name": "Tab 2", "plots": plot_list},
            {"name": "Skipped", "plots": []},
            {"name": "Tab 2", "plots": plot_list},
            {"name": 5, "plots": plot_list},
            {"plots": plot_list}, "not a tab", {"name": [], "plots": []}]))
        name_list = [tab.name_str for tab in self.workspace.tab_list]
        self.assertEqual(len(name_list), 5)
        self.assertEqual(len(set(name_list)), 5)
        # LLFR-00210: "Tab 1" of the replaced tab is used up; the empty
        # name became "Tab 2", so the file's first "Tab 2" is silently
        # "Tab 3" and its repeat is "Tab 4". LLFR-00231: the tabs left
        # with no plot are not created and use up no number.
        self.assertEqual(name_list, ["Tab 2", "Tab 3", "Tab 4", "Tab 5",
                                     "Tab 6"])
        replaced_list = result.report.replaced_line_list
        self.assertEqual(len(replaced_list), 4)
        self.assertIn("is empty", replaced_list[0])
        self.assertIn("earlier tab of the file", replaced_list[1])
        self.assertIn('"Tab 4"', replaced_list[1])
        self.assertIn("not a text", replaced_list[2])
        self.assertIn("not a text", replaced_list[3])
        self.assertNotIn("Skipped", result.report.text())

    @covers("LLFR-00235", "LLFR-00237", "LLFR-00229")
    def test_repeat_in_file_found_after_a_silent_rename(self) -> None:
        """A valid name renamed silently still counts as met in the file,
        so its repeat later in the file is reported.

        Inputs: none.
        Outputs: none.
        """
        first_tab = self.workspace.tab_list[0]
        self.workspace.add_plot(first_tab.tab_id_i).add_curve("Power")
        plot_list = [{"curves": [curve("Speed")]}]
        result = self.rebuild(minimal_layout([
            {"name": "Tab 1", "plots": plot_list},
            {"name": " Tab 1 ", "plots": plot_list},
            {"name": "Own", "plots": plot_list}]))
        self.assertEqual([tab.name_str for tab in self.workspace.tab_list],
                         ["Tab 1", "Tab 2", "Tab 3", "Own"])
        self.assertEqual(len(result.report.replaced_line_list), 1)
        self.assertIn("earlier tab of the file",
                      result.report.replaced_line_list[0])

    @covers("LLFR-00231", "LLFR-00229")
    def test_tabs_entry_that_is_not_a_list(self) -> None:
        """A "tabs" entry that is not a list adds no tab and is reported.

        Inputs: none.
        Outputs: none.
        """
        before_tuple = workspace_content(self.workspace)
        result = self.rebuild(minimal_layout("nothing"))
        self.assertEqual(workspace_content(self.workspace), before_tuple)
        self.assertEqual(result.first_tab_id_i, -1)
        self.assertFalse(result.tabs_replaced_b)
        self.assertIn("Tabs", result.report.not_rebuilt_line_list[0])


class LayoutMissingSignalTest(LayoutRebuildTestCase):
    """Signals that are not in the data file (LLFR-00231)."""

    @covers("LLFR-00231", "LLFR-00237")
    def test_missing_signals_no_curve_no_empty_plot_every_tab(self) -> None:
        """Missing signals draw nothing, empty plots and tabs left with
        no plot are not created, and each missing name is listed once.

        Inputs: none.
        Outputs: none.
        """
        layout_dict = minimal_layout([
            {"name": "Mixed", "plots": [
                {"curves": [curve("Gone"), curve("Speed", "#000000")]},
                {"curves": [curve("Gone"), curve("Lost")],
                 "data_tips": [{"signal": "Gone", "time": 1.0,
                                "label_position": None}]}]},
            {"name": "Nothing left", "plots": [
                {"curves": [curve("Lost")]}]}])
        result = self.rebuild(layout_dict)
        # LLFR-00231: "Nothing left" has no plot left: not created.
        self.assertEqual([tab.name_str for tab in self.workspace.tab_list],
                         ["Mixed"])
        self.assertEqual(len(self.workspace.tab_list[0].plot_list), 1)
        plot = self.workspace.tab_list[0].plot_list[0]
        self.assertEqual([item.signal_name_str for item in plot.curve_list],
                         ["Speed"])
        self.assertEqual(plot.curve_list[0].color_str, "#000000")
        self.assertEqual(result.report.missing_signal_list, ["Gone", "Lost"])
        report_text_str = result.report.text()
        self.assertEqual(report_text_str.count("  - Gone\n"), 1)
        self.assertEqual(report_text_str.count("  - Lost\n"), 1)
        self.assertIn("Data tip at 1 s", report_text_str)
        self.assertIn("not created", report_text_str)
        # LLFR-00237: the plots of the tab not created are reported, but
        # not the tab itself.
        self.assertIn("Plot 1 of tab \"Nothing left\": not created",
                      report_text_str)
        self.assertNotIn("Tab \"Nothing left\"", report_text_str)

    @covers("LLFR-00231", "LLFR-00056")
    def test_bad_curve_entries_are_skipped(self) -> None:
        """Curves without a name or drawn twice are skipped and reported.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(minimal_layout([one_plot_tab([
            "Speed", {"color": "#000000"}, {"signal": 3},
            curve("Speed"), curve("Speed", "#000000")])]))
        plot = self.only_plot()
        self.assertEqual([item.signal_name_str for item in plot.curve_list],
                         ["Speed"])
        self.assertEqual(len(result.report.not_rebuilt_line_list), 4)


class LayoutPointTest(LayoutRebuildTestCase):
    """Data tips and delta markers (LLFR-00232)."""

    def tip_layout(self, tip_time_s, signal_str: str = "Speed",
                   curve_list=None) -> dict:
        """Return a layout with one data tip.

        Inputs:
            tip_time_s: the saved time of the tip.
            signal_str: the signal of the tip.
            curve_list: the curves of the plot; Speed when None.
        Outputs: the layout content.
        """
        if curve_list is None:
            curve_list = [curve("Speed")]
        return minimal_layout([one_plot_tab(curve_list, data_tip_list=[
            {"signal": signal_str, "time": tip_time_s,
             "label_position": {"right_points": 5.0, "up_points": 6.0}}])])

    @covers("LLFR-00232")
    def test_tip_within_one_microsecond_snaps_to_sample(self) -> None:
        """A tip 0.9 us from a sample is placed on that sample.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(self.tip_layout(2.0 + 0.9e-6))
        tip = self.only_plot().pinned_tip_list[0]
        self.assertEqual(tip.time_s, 2.0)
        self.assertEqual(tip.value_f, 2.0)
        self.assertEqual(tip.label_offset_tuple, (5.0, 6.0))
        self.assertTrue(result.report.is_empty())

    @covers("LLFR-00232", "LLFR-00237")
    def test_tip_further_than_one_microsecond_is_not_rebuilt(self) -> None:
        """A tip 2 us from every sample is reported with its time.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(self.tip_layout(2.0 + 2e-6))
        self.assertEqual(self.only_plot().pinned_tip_list, [])
        self.assertIn("Data tip at 2.000002 s",
                      result.report.not_rebuilt_line_list[0])
        self.assertIn("1 microsecond", result.report.not_rebuilt_line_list[0])

    @covers("LLFR-00232", "LLFR-00237")
    def test_tip_on_a_signal_not_drawn_in_its_plot(self) -> None:
        """A tip on a signal of the file not drawn in the plot is lost.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(self.tip_layout(2.0, "Torque"))
        self.assertEqual(self.only_plot().pinned_tip_list, [])
        self.assertIn("not drawn in its plot",
                      result.report.not_rebuilt_line_list[0])
        self.assertEqual(result.report.missing_signal_list, [])

    @covers("LLFR-00232", "LLFR-00235")
    def test_tip_with_wrong_types(self) -> None:
        """Tips with a text time, no signal or a bad label position.

        Inputs: none.
        Outputs: none.
        """
        layout_dict = minimal_layout([one_plot_tab(
            [curve("Speed")], data_tip_list=[
                {"signal": "Speed", "time": "2.0"},
                {"time": 2.0}, 7,
                {"signal": "Speed", "time": 3.0,
                 "label_position": {"right_points": "x"}},
                {"signal": "Speed", "time": 4.0, "label_position": [1, 2]},
                {"signal": "Speed", "time": 5.0}])])
        result = self.rebuild(layout_dict)
        tip_list = self.only_plot().pinned_tip_list
        self.assertEqual([tip.time_s for tip in tip_list], [3.0, 4.0, 5.0])
        self.assertTrue(all(tip.label_offset_tuple == () for tip in tip_list))
        self.assertEqual(len(result.report.not_rebuilt_line_list), 3)
        self.assertEqual(len(result.report.replaced_line_list), 2)
        self.assertIn("an unreadable time",
                      result.report.not_rebuilt_line_list[0])

    @covers("LLFR-00232", "LLFR-00230")
    def test_delta_markers_snap_and_check_both_points(self) -> None:
        """Delta markers are placed on samples only when both points fit.

        Inputs: none.
        Outputs: none.
        """
        layout_dict = minimal_layout([one_plot_tab(
            [curve("Speed"), curve("Torque", "#000000")],
            delta_marker_list=[
                {"kind": "delta_x",
                 "first_point": {"signal": "Speed", "time": 1.0000004},
                 "second_point": {"signal": "Torque", "time": 3.0}},
                {"kind": "delta_y",
                 "first_point": {"signal": "Speed", "time": 1.0},
                 "second_point": {"signal": "Power", "time": 3.0}},
                {"kind": "delta_y",
                 "first_point": {"signal": "Speed", "time": 1.0},
                 "second_point": {"signal": "Speed", "time": 3.05}},
                {"kind": "delta_z",
                 "first_point": {"signal": "Speed", "time": 1.0},
                 "second_point": {"signal": "Speed", "time": 3.0}},
                {"kind": "delta_x", "first_point": "x"}])])
        result = self.rebuild(layout_dict)
        delta_list = self.only_plot().delta_marker_list
        self.assertEqual(len(delta_list), 1)
        self.assertEqual(delta_list[0].kind_str, DELTA_X_KIND_STR)
        self.assertEqual(delta_list[0].first_point_tuple,
                         ("Speed", 1.0, 1.0))
        self.assertEqual(delta_list[0].second_point_tuple,
                         ("Torque", 3.0, 6.0))
        not_rebuilt_list = result.report.not_rebuilt_line_list
        self.assertEqual(len(not_rebuilt_list), 4)
        self.assertIn("Delta Y marker between 1 s and 3 s",
                      not_rebuilt_list[0])
        self.assertIn("not drawn in its plot", not_rebuilt_list[0])
        self.assertIn("1 microsecond", not_rebuilt_list[1])
        self.assertIn("kind", not_rebuilt_list[2])
        self.assertIn("an unreadable time", not_rebuilt_list[3])


class LayoutMarkerTest(LayoutRebuildTestCase):
    """Vertical markers of the file (LLFR-00233)."""

    @covers("LLFR-00233", "LLFR-00230", "LLFR-00205", "LLFR-00111")
    def test_markers_added_inside_the_file_range(self) -> None:
        """Markers inside the range are added to the current ones.

        Inputs: none.
        Outputs: none.
        """
        tab = self.workspace.tab_list[0]
        self.workspace.add_plot(tab.tab_id_i).add_curve("Speed")
        self.workspace.add_marker(1.0)
        result = self.rebuild(minimal_layout(
            [one_plot_tab([curve("Speed")])], vertical_markers=[
                {"name": "Start", "time": 0.0},
                {"name": "Marker 1", "time": 10.0},
                {"name": "Marker 7", "time": 5.0},
                {"name": "Late", "time": 10.5},
                {"name": "Text", "time": "3"},
                {"name": "", "time": 4.0}]))
        name_time_list = [(marker.name_str, marker.time_s)
                          for marker in self.workspace.marker_list]
        self.assertEqual(name_time_list[:4], [
            ("Marker 1", 1.0), ("Start", 0.0), ("Marker 1", 10.0),
            ("Marker 7", 5.0)])
        # LLFR-00085, LLFR-00111: "Marker 7" used up the numbers up to 7.
        self.assertEqual(name_time_list[4], ("Marker 8", 4.0))
        self.assertEqual(self.workspace.add_marker(2.0).name_str, "Marker 9")
        not_rebuilt_list = result.report.not_rebuilt_line_list
        self.assertEqual(len(not_rebuilt_list), 2)
        self.assertIn('"Late" at 10.5 s', not_rebuilt_list[0])
        self.assertIn("outside the time range", not_rebuilt_list[0])
        self.assertIn("0 s to 10 s", not_rebuilt_list[0])
        self.assertIn("not a number", not_rebuilt_list[1])
        self.assertIn('"Marker 8"', result.report.replaced_line_list[0])

    @covers("LLFR-00233", "LLFR-00205", "LLFR-00231")
    def test_markers_need_a_plot(self) -> None:
        """With no plot rebuilt, no marker is kept, and it is reported.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(minimal_layout(
            [one_plot_tab([curve("Gone")])],
            vertical_markers=[{"name": "M", "time": 1.0}]))
        self.assertEqual(self.workspace.marker_list, [])
        self.assertIn("no plot", result.report.not_rebuilt_line_list[-1])


class LayoutRangeTest(LayoutRebuildTestCase):
    """The time range of the file (LLFR-00234)."""

    @covers("LLFR-00234", "LLFR-00119", "LLFR-00237")
    def test_range_limited_to_the_file(self) -> None:
        """A range that sticks out is limited and the change reported.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(minimal_layout(
            [one_plot_tab([curve("Speed")])],
            time_range={"start": -5.0, "end": 4.0}))
        self.assertEqual(result.time_range_tuple, (0.0, 4.0))
        self.assertIn("limited to 0 s to 4 s",
                      result.report.time_range_line_list[0])

    @covers("LLFR-00234", "LLFR-00237")
    def test_range_without_overlap_shows_the_whole_range(self) -> None:
        """A range outside the file shows the whole range, reported.

        Inputs: none.
        Outputs: none.
        """
        for range_value in ({"start": 20.0, "end": 30.0},
                            {"start": -3.0, "end": 0.0}):
            with self.subTest(range=range_value):
                self.setUp()
                result = self.rebuild(minimal_layout(
                    [one_plot_tab([curve("Speed")])],
                    time_range=range_value))
                self.assertEqual(result.time_range_tuple, ())
                self.assertIn("whole time range",
                              result.report.time_range_line_list[0])

    @covers("LLFR-00234", "LLFR-00235")
    def test_unusable_range(self) -> None:
        """A range of text, reversed or incomplete shows the whole range.

        Inputs: none.
        Outputs: none.
        """
        for range_value in ("all", {"start": "0", "end": 2.0},
                            {"start": 3.0, "end": 1.0}, {"end": 1.0}, []):
            with self.subTest(range=range_value):
                self.setUp()
                result = self.rebuild(minimal_layout(
                    [one_plot_tab([curve("Speed")])],
                    time_range=range_value))
                self.assertEqual(result.time_range_tuple, ())
                self.assertEqual(len(result.report.time_range_line_list), 1)


class LayoutValueTest(LayoutRebuildTestCase):
    """Values that cannot be used are replaced (LLFR-00235)."""

    @covers("LLFR-00235", "LLFR-00052")
    def test_bad_widths_become_width_one(self) -> None:
        """Widths 0, 6, 2.5, "3", true and missing become width 1.

        Inputs: none.
        Outputs: none.
        """
        width_list = [0, 6, 2.5, "3", True, None, 5]
        signal_list = [f"s{index_i}" for index_i in range(len(width_list))]
        signal_dict = make_signal_dict(signal_list)
        curve_list = [curve(signal_str, PALETTE_COLOR_TUPLE[index_i],
                            width_value)
                      for index_i, (signal_str, width_value) in enumerate(
                          zip(signal_list, width_list))]
        result = self.rebuild(minimal_layout([one_plot_tab(curve_list)]),
                              signal_dict)
        self.assertEqual([item.width_i for item in self.only_plot()
                          .curve_list], [1, 1, 1, 1, 1, 1, 5])
        self.assertEqual(len(result.report.replaced_line_list), 6)
        self.assertIn("replaced by 1", result.report.replaced_line_list[0])

    @covers("LLFR-00235", "LLFR-00033", "LLFR-00034", "LLFR-00083")
    def test_bad_and_duplicate_colors_get_the_next_color(self) -> None:
        """Invalid, duplicate or marker-like colors get the plot's next
        color, which is never one of the plot's colors.

        Inputs: none.
        Outputs: none.
        """
        signal_list = [f"s{index_i}" for index_i in range(12)]
        signal_dict = make_signal_dict(signal_list)
        color_list = ["#000000", "#1F77B4", "#2ca02c", "#d62728",
                      "#000000", "red", 12, MARKER_COLOR_STR, "#1f77b4",
                      None, "#abcdeg", "#123456"]
        curve_list = [{"signal": signal_str, "color": color_value,
                       "width": 1}
                      for signal_str, color_value in zip(signal_list,
                                                         color_list)]
        result = self.rebuild(minimal_layout([one_plot_tab(curve_list)]),
                              signal_dict)
        plot = self.only_plot()
        used_color_list = [item.color_str for item in plot.curve_list]
        self.assertEqual(len(set(used_color_list)), 12)
        self.assertEqual(used_color_list[:4], [
            "#000000", "#1f77b4", "#2ca02c", "#d62728"])
        self.assertEqual(used_color_list[11], "#123456")
        # LLFR-00033: the first replaced color is the next palette color
        # not yet used in the plot.
        self.assertEqual(used_color_list[4], PALETTE_COLOR_TUPLE[4])
        self.assertEqual(len(result.report.replaced_line_list), 7)
        # HLFR-00020: a curve added later still gets an unused color.
        plot.add_curve("Time")
        self.assertEqual(len({item.color_str for item in plot.curve_list}),
                         13)

    @covers("LLFR-00235", "HLFR-00018", "LLFR-00237")
    def test_plots_beyond_five_are_not_created(self) -> None:
        """The 6th plot of a tab is not created; its items are reported.

        Inputs: none.
        Outputs: none.
        """
        plot_list = [{"curves": [curve("Speed")]} for _ in range(5)]
        plot_list.insert(1, {"curves": [curve("Gone")]})
        plot_list.append({"curves": [curve("Torque")], "data_tips": [
            {"signal": "Torque", "time": 1.0}], "delta_markers": [
            {"kind": "delta_x",
             "first_point": {"signal": "Torque", "time": 1.0},
             "second_point": {"signal": "Torque", "time": 2.0}}]})
        result = self.rebuild(minimal_layout(
            [{"name": "Full", "plots": plot_list}]))
        self.assertEqual(len(self.workspace.tab_list[0].plot_list), 5)
        report_list = result.report.not_rebuilt_line_list
        self.assertTrue(any("plot 7" in line_str.lower()
                            and "at most 5" in line_str
                            for line_str in report_list))
        self.assertTrue(any(line_str.startswith("Data tip at 1 s")
                            and "tab is full" in line_str
                            for line_str in report_list))
        self.assertTrue(any(line_str.startswith(
            "Delta X marker between 1 s and 2 s") for line_str in report_list))

    @covers("LLFR-00235", "LLFR-00230")
    def test_bad_grid_and_panel_widths(self) -> None:
        """A grid that is not true or false and bad widths are reported;
        missing entries leave both unchanged without a report.

        Inputs: none.
        Outputs: none.
        """
        layout_dict = minimal_layout([])
        del layout_dict["grid"]
        del layout_dict["panel_widths"]
        result = self.rebuild(layout_dict)
        self.assertIsNone(result.grid_shown_b)
        self.assertEqual(result.panel_width_tuple, ())
        self.assertTrue(result.report.is_empty(), result.report.text())
        for grid_value, widths_value in (
                ("yes", {"plot_panel": 0, "signal_list_panel": 3}),
                (None, {"plot_panel": 2.5, "signal_list_panel": 3}),
                (1, [100, 200])):
            with self.subTest(grid=grid_value, widths=widths_value):
                self.setUp()
                result = self.rebuild(minimal_layout(
                    [], grid=grid_value, panel_widths=widths_value))
                self.assertIsNone(result.grid_shown_b)
                self.assertEqual(result.panel_width_tuple, ())
                self.assertEqual(len(result.report.replaced_line_list), 2)

    @covers("LLFR-00235", "LLFR-00231")
    def test_never_raises_on_wrong_types(self) -> None:
        """A layout full of wrong types is rebuilt without an exception.

        Inputs: none.
        Outputs: none.
        """
        for layout_dict in (
                minimal_layout([{"name": "A", "plots": "x"}]),
                minimal_layout([{"name": "A", "plots": [None, 3, []]}]),
                minimal_layout([{"name": "A", "plots": [{"curves": "x"}]}]),
                minimal_layout([one_plot_tab([curve("Speed")],
                                             data_tip_list=["x"],
                                             delta_marker_list=[None])]),
                minimal_layout([], vertical_markers="x"),
                minimal_layout([], vertical_markers=[None, [], {"time": 1}]),
                minimal_layout([], time_range={"start": 1e400, "end": 2}),
                {"format": "plot_tool layout", "version": 1}):
            with self.subTest(layout=layout_dict):
                self.setUp()
                result = self.rebuild(layout_dict)
                self.assertGreaterEqual(len(self.workspace.tab_list), 1)
                self.assertIsInstance(result.report.text(), str)


class LayoutReportTest(unittest.TestCase):
    """The text of the load report (LLFR-00237)."""

    @covers("LLFR-00237")
    def test_report_sections_and_order(self) -> None:
        """Each kind of entry has its heading, in the required order.

        Inputs: none.
        Outputs: none.
        """
        report = layout_file.LayoutReport()
        self.assertTrue(report.is_empty())
        report.add_replaced("Width 9 replaced by 1.")
        report.add_time_range("Range limited.")
        report.add_not_rebuilt("Data tip at 1 s: reason.")
        report.add_missing_signal("Speed")
        report.add_missing_signal("Speed")
        report.add_synthetic_signal("integral_Speed: reason.")
        self.assertFalse(report.is_empty())
        text_str = report.text()
        heading_list = [layout_file.SYNTHETIC_HEADING_STR,
                        layout_file.MISSING_HEADING_STR,
                        layout_file.NOT_REBUILT_HEADING_STR,
                        layout_file.TIME_RANGE_HEADING_STR,
                        layout_file.REPLACED_HEADING_STR]
        index_list = [text_str.index(heading_str)
                      for heading_str in heading_list]
        self.assertEqual(index_list, sorted(index_list))
        self.assertEqual(text_str.count("Speed"), 2)
        self.assertIn("  - Speed\n", text_str)

    @covers("LLFR-00237", "LLFR-00230")
    def test_synthetic_signal_hook(self) -> None:
        """The synthetic signal entries reach the builder, before tabs.

        Inputs: none.
        Outputs: none.
        """
        call_list = []
        workspace = Workspace(random.Random(1))
        signal_dict = make_signal_dict()
        entry_list = [{"name": "integral_Speed"}]

        def builder(synthetic_entry_list: list, report) -> None:
            """Record the call and report one signal not created.

            Inputs:
                synthetic_entry_list: the entries of the file.
                report: the LayoutReport.
            Outputs: none.
            """
            call_list.append((list(synthetic_entry_list),
                              len(workspace.tab_list[0].plot_list)))
            report.add_synthetic_signal("integral_Speed: not created.")
        result = rebuild_layout(workspace, minimal_layout(
            [one_plot_tab([curve("Speed")])],
            synthetic_signals=entry_list), signal_dict, signal_dict["Time"],
            builder)
        self.assertEqual(call_list, [(entry_list, 0)])
        self.assertIn("integral_Speed", result.report.text())


if __name__ == "__main__":
    unittest.main()
