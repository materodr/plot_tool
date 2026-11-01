"""Tests for undo in the plot controller, with a fake view (HLFR-00040).

Every undoable action of LLFR-00140 is run, recorded and undone, and
the model and the fake view are compared with their state from before
the action. No Qt is needed.
"""

import unittest

from tests.support import covers

from controller.plot_tools import MARKER_TOOL_STR, NO_TOOL_STR, TIP_TOOL_STR
from tests.controller.test_plot_controller import (
    PlotControllerTestCase, make_signal_file)


class UndoControllerTestCase(PlotControllerTestCase):
    """Shared setup: two tabs with plots, curves, a tip and markers.

    Tab 1 ("Engine") holds a plot with s1 and s2, a pinned tip on s1
    and two markers, and a second plot with s3. Tab 2 holds a plot with
    s4 only. Tab 1 is selected, the Vertical marker tool is active and
    the undo history is empty.
    """

    def setUp(self) -> None:
        """Build the shared state through the controller handlers.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.first_tab_id_i = self.first_tab_id()
        self.handler("rename_tab")(self.first_tab_id_i, "Engine")
        self.double_click("s1")
        self.plot_id_i = self.current_plot_ids()[0]
        self.drop(self.plot_id_i, "s2")
        self.handler("tip_pin_handler")(self.plot_id_i, "s1", 2.0, 2.0)
        self.handler("plot_tool")(MARKER_TOOL_STR)
        self.handler("marker_place_handler")(self.plot_id_i, 1.0)
        self.handler("marker_place_handler")(self.plot_id_i, 6.0)
        self.double_click("s3")
        self.second_plot_id_i = self.current_plot_ids()[1]
        self.handler("add_tab")()
        self.second_tab_id_i = self.view.current_tab_id()
        self.double_click("s4")
        self.lone_plot_id_i = self.current_plot_ids()[0]
        self.view.set_current_tab(self.first_tab_id_i)
        self.controller.undo_history.clear()
        self.controller.update_undo_enabled()

    def handler(self, name_str: str):
        """Return a handler the controller gave the fake view.

        Inputs:
            name_str: the handler's key in the fake view.
        Outputs: the handler function.
        """
        return self.view.handler_dict[name_str]

    def undo(self) -> None:
        """Run the Undo handler as the button or the shortcut does.

        Inputs: none.
        Outputs: none.
        """
        self.handler("undo")()

    def depth(self) -> int:
        """Return how many actions can be undone.

        Inputs: none.
        Outputs: the depth of the undo history.
        """
        return self.controller.undo_history.depth()

    def marker_id(self, index_i: int) -> int:
        """Return the id of a marker of the main plot.

        Inputs:
            index_i: index of the marker in placing order.
        Outputs: the marker id.
        """
        plot = self.workspace.find_plot(self.plot_id_i)
        return plot.marker_list[index_i].marker_id_i

    def model_dump(self) -> tuple:
        """Return what the model holds, in the format of view_dump.

        Inputs: none.
        Outputs: a tuple (tab tuples (id, name), plot tuples (plot id,
            tab id, curves (name, color, width), tips, markers)).
        """
        tab_tuple = tuple((tab.tab_id_i, tab.name_str)
                          for tab in self.workspace.tab_list)
        plot_list = []
        for tab in self.workspace.tab_list:
            for plot in tab.plot_list:
                curve_tuple = tuple((curve.signal_name_str, curve.color_str,
                                     curve.width_i)
                                    for curve in plot.curve_list)
                tip_tuple = tuple(
                    (tip.signal_name_str, tip.time_s, tip.value_f,
                     tuple(tip.label_offset_tuple))
                    for tip in plot.pinned_tip_list)
                marker_tuple = tuple(
                    (marker.marker_id_i, marker.name_str, marker.time_s)
                    for marker in plot.marker_list)
                plot_list.append((plot.plot_id_i, tab.tab_id_i, curve_tuple,
                                  tip_tuple, marker_tuple))
        return tab_tuple, tuple(plot_list)

    def view_dump(self) -> tuple:
        """Return what the fake view shows, in the format of model_dump.

        Inputs: none.
        Outputs: see model_dump.
        """
        tab_tuple = tuple(self.view.tab_dict.items())
        plot_list = []
        for tab_id_i, _ in tab_tuple:
            for plot_id_i in self.view.plot_id_list(tab_id_i):
                curve_data_list, tip_list = self.view.drawn_dict[plot_id_i]
                curve_tuple = tuple((curve[0], curve[3], curve[4])
                                    for curve in curve_data_list)
                tip_tuple = tuple((tip[0], tip[1], tip[2], tuple(tip[3]))
                                  for tip in tip_list)
                marker_tuple = tuple(
                    tuple(marker)
                    for marker in self.view.marker_drawn_dict[plot_id_i])
                plot_list.append((plot_id_i, tab_id_i, curve_tuple,
                                  tip_tuple, marker_tuple))
        return tab_tuple, tuple(plot_list)

    def assert_view_matches_model(self) -> None:
        """Check that the fake view shows exactly what the model holds.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.view_dump(), self.model_dump())
        self.assertEqual(self.view.delete_enabled_b,
                         self.workspace.can_delete_tab())

    def assert_undoable(self, action) -> None:
        """Run an action, check it is recorded, undo it and compare.

        Inputs:
            action: function without arguments that runs one handler.
        Outputs: none.
        """
        before_tuple = self.workspace.state_tuple()
        before_dump = self.model_dump()
        before_tab_id_i = self.view.current_tab_id()
        depth_i = self.depth()
        action()
        self.assertNotEqual(self.workspace.state_tuple(), before_tuple)
        self.assertEqual(self.depth(), depth_i + 1)
        self.assertTrue(self.view.undo_enabled_b)
        self.undo()
        self.assertEqual(self.workspace.state_tuple(), before_tuple)
        self.assertEqual(self.model_dump(), before_dump)
        self.assertEqual(self.depth(), depth_i)
        self.assert_view_matches_model()
        self.assertEqual(self.view.current_tab_id(), before_tab_id_i)

    def assert_not_recorded(self, action) -> None:
        """Run an action and check that it is not recorded for undo.

        Inputs:
            action: function without arguments that runs one handler.
        Outputs: none.
        """
        depth_i = self.depth()
        enabled_b = self.view.undo_enabled_b
        action()
        self.assertEqual(self.depth(), depth_i)
        self.assertEqual(self.view.undo_enabled_b, enabled_b)


