"""Tests for the names of delta markers and arrows in the model and the
layout file (issue #183, Part A).

Covers the default names (LLFR-00428, LLFR-00852, LLFR-00438), the
renames (LLFR-00429, LLFR-00853, LLFR-00854, LLFR-00856, LLFR-00439,
LLFR-00873, LLFR-00874, LLFR-00876), the names in the undo states
(LLFR-00140) and the delta marker names in the layout file (LLFR-00225,
LLFR-00430, LLFR-00857, LLFR-00858, LLFR-00859).
"""

import json
import random
import unittest

import numpy as np

from tests.support import covers

from model.layout_file import build_layout_dict, layout_text, rebuild_layout
from model.workspace import (
    DELTA_X_KIND_STR, DELTA_Y_KIND_STR, Workspace, plot_state_tuple)


def make_workspace_with_plot() -> tuple:
    """Return a workspace with one plot that draws Speed and Torque.

    Inputs: none.
    Outputs: (workspace, plot).
    """
    workspace = Workspace(random.Random(1))
    plot = workspace.add_plot(workspace.tab_list[0].tab_id_i)
    plot.add_curve("Speed")
    plot.add_curve("Torque")
    return workspace, plot


class DeltaMarkerNameModelTest(unittest.TestCase):
    """Names of delta markers in the model."""

    def setUp(self) -> None:
        """Create the workspace and its plot.

        Inputs: none.
        Outputs: none.
        """
        self.workspace, self.plot = make_workspace_with_plot()

    def place(self, kind_str: str):
        """Place a delta marker named by the workspace.

        Inputs:
            kind_str: DELTA_X_KIND_STR or DELTA_Y_KIND_STR.
        Outputs: the new DeltaMarker.
        """
        return self.plot.add_delta_marker(
            kind_str, ("Speed", 1.0, 2.0), ("Torque", 3.0, 5.0),
            name_str=self.workspace.take_delta_marker_name(kind_str))

    @covers("LLFR-00428", "LLFR-00851", "HLFR-00097")
    def test_names_count_by_kind_and_restart_on_reset(self) -> None:
        """Each kind counts from 1; numbers stay used up after a delete;
        reset (a file opened) restarts them.

        Inputs: none.
        Outputs: none.
        """
        first_marker = self.place(DELTA_X_KIND_STR)
        self.assertEqual(first_marker.name_str, "Delta X 1")
        self.assertEqual(self.place(DELTA_Y_KIND_STR).name_str, "Delta Y 1")
        self.plot.remove_delta_marker(first_marker.delta_marker_id_i)
        self.assertEqual(self.place(DELTA_X_KIND_STR).name_str, "Delta X 2")
        self.workspace.reset()
        self.assertEqual(self.workspace.take_delta_marker_name(
            DELTA_X_KIND_STR), "Delta X 1")
        with self.assertRaises(ValueError):
            self.workspace.take_delta_marker_name("z")

    @covers("LLFR-00852", "HLFR-00097")
    def test_names_in_use_are_skipped_in_every_plot(self) -> None:
        """A number whose name a marker of the same kind has, in any
        plot, is skipped and used up.

        Inputs: none.
        Outputs: none.
        """
        other_plot = self.workspace.add_plot(
            self.workspace.tab_list[0].tab_id_i)
        other_plot.add_curve("Speed")
        other_plot.add_delta_marker(DELTA_X_KIND_STR, ("Speed", 1.0, 2.0),
                                    ("Speed", 2.0, 3.0),
                                    name_str="Delta X 1")
        self.assertEqual(self.place(DELTA_X_KIND_STR).name_str, "Delta X 2")
        self.assertEqual(self.workspace.next_delta_number_dict[
            DELTA_X_KIND_STR], 3)

    @covers("LLFR-00428")
    def test_plot_gives_a_default_name_without_one(self) -> None:
        """A marker added with no name still gets a default name that is
        not used in its plot.

        Inputs: none.
        Outputs: none.
        """
        first_marker = self.plot.add_delta_marker(
            DELTA_Y_KIND_STR, ("Speed", 1.0, 2.0), ("Speed", 2.0, 3.0))
        second_marker = self.plot.add_delta_marker(
            DELTA_Y_KIND_STR, ("Speed", 1.0, 2.0), ("Speed", 2.0, 3.0), "",
            "   ")
        self.assertEqual(first_marker.name_str, "Delta Y 1")
        self.assertEqual(second_marker.name_str, "Delta Y 2")

    @covers("LLFR-00429", "LLFR-00853", "LLFR-00854", "LLFR-00856",
            "LLFR-00140", "HLFR-00110")
    def test_rename_changes_only_the_name(self) -> None:
        """A rename keeps the points, value and color, strips spaces and
        is in the undo state; a blank name, the same name or an unknown
        id change nothing.

        Inputs: none.
        Outputs: none.
        """
        delta_marker = self.place(DELTA_X_KIND_STR)
        delta_id_i = delta_marker.delta_marker_id_i
        before_tuple = (delta_marker.first_point_tuple,
                        delta_marker.second_point_tuple,
                        delta_marker.delta_f(), delta_marker.color_str)
        state_before_tuple = plot_state_tuple(self.plot)
        self.assertTrue(self.plot.rename_delta_marker(delta_id_i, " Lap "))
        self.assertEqual(delta_marker.name_str, "Lap")
        self.assertEqual((delta_marker.first_point_tuple,
                          delta_marker.second_point_tuple,
                          delta_marker.delta_f(), delta_marker.color_str),
                         before_tuple)
        self.assertNotEqual(plot_state_tuple(self.plot), state_before_tuple)
        self.assertEqual(plot_state_tuple(self.plot)[4][0][-1], "Lap")
        for name_str in ("", "   ", "Lap"):
            self.assertFalse(self.plot.rename_delta_marker(delta_id_i,
                                                           name_str))
        self.assertFalse(self.plot.rename_delta_marker(999, "Other"))
        self.assertEqual(delta_marker.name_str, "Lap")


