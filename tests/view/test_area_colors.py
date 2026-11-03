"""Tests for the colors of the areas (LLFR-00305, LLFR-00306, LLFR-00351):
the default color #ff8000 of a new area, and the see-through opacity
shared by every color the picker can give.
"""

import unittest

from matplotlib.colors import to_rgb

from tests.support import covers, requires_qt
from tests.view.test_plot_tools import PlotWidgetToolTestCase

from model.curve_colors import MARKER_COLOR_STR, PALETTE_COLOR_TUPLE
from model.workspace import DEFAULT_AREA_COLOR_STR, Workspace
from view import theme

# The opacity of view.plot_widget.AREA_ALPHA_F, which needs Qt to import.
AREA_ALPHA_F = 0.25


def drawn_rgb_tuple(color_str: str, alpha_f: float = AREA_ALPHA_F) -> tuple:
    """Return a color as drawn see-through on the plot background.

    Inputs:
        color_str: the fill color.
        alpha_f: the opacity it is drawn with.
    Outputs: (r, g, b) from 0 to 255.
    """
    background_tuple = to_rgb(theme.PLOT_BACKGROUND_COLOR_STR)
    return tuple(255.0 * (alpha_f * color_f
                          + (1.0 - alpha_f) * background_f)
                 for color_f, background_f in zip(to_rgb(color_str),
                                                  background_tuple))


class DefaultAreaColorTest(unittest.TestCase):
    """The default color of a new area (LLFR-00351). No Qt is needed."""

    @covers("LLFR-00351", "LLFR-00083", "LLFR-00305", "LLFR-00731")
    def test_new_area_gets_ff8000_drawn_paler(self) -> None:
        """A new area gets the reserved marker color #ff8000, which the
        see-through drawing shows paler than an opaque item of that
        color, and still orange.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(DEFAULT_AREA_COLOR_STR, "#ff8000")
        self.assertEqual(DEFAULT_AREA_COLOR_STR, MARKER_COLOR_STR)
        workspace = Workspace()
        plot = workspace.add_plot(workspace.tab_list[0].tab_id_i)
        plot.add_curve("Speed")
        self.assertEqual(workspace.add_area(1.0, 2.0).color_str, "#ff8000")
        drawn_tuple = drawn_rgb_tuple(DEFAULT_AREA_COLOR_STR)
        opaque_tuple = tuple(255.0 * channel_f for channel_f
                             in to_rgb(DEFAULT_AREA_COLOR_STR))
        for drawn_f, opaque_f in zip(drawn_tuple, opaque_tuple):
            self.assertGreaterEqual(drawn_f, opaque_f)
        self.assertGreater(drawn_tuple[2], opaque_tuple[2] + 100.0)
        self.assertGreater(drawn_tuple[0], drawn_tuple[1])
        self.assertGreater(drawn_tuple[1], drawn_tuple[2])


@requires_qt
class SharedAreaOpacityTest(PlotWidgetToolTestCase):
    """Every area color is drawn with the same see-through opacity
    (LLFR-00305, LLFR-00306, LLFR-00351)."""

    @covers("LLFR-00351", "LLFR-00305", "LLFR-00306", "LLFR-00732")
    def test_any_color_same_opacity_behind_the_curves(self) -> None:
        """The default color and colors the picker may give (black,
        white, a palette color, any other) are all drawn with the one
        see-through opacity, behind the curves and the grid.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import AREA_ALPHA_F as WIDGET_ALPHA_F
        self.assertEqual(WIDGET_ALPHA_F, AREA_ALPHA_F)
        self.assertLess(WIDGET_ALPHA_F, 1.0)
        color_list = [DEFAULT_AREA_COLOR_STR, "#000000", "#ffffff",
                      PALETTE_COLOR_TUPLE[0], "#7a3e9d"]
        self.plot_widget.set_grid_shown(True)
        self.plot_widget.set_areas([
            (index_i + 1, f"A{index_i}", float(2 * index_i),
             2.0 * index_i + 1.0, color_str)
            for index_i, color_str in enumerate(color_list)])
        self.draw()
        lowest_zorder_f = min(
            [line.get_zorder() for line in self.plot_widget.axes.lines]
            + [self.plot_widget.axes.xaxis.get_zorder(),
               self.plot_widget.axes.yaxis.get_zorder()])
        for index_i, color_str in enumerate(color_list):
            with self.subTest(color=color_str):
                band = self.plot_widget.area_artist_tuple(index_i + 1)[0]
                self.assertEqual(to_rgb(band.get_facecolor()),
                                 to_rgb(color_str))
                self.assertEqual(band.get_alpha(), WIDGET_ALPHA_F)
                self.assertLess(band.get_zorder(), lowest_zorder_f)


if __name__ == "__main__":
    unittest.main()
