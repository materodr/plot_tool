"""Tests that the search box is level with the plots (HLFR-00095).

Covers LLFR-00424: the bottom edge of the search box is at the height of
the bottom edge of the lowest plot of the current tab, including its
x-axis numbers and label, at any window size; and LLFR-00652: with no
plot in the current tab, it is where the bottom of a plot would be. The
checks use a real MainWindow with the real controllers, shown at several
sizes, with plots added and deleted, tabs switched and the panel border
moved. No modal dialog or menu is ever opened.
"""

import unittest

import numpy as np

from tests.support import covers, get_qt_application, requires_qt

# Allowed difference, in pixels, between the two bottom edges.
EDGE_TOLERANCE_I = 1
# Window sizes (width, height) of the checks.
WINDOW_SIZE_LIST = [(1200, 800), (900, 600), (1500, 950), (700, 520)]
# Rounds of Qt event processing allowed for the layouts to settle.
SETTLE_ROUNDS_I = 30


def bottom_edge_y(widget) -> int:
    """Return the screen y of the line just below a widget.

    Inputs:
        widget: a QWidget.
    Outputs: the global y of its top plus its height, in pixels.
    """
    from PyQt6.QtCore import QPoint
    return int(widget.mapToGlobal(QPoint(0, widget.height())).y())


