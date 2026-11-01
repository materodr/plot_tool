"""Tests for shared vertical markers and the marker preview in the view.

A real MainWindow and MainController are used, with a file built in the
test. The current tab holds three plots and a second tab holds one, so
that "every plot of the current tab" and "every plot of every tab" can
be told apart (LLFR-00203, LLFR-00205). Mouse events are sent through
the same matplotlib callbacks that real mouse events reach.
"""

import unittest
from unittest import mock

import numpy as np

from tests.support import covers, get_qt_application, requires_qt
from tests.view.test_markers_view import LEFT_BUTTON_I, send_mouse_event

from controller.plot_tools import MARKER_TOOL_STR, NO_TOOL_STR, ZOOM_TOOL_STR
from model.curve_colors import MARKER_COLOR_STR

# Number of plots in the first (current) tab.
CURRENT_TAB_PLOT_COUNT_I = 3
# Number of preview moves sent to check that no full draw happens.
PREVIEW_MOVE_COUNT_I = 30


@requires_qt
class SharedMarkerWindowTestCase(unittest.TestCase):
    """Base class: a shown window, 3 plots in tab 1 and 1 plot in tab 2."""

    def setUp(self) -> None:
        """Create the window and controllers, a file and the four plots.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtCore import QPoint
        from controller.main_controller import MainController
        # LLFR-00203: the real pointer is kept far from the plots, so
        # that activating the tool never shows a preview by itself; a
        # test may move it with move_cursor_to.
        self.cursor_mock = mock.MagicMock()
        self.cursor_mock.pos.return_value = QPoint(-10000, -10000)
        cursor_patcher = mock.patch("view.plot_widget.QCursor",
                                    self.cursor_mock)
        cursor_patcher.start()
        self.addCleanup(cursor_patcher.stop)
        from model.signal_file import SignalFile
        from view.main_window import MainWindow
        self.main_window = MainWindow()
        self.main_window.resize(1100, 900)
        self.controller = MainController(self.main_window)
        self.controller.start()
        time_array = np.linspace(0.0, 4.0, 41)
        signal_file = SignalFile("memory.csv", {
            "Time": time_array, "speed": time_array * 2.0,
            "force": np.sin(time_array), "torque": np.cos(time_array)})
        self.controller.plot_controller.on_file_opened(signal_file, False)
        self.plot_controller = self.controller.plot_controller
        self.workspace = self.plot_controller.workspace
        self.panel = self.main_window.plot_panel
        self.main_window.show()
        self.first_tab_id_i = self.panel.current_tab_id()
        for signal_name_str in ("speed", "force", "torque"):
            self.main_window.signal_double_click_handler(signal_name_str)
        self.plot_controller.on_add_tab()
        self.second_tab_id_i = self.panel.current_tab_id()
        self.main_window.signal_double_click_handler("speed")
        self.main_window.set_current_tab(self.first_tab_id_i)
        self.process_events()
        self.current_widget_list = list(
            self.panel.page_dict[self.first_tab_id_i].plot_widget_list)
        self.hidden_widget = (
            self.panel.page_dict[self.second_tab_id_i].plot_widget_list[0])
        self.assertEqual(len(self.current_widget_list),
                         CURRENT_TAB_PLOT_COUNT_I)

    def tearDown(self) -> None:
        """Release any held key and close the window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.tool_key_filter.handle_keyboard_lost()
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def process_events(self) -> None:
        """Let Qt run deferred work and draw the shown plots.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(3):
            self.application.processEvents()
        for plot_widget in self.panel.plot_widget_dict.values():
            if plot_widget.isVisible():
                plot_widget.canvas.draw()
        self.application.processEvents()

    def activate_marker_tool(self) -> None:
        """Click the Vertical marker button.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.top_panel.plot_tool_button_dict[
            MARKER_TOOL_STR].click()
        self.process_events()
        self.assertEqual(self.plot_controller.plot_tool_str, MARKER_TOOL_STR)

    def mouse(self, plot_widget, event_name_str: str, time_s: float) -> None:
        """Send a left-button mouse event at a time, mid-height.

        Inputs:
            plot_widget: the PlotWidget.
            event_name_str: the matplotlib event name.
            time_s: x value in seconds.
        Outputs: none.
        """
        bottom_f, top_f = plot_widget.axes.get_ylim()
        display_x_px, display_y_px = plot_widget.axes.transData.transform(
            (time_s, (bottom_f + top_f) / 2.0))
        send_mouse_event(plot_widget, event_name_str, float(display_x_px),
                         float(display_y_px), LEFT_BUTTON_I)

    def hover(self, plot_widget, time_s: float) -> None:
        """Move the mouse, with no button held, over a plot.

        Inputs:
            plot_widget: the PlotWidget.
            time_s: x value in seconds.
        Outputs: none.
        """
        self.mouse(plot_widget, "motion_notify_event", time_s)

    def click(self, plot_widget, time_s: float) -> None:
        """Press and release the left button at a time.

        Inputs:
            plot_widget: the PlotWidget.
            time_s: x value in seconds.
        Outputs: none.
        """
        self.mouse(plot_widget, "button_press_event", time_s)
        self.mouse(plot_widget, "button_release_event", time_s)
        self.process_events()

    def move_cursor_to(self, plot_widget, time_s: float) -> None:
        """Make the pointer position read by the plots be over a plot.

        Inputs:
            plot_widget: the PlotWidget.
            time_s: x value in seconds, at mid-height.
        Outputs: none. No mouse event is sent.
        """
        bottom_f, top_f = plot_widget.axes.get_ylim()
        widget_point = plot_widget.data_to_widget_point(
            time_s, (bottom_f + top_f) / 2.0)
        self.cursor_mock.pos.return_value = plot_widget.mapToGlobal(
            widget_point)

    def all_widget_list(self) -> list:
        """Return the plots of both tabs.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        return self.current_widget_list + [self.hidden_widget]

    def assert_preview_on_current_tab(self, time_s: float) -> None:
        """Check the preview is at a time on every plot of the tab.

        Inputs:
            time_s: the expected time, in seconds.
        Outputs: none.
        """
        for plot_widget in self.current_widget_list:
            self.assertTrue(plot_widget.marker_preview_shown())
            self.assertAlmostEqual(plot_widget.marker_preview_time_s(),
                                   time_s, delta=0.02)
        # LLFR-00203 Note: the plots of hidden tabs need no preview.
        self.assertFalse(self.hidden_widget.marker_preview_shown())

    def assert_no_preview(self) -> None:
        """Check that no plot of any tab shows the preview.

        Inputs: none.
        Outputs: none.
        """
        for plot_widget in self.all_widget_list():
            self.assertFalse(plot_widget.marker_preview_shown())
            self.assertTrue(np.isnan(plot_widget.marker_preview_time_s()))


class SharedMarkerDrawingTest(SharedMarkerWindowTestCase):
    """One marker on every plot of every tab (LLFR-00081, LLFR-00205)."""

    @covers("LLFR-00081", "LLFR-00205", "LLFR-00084", "LLFR-00092",
            "LLFR-00083", "LLFR-00143")
    def test_click_on_one_plot_draws_marker_on_all_plots(self) -> None:
        """A click on the middle plot draws one marker on all four plots.

        Inputs: none.
        Outputs: none.
        """
        self.activate_marker_tool()
        self.click(self.current_widget_list[1], 1.0)
        self.assertEqual(len(self.workspace.marker_list), 1)
        marker = self.workspace.marker_list[0]
        for plot_widget in self.all_widget_list():
            self.assertEqual(plot_widget.marker_id_list(),
                             [marker.marker_id_i])
            self.assertEqual(plot_widget.marker_label_text(
                marker.marker_id_i), "Marker 1")
            self.assertAlmostEqual(plot_widget.marker_time_s(
                marker.marker_id_i), marker.time_s)
            self.assertEqual(plot_widget.marker_time_text(
                marker.marker_id_i), f"t = {marker.time_s:.6g} s")
            line = plot_widget.marker_artist_tuple(marker.marker_id_i)[0]
            self.assertEqual(line.get_color(), MARKER_COLOR_STR)
            self.assertNotEqual(line.get_linestyle(), "-")

    @covers("LLFR-00205", "LLFR-00091", "LLFR-00088", "LLFR-00112")
    def test_new_plot_shows_markers_and_delete_applies_everywhere(
            self) -> None:
        """A later plot shows the markers; Delete on it removes them all.

        Inputs: none.
        Outputs: none.
        """
        self.activate_marker_tool()
        self.click(self.current_widget_list[0], 1.0)
        self.click(self.current_widget_list[0], 3.0)
        self.main_window.set_current_tab(self.second_tab_id_i)
        self.main_window.signal_double_click_handler("force")
        self.process_events()
        new_widget = self.panel.page_dict[
            self.second_tab_id_i].plot_widget_list[-1]
        id_list = [marker.marker_id_i for marker in self.workspace.marker_list]
        self.assertEqual(new_widget.marker_id_list(), id_list)
        self.assertEqual([new_widget.marker_label_text(marker_id_i)
                          for marker_id_i in id_list],
                         ["Marker 1", "Marker 2"])
        # Rename and delete through the controller, as the menus do.
        with mock.patch.object(
                self.main_window, "ask_marker_name", return_value="Peak"):
            self.plot_controller.on_marker_rename(new_widget.plot_id_i,
                                                  id_list[0])
        self.plot_controller.on_marker_delete(new_widget.plot_id_i,
                                              id_list[1])
        for plot_widget in self.all_widget_list() + [new_widget]:
            self.assertEqual(plot_widget.marker_id_list(), [id_list[0]])
            self.assertEqual(plot_widget.marker_label_text(id_list[0]),
                             "Peak")

    @covers("LLFR-00086", "LLFR-00093", "LLFR-00205")
    def test_drag_on_one_plot_moves_marker_on_all(self) -> None:
        """While dragged, the marker follows on the plots of the tab.

        Inputs: none.
        Outputs: none.
        """
        self.activate_marker_tool()
        dragged_widget = self.current_widget_list[2]
        self.click(dragged_widget, 1.0)
        marker_id_i = self.workspace.marker_list[0].marker_id_i
        start_s = dragged_widget.marker_time_s(marker_id_i)
        self.mouse(dragged_widget, "button_press_event", start_s)
        self.mouse(dragged_widget, "motion_notify_event", 2.5)
        dragged_time_s = dragged_widget.marker_time_s(marker_id_i)
        self.assertAlmostEqual(dragged_time_s, 2.5, delta=0.02)
        # LLFR-00205: live on every plot of the current tab, with the
        # time value too (LLFR-00093). The model is not changed yet.
        for plot_widget in self.current_widget_list:
            self.assertAlmostEqual(plot_widget.marker_time_s(marker_id_i),
                                   dragged_time_s)
            self.assertEqual(plot_widget.marker_time_text(marker_id_i),
                             f"t = {dragged_time_s:.6g} s")
        self.assertAlmostEqual(self.workspace.marker_list[0].time_s,
                               start_s)
        self.mouse(dragged_widget, "button_release_event", 2.5)
        self.process_events()
        # LLFR-00205: at the release, every plot of every tab has it.
        final_s = self.workspace.marker_list[0].time_s
        self.assertAlmostEqual(final_s, 2.5, delta=0.02)
        for plot_widget in self.all_widget_list():
            self.assertAlmostEqual(plot_widget.marker_time_s(marker_id_i),
                                   final_s)
        # One undoable action for the whole drag (LLFR-00140).
        self.plot_controller.on_undo()
        self.process_events()
        for plot_widget in self.all_widget_list_after_rebuild():
            self.assertAlmostEqual(plot_widget.marker_time_s(marker_id_i),
                                   start_s)

    def all_widget_list_after_rebuild(self) -> list:
        """Return the plot widgets of every tab, after an undo rebuilt them.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        return list(self.panel.plot_widget_dict.values())

    @covers("LLFR-00086", "LLFR-00205")
    def test_cancelled_drag_puts_the_marker_back_on_all(self) -> None:
        """A drag ended by a tool change shows the stored time again.

        Inputs: none.
        Outputs: none.
        """
        self.activate_marker_tool()
        dragged_widget = self.current_widget_list[0]
        self.click(dragged_widget, 1.0)
        marker_id_i = self.workspace.marker_list[0].marker_id_i
        start_s = dragged_widget.marker_time_s(marker_id_i)
        self.mouse(dragged_widget, "button_press_event", start_s)
        self.mouse(dragged_widget, "motion_notify_event", 3.0)
        self.main_window.top_panel.plot_tool_button_dict[
            ZOOM_TOOL_STR].click()
        self.process_events()
        for plot_widget in self.current_widget_list:
            self.assertAlmostEqual(plot_widget.marker_time_s(marker_id_i),
                                   start_s)


