"""Startup probe: report how long the app takes to show its window.

The probe exists only to check the standalone build (issue #67). It is
off unless the environment variable ``PLOT_TOOL_STARTUP_PROBE`` is
``"1"``, so a normal launch behaves exactly as before. When it is on:

1. as soon as the main window is shown and exposed on screen, one line
   is printed to standard output::

       plot_tool startup: window_shown_epoch_s=<time.time()>
       since_main_s=<seconds since src/main.py started> exposed=<yes|no>
       pid=<process id>

   (all on one line). ``tests/user_tests/measure_startup.py`` compares
   the epoch time with the time it launched the app;
2. if ``PLOT_TOOL_PROBE_FILES`` lists files (separated by
   ``os.pathsep``), each one is opened with the app's file loader and a
   line ``plot_tool probe file: OK|FAILED <name> ...`` is printed, to
   show that the bundle holds every library the loaders need;
3. the app quits, with exit code 0, or 1 when a probe file failed.

Code traced to LLFR-00058: the probe only watches the main window with
its three panels being shown; it is a build check, not a function.
"""

import os
import sys
import time

from PyQt6.QtCore import QTimer

STARTUP_PROBE_VARIABLE_STR = "PLOT_TOOL_STARTUP_PROBE"
PROBE_FILES_VARIABLE_STR = "PLOT_TOOL_PROBE_FILES"
STARTUP_LINE_PREFIX_STR = "plot_tool startup:"
PROBE_FILE_LINE_PREFIX_STR = "plot_tool probe file:"
# LLFR-00058: how often the probe checks the window, and how long it
# waits for it to be exposed before reporting anyway.
POLL_INTERVAL_MS_I = 10
EXPOSE_TIMEOUT_S = 30.0


def startup_probe_enabled(environment_dict: dict) -> bool:
    """Tell whether the startup probe is switched on.

    Inputs:
        environment_dict: the environment variables (os.environ).
    Outputs: True only when PLOT_TOOL_STARTUP_PROBE is "1".
    """
    # LLFR-00058: off by default, so a normal launch is unchanged.
    return environment_dict.get(STARTUP_PROBE_VARIABLE_STR, "") == "1"


def window_exposed(main_window) -> bool:
    """Tell whether the main window is shown and exposed on screen.

    Inputs:
        main_window: the app's MainWindow.
    Outputs: True when the window is visible and its native window is
        exposed (drawn by the window system).
    """
    # LLFR-00058: the window with its three panels is on screen.
    if not main_window.isVisible():
        return False
    window_handle = main_window.windowHandle()
    return window_handle is not None and window_handle.isExposed()


def startup_line_str(main_start_s: float, exposed_b: bool) -> str:
    """Build the line that reports the startup time.

    Inputs:
        main_start_s: time.perf_counter() when src/main.py started.
        exposed_b: whether the window was exposed when reporting.
    Outputs: the report line, without a line break.
    """
    # LLFR-00058: when the window was shown, in two clocks.
    since_main_s = time.perf_counter() - main_start_s
    exposed_str = "yes" if exposed_b else "no"
    return (f"{STARTUP_LINE_PREFIX_STR} "
            f"window_shown_epoch_s={time.time():.3f} "
            f"since_main_s={since_main_s:.3f} exposed={exposed_str} "
            f"pid={os.getpid()}")


def probe_file_path_list(environment_dict: dict) -> list:
    """Return the files the probe must open.

    Inputs:
        environment_dict: the environment variables (os.environ).
    Outputs: the paths listed in PLOT_TOOL_PROBE_FILES, in order; an
        empty list when the variable is missing or empty.
    """
    # LLFR-00058: optional check of the file loaders of the bundle.
    paths_str = environment_dict.get(PROBE_FILES_VARIABLE_STR, "")
    return [path_str for path_str in paths_str.split(os.pathsep)
            if path_str]


def probe_file_line_list(path_list: list, load_file) -> tuple:
    """Open each probe file and describe the result.

    Inputs:
        path_list: paths of the files to open.
        load_file: the app's loader (model.file_loader.load_signal_file).
    Outputs: a tuple (list of report lines, True when every file opened).
    """
    # LLFR-00058: each loader must work inside the standalone build.
    line_list = []
    all_opened_b = True
    for path_str in path_list:
        file_name_str = os.path.basename(path_str)
        try:
            signal_file = load_file(path_str)
        except Exception as error:
            all_opened_b = False
            line_list.append(f"{PROBE_FILE_LINE_PREFIX_STR} FAILED "
                             f"{file_name_str}: {error}")
            continue
        signal_count_i = len(signal_file.signal_name_list())
        line_list.append(f"{PROBE_FILE_LINE_PREFIX_STR} OK "
                         f"{file_name_str} signals={signal_count_i}")
    return line_list, all_opened_b


def report_startup(application, main_start_s: float, exposed_b: bool,
                   load_file, environment_dict: dict,
                   output_stream=None) -> None:
    """Print the startup report and quit the app.

    Inputs:
        application: the QApplication (only its ``exit`` is used).
        main_start_s: time.perf_counter() when src/main.py started.
        exposed_b: whether the window was exposed when reporting.
        load_file: the app's file loader, for the probe files.
        environment_dict: the environment variables (os.environ).
        output_stream: where to print; standard output when None.
    Outputs: none. Ends the event loop with exit code 0, or 1 when a
        probe file could not be opened.
    """
    # LLFR-00058: report the shown window first, so that opening the
    # probe files doesn't add to the measured time.
    stream = output_stream if output_stream is not None else sys.stdout
    print(startup_line_str(main_start_s, exposed_b), file=stream)
    line_list, all_opened_b = probe_file_line_list(
        probe_file_path_list(environment_dict), load_file)
    for line_str in line_list:
        print(line_str, file=stream)
    stream.flush()
    application.exit(0 if all_opened_b else 1)


def install_startup_probe(application, main_window, main_start_s: float,
                          load_file, environment_dict: dict = None) -> bool:
    """Switch on the startup probe when the environment asks for it.

    Inputs:
        application: the QApplication.
        main_window: the app's MainWindow, already shown.
        main_start_s: time.perf_counter() when src/main.py started.
        load_file: the app's file loader, for the probe files.
        environment_dict: the environment variables; os.environ when
            None.
    Outputs: True when the probe was installed; False (and nothing is
        changed) when PLOT_TOOL_STARTUP_PROBE is not "1".
    """
    # LLFR-00058: without the variable the app runs as usual.
    if environment_dict is None:
        environment_dict = dict(os.environ)
    if not startup_probe_enabled(environment_dict):
        return False
    deadline_s = time.perf_counter() + EXPOSE_TIMEOUT_S
    poll_timer = QTimer(main_window)
    poll_timer.setInterval(POLL_INTERVAL_MS_I)

    def check_window() -> None:
        """Report once the window is exposed, or when waiting too long.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00058: the window is on screen once it is exposed.
        exposed_b = window_exposed(main_window)
        if not exposed_b and time.perf_counter() < deadline_s:
            return
        poll_timer.stop()
        report_startup(application, main_start_s, exposed_b, load_file,
                       environment_dict)

    poll_timer.timeout.connect(check_window)
    poll_timer.start()
    return True
