"""Entry point of plot_tool.

Run with ``python src/main.py``. It shows the splash screen, builds the
view and the controller (COR-00003) and starts the Qt event loop.

The startup order matters (issue #75). Importing matplotlib, numpy,
pandas and the plot views takes most of the startup time, and many
seconds on the first launch of the standalone app, when matplotlib
builds its font list. So this module imports at its top only Qt and the
light view modules needed for the splash screen, shows the splash
screen (LLFR-00184), and only then imports the rest of the app, inside
``build_main_window``.

Setting the environment variable ``PLOT_TOOL_STARTUP_PROBE=1`` makes
the app print how long it took to show its splash screen and its
window, and quit (see ``view.startup_probe``). It is used to check the
standalone build.
"""

import time

# LLFR-00184, LLFR-00188: taken before any other import, so the startup
# probe also counts the time spent importing Qt and matplotlib.
MAIN_START_S = time.perf_counter()

import sys  # noqa: E402
import traceback  # noqa: E402

from view.matplotlib_cache import (  # noqa: E402
    use_persistent_matplotlib_folder)

# LLFR-00189: before matplotlib is imported (by build_main_window), so
# a built app keeps matplotlib's font list between launches (issue #67).
use_persistent_matplotlib_folder()

# LLFR-00184: only Qt and light modules before the splash screen; none
# of them imports matplotlib, numpy, pandas or the plot views.
from PyQt6 import sip  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from view import icons, message_boxes, splash_screen  # noqa: E402
from view import startup_probe, theme  # noqa: E402
from view.error_hook import format_error_message  # noqa: E402

# LLFR-00187: exit code of a launch that could not start.
STARTUP_ERROR_EXIT_CODE_I = 1
# LLFR-00184: (phase name, time.perf_counter()) of the startup steps
# before the splash screen, reported by the startup probe.
STARTUP_PHASE_LIST = [("imports", time.perf_counter())]


def build_main_window(application: QApplication) -> tuple:
    """Import the rest of the app and build the main window, not shown.

    Inputs:
        application: the QApplication (not used here; kept so that a
            replacement can be given to start_main_window in tests).
    Outputs: a tuple (main window, main controller). The controller
        must be kept for as long as the app runs. The window is shown
        by show_main_window, when the splash screen closes.
    """
    # LLFR-00184: the slow imports happen here, after the splash screen
    # is shown.
    from controller.main_controller import MainController
    from view.error_hook import install_error_hook
    from view.main_window import MainWindow
    # LLFR-00058: create the main window with its three panels.
    main_window = MainWindow()
    # LLFR-00071: an unexpected error shows a box instead of aborting.
    install_error_hook(main_window)
    controller = MainController(main_window)
    return main_window, controller


def show_main_window(window_tuple: tuple) -> None:
    """Show the main window built by build_main_window.

    Inputs:
        window_tuple: the tuple (main window, controller).
    Outputs: none.
    """
    # LLFR-00058: the controller shows the window with its panels.
    window_tuple[1].start()


def start_main_window(application: QApplication, splash,
                      build_function=build_main_window,
                      show_error=message_boxes.show_unexpected_error,
                      show_function=show_main_window):
    """Build the main window behind the splash screen, then swap them.

    Inputs:
        application: the QApplication.
        splash: the shown SplashScreen.
        build_function: builds the window without showing it, returning
            a tuple (main window, controller); build_main_window by
            default.
        show_error: shows the error box, taking (parent, message_str);
            message_boxes.show_unexpected_error by default.
        show_function: shows the window, taking the tuple of
            build_function; show_main_window by default.
    Outputs: the tuple of build_function, or None when it raised. Then
        the splash screen was closed first and the error box shown.
    """
    try:
        window_tuple = build_function(application)
    except Exception as error:
        # LLFR-00187: the app can't start; report it on stderr, close
        # the splash screen, then show the error box (HLFR-00002).
        traceback.print_exc()
        splash.close()
        show_error(None, format_error_message(type(error), error))
        return None
    # LLFR-00186: the window is shown and the splash screen closed in
    # the same step, so the splash is never above the visible window.
    splash.finish(window_tuple[0], lambda: show_function(window_tuple))
    return window_tuple


def main() -> int:
    """Start the application and run it until the window is closed.

    Inputs: none (command-line arguments are passed to Qt).
    Outputs: the exit code returned by the Qt event loop, or
        STARTUP_ERROR_EXIT_CODE_I when the app could not start.
    """
    # LLFR-00184: the application, its icon and its style first, then
    # the splash screen, before anything slow is imported.
    application = QApplication(sys.argv)
    STARTUP_PHASE_LIST.append(("application", time.perf_counter()))
    application.setWindowIcon(icons.app_icon())
    theme.apply_application_theme(application)
    STARTUP_PHASE_LIST.append(("icon_and_style", time.perf_counter()))
    splash = splash_screen.show_splash(
        application, phase_list=STARTUP_PHASE_LIST)
    # LLFR-00184: only with PLOT_TOOL_STARTUP_PROBE=1, report when the
    # splash screen was shown (build check).
    startup_probe.report_splash_shown(splash, MAIN_START_S,
                                      phase_list=STARTUP_PHASE_LIST)
    window_tuple = start_main_window(application, splash, build_main_window,
                                     message_boxes.show_unexpected_error)
    if window_tuple is None:
        # LLFR-00187: the error box was shown; end with an error code.
        sip.delete(splash)
        return STARTUP_ERROR_EXIT_CODE_I
    main_window = window_tuple[0]
    # LLFR-00406: once the window is shown, the file dialogs are built
    # in small steps, without showing any, so that even the first click
    # shows its dialog quickly (issue #165).
    main_window.schedule_file_dialog_preparation()
    from model.file_loader import load_signal_file
    # LLFR-00188: only with PLOT_TOOL_STARTUP_PROBE=1, report when the
    # window is shown and quit (build check, issue #67).
    startup_probe.install_startup_probe(application, main_window,
                                        MAIN_START_S, load_signal_file,
                                        splash=splash)
    exit_code_i = application.exec()
    # LLFR-00058: close down in a fixed order: the window with its
    # panels and plots and the splash screen first, while the
    # application still exists, and the application last (when main
    # returns). Left to the interpreter exit, Qt objects were destroyed
    # in any order, which sometimes crashed the app on macOS when it
    # quit (issue #67).
    sys.excepthook = sys.__excepthook__
    sip.delete(main_window)
    sip.delete(splash)
    return exit_code_i


if __name__ == "__main__":
    sys.exit(main())
