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
        self.open_file_handler = None

    def set_open_file_handler(self, handler) -> None:
        """Record the handler of the Open file button.

        Inputs:
            handler: the function called when Open file is clicked.
        Outputs: none.
        """
        self.open_file_handler = handler

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

    @covers("LLFR-00005")
    def test_open_file_button_runs_file_controller(self) -> None:
        """The Open file handler is the file controller's flow.

        Inputs: none.
        Outputs: none.
        """
        fake_window = FakeMainWindow()
        controller = MainController(fake_window)
        self.assertEqual(fake_window.open_file_handler,
                         controller.file_controller.open_file_requested)
        self.assertIs(controller.file_controller.view, fake_window)


if __name__ == "__main__":
    unittest.main()
