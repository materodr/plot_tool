"""Tests for the plot widget (curves, legend, menus, tips, drop, zoom)."""

import unittest

import numpy as np

from tests.support import covers, get_qt_application, requires_qt

WIDGET_WIDTH_I = 600
WIDGET_HEIGHT_I = 400
RED_STR = "#ff0000"
BLUE_STR = "#0000ff"
GREEN_STR = "#008000"


def menu_action_text_list(menu) -> list:
    """Return the texts of the top-level actions of a menu.

    Inputs:
        menu: a QMenu.
    Outputs: list of action texts, separators left out.
    """
    return [action.text() for action in menu.actions()
            if not action.isSeparator()]


def find_action(menu, text_str: str):
    """Return the action of a menu with the given text.

    Inputs:
        menu: a QMenu.
        text_str: the text of the action.
    Outputs: the QAction, or None when there is none.
    """
    for action in menu.actions():
        if action.text() == text_str:
            return action
    return None


@requires_qt
class PlotWidgetTestCase(unittest.TestCase):
    """Base class: creates a shown 600x400 plot widget for each test."""

    def setUp(self) -> None:
        """Create, size and show a plot widget.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.plot_widget import PlotWidget
        self.plot_widget = PlotWidget(7)
        self.plot_widget.resize(WIDGET_WIDTH_I, WIDGET_HEIGHT_I)
        self.plot_widget.show()
        self.application.processEvents()
        self.time_array = np.linspace(0.0, 10.0, 101)
        self.sine_array = np.sin(self.time_array)
        self.ramp_array = self.time_array * 0.1 + 3.0

    def tearDown(self) -> None:
        """Close and delete the plot widget.

        Inputs: none.
        Outputs: none.
        """
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

    def set_two_curves(self) -> None:
        """Draw a sine (red, width 1) and a ramp (blue, width 3).

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_curves([
            ("Sine", self.time_array, self.sine_array, RED_STR, 1),
            ("Ramp", self.time_array, self.ramp_array, BLUE_STR, 3)])
        self.draw()

    def recorder(self, signal) -> list:
        """Connect a Qt signal to a slot that records its arguments.

        Inputs:
            signal: a bound pyqtSignal.
        Outputs: the list that receives one tuple of arguments per
            emission.
        """
        record_list = []
        signal.connect(lambda *argument_tuple:
                       record_list.append(argument_tuple))
        return record_list

    def sample_point(self, signal_name_str: str, index_i: int):
        """Return the widget point of one sample of a curve.

        Inputs:
            signal_name_str: "Sine" or "Ramp".
            index_i: index of the sample.
        Outputs: QPoint in the widget's coordinates.
        """
        value_array = (self.sine_array if signal_name_str == "Sine"
                       else self.ramp_array)
        return self.plot_widget.data_to_widget_point(
            float(self.time_array[index_i]), float(value_array[index_i]))

    def empty_point(self):
        """Return a point inside the axes far from both curves.

        Inputs: none.
        Outputs: QPoint in the widget's coordinates.
        """
        # The sine stays in [-1, 1] and the ramp in [3, 4]; y = 2 at
        # t = 5 is far from both.
        return self.plot_widget.data_to_widget_point(5.0, 2.0)


