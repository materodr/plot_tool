"""Reviewer's tests of issue #260 for the model and the Qt-free helpers.

Covers the one table of type names against the table of LLFR-01255 in
the requirements file, the menu titles of a plot and of a vertical area
(LLFR-00426, LLFR-01390), the 40-character limit of a label (LLFR-00850),
the place of a plot in its tab (LLFR-01390), the Tangent at the odd
multiples of 90 degrees (LLFR-01306), the line widths and styles of the
plot objects (LLFR-01373, LLFR-01377, LLFR-01378, LLFR-01384) and that
a layout file with the old key "areas" rebuilds no vertical area
(LLFR-00225 item 11, owner's answer 7 of #260).
"""

import os
import re
import unittest

import numpy as np

from tests.model.test_layout_file import (
    LayoutRebuildTestCase, curve, minimal_layout, one_plot_tab)
from tests.support import REPOSITORY_ROOT_STR, covers

from model import object_names
from model.synthetic_operations import tangent_degrees
from model.workspace import (
    DEFAULT_ARROW_STYLE_STR, DEFAULT_CURVE_STYLE_STR,
    DEFAULT_DELTA_STYLE_STR, DEFAULT_FLAG_STYLE_STR,
    DEFAULT_SHAPE_STYLE_STR, DEFAULT_TEXT_NOTE_STYLE_STR,
    matrix_slot_tuple)
from view import line_looks

LLFR_FILE_STR = os.path.join(REPOSITORY_ROOT_STR, "docs", "requirements",
                             "low_level_functional_requirements.md")


def llfr_type_name_list() -> list:
    """Return the type names of the table of LLFR-01255.

    Inputs: none.
    Outputs: the second column of the table, in its order.
    """
    with open(LLFR_FILE_STR, encoding="utf-8") as llfr_file:
        text_str = llfr_file.read()
    section_str = text_str.split("### LLFR-01255 ", 1)[1].split("###", 1)[0]
    row_list = re.findall(r"^\| ([^|]+?) \| ([^|]+?) \|$", section_str,
                          re.MULTILINE)
    # The header row and the separator row are not type names.
    return [type_str for object_str, type_str in row_list
            if object_str != "Object" and not object_str.startswith("-")]


class TypeNameTableTest(unittest.TestCase):
    """The code's table of type names and the menu titles."""

    @covers("LLFR-01255", "HLFR-00096")
    def test_code_table_is_the_requirement_table(self) -> None:
        """TYPE_NAME_DICT holds exactly the type names of LLFR-01255.

        Inputs: none.
        Outputs: none.
        """
        requirement_list = llfr_type_name_list()
        self.assertEqual(len(requirement_list), 14)
        self.assertEqual(sorted(object_names.TYPE_NAME_DICT.values()),
                         sorted(requirement_list))

    @covers("LLFR-00426", "LLFR-01390", "LLFR-01255", "HLFR-00096")
    def test_titles_of_a_plot_and_a_vertical_area(self) -> None:
        """A plot's title is "Plot: <row>x<column>" and a vertical
        area's "Vert. Area: Area 1" (owner's correction of 23:44).

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(object_names.menu_title_text(
            object_names.PLOT_OBJECT_STR, "2x1"), "Plot: 2x1")
        self.assertEqual(object_names.menu_title_text(
            object_names.AREA_OBJECT_STR, "Area 1"), "Vert. Area: Area 1")
        self.assertEqual(object_names.menu_title_text(
            object_names.DATA_TIP_OBJECT_STR, "Data tip 3"),
            "Data Tip: Data tip 3")

    @covers("LLFR-00850", "LLFR-01257", "HLFR-00096")
    def test_forty_characters_are_not_shortened(self) -> None:
        """A label of exactly 40 characters is kept; one of 41 becomes
        40 characters with "…" in the middle.

        Inputs: none.
        Outputs: none.
        """
        forty_str = "a" * 20 + "b" * 20
        self.assertEqual(object_names.shortened_label(forty_str), forty_str)
        self.assertFalse(object_names.is_label_shortened(forty_str))
        long_str = forty_str + "c"
        short_str = object_names.shortened_label(long_str)
        self.assertEqual(len(short_str), 40)
        self.assertEqual(short_str.count("…"), 1)
        self.assertTrue(short_str.startswith("a" * 20))
        self.assertTrue(short_str.endswith("c"))
        self.assertTrue(object_names.is_label_shortened(long_str))


class PlotPlaceTest(unittest.TestCase):
    """The place of a plot in its tab's plot matrix."""

    @covers("LLFR-01390", "LLFR-01108", "HLFR-00096")
    def test_rows_from_the_top_and_columns_from_the_left(self) -> None:
        """In fill order, plot 2 of one column is 2x1, and plots 2, 3 and
        4 of a 2 x 2 matrix are 1x2, 2x1 and 2x2.

        Inputs: none.
        Outputs: none.
        """
        def place_str(plot_index_i: int, column_count_i: int) -> str:
            """Return the place of a plot as its menu title writes it.

            Inputs:
                plot_index_i: index of the plot in fill order, from 0.
                column_count_i: columns of the plot matrix.
            Outputs: "<row>x<column>".
            """
            row_i, column_i = matrix_slot_tuple(plot_index_i,
                                                column_count_i)
            return f"{row_i + 1}x{column_i + 1}"

        self.assertEqual(place_str(1, 1), "2x1")
        self.assertEqual([place_str(index_i, 2) for index_i in range(4)],
                         ["1x1", "1x2", "2x1", "2x2"])
        self.assertEqual(place_str(9, 10), "1x10")


