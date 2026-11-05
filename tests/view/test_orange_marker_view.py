"""Tests for the orange marker color as drawn by the plot widget
(LLFR-00083, LLFR-00172, LLFR-00203, LLFR-00208, LLFR-00305,
LLFR-00352, LLFR-00353, LLFR-00365).

Every item drawn in the reserved marker color must be exactly the
orange #ff8000, its previews a paler version of that orange, and no
curve color must come close to it.
"""

import colorsys
import unittest

from tests.support import covers, requires_qt
from tests.view.test_delta_markers_view import (
    DeltaWidgetTestCase, to_hex_str)
from tests.view.test_span_zoom import SpanWidgetTestCase

from model.curve_colors import (
    MARKER_COLOR_STR, PALETTE_COLOR_TUPLE, color_distance)
from model.workspace import DELTA_Y_KIND_STR

# LLFR-00083: the marker color fixed by the requirement.
ORANGE_STR = "#ff8000"


def hue_degree_f(color_str: str) -> float:
    """Return the hue of a color, in degrees.

    Inputs:
        color_str: color written as "#rrggbb".
    Outputs: the hue, from 0 to 360 degrees.
    """
    red_f, green_f, blue_f = (int(color_str[index_i:index_i + 2], 16)
                              / 255.0 for index_i in (1, 3, 5))
    return colorsys.rgb_to_hls(red_f, green_f, blue_f)[0] * 360.0


@requires_qt
class OrangeMarkerDrawingTest(DeltaWidgetTestCase):
    """Markers, delta markers, the span line and areas are orange."""

    @covers("LLFR-00083", "LLFR-00172", "LLFR-00365", "LLFR-00660")
    def test_vertical_and_delta_markers_are_ff8000(self) -> None:
        """A vertical marker and a Delta Y marker, with its dots and
        value, are drawn in #ff8000; the curves are far from it.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(MARKER_COLOR_STR, ORANGE_STR)
        self.plot_widget.set_markers([(1, "Flag 1", 5.0)])
        self.set_delta_markers([(2, DELTA_Y_KIND_STR,
                                 self.sine_point(2.0),
                                 self.ramp_point(6.0))])
        self.draw()
        line, label, time_text = self.plot_widget.marker_artist_tuple(1)
        for artist in (line, label, time_text):
            self.assertEqual(to_hex_str(artist.get_color()), ORANGE_STR)
        bracket, leader, dots, value_label = (
            self.plot_widget.delta_artist_tuple(2))
        for patch in (bracket, leader):
            self.assertEqual(to_hex_str(patch.get_edgecolor()), ORANGE_STR)
        self.assertEqual(to_hex_str(dots.get_markerfacecolor()), ORANGE_STR)
        self.assertEqual(to_hex_str(value_label.get_color()), ORANGE_STR)
        for palette_color_str in PALETTE_COLOR_TUPLE:
            self.assertGreaterEqual(
                color_distance(palette_color_str, ORANGE_STR), 70.0)

    @covers("LLFR-00203", "LLFR-00352", "LLFR-00353", "LLFR-00083",
            "LLFR-00660")
    def test_previews_are_a_paler_orange(self) -> None:
        """The marker preview color is #ff8000 mixed with the white plot
        background: still an orange hue, lighter, and not the marker
        color itself.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_widget as plot_widget_module
        preview_str = plot_widget_module.MARKER_PREVIEW_COLOR_STR
        self.assertNotEqual(preview_str, ORANGE_STR)
        self.assertEqual(preview_str, plot_widget_module.pale_color_str(
            ORANGE_STR, "#ffffff",
            plot_widget_module.MARKER_PREVIEW_PALE_RATIO_F))
        self.assertEqual(preview_str[1:3], "ff")
        self.assertAlmostEqual(hue_degree_f(preview_str),
                               hue_degree_f(ORANGE_STR), delta=2.0)
        self.assertGreater(int(preview_str[3:5], 16), 0x44)
        self.assertGreater(int(preview_str[5:7], 16), 0x00)

    @covers("LLFR-00305", "LLFR-00351", "LLFR-00083", "LLFR-00731")
    def test_default_area_is_see_through_ff8000(self) -> None:
        """A new area, and the area preview, use #ff8000 drawn
        see-through.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_widget as plot_widget_module
        self.assertEqual(plot_widget_module.AREA_COLOR_STR, ORANGE_STR)
        self.plot_widget.set_areas([(4, "Warm-up", 3.0, 5.0)])
        self.draw()
        band = self.plot_widget.area_artist_tuple(4)[0]
        self.assertEqual(to_hex_str(band.get_facecolor()), ORANGE_STR)
        self.assertLess(band.get_alpha(), 1.0)
        preview_band = self.plot_widget.area_preview_band
        self.assertEqual(to_hex_str(preview_band.get_facecolor()),
                         ORANGE_STR)
        self.assertEqual(to_hex_str(preview_band.get_edgecolor()),
                         ORANGE_STR)


@requires_qt
class OrangeSpanLineTest(SpanWidgetTestCase):
    """The time span selection line is orange (LLFR-00208)."""

    @covers("LLFR-00208", "LLFR-00083", "LLFR-00660")
    def test_span_selection_line_is_ff8000(self) -> None:
        """While the Zoom tool drags a span, the line and its end ticks
        are drawn in #ff8000.

        Inputs: none.
        Outputs: none.
        """
        self.left_press(self.point_at(2.0, 1.0))
        self.move_to(self.point_at(6.0, 1.0))
        self.assertTrue(self.plot_widget.time_span_line_shown())
        self.assertEqual(to_hex_str(self.plot_widget.span_line.get_color()),
                         ORANGE_STR)
        self.assertEqual(
            to_hex_str(self.plot_widget.span_end_ticks.get_color()),
            ORANGE_STR)
        self.left_release(self.point_at(6.0, 1.0))


@requires_qt
class AppIconRedTest(unittest.TestCase):
    """The app icon keeps a blue and a red curve (LLFR-00183)."""

    @covers("LLFR-00183", "LLFR-00144", "LLFR-00445")
    def test_icon_red_is_the_new_dark_red(self) -> None:
        """The icon's red curve follows the palette's dark red, which is
        still red, and stays far from the dark axes and the light
        background, so it is recognizable at 16 px; its blue is the
        palette's blue.

        Inputs: none.
        Outputs: none.
        """
        from view import icons, theme
        self.assertEqual(icons.APP_ICON_RED_COLOR_STR, PALETTE_COLOR_TUPLE[2])
        self.assertEqual(icons.APP_ICON_BLUE_COLOR_STR,
                         PALETTE_COLOR_TUPLE[0])
        red_i, green_i, blue_i = (
            int(icons.APP_ICON_RED_COLOR_STR[index_i:index_i + 2], 16)
            for index_i in (1, 3, 5))
        self.assertGreater(red_i, 2 * max(green_i, blue_i))
        for other_str in (theme.APP_ICON_AXIS_COLOR_STR,
                          theme.APP_ICON_TOP_COLOR_STR,
                          theme.APP_ICON_BOTTOM_COLOR_STR,
                          icons.APP_ICON_BLUE_COLOR_STR):
            self.assertGreaterEqual(
                color_distance(icons.APP_ICON_RED_COLOR_STR, other_str),
                100.0, other_str)


if __name__ == "__main__":
    unittest.main()
