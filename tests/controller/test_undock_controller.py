"""Tests for the undocked windows in the plot controller (#205, step 3).

They run the plot controller with the fake view of test_plot_controller:
undocking and docking a tab (HLFR-00123, HLFR-00124), one tab per window
and any number of windows (HLFR-00125, HLFR-00126), closing a window
(HLFR-00138), the signal list panel of a window (HLFR-00129) and the
panel width drags (HLFR-00131), all in one undo history (HLFR-00132,
HLFR-00133), and the plots made from the panel of a window (HLFR-00127).
"""

import unittest

from tests.support import covers
from tests.controller.test_plot_controller import PlotControllerTestCase


class UndockControllerTestCase(PlotControllerTestCase):
    """Helpers that run the window handlers of the fake view."""

    def add_tab(self) -> int:
        """Add a tab with "+" and return its id.

        Inputs: none.
        Outputs: the id of the new tab.
        """
        self.view.handler_dict["add_tab"]()
        return self.workspace.tab_list[len(
            self.workspace.docked_tab_list()) - 1].tab_id_i

    def undock(self, tab_id_i: int) -> None:
        """Click the undock button of a tab.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: none.
        """
        self.view.handler_dict["undock_handler"](tab_id_i)

    def dock(self, tab_id_i: int) -> None:
        """Click the dock button of a window.

        Inputs:
            tab_id_i: id of the tab of the window.
        Outputs: none.
        """
        self.view.handler_dict["dock_handler"](tab_id_i)

    def window_of(self, tab_id_i: int) -> int:
        """Return the id of the undocked window of a tab.

        Inputs:
            tab_id_i: id of an undocked tab.
        Outputs: its window id (0 for a docked tab).
        """
        return self.workspace.find_tab(tab_id_i).window_id_i

    def undo(self) -> None:
        """Run Undo.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["undo"]()

    def redo(self) -> None:
        """Run Redo.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["redo"]()

    def tab_ids(self) -> list:
        """Return the tab ids of the model in tab order.

        Inputs: none.
        Outputs: a list of int.
        """
        return [tab.tab_id_i for tab in self.workspace.tab_list]

    def undocked_ids(self) -> list:
        """Return the ids of the undocked tabs of the model.

        Inputs: none.
        Outputs: a list of int.
        """
        return [tab.tab_id_i for tab in self.workspace.undocked_tab_list()]