class UndoEachActionTest(UndoControllerTestCase):
    """Each undoable action of LLFR-00140 is recorded and undone."""

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00026")
    def test_add_tab(self) -> None:
        """Adding a tab is undone; the previous tab is selected again.

        Inputs: none.
        Outputs: none.
        """
        self.assert_undoable(lambda: self.handler("add_tab")())

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00028", "LLFR-00066")
    def test_delete_tab(self) -> None:
        """Deleting a tab with its plot is undone, plot and all.

        Inputs: none.
        Outputs: none.
        """
        self.assert_undoable(
            lambda: self.handler("delete_tab")(self.second_tab_id_i))
        self.assertTrue(self.view.delete_enabled_b)
        # Deleting the selected tab is undone too.
        self.view.set_current_tab(self.second_tab_id_i)
        self.assert_undoable(
            lambda: self.handler("delete_tab")(self.second_tab_id_i))

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00030")
    def test_rename_tab(self) -> None:
        """Renaming a tab is undone to the previous name.

        Inputs: none.
        Outputs: none.
        """
        self.assert_undoable(
            lambda: self.handler("rename_tab")(self.first_tab_id_i, "Brake"))
        self.assertEqual(self.view.tab_dict[self.first_tab_id_i], "Engine")

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00019", "LLFR-00020")
    def test_create_plot(self) -> None:
        """A double-click plot is undone as one action, plot and curve.

        Inputs: none.
        Outputs: none.
        """
        self.assert_undoable(lambda: self.double_click("s5"))
        self.assertEqual(len(self.current_plot_ids()), 2)

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00049")
    def test_delete_plot(self) -> None:
        """Deleting a plot is undone, in its old place in the tab.

        Inputs: none.
        Outputs: none.
        """
        self.assert_undoable(
            lambda: self.handler("plot_delete_handler")(self.plot_id_i))
        self.assertEqual(self.current_plot_ids(),
                         [self.plot_id_i, self.second_plot_id_i])

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00021")
    def test_add_curve(self) -> None:
        """A dropped curve is undone; dropping it again gives its color.

        Inputs: none.
        Outputs: none.
        """
        self.drop(self.plot_id_i, "s5")
        color_str = self.workspace.find_plot(
            self.plot_id_i).find_curve("s5").color_str
        self.undo()
        self.assert_undoable(lambda: self.drop(self.plot_id_i, "s5"))
        self.drop(self.plot_id_i, "s5")
        self.assertEqual(self.workspace.find_plot(
            self.plot_id_i).find_curve("s5").color_str, color_str)

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00039")
    def test_remove_curve(self) -> None:
        """Removing a curve is undone, with the tips pinned on it.

        Inputs: none.
        Outputs: none.
        """
        self.assert_undoable(
            lambda: self.handler("curve_delete_handler")(self.plot_id_i,
                                                         "s1"))
        plot = self.workspace.find_plot(self.plot_id_i)
        self.assertEqual(len(plot.pinned_tip_list), 1)

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00051")
    def test_remove_last_curve_undoes_the_plot_too(self) -> None:
        """Removing a plot's last curve deletes the plot; one undo brings
        back the plot with its curve.

        Inputs: none.
        Outputs: none.
        """
        self.view.set_current_tab(self.second_tab_id_i)
        self.assert_undoable(
            lambda: self.handler("curve_delete_handler")(
                self.lone_plot_id_i, "s4"))
        self.assertEqual(self.current_plot_ids(), [self.lone_plot_id_i])
        self.assertEqual(self.view.drawn_names(self.lone_plot_id_i), ["s4"])

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00041")
    def test_change_width(self) -> None:
        """Changing a curve's width is undone to the previous width.

        Inputs: none.
        Outputs: none.
        """
        self.assert_undoable(
            lambda: self.handler("curve_width_handler")(self.plot_id_i,
                                                        "s2", 4))
        plot = self.workspace.find_plot(self.plot_id_i)
        self.assertEqual(plot.find_curve("s2").width_i, 1)

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00045")
    def test_pin_tip(self) -> None:
        """Pinning a tip is undone.

        Inputs: none.
        Outputs: none.
        """
        self.assert_undoable(
            lambda: self.handler("tip_pin_handler")(self.plot_id_i, "s2",
                                                    3.0, 6.0))

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00152")
    def test_move_pinned_tip(self) -> None:
        """Moving a pinned tip is undone to its previous label place.

        Inputs: none.
        Outputs: none.
        """
        self.assert_undoable(
            lambda: self.handler("pinned_tip_move_handler")(
                self.plot_id_i, 0, 30.0, -12.0))
        # A second move from a moved place is undone to that place.
        self.handler("pinned_tip_move_handler")(self.plot_id_i, 0, 5.0, 5.0)
        self.assert_undoable(
            lambda: self.handler("pinned_tip_move_handler")(
                self.plot_id_i, 0, -8.0, 9.0))
        plot = self.workspace.find_plot(self.plot_id_i)
        self.assertEqual(plot.pinned_tip_list[0].label_offset_tuple,
                         (5.0, 5.0))

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00047")
    def test_delete_pinned_tip(self) -> None:
        """Deleting a pinned tip is undone.

        Inputs: none.
        Outputs: none.
        """
        self.assert_undoable(
            lambda: self.handler("pinned_tip_delete_handler")(
                self.plot_id_i, 0))

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00081", "LLFR-00111")
    def test_place_marker(self) -> None:
        """Placing a marker is undone; its number is not reused.

        Inputs: none.
        Outputs: none.
        """
        self.assert_undoable(
            lambda: self.handler("marker_place_handler")(self.plot_id_i,
                                                         4.0))
        self.handler("marker_place_handler")(self.plot_id_i, 4.0)
        plot = self.workspace.find_plot(self.plot_id_i)
        # LLFR-00085: the number counts from the state before the undone
        # action, so the new marker is "Marker 3" again.
        self.assertEqual(plot.marker_list[-1].name_str, "Marker 3")
        self.assertEqual(len({marker.marker_id_i
                              for marker in plot.marker_list}), 3)

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00086")
    def test_move_marker(self) -> None:
        """Moving a marker is undone to its previous time.

        Inputs: none.
        Outputs: none.
        """
        marker_id_i = self.marker_id(0)
        self.assert_undoable(
            lambda: self.handler("marker_move_handler")(self.plot_id_i,
                                                        marker_id_i, 7.5))
        plot = self.workspace.find_plot(self.plot_id_i)
        self.assertEqual(plot.find_marker(marker_id_i).time_s, 1.0)

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00088", "LLFR-00112")
    def test_rename_marker(self) -> None:
        """Renaming a marker is undone to the previous name.

        Inputs: none.
        Outputs: none.
        """
        marker_id_i = self.marker_id(1)
        self.view.marker_name_answer_list.append("Stop")
        self.assert_undoable(
            lambda: self.handler("marker_rename_handler")(self.plot_id_i,
                                                          marker_id_i))
        plot = self.workspace.find_plot(self.plot_id_i)
        self.assertEqual(plot.find_marker(marker_id_i).name_str, "Marker 2")

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00091")
    def test_delete_marker(self) -> None:
        """Deleting a marker is undone, with its id, name and time.

        Inputs: none.
        Outputs: none.
        """
        marker_id_i = self.marker_id(0)
        self.assert_undoable(
            lambda: self.handler("marker_delete_handler")(self.plot_id_i,
                                                          marker_id_i))
        plot = self.workspace.find_plot(self.plot_id_i)
        self.assertEqual(plot.marker_list[0].marker_id_i, marker_id_i)


