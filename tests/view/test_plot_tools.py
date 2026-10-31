"""Tests for the plot tools and the x-axis zoom (HLFR-00027, HLFR-00032).

Covers the Tip, Zoom and Vertical marker buttons of the top panel, the
rule of one active plot tool, click and wheel zoom in a plot widget, the
automatic y-axis fit, and the whole chain through MainWindow and the
real controllers. No modal dialog or menu is ever opened.
"""

import unittest

import numpy as np

from tests.support import covers, get_qt_application, requires_qt

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, PLOT_TOOL_TUPLE, TIP_TOOL_STR,
    ZOOM_TOOL_STR)

WIDGET_WIDTH_I = 600
WIDGET_HEIGHT_I = 400
RED_STR = "#ff0000"
BLUE_STR = "#0000ff"
ALL_TOOL_TUPLE = PLOT_TOOL_TUPLE + (NO_TOOL_STR,)
CURVE_CHECK_SAMPLE_COUNT_I = 2001


def recorder(signal) -> list:
    """Connect a Qt signal to a slot that records its arguments.

    Inputs:
        signal: a bound pyqtSignal.
    Outputs: the list that receives one tuple of arguments per emission.
    """
    record_list = []
    signal.connect(lambda *argument_tuple: record_list.append(argument_tuple))
    return record_list


