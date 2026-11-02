"""Tests for the arrows of the plot widget and the Arrow tool (issue #155).

Covers drawing an arrow with its preview (LLFR-00371, LLFR-00372), its
look (LLFR-00373), its place when the range or the size changes and the
cut at the edge of the drawing area (LLFR-00374), moving, rotating and
stretching it with previews (LLFR-00376, LLFR-00377), with the Arrow
tool or with no tool and not with the other tools (LLFR-00382,
LLFR-00384), the order of the objects at a point (LLFR-00383), its menu
(LLFR-00378, LLFR-00381), arrows in the exported image (LLFR-00129,
LLFR-00133), frequency plots, the mouse drag rule of the Z key
(LLFR-00207), and, through MainWindow and the real controllers, the
Arrow button (LLFR-00366, LLFR-00347, LLFR-00159, LLFR-00215), the R
key (LLFR-00367 to LLFR-00369, LLFR-00157), arrows on one plot only
(LLFR-00375) and undo and redo (LLFR-00140, LLFR-00138, LLFR-00192).
No modal dialog or menu is ever opened: ``execute_menu`` is replaced.
"""

import math
import unittest

import numpy as np

from tests.support import (
    button_name, button_tip_line_list, covers, get_qt_application,
    requires_qt)
from tests.view.test_plot_tools import PlotWidgetToolTestCase, recorder
from tests.view.test_xyz_keys import (
    FULL_RANGE_TUPLE, ZOOMED_RANGE_TUPLE, XyzKeyWindowTestCase)

from controller.plot_tools import (
    ARROW_TOOL_STR, NO_TOOL_STR, PLOT_TOOL_TUPLE, TEXT_TOOL_STR,
    ZOOM_TOOL_STR)

# Allowed error, in display pixels, of positions rounded to whole widget
# pixels.
PIXEL_TOLERANCE_PX = 1.5
# An arrow across an empty part of the test plot, between the sine (-1
# to 1) and the ramp (3 to 4): (start x, start y, end x, end y).
EMPTY_ARROW_TUPLE = (2.0, 1.5, 6.0, 2.5)
# A color easy to find in a rendered image.
MAGENTA_STR = "#ff00ff"
# The tools that must not edit an arrow (LLFR-00384).
OTHER_TOOL_TUPLE = tuple(tool_str for tool_str in PLOT_TOOL_TUPLE
                         if tool_str != ARROW_TOOL_STR)


def all_menu_actions(menu) -> list:
    """Return the actions of a menu and of its submenus.

    Inputs:
        menu: a QMenu.
    Outputs: a list of QAction.
    """
    action_list = []
    for action in menu.actions():
        action_list.append(action)
        if action.menu() is not None:
            action_list.extend(all_menu_actions(action.menu()))
    return action_list


@requires_qt
class ArrowWidgetTestCase(PlotWidgetToolTestCase):
    """Base class: the plot widget of PlotWidgetToolTestCase with
    recorders for the arrow requests and mouse helpers."""

    def setUp(self) -> None:
        """Record the arrow requests and the other requests.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.create_list = recorder(self.plot_widget.arrow_create_requested)
        self.change_list = recorder(self.plot_widget.arrow_change_requested)
        self.color_list = recorder(self.plot_widget.arrow_color_requested)
        self.delete_list = recorder(self.plot_widget.arrow_delete_requested)
        self.marker_place_list = recorder(
            self.plot_widget.marker_place_requested)
        self.note_move_list = recorder(
            self.plot_widget.text_note_move_requested)
        self.tip_move_list = recorder(
            self.plot_widget.pinned_tip_move_requested)

    def send(self, name_str: str, display_tuple: tuple,
             button=None) -> None:
        """Send a matplotlib mouse event to the canvas.

        Inputs:
            name_str: the matplotlib event name.
            display_tuple: (x, y) in display pixels.
            button: the matplotlib MouseButton, or None for a move.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseEvent
        event = MouseEvent(name_str, self.plot_widget.canvas,
                           float(display_tuple[0]), float(display_tuple[1]),
                           button=button)
        self.plot_widget.canvas.callbacks.process(name_str, event)

    def display_of(self, time_s: float, value_f: float) -> tuple:
        """Return the display pixels of a data point.

        Inputs:
            time_s: x value.
            value_f: y value.
        Outputs: (x, y) in display pixels.
        """
        point_array = self.plot_widget.axes.transData.transform(
            (time_s, value_f))
        return (float(point_array[0]), float(point_array[1]))

    def data_of(self, display_tuple: tuple) -> tuple:
        """Return the data values of a display point.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: (x, y) data values.
        """
        point_array = self.plot_widget.axes.transData.inverted().transform(
            display_tuple)
        return (float(point_array[0]), float(point_array[1]))

    def left_press(self, display_tuple: tuple) -> None:
        """Press the left button at a display point.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        self.send("button_press_event", display_tuple, MouseButton.LEFT)

    def move_to(self, display_tuple: tuple) -> None:
        """Move the pointer, with the left button held, to a point.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: none.
        """
        # A matplotlib event made here has no Qt event, so the button
        # counts as held (mouse_button_held_b).
        self.send("motion_notify_event", display_tuple)

    def left_release(self, display_tuple: tuple) -> None:
        """Release the left button at a display point.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        self.send("button_release_event", display_tuple, MouseButton.LEFT)
        self.application.processEvents()

    def drag(self, start_tuple: tuple, end_tuple: tuple) -> None:
        """Press at a point, move in two steps and release at another.

        Inputs:
            start_tuple: (x, y) of the press, in display pixels.
            end_tuple: (x, y) of the release, in display pixels.
        Outputs: none.
        """
        self.left_press(start_tuple)
        self.move_to(((start_tuple[0] + end_tuple[0]) / 2.0,
                      (start_tuple[1] + end_tuple[1]) / 2.0))
        self.move_to(end_tuple)
        self.left_release(end_tuple)

    def set_one_arrow(self, arrow_tuple: tuple = EMPTY_ARROW_TUPLE,
                      color_str: str = "#24303b") -> None:
        """Give the plot one arrow and draw it.

        Inputs:
            arrow_tuple: (start x, start y, end x, end y).
            color_str: its color.
        Outputs: none.
        """
        self.plot_widget.set_arrows([tuple(arrow_tuple) + (color_str,)])
        self.draw()

    def arrow_ends(self, arrow_index_i: int = 0) -> tuple:
        """Return the ends of a drawn arrow, in display pixels.

        Inputs:
            arrow_index_i: index of the arrow.
        Outputs: ((start x, start y), (end x, end y)).
        """
        return self.plot_widget.arrow_display_tuple(arrow_index_i)

    def assert_near(self, first_tuple: tuple, second_tuple: tuple,
                    tolerance_px: float = PIXEL_TOLERANCE_PX) -> None:
        """Check that two display points are close.

        Inputs:
            first_tuple: (x, y).
            second_tuple: (x, y).
            tolerance_px: allowed distance.
        Outputs: none.
        """
        self.assertLessEqual(
            math.hypot(first_tuple[0] - second_tuple[0],
                       first_tuple[1] - second_tuple[1]), tolerance_px,
            f"{first_tuple} is not near {second_tuple}")

    def emitted_ends(self, value_tuple: tuple) -> tuple:
        """Return the display pixels of the ends of an emitted arrow.

        Inputs:
            value_tuple: (start x, start y, end x, end y) data values.
        Outputs: ((start x, start y), (end x, end y)) display pixels.
        """
        return (self.display_of(*value_tuple[0:2]),
                self.display_of(*value_tuple[2:4]))

    def choose_menu(self, display_tuple: tuple, text_str: str) -> list:
        """Right-click at a display point and choose a menu action.

        Inputs:
            display_tuple: (x, y) in display pixels.
            text_str: text of the action to choose, "" for none.
        Outputs: the texts of the top-level actions of the menu.
        """
        shown_list = []

        def fake_execute_menu(menu, global_point):
            """Record the menu and return the chosen action.

            Inputs:
                menu: the QMenu that would be shown.
                global_point: QPoint in screen coordinates.
            Outputs: the matching QAction, or None.
            """
            shown_list.extend(action.text() for action in menu.actions())
            for action in all_menu_actions(menu):
                if action.text() == text_str:
                    return action
            return None

        self.plot_widget.execute_menu = fake_execute_menu
        self.plot_widget.show_context_menu(
            self.plot_widget.display_to_widget_point(*display_tuple))
        self.application.processEvents()
        return shown_list