class UndoNotRecordedTest(UndoControllerTestCase):
    """Actions that change nothing, or are not undoable, record nothing."""

    @covers("LLFR-00140", "LLFR-00067", "LLFR-00066")
    def test_refused_tab_actions(self) -> None:
        """Blank or same tab names, unknown tabs and the last tab.

        Inputs: none.
        Outputs: none.
        """
        rename = self.handler("rename_tab")
        self.assert_not_recorded(lambda: rename(self.first_tab_id_i, "  "))
        self.assert_not_recorded(
            lambda: rename(self.first_tab_id_i, " Engine "))
        self.assert_not_recorded(lambda: rename(999, "X"))
        self.assert_not_recorded(lambda: self.handler("delete_tab")(999))
        self.handler("delete_tab")(self.second_tab_id_i)
        self.controller.undo_history.clear()
        self.assert_not_recorded(
            lambda: self.handler("delete_tab")(self.first_tab_id_i))

    @covers("LLFR-00140", "LLFR-00031", "LLFR-00056", "LLFR-00019")
    def test_refused_plot_and_curve_actions(self) -> None:
        """Full tab, duplicate drop, unknown signal, plot or curve.

        Inputs: none.
        Outputs: none.
        """
        self.assert_not_recorded(lambda: self.drop(self.plot_id_i, "s1"))
        self.assert_not_recorded(lambda: self.drop(999, "s5"))
        self.assert_not_recorded(lambda: self.drop(self.plot_id_i, "nope"))
        self.assert_not_recorded(lambda: self.double_click("nope"))
        self.assert_not_recorded(
            lambda: self.handler("plot_delete_handler")(999))
        self.assert_not_recorded(
            lambda: self.handler("curve_delete_handler")(self.plot_id_i,
                                                         "s9"))
        for signal_name_str in ("s5", "s6", "s7"):
            self.double_click(signal_name_str)
        self.controller.undo_history.clear()
        self.assert_not_recorded(lambda: self.double_click("s8"))
        self.assertEqual(self.view.full_tab_count_i, 1)

    @covers("LLFR-00140", "LLFR-00041")
    def test_refused_width_changes(self) -> None:
        """The same width, a width out of range or an unknown curve.

        Inputs: none.
        Outputs: none.
        """
        width = self.handler("curve_width_handler")
        self.assert_not_recorded(lambda: width(self.plot_id_i, "s1", 1))
        self.assert_not_recorded(lambda: width(self.plot_id_i, "s1", 9))
        self.assert_not_recorded(lambda: width(self.plot_id_i, "s9", 2))
        self.assert_not_recorded(lambda: width(999, "s1", 2))

    @covers("LLFR-00140", "LLFR-00045", "LLFR-00047", "LLFR-00152")
    def test_refused_tip_actions(self) -> None:
        """Unknown curves or tips, bad offsets and a move to the same
        place.

        Inputs: none.
        Outputs: none.
        """
        self.assert_not_recorded(
            lambda: self.handler("tip_pin_handler")(self.plot_id_i, "s9",
                                                    1.0, 1.0))
        self.assert_not_recorded(
            lambda: self.handler("pinned_tip_delete_handler")(
                self.plot_id_i, 5))
        move = self.handler("pinned_tip_move_handler")
        self.assert_not_recorded(
            lambda: move(self.plot_id_i, 0, float("nan"), 1.0))
        self.assert_not_recorded(lambda: move(self.plot_id_i, 3, 1.0, 1.0))
        move(self.plot_id_i, 0, 4.0, 4.0)
        self.assert_not_recorded(lambda: move(self.plot_id_i, 0, 4.0, 4.0))

    @covers("LLFR-00140", "LLFR-00081", "LLFR-00086", "LLFR-00089")
    def test_refused_marker_actions(self) -> None:
        """No tool, unknown markers, same time, blank, same or cancelled
        names.

        Inputs: none.
        Outputs: none.
        """
        marker_id_i = self.marker_id(0)
        move = self.handler("marker_move_handler")
        rename = self.handler("marker_rename_handler")
        self.assert_not_recorded(lambda: move(self.plot_id_i,
                                              marker_id_i, 1.0))
        self.assert_not_recorded(lambda: move(self.plot_id_i, 999, 2.0))
        self.assert_not_recorded(
            lambda: self.handler("marker_delete_handler")(self.plot_id_i,
                                                          999))
        for answer in (None, "   ", "Marker 1"):
            self.view.marker_name_answer_list.append(answer)
            self.assert_not_recorded(
                lambda: rename(self.plot_id_i, marker_id_i))
        self.handler("plot_tool")(TIP_TOOL_STR)
        self.assert_not_recorded(
            lambda: self.handler("marker_place_handler")(self.plot_id_i,
                                                         3.0))

    @covers("LLFR-00140", "LLFR-00070", "LLFR-00115", "LLFR-00122",
            "LLFR-00079")
    def test_view_only_actions_are_not_undoable(self) -> None:
        """Zoom and pan, reset zoom, grid and plot tools are not recorded.

        Inputs: none.
        Outputs: none.
        """
        self.assert_not_recorded(
            lambda: self.handler("time_range_handler")(self.plot_id_i,
                                                       2.0, 4.0))
        self.assert_not_recorded(lambda: self.handler("reset_zoom")())
        self.assert_not_recorded(lambda: self.handler("grid")(True))
        self.assert_not_recorded(lambda: self.handler("grid")(False))
        self.assert_not_recorded(
            lambda: self.handler("plot_tool")(NO_TOOL_STR))
        self.assertFalse(self.view.undo_enabled_b)


