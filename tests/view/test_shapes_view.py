"""Tests for the shapes, line looks, tip names, hidden labels and menu
titles in the view (issue #260).

Covers, on one plot widget, drawing a circle or a rectangle with its
preview (LLFR-01314 to LLFR-01320, LLFR-01326 to LLFR-01328), the look
and layer of a shape (LLFR-01321 to LLFR-01325), moving and resizing it
(LLFR-01334 to LLFR-01346), its menu (LLFR-01347, LLFR-01351), its label
(LLFR-01353, LLFR-01364), the shapes in the exported image (LLFR-01365,
LLFR-01327), the "Width" and "Line style" options (LLFR-01370,
LLFR-01371, LLFR-01373, LLFR-01375, LLFR-01376, LLFR-01378), the data tip
name line (LLFR-01263) and the hidden labels (LLFR-01281, LLFR-01285,
LLFR-01286, LLFR-01287); through MainWindow and the real controllers,
the Circle and Rectangle buttons and the O and B keys (LLFR-01272 to
LLFR-01279), the Hide labels button (LLFR-01280 to LLFR-01284) and the
titles of the tab, signal and file menus with "Create signal"
(LLFR-01257 to LLFR-01262, LLFR-01289). No modal dialog or menu is ever
opened: ``execute_menu`` is replaced.
"""

import unittest

from tests.support import covers, requires_qt
from tests.view.menu_texts import SHAPE_MENU_TEXT_LIST, menu_option_texts
from tests.view.test_arrows_view import (
    MAGENTA_STR, ArrowWidgetTestCase, all_menu_actions)
from tests.view.test_plot_tools import recorder
from tests.view.test_xyz_keys import XyzKeyWindowTestCase

from controller.plot_tools import (
    CIRCLE_TOOL_STR, NO_TOOL_STR, RECTANGLE_TOOL_STR, ZOOM_TOOL_STR)

# A box in an empty part of the test plot, between the sine (-1 to 1)
# and the ramp (3 to 4): (first x, first y, second x, second y).
EMPTY_BOX_TUPLE = (2.0, 1.5, 6.0, 2.5)
# Allowed error, in data values, of a position rounded to whole pixels.
VALUE_TOLERANCE_F = 0.05


def shape_tuple(kind_str: str, box_tuple: tuple = EMPTY_BOX_TUPLE,
                color_str: str = "#ff8000", name_str: str = "Shape 1",
                width_i: int = 1, style_str: str = "continuous") -> tuple:
    """Return a shape tuple as the plot controller gives it.

    Inputs:
        kind_str: "circle" or "rectangle".
        box_tuple: (first x, first y, second x, second y).
        color_str: its color.
        name_str: its name.
        width_i: its width, 1 to 5.
        style_str: its line style.
    Outputs: the tuple for PlotWidget.set_shapes.
    """
    return ((kind_str,) + tuple(box_tuple)
            + (color_str, name_str, width_i, style_str))


@requires_qt
class ShapeWidgetTestCase(ArrowWidgetTestCase):
    """The plot widget of ArrowWidgetTestCase, with the shape requests
    recorded."""

    def setUp(self) -> None:
        """Record the shape and line look requests.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        widget = self.plot_widget
        self.shape_create_list = recorder(widget.shape_create_requested)
        self.shape_change_list = recorder(widget.shape_change_requested)
        self.shape_delete_list = recorder(widget.shape_delete_requested)
        self.shape_rename_list = recorder(widget.shape_rename_requested)
        self.width_list = recorder(widget.object_width_requested)
        self.style_list = recorder(widget.object_line_style_requested)

    def set_one_shape(self, kind_str: str = "rectangle",
                      **look_dict) -> None:
        """Give the plot one shape in the empty box and draw it.

        Inputs:
            kind_str: "circle" or "rectangle".
            look_dict: other fields of shape_tuple.
        Outputs: none.
        """
        self.plot_widget.set_shapes([shape_tuple(kind_str, **look_dict)])
        self.draw()

    def assert_values_near(self, value_tuple: tuple,
                           expected_tuple: tuple) -> None:
        """Check that data values are close to the expected ones.

        Inputs:
            value_tuple: the values found.
            expected_tuple: the values expected.
        Outputs: none.
        """
        self.assertEqual(len(value_tuple), len(expected_tuple))
        for value_f, expected_f in zip(value_tuple, expected_tuple):
            self.assertAlmostEqual(value_f, expected_f,
                                   delta=VALUE_TOLERANCE_F)

    def box_of(self, emitted_tuple: tuple) -> tuple:
        """Return a box as (left, bottom, right, top) data values.

        Inputs:
            emitted_tuple: (first x, first y, second x, second y).
        Outputs: the sorted box.
        """
        return (min(emitted_tuple[0], emitted_tuple[2]),
                min(emitted_tuple[1], emitted_tuple[3]),
                max(emitted_tuple[0], emitted_tuple[2]),
                max(emitted_tuple[1], emitted_tuple[3]))

    def double_click(self, display_tuple: tuple) -> None:
        """Send a left double-click to the canvas at a display point.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton, MouseEvent
        self.left_press(display_tuple)
        self.left_release(display_tuple)
        event = MouseEvent("button_press_event", self.plot_widget.canvas,
                           float(display_tuple[0]), float(display_tuple[1]),
                           button=MouseButton.LEFT, dblclick=True)
        self.plot_widget.canvas.callbacks.process("button_press_event",
                                                  event)
        self.left_release(display_tuple)

    def label_center(self, label) -> tuple:
        """Return the center of a drawn Text, in display pixels.

        Inputs:
            label: a matplotlib Text.
        Outputs: (x, y).
        """
        extent = label.get_window_extent(
            self.plot_widget.canvas.get_renderer())
        return ((extent.x0 + extent.x1) / 2.0, (extent.y0 + extent.y1) / 2.0)


