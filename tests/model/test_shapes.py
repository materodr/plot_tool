"""Tests for the shapes, line looks, tip names and hidden labels of the
model (issue #260).

Covers the circles and rectangles of a plot (HLFR-00158: LLFR-01305,
LLFR-01318, LLFR-01320 to LLFR-01323, LLFR-01327, LLFR-01337 to
LLFR-01339, LLFR-01346 to LLFR-01352), the widths and line styles of
the plot objects (HLFR-00159, HLFR-00160: LLFR-01359 to LLFR-01368),
the names of the pinned data tips (LLFR-01252 to LLFR-01260), the
hidden labels (LLFR-01270 to LLFR-01277), their undo states (LLFR-00140)
and their layout file entries (LLFR-00225, LLFR-01221).
"""

import json
import unittest

import numpy as np

from tests.support import covers

from model.layout_file import (
    LayoutReport, build_layout_dict, layout_text, layout_with_save_options,
    rebuild_layout)
from model.workspace import (
    ARROW_LINE_KIND_STR, CIRCLE_KIND_STR, CURVE_LINE_KIND_STR,
    DELTA_LINE_KIND_STR, DELTA_X_KIND_STR, FLAG_LINE_KIND_STR,
    RECTANGLE_KIND_STR, SHAPE_LINE_KIND_STR, TEXT_NOTE_LINE_KIND_STR,
    Workspace, plot_state_tuple)


