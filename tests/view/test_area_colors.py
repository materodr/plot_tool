"""Tests for the four area colors of view.theme (LLFR-00351,
LLFR-00305, LLFR-00306) and the orange marker color they start from
(LLFR-00083). No Qt is needed.
"""

import itertools
import unittest

from matplotlib.colors import to_rgb

from tests.support import covers

from model.curve_colors import MARKER_COLOR_STR, PALETTE_COLOR_TUPLE
from model.workspace import (
    AREA_COLOR_NAME_TUPLE, DEFAULT_AREA_COLOR_NAME_STR)
from view import theme

# The opacity of view.plot_widget.AREA_ALPHA_F, which needs Qt to import.
AREA_ALPHA_F = 0.25
# Smallest RGB distance (Euclidean, 0 to 255 per channel) between two
# area colors as drawn see-through on the plot background. Drawn at an
# opacity of 0.25 over white, every channel lies between about 191 and
# 255, so 40 units is a clear difference in that narrow band (two shades
# closer than about 25 units are hard to tell apart side by side).
MINIMUM_DRAWN_DISTANCE_F = 40.0
# Smallest distance between two of the four area colors as drawn. With
# the marker color #ff8000 (LLFR-00083, LLFR-00351) as the default
# Orange, the closest pair, Yellow and Orange, is about 28 apart, still
# above the 25 units under which two shades are hard to tell apart.
MINIMUM_DRAWN_PAIR_DISTANCE_F = 25.0
# Every channel of a drawn area color is at least this light.
MINIMUM_DRAWN_CHANNEL_F = 190.0


def drawn_rgb_tuple(color_str: str) -> tuple:
    """Return a color as drawn see-through on the plot background.

    Inputs:
        color_str: the fill color.
    Outputs: (r, g, b) from 0 to 255.
    """
    background_tuple = to_rgb(theme.PLOT_BACKGROUND_COLOR_STR)
    return tuple(255.0 * (AREA_ALPHA_F * color_f
                          + (1.0 - AREA_ALPHA_F) * background_f)
                 for color_f, background_f in zip(to_rgb(color_str),
                                                  background_tuple))


class AreaColorThemeTest(unittest.TestCase):
    """The colors are pale, see-through, distinct and not curve colors."""

    @covers("LLFR-00351", "LLFR-00305", "LLFR-00083")
    def test_four_colors_and_default_is_the_see_through_marker(
            self) -> None:
        """The four names are Orange, Blue, Green and Yellow, in menu
        order; "Orange", the default, is the marker color #ff8000 itself,
        which the see-through drawing makes paler than the markers.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(AREA_COLOR_NAME_TUPLE,
                         ("Orange", "Blue", "Green", "Yellow"))
        self.assertEqual(DEFAULT_AREA_COLOR_NAME_STR, "Orange")
        self.assertEqual(tuple(theme.AREA_COLOR_DICT), AREA_COLOR_NAME_TUPLE)
        self.assertEqual(theme.AREA_COLOR_DICT["Orange"], MARKER_COLOR_STR)
        self.assertEqual(MARKER_COLOR_STR, "#ff8000")
        # Paler as drawn: every channel is at least as light as the
        # marker's, and the green and blue clearly lighter.
        drawn_tuple = drawn_rgb_tuple(theme.AREA_COLOR_DICT["Orange"])
        marker_tuple = tuple(255.0 * channel_f
                             for channel_f in to_rgb(MARKER_COLOR_STR))
        for drawn_f, marker_f in zip(drawn_tuple, marker_tuple):
            self.assertGreaterEqual(drawn_f, marker_f)
        self.assertGreater(drawn_tuple[1], marker_tuple[1] + 90.0)
        self.assertGreater(drawn_tuple[2], marker_tuple[2] + 100.0)
        # Still an orange: red is the strongest channel, then green.
        self.assertGreater(drawn_tuple[0], drawn_tuple[1])
        self.assertGreater(drawn_tuple[1], drawn_tuple[2])

    @covers("LLFR-00351")
    def test_each_color_looks_like_its_name(self) -> None:
        """Blue is mostly blue, Green mostly green and Yellow has strong
        red and green with little blue.

        Inputs: none.
        Outputs: none.
        """
        red_f, green_f, blue_f = to_rgb(theme.AREA_COLOR_DICT["Blue"])
        self.assertGreater(blue_f, max(red_f, green_f))
        red_f, green_f, blue_f = to_rgb(theme.AREA_COLOR_DICT["Green"])
        self.assertGreater(green_f, max(red_f, blue_f))
        red_f, green_f, blue_f = to_rgb(theme.AREA_COLOR_DICT["Yellow"])
        self.assertGreater(min(red_f, green_f), 0.8)
        self.assertLess(blue_f, 0.3)

    @covers("LLFR-00351", "LLFR-00306", "LLFR-00033")
    def test_colors_pale_distinct_and_never_curve_colors(self) -> None:
        """Drawn see-through, every color is light and at least 25 from
        the others as drawn; none is a curve palette color.

        Inputs: none.
        Outputs: none.
        """
        palette_set = {to_rgb(color_str) for color_str in PALETTE_COLOR_TUPLE}
        for name_str, color_str in theme.AREA_COLOR_DICT.items():
            with self.subTest(color=name_str):
                self.assertNotIn(to_rgb(color_str), palette_set)
                for channel_f in drawn_rgb_tuple(color_str):
                    self.assertGreaterEqual(channel_f,
                                            MINIMUM_DRAWN_CHANNEL_F)
        for first_str, second_str in itertools.combinations(
                theme.AREA_COLOR_DICT.values(), 2):
            with self.subTest(pair=(first_str, second_str)):
                distance_f = sum(
                    (first_f - second_f) ** 2 for first_f, second_f in zip(
                        drawn_rgb_tuple(first_str),
                        drawn_rgb_tuple(second_str))) ** 0.5
                self.assertGreaterEqual(distance_f,
                                        MINIMUM_DRAWN_PAIR_DISTANCE_F)

    @covers("LLFR-00351", "LLFR-00033", "LLFR-00365")
    def test_drawn_areas_never_look_like_a_drawn_curve(self) -> None:
        """No area color, as drawn, is a palette color either, and every
        palette color stays far from the area colors as drawn.

        Inputs: none.
        Outputs: none.
        """
        for name_str, color_str in theme.AREA_COLOR_DICT.items():
            drawn_tuple = drawn_rgb_tuple(color_str)
            for palette_color_str in PALETTE_COLOR_TUPLE:
                with self.subTest(area=name_str, curve=palette_color_str):
                    palette_tuple = tuple(
                        255.0 * channel_f
                        for channel_f in to_rgb(palette_color_str))
                    distance_f = sum(
                        (first_f - second_f) ** 2 for first_f, second_f
                        in zip(drawn_tuple, palette_tuple)) ** 0.5
                    self.assertGreaterEqual(distance_f,
                                            MINIMUM_DRAWN_DISTANCE_F)


if __name__ == "__main__":
    unittest.main()
