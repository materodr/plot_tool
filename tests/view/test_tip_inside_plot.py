"""Tests that pinned tips stay inside their plot (HLFR-00025, HLFR-00041).

Covers LLFR-00179: when a plot changes size (more or fewer plots in the
tab, window resized) or range (zoom, pan), and when a tip drag ends,
each pinned tip whose point is shown is drawn at the position the user
gave it, moved by the shortest distance that keeps its whole box inside
the axes, still joined to its point by the dashed leader line
(LLFR-00151). The stored offset is never changed by this, so the tip
goes back to the user's position when the plot grows again. The issue
#70 steps are reproduced through MainWindow and the real controllers.
No modal dialog or menu is ever opened.
"""

import os
import tempfile
import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt
from tests.view.test_plot_tools import WIDGET_HEIGHT_I, WIDGET_WIDTH_I
from tests.view.test_tip_drag import (
    PIXEL_TOLERANCE_PX, RAMP_TIP_TUPLE, SINE_TIP_TUPLE, TipDragTestCase)

# Allowed error, in display pixels, of a box edge against the axes edge.
EDGE_TOLERANCE_PX = 0.5
# A plot height that leaves the axes too low for the tips of the tests.
SHORT_HEIGHT_I = 150
# Offset (points) that fits above a middle point only in a tall plot.
HIGH_OFFSET_TUPLE = (0.0, 80.0)
# Number of plots in the tab after issue #70's step 4.
FULL_TAB_PLOT_COUNT_I = 5
# Rounds of Qt event processing allowed for a resize to reach the canvas.
RESIZE_EVENT_ROUNDS_I = 50


def tip_box_and_axes_box(plot_widget, tip_index_i: int) -> tuple:
    """Return a pinned tip's label box and the axes box, as drawn.

    Inputs:
        plot_widget: the PlotWidget.
        tip_index_i: index of the tip.
    Outputs: a tuple (label box, axes box) of matplotlib Bboxes in
        display pixels.
    """
    annotation = plot_widget.pinned_tip_annotation(tip_index_i)
    return (plot_widget.tip_box_extent(annotation), plot_widget.axes.bbox)


def label_center_tuple(plot_widget, tip_index_i: int) -> tuple:
    """Return the center of a pinned tip's label box.

    Inputs:
        plot_widget: the PlotWidget.
        tip_index_i: index of the tip.
    Outputs: (x, y) in display pixels.
    """
    return plot_widget.tip_label_center_tuple(tip_index_i)


class TipInsideAssertions:
    """Mixin with the checks shared by the widget and end-to-end tests."""

    def assert_tip_inside(self, plot_widget, tip_index_i: int) -> None:
        """Check that a pinned tip's whole label box is inside the axes.

        Inputs:
            plot_widget: the PlotWidget.
            tip_index_i: index of the tip.
        Outputs: none.
        """
        box, axes_box = tip_box_and_axes_box(plot_widget, tip_index_i)
        self.assertGreaterEqual(box.x0, axes_box.x0 - EDGE_TOLERANCE_PX)
        self.assertLessEqual(box.x1, axes_box.x1 + EDGE_TOLERANCE_PX)
        self.assertGreaterEqual(box.y0, axes_box.y0 - EDGE_TOLERANCE_PX)
        self.assertLessEqual(box.y1, axes_box.y1 + EDGE_TOLERANCE_PX)

    def assert_label_at_offset(self, plot_widget, tip_index_i: int,
                               offset_tuple: tuple) -> None:
        """Check that a label's center is at its offset from its point.

        Inputs:
            plot_widget: the PlotWidget.
            tip_index_i: index of the tip.
            offset_tuple: (x, y) offset in points, y upwards.
        Outputs: none.
        """
        annotation = plot_widget.pinned_tip_annotation(tip_index_i)
        point_array = plot_widget.axes.transData.transform(annotation.xy)
        pixels_per_point_f = plot_widget.pixels_per_point_f()
        center_tuple = label_center_tuple(plot_widget, tip_index_i)
        self.assertAlmostEqual(
            center_tuple[0],
            float(point_array[0]) + offset_tuple[0] * pixels_per_point_f,
            delta=PIXEL_TOLERANCE_PX)
        self.assertAlmostEqual(
            center_tuple[1],
            float(point_array[1]) + offset_tuple[1] * pixels_per_point_f,
            delta=PIXEL_TOLERANCE_PX)


