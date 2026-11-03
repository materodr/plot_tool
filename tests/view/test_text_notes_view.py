"""Tests for the text notes of the plot widget (issue #130).

Covers the one-line text field of the Text tool (LLFR-00333 to
LLFR-00335), the look of a note (LLFR-00336), its place when the range
or the size changes (LLFR-00337, LLFR-00338), dragging it with any tool
(LLFR-00339), its menu (LLFR-00341 to LLFR-00343), notes on a frequency
plot, notes in the exported images (LLFR-00129, LLFR-00133), and the
whole chain through MainWindow and the real controllers, including the
keys typed in the field (LLFR-00157, LLFR-00195, LLFR-00196, LLFR-00207).
No modal dialog or menu is ever opened: ``execute_menu`` is replaced.
"""

import unittest

import numpy as np

from tests.view.menu_texts import menu_option_texts
from tests.support import covers, get_qt_application, requires_qt
from tests.view.test_plot_tools import (
    ALL_TOOL_TUPLE, PlotWidgetToolTestCase, recorder)

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, TEXT_TOOL_STR, ZOOM_TOOL_STR)

# Allowed error, in display pixels, of positions rounded to whole widget
# pixels.
PIXEL_TOLERANCE_PX = 1.5
# An empty place of the test plot: between the sine (-1 to 1) and the
# ramp (3 to 4).
EMPTY_PLACE_TUPLE = (5.0, 2.0)


def all_menu_actions(menu) -> list:
    """Return the actions of a menu and of its submenus.

    Inputs:
        menu: a QMenu.
    Outputs: a list of QAction.
    """
    action_list = []
    for action in menu.actions():
        action_list.append(action)
        if action.menu() is not None:
            action_list.extend(all_menu_actions(action.menu()))
    return action_list