class ArrowNameModelTest(unittest.TestCase):
    """Names of arrows in the model."""

    def setUp(self) -> None:
        """Create the workspace and its plot.

        Inputs: none.
        Outputs: none.
        """
        self.workspace, self.plot = make_workspace_with_plot()

    @covers("LLFR-00438", "LLFR-00872", "HLFR-00100")
    def test_arrow_names_grow_and_restart_on_reset(self) -> None:
        """"Arrow N" grows by 1 for each new arrow; reset restarts it.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.workspace.take_arrow_name(), "Arrow 1")
        self.assertEqual(self.workspace.take_arrow_name(), "Arrow 2")
        self.workspace.reset()
        self.assertEqual(self.workspace.take_arrow_name(), "Arrow 1")
        # Without a name, the plot names it after its own arrows.
        self.plot.add_arrow(0.0, 0.0, 1.0, 1.0, "Arrow 1")
        self.assertEqual(self.plot.add_arrow(0.0, 0.0, 2.0, 1.0).name_str,
                         "Arrow 2")

    @covers("LLFR-00439", "LLFR-00873", "LLFR-00874", "LLFR-00876",
            "LLFR-00140", "HLFR-00111")
    def test_rename_changes_only_the_name(self) -> None:
        """A rename keeps the ends and the color and is in the undo
        state; a blank name, the same name or an unknown index change
        nothing.

        Inputs: none.
        Outputs: none.
        """
        arrow = self.plot.add_arrow(0.0, 1.0, 2.0, 3.0, "Arrow 1")
        self.assertTrue(self.plot.rename_arrow(0, "  Peak "))
        self.assertEqual(arrow.name_str, "Peak")
        self.assertEqual((arrow.start_time_s, arrow.start_value_f,
                          arrow.end_time_s, arrow.end_value_f,
                          arrow.color_str),
                         (0.0, 1.0, 2.0, 3.0, "#ff8000"))
        self.assertEqual(plot_state_tuple(self.plot)[6][0][-1], "Peak")
        for name_str in ("", " ", "Peak"):
            self.assertFalse(self.plot.rename_arrow(0, name_str))
        self.assertFalse(self.plot.rename_arrow(3, "Other"))
        self.assertEqual(arrow.name_str, "Peak")


class DeltaMarkerNameLayoutTest(unittest.TestCase):
    """Delta marker names in the layout file."""

    def setUp(self) -> None:
        """Build a workspace with one named Delta X marker and the
        signals to rebuild it.

        Inputs: none.
        Outputs: none.
        """
        self.workspace, self.plot = make_workspace_with_plot()
        self.plot.add_delta_marker(DELTA_X_KIND_STR, ("Speed", 1.0, 2.0),
                                   ("Torque", 3.0, 6.0), name_str="Lap")
        time_array = np.arange(0.0, 5.0)
        self.signal_dict = {"Time": time_array, "Speed": 2.0 * time_array,
                            "Torque": 2.0 * time_array}

    def layout_dict(self) -> dict:
        """Return the layout file content of the workspace, read back.

        Inputs: none.
        Outputs: the dict read from the JSON text.
        """
        return json.loads(layout_text(build_layout_dict(
            self.workspace, self.workspace.tab_list[0].tab_id_i,
            (0.0, 4.0), False)))

    def load(self, layout_dict: dict) -> tuple:
        """Load a layout into a new workspace.

        Inputs:
            layout_dict: the layout file content.
        Outputs: (names of the rebuilt delta markers, report lines).
        """
        workspace = Workspace(random.Random(2))
        result = rebuild_layout(workspace, layout_dict, self.signal_dict,
                                self.signal_dict["Time"])
        name_list = [delta_marker.name_str for tab in workspace.tab_list
                     for plot in tab.plot_list
                     for delta_marker in plot.delta_marker_list]
        return name_list, result.report.text()

    def delta_entry(self, layout_dict: dict) -> dict:
        """Return the first delta marker entry of a layout.

        Inputs:
            layout_dict: the layout file content.
        Outputs: the dict of the entry.
        """
        return layout_dict["tabs"][0]["plots"][0]["delta_markers"][0]

    @covers("LLFR-00225", "LLFR-00430", "HLFR-00097")
    def test_name_saved_and_loaded(self) -> None:
        """The name is written under "name" and given back on load,
        with nothing reported.

        Inputs: none.
        Outputs: none.
        """
        layout_dict = self.layout_dict()
        self.assertEqual(self.delta_entry(layout_dict)["name"], "Lap")
        name_list, report_str = self.load(layout_dict)
        self.assertEqual(name_list, ["Lap"])
        self.assertNotIn("Lap", report_str)

    @covers("LLFR-00857", "LLFR-01200", "LLFR-00237", "HLFR-00097")
    def test_missing_name_gets_a_default_name_reported(self) -> None:
        """A delta marker with no saved name gets the default name, and
        the report lists it as a replaced value.

        Inputs: none.
        Outputs: none.
        """
        layout_dict = self.layout_dict()
        del self.delta_entry(layout_dict)["name"]
        name_list, report_str = self.load(layout_dict)
        self.assertEqual(name_list, ["Delta X 1"])
        self.assertEqual(
            report_str, "Values replaced:\n\nName of the Delta X marker "
            "between 1 s and 3 s in plot 1 of tab \"Tab 1\" is missing; "
            "replaced by \"Delta X 1\".")

    @covers("LLFR-00858", "LLFR-00859", "HLFR-00097")
    def test_unusable_name_is_replaced_and_reported(self) -> None:
        """An empty name or one that is not a text gets the default
        name, and the report lists it with the replaced values.

        Inputs: none.
        Outputs: none.
        """
        for name_value in ("", "   ", 12, None, ["Lap"]):
            with self.subTest(name=name_value):
                layout_dict = self.layout_dict()
                self.delta_entry(layout_dict)["name"] = name_value
                name_list, report_str = self.load(layout_dict)
                self.assertEqual(name_list, ["Delta X 1"])
                self.assertIn("Values replaced:", report_str)
                self.assertIn("replaced by \"Delta X 1\"", report_str)


if __name__ == "__main__":
    unittest.main()
