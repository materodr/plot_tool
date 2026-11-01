"""Tests for redo in the plot controller, with a fake view (HLFR-00048).

The undoable actions of LLFR-00140 are run, undone and redone, and the
model and the fake view are compared with their state from after the
action. No Qt is needed. The shared setup of the undo tests is reused.
"""

import unittest

from tests.support import covers

from controller.plot_tools import DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR
from model.undo_history import MAXIMUM_UNDO_DEPTH_I
from tests.controller.test_plot_controller import make_signal_file
from tests.controller.test_undo_controller import UndoControllerTestCase


class RedoControllerTestCase(UndoControllerTestCase):
    """Undo setup plus helpers to redo and to pick delta marker points."""

    def redo(self) -> None:
        """Run the Redo handler as the button or the shortcut does.

        Inputs: none.
        Outputs: none.
        """
        self.handler("redo")()

    def redo_depth(self) -> int:
        """Return how many undone actions can be redone.

        Inputs: none.
        Outputs: the depth of the redo stack.
        """
        return self.controller.undo_history.redo_depth()

    def pick(self, plot_id_i: int, signal_name_str: str,
             time_s: float) -> None:
        """Report a delta tool click on a curve sample.

        Inputs:
            plot_id_i: the clicked plot.
            signal_name_str: "s<k>", whose value is k * time.
            time_s: the time of the sample.
        Outputs: none.
        """
        value_f = float(signal_name_str[1:]) * time_s
        self.handler("delta_point_pick_handler")(
            plot_id_i, signal_name_str, time_s, value_f)

    def delta_dump(self) -> dict:
        """Return the delta markers drawn in every plot shown.

        Inputs: none.
        Outputs: plot id -> tuple of the drawn delta marker tuples.
        """
        return {plot_id_i: tuple(tuple(entry) for entry in
                                 self.view.delta_drawn_dict.get(
                                     plot_id_i, []))
                for tab_id_i in self.view.tab_dict
                for plot_id_i in self.view.plot_id_list(tab_id_i)}

    def assert_redoable(self, action) -> None:
        """Run an action, undo it, redo it and compare with after it.

        Inputs:
            action: function without arguments that runs one handler.
        Outputs: none.
        """
        before_tuple = self.workspace.state_tuple()
        depth_i = self.depth()
        action()
        after_tuple = self.workspace.state_tuple()
        after_dump = self.model_dump()
        after_delta_dict = self.delta_dump()
        after_tab_id_i = self.view.current_tab_id()
        self.assertNotEqual(after_tuple, before_tuple)
        self.assertFalse(self.view.redo_enabled_b)
        self.undo()
        self.assertEqual(self.workspace.state_tuple(), before_tuple)
        # LLFR-00194: something can be redone now.
        self.assertTrue(self.view.redo_enabled_b)
        self.assertEqual(self.redo_depth(), 1)
        self.redo()
        # LLFR-00192: the state after the action, model and view.
        self.assertEqual(self.workspace.state_tuple(), after_tuple)
        self.assertEqual(self.model_dump(), after_dump)
        self.assert_view_matches_model()
        self.assertEqual(self.delta_dump(), after_delta_dict)
        self.assertEqual(self.view.current_tab_id(), after_tab_id_i)
        self.assertFalse(self.view.redo_enabled_b)
        self.assertEqual(self.redo_depth(), 0)
        # LLFR-00192: the action can be undone again.
        self.assertEqual(self.depth(), depth_i + 1)
        self.assertTrue(self.view.undo_enabled_b)
        self.undo()
        self.assertEqual(self.workspace.state_tuple(), before_tuple)
        self.assert_view_matches_model()
        self.redo()
        self.assertEqual(self.workspace.state_tuple(), after_tuple)


