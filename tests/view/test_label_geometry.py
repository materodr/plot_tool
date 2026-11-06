"""Tests of the Qt-free parts of the labels and menu titles of issue #183
(Part A): the place of an arrow label (view.arrow_geometry) and the
shortened menu titles (view.elided_text).

These run without PyQt6; the drawing and the menus themselves are
tested in tests/view/test_labels_view.py.
"""

import math
import unittest

from tests.support import covers

from view import arrow_geometry

BOX_TUPLE = (0.0, 0.0, 100.0, 100.0)


def corner_list(place_tuple: tuple, width_px: float,
                height_px: float) -> list:
    """Return the four corners of a turned label box.

    Inputs:
        place_tuple: (center_x_px, center_y_px, angle_deg).
        width_px: width along the line.
        height_px: height across it.
    Outputs: a list of four (x, y).
    """
    center_x_px, center_y_px, angle_deg = place_tuple
    angle_f = math.radians(angle_deg)
    unit_tuple = (math.cos(angle_f), math.sin(angle_f))
    normal_tuple = (-unit_tuple[1], unit_tuple[0])
    return [(center_x_px + along_f * unit_tuple[0] * width_px / 2.0
             + across_f * normal_tuple[0] * height_px / 2.0,
             center_y_px + along_f * unit_tuple[1] * width_px / 2.0
             + across_f * normal_tuple[1] * height_px / 2.0)
            for along_f in (-1.0, 1.0) for across_f in (-1.0, 1.0)]


