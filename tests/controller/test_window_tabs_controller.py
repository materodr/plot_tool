"""Controller tests for undocked windows with several tabs (#205, step 5).

They run the plot controller with the fake view of test_plot_controller:
moving a tab into an undocked window (HLFR-00153), reordering, docking
and deleting the tabs of a window (HLFR-00125, HLFR-00142), closing a
window with all its tabs (HLFR-00138), the tab each window shows
(HLFR-00134) and the one undo history (HLFR-00132).
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

    @covers("LLFR-01115", "LLFR-01123", "LLFR-01118", "LLFR-00982",
            "LLFR-01024", "HLFR-00153", "HLFR-00125", "HLFR-00132")
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

    @covers("LLFR-01116", "HLFR-00153")
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

    @covers("LLFR-01109", "HLFR-00153")
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

    @covers("LLFR-01117", "LLFR-00996", "LLFR-01118", "LLFR-01024",
            "HLFR-00153")
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


class WindowTabsActionTest(WindowTabsControllerTestCase):
    """Reordering, docking, deleting and closing in a window."""

    @covers("LLFR-01122", "LLFR-01054", "LLFR-01055", "HLFR-00142")
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

    @covers("LLFR-00993", "LLFR-00994", "LLFR-01121", "LLFR-00995",
            "HLFR-00124", "HLFR-00125")
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

    @covers("LLFR-01033", "LLFR-01110", "LLFR-01121", "HLFR-00135")
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

    @covers("LLFR-01038", "LLFR-01039", "LLFR-01024", "HLFR-00138",
            "HLFR-00125")
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

    @covers("LLFR-00998", "LLFR-00932", "LLFR-01121", "HLFR-00125",
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

    @covers("LLFR-01003", "LLFR-01121", "HLFR-00127")
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

    @covers("LLFR-01012", "LLFR-01018", "HLFR-00129")
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


if __name__ == "__main__":
    unittest.main()
