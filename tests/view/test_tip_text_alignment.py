"""Tests that the text of the data tips is aligned to the left (HLFR-00024,
HLFR-00025).

Covers LLFR-00423: every line inside a hover data tip and a pinned data
tip starts at the left edge of the text, whichever side of its point
the box is drawn on (left of the point near the right edge, right of it
near the left edge) and also when a moved pinned tip is centred on the
position the user gave it. The check reads the drawn pixels: the left
end of the ink of the short first line ("t = ...") is where the left
end of the long second line is. No modal dialog or menu is ever opened.
"""

import unittest

import numpy as np

from tests.support import covers, requires_qt
from tests.view.test_plot_tools import BLUE_STR, PlotWidgetToolTestCase

from controller.plot_tools import TIP_TOOL_STR

# A long signal name, so the second line of a tip is much wider than
# its first line ("t = <time> s").
LONG_NAME_STR = "Long_signal_name_for_alignment"
# Pixels left out on each side of the box, so its border is not ink.
BOX_INSET_I = 3
# A pixel is text ink when all its channels are darker than this (the
# text is dark gray; the box is white; the borders are light or in the
# curve's pure color).
INK_LEVEL_I = 140
# Allowed difference, in pixels, between the left ends of two lines.
LEFT_EDGE_TOLERANCE_I = 3
# The lines must differ in width by more than this, so a right or centre
# alignment would be seen.
MINIMUM_WIDTH_DIFFERENCE_I = 15
# Tip times: near the right edge (box left of the point) and near the
# left edge (box right of the point).
RIGHT_TIME_S = 8.0
LEFT_TIME_S = 2.0
# A label offset (points), as after a drag: the box is centred there.
MOVED_OFFSET_TUPLE = (-60.0, -40.0)


@requires_qt
class TipTextAlignmentTest(PlotWidgetToolTestCase):
    """The lines of the hover and pinned tips start at the same x."""

    def setUp(self) -> None:
        """Draw one curve with a long name in the plot widget.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.plot_widget.set_curves([
            (LONG_NAME_STR, self.time_array, self.ramp_array, BLUE_STR, 1)])
        self.draw()

    def ramp_value_f(self, time_s: float) -> float:
        """Return the ramp's value at a time.

        Inputs:
            time_s: a time of the sample grid, in seconds.
        Outputs: the value of the curve there.
        """
        return float(time_s * 0.1 + 3.0)

    def line_ink_ranges(self, annotation) -> list:
        """Return the left and right ink columns of the two text lines.

        Inputs:
            annotation: the matplotlib Annotation of a drawn tip.
        Outputs: a list of two (left_px, right_px) tuples, for the top
            line and the bottom line, in buffer columns.
        """
        self.draw()
        canvas = self.plot_widget.canvas
        box = self.plot_widget.tip_box_extent(annotation)
        buffer_array = np.asarray(canvas.buffer_rgba())[..., :3].astype(int)
        height_i = buffer_array.shape[0]
        left_i = int(box.x0) + BOX_INSET_I
        right_i = int(box.x1) - BOX_INSET_I
        # Display y grows upwards; buffer rows grow downwards.
        top_i = height_i - int(box.y1) + BOX_INSET_I
        bottom_i = height_i - int(box.y0) - BOX_INSET_I
        self.assertGreater(right_i, left_i)
        self.assertGreater(bottom_i, top_i)
        middle_i = (top_i + bottom_i) // 2
        range_list = []
        for row_start_i, row_end_i in ((top_i, middle_i),
                                       (middle_i, bottom_i)):
            ink_mask_array = np.less(
                buffer_array[row_start_i:row_end_i,
                             left_i:right_i].max(axis=-1), INK_LEVEL_I)
            column_array = np.nonzero(ink_mask_array.any(axis=0))[0]
            self.assertGreater(len(column_array), 0)
            range_list.append((int(column_array.min()) + left_i,
                               int(column_array.max()) + left_i))
        return range_list

    def assert_left_aligned(self, annotation) -> None:
        """Check that both lines of a tip start at the same column.

        Inputs:
            annotation: the matplotlib Annotation of a drawn tip.
        Outputs: none.
        """
        first_tuple, second_tuple = self.line_ink_ranges(annotation)
        # The lines really differ in width, so the check is meaningful.
        self.assertGreater((second_tuple[1] - second_tuple[0])
                           - (first_tuple[1] - first_tuple[0]),
                           MINIMUM_WIDTH_DIFFERENCE_I)
        self.assertLessEqual(abs(first_tuple[0] - second_tuple[0]),
                             LEFT_EDGE_TOLERANCE_I)

    @covers("LLFR-00423", "LLFR-00042")
    def test_hover_tip_lines_start_at_the_left(self) -> None:
        """A hover tip on either side of its point is left-aligned.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(TIP_TOOL_STR)
        for time_s in (RIGHT_TIME_S, LEFT_TIME_S):
            with self.subTest(time_s=time_s):
                self.plot_widget.hover_at(
                    self.point_at(time_s, self.ramp_value_f(time_s)))
                self.assertIn(LONG_NAME_STR,
                              self.plot_widget.hover_tip_text())
                annotation = self.plot_widget.hover_annotation
                expected_str = ("right" if time_s == RIGHT_TIME_S
                                else "left")
                self.draw()
                # The box is placed on the side away from the edge.
                self.assertEqual(annotation.get_horizontalalignment(),
                                 expected_str)
                self.assert_left_aligned(annotation)

    @covers("LLFR-00423", "LLFR-00045")
    def test_pinned_tip_lines_start_at_the_left(self) -> None:
        """A pinned tip beside its point, on either side, or centred on
        a moved position, is left-aligned.

        Inputs: none.
        Outputs: none.
        """
        case_list = [
            (RIGHT_TIME_S, (), "right"),
            (LEFT_TIME_S, (), "left"),
            (RIGHT_TIME_S, MOVED_OFFSET_TUPLE, "center")]
        for time_s, offset_tuple, expected_str in case_list:
            with self.subTest(time_s=time_s, offset=offset_tuple):
                self.plot_widget.set_pinned_tips([
                    (LONG_NAME_STR, time_s, self.ramp_value_f(time_s),
                     offset_tuple)])
                self.draw()
                annotation = self.plot_widget.pinned_tip_annotation(0)
                self.assertIsNotNone(annotation)
                self.assertIn(LONG_NAME_STR,
                              self.plot_widget.pinned_tip_text(0))
                self.assertEqual(annotation.get_horizontalalignment(),
                                 expected_str)
                self.assert_left_aligned(annotation)


if __name__ == "__main__":
    unittest.main()