class ShapeDrawingTest(ShapeWidgetTestCase):
    """Drawing a new shape with the Circle or Rectangle tool."""

    @covers("LLFR-01314", "LLFR-01315", "LLFR-01316", "LLFR-01317",
            "LLFR-01328", "LLFR-01326", "HLFR-00158")
    def test_drag_shows_a_preview_and_release_creates(self) -> None:
        """Below 5 pixels nothing is shown; from 5 pixels on a preview of
        the tool's kind follows the pointer, with no label; the release
        removes it and asks for the box of the press and the release.

        Inputs: none.
        Outputs: none.
        """
        for tool_str, kind_str in ((CIRCLE_TOOL_STR, "circle"),
                                   (RECTANGLE_TOOL_STR, "rectangle")):
            with self.subTest(tool=tool_str):
                self.shape_create_list.clear()
                self.plot_widget.set_plot_tool(tool_str)
                press_tuple = self.display_of(2.0, 1.5)
                self.left_press(press_tuple)
                self.move_to((press_tuple[0] + 2.0, press_tuple[1] + 2.0))
                self.assertFalse(self.plot_widget.shape_preview_shown())
                self.move_to(self.display_of(4.0, 2.0))
                self.assertTrue(self.plot_widget.shape_preview_shown())
                release_tuple = self.display_of(6.0, 2.5)
                self.move_to(release_tuple)
                corner_tuple = (
                    self.plot_widget.shape_preview_display_tuple())
                self.assertEqual(len(corner_tuple), 2)
                self.assert_near(corner_tuple[1], release_tuple)
                self.left_release(release_tuple)
                self.assertFalse(self.plot_widget.shape_preview_shown())
                self.assertEqual(len(self.shape_create_list), 1)
                self.assertEqual(self.shape_create_list[0][0], kind_str)
                self.assert_values_near(
                    self.box_of(self.shape_create_list[0][1:]),
                    EMPTY_BOX_TUPLE)

    @covers("LLFR-01319", "LLFR-01320", "HLFR-00158")
    def test_small_box_creates_nothing(self) -> None:
        """A box less than 5 pixels high creates no shape.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(RECTANGLE_TOOL_STR)
        press_tuple = self.display_of(2.0, 1.5)
        self.drag(press_tuple, (press_tuple[0] + 60.0, press_tuple[1] + 2.0))
        self.assertEqual(self.shape_create_list, [])

    @covers("LLFR-01318", "HLFR-00158")
    def test_release_outside_ends_at_the_drawing_area(self) -> None:
        """A release right of the drawing area puts the corner on its
        right edge.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(RECTANGLE_TOOL_STR)
        right_f = self.plot_widget.axes.get_xlim()[1]
        box = self.plot_widget.axes.bbox
        press_tuple = self.display_of(6.0, 1.5)
        self.drag(press_tuple, (box.x1 + 80.0, press_tuple[1] + 40.0))
        self.assertEqual(len(self.shape_create_list), 1)
        self.assertAlmostEqual(
            self.box_of(self.shape_create_list[0][1:])[2], right_f,
            delta=VALUE_TOLERANCE_F)

    @covers("LLFR-01314", "LLFR-01345", "HLFR-00158")
    def test_no_shape_without_its_tool(self) -> None:
        """With no tool or the Zoom tool, a drag draws no shape.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (NO_TOOL_STR, ZOOM_TOOL_STR):
            self.plot_widget.set_plot_tool(tool_str)
            self.drag(self.display_of(2.0, 1.5), self.display_of(6.0, 2.5))
            self.plot_widget.cancel_drags()
        self.assertEqual(self.shape_create_list, [])


class ShapeLookTest(ShapeWidgetTestCase):
    """How a shape is drawn."""

    @covers("LLFR-01321", "LLFR-01322", "LLFR-01325", "LLFR-01329",
            "LLFR-01353", "LLFR-01373", "LLFR-01378", "HLFR-00158",
            "HLFR-00159", "HLFR-00160")
    def test_patch_kind_color_width_style_and_layer(self) -> None:
        """A circle is an ellipse in its box and a rectangle a rectangle,
        in its color, width and style, above the curves and below the
        arrows; the label holds the name.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.patches import Ellipse, Rectangle
        from matplotlib.colors import to_hex
        from view import shape_layer
        self.plot_widget.set_shapes([
            shape_tuple("circle", name_str="Circle 1", width_i=3,
                        style_str="dotted"),
            shape_tuple("rectangle", (7.0, -0.5, 9.0, 0.5), "#00aa00",
                        "Rectangle 1")])
        self.draw()
        self.assertEqual(self.plot_widget.shape_count(), 2)
        circle = self.plot_widget.shape_patch(0)
        rectangle = self.plot_widget.shape_patch(1)
        self.assertIsInstance(circle, Ellipse)
        self.assertIsInstance(rectangle, Rectangle)
        self.assertEqual(to_hex(rectangle.get_edgecolor()), "#00aa00")
        self.assertGreater(circle.get_linewidth(),
                           2.5 * rectangle.get_linewidth())
        self.assertNotEqual(circle.get_linestyle(),
                            rectangle.get_linestyle())
        curve_zorder_f = max(line.get_zorder()
                             for line in self.plot_widget.axes.lines)
        self.assertGreater(circle.get_zorder(), curve_zorder_f)
        self.assertEqual(circle.get_zorder(), shape_layer.SHAPE_ZORDER_F)
        self.assertEqual(self.plot_widget.shape_label(0).get_text(),
                         "Circle 1")
        self.assertEqual(self.plot_widget.shape_label(1).get_text(),
                         "Rectangle 1")
        # LLFR-01329: the box follows its values when the range changes.
        before_tuple = self.plot_widget.shape_display_tuple(1)
        self.plot_widget.zoom_to_range(5.0, 10.0)
        self.draw()
        self.assertNotEqual(self.plot_widget.shape_display_tuple(1),
                            before_tuple)

    @covers("LLFR-01365", "LLFR-01327", "HLFR-00158", "HLFR-00038",
            "HLFR-00039")
    def test_rendered_figure_shows_shapes_but_no_preview(self) -> None:
        """The export image holds a magenta rectangle, but not the
        preview of a shape being drawn.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export

        def magenta_pixel_count(image) -> int:
            """Count the pixels close to magenta.

            Inputs:
                image: a QImage.
            Outputs: the count.
            """
            count_i = 0
            for y_i in range(0, image.height()):
                for x_i in range(0, image.width(), 2):
                    color = image.pixelColor(x_i, y_i)
                    if (color.red() >= 180 and color.green() <= 120
                            and color.blue() >= 180):
                        count_i += 1
            return count_i

        figure = self.plot_widget.figure
        empty_count_i = magenta_pixel_count(
            plot_export.render_figure_image(figure, figure.dpi))
        self.set_one_shape(color_str=MAGENTA_STR, width_i=3)
        shown_count_i = magenta_pixel_count(
            plot_export.render_figure_image(figure, figure.dpi))
        self.assertGreater(shown_count_i, empty_count_i + 50)
        self.plot_widget.set_plot_tool(RECTANGLE_TOOL_STR)
        self.left_press(self.display_of(1.0, -0.5))
        self.move_to(self.display_of(9.0, 3.0))
        self.assertTrue(self.plot_widget.shape_preview_shown())
        preview_count_i = magenta_pixel_count(
            plot_export.render_figure_image(figure, figure.dpi))
        self.assertLessEqual(abs(preview_count_i - shown_count_i), 5)
        self.plot_widget.cancel_drags()


class ShapeEditTest(ShapeWidgetTestCase):
    """Moving and resizing a shape."""

    @covers("LLFR-01324", "LLFR-01334", "LLFR-01335", "LLFR-01344",
            "HLFR-00158", "HLFR-00085")
    def test_move_by_the_line_keeps_the_size(self) -> None:
        """With no tool, a drag from the bottom line moves the box by the
        drag and keeps its size; the inside is not the shape.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_shape()
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        self.assertEqual(self.plot_widget.shape_at(
            self.point_at(4.0, 2.0)), -1)
        self.assertEqual(self.plot_widget.shape_at(
            self.point_at(4.0, 1.5)), 0)
        self.left_press(self.display_of(4.0, 1.5))
        self.move_to(self.display_of(4.5, 1.7))
        self.assertTrue(self.plot_widget.shape_preview_shown())
        self.move_to(self.display_of(5.0, 1.75))
        self.left_release(self.display_of(5.0, 1.75))
        self.assertEqual(len(self.shape_change_list), 1)
        self.assertEqual(self.shape_change_list[0][0], 0)
        self.assert_values_near(self.box_of(self.shape_change_list[0][1:]),
                                (3.0, 1.75, 7.0, 2.75))

    @covers("LLFR-01337", "LLFR-01343", "HLFR-00158")
    def test_short_drag_changes_nothing(self) -> None:
        """A release less than 5 pixels from the press asks nothing.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_shape()
        self.plot_widget.set_plot_tool(RECTANGLE_TOOL_STR)
        press_tuple = self.display_of(4.0, 1.5)
        self.drag(press_tuple, (press_tuple[0] + 2.0, press_tuple[1]))
        self.assertEqual(self.shape_change_list, [])
        self.assertEqual(self.shape_create_list, [])

    @covers("LLFR-01338", "LLFR-01339", "LLFR-01340", "HLFR-00158")
    def test_resize_by_a_corner(self) -> None:
        """A drag from a corner moves that corner and keeps the opposite
        one.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_shape()
        self.plot_widget.set_plot_tool(RECTANGLE_TOOL_STR)
        self.drag(self.display_of(6.0, 2.5), self.display_of(8.0, 2.8))
        self.assertEqual(len(self.shape_change_list), 1)
        self.assert_values_near(self.box_of(self.shape_change_list[0][1:]),
                                (2.0, 1.5, 8.0, 2.8))

    @covers("LLFR-01345", "LLFR-01346", "HLFR-00158")
    def test_other_tools_leave_the_shape(self) -> None:
        """The Circle tool and the Zoom tool do not edit a rectangle.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_shape()
        for tool_str in (CIRCLE_TOOL_STR, ZOOM_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.drag(self.display_of(4.0, 1.5),
                          self.display_of(5.0, 1.8))
                self.plot_widget.cancel_drags()
        self.assertEqual(self.shape_change_list, [])


class ShapeMenuTest(ShapeWidgetTestCase):
    """The shape menu and the line options."""

    @covers("LLFR-01347", "LLFR-01350", "LLFR-01359", "LLFR-00426",
            "LLFR-01255", "HLFR-00158", "HLFR-00096")
    def test_menu_options_and_requests(self) -> None:
        """The menu has its title and options; Rename and Delete ask for
        the shape.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_shape(name_str="Zone")
        point_tuple = self.display_of(4.0, 1.5)
        self.assertEqual(self.choose_menu(point_tuple, ""),
                         SHAPE_MENU_TEXT_LIST)
        menu = self.plot_widget.build_context_menu(
            self.plot_widget.display_to_widget_point(*point_tuple))
        self.assertEqual(menu.actions()[0].text(), "Rectangle: Zone")
        self.choose_menu(point_tuple, "Rename")
        self.assertEqual(self.shape_rename_list, [(0,)])
        self.choose_menu(point_tuple, "Delete")
        self.assertEqual(self.shape_delete_list, [(0,)])

    @covers("LLFR-01370", "LLFR-01371", "LLFR-01375", "LLFR-01376",
            "LLFR-01372", "LLFR-01377", "HLFR-00159", "HLFR-00160")
    def test_width_and_line_style_options(self) -> None:
        """"Width" lists 1 to 5 and "Line style" the four styles, each
        with the current one checked; a choice asks for it.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_shape(width_i=2, style_str="dashed")
        menu = self.plot_widget.build_context_menu(self.point_at(4.0, 1.5))
        option_dict = {action.text(): action for action in menu.actions()}
        width_menu = option_dict["Width"].menu()
        style_menu = option_dict["Line style"].menu()
        self.assertEqual([action.text() for action in width_menu.actions()],
                         ["1", "2", "3", "4", "5"])
        self.assertEqual([action.isChecked()
                          for action in width_menu.actions()],
                         [False, True, False, False, False])
        self.assertEqual([action.text() for action in style_menu.actions()],
                         ["Continuous", "Dashed", "Dotted", "Dash-dotted"])
        self.assertTrue(style_menu.actions()[1].isChecked())
        point_tuple = self.display_of(4.0, 1.5)
        self.choose_menu(point_tuple, "4")
        self.choose_menu(point_tuple, "Dash-dotted")
        self.assertEqual(self.width_list, [("shape", 0, 4)])
        self.assertEqual(self.style_list, [("shape", 0, "dash_dotted")])

    @covers("LLFR-01351", "LLFR-01375", "HLFR-00158", "HLFR-00160")
    def test_shape_menu_over_a_curve_and_curve_line_style(self) -> None:
        """Over a curve, the line of a shape gets the shape menu; the
        curve menu alone has "Line style" too.

        Inputs: none.
        Outputs: none.
        """
        import numpy as np
        on_curve_tuple = self.display_of(5.0, float(np.sin(5.0)))
        curve_text_list = self.choose_menu(on_curve_tuple, "")
        self.assertIn("Line style", curve_text_list)
        self.choose_menu(on_curve_tuple, "Dotted")
        self.assertEqual(self.style_list, [("curve", "Sine", "dotted")])
        self.set_one_shape(box_tuple=(5.0, float(np.sin(5.0)), 7.0, 0.5))
        self.assertEqual(self.choose_menu(on_curve_tuple, ""),
                         SHAPE_MENU_TEXT_LIST)

    @covers("LLFR-01364", "HLFR-00158", "HLFR-00094")
    def test_double_click_on_the_label_renames(self) -> None:
        """A double-click on the name label asks to rename the shape.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_shape(name_str="Zone")
        self.double_click(self.label_center(self.plot_widget.shape_label(0)))
        self.assertEqual(self.shape_rename_list, [(0,)])


