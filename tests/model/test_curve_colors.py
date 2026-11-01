"""Tests for the curve colors of a plot (HLFR-00020)."""

import random
import re
import unittest

from tests.support import covers

from model.curve_colors import (
    MARKER_COLOR_STR, MAXIMUM_LUMINANCE_F, MINIMUM_COLOR_DISTANCE_F,
    PALETTE_COLOR_TUPLE, color_distance, color_luminance, hex_to_rgb,
    is_far_from_marker_color, next_curve_color, rgb_to_hex)

HEX_COLOR_PATTERN_STR = r"^#[0-9a-f]{6}$"


class PaletteTest(unittest.TestCase):
    """Check the predefined palette of 8 colors (LLFR-00033)."""

    @covers("LLFR-00033", "HLFR-00020")
    def test_palette_has_8_distinct_valid_colors(self) -> None:
        """The palette has 8 distinct "#rrggbb" colors.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(len(PALETTE_COLOR_TUPLE), 8)
        self.assertEqual(len(set(PALETTE_COLOR_TUPLE)), 8)
        for color_str in PALETTE_COLOR_TUPLE:
            self.assertRegex(color_str, HEX_COLOR_PATTERN_STR)

    @covers("LLFR-00033")
    def test_palette_colors_are_easy_to_tell_apart(self) -> None:
        """Palette colors are far apart and visible on white.

        Inputs: none.
        Outputs: none.
        """
        for index_i, first_str in enumerate(PALETTE_COLOR_TUPLE):
            self.assertLessEqual(color_luminance(first_str),
                                 MAXIMUM_LUMINANCE_F)
            for second_str in PALETTE_COLOR_TUPLE[index_i + 1:]:
                self.assertGreaterEqual(
                    color_distance(first_str, second_str),
                    MINIMUM_COLOR_DISTANCE_F)

    @covers("LLFR-00033")
    def test_first_8_curves_use_palette_in_order(self) -> None:
        """drawn_count_i 0 to 7 return the palette colors in order.

        Inputs: none.
        Outputs: none.
        """
        random_generator = random.Random(1)
        used_color_list = []
        for drawn_count_i in range(8):
            color_str = next_curve_color(drawn_count_i, used_color_list,
                                         random_generator)
            self.assertEqual(color_str, PALETTE_COLOR_TUPLE[drawn_count_i])
            used_color_list.append(color_str)


class RandomColorTest(unittest.TestCase):
    """Check the random colors from the 9th curve on (LLFR-00034)."""

    @covers("LLFR-00034", "HLFR-00020")
    def test_9th_to_30th_colors_differ_from_all_used(self) -> None:
        """Curves 9 to 30 get valid colors far from every used color.

        Inputs: none.
        Outputs: none.
        """
        random_generator = random.Random(12345)
        used_color_list = list(PALETTE_COLOR_TUPLE)
        for drawn_count_i in range(8, 30):
            color_str = next_curve_color(drawn_count_i, used_color_list,
                                         random_generator)
            self.assertRegex(color_str, HEX_COLOR_PATTERN_STR)
            self.assertNotIn(color_str, used_color_list)
            self.assertLessEqual(color_luminance(color_str),
                                 MAXIMUM_LUMINANCE_F)
            for used_str in used_color_list:
                self.assertGreaterEqual(color_distance(color_str, used_str),
                                        MINIMUM_COLOR_DISTANCE_F)
            used_color_list.append(color_str)
        self.assertEqual(len(set(used_color_list)), 30)

    @covers("LLFR-00034")
    def test_random_color_is_not_a_palette_index(self) -> None:
        """From the 9th curve on the color is random, not the palette.

        Inputs: none.
        Outputs: none.
        """
        first_str = next_curve_color(8, [], random.Random(1))
        second_str = next_curve_color(8, [], random.Random(2))
        self.assertNotEqual(first_str, second_str)

    @covers("LLFR-00034")
    def test_seeded_generator_gives_repeatable_colors(self) -> None:
        """The same seed gives the same color.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(next_curve_color(9, [], random.Random(7)),
                         next_curve_color(9, [], random.Random(7)))

    @covers("LLFR-00034")
    def test_crowded_plot_never_repeats_a_color(self) -> None:
        """With many used colors the distance relaxes but no duplicate.

        Inputs: none.
        Outputs: none.
        """
        random_generator = random.Random(99)
        used_color_list = []
        for drawn_count_i in range(8, 208):
            color_str = next_curve_color(drawn_count_i, used_color_list,
                                         random_generator)
            self.assertNotIn(color_str, used_color_list)
            used_color_list.append(color_str)
        self.assertEqual(len(set(used_color_list)), 200)

    @covers("LLFR-00034")
    def test_used_colors_are_compared_ignoring_case(self) -> None:
        """An upper-case used color is still avoided.

        Inputs: none.
        Outputs: none.
        """
        used_color_list = [color_str.upper()
                           for color_str in PALETTE_COLOR_TUPLE]
        color_str = next_curve_color(8, used_color_list, random.Random(3))
        for used_str in used_color_list:
            self.assertGreaterEqual(color_distance(color_str, used_str),
                                    MINIMUM_COLOR_DISTANCE_F)


