"""Tests for the vertical markers in the plot (HLFR-00028 to 00031).

The plot widget tests drive the same matplotlib callbacks that real
mouse events reach (button press, motion, release) and replace
``execute_menu`` so no modal menu is ever opened. The end-to-end test
uses a real MainWindow and MainController with patched dialogs.
"""

import os
import tempfile
import unittest
from unittest import mock

import numpy as np

from tests.support import covers, get_qt_application, requires_qt

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, PLOT_TOOL_TUPLE, TIP_TOOL_STR,
    ZOOM_TOOL_STR)
from model.curve_colors import MARKER_COLOR_STR, PALETTE_COLOR_TUPLE

WIDGET_WIDTH_I = 600
WIDGET_HEIGHT_I = 400
RED_STR = "#ff0000"
BLUE_STR = "#0000ff"
LEFT_BUTTON_I = 1
RIGHT_BUTTON_I = 3
# Display pixels allowed between where an item is and where it should be.
POSITION_TOLERANCE_PX_F = 2.0
# How far (display pixels) the label may sit below the top of the axes.
LABEL_TOP_GAP_PX_F = 20.0
# How far (display pixels) the time text may sit below the label.
TIME_GAP_PX_F = 12.0
FILE_TEXT_STR = (
    "Time,speed,force\n"
    "0,0,1\n0.5,1,0\n1,2,-1\n1.5,3,0\n2,4,1\n")


def recorder(signal) -> list:
    """Connect a Qt signal to a slot that records its arguments.

    Inputs:
        signal: a bound pyqtSignal.
    Outputs: the list that receives one tuple of arguments per emission.
    """
    record_list = []
    signal.connect(lambda *argument_tuple: record_list.append(argument_tuple))
    return record_list


def all_menu_actions(menu) -> list:
    """Return the actions of a menu and of its submenus.

    Inputs:
        menu: a QMenu.
    Outputs: a list of QAction.
    """
    action_list = list(menu.actions())
    for action in list(action_list):
        if action.menu() is not None:
            action_list.extend(action.menu().actions())
    return action_list


def send_mouse_event(plot_widget, event_name_str: str, display_x_px: float,
                     display_y_px: float, button_i: int,
                     double_click_b: bool = False) -> None:
    """Send a matplotlib mouse event to the canvas of a plot widget.

    Inputs:
        plot_widget: the PlotWidget.
        event_name_str: "button_press_event", "motion_notify_event" or
            "button_release_event".
        display_x_px: x in display pixels.
        display_y_px: y in display pixels.
        button_i: matplotlib button number (1 left, 3 right).
        double_click_b: True for the second press of a double-click.
    Outputs: none.
    """
    from matplotlib.backend_bases import MouseEvent
    mouse_event = MouseEvent(event_name_str, plot_widget.canvas,
                             display_x_px, display_y_px, button=button_i,
                             dblclick=double_click_b)
    plot_widget.canvas.callbacks.process(event_name_str, mouse_event)