class UndoHistoryBehaviourTest(UndoControllerTestCase):
    """Depth, availability and file opening."""

    @covers("LLFR-00141")
    def test_nothing_to_undo_does_nothing(self) -> None:
        """With an empty history, undo changes neither model nor view.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(self.view.undo_enabled_b)
        before_tuple = self.workspace.state_tuple()
        self.view.call_list.clear()
        self.undo()
        self.assertEqual(self.workspace.state_tuple(), before_tuple)
        self.assertEqual(self.view.call_list, [])
        self.assertFalse(self.view.undo_enabled_b)

    @covers("LLFR-00141")
    def test_button_follows_the_history(self) -> None:
        """Enabled after an action, disabled after undoing everything.

        Inputs: none.
        Outputs: none.
        """
        self.handler("add_tab")()
        self.assertTrue(self.view.undo_enabled_b)
        self.handler("add_tab")()
        self.undo()
        self.assertTrue(self.view.undo_enabled_b)
        self.undo()
        self.assertFalse(self.view.undo_enabled_b)

    @covers("LLFR-00139", "LLFR-00138")
    def test_twenty_one_actions_give_twenty_undos(self) -> None:
        """Only the 20 most recent of 21 actions can be undone, in order.

        Inputs: none.
        Outputs: none.
        """
        state_list = [self.workspace.state_tuple()]
        name_list = [f"Name {index_i}" for index_i in range(1, 22)]
        for name_str in name_list:
            self.handler("rename_tab")(self.first_tab_id_i, name_str)
            state_list.append(self.workspace.state_tuple())
        self.assertEqual(self.depth(), 20)
        for expected_index_i in range(20, 0, -1):
            self.assertTrue(self.view.undo_enabled_b)
            self.undo()
            self.assertEqual(self.workspace.state_tuple(),
                             state_list[expected_index_i])
        self.assertFalse(self.view.undo_enabled_b)
        # The first action fell out of the history: it stays done.
        self.undo()
        self.assertEqual(self.workspace.state_tuple(), state_list[1])
        self.assertEqual(self.view.tab_dict[self.first_tab_id_i], "Name 1")

    @covers("LLFR-00138", "LLFR-00140")
    def test_mixed_actions_undo_in_reverse_order(self) -> None:
        """A sequence of different actions is undone step by step.

        Inputs: none.
        Outputs: none.
        """
        state_list = [self.workspace.state_tuple()]
        marker_id_i = self.marker_id(1)
        action_list = [
            lambda: self.drop(self.second_plot_id_i, "s6"),
            lambda: self.handler("marker_move_handler")(
                self.plot_id_i, marker_id_i, 9.0),
            lambda: self.handler("plot_delete_handler")(self.plot_id_i),
            lambda: self.handler("delete_tab")(self.second_tab_id_i),
            lambda: self.handler("add_tab")()]
        for action in action_list:
            action()
            state_list.append(self.workspace.state_tuple())
        for expected_index_i in (4, 3, 2, 1, 0):
            self.undo()
            self.assertEqual(self.workspace.state_tuple(),
                             state_list[expected_index_i])
            self.assert_view_matches_model()

    @covers("LLFR-00142", "LLFR-00013", "LLFR-00141")
    def test_opening_a_file_clears_the_history(self) -> None:
        """A replaced file leaves nothing to undo.

        Inputs: none.
        Outputs: none.
        """
        self.handler("add_tab")()
        self.handler("rename_tab")(self.first_tab_id_i, "Z")
        self.assertTrue(self.view.undo_enabled_b)
        self.file_controller.open(make_signal_file(3), True)
        self.assertEqual(self.depth(), 0)
        self.assertFalse(self.view.undo_enabled_b)
        before_tuple = self.workspace.state_tuple()
        self.undo()
        self.assertEqual(self.workspace.state_tuple(), before_tuple)
        self.assertEqual(list(self.view.tab_dict.values()), ["Tab 1"])

    @covers("LLFR-00142", "LLFR-00141")
    def test_first_file_clears_actions_made_before(self) -> None:
        """Tab actions before the first file are cleared when it opens.

        Inputs: none.
        Outputs: none.
        """
        from controller.plot_controller import PlotController
        from tests.controller.test_plot_controller import (
            FakeFileController, FakePlotView)
        view = FakePlotView()
        file_controller = FakeFileController()
        controller = PlotController(view, file_controller)
        self.assertFalse(view.undo_enabled_b)
        view.handler_dict["add_tab"]()
        self.assertTrue(view.undo_enabled_b)
        file_controller.open(make_signal_file(2), False)
        self.assertFalse(controller.undo_history.can_undo())
        self.assertFalse(view.undo_enabled_b)


class UndoViewStateTest(UndoControllerTestCase):
    """Time ranges, tab selection and plot tool after an undo."""

    @covers("LLFR-00138", "LLFR-00070", "LLFR-00180")
    def test_restored_plot_shows_the_shared_range(self) -> None:
        """A recreated plot, and every other plot, show the shared range.

        Inputs: none.
        Outputs: none.
        """
        self.handler("time_range_handler")(self.plot_id_i, 2.0, 5.0)
        self.handler("plot_delete_handler")(self.plot_id_i)
        self.undo()
        for plot_id_i in (self.plot_id_i, self.second_plot_id_i,
                          self.lone_plot_id_i):
            self.assertEqual(self.view.range_dict[plot_id_i], (2.0, 5.0))

    @covers("LLFR-00138", "LLFR-00070", "LLFR-00180")
    def test_plot_restored_in_an_empty_tab_shows_the_shared_range(
            self) -> None:
        """A plot recreated in a tab left without plots takes the range.

        Inputs: none.
        Outputs: none.
        """
        self.handler("time_range_handler")(self.second_plot_id_i, 3.0, 4.0)
        self.view.set_current_tab(self.second_tab_id_i)
        self.handler("plot_delete_handler")(self.lone_plot_id_i)
        self.undo()
        self.assertEqual(self.view.range_dict[self.lone_plot_id_i],
                         (3.0, 4.0))

    @covers("LLFR-00138", "LLFR-00180")
    def test_plots_restored_after_all_were_deleted_show_whole_range(
            self) -> None:
        """With no plot left before the undo, the restored ones are unzoomed.

        Inputs: none.
        Outputs: none.
        """
        self.handler("time_range_handler")(self.plot_id_i, 3.0, 4.0)
        self.handler("delete_tab")(self.second_tab_id_i)
        self.handler("plot_delete_handler")(self.plot_id_i)
        self.handler("plot_delete_handler")(self.second_plot_id_i)
        self.assertEqual(self.controller.shared_time_range_tuple, ())
        self.undo()
        self.assertEqual(self.view.range_dict[self.second_plot_id_i],
                         (0.0, 10.0))
        self.undo()
        self.undo()
        for plot_id_i in (self.plot_id_i, self.second_plot_id_i,
                          self.lone_plot_id_i):
            self.assertEqual(self.view.range_dict[plot_id_i], (0.0, 10.0))

    @covers("LLFR-00138", "LLFR-00180")
    def test_undo_to_no_plots_resets_the_shared_range(self) -> None:
        """Undoing the creation of the only plot forgets the shared range.

        Inputs: none.
        Outputs: none.
        """
        self.file_controller.open(make_signal_file(3), True)
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.handler("time_range_handler")(plot_id_i, 3.0, 4.0)
        self.undo()
        self.assertEqual(self.controller.shared_time_range_tuple, ())
        self.view.call_list.clear()
        self.double_click("s2")
        self.assertNotIn("set_plot_time_range", self.view.method_names())

    @covers("LLFR-00138", "LLFR-00109")
    def test_plot_tool_and_grid_are_kept(self) -> None:
        """Undo changes neither the plot tool nor the grid.

        Inputs: none.
        Outputs: none.
        """
        self.handler("grid")(True)
        self.handler("add_tab")()
        self.undo()
        self.assertEqual(self.controller.plot_tool_str, MARKER_TOOL_STR)
        self.assertEqual(self.view.plot_tool_str, MARKER_TOOL_STR)
        self.assertTrue(self.controller.grid_shown_b)

    @covers("LLFR-00138")
    def test_selected_tab_follows_the_state_before(self) -> None:
        """Undo selects the tab that was selected before the action.

        Inputs: none.
        Outputs: none.
        """
        self.view.set_current_tab(self.second_tab_id_i)
        self.handler("rename_tab")(self.first_tab_id_i, "Other")
        self.view.set_current_tab(self.first_tab_id_i)
        self.undo()
        self.assertEqual(self.view.current_tab_id(), self.second_tab_id_i)

    @covers("LLFR-00138")
    def test_requests_after_undo_reach_the_restored_plots(self) -> None:
        """Handlers work on the restored plots and new ids are fresh.

        Inputs: none.
        Outputs: none.
        """
        self.handler("plot_delete_handler")(self.plot_id_i)
        self.undo()
        self.drop(self.plot_id_i, "s5")
        self.assertIn("s5", self.view.drawn_names(self.plot_id_i))
        self.double_click("s6")
        new_plot_id_i = self.current_plot_ids()[-1]
        self.assertGreater(new_plot_id_i, self.lone_plot_id_i)
        self.assert_view_matches_model()


if __name__ == "__main__":
    unittest.main()
