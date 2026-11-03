"""Tests for the Pan tool (issue #141, HLFR-00036, HLFR-00032).

Covers LLFR-00355 (the Pan button), LLFR-00356 (pan by left drag),
LLFR-00357 (what a press does with the Pan button active), with the
limits and y-axis fits of LLFR-00118 to LLFR-00120, the frequency plots
of LLFR-00258, the Z key of LLFR-00207 and the button rules of
LLFR-00079, LLFR-00109, LLFR-00159, LLFR-00214 and LLFR-00215. No modal
dialog or menu is ever opened.
"""

import os
import tempfile
import time
import unittest
from unittest import mock

import numpy as np

from tests.support import (
    button_name, button_tip_line_list, covers, get_qt_application,
    requires_qt)
from tests.support import OPEN_FILE_DIALOG_TARGET_STR
from tests.view.test_frequency_plots_view import (
    SAMPLE_COUNT_I, SAMPLE_RATE_HZ, SINE_AMPLITUDE_F, SINE_FREQUENCY_HZ,
    find_action)
from tests.view.test_navigation import (
    PIXEL_TOLERANCE_S, NavigationWidgetTestCase)
from tests.view.test_plot_tools import recorder

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, PAN_TOOL_STR, PLOT_TOOL_TUPLE,
    TIP_TOOL_STR, ZOOM_TOOL_STR)
from model.workspace import DELTA_X_KIND_STR

# LLFR-00215: the line below the name in the Pan button tip.
PAN_TIP_LINE_STR = "Drag on a plot to pan"


class PanToolDataTest(unittest.TestCase):
    """Checks of the Pan tool that need no Qt."""

    @covers("LLFR-00355", "LLFR-00347", "LLFR-00079")
    def test_pan_is_a_plot_tool_between_zoom_and_marker(self) -> None:
        """PAN_TOOL_STR is a plot tool, right after Zoom.

        Inputs: none.
        Outputs: none.
        """
        from controller.plot_tools import is_delta_tool, is_known_plot_tool
        self.assertTrue(is_known_plot_tool(PAN_TOOL_STR))
        self.assertFalse(is_delta_tool(PAN_TOOL_STR))
        zoom_index_i = PLOT_TOOL_TUPLE.index(ZOOM_TOOL_STR)
        self.assertEqual(PLOT_TOOL_TUPLE[zoom_index_i + 1], PAN_TOOL_STR)
        self.assertEqual(PLOT_TOOL_TUPLE[zoom_index_i + 2], MARKER_TOOL_STR)
        self.assertEqual(len(set(PLOT_TOOL_TUPLE)), len(PLOT_TOOL_TUPLE))

    @covers("LLFR-00159")
    def test_open_hand_icon_shape(self) -> None:
        """The Pan icon has four fingers, a palm and a thumb, drawn with
        the icon pen inside the grid.

        Inputs: none.
        Outputs: none.
        """
        from view import icon_shapes
        layer_list = icon_shapes.icon_layer_list(icon_shapes.PAN_ICON_STR)
        # Four fingers, the palm and the thumb.
        self.assertEqual(len(layer_list), 6)
        finger_x_list = []
        for command_list, stroke_str, fill_str, width_f in layer_list[:4]:
            self.assertEqual(stroke_str, icon_shapes.INK_ROLE_STR)
            self.assertEqual(width_f, icon_shapes.ICON_STROKE_WIDTH_F)
            # Each finger is a vertical stroke up from the palm.
            (_, start_x_f, start_y_f), (_, end_x_f, end_y_f) = command_list
            self.assertEqual(start_x_f, end_x_f)
            self.assertLess(end_y_f, start_y_f)
            finger_x_list.append(start_x_f)
        self.assertEqual(finger_x_list, sorted(finger_x_list))
        self.assertEqual(len(set(finger_x_list)), 4)