@requires_qt
class TextNoteWidgetTestCase(PlotWidgetToolTestCase):
    """Base class: the plot widget of PlotWidgetToolTestCase, active, with
    recorders for every request."""

    def setUp(self) -> None:
        """Make the widget's window active and record the requests.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        from PyQt6.QtTest import QTest
        self.plot_widget.activateWindow()
        self.assertTrue(QTest.qWaitForWindowActive(self.plot_widget))
        self.create_list = recorder(
            self.plot_widget.text_note_create_requested)
        self.move_list = recorder(self.plot_widget.text_note_move_requested)
        self.edit_list = recorder(self.plot_widget.text_note_edit_requested)
        self.delete_list = recorder(
            self.plot_widget.text_note_delete_requested)
        self.marker_place_list = recorder(
            self.plot_widget.marker_place_requested)
        self.delta_list = recorder(self.plot_widget.delta_point_picked)
        self.tip_move_list = recorder(
            self.plot_widget.pinned_tip_move_requested)
        self.editor = self.plot_widget.text_note_editor

    def send(self, name_str: str, display_tuple: tuple, button=None,
             double_click_b: bool = False) -> None:
        """Send a matplotlib mouse event to the canvas.

        Inputs:
            name_str: the matplotlib event name.
            display_tuple: (x, y) in display pixels.
            button: the matplotlib MouseButton, or None for a move.
            double_click_b: True for the second press of a double-click.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseEvent
        event = MouseEvent(name_str, self.plot_widget.canvas,
                           float(display_tuple[0]), float(display_tuple[1]),
                           button=button, dblclick=double_click_b)
        self.plot_widget.canvas.callbacks.process(name_str, event)

    def display_of(self, time_s: float, value_f: float) -> tuple:
        """Return the display pixels of a data point.

        Inputs:
            time_s: x value.
            value_f: y value.
        Outputs: (x, y) in display pixels.
        """
        point_array = self.plot_widget.axes.transData.transform(
            (time_s, value_f))
        return (float(point_array[0]), float(point_array[1]))

    def click_display(self, display_tuple: tuple) -> None:
        """Press and release the left button at a display point.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        self.send("button_press_event", display_tuple, MouseButton.LEFT)
        self.send("button_release_event", display_tuple, MouseButton.LEFT)
        self.application.processEvents()

    def drag_display(self, start_tuple: tuple, end_tuple: tuple) -> None:
        """Press at a point, move in two steps and release at another.

        Inputs:
            start_tuple: (x, y) of the press, in display pixels.
            end_tuple: (x, y) of the release, in display pixels.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        self.send("button_press_event", start_tuple, MouseButton.LEFT)
        self.send("motion_notify_event",
                  ((start_tuple[0] + end_tuple[0]) / 2.0,
                   (start_tuple[1] + end_tuple[1]) / 2.0))
        self.send("motion_notify_event", end_tuple)
        self.send("button_release_event", end_tuple, MouseButton.LEFT)
        self.application.processEvents()

    def type_and_press(self, text_str: str, key_name_str: str) -> None:
        """Type a text in the open field and press a key.

        Inputs:
            text_str: the text typed (after the field's text is
                replaced: it starts selected).
            key_name_str: name of the Qt.Key pressed afterwards.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        if text_str:
            QTest.keyClicks(self.editor, text_str)
        else:
            self.editor.clear()
        QTest.keyClick(self.editor, getattr(Qt.Key, key_name_str))
        self.application.processEvents()

    def open_field_at(self, time_s: float, value_f: float) -> None:
        """Click with the Text tool at a data point.

        Inputs:
            time_s: x value.
            value_f: y value.
        Outputs: none.
        """
        self.plot_widget.set_plot_tool(TEXT_TOOL_STR)
        self.click_display(self.display_of(time_s, value_f))

    def note_center(self, note_index_i: int = 0) -> tuple:
        """Return the center of a note's box, in display pixels.

        Inputs:
            note_index_i: index of the note.
        Outputs: (x, y).
        """
        box = self.plot_widget.text_note_box_extent(note_index_i)
        return ((float(box.x0) + float(box.x1)) / 2.0,
                (float(box.y0) + float(box.y1)) / 2.0)

    def choose_menu(self, display_tuple: tuple, text_str: str) -> list:
        """Right-click at a display point and choose a menu action.

        Inputs:
            display_tuple: (x, y) in display pixels.
            text_str: text of the action to choose, "" for none.
        Outputs: the texts of the top-level actions of the menu.
        """
        shown_list = []

        def fake_execute_menu(menu, global_point):
            """Record the menu and return the chosen action.

            Inputs:
                menu: the QMenu that would be shown.
                global_point: QPoint in screen coordinates.
            Outputs: the matching QAction, or None.
            """
            shown_list.extend(menu_option_texts(menu))
            for action in all_menu_actions(menu):
                if action.text() == text_str:
                    return action
            return None

        self.plot_widget.execute_menu = fake_execute_menu
        self.plot_widget.show_context_menu(
            self.plot_widget.display_to_widget_point(*display_tuple))
        self.application.processEvents()
        return shown_list


class TextFieldTest(TextNoteWidgetTestCase):
    """The one-line text field (LLFR-00333 to LLFR-00335)."""

    @covers("LLFR-00333")
    def test_click_opens_the_field_at_the_point_with_focus(self) -> None:
        """A click with the Text tool shows the field at the clicked
        point, with the keyboard focus in it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QLineEdit
        self.open_field_at(*EMPTY_PLACE_TUPLE)
        self.assertTrue(self.editor.isVisible())
        self.assertIsInstance(self.editor, QLineEdit)
        self.assertIs(self.application.focusWidget(), self.editor)
        clicked_point = self.plot_widget.data_to_widget_point(
            *EMPTY_PLACE_TUPLE)
        geometry = self.editor.geometry()
        self.assertLessEqual(abs(geometry.left() - clicked_point.x()), 1)
        self.assertLessEqual(abs(geometry.center().y() - clicked_point.y()),
                             2)
        self.assertEqual(self.create_list, [])

    @covers("LLFR-00333")
    def test_no_field_outside_the_drawing_area_or_without_tool(self) -> None:
        """A click on the margins, or without the Text tool, opens none.

        Inputs: none.
        Outputs: none.
        """
        axes_box = self.plot_widget.axes.bbox
        self.plot_widget.set_plot_tool(TEXT_TOOL_STR)
        self.click_display((float(axes_box.x0) - 20.0,
                            float(axes_box.y0) - 20.0))
        self.assertFalse(self.editor.isVisible())
        for tool_str in ALL_TOOL_TUPLE:
            if tool_str == TEXT_TOOL_STR:
                continue
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.click_display(self.display_of(*EMPTY_PLACE_TUPLE))
                self.assertFalse(self.plot_widget.text_note_editor_open_b)

    @covers("LLFR-00334", "LLFR-00734")
    def test_enter_confirms_at_the_clicked_values(self) -> None:
        """Enter removes the field and asks for a note with the text at
        the clicked x and y values.

        Inputs: none.
        Outputs: none.
        """
        self.open_field_at(*EMPTY_PLACE_TUPLE)
        self.type_and_press("Peak torque", "Key_Return")
        self.assertFalse(self.editor.isVisible())
        self.assertEqual(len(self.create_list), 1)
        text_str, time_s, value_f = self.create_list[0]
        self.assertEqual(text_str, "Peak torque")
        self.assertAlmostEqual(time_s, EMPTY_PLACE_TUPLE[0], delta=0.05)
        self.assertAlmostEqual(value_f, EMPTY_PLACE_TUPLE[1], delta=0.05)
        # The keypad's Enter acts the same.
        self.open_field_at(3.0, 2.5)
        self.type_and_press("second", "Key_Enter")
        self.assertEqual([entry[0] for entry in self.create_list],
                         ["Peak torque", "second"])

    @covers("LLFR-00334", "LLFR-00735")
    def test_blank_text_creates_nothing(self) -> None:
        """An empty field, or one with only spaces, asks for nothing.

        Inputs: none.
        Outputs: none.
        """
        for text_str in ("", "    "):
            with self.subTest(text=text_str):
                self.open_field_at(*EMPTY_PLACE_TUPLE)
                self.type_and_press(text_str, "Key_Return")
                self.assertFalse(self.editor.isVisible())
        self.assertEqual(self.create_list, [])
        self.assertEqual(
            [widget for widget in self.application.topLevelWidgets()
             if widget.isVisible() and widget.isModal()], [])

    @covers("LLFR-00335", "LLFR-00737", "LLFR-00738")
    def test_escape_cancels_silently(self) -> None:
        """Esc removes the field and asks for nothing.

        Inputs: none.
        Outputs: none.
        """
        self.open_field_at(*EMPTY_PLACE_TUPLE)
        self.type_and_press("not wanted", "Key_Escape")
        self.assertFalse(self.editor.isVisible())
        self.assertFalse(self.plot_widget.text_note_editor_open_b)
        self.application.processEvents()
        self.assertEqual(self.create_list, [])
        self.assertEqual(self.plot_widget.text_note_count(), 0)

    @covers("LLFR-00334", "LLFR-00734")
    def test_click_outside_confirms_and_does_nothing_else(self) -> None:
        """A click elsewhere on the plot confirms the text; that click
        opens no second field.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        self.open_field_at(*EMPTY_PLACE_TUPLE)
        QTest.keyClicks(self.editor, "outside")
        self.click_display(self.display_of(2.0, 2.5))
        self.assertEqual([entry[0] for entry in self.create_list],
                         ["outside"])
        self.assertFalse(self.plot_widget.text_note_editor_open_b)
        # The next click opens a field again.
        self.application.processEvents()
        self.click_display(self.display_of(2.0, 2.5))
        self.assertTrue(self.plot_widget.text_note_editor_open_b)

    @covers("LLFR-00334")
    def test_focus_to_another_widget_confirms(self) -> None:
        """The field also confirms when another widget takes the focus.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.open_field_at(*EMPTY_PLACE_TUPLE)
        QTest.keyClicks(self.editor, "focus")
        self.plot_widget.canvas.setFocus(Qt.FocusReason.MouseFocusReason)
        self.application.processEvents()
        self.assertEqual([entry[0] for entry in self.create_list], ["focus"])
        # The hidden field never confirms a second time.
        self.type_and_press("", "Key_Return")
        self.assertEqual(len(self.create_list), 1)

    @covers("LLFR-00333", "LLFR-00334", "LLFR-00733")
    def test_field_stays_open_when_the_tool_is_deactivated(self) -> None:
        """Deactivating the Text tool while typing keeps the field, and
        Enter still confirms it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
        self.open_field_at(*EMPTY_PLACE_TUPLE)
        QTest.keyClicks(self.editor, "kept")
        for tool_str in (NO_TOOL_STR, ZOOM_TOOL_STR, MARKER_TOOL_STR):
            self.plot_widget.set_plot_tool(tool_str)
            self.assertTrue(self.editor.isVisible())
            self.assertIs(self.application.focusWidget(), self.editor)
        from PyQt6.QtCore import Qt
        QTest.keyClick(self.editor, Qt.Key.Key_Return)
        self.assertEqual([entry[0] for entry in self.create_list], ["kept"])

    @covers("LLFR-00333", "LLFR-00340")
    def test_field_on_a_frequency_plot(self) -> None:
        """A frequency plot opens the field too, at a frequency in Hz.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from model.workspace import FREQUENCY_PLOT_KIND_STR
        from view.plot_widget import PlotWidget
        frequency_widget = PlotWidget(8, kind_str=FREQUENCY_PLOT_KIND_STR)
        frequency_widget.resize(600, 400)
        frequency_widget.show()
        frequency_widget.activateWindow()
        self.assertTrue(QTest.qWaitForWindowActive(frequency_widget))
        frequency_array = np.linspace(0.0, 50.0, 51)
        frequency_widget.set_curves([("fft_s", frequency_array,
                                      np.exp(-frequency_array / 10.0),
                                      "#0000ff", 1)])
        frequency_widget.canvas.draw()
        create_list = recorder(frequency_widget.text_note_create_requested)
        frequency_widget.set_plot_tool(TEXT_TOOL_STR)
        frequency_widget.press_at(
            frequency_widget.data_to_widget_point(20.0, 0.5))
        self.assertTrue(frequency_widget.text_note_editor.isVisible())
        QTest.keyClicks(frequency_widget.text_note_editor, "20 Hz")
        QTest.keyClick(frequency_widget.text_note_editor, Qt.Key.Key_Return)
        self.assertEqual(create_list[0][0], "20 Hz")
        self.assertAlmostEqual(create_list[0][1], 20.0, delta=0.3)
        frequency_widget.set_text_notes([("20 Hz", 20.0, 0.5)])
        frequency_widget.canvas.draw()
        self.assertTrue(frequency_widget.text_note_shown(0))
        frequency_widget.close()
        frequency_widget.deleteLater()
        self.application.processEvents()


