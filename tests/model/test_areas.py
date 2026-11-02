"""Tests for the areas of the workspace model (HLFR-00066 to HLFR-00069).

No Qt needed: the areas are plain model objects shared by every time
plot, like the vertical markers.
"""

import random
import unittest

from tests.support import covers

from model.curve_colors import MARKER_COLOR_STR
from model.workspace import (
    DEFAULT_AREA_COLOR_STR, FREQUENCY_PLOT_KIND_STR, Workspace,
    area_span_tuple, spans_overlap_b)


def area_name_list(workspace) -> list:
    """Return the names of the areas of a workspace.

    Inputs:
        workspace: the Workspace.
    Outputs: a list of names in creation order.
    """
    return [area.name_str for area in workspace.area_list]


class AreaModelTestCase(unittest.TestCase):
    """Shared setup: a workspace with one tab holding one time plot."""

    def setUp(self) -> None:
        """Create the workspace and a plot with a curve.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace(random.Random(3))
        self.tab = self.workspace.tab_list[0]
        self.plot = self.workspace.add_plot(self.tab.tab_id_i)
        self.plot.add_curve("speed")


class AreaSpanTest(unittest.TestCase):
    """The helpers that check spans and overlaps."""

    @covers("LLFR-00304")
    def test_span_is_sorted_and_must_be_finite_and_non_empty(self) -> None:
        """area_span_tuple sorts the times and refuses empty or
        infinite spans.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(area_span_tuple(3, 1.5), (1.5, 3.0))
        for start_s, end_s in ((1.0, 1.0), (float("nan"), 2.0),
                               (0.0, float("inf"))):
            with self.subTest(span=(start_s, end_s)):
                with self.assertRaises(ValueError):
                    area_span_tuple(start_s, end_s)

    @covers("LLFR-00304")
    def test_shared_edge_is_no_overlap(self) -> None:
        """Two spans that only share an edge do not overlap; any common
        part does.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(spans_overlap_b(1.0, 2.0, 2.0, 3.0))
        self.assertFalse(spans_overlap_b(2.0, 3.0, 1.0, 2.0))
        self.assertTrue(spans_overlap_b(1.0, 2.1, 2.0, 3.0))
        self.assertTrue(spans_overlap_b(1.0, 4.0, 2.0, 3.0))
        self.assertTrue(spans_overlap_b(2.5, 2.6, 2.0, 3.0))


class CreateAreaTest(AreaModelTestCase):
    """Creating areas (LLFR-00304, LLFR-00309)."""

    @covers("LLFR-00304", "LLFR-00309", "LLFR-00310")
    def test_create_names_area_n_and_sorts_the_times(self) -> None:
        """New areas are named "Area 1", "Area 2", with sorted times.

        Inputs: none.
        Outputs: none.
        """
        first_area = self.workspace.add_area(2.0, 1.0)
        second_area = self.workspace.add_area(3.0, 4.0)
        self.assertEqual(area_name_list(self.workspace),
                         ["Area 1", "Area 2"])
        self.assertEqual((first_area.start_s, first_area.end_s), (1.0, 2.0))
        self.assertNotEqual(first_area.area_id_i, second_area.area_id_i)
        self.assertEqual(self.workspace.area_state_tuple(), (
            (first_area.area_id_i, "Area 1", 1.0, 2.0,
             DEFAULT_AREA_COLOR_STR),
            (second_area.area_id_i, "Area 2", 3.0, 4.0,
             DEFAULT_AREA_COLOR_STR)))

    @covers("LLFR-00304", "LLFR-00309")
    def test_overlap_or_empty_span_creates_nothing(self) -> None:
        """An overlapping or empty area is refused and uses no number;
        an area that shares an edge is accepted.

        Inputs: none.
        Outputs: none.
        """
        self.workspace.add_area(1.0, 2.0)
        self.assertIsNone(self.workspace.add_area(1.5, 3.0))
        self.assertIsNone(self.workspace.add_area(0.0, 5.0))
        self.assertIsNone(self.workspace.add_area(3.0, 3.0))
        self.assertIsNone(self.workspace.add_area(float("nan"), 3.0))
        shared_edge_area = self.workspace.add_area(2.0, 3.0)
        self.assertIsNotNone(shared_edge_area)
        self.assertEqual(shared_edge_area.name_str, "Area 2")
        self.assertIsNotNone(self.workspace.add_area(0.5, 1.0))
        self.assertEqual(area_name_list(self.workspace),
                         ["Area 1", "Area 2", "Area 3"])

    @covers("LLFR-00309")
    def test_numbers_never_reused_until_reset(self) -> None:
        """A deleted area's number, or one whose creation is undone, is
        not reused; opening a file (reset) restarts at "Area 1".

        Inputs: none.
        Outputs: none.
        """
        snapshot = self.workspace.snapshot()
        area = self.workspace.add_area(1.0, 2.0)
        self.workspace.restore(snapshot)
        self.assertEqual(self.workspace.area_list, [])
        self.assertEqual(self.workspace.add_area(1.0, 2.0).name_str,
                         "Area 2")
        self.workspace.remove_area(self.workspace.area_list[0].area_id_i)
        self.assertFalse(self.workspace.remove_area(area.area_id_i))
        self.assertEqual(self.workspace.add_area(1.0, 2.0).name_str,
                         "Area 3")
        self.workspace.reset()
        self.assertEqual(self.workspace.area_list, [])
        plot = self.workspace.add_plot(self.workspace.tab_list[0].tab_id_i)
        plot.add_curve("speed")
        self.assertEqual(self.workspace.add_area(1.0, 2.0).name_str,
                         "Area 1")

    @covers("LLFR-00309", "LLFR-00319")
    def test_saved_name_is_kept_and_uses_up_its_number(self) -> None:
        """A named area keeps its name; "Area 7" makes the next default
        name "Area 8".

        Inputs: none.
        Outputs: none.
        """
        self.workspace.add_area(1.0, 2.0, "  Start-up  ")
        self.workspace.add_area(2.0, 3.0, "Area 7")
        self.workspace.add_area(4.0, 5.0)
        self.assertEqual(area_name_list(self.workspace),
                         ["Start-up", "Area 7", "Area 8"])


class ChangeAreaTest(AreaModelTestCase):
    """Moving, resizing, renaming and deleting areas."""

    def setUp(self) -> None:
        """Add two areas, from 1 s to 2 s and from 4 s to 5 s.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.first_area = self.workspace.add_area(1.0, 2.0)
        self.second_area = self.workspace.add_area(4.0, 5.0)

    @covers("LLFR-00312", "LLFR-00313")
    def test_move_and_resize_never_overlap(self) -> None:
        """A span may move up to the next area's edge but not over it.

        Inputs: none.
        Outputs: none.
        """
        area_id_i = self.first_area.area_id_i
        self.assertTrue(self.workspace.set_area_span(area_id_i, 3.0, 4.0))
        self.assertEqual((self.first_area.start_s, self.first_area.end_s),
                         (3.0, 4.0))
        self.assertFalse(self.workspace.set_area_span(area_id_i, 3.5, 4.5))
        self.assertFalse(self.workspace.set_area_span(area_id_i, 3.0, 4.0))
        self.assertFalse(self.workspace.set_area_span(area_id_i, 2.0, 2.0))
        self.assertFalse(self.workspace.set_area_span(999, 0.0, 0.5))
        self.assertTrue(self.workspace.set_area_span(area_id_i, 3.5, 0.5))
        self.assertEqual((self.first_area.start_s, self.first_area.end_s),
                         (0.5, 3.5))

    @covers("LLFR-00315")
    def test_rename_strips_and_blank_keeps_the_name(self) -> None:
        """A name is stored without surrounding spaces; a blank one is
        refused.

        Inputs: none.
        Outputs: none.
        """
        area_id_i = self.first_area.area_id_i
        self.assertTrue(self.workspace.rename_area(area_id_i, "  Run  "))
        self.assertEqual(self.first_area.name_str, "Run")
        self.assertFalse(self.workspace.rename_area(area_id_i, "   "))
        self.assertFalse(self.workspace.rename_area(area_id_i, ""))
        self.assertFalse(self.workspace.rename_area(999, "X"))
        self.assertEqual(self.first_area.name_str, "Run")

    @covers("LLFR-00309", "LLFR-00315")
    def test_rename_to_area_n_uses_up_n(self) -> None:
        """Renaming an area "Area 7" makes the next new area "Area 8".

        Inputs: none.
        Outputs: none.
        """
        self.workspace.rename_area(self.first_area.area_id_i, "Area 7")
        self.assertEqual(self.workspace.add_area(6.0, 7.0).name_str,
                         "Area 8")
        self.workspace.rename_area(self.second_area.area_id_i, "Area 3")
        self.assertEqual(self.workspace.add_area(8.0, 9.0).name_str,
                         "Area 9")

    @covers("LLFR-00316")
    def test_remove_area(self) -> None:
        """Removing an area leaves the others.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(self.workspace.remove_area(
            self.first_area.area_id_i))
        self.assertEqual(self.workspace.area_list, [self.second_area])

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00192")
    def test_areas_are_part_of_the_undo_state(self) -> None:
        """Every change of an area changes the state; a snapshot taken
        before restores the areas, and does not change afterwards.

        Inputs: none.
        Outputs: none.
        """
        snapshot = self.workspace.snapshot()
        area_id_i = self.first_area.area_id_i
        for action in (
                lambda: self.workspace.set_area_span(area_id_i, 2.0, 3.0),
                lambda: self.workspace.rename_area(area_id_i, "New"),
                lambda: self.workspace.remove_area(area_id_i),
                lambda: self.workspace.add_area(6.0, 7.0)):
            action()
            self.assertFalse(self.workspace.is_unchanged_since(snapshot))
            self.workspace.restore(snapshot)
            self.assertTrue(self.workspace.is_unchanged_since(snapshot))
        self.assertEqual(area_name_list(self.workspace),
                         ["Area 1", "Area 2"])
        self.workspace.rename_area(self.workspace.area_list[0].area_id_i,
                                   "Changed")
        self.assertEqual(snapshot.area_list[0].name_str, "Area 1")


class AreaColorTest(AreaModelTestCase):
    """The color of an area (LLFR-00351)."""

    @covers("LLFR-00351", "LLFR-00305", "LLFR-00319", "LLFR-00388")
    def test_any_color_and_new_areas_get_the_default(self) -> None:
        """A new area gets the reserved marker color; an area may be
        given any "#rrggbb" color, kept in lowercase; a value that is not
        written as "#rrggbb" (also the former color names) gives the
        default.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(DEFAULT_AREA_COLOR_STR, MARKER_COLOR_STR)
        self.assertEqual(self.workspace.add_area(1.0, 2.0).color_str,
                         DEFAULT_AREA_COLOR_STR)
        for index_i, color_value in enumerate(
                ("Orange", "Purple", "#12345", "#1234567", "12ab34",
                 "#12ab3g", None, 0x12AB34)):
            start_s = 3.0 + 2.0 * index_i
            self.assertEqual(self.workspace.add_area(
                start_s, start_s + 1.0, "", color_value).color_str,
                DEFAULT_AREA_COLOR_STR)
        self.assertEqual(self.workspace.add_area(
            50.0, 51.0, "", "#12AB34").color_str, "#12ab34")
        self.assertEqual(self.workspace.add_area(
            52.0, 53.0, "", "#000000").color_str, "#000000")

    @covers("LLFR-00351", "LLFR-00140", "LLFR-00138", "LLFR-00390")
    def test_set_color_is_part_of_the_undo_state(self) -> None:
        """A color change of a known area to another "#rrggbb" color
        changes the state; the same color (in any case), a value that is
        not "#rrggbb" or an unknown area changes nothing.

        Inputs: none.
        Outputs: none.
        """
        area = self.workspace.add_area(1.0, 2.0)
        snapshot = self.workspace.snapshot()
        self.assertFalse(self.workspace.set_area_color(
            area.area_id_i, DEFAULT_AREA_COLOR_STR.upper()))
        self.assertFalse(self.workspace.set_area_color(area.area_id_i,
                                                       "Blue"))
        self.assertFalse(self.workspace.set_area_color(area.area_id_i,
                                                       "#abc"))
        self.assertFalse(self.workspace.set_area_color(999, "#2f7dff"))
        self.assertTrue(self.workspace.is_unchanged_since(snapshot))
        self.assertTrue(self.workspace.set_area_color(area.area_id_i,
                                                      "#2F7DFF"))
        self.assertFalse(self.workspace.is_unchanged_since(snapshot))
        self.assertEqual(self.workspace.area_state_tuple()[0][4], "#2f7dff")
        self.workspace.restore(snapshot)
        self.assertEqual(self.workspace.area_list[0].color_str,
                         DEFAULT_AREA_COLOR_STR)