class ColorHelperTest(unittest.TestCase):
    """Check the color conversion helpers."""

    @covers("LLFR-00034")
    def test_hex_and_rgb_round_trip(self) -> None:
        """hex_to_rgb and rgb_to_hex are inverse.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(hex_to_rgb("#1f77b4"), (31, 119, 180))
        self.assertEqual(rgb_to_hex((31, 119, 180)), "#1f77b4")
        self.assertTrue(re.match(HEX_COLOR_PATTERN_STR,
                                 rgb_to_hex((0, 0, 255))))

    @covers("LLFR-00034")
    def test_distance_and_luminance_limits(self) -> None:
        """Distance is 0 for equal colors; white is lightest.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(color_distance("#123456", "#123456"), 0.0)
        self.assertAlmostEqual(color_distance("#000000", "#ffffff"),
                               (3 * 255 ** 2) ** 0.5)
        self.assertAlmostEqual(color_luminance("#ffffff"), 1.0)
        self.assertAlmostEqual(color_luminance("#000000"), 0.0)


class MarkerColorTest(unittest.TestCase):
    """Check the reserved vertical marker color (LLFR-00083)."""

    @covers("LLFR-00083", "LLFR-00033")
    def test_marker_color_is_not_a_palette_color(self) -> None:
        """The marker color is valid, visible and far from the palette.

        Inputs: none.
        Outputs: none.
        """
        self.assertRegex(MARKER_COLOR_STR, HEX_COLOR_PATTERN_STR)
        self.assertNotIn(MARKER_COLOR_STR, PALETTE_COLOR_TUPLE)
        self.assertLessEqual(color_luminance(MARKER_COLOR_STR),
                             MAXIMUM_LUMINANCE_F)
        for palette_color_str in PALETTE_COLOR_TUPLE:
            self.assertGreaterEqual(
                color_distance(palette_color_str, MARKER_COLOR_STR),
                MINIMUM_COLOR_DISTANCE_F, palette_color_str)
            self.assertTrue(is_far_from_marker_color(palette_color_str))
        self.assertFalse(is_far_from_marker_color(MARKER_COLOR_STR))

    @covers("LLFR-00083", "LLFR-00034")
    def test_random_colors_avoid_marker_color(self) -> None:
        """Random curve colors keep the full distance from the marker.

        Even with many used colors, which makes the distance to the used
        colors relax, the distance to the marker color is never relaxed.

        Inputs: none.
        Outputs: none.
        """
        for seed_i in range(5):
            random_generator = random.Random(seed_i)
            used_color_list = list(PALETTE_COLOR_TUPLE)
            for drawn_count_i in range(8, 80):
                color_str = next_curve_color(drawn_count_i, used_color_list,
                                             random_generator)
                self.assertNotEqual(color_str, MARKER_COLOR_STR)
                self.assertGreaterEqual(
                    color_distance(color_str, MARKER_COLOR_STR),
                    MINIMUM_COLOR_DISTANCE_F)
                used_color_list.append(color_str)


if __name__ == "__main__":
    unittest.main()