class RedoEachActionTest(RedoControllerTestCase):
    """Each undoable action of LLFR-00140 is redone after an undo."""

    @covers("LLFR-00192", "LLFR-00194", "LLFR-00026", "LLFR-00028",
            "LLFR-00030")
    def test_tab_actions(self) -> None:
        """Adding, deleting and renaming a tab are redone.

        Inputs: none.
        Outputs: none.
        """
        self.assert_redoable(lambda: self.handler("add_tab")())
        self.assert_redoable(
            lambda: self.handler("delete_tab")(self.second_tab_id_i))
        self.assert_redoable(
            lambda: self.handler("rename_tab")(self.first_tab_id_i, "Brake"))
        self.assertEqual(self.view.tab_dict[self.first_tab_id_i], "Brake")

    @covers("LLFR-00192", "LLFR-00019", "LLFR-00049", "LLFR-00021",
            "LLFR-00039", "LLFR-00041")
    def test_plot_and_curve_actions(self) -> None:
        """Creating and deleting a plot, adding, removing and widening a
        curve are redone.

        Inputs: none.
        Outputs: none.
        """
        self.assert_redoable(lambda: self.double_click("s5"))
        self.assert_redoable(
            lambda: self.handler("plot_delete_handler")(
                self.second_plot_id_i))
        self.assert_redoable(lambda: self.drop(self.plot_id_i, "s6"))
        self.assert_redoable(
            lambda: self.handler("curve_delete_handler")(self.plot_id_i,
                                                         "s2"))
        self.assert_redoable(
            lambda: self.handler("curve_width_handler")(self.plot_id_i,
                                                        "s1", 4))
        plot = self.workspace.find_plot(self.plot_id_i)
        self.assertEqual(plot.find_curve("s1").width_i, 4)

    @covers("LLFR-00192", "LLFR-00045", "LLFR-00047", "LLFR-00152")
    def test_tip_actions(self) -> None:
        """Pinning, moving and deleting a tip are redone.

        Inputs: none.
        Outputs: none.
        """
        self.assert_redoable(
            lambda: self.handler("tip_pin_handler")(self.plot_id_i, "s2",
                                                    3.0, 6.0))
        self.assert_redoable(
            lambda: self.handler("pinned_tip_move_handler")(
                self.plot_id_i, 0, 30.0, -12.0))
        self.assert_redoable(
            lambda: self.handler("pinned_tip_delete_handler")(
                self.plot_id_i, 0))

    @covers("LLFR-00192", "LLFR-00081", "LLFR-00086", "LLFR-00088",
            "LLFR-00091")
    def test_marker_actions(self) -> None:
        """Placing, moving, renaming and deleting a marker are redone.

        Inputs: none.
        Outputs: none.
        """
        self.assert_redoable(
            lambda: self.handler("marker_place_handler")(self.plot_id_i,
                                                         4.0))
        marker_id_i = self.marker_id(0)
        self.assert_redoable(
            lambda: self.handler("marker_move_handler")(self.plot_id_i,
                                                        marker_id_i, 7.5))
        self.view.marker_name_answer_list.append("Stop")
        self.assert_redoable(
            lambda: self.handler("marker_rename_handler")(self.plot_id_i,
                                                          marker_id_i))
        self.assert_redoable(
            lambda: self.handler("marker_delete_handler")(self.plot_id_i,
                                                          marker_id_i))
        # LLFR-00205: the markers belong to the workspace.
        self.assertIsNone(self.workspace.find_marker(marker_id_i))

    @covers("LLFR-00192", "LLFR-00164", "LLFR-00176", "LLFR-00178")
    def test_delta_marker_actions(self) -> None:
        """Placing and deleting delta markers, and removing a curve with a
        delta marker, are redone.

        Inputs: none.
        Outputs: none.
        """
        self.handler("plot_tool")(DELTA_X_TOOL_STR)

        def place_delta_x() -> None:
            """Pick two points of a Delta X marker.

            Inputs: none.
            Outputs: none.
            """
            self.pick(self.plot_id_i, "s1", 2.0)
            self.pick(self.plot_id_i, "s2", 5.0)

        self.assert_redoable(place_delta_x)
        plot = self.workspace.find_plot(self.plot_id_i)
        self.assertEqual(len(plot.delta_marker_list), 1)
        self.handler("plot_tool")(DELTA_Y_TOOL_STR)

        def place_delta_y() -> None:
            """Pick two points of a Delta Y marker.

            Inputs: none.
            Outputs: none.
            """
            self.pick(self.plot_id_i, "s1", 1.0)
            self.pick(self.plot_id_i, "s1", 8.0)

        self.assert_redoable(place_delta_y)
        plot = self.workspace.find_plot(self.plot_id_i)
        self.assertEqual(len(plot.delta_marker_list), 2)
        delta_marker_id_i = plot.delta_marker_list[1].delta_marker_id_i
        self.assert_redoable(
            lambda: self.handler("delta_marker_delete_handler")(
                self.plot_id_i, delta_marker_id_i))
        # LLFR-00178: removing s2 also removes the Delta X marker; the
        # redo removes both again.
        self.assert_redoable(
            lambda: self.handler("curve_delete_handler")(self.plot_id_i,
                                                         "s2"))
        plot = self.workspace.find_plot(self.plot_id_i)
        self.assertEqual(plot.delta_marker_list, [])

    @covers("LLFR-00192", "LLFR-00167")
    def test_redo_discards_a_pending_first_point(self) -> None:
        """A picked first point is discarded by a redo, like by an undo.

        Inputs: none.
        Outputs: none.
        """
        self.handler("add_tab")()
        self.undo()
        self.handler("plot_tool")(DELTA_X_TOOL_STR)
        self.pick(self.plot_id_i, "s1", 2.0)
        self.assertTrue(self.controller.pending_delta_tuple)
        self.redo()
        self.assertEqual(self.controller.pending_delta_tuple, ())
        self.assertEqual(len(self.view.tab_dict), 3)


