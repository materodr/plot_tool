"""Tests for editing the objects of a plot with no plot tool active, and
for the objects that react to a press with each plot tool (HLFR-00085,
HLFR-00032: LLFR-00382 to LLFR-00384, LLFR-00086, LLFR-00312,
LLFR-00313, LLFR-00152, LLFR-00153, LLFR-00339, LLFR-00318).

The first classes drive one shown 600x400 plot widget (0 s to 10 s, a
sine between -1 and 1 and a ramp between 3 and 4) with matplotlib mouse
events; y = 2 is between the two curves, so a point there holds no
curve. The last class sends real Qt mouse and key events to a MainWindow
with the real controllers. No modal dialog or menu is ever opened.
"""

import math
import unittest

from tests.support import covers, requires_qt
from tests.view import test_areas_view
from tests.view.test_areas_view import EMPTY_VALUE_F
from tests.view.test_plot_tools import recorder
from tests.view.test_span_zoom import PIXEL_TOLERANCE_S, SpanWidgetTestCase
from tests.view.test_xyz_keys import XyzKeyWindowTestCase

from controller.plot_tools import (
    AREA_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR, PAN_TOOL_STR,
    PLOT_TOOL_TUPLE, TEXT_TOOL_STR, ZOOM_TOOL_STR)
from model.workspace import DELTA_X_KIND_STR


class EditWidgetTestCase(SpanWidgetTestCase):
    """Base class: the plot widget with no plot tool active, a flag at
    8 s, an area from 3 s to 5 s and recorders for every request."""

    def setUp(self) -> None:
        """Leave no tool active, draw the flag and the area, record.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        self.plot_widget.set_markers([(9, "Flag 1", 8.0)])
        self.plot_widget.set_areas([(1, "Area 1", 3.0, 5.0)])
        self.draw()
        widget = self.plot_widget
        self.move_list = recorder(widget.marker_move_requested)
        self.marker_drag_list = recorder(widget.marker_drag_moved)
        self.place_list = recorder(widget.marker_place_requested)
        self.change_list = recorder(widget.area_change_requested)
        self.create_list = recorder(widget.area_create_requested)
        self.area_drag_list = recorder(widget.area_drag_moved)
        self.tip_move_list = recorder(widget.pinned_tip_move_requested)
        self.note_move_list = recorder(widget.text_note_move_requested)
        self.note_create_list = recorder(widget.text_note_create_requested)
        self.pick_list = recorder(widget.delta_point_picked)

    def at(self, time_s: float, offset_x_i: int = 0):
        """Return the widget point at a time, between the curves.

        Inputs:
            time_s: the time, in seconds.
            offset_x_i: widget pixels added to x.
        Outputs: QPoint in the widget's coordinates.
        """
        from PyQt6.QtCore import QPoint
        return self.point_at(time_s, EMPTY_VALUE_F) + QPoint(offset_x_i, 0)

    def box_center_point(self, box):
        """Return the widget point at the center of a display box.

        Inputs:
            box: a matplotlib Bbox in display pixels.
        Outputs: QPoint in the widget's coordinates.
        """
        return self.plot_widget.display_to_widget_point(
            (box.x0 + box.x1) / 2.0, (box.y0 + box.y1) / 2.0)

    def add_tip(self, time_s: float = 4.0):
        """Pin a tip on the ramp, its label 60 points below the point.

        Inputs:
            time_s: the time of the point.
        Outputs: the widget point at the center of the tip's label.
        """
        self.plot_widget.set_pinned_tips(
            [("Ramp", time_s, 3.0 + 0.1 * time_s, (0.0, -60.0))])
        self.draw()
        annotation = self.plot_widget.pinned_tip_annotation(0)
        return self.box_center_point(
            self.plot_widget.tip_box_extent(annotation))

    def add_note_at(self, widget_point):
        """Write a text note whose place is at a widget point.

        Inputs:
            widget_point: QPoint in the widget's coordinates.
        Outputs: the text note's box, in display pixels.
        """
        display_tuple = self.plot_widget.widget_to_display_tuple(
            widget_point)
        time_s, value_f = self.plot_widget.axes.transData.inverted(
            ).transform(display_tuple)
        self.plot_widget.set_text_notes([("Note", float(time_s),
                                          float(value_f))])
        self.draw()
        return self.plot_widget.text_note_box_extent(0)

    def time_of_point(self, widget_point) -> float:
        """Return the time under a widget point.

        Inputs:
            widget_point: QPoint in the widget's coordinates.
        Outputs: the time, in seconds.
        """
        return self.plot_widget.time_at(widget_point)

    def assert_nothing_requested(self) -> None:
        """Check that no flag, area, tip or note request was made.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.move_list, [])
        self.assertEqual(self.marker_drag_list, [])
        self.assertEqual(self.place_list, [])
        self.assertEqual(self.change_list, [])
        self.assertEqual(self.create_list, [])
        self.assertEqual(self.area_drag_list, [])
        self.assertEqual(self.tip_move_list, [])
        self.assertEqual(self.note_move_list, [])
        self.assertEqual(self.note_create_list, [])
        self.assertEqual(self.pick_list, [])
        self.assertEqual(self.range_list, [])
        self.assertEqual(self.pin_list, [])


