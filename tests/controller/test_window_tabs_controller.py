"""Controller tests for undocked windows with several tabs (#205, step 5).

They run the plot controller with the fake view of test_plot_controller:
moving a tab into an undocked window (HLFR-00154), reordering, docking
and deleting the tabs of a window (HLFR-00126, HLFR-00143), closing a
window with all its tabs (HLFR-00139), the tab each window shows
(HLFR-00135) and the one undo history (HLFR-00133).
"""

import unittest

from tests.support import covers
from tests.controller.test_undock_controller import UndockControllerTestCase


class WindowTabsControllerTestCase(UndockControllerTestCase):
    """Helpers for windows with several tabs."""

    def drop_on_window(self, tab_id_i: int, window_id_i: int,
                       index_i: int = -1) -> None:
        """Drop a tab on an undocked window, as the view reports it.

        Inputs:
            tab_id_i: id of the dragged tab.
            window_id_i: id of the window.
            index_i: the place among its tabs, -1 for after the last.
        Outputs: none.
        """
        self.view.handler_dict["window_drop_handler"](tab_id_i, window_id_i,
                                                      index_i)

    def window_tabs(self, window_id_i: int) -> list:
        """Return the tabs the fake view shows in a window.

        Inputs:
            window_id_i: id of the window.
        Outputs: a list of tab ids.
        """
        return list(self.view.window_tabs_dict.get(window_id_i, []))

    def three_tabs_two_in_a_window(self) -> tuple:
        """Make tabs 2 and 3 share a window; tab 1 stays docked.

        Inputs: none.
        Outputs: (first id, second id, third id, window id).
        """
        first_id_i = self.first_tab_id()
        second_id_i = self.add_tab()
        third_id_i = self.add_tab()
        self.undock(second_id_i)
        window_id_i = self.window_of(second_id_i)
        self.drop_on_window(third_id_i, window_id_i)
        return first_id_i, second_id_i, third_id_i, window_id_i


