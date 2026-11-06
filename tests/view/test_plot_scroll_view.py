"""Qt tests for the minimum plot height and the scrolled tabs (#260).

A real MainWindow and MainController are used (the setup of
test_plot_panel). They check the minimum height of a plot's drawing
area (HLFR-00165, LLFR-01394), the plots that fit or scroll in their tab
(HLFR-00166, LLFR-01395, LLFR-01396, LLFR-01401), the mouse wheel over
a plot of a scrolled tab (LLFR-01397), the exports of a scrolled tab
(LLFR-01398), the undocked windows (LLFR-01399) and the search box
beside a scrolled tab (LLFR-01400).

No test moves the shared mouse pointer: wheel events are sent to the
widgets directly.
"""

import unittest
from unittest import mock

from tests.support import covers, requires_qt
from tests.view.test_undocked_windows_view import UndockedWindowTestCase

# The 800 x 600 window the app can open at (owner answer of batch 4).
SMALL_WIDTH_I = 800
SMALL_HEIGHT_I = 600
# A window tall enough for one plot to fit without a scroll bar.
LARGE_WIDTH_I = 1400
LARGE_HEIGHT_I = 1000
# Pixels of rounding allowed between Qt and matplotlib sizes.
TOLERANCE_PX_I = 2
# The full tab of HLFR-00018 in the default 5 x 1 matrix.
FULL_TAB_PLOT_COUNT_I = 5


