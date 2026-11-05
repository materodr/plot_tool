"""Tests for the arrows of the workspace model (issue #155).

Covers the arrows of a plot (LLFR-00372 to LLFR-00375), their moves,
rotations and stretches (LLFR-00376, LLFR-00377), their color
(LLFR-00379, LLFR-00390) and deletion (LLFR-00380), the undo snapshots
(LLFR-00140, LLFR-00138, LLFR-00192), and the layout files, which never
hold arrows and keep the arrows of the kept tabs (LLFR-00226,
LLFR-00229).
"""

import json
import math
import unittest

import numpy as np

from tests.support import covers

from model.layout_file import (
    build_layout_dict, layout_text, rebuild_layout)
from model.workspace import (
    DEFAULT_ARROW_COLOR_STR, FREQUENCY_PLOT_KIND_STR, Arrow, Workspace,
    plot_state_tuple)


class ArrowModelTest(unittest.TestCase):
    """The arrows of one plot."""

    def setUp(self) -> None:
        """Create a workspace with one plot.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace()
        self.tab = self.workspace.tab_list[0]
        self.plot = self.workspace.add_plot(self.tab.tab_id_i)

    @covers("LLFR-00372", "LLFR-00373", "LLFR-00375", "HLFR-00081",
            "LLFR-00770", "LLFR-00778")
    def test_add_keeps_both_ends_and_the_default_color(self) -> None:
        """A new arrow goes from the press to the release, with the
        arrowhead at the release, in the app's text color; any number of
        arrows can be drawn, in order.

        Inputs: none.
        Outputs: none.
        """
        arrow = self.plot.add_arrow(1.0, 2.0, 3.5, -4.0)
        self.assertIsInstance(arrow, Arrow)
        self.assertEqual((arrow.start_time_s, arrow.start_value_f,
                          arrow.end_time_s, arrow.end_value_f),
                         (1.0, 2.0, 3.5, -4.0))
        self.assertEqual(arrow.color_str, "#ff8000")
        self.assertEqual(DEFAULT_ARROW_COLOR_STR, "#ff8000")
        for index_i in range(20):
            self.plot.add_arrow(index_i, 0.0, index_i + 1.0, 1.0)
        self.assertEqual(len(self.plot.arrow_list), 21)
        self.assertEqual(self.plot.arrow_list[5].start_time_s, 4.0)

    @covers("LLFR-00372", "LLFR-00374")
    def test_ends_must_be_finite_and_apart(self) -> None:
        """Values that are not finite, or two equal ends, are refused
        and add nothing.

        Inputs: none.
        Outputs: none.
        """
        for end_tuple in ((math.nan, 0.0, 1.0, 1.0),
                          (0.0, math.inf, 1.0, 1.0),
                          (0.0, 0.0, 1.0, -math.inf),
                          (2.0, 3.0, 2.0, 3.0)):
            with self.subTest(ends=end_tuple):
                with self.assertRaises(ValueError):
                    self.plot.add_arrow(*end_tuple)
        with self.assertRaises((TypeError, ValueError)):
            self.plot.add_arrow("a", 0.0, 1.0, 1.0)
        self.assertEqual(self.plot.arrow_list, [])

    @covers("LLFR-00376", "LLFR-00377", "HLFR-00082", "HLFR-00083",
            "LLFR-00786")
    def test_set_ends_moves_rotates_and_stretches(self) -> None:
        """New ends replace the old ones, the arrowhead staying at the
        end; the same ends, an unknown index or invalid ends change
        nothing.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_arrow(0.0, 0.0, 1.0, 1.0)
        # A move keeps the length and the direction.
        self.assertTrue(self.plot.set_arrow_ends(0, 2.0, 1.0, 3.0, 2.0))
        # A rotation and stretch around the start.
        self.assertTrue(self.plot.set_arrow_ends(0, 2.0, 1.0, 2.0, 5.0))
        arrow = self.plot.arrow_list[0]
        self.assertEqual((arrow.start_time_s, arrow.start_value_f,
                          arrow.end_time_s, arrow.end_value_f),
                         (2.0, 1.0, 2.0, 5.0))
        self.assertFalse(self.plot.set_arrow_ends(0, 2.0, 1.0, 2.0, 5.0))
        for index_value in (1, -1, True, "0", None):
            self.assertFalse(self.plot.set_arrow_ends(
                index_value, 0.0, 0.0, 9.0, 9.0))
        with self.assertRaises(ValueError):
            self.plot.set_arrow_ends(0, 1.0, 1.0, 1.0, 1.0)
        with self.assertRaises(ValueError):
            self.plot.set_arrow_ends(0, math.nan, 1.0, 1.0, 2.0)
        self.assertEqual(arrow.end_value_f, 5.0)

    @covers("LLFR-00379", "LLFR-00390", "HLFR-00088", "LLFR-00811")
    def test_color_takes_any_hex_color_once(self) -> None:
        """Any "#rrggbb" color is kept in lowercase; the same color, a
        value that is not a color or an unknown index changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_arrow(0.0, 0.0, 1.0, 1.0)
        self.assertTrue(self.plot.set_arrow_color(0, "#12AB9F"))
        self.assertEqual(self.plot.arrow_list[0].color_str, "#12ab9f")
        self.assertFalse(self.plot.set_arrow_color(0, "#12ab9f"))
        for bad_value in ("red", "#12ab9", "", None, 5):
            self.assertFalse(self.plot.set_arrow_color(0, bad_value))
        self.assertFalse(self.plot.set_arrow_color(3, "#000000"))
        self.assertEqual(self.plot.arrow_list[0].color_str, "#12ab9f")

    @covers("LLFR-00380", "HLFR-00084")
    def test_remove_takes_only_that_arrow(self) -> None:
        """Removing an arrow keeps the others in order; an unknown index
        removes nothing.

        Inputs: none.
        Outputs: none.
        """
        for index_i in range(3):
            self.plot.add_arrow(index_i, 0.0, index_i, 1.0)
        self.assertTrue(self.plot.remove_arrow(1))
        self.assertEqual([arrow.start_time_s
                          for arrow in self.plot.arrow_list], [0.0, 2.0])
        self.assertFalse(self.plot.remove_arrow(2))
        self.assertFalse(self.plot.remove_arrow(-1))
        self.assertEqual(len(self.plot.arrow_list), 2)

    @covers("LLFR-00375", "LLFR-00777")
    def test_arrows_belong_to_their_plot(self) -> None:
        """An arrow is only in its own plot, and goes away with it; a
        frequency plot holds arrows too.

        Inputs: none.
        Outputs: none.
        """
        other_plot = self.workspace.add_plot(self.tab.tab_id_i)
        frequency_plot = self.workspace.add_plot(
            self.tab.tab_id_i, FREQUENCY_PLOT_KIND_STR)
        self.plot.add_arrow(0.0, 0.0, 1.0, 1.0)
        frequency_plot.add_arrow(5.0, 0.1, 20.0, 0.5)
        self.assertEqual(other_plot.arrow_list, [])
        self.assertEqual(frequency_plot.arrow_list[0].end_time_s, 20.0)
        self.assertTrue(self.workspace.delete_plot(self.plot.plot_id_i))
        remaining_list = [arrow for tab in self.workspace.tab_list
                          for plot in tab.plot_list
                          for arrow in plot.arrow_list]
        self.assertEqual(len(remaining_list), 1)

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00192", "HLFR-00040")
    def test_snapshots_hold_the_arrows(self) -> None:
        """The plot state holds every arrow with its ends, color and
        name, so a change is seen; a restored snapshot brings the arrows
        back and shares nothing with the live plot.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_arrow(0.0, 0.0, 1.0, 1.0)
        state_tuple = plot_state_tuple(self.plot)
        self.assertEqual(state_tuple[6],
                         ((0.0, 0.0, 1.0, 1.0, "#ff8000", "Arrow 1", 1,
                           "dashed"),))
        # The kind stays last and the text notes stay at index 5.
        self.assertEqual(state_tuple[-1], self.plot.kind_str)
        self.assertEqual(state_tuple[5], ())
        snapshot = self.workspace.snapshot()
        for change_function in (
                lambda: self.plot.set_arrow_color(0, "#ff0000"),
                lambda: self.plot.set_arrow_ends(0, 0.0, 0.0, 2.0, 2.0),
                lambda: self.plot.add_arrow(5.0, 5.0, 6.0, 6.0),
                lambda: self.plot.remove_arrow(0)):
            with self.subTest(change=change_function):
                self.assertTrue(change_function())
                self.assertFalse(self.workspace.is_unchanged_since(snapshot))
                self.workspace.restore(snapshot)
                self.plot = self.workspace.find_plot(self.plot.plot_id_i)
                self.assertTrue(self.workspace.is_unchanged_since(snapshot))
        restored_arrow = self.plot.arrow_list[0]
        restored_arrow.color_str = "#000000"
        self.assertEqual(snapshot.tab_list[0].plot_list[0]
                         .arrow_list[0].color_str, "#ff8000")


