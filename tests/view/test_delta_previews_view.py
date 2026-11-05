"""Tests for the previews of the delta markers in the view (LLFR-00352
to LLFR-00354).

The plot widget tests drive the same matplotlib callbacks that real
mouse events reach, on the widget of DeltaWidgetTestCase ("Sine" and
"Ramp" sampled every 0.1 s from 0 to 10 s). The window tests use the
real MainWindow and MainController of SharedMarkerWindowTestCase, with
three plots in the current tab. In every test the real pointer is kept
far from the plots, so that activating a tool never shows a preview by
itself; a test moves it where it needs it.
"""

import time
import unittest
from unittest import mock

import numpy as np

from tests.support import covers, get_qt_application, requires_qt
from tests.view.test_delta_markers_view import (
    DeltaWidgetTestCase, to_hex_str)
from tests.view.test_markers_view import LEFT_BUTTON_I, send_mouse_event
from tests.view.test_plot_tools import recorder
from tests.view.test_shared_markers_view import (
    PREVIEW_MOVE_COUNT_I, SharedMarkerWindowTestCase)

from controller.plot_tools import (
    DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR,
    TIP_TOOL_STR, ZOOM_TOOL_STR)
from model.curve_colors import MARKER_COLOR_STR
from model.workspace import (
    DELTA_X_KIND_STR, DELTA_Y_KIND_STR, FREQUENCY_PLOT_KIND_STR)

# Display pixels allowed between two shapes that must be the same.
SHAPE_TOLERANCE_PX_F = 0.01
BLUE_STR = "#0000ff"
# Display pixels around the first point left out of the color check.
EXCLUDED_RADIUS_PX_F = 12.0


def keep_pointer_away(test_case):
    """Patch the pointer position read by the plots far from them.

    Inputs:
        test_case: the running unittest.TestCase.
    Outputs: the MagicMock that replaces QCursor; its pos() can be
        changed by the test.
    """
    from PyQt6.QtCore import QPoint
    cursor_mock = mock.MagicMock()
    cursor_mock.pos.return_value = QPoint(-10000, -10000)
    cursor_patcher = mock.patch("view.plot_widget.QCursor", cursor_mock)
    cursor_patcher.start()
    test_case.addCleanup(cursor_patcher.stop)
    return cursor_mock


