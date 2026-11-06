"""Tests for the shape, line look, tip name and hidden label handlers of
the plot controller (issue #260).

The fake view and the setup of tests.controller.test_plot_controller
are reused. Covers drawing, moving, resizing, recoloring, renaming and
deleting a shape (LLFR-01316, LLFR-01334, LLFR-01338, LLFR-01348 to
LLFR-01350, LLFR-01357 to LLFR-01363), the "Width" and "Line style"
options (LLFR-01371, LLFR-01376), the rename of a data tip (LLFR-01264 to
LLFR-01270), the Hide labels button (LLFR-01281 to LLFR-01285), and the
undo and redo of each of them (LLFR-00140, LLFR-00138, LLFR-00192).
"""

import unittest

from tests.support import covers

from controller.plot_tools import CIRCLE_TOOL_STR
from tests.controller.test_arrows_controller import ArrowControllerTestCase


class ShapeControllerTestCase(ArrowControllerTestCase):
    """Shared setup: one plot with s1, Circle tool active."""

    def setUp(self) -> None:
        """Open the file, plot s1 and activate the Circle tool.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.view.handler_dict["plot_tool"](CIRCLE_TOOL_STR)

    def drawn_shapes(self) -> list:
        """Return the shapes last drawn in the plot of the setup.

        Inputs: none.
        Outputs: the list of shape tuples.
        """
        return list(self.view.shape_drawn_dict.get(self.plot_id_i, []))

    def plot(self):
        """Return the model plot of the setup.

        Inputs: none.
        Outputs: the Plot.
        """
        return self.workspace.find_plot(self.plot_id_i)


class ShapeCreateTest(ShapeControllerTestCase):
    """Drawing and editing shapes."""

    @covers("LLFR-01316", "LLFR-01357", "LLFR-01358", "LLFR-00140",
            "LLFR-00138", "LLFR-00192", "HLFR-00158")
    def test_create_is_drawn_and_undoable(self) -> None:
        """A drawn shape is kept, named and drawn; undo and redo work and
        an undone drawing keeps its number used.

        Inputs: none.
        Outputs: none.
        """
        create = self.handler("shape_create_handler")
        create(self.plot_id_i, "circle", 1.0, 1.0, 3.0, 2.0)
        self.assertEqual(self.drawn_shapes(), [
            ("circle", 1.0, 1.0, 3.0, 2.0, "#ff8000", "Circle 1", 1,
             "continuous")])
        depth_i = self.undo_depth()
        self.undo()
        self.assertEqual(self.drawn_shapes(), [])
        self.redo()
        self.assertEqual(self.drawn_shapes()[0][6], "Circle 1")
        self.undo()
        create(self.plot_id_i, "rectangle", 1.0, 1.0, 3.0, 2.0)
        create(self.plot_id_i, "circle", 1.0, 1.0, 3.0, 2.0)
        self.assertEqual([shape_tuple[6] for shape_tuple
                          in self.drawn_shapes()],
                         ["Rectangle 1", "Circle 2"])
        self.assertEqual(self.undo_depth(), depth_i + 1)

    @covers("LLFR-01319", "LLFR-01320", "HLFR-00158")
    def test_bad_requests_create_nothing(self) -> None:
        """An unknown plot or kind, or a flat box, creates nothing and
        uses up no number.

        Inputs: none.
        Outputs: none.
        """
        create = self.handler("shape_create_handler")
        depth_i = self.undo_depth()
        create(999, "circle", 1.0, 1.0, 3.0, 2.0)
        create(self.plot_id_i, "star", 1.0, 1.0, 3.0, 2.0)
        create(self.plot_id_i, "circle", 1.0, 1.0, 1.0, 2.0)
        self.assertEqual(self.plot().shape_list, [])
        self.assertEqual(self.undo_depth(), depth_i)
        create(self.plot_id_i, "circle", 1.0, 1.0, 3.0, 2.0)
        self.assertEqual(self.drawn_shapes()[0][6], "Circle 1")

    @covers("LLFR-01334", "LLFR-01338", "LLFR-01348", "LLFR-01349",
            "LLFR-01350", "LLFR-01359", "LLFR-01360", "LLFR-01361",
            "LLFR-01362", "LLFR-01363", "LLFR-00140", "HLFR-00158")
    def test_edits_are_undoable(self) -> None:
        """Move, color, rename and delete each give one undo step; the
        same box, a cancelled dialog and a blank name give none.

        Inputs: none.
        Outputs: none.
        """
        self.handler("shape_create_handler")(
            self.plot_id_i, "rectangle", 1.0, 1.0, 3.0, 2.0)
        depth_i = self.undo_depth()
        change = self.handler("shape_change_handler")
        change(self.plot_id_i, 0, 1.0, 1.0, 3.0, 2.0)
        change(self.plot_id_i, 7, 2.0, 1.0, 3.0, 2.0)
        self.assertEqual(self.undo_depth(), depth_i)
        change(self.plot_id_i, 0, 2.0, 1.0, 4.0, 3.0)
        self.assertEqual(self.drawn_shapes()[0][1:5], (2.0, 1.0, 4.0, 3.0))
        self.assertEqual(self.undo_depth(), depth_i + 1)
        self.view.color_answer_list = ["#00aa00"]
        self.handler("shape_color_handler")(self.plot_id_i, 0)
        self.assertEqual(self.drawn_shapes()[0][5], "#00aa00")
        self.view.shape_name_answer_list = ["  "]
        self.handler("shape_rename_handler")(self.plot_id_i, 0)
        self.handler("shape_rename_handler")(self.plot_id_i, 0)
        self.assertEqual(self.view.shape_name_question_list,
                         ["Rectangle 1", "Rectangle 1"])
        self.assertEqual(self.undo_depth(), depth_i + 2)
        self.view.shape_name_answer_list = [" Zone "]
        self.handler("shape_rename_handler")(self.plot_id_i, 0)
        self.assertEqual(self.drawn_shapes()[0][6], "Zone")
        self.assertEqual(self.drawn_shapes()[0][1:6],
                         (2.0, 1.0, 4.0, 3.0, "#00aa00"))
        self.handler("shape_delete_handler")(self.plot_id_i, 0)
        self.assertEqual(self.drawn_shapes(), [])
        self.assertEqual(self.undo_depth(), depth_i + 4)
        self.undo()
        self.assertEqual(self.drawn_shapes()[0][6], "Zone")


class LineLookControllerTest(ShapeControllerTestCase):
    """The "Width" and "Line style" options."""

    @covers("LLFR-01371", "LLFR-01376", "LLFR-00140", "LLFR-00138",
            "HLFR-00159", "HLFR-00160")
    def test_each_kind_is_drawn_again(self) -> None:
        """A width or style of a flag, curve, delta marker, text note,
        arrow and shape is stored, drawn and undoable.

        Inputs: none.
        Outputs: none.
        """
        self.handler("shape_create_handler")(
            self.plot_id_i, "circle", 1.0, 1.0, 3.0, 2.0)
        self.handler("arrow_create_handler")(self.plot_id_i, 1.0, 1.0, 2.0,
                                             2.0)
        self.handler("text_note_create_handler")(self.plot_id_i, "Note",
                                                 1.0, 1.0)
        marker_id_i = self.workspace.add_marker(2.0).marker_id_i
        self.controller.show_markers()
        width = self.handler("object_width_handler")
        style = self.handler("object_line_style_handler")
        depth_i = self.undo_depth()
        width(self.plot_id_i, "shape", 0, 3)
        self.assertEqual(self.drawn_shapes()[0][7], 3)
        style(self.plot_id_i, "arrow", 0, "dotted")
        self.assertEqual(self.view.arrow_drawn_dict[self.plot_id_i][0][7],
                         "dotted")
        width(self.plot_id_i, "text_note", 0, 5)
        self.assertEqual(
            self.view.text_note_drawn_dict[self.plot_id_i][0][6], 5)
        style(self.plot_id_i, "flag", marker_id_i, "continuous")
        self.assertEqual(
            self.view.marker_drawn_dict[self.plot_id_i][0][5], "continuous")
        style(self.plot_id_i, "curve", "s1", "dash_dotted")
        curve_tuple = self.view.drawn_dict[self.plot_id_i][0][0]
        self.assertEqual(curve_tuple[5], "dash_dotted")
        self.assertEqual(self.undo_depth(), depth_i + 5)
        width(self.plot_id_i, "shape", 0, 3)
        width(self.plot_id_i, "shape", 0, 7)
        style(self.plot_id_i, "curve", "s1", "wavy")
        style(self.plot_id_i, "curve", "nope", "dotted")
        self.assertEqual(self.undo_depth(), depth_i + 5)
        self.undo()
        curve_tuple = self.view.drawn_dict[self.plot_id_i][0][0]
        self.assertEqual(curve_tuple[5], "continuous")


class TipRenameControllerTest(ShapeControllerTestCase):
    """The names of the pinned data tips."""

    @covers("LLFR-01264", "LLFR-01266", "LLFR-01267", "LLFR-01268",
            "LLFR-01269", "LLFR-01270", "LLFR-00140", "HLFR-00025")
    def test_pinned_tips_are_named_and_renamed(self) -> None:
        """New tips get "Data tip N"; a rename asks from the name, a
        blank one changes nothing and a real one is undoable.

        Inputs: none.
        Outputs: none.
        """
        pin = self.handler("tip_pin_handler")
        pin(self.plot_id_i, "s1", 2.0, 2.0)
        pin(self.plot_id_i, "s1", 4.0, 4.0)
        tip_list = self.view.drawn_dict[self.plot_id_i][1]
        self.assertEqual([tip[4] for tip in tip_list],
                         ["Data tip 1", "Data tip 2"])
        depth_i = self.undo_depth()
        rename = self.handler("pinned_tip_rename_handler")
        rename(self.plot_id_i, 1)
        self.view.tip_name_answer_list = ["   "]
        rename(self.plot_id_i, 1)
        rename(self.plot_id_i, 5)
        self.assertEqual(self.view.tip_name_question_list,
                         ["Data tip 2", "Data tip 2"])
        self.assertEqual(self.undo_depth(), depth_i)
        self.view.tip_name_answer_list = ["Peak"]
        rename(self.plot_id_i, 1)
        tip_list = self.view.drawn_dict[self.plot_id_i][1]
        self.assertEqual(tip_list[1], ("s1", 4.0, 4.0, (), "Peak"))
        self.assertEqual(self.undo_depth(), depth_i + 1)
        self.undo()
        self.assertEqual(self.view.drawn_dict[self.plot_id_i][1][1][4],
                         "Data tip 2")


class LabelsControllerTest(ShapeControllerTestCase):
    """The Hide labels button."""

    @covers("LLFR-01281", "LLFR-01282", "LLFR-01283", "LLFR-01284",
            "LLFR-00140", "LLFR-00138", "LLFR-00192", "HLFR-00161")
    def test_hide_and_show_are_undoable(self) -> None:
        """The labels are shown at start; each click is one undoable
        action, and undo and redo give the view the state back.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(self.view.labels_hidden_b)
        self.assertIsNotNone(self.view.labels_handler)
        depth_i = self.undo_depth()
        self.view.labels_handler(True)
        self.assertTrue(self.view.labels_hidden_b)
        self.assertTrue(self.workspace.labels_hidden_b)
        self.view.labels_handler(True)
        self.assertEqual(self.undo_depth(), depth_i + 1)
        self.view.labels_handler(False)
        self.assertFalse(self.view.labels_hidden_b)
        self.undo()
        self.assertTrue(self.view.labels_hidden_b)
        self.undo()
        self.assertFalse(self.view.labels_hidden_b)
        self.redo()
        self.assertTrue(self.view.labels_hidden_b)


if __name__ == "__main__":
    unittest.main()
