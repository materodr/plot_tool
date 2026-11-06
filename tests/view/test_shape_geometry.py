"""Tests for the geometry of the shapes and the line looks (issue #260).

Pure math, with no Qt: the box of two corners (LLFR-01314), the line of
a circle and of a rectangle (LLFR-01321, LLFR-01322, LLFR-01324), the
corners that a press drags (LLFR-01338 to LLFR-01341), the label place
(LLFR-01353 to LLFR-01355) and the widths and styles of the lines
(LLFR-01373, LLFR-01378).
"""

import unittest

from tests.support import covers

from view import line_looks, shape_geometry

AREA_TUPLE = (0.0, 0.0, 100.0, 100.0)


class ShapeGeometryTest(unittest.TestCase):
    """The shapes in display pixels."""

    @covers("LLFR-01314", "LLFR-01338", "LLFR-01339", "HLFR-00158")
    def test_box_and_corners(self) -> None:
        """Any two opposite corners give the same box and corners.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(shape_geometry.box_tuple((10, 50), (30, 20)),
                         (10, 20, 30, 50))
        corner_list = shape_geometry.corner_list((30, 20), (10, 50))
        self.assertEqual(corner_list, [(10, 20), (30, 20), (30, 50),
                                       (10, 50)])
        self.assertEqual(shape_geometry.opposite_corner(0, (10, 20),
                                                        (30, 50)), (30, 50))

    @covers("LLFR-01324", "LLFR-01321", "LLFR-01322", "HLFR-00158")
    def test_distance_to_the_line(self) -> None:
        """A point on the line is at 0; the center is far from it.

        Inputs: none.
        Outputs: none.
        """
        for kind_str in ("circle", "rectangle"):
            self.assertLess(shape_geometry.line_distance_f(
                kind_str, (50.0, 80.0), (20.0, 20.0), (80.0, 80.0)), 0.5)
            self.assertGreater(shape_geometry.line_distance_f(
                kind_str, (50.0, 50.0), (20.0, 20.0), (80.0, 80.0)), 25.0)
        # LLFR-01321: a corner of the box is off the circle's line.
        self.assertGreater(shape_geometry.line_distance_f(
            "circle", (20.0, 20.0), (20.0, 20.0), (80.0, 80.0)), 5.0)
        self.assertLess(shape_geometry.line_distance_f(
            "rectangle", (20.0, 20.0), (20.0, 20.0), (80.0, 80.0)), 1e-9)

    @covers("LLFR-01340", "LLFR-01341", "HLFR-00158")
    def test_nearest_corner_and_minimum_size(self) -> None:
        """The nearest corner within 5 pixels moves; the box keeps 5
        pixels of width and height.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(shape_geometry.nearest_corner_index(
            (21.0, 22.0), (20.0, 20.0), (24.0, 80.0), 5.0), 0)
        self.assertEqual(shape_geometry.nearest_corner_index(
            (23.5, 21.0), (20.0, 20.0), (24.0, 80.0), 5.0), 1)
        self.assertEqual(shape_geometry.nearest_corner_index(
            (50.0, 50.0), (20.0, 20.0), (80.0, 80.0), 5.0), -1)
        self.assertEqual(shape_geometry.kept_apart_corner(
            (10.0, 10.0), (12.0, 30.0), (40.0, 40.0), 5.0), (15.0, 30.0))
        self.assertEqual(shape_geometry.kept_apart_corner(
            (10.0, 10.0), (8.0, 9.0), (40.0, 40.0), 5.0), (5.0, 5.0))
        self.assertEqual(shape_geometry.kept_apart_corner(
            (10.0, 10.0), (10.0, 10.0), (40.0, 0.0), 5.0), (15.0, 5.0))

    @covers("LLFR-01353", "LLFR-01354", "LLFR-01355", "HLFR-00158")
    def test_label_place_and_hidden_label(self) -> None:
        """The label sits inside the top-left corner, kept inside the
        area; with no line in the area, the label is hidden.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(shape_geometry.label_place_tuple(
            (20.0, 20.0), (60.0, 60.0), (10.0, 5.0), AREA_TUPLE, 2.0),
            (22.0, 58.0))
        self.assertEqual(shape_geometry.label_place_tuple(
            (-50.0, 20.0), (60.0, 160.0), (10.0, 5.0), AREA_TUPLE, 2.0),
            (0.0, 100.0))
        self.assertTrue(shape_geometry.line_shown_b(
            "rectangle", (-50.0, 20.0), (60.0, 160.0), AREA_TUPLE))
        self.assertFalse(shape_geometry.line_shown_b(
            "rectangle", (-50.0, -50.0), (150.0, 150.0), AREA_TUPLE))
        self.assertFalse(shape_geometry.line_shown_b(
            "circle", (200.0, 200.0), (300.0, 300.0), AREA_TUPLE))


class LineLooksTest(unittest.TestCase):
    """The widths and the styles of the lines."""

    @covers("LLFR-01373", "LLFR-01372", "LLFR-01384", "HLFR-00159")
    def test_width_factors(self) -> None:
        """Width N is width 1 times 1, 2, 3, 4.5 or 6.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual([line_looks.line_width_f(1.5, width_i)
                          for width_i in range(1, 6)],
                         [1.5, 3.0, 4.5, 6.75, 9.0])
        self.assertEqual(line_looks.line_width_f(1.5, 9), 1.5)
        self.assertEqual(line_looks.width_or_one(True), 1)
        self.assertEqual(line_looks.width_or_one(4), 4)

    @covers("LLFR-01378", "LLFR-01375", "HLFR-00160")
    def test_styles(self) -> None:
        """Continuous, the dashes of the kind, dots and dash-dots.

        Inputs: none.
        Outputs: none.
        """
        kind_dash_tuple = (0, (3.0, 1.6))
        self.assertEqual(line_looks.matplotlib_line_style("continuous"), "-")
        self.assertEqual(line_looks.matplotlib_line_style(
            "dashed", kind_dash_tuple), kind_dash_tuple)
        self.assertEqual(line_looks.matplotlib_line_style("dashed"),
                         (0, (6.0, 4.0)))
        self.assertEqual(line_looks.matplotlib_line_style("dotted"),
                         line_looks.DOTTED_DASH_TUPLE)
        self.assertEqual(line_looks.matplotlib_line_style("dash_dotted"),
                         line_looks.DASH_DOTTED_DASH_TUPLE)
        self.assertEqual(list(line_looks.LINE_STYLE_TEXT_DICT.values()),
                         ["Continuous", "Dashed", "Dotted", "Dash-dotted"])
        self.assertEqual(line_looks.line_style_or("wavy", "dashed"),
                         "dashed")


if __name__ == "__main__":
    unittest.main()