class UndockDockTest(UndockControllerTestCase):
    """Undocking and docking a tab."""

    @covers("LLFR-00980", "LLFR-00981", "LLFR-01093", "LLFR-01015",
            "LLFR-00985", "HLFR-00123", "HLFR-00125")
    def test_undock_opens_a_window_with_the_tab(self) -> None:
        """The undocked tab keeps its plots, gets the window the view
        offers and a hidden panel.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        second_id_i = self.add_tab()
        self.view.set_current_tab(first_id_i)
        self.undock(first_id_i)
        tab = self.workspace.find_tab(first_id_i)
        self.assertTrue(tab.undocked_b)
        self.assertEqual([plot.plot_id_i for plot in tab.plot_list],
                         [plot_id_i])
        self.assertEqual(self.view.window_dict[first_id_i],
                         [(130, 160, 900, 600), False, 0])
        self.assertEqual(self.view.undocked_order_list, [first_id_i])
        # The tab order: docked tabs, then undocked ones.
        self.assertEqual(self.tab_ids(), [second_id_i, first_id_i])

    @covers("LLFR-00982", "HLFR-00014")
    def test_shown_tab_undocked_shows_nearest_docked_tab(self) -> None:
        """The main window shows the docked tab to the left, else right.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        second_id_i = self.add_tab()
        third_id_i = self.add_tab()
        self.view.set_current_tab(second_id_i)
        self.undock(second_id_i)
        self.assertEqual(self.view.current_tab_id(), first_id_i)
        self.view.set_current_tab(first_id_i)
        self.undock(first_id_i)
        self.assertEqual(self.view.current_tab_id(), third_id_i)

    @covers("LLFR-00983", "LLFR-00984", "LLFR-00066", "HLFR-00126")
    def test_last_docked_tab_cannot_be_undocked(self) -> None:
        """With one docked tab, the undock button is disabled and does
        nothing; Delete is disabled too.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        self.assertFalse(self.view.undock_enabled_b)
        self.undock(first_id_i)
        self.assertFalse(self.workspace.find_tab(first_id_i).undocked_b)
        self.assertFalse(self.controller.undo_history.can_undo())
        second_id_i = self.add_tab()
        self.assertTrue(self.view.undock_enabled_b)
        self.undock(second_id_i)
        self.assertFalse(self.view.undock_enabled_b)
        self.assertFalse(self.view.delete_enabled_b)

    @covers("LLFR-00999", "LLFR-01056", "HLFR-00126", "HLFR-00125")
    def test_any_number_of_windows_in_undock_order(self) -> None:
        """Every undock opens one more window, one tab each.

        Inputs: none.
        Outputs: none.
        """
        id_list = [self.first_tab_id()] + [self.add_tab()
                                           for _ in range(5)]
        for tab_id_i in (id_list[3], id_list[1], id_list[4], id_list[0]):
            self.undock(tab_id_i)
        self.assertEqual(self.undocked_ids(),
                         [id_list[3], id_list[1], id_list[4], id_list[0]])
        self.assertEqual(len(self.view.window_dict), 4)
        self.assertEqual(self.tab_ids(),
                         [id_list[2], id_list[5], id_list[3], id_list[1],
                          id_list[4], id_list[0]])

    @covers("LLFR-00993", "LLFR-00994", "LLFR-00995", "LLFR-00985",
            "HLFR-00124")
    def test_dock_puts_the_tab_last_and_shows_it(self) -> None:
        """A docked tab is the last docked tab and is shown.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        self.double_click("s2")
        second_id_i = self.add_tab()
        third_id_i = self.add_tab()
        self.undock(first_id_i)
        self.undock(second_id_i)
        self.dock(first_id_i)
        self.assertEqual(self.tab_ids(),
                         [third_id_i, first_id_i, second_id_i])
        self.assertNotIn(first_id_i, self.view.window_dict)
        self.assertIn("dock_tab_view", self.view.method_names())
        self.assertEqual(self.view.current_tab_id(), first_id_i)
        self.assertEqual(len(self.workspace.find_tab(first_id_i).plot_list),
                         1)

    @covers("LLFR-01032")
    def test_undocked_tab_is_not_moved_by_a_drag(self) -> None:
        """A tab drag never moves an undocked tab.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        self.add_tab()
        self.undock(first_id_i)
        before_list = self.tab_ids()
        self.view.handler_dict["move_tab"](first_id_i, 0)
        self.assertEqual(self.tab_ids(), before_list)


class UndockUndoTest(UndockControllerTestCase):
    """Undock, dock and close in the one undo history."""

    @covers("LLFR-01025", "LLFR-00138", "LLFR-00192", "LLFR-01024",
            "HLFR-00133", "HLFR-00040", "HLFR-00048")
    def test_undock_undo_and_redo(self) -> None:
        """Undo puts the tab back at its place; redo opens the window at
        the position it had.

        Inputs: none.
        Outputs: none.
        """
        second_id_i = self.add_tab()
        third_id_i = self.add_tab()
        self.undock(second_id_i)
        # The user moves the window; the view reports it.
        self.view.window_dict[second_id_i][0] = (5, 6, 700, 500)
        self.undo()
        self.assertEqual(self.undocked_ids(), [])
        self.assertEqual(self.tab_ids()[1], second_id_i)
        self.assertEqual(self.view.window_dict, {})
        self.redo()
        self.assertEqual(self.undocked_ids(), [second_id_i])
        self.assertEqual(self.view.window_dict[second_id_i][0],
                         (5, 6, 700, 500))
        self.assertEqual(self.view.current_tab_id(), third_id_i)

    @covers("LLFR-00138", "LLFR-00192", "LLFR-01021", "HLFR-00040")
    def test_open_window_keeps_its_place_on_undo(self) -> None:
        """An undo or a redo leaves a window that stays open where the
        user moved it.

        Inputs: none.
        Outputs: none.
        """
        second_id_i = self.add_tab()
        self.undock(second_id_i)
        self.view.handler_dict["double_click"]("s1", second_id_i)
        # The user moves the window after the action.
        self.view.window_dict[second_id_i][0] = (300, 200, 640, 480)
        self.undo()
        self.assertEqual(self.view.window_dict[second_id_i][0],
                         (300, 200, 640, 480))
        self.redo()
        self.assertEqual(self.view.window_dict[second_id_i][0],
                         (300, 200, 640, 480))

    @covers("LLFR-01025", "LLFR-01024", "LLFR-01094", "HLFR-00133")
    def test_dock_undo_opens_the_window_again(self) -> None:
        """Undoing a dock opens the window with its panel as it was.

        Inputs: none.
        Outputs: none.
        """
        self.add_tab()
        first_id_i = self.first_tab_id()
        self.undock(first_id_i)
        self.view.handler_dict["panel_toggle_handler"](self.window_of(first_id_i))
        self.view.window_dict[first_id_i][0] = (40, 50, 800, 400)
        self.dock(first_id_i)
        self.assertEqual(self.view.window_dict, {})
        self.undo()
        self.assertEqual(self.view.window_dict[first_id_i],
                         [(40, 50, 800, 400), True, 225])

    @covers("LLFR-01038", "LLFR-01039", "LLFR-01033", "LLFR-01034",
            "LLFR-01110", "HLFR-00138", "HLFR-00016")
    def test_window_close_deletes_the_tab_and_undo_brings_it(self) -> None:
        """Closing a window deletes its tab, with its window, undoably.

        Inputs: none.
        Outputs: none.
        """
        second_id_i = self.add_tab()
        self.view.set_current_tab(second_id_i)
        self.double_click("s3")
        self.undock(second_id_i)
        self.view.window_dict[second_id_i][0] = (11, 22, 640, 480)
        self.view.handler_dict["window_close_handler"](self.window_of(second_id_i))
        self.assertIsNone(self.workspace.find_tab(second_id_i))
        self.assertEqual(self.view.window_dict, {})
        self.undo()
        tab = self.workspace.find_tab(second_id_i)
        self.assertTrue(tab.undocked_b)
        self.assertEqual(len(tab.plot_list), 1)
        self.assertEqual(self.view.window_dict[second_id_i][0],
                         (11, 22, 640, 480))
        # Delete of the tab menu works on an undocked tab too, and closes
        # its window as part of the same undoable action.
        self.view.handler_dict["delete_tab"](second_id_i)
        self.assertIsNone(self.workspace.find_tab(second_id_i))
        self.assertEqual(self.view.window_dict, {})
        self.undo()
        self.assertIn(second_id_i, self.view.window_dict)

    @covers("LLFR-01022", "LLFR-01023", "HLFR-00132")
    def test_one_history_for_every_window(self) -> None:
        """Actions in the main window and in a window undo in order.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        second_id_i = self.add_tab()
        self.undock(second_id_i)
        # A plot in the window, from its own panel, then one in the main
        # window.
        self.view.handler_dict["double_click"]("s1", second_id_i)
        self.view.handler_dict["double_click"]("s2")
        self.assertEqual(len(self.workspace.find_tab(first_id_i).plot_list),
                         1)
        self.undo()
        self.assertEqual(len(self.workspace.find_tab(first_id_i).plot_list),
                         0)
        self.assertEqual(
            len(self.workspace.find_tab(second_id_i).plot_list), 1)
        self.undo()
        self.assertEqual(
            len(self.workspace.find_tab(second_id_i).plot_list), 0)
        self.undo()
        self.assertEqual(self.undocked_ids(), [])