class ArrowDrawingTest(ArrowWidgetTestCase):
    """Drawing a new arrow with the Arrow tool (LLFR-00371,
    LLFR-00372)."""

    @covers("LLFR-00371", "LLFR-00372", "LLFR-00373", "HLFR-00081")
    def test_drag_shows_a_preview_and_release_creates(self) -> None:
        """Below 5 pixels nothing is shown; from 5 pixels on a pale
        preview goes from the press to the pointer, outside the axes;
        the release removes it and asks once for the arrow from the
        press to the release, in any direction.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(ARROW_TOOL_STR)
        for start_xy, end_xy in (((3.0, 2.0), (7.0, 1.0)),
                                 ((7.0, 2.5), (2.0, 1.2)),
                                 ((5.0, 1.0), (5.0, 2.8))):
            with self.subTest(start=start_xy, end=end_xy):
                start_tuple = self.display_of(*start_xy)
                end_tuple = self.display_of(*end_xy)
                count_i = len(self.create_list)
                self.left_press(start_tuple)
                self.move_to((start_tuple[0] + 2.0, start_tuple[1] + 2.0))
                self.assertEqual(
                    self.plot_widget.arrow_preview_display_tuple(), ())
                self.assertTrue(self.plot_widget.is_mouse_drag_in_progress())
                self.move_to(end_tuple)
                preview_tuple = (
                    self.plot_widget.arrow_preview_display_tuple())
                self.assertEqual(len(preview_tuple), 2)
                self.assert_near(preview_tuple[0], start_tuple)
                self.assert_near(preview_tuple[1], end_tuple)
                # LLFR-00373: the preview is pale and never in the axes.
                self.plot_widget.place_arrow_preview()
                patch = self.plot_widget.arrow_preview_patch
                self.assertNotIn(patch, self.plot_widget.axes.patches)
                self.assertNotIn(patch, self.plot_widget.axes.get_children())
                self.assertNotEqual(
                    patch.get_facecolor()[:3],
                    (36.0 / 255.0, 48.0 / 255.0, 59.0 / 255.0))
                self.assertEqual(len(self.create_list), count_i)
                self.left_release(end_tuple)
                self.assertEqual(
                    self.plot_widget.arrow_preview_display_tuple(), ())
                self.assertFalse(
                    self.plot_widget.is_mouse_drag_in_progress())
                self.assertEqual(len(self.create_list), count_i + 1)
                start_px, end_px = self.emitted_ends(self.create_list[-1])
                self.assert_near(start_px, start_tuple)
                self.assert_near(end_px, end_tuple)
        self.assertEqual(self.change_list, [])
        # LLFR-00109: the tool stays active.
        self.assertEqual(self.plot_widget.plot_tool_str, ARROW_TOOL_STR)

    @covers("LLFR-00372")
    def test_release_near_the_press_creates_nothing(self) -> None:
        """A click, or a release less than 5 pixels from the press after
        the pointer went further, creates nothing and shows nothing.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(ARROW_TOOL_STR)
        start_tuple = self.display_of(4.0, 2.0)
        self.left_press(start_tuple)
        self.left_release(start_tuple)
        self.left_press(start_tuple)
        self.move_to((start_tuple[0] + 60.0, start_tuple[1]))
        self.assertTrue(self.plot_widget.arrow_preview_display_tuple())
        self.left_release((start_tuple[0] + 3.0, start_tuple[1]))
        self.assertEqual(self.plot_widget.arrow_preview_display_tuple(), ())
        self.assertEqual(self.create_list, [])
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())

    @covers("LLFR-00372")
    def test_release_outside_ends_at_the_drawing_area(self) -> None:
        """A release outside the drawing area ends the arrow at the
        nearest point of the drawing area.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(ARROW_TOOL_STR)
        box = self.plot_widget.axes.bbox
        start_tuple = self.display_of(5.0, 2.0)
        for outside_tuple, corner_tuple in (
                ((box.x1 + 80.0, box.y1 + 50.0), (box.x1, box.y1)),
                ((box.x0 - 40.0, start_tuple[1]), (box.x0, start_tuple[1])),
                ((start_tuple[0], box.y0 - 30.0), (start_tuple[0], box.y0))):
            with self.subTest(outside=outside_tuple):
                self.drag(start_tuple, outside_tuple)
                start_px, end_px = self.emitted_ends(self.create_list[-1])
                self.assert_near(start_px, start_tuple)
                self.assert_near(end_px, corner_tuple)

    @covers("LLFR-00371", "LLFR-00382")
    def test_no_arrow_outside_or_without_the_tool(self) -> None:
        """A press outside the drawing area, or a drag with no tool or
        another tool where no arrow is, creates no arrow.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(ARROW_TOOL_STR)
        box = self.plot_widget.axes.bbox
        self.drag((box.x0 - 20.0, box.y0 - 20.0),
                  self.display_of(5.0, 2.0))
        for tool_str in (NO_TOOL_STR,) + OTHER_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.drag(self.display_of(3.0, 2.0),
                          self.display_of(6.0, 2.2))
                if tool_str == TEXT_TOOL_STR:
                    self.plot_widget.cancel_text_note_editor()
                self.plot_widget.set_time_range(0.0, 10.0)
                self.draw()
        self.assertEqual(self.create_list, [])

    @covers("LLFR-00371", "LLFR-00372")
    def test_leaving_the_tool_cancels_the_drawing(self) -> None:
        """Another tool, or no tool, during a drawing removes the
        preview and creates nothing.

        Inputs: none.
        Outputs: none.
        """
        for new_tool_str in (NO_TOOL_STR, ZOOM_TOOL_STR):
            with self.subTest(tool=new_tool_str):
                self.plot_widget.set_plot_tool(ARROW_TOOL_STR)
                start_tuple = self.display_of(3.0, 2.0)
                self.left_press(start_tuple)
                self.move_to(self.display_of(6.0, 2.0))
                self.assertTrue(
                    self.plot_widget.arrow_preview_display_tuple())
                self.plot_widget.set_plot_tool(new_tool_str)
                self.assertEqual(
                    self.plot_widget.arrow_preview_display_tuple(), ())
                self.assertFalse(
                    self.plot_widget.is_mouse_drag_in_progress())
                self.left_release(self.display_of(6.0, 2.0))
        self.assertEqual(self.create_list, [])


