"""Tests for the highlight of the border between the panels (issue #105).

Covers LLFR-00280 (a blue line, 2 pixels wide, over the full height of
the two panels, shown while the pointer is over the border and while it
is dragged, hidden otherwise) and LLFR-00281 (the horizontal resize
pointer). A real MainWindow is shown offscreen; the pointer is simulated
with enter, leave and mouse events sent to the splitter handle.
"""

import unittest

from tests.support import covers, requires_qt
from tests.view.test_layout import LayoutTestCase

from view import theme


@requires_qt
class ResizeBorderTest(LayoutTestCase):
    """LLFR-00280, LLFR-00281: the border shows when it can be used."""

    def setUp(self) -> None:
        """Create and show the window and keep its splitter handle.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.show_window(self.main_window)
        self.splitter = self.main_window.lower_splitter
        self.handle = self.splitter.handle(1)

    def send_enter(self) -> None:
        """Send the handle the event of the pointer coming over it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPointF
        from PyQt6.QtGui import QEnterEvent
        local_point = QPointF(self.handle.width() / 2.0,
                              self.handle.height() / 2.0)
        global_point = QPointF(self.handle.mapToGlobal(
            local_point.toPoint()))
        self.application.sendEvent(
            self.handle, QEnterEvent(local_point, local_point, global_point))
        self.process_events()

    def send_leave(self) -> None:
        """Send the handle the event of the pointer leaving it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent
        self.application.sendEvent(self.handle, QEvent(QEvent.Type.Leave))
        self.process_events()

    def send_mouse(self, event_type, x_i: int, button_name_str: str,
                   buttons_name_str: str) -> None:
        """Send a mouse event to the handle at a horizontal position.

        Inputs:
            event_type: a QEvent.Type of a mouse event.
            x_i: horizontal position in handle coordinates, in pixels;
                the vertical position is the middle of the handle.
            button_name_str: name of the Qt.MouseButton that changed.
            buttons_name_str: name of the Qt.MouseButton held after it.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        local_point = QPoint(x_i, self.handle.height() // 2)
        self.application.sendEvent(self.handle, QMouseEvent(
            event_type, QPointF(local_point),
            QPointF(self.handle.mapToGlobal(local_point)),
            getattr(Qt.MouseButton, button_name_str),
            getattr(Qt.MouseButton, buttons_name_str),
            Qt.KeyboardModifier.NoModifier))
        self.process_events()

    def blue_column_list(self, y_i: int) -> list:
        """Return the pixel columns of the handle drawn in the line color.

        Inputs:
            y_i: the pixel row to look at, in handle coordinates.
        Outputs: a list of int, the columns whose pixel at row y_i has
            the color theme.RESIZE_BORDER_COLOR_STR.
        """
        image = self.handle.grab().toImage()
        ratio_f = image.width() / max(1, self.handle.width())
        line_color_str = theme.RESIZE_BORDER_COLOR_STR.lower()
        column_list = []
        for x_i in range(self.handle.width()):
            color_str = image.pixelColor(int(x_i * ratio_f),
                                         int(y_i * ratio_f)).name()
            if color_str == line_color_str:
                column_list.append(x_i)
        return column_list

    def assert_line_shown(self) -> None:
        """Check that a 2 pixel blue line covers the whole handle height.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(self.handle.highlight_shown())
        first_i, last_i = self.handle.highlight_column_tuple()
        self.assertEqual(last_i - first_i + 1, 2)
        height_i = self.handle.height()
        for y_i in (0, height_i // 4, height_i // 2, height_i - 1):
            with self.subTest(y_i=y_i):
                self.assertEqual(self.blue_column_list(y_i),
                                 [first_i, first_i + 1])

    def assert_line_hidden(self) -> None:
        """Check that no blue pixel is drawn on the handle.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(self.handle.highlight_shown())
        for y_i in (0, self.handle.height() // 2, self.handle.height() - 1):
            with self.subTest(y_i=y_i):
                self.assertEqual(self.blue_column_list(y_i), [])

    @covers("LLFR-00280")
    def test_handle_spans_the_two_panels(self) -> None:
        """The handle, and so the line, is as tall as the two panels.

        Inputs: none.
        Outputs: none.
        """
        from view.panel_splitter import PanelSplitterHandle
        self.assertIsInstance(self.handle, PanelSplitterHandle)
        plot_panel = self.main_window.plot_panel
        signal_list_panel = self.main_window.signal_list_panel
        self.assertEqual(self.handle.height(), plot_panel.height())
        self.assertEqual(self.handle.height(), signal_list_panel.height())
        self.assertEqual(self.handle.y(), plot_panel.y())
        self.assertEqual(self.handle.y(), signal_list_panel.y())
        # The handle lies exactly between the two panels.
        self.assertEqual(self.handle.x(),
                         plot_panel.x() + plot_panel.width())
        self.assertEqual(self.handle.x() + self.handle.width(),
                         signal_list_panel.x())

    @covers("LLFR-00280")
    def test_line_hidden_at_start(self) -> None:
        """Before the pointer comes over the border, nothing is drawn.

        Inputs: none.
        Outputs: none.
        """
        self.assert_line_hidden()

    @covers("LLFR-00280")
    def test_line_shown_on_hover_and_hidden_on_leave(self) -> None:
        """Hovering shows the blue line; leaving hides it at once.

        Inputs: none.
        Outputs: none.
        """
        self.send_enter()
        self.assert_line_shown()
        self.send_leave()
        self.assert_line_hidden()
        # Again, to check that the state does not stick.
        self.send_enter()
        self.assert_line_shown()
        self.send_leave()
        self.assert_line_hidden()

    @covers("LLFR-00280", "LLFR-00073")
    def test_line_shown_during_drag(self) -> None:
        """The line stays during a drag, even when the pointer leaves.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent
        plot_width_i = self.main_window.plot_panel.width()
        middle_i = self.handle.width() // 2
        self.send_enter()
        self.send_mouse(QEvent.Type.MouseButtonPress, middle_i,
                        "LeftButton", "LeftButton")
        self.assert_line_shown()
        # The pointer moves far from the border while it is dragged.
        self.send_leave()
        self.assert_line_shown()
        self.send_mouse(QEvent.Type.MouseMove, middle_i - 120,
                        "NoButton", "LeftButton")
        self.assert_line_shown()
        # The drag moved the border (LLFR-00073).
        self.assertLess(self.main_window.plot_panel.width(), plot_width_i)
        # Released away from the border: the line is hidden.
        self.send_mouse(QEvent.Type.MouseButtonRelease,
                        -self.handle.width() * 4, "LeftButton", "NoButton")
        self.assert_line_hidden()

    @covers("LLFR-00280")
    def test_release_over_the_border_keeps_the_line(self) -> None:
        """Released over the border, the line stays until the pointer leaves.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent
        middle_i = self.handle.width() // 2
        self.send_enter()
        self.send_mouse(QEvent.Type.MouseButtonPress, middle_i,
                        "LeftButton", "LeftButton")
        self.send_mouse(QEvent.Type.MouseButtonRelease, middle_i,
                        "LeftButton", "NoButton")
        self.assert_line_shown()
        self.send_leave()
        self.assert_line_hidden()

    @covers("LLFR-00280")
    def test_line_drawn_in_the_middle_of_the_border(self) -> None:
        """The 2 pixel line is centered on the handle.

        Inputs: none.
        Outputs: none.
        """
        first_i, last_i = self.handle.highlight_column_tuple()
        self.assertEqual(first_i, (self.handle.width() - 2) // 2)
        self.assertEqual(self.handle.width() - 1 - last_i, first_i
                         + (self.handle.width() % 2))

    @covers("LLFR-00281")
    def test_resize_pointer_over_the_border_and_during_drag(self) -> None:
        """The handle shows the horizontal resize pointer, also in a drag.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, Qt
        split_cursor = Qt.CursorShape.SplitHCursor
        self.assertEqual(self.handle.cursor().shape(), split_cursor)
        self.send_enter()
        self.assertEqual(self.handle.cursor().shape(), split_cursor)
        middle_i = self.handle.width() // 2
        self.send_mouse(QEvent.Type.MouseButtonPress, middle_i,
                        "LeftButton", "LeftButton")
        self.send_mouse(QEvent.Type.MouseMove, middle_i + 60,
                        "NoButton", "LeftButton")
        # The handle grabs the mouse during the drag, so its pointer is
        # the one shown wherever the pointer goes.
        self.assertEqual(self.handle.cursor().shape(), split_cursor)
        self.send_mouse(QEvent.Type.MouseButtonRelease, middle_i + 60,
                        "LeftButton", "NoButton")
        self.assertEqual(self.handle.cursor().shape(), split_cursor)
        # The panels themselves keep the normal pointer.
        self.assertNotEqual(
            self.main_window.signal_list_panel.cursor().shape(),
            split_cursor)


if __name__ == "__main__":
    unittest.main()
