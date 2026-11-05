"""GUI tests of issue #183, Part A: menu titles, delta marker and arrow
labels, and renaming a label by double-click.

They use a shown plot widget (tests.view.test_plot_tools) and, for the
tabs, a real MainWindow with the real controllers. No modal dialog or
menu is ever left open: menus are built without being run, or shown
with popup and closed, and the rename dialogs are patched.
"""

import math
import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt
from tests.view.menu_texts import (
    ARROW_MENU_TEXT_LIST, AREA_MENU_TEXT_LIST, DELTA_MENU_TEXT_LIST,
    FLAG_MENU_TEXT_LIST, TIP_MENU_TEXT_LIST, menu_option_texts)
from tests.view.test_plot_tools import (
    ALL_TOOL_TUPLE, PlotWidgetToolTestCase, recorder)

from controller.plot_tools import NO_TOOL_STR, ZOOM_TOOL_STR
from model.workspace import DELTA_X_KIND_STR, DELTA_Y_KIND_STR

ORANGE_STR = "#ff8000"
GREEN_STR = "#00aa00"
# A Delta X marker on the ramp from 2 s to 4 s (3.2 to 3.4).
DELTA_X_TUPLE = (5, DELTA_X_KIND_STR, ("Ramp", 2.0, 3.2),
                 ("Ramp", 4.0, 3.4), 2.0, ORANGE_STR, "Delta X 1")
# An arrow from (1 s, 1.5) to (3 s, 2.5), with its name.
ARROW_TUPLE = (1.0, 1.5, 3.0, 2.5, ORANGE_STR, "Arrow 1")


def center_of(box) -> tuple:
    """Return the center of a matplotlib Bbox.

    Inputs:
        box: a Bbox in display pixels.
    Outputs: (x, y).
    """
    return ((float(box.x0) + float(box.x1)) / 2.0,
            (float(box.y0) + float(box.y1)) / 2.0)


@requires_qt
class LabelWidgetTestCase(PlotWidgetToolTestCase):
    """Base class: the plot widget with recorders and display helpers."""

    def setUp(self) -> None:
        """Create the widget and record every request a click can make.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        widget = self.plot_widget
        self.rename_dict = {
            "flag": recorder(widget.marker_rename_requested),
            "area": recorder(widget.area_rename_requested),
            "delta": recorder(widget.delta_marker_rename_requested),
            "arrow": recorder(widget.arrow_rename_requested)}
        self.other_list = []
        for signal in (widget.marker_place_requested,
                       widget.marker_move_requested,
                       widget.delta_point_picked,
                       widget.area_create_requested,
                       widget.area_change_requested,
                       widget.arrow_create_requested,
                       widget.arrow_change_requested,
                       widget.pinned_tip_move_requested,
                       widget.text_note_create_requested,
                       widget.text_note_edit_requested):
            signal.connect(lambda *argument_tuple:
                           self.other_list.append(argument_tuple))

    def send(self, event_name_str: str, display_tuple: tuple,
             button_i: int = 1, double_click_b: bool = False) -> None:
        """Send a matplotlib mouse event at a display point.

        Inputs:
            event_name_str: the matplotlib event name.
            display_tuple: (x, y) in display pixels.
            button_i: matplotlib button number (1 is the left button),
                or None for a move.
            double_click_b: True for the second press of a double-click.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseEvent
        mouse_event = MouseEvent(event_name_str, self.plot_widget.canvas,
                                 display_tuple[0], display_tuple[1],
                                 button=button_i, dblclick=double_click_b)
        self.plot_widget.canvas.callbacks.process(event_name_str,
                                                  mouse_event)

    def double_click(self, display_tuple: tuple) -> None:
        """Send a left double-click at a display point and let the
        deferred requests run.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: none.
        """
        self.send("button_press_event", display_tuple)
        self.send("button_release_event", display_tuple)
        self.send("button_press_event", display_tuple, double_click_b=True)
        self.send("button_release_event", display_tuple)
        for _ in range(3):
            self.application.processEvents()

    def widget_point(self, display_tuple: tuple):
        """Return the widget point of a display point.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: QPoint.
        """
        return self.plot_widget.display_to_widget_point(*display_tuple)

    def data_display(self, time_s: float, value_f: float) -> tuple:
        """Return the display point of a data point.

        Inputs:
            time_s: x value.
            value_f: y value.
        Outputs: (x, y) in display pixels.
        """
        display_array = self.plot_widget.axes.transData.transform(
            (time_s, value_f))
        return (float(display_array[0]), float(display_array[1]))

    def renderer(self):
        """Return the canvas renderer.

        Inputs: none.
        Outputs: the matplotlib renderer.
        """
        return self.plot_widget.canvas.get_renderer()

    def box_of(self, annotation):
        """Return the display box of an annotation, with its label box.

        Inputs:
            annotation: a matplotlib Annotation.
        Outputs: a Bbox.
        """
        return self.plot_widget.tip_box_extent(annotation, self.renderer())

    def build_menu(self, display_tuple: tuple):
        """Build the plot menu of a display point.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: the QMenu (to be deleted by the caller).
        """
        return self.plot_widget.build_context_menu(
            self.widget_point(display_tuple))