class CurveDrawingTest(PlotWidgetTestCase):
    """Curves against time, with the given colors and widths."""

    @covers("LLFR-00068")
    def test_curves_use_time_on_x_axis(self) -> None:
        """Each line's x data is the time array; x label says seconds.

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        line_list = self.plot_widget.axes.get_lines()
        self.assertEqual(len(line_list), 2)
        for line in line_list:
            np.testing.assert_array_equal(line.get_xdata(), self.time_array)
        np.testing.assert_array_equal(line_list[0].get_ydata(),
                                      self.sine_array)
        self.assertIn("(s)", self.plot_widget.axes.get_xlabel())
        self.assertIn("Time", self.plot_widget.axes.get_xlabel())

    @covers("LLFR-00070", "LLFR-00068")
    def test_set_curves_shows_full_time_range(self) -> None:
        """After set_curves the x range covers all the samples.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_time_range(2.0, 3.0)
        self.set_two_curves()
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 0.0)
        self.assertAlmostEqual(end_s, 10.0)

    @covers("LLFR-00041", "LLFR-00052")
    def test_colors_and_widths_are_applied(self) -> None:
        """Lines get the given colors and the preset widths' line widths.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_hex
        from view.plot_widget import WIDTH_PIXELS_DICT
        self.set_two_curves()
        line_list = self.plot_widget.axes.get_lines()
        self.assertEqual(to_hex(line_list[0].get_color()), RED_STR)
        self.assertEqual(to_hex(line_list[1].get_color()), BLUE_STR)
        self.assertEqual(self.plot_widget.curve_line_width("Sine"), 1.0)
        self.assertEqual(self.plot_widget.curve_line_width("Ramp"),
                         WIDTH_PIXELS_DICT[3])
        self.assertEqual(self.plot_widget.curve_line_width("Missing"), 0.0)

    @covers("LLFR-00041", "LLFR-00052")
    def test_higher_preset_is_wider(self) -> None:
        """Width 1 draws 1.0 and each higher preset draws wider.

        Inputs: none.
        Outputs: none.
        """
        width_list = []
        for width_i in range(1, 6):
            self.plot_widget.set_curves([
                ("Sine", self.time_array, self.sine_array, RED_STR,
                 width_i)])
            width_list.append(self.plot_widget.curve_line_width("Sine"))
        self.assertEqual(width_list[0], 1.0)
        self.assertEqual(width_list, sorted(set(width_list)))
        self.assertEqual(len(width_list), 5)

    @covers("LLFR-00068", "LLFR-00036")
    def test_edge_case_data_does_not_crash(self) -> None:
        """Empty list, one sample, constant and large arrays are drawn.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_curves([])
        self.draw()
        self.assertEqual(self.plot_widget.axes.get_lines(), [])
        self.assertEqual(self.plot_widget.legend_entry_list(), [])
        self.plot_widget.set_curves([
            ("One", np.array([2.0]), np.array([5.0]), RED_STR, 1)])
        self.draw()
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertLess(start_s, 2.0)
        self.assertGreater(end_s, 2.0)
        self.plot_widget.set_tip_mode(True)
        self.plot_widget.hover_at(
            self.plot_widget.data_to_widget_point(2.0, 5.0))
        self.assertIn("One = 5", self.plot_widget.hover_tip_text())
        self.plot_widget.set_curves([
            ("Flat", self.time_array, np.full(101, 4.0), RED_STR, 1)])
        self.draw()
        low_f, high_f = self.plot_widget.axes.get_ylim()
        self.assertLess(low_f, 4.0)
        self.assertGreater(high_f, 4.0)
        large_time_array = np.linspace(0.0, 100.0, 1000000)
        self.plot_widget.set_curves([
            ("Big", large_time_array, np.cos(large_time_array), RED_STR,
             1)])
        self.draw()
        self.assertEqual(
            self.plot_widget.curve_at(
                self.plot_widget.data_to_widget_point(
                    float(large_time_array[500000]),
                    float(np.cos(large_time_array[500000])))), "Big")


