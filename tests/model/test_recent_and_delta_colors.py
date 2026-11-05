"""Tests for the recent colors rules, the delta marker colors of the
workspace and their layout entries (issue #167): HLFR-00088, HLFR-00092.
No Qt is needed.
"""

import random
import unittest

from tests.support import covers
from tests.model.test_layout_file import (
    LayoutRebuildTestCase, curve, make_rich_workspace, minimal_layout,
    one_plot_tab)

from model.curve_colors import MARKER_COLOR_STR
from model.layout_file import (
    build_layout_dict, layout_text, parse_layout_text)
from model.recent_colors import (
    MAXIMUM_RECENT_COLORS_I, cleaned_recent_colors, recent_colors_after_use)
from model.workspace import (
    DEFAULT_DELTA_MARKER_COLOR_STR, DELTA_X_KIND_STR, DELTA_Y_KIND_STR,
    Workspace)


def color_number(number_i: int) -> str:
    """Return a distinct "#rrggbb" color for a number.

    Inputs:
        number_i: a number from 0 to 255.
    Outputs: the color "#0000nn".
    """
    return f"#0000{number_i:02x}"


class RecentColorRulesTest(unittest.TestCase):
    """The rules of the recent colors list (LLFR-00419)."""

    @covers("LLFR-00419", "LLFR-00838")
    def test_used_color_goes_first_without_repeats(self) -> None:
        """A used color goes first and is removed from a later place;
        the case of the digits does not make another color.

        Inputs: none.
        Outputs: none.
        """
        color_list = recent_colors_after_use([], "#AA0000")
        self.assertEqual(color_list, ["#aa0000"])
        color_list = recent_colors_after_use(color_list, "#00bb00")
        color_list = recent_colors_after_use(color_list, "#0000cc")
        self.assertEqual(color_list, ["#0000cc", "#00bb00", "#aa0000"])
        color_list = recent_colors_after_use(color_list, "#AA0000")
        self.assertEqual(color_list, ["#aa0000", "#0000cc", "#00bb00"])
        # The color already first stays first, once.
        self.assertEqual(recent_colors_after_use(color_list, "#aa0000"),
                         color_list)

    @covers("LLFR-00419", "LLFR-00838")
    def test_only_the_last_eight_colors(self) -> None:
        """The list keeps the 8 most recent different colors.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(MAXIMUM_RECENT_COLORS_I, 8)
        color_list = []
        for number_i in range(12):
            color_list = recent_colors_after_use(color_list,
                                                 color_number(number_i))
        self.assertEqual(color_list, [color_number(number_i)
                                      for number_i in range(11, 3, -1)])
        # A color that fell out comes back first; the oldest goes.
        color_list = recent_colors_after_use(color_list, color_number(0))
        self.assertEqual(color_list[0], color_number(0))
        self.assertEqual(len(color_list), 8)
        self.assertNotIn(color_number(4), color_list)

    @covers("LLFR-00419", "LLFR-00838")
    def test_value_that_is_not_a_color_changes_nothing(self) -> None:
        """A used value that is not "#rrggbb" leaves the list as it is,
        and the given list is never changed in place.

        Inputs: none.
        Outputs: none.
        """
        start_list = ["#112233"]
        for value in ("blue", "#12345", None, 7, ""):
            self.assertEqual(recent_colors_after_use(start_list, value),
                             ["#112233"])
        recent_colors_after_use(start_list, "#445566")
        self.assertEqual(start_list, ["#112233"])

    @covers("LLFR-00419", "LLFR-00840")
    def test_stored_values_are_cleaned(self) -> None:
        """Values read from the settings: a single text, repeats, wrong
        entries and too many colors are cleaned; values that cannot be
        read give an empty list.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(cleaned_recent_colors("#ABCDEF"), ["#abcdef"])
        self.assertEqual(cleaned_recent_colors(
            ["#111111", "bad", "#111111", 5, "#222222"]),
            ["#111111", "#222222"])
        self.assertEqual(cleaned_recent_colors(
            [color_number(number_i) for number_i in range(10)]),
            [color_number(number_i) for number_i in range(8)])
        for value in (None, 3, {"a": 1}, "not a color", [], ()):
            self.assertEqual(cleaned_recent_colors(value), [])