@requires_qt
class TopPanelToolTest(unittest.TestCase):
    """The plot tool buttons and the rule of one active tool."""

    def setUp(self) -> None:
        """Create and show a top panel and record its tool changes.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.top_panel import TopPanel
        self.top_panel = TopPanel()
        self.top_panel.resize(800, 60)
        self.top_panel.show()
        self.application.processEvents()
        self.change_list = recorder(self.top_panel.plot_tool_changed)

    def tearDown(self) -> None:
        """Close and delete the panel.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.close()
        self.top_panel.deleteLater()
        self.application.processEvents()

    def button(self, tool_str: str):
        """Return the button of a plot tool.

        Inputs:
            tool_str: the tool name.
        Outputs: the ToggleButton.
        """
        return self.top_panel.plot_tool_button_dict[tool_str]

    def assert_only_active(self, tool_str: str) -> None:
        """Check that only one tool button (or none) looks active.

        Inputs:
            tool_str: the tool expected active, NO_TOOL_STR for none.
        Outputs: none.
        """
        from view.toggle_button import ACTIVE_COLOR_STR, NORMAL_COLOR_STR
        for other_tool_str in PLOT_TOOL_TUPLE:
            button = self.button(other_tool_str)
            expected_b = other_tool_str == tool_str
            self.assertEqual(button.is_active(), expected_b, other_tool_str)
            self.assertEqual(
                button.current_background_color_str(),
                ACTIVE_COLOR_STR if expected_b else NORMAL_COLOR_STR)
        self.assertEqual(self.top_panel.active_plot_tool(), tool_str)

    @covers("LLFR-00018", "LLFR-00077", "LLFR-00080")
    def test_tool_buttons_exist_with_exact_texts(self) -> None:
        """Tip, Zoom and Vertical marker are inactive toggle buttons.

        Inputs: none.
        Outputs: none.
        """
        from view.toggle_button import ToggleButton
        expected_dict = {TIP_TOOL_STR: "Tip", ZOOM_TOOL_STR: "Zoom",
                         MARKER_TOOL_STR: "Vertical marker"}
        self.assertEqual(self.top_panel.tip_button,
                         self.button(TIP_TOOL_STR))
        self.assertEqual(self.top_panel.zoom_button,
                         self.button(ZOOM_TOOL_STR))
        self.assertEqual(self.top_panel.marker_button,
                         self.button(MARKER_TOOL_STR))
        for tool_str, text_str in expected_dict.items():
            button = self.button(tool_str)
            self.assertIsInstance(button, ToggleButton)
            self.assertEqual(button.text(), text_str)
            self.assertTrue(button.isVisible())
            self.assertFalse(button.is_active())
            self.assertIs(button.parentWidget(), self.top_panel)
        self.assert_only_active(NO_TOOL_STR)

    @covers("LLFR-00018", "LLFR-00077", "LLFR-00080", "LLFR-00004")
    def test_tool_buttons_follow_open_file_in_order(self) -> None:
        """Open file, Tip, Zoom, Vertical marker, left to right.

        Inputs: none.
        Outputs: none.
        """
        button_list = [self.top_panel.open_file_button,
                       self.top_panel.tip_button,
                       self.top_panel.zoom_button,
                       self.top_panel.marker_button]
        for left_button, right_button in zip(button_list, button_list[1:]):
            self.assertLessEqual(left_button.x() + left_button.width(),
                                 right_button.x())
        self.assertLess(self.top_panel.marker_button.x(),
                        self.top_panel.width() // 2)

    @covers("LLFR-00079", "LLFR-00001")
    def test_activating_a_tool_deactivates_every_other(self) -> None:
        """For every pair, activating the second makes the first normal.

        Inputs: none.
        Outputs: none.
        """
        for first_tool_str in PLOT_TOOL_TUPLE:
            for second_tool_str in PLOT_TOOL_TUPLE:
                if first_tool_str == second_tool_str:
                    continue
                with self.subTest(first=first_tool_str,
                                  second=second_tool_str):
                    self.button(first_tool_str).click()
                    self.assert_only_active(first_tool_str)
                    self.change_list.clear()
                    self.button(second_tool_str).click()
                    self.assert_only_active(second_tool_str)
                    # Only the new tool is reported, never "no tool".
                    self.assertEqual(self.change_list, [(second_tool_str,)])
                    self.button(second_tool_str).click()
                    self.assert_only_active(NO_TOOL_STR)

    @covers("LLFR-00002", "LLFR-00109", "LLFR-00079")
    def test_second_click_leaves_no_tool_active(self) -> None:
        """Clicking the active tool button reports NO_TOOL_STR.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in PLOT_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.change_list.clear()
                self.button(tool_str).click()
                self.button(tool_str).click()
                self.assertEqual(self.change_list,
                                 [(tool_str,), (NO_TOOL_STR,)])
                self.assert_only_active(NO_TOOL_STR)

    @covers("LLFR-00079", "LLFR-00002")
    def test_open_file_button_is_not_a_plot_tool(self) -> None:
        """The Open file button neither ends nor is ended by a tool.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.zoom_button.click()
        self.top_panel.open_file_button.click()
        self.assertTrue(self.top_panel.open_file_button.is_active())
        self.assert_only_active(ZOOM_TOOL_STR)
        self.top_panel.tip_button.click()
        self.assertTrue(self.top_panel.open_file_button.is_active())
        self.assertEqual(self.change_list,
                         [(ZOOM_TOOL_STR,), (TIP_TOOL_STR,)])

    @covers("LLFR-00079")
    def test_show_plot_tool_sets_buttons_quietly(self) -> None:
        """show_plot_tool changes the buttons without reporting back.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in ALL_TOOL_TUPLE:
            self.top_panel.show_plot_tool(tool_str)
            self.assert_only_active(tool_str)
        self.assertEqual(self.change_list, [])


@requires_qt
class PlotWidgetToolTestCase(unittest.TestCase):
    """Base class: a shown 600x400 plot widget with two curves."""

    def setUp(self) -> None:
        """Create, size and show a plot widget with a sine and a ramp.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.plot_widget import PlotWidget
        self.plot_widget = PlotWidget(3)
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
        self.range_list = recorder(self.plot_widget.time_range_changed)
        self.pin_list = recorder(self.plot_widget.tip_pin_requested)

    def tearDown(self) -> None:
        """Close and delete the plot widget.

        Inputs: none.
        Outputs: none.
        """
        self.application.processEvents()
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

    def point_at(self, time_s: float, value_f: float = 0.0):
        """Return the widget point of a data point.

        Inputs:
            time_s: x value in seconds.
            value_f: y value.
        Outputs: QPoint in the widget's coordinates.
        """
        return self.plot_widget.data_to_widget_point(time_s, value_f)

    def press(self, time_s: float, value_f: float, button_i: int = 1,
              double_click_b: bool = False) -> None:
        """Send a matplotlib button press to the canvas at a data point.

        Inputs:
            time_s: x value in seconds.
            value_f: y value.
            button_i: matplotlib button number (1 is the left button).
            double_click_b: True for the second press of a double-click.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseEvent
        display_x_px, display_y_px = (
            self.plot_widget.axes.transData.transform((time_s, value_f)))
        press_event = MouseEvent(
            "button_press_event", self.plot_widget.canvas, display_x_px,
            display_y_px, button=button_i, dblclick=double_click_b)
        self.plot_widget.canvas.callbacks.process("button_press_event",
                                                  press_event)

    def scroll(self, time_s: float, step_i: int) -> None:
        """Send a matplotlib scroll event to the canvas at a time.

        Inputs:
            time_s: x value in seconds under the mouse.
            step_i: wheel steps, positive is forward.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseEvent
        display_x_px, display_y_px = (
            self.plot_widget.axes.transData.transform((time_s, 0.0)))
        scroll_event = MouseEvent(
            "scroll_event", self.plot_widget.canvas, display_x_px,
            display_y_px, button="up" if step_i > 0 else "down",
            step=step_i)
        self.plot_widget.canvas.callbacks.process("scroll_event",
                                                  scroll_event)

    def assert_curves_fit(self, plot_widget=None) -> None:
        """Check that every curve is fully inside the y limits.

        The curves are sampled densely by linear interpolation, as they
        are drawn, over the shown x range.

        Inputs:
            plot_widget: the PlotWidget to check (default: this test's).
        Outputs: none.
        """
        if plot_widget is None:
            plot_widget = self.plot_widget
        start_s, end_s = plot_widget.axes.get_xlim()
        low_f, high_f = plot_widget.axes.get_ylim()
        check_time_array = np.linspace(start_s, end_s,
                                       CURVE_CHECK_SAMPLE_COUNT_I)
        for (signal_name_str, time_array, value_array,
             _color_str, _width_i) in plot_widget.curve_data_list:
            inside_array = ((check_time_array >= time_array[0])
                            & (check_time_array <= time_array[-1]))
            drawn_array = np.interp(check_time_array[inside_array],
                                    time_array, value_array)
            self.assertGreaterEqual(float(np.min(drawn_array)),
                                    low_f - 1e-9, signal_name_str)
            self.assertLessEqual(float(np.max(drawn_array)),
                                 high_f + 1e-9, signal_name_str)


class ClickZoomTest(PlotWidgetToolTestCase):
    """Zoom tool: a left click zooms in by 2 around the clicked time."""

    @covers("LLFR-00078", "LLFR-00109", "LLFR-00076")
    def test_click_halves_range_around_click(self) -> None:
        """Each click halves the width and centres it on the click.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
        for expected_width_s in (5.0, 2.5, 1.25):
            point = self.point_at(4.0)
            clicked_s = self.plot_widget.time_at(point)
            self.plot_widget.click_at(point)
            start_s, end_s = self.plot_widget.time_range_tuple()
            self.assertAlmostEqual(end_s - start_s, expected_width_s)
            self.assertAlmostEqual((start_s + end_s) / 2.0, clicked_s)
            self.assertEqual(self.range_list[-1], (start_s, end_s))
            self.assert_curves_fit()
            self.draw()
        # LLFR-00109: the tool stays in use after every zoom.
        self.assertEqual(self.plot_widget.plot_tool_str, ZOOM_TOOL_STR)
        self.assertEqual(len(self.range_list), 3)
        self.assertEqual(self.pin_list, [])

    @covers("LLFR-00078", "LLFR-00074")
    def test_click_near_edge_stays_inside_data(self) -> None:
        """A click near the start keeps half the width, inside the data.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
        self.plot_widget.click_at(self.point_at(0.5))
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 0.0)
        self.assertAlmostEqual(end_s, 5.0)
        self.plot_widget.set_time_range(0.0, 10.0)
        self.draw()
        self.plot_widget.click_at(self.point_at(9.8))
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 5.0)
        self.assertAlmostEqual(end_s, 10.0)

    @covers("LLFR-00078")
    def test_canvas_press_zooms_and_double_click_zooms_once(self) -> None:
        """A real left press zooms; a double-click zooms only once.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
        self.press(5.0, 0.0)
        self.press(5.0, 0.0, double_click_b=True)
        self.assertEqual(len(self.range_list), 1)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(end_s - start_s, 5.0)
        self.assertAlmostEqual((start_s + end_s) / 2.0, 5.0, delta=0.05)
        # A right press never zooms.
        self.plot_widget.execute_menu = lambda menu, point: None
        self.press(5.0, 0.0, button_i=3)
        self.application.processEvents()
        self.assertEqual(len(self.range_list), 1)

    @covers("LLFR-00078", "LLFR-00042", "LLFR-00080")
    def test_click_zooms_only_with_zoom_tool(self) -> None:
        """With Tip, Vertical marker or no tool a click does not zoom.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (TIP_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.plot_widget.click_at(self.point_at(5.0, 3.5))
                self.press(5.0, 3.5)
                self.assertEqual(self.plot_widget.time_range_tuple(),
                                 (0.0, 10.0))
        self.assertEqual(self.range_list, [])

    @covers("LLFR-00078")
    def test_click_outside_axes_does_not_zoom(self) -> None:
        """A click on the axis labels, outside the axes, does nothing.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
        self.plot_widget.click_at(QPoint(2, WIDGET_HEIGHT_I - 2))
        self.assertEqual(self.range_list, [])
        self.assertEqual(self.plot_widget.time_range_tuple(), (0.0, 10.0))


class WheelZoomTest(PlotWidgetToolTestCase):
    """The mouse wheel zooms the x-axis with any tool or none."""

    @covers("LLFR-00074", "LLFR-00108")
    def test_wheel_zooms_with_every_tool_and_none(self) -> None:
        """Forward narrows and backward widens around the mouse time.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import ZOOM_IN_FACTOR_F
        for tool_str in ALL_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.plot_widget.set_time_range(0.0, 10.0)
                self.draw()
                self.range_list.clear()
                point = self.point_at(3.0)
                mouse_s = self.plot_widget.time_at(point)
                self.plot_widget.wheel_at(point, 1.0)
                start_s, end_s = self.plot_widget.time_range_tuple()
                self.assertAlmostEqual(end_s - start_s,
                                       10.0 * ZOOM_IN_FACTOR_F)
                # The time under the mouse stays where it was.
                self.assertAlmostEqual(
                    (mouse_s - start_s) / (end_s - start_s),
                    mouse_s / 10.0)
                self.draw()
                self.plot_widget.wheel_at(self.point_at(mouse_s), -1.0)
                wide_start_s, wide_end_s = (
                    self.plot_widget.time_range_tuple())
                self.assertAlmostEqual(wide_start_s, 0.0, delta=0.05)
                self.assertAlmostEqual(wide_end_s, 10.0, delta=0.05)
                self.assertEqual(len(self.range_list), 2)
                self.assertEqual(self.plot_widget.plot_tool_str, tool_str)

    @covers("LLFR-00074", "LLFR-00108")
    def test_scroll_event_zooms_with_every_tool(self) -> None:
        """A real scroll event zooms in with each tool and with none.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in ALL_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.plot_widget.set_time_range(0.0, 10.0)
                self.draw()
                self.range_list.clear()
                self.scroll(5.0, 1)
                self.assertEqual(len(self.range_list), 1)
                start_s, end_s = self.range_list[0]
                self.assertLess(end_s - start_s, 10.0)
                self.assertAlmostEqual((start_s + end_s) / 2.0, 5.0,
                                       delta=0.05)


class YAxisTest(PlotWidgetToolTestCase):
    """The y-axis is never zoomed by the user and always fits."""

    @covers("LLFR-00075")
    def test_no_user_path_changes_the_y_axis(self) -> None:
        """No toolbar, no key handler, no navigation; y only fits.

        Inputs: none.
        Outputs: none.
        """
        canvas = self.plot_widget.canvas
        self.assertIsNone(getattr(canvas, "toolbar", None))
        self.assertIsNone(getattr(canvas, "manager", None))
        self.assertFalse(self.plot_widget.axes.get_navigate())
        self.assertEqual(
            len(canvas.callbacks.callbacks.get("key_press_event", {})), 0)
        from matplotlib.backend_bases import KeyEvent
        fitted_tuple = self.plot_widget.axes.get_ylim()
        for key_str in ("o", "p", "l", "k", "h", "r"):
            key_event = KeyEvent("key_press_event", canvas, key_str)
            canvas.callbacks.process("key_press_event", key_event)
        self.assertEqual(self.plot_widget.axes.get_ylim(), fitted_tuple)
        self.assertEqual(self.plot_widget.axes.get_yscale(), "linear")
        # A wheel turn or a zoom click with the mouse high or low in the
        # plot gives the same y range: only x is zoomed.
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
        result_list = []
        for value_f in (-0.9, 3.9):
            self.plot_widget.set_time_range(0.0, 10.0)
            self.draw()
            self.plot_widget.wheel_at(self.point_at(5.0, value_f), 1.0)
            self.plot_widget.click_at(self.point_at(5.0, value_f))
            result_list.append((self.plot_widget.time_range_tuple(),
                                self.plot_widget.axes.get_ylim()))
        self.assertEqual(result_list[0][1], result_list[1][1])
        self.assertAlmostEqual(result_list[0][0][0], result_list[1][0][0],
                               delta=0.05)

    @covers("LLFR-00076", "LLFR-00074", "LLFR-00078")
    def test_curves_fit_after_every_zoom(self) -> None:
        """After wheel, click and shared-range zooms every curve fits.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
        for time_s in (1.0, 2.2, 7.7, 9.5):
            self.plot_widget.wheel_at(self.point_at(time_s), 2.0)
            self.assert_curves_fit()
            self.draw()
            self.plot_widget.click_at(self.point_at(time_s))
            self.assert_curves_fit()
            self.draw()
            self.plot_widget.wheel_at(self.point_at(time_s), -3.0)
            self.assert_curves_fit()
            self.draw()
        for start_s, end_s in ((0.0, 10.0), (1.57, 1.58), (4.0, 7.0)):
            self.plot_widget.set_time_range(start_s, end_s)
            self.assert_curves_fit()

    @covers("LLFR-00076")
    def test_coarse_curve_between_two_samples_fits(self) -> None:
        """A 3-sample curve zoomed between two samples stays visible.

        Inputs: none.
        Outputs: none.
        """
        coarse_time_array = np.array([0.0, 5.0, 10.0])
        coarse_value_array = np.array([0.0, 10.0, 0.0])
        self.plot_widget.set_curves([
            ("Coarse", coarse_time_array, coarse_value_array, RED_STR, 1)])
        self.draw()
        # No sample inside the window: the drawn values are 4 to 6.
        self.plot_widget.set_time_range(2.0, 3.0)
        low_f, high_f = self.plot_widget.axes.get_ylim()
        self.assertLessEqual(low_f, 4.0)
        self.assertGreaterEqual(high_f, 6.0)
        # The range fits the visible part, not the whole curve.
        self.assertGreater(low_f, 0.0)
        self.assertLess(high_f, 10.0)
        self.assert_curves_fit()
        # The window holds the peak and parts of both segments.
        self.plot_widget.set_time_range(4.0, 7.0)
        low_f, high_f = self.plot_widget.axes.get_ylim()
        self.assertLessEqual(low_f, 6.0)
        self.assertGreaterEqual(high_f, 10.0)
        self.assert_curves_fit()
        # With a fine curve as well, both are fitted.
        self.plot_widget.set_curves([
            ("Coarse", coarse_time_array, coarse_value_array, RED_STR, 1),
            ("Sine", self.time_array, self.sine_array, BLUE_STR, 1)])
        self.draw()
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
        for _ in range(4):
            self.plot_widget.click_at(self.point_at(2.4, 4.8))
            self.assert_curves_fit()
            self.draw()

    @covers("LLFR-00076")
    def test_unsorted_coarse_curve_fits(self) -> None:
        """A curve whose time is not sorted is also fitted by segments.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import visible_value_range_tuple
        time_array = np.array([0.0, 10.0, 2.0, 8.0])
        value_array = np.array([0.0, 10.0, -5.0, 3.0])
        self.plot_widget.set_curves([
            ("Zigzag", time_array, value_array, RED_STR, 1)])
        self.plot_widget.set_time_range(4.0, 6.0)
        low_f, high_f = self.plot_widget.axes.get_ylim()
        expected_tuple = visible_value_range_tuple(
            time_array, value_array, 4.0, 6.0, False)
        self.assertLessEqual(low_f, expected_tuple[0])
        self.assertGreaterEqual(high_f, expected_tuple[1])
        # Inside 4..6, segment 0->10 shows 4 to 6, segment 10->2 shows
        # -1.25 to 2.5 and segment 2->8 shows -2.33 to 0.33 (values
        # interpolated at the window's ends).
        self.assertAlmostEqual(expected_tuple[0], -5.0 + 8.0 * 2.0 / 6.0)
        self.assertAlmostEqual(expected_tuple[1], 6.0)

    @covers("LLFR-00076")
    def test_visible_value_range_edge_cases(self) -> None:
        """Empty, single-sample, vertical and outside cases.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import visible_value_range_tuple
        empty_array = np.zeros(0)
        self.assertEqual(visible_value_range_tuple(
            empty_array, empty_array, 0.0, 1.0, True), ())
        one_array = np.array([3.0])
        self.assertEqual(visible_value_range_tuple(
            one_array, np.array([7.0]), 0.0, 5.0, True), (7.0, 7.0))
        self.assertEqual(visible_value_range_tuple(
            one_array, np.array([7.0]), 4.0, 5.0, True), ())
        self.assertEqual(visible_value_range_tuple(
            np.array([1.0, 1.0]), np.array([0.0, 5.0]), 0.0, 2.0, True),
            (0.0, 5.0))
        line_time_array = np.array([0.0, 10.0])
        line_value_array = np.array([0.0, 100.0])
        self.assertEqual(visible_value_range_tuple(
            line_time_array, line_value_array, 11.0, 12.0, True), ())
        self.assertEqual(visible_value_range_tuple(
            line_time_array, line_value_array, 4.0, 6.0, True),
            (40.0, 60.0))


class TipToolTest(PlotWidgetToolTestCase):
    """Hover tips and pinning only work with the Tip tool."""

    @covers("LLFR-00042", "LLFR-00045")
    def test_tip_hover_and_pin_only_with_tip_tool(self) -> None:
        """Zoom, Vertical marker and no tool show no tip and pin nothing.

        Inputs: none.
        Outputs: none.
        """
        ramp_point = self.point_at(5.0, 3.5)
        for tool_str in (ZOOM_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.plot_widget.hover_at(ramp_point)
                self.assertEqual(self.plot_widget.hover_tip_text(), "")
                if tool_str == ZOOM_TOOL_STR:
                    continue
                self.plot_widget.click_at(ramp_point)
        self.assertEqual(self.pin_list, [])
        self.plot_widget.set_time_range(0.0, 10.0)
        self.draw()
        self.range_list.clear()
        self.plot_widget.set_plot_tool(TIP_TOOL_STR)
        self.plot_widget.hover_at(ramp_point)
        self.assertEqual(self.plot_widget.hover_tip_text(),
                         "t = 5 s\nRamp = 3.5")
        self.plot_widget.click_at(ramp_point)
        self.assertEqual(len(self.pin_list), 1)
        self.assertEqual(self.pin_list[0][0], "Ramp")
        # Pinning never zooms and keeps the Tip tool (LLFR-00109).
        self.assertEqual(self.range_list, [])
        self.assertEqual(self.plot_widget.plot_tool_str, TIP_TOOL_STR)

    @covers("LLFR-00042", "LLFR-00079")
    def test_leaving_tip_tool_hides_hover_tip(self) -> None:
        """Switching from Tip to another tool hides the shown tip.

        Inputs: none.
        Outputs: none.
        """
        ramp_point = self.point_at(5.0, 3.5)
        for tool_str in (ZOOM_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(TIP_TOOL_STR)
                self.plot_widget.hover_at(ramp_point)
                self.assertNotEqual(self.plot_widget.hover_tip_text(), "")
                self.plot_widget.set_plot_tool(tool_str)
                self.assertEqual(self.plot_widget.hover_tip_text(), "")
                self.assertFalse(
                    self.plot_widget.hover_annotation.get_visible())

    @covers("LLFR-00042", "LLFR-00079")
    def test_set_tip_mode_never_ends_another_tool(self) -> None:
        """The plot panel's set_tip_mode(False) keeps Zoom or Marker.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (ZOOM_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR):
            self.plot_widget.set_plot_tool(tool_str)
            self.plot_widget.set_tip_mode(False)
            self.assertEqual(self.plot_widget.plot_tool_str, tool_str)
        self.plot_widget.set_tip_mode(True)
        self.assertEqual(self.plot_widget.plot_tool_str, TIP_TOOL_STR)
        self.plot_widget.set_tip_mode(False)
        self.assertEqual(self.plot_widget.plot_tool_str, NO_TOOL_STR)


@requires_qt
class PlotToolEndToEndTest(unittest.TestCase):
    """Buttons, MainWindow, controllers and plots working together."""

    def setUp(self) -> None:
        """Create the window and controllers, open a file, add 2 plots.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from controller.main_controller import MainController
        from model.signal_file import SignalFile
        from view.main_window import MainWindow
        self.main_window = MainWindow()
        self.main_window.resize(1100, 800)
        self.controller = MainController(self.main_window)
        self.controller.start()
        time_array = np.linspace(0.0, 4.0, 41)
        signal_file = SignalFile("memory.csv", {
            "Time": time_array, "speed": time_array * 2.0,
            "force": np.sin(time_array), "angle": np.cos(time_array)})
        self.controller.plot_controller.on_file_opened(signal_file, False)
        self.top_panel = self.main_window.top_panel
        self.main_window.show()
        self.main_window.signal_double_click_handler("speed")
        self.main_window.signal_double_click_handler("force")
        self.process_events()

    def tearDown(self) -> None:
        """Close the window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.process_events()

    def process_events(self) -> None:
        """Let Qt lay out and draw the plots.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(3):
            self.application.processEvents()
        for plot_widget in self.plot_widgets():
            plot_widget.canvas.draw()

    def plot_widgets(self) -> list:
        """Return the plot widgets of the current tab, top to bottom.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        panel = self.main_window.plot_panel
        return list(panel.page_dict[panel.current_tab_id()]
                    .plot_widget_list)

    def assert_tool_everywhere(self, tool_str: str) -> None:
        """Check the tool of the window, the controller and every plot.

        Inputs:
            tool_str: the expected tool name.
        Outputs: none.
        """
        self.assertEqual(self.main_window.current_plot_tool(), tool_str)
        self.assertEqual(self.controller.plot_controller.plot_tool_str,
                         tool_str)
        self.assertEqual(self.top_panel.active_plot_tool(), tool_str)
        for plot_widget in self.plot_widgets():
            self.assertEqual(plot_widget.plot_tool_str, tool_str)

    @covers("LLFR-00079", "LLFR-00002", "LLFR-00042", "LLFR-00078",
            "LLFR-00080")
    def test_buttons_set_the_tool_of_all_plots(self) -> None:
        """Every button change reaches every plot, later plots too.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.assert_tool_everywhere(NO_TOOL_STR)
        for tool_str in (ZOOM_TOOL_STR, MARKER_TOOL_STR, TIP_TOOL_STR):
            QTest.mouseClick(self.top_panel.plot_tool_button_dict[tool_str],
                             Qt.MouseButton.LeftButton)
            self.assert_tool_everywhere(tool_str)
        self.top_panel.zoom_button.click()
        self.assert_tool_everywhere(ZOOM_TOOL_STR)
        self.assertFalse(self.top_panel.tip_button.is_active())
        # A plot created now gets the active tool.
        self.main_window.signal_double_click_handler("angle")
        self.process_events()
        self.assertEqual(len(self.plot_widgets()), 3)
        self.assert_tool_everywhere(ZOOM_TOOL_STR)
        # Clicking the active button again leaves no tool anywhere.
        self.top_panel.zoom_button.click()
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.main_window.signal_double_click_handler("speed")
        self.assert_tool_everywhere(NO_TOOL_STR)

    @covers("LLFR-00078", "LLFR-00070", "LLFR-00109", "LLFR-00076")
    def test_zoom_click_is_shared_by_the_tab(self) -> None:
        """A zoom click in one plot zooms every plot of the tab.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.zoom_button.click()
        first_widget, second_widget = self.plot_widgets()
        point = first_widget.data_to_widget_point(2.0, 4.0)
        clicked_s = first_widget.time_at(point)
        first_widget.click_at(point)
        self.application.processEvents()
        start_s, end_s = first_widget.time_range_tuple()
        self.assertAlmostEqual(end_s - start_s, 2.0)
        self.assertAlmostEqual((start_s + end_s) / 2.0, clicked_s)
        second_start_s, second_end_s = second_widget.time_range_tuple()
        self.assertAlmostEqual(second_start_s, start_s)
        self.assertAlmostEqual(second_end_s, end_s)
        # The y-axis of the other plot fits its own visible curve.
        low_f, high_f = second_widget.axes.get_ylim()
        visible_array = np.sin(np.linspace(start_s, end_s, 201))
        self.assertLessEqual(low_f, float(np.min(visible_array)) + 1e-9)
        self.assertGreaterEqual(high_f, float(np.max(visible_array)) - 1e-9)
        # LLFR-00109: the Zoom button stays active after the zoom.
        self.assertTrue(self.top_panel.zoom_button.is_active())
        self.assert_tool_everywhere(ZOOM_TOOL_STR)
        # A new plot in the tab takes the zoomed range.
        self.main_window.signal_double_click_handler("angle")
        self.process_events()
        third_start_s, third_end_s = self.plot_widgets()[2].time_range_tuple()
        self.assertAlmostEqual(third_start_s, start_s)
        self.assertAlmostEqual(third_end_s, end_s)

    @covers("LLFR-00074", "LLFR-00108", "LLFR-00070")
    def test_wheel_zoom_without_tool_is_shared(self) -> None:
        """With no tool active the wheel still zooms the whole tab.

        Inputs: none.
        Outputs: none.
        """
        self.assert_tool_everywhere(NO_TOOL_STR)
        first_widget, second_widget = self.plot_widgets()
        first_widget.wheel_at(first_widget.data_to_widget_point(2.0, 4.0),
                              1.0)
        self.application.processEvents()
        start_s, end_s = first_widget.time_range_tuple()
        self.assertLess(end_s - start_s, 4.0)
        second_start_s, second_end_s = second_widget.time_range_tuple()
        self.assertAlmostEqual(second_start_s, start_s)
        self.assertAlmostEqual(second_end_s, end_s)
        self.assert_tool_everywhere(NO_TOOL_STR)


if __name__ == "__main__":
    unittest.main()
