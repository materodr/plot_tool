"""Entry point of plot_tool.

Run with ``python src/main.py``. It builds the view and the controller
(COR-00003) and starts the Qt event loop.
"""

import sys

from PyQt6.QtWidgets import QApplication

from controller.main_controller import MainController
from view.error_hook import install_error_hook
from view.main_window import MainWindow


def main() -> int:
    """Start the application and run it until the window is closed.

    Inputs: none (command-line arguments are passed to Qt).
    Outputs: the exit code returned by the Qt event loop.
    """
    # LLFR-00058: create the main window with its three panels and show it.
    application = QApplication(sys.argv)
    main_window = MainWindow()
    # LLFR-00071: an unexpected error shows a box instead of aborting.
    install_error_hook(main_window)
    controller = MainController(main_window)
    controller.start()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