@requires_qt
class DeltaPreviewWidgetTestCase(DeltaWidgetTestCase):
    """The widget of DeltaWidgetTestCase, with the pointer kept away."""

    def setUp(self) -> None:
        """Create the widget and keep the real pointer away from it.

        Inputs: none.
        Outputs: none.
        """
        self.cursor_mock = keep_pointer_away(self)
        super().setUp()

    def hover(self, time_s: float, value_f: float) -> None:
        """Move the mouse, with no button held, to a data point.

        Inputs:
            time_s: x value in seconds.
            value_f: y value.
        Outputs: none.
        """
        self.mouse("motion_notify_event", time_s, value_f)

    def hover_display(self, display_tuple: tuple) -> None:
        """Move the mouse, with no button held, to a display point.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: none.
        """
        send_mouse_event(self.plot_widget, "motion_notify_event",
                         *display_tuple, LEFT_BUTTON_I)

    def wait_double_click_interval(self) -> None:
        """Process events until the double-click interval has passed.

        Inputs: none.
        Outputs: none. A click on a text note that waits (LLFR-01253) is
            done by then.
        """
        import time
        from PyQt6.QtWidgets import QApplication
        interval_s = (
            QApplication.styleHints().mouseDoubleClickInterval() / 1000.0)
        deadline_s = time.perf_counter() + interval_s + 0.15
        while time.perf_counter() < deadline_s:
            self.application.processEvents()
            time.sleep(0.01)

    def note_box_center(self) -> tuple:
        """Return the center of the box of the first text note.

        Inputs: none.
        Outputs: (x, y) in display pixels.
        """
        box = self.plot_widget.text_note_box_extent(0)
        return ((box.x0 + box.x1) / 2.0, (box.y0 + box.y1) / 2.0)

    def note_off_curves(self) -> tuple:
        """Write a text note between the sine and the ramp.

        Inputs: none.
        Outputs: (x, y) of the center of its box, in display pixels,
            where text_note_at finds it and no curve is near.
        """
        self.plot_widget.set_text_notes([("Note", 5.0, 2.0)])
        self.draw()
        center_tuple = self.note_box_center()
        widget_point = self.plot_widget.display_to_widget_point(
            *center_tuple)
        self.assertEqual(self.plot_widget.text_note_at(widget_point), 0)
        self.assertEqual(self.plot_widget.nearest_curve_tuple(widget_point),
                         ())
        return center_tuple

    def note_on_level_curve(self) -> tuple:
        """Write a text note with a constant curve "Level" through it.

        Inputs: none.
        Outputs: (x, y) of the center of the note's box, in display
            pixels, where text_note_at finds the note and the nearest
            curve is "Level".
        """
        self.note_off_curves()
        level_f = float(self.plot_widget.axes.transData.inverted().transform(
            self.note_box_center())[1])
        self.plot_widget.set_curves([
            ("Sine", self.time_array, self.sine_array, "#ff0000", 1),
            ("Ramp", self.time_array, self.ramp_array, "#0000ff", 1),
            ("Level", self.time_array,
             np.full_like(self.time_array, level_f), "#00aa00", 1)])
        self.plot_widget.set_text_notes([("Note", 5.0, 2.0)])
        self.draw()
        center_tuple = self.note_box_center()
        widget_point = self.plot_widget.display_to_widget_point(
            *center_tuple)
        self.assertEqual(self.plot_widget.text_note_at(widget_point), 0)
        self.assertEqual(
            self.plot_widget.nearest_curve_tuple(widget_point)[0], "Level")
        return center_tuple

    def assert_no_delta_preview(self) -> None:
        """Check that no delta preview is shown.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(self.plot_widget.delta_preview_shown())
        self.assertFalse(self.plot_widget.delta_preview_marker_shown())
        self.assertEqual(self.plot_widget.delta_preview_point(), ())
        self.assertEqual(self.plot_widget.delta_preview_text(), "")

    def preview_bracket_vertex_array(self):
        """Return the preview bracket's vertices as drawn now.

        Inputs: none.
        Outputs: numpy array of shape (N, 2), in display pixels.
        """
        bracket = self.plot_widget.delta_preview_artists()[2]
        return np.asarray(bracket.display_path(None).vertices)


class DeltaPointPreviewTest(DeltaPreviewWidgetTestCase):
    """The dot on the sample a click would pick (LLFR-00352)."""

    @covers("LLFR-00352", "LLFR-00163", "LLFR-00751")
    def test_dot_on_the_nearest_sample_follows_the_pointer(self) -> None:
        """The dot sits on the sample a click would pick and moves.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR):
            self.plot_widget.set_plot_tool(tool_str)
            self.hover(*self.sine_point(2.0)[1:])
            self.assertTrue(self.plot_widget.delta_preview_shown())
            # No first point: only the dot, no marker.
            self.assertFalse(self.plot_widget.delta_preview_marker_shown())
            self.assertEqual(self.plot_widget.delta_preview_point(),
                             self.sine_point(2.0))
            # Between two samples, the nearest one, as a click picks.
            self.hover(2.04, float(np.sin(2.04)))
            self.assertEqual(self.plot_widget.delta_preview_point(),
                             self.sine_point(2.0))
            self.hover(2.07, float(np.sin(2.07)))
            self.assertEqual(self.plot_widget.delta_preview_point(),
                             self.sine_point(2.1))
            # On the other curve.
            self.hover(*self.ramp_point(6.0)[1:])
            self.assertEqual(self.plot_widget.delta_preview_point(),
                             self.ramp_point(6.0))
            dot = self.plot_widget.delta_preview_artists()[0]
            self.assertEqual((float(dot.get_xdata()[0]),
                              float(dot.get_ydata()[0])),
                             self.ramp_point(6.0)[1:])
            # The same sample as the click reports.
            self.left_click(*self.ramp_point(6.0)[1:])
            self.assertEqual(self.pick_list[-1], self.ramp_point(6.0))

    @covers("LLFR-00352", "LLFR-00083", "LLFR-00172", "LLFR-00686")
    def test_dot_is_a_paler_marker_color(self) -> None:
        """The dot is a paler version of the marker color.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_rgb
        from view.plot_widget import (
            DELTA_PREVIEW_COLOR_STR, MARKER_PREVIEW_COLOR_STR)
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        self.hover(*self.sine_point(3.0)[1:])
        dot = self.plot_widget.delta_preview_artists()[0]
        self.assertEqual(dot.get_marker(), "o")
        self.assertEqual(to_hex_str(dot.get_markerfacecolor()),
                         DELTA_PREVIEW_COLOR_STR)
        # The same pale color as the marker preview (LLFR-00203).
        self.assertEqual(DELTA_PREVIEW_COLOR_STR, MARKER_PREVIEW_COLOR_STR)
        marker_rgb_tuple = to_rgb(MARKER_COLOR_STR)
        preview_rgb_tuple = to_rgb(DELTA_PREVIEW_COLOR_STR)
        self.assertNotEqual(preview_rgb_tuple, marker_rgb_tuple)
        self.assertGreater(sum(preview_rgb_tuple), sum(marker_rgb_tuple))

    def changed_pixel_array(self, clean_array, shown_array,
                            excluded_point_tuple: tuple = ()):
        """Return the RGB values of the pixels a blit changed.

        Inputs:
            clean_array: RGBA buffer of the canvas before the blit.
            shown_array: RGBA buffer after it.
            excluded_point_tuple: a data point (time_s, value_f) whose
                surroundings are left out, or () to keep every pixel.
        Outputs: numpy array of shape (N, 3) of integers 0 to 255.
        """
        changed_array = np.any(clean_array != shown_array, axis=2)
        if excluded_point_tuple:
            # The preview's leader line starts on the first point, whose
            # real dot keeps the full marker color (LLFR-00165); the
            # pixels where the two blend are left out.
            x_px, y_px = self.display_tuple(*excluded_point_tuple)
            row_array, column_array = np.indices(changed_array.shape)
            row_px = changed_array.shape[0] - y_px
            changed_array &= (np.hypot(column_array - x_px,
                                       row_array - row_px)
                              > EXCLUDED_RADIUS_PX_F)
        return shown_array[changed_array][:, :3].astype(int)

    def assert_drawn_in_pale_marker_color(self, pixel_array) -> None:
        """Check that blitted pixels are the paler marker color, never
        the marker color itself.

        Inputs:
            pixel_array: (N, 3) RGB values of the changed pixels.
        Outputs: none.
        """
        from matplotlib.colors import to_rgb
        from view.plot_widget import DELTA_PREVIEW_COLOR_STR
        pale_array = np.round(
            np.array(to_rgb(DELTA_PREVIEW_COLOR_STR)) * 255.0)
        marker_array = np.round(np.array(to_rgb(MARKER_COLOR_STR)) * 255.0)
        self.assertGreater(len(pixel_array), 0)
        pale_distance_array = np.max(np.abs(pixel_array - pale_array),
                                     axis=1)
        marker_distance_array = np.max(np.abs(pixel_array - marker_array),
                                       axis=1)
        # The solid inside of the dot (and of the lines and text) has
        # the pale color exactly, up to rounding.
        self.assertGreater(int(np.sum(pale_distance_array <= 2)), 10)
        # No pixel has the full marker color.
        self.assertEqual(int(np.sum(marker_distance_array <= 8)), 0)

    @covers("LLFR-00352", "LLFR-00353", "LLFR-00083", "LLFR-00172",
            "LLFR-00660", "LLFR-00686")
    def test_previews_are_drawn_in_the_pale_theme_marker_color(
            self) -> None:
        """The pixels the dot and the marker preview draw are the paler
        version of the theme's marker color, on time plots.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        from view.plot_widget import (
            DELTA_PREVIEW_COLOR_STR, MARKER_PREVIEW_PALE_RATIO_F,
            pale_color_str)
        # The marker color mixed with the theme's plot background.
        self.assertEqual(DELTA_PREVIEW_COLOR_STR, pale_color_str(
            MARKER_COLOR_STR, theme.PLOT_BACKGROUND_COLOR_STR,
            MARKER_PREVIEW_PALE_RATIO_F))
        for tool_str in (DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR):
            self.plot_widget.set_plot_tool(tool_str)
            self.plot_widget.set_delta_first_point(())
            self.draw()
            self.application.processEvents()
            clean_array = np.array(self.plot_widget.canvas.buffer_rgba(),
                                   copy=True)
            # LLFR-00352: the dot alone.
            self.hover(*self.ramp_point(6.0)[1:])
            self.assertFalse(self.plot_widget.delta_preview_marker_shown())
            self.assert_drawn_in_pale_marker_color(self.changed_pixel_array(
                clean_array,
                np.array(self.plot_widget.canvas.buffer_rgba(), copy=True)))
            self.plot_widget.on_mouse_leave(None)
            # LLFR-00353: the whole marker preview.
            self.plot_widget.set_delta_first_point(self.sine_point(2.0))
            self.draw()
            self.application.processEvents()
            clean_array = np.array(self.plot_widget.canvas.buffer_rgba(),
                                   copy=True)
            self.hover(*self.ramp_point(6.0)[1:])
            self.assertTrue(self.plot_widget.delta_preview_marker_shown())
            marker_pixel_array = self.changed_pixel_array(
                clean_array,
                np.array(self.plot_widget.canvas.buffer_rgba(), copy=True),
                self.sine_point(2.0)[1:])
            self.assert_drawn_in_pale_marker_color(marker_pixel_array)
            # The bracket, the leader lines and the value draw much more
            # than the dot alone.
            self.assertGreater(len(marker_pixel_array), 200)
            self.plot_widget.on_mouse_leave(None)

    @covers("LLFR-00352", "LLFR-00354", "LLFR-00165")
    def test_no_dot_off_the_curves_or_without_a_delta_tool(self) -> None:
        """Off the curves, out of the plot or with another tool: none.

        Inputs: none.
        Outputs: none.
        """
        # Without a delta tool, a hover on a curve shows nothing.
        for tool_str in (NO_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR):
            self.plot_widget.set_plot_tool(tool_str)
            self.hover(*self.sine_point(2.0)[1:])
            self.assert_no_delta_preview()
        self.plot_widget.set_plot_tool(DELTA_Y_TOOL_STR)
        self.hover(*self.sine_point(2.0)[1:])
        self.assertTrue(self.plot_widget.delta_preview_shown())
        # LLFR-00354: off every curve (between the two curves).
        self.hover(5.0, 1.5)
        self.assert_no_delta_preview()
        self.hover(*self.sine_point(2.0)[1:])
        self.assertTrue(self.plot_widget.delta_preview_shown())
        # Below the x-axis, outside the drawing area.
        axes_box = self.plot_widget.axes.bbox
        send_mouse_event(self.plot_widget, "motion_notify_event",
                         float(axes_box.x0 + 20.0),
                         float(axes_box.y0 - 15.0), LEFT_BUTTON_I)
        self.assert_no_delta_preview()
        self.hover(*self.sine_point(2.0)[1:])
        self.plot_widget.on_mouse_leave(None)
        self.assert_no_delta_preview()

    @covers("LLFR-00352", "LLFR-01238", "LLFR-01248", "LLFR-00163",
            "HLFR-00043")
    def test_dot_stays_over_a_pinned_tip(self) -> None:
        """Over a pinned tip the dot stays shown (LLFR-01238); a press
        there picks the point of the dot and does not move the tip
        (LLFR-01248).

        Inputs: none.
        Outputs: none.
        """
        point_tuple = self.sine_point(4.0)
        self.plot_widget.set_pinned_tips([point_tuple + ((),)])
        self.draw()
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        # The old rule hid the dot here, over the tip.
        self.hover(*point_tuple[1:])
        self.assertTrue(self.plot_widget.delta_preview_shown())
        self.hover(*self.sine_point(7.0)[1:])
        self.assertTrue(self.plot_widget.delta_preview_shown())
        # LLFR-01248: the press picks the point of the dot.
        self.hover(*point_tuple[1:])
        self.mouse("button_press_event", *point_tuple[1:])
        self.assertEqual(self.plot_widget.drag_tip_index_i, -1)
        self.mouse("button_release_event", *point_tuple[1:])
        self.assertEqual(self.pick_list, [point_tuple])