class WindowPanelTest(UndockControllerTestCase):
    """The signal list panel of a window and the panel widths."""

    @covers("LLFR-01012", "LLFR-01013", "LLFR-01016", "LLFR-01018",
            "HLFR-00129")
    def test_show_and_hide_with_first_width(self) -> None:
        """The first show gives 25% of the window's width; hiding and
        showing keep the width and are undoable.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        self.add_tab()
        self.view.new_window_answer_tuple = (0, 0, 400, 300)
        self.undock(first_id_i)
        toggle = self.view.handler_dict["panel_toggle_handler"]
        toggle(self.window_of(first_id_i))
        self.assertEqual(self.view.window_dict[first_id_i][1:], [True, 100])
        self.view.window_dict[first_id_i][2] = 150
        toggle(self.window_of(first_id_i))
        self.assertEqual(self.view.window_dict[first_id_i][1:],
                         [False, 150])
        toggle(self.window_of(first_id_i))
        self.assertEqual(self.view.window_dict[first_id_i][1:], [True, 150])
        self.undo()
        self.assertEqual(self.view.window_dict[first_id_i][1:],
                         [False, 150])
        self.undo()
        self.assertTrue(self.view.window_dict[first_id_i][1])

    @covers("LLFR-01016")
    def test_first_width_is_a_quarter_of_the_window(self) -> None:
        """A 900 pixel wide window gets a 225 pixel panel, whatever the
        main panel's width (240).

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        self.add_tab()
        self.undock(first_id_i)
        self.view.handler_dict["panel_toggle_handler"](self.window_of(first_id_i))
        self.assertEqual(self.view.window_dict[first_id_i][2], 225)

    @covers("LLFR-01020", "LLFR-00138", "HLFR-00131", "HLFR-00026")
    def test_main_panel_drag_is_undoable(self) -> None:
        """A drag of the main window's border is undone and redone.

        Inputs: none.
        Outputs: none.
        """
        width_handler = self.view.handler_dict["panel_width_handler"]
        self.view.main_panel_width_i = 320
        width_handler(-1, 240, 320)
        self.assertTrue(self.controller.undo_history.can_undo())
        self.undo()
        self.assertEqual(self.view.main_panel_width_i, 240)
        self.redo()
        self.assertEqual(self.view.main_panel_width_i, 320)

    @covers("LLFR-01020", "HLFR-00131")
    def test_window_panel_drag_is_undoable(self) -> None:
        """A drag of a window's border is undone to its start width.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        self.add_tab()
        self.undock(first_id_i)
        self.view.handler_dict["panel_toggle_handler"](self.window_of(first_id_i))
        self.view.window_dict[first_id_i][2] = 300
        self.view.handler_dict["panel_width_handler"](self.window_of(first_id_i), 240, 300)
        self.undo()
        self.assertEqual(self.view.window_dict[first_id_i][1:], [True, 240])

    @covers("LLFR-01020", "LLFR-01021", "HLFR-00131")
    def test_no_step_without_a_change_or_for_a_resize(self) -> None:
        """A drag back to the start width and a window resize record
        nothing.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["panel_width_handler"](-1, 240, 240)
        self.assertFalse(self.controller.undo_history.can_undo())
        # A window resize changes the width the view reports, with no
        # handler call; the next action records only itself.
        self.view.main_panel_width_i = 260
        self.double_click("s1")
        self.undo()
        self.assertFalse(self.controller.undo_history.can_undo())


