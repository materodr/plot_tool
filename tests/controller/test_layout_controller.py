"""Tests for the layout controller with a fake view (issue #107).

The Save layout and Load layout flows run with a real Workspace,
PlotController and LayoutController; the fake view answers the dialogs
and records the boxes. Files are written to a temporary folder. No Qt
is needed.
"""

import json
import os
import random
import tempfile
import unittest

import numpy as np

from tests.support import covers

from controller.layout_controller import LayoutController
from controller.plot_controller import PlotController
from controller.plot_tools import DELTA_X_TOOL_STR, MARKER_TOOL_STR
from model.layout_file import LAYOUT_FORMAT_STR
from model.signal_file import SignalFile
from model.workspace import Workspace
from tests.controller.test_plot_controller import (
    FakeFileController, FakePlotView)


class FakeLayoutView(FakePlotView):
    """The plot-panel fake view plus the layout facade.

    Attributes:
        layout_handler_tuple: (save handler, load handler).
        layout_buttons_enabled_b: last value given to
            set_layout_buttons_enabled.
        save_answer_list: paths returned, in order, by the save dialog
            ("" stands for a cancelled dialog).
        load_answer_list: paths returned, in order, by the load dialog.
        dialog_folder_list: (dialog kind, start folder) of every dialog.
        replace_answer_b: answer of ask_replace_existing_file.
        replace_question_list: paths asked about.
        save_error_list, load_error_list, report_list: texts of the boxes
            shown.
        write_failure_str: when not "", save_layout_bytes fails with it.
        panel_widths_tuple: the panel widths of the window.
        finished_list: names of the buttons returned to normal.
    """

    def __init__(self) -> None:
        """Start with no answers and no boxes.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        self.layout_handler_tuple = ()
        self.layout_buttons_enabled_b = None
        self.save_answer_list = []
        self.load_answer_list = []
        self.dialog_folder_list = []
        self.replace_answer_b = True
        self.replace_question_list = []
        self.save_error_list = []
        self.load_error_list = []
        self.report_list = []
        self.write_failure_str = ""
        self.panel_widths_tuple = (900, 300)
        self.finished_list = []

    def set_layout_handlers(self, save_handler, load_handler) -> None:
        """Record the handlers of the two layout buttons.

        Inputs:
            save_handler: run by Save layout.
            load_handler: run by Load layout.
        Outputs: none.
        """
        self.layout_handler_tuple = (save_handler, load_handler)

    def set_layout_buttons_enabled(self, enabled_b: bool) -> None:
        """Record whether the layout buttons are enabled.

        Inputs:
            enabled_b: True when they are enabled.
        Outputs: none.
        """
        self.layout_buttons_enabled_b = bool(enabled_b)

    def ask_layout_save_path(self, start_folder_str: str) -> str:
        """Answer the save dialog with the next prepared path.

        Inputs:
            start_folder_str: the folder the dialog would show.
        Outputs: the next answer, "" when none is left.
        """
        self.dialog_folder_list.append(("save", start_folder_str))
        return self.save_answer_list.pop(0) if self.save_answer_list else ""

    def ask_layout_load_path(self, start_folder_str: str) -> str:
        """Answer the load dialog with the next prepared path.

        Inputs:
            start_folder_str: the folder the dialog would show.
        Outputs: the next answer, "" when none is left.
        """
        self.dialog_folder_list.append(("load", start_folder_str))
        return self.load_answer_list.pop(0) if self.load_answer_list else ""

    def ask_replace_existing_file(self, path_str: str) -> bool:
        """Answer the replace question.

        Inputs:
            path_str: the existing file.
        Outputs: replace_answer_b.
        """
        self.replace_question_list.append(path_str)
        return self.replace_answer_b

    def save_layout_bytes(self, path_str: str,
                          content_bytes: bytes) -> tuple:
        """Write the bytes, or fail when write_failure_str is set.

        Inputs:
            path_str: the target path.
            content_bytes: the content.
        Outputs: (saved_b, reason_str).
        """
        if self.write_failure_str:
            return (False, self.write_failure_str)
        with open(path_str, "wb") as output_file:
            output_file.write(content_bytes)
        return (True, "")

    def panel_width_tuple(self) -> tuple:
        """Return the panel widths.

        Inputs: none.
        Outputs: (plot panel width, signal list panel width).
        """
        return self.panel_widths_tuple

    def set_panel_widths(self, plot_width_i: int, list_width_i: int) -> None:
        """Set the panel widths.

        Inputs:
            plot_width_i: width of the plot panel.
            list_width_i: width of the signal list panel.
        Outputs: none.
        """
        self.panel_widths_tuple = (plot_width_i, list_width_i)

    def show_layout_save_error(self, reason_str: str) -> None:
        """Record the save error box.

        Inputs:
            reason_str: why the file was not written.
        Outputs: none.
        """
        self.save_error_list.append(reason_str)

    def show_layout_load_error(self, message_str: str) -> None:
        """Record the load error box.

        Inputs:
            message_str: the text of the box.
        Outputs: none.
        """
        self.load_error_list.append(message_str)

    def show_layout_report(self, report_text_str: str) -> None:
        """Record the load report box.

        Inputs:
            report_text_str: the text of the box.
        Outputs: none.
        """
        self.report_list.append(report_text_str)

    def finish_save_layout_button(self) -> None:
        """Record that the Save layout button returned to normal.

        Inputs: none.
        Outputs: none.
        """
        self.finished_list.append("save")

    def finish_load_layout_button(self) -> None:
        """Record that the Load layout button returned to normal.

        Inputs: none.
        Outputs: none.
        """
        self.finished_list.append("load")


def make_data_file(signal_name_list=("Speed", "Torque", "Power")):
    """Return a SignalFile with Time from 0 to 10 s and some signals.

    Inputs:
        signal_name_list: the signals besides Time.
    Outputs: the SignalFile; signal k has the values (k + 1) * Time.
    """
    time_array = np.linspace(0.0, 10.0, 101)
    signal_dict = {"Time": time_array}
    for index_i, name_str in enumerate(signal_name_list):
        signal_dict[name_str] = time_array * (index_i + 1)
    return SignalFile("data.csv", signal_dict)


class LayoutControllerTestCase(unittest.TestCase):
    """Shared setup: the controllers, a temporary folder and a file."""

    def setUp(self) -> None:
        """Create the fake view and the controllers, and open a file.

        Inputs: none.
        Outputs: none.
        """
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.folder_str = self.temporary_folder.name
        self.view = FakeLayoutView()
        self.file_controller = FakeFileController()
        self.file_controller.dialog_folder_str = "/data/folder"
        self.workspace = Workspace(random.Random(2))
        self.plot_controller = PlotController(
            self.view, self.file_controller, self.workspace)
        self.controller = LayoutController(
            self.view, self.file_controller, self.plot_controller)
        self.file_controller.open(make_data_file(), False)

    def tearDown(self) -> None:
        """Remove the temporary folder.

        Inputs: none.
        Outputs: none.
        """
        self.temporary_folder.cleanup()

    def path(self, name_str: str) -> str:
        """Return a path in the temporary folder.

        Inputs:
            name_str: the file name.
        Outputs: the path.
        """
        return os.path.join(self.folder_str, name_str)

    def save(self, path_str: str) -> None:
        """Click Save layout and answer the dialog with a path.

        Inputs:
            path_str: the answer, "" to cancel.
        Outputs: none.
        """
        self.view.save_answer_list.append(path_str)
        self.view.layout_handler_tuple[0]()

    def load(self, path_str: str) -> None:
        """Click Load layout and answer the dialog with a path.

        Inputs:
            path_str: the answer, "" to cancel.
        Outputs: none.
        """
        self.view.load_answer_list.append(path_str)
        self.view.layout_handler_tuple[1]()

    def write_json(self, name_str: str, layout_dict) -> str:
        """Write a JSON value to a file of the temporary folder.

        Inputs:
            name_str: the file name.
            layout_dict: the value.
        Outputs: the path.
        """
        path_str = self.path(name_str)
        with open(path_str, "w", encoding="utf-8") as output_file:
            json.dump(layout_dict, output_file)
        return path_str

    def build_layout(self) -> None:
        """Build a layout through the handlers of the plot controller.

        Tab "Main" with a plot of Speed and Torque (a data tip on Speed
        and a Delta X marker), a second plot with Power, a vertical
        marker, the grid shown and a zoomed time range.

        Inputs: none.
        Outputs: none.
        """
        handler_dict = self.view.handler_dict
        tab_id_i = self.workspace.tab_list[0].tab_id_i
        handler_dict["rename_tab"](tab_id_i, "Main")
        handler_dict["double_click"]("Speed")
        plot_id_i = self.workspace.tab_list[0].plot_list[0].plot_id_i
        handler_dict["signal_drop_handler"](plot_id_i, "Torque")
        handler_dict["curve_width_handler"](plot_id_i, "Torque", 4)
        handler_dict["tip_pin_handler"](plot_id_i, "Speed", 2.0, 2.0)
        handler_dict["pinned_tip_move_handler"](plot_id_i, 0, 12.0, 8.0)
        handler_dict["plot_tool"](DELTA_X_TOOL_STR)
        handler_dict["delta_point_pick_handler"](plot_id_i, "Speed", 1.0,
                                                 1.0)
        handler_dict["delta_point_pick_handler"](plot_id_i, "Torque", 3.0,
                                                 6.0)
        handler_dict["plot_tool"](MARKER_TOOL_STR)
        handler_dict["marker_place_handler"](plot_id_i, 4.0)
        handler_dict["double_click"]("Power")
        handler_dict["grid"](True)
        handler_dict["time_range_handler"](plot_id_i, 1.0, 6.0)

    def content(self) -> tuple:
        """Return what the workspace shows, without ids.

        Inputs: none.
        Outputs: (tabs with plots, curves, tips and delta markers,
            markers).
        """
        tab_list = []
        for tab in self.workspace.tab_list:
            plot_list = []
            for plot in tab.plot_list:
                plot_list.append((
                    tuple((curve.signal_name_str, curve.color_str,
                           curve.width_i) for curve in plot.curve_list),
                    tuple((tip.signal_name_str, tip.time_s, tip.value_f,
                           tuple(tip.label_offset_tuple))
                          for tip in plot.pinned_tip_list),
                    tuple((delta.kind_str, delta.first_point_tuple,
                           delta.second_point_tuple)
                          for delta in plot.delta_marker_list)))
            tab_list.append((tab.name_str, tuple(plot_list)))
        return (tuple(tab_list), tuple((marker.name_str, marker.time_s)
                                       for marker in self.workspace
                                       .marker_list))


class LayoutButtonStateTest(LayoutControllerTestCase):
    """The buttons need a data file (LLFR-00218)."""

    @covers("LLFR-00218")
    def test_buttons_disabled_until_a_file_is_open(self) -> None:
        """Disabled at start, enabled once a file is open.

        Inputs: none.
        Outputs: none.
        """
        view = FakeLayoutView()
        file_controller = FakeFileController()
        plot_controller = PlotController(view, file_controller,
                                         Workspace(random.Random(1)))
        controller = LayoutController(view, file_controller,
                                      plot_controller)
        self.assertIs(view.layout_buttons_enabled_b, False)
        # LLFR-00218: neither button does anything without a data file.
        view.save_answer_list.append(self.path("never.json"))
        view.load_answer_list.append(self.path("never.json"))
        view.layout_handler_tuple[0]()
        view.layout_handler_tuple[1]()
        self.assertEqual(view.dialog_folder_list, [])
        self.assertFalse(os.path.exists(self.path("never.json")))
        self.assertEqual(view.finished_list, ["save", "load"])
        file_controller.open(make_data_file(), False)
        self.assertIs(view.layout_buttons_enabled_b, True)
        self.assertTrue(controller.data_file_open_b)


class SaveLayoutTest(LayoutControllerTestCase):
    """The Save layout flow (LLFR-00219 to LLFR-00224)."""

    @covers("LLFR-00219", "LLFR-00225", "LLFR-00227", "LLFR-00228")
    def test_save_writes_the_layout(self) -> None:
        """The file holds the layout of the plots as JSON.

        Inputs: none.
        Outputs: none.
        """
        self.build_layout()
        path_str = self.path("saved.json")
        self.save(path_str)
        with open(path_str, encoding="utf-8") as layout_file:
            text_str = layout_file.read()
        layout_dict = json.loads(text_str)
        self.assertEqual(list(layout_dict)[:2], ["format", "version"])
        self.assertEqual(layout_dict["format"], LAYOUT_FORMAT_STR)
        self.assertEqual(layout_dict["time_range"],
                         {"start": 1.0, "end": 6.0})
        self.assertIs(layout_dict["grid"], True)
        self.assertEqual(layout_dict["panel_widths"],
                         {"plot_panel": 900, "signal_list_panel": 300})
        self.assertEqual(layout_dict["tabs"][0]["name"], "Main")
        self.assertEqual(len(layout_dict["tabs"][0]["plots"]), 2)
        self.assertEqual(layout_dict["vertical_markers"],
                         [{"name": "Marker 1", "time": 4.0}])
        self.assertIn('\n  "tabs": [\n', text_str)
        self.assertEqual(self.view.finished_list, ["save"])
        self.assertEqual(self.view.save_error_list, [])

    @covers("LLFR-00225", "LLFR-00234")
    def test_whole_range_is_saved_as_the_file_range(self) -> None:
        """Without a zoom, the saved range is the whole file range.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["double_click"]("Speed")
        path_str = self.path("whole.json")
        self.save(path_str)
        with open(path_str, encoding="utf-8") as layout_file:
            layout_dict = json.load(layout_file)
        self.assertEqual(layout_dict["time_range"],
                         {"start": 0.0, "end": 10.0})

    @covers("LLFR-00219")
    def test_json_suffix_added_without_extension(self) -> None:
        """A name typed without an extension gets ".json".

        Inputs: none.
        Outputs: none.
        """
        self.save(self.path("plain"))
        self.assertTrue(os.path.exists(self.path("plain.json")))
        self.assertFalse(os.path.exists(self.path("plain")))
        self.save(self.path("other.txt"))
        self.assertTrue(os.path.exists(self.path("other.txt")))

    @covers("LLFR-00223")
    def test_replace_asked_when_suffix_names_an_existing_file(self) -> None:
        """The added ".json" names an existing file: replace is asked.

        Inputs: none.
        Outputs: none.
        """
        existing_str = self.write_json("taken.json", {"keep": 1})
        self.view.replace_answer_b = False
        self.save(self.path("taken"))
        self.assertEqual(self.view.replace_question_list, [existing_str])
        with open(existing_str, encoding="utf-8") as layout_file:
            self.assertEqual(json.load(layout_file), {"keep": 1})
        self.view.replace_answer_b = True
        self.save(self.path("taken"))
        with open(existing_str, encoding="utf-8") as layout_file:
            self.assertEqual(json.load(layout_file)["format"],
                             LAYOUT_FORMAT_STR)
        # LLFR-00223: a path the dialog returned with its extension was
        # already asked about by the dialog, so it is not asked again.
        self.save(existing_str)
        self.assertEqual(len(self.view.replace_question_list), 2)

    @covers("LLFR-00222")
    def test_cancel_saves_nothing(self) -> None:
        """A cancelled dialog writes no file and changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.build_layout()
        before_tuple = self.content()
        self.save("")
        self.assertEqual(os.listdir(self.folder_str), [])
        self.assertEqual(self.content(), before_tuple)
        self.assertEqual(self.view.finished_list, ["save"])

    @covers("LLFR-00224")
    def test_write_failure_shows_the_error_box(self) -> None:
        """A failed write is reported with its reason.

        Inputs: none.
        Outputs: none.
        """
        self.view.write_failure_str = "Permission denied: x.json"
        self.save(self.path("x.json"))
        self.assertEqual(self.view.save_error_list,
                         ["Permission denied: x.json"])
        self.assertEqual(self.view.finished_list, ["save"])

    @covers("LLFR-00238")
    def test_saving_is_not_undoable(self) -> None:
        """Saving records nothing for undo and keeps the history.

        Inputs: none.
        Outputs: none.
        """
        self.build_layout()
        depth_i = self.plot_controller.undo_history.depth()
        self.save(self.path("history.json"))
        self.assertEqual(self.plot_controller.undo_history.depth(), depth_i)


class DialogFolderTest(LayoutControllerTestCase):
    """The folder the layout dialogs show (LLFR-00220)."""

    @covers("LLFR-00220", "LLFR-00204")
    def test_folder_sequence(self) -> None:
        """First the Open file folder, then the last layout's folder.

        Inputs: none.
        Outputs: none.
        """
        sub_folder_str = self.path("sub")
        os.mkdir(sub_folder_str)
        # LLFR-00220: cancelled dialogs and failures do not move it.
        self.save("")
        self.load("")
        self.view.write_failure_str = "full"
        self.save(os.path.join(sub_folder_str, "fail.json"))
        self.view.write_failure_str = ""
        self.load(self.path("missing.json"))
        # LLFR-00204: the Open file folder may change meanwhile.
        self.file_controller.dialog_folder_str = "/data/other"
        self.save(os.path.join(sub_folder_str, "a.json"))
        self.load(self.path("missing.json"))
        loadable_str = self.path("loadable.json")
        self.save(loadable_str)
        self.save("")
        self.load(os.path.join(sub_folder_str, "a.json"))
        self.load("")
        self.assertEqual(self.view.dialog_folder_list, [
            ("save", "/data/folder"), ("load", "/data/folder"),
            ("save", "/data/folder"), ("load", "/data/folder"),
            ("save", "/data/other"), ("load", sub_folder_str),
            ("save", sub_folder_str), ("save", self.folder_str),
            ("load", self.folder_str), ("load", sub_folder_str)])


class LoadLayoutTest(LayoutControllerTestCase):
    """The Load layout flow (LLFR-00221, LLFR-00229 to LLFR-00238)."""

    def save_and_reopen(self, signal_name_list=("Speed", "Torque",
                                                "Power")) -> str:
        """Build and save a layout, then open a new data file.

        Inputs:
            signal_name_list: the signals of the new data file.
        Outputs: the path of the saved layout file.
        """
        self.build_layout()
        path_str = self.path("layout.json")
        self.save(path_str)
        self.saved_content_tuple = self.content()
        self.file_controller.open(make_data_file(signal_name_list), True)
        return path_str

    @covers("LLFR-00221", "LLFR-00230", "LLFR-00229", "LLFR-00237")
    def test_round_trip_after_replacing_the_file(self) -> None:
        """Loading into a new file rebuilds everything, with no report.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.save_and_reopen()
        self.view.panel_widths_tuple = (500, 500)
        self.view.handler_dict["grid"](False)
        self.load(path_str)
        self.assertEqual(self.content(), self.saved_content_tuple)
        self.assertEqual(self.view.report_list, [])
        self.assertEqual(self.view.load_error_list, [])
        # LLFR-00230: range, grid and panel widths of the file.
        for plot_id_i in self.view.plot_tab_dict:
            self.assertEqual(self.view.range_dict[plot_id_i], (1.0, 6.0))
        self.assertEqual(self.plot_controller.shared_time_range_tuple,
                         (1.0, 6.0))
        self.assertIs(self.view.grid_shown_b, True)
        self.assertEqual(self.view.panel_widths_tuple, (900, 300))
        # LLFR-00229: the views show the file's tabs, the first selected.
        self.assertEqual(list(self.view.tab_dict.values()), ["Main"])
        self.assertEqual(self.view.current_tab_id(),
                         self.workspace.tab_list[0].tab_id_i)
        self.assertEqual(self.view.finished_list[-1], "load")

    @covers("LLFR-00229")
    def test_tabs_added_after_tabs_with_plots(self) -> None:
        """Current tabs with plots are kept; the first new tab is shown.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.save_and_reopen()
        self.view.handler_dict["double_click"]("Torque")
        kept_tab_tuple = self.content()[0][0]
        self.load(path_str)
        tab_tuple = self.content()[0]
        self.assertEqual(len(tab_tuple), 2)
        self.assertEqual(tab_tuple[0], kept_tab_tuple)
        self.assertEqual(tab_tuple[1], self.saved_content_tuple[0][0])
        self.assertEqual(self.view.current_tab_id(),
                         self.workspace.tab_list[1].tab_id_i)
        self.assertEqual(list(self.view.tab_dict.values()),
                         ["Tab 1", "Main"])
        # LLFR-00230: the markers of the file are added on every plot.
        for plot_id_i in self.view.plot_tab_dict:
            self.assertEqual(len(self.view.marker_drawn_dict[plot_id_i]), 1)
        self.assertEqual(self.view.report_list, [])

    @covers("LLFR-00231", "LLFR-00232", "LLFR-00237")
    def test_missing_signal_report(self) -> None:
        """A missing signal draws nothing; the box lists it and the data
        tip and delta marker that needed it.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.save_and_reopen(("Speed", "Power"))
        self.load(path_str)
        main_tab_tuple = self.content()[0][0]
        first_plot_tuple = main_tab_tuple[1][0]
        self.assertEqual([item[0] for item in first_plot_tuple[0]],
                         ["Speed"])
        self.assertEqual(len(first_plot_tuple[1]), 1)
        self.assertEqual(first_plot_tuple[2], ())
        self.assertEqual(len(self.view.report_list), 1)
        report_str = self.view.report_list[0]
        self.assertIn("Signals not in the data file:\n  - Torque",
                      report_str)
        self.assertEqual(report_str.count("  - Torque"), 1)
        self.assertIn("Delta X marker between 1 s and 3 s", report_str)

    @covers("LLFR-00233", "LLFR-00234", "LLFR-00237")
    def test_shorter_file_limits_range_and_drops_markers(self) -> None:
        """A shorter data file limits the range and loses late markers.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.save_and_reopen()
        short_dict = {"Time": np.linspace(0.0, 3.0, 31)}
        for index_i, name_str in enumerate(("Speed", "Torque", "Power")):
            short_dict[name_str] = short_dict["Time"] * (index_i + 1)
        self.file_controller.open(SignalFile("short.csv", short_dict), True)
        self.load(path_str)
        self.assertEqual(self.plot_controller.shared_time_range_tuple,
                         (1.0, 3.0))
        self.assertEqual(self.workspace.marker_list, [])
        report_str = self.view.report_list[0]
        self.assertIn("limited to 1 s to 3 s", report_str)
        self.assertIn("Vertical marker \"Marker 1\" at 4 s", report_str)

    @covers("LLFR-00234")
    def test_range_without_overlap_shows_the_whole_file(self) -> None:
        """A range outside the file shows the whole range in every plot.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_json("far.json", {
            "format": LAYOUT_FORMAT_STR, "version": 1,
            "time_range": {"start": 50.0, "end": 60.0},
            "tabs": [{"name": "A", "plots": [{"curves": [
                {"signal": "Speed", "color": "#1f77b4", "width": 2}]}]}]})
        self.load(path_str)
        self.assertEqual(self.plot_controller.shared_time_range_tuple, ())
        for plot_id_i in self.view.plot_tab_dict:
            self.assertEqual(self.view.range_dict[plot_id_i], (0.0, 10.0))
        self.assertIn("whole time range", self.view.report_list[0])

    @covers("LLFR-00235", "LLFR-00237", "LLFR-00032")
    def test_replaced_values_and_sixth_plot(self) -> None:
        """Bad widths and colors are replaced; a 6th plot is skipped, and
        no Full Tab box is shown for it.

        Inputs: none.
        Outputs: none.
        """
        plot_list = [{"curves": [{"signal": "Speed", "color": "#000000",
                                  "width": 1}]} for _ in range(5)]
        plot_list[0]["curves"].append(
            {"signal": "Torque", "color": "#000000", "width": 9})
        plot_list.append({"curves": [{"signal": "Power",
                                      "color": "#1f77b4", "width": 1}]})
        path_str = self.write_json("full.json", {
            "format": LAYOUT_FORMAT_STR, "version": 1,
            "tabs": [{"name": "", "plots": plot_list}]})
        self.load(path_str)
        tab = self.workspace.tab_list[0]
        self.assertEqual(len(tab.plot_list), 5)
        self.assertEqual(len(self.view.plot_id_list(tab.tab_id_i)), 5)
        torque_curve = tab.plot_list[0].curve_list[1]
        self.assertEqual(torque_curve.width_i, 1)
        self.assertNotEqual(torque_curve.color_str, "#000000")
        self.assertEqual(self.view.full_tab_count_i, 0)
        report_str = self.view.report_list[0]
        self.assertIn("Values replaced:", report_str)
        self.assertIn("Width 9", report_str)
        self.assertIn("Color \"#000000\"", report_str)
        self.assertIn("is empty", report_str)
        self.assertIn("at most 5 plots", report_str)

    @covers("LLFR-00237")
    def test_no_report_when_everything_is_rebuilt(self) -> None:
        """A layout rebuilt as saved shows no box at all.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.save_and_reopen()
        self.load(path_str)
        self.assertEqual(self.view.report_list, [])
        self.assertEqual(self.view.load_error_list, [])

    @covers("LLFR-00238", "LLFR-00140")
    def test_load_clears_undo_and_redo(self) -> None:
        """Loading clears both histories and is not undoable itself.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.save_and_reopen()
        self.view.handler_dict["double_click"]("Speed")
        self.view.handler_dict["double_click"]("Torque")
        self.view.handler_dict["undo"]()
        self.assertTrue(self.view.undo_enabled_b)
        self.assertTrue(self.view.redo_enabled_b)
        self.load(path_str)
        self.assertEqual(self.plot_controller.undo_history.depth(), 0)
        self.assertFalse(self.plot_controller.undo_history.can_redo())
        self.assertIs(self.view.undo_enabled_b, False)
        self.assertIs(self.view.redo_enabled_b, False)
        before_tuple = self.content()
        self.view.handler_dict["undo"]()
        self.assertEqual(self.content(), before_tuple)

    @covers("LLFR-00222")
    def test_cancel_loads_nothing(self) -> None:
        """A cancelled dialog keeps the layout unchanged.

        Inputs: none.
        Outputs: none.
        """
        self.build_layout()
        before_tuple = self.content()
        depth_i = self.plot_controller.undo_history.depth()
        self.load("")
        self.assertEqual(self.content(), before_tuple)
        self.assertEqual(self.plot_controller.undo_history.depth(), depth_i)
        self.assertEqual(self.view.report_list, [])
        self.assertEqual(self.view.finished_list, ["load"])

    @covers("LLFR-00236")
    def test_unreadable_files_keep_the_layout(self) -> None:
        """A missing file, bad JSON or another JSON file is refused.

        Inputs: none.
        Outputs: none.
        """
        self.build_layout()
        before_tuple = self.content()
        depth_i = self.plot_controller.undo_history.depth()
        bad_json_str = self.path("bad.json")
        with open(bad_json_str, "w", encoding="utf-8") as output_file:
            output_file.write("{not json")
        other_str = self.write_json("other.json", {"format": "other",
                                                   "version": 1})
        for path_str in (self.path("missing.json"), bad_json_str,
                         other_str):
            with self.subTest(path=path_str):
                self.load(path_str)
                self.assertIn("could not be read as a layout file",
                              self.view.load_error_list[-1])
                self.assertEqual(self.content(), before_tuple)
                self.assertEqual(
                    self.plot_controller.undo_history.depth(), depth_i)
        self.assertEqual(len(self.view.load_error_list), 3)
        self.assertEqual(self.view.report_list, [])

    @covers("LLFR-00236", "LLFR-00071")
    def test_unexpected_failure_keeps_the_layout(self) -> None:
        """An unexpected error while rebuilding restores the layout.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.save_and_reopen()
        self.build_layout()
        before_tuple = self.content()

        def failing_builder(entry_list: list, report) -> None:
            """Raise as a broken synthetic signal builder would.

            Inputs:
                entry_list: the entries.
                report: the LayoutReport.
            Outputs: none.
            """
            raise RuntimeError("broken")
        self.controller.synthetic_signal_builder = failing_builder
        self.load(path_str)
        self.assertIn("broken", self.view.load_error_list[-1])
        self.assertEqual(self.content(), before_tuple)
        self.assertEqual(self.view.finished_list[-1], "load")


if __name__ == "__main__":
    unittest.main()
