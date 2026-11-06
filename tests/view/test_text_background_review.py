"""Reviewer's view tests of the text background (#270).

Independent of the implementer's tests. They follow the owner's answers
of 2026-11-06 in #270: batch 1, item 3 (the auto contrast grey and its
examples), batch 2, item 4 (the exports use the current choice), item 5
(the hover data tip keeps its white box) and item 6 (text notes and
pinned data tips). The choice of view.theme is put back after each
test, so no other test sees it.
"""

import unittest

from tests.support import covers, requires_qt
from tests.view.test_labels_view import LabelWidgetTestCase

from model.curve_colors import PALETTE_COLOR_TUPLE
from view import theme

TRANSPARENT_STR = "transparent"
AUTO_CONTRAST_STR = "auto_contrast"
YELLOW_STR = "#ffff00"
YELLOW_GREY_STR = "#9d9d9d"


class AutoContrastGreyReviewTest(unittest.TestCase):
    """The "Auto contrast" grey, with no Qt."""

    @covers("LLFR-01423", "HLFR-00167")
    def test_owner_examples_exactly(self) -> None:
        """The five examples of the owner give their greys exactly, and
        the default blue and the red of the palette give white.

        Inputs: none.
        Outputs: none.
        """
        for color_str, grey_str in (("#ff8000", "#ffffff"),
                                    (YELLOW_STR, YELLOW_GREY_STR),
                                    ("#00ff00", "#8a8a8a"),
                                    ("#00bfff", "#6b6b6b"),
                                    ("#ff0000", "#ffffff"),
                                    (PALETTE_COLOR_TUPLE[0], "#ffffff"),
                                    (PALETTE_COLOR_TUPLE[2], "#ffffff")):
            with self.subTest(color=color_str):
                self.assertEqual(theme.auto_contrast_grey_str(color_str),
                                 grey_str)

    @covers("LLFR-01423", "HLFR-00167")
    def test_never_black_for_a_light_color(self) -> None:
        """No color whose luminance is above that of mid grey gets a
        black box, white text included, and every grey reaches 2.5:1.

        Inputs: none.
        Outputs: none.
        """
        for value_i in range(0, 256, 17):
            for color_str in (f"#{value_i:02x}{value_i:02x}{value_i:02x}",
                              f"#ff{value_i:02x}00", f"#00{value_i:02x}ff",
                              f"#{value_i:02x}ffff"):
                grey_str = theme.auto_contrast_grey_str(color_str)
                with self.subTest(color=color_str):
                    self.assertGreaterEqual(
                        theme.contrast_ratio_f(color_str, grey_str), 2.5)
                    if theme.relative_luminance_f(color_str) > 0.2:
                        self.assertNotEqual(grey_str, "#000000")
        self.assertNotEqual(theme.auto_contrast_grey_str("#ffffff"),
                            "#000000")