@requires_qt
class PlotScrollTestCase(UndockedWindowTestCase):
    """Minimum plot height and scrolled tabs."""

    def settle(self, page) -> None:
        """Draw the plots of a page until their minimum heights settle.

        Inputs:
            page: the TabPage.
        Outputs: none.
        """
        for _ in range(4):
            self.process_events()
            for plot_widget in page.plot_widget_list:
                plot_widget.canvas.draw()
            self.process_events()

    def axes_height_px_f(self, plot_widget) -> float:
        """Return the height of a plot's drawing area in widget pixels.

        Inputs:
            plot_widget: the PlotWidget.
        Outputs: the axes height in widget (logical) pixels.
        """
        return (float(plot_widget.axes.bbox.height)
                / plot_widget.pixel_ratio_f())

    def full_small_tab(self):
        """Fill the current tab with 5 plots in an 800 x 600 window.

        Inputs: none.
        Outputs: the TabPage of the current tab.
        """
        self.main_window.resize(SMALL_WIDTH_I, SMALL_HEIGHT_I)
        self.add_plots(FULL_TAB_PLOT_COUNT_I)
        page = self.current_page()
        self.settle(page)
        return page

    @covers("LLFR-01394", "HLFR-00165")
    def test_tip_box_height_follows_the_font(self) -> None:
        """The minimum height is 3 tip boxes, measured with the font.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        (plot_widget,) = self.add_plots(1)
        box_height_f = plot_widget.tip_box_height_px()
        self.assertGreater(box_height_f, 0.0)
        self.assertAlmostEqual(plot_widget.minimum_axes_height_px(),
                               3.0 * box_height_f, places=3)
        plot_widget.tip_box_height_cache_dict.clear()
        with mock.patch.object(theme, "PLOT_TIP_FONT_SIZE_F",
                               2.0 * theme.PLOT_TIP_FONT_SIZE_F):
            larger_height_f = plot_widget.tip_box_height_px()
        plot_widget.tip_box_height_cache_dict.clear()
        self.assertGreater(larger_height_f, 1.5 * box_height_f)

    @covers("LLFR-01394", "LLFR-01396", "LLFR-01401", "HLFR-00165",
            "HLFR-00166", "LLFR-00179")
    def test_full_tab_scrolls_at_800_by_600(self) -> None:
        """5 plots at 800 x 600 keep their minimum height and scroll.

        Inputs: none.
        Outputs: none.
        """
        page = self.full_small_tab()
        self.assertEqual(self.main_window.width(), SMALL_WIDTH_I)
        self.assertEqual(self.main_window.height(), SMALL_HEIGHT_I)
        self.assertEqual(len(page.plot_widget_list), FULL_TAB_PLOT_COUNT_I)
        self.assertTrue(page.scrolls_b())
        scroll_bar = page.scroll_area.verticalScrollBar()
        self.assertTrue(scroll_bar.isVisible())
        self.assertGreater(scroll_bar.maximum(), 0)
        self.assertFalse(
            page.scroll_area.horizontalScrollBar().isVisible())
        self.assertGreater(page.plot_area.height(),
                           page.scroll_area.viewport().height())
        for plot_widget in page.plot_widget_list:
            self.assertGreaterEqual(
                self.axes_height_px_f(plot_widget) + TOLERANCE_PX_I,
                plot_widget.minimum_axes_height_px())
        # LLFR-01110: the rows are still one below the other, equal.
        height_list = [plot_widget.height()
                       for plot_widget in page.plot_widget_list]
        self.assertLessEqual(max(height_list) - min(height_list),
                             TOLERANCE_PX_I)

    @covers("LLFR-01395", "LLFR-01401", "HLFR-00166")
    def test_scroll_bar_only_while_needed(self) -> None:
        """The scroll bar goes away when the plots fit again.

        Inputs: none.
        Outputs: none.
        """
        page = self.full_small_tab()
        self.assertTrue(page.scroll_area.verticalScrollBar().isVisible())
        # Deleting plots until one is left: it fits, with no scroll bar.
        for plot_id_i in self.panel.plot_id_list(
                self.panel.current_tab_id())[1:]:
            self.plot_controller.on_plot_delete(plot_id_i)
            self.process_events()
        self.settle(page)
        self.assertFalse(page.scrolls_b())
        self.assertFalse(page.scroll_area.verticalScrollBar().isVisible())
        (plot_widget,) = page.plot_widget_list
        # LLFR-01395: the one plot fills the whole plot area.
        self.assertAlmostEqual(plot_widget.height(),
                               page.scroll_area.viewport().height(),
                               delta=TOLERANCE_PX_I)

    @covers("LLFR-01395", "HLFR-00166")
    def test_plots_that_fit_share_the_height(self) -> None:
        """In a large window, 2 plots share the height, no scroll bar.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.resize(LARGE_WIDTH_I, LARGE_HEIGHT_I)
        first, second = self.add_plots(2)
        page = self.current_page()
        self.settle(page)
        self.assertFalse(page.scrolls_b())
        self.assertFalse(page.scroll_area.verticalScrollBar().isVisible())
        self.assertAlmostEqual(first.height(), second.height(),
                               delta=TOLERANCE_PX_I)
        self.assertGreaterEqual(
            first.height() + second.height() + page.page_layout.spacing()
            + TOLERANCE_PX_I, page.scroll_area.viewport().height())

    @covers("LLFR-01397", "HLFR-00166", "LLFR-00074")
    def test_wheel_over_a_plot_zooms_and_does_not_scroll(self) -> None:
        """The wheel over a plot of a scrolled tab zooms the plot.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint, QPointF, Qt
        from PyQt6.QtGui import QWheelEvent
        from PyQt6.QtWidgets import QApplication
        page = self.full_small_tab()
        scroll_bar = page.scroll_area.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum() // 2)
        self.process_events()
        scroll_value_i = scroll_bar.value()
        plot_widget = page.plot_widget_list[1]
        scroll_event_list = []
        plot_widget.canvas.mpl_connect("scroll_event",
                                       scroll_event_list.append)
        old_range_tuple = tuple(plot_widget.axes.get_xlim())
        center = QPointF(plot_widget.canvas.width() / 2.0,
                         plot_widget.canvas.height() / 2.0)
        wheel_event = QWheelEvent(
            center, QPointF(plot_widget.canvas.mapToGlobal(center)),
            QPoint(0, 0), QPoint(0, 120), Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
            False)
        QApplication.sendEvent(plot_widget.canvas, wheel_event)
        self.process_events()
        self.assertTrue(scroll_event_list)
        self.assertEqual(scroll_bar.value(), scroll_value_i)
        new_range_tuple = tuple(plot_widget.axes.get_xlim())
        self.assertLess(new_range_tuple[1] - new_range_tuple[0],
                        old_range_tuple[1] - old_range_tuple[0])

    @covers("LLFR-01398", "HLFR-00166", "HLFR-00039", "LLFR-00133")
    def test_copied_image_holds_every_plot_whole(self) -> None:
        """The copied image of a scrolled tab holds all 5 plots whole.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_export import grab_page_image, plot_image_list
        page = self.full_small_tab()
        scroll_bar = page.scroll_area.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())
        self.process_events()
        image = grab_page_image(page)
        ratio_f = max(float(image.devicePixelRatio()), 1e-6)
        # The image is as tall as all the plots, not as the visible part,
        # and as wide as the plots, without the scroll bar.
        self.assertAlmostEqual(image.height() / ratio_f,
                               page.plot_area.height(),
                               delta=TOLERANCE_PX_I)
        self.assertGreater(image.height() / ratio_f,
                           page.scroll_area.viewport().height())
        self.assertAlmostEqual(image.width() / ratio_f,
                               page.plot_area.width(),
                               delta=TOLERANCE_PX_I)
        entry_list = plot_image_list(page)
        self.assertEqual(len(entry_list), FULL_TAB_PLOT_COUNT_I)
        top_list = [canvas_rect.y() for canvas_rect, _ in entry_list]
        self.assertAlmostEqual(top_list[0], 0.0, delta=TOLERANCE_PX_I)
        self.assertEqual(top_list, sorted(top_list))
        last_rect = entry_list[-1][0]
        self.assertAlmostEqual(last_rect.y() + last_rect.height(),
                               page.plot_area.height(),
                               delta=TOLERANCE_PX_I)
        for canvas_rect, plot_image in entry_list:
            self.assertFalse(plot_image.isNull())
            self.assertGreater(canvas_rect.height(), 0.0)

    @covers("LLFR-01399", "HLFR-00165", "HLFR-00166")
    def test_undocked_window_scrolls_too(self) -> None:
        """A full tab in a small undocked window scrolls the same way.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.show()
        self.add_tab()
        tab_id_i = self.panel.current_tab_id()
        self.add_plots(FULL_TAB_PLOT_COUNT_I)
        window = self.undock(tab_id_i)
        self.assertIsNotNone(window)
        window.resize(SMALL_WIDTH_I, SMALL_HEIGHT_I)
        page = window.page()
        self.settle(page)
        self.assertEqual(len(page.plot_widget_list), FULL_TAB_PLOT_COUNT_I)
        self.assertTrue(page.scrolls_b())
        self.assertTrue(page.scroll_area.verticalScrollBar().isVisible())
        for plot_widget in page.plot_widget_list:
            self.assertGreaterEqual(
                self.axes_height_px_f(plot_widget) + TOLERANCE_PX_I,
                plot_widget.minimum_axes_height_px())

    @covers("LLFR-01400", "HLFR-00095", "HLFR-00166")
    def test_search_box_follows_the_visible_plot_area(self) -> None:
        """Beside a scrolled tab, the search box ends where the view ends.

        Inputs: none.
        Outputs: none.
        """
        from view.search_box_alignment import bottom_edge_global_y
        page = self.full_small_tab()
        aligner = self.main_window.search_box_aligner
        self.assertIs(aligner.target_widget(), page.visible_plot_area())
        aligner.align()
        self.process_events()
        search_box = self.main_window.signal_list_panel.search_box
        self.assertAlmostEqual(
            bottom_edge_global_y(search_box),
            bottom_edge_global_y(page.visible_plot_area()),
            delta=TOLERANCE_PX_I)


if __name__ == "__main__":
    unittest.main()