class HoverTipOverObjectsTest(DeltaPreviewWidgetTestCase):
    """The hover data tip stays over other objects (LLFR-01238), except
    over a pinned tip (LLFR-01249)."""

    @covers("LLFR-01249", "LLFR-01238", "LLFR-00042", "LLFR-00153",
            "HLFR-00024", "HLFR-00041")
    def test_hover_tip_hidden_over_a_pinned_tip(self) -> None:
        """With the Data tip tool, the hover tip is hidden where a pinned
        tip is, shown again off it, and a press on the pinned tip moves
        it and pins nothing.

        Inputs: none.
        Outputs: none.
        """
        point_tuple = self.sine_point(4.0)
        self.plot_widget.set_pinned_tips([point_tuple + ((),)])
        self.draw()
        self.plot_widget.set_plot_tool(TIP_TOOL_STR)
        point_widget = self.plot_widget.display_to_widget_point(
            *self.display_tuple(*point_tuple[1:]))
        self.assertEqual(self.plot_widget.pinned_tip_at(point_widget), 0)
        self.hover(*point_tuple[1:])
        self.assertFalse(self.plot_widget.hover_annotation.get_visible())
        self.assertEqual(self.plot_widget.hover_point_tuple, ())
        next_tuple = self.sine_point(7.0)
        self.hover(*next_tuple[1:])
        self.assertTrue(self.plot_widget.hover_annotation.get_visible())
        self.assertEqual(self.plot_widget.hover_point_tuple[:2],
                         next_tuple[:2])
        self.hover(*point_tuple[1:])
        self.assertFalse(self.plot_widget.hover_annotation.get_visible())
        # LLFR-00153: the press moves the pinned tip, own kind of the
        # Data tip tool, and pins nothing.
        self.mouse("button_press_event", *point_tuple[1:])
        self.assertEqual(self.plot_widget.drag_tip_index_i, 0)
        self.mouse("button_release_event", *point_tuple[1:])
        self.assertEqual(self.pin_list, [])

    @covers("LLFR-01238", "LLFR-00042", "HLFR-00024")
    def test_hover_tip_over_a_text_note(self) -> None:
        """With the Data tip tool, the hover tip is shown on a curve
        where a text note is, and follows the pointer.

        Inputs: none.
        Outputs: none.
        """
        center_tuple = self.note_on_level_curve()
        self.plot_widget.set_plot_tool(TIP_TOOL_STR)
        self.hover_display(center_tuple)
        self.assertTrue(self.plot_widget.hover_annotation.get_visible())
        self.assertEqual(self.plot_widget.hover_point_tuple[0], "Level")
        first_s = self.plot_widget.hover_point_tuple[1]
        self.hover_display((center_tuple[0] + 15.0, center_tuple[1]))
        self.assertGreater(self.plot_widget.hover_point_tuple[1], first_s)


