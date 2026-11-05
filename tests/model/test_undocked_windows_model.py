"""Model tests for the undocked windows and their layout entries (#205).

They check the rules that need no Qt: where a window is opened
(model.window_placement, HLFR-00124, HLFR-00142), the docked and
undocked tabs of the Workspace (HLFR-00125 to HLFR-00127, HLFR-00134)
and the layout file entries of the windows and the plot matrices
(HLFR-00140, HLFR-00141, HLFR-00152, HLFR-00049, HLFR-00050,
HLFR-00052).
"""

import json
import random
import unittest

import numpy as np

from tests.support import covers

from model.layout_file import (
    build_layout_dict, layout_text, parse_layout_text, rebuild_layout)
from model.window_placement import (
    fitted_panel_width_i, new_window_tuple, placed_window_tuple)
from model.workspace import Workspace, first_panel_width_i

# Two screens side by side, the second one higher than the first.
MAIN_SCREEN_TUPLE = (0, 0, 1920, 1050)
SECOND_SCREEN_TUPLE = (1920, -200, 1280, 1000)


class WindowPlacementTest(unittest.TestCase):
    """Where an undocked window opens."""

    @covers("LLFR-01016", "LLFR-01128", "HLFR-00124")
    def test_new_window_is_the_plot_panel_moved_by_thirty(self) -> None:
        """The plot panel's size, 30 pixels right and down.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(new_window_tuple((12, 90, 950, 640)),
                         (42, 120, 950, 640))

    @covers("LLFR-01184", "LLFR-01054", "HLFR-00050", "HLFR-00141",
            "HLFR-00130")
    def test_panel_width_fitted_to_its_window(self) -> None:
        """A width wider than the window minus 100 pixels is trimmed to
        it; a width that fits, or a window of unknown width, keeps it;
        the panel keeps at least 1 pixel.

        Inputs: none.
        Outputs: none.
        """
        # Fits: kept as it is, up to the window's width minus 100.
        self.assertEqual(fitted_panel_width_i(300, 1000), 300)
        self.assertEqual(fitted_panel_width_i(900, 1000), 900)
        # Too wide: trimmed so that the plot panel keeps 100 pixels.
        self.assertEqual(fitted_panel_width_i(901, 1000), 900)
        self.assertEqual(fitted_panel_width_i(16777215, 600), 500)
        # A window of 100 pixels or less leaves the panel 1 pixel.
        self.assertEqual(fitted_panel_width_i(50, 101), 1)
        self.assertEqual(fitted_panel_width_i(50, 100), 1)
        self.assertEqual(fitted_panel_width_i(50, 30), 1)
        # An unknown window width keeps the width, at least 1 pixel.
        self.assertEqual(fitted_panel_width_i(5000, 0), 5000)
        self.assertEqual(fitted_panel_width_i(0, 0), 1)
        self.assertEqual(fitted_panel_width_i(-4, 1000), 1)

    @covers("LLFR-01083", "HLFR-00142")
    def test_window_on_a_screen_is_left_where_it_is(self) -> None:
        """A window whose top edge is on a screen does not move.

        Inputs: none.
        Outputs: none.
        """
        window_tuple = (2000, -100, 800, 600)
        self.assertEqual(placed_window_tuple(
            window_tuple, [MAIN_SCREEN_TUPLE, SECOND_SCREEN_TUPLE],
            MAIN_SCREEN_TUPLE), window_tuple)
        # 100 pixels of the top edge on the main screen are enough.
        edge_tuple = (1820, 100, 800, 600)
        self.assertEqual(placed_window_tuple(
            edge_tuple, [MAIN_SCREEN_TUPLE], MAIN_SCREEN_TUPLE), edge_tuple)

    @covers("LLFR-01083", "HLFR-00142")
    def test_window_off_screen_moves_onto_the_main_screen(self) -> None:
        """A window of a missing screen moves to the nearest place on the
        screen of the main window.

        Inputs: none.
        Outputs: none.
        """
        # Saved on the second screen, which is no longer connected.
        self.assertEqual(placed_window_tuple(
            (2000, -100, 800, 600), [MAIN_SCREEN_TUPLE], MAIN_SCREEN_TUPLE),
            (1120, 0, 800, 600))
        # Less than 100 pixels of the top edge on the screen.
        self.assertEqual(placed_window_tuple(
            (1830, 100, 800, 600), [MAIN_SCREEN_TUPLE], MAIN_SCREEN_TUPLE),
            (1120, 100, 800, 600))
        # The top edge above the screen (title bar out of reach).
        self.assertEqual(placed_window_tuple(
            (300, -50, 800, 600), [MAIN_SCREEN_TUPLE], MAIN_SCREEN_TUPLE),
            (300, 0, 800, 600))

    @covers("LLFR-01084", "HLFR-00142")
    def test_window_larger_than_the_screen_is_reduced(self) -> None:
        """The width or height, or both, fit the available area.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(placed_window_tuple(
            (100, 50, 2500, 800), [MAIN_SCREEN_TUPLE], MAIN_SCREEN_TUPLE),
            (100, 50, 1920, 800))
        self.assertEqual(placed_window_tuple(
            (5000, 5000, 2500, 1400), [MAIN_SCREEN_TUPLE],
            MAIN_SCREEN_TUPLE), (0, 0, 1920, 1050))

    @covers("LLFR-01051")
    def test_first_panel_width(self) -> None:
        """25% of the window's width, whatever the main panel's width.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(first_panel_width_i(240, 1000), 250)
        self.assertEqual(first_panel_width_i(240, 300), 75)
        self.assertEqual(first_panel_width_i(900, 1000), 250)
        self.assertEqual(first_panel_width_i(10, 1002), 250)
        self.assertEqual(first_panel_width_i(10, 3), 1)
        # An unknown window width falls back to the main panel's.
        self.assertEqual(first_panel_width_i(240, 0), 240)
        self.assertEqual(first_panel_width_i(0, 0), 1)


class WorkspaceDockTest(unittest.TestCase):
    """Docked and undocked tabs of the workspace."""

    def setUp(self) -> None:
        """Create a workspace with three tabs.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace(random.Random(2))
        self.workspace.add_tab()
        self.workspace.add_tab()
        self.id_list = [tab.tab_id_i for tab in self.workspace.tab_list]

    def tab_ids(self) -> list:
        """Return the tab ids in tab order.

        Inputs: none.
        Outputs: a list of int.
        """
        return [tab.tab_id_i for tab in self.workspace.tab_list]

    @covers("LLFR-01091", "LLFR-00025", "HLFR-00143")
    def test_tab_order_docked_then_undocked(self) -> None:
        """New tabs go after the last docked tab, before undocked ones.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(self.workspace.undock_tab(self.id_list[0],
                                                  (1, 2, 3, 4)))
        new_tab = self.workspace.add_tab()
        self.assertEqual(self.tab_ids(), [self.id_list[1], self.id_list[2],
                                          new_tab.tab_id_i, self.id_list[0]])
        self.assertTrue(self.workspace.dock_tab(self.id_list[0]))
        self.assertEqual(self.tab_ids()[-1], self.id_list[0])

    @covers("LLFR-01018", "LLFR-01069", "LLFR-00066")
    def test_delete_and_undock_rules(self) -> None:
        """An undocked tab can always be deleted; the last docked tab can
        be neither deleted nor undocked.

        Inputs: none.
        Outputs: none.
        """
        self.workspace.undock_tab(self.id_list[0])
        self.workspace.undock_tab(self.id_list[1])
        self.assertFalse(self.workspace.can_undock_tab(self.id_list[2]))
        self.assertFalse(self.workspace.undock_tab(self.id_list[2]))
        self.assertFalse(self.workspace.delete_tab(self.id_list[2]))
        self.assertTrue(self.workspace.can_delete_tab(self.id_list[0]))
        self.assertTrue(self.workspace.delete_tab(self.id_list[0]))

    @covers("LLFR-01060", "LLFR-01053", "LLFR-01055", "LLFR-00140")
    def test_window_state_is_undoable_but_not_its_place(self) -> None:
        """Docking, the panel and the widths change the undo state; the
        window position and size do not.

        Inputs: none.
        Outputs: none.
        """
        snapshot = self.workspace.snapshot()
        self.workspace.undock_tab(self.id_list[0], (1, 2, 3, 4))
        self.assertFalse(self.workspace.is_unchanged_since(snapshot))
        snapshot = self.workspace.snapshot()
        self.workspace.find_tab(self.id_list[0]).window_tuple = (9, 9, 9, 9)
        self.assertTrue(self.workspace.is_unchanged_since(snapshot))
        self.assertTrue(self.workspace.set_window_panel(
            self.workspace.find_tab(self.id_list[0]).window_id_i, True, 120))
        self.assertFalse(self.workspace.is_unchanged_since(snapshot))
        snapshot = self.workspace.snapshot()
        self.assertTrue(self.workspace.set_panel_width(-1, 310))
        self.assertFalse(self.workspace.is_unchanged_since(snapshot))
        self.workspace.restore(snapshot)
        self.assertEqual(self.workspace.main_panel_width_i, 0)


def signal_dict() -> dict:
    """Return the signals of one data file.

    Inputs: none.
    Outputs: a dict name -> numpy array with file1_Time and two signals.
    """
    time_array = np.linspace(0.0, 10.0, 101)
    return {"file1_Time": time_array, "file1_Speed": time_array * 2.0,
            "file1_Torque": time_array * 3.0}


def plot_entry(signal_name_str: str) -> dict:
    """Return a plot entry with one curve.

    Inputs:
        signal_name_str: the signal of the curve.
    Outputs: the entry.
    """
    return {"curves": [{"signal": signal_name_str, "color": "#1f77b4",
                        "width": 1}], "data_tips": [], "delta_markers": []}


def layout_with_tabs(tab_list: list) -> dict:
    """Return the content of a version 3 layout file.

    Inputs:
        tab_list: the "tabs" entry.
    Outputs: the dict.
    """
    return {"format": "plot_tool layout", "version": 3, "shown_tab": 0,
            "time_range": None, "grid": True, "panel_widths": None,
            "flags": [], "areas": [], "synthetic_signals": [],
            "tabs": tab_list}


class LayoutWindowsTest(unittest.TestCase):
    """The layout file entries of the windows and the plot matrices."""

    def setUp(self) -> None:
        """Create an empty workspace.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace(random.Random(4))
        self.signal_dict = signal_dict()

    def rebuild(self, layout_dict: dict):
        """Rebuild a layout with the default window of an undock.

        Inputs:
            layout_dict: the content of the file.
        Outputs: the LayoutResult.
        """
        return rebuild_layout(self.workspace, layout_dict, self.signal_dict,
                              self.signal_dict["file1_Time"], None, None,
                              (30, 40, 900, 700))

    @covers("LLFR-00225", "LLFR-01075", "LLFR-00227", "HLFR-00140",
            "HLFR-00152", "HLFR-00049")
    def test_saved_entries_of_tabs_and_windows(self) -> None:
        """Every tab saves undocked and plot_matrix; an undocked tab its
        window and panel, in whole pixels.

        Inputs: none.
        Outputs: none.
        """
        workspace = Workspace(random.Random(1))
        first_tab = workspace.tab_list[0]
        workspace.add_plot(first_tab.tab_id_i).add_curve("file1_Speed")
        second_tab = workspace.add_tab()
        workspace.set_plot_matrix(second_tab.tab_id_i, 2, 3)
        workspace.add_plot(second_tab.tab_id_i).add_curve("file1_Torque")
        workspace.undock_tab(second_tab.tab_id_i, (-5, 60, 800, 500))
        workspace.set_window_panel(second_tab.window_id_i, True, 210)
        text_str = layout_text(build_layout_dict(
            workspace, first_tab.tab_id_i, (), True))
        tab_list = json.loads(text_str)["tabs"]
        self.assertEqual(tab_list[0]["undocked"], False)
        self.assertEqual(tab_list[0]["plot_matrix"],
                         {"rows": 5, "columns": 1})
        self.assertNotIn("window", tab_list[0])
        self.assertEqual(tab_list[1]["undocked"], True)
        self.assertEqual(tab_list[1]["plot_matrix"],
                         {"rows": 2, "columns": 3})
        self.assertEqual(tab_list[1]["window"],
                         {"x": -5, "y": 60, "width": 800, "height": 500})
        self.assertEqual(tab_list[1]["signal_list_panel"],
                         {"shown": True, "width": 210})
        self.assertIn('\n        "x": -5,\n', text_str)

    @covers("LLFR-00225", "LLFR-01051")
    def test_panel_never_shown_saves_its_first_width(self) -> None:
        """A hidden panel that was never shown saves its first width,
        25% of the window's width.

        Inputs: none.
        Outputs: none.
        """
        workspace = Workspace(random.Random(1))
        workspace.add_tab()
        workspace.main_panel_width_i = 260
        tab = workspace.tab_list[0]
        workspace.undock_tab(tab.tab_id_i, (0, 0, 400, 300))
        entry_dict = build_layout_dict(workspace, -1, (), True)["tabs"][1]
        self.assertEqual(entry_dict["signal_list_panel"],
                         {"shown": False, "width": 100})

    @covers("LLFR-01076", "LLFR-01077", "LLFR-01078", "LLFR-01123",
            "LLFR-00477", "HLFR-00141", "HLFR-00050", "HLFR-00152")
    def test_round_trip_rebuilds_windows_and_matrices(self) -> None:
        """A saved layout comes back with the same windows and matrices,
        with nothing in the report.

        Inputs: none.
        Outputs: none.
        """
        workspace = Workspace(random.Random(1))
        first_tab = workspace.tab_list[0]
        workspace.add_plot(first_tab.tab_id_i).add_curve("file1_Speed")
        second_tab = workspace.add_tab()
        workspace.set_plot_matrix(second_tab.tab_id_i, 1, 2)
        workspace.add_plot(second_tab.tab_id_i).add_curve("file1_Torque")
        workspace.undock_tab(second_tab.tab_id_i, (100, 120, 640, 480))
        workspace.set_window_panel(second_tab.window_id_i, True, 190)
        layout_dict = parse_layout_text(layout_text(build_layout_dict(
            workspace, first_tab.tab_id_i, (), True)))
        result = self.rebuild(layout_dict)
        self.assertTrue(result.report.is_empty(), result.report.text())
        docked_list = self.workspace.docked_tab_list()
        undocked_list = self.workspace.undocked_tab_list()
        self.assertEqual(len(docked_list), 1)
        self.assertEqual(len(undocked_list), 1)
        self.assertEqual(result.first_tab_id_i, docked_list[0].tab_id_i)
        window_tab = undocked_list[0]
        self.assertEqual(window_tab.window_tuple, (100, 120, 640, 480))
        self.assertEqual((window_tab.panel_shown_b, window_tab.panel_width_i),
                         (True, 190))
        self.assertEqual((window_tab.row_count_i, window_tab.column_count_i),
                         (1, 2))

    @covers("LLFR-01124", "LLFR-01077")
    def test_older_file_gives_docked_tabs_and_default_matrix(self) -> None:
        """No undocked or plot_matrix entry: docked, 5 x 1, no report.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(layout_with_tabs(
            [{"name": "A", "plots": [plot_entry("file1_Speed")]}]))
        self.assertTrue(result.report.is_empty(), result.report.text())
        tab = self.workspace.tab_list[0]
        self.assertFalse(tab.undocked_b)
        self.assertEqual((tab.row_count_i, tab.column_count_i), (5, 1))

    @covers("LLFR-01125", "LLFR-01126", "HLFR-00052")
    def test_unusable_matrix_is_replaced_and_reported(self) -> None:
        """A matrix that is not 1 to 10 by 1 to 10 becomes 5 x 1.

        Inputs: none.
        Outputs: none.
        """
        for matrix_value in ({"rows": 11, "columns": 1},
                             {"rows": 2, "columns": "3"},
                             {"rows": True, "columns": 2}, [2, 2], None):
            with self.subTest(matrix=matrix_value):
                self.workspace = Workspace(random.Random(4))
                result = self.rebuild(layout_with_tabs(
                    [{"name": "A", "plot_matrix": matrix_value,
                      "plots": [plot_entry("file1_Speed")]}]))
                tab = self.workspace.tab_list[0]
                self.assertEqual((tab.row_count_i, tab.column_count_i),
                                 (5, 1))
                self.assertIn("Plot matrix", result.report.text())

    @covers("LLFR-00488", "LLFR-00237", "HLFR-00052", "HLFR-00152")
    def test_plots_beyond_the_saved_matrix_are_reported(self) -> None:
        """A 1 x 2 matrix keeps two plots; the third is reported.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(layout_with_tabs(
            [{"name": "A", "plot_matrix": {"rows": 1, "columns": 2},
              "plots": [plot_entry("file1_Speed"), plot_entry("file1_Torque"),
                        plot_entry("file1_Speed")]}]))
        self.assertEqual(len(self.workspace.tab_list[0].plot_list), 2)
        self.assertIn("Plot 3 of tab \"A\"", result.report.text())
        self.assertIn("1 × 2 plot matrix", result.report.text())

    @covers("LLFR-01081", "LLFR-01082", "HLFR-00141", "HLFR-00052")
    def test_unusable_window_values_take_undock_values(self) -> None:
        """Bad window and panel values become those of an undock and are
        listed as replaced.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(layout_with_tabs(
            [{"name": "Docked", "plots": [plot_entry("file1_Speed")]},
             {"name": "W", "undocked": True,
              "window": {"x": 1.5, "y": 2, "width": 0, "height": 300},
              "signal_list_panel": {"shown": "yes", "width": -4},
              "plots": [plot_entry("file1_Torque")]}]))
        tab = self.workspace.undocked_tab_list()[0]
        self.assertEqual(tab.window_tuple, (30, 40, 900, 700))
        self.assertEqual((tab.panel_shown_b, tab.panel_width_i), (False, 0))
        report_str = result.report.text()
        for what_str in ("Window position", "Window size",
                         "Signal list panel state",
                         "Signal list panel width"):
            self.assertIn(what_str, report_str)

    @covers("LLFR-01081", "LLFR-01082", "LLFR-00235", "LLFR-00237",
            "HLFR-00141", "HLFR-00052")
    def test_window_values_qt_cannot_take_are_replaced(self) -> None:
        """A panel width, a window size or a position that Qt can't take
        (above 2**31 - 1, or beyond 16777215 pixels) is replaced by the
        value of an undock and reported, like any unusable value.

        Inputs: none.
        Outputs: none.
        """
        for window_dict, panel_width_value, what_tuple in (
                ({"x": 10, "y": 20, "width": 800, "height": 600},
                 2 ** 31, ("Signal list panel width",)),
                ({"x": 10, "y": 20, "width": 800, "height": 600},
                 16777216, ("Signal list panel width",)),
                ({"x": 10, "y": 20, "width": 2 ** 31, "height": 600},
                 200, ("Window size",)),
                ({"x": 10, "y": 20, "width": 800, "height": 2 ** 63},
                 200, ("Window size",)),
                ({"x": 2 ** 31, "y": 20, "width": 800, "height": 600},
                 200, ("Window position",)),
                ({"x": 10, "y": -2 ** 31 - 1, "width": 800,
                  "height": 600}, 200, ("Window position",)),
                ({"x": -16777216, "y": 20, "width": 800,
                  "height": 600}, 200, ("Window position",))):
            with self.subTest(window=window_dict, width=panel_width_value):
                self.setUp()
                result = self.rebuild(layout_with_tabs(
                    [{"name": "Docked",
                      "plots": [plot_entry("file1_Speed")]},
                     {"name": "W", "undocked": True,
                      "window": window_dict,
                      "signal_list_panel": {"shown": True,
                                            "width": panel_width_value},
                      "plots": [plot_entry("file1_Torque")]}]))
                tab = self.workspace.undocked_tab_list()[0]
                report_str = result.report.text()
                for what_str in what_tuple:
                    self.assertIn(what_str, report_str)
                self.assertEqual(len(result.report.replaced_line_list), 1)
                x_i, y_i, width_i, height_i = tab.window_tuple
                for value_i in tab.window_tuple + (tab.panel_width_i,):
                    self.assertLessEqual(abs(value_i), 16777215)
                if "Window size" in what_tuple:
                    self.assertEqual((width_i, height_i), (900, 700))
                if "Window position" in what_tuple:
                    self.assertEqual((x_i, y_i), (30, 40))
                if "Signal list panel width" in what_tuple:
                    self.assertEqual(tab.panel_width_i, 0)
                    self.assertTrue(tab.panel_shown_b)

    @covers("LLFR-01081", "HLFR-00141")
    def test_largest_window_values_qt_takes_are_kept(self) -> None:
        """The limits themselves (16777215 pixels) are kept, unreported.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(layout_with_tabs(
            [{"name": "Docked", "plots": [plot_entry("file1_Speed")]},
             {"name": "W", "undocked": True,
              "window": {"x": -16777215, "y": 16777215,
                         "width": 16777215, "height": 1},
              "signal_list_panel": {"shown": True, "width": 16777215},
              "plots": [plot_entry("file1_Torque")]}]))
        self.assertTrue(result.report.is_empty(), result.report.text())
        tab = self.workspace.undocked_tab_list()[0]
        self.assertEqual(tab.window_tuple,
                         (-16777215, 16777215, 16777215, 1))
        self.assertEqual(tab.panel_width_i, 16777215)

    @covers("LLFR-01085", "LLFR-01076", "HLFR-00142", "HLFR-00052")
    def test_off_screen_window_is_not_reported(self) -> None:
        """A window saved far off-screen loads with no report; the view
        moves it onto a screen when it opens it.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(layout_with_tabs(
            [{"name": "Docked", "plots": [plot_entry("file1_Speed")]},
             {"name": "W", "undocked": True,
              "window": {"x": 90000, "y": -90000, "width": 5000,
                         "height": 4000},
              "signal_list_panel": {"shown": True, "width": 150},
              "plots": [plot_entry("file1_Torque")]}]))
        self.assertTrue(result.report.is_empty(), result.report.text())
        self.assertEqual(self.workspace.undocked_tab_list()[0].window_tuple,
                         (90000, -90000, 5000, 4000))
        self.assertEqual(placed_window_tuple(
            (90000, -90000, 5000, 4000), [MAIN_SCREEN_TUPLE],
            MAIN_SCREEN_TUPLE), MAIN_SCREEN_TUPLE)

    @covers("LLFR-01085", "LLFR-01184", "LLFR-01078", "LLFR-01081",
            "HLFR-00142", "HLFR-00141", "HLFR-00052")
    def test_too_wide_panel_width_is_not_reported(self) -> None:
        """A panel width in the range Qt takes but wider than its window
        loads as saved, with no report; the view trims it when it shows
        the panel (LLFR-01184).

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(layout_with_tabs(
            [{"name": "Docked", "plots": [plot_entry("file1_Speed")]},
             {"name": "W", "undocked": True,
              "window": {"x": 10, "y": 20, "width": 600, "height": 400},
              "signal_list_panel": {"shown": True, "width": 5000},
              "plots": [plot_entry("file1_Torque")]}]))
        self.assertTrue(result.report.is_empty(), result.report.text())
        tab = self.workspace.undocked_tab_list()[0]
        self.assertEqual(tab.panel_width_i, 5000)
        self.assertEqual(fitted_panel_width_i(tab.panel_width_i,
                                              tab.window_tuple[2]), 500)

    @covers("LLFR-01079", "LLFR-00475", "LLFR-01080", "HLFR-00141")
    def test_main_window_keeps_a_docked_tab(self) -> None:
        """With no plot anywhere and only undocked tabs in the file, the
        first docked tab stays in the main window.

        Inputs: none.
        Outputs: none.
        """
        kept_id_i = self.workspace.tab_list[0].tab_id_i
        window_tab = self.workspace.add_tab()
        self.workspace.undock_tab(window_tab.tab_id_i)
        result = self.rebuild(layout_with_tabs(
            [{"name": "W", "undocked": True,
              "window": {"x": 1, "y": 2, "width": 300, "height": 200},
              "signal_list_panel": {"shown": False, "width": 100},
              "plots": [plot_entry("file1_Speed")]}]))
        self.assertTrue(result.tabs_replaced_b)
        self.assertEqual(self.workspace.tab_list[0].tab_id_i, kept_id_i)
        self.assertFalse(self.workspace.tab_list[0].undocked_b)
        self.assertIsNone(self.workspace.find_tab(window_tab.tab_id_i))
        self.assertEqual(result.first_tab_id_i, -1)


if __name__ == "__main__":
    unittest.main()