@requires_qt
class PanToolWidgetTest(NavigationWidgetTestCase):
    """A left drag with the Pan tool, in a plot widget alone."""

    def setUp(self) -> None:
        """Create the plot widget with the Pan tool active.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.plot_widget.set_plot_tool(PAN_TOOL_STR)
        self.marker_move_list = recorder(
            self.plot_widget.marker_move_requested)
        self.marker_drag_list = recorder(self.plot_widget.marker_drag_moved)
        self.area_change_list = recorder(
            self.plot_widget.area_change_requested)
        self.area_create_list = recorder(
            self.plot_widget.area_create_requested)
        self.delta_pick_list = recorder(self.plot_widget.delta_point_picked)
        self.tip_move_list = recorder(
            self.plot_widget.pinned_tip_move_requested)
        self.note_move_list = recorder(
            self.plot_widget.text_note_move_requested)
        self.menu_list = []
        self.plot_widget.execute_menu = (
            lambda menu, point: self.menu_list.append(menu))

    def send_display(self, name_str: str, display_x_px: float,
                     display_y_px: float, left_b: bool = True) -> None:
        """Send a matplotlib mouse event at a display point.

        Inputs:
            name_str: the matplotlib event name.
            display_x_px: display x of the mouse.
            display_y_px: display y of the mouse.
            left_b: True to give the left button (press and release),
                False for a move without a button.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton, MouseEvent
        event = MouseEvent(name_str, self.plot_widget.canvas,
                           display_x_px, display_y_px,
                           button=MouseButton.LEFT if left_b else None)
        self.plot_widget.canvas.callbacks.process(name_str, event)

    def left_press(self, display_x_px: float, value_f: float = 0.0) -> None:
        """Press the left button at a display x and a y value.

        Inputs:
            display_x_px: display x of the mouse.
            value_f: y data value of the mouse.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        self.mouse_event("button_press_event", display_x_px, value_f,
                         MouseButton.LEFT)

    def left_release(self, display_x_px: float,
                     value_f: float = 0.0) -> None:
        """Release the left button at a display x and a y value.

        Inputs:
            display_x_px: display x of the mouse.
            value_f: y data value of the mouse.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        self.mouse_event("button_release_event", display_x_px, value_f,
                         MouseButton.LEFT)

    def zoom_to(self, start_s: float, end_s: float) -> None:
        """Show a time range and draw, then forget the emitted ranges.

        Inputs:
            start_s: first time shown.
            end_s: last time shown.
        Outputs: none.
        """
        self.plot_widget.set_time_range(start_s, end_s)
        self.draw()
        self.range_list.clear()

    def assert_nothing_else_happened(self) -> None:
        """Check that no item was changed and no menu was opened.

        Inputs: none.
        Outputs: none.
        """
        self.application.processEvents()
        self.assertEqual(self.pin_list, [])
        self.assertEqual(self.marker_place_list, [])
        self.assertEqual(self.marker_move_list, [])
        self.assertEqual(self.marker_drag_list, [])
        self.assertEqual(self.area_change_list, [])
        self.assertEqual(self.area_create_list, [])
        self.assertEqual(self.delta_pick_list, [])
        self.assertEqual(self.menu_list, [])
        self.assertFalse(self.plot_widget.text_note_editor_open_b)

    @covers("LLFR-00356", "LLFR-00120", "LLFR-00109")
    def test_left_drag_pans_by_the_pointer_distance(self) -> None:
        """The time grabbed at the press stays under the pointer, the
        width is kept, y fits the curves, and the tool stays active.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_to(2.0, 4.0)
        self.left_press(self.display_x_px(3.0))
        self.assertTrue(self.plot_widget.panning_b)
        self.assertEqual(self.range_list, [])
        target_x_px = self.display_x_px(3.5)
        self.move(target_x_px)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 1.5, delta=PIXEL_TOLERANCE_S)
        self.assertAlmostEqual(end_s - start_s, 2.0)
        self.assertAlmostEqual(self.display_x_px(3.0), target_x_px,
                               delta=2.0)
        self.assert_curves_fit()
        # Moving left drags the curves left: later times come in.
        target_x_px = self.display_x_px(2.0)
        self.move(target_x_px)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 2.5, delta=PIXEL_TOLERANCE_S)
        self.assertAlmostEqual(self.display_x_px(3.0), target_x_px,
                               delta=2.0)
        self.assert_curves_fit()
        self.left_release(target_x_px)
        self.assertFalse(self.plot_widget.panning_b)
        self.assertGreaterEqual(len(self.range_list), 2)
        self.assertEqual(self.range_list[-1],
                         self.plot_widget.time_range_tuple())
        # After the release a move no longer pans.
        emitted_count_i = len(self.range_list)
        self.move(self.display_x_px(2.0))
        self.assertEqual(len(self.range_list), emitted_count_i)
        # LLFR-00109: the tool is still active.
        self.assertEqual(self.plot_widget.plot_tool_str, PAN_TOOL_STR)
        self.assert_nothing_else_happened()

    @covers("LLFR-00356", "LLFR-00118")
    def test_no_pan_at_the_whole_range(self) -> None:
        """At the whole time range a left drag changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.left_press(self.display_x_px(5.0))
        for time_s in (7.0, 2.0, 9.9, 0.1):
            self.move(self.display_x_px(time_s))
            self.assertEqual(self.plot_widget.time_range_tuple(),
                             (0.0, 10.0))
        self.left_release(self.display_x_px(1.0))
        self.assertEqual(self.range_list, [])
        self.assert_nothing_else_happened()

    @covers("LLFR-00356", "LLFR-00119")
    def test_pan_stops_at_first_and_last_sample(self) -> None:
        """A long left drag stops at the data's ends and keeps the width.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_to(1.0, 3.0)
        press_x_px = self.display_x_px(2.0)
        pixels_per_second_f = self.display_x_px(3.0) - press_x_px
        self.left_press(press_x_px)
        self.move(press_x_px + 5.0 * pixels_per_second_f)
        self.assertEqual(self.plot_widget.time_range_tuple(), (0.0, 2.0))
        self.move(press_x_px - 20.0 * pixels_per_second_f)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 8.0)
        self.assertEqual(end_s, 10.0)
        for emitted_start_s, emitted_end_s in self.range_list:
            self.assertGreaterEqual(emitted_start_s, 0.0)
            self.assertLessEqual(emitted_end_s, 10.0)
            self.assertAlmostEqual(emitted_end_s - emitted_start_s, 2.0)
        self.left_release(press_x_px - 20.0 * pixels_per_second_f)

    @covers("LLFR-00357")
    def test_click_without_a_move_does_nothing(self) -> None:
        """A left press and release at one point shifts nothing, pins
        nothing, places nothing and opens nothing, also on a curve and
        on a double-click.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_to(3.0, 5.0)
        sine_value_f = float(np.sin(4.0))
        for value_f in (sine_value_f, 0.9):
            with self.subTest(value=value_f):
                press_x_px = self.display_x_px(4.0)
                self.left_press(press_x_px, value_f)
                self.move(press_x_px, value_f)
                self.left_release(press_x_px, value_f)
                from matplotlib.backend_bases import MouseButton
                self.mouse_event("button_press_event", press_x_px, value_f,
                                 MouseButton.LEFT, double_click_b=True)
                self.left_release(press_x_px, value_f)
                self.assertEqual(self.plot_widget.time_range_tuple(),
                                 (3.0, 5.0))
                self.assertFalse(self.plot_widget.panning_b)
        self.assertEqual(self.range_list, [])
        self.assertEqual(self.plot_widget.pinned_tip_count(), 0)
        self.assertEqual(self.plot_widget.hover_tip_text(), "")
        self.assert_nothing_else_happened()

    @covers("LLFR-00356")
    def test_press_outside_the_drawing_area_does_not_pan(self) -> None:
        """A press left of the axes (on the tick labels) starts nothing.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_to(3.0, 5.0)
        box = self.plot_widget.axes.bbox
        middle_y_px = (box.y0 + box.y1) / 2.0
        self.send_display("button_press_event", box.x0 - 15.0, middle_y_px)
        self.assertFalse(self.plot_widget.panning_b)
        self.send_display("motion_notify_event", box.x0 + 100.0,
                          middle_y_px, left_b=False)
        self.send_display("button_release_event", box.x0 + 100.0,
                          middle_y_px)
        self.assertEqual(self.plot_widget.time_range_tuple(), (3.0, 5.0))
        self.assertEqual(self.range_list, [])

    @covers("LLFR-00356", "LLFR-00079")
    def test_left_drag_pans_only_with_the_pan_tool(self) -> None:
        """With no tool or the Data tip tool a left drag does not pan;
        leaving the Pan tool during a drag ends the pan.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (NO_TOOL_STR, TIP_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.zoom_to(3.0, 5.0)
                self.left_press(self.display_x_px(4.0), 0.9)
                self.assertFalse(self.plot_widget.panning_b)
                self.move(self.display_x_px(4.5), 0.9)
                self.left_release(self.display_x_px(4.5), 0.9)
                self.assertEqual(self.plot_widget.time_range_tuple(),
                                 (3.0, 5.0))
        self.plot_widget.set_plot_tool(PAN_TOOL_STR)
        self.zoom_to(3.0, 5.0)
        self.left_press(self.display_x_px(4.0))
        self.assertTrue(self.plot_widget.panning_b)
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.assertFalse(self.plot_widget.panning_b)
        self.move(self.display_x_px(4.5))
        self.assertEqual(self.plot_widget.time_range_tuple(), (3.0, 5.0))

    @covers("LLFR-00356", "LLFR-00117")
    def test_wheel_button_pan_still_works_with_the_pan_tool(self) -> None:
        """The wheel button pans as before while the Pan tool is active,
        and a left press during it does not start a second pan.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_to(3.0, 5.0)
        self.middle_press(self.display_x_px(4.0))
        self.assertTrue(self.plot_widget.panning_b)
        self.left_press(self.display_x_px(4.0))
        target_x_px = self.display_x_px(4.5)
        self.move(target_x_px)
        self.middle_release(target_x_px)
        self.assertFalse(self.plot_widget.panning_b)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 2.5, delta=PIXEL_TOLERANCE_S)
        self.assertAlmostEqual(end_s - start_s, 2.0)

    @covers("LLFR-00207", "LLFR-00356")
    def test_pan_is_a_drag_in_progress(self) -> None:
        """From the left press to the release the plot reports a mouse
        drag, so the Z key does nothing.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_to(3.0, 5.0)
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        self.left_press(self.display_x_px(4.0))
        self.assertTrue(self.plot_widget.is_mouse_drag_in_progress())
        self.move(self.display_x_px(4.3))
        self.assertTrue(self.plot_widget.is_mouse_drag_in_progress())
        self.left_release(self.display_x_px(4.3))
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())

    @covers("LLFR-00357", "LLFR-00153", "LLFR-00152")
    def test_press_on_a_pinned_tip_moves_it_and_does_not_pan(self) -> None:
        """A left press on a pinned tip's label drags the label.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_to(3.0, 7.0)
        ramp_value_f = 5.0 * 0.1 + 3.0
        self.plot_widget.set_pinned_tips([("Ramp", 5.0, ramp_value_f)])
        self.draw()
        center_x_px, center_y_px = self.plot_widget.tip_label_center_tuple(0)
        self.send_display("button_press_event", center_x_px, center_y_px)
        self.assertFalse(self.plot_widget.panning_b)
        self.assertNotEqual(self.plot_widget.drag_tip_index_i, -1)
        self.send_display("motion_notify_event", center_x_px - 60.0,
                          center_y_px - 30.0, left_b=False)
        self.send_display("button_release_event", center_x_px - 60.0,
                          center_y_px - 30.0)
        self.application.processEvents()
        self.assertEqual(self.plot_widget.time_range_tuple(), (3.0, 7.0))
        self.assertEqual(self.range_list, [])
        self.assertEqual(len(self.tip_move_list), 1)
        self.assertEqual(self.tip_move_list[0][0], 0)

    @covers("LLFR-00357", "LLFR-00339")
    def test_press_on_a_text_note_moves_it_and_does_not_pan(self) -> None:
        """A left press on a text note drags the note.

        Inputs: none.
        Outputs: none.
        """
        self.zoom_to(3.0, 7.0)
        self.plot_widget.set_text_notes([("Hello", 4.0, 3.0)])
        self.draw()
        box = self.plot_widget.text_note_box_extent(0)
        center_x_px = (box.x0 + box.x1) / 2.0
        center_y_px = (box.y0 + box.y1) / 2.0
        self.send_display("button_press_event", center_x_px, center_y_px)
        self.assertFalse(self.plot_widget.panning_b)
        self.assertNotEqual(self.plot_widget.drag_note_index_i, -1)
        self.send_display("motion_notify_event", center_x_px + 80.0,
                          center_y_px, left_b=False)
        self.send_display("button_release_event", center_x_px + 80.0,
                          center_y_px)
        self.application.processEvents()
        self.assertEqual(self.plot_widget.time_range_tuple(), (3.0, 7.0))
        self.assertEqual(self.range_list, [])
        self.assertEqual(len(self.note_move_list), 1)
        self.assertEqual(self.note_move_list[0][0], 0)
        self.assertGreater(self.note_move_list[0][1], 4.0)

    def drag_pans_and_keeps(self, press_time_s: float,
                            press_value_f: float) -> None:
        """Drag from a point by 0.5 s and check that the plot panned.

        Inputs:
            press_time_s: time of the press.
            press_value_f: y value of the press.
        Outputs: none.
        """
        press_x_px = self.display_x_px(press_time_s)
        self.left_press(press_x_px, press_value_f)
        self.assertTrue(self.plot_widget.panning_b)
        target_x_px = self.display_x_px(press_time_s + 0.5)
        self.move(target_x_px, press_value_f)
        self.left_release(target_x_px, press_value_f)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 2.5, delta=PIXEL_TOLERANCE_S)
        self.assertAlmostEqual(end_s - start_s, 4.0)

    @covers("LLFR-00357", "LLFR-00086")
    def test_press_on_a_vertical_marker_pans(self) -> None:
        """A press on a marker pans and leaves the marker in place.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_markers([(1, "Flag 1", 4.0)])
        self.zoom_to(3.0, 7.0)
        self.assertEqual(self.plot_widget.marker_at(self.point_at(4.0, 0.5)),
                         1)
        self.drag_pans_and_keeps(4.0, 0.5)
        self.assertEqual(self.plot_widget.marker_time_s(1), 4.0)
        self.assert_nothing_else_happened()

    @covers("LLFR-00357", "LLFR-00163")
    def test_press_on_a_delta_marker_pans(self) -> None:
        """A press on a delta marker's dot pans, picks no point.

        Inputs: none.
        Outputs: none.
        """
        first_tuple = ("Ramp", 4.0, 3.4)
        second_tuple = ("Ramp", 5.0, 3.5)
        self.plot_widget.set_delta_markers(
            [(5, DELTA_X_KIND_STR, first_tuple, second_tuple, 1.0)])
        self.zoom_to(3.0, 7.0)
        self.assertEqual(
            self.plot_widget.delta_marker_at(self.point_at(5.0, 3.5)), 5)
        self.drag_pans_and_keeps(5.0, 3.5)
        self.assertEqual(self.plot_widget.delta_marker_id_list(), [5])
        self.assert_nothing_else_happened()

    @covers("LLFR-00357", "LLFR-00318")
    def test_press_inside_an_area_pans(self) -> None:
        """A press inside an area, and on its edge, pans and neither
        moves nor resizes the area.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_areas([(1, "Area 1", 4.0, 6.0)])
        for press_time_s in (5.0, 4.0):
            with self.subTest(press=press_time_s):
                self.zoom_to(3.0, 7.0)
                self.assertEqual(self.plot_widget.area_at(
                    self.point_at(press_time_s + 0.01, 0.5)), 1)
                self.drag_pans_and_keeps(press_time_s, 0.5)
                self.assertEqual(
                    self.plot_widget.area_data_list[0][2:4], (4.0, 6.0))
        self.assert_nothing_else_happened()


@requires_qt
class PanFrequencyPlotTest(unittest.TestCase):
    """A left drag with the Pan tool on a frequency plot alone."""

    @covers("LLFR-00356", "LLFR-00258", "LLFR-00118", "LLFR-00119")
    def test_left_drag_stays_in_the_frequency_range(self) -> None:
        """A left drag pans a zoomed frequency plot within 0 Hz to its
        highest frequency, and does nothing at its whole range.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        from model.workspace import FREQUENCY_PLOT_KIND_STR
        from view.plot_widget import PlotWidget
        application = get_qt_application()
        plot_widget = PlotWidget(3, kind_str=FREQUENCY_PLOT_KIND_STR)
        self.addCleanup(plot_widget.deleteLater)
        self.addCleanup(plot_widget.close)
        plot_widget.resize(600, 400)
        plot_widget.show()
        application.processEvents()
        frequency_array = np.linspace(0.0, 25.0, 251)
        plot_widget.set_curves([("fft_Speed", frequency_array,
                                 np.exp(-(frequency_array - 2.0) ** 2),
                                 "#0000ff", 1)])
        plot_widget.set_plot_tool(PAN_TOOL_STR)
        application.processEvents()
        plot_widget.canvas.draw()
        range_list = recorder(plot_widget.time_range_changed)
        start_point = plot_widget.data_to_widget_point(12.5, 0.5)
        plot_widget.press_at(start_point)
        self.assertTrue(plot_widget.panning_b)
        plot_widget.pan_to(QPoint(start_point.x() + 50, start_point.y()))
        plot_widget.pan_release_at(QPoint(start_point.x() + 50,
                                          start_point.y()))
        self.assertEqual(range_list, [])
        plot_widget.set_time_range(10.0, 15.0)
        application.processEvents()
        plot_widget.canvas.draw()
        # The y-axis now fits the low tail of the curve: press at its
        # middle, inside the drawing area.
        middle_value_f = sum(plot_widget.axes.get_ylim()) / 2.0
        start_point = plot_widget.data_to_widget_point(12.5, middle_value_f)
        plot_widget.press_at(start_point)
        plot_widget.pan_to(QPoint(start_point.x() + 5000, start_point.y()))
        plot_widget.pan_release_at(QPoint(start_point.x() + 5000,
                                          start_point.y()))
        self.assertAlmostEqual(range_list[-1][0], 0.0)
        self.assertAlmostEqual(range_list[-1][1], 5.0)


