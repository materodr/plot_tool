"""Entry point of plot_tool.

Run with ``python src/main.py``. It builds the view and the controller
(COR-00003) and starts the Qt event loop.

Setting the environment variable ``PLOT_TOOL_STARTUP_PROBE=1`` makes
the app print how long it took to show its window, and quit (see
``view.startup_probe``). It is used to check the standalone build.
"""

import time

# LLFR-00058: taken before the heavy imports, so the startup probe also
# counts the time spent importing Qt and matplotlib.
MAIN_START_S = time.perf_counter()

import sys  # noqa: E402

from view.matplotlib_cache import (  # noqa: E402
    use_persistent_matplotlib_folder)

# LLFR-00068: before matplotlib is imported (by the view below), so a
# built app keeps matplotlib's font list between launches (issue #67).
use_persistent_matplotlib_folder()

from PyQt6 import sip  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from controller.main_controller import MainController  # noqa: E402
from model.file_loader import load_signal_file  # noqa: E402
from view.error_hook import install_error_hook  # noqa: E402
from view.main_window import MainWindow  # noqa: E402
from view.startup_probe import install_startup_probe  # noqa: E402


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
    # LLFR-00058: only with PLOT_TOOL_STARTUP_PROBE=1, report when the
    # window is shown and quit (build check, issue #67).
    install_startup_probe(application, main_window, MAIN_START_S,
                          load_signal_file)
    exit_code_i = application.exec()
    # LLFR-00058: close down in a fixed order: the window with its
    # panels and plots first, while the application still exists, and
    # the application last (when main returns). Left to the interpreter
    # exit, Qt objects were destroyed in any order, which sometimes
    # crashed the app on macOS when it quit (issue #67).
    sys.excepthook = sys.__excepthook__
    sip.delete(main_window)
    return exit_code_i


if __name__ == "__main__":
    sys.exit(main())