class TextNoteDrawingTest(TextNoteWidgetTestCase):
    """How a note is drawn (LLFR-00336 to LLFR-00338, LLFR-00340)."""

    @covers("LLFR-00336")
    def test_dark_text_on_a_light_box_above_curves(self) -> None:
        """The text is dark, its box light and opaque, drawn above the
        curves, the grid and the pinned tips.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_hex
        from view import theme
        self.plot_widget.set_grid_shown(True)
        self.plot_widget.set_pinned_tips([("Ramp", 5.0, 3.5)])
        self.plot_widget.set_text_notes([("Readable", 5.0, 3.5)])
        self.draw()
        annotation = self.plot_widget.text_note_annotation(0)
        text_color_str = to_hex(annotation.get_color())
        box_color_str = to_hex(annotation.get_bbox_patch().get_facecolor())
        self.assertGreaterEqual(
            theme.contrast_ratio_f(text_color_str, box_color_str), 7.0)
        self.assertGreaterEqual(
            theme.contrast_ratio_f(box_color_str, "#000000"), 15.0)
        self.assertGreaterEqual(annotation.get_bbox_patch().get_alpha(),
                                0.9)
        self.assertEqual(annotation.get_text(), "Readable")
        highest_zorder_f = max(
            [line.get_zorder() for line in self.plot_widget.axes.lines]
            + [tip.get_zorder() for tip in
               self.plot_widget.pinned_annotation_list])
        self.assertGreater(annotation.get_zorder(), highest_zorder_f)
        self.assertTrue(self.plot_widget.text_note_shown(0))

    @covers("LLFR-00337")
    def test_note_follows_its_values_on_zoom_and_resize(self) -> None:
        """After a zoom or a resize the note is still at its point.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_text_notes([("at 4 s", 4.0, 2.0)])
        self.draw()
        for change in (lambda: self.plot_widget.zoom_to_range(2.0, 8.0),
                       lambda: self.plot_widget.resize(500, 300),
                       lambda: self.plot_widget.set_time_range(3.0, 5.0)):
            change()
            self.draw()
            box = self.plot_widget.text_note_box_extent(0)
            point_tuple = self.display_of(4.0, 2.0)
            self.assertTrue(self.plot_widget.text_note_shown(0))
            # The box starts at the point (left end, vertically centred),
            # with the box padding.
            self.assertLess(abs(float(box.x0) - point_tuple[0]), 12.0)
            self.assertLess(float(box.x0), point_tuple[0] + 0.5)
            self.assertAlmostEqual((float(box.y0) + float(box.y1)) / 2.0,
                                   point_tuple[1], delta=3.0)
            self.assertEqual(tuple(
                self.plot_widget.text_note_annotation(0).xy), (4.0, 2.0))

    @covers("LLFR-00337", "LLFR-00741")
    def test_note_hidden_while_its_values_are_outside(self) -> None:
        """A note is hidden, and cannot be hit, while its x or y value is
        outside the shown range, and comes back afterwards.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_text_notes([("hidden", 9.0, 2.0)])
        self.draw()
        self.assertTrue(self.plot_widget.text_note_shown(0))
        center_tuple = self.note_center()
        self.plot_widget.set_time_range(1.0, 5.0)
        self.draw()
        self.assertFalse(self.plot_widget.text_note_shown(0))
        self.assertEqual(self.plot_widget.text_note_at(
            self.plot_widget.display_to_widget_point(*center_tuple)), -1)
        # Its renderer skips it: the image has no note there.
        self.plot_widget.set_time_range(0.0, 10.0)
        self.draw()
        self.assertTrue(self.plot_widget.text_note_shown(0))
        # A y value outside the fitted y range hides it too.
        self.plot_widget.set_text_notes([("too high", 5.0, 100.0)])
        self.draw()
        self.assertFalse(self.plot_widget.text_note_shown(0))

    @covers("LLFR-00338")
    def test_note_kept_inside_the_drawing_area(self) -> None:
        """A note near an edge is moved the shortest way inside, and goes
        back to its point when there is room.

        Inputs: none.
        Outputs: none.
        """
        long_text_str = "a long note near the right edge of the plot"
        top_f = float(self.plot_widget.axes.get_ylim()[1])
        self.plot_widget.set_text_notes([(long_text_str, 9.9, top_f)])
        self.draw()
        axes_box = self.plot_widget.axes.bbox
        box = self.plot_widget.text_note_box_extent(0)
        self.assertLessEqual(float(box.x1), float(axes_box.x1) + 0.5)
        self.assertLessEqual(float(box.y1), float(axes_box.y1) + 0.5)
        # Moved only as far as needed: it touches the right and top edge.
        self.assertAlmostEqual(float(box.x1), float(axes_box.x1), delta=1.0)
        self.assertAlmostEqual(float(box.y1), float(axes_box.y1), delta=1.0)
        # The model place is unchanged.
        self.assertEqual(self.plot_widget.text_note_list[0][1:3],
                         (9.9, top_f))
        # Zoomed out, there is room on the point's right again (the note
        # is 12 points tall by default, LLFR-00385, so it needs about
        # three quarters of the plot's width).
        self.plot_widget.set_time_range(0.0, 40.0)
        self.draw()
        box = self.plot_widget.text_note_box_extent(0)
        point_tuple = self.display_of(9.9, top_f)
        self.assertLess(abs(float(box.x0) - point_tuple[0]), 12.0)

    @covers("LLFR-00338")
    def test_note_inside_after_a_smaller_plot(self) -> None:
        """Making the plot smaller keeps the note inside it.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_text_notes([("bottom left", 0.0, -1.0)])
        for width_i, height_i in ((600, 400), (300, 180), (200, 150)):
            self.plot_widget.resize(width_i, height_i)
            self.draw()
            axes_box = self.plot_widget.axes.bbox
            box = self.plot_widget.text_note_box_extent(0)
            if not self.plot_widget.text_note_shown(0):
                continue
            self.assertGreaterEqual(float(box.x0), float(axes_box.x0) - 0.5)
            self.assertGreaterEqual(float(box.y0), float(axes_box.y0) - 0.5)

    @covers("LLFR-00340", "LLFR-00745")
    def test_any_number_of_notes_and_redraws(self) -> None:
        """Many notes are drawn, and survive a redraw of the curves.

        Inputs: none.
        Outputs: none.
        """
        note_list = [(f"note {index_i}", float(index_i), 2.0)
                     for index_i in range(10)]
        self.plot_widget.set_text_notes(note_list)
        self.draw()
        self.assertEqual(self.plot_widget.text_note_count(), 10)
        self.plot_widget.set_curves([
            ("Sine", self.time_array, self.sine_array, "#ff0000", 2)])
        self.draw()
        self.assertEqual(self.plot_widget.text_note_count(), 10)
        self.assertEqual(
            [self.plot_widget.text_note_annotation(index_i).get_text()
             for index_i in range(10)],
            [note[0] for note in note_list])
        self.plot_widget.set_text_notes([])
        self.draw()
        self.assertEqual(self.plot_widget.text_note_count(), 0)
        self.assertEqual(
            [text for text in self.plot_widget.axes.texts
             if text.get_text().startswith("note ")], [])


