"""Tests for the curve colors of a plot (HLFR-00020)."""

import random
import re
import unittest

from tests.support import covers

from model.curve_colors import (
    MARKER_COLOR_DISTANCE_F, MARKER_COLOR_STR, MAXIMUM_LUMINANCE_F,
    MINIMUM_COLOR_DISTANCE_F,
    PALETTE_COLOR_TUPLE, color_distance, color_luminance, hex_color_or_none,
    hex_to_rgb,
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

    @covers("LLFR-00144", "LLFR-00033", "LLFR-00365", "HLFR-00020")
    def test_first_three_colors_are_blue_black_red(self) -> None:
        """The palette starts with blue, black and a dark red, in that
        order; the red is darker than, and far from, the marker color.

        Each of the three is checked by its dominant RGB channel, so the
        test does not depend on the exact shade.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(PALETTE_COLOR_TUPLE[:3],
                         ("#1f77b4", "#000000", "#b2182b"))
        red_i, green_i, blue_i = hex_to_rgb(PALETTE_COLOR_TUPLE[0])
        self.assertGreater(blue_i, max(red_i, green_i))
        self.assertEqual(hex_to_rgb(PALETTE_COLOR_TUPLE[1]), (0, 0, 0))
        red_i, green_i, blue_i = hex_to_rgb(PALETTE_COLOR_TUPLE[2])
        self.assertGreater(red_i, 2 * max(green_i, blue_i))
        # LLFR-00144, LLFR-00365: a dark red, clearly not the marker.
        self.assertLess(color_luminance(PALETTE_COLOR_TUPLE[2]),
                        color_luminance(MARKER_COLOR_STR))
        self.assertLess(red_i, hex_to_rgb(MARKER_COLOR_STR)[0])
        self.assertGreaterEqual(
            color_distance(PALETTE_COLOR_TUPLE[2], MARKER_COLOR_STR), 90.0)
        # The first, second and third curve of a plot get them.
        random_generator = random.Random(4)
        color_list = []
        for drawn_count_i in range(3):
            color_list.append(next_curve_color(drawn_count_i, color_list,
                                               random_generator))
        self.assertEqual(color_list, ["#1f77b4", "#000000", "#b2182b"])

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
    """Check the reserved marker color (LLFR-00083, LLFR-00365)."""

    @covers("LLFR-00083")
    def test_marker_color_is_orange_ff8000(self) -> None:
        """The marker color is exactly the orange #ff8000.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(MARKER_COLOR_STR, "#ff8000")
        self.assertRegex(MARKER_COLOR_STR, HEX_COLOR_PATTERN_STR)
        self.assertLessEqual(color_luminance(MARKER_COLOR_STR),
                             MAXIMUM_LUMINANCE_F)

    @covers("LLFR-00365", "LLFR-00083", "LLFR-00033")
    def test_every_palette_color_at_least_70_from_marker(self) -> None:
        """Each palette color is at a distance of at least 70 from the
        marker color; the threshold itself is 70.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(MARKER_COLOR_DISTANCE_F, 70.0)
        self.assertNotIn(MARKER_COLOR_STR, PALETTE_COLOR_TUPLE)
        for palette_color_str in PALETTE_COLOR_TUPLE:
            with self.subTest(color=palette_color_str):
                self.assertGreaterEqual(
                    color_distance(palette_color_str, MARKER_COLOR_STR),
                    70.0)
                self.assertTrue(is_far_from_marker_color(palette_color_str))
        self.assertFalse(is_far_from_marker_color(MARKER_COLOR_STR))

    @covers("LLFR-00365", "LLFR-00083")
    def test_is_far_from_marker_color_threshold(self) -> None:
        """A color just under 70 from the marker is too close; one at 70
        or more is far enough; the old palette red and orange are close.

        Inputs: none.
        Outputs: none.
        """
        # (255, 59, 0) is 69 away and (255, 58, 0) exactly 70 away.
        self.assertFalse(is_far_from_marker_color("#ff3b00"))
        self.assertTrue(is_far_from_marker_color("#ff3a00"))
        self.assertAlmostEqual(color_distance("#ff3a00", MARKER_COLOR_STR),
                               70.0)
        # The orange of the previous palette and the previous marker
        # orange are too close.
        self.assertFalse(is_far_from_marker_color("#ff7f0e"))
        self.assertFalse(is_far_from_marker_color("#ff9900"))
        # LLFR-00365: the palette red is darker than the marker color.
        self.assertLess(color_luminance(PALETTE_COLOR_TUPLE[2]),
                        color_luminance(MARKER_COLOR_STR))

    @covers("LLFR-00225", "LLFR-00319", "LLFR-00393")
    def test_hex_color_or_none(self) -> None:
        """Only a text "#rrggbb" is a color; it is returned in lowercase.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(hex_color_or_none("#FF8000"), "#ff8000")
        self.assertEqual(hex_color_or_none("#1f77b4"), "#1f77b4")
        self.assertEqual(hex_color_or_none("#AbCdEf"), "#abcdef")
        for value in ("ff8000", "#ff800", "#ff80000", "#gg8000", "Orange",
                      "", None, 16744448, ["#ff8000"], " #ff8000"):
            with self.subTest(value=value):
                self.assertIsNone(hex_color_or_none(value))

    @covers("LLFR-00365", "LLFR-00033")
    def test_palette_has_no_orange(self) -> None:
        """No palette color has the hue of an orange (red high, green
        between the red and the blue, saturated).

        Inputs: none.
        Outputs: none.
        """
        import colorsys
        for palette_color_str in PALETTE_COLOR_TUPLE:
            with self.subTest(color=palette_color_str):
                red_i, green_i, blue_i = hex_to_rgb(palette_color_str)
                hue_f, _, saturation_f = colorsys.rgb_to_hls(
                    red_i / 255.0, green_i / 255.0, blue_i / 255.0)
                # Orange hues lie between about 15 and 45 degrees.
                is_orange_b = (saturation_f > 0.4
                               and 15.0 <= hue_f * 360.0 <= 45.0)
                self.assertFalse(is_orange_b)

    @covers("LLFR-00365", "LLFR-00083", "LLFR-00034")
    def test_random_colors_avoid_marker_color(self) -> None:
        """Random curve colors keep at least 70 from the marker color.

        Even with many used colors, which makes the distance to the used
        colors relax, the distance to the marker color is never relaxed.

        Inputs: none.
        Outputs: none.
        """
        for seed_i in range(5):
            random_generator = random.Random(seed_i)
            used_color_list = list(PALETTE_COLOR_TUPLE)
            for drawn_count_i in range(8, 120):
                color_str = next_curve_color(drawn_count_i, used_color_list,
                                             random_generator)
                self.assertNotEqual(color_str, MARKER_COLOR_STR)
                self.assertGreaterEqual(
                    color_distance(color_str, MARKER_COLOR_STR), 70.0)
                used_color_list.append(color_str)

    @covers("LLFR-00365", "LLFR-00034")
    def test_random_colors_near_the_marker_are_rejected(self) -> None:
        """A generator that first offers colors close to the marker
        color gets a color only after them, far from the marker.

        Inputs: none.
        Outputs: none.
        """

        class ScriptedGenerator:
            """Gives a few orange shades first, then a dark blue.

            Inputs: none.
            Outputs: randint returns the scripted channel values.
            """

            def __init__(self) -> None:
                """Prepare the scripted values.

                Inputs: none.
                Outputs: none.
                """
                self.value_list = [255, 68, 0, 240, 80, 20, 255, 100, 40,
                                   20, 40, 120]

            def randint(self, low_i: int, high_i: int) -> int:
                """Return the next scripted value.

                Inputs:
                    low_i: lowest value (unused).
                    high_i: highest value (unused).
                Outputs: the next value of the script.
                """
                return self.value_list.pop(0)

        self.assertEqual(next_curve_color(8, [], ScriptedGenerator()),
                         "#142878")


if __name__ == "__main__":
    unittest.main()