class DeltaMarkerColorModelTest(unittest.TestCase):
    """The color of a delta marker in the workspace (LLFR-00172,
    LLFR-00409)."""

    def setUp(self) -> None:
        """Create a plot with Speed and two delta markers.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace(random.Random(2))
        self.plot = self.workspace.add_plot(
            self.workspace.tab_list[0].tab_id_i)
        self.plot.add_curve("Speed")
        self.first = self.plot.add_delta_marker(
            DELTA_X_KIND_STR, ("Speed", 1.0, 1.0), ("Speed", 2.0, 2.0))
        self.second = self.plot.add_delta_marker(
            DELTA_Y_KIND_STR, ("Speed", 1.0, 1.0), ("Speed", 3.0, 3.0))

    @covers("LLFR-00172", "LLFR-00083", "LLFR-00660")
    def test_new_marker_has_the_marker_color(self) -> None:
        """A new delta marker has the reserved marker color, also when
        an unusable color is given.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(DEFAULT_DELTA_MARKER_COLOR_STR, MARKER_COLOR_STR)
        self.assertEqual(self.first.color_str, MARKER_COLOR_STR)
        bad = self.plot.add_delta_marker(
            DELTA_X_KIND_STR, ("Speed", 1.0, 1.0), ("Speed", 2.0, 2.0),
            "red")
        self.assertEqual(bad.color_str, MARKER_COLOR_STR)
        given = self.plot.add_delta_marker(
            DELTA_X_KIND_STR, ("Speed", 1.0, 1.0), ("Speed", 2.0, 2.0),
            "#00AA00")
        self.assertEqual(given.color_str, "#00aa00")

    @covers("LLFR-00409", "LLFR-00390", "LLFR-00811", "LLFR-00819",
            "LLFR-00820")
    def test_set_color_changes_only_that_marker(self) -> None:
        """The new color is kept in lowercase for that marker only; its
        points and value stay; the same color, a wrong value or an
        unknown id changes nothing.

        Inputs: none.
        Outputs: none.
        """
        delta_f = self.second.delta_f()
        self.assertTrue(self.plot.set_delta_marker_color(
            self.second.delta_marker_id_i, "#1F77B4"))
        self.assertEqual(self.second.color_str, "#1f77b4")
        self.assertEqual(self.first.color_str, MARKER_COLOR_STR)
        self.assertEqual(self.second.delta_f(), delta_f)
        self.assertEqual(self.second.second_point_tuple, ("Speed", 3.0, 3.0))
        self.assertFalse(self.plot.set_delta_marker_color(
            self.second.delta_marker_id_i, "#1f77b4"))
        self.assertFalse(self.plot.set_delta_marker_color(
            self.second.delta_marker_id_i, "blue"))
        self.assertFalse(self.plot.set_delta_marker_color(999, "#000000"))

    @covers("LLFR-00409", "LLFR-00140", "LLFR-00138")
    def test_color_is_part_of_the_undo_state(self) -> None:
        """A color change makes the workspace differ from a snapshot,
        and restoring the snapshot brings the old color back.

        Inputs: none.
        Outputs: none.
        """
        snapshot = self.workspace.snapshot()
        self.plot.set_delta_marker_color(self.first.delta_marker_id_i,
                                         "#00aa00")
        self.assertFalse(self.workspace.is_unchanged_since(snapshot))
        self.workspace.restore(snapshot)
        restored = self.workspace.find_plot(
            self.plot.plot_id_i).delta_marker_list[0]
        self.assertEqual(restored.color_str, MARKER_COLOR_STR)


