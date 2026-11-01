"""Startup probe: report how long the app takes to show its window.

The probe exists only to check the standalone build (issue #67). It is
off unless the environment variable ``PLOT_TOOL_STARTUP_PROBE`` is
``"1"``, so a normal launch behaves exactly as before. When it is on:

1. as soon as the splash screen is on screen (HLFR-00046), before the
   slow imports start, one line is printed to standard output::

       plot_tool splash: splash_shown_epoch_s=<time.time()>
       since_main_s=<seconds since src/main.py started> exposed=<yes|no>
       heavy_modules=<none, or the slow modules already imported>
       pid=<process id>

   (all on one line, LLFR-00184);
2. as soon as the main window is shown and exposed on screen, one line
   is printed to standard output::

       plot_tool startup: window_shown_epoch_s=<time.time()>
       since_main_s=<seconds since src/main.py started> exposed=<yes|no>
       splash_visible=<yes|no> pid=<process id>

   (all on one line; splash_visible tells whether the splash screen is
   still shown, LLFR-00186). ``tests/user_tests/measure_startup.py``
   compares the epoch times with the time it launched the app;
3. if ``PLOT_TOOL_PROBE_FILES`` lists files (separated by
   ``os.pathsep``), each one is opened with the app's file loader and a
   line ``plot_tool probe file: OK|FAILED <name> ...`` is printed, to
   show that the bundle holds every library the loaders need;
4. the app quits, with exit code 0, or 1 when a probe file failed.

Code traced to LLFR-00058, LLFR-00184, LLFR-00186 and LLFR-00188: the
probe only watches the splash screen and the main window with its three
panels being shown; it is a build check, not a function.
"""

import os
import sys
import time
import traceback

from PyQt6.QtCore import QTimer

STARTUP_PROBE_VARIABLE_STR = "PLOT_TOOL_STARTUP_PROBE"
PROBE_FILES_VARIABLE_STR = "PLOT_TOOL_PROBE_FILES"
STARTUP_LINE_PREFIX_STR = "plot_tool startup:"
SPLASH_LINE_PREFIX_STR = "plot_tool splash:"
# LLFR-00184: modules that are slow to import and must not be imported
# before the splash screen is shown.
HEAVY_MODULE_TUPLE = ("matplotlib", "numpy", "pandas", "scipy",
                      "openpyxl", "h5py", "view.main_window",
                      "view.plot_widget", "controller.main_controller",
                      "model.file_loader")
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


def yes_no_str(value_b: bool) -> str:
    """Write a flag of a probe line.

    Inputs:
        value_b: the flag.
    Outputs: "yes" or "no".
    """
    # LLFR-00058: the flags of the probe lines.
    return "yes" if value_b else "no"


def startup_line_str(main_start_s: float, exposed_b: bool,
                     splash_visible_b: bool = False) -> str:
    """Build the line that reports the startup time.

    Inputs:
        main_start_s: time.perf_counter() when src/main.py started.
        exposed_b: whether the window was exposed when reporting.
        splash_visible_b: whether the splash screen was still shown.
    Outputs: the report line, without a line break.
    """
    # LLFR-00058, LLFR-00188: when the window was shown, in two clocks.
    # LLFR-00186: and whether the splash screen was closed by then.
    since_main_s = time.perf_counter() - main_start_s
    return (f"{STARTUP_LINE_PREFIX_STR} "
            f"window_shown_epoch_s={time.time():.3f} "
            f"since_main_s={since_main_s:.3f} "
            f"exposed={yes_no_str(exposed_b)} "
            f"splash_visible={yes_no_str(splash_visible_b)} "
            f"pid={os.getpid()}")


def loaded_heavy_module_list(module_dict: dict) -> list:
    """Return the slow modules that are already imported.

    Inputs:
        module_dict: the imported modules (sys.modules).
    Outputs: the names of HEAVY_MODULE_TUPLE found in module_dict, in
        that order.
    """
    # LLFR-00184: none of them may be imported before the splash shows.
    return [name_str for name_str in HEAVY_MODULE_TUPLE
            if name_str in module_dict]


def phases_str(main_start_s: float, phase_list: list) -> str:
    """Write the startup phases for a probe line.

    Inputs:
        main_start_s: time.perf_counter() when src/main.py started.
        phase_list: (phase name, time.perf_counter()) tuples.
    Outputs: "name:seconds,..." with the seconds since main_start_s, or
        "none" when the list is empty.
    """
    # LLFR-00184: where the time before the splash screen goes.
    return ",".join(f"{name_str}:{phase_s - main_start_s:.3f}"
                    for name_str, phase_s in phase_list) or "none"