class TextNoteDragTest(TextNoteWidgetTestCase):
    """Dragging a note (LLFR-00339, LLFR-00207)."""

    def setUp(self) -> None:
        """Draw one note on an empty place.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.plot_widget.set_text_notes([("drag me",) + EMPTY_PLACE_TUPLE])
        self.draw()

    @covers("LLFR-00339", "LLFR-00109", "LLFR-00742", "LLFR-00743")
    def test_drag_with_every_tool(self) -> None:
        """With any tool or none, a press on the note moves it, and does
        nothing else.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_markers([(1, "Flag 1", 5.0)])
        for tool_str in ALL_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.plot_widget.set_text_notes(
                    [("drag me",) + EMPTY_PLACE_TUPLE])
                self.plot_widget.set_plot_tool(tool_str)
                self.draw()
                self.move_list.clear()
                range_tuple = self.plot_widget.time_range_tuple()
                start_tuple = self.note_center()
                end_tuple = (start_tuple[0] - 60.0, start_tuple[1] - 30.0)
                self.drag_display(start_tuple, end_tuple)
                self.assertEqual(len(self.move_list), 1)
                note_index_i, time_s, value_f = self.move_list[0]
                self.assertEqual(note_index_i, 0)
                expected_array = (
                    self.plot_widget.axes.transData.inverted().transform(
                        (self.display_of(*EMPTY_PLACE_TUPLE)[0] - 60.0,
                         self.display_of(*EMPTY_PLACE_TUPLE)[1] - 30.0)))
                self.assertAlmostEqual(time_s, float(expected_array[0]),
                                       delta=0.05)
                self.assertAlmostEqual(value_f, float(expected_array[1]),
                                       delta=0.05)
                # The note is drawn at the drop place until redrawn.
                self.assertEqual(self.plot_widget.text_note_list[0][1:3],
                                 (time_s, value_f))
                self.assertEqual(self.pin_list, [])
                self.assertEqual(self.range_list, [])
                self.assertEqual(self.marker_place_list, [])
                self.assertEqual(self.delta_list, [])
                self.assertEqual(self.create_list, [])
                self.assertFalse(self.plot_widget.text_note_editor_open_b)
                self.assertEqual(self.plot_widget.marker_time_s(1), 5.0)
                self.assertEqual(self.plot_widget.time_range_tuple(),
                                 range_tuple)
                self.assertEqual(self.plot_widget.plot_tool_str, tool_str)

    @covers("LLFR-00339", "LLFR-00153", "LLFR-00743")
    def test_note_over_a_pinned_tip_wins(self) -> None:
        """A press where a note covers a pinned tip moves the note.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_pinned_tips([("Ramp", 5.0, 3.5)])
        self.plot_widget.set_text_notes([("over the tip", 5.0, 3.5)])
        self.draw()
        start_tuple = self.note_center()
        self.drag_display(start_tuple, (start_tuple[0], start_tuple[1] - 50))
        self.assertEqual(len(self.move_list), 1)
        self.assertEqual(self.tip_move_list, [])

    @covers("LLFR-00339")
    def test_click_without_move_and_place_kept_inside(self) -> None:
        """A press and release without a move asks for nothing; a drag
        far out of the plot leaves the note's point on its edge.

        Inputs: none.
        Outputs: none.
        """
        self.click_display(self.note_center())
        self.assertEqual(self.move_list, [])
        self.plot_widget.set_plot_tool(TEXT_TOOL_STR)
        self.click_display(self.note_center())
        # A click on a note with the Text tool opens no field.
        self.assertFalse(self.plot_widget.text_note_editor_open_b)
        self.drag_display(self.note_center(), (5000.0, -5000.0))
        self.assertEqual(len(self.move_list), 1)
        _, time_s, value_f = self.move_list[0]
        start_s, end_s = self.plot_widget.axes.get_xlim()
        low_f, high_f = self.plot_widget.axes.get_ylim()
        self.assertAlmostEqual(time_s, end_s, delta=1e-6 + 1e-9 * end_s)
        self.assertAlmostEqual(value_f, low_f, delta=1e-6 + abs(low_f) * 1e-9)
        self.draw()
        self.assertTrue(self.plot_widget.text_note_shown(0))

    @covers("LLFR-00207", "LLFR-00339", "LLFR-00454")
    def test_drag_counts_as_a_mouse_drag(self) -> None:
        """From the press to the release, a note drag is a mouse drag.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        start_tuple = self.note_center()
        self.send("button_press_event", start_tuple, MouseButton.LEFT)
        self.assertTrue(self.plot_widget.is_mouse_drag_in_progress())
        self.send("motion_notify_event", (start_tuple[0] + 20.0,
                                          start_tuple[1]))
        self.assertTrue(self.plot_widget.is_mouse_drag_in_progress())
        self.send("button_release_event", (start_tuple[0] + 20.0,
                                           start_tuple[1]),
                  MouseButton.LEFT)
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        # A right press cancels a drag and puts the note back.
        self.move_list.clear()
        start_tuple = self.note_center()
        self.send("button_press_event", start_tuple, MouseButton.LEFT)
        self.send("motion_notify_event", (start_tuple[0] + 40.0,
                                          start_tuple[1]))
        self.plot_widget.execute_menu = lambda menu, point: None
        self.send("button_press_event", start_tuple, MouseButton.RIGHT)
        self.application.processEvents()
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        self.assertEqual(self.move_list, [])
        self.assertTrue(self.plot_widget.text_note_shown(0))