class WindowDropControllerTest(WindowTabsControllerTestCase):
    """A docked tab dropped on an undocked window."""

    @covers("LLFR-01150", "LLFR-01158", "LLFR-01153", "LLFR-01017",
            "LLFR-01059", "HLFR-00154", "HLFR-00126", "HLFR-00133")
    def test_docked_tab_dropped_on_a_window(self) -> None:
        """The tab joins the window after its last tab and is shown
        there; the main window shows the nearest docked tab; one undo
        puts it back, one redo moves it again.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        second_id_i = self.add_tab()
        third_id_i = self.add_tab()
        self.undock(second_id_i)
        window_id_i = self.window_of(second_id_i)
        self.view.set_current_tab(third_id_i)
        self.drop_on_window(third_id_i, window_id_i)
        self.assertEqual(self.window_tabs(window_id_i),
                         [second_id_i, third_id_i])
        self.assertEqual(self.view.window_shown_dict[window_id_i],
                         third_id_i)
        self.assertEqual(self.view.current_tab_id(), first_id_i)
        self.undo()
        self.assertFalse(self.workspace.find_tab(third_id_i).undocked_b)
        self.assertEqual(self.window_tabs(window_id_i), [second_id_i])
        self.redo()
        self.assertEqual(self.window_tabs(window_id_i),
                         [second_id_i, third_id_i])

    @covers("LLFR-01151", "HLFR-00154")
    def test_drop_on_the_tab_row_place(self) -> None:
        """A drop at place 0 puts the tab first in the window.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, third_id_i, window_id_i = (
            self.three_tabs_two_in_a_window())
        fourth_id_i = self.add_tab()
        self.drop_on_window(fourth_id_i, window_id_i, 0)
        self.assertEqual(self.window_tabs(window_id_i),
                         [fourth_id_i, second_id_i, third_id_i])

    @covers("LLFR-01144", "HLFR-00154")
    def test_last_docked_tab_is_not_moved(self) -> None:
        """The last docked tab dropped on a window stays docked, with no
        undo record.

        Inputs: none.
        Outputs: none.
        """
        first_id_i, _, _, window_id_i = self.three_tabs_two_in_a_window()
        depth_i = self.controller.undo_history.depth()
        self.drop_on_window(first_id_i, window_id_i)
        self.assertFalse(self.workspace.find_tab(first_id_i).undocked_b)
        self.assertEqual(self.controller.undo_history.depth(), depth_i)

    @covers("LLFR-01152", "LLFR-01031", "LLFR-01153", "LLFR-01059",
            "HLFR-00154")
    def test_tab_moved_from_window_to_window(self) -> None:
        """The last tab of a window dropped on another window closes its
        window; one undo opens it again with its tab.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, third_id_i, window_id_i = (
            self.three_tabs_two_in_a_window())
        fourth_id_i = self.add_tab()
        self.undock(fourth_id_i)
        other_id_i = self.window_of(fourth_id_i)
        self.drop_on_window(fourth_id_i, window_id_i)
        self.assertNotIn(other_id_i, self.view.window_tabs_dict)
        self.assertEqual(self.window_tabs(window_id_i),
                         [second_id_i, third_id_i, fourth_id_i])
        self.undo()
        self.assertEqual(self.window_tabs(other_id_i), [fourth_id_i])
        self.assertEqual(self.window_tabs(window_id_i),
                         [second_id_i, third_id_i])


class WindowAddTabControllerTest(WindowTabsControllerTestCase):
    """The "+" button of an undocked window (LLFR-01203)."""

    @covers("LLFR-01203", "LLFR-00210", "LLFR-00212", "LLFR-00140",
            "HLFR-00015", "HLFR-00126")
    def test_plus_of_a_window_adds_the_tab_there(self) -> None:
        """The new tab is the last of the window, shown there, named
        "Tab N"; the main window keeps its tab; one undo removes it and
        one redo adds it again.

        Inputs: none.
        Outputs: none.
        """
        first_id_i, second_id_i, third_id_i, window_id_i = (
            self.three_tabs_two_in_a_window())
        self.view.set_current_tab(first_id_i)
        self.view.handler_dict["window_add_tab_handler"](window_id_i)
        tab_list = self.workspace.window_tab_list(window_id_i)
        self.assertEqual(len(tab_list), 3)
        new_tab = tab_list[-1]
        self.assertEqual(new_tab.name_str, "Tab 4")
        self.assertTrue(new_tab.undocked_b)
        self.assertEqual(self.window_tabs(window_id_i),
                         [second_id_i, third_id_i, new_tab.tab_id_i])
        self.assertEqual(self.view.window_shown_dict[window_id_i],
                         new_tab.tab_id_i)
        self.assertEqual(self.view.current_tab_id(), first_id_i)
        self.undo()
        self.assertEqual(self.window_tabs(window_id_i),
                         [second_id_i, third_id_i])
        self.assertIsNone(self.workspace.find_tab(new_tab.tab_id_i))
        self.redo()
        self.assertEqual(self.window_tabs(window_id_i),
                         [second_id_i, third_id_i, new_tab.tab_id_i])
        # LLFR-00210: the number is never reused, even after an undo.
        self.undo()
        self.view.handler_dict["window_add_tab_handler"](window_id_i)
        self.assertEqual(
            self.workspace.window_tab_list(window_id_i)[-1].name_str,
            "Tab 5")

    @covers("LLFR-01203", "HLFR-00015")
    def test_plus_of_an_unknown_window_changes_nothing(self) -> None:
        """A window id with no tab adds nothing and records nothing.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.controller.undo_history.depth()
        count_i = len(self.workspace.tab_list)
        self.view.handler_dict["window_add_tab_handler"](99)
        self.assertEqual(len(self.workspace.tab_list), count_i)
        self.assertEqual(self.controller.undo_history.depth(), depth_i)