class ShapeModelTest(unittest.TestCase):
    """The shapes of one plot."""

    def setUp(self) -> None:
        """Create a workspace with one plot.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace()
        self.plot = self.workspace.add_plot(self.workspace.tab_list[0]
                                            .tab_id_i)

    @covers("LLFR-01305", "LLFR-01312", "LLFR-01318", "LLFR-01320",
            "LLFR-01322", "LLFR-01346", "LLFR-01361", "LLFR-01366",
            "HLFR-00158")
    def test_new_shapes_get_their_defaults(self) -> None:
        """A shape keeps its box and gets the defaults of a new shape.

        Inputs: none.
        Outputs: none.
        """
        circle = self.plot.add_shape(CIRCLE_KIND_STR, 1.0, 2.0, 3.0, 5.0,
                                     self.workspace.take_shape_name(
                                         CIRCLE_KIND_STR))
        rectangle = self.plot.add_shape(
            RECTANGLE_KIND_STR, 4.0, 1.0, 2.0, -1.0,
            self.workspace.take_shape_name(RECTANGLE_KIND_STR))
        self.assertEqual((circle.start_time_s, circle.start_value_f,
                          circle.end_time_s, circle.end_value_f),
                         (1.0, 2.0, 3.0, 5.0))
        self.assertEqual(circle.name_str, "Circle 1")
        self.assertEqual(rectangle.name_str, "Rectangle 1")
        self.assertEqual(circle.color_str, "#ff8000")
        self.assertEqual((circle.width_i, circle.line_style_str),
                         (1, "continuous"))
        self.assertEqual(len(self.plot.shape_list), 2)
        for _ in range(5):
            self.plot.add_shape(CIRCLE_KIND_STR, 0.0, 0.0, 1.0, 1.0)
        self.assertEqual(len(self.plot.shape_list), 7)

    @covers("LLFR-01308", "LLFR-01356", "HLFR-00158")
    def test_unusable_boxes_and_kinds_are_refused(self) -> None:
        """A box without a width or a height, a value that is not finite
        or an unknown kind gives no shape.

        Inputs: none.
        Outputs: none.
        """
        for corner_tuple in ((1.0, 1.0, 1.0, 2.0), (1.0, 1.0, 2.0, 1.0),
                             (np.nan, 0.0, 1.0, 1.0),
                             (0.0, 0.0, np.inf, 1.0)):
            with self.assertRaises(ValueError):
                self.plot.add_shape(CIRCLE_KIND_STR, *corner_tuple)
        with self.assertRaises(ValueError):
            self.plot.add_shape("triangle", 0.0, 0.0, 1.0, 1.0)
        self.assertEqual(self.plot.shape_list, [])

    @covers("LLFR-01347", "HLFR-00158")
    def test_shape_numbers_keep_growing(self) -> None:
        """The numbers of each kind grow, also after a delete or undo.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.workspace.take_shape_name(CIRCLE_KIND_STR),
                         "Circle 1")
        snapshot = self.workspace.snapshot()
        self.assertEqual(self.workspace.take_shape_name(CIRCLE_KIND_STR),
                         "Circle 2")
        self.workspace.restore(snapshot)
        self.assertEqual(self.workspace.take_shape_name(CIRCLE_KIND_STR),
                         "Circle 3")
        self.assertEqual(self.workspace.take_shape_name(RECTANGLE_KIND_STR),
                         "Rectangle 1")

    @covers("LLFR-01323", "LLFR-01327", "LLFR-01337", "LLFR-01338",
            "LLFR-01339", "LLFR-01348", "LLFR-01349", "LLFR-01350",
            "LLFR-01352", "HLFR-00158")
    def test_edit_rename_recolor_and_delete(self) -> None:
        """Box, name and color change one at a time; blank names and the
        same values change nothing.

        Inputs: none.
        Outputs: none.
        """
        shape = self.plot.add_shape(RECTANGLE_KIND_STR, 0.0, 0.0, 2.0, 1.0,
                                    "Box")
        self.assertTrue(self.plot.set_shape_box(0, 1.0, 1.0, 3.0, 2.0))
        self.assertFalse(self.plot.set_shape_box(0, 1.0, 1.0, 3.0, 2.0))
        self.assertFalse(self.plot.set_shape_box(5, 1.0, 1.0, 3.0, 2.0))
        with self.assertRaises(ValueError):
            self.plot.set_shape_box(0, 1.0, 1.0, 1.0, 2.0)
        self.assertEqual(shape.end_time_s, 3.0)
        self.assertTrue(self.plot.rename_shape(0, "  Zone  "))
        self.assertEqual(shape.name_str, "Zone")
        for blank_str in ("", "   "):
            self.assertFalse(self.plot.rename_shape(0, blank_str))
        self.assertFalse(self.plot.rename_shape(0, "Zone"))
        self.assertEqual((shape.start_time_s, shape.color_str,
                          shape.width_i, shape.line_style_str),
                         (1.0, "#ff8000", 1, "continuous"))
        self.assertTrue(self.plot.set_shape_color(0, "#00AA00"))
        self.assertEqual(shape.color_str, "#00aa00")
        self.assertFalse(self.plot.set_shape_color(0, "green"))
        self.assertFalse(self.plot.remove_shape(3))
        self.assertTrue(self.plot.remove_shape(0))
        self.assertEqual(self.plot.shape_list, [])

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00192", "LLFR-01321",
            "HLFR-00158")
    def test_shapes_are_part_of_the_undo_state(self) -> None:
        """Every change of a shape changes the plot's undo state, and a
        snapshot gives the shapes back; deleting the plot removes them.

        Inputs: none.
        Outputs: none.
        """
        self.plot.add_shape(CIRCLE_KIND_STR, 0.0, 0.0, 1.0, 1.0, "C")
        snapshot = self.workspace.snapshot()
        for change in (lambda: self.plot.set_shape_box(0, 0, 0, 2, 2),
                       lambda: self.plot.rename_shape(0, "D"),
                       lambda: self.plot.set_shape_color(0, "#000000"),
                       lambda: self.workspace.set_line_look(
                           self.plot.plot_id_i, SHAPE_LINE_KIND_STR, 0, 3),
                       lambda: self.workspace.set_line_look(
                           self.plot.plot_id_i, SHAPE_LINE_KIND_STR, 0,
                           None, "dotted"),
                       lambda: self.plot.remove_shape(0)):
            self.workspace.restore(snapshot)
            self.plot = self.workspace.find_plot(self.plot.plot_id_i)
            change_plot = self.plot
            self.assertTrue(self.workspace.is_unchanged_since(snapshot))
            change()
            self.assertFalse(self.workspace.is_unchanged_since(snapshot),
                             change_plot.shape_list)
        self.workspace.restore(snapshot)
        restored_plot = self.workspace.find_plot(self.plot.plot_id_i)
        self.assertEqual(restored_plot.shape_list[0].name_str, "C")
        self.assertEqual(plot_state_tuple(restored_plot)[7][0][0],
                         CIRCLE_KIND_STR)
        self.workspace.delete_plot(restored_plot.plot_id_i)
        self.assertIsNone(self.workspace.find_plot(restored_plot.plot_id_i))


