"""Tests for the areas in layout files (LLFR-00225 item 11, LLFR-00230,
LLFR-00237, LLFR-00319). No Qt is needed.
"""

import json
import random
import unittest

from tests.model.test_layout_file import (
    LayoutRebuildTestCase, curve, minimal_layout, one_plot_tab)
from tests.support import covers

from model.layout_file import build_layout_dict, layout_text
from model.workspace import Workspace


def area_tuple_list(workspace) -> list:
    """Return the areas of a workspace as (name, start, end).

    Inputs:
        workspace: the Workspace.
    Outputs: a list of tuples in creation order.
    """
    return [(area.name_str, area.start_s, area.end_s)
            for area in workspace.area_list]


class LayoutAreaWriteTest(unittest.TestCase):
    """Areas written to the layout file."""

    @covers("LLFR-00225", "LLFR-00227")
    def test_each_area_saved_with_name_start_and_end(self) -> None:
        """The file lists every area, in creation order, with its name
        and its times in seconds, read back as the same values.

        Inputs: none.
        Outputs: none.
        """
        workspace = Workspace(random.Random(2))
        plot = workspace.add_plot(workspace.tab_list[0].tab_id_i)
        plot.add_curve("Speed")
        workspace.add_area(0.1, 1.0 / 3.0)
        area = workspace.add_area(5.0, 7.25, "Run")
        workspace.set_area_color(area.area_id_i, "Green")
        layout_dict = build_layout_dict(workspace, -1, (), False)
        self.assertEqual(layout_dict["areas"], [
            {"name": "Area 1", "start": 0.1, "end": 1.0 / 3.0,
             "color": "Magenta"},
            {"name": "Run", "start": 5.0, "end": 7.25, "color": "Green"}])
        read_dict = json.loads(layout_text(layout_dict))
        self.assertEqual(read_dict["areas"][0]["end"], 1.0 / 3.0)
        workspace_without_area = Workspace()
        self.assertEqual(build_layout_dict(
            workspace_without_area, -1, (), False)["areas"], [])