class MarkerPreviewTest(SharedMarkerWindowTestCase):
    """The preview of the marker a click would place (LLFR-00203)."""

    @covers("LLFR-00203")
    def test_preview_on_every_plot_of_the_tab_follows_the_mouse(
            self) -> None:
        """Hovering one plot shows the preview on the three of the tab.

        Inputs: none.
        Outputs: none.
        """
        self.activate_marker_tool()
        self.assert_no_preview()
        hovered_widget = self.current_widget_list[1]
        self.hover(hovered_widget, 1.0)
        self.assert_preview_on_current_tab(1.0)
        self.hover(hovered_widget, 3.0)
        self.assert_preview_on_current_tab(3.0)
        # Hovering another plot of the tab moves it there too.
        self.hover(self.current_widget_list[0], 2.0)
        self.assert_preview_on_current_tab(2.0)
        # LLFR-00092: with its time value.
        for plot_widget in self.current_widget_list:
            self.assertEqual(
                plot_widget.marker_preview_text(),
                f"t = {plot_widget.marker_preview_time_s():.6g} s")

    @covers("LLFR-00203", "LLFR-00083", "LLFR-00143")
    def test_preview_is_a_paler_dashed_line(self) -> None:
        """The preview is dashed, in a paler version of the marker color.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_rgb
        from view.plot_widget import MARKER_PREVIEW_COLOR_STR
        self.activate_marker_tool()
        plot_widget = self.current_widget_list[0]
        self.hover(plot_widget, 1.0)
        self.assertEqual(plot_widget.preview_line.get_color(),
                         MARKER_PREVIEW_COLOR_STR)
        self.assertNotEqual(plot_widget.preview_line.get_linestyle(), "-")
        # Paler: every channel is closer to white than the marker's.
        marker_rgb_tuple = to_rgb(MARKER_COLOR_STR)
        preview_rgb_tuple = to_rgb(MARKER_PREVIEW_COLOR_STR)
        self.assertGreater(sum(preview_rgb_tuple), sum(marker_rgb_tuple))
        self.assertNotEqual(preview_rgb_tuple, marker_rgb_tuple)

    @covers("LLFR-00203")
    def test_preview_is_hidden_on_leave_and_deactivation(self) -> None:
        """Leaving the plot or deactivating the tool hides the preview.

        Inputs: none.
        Outputs: none.
        """
        self.activate_marker_tool()
        hovered_widget = self.current_widget_list[2]
        self.hover(hovered_widget, 1.0)
        self.assert_preview_on_current_tab(1.0)
        hovered_widget.on_mouse_leave(None)
        self.assert_no_preview()
        # Outside the drawing area (below the x-axis) there is none.
        axes_box = hovered_widget.axes.bbox
        send_mouse_event(hovered_widget, "motion_notify_event",
                         float(axes_box.x0 + 20.0),
                         float(axes_box.y0 - 15.0), LEFT_BUTTON_I)
        self.assert_no_preview()
        self.hover(hovered_widget, 2.0)
        self.assert_preview_on_current_tab(2.0)
        # The button is clicked again: no tool, no preview.
        self.main_window.top_panel.plot_tool_button_dict[
            MARKER_TOOL_STR].click()
        self.process_events()
        self.assertEqual(self.plot_controller.plot_tool_str, NO_TOOL_STR)
        self.assert_no_preview()
        # And no preview with another tool.
        self.main_window.top_panel.plot_tool_button_dict[
            ZOOM_TOOL_STR].click()
        self.hover(hovered_widget, 2.5)
        self.assert_no_preview()

    @covers("LLFR-00203", "LLFR-00154", "LLFR-00155")
    def test_preview_while_shift_is_held(self) -> None:
        """Holding Shift shows the preview; releasing it hides it.

        Inputs: none.
        Outputs: none.
        """
        from tests.view.test_tip_key import send_key
        send_key(self.main_window, "KeyPress", "Key_Shift", "ShiftModifier")
        self.application.processEvents()
        self.assertEqual(self.plot_controller.plot_tool_str, MARKER_TOOL_STR)
        self.hover(self.current_widget_list[0], 1.5)
        self.assert_preview_on_current_tab(1.5)
        send_key(self.main_window, "KeyRelease", "Key_Shift")
        self.application.processEvents()
        self.assertEqual(self.plot_controller.plot_tool_str, NO_TOOL_STR)
        self.assert_no_preview()

    @covers("LLFR-00203", "LLFR-00154")
    def test_shift_shows_preview_without_moving_the_mouse(self) -> None:
        """With the pointer resting on a plot, Shift shows the preview.

        Inputs: none.
        Outputs: none.
        """
        from tests.view.test_tip_key import send_key
        self.move_cursor_to(self.current_widget_list[2], 2.5)
        send_key(self.main_window, "KeyPress", "Key_Shift", "ShiftModifier")
        self.application.processEvents()
        self.assert_preview_on_current_tab(2.5)
        send_key(self.main_window, "KeyRelease", "Key_Shift")
        self.application.processEvents()
        self.assert_no_preview()

    @covers("LLFR-00203", "LLFR-00081")
    def test_no_preview_over_a_marker_or_while_dragging(self) -> None:
        """Over a marker, and during a drag, the preview is hidden.

        Inputs: none.
        Outputs: none.
        """
        self.activate_marker_tool()
        plot_widget = self.current_widget_list[0]
        self.click(plot_widget, 1.0)
        # LLFR-00081: the click placed a marker under the pointer.
        self.assert_no_preview()
        marker_id_i = self.workspace.marker_list[0].marker_id_i
        marker_s = plot_widget.marker_time_s(marker_id_i)
        self.hover(plot_widget, 3.0)
        self.assert_preview_on_current_tab(3.0)
        self.hover(plot_widget, marker_s)
        self.assert_no_preview()
        # Over the same marker on another plot of the tab, too.
        self.hover(self.current_widget_list[1], 3.0)
        self.assert_preview_on_current_tab(3.0)
        self.hover(self.current_widget_list[1], marker_s)
        self.assert_no_preview()
        # During a drag no preview, on any plot.
        self.mouse(plot_widget, "button_press_event", marker_s)
        self.mouse(plot_widget, "motion_notify_event", 2.0)
        self.assert_no_preview()
        self.mouse(plot_widget, "button_release_event", 2.0)
        self.process_events()
        self.assert_no_preview()

    @covers("LLFR-00203")
    def test_preview_moves_redraw_only_the_preview(self) -> None:
        """Following the mouse never makes a full draw of any canvas.

        Inputs: none.
        Outputs: none.
        """
        self.activate_marker_tool()
        draw_count_list = [0]

        def count_draw(event) -> None:
            """Count a full draw of a canvas.

            Inputs:
                event: the matplotlib DrawEvent.
            Outputs: none.
            """
            draw_count_list[0] += 1

        for plot_widget in self.current_widget_list:
            plot_widget.canvas.mpl_connect("draw_event", count_draw)
        hovered_widget = self.current_widget_list[0]
        self.hover(hovered_widget, 0.5)
        self.application.processEvents()
        draw_count_list[0] = 0
        for move_i in range(PREVIEW_MOVE_COUNT_I):
            self.hover(hovered_widget,
                       0.5 + 3.0 * move_i / PREVIEW_MOVE_COUNT_I)
        self.application.processEvents()
        self.assertEqual(draw_count_list[0], 0)
        self.assert_preview_on_current_tab(
            0.5 + 3.0 * (PREVIEW_MOVE_COUNT_I - 1) / PREVIEW_MOVE_COUNT_I)

    @covers("LLFR-00203")
    def test_preview_is_drawn_on_the_canvas_and_removed(self) -> None:
        """Showing the preview changes the canvas image; hiding restores.

        Inputs: none.
        Outputs: none.
        """
        self.activate_marker_tool()
        plot_widget = self.current_widget_list[0]
        self.application.processEvents()
        clean_array = np.array(plot_widget.canvas.buffer_rgba(), copy=True)
        self.hover(plot_widget, 2.0)
        shown_array = np.array(plot_widget.canvas.buffer_rgba(), copy=True)
        self.assertFalse(np.array_equal(clean_array, shown_array))
        plot_widget.on_mouse_leave(None)
        hidden_array = np.array(plot_widget.canvas.buffer_rgba(), copy=True)
        self.assertTrue(np.array_equal(clean_array, hidden_array))

    @covers("LLFR-00203", "LLFR-00129", "LLFR-00133")
    def test_preview_is_not_exported_or_copied(self) -> None:
        """The PDF images and the copied image never show the preview.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.activate_marker_tool()
        page = self.panel.page_dict[self.first_tab_id_i]
        plot_widget = self.current_widget_list[0]
        # LLFR-00133, LLFR-00129: the copied image and the PDF pages are
        # grabs of the tab page, which paint each plot from its canvas
        # image. When the page is grabbed, no plot shows the preview, and
        # no preview artist is drawn on any canvas during the export.
        # (Pixels of separate draws are not compared: the plots fit
        # their legend and tips at each draw, so two draws may differ.)
        self.hover(plot_widget, 2.5)
        self.assert_preview_on_current_tab(2.5)
        shown_at_grab_list = []
        original_grab = page.grab

        def recording_grab(*argument_tuple):
            """Record which plots show the preview, then grab.

            Inputs:
                argument_tuple: the arguments of QWidget.grab.
            Outputs: the QPixmap of the grab.
            """
            shown_at_grab_list.append(
                [page_widget.marker_preview_shown()
                 for page_widget in page.plot_widget_list])
            return original_grab(*argument_tuple)

        page.grab = recording_grab
        preview_artist_list = []
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
        for page_widget in page.plot_widget_list:
            preview_artist_list.extend((page_widget.preview_line,
                                        page_widget.preview_time_text))
        self.assertFalse(page_image.isNull())
        self.assertEqual(shown_at_grab_list,
                         [[False] * CURRENT_TAB_PLOT_COUNT_I])
        for draw_artist_mock in draw_artist_mock_list:
            for call in draw_artist_mock.call_args_list:
                self.assertNotIn(call.args[0], preview_artist_list)
        self.assert_no_preview()
        # The next mouse move over a plot shows it again.
        self.hover(plot_widget, 3.0)
        self.assert_preview_on_current_tab(3.0)
        # LLFR-00129: the PDF draws each figure again at a higher dpi.
        plot_widget.on_mouse_leave(None)
        clean_figure_image = plot_export.render_figure_image(
            plot_widget.figure, 100.0)
        self.hover(plot_widget, 2.0)
        self.assert_preview_on_current_tab(2.0)
        self.assertEqual(plot_export.render_figure_image(
            plot_widget.figure, 100.0), clean_figure_image)
        # The preview artists are not part of the axes.
        for artist in (plot_widget.preview_line,
                       plot_widget.preview_time_text):
            self.assertNotIn(artist, plot_widget.axes.get_children())


if __name__ == "__main__":
    unittest.main()
