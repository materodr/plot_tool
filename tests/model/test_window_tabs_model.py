"""Model tests for undocked windows with several tabs (#205, step 5).

They check, with no Qt, the windows of the Workspace that hold several
tabs (HLFR-00126), the moves of a tab into an undocked window
(HLFR-00154), the closing of a window with all its tabs (HLFR-00139),
the tab each window shows (HLFR-00135), the tab order (HLFR-00143) and
the window numbers of the layout file (HLFR-00140, HLFR-00141).
"""

import json
import random
import unittest

from tests.support import covers
from tests.model.test_undocked_windows_model import signal_dict

from model.layout_file import (
    build_layout_dict, layout_text, parse_layout_text, rebuild_layout)
from model.workspace import Workspace


class WindowTabsTestCase(unittest.TestCase):
    """A workspace with four tabs, each with one plot."""

    def setUp(self) -> None:
        """Create four tabs with a plot each.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace(random.Random(3))
        for _ in range(3):
            self.workspace.add_tab()
        self.id_list = [tab.tab_id_i for tab in self.workspace.tab_list]
        for tab_id_i in self.id_list:
            self.workspace.add_plot(tab_id_i).add_curve("file1_Speed")

    def window_of(self, tab_id_i: int) -> int:
        """Return the window id of a tab.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: its window id, 0 for a docked tab.
        """
        return self.workspace.find_tab(tab_id_i).window_id_i

    def order(self) -> list:
        """Return the tab ids in tab order.

        Inputs: none.
        Outputs: a list of int.
        """
        return [tab.tab_id_i for tab in self.workspace.tab_list]


class AddTabToWindowTest(WindowTabsTestCase):
    """The "+" button of an undocked window adds a tab there."""

    @covers("LLFR-01203", "LLFR-00210", "LLFR-01091", "HLFR-00015")
    def test_new_tab_is_last_of_its_window(self) -> None:
        """The tab takes the next "Tab N", joins the window after its
        last tab with the window values, and the window shows it.

        Inputs: none.
        Outputs: none.
        """
        workspace = self.workspace
        self.assertTrue(workspace.undock_tab(self.id_list[1],
                                             (10, 20, 300, 200)))
        window_id_i = self.window_of(self.id_list[1])
        tab = workspace.add_tab_to_window(window_id_i)
        self.assertEqual(tab.name_str, "Tab 5")
        self.assertEqual([member.tab_id_i for member
                          in workspace.window_tab_list(window_id_i)],
                         [self.id_list[1], tab.tab_id_i])
        self.assertEqual(tuple(tab.window_tuple), (10, 20, 300, 200))
        self.assertIs(workspace.window_shown_tab(window_id_i), tab)
        # LLFR-01091: the undocked tabs stay after the docked ones.
        self.assertEqual(self.order()[-2:], [self.id_list[1], tab.tab_id_i])
        self.assertIsNone(workspace.add_tab_to_window(99))


class MoveIntoWindowTest(WindowTabsTestCase):
    """Moving tabs into undocked windows."""

    @covers("LLFR-01150", "LLFR-01158", "LLFR-01020", "LLFR-01031",
            "LLFR-01091", "HLFR-00154", "HLFR-00126")
    def test_docked_tab_joins_a_window_after_its_last_tab(self) -> None:
        """A docked tab dropped on a window goes after its last tab, is
        shown, takes the window's values and keeps its plots.

        Inputs: none.
        Outputs: none.
        """
        first_i, second_i, third_i, fourth_i = self.id_list
        self.workspace.undock_tab(second_i, (10, 20, 600, 400))
        window_id_i = self.window_of(second_i)
        self.workspace.set_window_panel(window_id_i, True, 150)
        plot_id_list = [plot.plot_id_i for plot in
                        self.workspace.find_tab(third_i).plot_list]
        self.assertTrue(self.workspace.move_tab_to_window(third_i,
                                                          window_id_i))
        third_tab = self.workspace.find_tab(third_i)
        self.assertEqual(third_tab.window_id_i, window_id_i)
        self.assertEqual(third_tab.window_tuple, (10, 20, 600, 400))
        self.assertEqual((third_tab.panel_shown_b, third_tab.panel_width_i),
                         (True, 150))
        self.assertEqual([plot.plot_id_i for plot in third_tab.plot_list],
                         plot_id_list)
        self.assertEqual([tab.tab_id_i for tab in
                          self.workspace.window_tab_list(window_id_i)],
                         [second_i, third_i])
        self.assertEqual(self.workspace.window_shown_tab(
            window_id_i).tab_id_i, third_i)
        # LLFR-01091: docked tabs first, then the window's tabs.
        self.assertEqual(self.order(), [first_i, fourth_i, second_i,
                                        third_i])

    @covers("LLFR-01151", "HLFR-00154")
    def test_tab_goes_to_the_place_of_the_drop(self) -> None:
        """With a place, the tab goes before the window's tab there.

        Inputs: none.
        Outputs: none.
        """
        first_i, second_i, third_i, fourth_i = self.id_list
        self.workspace.undock_tab(second_i)
        window_id_i = self.window_of(second_i)
        self.workspace.move_tab_to_window(third_i, window_id_i)
        self.workspace.move_tab_to_window(fourth_i, window_id_i, 0)
        self.assertEqual([tab.tab_id_i for tab in
                          self.workspace.window_tab_list(window_id_i)],
                         [fourth_i, second_i, third_i])
        self.assertEqual(self.order(), [first_i, fourth_i, second_i,
                                        third_i])

    @covers("LLFR-01144", "HLFR-00154")
    def test_last_docked_tab_stays_docked(self) -> None:
        """The last docked tab cannot join a window; nor a tab its own
        window, nor any tab an unknown window.

        Inputs: none.
        Outputs: none.
        """
        first_i, second_i, third_i, fourth_i = self.id_list
        for tab_id_i in (second_i, third_i, fourth_i):
            self.workspace.undock_tab(tab_id_i)
        window_id_i = self.window_of(second_i)
        before_list = self.order()
        self.assertFalse(self.workspace.move_tab_to_window(first_i,
                                                           window_id_i))
        self.assertFalse(self.workspace.move_tab_to_window(second_i,
                                                           window_id_i))
        self.assertFalse(self.workspace.move_tab_to_window(third_i, 999))
        self.assertEqual(self.order(), before_list)
        self.assertFalse(self.workspace.find_tab(first_i).undocked_b)

    @covers("LLFR-01152", "LLFR-01031", "LLFR-01156", "HLFR-00154")
    def test_tab_moves_between_windows(self) -> None:
        """A window's last tab moved into another window empties it, so
        it is gone; a window that keeps tabs shows its nearest one.

        Inputs: none.
        Outputs: none.
        """
        first_i, second_i, third_i, fourth_i = self.id_list
        self.workspace.undock_tab(second_i)
        self.workspace.undock_tab(third_i)
        self.workspace.undock_tab(fourth_i)
        window_a_i = self.window_of(second_i)
        window_b_i = self.window_of(third_i)
        window_c_i = self.window_of(fourth_i)
        self.workspace.move_tab_to_window(fourth_i, window_a_i)
        self.assertEqual(self.workspace.window_id_list(),
                         [window_a_i, window_b_i])
        self.assertNotIn(window_c_i, self.workspace.window_id_list())
        before_dict = self.workspace.window_order_dict()
        shown_dict = self.workspace.shown_tab_dict()
        self.assertEqual(shown_dict[window_a_i], fourth_i)
        self.workspace.move_tab_to_window(fourth_i, window_b_i)
        self.workspace.repair_window_shown_tabs(before_dict, shown_dict)
        # LLFR-01156: window A shows the tab left of the one that left.
        self.assertEqual(self.workspace.window_shown_tab(
            window_a_i).tab_id_i, second_i)
        self.assertEqual(self.workspace.window_shown_tab(
            window_b_i).tab_id_i, fourth_i)

    @covers("LLFR-01156", "HLFR-00126")
    def test_shown_tab_goes_to_the_right_when_first(self) -> None:
        """When the window's first tab leaves, the next one is shown.

        Inputs: none.
        Outputs: none.
        """
        _, second_i, third_i, fourth_i = self.id_list
        self.workspace.undock_tab(second_i)
        window_id_i = self.window_of(second_i)
        self.workspace.move_tab_to_window(third_i, window_id_i)
        self.workspace.move_tab_to_window(fourth_i, window_id_i)
        self.workspace.show_window_tab(second_i)
        before_dict = self.workspace.window_order_dict()
        shown_dict = self.workspace.shown_tab_dict()
        self.workspace.dock_tab(second_i)
        self.workspace.repair_window_shown_tabs(before_dict, shown_dict)
        self.assertEqual(self.workspace.window_shown_tab(
            window_id_i).tab_id_i, third_i)


class MoveIntoNewWindowTest(WindowTabsTestCase):
    """A tab of an undocked window moved into a new undocked window."""

    @covers("LLFR-01167", "LLFR-01168", "LLFR-01050", "LLFR-01020",
            "LLFR-01091", "HLFR-00126", "HLFR-00127")
    def test_tab_gets_a_new_window(self) -> None:
        """The tab gets a new window id, the drop's window tuple, a
        hidden panel and keeps its plot; the old window keeps its other
        tab; a window left empty is gone.

        Inputs: none.
        Outputs: none.
        """
        first_i, second_i, third_i, fourth_i = self.id_list
        self.workspace.undock_tab(second_i)
        window_a_i = self.window_of(second_i)
        self.workspace.move_tab_to_window(third_i, window_a_i)
        self.workspace.set_window_panel(window_a_i, True, 200)
        self.assertTrue(self.workspace.move_tab_to_new_window(
            second_i, (1500, 70, 900, 600)))
        window_b_i = self.window_of(second_i)
        self.assertNotIn(window_b_i, (0, window_a_i))
        tab = self.workspace.find_tab(second_i)
        self.assertEqual(tab.window_tuple, (1500, 70, 900, 600))
        self.assertFalse(tab.panel_shown_b)
        self.assertEqual(tab.panel_width_i, 0)
        self.assertEqual(len(tab.plot_list), 1)
        self.assertEqual(self.workspace.window_id_list(),
                         [window_a_i, window_b_i])
        self.assertEqual(self.order(), [first_i, fourth_i, third_i,
                                        second_i])
        # LLFR-01168: the last tab of window A leaves; A is gone.
        self.assertTrue(self.workspace.move_tab_to_new_window(
            third_i, (10, 20, 300, 200)))
        window_c_i = self.window_of(third_i)
        self.assertEqual(self.workspace.window_id_list(),
                         [window_b_i, window_c_i])

    @covers("LLFR-01167", "HLFR-00126")
    def test_docked_or_unknown_tab_is_not_moved(self) -> None:
        """A docked tab or an unknown id changes nothing.

        Inputs: none.
        Outputs: none.
        """
        first_i = self.id_list[0]
        before_list = self.order()
        self.assertFalse(self.workspace.move_tab_to_new_window(
            first_i, (1, 2, 3, 4)))
        self.assertFalse(self.workspace.move_tab_to_new_window(
            999, (1, 2, 3, 4)))
        self.assertEqual(self.order(), before_list)
        self.assertEqual(self.workspace.window_id_list(), [])


class WindowTabOrderTest(WindowTabsTestCase):
    """Reordering, docking, closing and undoing in windows."""

    def one_window_of_three(self) -> int:
        """Put tabs 2 to 4 in one window.

        Inputs: none.
        Outputs: the window id.
        """
        _, second_i, third_i, fourth_i = self.id_list
        self.workspace.undock_tab(second_i)
        window_id_i = self.window_of(second_i)
        self.workspace.move_tab_to_window(third_i, window_id_i)
        self.workspace.move_tab_to_window(fourth_i, window_id_i)
        return window_id_i

    @covers("LLFR-01157", "LLFR-01166", "LLFR-01089", "LLFR-01090",
            "HLFR-00143")
    def test_reorder_in_a_window(self) -> None:
        """A tab moves within its window; its own place changes nothing.

        Inputs: none.
        Outputs: none.
        """
        first_i, second_i, third_i, fourth_i = self.id_list
        window_id_i = self.one_window_of_three()
        self.assertTrue(self.workspace.move_tab_in_window(fourth_i, 0))
        self.assertEqual(self.order(), [first_i, fourth_i, second_i,
                                        third_i])
        self.assertFalse(self.workspace.move_tab_in_window(fourth_i, 0))
        self.assertFalse(self.workspace.move_tab_in_window(first_i, 1))
        self.assertEqual(self.workspace.window_id_list(), [window_id_i])

    @covers("LLFR-01028", "LLFR-01029", "HLFR-00125", "HLFR-00126")
    def test_dock_keeps_the_other_tabs_in_the_window(self) -> None:
        """Docking one tab of three leaves two in the window; docking the
        last one closes it.

        Inputs: none.
        Outputs: none.
        """
        first_i, second_i, third_i, fourth_i = self.id_list
        window_id_i = self.one_window_of_three()
        self.workspace.dock_tab(third_i)
        self.assertEqual([tab.tab_id_i for tab in
                          self.workspace.window_tab_list(window_id_i)],
                         [second_i, fourth_i])
        self.assertEqual(self.order(), [first_i, third_i, second_i,
                                        fourth_i])
        self.workspace.dock_tab(second_i)
        self.workspace.dock_tab(fourth_i)
        self.assertEqual(self.workspace.window_id_list(), [])

    @covers("LLFR-01073", "LLFR-01074", "LLFR-01059", "HLFR-00139")
    def test_window_closed_with_all_its_tabs_and_undone(self) -> None:
        """delete_window removes every tab of the window; a restore of
        the snapshot brings back the window with its tabs in order.

        Inputs: none.
        Outputs: none.
        """
        first_i, second_i, third_i, fourth_i = self.id_list
        window_id_i = self.one_window_of_three()
        snapshot = self.workspace.snapshot(first_i)
        self.assertEqual(self.workspace.delete_window(window_id_i),
                         [second_i, third_i, fourth_i])
        self.assertEqual(self.order(), [first_i])
        self.assertFalse(self.workspace.is_unchanged_since(snapshot))
        self.workspace.restore(snapshot)
        self.assertEqual([tab.tab_id_i for tab in
                          self.workspace.window_tab_list(window_id_i)],
                         [second_i, third_i, fourth_i])
        # Window ids are never handed out again.
        self.assertGreater(self.workspace.next_window_id_i, window_id_i)
        self.assertEqual(self.workspace.delete_window(999), [])

    @covers("LLFR-01153", "LLFR-00140", "HLFR-00154")
    def test_move_changes_the_undo_state(self) -> None:
        """A move into a window is a change for undo; the shown tab and
        the window place are not.

        Inputs: none.
        Outputs: none.
        """
        _, second_i, third_i, _ = self.id_list
        self.workspace.undock_tab(second_i)
        window_id_i = self.window_of(second_i)
        snapshot = self.workspace.snapshot()
        self.workspace.move_tab_to_window(third_i, window_id_i)
        self.assertFalse(self.workspace.is_unchanged_since(snapshot))
        snapshot = self.workspace.snapshot()
        self.workspace.show_window_tab(second_i)
        self.workspace.set_window_geometry(window_id_i, (1, 2, 3, 4))
        self.assertTrue(self.workspace.is_unchanged_since(snapshot))

    @covers("LLFR-01047", "LLFR-01048", "LLFR-01055", "HLFR-00130")
    def test_panel_of_a_window_is_shared_by_its_tabs(self) -> None:
        """The panel state and width of a window apply to all its tabs.

        Inputs: none.
        Outputs: none.
        """
        _, second_i, third_i, fourth_i = self.id_list
        window_id_i = self.one_window_of_three()
        self.assertTrue(self.workspace.set_window_panel(window_id_i, True,
                                                        210))
        self.assertTrue(self.workspace.set_panel_width(window_id_i, 230))
        for tab_id_i in (second_i, third_i, fourth_i):
            tab = self.workspace.find_tab(tab_id_i)
            self.assertEqual((tab.panel_shown_b, tab.panel_width_i),
                             (True, 230))
        self.assertFalse(self.workspace.set_window_panel(999, True, 1))
        self.assertFalse(self.workspace.set_panel_width(999, 1))


class LayoutWindowNumberTest(WindowTabsTestCase):
    """The window numbers of the layout file."""

    def rebuild(self, layout_dict: dict):
        """Rebuild a layout in a new workspace.

        Inputs:
            layout_dict: the content of the file.
        Outputs: (new Workspace, LayoutResult).
        """
        new_workspace = Workspace(random.Random(5))
        names_dict = signal_dict()
        result = rebuild_layout(new_workspace, layout_dict, names_dict,
                                names_dict["file1_Time"], None, None,
                                (30, 40, 900, 700))
        return new_workspace, result

    def two_windows(self) -> tuple:
        """Put tabs 2 and 3 in one window and tab 4 in another.

        Inputs: none.
        Outputs: (window of tabs 2 and 3, window of tab 4).
        """
        _, second_i, third_i, fourth_i = self.id_list
        self.workspace.undock_tab(second_i, (100, 110, 640, 480))
        window_a_i = self.window_of(second_i)
        self.workspace.set_window_panel(window_a_i, True, 160)
        self.workspace.move_tab_to_window(third_i, window_a_i)
        self.workspace.undock_tab(fourth_i, (300, 310, 500, 400))
        return window_a_i, self.window_of(fourth_i)

    @covers("LLFR-00225", "LLFR-01075", "LLFR-00471", "HLFR-00140",
            "HLFR-00126")
    def test_window_numbers_saved(self) -> None:
        """The tabs of one window share a number, numbered from 1 in the
        tab order; the version stays 3.

        Inputs: none.
        Outputs: none.
        """
        self.two_windows()
        layout_dict = json.loads(layout_text(build_layout_dict(
            self.workspace, self.id_list[0], (), True)))
        self.assertEqual(layout_dict["version"], 3)
        tab_list = layout_dict["tabs"]
        self.assertNotIn("window_number", tab_list[0])
        self.assertEqual([entry["window_number"] for entry in tab_list[1:]],
                         [1, 1, 2])
        self.assertEqual(tab_list[1]["window"], tab_list[2]["window"])

    @covers("LLFR-01159", "LLFR-01161", "LLFR-01076", "LLFR-01078",
            "HLFR-00141", "HLFR-00126")
    def test_round_trip_rebuilds_shared_windows(self) -> None:
        """Loading gives two windows, the first with two tabs in order,
        its first tab shown, and nothing in the report.

        Inputs: none.
        Outputs: none.
        """
        self.two_windows()
        layout_dict = parse_layout_text(layout_text(build_layout_dict(
            self.workspace, self.id_list[0], (), True)))
        new_workspace, result = self.rebuild(layout_dict)
        self.assertTrue(result.report.is_empty(), result.report.text())
        window_id_list = new_workspace.window_id_list()
        self.assertEqual(len(window_id_list), 2)
        first_list = new_workspace.window_tab_list(window_id_list[0])
        self.assertEqual([tab.name_str for tab in first_list],
                         ["Tab 2", "Tab 3"])
        self.assertEqual(first_list[1].window_tuple, (100, 110, 640, 480))
        self.assertEqual((first_list[1].panel_shown_b,
                          first_list[1].panel_width_i), (True, 160))
        self.assertEqual(new_workspace.window_shown_tab(
            window_id_list[0]).name_str, "Tab 2")
        second_list = new_workspace.window_tab_list(window_id_list[1])
        self.assertEqual([tab.name_str for tab in second_list], ["Tab 4"])

    @covers("LLFR-01160", "LLFR-01077", "HLFR-00141")
    def test_file_without_numbers_opens_a_window_per_tab(self) -> None:
        """Undocked tabs with no window number get a window each, with
        nothing reported.

        Inputs: none.
        Outputs: none.
        """
        self.two_windows()
        layout_dict = parse_layout_text(layout_text(build_layout_dict(
            self.workspace, self.id_list[0], (), True)))
        for entry_dict in layout_dict["tabs"]:
            entry_dict.pop("window_number", None)
        new_workspace, result = self.rebuild(layout_dict)
        self.assertTrue(result.report.is_empty(), result.report.text())
        self.assertEqual(len(new_workspace.window_id_list()), 3)

    @covers("LLFR-01165", "LLFR-01082", "LLFR-00237", "HLFR-00141",
            "HLFR-00052")
    def test_unusable_number_gives_a_window_of_its_own(self) -> None:
        """A window number that is not a whole number of 1 or more gives
        the tab its own window and is reported as replaced.

        Inputs: none.
        Outputs: none.
        """
        self.two_windows()
        layout_dict = parse_layout_text(layout_text(build_layout_dict(
            self.workspace, self.id_list[0], (), True)))
        layout_dict["tabs"][2]["window_number"] = "one"
        new_workspace, result = self.rebuild(layout_dict)
        self.assertEqual(len(new_workspace.window_id_list()), 3)
        self.assertIn("Window number", result.report.text())
        self.assertIn("a window of its own", result.report.text())


class MainPanelLayoutTest(WindowTabsTestCase):
    """Whether the main window shows its signal list panel, in the layout
    file (LLFR-00225 item 9, LLFR-01214)."""

    # The same rebuild as for the window numbers.
    rebuild = LayoutWindowNumberTest.rebuild

    @covers("LLFR-00225", "LLFR-01214", "LLFR-01053", "HLFR-00131",
            "HLFR-00049", "HLFR-00050")
    def test_main_panel_state_saved_and_loaded(self) -> None:
        """The file holds the state; loading it sets the model and the
        result; a file without it leaves the panel as it is; a value that
        is no bool is reported.

        Inputs: none.
        Outputs: none.
        """
        self.workspace.main_panel_shown_b = False
        layout_dict = parse_layout_text(layout_text(build_layout_dict(
            self.workspace, self.id_list[0], (), True)))
        self.assertIs(layout_dict["signal_list_panel_shown"], False)
        new_workspace, result = self.rebuild(layout_dict)
        self.assertFalse(new_workspace.main_panel_shown_b)
        self.assertIs(result.main_panel_shown_b, False)
        self.assertTrue(result.report.is_empty(), result.report.text())
        layout_dict.pop("signal_list_panel_shown")
        new_workspace, result = self.rebuild(layout_dict)
        self.assertTrue(new_workspace.main_panel_shown_b)
        self.assertIsNone(result.main_panel_shown_b)
        layout_dict["signal_list_panel_shown"] = "yes"
        _, result = self.rebuild(layout_dict)
        self.assertIsNone(result.main_panel_shown_b)
        self.assertIn("Signal list panel shown", result.report.text())

    @covers("LLFR-01053", "HLFR-00131")
    def test_main_panel_state_is_part_of_the_undo_state(self) -> None:
        """Hiding the main window's panel changes the state an undo
        restores, and a restore puts it back.

        Inputs: none.
        Outputs: none.
        """
        snapshot = self.workspace.snapshot()
        self.workspace.main_panel_shown_b = False
        self.assertFalse(self.workspace.is_unchanged_since(snapshot))
        self.workspace.restore(snapshot)
        self.assertTrue(self.workspace.main_panel_shown_b)
        self.assertTrue(self.workspace.is_unchanged_since(snapshot))


if __name__ == "__main__":
    unittest.main()