class LineLookModelTest(unittest.TestCase):
    """The widths and line styles of the objects of a plot."""

    def setUp(self) -> None:
        """Create a plot with one object of each kind.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace()
        self.plot = self.workspace.add_plot(self.workspace.tab_list[0]
                                            .tab_id_i)
        self.plot.add_curve("s1")
        self.plot.add_curve("s2")
        self.flag = self.workspace.add_marker(1.0)
        self.delta = self.plot.add_delta_marker(
            DELTA_X_KIND_STR, ("s1", 1.0, 1.0), ("s2", 2.0, 2.0))
        self.plot.add_text_note("Note", 1.0, 1.0)
        self.plot.add_arrow(0.0, 0.0, 1.0, 1.0)
        self.plot.add_shape(CIRCLE_KIND_STR, 0.0, 0.0, 1.0, 1.0)

    def item_dict(self) -> dict:
        """Return the item of each kind for set_line_look.

        Inputs: none.
        Outputs: kind -> (item, the object).
        """
        return {
            FLAG_LINE_KIND_STR: (self.flag.marker_id_i, self.flag),
            CURVE_LINE_KIND_STR: ("s1", self.plot.curve_list[0]),
            DELTA_LINE_KIND_STR: (self.delta.delta_marker_id_i, self.delta),
            TEXT_NOTE_LINE_KIND_STR: (0, self.plot.text_note_list[0]),
            ARROW_LINE_KIND_STR: (0, self.plot.arrow_list[0]),
            SHAPE_LINE_KIND_STR: (0, self.plot.shape_list[0])}

    @covers("LLFR-01361", "LLFR-01366", "HLFR-00159", "HLFR-00160")
    def test_defaults_are_the_former_looks(self) -> None:
        """Width 1 everywhere; dashed flags, deltas and arrows, and
        continuous curves, text notes and shapes.

        Inputs: none.
        Outputs: none.
        """
        style_dict = {FLAG_LINE_KIND_STR: "dashed",
                      CURVE_LINE_KIND_STR: "continuous",
                      DELTA_LINE_KIND_STR: "dashed",
                      TEXT_NOTE_LINE_KIND_STR: "continuous",
                      ARROW_LINE_KIND_STR: "dashed",
                      SHAPE_LINE_KIND_STR: "continuous"}
        for kind_str, (_, line_object) in self.item_dict().items():
            with self.subTest(kind=kind_str):
                self.assertEqual(line_object.width_i, 1)
                self.assertEqual(line_object.line_style_str,
                                 style_dict[kind_str])

    @covers("LLFR-01360", "LLFR-01365", "LLFR-00140", "HLFR-00159",
            "HLFR-00160")
    def test_width_and_style_of_every_kind(self) -> None:
        """Each kind takes a preset width and a style, recorded in the
        undo state; other values and the same value change nothing.

        Inputs: none.
        Outputs: none.
        """
        plot_id_i = self.plot.plot_id_i
        for kind_str, (item, line_object) in self.item_dict().items():
            with self.subTest(kind=kind_str):
                snapshot = self.workspace.snapshot()
                self.assertTrue(self.workspace.set_line_look(
                    plot_id_i, kind_str, item, 4))
                self.assertEqual(line_object.width_i, 4)
                self.assertFalse(self.workspace.is_unchanged_since(snapshot))
                self.assertFalse(self.workspace.set_line_look(
                    plot_id_i, kind_str, item, 4))
                for bad_width in (0, 6, True, 2.0, "3"):
                    self.assertFalse(self.workspace.set_line_look(
                        plot_id_i, kind_str, item, bad_width))
                self.assertTrue(self.workspace.set_line_look(
                    plot_id_i, kind_str, item, None, "dash_dotted"))
                self.assertEqual(line_object.line_style_str, "dash_dotted")
                self.assertFalse(self.workspace.set_line_look(
                    plot_id_i, kind_str, item, None, "wavy"))
                self.assertEqual(line_object.line_style_str, "dash_dotted")
        self.assertFalse(self.workspace.set_line_look(
            plot_id_i, ARROW_LINE_KIND_STR, 9, 2))
        self.assertFalse(self.workspace.set_line_look(
            plot_id_i, "unknown", 0, 2))
        self.assertFalse(self.workspace.set_line_look(
            999, CURVE_LINE_KIND_STR, "s1", 2))


class TipNameModelTest(unittest.TestCase):
    """The names of the pinned data tips."""

    def setUp(self) -> None:
        """Create a plot with one curve.

        Inputs: none.
        Outputs: none.
        """
        self.workspace = Workspace()
        self.plot = self.workspace.add_plot(self.workspace.tab_list[0]
                                            .tab_id_i)
        self.plot.add_curve("s1")

    @covers("LLFR-01253", "LLFR-01254", "HLFR-00025")
    def test_default_names_keep_counting(self) -> None:
        """"Data tip N" grows for each new tip, also after an undo.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.workspace.take_tip_name(), "Data tip 1")
        snapshot = self.workspace.snapshot()
        self.assertEqual(self.workspace.take_tip_name(), "Data tip 2")
        self.workspace.restore(snapshot)
        self.assertEqual(self.workspace.take_tip_name(), "Data tip 3")
        tip = self.plot.add_pinned_tip("s1", 1.0, 1.0)
        self.assertEqual(tip.name_str, "Data tip 1")

    @covers("LLFR-01255", "LLFR-01256", "LLFR-01257", "LLFR-01259",
            "LLFR-00140", "HLFR-00025")
    def test_rename_changes_only_the_name(self) -> None:
        """A rename strips spaces; a blank name or an unknown tip changes
        nothing; the point and the offset stay.

        Inputs: none.
        Outputs: none.
        """
        tip = self.plot.add_pinned_tip("s1", 1.0, 2.0, "Data tip 1")
        self.plot.move_pinned_tip(tip, (10.0, 5.0))
        snapshot = self.workspace.snapshot()
        self.assertTrue(self.plot.rename_pinned_tip(0, " Peak "))
        self.assertFalse(self.workspace.is_unchanged_since(snapshot))
        self.assertEqual(tip.name_str, "Peak")
        for bad_tuple in ((0, ""), (0, "  "), (0, "Peak"), (1, "X"),
                          (True, "X")):
            self.assertFalse(self.plot.rename_pinned_tip(*bad_tuple))
        self.assertEqual((tip.signal_name_str, tip.time_s, tip.value_f,
                          tip.label_offset_tuple),
                         ("s1", 1.0, 2.0, (10.0, 5.0)))