class AreasWithoutPlotsTest(AreaModelTestCase):
    """Areas go with the last plot, like the vertical markers."""

    @covers("LLFR-00310", "LLFR-00205")
    def test_last_plot_deleted_deletes_the_areas(self) -> None:
        """Deleting the last plot deletes every area in the same change,
        so the snapshot before it brings them back.

        Inputs: none.
        Outputs: none.
        """
        self.workspace.add_area(1.0, 2.0)
        snapshot = self.workspace.snapshot()
        self.workspace.delete_plot(self.plot.plot_id_i)
        self.assertEqual(self.workspace.area_list, [])
        self.workspace.restore(snapshot)
        self.assertEqual(area_name_list(self.workspace), ["Area 1"])

    @covers("LLFR-00310")
    def test_last_tab_with_plots_and_last_curve(self) -> None:
        """Deleting the tab of the last plot, or the last curve, deletes
        every area; while another plot exists, the areas stay.

        Inputs: none.
        Outputs: none.
        """
        other_tab = self.workspace.add_tab()
        other_plot = self.workspace.add_plot(other_tab.tab_id_i,
                                             FREQUENCY_PLOT_KIND_STR)
        other_plot.add_curve("fft")
        self.workspace.add_area(1.0, 2.0)
        self.workspace.delete_plot(self.plot.plot_id_i)
        # A frequency plot is still a plot: the areas stay for later
        # time plots.
        self.assertEqual(area_name_list(self.workspace), ["Area 1"])
        self.workspace.remove_curve(other_plot.plot_id_i, "fft")
        self.assertEqual(self.workspace.area_list, [])
        plot = self.workspace.add_plot(other_tab.tab_id_i)
        plot.add_curve("speed")
        self.workspace.add_area(1.0, 2.0)
        self.workspace.delete_tab(other_tab.tab_id_i)
        self.assertEqual(self.workspace.area_list, [])
        self.assertEqual(self.workspace.add_area(1.0, 2.0).name_str,
                         "Area 3")


if __name__ == "__main__":
    unittest.main()