class PressWherePreviewShownTest(DeltaPreviewWidgetTestCase):
    """A press where the preview of the active tool is shown places what
    the preview shows, also on a pinned tip or a text note
    (LLFR-01248)."""

    def setUp(self) -> None:
        """Create the widget and record the moves of tips and notes.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.tip_move_list = recorder(
            self.plot_widget.pinned_tip_move_requested)
        self.note_move_list = recorder(
            self.plot_widget.text_note_move_requested)

    def press_release_display(self, display_tuple: tuple) -> None:
        """Hover a display point, press there and release there.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: none.
        """
        self.hover_display(display_tuple)
        send_mouse_event(self.plot_widget, "button_press_event",
                         *display_tuple, LEFT_BUTTON_I)
        self.press_tip_index_i = self.plot_widget.drag_tip_index_i
        self.press_note_index_i = self.plot_widget.drag_note_index_i
        send_mouse_event(self.plot_widget, "button_release_event",
                         *display_tuple, LEFT_BUTTON_I)

    def tip_point_display(self) -> tuple:
        """Pin a tip on the sine at 4 s and return its point.

        Inputs: none.
        Outputs: (x, y) of the tip's point, in display pixels, where
            pinned_tip_at finds the tip.
        """
        point_tuple = self.sine_point(4.0)
        self.plot_widget.set_pinned_tips([point_tuple + ((),)])
        self.draw()
        display_tuple = self.display_tuple(*point_tuple[1:])
        self.assertEqual(self.plot_widget.pinned_tip_at(
            self.plot_widget.display_to_widget_point(*display_tuple)), 0)
        return display_tuple

    @covers("LLFR-01248", "LLFR-00081", "LLFR-00203", "LLFR-00153",
            "HLFR-00028")
    def test_flag_placed_over_a_pinned_tip(self) -> None:
        """With the Flag tool, a press on a pinned tip where the flag
        preview is shown asks for the flag of the preview and does not
        grab the tip.

        Inputs: none.
        Outputs: none.
        """
        display_tuple = self.tip_point_display()
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.hover_display(display_tuple)
        self.assertTrue(self.plot_widget.marker_preview_shown())
        preview_s = self.plot_widget.marker_preview_time_s()
        self.press_release_display(display_tuple)
        self.assertEqual(self.press_tip_index_i, -1)
        self.assertEqual(len(self.place_list), 1)
        self.assertAlmostEqual(self.place_list[0][0], preview_s, delta=1e-9)
        self.assertEqual(self.tip_move_list, [])

    @covers("LLFR-01248", "LLFR-01253", "LLFR-00081", "LLFR-00339",
            "LLFR-00742", "HLFR-00028")
    def test_flag_placed_over_a_text_note(self) -> None:
        """With the Flag tool, a click on a text note asks for the flag
        of the preview once the double-click interval has passed, and
        does not grab the note.

        Inputs: none.
        Outputs: none.
        """
        center_tuple = self.note_off_curves()
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.hover_display(center_tuple)
        self.assertTrue(self.plot_widget.marker_preview_shown())
        preview_s = self.plot_widget.marker_preview_time_s()
        self.press_release_display(center_tuple)
        self.assertEqual(self.press_note_index_i, -1)
        # LLFR-01253: the click waits for the double-click interval.
        self.assertEqual(self.place_list, [])
        self.wait_double_click_interval()
        self.assertEqual(len(self.place_list), 1)
        self.assertAlmostEqual(self.place_list[0][0], preview_s, delta=1e-9)
        self.assertEqual(self.note_move_list, [])

    @covers("LLFR-01254", "LLFR-01253", "LLFR-01248", "HLFR-00028")
    def test_waiting_click_done_by_the_next_press(self) -> None:
        """A click on a note that waits is done at once by another left
        press, a right press, a wheel press or a change of tool, before
        the interval ends, and only once.

        Inputs: none.
        Outputs: none.
        """
        center_tuple = self.note_off_curves()
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        # The time the preview shows once the pointer is there.
        self.hover_display(center_tuple)
        preview_s = self.plot_widget.marker_preview_time_s()
        self.press_release_display(center_tuple)
        self.assertEqual(self.place_list, [])
        # Another left press, away from the note: both flags at once,
        # the waiting one first.
        other_tuple = (center_tuple[0] - 120.0, center_tuple[1])
        self.press_release_display(other_tuple)
        self.assertEqual(len(self.place_list), 2)
        self.assertAlmostEqual(self.place_list[0][0], preview_s, delta=1e-9)
        # A right press and a wheel press do it at once too.
        for button_i in (3, 2):
            with self.subTest(button=button_i):
                self.place_list.clear()
                self.press_release_display(center_tuple)
                with mock.patch.object(self.plot_widget,
                                       "request_context_menu"):
                    send_mouse_event(self.plot_widget, "button_press_event",
                                     *other_tuple, button_i)
                    self.assertEqual(len(self.place_list), 1)
                    send_mouse_event(self.plot_widget,
                                     "button_release_event", *other_tuple,
                                     button_i)
        # A change of tool does it at once, while the widget still has
        # the Flag tool, and the end of the interval adds nothing.
        self.place_list.clear()
        self.press_release_display(center_tuple)
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        self.assertEqual(len(self.place_list), 1)
        self.wait_double_click_interval()
        self.assertEqual(len(self.place_list), 1)

    @covers("LLFR-01253", "LLFR-01248", "HLFR-00028", "HLFR-00043")
    def test_waiting_click_lands_where_the_preview_showed(self) -> None:
        """A zoom during the wait doesn't move the flag or the delta
        point away from what the preview showed at the press.

        Inputs: none.
        Outputs: none.
        """
        # The flag: the time of the preview at the press.
        center_tuple = self.note_off_curves()
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.hover_display(center_tuple)
        preview_s = self.plot_widget.marker_preview_time_s()
        self.press_release_display(center_tuple)
        self.plot_widget.set_time_range(1.0, 3.0)
        self.draw()
        self.assertNotAlmostEqual(
            self.plot_widget.time_at(self.plot_widget
                                     .display_to_widget_point(*center_tuple)),
            preview_s, delta=0.05)
        self.wait_double_click_interval()
        self.assertEqual(len(self.place_list), 1)
        self.assertAlmostEqual(self.place_list[0][0], preview_s, delta=1e-9)
        # The delta point: the sample of the dot at the press.
        self.plot_widget.set_time_range(0.0, 10.0)
        center_tuple = self.note_on_level_curve()
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        self.hover_display(center_tuple)
        target_tuple = self.plot_widget.delta_preview_point_tuple
        self.press_release_display(center_tuple)
        self.plot_widget.set_time_range(2.0, 3.0)
        self.draw()
        self.wait_double_click_interval()
        self.assertEqual(self.pick_list, [target_tuple])

    @covers("LLFR-01248", "LLFR-01253", "LLFR-00045", "LLFR-00042",
            "LLFR-00742", "HLFR-00025")
    def test_tip_pinned_over_a_text_note(self) -> None:
        """With the Data tip tool, a press on a text note where the hover
        tip is shown pins that point and does not grab the note.

        Inputs: none.
        Outputs: none.
        """
        center_tuple = self.note_on_level_curve()
        self.plot_widget.set_plot_tool(TIP_TOOL_STR)
        self.hover_display(center_tuple)
        hover_tuple = self.plot_widget.hover_point_tuple
        self.assertEqual(hover_tuple[0], "Level")
        self.press_release_display(center_tuple)
        self.assertEqual(self.press_note_index_i, -1)
        # LLFR-01253: the point of the hover tip shown at the press, once
        # the double-click interval has passed.
        self.hover_display((center_tuple[0] + 25.0, center_tuple[1]))
        self.assertEqual(self.pin_list, [])
        self.wait_double_click_interval()
        self.assertEqual(self.pin_list, [hover_tuple])
        self.assertEqual(self.note_move_list, [])

    @covers("LLFR-01248", "LLFR-01253", "LLFR-00163", "LLFR-00352",
            "LLFR-00742", "HLFR-00043", "HLFR-00044")
    def test_point_picked_over_a_text_note(self) -> None:
        """With a delta tool, a press on a text note where the dot is
        shown picks the point of the dot and does not grab the note.

        Inputs: none.
        Outputs: none.
        """
        center_tuple = self.note_on_level_curve()
        for tool_str in (DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.pick_list.clear()
                self.plot_widget.set_plot_tool(tool_str)
                self.hover_display(center_tuple)
                self.assertTrue(self.plot_widget.delta_preview_shown())
                target_tuple = self.plot_widget.delta_preview_point_tuple
                self.press_release_display(center_tuple)
                self.assertEqual(self.press_note_index_i, -1)
                self.wait_double_click_interval()
                self.assertEqual(self.pick_list, [target_tuple])
                self.assertEqual(target_tuple[0], "Level")
                self.assertEqual(self.note_move_list, [])

    @covers("LLFR-01248", "LLFR-00742", "LLFR-00339", "LLFR-00354")
    def test_note_grabbed_where_no_dot_is_shown(self) -> None:
        """With a delta tool, a press on a text note off every curve,
        where no dot is shown, still grabs the note and picks nothing.

        Inputs: none.
        Outputs: none.
        """
        center_tuple = self.note_off_curves()
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        self.hover_display(center_tuple)
        self.assertFalse(self.plot_widget.delta_preview_shown())
        self.hover_display(center_tuple)
        send_mouse_event(self.plot_widget, "button_press_event",
                         *center_tuple, LEFT_BUTTON_I)
        self.assertEqual(self.plot_widget.drag_note_index_i, 0)
        end_tuple = (center_tuple[0] + 30.0, center_tuple[1])
        send_mouse_event(self.plot_widget, "motion_notify_event",
                         *end_tuple, LEFT_BUTTON_I)
        send_mouse_event(self.plot_widget, "button_release_event",
                         *end_tuple, LEFT_BUTTON_I)
        self.assertEqual(len(self.note_move_list), 1)
        self.assertEqual(self.pick_list, [])


class HeldKeyWaitingClickTest(SharedMarkerWindowTestCase):
    """A tool key released while a click on a text note waits does that
    click at once (LLFR-01254), in the real window."""

    def note_on_sample(self, plot_widget, time_s: float) -> tuple:
        """Draw a text note whose box is centred on a curve sample.

        Inputs:
            plot_widget: the PlotWidget (its first curve is used).
            time_s: a time of the sample grid (0, 0.1, ..., 4 s).
        Outputs: (x, y) of the centre of the note's box, in display
            pixels, where the note and the curve are both found.
        """
        signal_name_str, time_array, value_array = (
            plot_widget.curve_data_list[0][:3])
        index_i = int(round(time_s * 10.0))
        sample_tuple = (float(time_array[index_i]),
                        float(value_array[index_i]))
        plot_widget.set_text_notes([("Note",) + sample_tuple])
        plot_widget.canvas.draw()
        box = plot_widget.text_note_box_extent(0)
        place_x_px, place_y_px = plot_widget.axes.transData.transform(
            sample_tuple)
        offset_tuple = ((box.x0 + box.x1) / 2.0 - float(place_x_px),
                        (box.y0 + box.y1) / 2.0 - float(place_y_px))
        place_tuple = plot_widget.axes.transData.inverted().transform(
            (float(place_x_px) - offset_tuple[0],
             float(place_y_px) - offset_tuple[1]))
        plot_widget.set_text_notes([("Note", float(place_tuple[0]),
                                     float(place_tuple[1]))])
        plot_widget.canvas.draw()
        box = plot_widget.text_note_box_extent(0)
        center_tuple = ((box.x0 + box.x1) / 2.0, (box.y0 + box.y1) / 2.0)
        widget_point = plot_widget.display_to_widget_point(*center_tuple)
        self.assertEqual(plot_widget.text_note_at(widget_point), 0)
        self.assertEqual(plot_widget.nearest_curve_tuple(widget_point)[0],
                         signal_name_str)
        return center_tuple

    def press_key(self, key_name_str: str) -> None:
        """Press a key on the window, as Qt does.

        Inputs:
            key_name_str: name of a Qt.Key.
        Outputs: none.
        """
        from tests.view.test_tip_key import send_key
        for event_name_str in ("ShortcutOverride", "KeyPress"):
            send_key(self.main_window, event_name_str, key_name_str)

    def release_key(self, key_name_str: str) -> None:
        """Release a key on the window.

        Inputs:
            key_name_str: name of a Qt.Key.
        Outputs: none.
        """
        from tests.view.test_tip_key import send_key
        send_key(self.main_window, "KeyRelease", key_name_str)

    def click_display(self, plot_widget, display_tuple: tuple) -> None:
        """Hover a display point, then press and release there.

        Inputs:
            plot_widget: the PlotWidget.
            display_tuple: (x, y) in display pixels.
        Outputs: none.
        """
        for event_name_str in ("motion_notify_event", "button_press_event",
                               "button_release_event"):
            send_mouse_event(plot_widget, event_name_str, *display_tuple,
                             LEFT_BUTTON_I)

    def plot_of(self, plot_widget):
        """Return the model plot drawn by a widget.

        Inputs:
            plot_widget: the PlotWidget.
        Outputs: the Plot of the workspace.
        """
        return self.workspace.find_plot(plot_widget.plot_id_i)

    @covers("LLFR-01254", "LLFR-01253", "LLFR-00154", "LLFR-00155",
            "HLFR-00028")
    def test_shift_released_at_once_places_the_flag(self) -> None:
        """Shift held, a click on a note, Shift released before the
        double-click interval ends: exactly one flag, at the time of the
        preview.

        Inputs: none.
        Outputs: none.
        """
        plot_widget = self.current_widget_list[0]
        center_tuple = self.note_on_sample(plot_widget, 2.0)
        self.press_key("Key_Shift")
        self.assertEqual(self.plot_controller.plot_tool_str, MARKER_TOOL_STR)
        send_mouse_event(plot_widget, "motion_notify_event", *center_tuple,
                         LEFT_BUTTON_I)
        self.assertTrue(plot_widget.marker_preview_shown())
        preview_s = plot_widget.marker_preview_time_s()
        self.click_display(plot_widget, center_tuple)
        self.assertEqual(self.workspace.marker_list, [])
        self.release_key("Key_Shift")
        self.assertEqual(self.plot_controller.plot_tool_str, NO_TOOL_STR)
        self.assertEqual(len(self.workspace.marker_list), 1)
        self.assertAlmostEqual(self.workspace.marker_list[0].time_s,
                               preview_s, delta=1e-9)
        # The end of the double-click interval adds no second flag.
        deadline_s = time.perf_counter() + 0.7
        while time.perf_counter() < deadline_s:
            self.application.processEvents()
            time.sleep(0.01)
        self.assertEqual(len(self.workspace.marker_list), 1)

    @covers("LLFR-01254", "LLFR-01253", "LLFR-00148", "LLFR-00149",
            "HLFR-00025")
    def test_tip_key_released_at_once_pins_the_tip(self) -> None:
        """The Data tip key held, a click on a note over the curve, the
        key released at once: exactly one pinned tip, at the point of
        the hover tip of the press.

        Inputs: none.
        Outputs: none.
        """
        plot_widget = self.current_widget_list[0]
        center_tuple = self.note_on_sample(plot_widget, 2.0)
        self.press_key("Key_Control")
        self.assertEqual(self.plot_controller.plot_tool_str, TIP_TOOL_STR)
        send_mouse_event(plot_widget, "motion_notify_event", *center_tuple,
                         LEFT_BUTTON_I)
        hover_tuple = tuple(plot_widget.hover_point_tuple)
        self.assertEqual(len(hover_tuple), 3)
        self.click_display(plot_widget, center_tuple)
        self.assertEqual(self.plot_of(plot_widget).pinned_tip_list, [])
        self.release_key("Key_Control")
        self.assertEqual(self.plot_controller.plot_tool_str, NO_TOOL_STR)
        tip_list = self.plot_of(plot_widget).pinned_tip_list
        self.assertEqual(len(tip_list), 1)
        self.assertEqual((tip_list[0].signal_name_str, tip_list[0].time_s,
                          tip_list[0].value_f), hover_tuple)

    @covers("LLFR-01254", "LLFR-01253", "LLFR-00197", "LLFR-00198",
            "LLFR-00164", "HLFR-00043")
    def test_x_key_released_at_once_draws_the_marker(self) -> None:
        """X held, a first point picked on the curve, then a click on a
        note over the curve and X released at once: the Delta X marker
        of the two points is drawn.

        Inputs: none.
        Outputs: none.
        """
        plot_widget = self.current_widget_list[0]
        self.press_key("Key_X")
        self.assertEqual(self.plot_controller.plot_tool_str,
                         DELTA_X_TOOL_STR)
        time_array, value_array = plot_widget.curve_data_list[0][1:3]
        first_x_px, first_y_px = plot_widget.axes.transData.transform(
            (float(time_array[10]), float(value_array[10])))
        self.click_display(plot_widget, (float(first_x_px),
                                         float(first_y_px)))
        self.application.processEvents()
        # The note is drawn after the first point, whose pick may draw
        # the plot again from the model.
        center_tuple = self.note_on_sample(plot_widget, 2.0)
        send_mouse_event(plot_widget, "motion_notify_event", *center_tuple,
                         LEFT_BUTTON_I)
        target_tuple = plot_widget.delta_preview_point()
        self.assertEqual(len(target_tuple), 3)
        self.click_display(plot_widget, center_tuple)
        self.assertEqual(self.plot_of(plot_widget).delta_marker_list, [])
        self.release_key("Key_X")
        self.assertEqual(self.plot_controller.plot_tool_str, NO_TOOL_STR)
        delta_list = self.plot_of(plot_widget).delta_marker_list
        self.assertEqual(len(delta_list), 1)
        self.assertEqual(tuple(delta_list[0].second_point_tuple),
                         target_tuple)


class DeltaMarkerPreviewTest(DeltaPreviewWidgetTestCase):
    """The preview of the marker a second click would draw
    (LLFR-00353)."""

    @covers("LLFR-00353", "LLFR-00168", "LLFR-00169", "LLFR-00164",
            "LLFR-00752")
    def test_delta_x_preview_is_the_marker_a_click_would_draw(
            self) -> None:
        """Same bracket and value as the real Delta X marker, updated.

        Inputs: none.
        Outputs: none.
        """
        from view import value_text
        from view.plot_widget import DELTA_PREVIEW_COLOR_STR
        first_tuple = self.sine_point(2.0)
        second_tuple = self.ramp_point(6.0)
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        self.plot_widget.set_delta_first_point(first_tuple)
        # A real marker between the same points, to compare shapes.
        self.set_delta_markers([(1, DELTA_X_KIND_STR, first_tuple,
                                 second_tuple)])
        self.hover(*second_tuple[1:])
        self.assertTrue(self.plot_widget.delta_preview_marker_shown())
        self.assertEqual(self.plot_widget.delta_preview_point(), second_tuple)
        delta_s = second_tuple[1] - first_tuple[1]
        self.assertAlmostEqual(self.plot_widget.delta_preview_value_f(),
                               delta_s)
        self.assertEqual(self.plot_widget.delta_preview_text(),
                         value_text.format_delta_x_text(delta_s))
        self.assertEqual(self.plot_widget.delta_preview_text(), "Δt = 4 s")
        self.assertEqual(self.plot_widget.delta_preview_text(),
                         self.plot_widget.delta_label_text(1))
        np.testing.assert_allclose(self.preview_bracket_vertex_array(),
                                   self.bracket_vertex_array(1),
                                   atol=SHAPE_TOLERANCE_PX_F)
        # In the paler marker color.
        dot, leader, bracket, label = self.plot_widget.delta_preview_artists()
        for patch in (leader, bracket):
            self.assertEqual(to_hex_str(patch.get_edgecolor()),
                             DELTA_PREVIEW_COLOR_STR)
        self.assertEqual(to_hex_str(label.get_color()),
                         DELTA_PREVIEW_COLOR_STR)
        self.assertEqual(label.get_text(), "Δt = 4 s")
        # Updated as the pointer moves: backwards gives a negative value.
        self.hover(*self.sine_point(0.5)[1:])
        self.assertEqual(self.plot_widget.delta_preview_text(),
                         value_text.format_delta_x_text(
                             self.sine_point(0.5)[1] - first_tuple[1]))
        self.assertTrue(self.plot_widget.delta_preview_text().startswith(
            "Δt = -"))

    @covers("LLFR-00353", "LLFR-00170", "LLFR-00171", "LLFR-00685")
    def test_delta_y_preview_with_its_mirroring(self) -> None:
        """Same bracket, side and value as the real Delta Y marker.

        Inputs: none.
        Outputs: none.
        """
        from view import value_text
        self.plot_widget.set_plot_tool(DELTA_Y_TOOL_STR)
        for first_tuple, second_tuple in (
                (self.sine_point(2.0), self.ramp_point(4.0)),
                # Near the right edge: mirrored to the left.
                (self.sine_point(9.6), self.ramp_point(9.9))):
            self.plot_widget.set_delta_first_point(first_tuple)
            self.set_delta_markers([(1, DELTA_Y_KIND_STR, first_tuple,
                                     second_tuple)])
            self.hover(*second_tuple[1:])
            self.assertTrue(self.plot_widget.delta_preview_marker_shown())
            delta_f = second_tuple[2] - first_tuple[2]
            self.assertEqual(self.plot_widget.delta_preview_text(),
                             value_text.format_delta_y_text(delta_f))
            self.assertEqual(self.plot_widget.delta_preview_text(),
                             self.plot_widget.delta_label_text(1))
            preview_bracket = self.plot_widget.delta_preview_artists()[2]
            self.assertEqual(preview_bracket.side_function(None),
                             self.delta_y_side(1))
            np.testing.assert_allclose(self.preview_bracket_vertex_array(),
                                       self.bracket_vertex_array(1),
                                       atol=SHAPE_TOLERANCE_PX_F)
        self.assertEqual(self.delta_y_side(1), "left")

    @covers("LLFR-00353", "LLFR-00164", "LLFR-00682")
    def test_kind_follows_the_active_button(self) -> None:
        """Switching between Delta X and Delta Y changes the preview.

        Inputs: none.
        Outputs: none.
        """
        first_tuple = self.sine_point(2.0)
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        self.plot_widget.set_delta_first_point(first_tuple)
        # The dot of the first point is drawn, so the preview is blitted
        # at once (a blit waits for a pending full draw).
        self.draw()
        self.hover(*self.ramp_point(5.0)[1:])
        self.assertTrue(self.plot_widget.delta_preview_text().startswith(
            "Δt = "))
        self.assertEqual(self.plot_widget.delta_preview_artists()[2].kind_str,
                         DELTA_X_KIND_STR)
        self.plot_widget.set_plot_tool(DELTA_Y_TOOL_STR)
        self.assertTrue(self.plot_widget.delta_preview_marker_shown())
        self.assertTrue(self.plot_widget.delta_preview_text().startswith(
            "Δy = "))
        self.assertEqual(self.plot_widget.delta_preview_artists()[2].kind_str,
                         DELTA_Y_KIND_STR)

    @covers("LLFR-00353", "LLFR-00163", "LLFR-00164", "LLFR-00680",
            "LLFR-00681", "LLFR-00432")
    def test_preview_follows_the_first_point_as_it_is_picked(self) -> None:
        """Picking a first point turns the dot into a marker preview;
        placing the marker turns it back into a dot.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        self.hover(*self.sine_point(3.0)[1:])
        self.assertFalse(self.plot_widget.delta_preview_marker_shown())
        # The controller answers the click with the first point. The
        # pointer is still on it, where a marker would measure zero, so
        # no preview is shown (LLFR-00432).
        self.plot_widget.set_delta_first_point(self.sine_point(3.0))
        self.assertFalse(self.plot_widget.delta_preview_marker_shown())
        self.assertEqual(self.plot_widget.delta_preview_text(), "")
        self.hover(*self.sine_point(4.0)[1:])
        self.assertTrue(self.plot_widget.delta_preview_marker_shown())
        self.assertEqual(self.plot_widget.delta_preview_text(), "Δt = 1 s")
        # The second click places the marker; the first point goes.
        self.plot_widget.set_delta_first_point(())
        self.assertTrue(self.plot_widget.delta_preview_shown())
        self.assertFalse(self.plot_widget.delta_preview_marker_shown())


