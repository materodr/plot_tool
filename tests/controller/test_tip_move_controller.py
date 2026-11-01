"""Tests for the pinned tip move handler of the plot controller
(HLFR-00041).

The fake view and the setup of tests.controller.test_plot_controller
are reused: a real Workspace, a SignalFile built in the test and a view
that records every call (no Qt needed).
"""

import math
import unittest

from tests.support import covers

from tests.controller.test_plot_controller import PlotControllerTestCase


class TipMoveControllerTest(PlotControllerTestCase):
    """on_pinned_tip_move stores the label offset and redraws."""

    def setUp(self) -> None:
        """Open the file, plot s1 and pin two tips.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.double_click("s1")
        self.plot_id_i = self.current_plot_ids()[0]
        self.plot = self.workspace.find_plot(self.plot_id_i)
        self.view.handler_dict["tip_pin_handler"](self.plot_id_i, "s1",
                                                  2.0, 2.0)
        self.view.handler_dict["tip_pin_handler"](self.plot_id_i, "s1",
                                                  4.0, 4.0)

    def move(self, tip_index_i: int, offset_x_f: float, offset_y_f: float,
             plot_id_i: int = None) -> None:
        """Run the move handler as a released tip drag does.

        Inputs:
            tip_index_i: index of the tip.
            offset_x_f: label offset to the right, in points.
            offset_y_f: label offset upwards, in points.
            plot_id_i: id of the plot (default: the plot of the setup).
        Outputs: none.
        """
        if plot_id_i is None:
            plot_id_i = self.plot_id_i
        self.view.handler_dict["pinned_tip_move_handler"](
            plot_id_i, tip_index_i, offset_x_f, offset_y_f)

    def drawn_tips(self) -> list:
        """Return the pinned tip tuples last drawn in the plot.

        Inputs: none.
        Outputs: a list of tuples.
        """
        return self.view.drawn_dict[self.plot_id_i][1]

    @covers("LLFR-00152", "HLFR-00041")
    def test_move_stores_the_offset_and_redraws(self) -> None:
        """The moved tip is drawn with its offset and the same values.

        Inputs: none.
        Outputs: none.
        """
        self.assertIn("pinned_tip_move_handler", self.view.handler_dict)
        self.move(1, -30.0, 12.5)
        self.assertEqual(self.drawn_tips(), [("s1", 2.0, 2.0, ()),
                                             ("s1", 4.0, 4.0,
                                              (-30.0, 12.5))])
        self.assertEqual(self.plot.pinned_tip_list[1].label_offset_tuple,
                         (-30.0, 12.5))
        # A second move replaces the offset.
        self.move(1, 5.0, 6.0)
        self.assertEqual(self.drawn_tips()[1], ("s1", 4.0, 4.0, (5.0, 6.0)))

    @covers("LLFR-00152")
    def test_moved_offset_survives_other_changes(self) -> None:
        """Pinning, deleting another tip and redrawing keep the offset.

        Inputs: none.
        Outputs: none.
        """
        self.move(1, 20.0, 20.0)
        self.view.handler_dict["tip_pin_handler"](self.plot_id_i, "s1",
                                                  6.0, 6.0)
        self.view.handler_dict["pinned_tip_delete_handler"](
            self.plot_id_i, 0)
        self.assertEqual(self.drawn_tips(), [("s1", 4.0, 4.0, (20.0, 20.0)),
                                             ("s1", 6.0, 6.0, ())])

    @covers("LLFR-00152")
    def test_unknown_plot_or_tip_is_ignored(self) -> None:
        """Requests for an unknown plot or tip index change nothing.

        Inputs: none.
        Outputs: none.
        """
        before_list = list(self.drawn_tips())
        call_count_i = len(self.view.call_list)
        self.move(0, 1.0, 1.0, plot_id_i=9999)
        self.move(2, 1.0, 1.0)
        self.move(-1, 1.0, 1.0)
        self.assertEqual(self.drawn_tips(), before_list)
        self.assertEqual(len(self.view.call_list), call_count_i)
        self.assertEqual([pinned_tip.label_offset_tuple
                          for pinned_tip in self.plot.pinned_tip_list],
                         [(), ()])

    @covers("LLFR-00152")
    def test_offset_that_is_not_finite_is_ignored(self) -> None:
        """NaN or infinite offsets are not stored and nothing redraws.

        Inputs: none.
        Outputs: none.
        """
        call_count_i = len(self.view.call_list)
        self.move(0, math.nan, 1.0)
        self.move(0, 1.0, math.inf)
        self.assertEqual(len(self.view.call_list), call_count_i)
        self.assertEqual(self.plot.pinned_tip_list[0].label_offset_tuple,
                         ())


if __name__ == "__main__":
    unittest.main()