class LegendTest(PlotWidgetTestCase):
    """Legend above the axes with names in curve colors."""

    @covers("LLFR-00035")
    def test_legend_is_above_axes(self) -> None:
        """The legend's bottom edge is at or above the axes' top edge.

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        renderer = self.plot_widget.canvas.get_renderer()
        legend = self.plot_widget.axes.get_legend()
        self.assertIsNotNone(legend)
        legend_box = legend.get_window_extent(renderer)
        axes_box = self.plot_widget.axes.get_window_extent(renderer)
        self.assertGreaterEqual(legend_box.y0, axes_box.y1)
        # The legend is not clipped by the top of the figure.
        self.assertLessEqual(legend_box.y1,
                             self.plot_widget.figure.bbox.height + 1.0)

    @covers("LLFR-00035")
    def test_legend_stays_above_after_resize(self) -> None:
        """With many curves and a small widget the legend stays above.

        Inputs: none.
        Outputs: none.
        """
        curve_list = [(f"Signal {index_i}", self.time_array,
                       self.sine_array + index_i, RED_STR, 1)
                      for index_i in range(9)]
        self.plot_widget.set_curves(curve_list)
        self.plot_widget.resize(300, 300)
        self.draw()
        renderer = self.plot_widget.canvas.get_renderer()
        legend_box = self.plot_widget.axes.get_legend().get_window_extent(
            renderer)
        axes_box = self.plot_widget.axes.get_window_extent(renderer)
        self.assertGreaterEqual(legend_box.y0, axes_box.y1)
        self.assertEqual(len(self.plot_widget.legend_entry_list()), 9)

    @covers("LLFR-00036", "LLFR-00037")
    def test_legend_names_and_colors(self) -> None:
        """Legend entries list the names in order in the curve colors.

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        self.assertEqual(self.plot_widget.legend_entry_list(),
                         [("Sine", RED_STR), ("Ramp", BLUE_STR)])

    @covers("LLFR-00036")
    def test_no_legend_without_curves(self) -> None:
        """Removing all curves removes the legend.

        Inputs: none.
        Outputs: none.
        """
        self.assertIsNone(self.plot_widget.axes.get_legend())
        self.set_two_curves()
        self.plot_widget.set_curves([])
        self.draw()
        self.assertIsNone(self.plot_widget.axes.get_legend())
        self.assertEqual(self.plot_widget.legend_entry_list(), [])