class TextNoteMenuTest(TextNoteWidgetTestCase):
    """The text note menu (LLFR-00341 to LLFR-00343, LLFR-00048)."""

    def setUp(self) -> None:
        """Draw a note over the ramp curve and a vertical marker.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.plot_widget.set_markers([(1, "Flag 1", 6.0)])
        self.plot_widget.set_delta_markers([
            (1, "y", ("Ramp", 6.0, 3.6), ("Ramp", 7.0, 3.7), 0.1)])
        self.plot_widget.set_text_notes([("over items", 5.9, 3.59)])
        self.draw()

    @covers("LLFR-00341", "LLFR-00048", "LLFR-00385", "LLFR-00387")
    def test_menu_over_curve_and_markers(self) -> None:
        """A right-click on the note shows Edit, Size, Border color, Text
        color and Delete only, in this order, also over a curve, a
        vertical marker and a delta marker.

        Inputs: none.
        Outputs: none.
        """
        center_tuple = self.note_center()
        widget_point = self.plot_widget.display_to_widget_point(
            *center_tuple)
        self.assertNotEqual(self.plot_widget.text_note_at(widget_point), -1)
        shown_list = self.choose_menu(center_tuple, "")
        self.assertEqual(shown_list, ["Edit", "Size", "Border color",
                                      "Text color", "Delete"])
        # Away from the note, the plot's own menus come back.
        self.assertEqual(self.choose_menu(self.display_of(1.0, 1.5), ""),
                         ["Delete plot"])

    @covers("LLFR-00343")
    def test_delete_asks_for_the_note(self) -> None:
        """Delete asks to remove that note.

        Inputs: none.
        Outputs: none.
        """
        self.choose_menu(self.note_center(), "Delete")
        self.assertEqual(self.delete_list, [(0,)])
        self.assertEqual(self.plot_widget.marker_id_list(), [1])

    @covers("LLFR-00342", "LLFR-00333", "LLFR-00746")
    def test_edit_opens_the_field_with_the_text(self) -> None:
        """Edit shows the field over the note with its text; Enter asks
        for the new text; a blank text asks for nothing.

        Inputs: none.
        Outputs: none.
        """
        box = self.plot_widget.text_note_box_extent(0)
        self.choose_menu(self.note_center(), "Edit")
        self.assertTrue(self.editor.isVisible())
        self.assertEqual(self.editor.text(), "over items")
        self.assertIs(self.application.focusWidget(), self.editor)
        left_point = self.plot_widget.display_to_widget_point(
            float(box.x0), float(box.y0))
        self.assertLessEqual(abs(self.editor.geometry().left()
                                 - left_point.x()), 2)
        self.type_and_press("edited", "Key_Return")
        self.assertEqual(self.edit_list, [(0, "edited")])
        self.assertEqual(self.create_list, [])
        self.choose_menu(self.note_center(), "Edit")
        self.type_and_press("   ", "Key_Return")
        self.assertEqual(self.edit_list, [(0, "edited")])
        self.choose_menu(self.note_center(), "Edit")
        self.type_and_press("x", "Key_Escape")
        self.assertEqual(self.edit_list, [(0, "edited")])


class EditFieldRebindTest(TextNoteWidgetTestCase):
    """The Edit field never changes another note (LLFR-00342)."""

    @covers("LLFR-00342", "LLFR-00138", "LLFR-00192")
    def test_edit_field_closed_when_the_notes_change(self) -> None:
        """When the notes are drawn again with another list (as after an
        undo or a redo), an open Edit field is closed and Enter writes
        nothing; the same list keeps it open.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        note_list = [("first", 2.0, 2.0), ("second", 6.0, 2.0)]
        self.plot_widget.set_text_notes(note_list)
        self.draw()
        self.plot_widget.edit_text_note_at(1)
        self.assertTrue(self.editor.isVisible())
        # The same notes drawn again keep the field.
        self.plot_widget.set_text_notes(list(note_list))
        self.assertTrue(self.editor.isVisible())
        QTest.keyClicks(self.editor, "changed")
        # An undo puts a note back before the edited one.
        self.plot_widget.set_text_notes(
            [("restored", 1.0, 1.0)] + note_list)
        self.application.processEvents()
        self.assertFalse(self.editor.isVisible())
        self.assertFalse(self.plot_widget.text_note_editor_open_b)
        QTest.keyClick(self.editor, Qt.Key.Key_Return)
        self.application.processEvents()
        self.assertEqual(self.edit_list, [])
        self.assertEqual(self.create_list, [])

    @covers("LLFR-00333", "LLFR-00340")
    def test_new_note_field_stays_open_when_the_notes_change(
            self) -> None:
        """A field for a new note keeps its clicked place when the notes
        are drawn again.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.open_field_at(*EMPTY_PLACE_TUPLE)
        QTest.keyClicks(self.editor, "new")
        self.plot_widget.set_text_notes([("other", 1.0, 1.0)])
        self.assertTrue(self.editor.isVisible())
        QTest.keyClick(self.editor, Qt.Key.Key_Return)
        self.assertEqual([entry[0] for entry in self.create_list], ["new"])


class TextNoteImageTest(TextNoteWidgetTestCase):
    """Notes in the PDF pages and the copied image (LLFR-00129,
    LLFR-00133)."""

    @covers("LLFR-00129", "LLFR-00133", "LLFR-00337", "LLFR-00387",
            "LLFR-00739", "LLFR-00741", "LLFR-00808")
    def test_rendered_figure_shows_shown_notes_only(self) -> None:
        """The figure image of the export holds the note, in its own
        border and text colors, and a hidden note is not in it.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export

        def note_pixel_count(image) -> int:
            """Count the pixels close to the note's magenta.

            Inputs:
                image: a QImage.
            Outputs: the count.
            """
            count_i = 0
            for y_i in range(0, image.height(), 2):
                for x_i in range(0, image.width(), 2):
                    color = image.pixelColor(x_i, y_i)
                    if (color.red() >= 200 and color.green() <= 60
                            and color.blue() >= 200):
                        count_i += 1
            return count_i

        figure = self.plot_widget.figure
        empty_count_i = note_pixel_count(
            plot_export.render_figure_image(figure, figure.dpi))
        self.plot_widget.set_text_notes(
            [("Exported note text", 2.0, 2.0, 16, "#ff00ff", "#ff00ff")])
        self.draw()
        shown_count_i = note_pixel_count(
            plot_export.render_figure_image(figure, 2.0 * figure.dpi))
        self.assertGreater(shown_count_i, empty_count_i + 50)
        self.plot_widget.set_time_range(4.0, 8.0)
        self.draw()
        hidden_count_i = note_pixel_count(
            plot_export.render_figure_image(figure, figure.dpi))
        self.assertLessEqual(hidden_count_i, empty_count_i + 5)