@requires_qt
class TextBackgroundReviewViewTest(LabelWidgetTestCase):
    """The choice on one shown plot widget and in its exported image."""

    def setUp(self) -> None:
        """Create the widget and put back the theme's choice afterwards.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.addCleanup(theme.set_text_background, theme.text_background_str)
        theme.set_text_background(AUTO_CONTRAST_STR)

    def apply(self, choice_str: str) -> None:
        """Set the choice as MainWindow does and draw the widget again.

        Inputs:
            choice_str: "transparent" or "auto_contrast".
        Outputs: none.
        """
        theme.set_text_background(choice_str)
        self.plot_widget.refresh_text_background()
        self.draw()

    def grey_pixel_count(self) -> int:
        """Count the pixels of the exported image in the yellow's grey.

        Inputs: none.
        Outputs: the number of pixels within 2 of #9d9d9d in each of
            red, green and blue.
        """
        from view import plot_export
        figure = self.plot_widget.figure
        image = plot_export.render_figure_image(figure, figure.dpi)
        grey_i = int(YELLOW_GREY_STR[1:3], 16)
        count_i = 0
        for y_i in range(image.height()):
            for x_i in range(image.width()):
                color = image.pixelColor(x_i, y_i)
                if (abs(color.red() - grey_i) <= 2
                        and abs(color.green() - grey_i) <= 2
                        and abs(color.blue() - grey_i) <= 2):
                    count_i += 1
        return count_i

    @covers("LLFR-01430", "LLFR-01422", "LLFR-01423", "HLFR-00167",
            "HLFR-00038", "HLFR-00039")
    def test_exported_image_follows_the_choice(self) -> None:
        """The image the exports draw (PDF, Word, PNG and Copy all use
        render_figure_image) has the grey box of a yellow area label and
        flag with "Auto contrast", and no such box with "Transparent".

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_areas([(1, "Warm-up area", 6.0, 8.0,
                                     YELLOW_STR)])
        self.plot_widget.set_markers([(9, "Start flag", 3.0, YELLOW_STR)])
        self.draw()
        auto_count_i = self.grey_pixel_count()
        self.apply(TRANSPARENT_STR)
        transparent_count_i = self.grey_pixel_count()
        self.assertGreater(auto_count_i, transparent_count_i + 100)
        self.apply(AUTO_CONTRAST_STR)
        self.assertGreater(self.grey_pixel_count(),
                           transparent_count_i + 100)

    @covers("LLFR-01421", "LLFR-00042", "HLFR-00167", "HLFR-00024")
    def test_hover_data_tip_stays_white(self) -> None:
        """With "Transparent", the hover data tip keeps its white,
        bordered box, also on a plot created after the choice.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_hex
        from view.plot_widget import PlotWidget
        self.apply(TRANSPARENT_STR)
        for widget in (self.plot_widget, PlotWidget(4)):
            with self.subTest(widget=widget):
                patch = widget.hover_annotation.get_bbox_patch()
                self.assertEqual(to_hex(patch.get_facecolor()), "#ffffff")
                self.assertGreater(patch.get_linewidth(), 0.0)

    @covers("LLFR-01418", "LLFR-01419", "LLFR-01421", "LLFR-01422",
            "HLFR-00167", "HLFR-00158")
    def test_circle_and_rectangle(self) -> None:
        """The menu of a circle and of a rectangle has "Text background"
        right below "Color", with the current choice checked, and its
        label follows the choice.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6 import sip
        for kind_str in ("circle", "rectangle"):
            with self.subTest(kind=kind_str):
                self.apply(AUTO_CONTRAST_STR)
                self.plot_widget.set_shapes([
                    (kind_str, 2.0, 1.5, 6.0, 2.5, YELLOW_STR, "Zone", 1,
                     "continuous")])
                self.draw()
                menu = self.build_menu(self.data_display(4.0, 1.5))
                text_list = [action.text() for action in menu.actions()]
                index_i = text_list.index("Text background")
                self.assertEqual(text_list[index_i - 1], "Color")
                entry_list = [
                    (entry.text(), entry.isChecked())
                    for entry in menu.actions()[index_i].menu().actions()]
                sip.delete(menu)
                self.assertEqual(entry_list, [("Transparent", False),
                                              ("Auto contrast", True)])
                label = self.plot_widget.shape_label_list[0]
                from matplotlib.colors import to_hex
                self.assertEqual(
                    to_hex(label.get_bbox_patch().get_facecolor()),
                    YELLOW_GREY_STR)
                self.apply(TRANSPARENT_STR)
                label = self.plot_widget.shape_label_list[0]
                self.assertEqual(
                    label.get_bbox_patch().get_facecolor()[3], 0.0)

    @covers("LLFR-01422", "LLFR-01424", "LLFR-00151", "HLFR-00167",
            "HLFR-00025", "HLFR-00073")
    def test_note_and_tip_boxes_and_tip_leader(self) -> None:
        """A text note with yellow text and a pinned data tip: "Auto
        contrast" gives the grey fill (white for the dark tip text) with
        the border; "Transparent" no fill and no border, while the tip
        keeps its dashed leader line and its dot.

        Inputs: none.
        Outputs: none.
        """
        widget = self.plot_widget
        widget.set_text_notes([("Yellow note", 4.5, 2.0)])
        widget.set_pinned_tips([("Ramp", 9.0, 3.9, (0.0, -60.0),
                                 "Data tip 1")])
        self.draw()
        from matplotlib.colors import to_hex
        tip = widget.pinned_tip_annotation(0)
        self.assertEqual(to_hex(tip.get_bbox_patch().get_facecolor()),
                         theme.auto_contrast_grey_str(
                             theme.TIP_TEXT_COLOR_STR))
        self.assertGreater(tip.get_bbox_patch().get_linewidth(), 0.0)
        self.apply(TRANSPARENT_STR)
        for annotation in (widget.text_note_annotation(0),
                           widget.pinned_tip_annotation(0)):
            patch = annotation.get_bbox_patch()
            with self.subTest(annotation=annotation.get_text()):
                self.assertEqual(patch.get_facecolor()[3], 0.0)
                self.assertTrue(patch.get_linewidth() == 0.0
                                or patch.get_edgecolor()[3] == 0.0)
        tip = widget.pinned_tip_annotation(0)
        self.assertIsNotNone(tip.arrow_patch)
        self.assertGreater(tip.arrow_patch.get_linewidth(), 0.0)
        self.assertEqual(len(widget.pinned_marker_list), 1)
        self.assertTrue(widget.pinned_marker_list[0].get_visible())


if __name__ == "__main__":
    unittest.main()
