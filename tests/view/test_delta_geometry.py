"""Tests for the delta marker shapes and value texts (no Qt needed).

view.delta_geometry and view.value_text import only numpy and
matplotlib, so these tests also run where PyQt6 is not installed.
"""

import unittest

import numpy as np

from tests.support import covers

from view import delta_geometry, value_text
from model.workspace import DELTA_X_KIND_STR, DELTA_Y_KIND_STR

GAP_PX_F = 5.0
DEPTH_PX_F = 10.0


class BracketShapeTest(unittest.TestCase):
    """Placement and orientation of the curly brackets."""

    @covers("LLFR-00168")
    def test_delta_x_is_above_the_higher_point_tip_up(self) -> None:
        """Ends at both times, above the higher point; tip up, centred.

        Inputs: none.
        Outputs: none.
        """
        bracket_path, leader_path, tip_tuple = (
            delta_geometry.delta_geometry_tuple(
                DELTA_X_KIND_STR, (100.0, 50.0), (300.0, 80.0), GAP_PX_F,
                DEPTH_PX_F))
        vertex_array = bracket_path.vertices
        # The two ends are at the times of the points, at the same height
        # just above the higher point.
        self.assertEqual(tuple(vertex_array[0]), (100.0, 85.0))
        self.assertEqual(tuple(vertex_array[-1]), (300.0, 85.0))
        # Nothing of the bracket is below its ends: it points up.
        self.assertGreaterEqual(float(np.min(vertex_array[:, 1])), 85.0)
        self.assertEqual(tip_tuple, (200.0, 95.0))
        self.assertEqual(float(np.max(vertex_array[:, 1])), 95.0)
        # The leader lines go straight up from each point to its end.
        self.assertEqual([tuple(point) for point in leader_path.vertices],
                         [(100.0, 50.0), (100.0, 85.0),
                          (300.0, 80.0), (300.0, 85.0)])

    @covers("LLFR-00170")
    def test_delta_y_is_right_of_the_later_point_tip_right(self) -> None:
        """Ends at both values, right of the later point; tip right.

        Inputs: none.
        Outputs: none.
        """
        bracket_path, leader_path, tip_tuple = (
            delta_geometry.delta_geometry_tuple(
                DELTA_Y_KIND_STR, (300.0, 50.0), (100.0, 80.0), GAP_PX_F,
                DEPTH_PX_F))
        vertex_array = bracket_path.vertices
        # The later point is the one further right (x = 300).
        self.assertEqual(tuple(vertex_array[0]), (305.0, 50.0))
        self.assertEqual(tuple(vertex_array[-1]), (305.0, 80.0))
        self.assertGreaterEqual(float(np.min(vertex_array[:, 0])), 305.0)
        self.assertEqual(tip_tuple, (315.0, 65.0))
        self.assertEqual(float(np.max(vertex_array[:, 0])), 315.0)
        self.assertEqual([tuple(point) for point in leader_path.vertices],
                         [(300.0, 50.0), (305.0, 50.0),
                          (100.0, 80.0), (305.0, 80.0)])

    @covers("LLFR-00170")
    def test_delta_y_mirrored_left_of_the_earlier_point(self) -> None:
        """On the left side: left of the earlier point, tip left.

        Inputs: none.
        Outputs: none.
        """
        bracket_path, leader_path, tip_tuple = (
            delta_geometry.delta_geometry_tuple(
                DELTA_Y_KIND_STR, (300.0, 50.0), (100.0, 80.0), GAP_PX_F,
                DEPTH_PX_F, delta_geometry.LEFT_SIDE_STR))
        vertex_array = bracket_path.vertices
        self.assertEqual(tuple(vertex_array[0]), (95.0, 50.0))
        self.assertEqual(tuple(vertex_array[-1]), (95.0, 80.0))
        self.assertLessEqual(float(np.max(vertex_array[:, 0])), 95.0)
        self.assertEqual(tip_tuple, (85.0, 65.0))
        self.assertEqual(float(np.min(vertex_array[:, 0])), 85.0)
        self.assertEqual([tuple(point) for point in leader_path.vertices],
                         [(300.0, 50.0), (95.0, 50.0),
                          (100.0, 80.0), (95.0, 80.0)])
        # A Delta X marker ignores the side.
        x_path, _, _ = delta_geometry.delta_geometry_tuple(
            DELTA_X_KIND_STR, (100.0, 50.0), (300.0, 80.0), GAP_PX_F,
            DEPTH_PX_F, delta_geometry.LEFT_SIDE_STR)
        self.assertEqual(tuple(x_path.vertices[0]), (100.0, 85.0))

    @covers("LLFR-00170")
    def test_side_choice(self) -> None:
        """Right when it fits, else left when it fits, else more room.

        Inputs: none.
        Outputs: none.
        """
        choose = delta_geometry.choose_delta_y_side
        right_str = delta_geometry.RIGHT_SIDE_STR
        left_str = delta_geometry.LEFT_SIDE_STR
        # Area 0..500; points at 200 and 300; 150 px needed.
        self.assertEqual(choose(200.0, 300.0, 150.0, 0.0, 500.0), right_str)
        self.assertEqual(choose(300.0, 200.0, 150.0, 0.0, 500.0), right_str)
        # Later point at 450: no room right, room left of 200.
        self.assertEqual(choose(200.0, 450.0, 150.0, 0.0, 500.0), left_str)
        # Neither fits: the side with more room.
        self.assertEqual(choose(100.0, 450.0, 150.0, 0.0, 500.0), left_str)
        self.assertEqual(choose(20.0, 400.0, 150.0, 0.0, 500.0), right_str)

    @covers("LLFR-00168", "LLFR-00170")
    def test_bracket_is_symmetric_and_reversed_points_match(self) -> None:
        """Swapping the points gives the same bracket shape.

        Inputs: none.
        Outputs: none.
        """
        for kind_str in (DELTA_X_KIND_STR, DELTA_Y_KIND_STR):
            with self.subTest(kind=kind_str):
                forward_path, _, forward_tip = (
                    delta_geometry.delta_geometry_tuple(
                        kind_str, (10.0, 20.0), (90.0, 70.0), GAP_PX_F,
                        DEPTH_PX_F))
                backward_path, _, backward_tip = (
                    delta_geometry.delta_geometry_tuple(
                        kind_str, (90.0, 70.0), (10.0, 20.0), GAP_PX_F,
                        DEPTH_PX_F))
                np.testing.assert_allclose(forward_path.vertices,
                                           backward_path.vertices)
                self.assertEqual(forward_tip, backward_tip)

    @covers("LLFR-00168")
    def test_zero_width_bracket_is_drawable(self) -> None:
        """Two points at the same time still give finite vertices.

        Inputs: none.
        Outputs: none.
        """
        bracket_path, _, tip_tuple = delta_geometry.delta_geometry_tuple(
            DELTA_X_KIND_STR, (50.0, 10.0), (50.0, 30.0), GAP_PX_F,
            DEPTH_PX_F)
        self.assertTrue(np.all(np.isfinite(bracket_path.vertices)))
        self.assertEqual(tip_tuple, (50.0, 45.0))

    @covers("LLFR-00175")
    def test_path_distance(self) -> None:
        """The distance is 0 on the bracket and grows away from it.

        Inputs: none.
        Outputs: none.
        """
        bracket_path, _, tip_tuple = delta_geometry.delta_geometry_tuple(
            DELTA_X_KIND_STR, (100.0, 50.0), (300.0, 80.0), GAP_PX_F,
            DEPTH_PX_F)
        self.assertAlmostEqual(delta_geometry.path_distance_px(
            bracket_path, *tip_tuple), 0.0)
        # The straight middle part of the left half is at y = 90.
        self.assertAlmostEqual(delta_geometry.path_distance_px(
            bracket_path, 150.0, 90.0), 0.0)
        self.assertAlmostEqual(delta_geometry.path_distance_px(
            bracket_path, 150.0, 120.0), 30.0)


