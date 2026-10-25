"""Tests for the main controller with a fake view (no Qt needed)."""

import unittest

from tests.support import covers

from controller.main_controller import MainController


class FakeMainWindow:
    """Stand-in for MainWindow that records whether it was shown."""

    def __init__(self) -> None:
        """Start as not shown.

        Inputs: none.
        Outputs: none.
        """
        self.shown_b = False

    def show(self) -> None:
        """Record that the window was shown.

        Inputs: none.
        Outputs: none.
        """
        self.shown_b = True


class MainControllerStartTest(unittest.TestCase):
    """Check that starting the controller shows the window."""

    @covers("LLFR-00058")
    def test_start_shows_main_window(self) -> None:
        """start() shows the main window with its panels.

        Inputs: none.
        Outputs: none.
        """
        fake_window = FakeMainWindow()
        MainController(fake_window).start()
        self.assertTrue(fake_window.shown_b)


if __name__ == "__main__":
    unittest.main()
