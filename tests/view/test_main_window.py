"""Tests for the main window layout (HLFR-00001)."""

import unittest

from tests.support import covers, get_qt_application, requires_qt


@requires_qt
class MainWindowLayoutTest(unittest.TestCase):
    """Check that the window has the three panels in the right places."""

    def setUp(self) -> None:
        """Create and show a main window.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.main_window import MainWindow
        self.main_window = MainWindow()
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

    def panel_position_tuple(self, panel) -> tuple:
        """Return a panel's top-left corner in window coordinates.

        Inputs:
            panel: a widget inside the main window.
        Outputs: a tuple (x, y) in pixels.
        """
        from PyQt6.QtCore import QPoint
        corner = panel.mapTo(self.main_window, QPoint(0, 0))
        return (corner.x(), corner.y())

    @covers("LLFR-00058")
    def test_window_has_three_visible_panels(self) -> None:
        """The top, plot and signal list panels exist and are visible.

        Inputs: none.
        Outputs: none.
        """
        for panel in (self.main_window.top_panel,
                      self.main_window.plot_panel,
                      self.main_window.signal_list_panel):
            self.assertTrue(panel.isVisible())

    @covers("LLFR-00058")
    def test_top_panel_is_above_other_panels(self) -> None:
        """The top panel ends above where the other two panels start.

        Inputs: none.
        Outputs: none.
        """
        top_x_i, top_y_i = self.panel_position_tuple(
            self.main_window.top_panel)
        top_bottom_i = top_y_i + self.main_window.top_panel.height()
        for panel in (self.main_window.plot_panel,
                      self.main_window.signal_list_panel):
            panel_x_i, panel_y_i = self.panel_position_tuple(panel)
            self.assertLessEqual(top_bottom_i, panel_y_i)

    @covers("LLFR-00058")
    def test_signal_list_is_right_of_plot_panel(self) -> None:
        """The signal list panel starts right of where the plot panel ends.

        Inputs: none.
        Outputs: none.
        """
        plot_x_i, plot_y_i = self.panel_position_tuple(
            self.main_window.plot_panel)
        list_x_i, list_y_i = self.panel_position_tuple(
            self.main_window.signal_list_panel)
        plot_right_i = plot_x_i + self.main_window.plot_panel.width()
        self.assertLessEqual(plot_right_i, list_x_i)


if __name__ == "__main__":
    unittest.main()
