"""Tests for frequency plots in the window (HLFR-00058, needs PyQt6).

The first tests check a frequency PlotWidget on its own: its x-axis
label, curves in Hz, zoom and pan limits, the absence of vertical
markers and of their preview, and the texts of its data tips and Delta
X markers. The end-to-end tests open a CSV file with a sine in the main
window, create its FFT through the signal list menu and plot it.
"""

import os
import tempfile
import unittest
from unittest import mock

import numpy as np

from tests.support import covers, get_qt_application, requires_qt

from controller.plot_tools import (
    MARKER_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR)
from model.workspace import FREQUENCY_PLOT_KIND_STR, TIME_PLOT_KIND_STR

WIDGET_WIDTH_I = 600
WIDGET_HEIGHT_I = 400
BLUE_STR = "#0000ff"
# The end-to-end file: a sine of amplitude 1.5 at 2 Hz, sampled at
# 50 Hz for 10 s, so the FFT goes from 0 Hz to 25 Hz in 0.1 Hz steps.
SINE_FREQUENCY_HZ = 2.0
SINE_AMPLITUDE_F = 1.5
SAMPLE_RATE_HZ = 50.0
SAMPLE_COUNT_I = 500


def find_action(menu, text_str: str):
    """Return the action of a menu, or of its submenus, with a text.

    Inputs:
        menu: a QMenu.
        text_str: the text of the action.
    Outputs: the QAction, or None when there is none.
    """
    for action in menu.actions():
        if action.text() == text_str:
            return action
        if action.menu() is not None:
            found_action = find_action(action.menu(), text_str)
            if found_action is not None:
                return found_action
    return None


