"""Tests for the five area colors of view.theme (LLFR-00351,
LLFR-00305, LLFR-00306). No Qt is needed.
"""

import itertools
import unittest

from matplotlib.colors import to_rgb

from tests.support import covers

from model.curve_colors import MARKER_COLOR_STR, PALETTE_COLOR_TUPLE
from model.workspace import AREA_COLOR_NAME_TUPLE
from view import theme

# The opacity of view.plot_widget.AREA_ALPHA_F, which needs Qt to import.
AREA_ALPHA_F = 0.25
# Smallest RGB distance (0 to 255 per channel) between two area colors
# as drawn see-through on the plot background.
MINIMUM_DRAWN_DISTANCE_F = 25.0
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

    @covers("LLFR-00351", "LLFR-00305")
    def test_one_color_per_name_and_default_is_the_pale_marker(
            self) -> None:
        """Each of the five names has a color; "Magenta" is the marker
        color mixed with 45% of the background.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(tuple(theme.AREA_COLOR_DICT), AREA_COLOR_NAME_TUPLE)
        marker_tuple = to_rgb(MARKER_COLOR_STR)
        background_tuple = to_rgb(theme.PLOT_BACKGROUND_COLOR_STR)
        expected_tuple = tuple(
            0.55 * marker_f + 0.45 * background_f
            for marker_f, background_f in zip(marker_tuple,
                                              background_tuple))
        for value_f, expected_f in zip(
                to_rgb(theme.AREA_COLOR_DICT["Magenta"]), expected_tuple):
            self.assertAlmostEqual(value_f, expected_f, delta=1.0 / 255.0)

    @covers("LLFR-00351", "LLFR-00306", "LLFR-00033")
    def test_colors_pale_distinct_and_never_curve_colors(self) -> None:
        """Drawn see-through, every color is light and far enough from
        the others; none is a curve palette color or the marker color.

        Inputs: none.
        Outputs: none.
        """
        palette_set = {to_rgb(color_str) for color_str in PALETTE_COLOR_TUPLE}
        palette_set.add(to_rgb(MARKER_COLOR_STR))
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
                self.assertGreaterEqual(distance_f, MINIMUM_DRAWN_DISTANCE_F)


if __name__ == "__main__":
    unittest.main()