class ArrowLookTest(ArrowWidgetTestCase):
    """The look and the place of an arrow (LLFR-00373, LLFR-00374)."""

    @covers("LLFR-00373")
    def test_solid_line_and_head_in_its_color_between_layers(self) -> None:
        """An arrow without a color gets #24303b; its line is solid, its
        head filled, both in its color, drawn above the curves, flags,
        areas and delta markers and below the pinned tips and notes.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_hex
        from view import plot_widget as plot_widget_module
        self.plot_widget.set_arrows([EMPTY_ARROW_TUPLE])
        self.draw()
        patch = self.plot_widget.arrow_patch(0)
        self.assertEqual(self.plot_widget.arrow_list[0][4], "#24303b")
        self.assertEqual(to_hex(patch.get_edgecolor()), "#24303b")
        self.assertEqual(to_hex(patch.get_facecolor()), "#24303b")
        self.assertEqual(patch.get_linestyle(), "-")
        self.assertIn(patch, self.plot_widget.axes.get_children())
        zorder_f = patch.get_zorder()
        curve_zorder_list = [
            line.get_zorder() for line in self.plot_widget.axes.lines]
        self.assertGreater(zorder_f, max(curve_zorder_list))
        self.assertGreater(zorder_f, plot_widget_module.MARKER_ZORDER_F)
        self.assertGreater(zorder_f, plot_widget_module.AREA_ZORDER_F)
        self.assertGreater(zorder_f,
                           plot_widget_module.DELTA_ZORDER_F + 0.2)
        self.assertLess(zorder_f, 9.0)
        self.assertLess(zorder_f, plot_widget_module.TEXT_NOTE_ZORDER_F)
        # The drawn path holds the line and the closed head, whose point
        # is the arrow's end.
        path = patch.get_path()
        self.assertEqual(len(path.vertices), 6)
        start_tuple, end_tuple = self.arrow_ends()
        self.assert_near(tuple(path.vertices[0]), start_tuple)
        self.assert_near(tuple(path.vertices[2]), end_tuple)

    @covers("LLFR-00374")
    def test_follows_its_ends_on_zoom_pan_and_resize(self) -> None:
        """After a zoom, a pan and a resize the drawn arrow is still at
        the values of its ends.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_arrow()
        for change_function in (
                lambda: self.plot_widget.set_time_range(1.0, 8.0),
                lambda: self.plot_widget.set_time_range(1.5, 8.5),
                lambda: self.plot_widget.resize(450, 300)):
            with self.subTest(change=change_function):
                change_function()
                self.draw()
                patch = self.plot_widget.arrow_patch(0)
                vertex_array = patch.get_path().vertices
                self.assert_near(tuple(vertex_array[0]),
                                 self.display_of(*EMPTY_ARROW_TUPLE[0:2]),
                                 0.01)
                self.assert_near(tuple(vertex_array[2]),
                                 self.display_of(*EMPTY_ARROW_TUPLE[2:4]),
                                 0.01)

    @covers("LLFR-00374")
    def test_cut_at_the_edge_and_head_only_while_shown(self) -> None:
        """An arrow is clipped to the drawing area, and its head is
        drawn only while the end that holds it is shown.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_arrow()
        patch = self.plot_widget.arrow_patch(0)
        self.assertIsNotNone(patch.get_clip_path())
        # The end (x = 6) leaves the shown range: no head.
        self.plot_widget.set_time_range(0.0, 5.0)
        self.draw()
        self.assertEqual(len(patch.get_path().vertices), 2)
        # The start leaves it instead: the head is back.
        self.plot_widget.set_time_range(3.0, 9.0)
        self.draw()
        self.assertEqual(len(patch.get_path().vertices), 6)
        # Off the start, the line is not hit outside the drawing area.
        box = self.plot_widget.axes.bbox
        self.assertEqual(
            self.plot_widget.arrow_at(self.plot_widget.display_to_widget_point(
                box.x0 - 5.0, self.display_of(2.0, 1.5)[1])), -1)

    @covers("LLFR-00373", "LLFR-00383")
    def test_on_the_arrow_within_5_pixels_or_on_the_head(self) -> None:
        """A point within 5 pixels of the line or on the head is on the
        arrow; further away it is not; of two arrows the one drawn last
        is found.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_arrow()
        start_tuple, end_tuple = self.arrow_ends()
        middle_tuple = ((start_tuple[0] + end_tuple[0]) / 2.0,
                        (start_tuple[1] + end_tuple[1]) / 2.0)
        length_px = math.hypot(end_tuple[0] - start_tuple[0],
                               end_tuple[1] - start_tuple[1])
        normal_tuple = (-(end_tuple[1] - start_tuple[1]) / length_px,
                        (end_tuple[0] - start_tuple[0]) / length_px)

        def found(distance_px: float) -> int:
            """Return the arrow found at a distance from the middle.

            Inputs:
                distance_px: display pixels along the normal.
            Outputs: the arrow index or -1.
            """
            return self.plot_widget.arrow_at(
                self.plot_widget.display_to_widget_point(
                    middle_tuple[0] + normal_tuple[0] * distance_px,
                    middle_tuple[1] + normal_tuple[1] * distance_px))

        ratio_f = self.plot_widget.pixel_ratio_f()
        self.assertEqual(found(0.0), 0)
        self.assertEqual(found(3.5 * ratio_f), 0)
        self.assertEqual(found(-3.5 * ratio_f), 0)
        self.assertEqual(found(8.0 * ratio_f), -1)
        # The head is wider than 5 pixels around the line near its back.
        from view import arrow_geometry
        vertex_array = arrow_geometry.head_vertex_array(
            start_tuple, end_tuple, self.plot_widget.pixels_per_point_f())
        corner_tuple = tuple(0.85 * vertex_array[1] + 0.15 * vertex_array[0])
        self.assertEqual(self.plot_widget.arrow_at(
            self.plot_widget.display_to_widget_point(*corner_tuple)), 0)
        # Two arrows crossing: the last one wins.
        self.plot_widget.set_arrows([EMPTY_ARROW_TUPLE,
                                     (2.0, 2.5, 6.0, 1.5)])
        self.draw()
        self.assertEqual(self.plot_widget.arrow_at(
            self.plot_widget.display_to_widget_point(
                *self.display_of(4.0, 2.0))), 1)