class MenuTitleTest(LabelWidgetTestCase):
    """The title of every plot menu (LLFR-00425, LLFR-00426,
    LLFR-00845 to LLFR-00850)."""

    def check_title(self, display_tuple: tuple, title_str: str,
                    option_list: list) -> None:
        """Check the title, separator and options of the menu at a point.

        Inputs:
            display_tuple: (x, y) in display pixels.
            title_str: the expected title.
            option_list: the expected options, in order.
        Outputs: none.
        """
        from PyQt6 import sip
        from view import theme
        from view.menu_title import is_menu_title, menu_title_label
        menu = self.build_menu(display_tuple)
        action_list = menu.actions()
        self.assertTrue(is_menu_title(action_list[0]))
        self.assertTrue(action_list[1].isSeparator())
        self.assertEqual(menu_title_label(menu).text(), title_str)
        # LLFR-00847 to LLFR-00849: disabled, so never highlighted and
        # with no request.
        self.assertFalse(action_list[0].isEnabled())
        self.assertIsNone(action_list[0].data())
        label = menu_title_label(menu)
        self.assertTrue(label.font().bold())
        self.assertIn(theme.MUTED_TEXT_COLOR_STR, label.styleSheet())
        self.assertIn("bold", label.styleSheet())
        self.assertEqual(menu_option_texts(menu), option_list)
        self.assertTrue(all(action.isEnabled()
                            for action in action_list[2:]))
        sip.delete(menu)

    @covers("LLFR-00425", "LLFR-00426", "LLFR-00845", "LLFR-00846",
            "LLFR-00847", "LLFR-00849", "LLFR-00378", "LLFR-00175",
            "HLFR-00096", "HLFR-00108", "HLFR-00109")
    def test_every_menu_has_its_title(self) -> None:
        """Curve, plot, pinned tip, flag, area, delta marker, text note
        and arrow menus start with the object's name, in bold and paler,
        then a separator.

        Inputs: none.
        Outputs: none.
        """
        widget = self.plot_widget
        with self.subTest(menu="curve"):
            self.check_title(self.data_display(5.0, 3.5), "Ramp",
                             ["Delete signal", "Width"])
        with self.subTest(menu="plot"):
            self.check_title(self.data_display(9.0, -0.5), "Plot",
                             ["Position", "Delete plot"])
        with self.subTest(menu="tip"):
            widget.set_pinned_tips([("Ramp", 4.0, 3.4, (0.0, -60.0))])
            self.draw()
            self.check_title(center_of(self.box_of(
                widget.pinned_tip_annotation(0))), "Ramp",
                TIP_MENU_TEXT_LIST)
            widget.set_pinned_tips([])
        with self.subTest(menu="flag"):
            widget.set_markers([(9, "Start", 4.0, ORANGE_STR)])
            self.draw()
            self.check_title(self.data_display(4.0, 2.0), "Start",
                             FLAG_MENU_TEXT_LIST)
            widget.set_markers([])
        with self.subTest(menu="area"):
            widget.set_areas([(1, "Warm-up", 6.0, 8.0, ORANGE_STR)])
            self.draw()
            self.check_title(self.data_display(7.0, 1.6), "Warm-up",
                             AREA_MENU_TEXT_LIST)
            widget.set_areas([])
        with self.subTest(menu="delta"):
            widget.set_delta_markers([DELTA_X_TUPLE])
            self.draw()
            self.check_title(self.data_display(2.0, 3.2), "Delta X 1",
                             DELTA_MENU_TEXT_LIST)
            widget.set_delta_markers([])
        with self.subTest(menu="text note"):
            widget.set_text_notes([("Note text", 4.5, 2.0)])
            self.draw()
            box = widget.text_note_box_extent(0)
            self.check_title(center_of(box), "Note text",
                             ["Edit", "Size", "Border color", "Text color",
                              "Delete"])
            widget.set_text_notes([])
        with self.subTest(menu="arrow"):
            widget.set_arrows([ARROW_TUPLE])
            self.draw()
            self.check_title(self.data_display(2.0, 2.0), "Arrow 1",
                             ARROW_MENU_TEXT_LIST)

    @covers("LLFR-00850", "LLFR-00426", "HLFR-00096")
    def test_long_title_is_shortened(self) -> None:
        """A name of more than 40 characters is shortened to 40 with
        "..." in the middle.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6 import sip
        from view.menu_title import menu_title_label
        long_name_str = "Flag_" + "a" * 50 + "_end"
        self.plot_widget.set_markers([(9, long_name_str, 4.0, ORANGE_STR)])
        self.draw()
        menu = self.build_menu(self.data_display(4.0, 2.0))
        title_str = menu_title_label(menu).text()
        self.assertEqual(len(title_str), 40)
        self.assertTrue(title_str.startswith("Flag_"))
        self.assertTrue(title_str.endswith("_end"))
        self.assertIn("...", title_str)
        sip.delete(menu)

    @covers("LLFR-00847", "LLFR-00848", "LLFR-00849", "HLFR-00109")
    def test_clicking_the_title_does_nothing(self) -> None:
        """A click on the title of a shown menu keeps the menu open and
        sends nothing; the keyboard skips the title.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6 import sip
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtGui import QCursor
        from view.menu_title import menu_title_label
        # QTest moves the pointer of the test session: put it back at
        # the end, so later tests see no hover.
        cursor_point = QCursor.pos()
        self.addCleanup(QCursor.setPos, cursor_point)
        self.plot_widget.set_markers([(9, "Start", 4.0, ORANGE_STR)])
        self.draw()
        menu = self.build_menu(self.data_display(4.0, 2.0))
        triggered_list = recorder(menu.triggered)
        menu.popup(self.plot_widget.mapToGlobal(QPoint(50, 50)))
        self.application.processEvents()
        title_label = menu_title_label(menu)
        title_action = menu.actions()[0]
        QTest.mouseMove(title_label)
        QTest.mouseClick(title_label, Qt.MouseButton.LeftButton)
        self.application.processEvents()
        self.assertTrue(menu.isVisible())
        self.assertEqual(triggered_list, [])
        self.assertIsNot(menu.activeAction(), title_action)
        self.assertEqual(sum(len(record_list) for record_list
                             in self.rename_dict.values()), 0)
        QTest.keyClick(menu, Qt.Key.Key_Down)
        self.application.processEvents()
        self.assertIsNot(menu.activeAction(), title_action)
        menu.close()
        self.application.processEvents()
        sip.delete(menu)

    @covers("LLFR-00429", "LLFR-00439", "LLFR-00175", "LLFR-00378",
            "HLFR-00110", "HLFR-00111")
    def test_rename_options_emit_their_request(self) -> None:
        """"Rename" of a delta marker or an arrow asks for its rename.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6 import sip
        self.plot_widget.set_delta_markers([DELTA_X_TUPLE])
        self.plot_widget.set_arrows([ARROW_TUPLE])
        self.draw()
        for display_tuple, kind_str, item_i in (
                (self.data_display(2.0, 3.2), "delta", 5),
                (self.data_display(2.0, 2.0), "arrow", 0)):
            menu = self.build_menu(display_tuple)
            rename_action = next(action for action in menu.actions()
                                 if action.text() == "Rename")
            rename_action.trigger()
            sip.delete(menu)
            self.assertEqual(self.rename_dict[kind_str], [(item_i,)])


class DeltaNameLabelTest(LabelWidgetTestCase):
    """The label of a delta marker's name (LLFR-00427, LLFR-00818,
    LLFR-00685)."""

    @covers("LLFR-00427", "LLFR-00818", "HLFR-00097")
    def test_name_drawn_above_the_value_in_its_color(self) -> None:
        """The name is shown in a label directly above the value, in the
        marker's color, also after a color change.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_hex
        widget = self.plot_widget
        widget.set_delta_markers([DELTA_X_TUPLE])
        self.draw()
        self.assertEqual(widget.delta_name_text(5), "Delta X 1")
        name_label = widget.delta_name_label(5)
        value_label = widget.delta_artist_tuple(5)[3]
        self.assertEqual(to_hex(name_label.get_color()), ORANGE_STR)
        name_box = self.box_of(name_label)
        value_box = self.box_of(value_label)
        self.assertGreaterEqual(float(name_box.y0), float(value_box.y1))
        self.assertLess(float(name_box.y0) - float(value_box.y1), 6.0)
        self.assertAlmostEqual(center_of(name_box)[0],
                               center_of(value_box)[0], delta=1.0)
        axes_box = widget.axes.bbox
        self.assertLessEqual(float(name_box.y1), float(axes_box.y1) + 0.5)
        green_tuple = DELTA_X_TUPLE[:5] + (GREEN_STR, "Lap")
        widget.set_delta_markers([green_tuple])
        self.draw()
        self.assertEqual(widget.delta_name_text(5), "Lap")
        self.assertEqual(to_hex(widget.delta_name_label(5).get_color()),
                         GREEN_STR)

    @covers("LLFR-00427", "LLFR-00685", "HLFR-00097")
    def test_delta_y_label_fits_inside_the_plot(self) -> None:
        """Near the right edge, a Delta Y marker with a long name is
        drawn mirrored, its value and name inside the plot.

        Inputs: none.
        Outputs: none.
        """
        widget = self.plot_widget
        widget.set_delta_markers([(
            6, DELTA_Y_KIND_STR, ("Ramp", 9.5, 3.95), ("Ramp", 9.9, 3.99),
            0.04, ORANGE_STR, "A rather long delta marker name")])
        self.draw()
        axes_box = widget.axes.bbox
        for annotation in (widget.delta_name_label(6),
                           widget.delta_artist_tuple(6)[3]):
            box = self.box_of(annotation)
            self.assertGreaterEqual(float(box.x0), float(axes_box.x0) - 0.5)
            self.assertLessEqual(float(box.x1), float(axes_box.x1) + 0.5)
            point_x_px = self.data_display(9.5, 3.95)[0]
            self.assertLess(float(box.x1), point_x_px)

    @covers("LLFR-00427", "LLFR-00353")
    def test_no_name_label_without_a_name(self) -> None:
        """Without a name (as for the preview), no name label is drawn.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_delta_markers([DELTA_X_TUPLE[:6]])
        self.draw()
        self.assertIsNone(self.plot_widget.delta_name_label(5))
        self.assertEqual(self.plot_widget.delta_name_text(5), "")


class ArrowLabelViewTest(LabelWidgetTestCase):
    """The label of an arrow's name (LLFR-00436, LLFR-00437,
    LLFR-00869 to LLFR-00871, LLFR-00373)."""

    def screen_angle_deg(self, arrow_index_i: int) -> float:
        """Return the angle of a drawn arrow's line on screen.

        Inputs:
            arrow_index_i: index of the arrow.
        Outputs: the angle in degrees, in (-90, 90].
        """
        start_tuple, end_tuple = self.plot_widget.arrow_display_tuple(
            arrow_index_i)
        angle_deg = math.degrees(math.atan2(end_tuple[1] - start_tuple[1],
                                            end_tuple[0] - start_tuple[0]))
        if angle_deg <= -90.0:
            angle_deg += 180.0
        if angle_deg > 90.0:
            angle_deg -= 180.0
        return angle_deg

    @covers("LLFR-00436", "LLFR-00869", "LLFR-00887", "LLFR-00373",
            "LLFR-01201", "LLFR-00788", "HLFR-00100")
    def test_label_parallel_readable_and_part_of_the_arrow(self) -> None:
        """The name is drawn next to the middle of the line, parallel to
        it as shown, never upside down, in the arrow's color; a point on
        it is on the arrow.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_hex
        widget = self.plot_widget
        # The second arrow points to the left and down.
        widget.set_arrows([ARROW_TUPLE,
                           (8.0, 2.5, 6.0, 1.5, GREEN_STR, "Back")])
        self.draw()
        for index_i, name_str, color_str in ((0, "Arrow 1", ORANGE_STR),
                                             (1, "Back", GREEN_STR)):
            with self.subTest(arrow=name_str):
                arrow_label = widget.arrow_label(index_i)
                self.assertEqual(arrow_label.get_text(), name_str)
                self.assertEqual(to_hex(arrow_label.get_color()), color_str)
                place_tuple = widget.arrow_label_place_tuple(index_i)
                self.assertAlmostEqual(place_tuple[2],
                                       self.screen_angle_deg(index_i),
                                       delta=0.5)
                self.assertGreater(place_tuple[2], -90.0)
                self.assertLessEqual(place_tuple[2], 90.0)
                start_tuple, end_tuple = widget.arrow_display_tuple(index_i)
                middle_tuple = ((start_tuple[0] + end_tuple[0]) / 2.0,
                                (start_tuple[1] + end_tuple[1]) / 2.0)
                self.assertLess(math.hypot(place_tuple[0] - middle_tuple[0],
                                           place_tuple[1] - middle_tuple[1]),
                                place_tuple[4])
                self.assertEqual(widget.arrow_at(self.widget_point(
                    place_tuple[:2])), index_i)

    @covers("LLFR-00437", "LLFR-00871", "HLFR-00112")
    def test_label_follows_the_range_and_hides(self) -> None:
        """A change of the time range moves the label with the arrow; it
        is hidden while no part of the line is shown.

        Inputs: none.
        Outputs: none.
        """
        widget = self.plot_widget
        widget.set_arrows([ARROW_TUPLE])
        self.draw()
        first_place_tuple = widget.arrow_label_place_tuple(0)
        widget.set_time_range(0.0, 5.0)
        self.draw()
        second_place_tuple = widget.arrow_label_place_tuple(0)
        self.assertGreater(abs(second_place_tuple[0]
                               - first_place_tuple[0]), 5.0)
        widget.set_time_range(5.0, 10.0)
        self.draw()
        self.assertEqual(widget.arrow_label_place_tuple(0), ())

    @covers("LLFR-00870", "LLFR-00376", "HLFR-00112")
    def test_label_follows_the_move_preview(self) -> None:
        """While the arrow is dragged with no tool, the label of the
        preview has its name and moves with the pointer.

        Inputs: none.
        Outputs: none.
        """
        widget = self.plot_widget
        widget.set_plot_tool(NO_TOOL_STR)
        widget.set_arrows([ARROW_TUPLE])
        self.draw()
        label_place_tuple = widget.arrow_label_place_tuple(0)
        press_tuple = self.data_display(2.0, 2.0)
        self.send("button_press_event", press_tuple)
        moved_tuple = (press_tuple[0] + 40.0, press_tuple[1])
        self.send("motion_notify_event", moved_tuple, None)
        preview_place_tuple = widget.arrow_preview_label_place_tuple()
        self.assertEqual(widget.arrow_preview_label.get_text(), "Arrow 1")
        self.assertAlmostEqual(preview_place_tuple[0] - label_place_tuple[0],
                               40.0, delta=2.0)
        self.assertAlmostEqual(preview_place_tuple[1], label_place_tuple[1],
                               delta=2.0)
        self.send("button_release_event", moved_tuple)
        self.assertEqual(widget.arrow_preview_label_place_tuple(), ())


