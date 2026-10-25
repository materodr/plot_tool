"""Tests for the workspace model: tabs, plots, curves and pinned tips."""

import random
import unittest

from tests.support import covers

from model.curve_colors import PALETTE_COLOR_TUPLE
from model.workspace import (
    DEFAULT_WIDTH_I, MAXIMUM_PLOTS_PER_TAB_I, PRESET_WIDTH_TUPLE, Curve,
    PinnedTip, Plot, Tab, Workspace)


def new_workspace() -> Workspace:
    """Return a workspace with a seeded random generator.

    Inputs: none.
    Outputs: a new Workspace.
    """
    return Workspace(random.Random(2026))


class TabTest(unittest.TestCase):
    """Check adding, deleting and renaming tabs."""

    @covers("LLFR-00024", "HLFR-00014")
    def test_starts_with_one_empty_tab(self) -> None:
        """A new workspace has one tab "Tab 1" with no plots.

        Inputs: none.
        Outputs: none.
        """
        workspace = Workspace()
        self.assertEqual(len(workspace.tab_list), 1)
        self.assertIsInstance(workspace.tab_list[0], Tab)
        self.assertEqual(workspace.tab_list[0].name_str, "Tab 1")
        self.assertEqual(workspace.tab_list[0].plot_list, [])

    @covers("LLFR-00026", "HLFR-00015")
    def test_add_tab_appends_named_tabs(self) -> None:
        """add_tab appends "Tab 2", "Tab 3" with new ids.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        second_tab = workspace.add_tab()
        third_tab = workspace.add_tab()
        self.assertEqual([tab.name_str for tab in workspace.tab_list],
                         ["Tab 1", "Tab 2", "Tab 3"])
        self.assertIs(workspace.tab_list[-1], third_tab)
        self.assertEqual(second_tab.plot_list, [])
        id_list = [tab.tab_id_i for tab in workspace.tab_list]
        self.assertEqual(len(set(id_list)), 3)

    @covers("LLFR-00026")
    def test_add_tab_skips_used_names(self) -> None:
        """A default name already in use is skipped.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        first_tab = workspace.tab_list[0]
        workspace.rename_tab(first_tab.tab_id_i, "Tab 2")
        self.assertEqual(workspace.add_tab().name_str, "Tab 1")
        self.assertEqual(workspace.add_tab().name_str, "Tab 3")

    @covers("LLFR-00028", "HLFR-00016")
    def test_delete_tab_removes_it_with_its_plots(self) -> None:
        """delete_tab removes the tab and its plots.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        second_tab = workspace.add_tab()
        plot = workspace.add_plot(second_tab.tab_id_i)
        self.assertTrue(workspace.delete_tab(second_tab.tab_id_i))
        self.assertIsNone(workspace.find_tab(second_tab.tab_id_i))
        self.assertIsNone(workspace.find_plot(plot.plot_id_i))
        self.assertEqual(len(workspace.tab_list), 1)

    @covers("LLFR-00066", "LLFR-00028")
    def test_last_tab_cannot_be_deleted(self) -> None:
        """With one tab, can_delete_tab is False and delete refuses.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        only_tab = workspace.tab_list[0]
        self.assertFalse(workspace.can_delete_tab())
        self.assertFalse(workspace.delete_tab(only_tab.tab_id_i))
        self.assertEqual(workspace.tab_list, [only_tab])
        second_tab = workspace.add_tab()
        self.assertTrue(workspace.can_delete_tab())
        self.assertTrue(workspace.delete_tab(only_tab.tab_id_i))
        self.assertFalse(workspace.can_delete_tab())
        self.assertFalse(workspace.delete_tab(second_tab.tab_id_i))

    @covers("LLFR-00028")
    def test_delete_unknown_tab_is_refused(self) -> None:
        """delete_tab with an unknown id returns False.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        workspace.add_tab()
        self.assertFalse(workspace.delete_tab(999))
        self.assertEqual(len(workspace.tab_list), 2)

    @covers("LLFR-00030", "HLFR-00017")
    def test_rename_strips_surrounding_spaces(self) -> None:
        """A valid name is stored without surrounding spaces.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        self.assertTrue(workspace.rename_tab(tab.tab_id_i, "  Speed  "))
        self.assertEqual(tab.name_str, "Speed")
        self.assertTrue(workspace.rename_tab(tab.tab_id_i, "Motor A"))
        self.assertEqual(tab.name_str, "Motor A")

    @covers("LLFR-00067", "LLFR-00030")
    def test_rename_with_blank_name_keeps_old_name(self) -> None:
        """"", spaces and whitespace keep the previous name.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        for blank_name_str in ("", "   ", "\t \n"):
            with self.subTest(blank_name_str=blank_name_str):
                self.assertFalse(workspace.rename_tab(tab.tab_id_i,
                                                      blank_name_str))
                self.assertEqual(tab.name_str, "Tab 1")

    @covers("LLFR-00030")
    def test_rename_unknown_tab_is_refused(self) -> None:
        """rename_tab with an unknown id returns False.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        self.assertFalse(workspace.rename_tab(999, "Name"))
        self.assertEqual(workspace.tab_list[0].name_str, "Tab 1")