class NewWindowDropControllerTest(WindowTabsControllerTestCase):
    """A tab of an undocked window dropped outside the app."""

    def drop_outside(self, tab_id_i: int, x_i: int = 1500,
                     y_i: int = 70) -> None:
        """Drop a tab outside every app window, as the view reports it.

        Inputs:
            tab_id_i: id of the dragged tab.
            x_i, y_i: the point of the drop.
        Outputs: none.
        """
        self.view.handler_dict["new_window_drop_handler"](tab_id_i, x_i,
                                                          y_i)

    @covers("LLFR-01167", "LLFR-01168", "LLFR-01169", "LLFR-01050",
            "LLFR-01020", "LLFR-01059", "HLFR-00126", "HLFR-00040",
            "HLFR-00048", "HLFR-00133")
    def test_last_tab_of_a_window_dropped_outside(self) -> None:
        """The only tab of a window moves into a new window at the drop
        point, with the plot panel's size and a hidden panel; the old
        window closes; it is one undoable action, redone by one redo.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        second_id_i = self.add_tab()
        self.double_click("s1")
        self.undock(second_id_i)
        old_window_id_i = self.window_of(second_id_i)
        self.view.handler_dict["panel_toggle_handler"](old_window_id_i)
        depth_i = self.controller.undo_history.depth()
        self.drop_outside(second_id_i, 1500, 70)
        new_window_id_i = self.window_of(second_id_i)
        self.assertNotEqual(new_window_id_i, old_window_id_i)
        self.assertNotIn(old_window_id_i, self.view.window_tabs_dict)
        self.assertEqual(self.window_tabs(new_window_id_i), [second_id_i])
        self.assertEqual(self.view.window_dict[second_id_i],
                         [(1500, 70, 900, 600), False, 0])
        self.assertEqual(
            len(self.workspace.find_tab(second_id_i).plot_list), 1)
        self.assertEqual(self.controller.undo_history.depth(), depth_i + 1)
        self.undo()
        self.assertEqual(self.window_of(second_id_i), old_window_id_i)
        self.assertEqual(self.window_tabs(old_window_id_i), [second_id_i])
        self.assertNotIn(new_window_id_i, self.view.window_tabs_dict)
        self.assertTrue(self.workspace.find_tab(second_id_i).panel_shown_b)
        self.redo()
        self.assertEqual(self.window_of(second_id_i), new_window_id_i)
        self.assertNotIn(old_window_id_i, self.view.window_tabs_dict)

    @covers("LLFR-01184", "LLFR-01167", "LLFR-01016", "HLFR-00126",
            "HLFR-00127", "HLFR-00124")
    def test_drop_outside_keeps_the_size_of_its_window(self) -> None:
        """A tab dropped outside the app gets the size its window has at
        the drop (after the user resized it), at the drop point; the
        window it came from keeps its size after an undo; an undock from
        the main window still gets the plot panel's size.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        second_id_i = self.add_tab()
        self.double_click("s1")
        third_id_i = self.add_tab()
        self.undock(second_id_i)
        old_window_id_i = self.window_of(second_id_i)
        # The user resizes the window: only the view knows its new size.
        self.view.window_dict[second_id_i][0] = (100, 120, 700, 450)
        self.drop_outside(second_id_i, 1500, 70)
        self.assertEqual(self.view.window_dict[second_id_i][0],
                         (1500, 70, 700, 450))
        self.assertIn(("dropped_window_tuple", 1500, 70),
                      self.view.call_list)
        self.undo()
        self.assertEqual(self.window_of(second_id_i), old_window_id_i)
        self.assertEqual(self.view.window_dict[second_id_i][0],
                         (100, 120, 700, 450))
        # LLFR-01016: a tab of the main window dropped outside the plot
        # panel gets the size of the plot panel (new_window_answer_tuple).
        self.view.handler_dict["undock_drop_handler"](third_id_i, 300, 40)
        self.assertEqual(self.view.window_dict[third_id_i][0],
                         (300, 40) + tuple(
                             self.view.new_window_answer_tuple[2:]))
        self.assertNotEqual(tuple(self.view.new_window_answer_tuple[2:]),
                            (700, 450))

    @covers("LLFR-01167", "LLFR-01168", "LLFR-01156", "HLFR-00126",
            "HLFR-00127")
    def test_one_of_two_tabs_dropped_outside(self) -> None:
        """One tab of a window with two tabs gets a window of its own;
        the old window keeps the other tab and shows it.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, third_id_i, window_id_i = (
            self.three_tabs_two_in_a_window())
        self.assertEqual(self.view.window_shown_dict[window_id_i],
                         third_id_i)
        self.drop_outside(third_id_i)
        new_window_id_i = self.window_of(third_id_i)
        self.assertNotEqual(new_window_id_i, window_id_i)
        self.assertEqual(self.window_tabs(window_id_i), [second_id_i])
        self.assertEqual(self.view.window_shown_dict[window_id_i],
                         second_id_i)
        self.assertEqual(self.window_tabs(new_window_id_i), [third_id_i])
        self.assertEqual(self.workspace.window_id_list(),
                         [window_id_i, new_window_id_i])

    @covers("LLFR-01167", "HLFR-00126")
    def test_docked_tab_is_not_moved(self) -> None:
        """The handler changes nothing for a docked tab.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        self.add_tab()
        depth_i = self.controller.undo_history.depth()
        self.drop_outside(first_id_i)
        self.assertFalse(self.workspace.find_tab(first_id_i).undocked_b)
        self.assertEqual(self.controller.undo_history.depth(), depth_i)