class ArrowEditTest(ArrowWidgetTestCase):
    """Moving, rotating and stretching an arrow (LLFR-00376,
    LLFR-00377, LLFR-00382, LLFR-00384)."""

    @covers("LLFR-00376", "LLFR-00382", "HLFR-00082", "HLFR-00085")
    def test_move_by_the_middle_keeps_length_and_direction(self) -> None:
        """With the Arrow tool or no tool, a drag from the middle shows a
        pale preview of the moved arrow and the release asks for the
        same arrow shifted by the drag.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (ARROW_TOOL_STR, NO_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.set_one_arrow(color_str="#0000aa")
                start_tuple, end_tuple = self.arrow_ends()
                middle_tuple = ((start_tuple[0] + end_tuple[0]) / 2.0,
                                (start_tuple[1] + end_tuple[1]) / 2.0)
                shift_tuple = (40.0, -25.0)
                target_tuple = (middle_tuple[0] + shift_tuple[0],
                                middle_tuple[1] + shift_tuple[1])
                self.left_press(middle_tuple)
                self.move_to(target_tuple)
                preview_tuple = (
                    self.plot_widget.arrow_preview_display_tuple())
                self.assert_near(preview_tuple[0],
                                 (start_tuple[0] + shift_tuple[0],
                                  start_tuple[1] + shift_tuple[1]))
                self.assert_near(preview_tuple[1],
                                 (end_tuple[0] + shift_tuple[0],
                                  end_tuple[1] + shift_tuple[1]))
                # LLFR-00373: a paler version of the arrow's color.
                from matplotlib.colors import to_hex
                self.plot_widget.place_arrow_preview()
                pale_str = to_hex(
                    self.plot_widget.arrow_preview_patch.get_facecolor())
                self.assertNotEqual(pale_str, "#0000aa")
                self.assertGreater(int(pale_str[1:3], 16), 0x40)
                self.left_release(target_tuple)
                self.assertEqual(self.change_list[-1][0], 0)
                new_start_px, new_end_px = self.emitted_ends(
                    self.change_list[-1][1:])
                self.assert_near(new_start_px,
                                 (start_tuple[0] + shift_tuple[0],
                                  start_tuple[1] + shift_tuple[1]))
                self.assert_near(new_end_px,
                                 (end_tuple[0] + shift_tuple[0],
                                  end_tuple[1] + shift_tuple[1]))
                self.assertEqual(
                    self.plot_widget.arrow_preview_display_tuple(), ())
        self.assertEqual(self.create_list, [])

    @covers("LLFR-00376", "LLFR-00377")
    def test_short_release_changes_nothing(self) -> None:
        """A release less than 5 pixels from the press, on the middle or
        on an end, changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(ARROW_TOOL_STR)
        self.set_one_arrow()
        start_tuple, end_tuple = self.arrow_ends()
        middle_tuple = ((start_tuple[0] + end_tuple[0]) / 2.0,
                        (start_tuple[1] + end_tuple[1]) / 2.0)
        for press_tuple in (middle_tuple, end_tuple, start_tuple):
            self.left_press(press_tuple)
            self.move_to((press_tuple[0] + 50.0, press_tuple[1] + 30.0))
            self.left_release((press_tuple[0] + 2.0, press_tuple[1]))
        self.assertEqual(self.change_list, [])
        self.assertEqual(self.create_list, [])

    @covers("LLFR-00377", "LLFR-00382", "HLFR-00083", "HLFR-00085")
    def test_rotate_and_stretch_by_either_end(self) -> None:
        """A drag from within 5 pixels of an end moves that end to the
        pointer and keeps the other end; the arrowhead stays at the end
        it was at.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (ARROW_TOOL_STR, NO_TOOL_STR):
            for end_name_str in ("start", "end"):
                with self.subTest(tool=tool_str, end=end_name_str):
                    self.plot_widget.set_plot_tool(tool_str)
                    self.set_one_arrow()
                    start_tuple, end_tuple = self.arrow_ends()
                    pressed_tuple = (start_tuple if end_name_str == "start"
                                     else end_tuple)
                    press_tuple = (pressed_tuple[0] + 2.0,
                                   pressed_tuple[1] + 1.0)
                    target_tuple = self.display_of(5.0, 3.6)
                    self.left_press(press_tuple)
                    self.move_to(target_tuple)
                    preview_tuple = (
                        self.plot_widget.arrow_preview_display_tuple())
                    self.left_release(target_tuple)
                    new_start_px, new_end_px = self.emitted_ends(
                        self.change_list[-1][1:])
                    if end_name_str == "start":
                        self.assert_near(new_start_px, target_tuple)
                        self.assert_near(new_end_px, end_tuple, 0.01)
                    else:
                        self.assert_near(new_start_px, start_tuple, 0.01)
                        self.assert_near(new_end_px, target_tuple)
                    self.assert_near(preview_tuple[0], new_start_px)
                    self.assert_near(preview_tuple[1], new_end_px)

    @covers("LLFR-00377")
    def test_nearer_end_and_minimum_length(self) -> None:
        """On a short arrow, a press within 5 pixels of both ends moves
        the nearer one; the moved end stays 5 pixels from the other; a
        release outside the drawing area puts it on the edge.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(ARROW_TOOL_STR)
        ratio_f = self.plot_widget.pixel_ratio_f()
        start_tuple = self.display_of(5.0, 2.0)
        end_tuple = (start_tuple[0] + 8.0 * ratio_f, start_tuple[1])
        self.set_one_arrow(self.data_of(start_tuple)
                           + self.data_of(end_tuple))
        # Press 2 pixels from the start, 6 from the end: the start moves,
        # and dropping it on the end keeps it 5 pixels away.
        self.left_press((start_tuple[0] + 2.0 * ratio_f, start_tuple[1]))
        self.move_to((start_tuple[0] + 40.0, start_tuple[1] + 40.0))
        self.move_to((end_tuple[0] + 1.0 * ratio_f, end_tuple[1]))
        self.left_release((end_tuple[0] + 1.0 * ratio_f, end_tuple[1]))
        new_start_px, new_end_px = self.emitted_ends(self.change_list[-1][1:])
        self.assert_near(new_end_px, end_tuple, 0.01)
        self.assertAlmostEqual(
            math.hypot(new_start_px[0] - new_end_px[0],
                       new_start_px[1] - new_end_px[1]), 5.0 * ratio_f,
            delta=0.01)
        # Press 2 pixels from the end: the end moves; released far
        # outside the drawing area, it lands on its edge.
        self.set_one_arrow(self.data_of(start_tuple)
                           + self.data_of(end_tuple))
        box = self.plot_widget.axes.bbox
        self.drag((end_tuple[0] - 2.0 * ratio_f, end_tuple[1]),
                  (box.x1 + 100.0, start_tuple[1]))
        new_start_px, new_end_px = self.emitted_ends(self.change_list[-1][1:])
        self.assert_near(new_start_px, start_tuple, 0.01)
        self.assert_near(new_end_px, (box.x1, start_tuple[1]))

    @covers("LLFR-00384", "LLFR-00357", "LLFR-00318")
    def test_other_tools_never_edit_an_arrow(self) -> None:
        """With every other tool, a drag on an arrow asks for no arrow
        change and does what the tool does there: the Zoom tool selects
        a span and the Text tool opens its field.

        Inputs: none.
        Outputs: none.
        """
        self.set_one_arrow()
        for tool_str in OTHER_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                start_tuple, end_tuple = self.arrow_ends()
                middle_tuple = ((start_tuple[0] + end_tuple[0]) / 2.0,
                                (start_tuple[1] + end_tuple[1]) / 2.0)
                for press_tuple in (middle_tuple, end_tuple):
                    self.left_press(press_tuple)
                    if tool_str == TEXT_TOOL_STR:
                        self.assertTrue(
                            self.plot_widget.text_note_editor_open_b)
                        self.plot_widget.cancel_text_note_editor()
                        self.application.processEvents()
                    self.move_to((press_tuple[0] + 40.0,
                                  press_tuple[1] - 30.0))
                    if tool_str == ZOOM_TOOL_STR:
                        self.assertTrue(
                            self.plot_widget.time_span_line_shown())
                    self.assertEqual(
                        self.plot_widget.arrow_preview_display_tuple(), ())
                    self.left_release((press_tuple[0] + 40.0,
                                       press_tuple[1] - 30.0))
                    self.plot_widget.set_time_range(0.0, 10.0)
                    self.draw()
        self.assertEqual(self.change_list, [])
        self.assertEqual(self.create_list, [])

    @covers("LLFR-00383", "LLFR-00153", "LLFR-00339")
    def test_notes_and_tips_over_an_arrow_win(self) -> None:
        """A press on a text note or a pinned tip drawn over an arrow
        moves the note or the tip, never the arrow; with no tool, a press
        on an arrow over a curve moves the arrow.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(ARROW_TOOL_STR)
        self.plot_widget.set_text_notes([("Note", 4.0, 2.0)])
        self.draw()
        box = self.plot_widget.text_note_box_extent(0)
        note_center_tuple = ((box.x0 + box.x1) / 2.0,
                             (box.y0 + box.y1) / 2.0)
        note_data_tuple = self.data_of(note_center_tuple)
        self.set_one_arrow((note_data_tuple[0] - 1.0, note_data_tuple[1],
                            note_data_tuple[0] + 1.0, note_data_tuple[1]))
        self.drag(note_center_tuple,
                  (note_center_tuple[0] + 30.0, note_center_tuple[1] + 20.0))
        self.assertEqual(len(self.note_move_list), 1)
        self.assertEqual(self.change_list, [])
        self.assertEqual(self.create_list, [])
        # A pinned tip over the arrow.
        self.plot_widget.set_text_notes([])
        self.plot_widget.set_pinned_tips([("Sine", 5.0, math.sin(5.0))])
        self.draw()
        tip_center_tuple = self.plot_widget.tip_label_center_tuple(0)
        tip_data_tuple = self.data_of(tip_center_tuple)
        self.set_one_arrow((tip_data_tuple[0] - 1.0, tip_data_tuple[1],
                            tip_data_tuple[0] + 1.0, tip_data_tuple[1]))
        self.drag(tip_center_tuple,
                  (tip_center_tuple[0] - 30.0, tip_center_tuple[1] + 20.0))
        self.assertEqual(len(self.tip_move_list), 1)
        self.assertEqual(self.change_list, [])
        # An arrow over a curve, with no tool: the arrow moves.
        self.plot_widget.set_pinned_tips([])
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        self.set_one_arrow((1.0, 3.1, 9.0, 3.9))
        self.drag(self.display_of(5.0, 3.5), self.display_of(5.0, 2.0))
        self.assertEqual(len(self.change_list), 1)

    @covers("LLFR-00207", "LLFR-00376")
    def test_drag_counts_as_a_mouse_drag(self) -> None:
        """From the press to the release, a drawing or an edit of an
        arrow is a mouse drag; a right press cancels it.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        self.set_one_arrow()
        start_tuple, end_tuple = self.arrow_ends()
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        self.left_press(end_tuple)
        self.assertTrue(self.plot_widget.is_mouse_drag_in_progress())
        self.move_to((end_tuple[0] + 30.0, end_tuple[1]))
        self.assertTrue(self.plot_widget.is_mouse_drag_in_progress())
        self.plot_widget.cancel_drags()
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        self.assertEqual(self.plot_widget.arrow_preview_display_tuple(), ())
        self.left_release((end_tuple[0] + 30.0, end_tuple[1]))
        self.assertEqual(self.change_list, [])
        # A new list of arrows ends an edit drag without a request.
        self.left_press(end_tuple)
        self.move_to((end_tuple[0] + 30.0, end_tuple[1]))
        self.set_one_arrow()
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        self.left_release((end_tuple[0] + 30.0, end_tuple[1]))
        self.assertEqual(self.change_list, [])