class LabelContrastBoxTest(LabelWidgetTestCase):
    """Colored labels on an opaque box with a WCAG contrast of at least
    4.5:1 (LLFR-00704, LLFR-00436, LLFR-01202)."""

    def assert_contrast_box(self, text) -> None:
        """Check that a text is drawn on an opaque box that reads with it.

        Inputs:
            text: a matplotlib Text with a box.
        Outputs: none.
        """
        from matplotlib.colors import to_hex
        from view import theme
        text_color_str = to_hex(text.get_color())
        box_patch = text.get_bbox_patch()
        self.assertIsNotNone(box_patch)
        box_color_str = to_hex(box_patch.get_facecolor())
        self.assertEqual(box_color_str,
                         theme.area_label_box_color_str(text_color_str))
        self.assertIn(box_patch.get_alpha(), (None, 1.0))
        self.assertGreaterEqual(
            theme.contrast_ratio_f(text_color_str, box_color_str), 4.5)

    @covers("LLFR-00436", "LLFR-00704", "LLFR-00870", "HLFR-00100")
    def test_arrow_label_and_preview_on_a_contrast_box(self) -> None:
        """The label of an arrow in the default orange, in green and in
        a dark blue, and the label of the move preview in its pale
        color, each reach 4.5:1 on their box; orange gets a black box,
        the dark blue a white one.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_hex
        widget = self.plot_widget
        widget.set_plot_tool(NO_TOOL_STR)
        widget.set_arrows([ARROW_TUPLE,
                           (6.0, 1.5, 8.0, 2.5, GREEN_STR, "Green"),
                           (4.0, 1.0, 5.0, 2.0, "#1f3b8c", "Blue")])
        self.draw()
        for index_i in range(3):
            with self.subTest(arrow=index_i):
                self.assert_contrast_box(widget.arrow_label(index_i))
        self.assertEqual(to_hex(widget.arrow_label(0).get_bbox_patch()
                                .get_facecolor()), "#000000")
        self.assertEqual(to_hex(widget.arrow_label(2).get_bbox_patch()
                                .get_facecolor()), "#ffffff")
        press_tuple = self.data_display(2.0, 2.0)
        self.send("button_press_event", press_tuple)
        moved_tuple = (press_tuple[0] + 40.0, press_tuple[1])
        self.send("motion_notify_event", moved_tuple, None)
        self.assertEqual(widget.arrow_preview_label.get_text(), "Arrow 1")
        self.assert_contrast_box(widget.arrow_preview_label)
        self.send("button_release_event", moved_tuple)

    @covers("LLFR-01202", "LLFR-00704", "LLFR-00084", "LLFR-00092",
            "LLFR-00427", "LLFR-00169", "LLFR-00203", "LLFR-00353",
            "HLFR-00028", "HLFR-00097")
    def test_flag_and_delta_marker_labels_on_a_contrast_box(self) -> None:
        """The name and time of flags, the name and value of delta
        markers, and the texts of the flag and delta marker previews
        reach 4.5:1 on their boxes; the value keeps its colored border.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_hex
        widget = self.plot_widget
        widget.set_markers([(1, "Flag 1", 2.0, ORANGE_STR),
                            (2, "Dark", 4.0, "#1f3b8c")])
        widget.set_delta_markers([DELTA_X_TUPLE])
        self.draw()
        for marker_id_i in (1, 2):
            _, label, time_text = widget.marker_artist_tuple(marker_id_i)
            for text in (label, time_text):
                with self.subTest(flag=marker_id_i, text=text.get_text()):
                    self.assert_contrast_box(text)
        self.assert_contrast_box(widget.delta_name_label(5))
        value_label = widget.delta_artist_tuple(5)[3]
        self.assert_contrast_box(value_label)
        self.assertEqual(to_hex(value_label.get_bbox_patch()
                                .get_edgecolor()), ORANGE_STR)
        # The previews, in their paler color.
        self.assert_contrast_box(widget.preview_time_text)
        self.assert_contrast_box(widget.delta_preview_artist_tuple[2])