@requires_qt
class MarkerWidgetTestCase(unittest.TestCase):
    """Base class: a shown 600x400 plot widget with a sine and a ramp."""

    def setUp(self) -> None:
        """Create, size and show the plot widget and draw two curves.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.plot_widget import PlotWidget
        self.plot_widget = PlotWidget(4)
        self.plot_widget.resize(WIDGET_WIDTH_I, WIDGET_HEIGHT_I)
        self.plot_widget.show()
        self.application.processEvents()
        self.time_array = np.linspace(0.0, 10.0, 101)
        self.sine_array = np.sin(self.time_array)
        self.ramp_array = self.time_array * 0.1 + 3.0
        self.plot_widget.set_curves([
            ("Sine", self.time_array, self.sine_array, RED_STR, 1),
            ("Ramp", self.time_array, self.ramp_array, BLUE_STR, 1)])
        self.draw()
        self.place_list = recorder(self.plot_widget.marker_place_requested)
        self.move_list = recorder(self.plot_widget.marker_move_requested)
        self.rename_list = recorder(
            self.plot_widget.marker_rename_requested)
        self.delete_list = recorder(
            self.plot_widget.marker_delete_requested)
        self.range_list = recorder(self.plot_widget.time_range_changed)
        self.pin_list = recorder(self.plot_widget.tip_pin_requested)

    def tearDown(self) -> None:
        """Close and delete the plot widget, unless a test deleted it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6 import sip
        self.application.processEvents()
        if sip.isdeleted(self.plot_widget):
            return
        self.plot_widget.close()
        self.plot_widget.deleteLater()
        self.application.processEvents()

    def draw(self) -> None:
        """Process events and draw the canvas so coordinates are final.

        Inputs: none.
        Outputs: none.
        """
        self.application.processEvents()
        self.plot_widget.canvas.draw()

    def renderer(self):
        """Return the canvas renderer used for text extents.

        Inputs: none.
        Outputs: the matplotlib renderer.
        """
        return self.plot_widget.canvas.get_renderer()

    def display_tuple(self, time_s: float, value_f: float) -> tuple:
        """Return the display pixels of a data point.

        Inputs:
            time_s: x value in seconds.
            value_f: y value.
        Outputs: a tuple (x, y) in display pixels.
        """
        display_x_px, display_y_px = (
            self.plot_widget.axes.transData.transform((time_s, value_f)))
        return (float(display_x_px), float(display_y_px))

    def mouse(self, event_name_str: str, time_s: float, value_f: float,
              button_i: int = LEFT_BUTTON_I,
              double_click_b: bool = False) -> None:
        """Send a mouse event at a data point.

        Inputs:
            event_name_str: the matplotlib event name.
            time_s: x value in seconds.
            value_f: y value.
            button_i: matplotlib button number.
            double_click_b: True for the second press of a double-click.
        Outputs: none.
        """
        display_x_px, display_y_px = self.display_tuple(time_s, value_f)
        send_mouse_event(self.plot_widget, event_name_str, display_x_px,
                         display_y_px, button_i, double_click_b)

    def set_markers(self, marker_data_list: list) -> None:
        """Draw markers in the widget and the canvas.

        Inputs:
            marker_data_list: tuples (marker_id_i, name_str, time_s).
        Outputs: none.
        """
        self.plot_widget.set_markers(marker_data_list)
        self.draw()

    def choose_action_text(self, text_str: str) -> list:
        """Make the menu return the action with a text instead of blocking.

        Inputs:
            text_str: text of the action to choose ("" for none).
        Outputs: a list that receives the texts of every shown menu's
            top-level actions.
        """
        shown_list = []

        def fake_execute_menu(menu, global_point):
            """Record the menu and return the chosen action.

            Inputs:
                menu: the QMenu that would be shown.
                global_point: QPoint in screen coordinates.
            Outputs: the matching QAction, or None.
            """
            shown_list.append([action.text() for action in menu.actions()
                               if not action.isSeparator()])
            for action in all_menu_actions(menu):
                if action.text() == text_str and action.menu() is None:
                    return action
            return None

        self.plot_widget.execute_menu = fake_execute_menu
        return shown_list

    def right_click(self, time_s: float, value_f: float) -> None:
        """Right-press at a data point and let the deferred menu run.

        Inputs:
            time_s: x value in seconds.
            value_f: y value.
        Outputs: none.
        """
        self.mouse("button_press_event", time_s, value_f, RIGHT_BUTTON_I)
        for _ in range(3):
            self.application.processEvents()

    def menu_texts_at(self, time_s: float, value_f: float) -> list:
        """Return the top-level texts of the menu built at a data point.

        Inputs:
            time_s: x value in seconds.
            value_f: y value.
        Outputs: a list of action texts.
        """
        from PyQt6 import sip
        menu = self.plot_widget.build_context_menu(
            self.plot_widget.data_to_widget_point(time_s, value_f))
        text_list = [action.text() for action in menu.actions()
                     if not action.isSeparator()]
        sip.delete(menu)
        return text_list


