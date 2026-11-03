"""Tests for the arrow shape in display pixels (view.arrow_geometry).

No Qt is needed: the functions are plain geometry used by the drawn
arrows and by the plot widget's hit tests (LLFR-00373, LLFR-00374).
"""

import math
import unittest

import numpy as np

from tests.support import covers

from view import arrow_geometry


class ArrowGeometryTest(unittest.TestCase):
    """The arrowhead, the hit tests and the path of an arrow."""

    @covers("LLFR-00373")
    def test_head_points_at_the_end_away_from_the_start(self) -> None:
        """The head's point is the end, its back corners are behind it,
        on both sides of the line, at the nominal size in points.

        Inputs: none.
        Outputs: none.
        """
        vertex_array = arrow_geometry.head_vertex_array(
            (0.0, 0.0), (100.0, 0.0), 1.0)
        self.assertEqual(tuple(vertex_array[0]), (100.0, 0.0))
        length_f = arrow_geometry.ARROW_HEAD_LENGTH_POINTS_F
        half_f = arrow_geometry.ARROW_HEAD_HALF_WIDTH_POINTS_F
        self.assertTrue(np.allclose(vertex_array[1],
                                    (100.0 - length_f, half_f)))
        self.assertTrue(np.allclose(vertex_array[2],
                                    (100.0 - length_f, -half_f)))
        # Twice the pixels per point give a head twice as large.
        large_array = arrow_geometry.head_vertex_array(
            (0.0, 0.0), (100.0, 0.0), 2.0)
        self.assertAlmostEqual(100.0 - large_array[1][0], 2.0 * length_f)
        # A short arrow gets a smaller head; equal ends give a point.
        short_array = arrow_geometry.head_vertex_array(
            (0.0, 0.0), (5.0, 0.0), 1.0)
        self.assertLessEqual(5.0 - short_array[1][0], 3.0 + 1e-9)
        same_array = arrow_geometry.head_vertex_array(
            (3.0, 4.0), (3.0, 4.0), 1.0)
        self.assertTrue(np.allclose(same_array, 3 * [[3.0, 4.0]]))

    @covers("LLFR-00373")
    def test_points_on_the_line_and_on_the_head(self) -> None:
        """Distances to the segment and points in the head triangle.

        Inputs: none.
        Outputs: none.
        """
        self.assertAlmostEqual(arrow_geometry.segment_distance_f(
            (50.0, 4.0), (0.0, 0.0), (100.0, 0.0)), 4.0)
        self.assertAlmostEqual(arrow_geometry.segment_distance_f(
            (-3.0, 4.0), (0.0, 0.0), (100.0, 0.0)), 5.0)
        self.assertAlmostEqual(arrow_geometry.segment_distance_f(
            (1.0, 1.0), (0.0, 0.0), (0.0, 0.0)), math.sqrt(2.0))
        vertex_array = arrow_geometry.head_vertex_array(
            (0.0, 0.0), (100.0, 0.0), 1.0)
        self.assertTrue(arrow_geometry.point_in_triangle_b(
            (97.0, 0.5), vertex_array))
        self.assertTrue(arrow_geometry.point_in_triangle_b(
            tuple(vertex_array[1]), vertex_array))
        self.assertFalse(arrow_geometry.point_in_triangle_b(
            (90.0, 8.0), vertex_array))

    @covers("LLFR-00373", "LLFR-00374", "LLFR-00776")
    def test_path_with_and_without_head(self) -> None:
        """With its head, the path is the line to the head's back and the
        closed head; without it, only the line to the end.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.path import Path
        path = arrow_geometry.arrow_path((0.0, 0.0), (100.0, 0.0), 1.0,
                                         True)
        self.assertEqual(len(path.vertices), 6)
        self.assertEqual(list(path.codes),
                         [Path.MOVETO, Path.LINETO, Path.MOVETO,
                          Path.LINETO, Path.LINETO, Path.CLOSEPOLY])
        self.assertLess(path.vertices[1][0], 100.0)
        self.assertEqual(tuple(path.vertices[2]), (100.0, 0.0))
        line_path = arrow_geometry.arrow_path((0.0, 0.0), (100.0, 0.0),
                                              1.0, False)
        self.assertEqual(line_path.vertices.tolist(),
                         [[0.0, 0.0], [100.0, 0.0]])


if __name__ == "__main__":
    unittest.main()