@requires_qt
class NoToolDragTest(EditWidgetTestCase):
    """With no plot tool active, a drag moves the object under it
    (LLFR-00382)."""

    @covers("LLFR-00382", "LLFR-00086", "LLFR-00093", "LLFR-00205",
            "LLFR-00207")
    def test_drag_moves_a_flag(self) -> None:
        """A drag on a flag moves it with the pointer, its time value
        follows, the other plots are told live, a drag is in progress
        until the release, and the release asks once for the move.

        Inputs: none.
        Outputs: none.
        """
        self.left_press(self.at(8.0))
        self.assertTrue(self.plot_widget.is_mouse_drag_in_progress())
        self.move_to(self.at(6.0))
        self.assertAlmostEqual(self.plot_widget.marker_time_s(9), 6.0,
                               delta=PIXEL_TOLERANCE_S)
        from view.plot_widget import format_time_text
        self.assertEqual(
            self.plot_widget.marker_time_text(9),
            format_time_text(self.plot_widget.marker_time_s(9)))
        self.assertTrue(self.marker_drag_list)
        self.assertEqual(self.marker_drag_list[-1][0], 9)
        self.assertEqual(self.move_list, [])
        self.left_release(self.at(6.5))
        self.assertEqual(len(self.move_list), 1)
        self.assertEqual(self.move_list[0][0], 9)
        self.assertAlmostEqual(self.move_list[0][1], 6.5,
                               delta=PIXEL_TOLERANCE_S)
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        self.assertEqual(self.place_list, [])
        self.assertEqual(self.range_list, [])

    @covers("LLFR-00382", "LLFR-00312", "LLFR-00308", "LLFR-00310",
            "LLFR-00207")
    def test_drag_inside_an_area_moves_it(self) -> None:
        """A drag from inside an area moves it keeping its width, live
        on the other plots, and the release asks once for the new span;
        no new area is ever created.

        Inputs: none.
        Outputs: none.
        """
        self.left_press(self.at(4.0))
        self.assertTrue(self.plot_widget.is_mouse_drag_in_progress())
        self.move_to(self.at(5.0))
        drawn_tuple = self.plot_widget.area_drawn_span_tuple(1)
        self.assertAlmostEqual(drawn_tuple[0], 4.0, delta=PIXEL_TOLERANCE_S)
        self.assertTrue(self.area_drag_list)
        self.left_release(self.at(5.5))
        self.assertEqual(len(self.change_list), 1)
        area_id_i, start_s, end_s = self.change_list[0]
        self.assertEqual(area_id_i, 1)
        self.assertAlmostEqual(start_s, 4.5, delta=PIXEL_TOLERANCE_S)
        self.assertAlmostEqual(end_s - start_s, 2.0)
        self.assertEqual(self.create_list, [])
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())

    @covers("LLFR-00382", "LLFR-00313")
    def test_drag_near_either_edge_resizes_the_area(self) -> None:
        """A drag within 5 pixels of the start or the end edge moves only
        that edge.

        Inputs: none.
        Outputs: none.
        """
        self.drag(self.at(3.0, 3), self.at(1.0))
        self.assertEqual(self.change_list[-1][0], 1)
        self.assertAlmostEqual(self.change_list[-1][1], 1.0,
                               delta=PIXEL_TOLERANCE_S)
        self.assertEqual(self.change_list[-1][2], 5.0)
        self.drag(self.at(5.0, -3), self.at(6.0))
        self.assertEqual(self.change_list[-1][1], 3.0)
        self.assertAlmostEqual(self.change_list[-1][2], 6.0,
                               delta=PIXEL_TOLERANCE_S)
        self.assertEqual(len(self.change_list), 2)
        self.assertEqual(self.create_list, [])

    @covers("LLFR-00382", "LLFR-00152", "LLFR-00153")
    def test_drag_moves_a_pinned_tip(self) -> None:
        """A drag on a pinned tip's label moves the label.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        tip_point = self.add_tip(1.0)
        self.drag(tip_point, tip_point + QPoint(40, 0))
        self.assertEqual(len(self.tip_move_list), 1)
        self.assertEqual(self.tip_move_list[0][0], 0)
        self.assertEqual(self.pin_list, [])

    @covers("LLFR-00382", "LLFR-00339")
    def test_drag_moves_a_text_note(self) -> None:
        """A drag on a text note moves it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        box = self.add_note_at(self.at(1.5))
        note_point = self.box_center_point(box)
        self.drag(note_point, note_point + QPoint(40, 0))
        self.assertEqual(len(self.note_move_list), 1)
        self.assertEqual(self.note_move_list[0][0], 0)
        self.assertEqual(self.note_create_list, [])

    @covers("LLFR-00382", "LLFR-00203", "LLFR-00303")
    def test_press_on_empty_space_or_a_curve_does_nothing(self) -> None:
        """A press and drag where no object is drawn, or on a curve,
        does nothing: no drag, no zoom, no pin, no new flag or area, no
        flag preview and no area preview.

        Inputs: none.
        Outputs: none.
        """
        for start_point, end_point in (
                (self.at(1.0), self.at(2.5)),
                (self.point_at(6.0, 3.6), self.point_at(7.0, 3.7)),
                (self.point_at(1.0, math.sin(1.0)),
                 self.point_at(2.0, math.sin(2.0)))):
            with self.subTest(start=(start_point.x(), start_point.y())):
                self.move_to(start_point)
                self.assertFalse(self.plot_widget.marker_preview_shown())
                self.left_press(start_point)
                self.assertFalse(
                    self.plot_widget.is_mouse_drag_in_progress())
                self.move_to(end_point)
                self.assertEqual(
                    self.plot_widget.area_preview_span_tuple(), ())
                self.assertFalse(self.plot_widget.time_span_line_shown())
                self.left_release(end_point)
        self.assertFalse(self.plot_widget.text_note_editor_open_b)
        self.assertEqual(self.plot_widget.marker_time_s(9), 8.0)
        self.assertEqual(self.plot_widget.area_drawn_span_tuple(1),
                         (3.0, 5.0))
        self.assert_nothing_requested()

    @covers("LLFR-00382", "LLFR-00384")
    def test_delta_marker_is_never_moved(self) -> None:
        """A press and drag on a delta marker's label with no tool active
        does nothing: the marker stays where it is.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_delta_markers([
            (5, DELTA_X_KIND_STR, ("Ramp", 6.0, 3.6), ("Ramp", 7.0, 3.7),
             1.0)])
        self.draw()
        label = self.plot_widget.delta_artist_tuple(5)[3]
        label_box = self.plot_widget.tip_box_extent(label)
        before_tuple = (label_box.x0, label_box.y0)
        label_point = self.box_center_point(label_box)
        self.assertEqual(self.plot_widget.delta_marker_at(label_point), 5)
        from PyQt6.QtCore import QPoint
        self.drag(label_point, label_point + QPoint(30, 20))
        label = self.plot_widget.delta_artist_tuple(5)[3]
        label_box = self.plot_widget.tip_box_extent(label)
        self.assertEqual((label_box.x0, label_box.y0), before_tuple)
        self.assertEqual(self.plot_widget.delta_marker_data_list[0][2],
                         ("Ramp", 6.0, 3.6))
        self.assert_nothing_requested()

    @covers("LLFR-00382", "LLFR-00086", "LLFR-00312")
    def test_press_and_release_without_move_changes_nothing(self) -> None:
        """A click on a flag or inside an area asks for nothing.

        Inputs: none.
        Outputs: none.
        """
        for press_point in (self.at(8.0), self.at(4.0), self.at(3.0, 1)):
            self.left_press(press_point)
            self.left_release(press_point)
        self.assert_nothing_requested()

    @covers("LLFR-00382", "LLFR-00205", "LLFR-00310")
    def test_follow_on_another_plot_with_no_tool(self) -> None:
        """A plot with no tool active shows a flag or an area dragged on
        another plot of the tab where the drag puts it.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.follow_marker_drag(9, 7.0)
        self.assertEqual(self.plot_widget.marker_time_s(9), 7.0)
        self.plot_widget.follow_area_drag(1, 3.5, 5.5)
        self.assertEqual(self.plot_widget.area_drawn_span_tuple(1),
                         (3.5, 5.5))