class MarkerDrawingTest(MarkerWidgetTestCase):
    """Line, color, label and time of a marker."""

    def assert_line_covers_y_range(self, marker_id_i: int) -> None:
        """Check that a marker line spans the whole axes height.

        Inputs:
            marker_id_i: id of the marker.
        Outputs: none.
        """
        line = self.plot_widget.marker_artist_tuple(marker_id_i)[0]
        self.assertTrue(line.get_visible())
        self.assertEqual(list(line.get_ydata()), [0, 1])
        self.assertEqual(line.get_transform(),
                         self.plot_widget.axes.get_xaxis_transform())
        line_box = line.get_window_extent(self.renderer())
        axes_box = self.plot_widget.axes.bbox
        self.assertAlmostEqual(line_box.y0, axes_box.y0,
                               delta=POSITION_TOLERANCE_PX_F)
        self.assertAlmostEqual(line_box.y1, axes_box.y1,
                               delta=POSITION_TOLERANCE_PX_F)

    @covers("LLFR-00082")
    def test_line_covers_y_range_at_any_zoom(self) -> None:
        """The line spans the y range before and after zooms.

        Inputs: none.
        Outputs: none.
        """
        self.set_markers([(1, "Marker 1", 4.0)])
        self.assertEqual(self.plot_widget.marker_count(), 1)
        self.assert_line_covers_y_range(1)
        full_ylim_tuple = self.plot_widget.axes.get_ylim()
        # Zoom where only the sine is in view; the y range changes.
        for start_s, end_s in ((3.5, 4.5), (3.9, 4.1), (0.0, 10.0)):
            with self.subTest(range=(start_s, end_s)):
                self.plot_widget.set_time_range(start_s, end_s)
                self.draw()
                self.assert_line_covers_y_range(1)
        self.plot_widget.set_time_range(3.9, 4.1)
        self.draw()
        self.assertNotEqual(self.plot_widget.axes.get_ylim(),
                            full_ylim_tuple)
        # The wheel zoom also keeps the full height.
        self.plot_widget.wheel_at(
            self.plot_widget.data_to_widget_point(4.0, 0.0), -3.0)
        self.draw()
        self.assert_line_covers_y_range(1)

    @covers("LLFR-00083", "LLFR-00033")
    def test_marker_color_is_reserved(self) -> None:
        """Line, label and time use the marker color, no curve color.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_hex
        self.set_markers([(1, "Marker 1", 4.0)])
        line, label, time_text = self.plot_widget.marker_artist_tuple(1)
        for artist_color in (line.get_color(), label.get_color(),
                             time_text.get_color()):
            self.assertEqual(to_hex(artist_color), MARKER_COLOR_STR)
        self.assertNotIn(MARKER_COLOR_STR, PALETTE_COLOR_TUPLE)
        curve_color_set = {to_hex(curve_line.get_color()) for curve_line
                           in self.plot_widget.curve_line_dict.values()}
        self.assertNotIn(MARKER_COLOR_STR, curve_color_set)

    @covers("LLFR-00084", "LLFR-00092")
    def test_label_at_top_and_time_below(self) -> None:
        """The name is at the top of the line, the time directly below.

        Inputs: none.
        Outputs: none.
        """
        self.set_markers([(1, "Marker 1", 2.0), (2, "End", 8.0)])
        self.assertEqual(self.plot_widget.marker_label_text(1), "Marker 1")
        self.assertEqual(self.plot_widget.marker_time_text(1), "t = 2 s")
        self.assertEqual(self.plot_widget.marker_label_text(2), "End")
        self.assertEqual(self.plot_widget.marker_time_text(2), "t = 8 s")
        axes_box = self.plot_widget.axes.bbox
        for marker_id_i, time_s in ((1, 2.0), (2, 8.0)):
            with self.subTest(marker=marker_id_i):
                _, label, time_text = (
                    self.plot_widget.marker_artist_tuple(marker_id_i))
                label_box = label.get_window_extent(self.renderer())
                time_box = time_text.get_window_extent(self.renderer())
                line_x_px = self.display_tuple(time_s, 0.0)[0]
                # Label: inside the axes, at their top.
                self.assertLessEqual(label_box.y1, axes_box.y1)
                self.assertGreaterEqual(label_box.y1,
                                        axes_box.y1 - LABEL_TOP_GAP_PX_F)
                # Time: directly below the label.
                self.assertLessEqual(time_box.y1, label_box.y0)
                self.assertGreaterEqual(time_box.y1,
                                        label_box.y0 - TIME_GAP_PX_F)
                # Both beside the line, inside the axes.
                for text_box in (label_box, time_box):
                    self.assertGreaterEqual(text_box.x0, axes_box.x0)
                    self.assertLessEqual(text_box.x1, axes_box.x1)
                    self.assertLessEqual(
                        min(abs(text_box.x0 - line_x_px),
                            abs(text_box.x1 - line_x_px)),
                        LABEL_TOP_GAP_PX_F)

    @covers("LLFR-00084", "LLFR-00092")
    def test_texts_follow_the_marker_when_the_range_changes(self) -> None:
        """After a zoom the texts move with the line; hidden off range.

        Inputs: none.
        Outputs: none.
        """
        self.set_markers([(1, "Marker 1", 4.0), (2, "Marker 2", 7.0)])
        self.plot_widget.set_time_range(3.0, 6.0)
        self.draw()
        line, label, time_text = self.plot_widget.marker_artist_tuple(1)
        label_box = label.get_window_extent(self.renderer())
        line_x_px = self.display_tuple(4.0, 0.0)[0]
        self.assertLessEqual(min(abs(label_box.x0 - line_x_px),
                                 abs(label_box.x1 - line_x_px)),
                             LABEL_TOP_GAP_PX_F)
        self.assertTrue(label.get_visible())
        # Marker 2 is outside the shown range: not drawn.
        for artist in self.plot_widget.marker_artist_tuple(2):
            self.assertFalse(artist.get_visible())
        self.plot_widget.set_time_range(0.0, 10.0)
        self.draw()
        for artist in self.plot_widget.marker_artist_tuple(2):
            self.assertTrue(artist.get_visible())

    @covers("LLFR-00084", "LLFR-00112")
    def test_names_are_shown_literally(self) -> None:
        """Names with mathtext characters are drawn as typed.

        Inputs: none.
        Outputs: none.
        """
        name_str = "$x_1$ & 50% {a}"
        self.set_markers([(5, name_str, 1.0)])
        _, label, time_text = self.plot_widget.marker_artist_tuple(5)
        self.assertEqual(self.plot_widget.marker_label_text(5), name_str)
        self.assertFalse(label.get_parse_math())
        self.assertFalse(time_text.get_parse_math())

    @covers("LLFR-00081", "LLFR-00091", "LLFR-00112")
    def test_set_markers_replaces_and_survives_set_curves(self) -> None:
        """set_markers draws exactly its list; set_curves keeps them.

        Inputs: none.
        Outputs: none.
        """
        self.set_markers([(1, "Marker 1", 2.0), (2, "Marker 2", 3.0)])
        self.assertEqual(self.plot_widget.marker_count(), 2)
        self.set_markers([(2, "Renamed", 3.0)])
        self.assertEqual(self.plot_widget.marker_count(), 1)
        self.assertEqual(self.plot_widget.marker_label_text(1), "")
        self.assertEqual(self.plot_widget.marker_label_text(2), "Renamed")
        self.plot_widget.set_curves([
            ("Sine", self.time_array, self.sine_array, RED_STR, 1)])
        self.draw()
        self.assertEqual(self.plot_widget.marker_count(), 1)
        self.assert_line_covers_y_range(2)
        self.set_markers([])
        self.assertEqual(self.plot_widget.marker_count(), 0)
        self.assertEqual(self.plot_widget.marker_artist_dict, {})


class MarkerClickTest(MarkerWidgetTestCase):
    """A left click with the Vertical marker tool places a marker."""

    @covers("LLFR-00081", "LLFR-00109")
    def test_click_places_at_clicked_time(self) -> None:
        """A left press on the axes asks for a marker at its time.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.mouse("button_press_event", 2.5, 0.0)
        self.mouse("button_release_event", 2.5, 0.0)
        self.mouse("button_press_event", 7.5, 3.75)
        self.mouse("button_release_event", 7.5, 3.75)
        self.assertEqual(len(self.place_list), 2)
        self.assertAlmostEqual(self.place_list[0][0], 2.5, delta=0.05)
        self.assertAlmostEqual(self.place_list[1][0], 7.5, delta=0.05)
        # Placing never zooms, pins or changes the tool.
        self.assertEqual(self.range_list, [])
        self.assertEqual(self.pin_list, [])
        self.assertEqual(self.move_list, [])
        self.assertEqual(self.plot_widget.plot_tool_str, MARKER_TOOL_STR)

    @covers("LLFR-00081")
    def test_double_click_places_once(self) -> None:
        """The second press of a double-click places nothing more.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.mouse("button_press_event", 5.0, 0.0)
        self.mouse("button_release_event", 5.0, 0.0)
        self.mouse("button_press_event", 5.0, 0.0, double_click_b=True)
        self.mouse("button_release_event", 5.0, 0.0)
        self.assertEqual(len(self.place_list), 1)

    @covers("LLFR-00081", "LLFR-00080")
    def test_click_places_only_with_marker_tool(self) -> None:
        """With Tip, Zoom or no tool, a click places no marker.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (TIP_TOOL_STR, ZOOM_TOOL_STR, NO_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.mouse("button_press_event", 5.0, 2.0)
                self.mouse("button_release_event", 5.0, 2.0)
        self.assertEqual(self.place_list, [])
        # The Zoom tool still zooms (the click did what it did before).
        self.assertEqual(len(self.range_list), 1)

    @covers("LLFR-00081")
    def test_click_on_existing_marker_places_nothing(self) -> None:
        """A click on a marker's line or label places no new marker.

        Inputs: none.
        Outputs: none.
        """
        self.set_markers([(1, "Marker 1", 5.0)])
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        low_f, high_f = self.plot_widget.axes.get_ylim()
        for value_f in (low_f + 0.1 * (high_f - low_f), 2.0, 3.5):
            self.plot_widget.click_at(
                self.plot_widget.data_to_widget_point(5.0, value_f))
        # A few pixels beside the line is still on the line.
        line_x_px, line_y_px = self.display_tuple(5.0, 2.0)
        send_mouse_event(self.plot_widget, "button_press_event",
                         line_x_px + 3.0, line_y_px, LEFT_BUTTON_I)
        send_mouse_event(self.plot_widget, "button_release_event",
                         line_x_px + 3.0, line_y_px, LEFT_BUTTON_I)
        # The label is on the marker too.
        _, label, _ = self.plot_widget.marker_artist_tuple(1)
        label_box = label.get_window_extent(self.renderer())
        label_point = self.plot_widget.display_to_widget_point(
            label_box.x1 - 2.0, (label_box.y0 + label_box.y1) / 2.0)
        self.assertEqual(self.plot_widget.marker_at(label_point), 1)
        self.plot_widget.click_at(label_point)
        self.assertEqual(self.place_list, [])
        self.assertEqual(self.move_list, [])
        # Far from the marker, a click places one.
        self.plot_widget.click_at(
            self.plot_widget.data_to_widget_point(8.0, 2.0))
        self.assertEqual(len(self.place_list), 1)

    @covers("LLFR-00081")
    def test_click_outside_axes_places_nothing(self) -> None:
        """A click on the axis labels, outside the axes, does nothing.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.plot_widget.click_at(QPoint(2, WIDGET_HEIGHT_I - 2))
        self.assertEqual(self.place_list, [])


class MarkerDragTest(MarkerWidgetTestCase):
    """Dragging a marker with the Vertical marker tool."""

    def setUp(self) -> None:
        """Draw one marker at t = 4 s and activate the marker tool.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.set_markers([(9, "Marker 1", 4.0)])
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)

    @covers("LLFR-00086", "LLFR-00093")
    def test_drag_follows_mouse_and_reports_once(self) -> None:
        """Line and time follow every move; one request on release.

        Inputs: none.
        Outputs: none.
        """
        self.mouse("button_press_event", 4.0, 2.0)
        shown_time_list = []
        for time_s in (4.5, 5.0, 6.0, 6.5):
            self.mouse("motion_notify_event", time_s, 2.0)
            self.assertAlmostEqual(self.plot_widget.marker_time_s(9),
                                   time_s, delta=0.05)
            time_text_str = self.plot_widget.marker_time_text(9)
            self.assertEqual(
                time_text_str,
                f"t = {self.plot_widget.marker_time_s(9):.6g} s")
            shown_time_list.append(time_text_str)
            # Nothing is requested while dragging.
            self.assertEqual(self.move_list, [])
        self.assertEqual(len(set(shown_time_list)), 4)
        # The label follows the line.
        _, label, _ = self.plot_widget.marker_artist_tuple(9)
        self.assertAlmostEqual(label.xy[0], self.plot_widget.marker_time_s(9))
        self.mouse("button_release_event", 6.5, 2.0)
        self.assertEqual(len(self.move_list), 1)
        marker_id_i, time_s = self.move_list[0]
        self.assertEqual(marker_id_i, 9)
        self.assertAlmostEqual(time_s, 6.5, delta=0.05)
        # No new marker, no zoom, no pin; the tool stays.
        self.assertEqual(self.place_list, [])
        self.assertEqual(self.range_list, [])
        self.assertEqual(self.pin_list, [])
        self.assertEqual(self.plot_widget.plot_tool_str, MARKER_TOOL_STR)
        # Later moves without the button do not drag any more.
        self.mouse("motion_notify_event", 8.0, 2.0)
        self.mouse("button_release_event", 8.0, 2.0)
        self.assertEqual(len(self.move_list), 1)
        self.assertAlmostEqual(self.plot_widget.marker_time_s(9), 6.5,
                               delta=0.05)

    @covers("LLFR-00086")
    def test_press_and_release_without_move_emits_nothing(self) -> None:
        """A press and release on a marker neither moves nor places.

        Inputs: none.
        Outputs: none.
        """
        self.mouse("button_press_event", 4.0, 2.0)
        self.mouse("motion_notify_event", 4.0, 2.0)
        self.mouse("button_release_event", 4.0, 2.0)
        self.assertEqual(self.move_list, [])
        self.assertEqual(self.place_list, [])
        self.assertEqual(self.plot_widget.marker_time_s(9), 4.0)
        self.assertEqual(self.plot_widget.marker_time_text(9), "t = 4 s")

    @covers("LLFR-00086", "LLFR-00093")
    def test_drag_stays_inside_the_shown_range(self) -> None:
        """Dragging past the edge leaves the marker at the edge.

        Inputs: none.
        Outputs: none.
        """
        self.mouse("button_press_event", 4.0, 2.0)
        self.mouse("motion_notify_event", 14.0, 2.0)
        _, end_s = self.plot_widget.time_range_tuple()
        self.assertEqual(self.plot_widget.marker_time_s(9), end_s)
        self.assertEqual(self.plot_widget.marker_time_text(9),
                         f"t = {end_s:.6g} s")
        self.mouse("button_release_event", 14.0, 2.0)
        self.assertEqual(self.move_list, [(9, end_s)])

    @covers("LLFR-00086", "LLFR-00078")
    def test_drag_needs_the_marker_tool(self) -> None:
        """With another tool a press on the marker does not grab it.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (TIP_TOOL_STR, NO_TOOL_STR, ZOOM_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.mouse("button_press_event", 4.0, 2.0)
                self.mouse("motion_notify_event", 6.0, 2.0)
                self.mouse("button_release_event", 6.0, 2.0)
                self.assertEqual(self.plot_widget.marker_time_s(9), 4.0)
        self.assertEqual(self.move_list, [])
        self.assertEqual(self.place_list, [])
        # The Zoom tool zoomed instead.
        self.assertEqual(len(self.range_list), 1)

    @covers("LLFR-00086")
    def test_tool_change_during_drag_cancels_it(self) -> None:
        """Leaving the marker tool mid-drag puts the marker back.

        Inputs: none.
        Outputs: none.
        """
        self.mouse("button_press_event", 4.0, 2.0)
        self.mouse("motion_notify_event", 6.0, 2.0)
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
        self.assertEqual(self.plot_widget.marker_time_s(9), 4.0)
        self.mouse("button_release_event", 6.0, 2.0)
        self.assertEqual(self.move_list, [])

    @covers("LLFR-00086")
    def test_release_slot_may_redraw_the_markers(self) -> None:
        """A slot that redraws the markers on release is safe.

        Inputs: none.
        Outputs: none.
        """
        def redraw(marker_id_i: int, time_s: float) -> None:
            """Redraw the marker at its new time, as the controller does.

            Inputs:
                marker_id_i: id of the moved marker.
                time_s: the new time in seconds.
            Outputs: none.
            """
            self.plot_widget.set_curves(self.plot_widget.curve_data_list)
            self.plot_widget.set_markers([(marker_id_i, "Marker 1",
                                           time_s)])

        self.plot_widget.marker_move_requested.connect(redraw)
        self.mouse("button_press_event", 4.0, 2.0)
        self.mouse("motion_notify_event", 7.0, 2.0)
        self.mouse("button_release_event", 7.0, 2.0)
        self.draw()
        self.assertAlmostEqual(self.plot_widget.marker_time_s(9), 7.0,
                               delta=0.05)
        self.assertEqual(self.plot_widget.marker_count(), 1)


class MarkerMenuTest(MarkerWidgetTestCase):
    """Right-click menu of a marker (Rename, Delete) and its priority."""

    def setUp(self) -> None:
        """Draw a marker at t = 5 s, where the ramp is 3.5.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.set_markers([(3, "Marker 1", 5.0)])

    @covers("LLFR-00110", "LLFR-00087", "LLFR-00090")
    def test_marker_over_curve_shows_marker_menu(self) -> None:
        """Where the marker crosses a curve, the marker menu is shown.

        Inputs: none.
        Outputs: none.
        """
        crossing_point = self.plot_widget.data_to_widget_point(5.0, 3.5)
        self.assertEqual(self.plot_widget.curve_at(crossing_point), "Ramp")
        self.assertEqual(self.plot_widget.marker_at(crossing_point), 3)
        self.assertEqual(self.menu_texts_at(5.0, 3.5), ["Rename", "Delete"])
        self.assertEqual(self.menu_texts_at(5.0, float(np.sin(5.0))),
                         ["Rename", "Delete"])
        # Away from the marker the same curve shows the curve menu.
        self.assertEqual(self.menu_texts_at(8.0, 3.8),
                         ["Delete signal", "Width"])

    @covers("LLFR-00087", "LLFR-00090", "LLFR-00048")
    def test_marker_menu_with_every_tool_and_no_delete_plot(self) -> None:
        """The marker menu is the same with any tool; no "Delete plot".

        Inputs: none.
        Outputs: none.
        """
        for tool_str in PLOT_TOOL_TUPLE + (NO_TOOL_STR,):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                for value_f in (2.0, 3.5):
                    text_list = self.menu_texts_at(5.0, value_f)
                    self.assertEqual(text_list, ["Rename", "Delete"])
                    self.assertNotIn("Delete plot", text_list)
        # An empty area away from the marker still offers "Delete plot".
        self.assertEqual(self.menu_texts_at(8.0, 2.0), ["Delete plot"])

    @covers("LLFR-00048", "LLFR-00087")
    def test_label_shows_marker_menu(self) -> None:
        """A right-click on the label itself shows the marker menu.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6 import sip
        _, label, _ = self.plot_widget.marker_artist_tuple(3)
        label_box = label.get_window_extent(self.renderer())
        label_point = self.plot_widget.display_to_widget_point(
            label_box.x1 - 2.0, (label_box.y0 + label_box.y1) / 2.0)
        menu = self.plot_widget.build_context_menu(label_point)
        self.assertEqual([action.text() for action in menu.actions()],
                         ["Rename", "Delete"])
        sip.delete(menu)

    @covers("LLFR-00087", "LLFR-00088", "LLFR-00090", "LLFR-00091")
    def test_deferred_menu_emits_rename_and_delete(self) -> None:
        """Choosing Rename or Delete emits the request with the id.

        Inputs: none.
        Outputs: none.
        """
        shown_list = self.choose_action_text("Rename")
        self.right_click(5.0, 3.5)
        self.assertEqual(shown_list, [["Rename", "Delete"]])
        self.assertEqual(self.rename_list, [(3,)])
        self.assertEqual(self.delete_list, [])
        self.choose_action_text("Delete")
        self.right_click(5.0, 3.5)
        self.assertEqual(self.delete_list, [(3,)])
        # Closing the menu without a choice emits nothing.
        self.choose_action_text("")
        self.right_click(5.0, 3.5)
        self.assertEqual(self.rename_list, [(3,)])
        self.assertEqual(self.delete_list, [(3,)])

    @covers("LLFR-00090", "LLFR-00091")
    def test_delete_slot_may_delete_widget(self) -> None:
        """A slot that deletes the widget at once on Delete is safe.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6 import sip
        self.choose_action_text("Delete")
        record_list = []

        def delete_widget(marker_id_i: int) -> None:
            """Record the id and delete the plot widget right away.

            Inputs:
                marker_id_i: id of the marker.
            Outputs: none.
            """
            record_list.append(marker_id_i)
            sip.delete(self.plot_widget)

        self.plot_widget.marker_delete_requested.connect(delete_widget)
        self.right_click(5.0, 3.5)
        self.assertEqual(record_list, [3])
        self.assertTrue(sip.isdeleted(self.plot_widget))

    @covers("LLFR-00046", "LLFR-00110")
    def test_pinned_tip_on_top_of_marker_wins(self) -> None:
        """A pinned tip drawn over a marker keeps its own menu.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_pinned_tips([("Ramp", 5.0, 3.5)])
        self.draw()
        self.assertEqual(self.menu_texts_at(5.0, 3.5), ["Delete"])
        # Lower on the line, away from the tip, the marker menu is back.
        self.assertEqual(self.menu_texts_at(5.0, float(np.sin(5.0))),
                         ["Rename", "Delete"])


@requires_qt
class MarkerEndToEndTest(unittest.TestCase):
    """Open a CSV, plot a signal and use the Vertical marker tool."""

    def setUp(self) -> None:
        """Create the window and controllers, open a CSV, plot speed.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QFileDialog
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        path_str = os.path.join(self.temporary_folder.name, "markers.csv")
        with open(path_str, "w", encoding="utf-8") as file:
            file.write(FILE_TEXT_STR)
        self.main_window = MainWindow()
        self.main_window.resize(1100, 800)
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.main_window.show()
        with mock.patch.object(QFileDialog, "getOpenFileName",
                               return_value=(path_str, "")):
            QTest.mouseClick(self.main_window.top_panel.open_file_button,
                             Qt.MouseButton.LeftButton)
            self.process_events()
        self.main_window.signal_double_click_handler("speed")
        self.process_events()
        self.plot_widget = self.only_plot_widget()

    def tearDown(self) -> None:
        """Close the window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.process_events()

    def process_events(self) -> None:
        """Let Qt run deferred work and draw the plots.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(3):
            self.application.processEvents()
        plot_panel = self.main_window.plot_panel
        for plot_widget in plot_panel.plot_widget_dict.values():
            plot_widget.canvas.draw()

    def only_plot_widget(self):
        """Return the single plot widget of the window.

        Inputs: none.
        Outputs: the PlotWidget.
        """
        plot_widget_list = list(
            self.main_window.plot_panel.plot_widget_dict.values())
        self.assertEqual(len(plot_widget_list), 1)
        return plot_widget_list[0]

    def left_click(self, time_s: float, value_f: float) -> None:
        """Press and release the left button at a data point.

        Inputs:
            time_s: x value in seconds.
            value_f: y value.
        Outputs: none.
        """
        display_x_px, display_y_px = (
            self.plot_widget.axes.transData.transform((time_s, value_f)))
        for event_name_str in ("button_press_event", "button_release_event"):
            send_mouse_event(self.plot_widget, event_name_str,
                             float(display_x_px), float(display_y_px),
                             LEFT_BUTTON_I)
        self.process_events()

    def right_click_choose(self, time_s: float, value_f: float,
                           text_str: str) -> list:
        """Right-click at a data point and choose a menu action.

        Inputs:
            time_s: x value in seconds.
            value_f: y value.
            text_str: text of the action to choose.
        Outputs: the texts of the menu that was shown.
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
        display_x_px, display_y_px = (
            self.plot_widget.axes.transData.transform((time_s, value_f)))
        send_mouse_event(self.plot_widget, "button_press_event",
                         float(display_x_px), float(display_y_px),
                         RIGHT_BUTTON_I)
        self.process_events()
        return shown_list

    def drawn_markers(self) -> list:
        """Return the (id, name, time) of the drawn markers.

        Inputs: none.
        Outputs: a list of tuples, in placing order.
        """
        return [(marker_id_i, self.plot_widget.marker_label_text(
            marker_id_i), self.plot_widget.marker_time_s(marker_id_i))
            for marker_id_i in self.plot_widget.marker_id_list()]

    def drawn_names(self) -> list:
        """Return the label texts of the drawn markers.

        Inputs: none.
        Outputs: a list of str, in placing order.
        """
        return [marker_tuple[1] for marker_tuple in self.drawn_markers()]

    @covers("LLFR-00080", "LLFR-00081", "LLFR-00085", "LLFR-00091",
            "LLFR-00111", "LLFR-00109", "LLFR-00092")
    def test_place_delete_and_place_again(self) -> None:
        """Marker 1 and 2, delete Marker 2, then the next is Marker 3.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        top_panel = self.main_window.top_panel
        QTest.mouseClick(top_panel.plot_tool_button_dict[MARKER_TOOL_STR],
                         Qt.MouseButton.LeftButton)
        self.process_events()
        self.assertEqual(self.plot_widget.plot_tool_str, MARKER_TOOL_STR)
        self.left_click(0.5, 2.5)
        self.left_click(1.5, 2.5)
        self.assertEqual(self.drawn_names(), ["Marker 1", "Marker 2"])
        first_id_i, _, first_time_s = self.drawn_markers()[0]
        second_id_i, _, second_time_s = self.drawn_markers()[1]
        self.assertAlmostEqual(first_time_s, 0.5, delta=0.02)
        self.assertAlmostEqual(second_time_s, 1.5, delta=0.02)
        self.assertEqual(self.plot_widget.marker_time_text(first_id_i),
                         f"t = {first_time_s:.6g} s")
        # LLFR-00109: the button is still active after placing.
        self.assertTrue(
            top_panel.plot_tool_button_dict[MARKER_TOOL_STR].is_active())
        shown_list = self.right_click_choose(second_time_s, 2.5, "Delete")
        self.assertEqual(shown_list, ["Rename", "Delete"])
        self.assertEqual(self.drawn_names(), ["Marker 1"])
        self.left_click(1.0, 2.5)
        self.assertEqual(self.drawn_names(), ["Marker 1", "Marker 3"])
        self.assertTrue(
            top_panel.plot_tool_button_dict[MARKER_TOOL_STR].is_active())

    @covers("LLFR-00087", "LLFR-00088", "LLFR-00089", "LLFR-00112")
    def test_rename_through_the_dialog(self) -> None:
        """Rename shows the typed name; a blank name keeps the old one.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        self.main_window.top_panel.plot_tool_button_dict[
            MARKER_TOOL_STR].click()
        self.process_events()
        self.left_click(1.0, 2.5)
        marker_id_i, _, time_s = self.drawn_markers()[0]
        with mock.patch.object(QInputDialog, "getText",
                               return_value=("  Peak $1$ ", True)
                               ) as dialog_mock:
            self.right_click_choose(time_s, 2.5, "Rename")
        self.assertEqual(dialog_mock.call_count, 1)
        # The dialog starts from the current name.
        self.assertIn("Marker 1", dialog_mock.call_args[0])
        self.assertEqual(self.drawn_names(), ["Peak $1$"])
        self.assertEqual(self.plot_widget.marker_label_text(marker_id_i),
                         "Peak $1$")
        with mock.patch.object(QMessageBox, "exec") as box_mock:
            for answer_tuple in (("   ", True), ("", True),
                                 ("Ignored", False)):
                with mock.patch.object(QInputDialog, "getText",
                                       return_value=answer_tuple):
                    self.right_click_choose(time_s, 2.5, "Rename")
                self.assertEqual(self.drawn_names(), ["Peak $1$"])
        self.assertEqual(box_mock.call_count, 0)

    @covers("LLFR-00086", "LLFR-00093", "LLFR-00092")
    def test_drag_moves_the_marker_in_the_model(self) -> None:
        """A drag leaves the marker at the release time after redraw.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.top_panel.plot_tool_button_dict[
            MARKER_TOOL_STR].click()
        self.process_events()
        self.left_click(0.5, 2.5)
        marker_id_i, _, start_s = self.drawn_markers()[0]
        transform = self.plot_widget.axes.transData
        press_x_px, press_y_px = transform.transform((start_s, 2.5))
        target_x_px, _ = transform.transform((1.5, 2.5))
        send_mouse_event(self.plot_widget, "button_press_event",
                         float(press_x_px), float(press_y_px),
                         LEFT_BUTTON_I)
        send_mouse_event(self.plot_widget, "motion_notify_event",
                         float(target_x_px), float(press_y_px),
                         LEFT_BUTTON_I)
        self.assertAlmostEqual(self.plot_widget.marker_time_s(marker_id_i),
                               1.5, delta=0.02)
        send_mouse_event(self.plot_widget, "button_release_event",
                         float(target_x_px), float(press_y_px),
                         LEFT_BUTTON_I)
        self.process_events()
        # LLFR-00205: the markers belong to the workspace.
        workspace = self.controller.plot_controller.workspace
        self.assertEqual(len(workspace.marker_list), 1)
        self.assertAlmostEqual(workspace.marker_list[0].time_s, 1.5,
                               delta=0.02)
        self.assertEqual(self.drawn_names(), ["Marker 1"])
        self.assertEqual(self.plot_widget.marker_time_text(marker_id_i),
                         f"t = {workspace.marker_list[0].time_s:.6g} s")


if __name__ == "__main__":
    unittest.main()