class ArrowMenuTest(ArrowWidgetTestCase):
    """The arrow menu (LLFR-00378 to LLFR-00381)."""

    @covers("LLFR-00378", "LLFR-00379", "LLFR-00380", "LLFR-00381",
            "LLFR-00048")
    def test_menu_over_curves_with_every_tool(self) -> None:
        """An arrow over a curve shows "Color" and "Delete" with any
        tool, and each asks for that arrow; elsewhere "Delete plot".

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_arrows([EMPTY_ARROW_TUPLE,
                                     (1.0, 3.1, 9.0, 3.9)])
        self.draw()
        on_curve_tuple = self.display_of(5.0, 3.5)
        for tool_str in PLOT_TOOL_TUPLE + (NO_TOOL_STR,):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.assertEqual(self.choose_menu(on_curve_tuple, ""),
                                 ["Color", "Delete"])
        self.choose_menu(on_curve_tuple, "Color")
        self.assertEqual(self.color_list, [(1,)])
        self.choose_menu(self.display_of(4.0, 2.0), "Delete")
        self.assertEqual(self.delete_list, [(0,)])
        self.assertEqual(self.choose_menu(self.display_of(8.0, 2.0), ""),
                         ["Delete plot"])

    @covers("LLFR-00381", "LLFR-00341", "LLFR-00046")
    def test_note_and_tip_menus_over_an_arrow(self) -> None:
        """A text note or a pinned tip over an arrow shows its own menu.

        Inputs: none.
        Outputs: none.
        """
        delete_tip_list = recorder(
            self.plot_widget.pinned_tip_delete_requested)
        self.plot_widget.set_text_notes([("Note", 4.0, 2.0)])
        self.draw()
        box = self.plot_widget.text_note_box_extent(0)
        note_center_tuple = ((box.x0 + box.x1) / 2.0,
                             (box.y0 + box.y1) / 2.0)
        note_data_tuple = self.data_of(note_center_tuple)
        self.set_one_arrow((note_data_tuple[0] - 1.0, note_data_tuple[1],
                            note_data_tuple[0] + 1.0, note_data_tuple[1]))
        self.assertEqual(self.choose_menu(note_center_tuple, "")[0], "Edit")
        self.plot_widget.set_text_notes([])
        self.plot_widget.set_pinned_tips([("Sine", 5.0, math.sin(5.0))])
        self.draw()
        tip_center_tuple = self.plot_widget.tip_label_center_tuple(0)
        tip_data_tuple = self.data_of(tip_center_tuple)
        self.set_one_arrow((tip_data_tuple[0] - 1.0, tip_data_tuple[1],
                            tip_data_tuple[0] + 1.0, tip_data_tuple[1]))
        self.choose_menu(tip_center_tuple, "Delete")
        self.assertEqual(delete_tip_list, [(0,)])
        self.assertEqual(self.delete_list, [])


class ArrowImageTest(ArrowWidgetTestCase):
    """Arrows in the PDF pages and the copied image (LLFR-00129,
    LLFR-00133), without their previews (LLFR-00373)."""

    @covers("LLFR-00129", "LLFR-00133", "LLFR-00373")
    def test_rendered_figure_shows_arrows_but_no_preview(self) -> None:
        """The figure image of the export holds a magenta arrow, but not
        the preview of an arrow being drawn.

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
        self.set_one_arrow(color_str=MAGENTA_STR)
        shown_count_i = magenta_pixel_count(
            plot_export.render_figure_image(figure, figure.dpi))
        self.assertGreater(shown_count_i, empty_count_i + 50)
        # A preview of a magenta arrow being moved is not in the image.
        self.plot_widget.set_plot_tool(ARROW_TOOL_STR)
        start_tuple, end_tuple = self.arrow_ends()
        self.left_press(end_tuple)
        self.move_to(self.display_of(9.0, 1.0))
        self.assertTrue(self.plot_widget.arrow_preview_display_tuple())
        preview_count_i = magenta_pixel_count(
            plot_export.render_figure_image(figure, figure.dpi))
        self.assertLessEqual(abs(preview_count_i - shown_count_i), 5)
        self.plot_widget.cancel_drags()


