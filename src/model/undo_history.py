"""Undo and redo history: the states to return to (HLFR-00040, HLFR-00048).

The history holds no Qt code (COR-00009). The controller records the
state of the workspace before each undoable action (LLFR-00140) and
takes the most recent one back when the user undoes (LLFR-00138). The
state the undo leaves is kept on a redo stack, so that a redo can
return to it (LLFR-00192); a new action empties that stack
(LLFR-00193).
"""

# LLFR-00139: only the 30 most recent undoable actions can be undone.
MAXIMUM_UNDO_DEPTH_I = 30


class UndoHistory:
    """Two bounded stacks of saved states, most recent on top.

    Inputs:
        maximum_depth_i: how many states each stack keeps; when one more
            is added, the oldest is dropped (LLFR-00139).
    Attributes:
        maximum_depth_i: the number of states kept at most per stack.
        snapshot_list: the states to return to by undo, oldest first.
        redo_snapshot_list: the states to return to by redo, oldest
            first; the top one is the state after the most recently
            undone action (LLFR-00192).
    """

    def __init__(self, maximum_depth_i: int = MAXIMUM_UNDO_DEPTH_I) -> None:
        """Create an empty history.

        Inputs:
            maximum_depth_i: how many states are kept, at least 1.
        Outputs: none. Raises ValueError when maximum_depth_i < 1.
        """
        # LLFR-00139: the depth of the history.
        if int(maximum_depth_i) < 1:
            raise ValueError("The undo history must keep at least one "
                             "state.")
        self.maximum_depth_i = int(maximum_depth_i)
        self.snapshot_list = []
        # LLFR-00192: nothing has been undone yet.
        self.redo_snapshot_list = []

    def _push_undo_state(self, snapshot) -> None:
        """Put a state on the undo stack, keeping its depth limit.

        Inputs:
            snapshot: the state to return to by undo.
        Outputs: none. The oldest state is dropped when the stack
            already holds maximum_depth_i states.
        """
        # LLFR-00139: keep only the most recent states, also after a
        # redo puts a state back.
        self.snapshot_list.append(snapshot)
        if len(self.snapshot_list) > self.maximum_depth_i:
            del self.snapshot_list[:-self.maximum_depth_i]

    def record(self, snapshot) -> None:
        """Save the state from before an undoable action.

        Inputs:
            snapshot: the saved state (any object; the history does not
                look inside it).
        Outputs: none. The oldest state is dropped when the history
            already holds maximum_depth_i states, and every undone
            action is forgotten.
        """
        # LLFR-00140: each undoable action saves the state before it.
        self._push_undo_state(snapshot)
        # LLFR-00193: a new action discards the undone actions.
        self.redo_snapshot_list = []

    def can_undo(self) -> bool:
        """Tell whether an action is left to undo.

        Inputs: none.
        Outputs: True when at least one state is saved for undo.
        """
        # LLFR-00141: with nothing to undo the Undo button is disabled.
        return bool(self.snapshot_list)

    def can_redo(self) -> bool:
        """Tell whether an undone action is left to redo.

        Inputs: none.
        Outputs: True when at least one state is saved for redo.
        """
        # LLFR-00194: with nothing to redo the Redo button is disabled.
        return bool(self.redo_snapshot_list)

    def depth(self) -> int:
        """Return how many actions can be undone in a row.

        Inputs: none.
        Outputs: the number of states saved for undo.
        """
        # LLFR-00139: at most maximum_depth_i.
        return len(self.snapshot_list)

    def redo_depth(self) -> int:
        """Return how many undone actions can be redone in a row.

        Inputs: none.
        Outputs: the number of states saved for redo.
        """
        # LLFR-00192 Note: every action undone since the last new one.
        return len(self.redo_snapshot_list)

    def pop(self):
        """Take out the state saved before the most recent action.

        Inputs: none.
        Outputs: the most recent saved state. Raises IndexError when the
            history is empty. The redo stack is not changed; use undo to
            keep the current state for redo.
        """
        # LLFR-00138: the most recent action not undone yet is reversed
        # first.
        if not self.snapshot_list:
            raise IndexError("There is no action to undo.")
        return self.snapshot_list.pop()

    def undo(self, current_snapshot):
        """Undo: trade the current state for the one before the action.

        Inputs:
            current_snapshot: the state shown now, after the action
                being undone; it is kept so that a redo can return to
                it (LLFR-00192).
        Outputs: the state saved before the most recent action not
            undone yet. Raises IndexError when nothing is left to undo;
            then nothing is changed.
        """
        # LLFR-00138: the most recent action not undone yet first.
        snapshot = self.pop()
        # LLFR-00192: the undone action can be redone.
        self.redo_snapshot_list.append(current_snapshot)
        if len(self.redo_snapshot_list) > self.maximum_depth_i:
            del self.redo_snapshot_list[:-self.maximum_depth_i]
        return snapshot

    def redo(self, current_snapshot):
        """Redo: trade the current state for the one after the action.

        Inputs:
            current_snapshot: the state shown now, before the action
                being redone; it is kept so that the action can be
                undone again (LLFR-00192).
        Outputs: the state saved after the most recently undone action
            not redone yet. Raises IndexError when nothing is left to
            redo; then nothing is changed.
        """
        # LLFR-00194: nothing to redo.
        if not self.redo_snapshot_list:
            raise IndexError("There is no action to redo.")
        # LLFR-00192: the most recently undone action first, and it can
        # be undone again; LLFR-00139: the undo stack keeps its limit.
        snapshot = self.redo_snapshot_list.pop()
        self._push_undo_state(current_snapshot)
        return snapshot

    def clear(self) -> None:
        """Forget every saved state, for undo and for redo.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00142: a newly opened file starts with no undo history
        # and no redo history.
        self.snapshot_list = []
        self.redo_snapshot_list = []

    def saved_snapshot_list(self) -> list:
        """Return every saved state, for undo and for redo.

        Inputs: none.
        Outputs: a new list with the undo states, oldest first, then the
            redo states, oldest first. The states themselves are the
            saved objects, so a caller may update them in place.
        """
        # LLFR-00266: renaming a synthetic signal is not undoable and
        # keeps the history, so the saved states are renamed in place.
        return list(self.snapshot_list) + list(self.redo_snapshot_list)