@requires_qt
class ObjectOrderTest(EditWidgetTestCase):
    """The first object at a pressed point reacts (LLFR-00383)."""

    @covers("LLFR-00383", "LLFR-00382", "LLFR-00318")
    def test_flag_inside_an_area_moves_the_flag(self) -> None:
        """A press on a flag drawn inside an area moves the flag, not
        the area, with no tool active.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_markers([(9, "Flag 1", 4.0)])
        self.draw()
        self.drag(self.at(4.0), self.at(6.0))
        self.assertEqual(len(self.move_list), 1)
        self.assertEqual(self.move_list[0][0], 9)
        self.assertEqual(self.change_list, [])
        self.assertEqual(self.area_drag_list, [])
        self.assertEqual(self.plot_widget.area_drawn_span_tuple(1),
                         (3.0, 5.0))

    @covers("LLFR-00383", "LLFR-00153")
    def test_pinned_tip_over_a_flag_and_an_area_moves_the_tip(
            self) -> None:
        """A press on a pinned tip drawn over a flag inside an area
        moves the tip only.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        tip_point = self.add_tip(4.0)
        self.plot_widget.set_markers(
            [(9, "Flag 1", self.time_of_point(tip_point))])
        self.draw()
        self.assertEqual(self.plot_widget.marker_at(tip_point), 9)
        self.assertEqual(self.plot_widget.area_at(tip_point), 1)
        self.drag(tip_point, tip_point + QPoint(40, 0))
        self.assertEqual(len(self.tip_move_list), 1)
        self.assertEqual(self.move_list, [])
        self.assertEqual(self.marker_drag_list, [])
        self.assertEqual(self.change_list, [])

    @covers("LLFR-00383", "LLFR-00339")
    def test_text_note_over_a_pinned_tip_moves_the_note(self) -> None:
        """A press where a text note and a pinned tip overlap, over a
        flag and an area, moves the note only.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        tip_point = self.add_tip(4.0)
        self.plot_widget.set_markers(
            [(9, "Flag 1", self.time_of_point(tip_point))])
        note_box = self.add_note_at(tip_point)
        tip_box = self.plot_widget.tip_box_extent(
            self.plot_widget.pinned_tip_annotation(0))
        overlap_point = self.plot_widget.display_to_widget_point(
            (max(note_box.x0, tip_box.x0) + min(note_box.x1, tip_box.x1))
            / 2.0,
            (max(note_box.y0, tip_box.y0) + min(note_box.y1, tip_box.y1))
            / 2.0)
        self.assertEqual(self.plot_widget.text_note_at(overlap_point), 0)
        self.assertEqual(self.plot_widget.pinned_tip_at(overlap_point), 0)
        self.drag(overlap_point, overlap_point + QPoint(40, 0))
        self.assertEqual(len(self.note_move_list), 1)
        self.assertEqual(self.tip_move_list, [])
        self.assertEqual(self.move_list, [])
        self.assertEqual(self.change_list, [])

    @covers("LLFR-00383", "LLFR-00086", "LLFR-00313")
    def test_among_the_same_kind_the_last_drawn_reacts(self) -> None:
        """Of two flags at the same time, the last placed moves; at the
        edge shared by two areas, the last created is resized.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_markers([(1, "Flag 1", 8.0),
                                      (2, "Flag 2", 8.0)])
        self.plot_widget.set_areas([(1, "Area 1", 3.0, 5.0),
                                    (2, "Area 2", 5.0, 7.0)])
        self.draw()
        self.drag(self.at(8.0), self.at(9.0))
        self.assertEqual([move_tuple[0] for move_tuple in self.move_list],
                         [2])
        self.drag(self.at(5.0), self.at(6.0))
        self.assertEqual(len(self.change_list), 1)
        area_id_i, start_s, end_s = self.change_list[0]
        self.assertEqual(area_id_i, 2)
        self.assertAlmostEqual(start_s, 6.0, delta=PIXEL_TOLERANCE_S)
        self.assertEqual(end_s, 7.0)