@requires_qt
class FrequencyPlotWidgetTest(unittest.TestCase):
    """A frequency PlotWidget on its own."""

    def setUp(self) -> None:
        """Create a shown frequency plot with one FFT-like curve.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.plot_widget import PlotWidget
        self.plot_widget = PlotWidget(3, kind_str=FREQUENCY_PLOT_KIND_STR)
        self.plot_widget.resize(WIDGET_WIDTH_I, WIDGET_HEIGHT_I)
        self.plot_widget.show()
        self.application.processEvents()
        self.frequency_array = np.linspace(0.0, 25.0, 251)
        self.amplitude_array = np.exp(-(self.frequency_array - 2.0) ** 2)
        self.plot_widget.set_curves([
            ("fft_Speed", self.frequency_array, self.amplitude_array,
             BLUE_STR, 1)])
        self.draw()

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

    def recorder(self, signal) -> list:
        """Connect a Qt signal to a slot that records its arguments.

        Inputs:
            signal: a bound pyqtSignal.
        Outputs: the list that receives one tuple per emission.
        """
        record_list = []
        signal.connect(lambda *argument_tuple:
                       record_list.append(argument_tuple))
        return record_list

    def sample_point(self, index_i: int):
        """Return the widget point of one sample of the curve.

        Inputs:
            index_i: index of the sample.
        Outputs: QPoint in the widget's coordinates.
        """
        return self.plot_widget.data_to_widget_point(
            float(self.frequency_array[index_i]),
            float(self.amplitude_array[index_i]))

    @covers("LLFR-00256", "LLFR-00068", "HLFR-00058")
    def test_axis_label_and_curve_in_hz(self) -> None:
        """The x-axis says Hz and the curve is drawn against frequency.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import PlotWidget
        self.assertTrue(self.plot_widget.frequency_plot_b)
        self.assertEqual(self.plot_widget.axes.get_xlabel(),
                         "Frequency (Hz)")
        line = self.plot_widget.curve_line_dict["fft_Speed"]
        np.testing.assert_allclose(line.get_xdata(), self.frequency_array)
        self.assertEqual(self.plot_widget.time_range_tuple(), (0.0, 25.0))
        # A time plot keeps its label; the kind is chosen at creation.
        time_widget = PlotWidget(4, kind_str=TIME_PLOT_KIND_STR)
        self.assertFalse(time_widget.frequency_plot_b)
        self.assertEqual(time_widget.axes.get_xlabel(), "Time (s)")
        time_widget.deleteLater()

    @covers("LLFR-00258", "LLFR-00074", "LLFR-00113", "LLFR-00078")
    def test_wheel_and_click_zoom_stay_in_the_frequency_range(self) -> None:
        """Zoom out stops at 0 Hz to the highest frequency.

        Inputs: none.
        Outputs: none.
        """
        range_list = self.recorder(self.plot_widget.time_range_changed)
        center_point = self.sample_point(20)
        self.plot_widget.wheel_at(center_point, -3.0)
        self.assertEqual(range_list, [])
        self.assertEqual(self.plot_widget.time_range_tuple(), (0.0, 25.0))
        self.plot_widget.wheel_at(center_point, 1.0)
        self.assertEqual(len(range_list), 1)
        start_hz, end_hz = range_list[0]
        self.assertAlmostEqual(end_hz - start_hz, 25.0 * 0.95)
        self.assertGreaterEqual(start_hz, 0.0)
        self.assertLessEqual(end_hz, 25.0)
        self.plot_widget.wheel_at(center_point, -5.0)
        self.assertEqual(range_list[-1], (0.0, 25.0))

    @covers("LLFR-00258", "LLFR-00117", "LLFR-00118", "LLFR-00119")
    def test_pan_stays_in_the_frequency_range(self) -> None:
        """A pan never goes below 0 Hz or above the highest frequency.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        range_list = self.recorder(self.plot_widget.time_range_changed)
        # LLFR-00118: no pan at the whole range.
        start_point = self.sample_point(100)
        self.plot_widget.pan_press_at(start_point)
        self.plot_widget.pan_to(QPoint(start_point.x() + 50,
                                       start_point.y()))
        self.plot_widget.pan_release_at(QPoint(start_point.x() + 50,
                                               start_point.y()))
        self.assertEqual(range_list, [])
        self.plot_widget.set_time_range(10.0, 15.0)
        self.draw()
        start_point = self.plot_widget.data_to_widget_point(12.5, 0.0)
        self.plot_widget.pan_press_at(start_point)
        self.plot_widget.pan_to(QPoint(start_point.x() + 5000,
                                       start_point.y()))
        self.plot_widget.pan_release_at(QPoint(start_point.x() + 5000,
                                               start_point.y()))
        self.assertAlmostEqual(range_list[-1][0], 0.0)
        self.assertAlmostEqual(range_list[-1][1], 5.0)

    def axes_edge_point(self, right_b: bool, outside_px_i: int):
        """Return a widget point beside the left or right axes edge.

        Inputs:
            right_b: True for the right edge, False for the left one.
            outside_px_i: widget pixels beyond the edge.
        Outputs: QPoint in the widget's coordinates, at mid height.
        """
        from PyQt6.QtCore import QPoint
        box = self.plot_widget.axes.bbox
        edge_point = self.plot_widget.display_to_widget_point(
            box.x1 if right_b else box.x0, (box.y0 + box.y1) / 2.0)
        offset_i = outside_px_i if right_b else -outside_px_i
        return QPoint(edge_point.x() + offset_i, edge_point.y())

    def span_zoom(self, press_point, release_point) -> None:
        """Select a span with the Zoom tool, from a press to a release.

        Inputs:
            press_point: QPoint of the press, on the drawing area.
            release_point: QPoint of the release.
        Outputs: none.
        """
        self.plot_widget.span_press_at(press_point)
        self.plot_widget.span_drag_to(release_point)
        self.plot_widget.span_release_at(release_point)
        self.draw()

    @covers("LLFR-00258", "LLFR-00209", "LLFR-00208")
    def test_span_zoom_stays_in_the_frequency_range(self) -> None:
        """A span dragged past an edge stops at 0 Hz or at the highest
        frequency.

        Inputs: none.
        Outputs: none.
        """
        range_list = self.recorder(self.plot_widget.time_range_changed)
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
        # At the whole range, the edges are 0 Hz and 25 Hz.
        self.span_zoom(self.plot_widget.data_to_widget_point(10.0, 0.5),
                       self.axes_edge_point(False, 40))
        self.assertEqual(len(range_list), 1)
        start_hz, end_hz = range_list[-1]
        self.assertAlmostEqual(start_hz, 0.0, places=9)
        self.assertAlmostEqual(end_hz, 10.0, delta=0.2)
        self.plot_widget.set_time_range(0.0, 25.0)
        self.draw()
        self.span_zoom(self.plot_widget.data_to_widget_point(15.0, 0.5),
                       self.axes_edge_point(True, 40))
        start_hz, end_hz = range_list[-1]
        self.assertAlmostEqual(start_hz, 15.0, delta=0.2)
        self.assertAlmostEqual(end_hz, 25.0, places=9)
        # Shown wider than its frequency range, the span is still cut
        # to 0 Hz and to the highest frequency.
        self.plot_widget.set_time_range(-10.0, 35.0)
        self.draw()
        self.span_zoom(self.plot_widget.data_to_widget_point(10.0, 0.5),
                       self.axes_edge_point(False, 40))
        self.assertEqual(range_list[-1][0], 0.0)
        self.assertAlmostEqual(range_list[-1][1], 10.0, delta=0.3)
        self.plot_widget.set_time_range(-10.0, 35.0)
        self.draw()
        self.span_zoom(self.plot_widget.data_to_widget_point(15.0, 0.5),
                       self.axes_edge_point(True, 40))
        self.assertAlmostEqual(range_list[-1][0], 15.0, delta=0.3)
        self.assertEqual(range_list[-1][1], 25.0)
        self.assertEqual(self.plot_widget.time_range_tuple(),
                         range_list[-1])

    @covers("LLFR-00259", "LLFR-00203", "LLFR-00205", "LLFR-00081")
    def test_no_marker_and_no_preview(self) -> None:
        """Markers are not drawn, previewed or placed on the plot.

        Inputs: none.
        Outputs: none.
        """
        place_list = self.recorder(self.plot_widget.marker_place_requested)
        preview_list = self.recorder(
            self.plot_widget.marker_preview_changed)
        self.plot_widget.set_markers([(1, "Marker 1", 2.0)])
        self.draw()
        self.assertEqual(self.plot_widget.marker_count(), 0)
        self.assertEqual(self.plot_widget.marker_id_list(), [])
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        point = self.plot_widget.data_to_widget_point(5.0, 0.5)
        self.plot_widget.update_marker_preview(point)
        self.assertFalse(self.plot_widget.marker_preview_shown())
        # The preview of a time plot of the tab is not shown here either.
        self.plot_widget.show_marker_preview(5.0)
        self.assertFalse(self.plot_widget.marker_preview_shown())
        self.plot_widget.press_at(point)
        self.plot_widget.release_at(point)
        self.assertEqual(place_list, [])
        self.assertEqual(preview_list, [])

    @covers("LLFR-00260", "LLFR-00042", "LLFR-00045", "LLFR-00044")
    def test_data_tips_show_the_frequency_in_hz(self) -> None:
        """Hover and pinned data tips show "f = <value> Hz".

        Inputs: none.
        Outputs: none.
        """
        from view import value_text
        self.plot_widget.set_plot_tool(TIP_TOOL_STR)
        self.plot_widget.hover_at(self.sample_point(20))
        expected_str = value_text.format_frequency_tip_text(
            "fft_Speed", 2.0, 1.0)
        self.assertEqual(self.plot_widget.hover_tip_text(), expected_str)
        self.assertTrue(expected_str.startswith("f = 2 Hz\n"))
        self.assertNotIn(" s\n", expected_str)
        self.plot_widget.set_pinned_tips([("fft_Speed", 2.0, 1.0)])
        self.assertEqual(self.plot_widget.pinned_tip_text(0), expected_str)

    @covers("LLFR-00261", "LLFR-00171", "LLFR-00168")
    def test_delta_x_shows_delta_f(self) -> None:
        """A Delta X marker shows "Δf = <value> Hz"; Delta Y is as usual.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_delta_markers([
            (5, "x", ("fft_Speed", 1.0, 0.4), ("fft_Speed", 3.5, 0.1),
             2.5),
            (6, "y", ("fft_Speed", 1.0, 0.4), ("fft_Speed", 3.5, 0.1),
             -0.3)])
        self.draw()
        self.assertEqual(self.plot_widget.delta_label_text(5),
                         "Δf = 2.5 Hz")
        self.assertEqual(self.plot_widget.delta_label_text(6), "Δy = -0.3")