@requires_qt
class InsideShiftTest(unittest.TestCase):
    """The shortest shift of a segment into another (LLFR-00179)."""

    @covers("LLFR-00179")
    def test_shift_is_the_shortest_and_zero_inside(self) -> None:
        """Inside: no shift; outside: just enough; too long: one edge.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import inside_shift_px
        self.assertEqual(inside_shift_px(20.0, 40.0, 0.0, 100.0, True), 0.0)
        self.assertEqual(inside_shift_px(-15.0, 5.0, 0.0, 100.0, True),
                         15.0)
        self.assertEqual(inside_shift_px(90.0, 130.0, 0.0, 100.0, False),
                         -30.0)
        # A box exactly as long as the area fits once shifted.
        self.assertEqual(inside_shift_px(10.0, 110.0, 0.0, 100.0, True),
                         -10.0)
        # Longer than the area: the high or the low ends are aligned.
        self.assertEqual(inside_shift_px(-50.0, 150.0, 0.0, 100.0, True),
                         -50.0)
        self.assertEqual(inside_shift_px(-50.0, 150.0, 0.0, 100.0, False),
                         50.0)


@requires_qt
class TipInsideWidgetTest(TipInsideAssertions, TipDragTestCase):
    """A plot widget whose pinned tips must stay inside its axes."""

    def resize_plot(self, width_i: int, height_i: int) -> None:
        """Resize the plot widget and draw it at the new size.

        Inputs:
            width_i: new width in widget pixels.
            height_i: new height in widget pixels.
        Outputs: none.
        """
        self.plot_widget.resize(width_i, height_i)
        canvas = self.plot_widget.canvas
        for _ in range(RESIZE_EVENT_ROUNDS_I):
            self.application.processEvents()
            if (canvas.width(), canvas.height()) == (width_i, height_i):
                break
        canvas.draw()
        ratio_f = self.plot_widget.pixel_ratio_f()
        self.assertAlmostEqual(
            float(self.plot_widget.figure.bbox.height),
            canvas.height() * ratio_f, delta=1.0,
            msg=f"canvas {canvas.width()}x{canvas.height()}, "
                f"widget {self.plot_widget.width()}x"
                f"{self.plot_widget.height()}")

    def pin_high_ramp_tip(self) -> None:
        """Pin the ramp tip with an offset far above its point.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_pinned_tips([
            RAMP_TIP_TUPLE + (HIGH_OFFSET_TUPLE,), SINE_TIP_TUPLE])
        self.draw()

    @covers("LLFR-00179", "LLFR-00151", "HLFR-00025")
    def test_shrunk_plot_keeps_tips_inside_and_grows_back(self) -> None:
        """A shorter plot moves the label in; a taller one moves it back.

        Inputs: none.
        Outputs: none.
        """
        self.pin_high_ramp_tip()
        # Tall plot: the label is where the user put it.
        self.assert_tip_inside(self.plot_widget, 0)
        self.assert_label_at_offset(self.plot_widget, 0, HIGH_OFFSET_TUPLE)
        self.resize_plot(WIDGET_WIDTH_I, SHORT_HEIGHT_I)
        box, axes_box = tip_box_and_axes_box(self.plot_widget, 0)
        self.assertLess(axes_box.height, WIDGET_HEIGHT_I / 2.0)
        for tip_index_i in range(2):
            self.assert_tip_inside(self.plot_widget, tip_index_i)
            self.assert_leader_connected(tip_index_i)
        # The shortest move: only up and down, against the top edge.
        self.assertAlmostEqual(box.y1, axes_box.y1, delta=EDGE_TOLERANCE_PX)
        self.assertAlmostEqual(label_center_tuple(self.plot_widget, 0)[0],
                               self.point_display(0)[0],
                               delta=PIXEL_TOLERANCE_PX)
        # The stored offset is not changed by the clamping.
        self.assertEqual(self.plot_widget.tip_label_offset_tuple(0),
                         HIGH_OFFSET_TUPLE)
        self.assertEqual(self.plot_widget.pinned_tip_list[0][3],
                         HIGH_OFFSET_TUPLE)
        # Grown again, the label is back at the user's position.
        self.resize_plot(WIDGET_WIDTH_I, WIDGET_HEIGHT_I)
        self.assert_label_at_offset(self.plot_widget, 0, HIGH_OFFSET_TUPLE)
        self.assert_tip_inside(self.plot_widget, 0)
        self.assert_leader_connected(0)

    @covers("LLFR-00179", "LLFR-00045")
    def test_tip_placed_beside_its_point_near_the_top_edge(self) -> None:
        """A tip without offset near a corner stays inside a short plot.

        Inputs: none.
        Outputs: none.
        """
        # The ramp's last samples are at the top right of the axes.
        self.plot_widget.set_pinned_tips([("Ramp", 9.9, 3.99),
                                          ("Ramp", 0.1, 3.01)])
        self.resize_plot(WIDGET_WIDTH_I, SHORT_HEIGHT_I)
        for tip_index_i in range(2):
            self.assert_tip_inside(self.plot_widget, tip_index_i)
            self.assert_leader_connected(tip_index_i)
            self.assertEqual(
                self.plot_widget.tip_label_offset_tuple(tip_index_i), ())

    @covers("LLFR-00179", "LLFR-00151")
    def test_zoom_and_pan_keep_shown_tips_inside(self) -> None:
        """Ranges that put a point near an edge keep its label inside.

        Inputs: none.
        Outputs: none.
        """
        side_offset_tuple = (60.0, 0.0)
        self.plot_widget.set_pinned_tips([
            RAMP_TIP_TUPLE + (side_offset_tuple,),
            SINE_TIP_TUPLE + ((-60.0, 0.0),)])
        self.draw()
        for start_s, end_s in ((0.0, 5.2), (4.9, 10.0), (1.95, 5.05),
                               (0.0, 10.0)):
            self.plot_widget.set_time_range(start_s, end_s)
            self.draw()
            for tip_index_i in range(2):
                point_x_px, point_y_px = self.point_display(tip_index_i)
                if not self.plot_widget.inside_axes_b(point_x_px,
                                                      point_y_px):
                    # Not shown: the sine tip at 2 s for (4.9, 10).
                    self.assertGreater(start_s, 2.0)
                    continue
                self.assert_tip_inside(self.plot_widget, tip_index_i)
                self.assert_leader_connected(tip_index_i)
        # Zoom with the wheel around the ramp tip's point.
        self.plot_widget.wheel_at(self.point_at(5.0, 3.5), 6.0)
        self.draw()
        self.assert_tip_inside(self.plot_widget, 0)
        self.assert_leader_connected(0)
        # Pan with the wheel button so the point gets near the left edge.
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.plot_widget.pan_press_at(self.point_at(start_s + 0.05
                                                    * (end_s - start_s)))
        self.plot_widget.pan_to(self.point_at(5.0, 0.0))
        self.plot_widget.pan_release_at(self.point_at(5.0, 0.0))
        self.draw()
        point_x_px, point_y_px = self.point_display(0)
        if self.plot_widget.inside_axes_b(point_x_px, point_y_px):
            self.assert_tip_inside(self.plot_widget, 0)
            self.assert_leader_connected(0)
        self.assertEqual(self.plot_widget.tip_label_offset_tuple(0),
                         side_offset_tuple)

    @covers("LLFR-00179")
    def test_tip_outside_the_range_is_left_alone(self) -> None:
        """A tip whose point is not shown is not drawn nor moved.

        Inputs: none.
        Outputs: none.
        """
        self.pin_high_ramp_tip()
        self.resize_plot(WIDGET_WIDTH_I, SHORT_HEIGHT_I)
        self.plot_widget.set_time_range(0.0, 2.0)
        self.draw()
        annotation = self.plot_widget.pinned_tip_annotation(0)
        self.assertEqual(tuple(annotation.xyann), HIGH_OFFSET_TUPLE)
        center_tuple = label_center_tuple(self.plot_widget, 0)
        self.assertEqual(self.plot_widget.pinned_tip_at(
            self.plot_widget.display_to_widget_point(*center_tuple)), -1)
        # The sine tip at 2 s is still shown and inside.
        self.assert_tip_inside(self.plot_widget, 1)
        # Shown again, the ramp tip is kept inside.
        self.plot_widget.set_time_range(0.0, 10.0)
        self.draw()
        self.assert_tip_inside(self.plot_widget, 0)

    @covers("LLFR-00179", "LLFR-00152", "LLFR-00151", "HLFR-00041")
    def test_drag_ending_partly_outside_is_drawn_inside(self) -> None:
        """A label dropped half out of the plot is drawn inside it.

        Inputs: none.
        Outputs: none.
        """
        self.drag_label(0.0, 5000.0)
        self.assertEqual(len(self.move_list), 1)
        _, offset_x_f, offset_y_f = self.move_list[0]
        # The dropped position is the one stored, as given by the user.
        self.assertEqual(self.plot_widget.tip_label_offset_tuple(0),
                         (offset_x_f, offset_y_f))
        pixels_per_point_f = self.plot_widget.pixels_per_point_f()
        axes_box = self.plot_widget.axes.bbox
        self.assertAlmostEqual(
            self.point_display(0)[1] + offset_y_f * pixels_per_point_f,
            axes_box.y1, delta=PIXEL_TOLERANCE_PX)
        # The drawn label is moved down just enough to be whole.
        box, axes_box = tip_box_and_axes_box(self.plot_widget, 0)
        self.assert_tip_inside(self.plot_widget, 0)
        self.assertAlmostEqual(box.y1, axes_box.y1, delta=EDGE_TOLERANCE_PX)
        self.assert_leader_connected(0)
        # It can still be grabbed where it is drawn.
        center_tuple = label_center_tuple(self.plot_widget, 0)
        self.assertEqual(self.plot_widget.pinned_tip_at(
            self.plot_widget.display_to_widget_point(*center_tuple)), 0)
        # A second drag from there moves it as usual.
        self.drag_label(-80.0, -60.0)
        self.assertEqual(len(self.move_list), 2)
        self.assert_tip_inside(self.plot_widget, 0)
        self.assert_label_at_offset(self.plot_widget, 0,
                                    self.move_list[1][1:])

    @covers("LLFR-00179")
    def test_tiny_plot_does_not_crash(self) -> None:
        """A plot smaller than the label keeps it at the top-left edges.

        Inputs: none.
        Outputs: none.
        """
        self.pin_high_ramp_tip()
        for width_i, height_i in ((140, 70), (60, 40), (WIDGET_WIDTH_I,
                                                        WIDGET_HEIGHT_I)):
            self.resize_plot(width_i, height_i)
            self.assertEqual(self.plot_widget.pinned_tip_count(), 2)
            for tip_index_i in range(2):
                point_x_px, point_y_px = self.point_display(tip_index_i)
                if not self.plot_widget.inside_axes_b(point_x_px,
                                                      point_y_px):
                    continue
                box, axes_box = tip_box_and_axes_box(self.plot_widget,
                                                     tip_index_i)
                if box.width <= axes_box.width:
                    self.assertGreaterEqual(
                        box.x0, axes_box.x0 - EDGE_TOLERANCE_PX)
                    self.assertLessEqual(box.x1,
                                         axes_box.x1 + EDGE_TOLERANCE_PX)
                else:
                    self.assertAlmostEqual(box.x0, axes_box.x0,
                                           delta=EDGE_TOLERANCE_PX)
                if box.height <= axes_box.height:
                    self.assertGreaterEqual(
                        box.y0, axes_box.y0 - EDGE_TOLERANCE_PX)
                    self.assertLessEqual(box.y1,
                                         axes_box.y1 + EDGE_TOLERANCE_PX)
                else:
                    self.assertAlmostEqual(box.y1, axes_box.y1,
                                           delta=EDGE_TOLERANCE_PX)
        self.assert_label_at_offset(self.plot_widget, 0, HIGH_OFFSET_TUPLE)