@requires_qt
class ActiveToolObjectsTest(EditWidgetTestCase):
    """With a plot tool active, only its own objects react
    (LLFR-00384)."""

    def press_drag_release(self, tool_str: str, start_point,
                           end_point) -> None:
        """Drag with a tool, closing a text field the Text tool opens,
        then show the whole time range again.

        Inputs:
            tool_str: the active tool.
            start_point: QPoint of the press.
            end_point: QPoint of the release.
        Outputs: none.
        """
        self.left_press(start_point)
        if tool_str == TEXT_TOOL_STR:
            # LLFR-00333: the press opens the text field, as elsewhere.
            self.assertTrue(self.plot_widget.text_note_editor_open_b)
            self.plot_widget.cancel_text_note_editor()
            self.application.processEvents()
        self.move_to(end_point)
        self.left_release(end_point)
        self.plot_widget.set_time_range(0.0, 10.0)
        self.draw()

    @covers("LLFR-00384", "LLFR-00086", "LLFR-00357", "LLFR-00078")
    def test_only_the_flag_tool_moves_a_flag(self) -> None:
        """With every tool but Flag, a drag on a flag leaves it where it
        is and acts as the tool does elsewhere (the Zoom tool zooms);
        with the Flag tool it moves.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in PLOT_TOOL_TUPLE:
            if tool_str == MARKER_TOOL_STR:
                continue
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                range_count_i = len(self.range_list)
                self.press_drag_release(tool_str, self.at(8.0),
                                        self.at(9.0))
                self.assertEqual(self.plot_widget.marker_time_s(9), 8.0)
                if tool_str == ZOOM_TOOL_STR:
                    self.assertGreater(len(self.range_list), range_count_i)
        self.assertEqual(self.move_list, [])
        self.assertEqual(self.marker_drag_list, [])
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.drag(self.at(8.0), self.at(9.0))
        self.assertEqual(len(self.move_list), 1)
        self.assertEqual(self.place_list, [])

    @covers("LLFR-00384", "LLFR-00318", "LLFR-00312", "LLFR-00313",
            "LLFR-00357")
    def test_only_the_area_tool_moves_or_resizes_an_area(self) -> None:
        """With every tool but Area, a drag inside an area or on its edge
        leaves it where it is; with the Area tool it moves; with the Area
        tool a press on a flag does not move the flag.

        Inputs: none.
        Outputs: none.
        """
        for tool_str in PLOT_TOOL_TUPLE:
            if tool_str == AREA_TOOL_STR:
                continue
            for start_point in (self.at(4.0), self.at(3.0, 2)):
                with self.subTest(tool=tool_str, x=start_point.x()):
                    self.plot_widget.set_plot_tool(tool_str)
                    self.press_drag_release(tool_str, start_point,
                                            self.at(4.6))
                    self.assertEqual(
                        self.plot_widget.area_drawn_span_tuple(1),
                        (3.0, 5.0))
        self.assertEqual(self.change_list, [])
        self.assertEqual(self.area_drag_list, [])
        self.plot_widget.set_plot_tool(AREA_TOOL_STR)
        self.drag(self.at(8.0), self.at(9.0))
        self.assertEqual(self.move_list, [])
        self.assertEqual(self.plot_widget.marker_time_s(9), 8.0)
        self.drag(self.at(4.0), self.at(4.5))
        self.assertEqual(len(self.change_list), 1)

    @covers("LLFR-00384", "LLFR-00153", "LLFR-00339", "LLFR-00357")
    def test_tips_and_notes_move_with_every_tool(self) -> None:
        """With every tool, and with none, a drag on a pinned tip moves
        the tip and a drag on a text note moves the note, and the tool
        does nothing else (no zoom, no pan, no new flag, area, note or
        pick).

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.add_tip(1.0)
        self.add_note_at(self.at(6.5))
        for count_i, tool_str in enumerate(
                PLOT_TOOL_TUPLE + (NO_TOOL_STR,), start=1):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                # The objects are found again where they are drawn now;
                # each drag goes up and down (left and right) in turn.
                step_i = 15 if count_i % 2 else -15
                tip_point = self.box_center_point(
                    self.plot_widget.tip_box_extent(
                        self.plot_widget.pinned_tip_annotation(0)))
                note_point = self.box_center_point(
                    self.plot_widget.text_note_box_extent(0))
                self.assertEqual(self.plot_widget.pinned_tip_at(note_point),
                                 -1)
                self.assertEqual(self.plot_widget.text_note_at(tip_point),
                                 -1)
                self.drag(tip_point, tip_point + QPoint(0, step_i))
                self.assertEqual(len(self.tip_move_list), count_i)
                self.drag(note_point, note_point + QPoint(step_i, 0))
                self.assertEqual(len(self.note_move_list), count_i)
                self.assertFalse(self.plot_widget.text_note_editor_open_b)
                self.draw()
        self.assertEqual(self.range_list, [])
        self.assertEqual(self.place_list, [])
        self.assertEqual(self.create_list, [])
        self.assertEqual(self.note_create_list, [])
        self.assertEqual(self.pick_list, [])
        self.assertEqual(self.pin_list, [])

    @covers("LLFR-00384", "LLFR-00357", "LLFR-00356")
    def test_pan_tool_pans_over_a_flag_and_an_area(self) -> None:
        """With the Pan tool and a zoomed plot, a drag on a flag or in an
        area pans and changes neither.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.plot_widget.set_plot_tool(PAN_TOOL_STR)
        for start_point in (self.at(8.0), self.at(4.0)):
            with self.subTest(x=start_point.x()):
                self.plot_widget.set_time_range(2.0, 9.0)
                self.draw()
                range_count_i = len(self.range_list)
                start_point = self.plot_widget.data_to_widget_point(
                    self.time_of_point(start_point), EMPTY_VALUE_F)
                self.drag(start_point, start_point + QPoint(-40, 0))
                self.assertGreater(len(self.range_list), range_count_i)
        self.assertEqual(self.move_list, [])
        self.assertEqual(self.change_list, [])
        self.assertEqual(self.marker_drag_list, [])
        self.assertEqual(self.area_drag_list, [])


@requires_qt
class EditWindowTest(XyzKeyWindowTestCase):
    """Real Qt mouse and key events in the main window with no tool
    active: two plots of 0 s to 4 s."""

    # The mouse helpers of the area window tests (not their tests, so
    # the class is not imported here, where unittest would run them).
    send_left = test_areas_view.AreaWindowTest.send_left
    drag_area = test_areas_view.AreaWindowTest.drag_area
    area_list = test_areas_view.AreaWindowTest.area_list

    def setUp(self) -> None:
        """Put a flag at 3 s and an area from 1 s to 2 s on every plot.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        plot_controller = self.controller.plot_controller
        plot_controller.workspace.add_marker(3.0)
        plot_controller.show_markers()
        plot_controller.workspace.add_area(1.0, 2.0)
        plot_controller.show_areas()
        self.draw_plots()
        self.marker_id_i = plot_controller.workspace.marker_list[
            0].marker_id_i
        self.area_id_i = plot_controller.workspace.area_list[0].area_id_i

    def flag_time_s(self) -> float:
        """Return the time of the flag in the model.

        Inputs: none.
        Outputs: the time, in seconds.
        """
        return self.controller.plot_controller.workspace.marker_list[
            0].time_s

    @covers("LLFR-00382", "LLFR-00086", "LLFR-00205", "LLFR-00207",
            "LLFR-00138", "LLFR-00140")
    def test_flag_drag_moves_it_on_every_time_plot(self) -> None:
        """With no tool, a drag moves the flag on the other plot of the
        tab before the release; Z does nothing during it; the move is one
        undoable action.

        Inputs: none.
        Outputs: none.
        """
        self.assert_tool_everywhere(NO_TOOL_STR)
        first_widget, second_widget = self.plot_widgets()
        zoomed_range_tuple = (2.5, 3.8)
        first_widget.zoom_to_range(*zoomed_range_tuple)
        self.application.processEvents()
        self.draw_plots()
        self.assert_every_range(zoomed_range_tuple)
        undo_history = self.controller.plot_controller.undo_history
        depth_i = undo_history.depth()

        def check_during_drag() -> None:
            """Check the other plot and the Z key mid-drag.

            Inputs: none.
            Outputs: none.
            """
            self.assertTrue(self.main_window.is_mouse_drag_in_progress())
            self.assertAlmostEqual(
                second_widget.marker_time_s(self.marker_id_i), 3.4,
                delta=0.03)
            self.press_key("Key_Z", first_widget.canvas)
            self.release_key("Key_Z", first_widget.canvas)
            self.assert_every_range(zoomed_range_tuple)

        self.drag_area(first_widget, 3.0, 3.4, check_during_drag)
        self.assertAlmostEqual(self.flag_time_s(), 3.4, delta=0.03)
        self.assertEqual(undo_history.depth(), depth_i + 1)
        self.assertFalse(self.main_window.is_mouse_drag_in_progress())
        self.assert_tool_everywhere(NO_TOOL_STR)
        self.controller.plot_controller.on_undo()
        self.application.processEvents()
        self.assertEqual(self.flag_time_s(), 3.0)
        for plot_widget in self.plot_widgets():
            self.assertEqual(plot_widget.marker_time_s(self.marker_id_i),
                             3.0)

    @covers("LLFR-00382", "LLFR-00312", "LLFR-00310", "LLFR-00138",
            "LLFR-00140")
    def test_area_move_is_one_undoable_action(self) -> None:
        """With no tool, a drag inside the area moves it on every plot as
        one undoable action, and creates no area.

        Inputs: none.
        Outputs: none.
        """
        first_widget, second_widget = self.plot_widgets()
        undo_history = self.controller.plot_controller.undo_history
        depth_i = undo_history.depth()
        self.drag_area(first_widget, 1.5, 2.0)
        self.assertEqual(len(self.area_list()), 1)
        name_str, start_s, end_s = self.area_list()[0]
        self.assertAlmostEqual(start_s, 1.5, delta=0.03)
        self.assertAlmostEqual(end_s - start_s, 1.0)
        self.assertEqual(undo_history.depth(), depth_i + 1)
        self.assertAlmostEqual(
            second_widget.area_drawn_span_tuple(self.area_id_i)[0], start_s)
        self.controller.plot_controller.on_undo()
        self.application.processEvents()
        self.assertEqual(self.area_list(), [(name_str, 1.0, 2.0)])

    @covers("LLFR-00382", "LLFR-00313", "LLFR-00140")
    def test_area_resize_with_no_tool(self) -> None:
        """With no tool, a drag on the end edge of the area resizes it.

        Inputs: none.
        Outputs: none.
        """
        first_widget = self.plot_widgets()[0]
        self.drag_area(first_widget, 2.0, 2.5)
        _, start_s, end_s = self.area_list()[0]
        self.assertEqual(start_s, 1.0)
        self.assertAlmostEqual(end_s, 2.5, delta=0.03)

    @covers("LLFR-00382", "LLFR-00384")
    def test_empty_press_and_other_tools_change_nothing(self) -> None:
        """With no tool, a drag on an empty part of the plot changes
        nothing and records nothing; with the Zoom tool, a drag on the
        flag or in the area zooms and moves neither.

        Inputs: none.
        Outputs: none.
        """
        first_widget = self.plot_widgets()[0]
        undo_history = self.controller.plot_controller.undo_history
        depth_i = undo_history.depth()
        self.drag_area(first_widget, 0.3, 0.7)
        self.assertEqual(undo_history.depth(), depth_i)
        self.assertEqual(self.area_list(), [("Area 1", 1.0, 2.0)])
        self.assert_every_range((0.0, 4.0))
        self.top_panel.plot_tool_button_dict[ZOOM_TOOL_STR].click()
        self.application.processEvents()
        self.drag_area(first_widget, 3.0, 3.5)
        self.assertEqual(self.flag_time_s(), 3.0)
        start_s, end_s = first_widget.time_range_tuple()
        self.assertAlmostEqual(start_s, 3.0, delta=0.03)
        self.assertAlmostEqual(end_s, 3.5, delta=0.03)
        self.assertEqual(self.area_list(), [("Area 1", 1.0, 2.0)])
        self.assertEqual(undo_history.depth(), depth_i)


if __name__ == "__main__":
    unittest.main()