class DeltaMarkerColorLayoutTest(LayoutRebuildTestCase):
    """Delta marker colors in a layout file (LLFR-00225 item 8,
    LLFR-00410)."""

    def delta_entry(self, **entry_dict) -> dict:
        """Return a Delta X entry between Speed at 1 s and 2 s.

        Inputs:
            entry_dict: entries to add, for example color.
        Outputs: the delta marker entry.
        """
        # LLFR-01200: a name is given, so that only a test's own
        # missing or changed values are reported.
        delta_dict = {"name": "Gap", "kind": "delta_x",
                      "first_point": {"signal": "Speed", "time": 1.0},
                      "second_point": {"signal": "Speed", "time": 2.0}}
        delta_dict.update(entry_dict)
        return delta_dict

    @covers("LLFR-00225", "LLFR-00410", "LLFR-00230", "LLFR-00237",
            "LLFR-00493", "LLFR-00821")
    def test_round_trip_keeps_each_color(self) -> None:
        """Each delta marker is saved with its color, in lowercase, and
        rebuilt with it, with nothing to report.

        Inputs: none.
        Outputs: none.
        """
        saved_workspace = make_rich_workspace()
        plot = saved_workspace.tab_list[0].plot_list[0]
        plot.set_delta_marker_color(
            plot.delta_marker_list[1].delta_marker_id_i, "#ABCDEF")
        layout_dict = build_layout_dict(saved_workspace, -1, (), False, ())
        saved_list = layout_dict["tabs"][0]["plots"][0]["delta_markers"]
        self.assertEqual([entry["color"] for entry in saved_list],
                         [MARKER_COLOR_STR, "#abcdef"])
        result = self.rebuild(parse_layout_text(layout_text(layout_dict)))
        self.assertTrue(result.report.is_empty(), result.report.text())
        rebuilt_plot = self.workspace.tab_list[0].plot_list[0]
        self.assertEqual([delta_marker.color_str for delta_marker
                          in rebuilt_plot.delta_marker_list],
                         [MARKER_COLOR_STR, "#abcdef"])

    @covers("LLFR-00410", "LLFR-00235", "LLFR-00237", "LLFR-00172",
            "LLFR-00821", "LLFR-00822", "LLFR-00823", "LLFR-00824",
            "LLFR-01200")
    def test_saved_colors_read_back(self) -> None:
        """A "#rrggbb" color in any case is used; a missing one, or any
        other value, is replaced by the default color and listed as a
        replaced value.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(minimal_layout([one_plot_tab(
            [curve("Speed")], delta_marker_list=[
                self.delta_entry(color="#00AA11"),
                self.delta_entry(),
                self.delta_entry(color="Blue"),
                self.delta_entry(color=255)])]))
        self.assertEqual([delta_marker.color_str for delta_marker
                          in self.only_plot().delta_marker_list],
                         ["#00aa11", MARKER_COLOR_STR, MARKER_COLOR_STR,
                          MARKER_COLOR_STR])
        replaced_list = result.report.replaced_line_list
        self.assertEqual(len(replaced_list), 3)
        # LLFR-00822, LLFR-01200: the missing color is listed first.
        self.assertEqual(
            replaced_list[0], "Color of the Delta X marker between "
            "1 s and 2 s in plot 1 of tab \"Tab A\" is missing; replaced "
            f"by \"{MARKER_COLOR_STR}\".")
        for replaced_str, value_str in zip(replaced_list[1:],
                                           ('"Blue"', "255")):
            self.assertIn(f"Color {value_str} of the Delta X marker",
                          replaced_str)
            self.assertIn("between 1 s and 2 s", replaced_str)
            self.assertIn(f"replaced by \"{MARKER_COLOR_STR}\"",
                          replaced_str)
        self.assertEqual(result.report.not_rebuilt_line_list, [])

    @covers("LLFR-00410", "LLFR-00822", "LLFR-01200", "LLFR-00237")
    def test_file_without_delta_colors_reports_the_default(self) -> None:
        """A delta marker with no saved color is rebuilt with the default
        color, and the load report lists it as a replaced value.

        Inputs: none.
        Outputs: none.
        """
        result = self.rebuild(minimal_layout([one_plot_tab(
            [curve("Speed")], delta_marker_list=[self.delta_entry()])]))
        self.assertEqual(result.report.replaced_line_list, [
            "Color of the Delta X marker between 1 s and 2 s in "
            "plot 1 of tab \"Tab A\" is missing; replaced by "
            f"\"{MARKER_COLOR_STR}\"."])
        self.assertEqual(result.report.not_rebuilt_line_list, [])
        self.assertEqual(self.only_plot().delta_marker_list[0].color_str,
                         MARKER_COLOR_STR)


if __name__ == "__main__":
    unittest.main()