class LayoutAreaRebuildTest(LayoutRebuildTestCase):
    """Areas rebuilt from a layout file (LLFR-00319)."""

    def layout_with_areas(self, area_entry_list: list) -> dict:
        """Return a layout of one plot of Speed with some areas.

        Inputs:
            area_entry_list: the "areas" entry.
        Outputs: the layout dict.
        """
        return minimal_layout([one_plot_tab([curve("Speed")])],
                              areas=area_entry_list)

    @covers("LLFR-00319", "LLFR-00230", "LLFR-00310", "LLFR-00237")
    def test_round_trip_rebuilds_the_areas_as_saved(self) -> None:
        """Saving and loading in an empty workspace gives the same areas
        and an empty report.

        Inputs: none.
        Outputs: none.
        """
        source = Workspace(random.Random(4))
        source.add_plot(source.tab_list[0].tab_id_i).add_curve("Speed")
        source.add_area(1.0, 2.5)
        climb = source.add_area(2.5, 4.0, "Climb")
        source.set_area_color(climb.area_id_i, "Pink")
        layout_dict = json.loads(layout_text(
            build_layout_dict(source, -1, (), False)))
        result = self.rebuild(layout_dict)
        self.assertTrue(result.report.is_empty(), result.report.text())
        self.assertEqual(area_tuple_list(self.workspace),
                         area_tuple_list(source))
        self.assertEqual(self.workspace.add_area(6.0, 7.0).name_str,
                         "Area 2")

    @covers("LLFR-00319", "LLFR-00237", "LLFR-00230")
    def test_every_reason_an_area_is_not_rebuilt(self) -> None:
        """Areas with a wrong order, times outside the file, an overlap
        with a current area or with one rebuilt before, or unreadable
        times are left out, each with its reason.

        Inputs: none.
        Outputs: none.
        """
        tab = self.workspace.tab_list[0]
        self.workspace.add_plot(tab.tab_id_i).add_curve("Speed")
        self.workspace.add_area(8.0, 9.0, "Current")
        result = self.rebuild(self.layout_with_areas([
            {"name": "Good", "start": 1.0, "end": 2.0},
            {"name": "Backwards", "start": 3.0, "end": 2.5},
            {"name": "Equal", "start": 3.0, "end": 3.0},
            {"name": "Late", "start": 9.5, "end": 10.5},
            {"name": "Early", "start": -0.5, "end": 0.5},
            {"name": "OverCurrent", "start": 7.5, "end": 8.5},
            {"name": "OverGood", "start": 1.5, "end": 2.5},
            {"name": "Touching", "start": 2.0, "end": 3.0},
            {"name": "Edge", "start": 0.0, "end": 1.0},
            {"name": "Text", "start": "1", "end": 2.0},
            "not an area"]))
        self.assertEqual(area_tuple_list(self.workspace), [
            ("Current", 8.0, 9.0), ("Good", 1.0, 2.0),
            ("Touching", 2.0, 3.0), ("Edge", 0.0, 1.0)])
        line_list = result.report.not_rebuilt_line_list
        self.assertEqual(len(line_list), 8)
        self.assertIn('"Backwards" from 3 s to 2.5 s', line_list[0])
        self.assertIn("start time is not before its end time",
                      line_list[0])
        self.assertIn("start time is not before", line_list[1])
        for line_str in line_list[2:4]:
            self.assertIn("not within the time range of the data file",
                          line_str)
            self.assertIn("0 s to 10 s", line_str)
        self.assertIn('overlaps a current area, "Current"', line_list[4])
        self.assertIn("overlaps an area already rebuilt from this file, "
                      "\"Good\"", line_list[5])
        self.assertIn("not a number", line_list[6])
        self.assertIn("not a number", line_list[7])
        self.assertIn("Not rebuilt:", result.report.text())

    @covers("LLFR-00319", "LLFR-00310", "LLFR-00231")
    def test_areas_need_a_plot(self) -> None:
        """With no plot rebuilt, no area is kept, and it is reported.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(minimal_layout(
            [one_plot_tab([curve("Gone")])],
            areas=[{"name": "A", "start": 1.0, "end": 2.0}]))
        self.assertEqual(self.workspace.area_list, [])
        self.assertIn("no plot", result.report.not_rebuilt_line_list[-1])

    @covers("LLFR-00235", "LLFR-00309", "LLFR-00237")
    def test_unusable_name_is_replaced_by_a_default_name(self) -> None:
        """An empty or non-text name becomes "Area N"; a saved "Area 4"
        uses up its number.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(self.layout_with_areas([
            {"name": "Area 4", "start": 1.0, "end": 2.0},
            {"name": "  ", "start": 3.0, "end": 4.0},
            {"start": 5.0, "end": 6.0}]))
        self.assertEqual([name_str for name_str, _, _
                          in area_tuple_list(self.workspace)],
                         ["Area 4", "Area 5", "Area 6"])
        self.assertEqual(len(result.report.replaced_line_list), 2)
        self.assertIn('replaced by "Area 5"',
                      result.report.replaced_line_list[0])

    @covers("LLFR-00319", "LLFR-00351", "LLFR-00235", "LLFR-00237")
    def test_missing_or_unknown_color_gives_the_default(self) -> None:
        """An area without "color" (an older file) gets the default color
        silently; an unknown color gets it too and is reported as a
        replaced value; a known color is kept.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(self.layout_with_areas([
            {"name": "Old", "start": 1.0, "end": 2.0},
            {"name": "Odd", "start": 3.0, "end": 4.0, "color": "Purple"},
            {"name": "Num", "start": 5.0, "end": 6.0, "color": 3},
            {"name": "Ok", "start": 7.0, "end": 8.0, "color": "Yellow"}]))
        self.assertEqual([area.color_name_str
                          for area in self.workspace.area_list],
                         ["Magenta", "Magenta", "Magenta", "Yellow"])
        replaced_list = result.report.replaced_line_list
        self.assertEqual(len(replaced_list), 2)
        self.assertIn('Color "Purple" of the area "Odd"', replaced_list[0])
        self.assertIn('replaced by "Magenta"', replaced_list[0])
        self.assertIn('Color 3 of the area "Num"', replaced_list[1])
        self.assertIn("Values replaced:", result.report.text())
        self.assertEqual(result.report.not_rebuilt_line_list, [])

    @covers("LLFR-00319", "LLFR-00230")
    def test_file_without_areas_entry_adds_none(self) -> None:
        """An older file without "areas", or with a value that is not a
        list, adds no area and keeps the current ones.

        Inputs: none.
        Outputs: none.
        """
        tab = self.workspace.tab_list[0]
        self.workspace.add_plot(tab.tab_id_i).add_curve("Speed")
        self.workspace.add_area(1.0, 2.0)
        result = self.rebuild(minimal_layout(
            [one_plot_tab([curve("Speed")])]))
        self.assertTrue(result.report.is_empty())
        self.rebuild(self.layout_with_areas("wrong"))
        self.assertEqual(area_tuple_list(self.workspace),
                         [("Area 1", 1.0, 2.0)])


if __name__ == "__main__":
    unittest.main()