class LabelsAndTipNamesTest(ShapeWidgetTestCase):
    """The data tip name line and the hidden labels on a plot widget."""

    @covers("LLFR-01263", "LLFR-01281", "LLFR-01282", "LLFR-01285",
            "HLFR-00025", "HLFR-00161")
    def test_tip_name_line_and_hidden_names(self) -> None:
        """A pinned tip shows its name on its first line; hidden labels
        leave the values but drop the names of the tip, flag and shape.

        Inputs: none.
        Outputs: none.
        """
        import numpy as np
        self.plot_widget.set_pinned_tips([
            ("Sine", 2.0, float(np.sin(2.0)), (), "Peak")])
        self.plot_widget.set_markers([(1, "Start", 3.0, "#ff8000")])
        self.set_one_shape(name_str="Zone")
        tip_text_str = self.plot_widget.pinned_annotation_list[0].get_text()
        self.assertEqual(tip_text_str.splitlines()[0], "Peak")
        self.assertEqual(self.plot_widget.marker_label_text(1), "Start")
        self.plot_widget.set_labels_hidden(True)
        self.draw()
        hidden_text_str = (
            self.plot_widget.pinned_annotation_list[0].get_text())
        self.assertNotIn("Peak", hidden_text_str)
        self.assertEqual(hidden_text_str,
                         "\n".join(tip_text_str.splitlines()[1:]))
        self.assertEqual(self.plot_widget.marker_label_text(1), "")
        self.assertEqual(self.plot_widget.shape_label(0).get_text(), "")
        # LLFR-01285: an object drawn afterwards has no name either.
        self.plot_widget.set_shapes([shape_tuple("circle",
                                                 name_str="Later")])
        self.draw()
        self.assertEqual(self.plot_widget.shape_label(0).get_text(), "")
        self.plot_widget.set_labels_hidden(False)
        self.draw()
        self.assertEqual(self.plot_widget.shape_label(0).get_text(),
                         "Later")
        self.assertEqual(self.plot_widget.marker_label_text(1), "Start")

    @covers("LLFR-01287", "HLFR-00161", "HLFR-00094")
    def test_double_click_on_a_hidden_label_renames_nothing(self) -> None:
        """Where the hidden label of a shape would be, a double-click
        asks no rename.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_shape(name_str="Zone")
        center_tuple = self.label_center(self.plot_widget.shape_label(0))
        self.plot_widget.set_labels_hidden(True)
        self.draw()
        self.double_click(center_tuple)
        self.assertEqual(self.shape_rename_list, [])

    @covers("LLFR-01388", "LLFR-01389", "LLFR-01287", "HLFR-00094",
            "HLFR-00025")
    def test_double_click_on_a_data_tip_name(self) -> None:
        """A double-click on the name line of a pinned tip asks for its
        rename; on its value lines, or while the labels are hidden, it
        asks nothing.

        Inputs: none.
        Outputs: none.
        """
        import numpy as np
        widget = self.plot_widget
        rename_list = recorder(widget.pinned_tip_rename_requested)
        widget.set_pinned_tips([("Sine", 2.0, float(np.sin(2.0)), (),
                                 "Peak")])
        self.draw()
        annotation = widget.pinned_annotation_list[0]
        text_box = annotation.get_window_extent(
            widget.canvas.get_renderer())
        line_count_i = annotation.get_text().count("\n") + 1
        line_height_f = text_box.height / line_count_i
        center_x_f = (text_box.x0 + text_box.x1) / 2.0
        name_tuple = (center_x_f, text_box.y1 - line_height_f / 2.0)
        value_tuple = (center_x_f, text_box.y0 + line_height_f / 2.0)
        # LLFR-01389: the value lines rename nothing.
        self.double_click(value_tuple)
        self.application.processEvents()
        self.assertEqual(rename_list, [])
        # LLFR-01388: the name line acts as "Rename".
        self.double_click(name_tuple)
        self.application.processEvents()
        self.assertEqual(rename_list, [(0,)])
        # LLFR-01287: no name line while the labels are hidden.
        widget.set_labels_hidden(True)
        self.draw()
        self.double_click(name_tuple)
        self.application.processEvents()
        self.assertEqual(rename_list, [(0,)])

    @covers("LLFR-01391", "LLFR-01364", "HLFR-00094", "HLFR-00158")
    def test_double_click_on_a_shape_line_renames_nothing(self) -> None:
        """A double-click on the line of a shape, away from its label,
        asks no rename.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_shape(name_str="Zone")
        self.double_click(self.display_of(EMPTY_BOX_TUPLE[2], 2.0))
        self.application.processEvents()
        self.assertEqual(self.shape_rename_list, [])

    @covers("LLFR-01252", "LLFR-01385", "LLFR-01238", "LLFR-00886",
            "LLFR-01346", "LLFR-01287", "HLFR-00158", "HLFR-00161",
            "HLFR-00028")
    def test_flag_preview_over_a_shape_name(self) -> None:
        """With the Flag tool, the flag preview is shown over the line
        of a shape, hidden over the name in its label, and shown there
        again while the labels are hidden.

        Inputs: none.
        Outputs: none.
        """
        from controller.plot_tools import MARKER_TOOL_STR
        widget = self.plot_widget
        self.set_one_shape(name_str="Zone")
        center_tuple = self.label_center(widget.shape_label(0))
        # LLFR-01238: on the right side of the box, away from its label.
        line_tuple = self.display_of(EMPTY_BOX_TUPLE[2], 2.0)
        widget.set_plot_tool(MARKER_TOOL_STR)
        self.send("motion_notify_event", line_tuple)
        self.assertTrue(widget.marker_preview_shown())
        # LLFR-01252: none over the name, where a click changes nothing.
        self.send("motion_notify_event", center_tuple)
        self.assertFalse(widget.marker_preview_shown())
        # LLFR-00886, LLFR-01346: a click on the name places no flag.
        place_list = recorder(widget.marker_place_requested)
        self.left_press(center_tuple)
        self.left_release(center_tuple)
        self.application.processEvents()
        self.assertEqual(place_list, [])
        # LLFR-01385: a hidden name is not there.
        widget.set_labels_hidden(True)
        self.draw()
        self.send("motion_notify_event", line_tuple)
        self.send("motion_notify_event", center_tuple)
        self.assertTrue(widget.marker_preview_shown())
        # LLFR-01287: and a click there places the flag.
        self.left_press(center_tuple)
        self.left_release(center_tuple)
        self.application.processEvents()
        self.assertEqual(len(place_list), 1)