class TangentGapTest(unittest.TestCase):
    """The NaN of the Tangent."""

    @covers("LLFR-01306", "LLFR-01305", "HLFR-00163")
    def test_only_odd_multiples_of_90_are_gaps(self) -> None:
        """-270, -90, 90, 270 and 450 degrees give NaN; 0, 180, -180,
        360 and 89.9 give numbers.

        Inputs: none.
        Outputs: none.
        """
        gap_array = tangent_degrees(np.array([-270.0, -90.0, 90.0, 270.0,
                                              450.0]))
        self.assertTrue(np.isnan(gap_array).all())
        number_array = tangent_degrees(np.array([0.0, 180.0, -180.0, 360.0,
                                                 89.9, 45.0]))
        self.assertFalse(np.isnan(number_array).any())
        np.testing.assert_allclose(number_array[:4], 0.0, atol=1e-12)
        self.assertAlmostEqual(float(number_array[5]), 1.0)


class LineLookTest(unittest.TestCase):
    """The widths and styles of the lines of the plot objects."""

    @covers("LLFR-01373", "LLFR-01384", "LLFR-00041", "HLFR-00159")
    def test_widths_grow_as_the_curve_widths(self) -> None:
        """Width N is width 1 times 1, 2, 3, 4.5 or 6, and a value that
        is not a preset width counts as width 1.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual([line_looks.line_width_f(1.5, width_i)
                          for width_i in range(1, 6)],
                         [1.5, 3.0, 4.5, 6.75, 9.0])
        for width_value in (0, 6, None, "2"):
            with self.subTest(width=width_value):
                self.assertEqual(line_looks.line_width_f(1.5, width_value),
                                 1.5)
        self.assertEqual(line_looks.width_or_one(True), 1)
        self.assertEqual(line_looks.width_or_one(4), 4)

    @covers("LLFR-01377", "HLFR-00160")
    def test_default_styles_are_the_former_ones(self) -> None:
        """Flags, delta markers and arrows are dashed; curves, text
        notes and shapes are continuous.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual((DEFAULT_FLAG_STYLE_STR, DEFAULT_DELTA_STYLE_STR,
                          DEFAULT_ARROW_STYLE_STR),
                         ("dashed", "dashed", "dashed"))
        self.assertEqual((DEFAULT_CURVE_STYLE_STR,
                          DEFAULT_TEXT_NOTE_STYLE_STR,
                          DEFAULT_SHAPE_STYLE_STR),
                         ("continuous", "continuous", "continuous"))

    @covers("LLFR-01378", "LLFR-01376", "HLFR-00160")
    def test_four_distinct_styles(self) -> None:
        """The four styles give four different matplotlib styles; a
        dashed line keeps its kind's own pattern; an unknown style is
        continuous.

        Inputs: none.
        Outputs: none.
        """
        style_list = [line_looks.matplotlib_line_style(style_str)
                      for style_str in ("continuous", "dashed", "dotted",
                                        "dash_dotted")]
        self.assertEqual(style_list[0], "-")
        self.assertEqual(len({repr(style) for style in style_list}), 4)
        self.assertEqual(style_list[1], (0, (6.0, 4.0)))
        own_pattern_tuple = (0, (3.0, 3.0))
        self.assertEqual(line_looks.matplotlib_line_style(
            "dashed", own_pattern_tuple), own_pattern_tuple)
        self.assertEqual(line_looks.matplotlib_line_style("wavy"), "-")
        self.assertEqual(list(line_looks.LINE_STYLE_TEXT_DICT.values()),
                         ["Continuous", "Dashed", "Dotted", "Dash-dotted"])


class OldAreasKeyTest(LayoutRebuildTestCase):
    """The vertical areas are read only under their new key."""

    @covers("LLFR-00225", "LLFR-00479", "LLFR-00472", "HLFR-00066",
            "HLFR-00050")
    def test_old_areas_key_rebuilds_nothing(self) -> None:
        """A file with "areas" instead of "vertical_areas" rebuilds no
        vertical area; the same entry under "vertical_areas" does.

        Inputs: none.
        Outputs: none.
        """
        area_entry_list = [{"name": "Run", "start": 1.0, "end": 2.0,
                            "color": "#ff8000"}]
        self.rebuild(minimal_layout([one_plot_tab([curve("Speed")])],
                                    areas=area_entry_list))
        self.assertEqual(self.workspace.area_list, [])
        self.rebuild(minimal_layout([one_plot_tab([curve("Speed")])],
                                    vertical_areas=area_entry_list))
        self.assertEqual([area.name_str
                          for area in self.workspace.area_list], ["Run"])


if __name__ == "__main__":
    unittest.main()