@requires_qt
class TipInsideEndToEndTest(TipInsideAssertions, unittest.TestCase):
    """Issue #70's steps through MainWindow and the real controllers."""

    def setUp(self) -> None:
        """Open a CSV with six signals and plot the first one.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QFileDialog
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.temporary_directory = tempfile.TemporaryDirectory()
        path_str = os.path.join(self.temporary_directory.name, "data.csv")
        self.signal_name_list = ["speed", "a", "b", "c", "d"]
        with open(path_str, "w", encoding="utf-8") as csv_file:
            csv_file.write("Time," + ",".join(self.signal_name_list) + "\n")
            for index_i in range(11):
                csv_file.write(f"{index_i},{index_i * 2},{index_i},"
                               f"{-index_i},{index_i % 3},{index_i * 3}\n")
        self.window = MainWindow()
        self.window.resize(1000, 700)
        self.controller = MainController(self.window)
        self.controller.start()
        self.window.show()
        with mock.patch.object(QFileDialog, "getOpenFileName",
                               return_value=(path_str, "")):
            self.window.top_panel.open_file_button.click()
            self.process_events()
        self.window.signal_double_click_handler("speed")
        self.process_events()
        self.plot_controller = self.controller.plot_controller
        self.plot_id_i = self.plot_id_list()[0]
        self.plot_widget = self.window.plot_panel.plot_view(self.plot_id_i)

    def tearDown(self) -> None:
        """Close the window and remove the temporary file.

        Inputs: none.
        Outputs: none.
        """
        self.process_events()
        self.window.close()
        self.window.deleteLater()
        self.process_events()
        self.temporary_directory.cleanup()

    def process_events(self) -> None:
        """Let Qt handle pending events, deferred calls and resizes.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(5):
            self.application.processEvents()

    def plot_id_list(self) -> list:
        """Return the plot ids of the current tab.

        Inputs: none.
        Outputs: list of plot ids, top to bottom.
        """
        return self.window.plot_panel.plot_id_list(
            self.window.current_tab_id())

    def stored_offset_list(self) -> list:
        """Return the label offsets the model stores for the first plot.

        Inputs: none.
        Outputs: list of offset tuples, one per pinned tip.
        """
        plot = self.plot_controller.workspace.find_plot(self.plot_id_i)
        return [tuple(pinned_tip.label_offset_tuple)
                for pinned_tip in plot.pinned_tip_list]

    def draw_first_plot(self) -> None:
        """Process events and draw the first plot at its current size.

        Inputs: none.
        Outputs: none.
        """
        self.process_events()
        self.plot_widget.canvas.draw()

    def pin_tips_near_the_top(self) -> None:
        """Pin a moved tip and an automatic tip near the top of the plot.

        Inputs: none.
        Outputs: none.
        """
        # speed goes from 0 to 20: 18 at 9 s is near the top right.
        self.plot_controller.on_tip_pin(self.plot_id_i, "speed", 5.0, 10.0)
        self.plot_controller.on_pinned_tip_move(
            self.plot_id_i, 0, HIGH_OFFSET_TUPLE[0], HIGH_OFFSET_TUPLE[1])
        self.plot_controller.on_tip_pin(self.plot_id_i, "speed", 9.0, 18.0)
        self.draw_first_plot()
        self.assertEqual(self.plot_widget.pinned_tip_count(), 2)

    @covers("LLFR-00179", "LLFR-00151", "HLFR-00025", "HLFR-00041")
    def test_issue_70_more_plots_keep_the_tip_inside(self) -> None:
        """Four more plots shrink the first; its tips stay inside.

        Inputs: none.
        Outputs: none.
        """
        self.pin_tips_near_the_top()
        tall_height_f = float(self.plot_widget.axes.bbox.height)
        self.assert_label_at_offset(self.plot_widget, 0, HIGH_OFFSET_TUPLE)
        for signal_name_str in self.signal_name_list[1:]:
            self.window.signal_double_click_handler(signal_name_str)
            self.process_events()
        self.assertEqual(len(self.plot_id_list()), FULL_TAB_PLOT_COUNT_I)
        self.assertIs(self.window.plot_panel.plot_view(self.plot_id_i),
                      self.plot_widget)
        self.draw_first_plot()
        self.assertLess(float(self.plot_widget.axes.bbox.height),
                        tall_height_f / 2.0)
        for tip_index_i in range(2):
            self.assert_tip_inside(self.plot_widget, tip_index_i)
        self.assertEqual(self.stored_offset_list(),
                         [HIGH_OFFSET_TUPLE, ()])
        # The plots are deleted again: the tip goes back to its place.
        for plot_id_i in self.plot_id_list()[1:]:
            self.plot_controller.on_plot_delete(plot_id_i)
            self.process_events()
        self.assertEqual(self.plot_id_list(), [self.plot_id_i])
        self.draw_first_plot()
        self.assert_label_at_offset(self.plot_widget, 0, HIGH_OFFSET_TUPLE)
        for tip_index_i in range(2):
            self.assert_tip_inside(self.plot_widget, tip_index_i)
        self.assertEqual(self.stored_offset_list(),
                         [HIGH_OFFSET_TUPLE, ()])

    @covers("LLFR-00179", "HLFR-00025")
    def test_window_resize_keeps_the_tip_inside(self) -> None:
        """A smaller window keeps the tips inside; a larger one restores.

        Inputs: none.
        Outputs: none.
        """
        self.pin_tips_near_the_top()
        self.window.resize(600, 300)
        self.draw_first_plot()
        for tip_index_i in range(2):
            self.assert_tip_inside(self.plot_widget, tip_index_i)
        self.window.resize(1000, 700)
        self.draw_first_plot()
        self.assert_label_at_offset(self.plot_widget, 0, HIGH_OFFSET_TUPLE)
        self.assertEqual(self.stored_offset_list(),
                         [HIGH_OFFSET_TUPLE, ()])


if __name__ == "__main__":
    unittest.main()