@requires_qt
class FrequencyPlotEndToEndTest(unittest.TestCase):
    """Open a CSV file with a sine and plot its FFT in the window."""

    def setUp(self) -> None:
        """Create the window and the controllers and open the file.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.message_box_class = QMessageBox
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        self.folder_str = self.temporary_folder.name
        path_str = os.path.join(self.folder_str, "sine.csv")
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
        self.box_patch = mock.patch.object(
            QMessageBox, "exec", new=lambda box: self.fake_exec(box))
        self.box_patch.start()
        self.addCleanup(self.box_patch.stop)
        self.panel = self.main_window.signal_list_panel
        self.plot_controller = self.controller.plot_controller
        with mock.patch.object(QFileDialog, "getOpenFileName",
                               return_value=(path_str, "")):
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

    def fake_exec(self, box) -> int:
        """Stand-in for QMessageBox.exec that records the box.

        Inputs:
            box: the QMessageBox being shown.
        Outputs: Yes for a question, otherwise OK.
        """
        self.box_record_list.append(
            (box.windowTitle(), box.icon(), box.text()))
        standard_button = self.message_box_class.StandardButton
        if box.icon() == self.message_box_class.Icon.Question:
            return standard_button.Yes.value
        return standard_button.Ok.value

    def choose(self, name_str: str, option_str: str) -> None:
        """Right-click a signal name and choose an option of its menu.

        Inputs:
            name_str: the signal name.
            option_str: the text of the option.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.panel.execute_menu = lambda menu, point: find_action(
            menu, option_str)
        self.panel.show_signal_menu(name_str, QPoint(0, 0))
        self.application.processEvents()

    def double_click(self, name_str: str):
        """Double-click a signal name and return the new plot widget.

        Inputs:
            name_str: the signal name.
        Outputs: the PlotWidget of the last plot of the current tab.
        """
        self.panel.signal_double_clicked.emit(name_str)
        self.application.processEvents()
        return self.plot_widget_list()[-1]

    def plot_widget_list(self) -> list:
        """Return the plot widgets of the current tab, top to bottom.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        plot_panel = self.main_window.plot_panel
        return [plot_panel.plot_view(plot_id_i) for plot_id_i
                in plot_panel.plot_id_list(plot_panel.current_tab_id())]

    def create_fft(self) -> str:
        """Create the FFT of Speed through the signal list menu.

        Inputs: none.
        Outputs: the name of the FFT signal.
        """
        self.choose("Speed", "FFT (fft)")
        return self.panel.signal_name_list()[-1]

    @covers("LLFR-00256", "LLFR-00249", "LLFR-00019", "HLFR-00058",
            "HLFR-00057")
    def test_fft_of_a_sine_peaks_at_its_frequency(self) -> None:
        """The frequency plot of a 2 Hz sine peaks at 2 Hz.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        self.assertTrue(fft_name_str.startswith("fft_"))
        self.assertTrue(fft_name_str.endswith("s_Speed"))
        plot_widget = self.double_click(fft_name_str)
        self.assertTrue(plot_widget.frequency_plot_b)
        self.assertEqual(plot_widget.axes.get_xlabel(), "Frequency (Hz)")
        line = plot_widget.curve_line_dict[fft_name_str]
        frequency_array = np.asarray(line.get_xdata(), dtype=float)
        amplitude_array = np.asarray(line.get_ydata(), dtype=float)
        self.assertEqual(frequency_array[0], 0.0)
        self.assertAlmostEqual(frequency_array[-1], SAMPLE_RATE_HZ / 2.0)
        peak_index_i = int(np.argmax(amplitude_array))
        self.assertAlmostEqual(frequency_array[peak_index_i],
                               SINE_FREQUENCY_HZ, places=6)
        self.assertAlmostEqual(amplitude_array[peak_index_i],
                               SINE_AMPLITUDE_F, delta=0.1)
        start_hz, end_hz = plot_widget.time_range_tuple()
        self.assertEqual(start_hz, 0.0)
        self.assertAlmostEqual(end_hz, SAMPLE_RATE_HZ / 2.0)
        self.assertEqual(self.box_record_list, [])

    @covers("LLFR-00257", "LLFR-00258", "LLFR-00070", "LLFR-00115")
    def test_mixing_is_refused_and_ranges_stay_apart(self) -> None:
        """Drops that mix kinds show the box; zooms stay per plot.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        time_widget = self.double_click("Torque")
        frequency_widget = self.double_click(fft_name_str)
        self.plot_controller.on_signal_dropped(frequency_widget.plot_id_i,
                                               "Speed")
        self.plot_controller.on_signal_dropped(time_widget.plot_id_i,
                                               fft_name_str)
        self.application.processEvents()
        self.assertEqual(len(self.box_record_list), 2)
        for title_str, icon, text_str in self.box_record_list:
            self.assertEqual(icon, self.message_box_class.Icon.Information)
            self.assertIn("FFT signals and time signals cannot be drawn "
                          "in the same plot", text_str)
        self.assertEqual(list(frequency_widget.curve_line_dict),
                         [fft_name_str])
        self.assertEqual(list(time_widget.curve_line_dict), ["Torque"])
        # A wheel zoom of the frequency plot leaves the time plot alone.
        time_range_tuple = time_widget.time_range_tuple()
        frequency_widget.wheel_at(
            frequency_widget.data_to_widget_point(2.0, 0.0), 4.0)
        self.application.processEvents()
        self.assertEqual(time_widget.time_range_tuple(), time_range_tuple)
        zoomed_tuple = frequency_widget.time_range_tuple()
        self.assertLess(zoomed_tuple[1] - zoomed_tuple[0], 25.0)
        # A wheel zoom of the time plot leaves the frequency plot alone.
        time_widget.wheel_at(time_widget.data_to_widget_point(5.0, 0.0),
                             2.0)
        self.application.processEvents()
        self.assertEqual(frequency_widget.time_range_tuple(), zoomed_tuple)
        # Reset zoom: the whole time range and the whole frequency range.
        self.plot_controller.on_reset_zoom()
        self.application.processEvents()
        self.assertEqual(time_widget.time_range_tuple(), (0.0, 9.98))
        self.assertEqual(frequency_widget.time_range_tuple()[0], 0.0)
        self.assertAlmostEqual(frequency_widget.time_range_tuple()[1],
                               SAMPLE_RATE_HZ / 2.0)

    @covers("LLFR-00258", "LLFR-00209", "LLFR-00070")
    def test_span_zooms_stay_apart(self) -> None:
        """A span zoom of a frequency plot leaves the time plots alone,
        and a span zoom of a time plot leaves the frequency plot alone.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        time_widget = self.double_click("Torque")
        other_time_widget = self.double_click("Speed")
        frequency_widget = self.double_click(fft_name_str)
        self.plot_controller.on_plot_tool_changed(ZOOM_TOOL_STR)
        self.application.processEvents()
        for plot_widget in (time_widget, other_time_widget,
                            frequency_widget):
            plot_widget.canvas.draw()
        time_range_tuple = time_widget.time_range_tuple()
        # Span zoom of the frequency plot, from 1 Hz to 6 Hz.
        press_point = frequency_widget.data_to_widget_point(1.0, 0.5)
        release_point = frequency_widget.data_to_widget_point(6.0, 0.5)
        frequency_widget.span_press_at(press_point)
        frequency_widget.span_drag_to(release_point)
        frequency_widget.span_release_at(release_point)
        self.application.processEvents()
        start_hz, end_hz = frequency_widget.time_range_tuple()
        self.assertAlmostEqual(start_hz, 1.0, delta=0.2)
        self.assertAlmostEqual(end_hz, 6.0, delta=0.2)
        frequency_plot = self.plot_controller.workspace.find_plot(
            frequency_widget.plot_id_i)
        self.assertEqual(frequency_plot.frequency_range_tuple,
                         (start_hz, end_hz))
        self.assertEqual(time_widget.time_range_tuple(), time_range_tuple)
        self.assertEqual(other_time_widget.time_range_tuple(),
                         time_range_tuple)
        self.assertEqual(self.plot_controller.shared_time_range_tuple, ())
        # Span zoom of a time plot, from 2 s to 5 s: every time plot.
        time_widget.canvas.draw()
        press_point = time_widget.data_to_widget_point(2.0, 10.0)
        release_point = time_widget.data_to_widget_point(5.0, 10.0)
        time_widget.span_press_at(press_point)
        time_widget.span_drag_to(release_point)
        time_widget.span_release_at(release_point)
        self.application.processEvents()
        zoomed_tuple = time_widget.time_range_tuple()
        self.assertAlmostEqual(zoomed_tuple[0], 2.0, delta=0.1)
        self.assertAlmostEqual(zoomed_tuple[1], 5.0, delta=0.1)
        self.assertEqual(other_time_widget.time_range_tuple(),
                         zoomed_tuple)
        self.assertEqual(frequency_widget.time_range_tuple(),
                         (start_hz, end_hz))

    @covers("LLFR-00259", "LLFR-00203", "LLFR-00205")
    def test_markers_skip_the_frequency_plot(self) -> None:
        """A marker placed on the time plot is not on the frequency plot.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        time_widget = self.double_click("Torque")
        frequency_widget = self.double_click(fft_name_str)
        self.plot_controller.on_plot_tool_changed(MARKER_TOOL_STR)
        self.application.processEvents()
        time_widget.canvas.draw()
        frequency_widget.canvas.draw()
        frequency_point = frequency_widget.data_to_widget_point(3.0, 0.5)
        frequency_widget.press_at(frequency_point)
        frequency_widget.release_at(frequency_point)
        self.application.processEvents()
        self.assertEqual(self.plot_controller.workspace.marker_list, [])
        time_widget.press_at(time_widget.data_to_widget_point(4.0, 10.0))
        self.application.processEvents()
        self.assertEqual(len(self.plot_controller.workspace.marker_list), 1)
        self.assertEqual(time_widget.marker_count(), 1)
        self.assertEqual(frequency_widget.marker_count(), 0)
        # The preview of the time plot is not relayed to it.
        time_widget.update_marker_preview(
            time_widget.data_to_widget_point(6.0, 10.0))
        self.assertTrue(time_widget.marker_preview_shown())
        self.assertFalse(frequency_widget.marker_preview_shown())

    @covers("LLFR-00129", "LLFR-00133", "LLFR-00256", "HLFR-00038",
            "HLFR-00039")
    def test_export_and_copy_include_the_frequency_plot(self) -> None:
        """The PDF and the copied image show the frequency plot.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        from view import plot_export
        frequency_widget = self.double_click(self.create_fft())
        path_str = os.path.join(self.folder_str, "plots.pdf")
        saved_b, reason_str = self.main_window.save_tabs_pdf(path_str)
        self.assertTrue(saved_b, reason_str)
        with open(path_str, "rb") as pdf_file:
            self.assertTrue(pdf_file.read().startswith(b"%PDF"))
        snapshot_list = plot_export.grab_exportable_images(
            self.main_window.plot_panel.tab_widget)
        self.assertEqual(len(snapshot_list), 1)
        # The exported figure is the plot as shown, labeled in Hz.
        self.assertEqual(frequency_widget.axes.get_xlabel(),
                         "Frequency (Hz)")
        self.assertFalse(plot_export.render_figure_image(
            frequency_widget.figure, 100.0).isNull())
        copied_b, reason_str = self.main_window.copy_current_tab_image()
        self.assertTrue(copied_b, reason_str)
        self.assertFalse(QApplication.clipboard().image().isNull())

    @covers("LLFR-00140", "LLFR-00138", "LLFR-00192", "LLFR-00039",
            "LLFR-00051")
    def test_undo_redo_and_curve_removal(self) -> None:
        """Undo and redo rebuild the frequency plot as a frequency plot.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft()
        frequency_widget = self.double_click(fft_name_str)
        plot_id_i = frequency_widget.plot_id_i
        self.plot_controller.on_undo()
        self.application.processEvents()
        self.assertEqual(self.plot_widget_list(), [])
        self.plot_controller.on_redo()
        self.application.processEvents()
        redone_widget = self.main_window.plot_panel.plot_view(plot_id_i)
        self.assertTrue(redone_widget.frequency_plot_b)
        self.assertEqual(redone_widget.axes.get_xlabel(), "Frequency (Hz)")
        self.assertEqual(list(redone_widget.curve_line_dict),
                         [fft_name_str])
        # LLFR-00051: removing its only curve deletes the plot.
        self.plot_controller.on_curve_delete(plot_id_i, fft_name_str)
        self.application.processEvents()
        self.assertEqual(self.plot_widget_list(), [])


if __name__ == "__main__":
    unittest.main()