class HeadroomTest(unittest.TestCase):
    """The y range keeps room above a Delta X marker."""

    @covers("LLFR-00168", "LLFR-00076")
    def test_room_is_added_only_when_needed(self) -> None:
        """The top rises to leave the asked part free, never falls.

        Inputs: none.
        Outputs: none.
        """
        new_high_f = delta_geometry.headroom_high_f(0.0, 10.0, 10.0, 0.2)
        # 20 % of the new range is free above the value 10.
        self.assertAlmostEqual((new_high_f - 10.0) / (new_high_f - 0.0), 0.2)
        # A low value already has room: the curves' range is kept.
        self.assertEqual(delta_geometry.headroom_high_f(0.0, 10.0, 2.0, 0.2),
                         10.0)
        # The ratio is capped, so the range stays finite.
        self.assertTrue(np.isfinite(delta_geometry.headroom_high_f(
            0.0, 10.0, 10.0, 1.0)))


class ValueTextTest(unittest.TestCase):
    """Texts of the delta markers, in the tips' number formats."""

    @covers("LLFR-00169", "LLFR-00043")
    def test_delta_x_text(self) -> None:
        """"Δt = <value> s" with the tip's x format, sign kept.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(value_text.format_delta_x_text(1.5), "Δt = 1.5 s")
        self.assertEqual(value_text.format_delta_x_text(-0.25),
                         "Δt = -0.25 s")
        # 0.3 - 0.1 is 0.19999999999999998 in floating point.
        self.assertEqual(value_text.format_delta_x_text(0.3 - 0.1),
                         "Δt = 0.2 s")
        self.assertEqual(value_text.format_time_text(0.3 - 0.1),
                         "t = 0.2 s")
        self.assertEqual(value_text.format_delta_x_text(123456789.0),
                         f"Δt = {value_text.format_time_value(123456789.0)}"
                         f" s")

    @covers("LLFR-00171", "LLFR-00044")
    def test_delta_y_text(self) -> None:
        """"Δy = <value>" with the tip's y format, no unit, sign kept.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(value_text.format_delta_y_text(-10.0), "Δy = -10")
        self.assertEqual(value_text.format_delta_y_text(1.0 / 3.0),
                         "Δy = 0.333333")
        tip_str = value_text.format_tip_text("speed", 1.0, 1.0 / 3.0)
        self.assertEqual(tip_str, "t = 1 s\nspeed = 0.333333")


if __name__ == "__main__":
    unittest.main()
