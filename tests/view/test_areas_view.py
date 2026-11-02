"""Tests for the areas in the plot widget and the main window
(HLFR-00066 to HLFR-00069, LLFR-00303 to LLFR-00318).

The first classes drive one shown 600x400 plot widget (0 s to 10 s, a
sine between -1 and 1 and a ramp between 3 and 4) with matplotlib mouse
events; y = 2 is between the two curves, so a point there holds no
curve. The last class sends real Qt mouse and key events to a MainWindow
with the real controllers. No modal dialog or menu is ever opened.
"""

import unittest

import numpy as np

from tests.support import covers, get_qt_application, requires_qt
from tests.view.test_plot_tools import recorder
from tests.view.test_span_zoom import (
    PIXEL_TOLERANCE_S, SpanWidgetTestCase)
from tests.view.test_xyz_keys import XyzKeyWindowTestCase

from controller.plot_tools import (
    AREA_TOOL_STR, NO_TOOL_STR, PLOT_TOOL_TUPLE, ZOOM_TOOL_STR)
from model.curve_colors import MARKER_COLOR_STR
from model.workspace import FREQUENCY_PLOT_KIND_STR

# y value between the sine and the ramp: no curve there.
EMPTY_VALUE_F = 2.0


class AreaWidgetTestCase(SpanWidgetTestCase):
    """Base class: the plot widget with the Area tool and recorders."""

    def setUp(self) -> None:
        """Activate the Area tool and record the area requests.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.plot_widget.set_plot_tool(AREA_TOOL_STR)
        self.create_list = recorder(self.plot_widget.area_create_requested)
        self.change_list = recorder(self.plot_widget.area_change_requested)
        self.drag_list = recorder(self.plot_widget.area_drag_moved)

    def at(self, time_s: float, offset_x_i: int = 0):
        """Return the widget point at a time, between the curves.

        Inputs:
            time_s: the time, in seconds.
            offset_x_i: widget pixels added to x.
        Outputs: QPoint in the widget's coordinates.
        """
        from PyQt6.QtCore import QPoint
        return self.point_at(time_s, EMPTY_VALUE_F) + QPoint(offset_x_i, 0)

    def set_areas(self, area_data_list: list) -> None:
        """Give the widget its areas and draw it.

        Inputs:
            area_data_list: tuples (area_id_i, name_str, start_s, end_s).
        Outputs: none.
        """
        self.plot_widget.set_areas(area_data_list)
        self.draw()

    def assert_span(self, span_tuple: tuple, start_s: float,
                    end_s: float) -> None:
        """Check a (start, end) span within a pixel.

        Inputs:
            span_tuple: the span to check.
            start_s: the expected start, in s.
            end_s: the expected end, in s.
        Outputs: none.
        """
        self.assertEqual(len(span_tuple), 2)
        self.assertAlmostEqual(span_tuple[0], start_s,
                               delta=PIXEL_TOLERANCE_S)
        self.assertAlmostEqual(span_tuple[1], end_s, delta=PIXEL_TOLERANCE_S)


@requires_qt
class AreaCreateTest(AreaWidgetTestCase):
    """Preview and creation of a new area (LLFR-00303, LLFR-00304)."""

    @covers("LLFR-00303", "LLFR-00304", "LLFR-00207")
    def test_drag_shows_a_preview_and_release_creates(self) -> None:
        """No preview before 5 pixels; then a preview from the press to
        the pointer; the release asks once for the area and removes the
        preview. A drag is in progress from the press to the release.

        Inputs: none.
        Outputs: none.
        """
        self.left_press(self.at(2.0))
        self.assertTrue(self.plot_widget.is_mouse_drag_in_progress())
        self.move_to(self.at(2.0, 4))
        self.assertEqual(self.plot_widget.area_preview_span_tuple(), ())
        self.move_to(self.at(4.0))
        self.assert_span(self.plot_widget.area_preview_span_tuple(), 2.0,
                         4.0)
        self.move_to(self.at(1.0))
        self.assert_span(self.plot_widget.area_preview_span_tuple(), 1.0,
                         2.0)
        self.left_release(self.at(4.5))
        self.assertEqual(len(self.create_list), 1)
        self.assert_span(self.create_list[0], 2.0, 4.5)
        self.assertEqual(self.plot_widget.area_preview_span_tuple(), ())
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())

    @covers("LLFR-00303", "LLFR-00129", "LLFR-00133")
    def test_preview_is_never_part_of_a_full_draw(self) -> None:
        """The preview band is not an artist of the axes, so a draw, the
        PDF export and the copy never contain it.

        Inputs: none.
        Outputs: none.
        """
        self.left_press(self.at(2.0))
        self.move_to(self.at(5.0))
        self.assertTrue(self.plot_widget.area_preview_span_tuple())
        self.assertNotIn(self.plot_widget.area_preview_band,
                         self.plot_widget.axes.get_children())
        self.plot_widget.canvas.draw()
        self.assertTrue(self.plot_widget.area_preview_span_tuple())
        self.left_release(self.at(5.0))

    @covers("LLFR-00304")
    def test_release_less_than_5_pixels_away_creates_nothing(self) -> None:
        """A release 4 pixels from the press, even after a longer move,
        creates nothing and shows no message.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        for offset_tuple in ((4, 0), (0, 4), (-3, -3)):
            with self.subTest(offset=offset_tuple):
                press_point = self.at(5.0)
                self.left_press(press_point)
                self.move_to(self.at(7.0))
                self.left_release(press_point + QPoint(*offset_tuple))
                self.assertEqual(self.create_list, [])
                self.assertEqual(self.plot_widget.area_preview_span_tuple(),
                                 ())
                self.assertFalse(
                    self.plot_widget.is_mouse_drag_in_progress())

    @covers("LLFR-00303")
    def test_press_near_the_drawing_area_edges_starts_nothing(self) -> None:
        """A press 5 pixels or less inside the drawing area's edges, or
        outside it, starts no area.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        box = self.plot_widget.axes.bbox
        middle_y_px = (box.y0 + box.y1) / 2.0
        ratio_f = self.plot_widget.pixel_ratio_f()
        edge_point_list = [
            self.plot_widget.display_to_widget_point(box.x0 + 3 * ratio_f,
                                                     middle_y_px),
            self.plot_widget.display_to_widget_point(box.x1 - 3 * ratio_f,
                                                     middle_y_px),
            self.plot_widget.display_to_widget_point(
                (box.x0 + box.x1) / 2.0, box.y1 - 3 * ratio_f),
            self.plot_widget.display_to_widget_point(
                (box.x0 + box.x1) / 2.0, box.y0 + 3 * ratio_f),
            self.axes_edge_point(False, 10)]
        for press_point in edge_point_list:
            with self.subTest(point=(press_point.x(), press_point.y())):
                self.left_press(press_point)
                self.assertFalse(
                    self.plot_widget.is_mouse_drag_in_progress())
                self.move_to(press_point + QPoint(60, 0))
                self.left_release(press_point + QPoint(60, 0))
        self.assertEqual(self.create_list, [])

    @covers("LLFR-00303", "LLFR-00304")
    def test_preview_stops_at_the_nearest_area(self) -> None:
        """A new area stops at the edge of the area on either side, so
        that it may share the edge but never overlaps.

        Inputs: none.
        Outputs: none.
        """
        self.set_areas([(7, "Area 1", 5.0, 6.0), (8, "Area 2", 1.0, 1.5)])
        self.left_press(self.at(3.0))
        self.move_to(self.at(8.0))
        self.assert_span(self.plot_widget.area_preview_span_tuple(), 3.0,
                         5.0)
        self.assertEqual(self.plot_widget.area_preview_span_tuple()[1], 5.0)
        self.move_to(self.at(0.2))
        self.assertEqual(self.plot_widget.area_preview_span_tuple()[0], 1.5)
        self.left_release(self.at(0.2))
        self.assertEqual(self.create_list[0][0], 1.5)
        self.assert_span(self.create_list[0], 1.5, 3.0)

    @covers("LLFR-00304", "LLFR-00119")
    def test_release_outside_ends_at_the_nearer_edge(self) -> None:
        """A release right or left of the drawing area ends the area at
        that edge of the shown range.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_time_range(2.0, 6.0)
        self.draw()
        self.drag(self.at(4.0), self.axes_edge_point(True, 30))
        self.assert_span(self.create_list[-1], 4.0, 6.0)
        self.drag(self.at(3.0), self.axes_edge_point(False, 30))
        self.assert_span(self.create_list[-1], 2.0, 3.0)

    @covers("LLFR-00311")
    def test_frequency_plot_shows_and_creates_no_area(self) -> None:
        """A frequency plot draws no area and a drag on it with the Area
        tool asks for none.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import PlotWidget
        frequency_widget = PlotWidget(9, kind_str=FREQUENCY_PLOT_KIND_STR)
        try:
            frequency_widget.resize(600, 400)
            frequency_widget.show()
            frequency_array = np.linspace(0.0, 10.0, 101)
            frequency_widget.set_curves([
                ("fft", frequency_array, np.cos(frequency_array), "#ff0000",
                 1)])
            frequency_widget.set_plot_tool(AREA_TOOL_STR)
            frequency_widget.set_areas([(1, "Area 1", 2.0, 3.0)])
            self.application.processEvents()
            frequency_widget.canvas.draw()
            self.assertEqual(frequency_widget.area_id_list(), [])
            created_list = recorder(frequency_widget.area_create_requested)
            point = frequency_widget.data_to_widget_point(5.0, 0.0)
            frequency_widget.area_press_at(point)
            self.assertFalse(frequency_widget.is_mouse_drag_in_progress())
            frequency_widget.area_drag_to(
                frequency_widget.data_to_widget_point(7.0, 0.0))
            self.assertEqual(frequency_widget.area_preview_span_tuple(), ())
            self.assertEqual(created_list, [])
        finally:
            frequency_widget.close()
            frequency_widget.deleteLater()
            self.application.processEvents()


@requires_qt
class AreaLookTest(AreaWidgetTestCase):
    """How an area is drawn (LLFR-00305 to LLFR-00308)."""

    @covers("LLFR-00305", "LLFR-00306", "LLFR-00307", "LLFR-00308")
    def test_band_label_and_times(self) -> None:
        """A see-through band in a paler marker color over the whole y
        range, behind the grid and curves, with its name and times.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_rgb
        from view.plot_widget import AREA_COLOR_STR
        self.plot_widget.set_grid_shown(True)
        self.set_areas([(4, "Warm-up", 3.0, 5.0)])
        band, label, times_text = self.plot_widget.area_artist_tuple(4)
        self.assertIn(band, self.plot_widget.axes.get_children())
        self.assertTrue(band.get_visible())
        self.assertLess(band.get_alpha(), 1.0)
        self.assertGreater(band.get_alpha(), 0.0)
        face_tuple = to_rgb(band.get_facecolor())
        marker_tuple = to_rgb(MARKER_COLOR_STR)
        self.assertEqual(face_tuple, to_rgb(AREA_COLOR_STR))
        self.assertNotEqual(face_tuple, marker_tuple)
        # Paler: every channel is closer to white than the marker color.
        for face_f, marker_f in zip(face_tuple, marker_tuple):
            self.assertGreaterEqual(face_f, marker_f)
        # The whole y range, whatever it is: y from 0 to 1 in axes units.
        self.assertEqual((band.get_y(), band.get_height()), (0.0, 1.0))
        self.assertEqual((band.get_x(), band.get_width()), (3.0, 2.0))
        # Behind the curves, the grid and every other item.
        for line in self.plot_widget.axes.get_lines():
            self.assertLess(band.get_zorder(), line.get_zorder())
            self.assertLess(label.get_zorder(), line.get_zorder())
        self.assertLess(band.get_zorder(),
                        self.plot_widget.axes.xaxis.get_zorder())
        self.assertLess(label.get_zorder(),
                        self.plot_widget.axes.xaxis.get_zorder())
        # LLFR-00306: also behind the vertical markers, delta markers and
        # pinned data tips drawn over the area. (Text notes come with
        # issue #130 and are checked there.)
        self.plot_widget.set_markers([(5, "Marker 1", 4.0)])
        self.plot_widget.set_pinned_tips([("Ramp", 4.5, 3.45, ())])
        self.plot_widget.set_delta_markers([
            (6, "y", ("Ramp", 3.5, 3.35), ("Sine", 3.5, float(np.sin(3.5))),
             0.0)])
        self.draw()
        item_list = list(self.plot_widget.marker_artist_tuple(5))
        item_list += [artist for artist
                      in self.plot_widget.delta_artist_tuple(6)]
        item_list.append(self.plot_widget.pinned_tip_annotation(0))
        self.assertEqual(len(item_list), 8)
        for artist in item_list:
            self.assertLess(band.get_zorder(), artist.get_zorder())
            self.assertLess(label.get_zorder(), artist.get_zorder())
            self.assertLess(times_text.get_zorder(), artist.get_zorder())
        self.assertEqual(self.plot_widget.area_label_text(4), "Warm-up")
        self.assertEqual(label.xy, (3.0, 1.0))
        self.assertEqual(self.plot_widget.area_times_text(4),
                         "3 s to 5 s")
        renderer = self.plot_widget.canvas.get_renderer()
        label_box = label.get_window_extent(renderer)
        times_box = times_text.get_window_extent(renderer)
        self.assertLess(times_box.y1, label_box.y1)
        self.assertLessEqual(times_box.y1, label_box.y0 + 1.0)

    @covers("LLFR-00351", "LLFR-00305", "LLFR-00306")
    def test_each_color_drawn_with_the_same_opacity(self) -> None:
        """Every area is drawn in its own color, with the same see-through
        opacity; an unknown color name gives the default.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_rgb
        from view import theme
        from view.plot_widget import AREA_ALPHA_F
        area_list = [(index_i + 1, name_str, float(index_i),
                      index_i + 0.5, name_str)
                     for index_i, name_str
                     in enumerate(theme.AREA_COLOR_DICT)]
        area_list.append((9, "Odd", 8.0, 9.0, "Purple"))
        self.set_areas(area_list)
        for area_id_i, _, _, _, name_str in area_list:
            band = self.plot_widget.area_artist_tuple(area_id_i)[0]
            expected_str = theme.AREA_COLOR_DICT.get(
                name_str, theme.AREA_COLOR_DICT["Magenta"])
            self.assertEqual(to_rgb(band.get_facecolor()),
                             to_rgb(expected_str))
            self.assertEqual(band.get_alpha(), AREA_ALPHA_F)

    @covers("LLFR-00307", "LLFR-00308")
    def test_label_in_the_upper_left_corner_of_the_band(self) -> None:
        """Measured in the drawn plot, the label's box starts just right
        of the band's left edge and just below the drawing area's top;
        the times are directly below it; with the start out of view, the
        label is at the left edge of the drawing area.

        Inputs: none.
        Outputs: none.
        """
        self.set_areas([(4, "Warm-up", 3.0, 6.0)])
        renderer = self.plot_widget.canvas.get_renderer()
        _, label, times_text = self.plot_widget.area_artist_tuple(4)
        corner_limit_px = 12.0 * self.plot_widget.pixel_ratio_f()
        for view_tuple, left_s in (((0.0, 10.0), 3.0), ((4.0, 8.0), 4.0)):
            with self.subTest(view=view_tuple):
                self.plot_widget.set_time_range(*view_tuple)
                self.draw()
                left_px = self.plot_widget.time_x_px(left_s)
                top_px = float(self.plot_widget.axes.bbox.y1)
                label_box = label.get_bbox_patch().get_window_extent(
                    renderer)
                times_box = times_text.get_bbox_patch().get_window_extent(
                    renderer)
                self.assertGreaterEqual(label_box.x0, left_px - 1.0)
                self.assertLess(label_box.x0 - left_px, corner_limit_px)
                self.assertLessEqual(label_box.y1, top_px + 1.0)
                self.assertLess(top_px - label_box.y1, corner_limit_px)
                self.assertAlmostEqual(times_box.x0, label_box.x0,
                                       delta=1.0)
                self.assertLessEqual(times_box.y1, label_box.y0 + 1.0)
                self.assertLess(label_box.y0 - times_box.y1,
                                corner_limit_px)
                self.assertTrue(self.plot_widget.axes.bbox.contains(
                    label_box.x0 + 1.0, label_box.y1 - 1.0))

    @covers("LLFR-00305", "LLFR-00307")
    def test_area_follows_the_range_and_hides_outside_it(self) -> None:
        """The label stays at the top left of the visible part; an area
        outside the shown range is hidden.

        Inputs: none.
        Outputs: none.
        """
        self.set_areas([(4, "A", 3.0, 5.0)])
        self.plot_widget.set_time_range(4.0, 8.0)
        self.draw()
        band, label, times_text = self.plot_widget.area_artist_tuple(4)
        self.assertTrue(band.get_visible())
        self.assertEqual(label.xy, (4.0, 1.0))
        self.plot_widget.set_time_range(6.0, 8.0)
        self.draw()
        for artist in (band, label, times_text):
            self.assertFalse(artist.get_visible())
        # A redraw of the curves keeps the areas.
        self.plot_widget.set_curves(self.plot_widget.curve_data_list)
        self.draw()
        self.assertEqual(self.plot_widget.area_id_list(), [4])
        self.assertEqual(self.plot_widget.area_label_text(4), "A")


@requires_qt
class AreaMoveResizeTest(AreaWidgetTestCase):
    """Moving and resizing areas (LLFR-00312, LLFR-00313)."""

    def setUp(self) -> None:
        """Draw "Area 1" from 3 s to 5 s and "Area 2" from 7 s to 8 s.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.set_areas([(1, "Area 1", 3.0, 5.0), (2, "Area 2", 7.0, 8.0)])

    @covers("LLFR-00312", "LLFR-00308", "LLFR-00310", "LLFR-00207")
    def test_press_inside_moves_the_area_keeping_its_width(self) -> None:
        """A drag from inside the area moves it with the pointer, its
        times update live, and the release asks once for the new span.

        Inputs: none.
        Outputs: none.
        """
        self.left_press(self.at(4.0))
        self.assertTrue(self.plot_widget.is_mouse_drag_in_progress())
        self.move_to(self.at(4.5))
        self.assert_span(self.plot_widget.area_drawn_span_tuple(1), 3.5,
                         5.5)
        self.assertEqual(self.plot_widget.area_times_text(1),
                         self.expected_times_text(1))
        self.assertTrue(self.drag_list)
        self.assertEqual(self.drag_list[-1][0], 1)
        self.assertEqual(self.change_list, [])
        self.assertEqual(self.create_list, [])
        self.left_release(self.at(5.0))
        self.assertEqual(len(self.change_list), 1)
        self.assertEqual(self.change_list[0][0], 1)
        self.assert_span(self.change_list[0][1:], 4.0, 6.0)
        self.assertAlmostEqual(self.change_list[0][2]
                               - self.change_list[0][1], 2.0)
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())

    def expected_times_text(self, area_id_i: int) -> str:
        """Return the times text of an area at its drawn span.

        Inputs:
            area_id_i: id of the area.
        Outputs: the text "<start> s to <end> s".
        """
        from view import value_text
        return value_text.format_area_times_text(
            *self.plot_widget.area_drawn_span_tuple(area_id_i))

    @covers("LLFR-00312", "LLFR-00119")
    def test_move_stops_at_the_next_area_and_the_file_range(self) -> None:
        """A moved area stops at the next area's edge and at the start of
        the file.

        Inputs: none.
        Outputs: none.
        """
        self.drag(self.at(4.0), self.at(9.5))
        self.assertEqual(self.change_list[-1][1:], (5.0, 7.0))
        self.plot_widget.set_areas([(1, "Area 1", 5.0, 7.0),
                                    (2, "Area 2", 7.0, 8.0)])
        self.draw()
        self.drag(self.at(6.0), self.axes_edge_point(False, 40))
        self.assertEqual(self.change_list[-1][1:], (0.0, 2.0))

    @covers("LLFR-00313", "LLFR-00308")
    def test_press_near_an_edge_resizes(self) -> None:
        """A press within 5 pixels of an edge, inside or outside the
        band, moves only that edge.

        Inputs: none.
        Outputs: none.
        """
        self.drag(self.at(3.0, 3), self.at(1.0))
        self.assertEqual(self.change_list[-1][0], 1)
        self.assert_span(self.change_list[-1][1:], 1.0, 5.0)
        self.assertEqual(self.change_list[-1][2], 5.0)
        self.drag(self.at(5.0, 4), self.at(6.0))
        self.assertEqual(self.change_list[-1][1], 3.0)
        self.assert_span(self.change_list[-1][1:], 3.0, 6.0)
        self.assertEqual(self.create_list, [])

    @covers("LLFR-00313", "LLFR-00119")
    def test_resize_limits(self) -> None:
        """An edge stops at the next area, at the file's range and 5
        pixels before the other edge.

        Inputs: none.
        Outputs: none.
        """
        self.drag(self.at(5.0, -2), self.at(9.0))
        self.assertEqual(self.change_list[-1][1:], (3.0, 7.0))
        self.drag(self.at(8.0, 2), self.axes_edge_point(True, 40))
        self.assertEqual(self.change_list[-1][0], 2)
        self.assertEqual(self.change_list[-1][1], 7.0)
        self.assert_span(self.change_list[-1][1:], 7.0, 10.0)
        self.assertLessEqual(self.change_list[-1][2], 10.0)
        self.drag(self.at(3.0, 2), self.at(6.0))
        start_s, end_s = self.change_list[-1][1:]
        self.assertEqual(end_s, 5.0)
        width_px = (self.plot_widget.time_x_px(end_s)
                    - self.plot_widget.time_x_px(start_s))
        self.assertAlmostEqual(
            width_px, 5.0 * self.plot_widget.pixel_ratio_f(), delta=0.5)

    @covers("LLFR-00312", "LLFR-00313")
    def test_press_and_release_without_move_changes_nothing(self) -> None:
        """A click inside an area or on its edge asks for nothing.

        Inputs: none.
        Outputs: none.
        """
        for press_point in (self.at(4.0), self.at(3.0, 1)):
            self.left_press(press_point)
            self.left_release(press_point)
        self.assertEqual(self.change_list, [])
        self.assertEqual(self.create_list, [])

    @covers("LLFR-00312", "LLFR-00310")
    def test_tool_change_cancels_a_move(self) -> None:
        """Leaving the Area tool mid-drag puts the area back and asks for
        nothing; the other plots are told to put it back too.

        Inputs: none.
        Outputs: none.
        """
        self.left_press(self.at(4.0))
        self.move_to(self.at(6.0))
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
        self.assertEqual(self.plot_widget.area_drawn_span_tuple(1),
                         (3.0, 5.0))
        self.assertEqual(self.drag_list[-1], (1, 3.0, 5.0))
        self.left_release(self.at(6.0))
        self.assertEqual(self.change_list, [])
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())

    @covers("LLFR-00310")
    def test_follow_drag_moves_only_the_drawing(self) -> None:
        """follow_area_drag (another plot of the tab) moves the band and
        its times, not the stored areas.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.follow_area_drag(1, 3.5, 5.5)
        self.assertEqual(self.plot_widget.area_drawn_span_tuple(1),
                         (3.5, 5.5))
        self.assertEqual(self.plot_widget.area_times_text(1),
                         "3.5 s to 5.5 s")
        self.assertEqual(self.plot_widget.area_data_list[0][2:], (3.0, 5.0))
        self.plot_widget.follow_area_drag(99, 1.0, 2.0)


@requires_qt
class AreaOtherToolsTest(AreaWidgetTestCase):
    """Areas change nothing for the other tools (LLFR-00318)."""

    @covers("LLFR-00318", "LLFR-00208")
    def test_other_tools_never_move_or_resize_an_area(self) -> None:
        """With every other tool, and with none, a drag inside an area
        or on its edge asks for no area change; the Zoom tool still
        selects a span there.

        Inputs: none.
        Outputs: none.
        """
        self.set_areas([(1, "Area 1", 3.0, 5.0)])
        for tool_str in (NO_TOOL_STR,) + tuple(
                tool_str for tool_str in PLOT_TOOL_TUPLE
                if tool_str != AREA_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                for press_point in (self.at(4.0), self.at(3.0, 2)):
                    self.left_press(press_point)
                    self.move_to(self.at(4.6))
                    if tool_str == ZOOM_TOOL_STR:
                        self.assertTrue(
                            self.plot_widget.time_span_line_shown())
                    self.assertEqual(
                        self.plot_widget.area_drawn_span_tuple(1),
                        (3.0, 5.0))
                    self.left_release(self.at(4.6))
                    self.plot_widget.set_time_range(0.0, 10.0)
                    self.draw()
        self.assertEqual(self.change_list, [])
        self.assertEqual(self.create_list, [])
        self.assertEqual(self.drag_list, [])

    @covers("LLFR-00153", "LLFR-00318")
    def test_press_on_a_pinned_tip_moves_the_tip(self) -> None:
        """With the Area tool, a press on a pinned tip inside an area
        moves the tip, not the area.

        Inputs: none.
        Outputs: none.
        """
        self.set_areas([(1, "Area 1", 3.0, 6.0)])
        self.plot_widget.set_pinned_tips([("Ramp", 4.0, 3.4, (0.0, -60.0))])
        self.draw()
        move_list = recorder(self.plot_widget.pinned_tip_move_requested)
        annotation = self.plot_widget.pinned_tip_annotation(0)
        box = self.plot_widget.tip_box_extent(annotation)
        tip_point = self.plot_widget.display_to_widget_point(
            (box.x0 + box.x1) / 2.0, (box.y0 + box.y1) / 2.0)
        from PyQt6.QtCore import QPoint
        self.drag(tip_point, tip_point + QPoint(30, 0))
        self.assertEqual(len(move_list), 1)
        self.assertEqual(self.change_list, [])
        self.assertEqual(self.create_list, [])


@requires_qt
class AreaMenuTest(AreaWidgetTestCase):
    """The area menu and the priority of other items (LLFR-00314 to
    LLFR-00317, LLFR-00048)."""

    def setUp(self) -> None:
        """Draw "Area 1" from 2 s to 6 s.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.set_areas([(1, "Area 1", 2.0, 6.0)])

    def menu_texts(self, widget_point, choose_str: str = "") -> list:
        """Show the context menu at a point without blocking.

        Inputs:
            widget_point: QPoint in the widget's coordinates.
            choose_str: the text of the action to choose, "" for none.
        Outputs: the texts of the menu's top-level actions.
        """
        shown_list = []
        self.submenu_dict = {}

        def fake_execute_menu(menu, global_point):
            """Record the menu and choose an action by its text.

            Inputs:
                menu: the QMenu.
                global_point: unused.
            Outputs: the chosen QAction or None.
            """
            shown_list.extend(action.text() for action in menu.actions())
            action_list = list(menu.actions())
            for action in list(action_list):
                if action.menu() is not None:
                    # The "Color" submenu: record its entries too.
                    self.submenu_dict[action.text()] = [
                        (sub_action.text(), sub_action.isCheckable(),
                         sub_action.isChecked())
                        for sub_action in action.menu().actions()]
                    action_list.extend(action.menu().actions())
            for action in action_list:
                if action.text() == choose_str and action.menu() is None:
                    return action
            return None

        self.plot_widget.execute_menu = fake_execute_menu
        self.plot_widget.show_context_menu(widget_point)
        return shown_list

    @covers("LLFR-00314", "LLFR-00315", "LLFR-00316", "LLFR-00317")
    def test_area_menu_and_its_requests(self) -> None:
        """Inside the area, away from every other item, the menu has
        Rename, Color, Delete and Delete plot, each emitting its request,
        with any tool.

        Inputs: none.
        Outputs: none.
        """
        rename_list = recorder(self.plot_widget.area_rename_requested)
        delete_list = recorder(self.plot_widget.area_delete_requested)
        plot_delete_list = recorder(self.plot_widget.plot_delete_requested)
        for tool_str in (AREA_TOOL_STR, NO_TOOL_STR, ZOOM_TOOL_STR):
            self.plot_widget.set_plot_tool(tool_str)
            self.assertEqual(self.menu_texts(self.at(4.0)),
                             ["Rename", "Color", "Delete", "Delete plot"])
        self.menu_texts(self.at(4.0), "Rename")
        self.menu_texts(self.at(4.0), "Delete")
        self.menu_texts(self.at(4.0), "Delete plot")
        self.assertEqual(rename_list, [(1,)])
        self.assertEqual(delete_list, [(1,)])
        self.assertEqual(plot_delete_list, [()])

    @covers("LLFR-00351", "LLFR-00314")
    def test_color_submenu_lists_five_colors_and_emits_the_choice(
            self) -> None:
        """"Color" lists the five colors, the area's own one checked;
        choosing one emits area_color_requested with its name.

        Inputs: none.
        Outputs: none.
        """
        color_list = recorder(self.plot_widget.area_color_requested)
        self.menu_texts(self.at(4.0))
        self.assertEqual(self.submenu_dict["Color"], [
            ("Magenta", True, True), ("Blue", True, False),
            ("Green", True, False), ("Yellow", True, False),
            ("Pink", True, False)])
        self.menu_texts(self.at(4.0), "Green")
        self.assertEqual(color_list, [(1, "Green")])
        self.set_areas([(1, "Area 1", 2.0, 6.0, "Yellow")])
        self.menu_texts(self.at(4.0))
        self.assertEqual([entry[0] for entry in self.submenu_dict["Color"]
                          if entry[2]], ["Yellow"])

    @covers("LLFR-00317", "LLFR-00110", "LLFR-00038", "LLFR-00046",
            "LLFR-00175")
    def test_items_inside_the_area_take_the_menu(self) -> None:
        """A curve, a vertical marker, a pinned tip or a delta marker
        inside the area shows its own menu.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(
            self.menu_texts(self.point_at(4.0, float(np.sin(4.0)))),
            ["Delete signal", "Width"])
        self.plot_widget.set_markers([(5, "Marker 1", 3.0)])
        self.draw()
        self.assertEqual(self.menu_texts(self.at(3.0)), ["Rename", "Delete"])
        self.plot_widget.set_pinned_tips([("Ramp", 5.0, 3.5, ())])
        self.draw()
        self.assertEqual(self.menu_texts(self.point_at(5.0, 3.5)),
                         ["Delete"])
        self.plot_widget.set_pinned_tips([])
        self.plot_widget.set_delta_markers([
            (6, "y", ("Ramp", 4.5, 3.45), ("Sine", 4.5, float(np.sin(4.5))),
             0.0)])
        self.draw()
        delta_box_list = self.plot_widget.delta_artist_tuple(6)
        self.assertTrue(delta_box_list)
        dots = delta_box_list[2]
        dot_point = self.plot_widget.data_to_widget_point(
            float(dots.get_xdata()[0]), float(dots.get_ydata()[0]))
        self.assertEqual(self.menu_texts(dot_point), ["Delete"])
        self.assertEqual(self.plot_widget.delta_marker_at(dot_point), 6)

    @covers("LLFR-00048", "LLFR-00314")
    def test_outside_the_area_only_delete_plot(self) -> None:
        """Outside every area and item, the menu has only Delete plot.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.menu_texts(self.at(8.0)), ["Delete plot"])
        self.assertEqual(self.plot_widget.area_at(self.at(8.0)), -1)
        self.assertEqual(self.plot_widget.area_at(self.at(4.0)), 1)


