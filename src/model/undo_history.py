"""Undo history: the states to return to when the user undoes (HLFR-00040).

The history holds no Qt code (COR-00009). The controller records the
state of the workspace before each undoable action (LLFR-00140) and
takes the most recent one back when the user undoes (LLFR-00138).
"""

# LLFR-00139: only the 20 most recent undoable actions can be undone.
MAXIMUM_UNDO_DEPTH_I = 20


class UndoHistory:
    """A bounded stack of saved states, most recent on top.

    Inputs:
        maximum_depth_i: how many states are kept; when one more is
            recorded, the oldest is dropped (LLFR-00139).
    Attributes:
        maximum_depth_i: the number of states kept at most.
        snapshot_list: the saved states, oldest first.
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

    def record(self, snapshot) -> None:
        """Save the state from before an undoable action.

        Inputs:
            snapshot: the saved state (any object; the history does not
                look inside it).
        Outputs: none. The oldest state is dropped when the history
            already holds maximum_depth_i states.
        """
        # LLFR-00140: each undoable action saves the state before it.
        self.snapshot_list.append(snapshot)
        # LLFR-00139: keep only the most recent states.
        if len(self.snapshot_list) > self.maximum_depth_i:
            del self.snapshot_list[:-self.maximum_depth_i]

    def can_undo(self) -> bool:
        """Tell whether an action is left to undo.

        Inputs: none.
        Outputs: True when at least one state is saved.
        """
        # LLFR-00141: with nothing to undo the Undo button is disabled.
        return bool(self.snapshot_list)

    def depth(self) -> int:
        """Return how many actions can be undone in a row.

        Inputs: none.
        Outputs: the number of saved states.
        """
        # LLFR-00139: at most maximum_depth_i.
        return len(self.snapshot_list)

    def pop(self):
        """Take out the state saved before the most recent action.

        Inputs: none.
        Outputs: the most recent saved state. Raises IndexError when the
            history is empty.
        """
        # LLFR-00138: the most recent action not undone yet is reversed
        # first.
        if not self.snapshot_list:
            raise IndexError("There is no action to undo.")
        return self.snapshot_list.pop()

    def clear(self) -> None:
        """Forget every saved state.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00142: a newly opened file starts with no undo history.
        self.snapshot_list = []