class LabelDoubleClickTest(LabelWidgetTestCase):
    """Renaming by a double-click on a label (LLFR-00420, LLFR-00842,
    LLFR-00422, LLFR-00843)."""

    def label_point_dict(self) -> dict:
        """Draw one flag, area, delta marker and arrow apart, and return
        the display point of each name label.

        Inputs: none.
        Outputs: a dict kind -> (display point, expected id or index).
        """
        widget = self.plot_widget
        widget.set_markers([(9, "Start", 8.5, ORANGE_STR)])
        widget.set_areas([(1, "Warm-up", 0.5, 2.0, ORANGE_STR)])
        widget.set_delta_markers([DELTA_X_TUPLE])
        widget.set_arrows([(5.0, -0.5, 7.0, 0.5, ORANGE_STR, "Arrow 1")])
        self.draw()
        return {
            "flag": (center_of(self.box_of(
                widget.marker_artist_tuple(9)[1])), 9),
            "area": (center_of(self.box_of(
                widget.area_artist_tuple(1)[1])), 1),
            "delta": (center_of(self.box_of(widget.delta_name_label(5))),
                      5),
            "arrow": (widget.arrow_label_place_tuple(0)[:2], 0)}

    @covers("LLFR-00420", "LLFR-00842", "HLFR-00094", "HLFR-00107",
            "HLFR-00110", "HLFR-00111")
    def test_double_click_renames_with_any_tool(self) -> None:
        """With every tool or none, a double-click on the name of a flag,
        an area, a delta marker or an arrow asks for its rename once and
        does nothing else.

        Inputs: none.
        Outputs: none.
        """
        point_dict = self.label_point_dict()
        for tool_str in ALL_TOOL_TUPLE:
            for kind_str, (display_tuple, item_i) in point_dict.items():
                with self.subTest(tool=tool_str, label=kind_str):
                    self.plot_widget.set_plot_tool(tool_str)
                    for record_list in self.rename_dict.values():
                        record_list.clear()
                    self.other_list.clear()
                    range_count_i = len(self.range_list)
                    pin_count_i = len(self.pin_list)
                    self.double_click(display_tuple)
                    self.assertEqual(self.rename_dict[kind_str],
                                     [(item_i,)])
                    self.assertEqual(sum(
                        len(record_list) for record_list
                        in self.rename_dict.values()), 1)
                    self.assertEqual(self.other_list, [])
                    self.assertEqual(len(self.range_list), range_count_i)
                    self.assertEqual(len(self.pin_list), pin_count_i)
                    self.assertFalse(
                        self.plot_widget.text_note_editor_open_b)
                    self.assertFalse(
                        self.plot_widget.is_mouse_drag_in_progress())

    @covers("LLFR-00886", "LLFR-00081", "LLFR-00078", "LLFR-00045",
            "LLFR-00333", "LLFR-00163", "LLFR-00798", "HLFR-00094",
            "HLFR-00107")
    def test_single_click_on_a_name_changes_nothing(self) -> None:
        """With every tool or none, a single left click on the name of a
        flag, an area, a delta marker or an arrow asks for nothing and
        changes nothing: no flag, zoom, data tip, text field or delta
        point.

        Inputs: none.
        Outputs: none.
        """
        point_dict = self.label_point_dict()
        for tool_str in ALL_TOOL_TUPLE:
            for kind_str, (display_tuple, _) in point_dict.items():
                with self.subTest(tool=tool_str, label=kind_str):
                    self.plot_widget.set_plot_tool(tool_str)
                    self.other_list.clear()
                    range_count_i = len(self.range_list)
                    pin_count_i = len(self.pin_list)
                    self.send("button_press_event", display_tuple)
                    self.send("button_release_event", display_tuple)
                    for _ in range(3):
                        self.application.processEvents()
                    self.assertEqual(self.other_list, [])
                    self.assertEqual(len(self.range_list), range_count_i)
                    self.assertEqual(len(self.pin_list), pin_count_i)
                    self.assertFalse(
                        self.plot_widget.text_note_editor_open_b)
                    self.assertEqual(sum(
                        len(record_list) for record_list
                        in self.rename_dict.values()), 0)

    def name_on_curve_tuple(self) -> tuple:
        """Draw a delta marker whose name label lies on a curve.

        A constant curve "Level" is drawn through the center of the name
        label of a Delta X marker on the sine, so that a hover tip, a
        pin or a delta point pick is possible there.

        Inputs: none.
        Outputs: the display point of the center of the name label.
        """
        import numpy as np
        widget = self.plot_widget
        delta_tuple = (7, DELTA_X_KIND_STR,
                       ("Sine", 4.6, float(np.sin(4.6))),
                       ("Sine", 5.0, float(np.sin(5.0))), 0.0, ORANGE_STR,
                       "Delta X 1")
        widget.set_delta_markers([delta_tuple])
        self.draw()
        center_tuple = center_of(self.box_of(widget.delta_name_label(7)))
        level_f = float(widget.axes.transData.inverted().transform(
            center_tuple)[1])
        widget.set_curves([
            ("Sine", self.time_array, self.sine_array, "#ff0000", 1),
            ("Ramp", self.time_array, self.ramp_array, "#0000ff", 1),
            ("Level", self.time_array,
             np.full_like(self.time_array, level_f), GREEN_STR, 1)])
        widget.set_delta_markers([delta_tuple])
        self.draw()
        center_tuple = center_of(self.box_of(widget.delta_name_label(7)))
        self.assertEqual(widget.name_label_tuple_at(
            self.widget_point(center_tuple)), ("delta", 7))
        self.assertEqual(widget.nearest_curve_tuple(
            self.widget_point(center_tuple))[0], "Level")
        return center_tuple

    def drag_from(self, display_tuple: tuple) -> None:
        """Hover a point, press there, move 20 pixels left and release.

        Inputs:
            display_tuple: (x, y) of the press, in display pixels.
        Outputs: none.
        """
        end_tuple = (display_tuple[0] - 20.0, display_tuple[1])
        self.send("motion_notify_event", display_tuple, None)
        self.send("button_press_event", display_tuple)
        self.send("motion_notify_event", end_tuple, None)
        self.send("button_release_event", end_tuple)
        self.application.processEvents()

    @covers("LLFR-00886", "LLFR-00798", "LLFR-00045", "HLFR-00094")
    def test_drag_from_a_name_pins_with_the_tip_tool(self) -> None:
        """With the Data tip tool, a drag of 5 pixels or more from a name
        label over a curve pins the tip, as elsewhere; a single click
        there pins nothing.

        Inputs: none.
        Outputs: none.
        """
        from controller.plot_tools import TIP_TOOL_STR
        center_tuple = self.name_on_curve_tuple()
        self.plot_widget.set_plot_tool(TIP_TOOL_STR)
        self.send("motion_notify_event", center_tuple, None)
        self.send("button_press_event", center_tuple)
        self.send("button_release_event", center_tuple)
        self.assertEqual(self.pin_list, [])
        self.drag_from(center_tuple)
        self.assertEqual(len(self.pin_list), 1)
        self.assertEqual(self.pin_list[0][0], "Level")

    @covers("LLFR-00886", "LLFR-00798", "LLFR-00163", "HLFR-00094")
    def test_drag_from_a_name_picks_with_the_delta_tools(self) -> None:
        """With the Delta X or Delta Y tool, a drag of 5 pixels or more
        from a name label over a curve picks the sample, as elsewhere.

        Inputs: none.
        Outputs: none.
        """
        from controller.plot_tools import DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR
        center_tuple = self.name_on_curve_tuple()
        pick_list = recorder(self.plot_widget.delta_point_picked)
        for tool_str in (DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                pick_list.clear()
                self.drag_from(center_tuple)
                self.assertEqual(len(pick_list), 1)
                self.assertEqual(pick_list[0][0], "Level")

    @covers("LLFR-00886", "LLFR-00166", "LLFR-00684", "LLFR-00163",
            "HLFR-00094")
    def test_click_on_a_name_over_a_curve_picks_nothing(self) -> None:
        """With the Delta X or Delta Y tool, a single click on a name
        label over a curve picks no point, so a first point picked in
        another plot is neither replaced nor discarded.

        Inputs: none.
        Outputs: none.
        """
        from controller.plot_tools import DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR
        center_tuple = self.name_on_curve_tuple()
        pick_list = recorder(self.plot_widget.delta_point_picked)
        for tool_str in (DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.send("button_press_event", center_tuple)
                self.send("button_release_event", center_tuple)
                self.application.processEvents()
                self.assertEqual(pick_list, [])

    @covers("LLFR-00886", "LLFR-00798", "LLFR-00081", "HLFR-00094")
    def test_drag_from_a_name_places_a_flag(self) -> None:
        """With the Flag tool, a drag of 5 pixels or more from the name of
        an area places a flag at the press, as elsewhere.

        Inputs: none.
        Outputs: none.
        """
        from controller.plot_tools import MARKER_TOOL_STR
        display_tuple = self.label_point_dict()["area"][0]
        place_list = recorder(self.plot_widget.marker_place_requested)
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.drag_from(display_tuple)
        self.assertEqual(len(place_list), 1)
        press_time_s = float(self.plot_widget.axes.transData.inverted(
        ).transform(display_tuple)[0])
        self.assertAlmostEqual(place_list[0][0], press_time_s, delta=0.05)

    @covers("LLFR-00886", "LLFR-00798", "LLFR-00333", "HLFR-00094")
    def test_drag_from_a_name_opens_the_text_field(self) -> None:
        """With the Text tool, a drag of 5 pixels or more from the name
        of an area opens the text field, as elsewhere.

        Inputs: none.
        Outputs: none.
        """
        from controller.plot_tools import TEXT_TOOL_STR
        display_tuple = self.label_point_dict()["area"][0]
        self.plot_widget.set_plot_tool(TEXT_TOOL_STR)
        self.drag_from(display_tuple)
        self.assertTrue(self.plot_widget.text_note_editor_open_b)
        self.plot_widget.cancel_text_note_editor()
        self.application.processEvents()

    @covers("LLFR-00886", "LLFR-00208", "HLFR-00094")
    def test_drag_from_a_name_still_zooms(self) -> None:
        """With the Zoom tool, a drag of 5 pixels or more from the name
        of a flag selects a time span and zooms, as elsewhere.

        Inputs: none.
        Outputs: none.
        """
        display_tuple = self.label_point_dict()["flag"][0]
        self.plot_widget.set_plot_tool(ZOOM_TOOL_STR)
        end_tuple = (display_tuple[0] - 80.0, display_tuple[1])
        self.send("button_press_event", display_tuple)
        self.send("motion_notify_event", end_tuple, None)
        self.send("button_release_event", end_tuple)
        self.application.processEvents()
        self.assertEqual(len(self.range_list), 1)

    @covers("LLFR-00422", "LLFR-00843", "LLFR-00844", "HLFR-00107")
    def test_double_click_on_values_renames_nothing(self) -> None:
        """A double-click on a flag's time, an area's times or a delta
        marker's value asks for no rename and changes no value.

        Inputs: none.
        Outputs: none.
        """
        widget = self.plot_widget
        self.label_point_dict()
        value_point_list = [
            center_of(self.box_of(widget.marker_artist_tuple(9)[2])),
            center_of(self.box_of(widget.area_artist_tuple(1)[2])),
            center_of(self.box_of(widget.delta_artist_tuple(5)[3]))]
        for tool_str in ALL_TOOL_TUPLE:
            widget.set_plot_tool(tool_str)
            for display_tuple in value_point_list:
                with self.subTest(tool=tool_str, point=display_tuple):
                    self.double_click(display_tuple)
                    self.assertEqual(sum(
                        len(record_list) for record_list
                        in self.rename_dict.values()), 0)
                    widget.cancel_text_note_editor()
                    self.application.processEvents()
        self.assertEqual(widget.marker_time_s(9), 8.5)
        self.assertEqual(widget.area_drawn_span_tuple(1), (0.5, 2.0))
        self.assertEqual(widget.delta_label_text(5),
                         widget.delta_value_text(DELTA_X_KIND_STR, 2.0))


@requires_qt
class TabDoubleClickTest(unittest.TestCase):
    """A double-click on a tab renames it (LLFR-00421)."""

    def setUp(self) -> None:
        """Create the window and the controllers.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.main_window = MainWindow()
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.main_window.show()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def double_click_tab(self, button, typed_name_str: str) -> list:
        """Double-click the first tab and answer the rename dialog.

        Inputs:
            button: the Qt.MouseButton of the double-click.
            typed_name_str: the text the user types and accepts.
        Outputs: the list of the getText calls.
        """
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtWidgets import QInputDialog
        tab_bar = self.main_window.plot_panel.tab_widget.tabBar()
        local_point = QPointF(tab_bar.tabRect(0).center())
        # The event is sent directly, so the mouse pointer of the test
        # session does not move and later tests see no hover.
        double_click_event = QMouseEvent(
            QEvent.Type.MouseButtonDblClick, local_point,
            QPointF(tab_bar.mapToGlobal(local_point)), button, button,
            Qt.KeyboardModifier.NoModifier)
        with mock.patch.object(QInputDialog, "getText",
                               return_value=(typed_name_str, True)) as (
                get_text):
            self.application.sendEvent(tab_bar, double_click_event)
            for _ in range(3):
                self.application.processEvents()
        return get_text.call_args_list

    @covers("LLFR-00421", "LLFR-00030", "HLFR-00094", "HLFR-00017")
    def test_left_double_click_renames_the_tab(self) -> None:
        """A left double-click opens the rename dialog with the tab's
        name, and the typed name is used as with "Rename".

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        call_list = self.double_click_tab(Qt.MouseButton.LeftButton,
                                          " Engine ")
        self.assertEqual(len(call_list), 1)
        self.assertIn("Tab 1", call_list[0].args)
        self.assertEqual(self.main_window.tab_name_list(), ["Engine"])

    @covers("LLFR-00421", "LLFR-00067", "HLFR-00094")
    def test_blank_name_or_right_double_click_keeps_the_name(self) -> None:
        """A blank typed name keeps the name; a right double-click opens
        no dialog.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        self.double_click_tab(Qt.MouseButton.LeftButton, "   ")
        self.assertEqual(self.main_window.tab_name_list(), ["Tab 1"])
        call_list = self.double_click_tab(Qt.MouseButton.RightButton,
                                          "Other")
        self.assertEqual(call_list, [])
        self.assertEqual(self.main_window.tab_name_list(), ["Tab 1"])


if __name__ == "__main__":
    unittest.main()