@requires_qt
class DeltaPreviewFrequencyPlotTest(unittest.TestCase):
    """The marker preview on a frequency plot (LLFR-00353, LLFR-00261)."""

    def setUp(self) -> None:
        """Create and show a frequency plot with one spectrum.

        Inputs: none.
        Outputs: none.
        """
        keep_pointer_away(self)
        self.application = get_qt_application()
        from view.plot_widget import PlotWidget
        self.plot_widget = PlotWidget(3, kind_str=FREQUENCY_PLOT_KIND_STR)
        self.plot_widget.resize(600, 400)
        self.plot_widget.show()
        self.frequency_array = np.linspace(0.0, 25.0, 251)
        self.amplitude_array = np.exp(-(self.frequency_array - 2.0) ** 2)
        self.plot_widget.set_curves([
            ("fft_Speed", self.frequency_array, self.amplitude_array,
             BLUE_STR, 1)])
        self.application.processEvents()
        self.plot_widget.canvas.draw()

    def tearDown(self) -> None:
        """Close and delete the plot widget.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.close()
        self.plot_widget.deleteLater()
        self.application.processEvents()

    def point(self, index_i: int) -> tuple:
        """Return a sample of the spectrum.

        Inputs:
            index_i: index of the sample.
        Outputs: (signal_name_str, frequency_hz, value_f).
        """
        return ("fft_Speed", float(self.frequency_array[index_i]),
                float(self.amplitude_array[index_i]))

    def hover(self, point_tuple: tuple) -> None:
        """Move the mouse over a sample.

        Inputs:
            point_tuple: (signal_name_str, frequency_hz, value_f).
        Outputs: none.
        """
        display_x_px, display_y_px = self.plot_widget.axes.transData.transform(
            point_tuple[1:])
        send_mouse_event(self.plot_widget, "motion_notify_event",
                         float(display_x_px), float(display_y_px),
                         LEFT_BUTTON_I)

    @covers("LLFR-00353", "LLFR-00352", "LLFR-00261")
    def test_delta_x_preview_shows_the_frequency_difference(self) -> None:
        """"Δf = <value> Hz" between the first point and the pointer.

        Inputs: none.
        Outputs: none.
        """
        from view import value_text
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        self.hover(self.point(10))
        self.assertTrue(self.plot_widget.delta_preview_shown())
        self.assertEqual(self.plot_widget.delta_preview_point(),
                         self.point(10))
        self.plot_widget.set_delta_first_point(self.point(10))
        self.hover(self.point(40))
        self.assertTrue(self.plot_widget.delta_preview_marker_shown())
        delta_hz = self.point(40)[1] - self.point(10)[1]
        self.assertEqual(self.plot_widget.delta_preview_text(),
                         value_text.format_delta_frequency_text(delta_hz))
        self.assertTrue(self.plot_widget.delta_preview_text().startswith(
            "Δf = "))
        self.assertTrue(self.plot_widget.delta_preview_text().endswith(" Hz"))
        # Delta Y keeps the "Δy" text on a frequency plot too.
        self.plot_widget.set_plot_tool(DELTA_Y_TOOL_STR)
        self.assertTrue(self.plot_widget.delta_preview_text().startswith(
            "Δy = "))


class DeltaPreviewHiddenTest(DeltaPreviewWidgetTestCase):
    """When the previews go, and what they never reach (LLFR-00354)."""

    @covers("LLFR-00354", "LLFR-00165", "LLFR-00167", "LLFR-00756")
    def test_hidden_off_curve_and_on_deactivation_first_dot_kept(
            self) -> None:
        """Off the curves the dot of the first point stays; leaving the
        delta tools hides everything.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        self.plot_widget.set_delta_first_point(self.sine_point(2.0))
        self.draw()
        first_dot = self.plot_widget.delta_first_point_artist
        self.hover(*self.ramp_point(5.0)[1:])
        self.assertTrue(self.plot_widget.delta_preview_marker_shown())
        self.hover(5.0, 1.5)
        self.assert_no_delta_preview()
        # LLFR-00165: the dot of the first point is still drawn.
        self.assertIs(self.plot_widget.delta_first_point_artist, first_dot)
        self.assertIn(first_dot, self.plot_widget.axes.lines)
        self.hover(*self.ramp_point(5.0)[1:])
        self.plot_widget.on_mouse_leave(None)
        self.assert_no_delta_preview()
        self.assertIn(first_dot, self.plot_widget.axes.lines)
        # The button is deactivated: no preview at all.
        self.hover(*self.ramp_point(5.0)[1:])
        self.assertTrue(self.plot_widget.delta_preview_shown())
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        self.assert_no_delta_preview()
        # And none with another tool, also after a move.
        self.plot_widget.set_plot_tool(TIP_TOOL_STR)
        self.hover(*self.ramp_point(6.0)[1:])
        self.assert_no_delta_preview()

    @covers("LLFR-00354", "LLFR-00352", "LLFR-00197", "LLFR-00200")
    def test_tool_activated_with_the_pointer_on_a_curve(self) -> None:
        """Activating a delta tool (X or Y held) with the pointer resting
        on a curve shows the dot without a mouse move.

        Inputs: none.
        Outputs: none.
        """
        point_tuple = self.sine_point(3.0)
        widget_point = self.plot_widget.data_to_widget_point(
            *point_tuple[1:])
        self.cursor_mock.pos.return_value = self.plot_widget.mapToGlobal(
            widget_point)
        for tool_str in (DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR):
            self.plot_widget.set_plot_tool(tool_str)
            self.assertEqual(self.plot_widget.delta_preview_point(),
                             point_tuple)
            self.plot_widget.set_plot_tool(NO_TOOL_STR)
            self.assert_no_delta_preview()

    @covers("LLFR-00354", "LLFR-00352", "LLFR-00353", "LLFR-00752")
    def test_following_the_pointer_never_redraws_the_canvas(self) -> None:
        """Moves only blit the preview: no full draw of the canvas.

        Inputs: none.
        Outputs: none.
        """
        draw_count_list = [0]

        def count_draw(event) -> None:
            """Count a full draw of the canvas.

            Inputs:
                event: the matplotlib DrawEvent.
            Outputs: none.
            """
            draw_count_list[0] += 1

        self.plot_widget.canvas.mpl_connect("draw_event", count_draw)
        for tool_str in (DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR):
            self.plot_widget.set_plot_tool(tool_str)
            self.plot_widget.set_delta_first_point(self.sine_point(1.0))
            self.draw()
            self.hover(*self.sine_point(1.0)[1:])
            self.application.processEvents()
            draw_count_list[0] = 0
            for move_i in range(PREVIEW_MOVE_COUNT_I):
                time_s = round(1.5 + 0.2 * move_i, 1)
                self.hover(*self.sine_point(time_s)[1:])
                self.assertTrue(
                    self.plot_widget.delta_preview_marker_shown())
                # Off the curve and back, too.
                self.hover(time_s, 1.5)
            self.application.processEvents()
            self.assertEqual(draw_count_list[0], 0)

    @covers("LLFR-00354", "LLFR-00352")
    def test_preview_is_drawn_on_the_canvas_and_removed(self) -> None:
        """Showing the preview changes the canvas image; hiding it
        gives back the image of the last full draw.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        self.plot_widget.set_delta_first_point(self.sine_point(2.0))
        self.draw()
        self.application.processEvents()
        clean_array = np.array(self.plot_widget.canvas.buffer_rgba(),
                               copy=True)
        self.hover(*self.ramp_point(6.0)[1:])
        shown_array = np.array(self.plot_widget.canvas.buffer_rgba(),
                               copy=True)
        self.assertFalse(np.array_equal(clean_array, shown_array))
        self.plot_widget.on_mouse_leave(None)
        hidden_array = np.array(self.plot_widget.canvas.buffer_rgba(),
                                copy=True)
        self.assertTrue(np.array_equal(clean_array, hidden_array))

    @covers("LLFR-00354", "LLFR-00129", "LLFR-00133", "LLFR-00753")
    def test_preview_artists_are_not_part_of_the_figure(self) -> None:
        """The preview artists are not in the axes, a full draw or the
        PDF image of the figure.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.plot_widget.set_plot_tool(DELTA_Y_TOOL_STR)
        self.plot_widget.set_delta_first_point(self.sine_point(2.0))
        self.draw()
        clean_figure_image = plot_export.render_figure_image(
            self.plot_widget.figure, 100.0)
        self.hover(*self.ramp_point(6.0)[1:])
        self.assertTrue(self.plot_widget.delta_preview_marker_shown())
        children_list = self.plot_widget.axes.get_children()
        for artist in self.plot_widget.delta_preview_artists():
            self.assertNotIn(artist, children_list)
        with mock.patch.object(
                self.plot_widget.axes, "draw_artist",
                wraps=self.plot_widget.axes.draw_artist) as draw_mock:
            self.assertEqual(plot_export.render_figure_image(
                self.plot_widget.figure, 100.0), clean_figure_image)
        for call in draw_mock.call_args_list:
            self.assertNotIn(call.args[0],
                             self.plot_widget.delta_preview_artists())