def splash_line_str(main_start_s: float, exposed_b: bool,
                    module_dict: dict, phase_list: list = None) -> str:
    """Build the line that reports when the splash screen was shown.

    Inputs:
        main_start_s: time.perf_counter() when src/main.py started.
        exposed_b: whether the splash was exposed on screen.
        module_dict: the imported modules (sys.modules).
        phase_list: (phase name, time.perf_counter()) tuples of the
            startup so far; None for none.
    Outputs: the report line, without a line break.
    """
    # LLFR-00184: when the splash was shown, and which slow modules were
    # already imported then.
    since_main_s = time.perf_counter() - main_start_s
    heavy_module_list = loaded_heavy_module_list(module_dict)
    heavy_modules_str = ",".join(heavy_module_list) or "none"
    return (f"{SPLASH_LINE_PREFIX_STR} "
            f"splash_shown_epoch_s={time.time():.3f} "
            f"since_main_s={since_main_s:.3f} "
            f"exposed={yes_no_str(exposed_b)} "
            f"heavy_modules={heavy_modules_str} "
            f"phases={phases_str(main_start_s, phase_list or [])} "
            f"pid={os.getpid()}")


def report_splash_shown(splash, main_start_s: float,
                        environment_dict: dict = None,
                        output_stream=None, phase_list: list = None) -> bool:
    """Print the splash line when the startup probe is on.

    Inputs:
        splash: the shown SplashScreen.
        main_start_s: time.perf_counter() when src/main.py started.
        environment_dict: the environment variables; os.environ when
            None.
        output_stream: where to print; standard output when None.
        phase_list: (phase name, time.perf_counter()) tuples of the
            startup so far, printed with the line.
    Outputs: True when the line was printed; False (nothing printed)
        when PLOT_TOOL_STARTUP_PROBE is not "1".
    """
    # LLFR-00184: without the variable the app runs as usual.
    if environment_dict is None:
        environment_dict = dict(os.environ)
    if not startup_probe_enabled(environment_dict):
        return False
    from view.splash_screen import splash_exposed
    stream = output_stream if output_stream is not None else sys.stdout
    print(splash_line_str(main_start_s, splash_exposed(splash),
                          sys.modules, phase_list), file=stream)
    stream.flush()
    return True


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
        signal_count_i = len(signal_file.signal_name_list)
        line_list.append(f"{PROBE_FILE_LINE_PREFIX_STR} OK "
                         f"{file_name_str} signals={signal_count_i}")
    return line_list, all_opened_b


def report_startup(application, main_start_s: float, exposed_b: bool,
                   load_file, environment_dict: dict,
                   output_stream=None,
                   splash_visible_b: bool = False) -> None:
    """Print the startup report and quit the app.

    Inputs:
        application: the QApplication (only its ``exit`` is used).
        main_start_s: time.perf_counter() when src/main.py started.
        exposed_b: whether the window was exposed when reporting.
        load_file: the app's file loader, for the probe files.
        environment_dict: the environment variables (os.environ).
        output_stream: where to print; standard output when None.
        splash_visible_b: whether the splash screen was still shown.
    Outputs: none. Ends the event loop with exit code 0, or 1 when a
        probe file could not be opened.
    """
    # LLFR-00058: report the shown window first, so that opening the
    # probe files doesn't add to the measured time.
    stream = output_stream if output_stream is not None else sys.stdout
    print(startup_line_str(main_start_s, exposed_b, splash_visible_b),
          file=stream)
    line_list, all_opened_b = probe_file_line_list(
        probe_file_path_list(environment_dict), load_file)
    for line_str in line_list:
        print(line_str, file=stream)
    stream.flush()
    application.exit(0 if all_opened_b else 1)


def install_startup_probe(application, main_window, main_start_s: float,
                          load_file, environment_dict: dict = None,
                          splash=None) -> bool:
    """Switch on the startup probe when the environment asks for it.

    Inputs:
        application: the QApplication.
        main_window: the app's MainWindow, already shown.
        main_start_s: time.perf_counter() when src/main.py started.
        load_file: the app's file loader, for the probe files.
        environment_dict: the environment variables; os.environ when
            None.
        splash: the SplashScreen, whose visibility is reported with the
            window (LLFR-00186); None when there is none.
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
        try:
            splash_visible_b = (splash is not None
                                and splash.isVisible())
            report_startup(application, main_start_s, exposed_b,
                           load_file, environment_dict,
                           splash_visible_b=splash_visible_b)
        except Exception:
            # LLFR-00058: a probe failure must end the run with an
            # error, not open an error box that waits for a user.
            traceback.print_exc()
            application.exit(1)

    poll_timer.timeout.connect(check_window)
    poll_timer.start()
    return True