class ArrowLabelPlaceTest(unittest.TestCase):
    """Where an arrow label goes (LLFR-00436, LLFR-00437, LLFR-00869,
    LLFR-00871)."""

    def assert_inside(self, place_tuple: tuple, width_px: float,
                      height_px: float) -> None:
        """Check that a label box is inside BOX_TUPLE.

        Inputs:
            place_tuple: the place of the label.
            width_px: its width.
            height_px: its height.
        Outputs: none.
        """
        for x_px, y_px in corner_list(place_tuple, width_px, height_px):
            self.assertGreaterEqual(x_px, -1e-6)
            self.assertLessEqual(x_px, 100.0 + 1e-6)
            self.assertGreaterEqual(y_px, -1e-6)
            self.assertLessEqual(y_px, 100.0 + 1e-6)

    @covers("LLFR-00436", "LLFR-00887", "HLFR-00100")
    def test_label_beside_the_middle_and_parallel(self) -> None:
        """The label is centered next to the middle of the line, beside
        it, turned to the angle of the line.

        Inputs: none.
        Outputs: none.
        """
        place_tuple = arrow_geometry.label_place_tuple(
            (20.0, 20.0), (80.0, 80.0), 20.0, 8.0, 2.0, BOX_TUPLE)
        self.assertAlmostEqual(place_tuple[2], 45.0)
        # The center is 4 + 2 pixels from the middle (50, 50), across.
        offset_x_px = place_tuple[0] - 50.0
        offset_y_px = place_tuple[1] - 50.0
        self.assertAlmostEqual(math.hypot(offset_x_px, offset_y_px), 6.0)
        self.assertAlmostEqual(offset_x_px + offset_y_px, 0.0)
        # LLFR-00887: on the upper side as the text is read.
        self.assertGreater(offset_y_px, 0.0)
        self.assertTrue(arrow_geometry.point_in_label_b(
            place_tuple[:2], place_tuple, 20.0, 8.0))
        self.assertFalse(arrow_geometry.point_in_label_b(
            (50.0, 50.0), place_tuple, 20.0, 8.0))

    @covers("LLFR-00869", "HLFR-00100")
    def test_never_upside_down(self) -> None:
        """Whatever the direction of the arrow, the text angle is
        between -90 and 90 degrees, and both directions of one line give
        the same angle.

        Inputs: none.
        Outputs: none.
        """
        for angle_deg in range(0, 360, 15):
            angle_f = math.radians(angle_deg)
            end_tuple = (50.0 + 30.0 * math.cos(angle_f),
                         50.0 + 30.0 * math.sin(angle_f))
            with self.subTest(angle=angle_deg):
                forward_tuple = arrow_geometry.label_place_tuple(
                    (50.0, 50.0), end_tuple, 10.0, 6.0, 2.0, BOX_TUPLE)
                backward_tuple = arrow_geometry.label_place_tuple(
                    end_tuple, (50.0, 50.0), 10.0, 6.0, 2.0, BOX_TUPLE)
                self.assertGreater(forward_tuple[2], -90.0 - 1e-9)
                self.assertLessEqual(forward_tuple[2], 90.0 + 1e-9)
                self.assertAlmostEqual(forward_tuple[2], backward_tuple[2])

    @covers("LLFR-00437", "LLFR-00887", "HLFR-00112", "HLFR-00100")
    def test_kept_inside_by_moving_along_the_line(self) -> None:
        """When the middle of the shown part is near the edge, the label
        moves along the line, the shortest way, to stay inside.

        Inputs: none.
        Outputs: none.
        """
        # A horizontal line whose shown part is 70 to 100: its middle is
        # 85, but a 40 px wide label must end at 100, so its center is 80.
        place_tuple = arrow_geometry.label_place_tuple(
            (70.0, 50.0), (300.0, 50.0), 40.0, 8.0, 2.0, BOX_TUPLE)
        self.assertAlmostEqual(place_tuple[0], 80.0)
        self.assertAlmostEqual(place_tuple[1], 56.0)
        self.assert_inside(place_tuple, 40.0, 8.0)
        # A line along the top edge has its label below it instead.
        place_tuple = arrow_geometry.label_place_tuple(
            (0.0, 97.0), (100.0, 97.0), 30.0, 8.0, 2.0, BOX_TUPLE)
        self.assert_inside(place_tuple, 30.0, 8.0)
        self.assertLess(place_tuple[1], 97.0)

    @covers("LLFR-00888", "LLFR-00887", "LLFR-00437", "HLFR-00100")
    def test_no_room_on_either_side_keeps_the_upper_side(self) -> None:
        """When the label fits on neither side of the line, it stays on
        the upper side, next to the middle of the shown part.

        Inputs: none.
        Outputs: none.
        """
        # A drawing area 20 px high and a label 15 px high beside a line
        # at y = 10: neither side keeps it inside.
        place_tuple = arrow_geometry.label_place_tuple(
            (-40.0, 10.0), (100.0, 10.0), 30.0, 15.0, 2.0,
            (0.0, 0.0, 100.0, 20.0))
        self.assertAlmostEqual(place_tuple[0], 50.0)
        self.assertAlmostEqual(place_tuple[1], 10.0 + 7.5 + 2.0)
        self.assertAlmostEqual(place_tuple[2], 0.0)

    @covers("LLFR-00437", "LLFR-00871", "HLFR-00112", "HLFR-00100")
    def test_follows_the_shown_part_and_hides(self) -> None:
        """The label follows the part of the line inside the drawing
        area, and is hidden when no part is inside.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(arrow_geometry.clipped_segment_tuple(
            (-50.0, 50.0), (50.0, 50.0), BOX_TUPLE),
            ((0.0, 50.0), (50.0, 50.0)))
        place_tuple = arrow_geometry.label_place_tuple(
            (-50.0, 50.0), (50.0, 50.0), 10.0, 6.0, 2.0, BOX_TUPLE)
        self.assertAlmostEqual(place_tuple[0], 25.0)
        self.assertEqual(arrow_geometry.label_place_tuple(
            (-50.0, -10.0), (-5.0, -40.0), 10.0, 6.0, 2.0, BOX_TUPLE), ())
        self.assertEqual(arrow_geometry.clipped_segment_tuple(
            (110.0, 0.0), (110.0, 100.0), BOX_TUPLE), ())
        self.assertFalse(arrow_geometry.point_in_label_b(
            (5.0, 5.0), (), 10.0, 6.0))


if __name__ == "__main__":
    unittest.main()