class ArrowLayoutTest(unittest.TestCase):
    """Arrows and layout files (LLFR-00226, LLFR-00229)."""

    def setUp(self) -> None:
        """Create a workspace with an arrow on a plot with one curve.

        Inputs: none.
        Outputs: none.
        """
        self.time_array = np.linspace(0.0, 4.0, 41)
        self.signal_dict = {"Time": self.time_array,
                            "speed": self.time_array * 2.0}
        self.workspace = Workspace()
        tab = self.workspace.tab_list[0]
        self.plot = self.workspace.add_plot(tab.tab_id_i)
        self.plot.add_curve("speed")
        self.plot.add_arrow(0.5, 1.0, 2.5, 6.0)
        self.plot.set_arrow_color(0, "#aa00cc")

    @covers("LLFR-00226")
    def test_layout_file_holds_no_arrow(self) -> None:
        """The layout text names no arrow, no arrow end and no arrow
        color.

        Inputs: none.
        Outputs: none.
        """
        layout_dict = build_layout_dict(
            self.workspace, self.workspace.tab_list[0].tab_id_i, (),
            False)
        text_str = layout_text(layout_dict)
        self.assertNotIn("arrow", text_str.lower())
        self.assertNotIn("aa00cc", text_str.lower())
        plot_entry_dict = json.loads(text_str)["tabs"][0]["plots"][0]
        self.assertEqual(sorted(plot_entry_dict),
                         ["curves", "data_tips", "delta_markers", "shapes"])

    @covers("LLFR-00226", "LLFR-00229", "LLFR-00473", "LLFR-00474")
    def test_loading_keeps_the_arrows_of_the_kept_tabs(self) -> None:
        """Loading a layout adds tabs after the current ones, whose
        arrows stay unchanged, and the new plots have no arrow.

        Inputs: none.
        Outputs: none.
        """
        layout_dict = json.loads(layout_text(build_layout_dict(
            self.workspace, self.workspace.tab_list[0].tab_id_i, (),
            False)))
        rebuild_layout(self.workspace, layout_dict, self.signal_dict,
                       self.time_array)
        self.assertEqual(len(self.workspace.tab_list), 2)
        kept_plot = self.workspace.tab_list[0].plot_list[0]
        self.assertIs(kept_plot, self.plot)
        self.assertEqual(len(kept_plot.arrow_list), 1)
        self.assertEqual(kept_plot.arrow_list[0].color_str, "#aa00cc")
        self.assertEqual(kept_plot.arrow_list[0].end_value_f, 6.0)
        new_plot = self.workspace.tab_list[1].plot_list[0]
        self.assertEqual(new_plot.arrow_list, [])


if __name__ == "__main__":
    unittest.main()