@requires_qt
class AreaWindowTest(XyzKeyWindowTestCase):
    """Real Qt mouse and key events in the main window: two plots of
    0 s to 4 s, then a second tab."""

    def send_left(self, plot_widget, event_type_name_str: str,
                  time_s: float, buttons_name_str: str) -> None:
        """Send a Qt left-button mouse event at a time, mid height.

        Inputs:
            plot_widget: the PlotWidget.
            event_type_name_str: "MouseButtonPress", "MouseMove" or
                "MouseButtonRelease".
            time_s: the time of the point.
            buttons_name_str: name of the Qt.MouseButton held after it.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        bottom_f, top_f = plot_widget.axes.get_ylim()
        canvas = plot_widget.canvas
        widget_point = plot_widget.data_to_widget_point(
            time_s, bottom_f + 0.3 * (top_f - bottom_f))
        local_point = QPointF(canvas.mapFrom(plot_widget, widget_point))
        button = (Qt.MouseButton.NoButton
                  if event_type_name_str == "MouseMove"
                  else Qt.MouseButton.LeftButton)
        self.application.sendEvent(canvas, QMouseEvent(
            getattr(QEvent.Type, event_type_name_str), local_point,
            QPointF(canvas.mapToGlobal(local_point)), button,
            getattr(Qt.MouseButton, buttons_name_str),
            Qt.KeyboardModifier.NoModifier))
        self.application.processEvents()

    def drag_area(self, plot_widget, start_s: float, end_s: float,
                  check_function=None) -> None:
        """Drag with the left button from one time to another.

        Inputs:
            plot_widget: the PlotWidget.
            start_s: the time of the press.
            end_s: the time of the release.
            check_function: optional function without arguments called
                before the release.
        Outputs: none.
        """
        self.send_left(plot_widget, "MouseButtonPress", start_s,
                       "LeftButton")
        for fraction_f in (0.5, 1.0):
            self.send_left(plot_widget, "MouseMove",
                           start_s + fraction_f * (end_s - start_s),
                           "LeftButton")
        if check_function is not None:
            check_function()
        self.send_left(plot_widget, "MouseButtonRelease", end_s, "NoButton")

    def area_list(self) -> list:
        """Return the areas of the model as (name, start, end).

        Inputs: none.
        Outputs: a list of tuples.
        """
        return [(area.name_str, area.start_s, area.end_s) for area in
                self.controller.plot_controller.workspace.area_list]

    @covers("LLFR-00303", "LLFR-00304", "LLFR-00310", "LLFR-00309",
            "LLFR-00138", "LLFR-00286")
    def test_drag_creates_an_area_on_every_time_plot(self) -> None:
        """A drag with the Area button creates "Area 1" on both plots,
        on a plot of another tab created later, and undo removes it from
        all of them.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.plot_tool_button_dict[AREA_TOOL_STR].click()
        self.application.processEvents()
        first_widget, second_widget = self.plot_widgets()
        self.drag_area(first_widget, 1.0, 2.5)
        self.assertEqual(len(self.area_list()), 1)
        name_str, start_s, end_s = self.area_list()[0]
        self.assertEqual(name_str, "Area 1")
        self.assertAlmostEqual(start_s, 1.0, delta=0.02)
        self.assertAlmostEqual(end_s, 2.5, delta=0.02)
        area_id_i = (self.controller.plot_controller.workspace
                     .area_list[0].area_id_i)
        for plot_widget in (first_widget, second_widget):
            self.assertEqual(plot_widget.area_id_list(), [area_id_i])
            self.assertEqual(plot_widget.area_label_text(area_id_i),
                             "Area 1")
        self.main_window.plot_panel.request_add_tab()
        self.main_window.signal_double_click_handler("speed")
        self.application.processEvents()
        (new_widget,) = self.plot_widgets()
        self.assertEqual(new_widget.area_id_list(), [area_id_i])
        self.controller.plot_controller.on_undo()
        self.controller.plot_controller.on_undo()
        self.controller.plot_controller.on_undo()
        self.application.processEvents()
        self.assertEqual(self.area_list(), [])
        for plot_widget in self.all_plot_widgets():
            self.assertEqual(plot_widget.area_id_list(), [])

    @covers("LLFR-00312", "LLFR-00310", "LLFR-00207", "LLFR-00140")
    def test_move_follows_on_the_tab_and_z_waits(self) -> None:
        """Moving an area shows it moving on the other plot of the tab
        before the release; the Z key does nothing during the drag; the
        move is one undoable action.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.plot_tool_button_dict[AREA_TOOL_STR].click()
        self.application.processEvents()
        first_widget, second_widget = self.plot_widgets()
        self.drag_area(first_widget, 1.0, 2.0)
        area_id_i = (self.controller.plot_controller.workspace
                     .area_list[0].area_id_i)
        self.zoom_in()
        undo_history = self.controller.plot_controller.undo_history
        depth_i = undo_history.depth()
        start_s, end_s = self.area_list()[0][1:]
        middle_s = (start_s + end_s) / 2.0

        def check_during_drag() -> None:
            """Check the other plot and the Z key mid-drag.

            Inputs: none.
            Outputs: none.
            """
            self.assertTrue(self.main_window.is_mouse_drag_in_progress())
            drawn_start_s = second_widget.area_drawn_span_tuple(
                area_id_i)[0]
            self.assertAlmostEqual(drawn_start_s, start_s + 0.3,
                                   delta=0.03)
            self.press_key("Key_Z", first_widget.canvas)
            self.release_key("Key_Z", first_widget.canvas)
            self.assert_every_range(self.zoomed_range())

        self.drag_area(first_widget, middle_s, middle_s + 0.3,
                       check_during_drag)
        new_start_s, new_end_s = self.area_list()[0][1:]
        self.assertAlmostEqual(new_start_s, start_s + 0.3, delta=0.03)
        self.assertAlmostEqual(new_end_s - new_start_s, end_s - start_s)
        self.assertEqual(undo_history.depth(), depth_i + 1)
        self.assertAlmostEqual(
            second_widget.area_drawn_span_tuple(area_id_i)[0], new_start_s)

    def zoomed_range(self) -> tuple:
        """Return the range zoom_in shows.

        Inputs: none.
        Outputs: the (start_s, end_s) of test_xyz_keys.
        """
        from tests.view.test_xyz_keys import ZOOMED_RANGE_TUPLE
        return ZOOMED_RANGE_TUPLE

    @covers("LLFR-00351", "LLFR-00310", "LLFR-00138", "LLFR-00192")
    def test_color_from_the_menu_on_every_plot_of_every_tab(self) -> None:
        """Choosing "Blue" in the area menu of one plot draws the area in
        blue on every time plot, the other tab included; undo and redo
        follow.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_rgb
        from view import theme
        self.top_panel.plot_tool_button_dict[AREA_TOOL_STR].click()
        self.application.processEvents()
        first_widget = self.plot_widgets()[0]
        self.drag_area(first_widget, 1.0, 2.0)
        area_id_i = (self.controller.plot_controller.workspace
                     .area_list[0].area_id_i)
        first_tab_id_i = self.main_window.current_tab_id()
        self.main_window.plot_panel.request_add_tab()
        self.main_window.signal_double_click_handler("speed")
        self.main_window.set_current_tab(first_tab_id_i)
        self.application.processEvents()
        self.assertEqual(len(self.all_plot_widgets()), 3)
        first_widget = self.plot_widgets()[0]
        first_widget.canvas.draw()
        point = first_widget.data_to_widget_point(
            1.5, first_widget.axes.get_ylim()[0] + 0.8 * (
                first_widget.axes.get_ylim()[1]
                - first_widget.axes.get_ylim()[0]))
        menu, request_list = first_widget.context_menu_and_requests(point)
        color_action = next(
            sub_action for action in menu.actions()
            if action.menu() is not None
            for sub_action in action.menu().actions()
            if sub_action.text() == "Blue")
        request_list[color_action.data()]()
        self.application.processEvents()

        def assert_color(name_str: str) -> None:
            """Check the band color of the area on every plot.

            Inputs:
                name_str: the expected color name.
            Outputs: none.
            """
            for plot_widget in self.all_plot_widgets():
                band = plot_widget.area_artist_tuple(area_id_i)[0]
                self.assertEqual(to_rgb(band.get_facecolor()),
                                 to_rgb(theme.AREA_COLOR_DICT[name_str]))

        assert_color("Blue")
        self.controller.plot_controller.on_undo()
        self.application.processEvents()
        assert_color("Magenta")
        self.controller.plot_controller.on_redo()
        self.application.processEvents()
        assert_color("Blue")

    @covers("LLFR-00129", "LLFR-00305")
    def test_export_draws_the_areas(self) -> None:
        """The figure rendered for the PDF holds the area band as an
        artist of its axes, and renders without error.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.top_panel.plot_tool_button_dict[AREA_TOOL_STR].click()
        self.application.processEvents()
        first_widget = self.plot_widgets()[0]
        self.drag_area(first_widget, 1.0, 2.0)
        area_id_i = (self.controller.plot_controller.workspace
                     .area_list[0].area_id_i)
        band = first_widget.area_artist_tuple(area_id_i)[0]
        self.assertIn(band, first_widget.axes.get_children())
        image = plot_export.render_figure_image(first_widget.figure, 100.0)
        self.assertFalse(image.isNull())
        self.assertTrue(band.get_visible())


if __name__ == "__main__":
    unittest.main()