class DeltaPreviewWindowTest(SharedMarkerWindowTestCase):
    """The previews in the real window: another plot, the X and Y keys,
    the export, the copy, the layout and the undo history."""

    def hover_sample(self, plot_widget, time_s: float) -> None:
        """Move the mouse over the sample of a plot's curve at a time.

        Inputs:
            plot_widget: the PlotWidget (one curve).
            time_s: a time of the sample grid (0, 0.1, ..., 4 s).
        Outputs: none.
        """
        display_x_px, display_y_px = plot_widget.axes.transData.transform(
            self.sample(plot_widget, time_s)[1:])
        send_mouse_event(plot_widget, "motion_notify_event",
                         float(display_x_px), float(display_y_px),
                         LEFT_BUTTON_I)

    def click_sample(self, plot_widget, time_s: float) -> None:
        """Press and release the left button on a sample.

        Inputs:
            plot_widget: the PlotWidget (one curve).
            time_s: a time of the sample grid.
        Outputs: none.
        """
        display_x_px, display_y_px = plot_widget.axes.transData.transform(
            self.sample(plot_widget, time_s)[1:])
        for event_name_str in ("button_press_event", "button_release_event"):
            send_mouse_event(plot_widget, event_name_str,
                             float(display_x_px), float(display_y_px),
                             LEFT_BUTTON_I)
        self.process_events()

    def sample(self, plot_widget, time_s: float) -> tuple:
        """Return the sample of a plot's only curve at a time.

        Inputs:
            plot_widget: the PlotWidget.
            time_s: a time of the sample grid.
        Outputs: (signal_name_str, time_s, value_f).
        """
        signal_name_str, time_array, value_array = (
            plot_widget.curve_data_list[0][:3])
        index_i = int(round(time_s * 10.0))
        return (signal_name_str, float(time_array[index_i]),
                float(value_array[index_i]))

    def widget_list(self) -> list:
        """Return the plots of the current tab, as now drawn.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        return list(self.panel.page_dict[self.first_tab_id_i]
                    .plot_widget_list)

    def press_key(self, key_name_str: str) -> None:
        """Press a key on the window, as Qt does.

        Inputs:
            key_name_str: name of a Qt.Key.
        Outputs: none.
        """
        from tests.view.test_tip_key import send_key
        for event_name_str in ("ShortcutOverride", "KeyPress"):
            send_key(self.main_window, event_name_str, key_name_str)
        self.application.processEvents()

    def release_key(self, key_name_str: str) -> None:
        """Release a key on the window.

        Inputs:
            key_name_str: name of a Qt.Key.
        Outputs: none.
        """
        from tests.view.test_tip_key import send_key
        send_key(self.main_window, "KeyRelease", key_name_str)
        self.application.processEvents()

    @covers("LLFR-00352", "LLFR-00353", "LLFR-00166", "LLFR-00354")
    def test_previews_across_plots(self) -> None:
        """A dot before the first click, the marker in the same plot,
        only a dot on another plot, which a click there makes the new
        first point.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.top_panel.plot_tool_button_dict[
            DELTA_X_TOOL_STR].click()
        self.process_events()
        self.assertEqual(self.plot_controller.plot_tool_str,
                         DELTA_X_TOOL_STR)
        speed_widget, force_widget, _ = self.widget_list()
        self.hover_sample(speed_widget, 1.0)
        self.assertEqual(speed_widget.delta_preview_point(),
                         self.sample(speed_widget, 1.0))
        self.assertFalse(speed_widget.delta_preview_marker_shown())
        self.click_sample(speed_widget, 1.0)
        speed_widget, force_widget, _ = self.widget_list()
        self.assertEqual(speed_widget.delta_first_point_tuple,
                         self.sample(speed_widget, 1.0))
        self.hover_sample(speed_widget, 3.0)
        self.assertTrue(speed_widget.delta_preview_marker_shown())
        self.assertEqual(speed_widget.delta_preview_text(), "Δt = 2 s")
        # LLFR-00166: on another plot a click takes a new first point,
        # so only the dot is previewed there.
        speed_widget.on_mouse_leave(None)
        self.assertFalse(speed_widget.delta_preview_shown())
        self.assertTrue(speed_widget.delta_first_point_tuple)
        self.hover_sample(force_widget, 2.0)
        self.assertTrue(force_widget.delta_preview_shown())
        self.assertFalse(force_widget.delta_preview_marker_shown())
        self.assertEqual(force_widget.delta_preview_point(),
                         self.sample(force_widget, 2.0))
        self.click_sample(force_widget, 2.0)
        speed_widget, force_widget, _ = self.widget_list()
        self.assertEqual(speed_widget.delta_first_point_tuple, ())
        self.hover_sample(force_widget, 2.5)
        self.assertTrue(force_widget.delta_preview_marker_shown())
        self.assertEqual(force_widget.delta_preview_text(), "Δt = 0.5 s")
        # Deactivating the button hides it.
        self.main_window.top_panel.plot_tool_button_dict[
            DELTA_X_TOOL_STR].click()
        self.process_events()
        for plot_widget in self.widget_list():
            self.assertFalse(plot_widget.delta_preview_shown())

    @covers("LLFR-00352", "LLFR-00197", "LLFR-00198", "LLFR-00200",
            "LLFR-00201", "LLFR-00354", "LLFR-00751")
    def test_x_and_y_keys_held_show_the_preview(self) -> None:
        """Holding X or Y with the pointer on a curve shows the dot at
        once and while moving; releasing the key hides it.

        Inputs: none.
        Outputs: none.
        """
        plot_widget = self.widget_list()[0]
        point_tuple = self.sample(plot_widget, 2.0)
        widget_point = plot_widget.data_to_widget_point(*point_tuple[1:])
        self.cursor_mock.pos.return_value = plot_widget.mapToGlobal(
            widget_point)
        for key_name_str, tool_str in (("Key_X", DELTA_X_TOOL_STR),
                                       ("Key_Y", DELTA_Y_TOOL_STR)):
            self.press_key(key_name_str)
            self.assertEqual(self.plot_controller.plot_tool_str, tool_str)
            self.assertEqual(plot_widget.delta_preview_point(), point_tuple)
            self.hover_sample(plot_widget, 3.0)
            self.assertEqual(plot_widget.delta_preview_point(),
                             self.sample(plot_widget, 3.0))
            self.release_key(key_name_str)
            self.assertEqual(self.plot_controller.plot_tool_str, NO_TOOL_STR)
            self.assertFalse(plot_widget.delta_preview_shown())
            self.hover_sample(plot_widget, 2.0)

    @covers("LLFR-00354", "LLFR-00129", "LLFR-00133", "LLFR-00140",
            "LLFR-00225", "LLFR-00753", "LLFR-00754", "LLFR-00755")
    def test_not_exported_copied_saved_or_undoable(self) -> None:
        """The grab of the page never shows the previews; the layout
        and the undo history do not change while they are shown.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.main_window.top_panel.plot_tool_button_dict[
            DELTA_Y_TOOL_STR].click()
        self.process_events()
        speed_widget = self.widget_list()[0]
        self.click_sample(speed_widget, 1.0)
        speed_widget, force_widget, _ = self.widget_list()
        layout_dict = self.plot_controller.layout_dict()
        undo_b = self.plot_controller.undo_history.can_undo()
        redo_b = self.plot_controller.undo_history.can_redo()
        self.hover_sample(speed_widget, 3.0)
        self.assertTrue(speed_widget.delta_preview_marker_shown())
        self.hover_sample(force_widget, 2.0)
        self.assertTrue(force_widget.delta_preview_shown())
        # LLFR-00225, LLFR-00140: nothing of the previews is kept.
        self.assertEqual(self.plot_controller.layout_dict(), layout_dict)
        self.assertEqual(self.plot_controller.undo_history.can_undo(),
                         undo_b)
        self.assertEqual(self.plot_controller.undo_history.can_redo(),
                         redo_b)
        self.assertEqual(len(self.workspace.find_plot(
            speed_widget.plot_id_i).delta_marker_list), 0)
        # LLFR-00129, LLFR-00133: the PDF pages and the copied image are
        # grabs of the tab page; no preview is shown or drawn then.
        page = self.panel.page_dict[self.first_tab_id_i]
        shown_at_grab_list = []
        original_grab = page.grab

        def recording_grab(*argument_tuple):
            """Record which plots show a preview, then grab.

            Inputs:
                argument_tuple: the arguments of QWidget.grab.
            Outputs: the QPixmap of the grab.
            """
            shown_at_grab_list.append(
                [page_widget.delta_preview_shown()
                 for page_widget in page.plot_widget_list])
            return original_grab(*argument_tuple)

        page.grab = recording_grab
        patcher_list = [mock.patch.object(
            page_widget.axes, "draw_artist",
            wraps=page_widget.axes.draw_artist)
            for page_widget in page.plot_widget_list]
        draw_artist_mock_list = [patcher.start() for patcher in patcher_list]
        try:
            page_image = plot_export.grab_page_image(page)
            self.application.processEvents()
        finally:
            for patcher in patcher_list:
                patcher.stop()
            del page.grab
        self.assertFalse(page_image.isNull())
        self.assertEqual(shown_at_grab_list, [[False] * len(
            page.plot_widget_list)])
        preview_artist_list = []
        for page_widget in page.plot_widget_list:
            preview_artist_list.extend(page_widget.delta_preview_artists())
        for draw_artist_mock in draw_artist_mock_list:
            for call in draw_artist_mock.call_args_list:
                self.assertNotIn(call.args[0], preview_artist_list)
        # The first point's dot stays; the next move shows the preview.
        self.assertTrue(speed_widget.delta_first_point_tuple)
        self.hover_sample(speed_widget, 2.0)
        self.assertTrue(speed_widget.delta_preview_marker_shown())


if __name__ == "__main__":
    unittest.main()