@requires_qt
class FrequencyPlotArrowTest(ArrowWidgetTestCase):
    """Arrows on a frequency plot (LLFR-00371)."""

    def setUp(self) -> None:
        """Replace the widget by a frequency plot with one curve.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        from model.workspace import FREQUENCY_PLOT_KIND_STR
        from view.plot_widget import PlotWidget
        self.plot_widget.close()
        self.plot_widget.deleteLater()
        self.plot_widget = PlotWidget(4, kind_str=FREQUENCY_PLOT_KIND_STR)
        self.plot_widget.resize(600, 400)
        self.plot_widget.show()
        self.application.processEvents()
        frequency_array = np.linspace(0.0, 50.0, 51)
        self.plot_widget.set_curves([
            ("fft_s1", frequency_array, np.exp(-frequency_array / 10.0),
             "#0000ff", 1)])
        self.draw()
        self.create_list = recorder(self.plot_widget.arrow_create_requested)
        self.change_list = recorder(self.plot_widget.arrow_change_requested)

    @covers("LLFR-00371", "LLFR-00372", "LLFR-00376", "LLFR-00374")
    def test_draw_and_move_on_a_frequency_plot(self) -> None:
        """The Arrow tool draws an arrow on a frequency plot, with x in
        Hz, and the arrow can be moved there.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(ARROW_TOOL_STR)
        start_tuple = self.display_of(10.0, 0.5)
        end_tuple = self.display_of(30.0, 0.8)
        self.drag(start_tuple, end_tuple)
        self.assertEqual(len(self.create_list), 1)
        value_tuple = self.create_list[0]
        self.assertAlmostEqual(value_tuple[0], 10.0, delta=0.5)
        self.assertAlmostEqual(value_tuple[2], 30.0, delta=0.5)
        self.set_one_arrow(value_tuple)
        start_px, end_px = self.arrow_ends()
        middle_tuple = ((start_px[0] + end_px[0]) / 2.0,
                        (start_px[1] + end_px[1]) / 2.0)
        self.drag(middle_tuple, (middle_tuple[0] + 30.0, middle_tuple[1]))
        self.assertEqual(len(self.change_list), 1)
        self.assertGreater(self.change_list[0][1], value_tuple[0])