class LabelsHiddenModelTest(unittest.TestCase):
    """Whether the labels are hidden."""

    @covers("LLFR-01273", "LLFR-00140", "LLFR-00138", "HLFR-00161")
    def test_hidden_labels_are_an_undo_state(self) -> None:
        """The labels are shown at start; hiding them changes the undo
        state, and a restore gives the state back.

        Inputs: none.
        Outputs: none.
        """
        workspace = Workspace()
        self.assertFalse(workspace.labels_hidden_b)
        snapshot = workspace.snapshot()
        workspace.labels_hidden_b = True
        self.assertFalse(workspace.is_unchanged_since(snapshot))
        hidden_snapshot = workspace.snapshot()
        workspace.restore(snapshot)
        self.assertFalse(workspace.labels_hidden_b)
        workspace.restore(hidden_snapshot)
        self.assertTrue(workspace.labels_hidden_b)


class LayoutLooksTest(unittest.TestCase):
    """The new entries of the layout file."""

    def setUp(self) -> None:
        """Create a workspace with every new value.

        Inputs: none.
        Outputs: none.
        """
        self.time_array = np.arange(0.0, 10.0, 0.5)
        self.signal_dict = {"file1_Time": self.time_array,
                            "file1_s1": self.time_array * 2.0}
        self.workspace = Workspace()
        self.plot = self.workspace.add_plot(self.workspace.tab_list[0]
                                            .tab_id_i)
        self.plot.add_curve("file1_s1")
        self.plot.curve_list[0].line_style_str = "dotted"
        tip = self.plot.add_pinned_tip("file1_s1", 1.0, 2.0, "Peak")
        self.assertEqual(tip.name_str, "Peak")
        delta = self.plot.add_delta_marker(
            DELTA_X_KIND_STR, ("file1_s1", 1.0, 2.0),
            ("file1_s1", 2.0, 4.0), name_str="Lap")
        delta.width_i, delta.line_style_str = 3, "continuous"
        flag = self.workspace.add_marker(2.0)
        flag.width_i, flag.line_style_str = 5, "dotted"
        shape = self.plot.add_shape(RECTANGLE_KIND_STR, 1.0, 1.0, 3.0, 5.0,
                                    "Zone")
        shape.color_str, shape.width_i = "#00aa00", 2
        shape.line_style_str = "dashed"
        self.workspace.labels_hidden_b = True

    def saved_dict(self) -> dict:
        """Return the layout file content of the workspace.

        Inputs: none.
        Outputs: the dict read back from the JSON text.
        """
        return json.loads(layout_text(build_layout_dict(
            self.workspace, self.workspace.tab_list[0].tab_id_i, (),
            True)))

    @covers("LLFR-00225", "LLFR-00227", "HLFR-00158", "HLFR-00159",
            "HLFR-00160", "HLFR-00161", "LLFR-01252")
    def test_file_holds_the_new_values(self) -> None:
        """Curve style, tip name, delta and flag looks, shapes and the
        labels setting are written with English keys.

        Inputs: none.
        Outputs: none.
        """
        layout_dict = self.saved_dict()
        plot_dict = layout_dict["tabs"][0]["plots"][0]
        self.assertEqual(plot_dict["curves"][0]["line_style"], "dotted")
        self.assertEqual(plot_dict["data_tips"][0]["name"], "Peak")
        self.assertEqual((plot_dict["delta_markers"][0]["width"],
                          plot_dict["delta_markers"][0]["line_style"]),
                         (3, "continuous"))
        self.assertEqual((layout_dict["flags"][0]["width"],
                          layout_dict["flags"][0]["line_style"]),
                         (5, "dotted"))
        self.assertEqual(plot_dict["shapes"], [
            {"kind": "rectangle", "name": "Zone",
             "corners": [1.0, 1.0, 3.0, 5.0], "color": "#00aa00",
             "width": 2, "line_style": "dashed"}])
        self.assertIs(layout_dict["labels_shown"], False)

    @covers("LLFR-01221", "HLFR-00156")
    def test_markers_off_leaves_out_the_shapes(self) -> None:
        """Without the markers, the file holds no shape.

        Inputs: none.
        Outputs: none.
        """
        layout_dict = layout_with_save_options(self.saved_dict(), False)
        self.assertEqual(layout_dict["tabs"][0]["plots"][0]["shapes"], [])

    @covers("LLFR-01355", "LLFR-01260", "LLFR-01277", "LLFR-01363",
            "LLFR-01368", "HLFR-00158", "HLFR-00050")
    def test_load_rebuilds_the_new_values(self) -> None:
        """A load rebuilds the shapes, tip names, looks and the labels
        setting as saved.

        Inputs: none.
        Outputs: none.
        """
        layout_dict = self.saved_dict()
        workspace = Workspace()
        result = rebuild_layout(workspace, layout_dict, self.signal_dict,
                                self.time_array)
        plot = workspace.tab_list[0].plot_list[0]
        self.assertEqual(plot.curve_list[0].line_style_str, "dotted")
        self.assertEqual(plot.pinned_tip_list[0].name_str, "Peak")
        self.assertEqual((plot.delta_marker_list[0].width_i,
                          plot.delta_marker_list[0].line_style_str),
                         (3, "continuous"))
        self.assertEqual((workspace.marker_list[0].width_i,
                          workspace.marker_list[0].line_style_str),
                         (5, "dotted"))
        shape = plot.shape_list[0]
        self.assertEqual((shape.kind_str, shape.name_str, shape.color_str,
                          shape.width_i, shape.line_style_str,
                          shape.end_value_f),
                         ("rectangle", "Zone", "#00aa00", 2, "dashed", 5.0))
        self.assertIs(result.labels_hidden_b, True)

    @covers("LLFR-01356", "LLFR-01357", "LLFR-01358", "LLFR-01363",
            "LLFR-01368", "LLFR-01260", "LLFR-01277", "HLFR-00052")
    def test_unusable_values_are_replaced_or_reported(self) -> None:
        """Unknown kinds and boxes are left out and reported; unusable
        names, widths and styles get the defaults.

        Inputs: none.
        Outputs: none.
        """
        layout_dict = self.saved_dict()
        plot_dict = layout_dict["tabs"][0]["plots"][0]
        plot_dict["shapes"] = [
            {"kind": "star", "name": "S", "corners": [0, 0, 1, 1]},
            {"kind": "circle", "name": "Flat", "corners": [0, 1, 2, 1]},
            {"kind": "circle", "corners": [0, 0, "a", 1]},
            {"kind": "circle", "name": "  ", "corners": [0, 0, 2, 2],
             "color": "red", "width": 9, "line_style": "wavy"}]
        plot_dict["curves"][0]["line_style"] = 3
        plot_dict["data_tips"][0]["name"] = ""
        plot_dict["delta_markers"][0].pop("width")
        layout_dict["flags"][0]["line_style"] = "none"
        layout_dict.pop("labels_shown")
        workspace = Workspace()
        result = rebuild_layout(workspace, layout_dict, self.signal_dict,
                                self.time_array)
        plot = workspace.tab_list[0].plot_list[0]
        self.assertEqual(len(plot.shape_list), 1)
        shape = plot.shape_list[0]
        self.assertEqual((shape.name_str, shape.color_str, shape.width_i,
                          shape.line_style_str),
                         ("Circle 1", "#ff8000", 1, "continuous"))
        self.assertEqual(plot.curve_list[0].line_style_str, "continuous")
        self.assertEqual(plot.pinned_tip_list[0].name_str, "Data tip 1")
        self.assertEqual(plot.delta_marker_list[0].width_i, 1)
        self.assertEqual(workspace.marker_list[0].line_style_str, "dashed")
        self.assertIsNone(result.labels_hidden_b)
        report_text_str = result.report.text()
        for name_str in ('"star"', '"Flat"'):
            self.assertIn(name_str, report_text_str)
        self.assertEqual(report_text_str.count("Shape "), 3)
        self.assertIsInstance(result.report, LayoutReport)


if __name__ == "__main__":
    unittest.main()
