"""Tests for the label position of a pinned tip in the model
(HLFR-00041).

A moved tip keeps the point whose values it shows; only the offset of
its label changes (LLFR-00152).
"""

import math
import random
import unittest

from tests.support import covers

from model.workspace import (
    AUTOMATIC_LABEL_OFFSET_TUPLE, PinnedTip, Plot, Workspace)


class PinnedTipPositionTest(unittest.TestCase):
    """Plot.move_pinned_tip and the default label offset."""

    def setUp(self) -> None:
        """Create a plot with one curve and two tips at the same point.

        Inputs: none.
        Outputs: none.
        """
        workspace = Workspace(random.Random(3))
        self.plot = workspace.add_plot(workspace.tab_list[0].tab_id_i)
        self.plot.add_curve("Speed")
        self.first_tip = self.plot.add_pinned_tip("Speed", 1.0, 2.0)
        self.second_tip = self.plot.add_pinned_tip("Speed", 1.0, 2.0)

    @covers("LLFR-00152")
    def test_new_tip_has_the_automatic_offset(self) -> None:
        """A tip that was never moved has the empty (automatic) offset.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(AUTOMATIC_LABEL_OFFSET_TUPLE, ())
        self.assertEqual(self.first_tip.label_offset_tuple, ())
        self.assertEqual(PinnedTip("Speed", 1.0, 2.0).label_offset_tuple,
                         ())

    @covers("LLFR-00152", "HLFR-00041")
    def test_move_changes_only_the_label_offset(self) -> None:
        """The offset is stored as floats; signal, time, value stay.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(self.plot.move_pinned_tip(self.first_tip,
                                                  (-40, 25.5)))
        self.assertEqual(self.first_tip.label_offset_tuple, (-40.0, 25.5))
        self.assertIsInstance(self.first_tip.label_offset_tuple[0], float)
        self.assertEqual((self.first_tip.signal_name_str,
                          self.first_tip.time_s, self.first_tip.value_f),
                         ("Speed", 1.0, 2.0))
        # An equal tip at the same point is a different tip.
        self.assertEqual(self.second_tip.label_offset_tuple, ())
        self.assertTrue(self.plot.move_pinned_tip(self.first_tip,
                                                  [3.0, -4.0]))
        self.assertEqual(self.first_tip.label_offset_tuple, (3.0, -4.0))
        self.assertEqual(len(self.plot.pinned_tip_list), 2)

    @covers("LLFR-00152")
    def test_move_of_a_tip_not_in_the_plot_returns_false(self) -> None:
        """A tip of another plot, or a removed tip, is not moved.

        Inputs: none.
        Outputs: none.
        """
        stranger_tip = PinnedTip("Speed", 1.0, 2.0)
        self.assertFalse(self.plot.move_pinned_tip(stranger_tip,
                                                   (1.0, 1.0)))
        self.assertEqual(stranger_tip.label_offset_tuple, ())
        self.plot.remove_pinned_tip(self.second_tip)
        self.assertFalse(self.plot.move_pinned_tip(self.second_tip,
                                                   (1.0, 1.0)))
        self.assertEqual(self.second_tip.label_offset_tuple, ())

    @covers("LLFR-00152")
    def test_invalid_offsets_raise_and_change_nothing(self) -> None:
        """Offsets that are not two finite numbers are refused.

        Inputs: none.
        Outputs: none.
        """
        self.plot.move_pinned_tip(self.first_tip, (5.0, 6.0))
        for bad_offset in ((), (1.0,), (1.0, 2.0, 3.0), (math.nan, 1.0),
                           (1.0, math.inf), ("left", 1.0)):
            with self.subTest(offset=bad_offset):
                with self.assertRaises(ValueError):
                    self.plot.move_pinned_tip(self.first_tip, bad_offset)
                self.assertEqual(self.first_tip.label_offset_tuple,
                                 (5.0, 6.0))

    @covers("LLFR-00152", "LLFR-00047")
    def test_moved_tip_is_removed_with_its_curve(self) -> None:
        """A moved tip still belongs to its curve.

        Inputs: none.
        Outputs: none.
        """
        self.plot.move_pinned_tip(self.first_tip, (10.0, 10.0))
        self.plot.remove_curve("Speed")
        self.assertEqual(self.plot.pinned_tip_list, [])
        self.assertIsInstance(self.plot, Plot)


if __name__ == "__main__":
    unittest.main()