class ShapeEdgeTest(ShapeWidgetTestCase):
    """Shapes at the edge of the drawing area and under other items."""

    @covers("LLFR-01330", "HLFR-00158")
    def test_shape_is_cut_at_the_edge(self) -> None:
        """A shape partly outside the shown range is clipped to the
        drawing area.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_shape(box_tuple=(8.0, 1.5, 14.0, 2.5))
        patch = self.plot_widget.shape_patch(0)
        self.assertTrue(patch.get_clip_on())
        self.assertTrue(patch.get_clip_path() is not None
                        or patch.get_clip_box() is not None)

    @covers("LLFR-01336", "HLFR-00158")
    def test_move_released_outside_uses_the_nearest_point(self) -> None:
        """A move released right of the drawing area moves the shape as
        far as the right edge.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_shape()
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        right_f = self.plot_widget.axes.get_xlim()[1]
        press_tuple = self.display_of(4.0, 1.5)
        box = self.plot_widget.axes.bbox
        self.drag(press_tuple, (box.x1 + 120.0, press_tuple[1]))
        self.assertEqual(len(self.shape_change_list), 1)
        shift_f = right_f - 4.0
        self.assert_values_near(self.box_of(self.shape_change_list[0][1:]),
                                (2.0 + shift_f, 1.5, 6.0 + shift_f, 2.5))

    @covers("LLFR-01342", "HLFR-00158")
    def test_corner_released_outside_uses_the_nearest_point(self) -> None:
        """A corner released above the drawing area stops at its top.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_shape()
        self.plot_widget.set_plot_tool(RECTANGLE_TOOL_STR)
        top_f = self.plot_widget.axes.get_ylim()[1]
        corner_tuple = self.display_of(6.0, 2.5)
        box = self.plot_widget.axes.bbox
        self.drag(corner_tuple, (corner_tuple[0], box.y1 + 120.0))
        self.assertEqual(len(self.shape_change_list), 1)
        self.assert_values_near(self.box_of(self.shape_change_list[0][1:]),
                                (2.0, 1.5, 6.0, top_f))

    @covers("LLFR-01352", "HLFR-00158")
    def test_arrow_over_a_shape_gets_its_menu(self) -> None:
        """Where an arrow is drawn over the line of a shape, the
        right-click shows the arrow menu.

        Inputs: none.
        Outputs: none.
        """
        from tests.view.menu_texts import ARROW_MENU_TEXT_LIST
        self.set_one_shape()
        point_tuple = self.display_of(4.0, 1.5)
        self.assertEqual(self.choose_menu(point_tuple, ""),
                         SHAPE_MENU_TEXT_LIST)
        self.set_one_arrow((3.0, 1.5, 5.0, 1.5))
        self.assertEqual(self.choose_menu(point_tuple, ""),
                         ARROW_MENU_TEXT_LIST)

    @covers("LLFR-01356", "HLFR-00158")
    def test_label_follows_the_preview(self) -> None:
        """While a shape is moved, its label is drawn with the preview,
        moved with it.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_shape(name_str="Zone")
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        before_tuple = self.plot_widget.shape_label(0).get_position()
        self.left_press(self.display_of(4.0, 1.5))
        self.move_to(self.display_of(4.5, 1.6))
        self.move_to(self.display_of(5.0, 1.7))
        preview_label = self.plot_widget.shape_preview_label
        self.assertEqual(preview_label.get_text(), "Zone")
        self.assertGreater(preview_label.get_position()[0],
                           before_tuple[0] + 5.0)
        self.plot_widget.cancel_drags()

    @covers("LLFR-01286", "HLFR-00161", "HLFR-00038", "HLFR-00039")
    def test_hidden_labels_are_not_exported(self) -> None:
        """The export image of a magenta shape has fewer magenta pixels
        once its label is hidden, and the label stays empty.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export

        def magenta_pixel_count(image) -> int:
            """Count the pixels close to magenta.

            Inputs:
                image: a QImage.
            Outputs: the count.
            """
            count_i = 0
            for y_i in range(0, image.height()):
                for x_i in range(image.width()):
                    color = image.pixelColor(x_i, y_i)
                    if (color.red() >= 180 and color.green() <= 120
                            and color.blue() >= 180):
                        count_i += 1
            return count_i

        figure = self.plot_widget.figure
        self.set_one_shape(color_str=MAGENTA_STR, name_str="WWWWWWWW")
        shown_count_i = magenta_pixel_count(
            plot_export.render_figure_image(figure, figure.dpi))
        self.plot_widget.set_labels_hidden(True)
        self.draw()
        hidden_count_i = magenta_pixel_count(
            plot_export.render_figure_image(figure, figure.dpi))
        self.assertLess(hidden_count_i, shown_count_i - 20)
        self.assertEqual(self.plot_widget.shape_label(0).get_text(), "")


@requires_qt
class ShapeWindowTest(XyzKeyWindowTestCase):
    """The new buttons and keys through MainWindow and the controllers."""

    def drag_on(self, plot_widget, start_tuple: tuple,
                end_tuple: tuple) -> None:
        """Drag with the left button on a plot widget between data points.

        Inputs:
            plot_widget: the PlotWidget.
            start_tuple: (x, y) data values of the press.
            end_tuple: (x, y) data values of the release.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton, MouseEvent
        start_array = plot_widget.axes.transData.transform(start_tuple)
        end_array = plot_widget.axes.transData.transform(end_tuple)
        for name_str, point_array, button in (
                ("button_press_event", start_array, MouseButton.LEFT),
                ("motion_notify_event", (start_array + end_array) / 2.0,
                 None),
                ("motion_notify_event", end_array, None),
                ("button_release_event", end_array, MouseButton.LEFT)):
            event = MouseEvent(name_str, plot_widget.canvas,
                               float(point_array[0]), float(point_array[1]),
                               button=button)
            plot_widget.canvas.callbacks.process(name_str, event)
        self.application.processEvents()

    def model_shapes(self) -> list:
        """Return the shapes of the first plot of the model.

        Inputs: none.
        Outputs: a list of Shape.
        """
        workspace = self.controller.plot_controller.workspace
        plot_id_i = self.plot_widgets()[0].plot_id_i
        return list(workspace.find_plot(plot_id_i).shape_list)

    @covers("LLFR-01272", "LLFR-01273", "LLFR-00347", "HLFR-00158",
            "HLFR-00032")
    def test_buttons_are_exclusive_plot_tools(self) -> None:
        """Circle and Rectangle are plot tool buttons right of Arrow.

        Inputs: none.
        Outputs: none.
        """
        button_dict = self.top_panel.plot_tool_button_dict
        self.assertIs(button_dict[CIRCLE_TOOL_STR],
                      self.top_panel.circle_button)
        self.assertIs(button_dict[RECTANGLE_TOOL_STR],
                      self.top_panel.rectangle_button)
        self.top_panel.circle_button.click()
        self.application.processEvents()
        self.assert_tool_everywhere(CIRCLE_TOOL_STR)
        self.top_panel.rectangle_button.click()
        self.application.processEvents()
        self.assert_tool_everywhere(RECTANGLE_TOOL_STR)
        self.assertFalse(self.top_panel.circle_button.isChecked())

    @covers("LLFR-01274", "LLFR-01275", "LLFR-01276", "LLFR-01277",
            "LLFR-01278", "LLFR-01279", "LLFR-01071", "HLFR-00158")
    def test_hold_c_and_r(self) -> None:
        """Holding C or R keeps Circle or Rectangle active; the release
        or another key leaves no tool; Ctrl+C or Cmd+C activates none.

        Inputs: none.
        Outputs: none.
        """
        canvas = self.plot_widgets()[0].canvas
        for key_name_str, tool_str in (("Key_C", CIRCLE_TOOL_STR),
                                       ("Key_R", RECTANGLE_TOOL_STR)):
            with self.subTest(key=key_name_str):
                self.press_key(key_name_str, canvas)
                self.assert_tool_everywhere(tool_str)
                self.release_key(key_name_str, canvas)
                self.assert_tool_everywhere(NO_TOOL_STR)
                self.press_key(key_name_str)
                self.press_key("Key_Q")
                self.assert_tool_everywhere(NO_TOOL_STR)
                self.release_key("Key_Q")
                self.release_key(key_name_str)
                self.assert_tool_everywhere(NO_TOOL_STR)
        # LLFR-01274 Note: C with Ctrl (Cmd on macOS) is the Copy
        # shortcut, not a held C.
        self.press_key("Key_C", modifier_name_str="ControlModifier")
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.release_key("Key_C")
        self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-01316", "LLFR-01357", "LLFR-01331", "LLFR-00140",
            "LLFR-00138", "HLFR-00158", "HLFR-00040")
    def test_draw_and_undo_on_one_plot(self) -> None:
        """A rectangle drawn on the first plot is named, kept on that
        plot only and undone in one step.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.rectangle_button.click()
        self.application.processEvents()
        first_widget, second_widget = self.plot_widgets()[0:2]
        bottom_f, top_f = first_widget.axes.get_ylim()
        left_f, right_f = first_widget.axes.get_xlim()
        width_f = right_f - left_f
        height_f = top_f - bottom_f
        self.drag_on(first_widget,
                     (left_f + 0.2 * width_f, bottom_f + 0.2 * height_f),
                     (left_f + 0.6 * width_f, bottom_f + 0.7 * height_f))
        shape_list = self.model_shapes()
        self.assertEqual(len(shape_list), 1)
        self.assertEqual(shape_list[0].name_str, "Rectangle 1")
        self.assertEqual(self.plot_widgets()[0].shape_count(), 1)
        self.assertEqual(second_widget.shape_count(), 0)
        self.main_window.undo_handler()
        self.application.processEvents()
        self.assertEqual(self.model_shapes(), [])

    @covers("LLFR-01280", "LLFR-01281", "LLFR-01282", "LLFR-01283",
            "LLFR-01284", "LLFR-01285", "LLFR-00140", "HLFR-00161")
    def test_hide_labels_button(self) -> None:
        """The button is off at start; a click hides the labels of every
        plot, also of a new plot, and is undoable.

        Inputs: none.
        Outputs: none.
        """
        button = self.top_panel.labels_button
        self.assertFalse(button.isChecked())
        self.assertFalse(any(widget.labels_hidden_b
                             for widget in self.all_plot_widgets()))
        button.click()
        self.application.processEvents()
        self.assertTrue(button.isChecked())
        self.assertTrue(all(widget.labels_hidden_b
                            for widget in self.all_plot_widgets()))
        self.main_window.signal_double_click_handler("speed")
        self.application.processEvents()
        self.assertTrue(all(widget.labels_hidden_b
                            for widget in self.all_plot_widgets()))
        self.main_window.undo_handler()
        self.main_window.undo_handler()
        self.application.processEvents()
        self.assertFalse(button.isChecked())
        self.assertFalse(any(widget.labels_hidden_b
                             for widget in self.all_plot_widgets()))

    @covers("LLFR-01258", "LLFR-01259", "LLFR-01261", "LLFR-01262",
            "LLFR-01289", "HLFR-00016", "HLFR-00061", "HLFR-00118",
            "HLFR-00162")
    def test_titles_of_the_tab_signal_and_file_menus(self) -> None:
        """The tab, signal and file menus start with their title and a
        separator; the file menu has "Create signal" with six options.

        Inputs: none.
        Outputs: none.
        """
        from view.menu_title import is_menu_title
        plot_panel = self.main_window.plot_panel
        tab_menu = plot_panel.build_tab_menu(0)
        self.assertTrue(is_menu_title(tab_menu.actions()[0]))
        self.assertTrue(tab_menu.actions()[1].isSeparator())
        page = plot_panel.page_dict[plot_panel.tab_id_at_index(0)]
        self.assertEqual(tab_menu.actions()[0].text(),
                         "Tab: " + page.name_str)
        signal_panel = self.main_window.signal_list_panel
        signal_menu = signal_panel.build_signal_menu("speed")
        self.assertEqual(signal_menu.actions()[0].text(), "Signal: speed")
        self.assertFalse(signal_menu.actions()[0].isEnabled())
        file_menu = signal_panel.build_file_menu(1)
        self.assertTrue(file_menu.actions()[0].text().startswith("File: "))
        self.assertTrue(is_menu_title(file_menu.actions()[0]))
        option_list = menu_option_texts(file_menu)
        self.assertEqual(option_list[0], "Create signal")
        create_menu = file_menu.actions()[2].menu()
        self.assertEqual([action.text() for action in create_menu.actions()],
                         ["Constant", "Step", "Ramp", "Polynomial", "Sine",
                          "Cosine"])
        self.assertTrue(set(all_menu_actions(create_menu))
                        <= set(all_menu_actions(file_menu)))

    @covers("LLFR-01390", "LLFR-00426", "LLFR-00425", "HLFR-00096")
    def test_plot_menu_title_is_its_place(self) -> None:
        """The plot menu title is "Plot: <row>x<column>": the second plot
        of a one-column tab is 2x1, and of a 2 x 2 matrix 1x2.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint

        def plot_title_str(plot_widget) -> str:
            """Return the title of the menu of an empty point of a plot.

            Inputs:
                plot_widget: a PlotWidget of the current tab.
            Outputs: the text of the title action.
            """
            box = plot_widget.axes.bbox
            display_tuple = (float(box.x0) + 0.02 * float(box.width),
                             float(box.y0) + 0.98 * float(box.height))
            widget_point = plot_widget.display_to_widget_point(
                *display_tuple)
            menu = plot_widget.build_context_menu(
                QPoint(widget_point.x(), widget_point.y()))
            return menu.actions()[0].text()

        plot_widget_list = self.plot_widgets()
        self.assertGreaterEqual(len(plot_widget_list), 2)
        self.assertEqual(plot_title_str(plot_widget_list[0]), "Plot: 1x1")
        self.assertEqual(plot_title_str(plot_widget_list[1]), "Plot: 2x1")
        plot_panel = self.main_window.plot_panel
        self.controller.plot_controller.on_plot_matrix(
            plot_panel.current_tab_id(), 2, 2)
        self.application.processEvents()
        plot_widget_list = self.plot_widgets()
        self.assertEqual(plot_title_str(plot_widget_list[1]), "Plot: 1x2")

    @covers("LLFR-01257", "LLFR-01260", "HLFR-00096")
    def test_long_signal_name_tip(self) -> None:
        """A signal name longer than 40 characters is shortened in the
        title, and the whole name is its tip.

        Inputs: none.
        Outputs: none.
        """
        long_str = "a_very_long_signal_name_" + "x" * 30 + "_end"
        signal_menu = self.main_window.signal_list_panel.build_signal_menu(
            long_str)
        title_action = signal_menu.actions()[0]
        self.assertEqual(len(title_action.text()), len("Signal: ") + 40)
        self.assertIn("…", title_action.text())
        self.assertEqual(title_action.toolTip(), long_str)
        self.assertTrue(signal_menu.toolTipsVisible())


if __name__ == "__main__":
    unittest.main()