class HitTestTest(PlotWidgetTestCase):
    """Coordinate conversion and finding curves under a point."""

    @covers("LLFR-00038", "LLFR-00042")
    def test_curve_found_at_its_samples(self) -> None:
        """curve_at finds each curve at its own samples, "" far away.

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        for index_i in (1, 25, 50, 99):
            self.assertEqual(self.plot_widget.curve_at(
                self.sample_point("Sine", index_i)), "Sine")
            self.assertEqual(self.plot_widget.curve_at(
                self.sample_point("Ramp", index_i)), "Ramp")
        self.assertEqual(self.plot_widget.curve_at(self.empty_point()), "")

    @covers("LLFR-00038")
    def test_curve_found_between_samples(self) -> None:
        """A point on a segment between two samples hits the curve.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.set_two_curves()
        first_point = self.sample_point("Ramp", 40)
        second_point = self.sample_point("Ramp", 41)
        middle_point = QPoint((first_point.x() + second_point.x()) // 2,
                              (first_point.y() + second_point.y()) // 2)
        self.assertEqual(self.plot_widget.curve_at(middle_point), "Ramp")

    @covers("LLFR-00038", "LLFR-00048")
    def test_points_outside_axes_hit_nothing(self) -> None:
        """Points outside the axes area are never on a curve.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.set_two_curves()
        self.assertEqual(self.plot_widget.curve_at(QPoint(1, 1)), "")
        self.assertEqual(self.plot_widget.curve_at(QPoint(-50, -50)), "")

    @covers("LLFR-00042")
    def test_tolerance_in_pixels(self) -> None:
        """A point a few pixels off hits; one far off does not.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        from view.plot_widget import PICK_TOLERANCE_PIXELS_I
        self.set_two_curves()
        sample_point = self.sample_point("Ramp", 50)
        near_point = QPoint(sample_point.x(), sample_point.y()
                            + PICK_TOLERANCE_PIXELS_I // 2)
        far_point = QPoint(sample_point.x(), sample_point.y()
                           + PICK_TOLERANCE_PIXELS_I * 5)
        self.assertEqual(self.plot_widget.curve_at(near_point), "Ramp")
        self.assertEqual(self.plot_widget.curve_at(far_point), "")


class ContextMenuTest(PlotWidgetTestCase):
    """Right-click menus on curves, pinned tips and empty areas."""

    @covers("LLFR-00038", "LLFR-00039")
    def test_curve_menu_delete_signal(self) -> None:
        """"Delete signal" on a curve emits curve_delete_requested(name).

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        record_list = self.recorder(self.plot_widget.curve_delete_requested)
        menu = self.plot_widget.build_context_menu(
            self.sample_point("Ramp", 30))
        self.assertEqual(menu_action_text_list(menu),
                         ["Delete signal", "Width"])
        find_action(menu, "Delete signal").trigger()
        self.assertEqual(record_list, [("Ramp",)])

    @covers("LLFR-00040", "LLFR-00041")
    def test_curve_menu_width_submenu(self) -> None:
        """"Width" lists 1..5, checks the current one and emits choices.

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        record_list = self.recorder(self.plot_widget.curve_width_requested)
        menu = self.plot_widget.build_context_menu(
            self.sample_point("Ramp", 30))
        width_menu = find_action(menu, "Width").menu()
        self.assertIsNotNone(width_menu)
        self.assertEqual(menu_action_text_list(width_menu),
                         ["1", "2", "3", "4", "5"])
        checked_list = [action.text() for action in width_menu.actions()
                        if action.isChecked()]
        self.assertEqual(checked_list, ["3"])
        find_action(width_menu, "5").trigger()
        find_action(width_menu, "1").trigger()
        self.assertEqual(record_list, [("Ramp", 5), ("Ramp", 1)])

    @covers("LLFR-00041")
    def test_width_change_redraws_wider(self) -> None:
        """Redrawing with the chosen preset changes the line width.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import WIDTH_PIXELS_DICT
        self.set_two_curves()
        self.plot_widget.set_curves([
            ("Sine", self.time_array, self.sine_array, RED_STR, 5),
            ("Ramp", self.time_array, self.ramp_array, BLUE_STR, 3)])
        self.assertEqual(self.plot_widget.curve_line_width("Sine"),
                         WIDTH_PIXELS_DICT[5])
        self.assertGreater(self.plot_widget.curve_line_width("Sine"),
                           WIDTH_PIXELS_DICT[1])

    @covers("LLFR-00048", "LLFR-00049")
    def test_empty_area_menu_delete_plot(self) -> None:
        """"Delete plot" on an empty area emits plot_delete_requested.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.set_two_curves()
        record_list = self.recorder(self.plot_widget.plot_delete_requested)
        menu = self.plot_widget.build_context_menu(self.empty_point())
        self.assertEqual(menu_action_text_list(menu), ["Delete plot"])
        find_action(menu, "Delete plot").trigger()
        self.assertEqual(record_list, [()])
        # Outside the axes (margins) is also an empty area of the plot.
        margin_menu = self.plot_widget.build_context_menu(QPoint(2, 2))
        self.assertEqual(menu_action_text_list(margin_menu),
                         ["Delete plot"])

    @covers("LLFR-00048")
    def test_menu_of_plot_without_curves(self) -> None:
        """A plot with no curves still offers "Delete plot".

        Inputs: none.
        Outputs: none.
        """
        self.draw()
        menu = self.plot_widget.build_context_menu(
            self.plot_widget.data_to_widget_point(0.5, 0.5))
        self.assertEqual(menu_action_text_list(menu), ["Delete plot"])

    @covers("LLFR-00046", "LLFR-00047")
    def test_pinned_tip_menu_delete(self) -> None:
        """"Delete" on a pinned tip emits its index; it beats the curve.

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        self.plot_widget.set_pinned_tips([
            ("Sine", float(self.time_array[20]),
             float(self.sine_array[20])),
            ("Ramp", float(self.time_array[70]),
             float(self.ramp_array[70]))])
        self.draw()
        record_list = self.recorder(
            self.plot_widget.pinned_tip_delete_requested)
        tip_point = self.sample_point("Ramp", 70)
        self.assertEqual(self.plot_widget.pinned_tip_at(tip_point), 1)
        self.assertEqual(self.plot_widget.pinned_tip_at(
            self.sample_point("Sine", 20)), 0)
        menu = self.plot_widget.build_context_menu(tip_point)
        self.assertEqual(menu_action_text_list(menu), ["Delete"])
        find_action(menu, "Delete").trigger()
        self.assertEqual(record_list, [(1,)])
        # Elsewhere on the curve the curve menu is shown.
        self.assertEqual(self.plot_widget.pinned_tip_at(
            self.sample_point("Ramp", 5)), -1)
        curve_menu = self.plot_widget.build_context_menu(
            self.sample_point("Ramp", 5))
        self.assertIn("Delete signal", menu_action_text_list(curve_menu))

    @covers("LLFR-00046")
    def test_pinned_tip_hit_on_its_box(self) -> None:
        """A click on the tip's text box also hits the pinned tip.

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        self.plot_widget.set_pinned_tips([
            ("Sine", float(self.time_array[20]),
             float(self.sine_array[20]))])
        self.draw()
        renderer = self.plot_widget.canvas.get_renderer()
        box = self.plot_widget.pinned_annotation_list[0].get_window_extent(
            renderer)
        box_point = self.plot_widget.display_to_widget_point(
            (box.x0 + box.x1) / 2.0, (box.y0 + box.y1) / 2.0)
        self.assertEqual(self.plot_widget.pinned_tip_at(box_point), 0)


class TipTest(PlotWidgetTestCase):
    """Hover tips in tip mode and pinning them."""

    @covers("LLFR-00042", "LLFR-00043", "LLFR-00044")
    def test_hover_tip_only_in_tip_mode(self) -> None:
        """No tip when off; time in s and value when on; hidden off again.

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        ramp_point = self.sample_point("Ramp", 50)
        self.plot_widget.hover_at(ramp_point)
        self.assertEqual(self.plot_widget.hover_tip_text(), "")
        self.plot_widget.set_tip_mode(True)
        self.plot_widget.hover_at(ramp_point)
        tip_text_str = self.plot_widget.hover_tip_text()
        self.assertEqual(tip_text_str, "t = 5 s\nRamp = 3.5")
        self.assertTrue(self.plot_widget.hover_annotation.get_visible())
        self.plot_widget.set_tip_mode(False)
        self.assertEqual(self.plot_widget.hover_tip_text(), "")
        self.assertFalse(self.plot_widget.hover_annotation.get_visible())

    @covers("LLFR-00042")
    def test_hover_tip_hides_off_curve(self) -> None:
        """Moving away from the curves hides the tip.

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        self.plot_widget.set_tip_mode(True)
        self.plot_widget.hover_at(self.sample_point("Sine", 10))
        self.assertTrue(self.plot_widget.hover_tip_text().startswith("t = "))
        self.plot_widget.hover_at(self.empty_point())
        self.assertEqual(self.plot_widget.hover_tip_text(), "")

    @covers("LLFR-00043", "LLFR-00044")
    def test_tip_values_as_stored(self) -> None:
        """The tip shows the sample's time in s and its raw value.

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        self.plot_widget.set_tip_mode(True)
        self.plot_widget.hover_at(self.sample_point("Sine", 13))
        expected_str = (f"t = {self.time_array[13]:.6g} s\n"
                        f"Sine = {self.sine_array[13]:.6g}")
        self.assertEqual(self.plot_widget.hover_tip_text(), expected_str)

    @covers("LLFR-00045")
    def test_click_pins_shown_tip(self) -> None:
        """A left click while a tip is shown emits tip_pin_requested.

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        record_list = self.recorder(self.plot_widget.tip_pin_requested)
        ramp_point = self.sample_point("Ramp", 50)
        self.plot_widget.click_at(ramp_point)
        self.assertEqual(record_list, [])
        self.plot_widget.set_tip_mode(True)
        self.plot_widget.click_at(self.empty_point())
        self.assertEqual(record_list, [])
        self.plot_widget.hover_at(ramp_point)
        self.plot_widget.click_at(ramp_point)
        self.assertEqual(len(record_list), 1)
        name_str, time_s, value_f = record_list[0]
        self.assertEqual(name_str, "Ramp")
        self.assertAlmostEqual(time_s, 5.0)
        self.assertAlmostEqual(value_f, 3.5)

    @covers("LLFR-00045", "LLFR-00047")
    def test_set_pinned_tips_draws_annotations(self) -> None:
        """set_pinned_tips draws one annotation per tip and replaces them.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.text import Annotation
        self.set_two_curves()
        self.plot_widget.set_pinned_tips([("Sine", 1.0, 0.5),
                                          ("Ramp", 2.0, 3.2)])
        self.draw()
        self.assertEqual(self.plot_widget.pinned_tip_count(), 2)
        text_list = [child.get_text()
                     for child in self.plot_widget.axes.get_children()
                     if isinstance(child, Annotation)
                     and child.get_visible()]
        self.assertIn("t = 1 s\nSine = 0.5", text_list)
        self.assertIn("t = 2 s\nRamp = 3.2", text_list)
        self.plot_widget.set_pinned_tips([("Ramp", 2.0, 3.2)])
        self.draw()
        self.assertEqual(self.plot_widget.pinned_tip_count(), 1)
        self.plot_widget.set_pinned_tips([])
        self.assertEqual(self.plot_widget.pinned_tip_count(), 0)

    @covers("LLFR-00045")
    def test_pinned_tips_survive_set_curves(self) -> None:
        """Redrawing the curves keeps the pinned tips drawn.

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        self.plot_widget.set_pinned_tips([("Sine", 1.0, 0.5)])
        self.set_two_curves()
        self.assertEqual(self.plot_widget.pinned_tip_count(), 1)


class DropTest(PlotWidgetTestCase):
    """Dropping signal names from the signal list."""

    def mime_data(self, signal_b: bool, name_str: str):
        """Build drag data.

        Inputs:
            signal_b: True to add the signal MIME type.
            name_str: the signal name.
        Outputs: a QMimeData with the name as text, and with the signal
            type when signal_b is True.
        """
        from PyQt6.QtCore import QByteArray, QMimeData
        from view.plot_widget import SIGNAL_MIME_TYPE_STR
        mime_data = QMimeData()
        mime_data.setText(name_str)
        if signal_b:
            mime_data.setData(SIGNAL_MIME_TYPE_STR,
                              QByteArray(name_str.encode("utf-8")))
        return mime_data

    def drag_events_tuple(self, mime_data) -> tuple:
        """Build drag-enter, drag-move and drop events over the plot.

        Inputs:
            mime_data: the QMimeData carried by the drag.
        Outputs: a tuple (enter event, move event, drop event).
        """
        from PyQt6.QtCore import QPoint, QPointF, Qt
        from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
        center_point = QPoint(WIDGET_WIDTH_I // 2, WIDGET_HEIGHT_I // 2)
        action = Qt.DropAction.CopyAction
        no_button = Qt.MouseButton.NoButton
        no_modifier = Qt.KeyboardModifier.NoModifier
        enter_event = QDragEnterEvent(center_point, action, mime_data,
                                      no_button, no_modifier)
        move_event = QDragMoveEvent(center_point, action, mime_data,
                                    no_button, no_modifier)
        drop_event = QDropEvent(QPointF(center_point), action, mime_data,
                                no_button, no_modifier)
        return enter_event, move_event, drop_event

    @covers("LLFR-00021")
    def test_signal_drop_emits_name(self) -> None:
        """A drag with the signal type is accepted and its name emitted.

        Inputs: none.
        Outputs: none.
        """
        record_list = self.recorder(self.plot_widget.signal_dropped)
        self.assertTrue(self.plot_widget.acceptDrops())
        enter_event, move_event, drop_event = self.drag_events_tuple(
            self.mime_data(True, "Time"))
        self.plot_widget.dragEnterEvent(enter_event)
        self.assertTrue(enter_event.isAccepted())
        self.plot_widget.dragMoveEvent(move_event)
        self.assertTrue(move_event.isAccepted())
        self.plot_widget.dropEvent(drop_event)
        self.assertTrue(drop_event.isAccepted())
        self.assertEqual(record_list, [("Time",)])

    @covers("LLFR-00021")
    def test_plain_text_drop_is_rejected(self) -> None:
        """A drag with plain text only is ignored and emits nothing.

        Inputs: none.
        Outputs: none.
        """
        record_list = self.recorder(self.plot_widget.signal_dropped)
        enter_event, move_event, drop_event = self.drag_events_tuple(
            self.mime_data(False, "Sine"))
        self.plot_widget.dragEnterEvent(enter_event)
        self.assertFalse(enter_event.isAccepted())
        self.plot_widget.dragMoveEvent(move_event)
        self.assertFalse(move_event.isAccepted())
        self.plot_widget.dropEvent(drop_event)
        self.assertFalse(drop_event.isAccepted())
        self.assertEqual(record_list, [])

    @covers("LLFR-00021")
    def test_repeated_drop_is_reported_each_time(self) -> None:
        """The widget emits every drop; duplicates are the controller's.

        Inputs: none.
        Outputs: none.
        """
        record_list = self.recorder(self.plot_widget.signal_dropped)
        for _ in range(2):
            drop_event = self.drag_events_tuple(
                self.mime_data(True, "Sine"))[2]
            self.plot_widget.dropEvent(drop_event)
        self.assertEqual(record_list, [("Sine",), ("Sine",)])


class TimeRangeTest(PlotWidgetTestCase):
    """Programmatic and user changes of the time range."""

    @covers("LLFR-00070")
    def test_set_time_range_does_not_emit(self) -> None:
        """set_time_range changes the shown range silently.

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        record_list = self.recorder(self.plot_widget.time_range_changed)
        self.plot_widget.set_time_range(2.0, 4.0)
        start_s, end_s = self.plot_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 2.0)
        self.assertAlmostEqual(end_s, 4.0)
        self.assertEqual(record_list, [])

    @covers("LLFR-00070")
    def test_y_axis_fits_visible_data(self) -> None:
        """With a narrow time range the y-axis fits the visible values.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_curves([
            ("Ramp", self.time_array, self.ramp_array, BLUE_STR, 1)])
        self.plot_widget.set_time_range(0.0, 1.0)
        low_f, high_f = self.plot_widget.axes.get_ylim()
        self.assertLessEqual(low_f, 3.0)
        self.assertGreaterEqual(high_f, 3.1)
        self.assertLess(high_f, 3.5)

    @covers("LLFR-00070")
    def test_wheel_zoom_emits_narrower_range(self) -> None:
        """Wheel up narrows the range around the mouse and emits it.

        Inputs: none.
        Outputs: none.
        """
        self.set_two_curves()
        record_list = self.recorder(self.plot_widget.time_range_changed)
        center_point = self.plot_widget.data_to_widget_point(5.0, 0.0)
        self.plot_widget.wheel_at(center_point, 1.0)
        self.assertEqual(len(record_list), 1)
        start_s, end_s = record_list[0]
        self.assertLess(end_s - start_s, 10.0)
        self.assertGreater(start_s, 0.0)
        self.assertLess(end_s, 10.0)
        self.assertAlmostEqual((start_s + end_s) / 2.0, 5.0, delta=0.1)
        self.assertEqual(self.plot_widget.time_range_tuple(),
                         (start_s, end_s))
        # Wheel down widens it again.
        self.plot_widget.wheel_at(center_point, -1.0)
        wide_start_s, wide_end_s = record_list[1]
        self.assertGreater(wide_end_s - wide_start_s, end_s - start_s)

    @covers("LLFR-00070")
    def test_scroll_event_runs_zoom(self) -> None:
        """A matplotlib scroll event on the canvas zooms the time axis.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseEvent
        self.set_two_curves()
        record_list = self.recorder(self.plot_widget.time_range_changed)
        display_x_px, display_y_px = (
            self.plot_widget.axes.transData.transform((5.0, 0.0)))
        scroll_event = MouseEvent("scroll_event", self.plot_widget.canvas,
                                  display_x_px, display_y_px, button="up",
                                  step=1)
        self.plot_widget.canvas.callbacks.process("scroll_event",
                                                  scroll_event)
        self.assertEqual(len(record_list), 1)
        start_s, end_s = record_list[0]
        self.assertLess(end_s - start_s, 10.0)

    @covers("LLFR-00042")
    def test_motion_event_runs_hover(self) -> None:
        """A matplotlib motion event over a curve shows the hover tip.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseEvent
        self.set_two_curves()
        self.plot_widget.set_tip_mode(True)
        display_x_px, display_y_px = (
            self.plot_widget.axes.transData.transform(
                (float(self.time_array[50]), float(self.ramp_array[50]))))
        motion_event = MouseEvent("motion_notify_event",
                                  self.plot_widget.canvas, display_x_px,
                                  display_y_px)
        self.plot_widget.canvas.callbacks.process("motion_notify_event",
                                                  motion_event)
        self.assertEqual(self.plot_widget.hover_tip_text(),
                         "t = 5 s\nRamp = 3.5")


if __name__ == "__main__":
    unittest.main()