class WindowTabsActionTest(WindowTabsControllerTestCase):
    """Reordering, docking, deleting and closing in a window."""

    @covers("LLFR-01157", "LLFR-01166", "LLFR-01089", "LLFR-01090",
            "HLFR-00143")
    def test_reorder_in_the_window_is_undoable(self) -> None:
        """A drag in the window's tab row is one undoable action; a drag
        back to the place records nothing.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, third_id_i, window_id_i = (
            self.three_tabs_two_in_a_window())
        move = self.view.handler_dict["window_tab_move_handler"]
        depth_i = self.controller.undo_history.depth()
        move(third_id_i, 0)
        self.assertEqual(self.window_tabs(window_id_i),
                         [third_id_i, second_id_i])
        self.assertEqual(self.controller.undo_history.depth(), depth_i + 1)
        move(third_id_i, 0)
        self.assertEqual(self.controller.undo_history.depth(), depth_i + 1)
        self.undo()
        self.assertEqual(self.window_tabs(window_id_i),
                         [second_id_i, third_id_i])

    @covers("LLFR-01028", "LLFR-01029", "LLFR-01156", "LLFR-01030",
            "HLFR-00125", "HLFR-00126")
    def test_dock_one_tab_keeps_the_window(self) -> None:
        """Docking the shown tab of a window of two keeps the window with
        the other tab, shown; docking that one closes the window.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, third_id_i, window_id_i = (
            self.three_tabs_two_in_a_window())
        self.dock(third_id_i)
        self.assertEqual(self.window_tabs(window_id_i), [second_id_i])
        self.assertEqual(self.view.window_shown_dict[window_id_i],
                         second_id_i)
        self.assertEqual(self.view.current_tab_id(), third_id_i)
        self.dock(second_id_i)
        self.assertEqual(self.view.window_tabs_dict, {})

    @covers("LLFR-01068", "LLFR-01145", "LLFR-01156", "HLFR-00136")
    def test_delete_one_tab_keeps_the_window(self) -> None:
        """Deleting the shown tab of a window of two keeps the window
        with the other tab shown.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, third_id_i, window_id_i = (
            self.three_tabs_two_in_a_window())
        self.view.handler_dict["delete_tab"](third_id_i)
        self.assertEqual(self.window_tabs(window_id_i), [second_id_i])
        self.assertEqual(self.view.window_shown_dict[window_id_i],
                         second_id_i)

    @covers("LLFR-01073", "LLFR-01074", "LLFR-01059", "HLFR-00139",
            "HLFR-00126")
    def test_window_close_deletes_all_its_tabs(self) -> None:
        """Closing a window of two tabs deletes both as one action; one
        undo opens the window again with both, in order.

        Inputs: none.
        Outputs: none.
        """
        first_id_i, second_id_i, third_id_i, window_id_i = (
            self.three_tabs_two_in_a_window())
        self.view.window_entry_dict[window_id_i][0] = (7, 8, 600, 400)
        depth_i = self.controller.undo_history.depth()
        self.view.handler_dict["window_close_handler"](window_id_i)
        self.assertEqual(self.tab_ids(), [first_id_i])
        self.assertEqual(self.view.window_tabs_dict, {})
        self.assertEqual(self.controller.undo_history.depth(), depth_i + 1)
        self.undo()
        self.assertEqual(self.window_tabs(window_id_i),
                         [second_id_i, third_id_i])
        self.assertEqual(self.view.window_entry_dict[window_id_i][0],
                         (7, 8, 600, 400))

    @covers("LLFR-01033", "LLFR-00932", "LLFR-01156", "HLFR-00126",
            "HLFR-00118")
    def test_file_close_closes_only_the_emptied_tab(self) -> None:
        """A close that empties one tab of a window of two keeps the
        window with the other tab.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        second_id_i = self.add_tab()
        self.view.set_current_tab(second_id_i)
        self.double_click("s1")
        third_id_i = self.add_tab()
        self.view.set_current_tab(third_id_i)
        self.double_click("s2")
        self.undock(second_id_i)
        window_id_i = self.window_of(second_id_i)
        self.drop_on_window(third_id_i, window_id_i)
        self.controller.close_signals(["s2"])
        self.assertEqual(self.tab_ids(), [first_id_i, second_id_i])
        self.assertEqual(self.window_tabs(window_id_i), [second_id_i])
        self.assertEqual(self.view.window_shown_dict[window_id_i],
                         second_id_i)

    @covers("LLFR-01038", "LLFR-01156", "HLFR-00128")
    def test_shown_tab_follows_the_view(self) -> None:
        """The tab a window shows in the view is kept by the model before
        an action, so a later action keeps showing it.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, third_id_i, window_id_i = (
            self.three_tabs_two_in_a_window())
        self.view.window_shown_dict[window_id_i] = second_id_i
        fourth_id_i = self.add_tab()
        self.assertEqual(self.workspace.window_shown_tab(
            window_id_i).tab_id_i, second_id_i)
        self.assertNotEqual(fourth_id_i, second_id_i)

    @covers("LLFR-01047", "LLFR-01053", "HLFR-00130")
    def test_panel_toggle_acts_on_the_whole_window(self) -> None:
        """The signal list button of a window of two tabs shows the one
        panel of the window, kept by both tabs.

        Inputs: none.
        Outputs: none.
        """
        _, second_id_i, third_id_i, window_id_i = (
            self.three_tabs_two_in_a_window())
        self.view.handler_dict["panel_toggle_handler"](window_id_i)
        self.assertTrue(self.view.window_entry_dict[window_id_i][1])
        for tab_id_i in (second_id_i, third_id_i):
            self.assertTrue(self.workspace.find_tab(tab_id_i).panel_shown_b)


class MainPanelToggleControllerTest(WindowTabsControllerTestCase):
    """The signal list button of the main window (LLFR-01211)."""

    @covers("LLFR-01211", "LLFR-01212", "LLFR-01047", "LLFR-01048",
            "LLFR-01053", "LLFR-00140", "HLFR-00131", "HLFR-00040",
            "HLFR-00048")
    def test_main_panel_hidden_and_shown_as_undoable_actions(self) -> None:
        """The panel starts shown; the button of window -1 hides it, the
        width kept, then shows it; each click is one undoable action.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(self.workspace.main_panel_shown_b)
        depth_i = self.controller.undo_history.depth()
        self.view.handler_dict["panel_toggle_handler"](-1)
        self.assertFalse(self.workspace.main_panel_shown_b)
        self.assertEqual(self.view.call_list[-1],
                         ("set_main_panel", False, 240))
        self.assertEqual(self.controller.undo_history.depth(), depth_i + 1)
        self.view.handler_dict["panel_toggle_handler"](-1)
        self.assertTrue(self.workspace.main_panel_shown_b)
        self.assertEqual(self.view.call_list[-1],
                         ("set_main_panel", True, 240))
        self.undo()
        self.assertFalse(self.workspace.main_panel_shown_b)
        self.assertFalse(self.view.main_panel_shown_b)
        self.undo()
        self.assertTrue(self.workspace.main_panel_shown_b)
        self.assertTrue(self.view.main_panel_shown_b)
        self.redo()
        self.assertFalse(self.view.main_panel_shown_b)

    @covers("LLFR-01141", "HLFR-00131")
    def test_search_shortcut_shows_only_a_hidden_main_panel(self) -> None:
        """Ctrl+F in the main window shows its hidden panel, as one
        undoable action, and does nothing while it is shown.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.controller.undo_history.depth()
        self.view.handler_dict["panel_show_handler"](-1)
        self.assertTrue(self.workspace.main_panel_shown_b)
        self.assertEqual(self.controller.undo_history.depth(), depth_i)
        self.view.handler_dict["panel_toggle_handler"](-1)
        self.view.handler_dict["panel_show_handler"](-1)
        self.assertTrue(self.workspace.main_panel_shown_b)
        self.assertEqual(self.controller.undo_history.depth(), depth_i + 2)


if __name__ == "__main__":
    unittest.main()