@requires_qt
class PanEndToEndTest(unittest.TestCase):
    """The Pan button and tool in the main window with a real file."""

    def setUp(self) -> None:
        """Create the window and the controllers and open a sine file.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.message_box_class = QMessageBox
        temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_folder.cleanup)
        path_str = os.path.join(temporary_folder.name, "sine.csv")
        with open(path_str, "w", encoding="utf-8") as data_file:
            data_file.write("Time,Speed,Torque\n")
            for index_i in range(SAMPLE_COUNT_I):
                time_s = index_i / SAMPLE_RATE_HZ
                speed_f = SINE_AMPLITUDE_F * np.sin(
                    2.0 * np.pi * SINE_FREQUENCY_HZ * time_s)
                data_file.write(f"{time_s:.2f},{speed_f:.9f},{index_i}\n")
        self.main_window = MainWindow()
        self.main_window.resize(1000, 800)
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.main_window.show()
        self.application.processEvents()
        self.box_record_list = []
        box_patch = mock.patch.object(
            QMessageBox, "exec",
            new=lambda box: self.box_record_list.append(box.text()) or 0)
        box_patch.start()
        self.addCleanup(box_patch.stop)
        self.top_panel = self.main_window.top_panel
        self.panel = self.main_window.signal_list_panel
        with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                        return_value=path_str):
            self.main_window._on_open_file_activated()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def double_click(self, name_str: str):
        """Double-click a signal name and return the new plot widget.

        Inputs:
            name_str: the signal name.
        Outputs: the PlotWidget of the last plot of the current tab.
        """
        self.panel.signal_double_clicked.emit(name_str)
        self.application.processEvents()
        plot_panel = self.main_window.plot_panel
        plot_id_list = plot_panel.plot_id_list(plot_panel.current_tab_id())
        plot_widget = plot_panel.plot_view(plot_id_list[-1])
        plot_widget.canvas.draw()
        return plot_widget

    def create_fft(self) -> str:
        """Create the FFT of Speed through the signal list menu.

        Inputs: none.
        Outputs: the name of the FFT signal.
        """
        from PyQt6.QtCore import QPoint
        self.panel.execute_menu = lambda menu, point: find_action(
            menu, "FFT (fft)")
        self.panel.show_signal_menu("Speed", QPoint(0, 0))
        self.application.processEvents()
        return self.panel.signal_name_list()[-1]

    def left_drag(self, plot_widget, start_tuple: tuple,
                  end_tuple: tuple, before_release=None) -> None:
        """Drag with the left button between two data points.

        Inputs:
            plot_widget: the PlotWidget.
            start_tuple: (x value, y value) of the press.
            end_tuple: (x value, y value) of the move and release.
            before_release: optional function called before the release.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton, MouseEvent
        canvas = plot_widget.canvas
        start_px = plot_widget.axes.transData.transform(start_tuple)
        end_px = plot_widget.axes.transData.transform(end_tuple)
        for name_str, point_px, button in (
                ("button_press_event", start_px, MouseButton.LEFT),
                ("motion_notify_event", end_px, None)):
            canvas.callbacks.process(name_str, MouseEvent(
                name_str, canvas, float(point_px[0]), float(point_px[1]),
                button=button))
        if before_release is not None:
            before_release()
        canvas.callbacks.process("button_release_event", MouseEvent(
            "button_release_event", canvas, float(end_px[0]),
            float(end_px[1]), button=MouseButton.LEFT))
        self.application.processEvents()

    @covers("LLFR-00355", "LLFR-00356", "LLFR-00258", "LLFR-00070",
            "LLFR-00109", "LLFR-00079")
    def test_pan_moves_all_time_plots_and_one_frequency_plot(self) -> None:
        """With the Pan button active, a left drag on a time plot pans
        every time plot and not the frequency plot; a drag on the
        frequency plot pans only it; the button stays active.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        time_widget = self.double_click("Torque")
        other_time_widget = self.double_click("Speed")
        frequency_widget = self.double_click(fft_name_str)
        self.assertTrue(frequency_widget.frequency_plot_b)
        self.top_panel.zoom_button.click()
        self.top_panel.pan_button.click()
        self.application.processEvents()
        self.assertTrue(self.top_panel.pan_button.is_active())
        self.assertFalse(self.top_panel.zoom_button.is_active())
        self.assertEqual(self.top_panel.active_plot_tool(), PAN_TOOL_STR)
        for plot_widget in (time_widget, other_time_widget,
                            frequency_widget):
            self.assertEqual(plot_widget.plot_tool_str, PAN_TOOL_STR)
        # Zoom the time plots and the frequency plot first.
        time_widget.wheel_at(time_widget.data_to_widget_point(5.0, 0.0),
                             10.0)
        frequency_widget.wheel_at(
            frequency_widget.data_to_widget_point(12.0, 0.0), 10.0)
        self.application.processEvents()
        for plot_widget in (time_widget, other_time_widget,
                            frequency_widget):
            plot_widget.canvas.draw()
        time_range_tuple = time_widget.time_range_tuple()
        frequency_range_tuple = frequency_widget.time_range_tuple()
        time_width_s = time_range_tuple[1] - time_range_tuple[0]
        # A drag on a time plot: every time plot follows.
        self.left_drag(time_widget, (5.0, 250.0),
                       (5.0 + time_width_s / 4.0, 250.0))
        panned_tuple = time_widget.time_range_tuple()
        self.assertAlmostEqual(panned_tuple[0],
                               time_range_tuple[0] - time_width_s / 4.0,
                               delta=time_width_s / 50.0)
        self.assertAlmostEqual(panned_tuple[1] - panned_tuple[0],
                               time_width_s)
        self.assertEqual(other_time_widget.time_range_tuple(), panned_tuple)
        self.assertEqual(frequency_widget.time_range_tuple(),
                         frequency_range_tuple)
        # A drag on the frequency plot: only it moves.
        frequency_width_hz = (frequency_range_tuple[1]
                              - frequency_range_tuple[0])
        frequency_widget.canvas.draw()
        # The y-axis fits the curve in the zoomed range: press at its
        # middle, inside the drawing area.
        middle_value_f = sum(frequency_widget.axes.get_ylim()) / 2.0
        self.left_drag(frequency_widget, (12.0, middle_value_f),
                       (12.0 - frequency_width_hz / 4.0, middle_value_f))
        moved_tuple = frequency_widget.time_range_tuple()
        self.assertAlmostEqual(
            moved_tuple[0], frequency_range_tuple[0]
            + frequency_width_hz / 4.0, delta=frequency_width_hz / 50.0)
        self.assertEqual(time_widget.time_range_tuple(), panned_tuple)
        self.assertEqual(other_time_widget.time_range_tuple(), panned_tuple)
        # LLFR-00109: still active after the pans.
        self.assertTrue(self.top_panel.pan_button.is_active())
        self.assertEqual(self.box_record_list, [])

    @covers("LLFR-00207", "LLFR-00356")
    def test_z_key_does_nothing_during_a_pan(self) -> None:
        """While the left button pans, the Z key resets nothing; after
        the release it resets the zoom again.

        Inputs: none.
        Outputs: none.
        """
        time_widget = self.double_click("Torque")
        self.top_panel.pan_button.click()
        time_widget.wheel_at(time_widget.data_to_widget_point(5.0, 0.0),
                             10.0)
        self.application.processEvents()
        time_widget.canvas.draw()
        start_s, end_s = time_widget.time_range_tuple()
        width_s = end_s - start_s
        reset_list = []

        def press_z_during_drag() -> None:
            """Press Z while the button is held.

            Inputs: none.
            Outputs: none.
            """
            reset_list.append(self.main_window.is_mouse_drag_in_progress())
            self.main_window.on_reset_zoom_key()
            self.application.processEvents()
            reset_list.append(
                self.top_panel.reset_zoom_button.is_active())
            reset_list.append(time_widget.time_range_tuple())

        self.left_drag(time_widget, (5.0, 250.0),
                       (5.0 + width_s / 4.0, 250.0), press_z_during_drag)
        self.assertTrue(reset_list[0])
        self.assertFalse(reset_list[1])
        self.assertAlmostEqual(reset_list[2][1] - reset_list[2][0], width_s)
        self.assertFalse(self.main_window.is_mouse_drag_in_progress())
        self.main_window.on_reset_zoom_key()
        self.application.processEvents()
        self.assertEqual(time_widget.time_range_tuple(), (0.0, 9.98))


@requires_qt
class PanButtonTest(unittest.TestCase):
    """LLFR-00355: the Pan button of the top panel."""

    def setUp(self) -> None:
        """Create and show a top panel.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.top_panel import TopPanel
        self.top_panel = TopPanel()
        self.top_panel.resize(1100, 40)
        self.top_panel.show()
        self.application.processEvents()
        self.change_list = recorder(self.top_panel.plot_tool_changed)

    def tearDown(self) -> None:
        """Close the panel.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.close()
        self.top_panel.deleteLater()
        self.application.processEvents()

    @covers("LLFR-00355", "LLFR-00347", "LLFR-00348", "LLFR-00158",
            "LLFR-00159")
    def test_pan_button_between_zoom_and_marker(self) -> None:
        """"Pan" is the toggle button joined between Zoom and Vertical
        marker, showing only the open hand icon.

        Inputs: none.
        Outputs: none.
        """
        from view import icon_shapes
        from view.toggle_button import ToggleButton
        from view.action_button import ActionButton
        pan_button = self.top_panel.pan_button
        self.assertIsInstance(pan_button, ToggleButton)
        self.assertNotIsInstance(pan_button, ActionButton)
        self.assertEqual(button_name(pan_button), "Pan")
        self.assertEqual(pan_button.text(), "")
        self.assertEqual(pan_button.icon_name_str, icon_shapes.PAN_ICON_STR)
        self.assertFalse(pan_button.icon().isNull())
        self.assertIs(self.top_panel.plot_tool_button_dict[PAN_TOOL_STR],
                      pan_button)
        button_list = self.top_panel.button_list()
        pan_index_i = button_list.index(pan_button)
        self.assertIs(button_list[pan_index_i - 1],
                      self.top_panel.zoom_button)
        self.assertIs(button_list[pan_index_i + 1],
                      self.top_panel.marker_button)
        self.assertEqual(self.top_panel.zoom_button.geometry().right() + 1,
                         pan_button.x())
        self.assertEqual(pan_button.geometry().right() + 1,
                         self.top_panel.marker_button.x())
        self.assertFalse(pan_button.is_active())

    @covers("LLFR-00215", "LLFR-00214", "LLFR-00213", "LLFR-00181")
    def test_pan_button_tip_on_both_systems(self) -> None:
        """The tip shows "Pan" and "Drag on a plot to pan" in a paler
        color, on macOS and on Windows.

        Inputs: none.
        Outputs: none.
        """
        from view import theme, top_panel
        for macos_b in (True, False):
            with self.subTest(macos=macos_b):
                tip_str = top_panel.button_tip_text_str("Pan", macos_b)
                self.assertIn(">Pan</div>", tip_str)
                self.assertIn(
                    f'color:{theme.TOOLTIP_DETAIL_COLOR_STR}">'
                    f'{PAN_TIP_LINE_STR}</div>', tip_str)
                self.assertEqual(
                    top_panel.button_tip_detail_list("Pan", macos_b),
                    [PAN_TIP_LINE_STR])
        self.assertEqual(button_tip_line_list(self.top_panel.pan_button),
                         ["Pan", PAN_TIP_LINE_STR])

    @covers("LLFR-00079", "LLFR-00109", "LLFR-00002", "LLFR-00001",
            "LLFR-00355")
    def test_pan_is_exclusive_and_stays_active(self) -> None:
        """Pan deactivates the other tools, is deactivated by them, and
        stays active until clicked again.

        Inputs: none.
        Outputs: none.
        """
        pan_button = self.top_panel.pan_button
        for other_tool_str in PLOT_TOOL_TUPLE:
            if other_tool_str == PAN_TOOL_STR:
                continue
            with self.subTest(other=other_tool_str):
                other_button = self.top_panel.plot_tool_button_dict[
                    other_tool_str]
                other_button.click()
                pan_button.click()
                self.assertTrue(pan_button.is_active())
                self.assertFalse(other_button.is_active())
                self.assertEqual(self.top_panel.active_plot_tool(),
                                 PAN_TOOL_STR)
                self.application.processEvents()
                time.sleep(0.05)
                self.application.processEvents()
                self.assertTrue(pan_button.is_active())
                other_button.click()
                self.assertFalse(pan_button.is_active())
                other_button.click()
        self.change_list.clear()
        pan_button.click()
        pan_button.click()
        self.assertEqual(self.change_list,
                         [(PAN_TOOL_STR,), (NO_TOOL_STR,)])
        self.assertFalse(pan_button.is_active())


if __name__ == "__main__":
    unittest.main()