@requires_qt
class ArrowButtonTest(unittest.TestCase):
    """The Arrow button of the top panel (LLFR-00366, LLFR-00347,
    LLFR-00159, LLFR-00215)."""

    def setUp(self) -> None:
        """Create and show a top panel wide enough for every button.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.top_panel import TopPanel
        self.top_panel = TopPanel()
        self.top_panel.resize(1100, 60)
        self.top_panel.show()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close and delete the panel.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.close()
        self.top_panel.deleteLater()
        self.application.processEvents()

    @covers("LLFR-00366", "LLFR-00347", "LLFR-00158", "LLFR-00159",
            "LLFR-00213", "LLFR-00215")
    def test_button_icon_tip_and_place(self) -> None:
        """The Arrow button shows only the arrow icon, its tip says
        "Hold R", and it is the last plot tool, right of Text.

        Inputs: none.
        Outputs: none.
        """
        from view import icon_shapes
        button = self.top_panel.arrow_button
        self.assertEqual(button_name(button), "Arrow")
        self.assertEqual(button.text(), "")
        self.assertEqual(button.icon_name_str, icon_shapes.ARROW_ICON_STR)
        self.assertEqual(button_tip_line_list(button), ["Arrow", "Hold R"])
        tool_button_list = list(
            self.top_panel.plot_tool_button_dict.values())
        self.assertIs(tool_button_list[-1], button)
        self.assertIs(self.top_panel.plot_tool_button_dict[ARROW_TOOL_STR],
                      button)
        self.assertEqual(button.x(), self.top_panel.text_button.x()
                         + self.top_panel.text_button.width())
        self.assertIn(button, self.top_panel.button_group_list[1])

    @covers("LLFR-00159")
    def test_icon_points_up_and_to_the_right(self) -> None:
        """The arrow icon is a straight shaft from the lower left with a
        filled head at the upper right.

        Inputs: none.
        Outputs: none.
        """
        from view import icon_shapes
        layer_list = icon_shapes.icon_layer_list(icon_shapes.ARROW_ICON_STR)
        shaft_command_list = layer_list[0][0]
        (start_x_f, start_y_f), (end_x_f, end_y_f) = (
            shaft_command_list[0][1:], shaft_command_list[1][1:])
        # The grid's y grows downwards: up and to the right.
        self.assertGreater(end_x_f, start_x_f)
        self.assertLess(end_y_f, start_y_f)
        head_command_list = layer_list[1][0]
        self.assertTrue(layer_list[1][2])
        tip_x_f, tip_y_f = head_command_list[0][1:]
        self.assertGreater(tip_x_f, end_x_f)
        self.assertLess(tip_y_f, end_y_f)

    @covers("LLFR-00366", "LLFR-00079", "LLFR-00109", "LLFR-00002")
    def test_arrow_is_an_exclusive_plot_tool(self) -> None:
        """A click on Arrow makes it the only active tool, until it is
        clicked again or another tool is chosen.

        Inputs: none.
        Outputs: none.
        """
        reported_list = []
        self.top_panel.plot_tool_changed.connect(reported_list.append)
        button = self.top_panel.arrow_button
        for other_tool_str in PLOT_TOOL_TUPLE[:-1]:
            with self.subTest(other=other_tool_str):
                other_button = self.top_panel.plot_tool_button_dict[
                    other_tool_str]
                other_button.click()
                button.click()
                self.assertTrue(button.is_active())
                self.assertFalse(other_button.is_active())
                self.assertEqual(reported_list[-1], ARROW_TOOL_STR)
                other_button.click()
                self.assertFalse(button.is_active())
                other_button.click()
        button.click()
        button.click()
        self.assertFalse(button.is_active())
        self.assertEqual(reported_list[-1], NO_TOOL_STR)


@requires_qt
class ArrowKeyAndEndToEndTest(XyzKeyWindowTestCase):
    """The R key and arrows through MainWindow and the real
    controllers."""

    def model_arrows(self, plot_index_i: int = 0) -> list:
        """Return the arrows of a plot of the current tab in the model.

        Inputs:
            plot_index_i: index of the plot in the tab.
        Outputs: a list of (start x, start y, end x, end y, color).
        """
        plot = self.controller.plot_controller.workspace.find_plot(
            self.plot_widgets()[plot_index_i].plot_id_i)
        return [(arrow.start_time_s, arrow.start_value_f, arrow.end_time_s,
                 arrow.end_value_f, arrow.color_str)
                for arrow in plot.arrow_list]

    def draw_arrow(self, start_s: float = 1.0, end_s: float = 2.5) -> None:
        """Draw an arrow across the first plot with the mouse.

        Inputs:
            start_s: time of the press, in the middle of the y range.
            end_s: time of the release.
        Outputs: none.
        """
        self.draw_plots()
        plot_widget = self.plot_widgets()[0]
        self.send_mouse(plot_widget, "MouseButtonPress", start_s,
                        "LeftButton", "LeftButton")
        self.send_mouse(plot_widget, "MouseMove", (start_s + end_s) / 2.0,
                        "NoButton", "LeftButton")
        self.send_mouse(plot_widget, "MouseButtonRelease", end_s,
                        "LeftButton", "NoButton")

    @covers("LLFR-00367", "LLFR-00368", "LLFR-00079")
    def test_hold_r_and_release(self) -> None:
        """R alone makes Arrow the only active tool, whatever tool was
        active; the release leaves no tool active.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from view import tip_key_filter
        self.assertEqual(tip_key_filter.ARROW_KEY_I, int(Qt.Key.Key_R.value))
        self.assertNotIn(tip_key_filter.ARROW_KEY_I,
                         tip_key_filter.OWN_MODIFIER_DICT)
        canvas = self.plot_widgets()[0].canvas
        for previous_tool_str in (NO_TOOL_STR,) + PLOT_TOOL_TUPLE:
            with self.subTest(previous=previous_tool_str):
                if previous_tool_str != NO_TOOL_STR:
                    self.top_panel.plot_tool_button_dict[
                        previous_tool_str].click()
                    self.application.processEvents()
                self.press_key("Key_R", canvas)
                self.assert_tool_everywhere(ARROW_TOOL_STR)
                self.release_key("Key_R", canvas)
                self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00369", "LLFR-00367")
    def test_other_key_or_modifier_ends_the_hold(self) -> None:
        """Another key while R is held leaves no tool active; R with a
        modifier or with another key held activates nothing; auto-repeat
        keeps the hold.

        Inputs: none.
        Outputs: none.
        """
        for other_key_name_str in ("Key_B", "Key_Shift", "Key_Control",
                                   "Key_X", "Key_A", "Key_T", "Key_Z"):
            with self.subTest(other=other_key_name_str):
                self.press_key("Key_R")
                self.assert_tool_everywhere(ARROW_TOOL_STR)
                self.press_key(other_key_name_str)
                self.assert_tool_everywhere(NO_TOOL_STR)
                self.release_key(other_key_name_str)
                self.release_key("Key_R")
                self.assert_tool_everywhere(NO_TOOL_STR)
        for modifier_name_str in ("ControlModifier", "ShiftModifier",
                                  "AltModifier"):
            self.press_key("Key_R", modifier_name_str=modifier_name_str)
            self.assert_tool_everywhere(NO_TOOL_STR)
            self.release_key("Key_R")
        self.press_key("Key_B")
        self.press_key("Key_R")
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.release_key("Key_R")
        self.release_key("Key_B")
        self.press_key("Key_R")
        for _ in range(3):
            self.release_key("Key_R", auto_repeat_b=True)
            self.press_key("Key_R", auto_repeat_b=True)
            self.assert_tool_everywhere(ARROW_TOOL_STR)
        self.release_key("Key_R")
        self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00157", "LLFR-00367")
    def test_r_typed_in_the_search_box(self) -> None:
        """In the search box r and R are typed and change no tool.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        self.activate_window()
        self.search_box.setFocus()
        self.application.processEvents()
        QTest.keyClicks(self.search_box, "rR")
        self.application.processEvents()
        self.assertEqual(self.search_box.text(), "rR")
        self.press_key("Key_R", self.search_box)
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.release_key("Key_R", self.search_box)

    @covers("LLFR-00372", "LLFR-00375", "LLFR-00140", "LLFR-00138",
            "LLFR-00192", "HLFR-00081", "HLFR-00040", "HLFR-00048")
    def test_draw_undo_and_redo_on_one_plot(self) -> None:
        """An arrow drawn with the mouse is kept on its plot only; Undo
        removes it and Redo brings it back.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.plot_tool_button_dict[ARROW_TOOL_STR].click()
        self.application.processEvents()
        self.draw_arrow()
        arrow_list = self.model_arrows()
        self.assertEqual(len(arrow_list), 1)
        self.assertAlmostEqual(arrow_list[0][0], 1.0, delta=0.05)
        self.assertAlmostEqual(arrow_list[0][2], 2.5, delta=0.05)
        self.assertEqual(arrow_list[0][4], "#24303b")
        self.assertEqual(self.plot_widgets()[0].arrow_count(), 1)
        self.assertEqual(self.plot_widgets()[1].arrow_count(), 0)
        self.assertEqual(self.model_arrows(1), [])
        self.main_window.undo_handler()
        self.application.processEvents()
        self.assertEqual(self.model_arrows(), [])
        self.assertEqual(self.plot_widgets()[0].arrow_count(), 0)
        self.main_window.redo_handler()
        self.application.processEvents()
        self.assertEqual(len(self.model_arrows()), 1)
        self.assertEqual(self.plot_widgets()[0].arrow_count(), 1)

    @covers("LLFR-00207", "LLFR-00371", "LLFR-00376")
    def test_z_does_nothing_during_an_arrow_drag(self) -> None:
        """Z while an arrow is drawn or dragged does nothing; after the
        release it resets.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.plot_tool_button_dict[ARROW_TOOL_STR].click()
        self.zoom_in()
        self.draw_plots()
        plot_widget = self.plot_widgets()[0]
        self.send_mouse(plot_widget, "MouseButtonPress", 1.0,
                        "LeftButton", "LeftButton")
        self.send_mouse(plot_widget, "MouseMove", 1.8, "NoButton",
                        "LeftButton")
        self.assertTrue(self.main_window.is_mouse_drag_in_progress())
        self.press_key("Key_Z", plot_widget.canvas)
        self.release_key("Key_Z", plot_widget.canvas)
        self.assert_every_range(ZOOMED_RANGE_TUPLE)
        self.send_mouse(plot_widget, "MouseButtonRelease", 1.8,
                        "LeftButton", "NoButton")
        self.assertFalse(self.main_window.is_mouse_drag_in_progress())
        self.assertEqual(len(self.model_arrows()), 1)
        # With no tool, a drag of the arrow is a mouse drag too.
        self.top_panel.plot_tool_button_dict[ARROW_TOOL_STR].click()
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.draw_plots()
        plot_widget = self.plot_widgets()[0]
        self.send_mouse(plot_widget, "MouseButtonPress", 1.4,
                        "LeftButton", "LeftButton")
        self.send_mouse(plot_widget, "MouseMove", 2.0, "NoButton",
                        "LeftButton")
        self.assertTrue(self.main_window.is_mouse_drag_in_progress())
        self.press_key("Key_Z", plot_widget.canvas)
        self.release_key("Key_Z", plot_widget.canvas)
        self.assert_every_range(ZOOMED_RANGE_TUPLE)
        self.send_mouse(plot_widget, "MouseButtonRelease", 2.0,
                        "LeftButton", "NoButton")
        arrow_list = self.model_arrows()
        self.assertAlmostEqual(arrow_list[0][0], 1.6, delta=0.05)
        self.press_key("Key_Z")
        self.release_key("Key_Z")
        self.assert_every_range(FULL_RANGE_TUPLE)

    @covers("LLFR-00379", "LLFR-00380", "LLFR-00390")
    def test_color_and_delete_through_the_menu(self) -> None:
        """"Color" asks the shared picker and draws the arrow in the
        confirmed color; "Delete" removes it; both are undoable.

        Inputs: none.
        Outputs: none.
        """
        from unittest import mock
        self.top_panel.plot_tool_button_dict[ARROW_TOOL_STR].click()
        self.draw_arrow()
        self.draw_plots()
        plot_widget = self.plot_widgets()[0]
        bottom_f, top_f = plot_widget.axes.get_ylim()
        menu_point = plot_widget.data_to_widget_point(
            1.75, (bottom_f + top_f) / 2.0)

        def choose(text_str: str):
            """Return a fake execute_menu that picks one action.

            Inputs:
                text_str: the action text.
            Outputs: the function.
            """
            def fake_execute_menu(menu, global_point):
                """Return the action with the text.

                Inputs:
                    menu: the QMenu.
                    global_point: unused.
                Outputs: the QAction or None.
                """
                for action in menu.actions():
                    if action.text() == text_str:
                        return action
                return None
            return fake_execute_menu

        plot_widget.execute_menu = choose("Color")
        with mock.patch.object(self.main_window, "ask_color",
                               return_value="#00aa00") as ask_mock:
            plot_widget.show_context_menu(menu_point)
            self.application.processEvents()
        ask_mock.assert_called_once_with("#24303b")
        self.assertEqual(self.model_arrows()[0][4], "#00aa00")
        plot_widget = self.plot_widgets()[0]
        self.assertEqual(plot_widget.arrow_list[0][4], "#00aa00")
        plot_widget.execute_menu = choose("Delete")
        plot_widget.show_context_menu(menu_point)
        self.application.processEvents()
        self.assertEqual(self.model_arrows(), [])
        self.main_window.undo_handler()
        self.application.processEvents()
        self.assertEqual(self.model_arrows()[0][4], "#00aa00")
        self.main_window.undo_handler()
        self.application.processEvents()
        self.assertEqual(self.model_arrows()[0][4], "#24303b")


if __name__ == "__main__":
    unittest.main()