class PlotInTabTest(unittest.TestCase):
    """Check adding and deleting plots in a tab."""

    @covers("LLFR-00031", "HLFR-00018", "LLFR-00069")
    def test_sixth_plot_is_refused(self) -> None:
        """A tab takes 5 plots in order; the 6th is refused.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        plot_list = []
        for _ in range(MAXIMUM_PLOTS_PER_TAB_I):
            self.assertFalse(tab.is_full())
            plot = workspace.add_plot(tab.tab_id_i)
            self.assertIsInstance(plot, Plot)
            plot_list.append(plot)
        self.assertEqual(MAXIMUM_PLOTS_PER_TAB_I, 5)
        self.assertTrue(tab.is_full())
        self.assertIsNone(workspace.add_plot(tab.tab_id_i))
        self.assertEqual(tab.plot_list, plot_list)

    @covers("LLFR-00031", "HLFR-00018")
    def test_full_tab_does_not_block_other_tabs(self) -> None:
        """A full tab doesn't stop plots in another tab.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        first_tab = workspace.tab_list[0]
        for _ in range(MAXIMUM_PLOTS_PER_TAB_I):
            workspace.add_plot(first_tab.tab_id_i)
        second_tab = workspace.add_tab()
        self.assertIsNotNone(workspace.add_plot(second_tab.tab_id_i))
        self.assertIsNone(workspace.add_plot(999))

    @covers("LLFR-00031", "LLFR-00049")
    def test_deleting_a_plot_frees_a_place(self) -> None:
        """After deleting a plot from a full tab, a new one fits.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        plot_list = [workspace.add_plot(tab.tab_id_i)
                     for _ in range(MAXIMUM_PLOTS_PER_TAB_I)]
        workspace.delete_plot(plot_list[0].plot_id_i)
        self.assertFalse(tab.is_full())
        self.assertIsNotNone(workspace.add_plot(tab.tab_id_i))

    @covers("LLFR-00049", "HLFR-00019")
    def test_delete_middle_plot_keeps_order(self) -> None:
        """Deleting a middle plot keeps the others in order.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab = workspace.tab_list[0]
        plot_list = [workspace.add_plot(tab.tab_id_i) for _ in range(4)]
        plot_list[1].add_curve("Speed")
        self.assertTrue(workspace.delete_plot(plot_list[1].plot_id_i))
        self.assertEqual(tab.plot_list,
                         [plot_list[0], plot_list[2], plot_list[3]])
        self.assertIsNone(workspace.find_plot(plot_list[1].plot_id_i))
        self.assertFalse(workspace.delete_plot(plot_list[1].plot_id_i))

    @covers("LLFR-00049")
    def test_find_plot_and_tab_of_plot(self) -> None:
        """Plots are found by id across tabs.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        first_tab = workspace.tab_list[0]
        second_tab = workspace.add_tab()
        first_plot = workspace.add_plot(first_tab.tab_id_i)
        second_plot = workspace.add_plot(second_tab.tab_id_i)
        self.assertIs(workspace.find_plot(second_plot.plot_id_i),
                      second_plot)
        self.assertIs(workspace.tab_of_plot(first_plot.plot_id_i),
                      first_tab)
        self.assertIs(second_tab.find_plot(second_plot.plot_id_i),
                      second_plot)
        self.assertIsNone(first_tab.find_plot(second_plot.plot_id_i))
        self.assertIsNone(workspace.tab_of_plot(999))
        self.assertIsNone(workspace.find_plot(999))


class CurveTest(unittest.TestCase):
    """Check curves: colors, duplicates, widths and removal."""

    def setUp(self) -> None:
        """Create a workspace with one plot.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = new_workspace()
        self.tab = self.workspace.tab_list[0]
        self.plot = self.workspace.add_plot(self.tab.tab_id_i)

    @covers("LLFR-00052", "HLFR-00023")
    def test_new_curve_has_default_width(self) -> None:
        """A new curve has width 1.

        Inputs: none.
        Outputs: none.
        """
        curve = self.plot.add_curve("Speed")
        self.assertIsInstance(curve, Curve)
        self.assertEqual(curve.signal_name_str, "Speed")
        self.assertEqual(DEFAULT_WIDTH_I, 1)
        self.assertEqual(curve.width_i, 1)

    @covers("LLFR-00033", "HLFR-00020")
    def test_first_8_curves_use_palette_in_order(self) -> None:
        """The first 8 curves take the palette colors in order.

        Inputs: none.
        Outputs: none.
        """
        color_list = [self.plot.add_curve(f"Signal {index_i}").color_str
                      for index_i in range(8)]
        self.assertEqual(color_list, list(PALETTE_COLOR_TUPLE))
        self.assertEqual(self.plot.drawn_count_i, 8)

    @covers("LLFR-00034", "HLFR-00020")
    def test_9th_to_30th_curves_have_distinct_colors(self) -> None:
        """Curves 9 to 30 get colors different from all current ones.

        Inputs: none.
        Outputs: none.
        """
        for index_i in range(30):
            curve = self.plot.add_curve(f"Signal {index_i}")
            other_color_list = [held.color_str
                                for held in self.plot.curve_list
                                if held is not curve]
            self.assertNotIn(curve.color_str, other_color_list)
        color_set = {curve.color_str for curve in self.plot.curve_list}
        self.assertEqual(len(color_set), 30)

    @covers("LLFR-00033", "LLFR-00034", "HLFR-00020")
    def test_colors_after_deletes_stay_distinct(self) -> None:
        """After deletes, new curves still get unused colors.

        Inputs: none.
        Outputs: none.
        """
        for index_i in range(8):
            self.plot.add_curve(f"Signal {index_i}")
        self.plot.remove_curve("Signal 0")
        self.plot.remove_curve("Signal 3")
        # The 9th drawn curve gets a random color, not a palette reuse.
        ninth_curve = self.plot.add_curve("Signal 8")
        self.assertEqual(self.plot.drawn_count_i, 9)
        self.assertNotIn(ninth_curve.color_str,
                         [curve.color_str for curve in self.plot.curve_list
                          if curve is not ninth_curve])
        for index_i in range(9, 20):
            self.plot.add_curve(f"Signal {index_i}")
            self.plot.remove_curve(f"Signal {index_i - 5}")
        color_list = [curve.color_str for curve in self.plot.curve_list]
        self.assertEqual(len(color_list), len(set(color_list)))

    @covers("HLFR-00020")
    def test_colors_restart_in_each_plot(self) -> None:
        """Each plot starts its colors from the palette.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_curve("Speed")
        other_plot = self.workspace.add_plot(self.tab.tab_id_i)
        self.assertEqual(other_plot.add_curve("Speed").color_str,
                         PALETTE_COLOR_TUPLE[0])

    @covers("LLFR-00056")
    def test_duplicate_curve_is_not_added(self) -> None:
        """Adding a signal twice returns None and changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_curve("Speed")
        self.assertTrue(self.plot.has_signal("Speed"))
        self.assertIsNone(self.plot.add_curve("Speed"))
        self.assertEqual(len(self.plot.curve_list), 1)
        self.assertEqual(self.plot.drawn_count_i, 1)
        self.assertFalse(self.plot.has_signal("speed"))

    @covers("LLFR-00041", "HLFR-00023")
    def test_set_width_to_each_preset(self) -> None:
        """Every preset width 1 to 5 can be set.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(PRESET_WIDTH_TUPLE, (1, 2, 3, 4, 5))
        self.plot.add_curve("Speed")
        self.plot.add_curve("Torque")
        for width_i in PRESET_WIDTH_TUPLE:
            self.plot.set_curve_width("Speed", width_i)
            self.assertEqual(self.plot.find_curve("Speed").width_i, width_i)
        self.assertEqual(self.plot.find_curve("Torque").width_i, 1)

    @covers("LLFR-00041")
    def test_invalid_width_is_rejected(self) -> None:
        """Widths outside 1 to 5 raise ValueError and change nothing.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_curve("Speed")
        self.plot.set_curve_width("Speed", 3)
        for bad_width in (0, 6, -1, 2.5, True, "2", None):
            with self.subTest(bad_width=bad_width):
                with self.assertRaises(ValueError):
                    self.plot.set_curve_width("Speed", bad_width)
                self.assertEqual(self.plot.find_curve("Speed").width_i, 3)

    @covers("LLFR-00041")
    def test_width_of_missing_signal_is_rejected(self) -> None:
        """Setting the width of a signal not in the plot raises.

        Inputs: none.
        Outputs: none.
        """
        with self.assertRaises(ValueError):
            self.plot.set_curve_width("Missing", 2)

    @covers("LLFR-00039", "HLFR-00022")
    def test_plot_remove_curve(self) -> None:
        """Plot.remove_curve removes only that curve.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_curve("Speed")
        self.plot.add_curve("Torque")
        self.assertTrue(self.plot.remove_curve("Speed"))
        self.assertEqual([curve.signal_name_str
                          for curve in self.plot.curve_list], ["Torque"])
        self.assertFalse(self.plot.remove_curve("Speed"))
        self.assertIsNone(self.plot.find_curve("Speed"))

    @covers("LLFR-00039", "LLFR-00051", "HLFR-00022")
    def test_workspace_remove_curve_keeps_non_empty_plot(self) -> None:
        """Removing one of two curves keeps the plot.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_curve("Speed")
        self.plot.add_curve("Torque")
        self.assertTrue(self.workspace.remove_curve(self.plot.plot_id_i,
                                                    "Speed"))
        self.assertIs(self.workspace.find_plot(self.plot.plot_id_i),
                      self.plot)
        self.assertFalse(self.plot.is_empty())

    @covers("LLFR-00051", "LLFR-00039", "HLFR-00019")
    def test_removing_last_curve_deletes_plot(self) -> None:
        """Removing the last curve deletes the plot; others keep order.

        Inputs: none.
        Outputs: none.
        """
        top_plot = self.plot
        middle_plot = self.workspace.add_plot(self.tab.tab_id_i)
        bottom_plot = self.workspace.add_plot(self.tab.tab_id_i)
        middle_plot.add_curve("Speed")
        self.assertTrue(self.workspace.remove_curve(middle_plot.plot_id_i,
                                                    "Speed"))
        self.assertTrue(middle_plot.is_empty())
        self.assertEqual(self.tab.plot_list, [top_plot, bottom_plot])

    @covers("LLFR-00039")
    def test_workspace_remove_curve_failures(self) -> None:
        """Unknown plot or signal returns False and changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_curve("Speed")
        self.assertFalse(self.workspace.remove_curve(999, "Speed"))
        self.assertFalse(self.workspace.remove_curve(self.plot.plot_id_i,
                                                     "Missing"))
        self.assertEqual(len(self.plot.curve_list), 1)
        self.assertEqual(self.tab.plot_list, [self.plot])


class PinnedTipTest(unittest.TestCase):
    """Check pinning and removing tips (HLFR-00025)."""

    def setUp(self) -> None:
        """Create a plot with two curves.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = new_workspace()
        tab = self.workspace.tab_list[0]
        self.plot = self.workspace.add_plot(tab.tab_id_i)
        self.plot.add_curve("Speed")
        self.plot.add_curve("Torque")

    @covers("LLFR-00045")
    def test_add_pinned_tip_stores_point(self) -> None:
        """A pinned tip keeps its signal, time and value.

        Inputs: none.
        Outputs: none.
        """
        pinned_tip = self.plot.add_pinned_tip("Speed", 1.5, -2.25)
        self.assertIsInstance(pinned_tip, PinnedTip)
        self.assertEqual(pinned_tip.signal_name_str, "Speed")
        self.assertEqual(pinned_tip.time_s, 1.5)
        self.assertEqual(pinned_tip.value_f, -2.25)
        self.assertEqual(self.plot.pinned_tip_list, [pinned_tip])

    @covers("LLFR-00045")
    def test_pinned_tip_on_missing_signal_is_rejected(self) -> None:
        """Pinning a tip on a signal not in the plot raises.

        Inputs: none.
        Outputs: none.
        """
        with self.assertRaises(ValueError):
            self.plot.add_pinned_tip("Missing", 0.0, 0.0)
        self.assertEqual(self.plot.pinned_tip_list, [])

    @covers("LLFR-00047", "LLFR-00045")
    def test_remove_pinned_tip_removes_only_that_tip(self) -> None:
        """Equal tips are removed one at a time, by identity.

        Inputs: none.
        Outputs: none.
        """
        first_tip = self.plot.add_pinned_tip("Speed", 1.0, 2.0)
        second_tip = self.plot.add_pinned_tip("Speed", 1.0, 2.0)
        self.assertTrue(self.plot.remove_pinned_tip(second_tip))
        self.assertEqual(len(self.plot.pinned_tip_list), 1)
        self.assertIs(self.plot.pinned_tip_list[0], first_tip)
        self.assertFalse(self.plot.remove_pinned_tip(second_tip))
        self.assertFalse(self.plot.remove_pinned_tip(
            PinnedTip("Speed", 1.0, 2.0)))
        self.assertTrue(self.plot.remove_pinned_tip(first_tip))
        self.assertEqual(self.plot.pinned_tip_list, [])

    @covers("LLFR-00039", "LLFR-00047")
    def test_removing_curve_removes_its_tips(self) -> None:
        """Tips of a removed curve go; tips of other curves stay.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_pinned_tip("Speed", 1.0, 2.0)
        torque_tip = self.plot.add_pinned_tip("Torque", 3.0, 4.0)
        self.plot.add_pinned_tip("Speed", 5.0, 6.0)
        self.plot.remove_curve("Speed")
        self.assertEqual(self.plot.pinned_tip_list, [torque_tip])


class ResetTest(unittest.TestCase):
    """Check reset when the file is replaced and id uniqueness."""

    @covers("LLFR-00015", "LLFR-00016", "HLFR-00014")
    def test_reset_after_many_tabs_and_plots(self) -> None:
        """reset leaves one tab "Tab 1" with no plots.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        old_plot_list = []
        for _ in range(4):
            tab = workspace.add_tab()
            workspace.rename_tab(tab.tab_id_i, "Custom")
            for _ in range(3):
                plot = workspace.add_plot(tab.tab_id_i)
                plot.add_curve("Speed")
                old_plot_list.append(plot)
        workspace.reset()
        self.assertEqual(len(workspace.tab_list), 1)
        self.assertEqual(workspace.tab_list[0].name_str, "Tab 1")
        self.assertEqual(workspace.tab_list[0].plot_list, [])
        for plot in old_plot_list:
            self.assertIsNone(workspace.find_plot(plot.plot_id_i))
        self.assertFalse(workspace.can_delete_tab())

    @covers("LLFR-00015", "LLFR-00016", "LLFR-00026")
    def test_ids_are_never_reused(self) -> None:
        """Tab and plot ids keep counting up after deletes and reset.

        Inputs: none.
        Outputs: none.
        """
        workspace = new_workspace()
        tab_id_set = {workspace.tab_list[0].tab_id_i}
        plot_id_set = set()
        for _ in range(3):
            tab = workspace.add_tab()
            self.assertNotIn(tab.tab_id_i, tab_id_set)
            tab_id_set.add(tab.tab_id_i)
            plot = workspace.add_plot(tab.tab_id_i)
            self.assertNotIn(plot.plot_id_i, plot_id_set)
            plot_id_set.add(plot.plot_id_i)
            workspace.delete_plot(plot.plot_id_i)
            workspace.delete_tab(tab.tab_id_i)
        workspace.reset()
        new_tab = workspace.tab_list[0]
        self.assertNotIn(new_tab.tab_id_i, tab_id_set)
        new_plot = workspace.add_plot(new_tab.tab_id_i)
        self.assertNotIn(new_plot.plot_id_i, plot_id_set)


if __name__ == "__main__":
    unittest.main()