@requires_qt
class SearchBoxAlignmentTest(unittest.TestCase):
    """The search box ends where the lowest plot of the tab ends."""

    def setUp(self) -> None:
        """Create and show a window with a file of three signals.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from controller.main_controller import MainController
        from model.signal_file import SignalFile
        from view.main_window import MainWindow
        self.main_window = MainWindow()
        self.main_window.resize(*WINDOW_SIZE_LIST[0])
        self.controller = MainController(self.main_window)
        time_array = np.linspace(0.0, 4.0, 41)
        self.plot_controller = self.controller.plot_controller
        self.plot_controller.on_file_opened(SignalFile("memory.csv", {
            "Time": time_array, "speed": time_array * 2.0,
            "force": np.sin(time_array)}), False)
        self.main_window.show()
        self.settle()

    def tearDown(self) -> None:
        """Close the window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def settle(self) -> None:
        """Let Qt run the pending layouts, resizes and timers.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(SETTLE_ROUNDS_I):
            self.application.processEvents()

    def current_plot_widgets(self) -> list:
        """Return the plot widgets of the current tab, top to bottom.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        plot_panel = self.main_window.plot_panel
        return [plot_panel.plot_view(plot_id_i) for plot_id_i
                in plot_panel.plot_id_list(plot_panel.current_tab_id())]

    def search_box_bottom_y(self) -> int:
        """Return the screen y just below the search box.

        Inputs: none.
        Outputs: the global y, in pixels.
        """
        return bottom_edge_y(self.main_window.signal_list_panel.search_box)

    def assert_level_with_lowest_plot(self) -> None:
        """Check LLFR-00424 for the current tab, which holds plots.

        Inputs: none.
        Outputs: none.
        """
        plot_widget_list = self.current_plot_widgets()
        self.assertTrue(plot_widget_list)
        lowest_widget = plot_widget_list[-1]
        lowest_bottom_i = max(bottom_edge_y(plot_widget)
                              for plot_widget in plot_widget_list)
        self.assertEqual(bottom_edge_y(lowest_widget), lowest_bottom_i)
        self.assertLessEqual(
            abs(self.search_box_bottom_y() - lowest_bottom_i),
            EDGE_TOLERANCE_I)
        # The x-axis numbers and label are drawn inside the plot widget,
        # so its bottom edge is the bottom of the plot including them.
        lowest_widget.canvas.draw()
        renderer = lowest_widget.canvas.get_renderer()
        label_box = lowest_widget.axes.xaxis.label.get_window_extent(
            renderer)
        tick_box = lowest_widget.axes.xaxis.get_tightbbox(renderer)
        self.assertGreaterEqual(label_box.y0, 0.0)
        self.assertGreaterEqual(tick_box.y0, 0.0)
        self.assertGreater(label_box.height, 0.0)

    def assert_level_with_empty_page(self) -> None:
        """Check LLFR-00652 for the current tab, which holds no plot.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.current_plot_widgets(), [])
        page = self.main_window.plot_panel.tab_widget.currentWidget()
        self.assertLessEqual(
            abs(self.search_box_bottom_y() - bottom_edge_y(page)),
            EDGE_TOLERANCE_I)

    @covers("LLFR-00424", "HLFR-00095")
    def test_level_with_the_lowest_plot_at_any_size(self) -> None:
        """With one, then three plots, at several window sizes.

        Inputs: none.
        Outputs: none.
        """
        self.plot_controller.on_signal_double_clicked("speed")
        self.settle()
        self.assert_level_with_lowest_plot()
        self.plot_controller.on_signal_double_clicked("force")
        self.plot_controller.on_signal_double_clicked("Time")
        self.settle()
        self.assertEqual(len(self.current_plot_widgets()), 3)
        for width_i, height_i in WINDOW_SIZE_LIST:
            with self.subTest(width_i=width_i, height_i=height_i):
                self.main_window.resize(width_i, height_i)
                self.settle()
                self.assert_level_with_lowest_plot()

    @covers("LLFR-00424", "LLFR-00652", "HLFR-00095")
    def test_level_after_plots_are_deleted(self) -> None:
        """Deleting the lowest plot, then the last one, keeps it level.

        Inputs: none.
        Outputs: none.
        """
        self.plot_controller.on_signal_double_clicked("speed")
        self.plot_controller.on_signal_double_clicked("force")
        self.settle()
        self.assert_level_with_lowest_plot()
        for plot_widget in reversed(self.current_plot_widgets()):
            self.plot_controller.on_plot_delete(plot_widget.plot_id_i)
            self.settle()
            if self.current_plot_widgets():
                self.assert_level_with_lowest_plot()
        self.assert_level_with_empty_page()

    @covers("LLFR-00652", "HLFR-00095")
    def test_level_with_no_plot_at_any_size(self) -> None:
        """An empty tab: the search box ends at the bottom of the page.

        Inputs: none.
        Outputs: none.
        """
        for width_i, height_i in WINDOW_SIZE_LIST:
            with self.subTest(width_i=width_i, height_i=height_i):
                self.main_window.resize(width_i, height_i)
                self.settle()
                self.assert_level_with_empty_page()

    @covers("LLFR-00424", "LLFR-00652", "HLFR-00095")
    def test_level_when_the_tab_changes(self) -> None:
        """A tab with plots and an empty tab each give a level edge.

        Inputs: none.
        Outputs: none.
        """
        self.plot_controller.on_signal_double_clicked("speed")
        first_tab_id_i = self.main_window.plot_panel.current_tab_id()
        self.plot_controller.on_add_tab()
        self.settle()
        second_tab_id_i = self.main_window.plot_panel.current_tab_id()
        self.assertNotEqual(first_tab_id_i, second_tab_id_i)
        self.assert_level_with_empty_page()
        self.main_window.plot_panel.set_current_tab(first_tab_id_i)
        self.settle()
        self.assert_level_with_lowest_plot()
        self.main_window.plot_panel.set_current_tab(second_tab_id_i)
        self.settle()
        self.assert_level_with_empty_page()

    @covers("LLFR-00424", "HLFR-00095")
    def test_level_after_the_panel_border_moves(self) -> None:
        """Other panel widths keep the edges level.

        Inputs: none.
        Outputs: none.
        """
        self.plot_controller.on_signal_double_clicked("speed")
        self.plot_controller.on_signal_double_clicked("force")
        self.settle()
        splitter = self.main_window.lower_splitter
        total_width_i = sum(splitter.sizes())
        for list_width_i in (180, 400):
            with self.subTest(list_width_i=list_width_i):
                splitter.setSizes([total_width_i - list_width_i,
                                   list_width_i])
                self.settle()
                self.assert_level_with_lowest_plot()

    @covers("LLFR-00560", "LLFR-00424")
    def test_loading_text_keeps_the_search_box_level(self) -> None:
        """Showing "Loading..." moves neither the search box nor the
        alignment, and the status line stays directly above the box.

        Inputs: none.
        Outputs: none.
        """
        self.plot_controller.on_signal_double_clicked("speed")
        self.settle()
        panel = self.main_window.signal_list_panel
        before_bottom_i = self.search_box_bottom_y()
        panel.show_status_text("Loading...")
        self.settle()
        self.assertEqual(self.search_box_bottom_y(), before_bottom_i)
        self.assert_level_with_lowest_plot()
        status_bottom_i = bottom_edge_y(panel.status_label)
        search_top_i = (bottom_edge_y(panel.search_box)
                        - panel.search_box.height())
        self.assertLessEqual(status_bottom_i, search_top_i)
        panel.show_status_text("")
        self.settle()
        self.assertEqual(self.search_box_bottom_y(), before_bottom_i)


if __name__ == "__main__":
    unittest.main()