class WindowSignalListTest(UndockControllerTestCase):
    """Plots made from the signal list panel of a window."""

    @covers("LLFR-01003", "LLFR-00019", "LLFR-01002", "HLFR-00127",
            "HLFR-00012")
    def test_double_click_plots_in_the_tab_of_the_window(self) -> None:
        """A double-click in a window's panel plots in its tab.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        second_id_i = self.add_tab()
        self.undock(second_id_i)
        self.view.handler_dict["double_click"]("s1", second_id_i)
        self.assertEqual(
            len(self.workspace.find_tab(second_id_i).plot_list), 1)
        self.assertEqual(len(self.workspace.find_tab(first_id_i).plot_list),
                         0)

    @covers("LLFR-01003", "LLFR-00295", "LLFR-01005", "HLFR-00064")
    def test_enter_plots_in_the_tab_of_the_window(self) -> None:
        """Enter in a window's panel plots its selection in its tab.

        Inputs: none.
        Outputs: none.
        """
        second_id_i = self.add_tab()
        self.undock(second_id_i)
        self.view.handler_dict["plot_selection"](["s1", "s2"], second_id_i)
        tab = self.workspace.find_tab(second_id_i)
        self.assertEqual(len(tab.plot_list), 1)
        self.assertEqual(len(tab.plot_list[0].curve_list), 2)


class WindowFileCloseTest(UndockControllerTestCase):
    """A file close that empties an undocked tab."""

    @covers("LLFR-00998", "LLFR-00961", "LLFR-00932", "HLFR-00125",
            "HLFR-00118")
    def test_emptied_undocked_tab_closes_with_its_window(self) -> None:
        """The undocked tab and its window close; a docked tab stays.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        self.double_click("s1")
        second_id_i = self.add_tab()
        self.view.set_current_tab(second_id_i)
        self.double_click("s2")
        self.undock(second_id_i)
        self.close_all_files()
        self.assertEqual(self.tab_ids(), [first_id_i])
        self.assertEqual(self.view.window_dict, {})
        self.assertEqual(self.view.current_tab_id(), first_id_i)

    @covers("LLFR-00961", "LLFR-00962")
    def test_main_window_keeps_its_first_docked_tab(self) -> None:
        """When every docked tab empties, the first docked one stays.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        second_id_i = self.add_tab()
        third_id_i = self.add_tab()
        self.view.set_current_tab(second_id_i)
        self.double_click("s1")
        self.view.set_current_tab(third_id_i)
        self.double_click("s2")
        self.view.set_current_tab(first_id_i)
        self.double_click("s3")
        self.undock(first_id_i)
        self.close_all_files()
        self.assertEqual(self.tab_ids(), [second_id_i])
        self.assertEqual(self.view.current_tab_id(), second_id_i)


class DragUndockDockTest(UndockControllerTestCase):
    """Undocking and docking a tab by dragging it (HLFR-00152)."""

    @covers("LLFR-01107", "LLFR-00981", "LLFR-01015", "LLFR-00985",
            "LLFR-01025", "HLFR-00152", "HLFR-00123")
    def test_drop_outside_undocks_at_the_drop_point(self) -> None:
        """A tab dropped outside the main window opens a window whose
        top-left corner is at the drop, with a hidden panel; one
        undoable action.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        self.double_click("s1")
        second_id_i = self.add_tab()
        self.controller.undo_history.clear()
        self.view.handler_dict["undock_drop_handler"](first_id_i, 1500, 70)
        self.assertEqual(self.undocked_ids(), [first_id_i])
        self.assertEqual(self.view.window_dict[first_id_i],
                         [(1500, 70, 900, 600), False, 0])
        self.assertEqual(
            len(self.workspace.find_tab(first_id_i).plot_list), 1)
        self.assertEqual(self.controller.undo_history.depth(), 1)
        self.undo()
        self.assertEqual(self.undocked_ids(), [])
        self.assertEqual(self.tab_ids(), [first_id_i, second_id_i])
        self.redo()
        self.assertEqual(self.undocked_ids(), [first_id_i])

    @covers("LLFR-01109", "HLFR-00152")
    def test_last_docked_tab_stays_docked(self) -> None:
        """Dropping the last docked tab outside changes nothing.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        second_id_i = self.add_tab()
        self.undock(second_id_i)
        self.controller.undo_history.clear()
        self.view.call_list.clear()
        self.view.handler_dict["undock_drop_handler"](first_id_i, 10, 10)
        self.assertEqual(self.undocked_ids(), [second_id_i])
        self.assertFalse(self.workspace.find_tab(first_id_i).undocked_b)
        self.assertFalse(self.controller.undo_history.can_undo())
        self.assertNotIn("set_window_tabs", self.view.method_names())

    @covers("LLFR-01108", "LLFR-00994", "LLFR-00995", "LLFR-01025",
            "LLFR-01056", "HLFR-00152", "HLFR-00124")
    def test_drop_on_tab_row_docks_at_the_place(self) -> None:
        """A tab button dropped on the main tab row docks the tab at the
        drop place, closes its window, shows it; undo and redo.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        second_id_i = self.add_tab()
        third_id_i = self.add_tab()
        self.undock(third_id_i)
        self.controller.undo_history.clear()
        self.view.handler_dict["dock_drop_handler"](third_id_i, 1)
        self.assertEqual(self.undocked_ids(), [])
        self.assertEqual(self.tab_ids(),
                         [first_id_i, third_id_i, second_id_i])
        self.assertEqual(list(self.view.tab_dict),
                         [first_id_i, third_id_i, second_id_i])
        self.assertNotIn(third_id_i, self.view.window_dict)
        self.assertEqual(self.view.current_tab_id(), third_id_i)
        self.undo()
        self.assertEqual(self.undocked_ids(), [third_id_i])
        self.assertIn(third_id_i, self.view.window_dict)
        self.redo()
        self.assertEqual(self.tab_ids(),
                         [first_id_i, third_id_i, second_id_i])

    @covers("LLFR-01108", "HLFR-00152")
    def test_drop_places_first_and_last(self) -> None:
        """A drop before the first tab docks it first; a place past the
        last docked tab docks it last, before the undocked tabs.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        second_id_i = self.add_tab()
        third_id_i = self.add_tab()
        self.undock(second_id_i)
        self.undock(third_id_i)
        self.view.handler_dict["dock_drop_handler"](third_id_i, 0)
        self.assertEqual(self.tab_ids(),
                         [third_id_i, first_id_i, second_id_i])
        self.view.handler_dict["dock_drop_handler"](second_id_i, 9)
        self.assertEqual(self.tab_ids(),
                         [third_id_i, first_id_i, second_id_i])
        self.assertEqual(self.undocked_ids(), [])

    @covers("LLFR-00993", "LLFR-01108")
    def test_dock_button_still_docks_last(self) -> None:
        """The dock button docks the tab as the last docked tab.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        second_id_i = self.add_tab()
        third_id_i = self.add_tab()
        self.undock(first_id_i)
        self.dock(first_id_i)
        self.assertEqual(self.tab_ids(),
                         [second_id_i, third_id_i, first_id_i])


class SearchShortcutPanelTest(UndockControllerTestCase):
    """Ctrl+F (Cmd+F) shows a hidden panel first (LLFR-01106)."""

    @covers("LLFR-01106", "LLFR-01018", "LLFR-01016", "HLFR-00129")
    def test_hidden_panel_is_shown_as_one_undoable_action(self) -> None:
        """The hidden panel is shown at its first width and the show is
        undoable; a shown panel and the main window change nothing.

        Inputs: none.
        Outputs: none.
        """
        first_id_i = self.first_tab_id()
        self.add_tab()
        self.undock(first_id_i)
        self.controller.undo_history.clear()
        show = self.view.handler_dict["panel_show_handler"]
        show(self.window_of(first_id_i))
        self.assertEqual(self.view.window_dict[first_id_i][1:],
                         [True, 225])
        self.assertEqual(self.controller.undo_history.depth(), 1)
        show(self.window_of(first_id_i))
        show(-1)
        self.assertEqual(self.controller.undo_history.depth(), 1)
        self.assertTrue(self.view.window_dict[first_id_i][1])
        self.undo()
        self.assertFalse(self.view.window_dict[first_id_i][1])


if __name__ == "__main__":
    unittest.main()