class RedoHistoryBehaviourTest(RedoControllerTestCase):
    """Order, availability, new actions and file opening."""

    @covers("LLFR-00194")
    def test_nothing_to_redo_does_nothing(self) -> None:
        """With nothing undone, redo changes neither model nor view.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(self.view.redo_enabled_b)
        self.handler("add_tab")()
        before_tuple = self.workspace.state_tuple()
        self.view.call_list.clear()
        self.redo()
        self.assertEqual(self.workspace.state_tuple(), before_tuple)
        self.assertEqual(self.view.call_list, [])
        self.assertFalse(self.view.redo_enabled_b)
        self.assertEqual(self.depth(), 1)

    @covers("LLFR-00194", "LLFR-00141")
    def test_buttons_follow_the_history(self) -> None:
        """Redo is enabled after an undo and disabled after redoing all.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(self.view.undo_enabled_b)
        self.assertFalse(self.view.redo_enabled_b)
        self.handler("add_tab")()
        self.handler("add_tab")()
        self.assertFalse(self.view.redo_enabled_b)
        self.undo()
        self.assertTrue(self.view.redo_enabled_b)
        self.undo()
        self.assertTrue(self.view.redo_enabled_b)
        self.assertFalse(self.view.undo_enabled_b)
        self.redo()
        self.assertTrue(self.view.redo_enabled_b)
        self.assertTrue(self.view.undo_enabled_b)
        self.redo()
        self.assertFalse(self.view.redo_enabled_b)
        self.assertTrue(self.view.undo_enabled_b)

    @covers("LLFR-00192", "LLFR-00139", "LLFR-00138")
    def test_redo_every_undone_action_in_order(self) -> None:
        """31 actions: 30 undos, then 30 redos back to the last state.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(MAXIMUM_UNDO_DEPTH_I, 30)
        state_list = [self.workspace.state_tuple()]
        for index_i in range(1, 32):
            self.handler("rename_tab")(self.first_tab_id_i,
                                       f"Name {index_i}")
            state_list.append(self.workspace.state_tuple())
        while self.view.undo_enabled_b:
            self.undo()
        self.assertEqual(self.workspace.state_tuple(), state_list[1])
        self.assertEqual(self.redo_depth(), 30)
        for expected_index_i in range(2, 32):
            self.assertTrue(self.view.redo_enabled_b)
            self.redo()
            self.assertEqual(self.workspace.state_tuple(),
                             state_list[expected_index_i])
            self.assert_view_matches_model()
        self.assertFalse(self.view.redo_enabled_b)
        self.assertEqual(self.depth(), 30)
        self.assertEqual(self.view.tab_dict[self.first_tab_id_i], "Name 31")

    @covers("LLFR-00192", "LLFR-00138")
    def test_mixed_undo_and_redo(self) -> None:
        """Undo two, redo one, undo one, redo two lands on the last state.

        Inputs: none.
        Outputs: none.
        """
        state_list = [self.workspace.state_tuple()]
        action_list = [
            lambda: self.drop(self.second_plot_id_i, "s6"),
            lambda: self.handler("plot_delete_handler")(self.plot_id_i),
            lambda: self.handler("delete_tab")(self.second_tab_id_i)]
        for action in action_list:
            action()
            state_list.append(self.workspace.state_tuple())
        self.undo()
        self.undo()
        self.assertEqual(self.workspace.state_tuple(), state_list[1])
        self.redo()
        self.assertEqual(self.workspace.state_tuple(), state_list[2])
        self.undo()
        self.assertEqual(self.workspace.state_tuple(), state_list[1])
        self.redo()
        self.redo()
        self.assertEqual(self.workspace.state_tuple(), state_list[3])
        self.assert_view_matches_model()
        self.assertFalse(self.view.redo_enabled_b)

    @covers("LLFR-00193", "LLFR-00194")
    def test_new_action_clears_redo(self) -> None:
        """An undoable action after undoing discards the undone actions.

        Inputs: none.
        Outputs: none.
        """
        self.handler("add_tab")()
        self.handler("rename_tab")(self.first_tab_id_i, "A")
        self.undo()
        self.undo()
        self.assertEqual(self.redo_depth(), 2)
        self.handler("rename_tab")(self.first_tab_id_i, "B")
        self.assertFalse(self.view.redo_enabled_b)
        self.assertEqual(self.redo_depth(), 0)
        before_tuple = self.workspace.state_tuple()
        self.redo()
        self.assertEqual(self.workspace.state_tuple(), before_tuple)
        self.assertEqual(self.view.tab_dict[self.first_tab_id_i], "B")
        self.assertEqual(len(self.view.tab_dict), 2)

    @covers("LLFR-00193", "LLFR-00140")
    def test_refused_and_view_only_actions_keep_redo(self) -> None:
        """Actions that record nothing do not discard the undone ones.

        Inputs: none.
        Outputs: none.
        """
        self.handler("add_tab")()
        self.undo()
        # A refused rename, a duplicate drop, a zoom and the grid.
        self.handler("rename_tab")(self.first_tab_id_i, "   ")
        self.drop(self.plot_id_i, "s1")
        self.handler("time_range_handler")(self.plot_id_i, 2.0, 4.0)
        self.handler("grid")(True)
        self.assertTrue(self.view.redo_enabled_b)
        self.redo()
        self.assertEqual(len(self.view.tab_dict), 3)

    @covers("LLFR-00142", "LLFR-00194", "LLFR-00013")
    def test_opening_a_file_clears_redo(self) -> None:
        """A replaced file leaves nothing to undo and nothing to redo.

        Inputs: none.
        Outputs: none.
        """
        self.handler("add_tab")()
        self.handler("rename_tab")(self.first_tab_id_i, "Z")
        self.undo()
        self.assertTrue(self.view.redo_enabled_b)
        self.file_controller.open(make_signal_file(3), True)
        self.assertEqual(self.redo_depth(), 0)
        self.assertFalse(self.view.redo_enabled_b)
        self.assertFalse(self.view.undo_enabled_b)
        before_tuple = self.workspace.state_tuple()
        self.redo()
        self.assertEqual(self.workspace.state_tuple(), before_tuple)
        self.assertEqual(list(self.view.tab_dict.values()), ["Tab 1"])

    @covers("LLFR-00192")
    def test_redo_selects_the_tab_shown_when_undoing(self) -> None:
        """Redo selects the tab that was selected when the undo ran.

        Inputs: none.
        Outputs: none.
        """
        self.view.set_current_tab(self.second_tab_id_i)
        self.handler("rename_tab")(self.first_tab_id_i, "Other")
        self.undo()
        self.view.set_current_tab(self.first_tab_id_i)
        self.redo()
        self.assertEqual(self.view.current_tab_id(), self.second_tab_id_i)


if __name__ == "__main__":
    unittest.main()