@requires_qt
class TextNoteEndToEndTest(unittest.TestCase):
    """Text notes through MainWindow and the real controllers."""

    def setUp(self) -> None:
        """Create the window with a file and one plot, and show it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtTest import QTest
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
            "Time": time_array, "speed": time_array * 2.0})
        self.controller.plot_controller.on_file_opened(signal_file, False)
        self.controller.signal_list_controller.on_file_opened(
            signal_file, False)
        self.main_window.show()
        self.main_window.signal_double_click_handler("speed")
        self.process_events()
        self.main_window.activateWindow()
        self.assertTrue(QTest.qWaitForWindowActive(self.main_window))
        self.plot_widget = list(
            self.main_window.plot_panel.plot_widget_dict.values())[0]
        self.plot_widget.canvas.draw()
        self.plot_controller = self.controller.plot_controller

    def tearDown(self) -> None:
        """Release any held key and close the window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.tool_key_filter.handle_keyboard_lost()
        self.main_window.close()
        self.main_window.deleteLater()
        self.process_events()

    def process_events(self) -> None:
        """Let Qt handle pending events and deferred calls.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(3):
            self.application.processEvents()

    def model_notes(self) -> list:
        """Return the notes of the plot in the model.

        Inputs: none.
        Outputs: a list of (text_str, time_s, value_f).
        """
        plot = self.plot_controller.workspace.find_plot(
            self.plot_widget.plot_id_i)
        return [(note.text_str, note.time_s, note.value_f)
                for note in plot.text_note_list]

    def open_field(self, time_s: float = 2.0) -> None:
        """Activate the Text tool and click the plot.

        Inputs:
            time_s: x value of the click (y is 4); a place with no note.
        Outputs: none.
        """
        self.main_window.top_panel.plot_tool_button_dict[
            TEXT_TOOL_STR].click()
        self.process_events()
        self.plot_widget = list(
            self.main_window.plot_panel.plot_widget_dict.values())[0]
        self.plot_widget.press_at(
            self.plot_widget.data_to_widget_point(time_s, 4.0))
        self.process_events()
        self.assertIs(self.application.focusWidget(),
                      self.plot_widget.text_note_editor)

    @covers("LLFR-00334", "LLFR-00140", "LLFR-00138", "LLFR-00192",
            "HLFR-00073")
    def test_write_undo_and_redo(self) -> None:
        """A confirmed text is kept by the controller; Undo and Redo
        remove it and bring it back.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.open_field()
        editor = self.plot_widget.text_note_editor
        QTest.keyClicks(editor, "Shift change")
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.process_events()
        self.assertEqual([note[0] for note in self.model_notes()],
                         ["Shift change"])
        self.assertEqual(self.plot_widget.text_note_count(), 1)
        self.main_window.run_undo()
        self.process_events()
        self.assertEqual(self.model_notes(), [])
        self.main_window.run_redo()
        self.process_events()
        self.assertEqual([note[0] for note in self.model_notes()],
                         ["Shift change"])
        plot_widget = list(
            self.main_window.plot_panel.plot_widget_dict.values())[0]
        self.assertEqual(plot_widget.text_note_count(), 1)

    @covers("LLFR-00157", "LLFR-00195", "LLFR-00196", "LLFR-00207",
            "LLFR-00321")
    def test_keys_in_the_field_act_on_the_text_only(self) -> None:
        """While typing, T, A, X, Y, Z, Shift, Ctrl+Z and Ctrl+Y change
        neither the tool, the range nor the undo history.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.plot_widget.zoom_to_range(1.0, 3.0)
        self.process_events()
        self.open_field()
        editor = self.plot_widget.text_note_editor
        undo_depth_i = len(
            self.plot_controller.undo_history.saved_snapshot_list())
        QTest.keyClicks(editor, "TAXYZtaxyz")
        QTest.keyClick(editor, Qt.Key.Key_Shift,
                       Qt.KeyboardModifier.ShiftModifier)
        self.process_events()
        self.assertEqual(editor.text(), "TAXYZtaxyz")
        self.assertEqual(self.plot_controller.plot_tool_str, TEXT_TOOL_STR)
        self.assertEqual(self.plot_widget.time_range_tuple(), (1.0, 3.0))
        self.main_window._on_undo_shortcut()
        self.main_window._on_redo_shortcut()
        self.process_events()
        self.assertEqual(
            len(self.plot_controller.undo_history.saved_snapshot_list()),
            undo_depth_i)
        self.assertTrue(editor.isVisible())
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.process_events()
        self.assertEqual([note[0] for note in self.model_notes()],
                         ["TAXYZtaxyz"])

    @covers("LLFR-00339", "LLFR-00341", "LLFR-00342", "LLFR-00343",
            "HLFR-00074", "HLFR-00075", "HLFR-00076")
    def test_move_edit_and_delete_through_the_controller(self) -> None:
        """Drag, Edit and Delete change the model, and each is undone.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton, MouseEvent
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.open_field()
        QTest.keyClicks(self.plot_widget.text_note_editor, "note")
        QTest.keyClick(self.plot_widget.text_note_editor, Qt.Key.Key_Return)
        self.process_events()
        self.main_window.top_panel.plot_tool_button_dict[
            TEXT_TOOL_STR].click()
        self.process_events()
        self.plot_widget.canvas.draw()
        written_tuple = self.model_notes()[0]
        box = self.plot_widget.text_note_box_extent(0)
        start_tuple = ((float(box.x0) + float(box.x1)) / 2.0,
                       (float(box.y0) + float(box.y1)) / 2.0)
        end_tuple = (start_tuple[0] + 80.0, start_tuple[1] - 40.0)
        for name_str, display_tuple, button in (
                ("button_press_event", start_tuple, MouseButton.LEFT),
                ("motion_notify_event", end_tuple, None),
                ("button_release_event", end_tuple, MouseButton.LEFT)):
            self.plot_widget.canvas.callbacks.process(name_str, MouseEvent(
                name_str, self.plot_widget.canvas, display_tuple[0],
                display_tuple[1], button=button))
        self.process_events()
        moved_tuple = self.model_notes()[0]
        self.assertEqual(moved_tuple[0], "note")
        self.assertGreater(moved_tuple[1], written_tuple[1])
        self.assertLess(moved_tuple[2], written_tuple[2])
        # Edit through the menu.
        self.plot_widget.canvas.draw()
        box = self.plot_widget.text_note_box_extent(0)
        center_point = self.plot_widget.display_to_widget_point(
            (float(box.x0) + float(box.x1)) / 2.0,
            (float(box.y0) + float(box.y1)) / 2.0)

        def choose(text_str: str):
            """Return a fake execute_menu that chooses an action.

            Inputs:
                text_str: the action text.
            Outputs: the function.
            """
            def fake_execute_menu(menu, global_point):
                """Choose the action named text_str.

                Inputs:
                    menu: the QMenu.
                    global_point: unused.
                Outputs: the QAction or None.
                """
                for action in menu.actions():
                    if action.text() == text_str:
                        return action
                return None
            return fake_execute_menu

        self.plot_widget.execute_menu = choose("Edit")
        self.plot_widget.show_context_menu(center_point)
        self.process_events()
        editor = self.plot_widget.text_note_editor
        QTest.keyClicks(editor, "edited")
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.process_events()
        self.assertEqual(self.model_notes()[0][0], "edited")
        self.plot_widget.execute_menu = choose("Delete")
        self.plot_widget.show_context_menu(center_point)
        self.process_events()
        self.assertEqual(self.model_notes(), [])
        for expected_str in ("edited", "note"):
            self.main_window.run_undo()
            self.process_events()
            self.assertEqual(self.model_notes()[0][0], expected_str)
        self.main_window.run_undo()
        self.process_events()
        self.assertEqual(self.model_notes()[0], written_tuple)

    @covers("LLFR-00340", "LLFR-00049", "LLFR-00744")
    def test_notes_only_on_their_plot_and_removed_with_it(self) -> None:
        """A note shows only on its plot and goes with it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.main_window.signal_double_click_handler("Time")
        self.process_events()
        self.open_field()
        QTest.keyClicks(self.plot_widget.text_note_editor, "first plot")
        QTest.keyClick(self.plot_widget.text_note_editor, Qt.Key.Key_Return)
        self.process_events()
        widget_list = list(
            self.main_window.plot_panel.plot_widget_dict.values())
        self.assertEqual([widget.text_note_count()
                          for widget in widget_list], [1, 0])
        self.plot_controller.on_plot_delete(widget_list[0].plot_id_i)
        self.process_events()
        widget_list = list(
            self.main_window.plot_panel.plot_widget_dict.values())
        self.assertEqual([widget.text_note_count()
                          for widget in widget_list], [0])
        self.assertEqual(
            [plot.text_note_list for tab in
             self.plot_controller.workspace.tab_list
             for plot in tab.plot_list], [[]])

    @covers("LLFR-00333", "LLFR-00334", "LLFR-00079", "LLFR-00733")
    def test_tool_buttons_clicked_with_the_mouse_keep_the_field(
            self) -> None:
        """Real mouse clicks on the Text button and on other plot tool
        buttons while typing keep the field open, with its text and the
        focus; Enter then writes the note.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.open_field()
        editor = self.plot_widget.text_note_editor
        QTest.keyClicks(editor, "typed")
        tool_button_dict = self.main_window.top_panel.plot_tool_button_dict
        for tool_str, expected_tool_str in (
                (TEXT_TOOL_STR, NO_TOOL_STR),
                (ZOOM_TOOL_STR, ZOOM_TOOL_STR),
                (MARKER_TOOL_STR, MARKER_TOOL_STR),
                (TEXT_TOOL_STR, TEXT_TOOL_STR)):
            with self.subTest(button=tool_str):
                QTest.mouseClick(tool_button_dict[tool_str],
                                 Qt.MouseButton.LeftButton)
                self.process_events()
                self.assertEqual(self.plot_controller.plot_tool_str,
                                 expected_tool_str)
                self.assertTrue(editor.isVisible())
                self.assertIs(self.application.focusWidget(), editor)
                self.assertEqual(editor.text(), "typed")
                self.assertEqual(self.model_notes(), [])
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.process_events()
        self.assertEqual([note[0] for note in self.model_notes()],
                         ["typed"])

    @covers("LLFR-00333")
    def test_top_panel_buttons_never_take_the_focus(self) -> None:
        """Every top panel button has no keyboard focus policy.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from view.toggle_button import ToggleButton
        button_list = self.main_window.top_panel.findChildren(ToggleButton)
        self.assertGreaterEqual(len(button_list), 16)
        for button in button_list:
            self.assertEqual(button.focusPolicy(), Qt.FocusPolicy.NoFocus)

    @covers("LLFR-00334")
    def test_press_on_widgets_without_focus_confirms(self) -> None:
        """A press on the top panel background, on a disabled button or
        on the splitter handle confirms the field.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtTest import QTest
        top_panel = self.main_window.top_panel
        # The rightmost place of the panel that holds no button.
        background_point = next(
            QPoint(x_i, top_panel.height() // 2)
            for x_i in range(top_panel.width() - 2, 0, -1)
            if top_panel.childAt(QPoint(x_i, top_panel.height() // 2))
            is None)
        redo_button = top_panel.redo_button
        self.assertFalse(redo_button.isEnabled())
        splitter_handle = self.main_window.lower_splitter.handle(1)
        for index_i, (widget, point) in enumerate((
                (top_panel, background_point),
                (redo_button, redo_button.rect().center()),
                (splitter_handle, splitter_handle.rect().center()))):
            with self.subTest(widget=type(widget).__name__):
                # Each note at its own place, so no click lands on one.
                self.open_field(0.5 + 1.2 * index_i)
                editor = self.plot_widget.text_note_editor
                QTest.keyClicks(editor, f"note {index_i}")
                QTest.mousePress(widget, Qt.MouseButton.LeftButton,
                                 Qt.KeyboardModifier.NoModifier, point)
                QTest.mouseRelease(widget, Qt.MouseButton.LeftButton,
                                   Qt.KeyboardModifier.NoModifier, point)
                self.process_events()
                self.assertFalse(editor.isVisible())
                self.assertEqual(self.model_notes()[-1][0],
                                 f"note {index_i}")
                self.main_window.top_panel.plot_tool_button_dict[
                    TEXT_TOOL_STR].click()
                self.process_events()
        self.assertEqual(len(self.model_notes()), 3)

    @covers("LLFR-00342", "LLFR-00138")
    def test_undo_while_editing_changes_no_other_note(self) -> None:
        """An undo while the Edit field is open closes it; Enter then
        changes no note.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        for text_str, time_s in (("A", 1.0), ("B", 3.0)):
            self.plot_controller.on_text_note_create(
                self.plot_widget.plot_id_i, text_str, time_s, 4.0)
        self.plot_controller.on_text_note_delete(
            self.plot_widget.plot_id_i, 0)
        self.process_events()
        self.plot_widget.canvas.draw()
        self.plot_widget.edit_text_note_at(0)
        editor = self.plot_widget.text_note_editor
        self.assertEqual(editor.text(), "B")
        QTest.keyClicks(editor, "changed")
        self.main_window.run_undo()
        self.process_events()
        self.assertEqual([note[0] for note in self.model_notes()],
                         ["A", "B"])
        self.assertFalse(editor.isVisible())
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.process_events()
        self.assertEqual([note[0] for note in self.model_notes()],
                         ["A", "B"])

    @covers("LLFR-00334", "LLFR-00333", "LLFR-00733")
    def test_tool_switched_off_with_its_button_while_typing(self) -> None:
        """Clicking the Text button off keeps the field; Enter writes.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.open_field()
        editor = self.plot_widget.text_note_editor
        QTest.keyClicks(editor, "late")
        QTest.mouseClick(
            self.main_window.top_panel.plot_tool_button_dict[TEXT_TOOL_STR],
            Qt.MouseButton.LeftButton)
        self.process_events()
        self.assertEqual(self.plot_controller.plot_tool_str, NO_TOOL_STR)
        self.assertTrue(editor.isVisible())
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.process_events()
        self.assertEqual([note[0] for note in self.model_notes()],
                         ["late"])


if __name__ == "__main__":
    unittest.main()
