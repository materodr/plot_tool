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
4. if ``PLOT_TOOL_DIALOG_PROBE`` is ``"1"``, each file dialog of the
   app (LLFR-00406) is shown twice, as a click would (measure_dialog),
   PROBE_PAUSE_S after the previous one, and closed as soon as it is
   shown; for each one a line is printed::

       plot_tool dialog: name=<dialog> click=<1|2> shown_s=<seconds
       from the request to the dialog being shown> visible=<yes|no>
       prepared=<yes|no> prepare_s=<seconds the preparation took>

   (all on one line). The first request comes once the dialogs have
   been prepared, or after DIALOG_PREPARE_TIMEOUT_S. Before them, one
   line tells how the preparation went::

       plot_tool prepare: prepared=<yes|no> waited_s=<seconds from the
       window line> steps=<count> prepare_s=<seconds in the steps>
       longest_step_s=<seconds> longest_turn_s=<longest event-loop
       turn meanwhile> step_s=<seconds of each step, comma-separated>
       panels=<what each panel warm-up step did, comma-separated, or
       none> dialog_seen=<yes|no>

   (all on one line; dialog_seen tells whether a file dialog was
   visible before the first request, which must never happen);
5. the app quits, with exit code 0, or 1 when a probe file failed.

Code traced to LLFR-00058, LLFR-00184, LLFR-00186, LLFR-00188 and
LLFR-00406: the probe only watches the splash screen, the main window
with its three panels and the file dialogs being shown; it is a build
check, not a function.
"""

import os
import sys
import time
import traceback

from PyQt6.QtCore import Qt, QTimer

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
# LLFR-00406: the dialog part of the probe.
DIALOG_PROBE_VARIABLE_STR = "PLOT_TOOL_DIALOG_PROBE"
DIALOG_LINE_PREFIX_STR = "plot_tool dialog:"
PREPARE_LINE_PREFIX_STR = "plot_tool prepare:"
DIALOG_PREPARE_TIMEOUT_S = 10.0
# LLFR-00406: (name in the probe line, key of the dialog in the main
# window's FileDialogPool).
PROBE_DIALOG_TUPLE = (
    ("open_file", "open_file"), ("save_layout", "save_layout"),
    ("load_layout", "load_layout"), ("save_pdf", "save_pdf"),
    ("save_signals", "save_signals"))
PROBE_CLICK_COUNT_I = 2
# LLFR-00406: the time between two requests, as between two clicks.
PROBE_PAUSE_S = 0.5
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


def dialog_probe_enabled(environment_dict: dict) -> bool:
    """Tell whether the dialog part of the probe is switched on.

    Inputs:
        environment_dict: the environment variables (os.environ).
    Outputs: True only when PLOT_TOOL_DIALOG_PROBE is "1".
    """
    # LLFR-00406: off by default.
    return environment_dict.get(DIALOG_PROBE_VARIABLE_STR, "") == "1"


def dialog_line_str(name_str: str, click_i: int, shown_s: float,
                    visible_b: bool, prepared_b: bool,
                    prepare_s: float) -> str:
    """Build the line that reports how fast one dialog was shown.

    Inputs:
        name_str: the name of the dialog.
        click_i: 1 for the first request, 2 for the next one.
        shown_s: seconds from the request to the dialog being shown.
        visible_b: whether the dialog was visible then.
        prepared_b: whether the dialogs had been prepared before.
        prepare_s: how long their preparation took.
    Outputs: the report line, without a line break.
    """
    # LLFR-00406: one line per dialog and request.
    return (f"{DIALOG_LINE_PREFIX_STR} name={name_str} click={click_i} "
            f"shown_s={shown_s:.3f} visible={yes_no_str(visible_b)} "
            f"prepared={yes_no_str(prepared_b)} "
            f"prepare_s={prepare_s:.3f}")


def measure_dialog(main_window, application, key_str: str) -> tuple:
    """Show one file dialog as a click would, then close it.

    The probe first lets the event loop run for PROBE_PAUSE_S, as the
    time between two clicks of a user, so that the closing of the
    previous dialog is not counted. The dialog is then shown as a
    standalone window, as ``exec`` (the click) shows it, but with
    ``show`` on a non-modal dialog, so that the probe never waits in a
    modal loop it cannot close (a system panel run with ``exec`` on
    macOS runs the system's own modal loop). ``open`` would show it as
    a sheet of the main window instead, with an animation that the
    next sheet must wait for.

    Inputs:
        main_window: the app's MainWindow.
        application: the QApplication, to let the dialog be drawn.
        key_str: the key of the dialog in main_window.file_dialog_pool.
    Outputs: a tuple (seconds from the request to the dialog being
        shown and drawn, True when it was visible then).
    """
    # LLFR-00406: the same steps as the MainWindow ask_... methods,
    # up to the dialog being on screen.
    pause_until_s = time.perf_counter() + PROBE_PAUSE_S
    while time.perf_counter() < pause_until_s:
        application.processEvents()
        time.sleep(POLL_INTERVAL_MS_I / 1000.0)
    start_s = time.perf_counter()
    dialog = main_window.file_dialog_pool.prepared_dialog(key_str)
    modality = dialog.windowModality()
    dialog.setWindowModality(Qt.WindowModality.NonModal)
    dialog.show()
    application.processEvents()
    shown_s = time.perf_counter() - start_s
    visible_b = bool(dialog.isVisible())
    dialog.reject()
    dialog.setWindowModality(modality)
    application.processEvents()
    return shown_s, visible_b


def prepare_line_str(pool, waited_s: float, longest_wait_s: float,
                     dialog_seen_b: bool) -> str:
    """Build the line that reports the preparation of the dialogs.

    Inputs:
        pool: the main window's FileDialogPool.
        waited_s: seconds from the window being shown to the dialogs
            being prepared.
        longest_wait_s: the longest time one turn of the event loop
            took meanwhile, so how long the window was kept from
            answering the user at most.
        dialog_seen_b: whether a file dialog was visible meanwhile.
    Outputs: the report line, without a line break.
    """
    # LLFR-00406, LLFR-00188: the preparation shows nothing and never
    # blocks the window for long.
    step_s_str = ",".join(f"{step_s:.3f}"
                          for step_s in pool.step_duration_list)
    return (f"{PREPARE_LINE_PREFIX_STR} "
            f"prepared={yes_no_str(pool.prepared_b)} "
            f"waited_s={waited_s:.3f} steps={pool.step_count_i} "
            f"prepare_s={pool.prepare_duration_s:.3f} "
            f"longest_step_s={pool.longest_step_s:.3f} "
            f"longest_turn_s={longest_wait_s:.3f} "
            f"step_s={step_s_str or 'none'} "
            f"panels={pool.panel_state_str()} "
            f"dialog_seen={yes_no_str(dialog_seen_b)}")


def any_dialog_visible(pool) -> bool:
    """Tell whether a dialog of the pool is shown.

    Inputs:
        pool: the main window's FileDialogPool.
    Outputs: True when a built dialog of the pool is visible.
    """
    # LLFR-00406: no dialog may appear without a click (issue #165).
    return any(pool.is_built(key_str) and pool.dialog(key_str).isVisible()
               for key_str in pool.key_list())


def wait_for_preparation(pool, application) -> tuple:
    """Let the event loop run until the dialogs are prepared.

    Inputs:
        pool: the main window's FileDialogPool.
        application: the QApplication.
    Outputs: a tuple (seconds waited, longest processEvents call in
        seconds, True when a dialog of the pool was seen visible).
    """
    # LLFR-00406: as a user would wait before clicking; each turn is
    # timed, so a preparation step that blocks the window shows.
    start_s = time.perf_counter()
    deadline_s = start_s + DIALOG_PREPARE_TIMEOUT_S
    longest_wait_s = 0.0
    dialog_seen_b = False
    while not pool.prepared_b and time.perf_counter() < deadline_s:
        turn_start_s = time.perf_counter()
        application.processEvents()
        longest_wait_s = max(longest_wait_s,
                             time.perf_counter() - turn_start_s)
        dialog_seen_b = dialog_seen_b or any_dialog_visible(pool)
        time.sleep(POLL_INTERVAL_MS_I / 1000.0)
    return time.perf_counter() - start_s, longest_wait_s, dialog_seen_b


def dialog_line_list(main_window, application, output_stream=None) -> list:
    """Measure every file dialog twice and describe the results.

    Inputs:
        main_window: the app's MainWindow, shown.
        application: the QApplication, to let pending work run.
        output_stream: where to print each line as soon as it is
            measured, or None to print nothing.
    Outputs: a list of report lines: the prepare line, then one
        dialog_line_str per dialog and request.
    """
    # LLFR-00406: wait for the preparation that the app schedules once
    # the window is shown, as a user would before clicking.
    pool = main_window.file_dialog_pool
    waited_s, longest_wait_s, dialog_seen_b = wait_for_preparation(
        pool, application)
    line_list = [prepare_line_str(pool, waited_s, longest_wait_s,
                                  dialog_seen_b)]
    if output_stream is not None:
        print(line_list[0], file=output_stream)
        output_stream.flush()
    for name_str, key_str in PROBE_DIALOG_TUPLE:
        for click_i in range(1, PROBE_CLICK_COUNT_I + 1):
            prepared_b = pool.prepared_b
            shown_s, visible_b = measure_dialog(main_window, application,
                                                key_str)
            line_str = dialog_line_str(
                name_str, click_i, shown_s, visible_b, prepared_b,
                pool.prepare_duration_s)
            line_list.append(line_str)
            if output_stream is not None:
                # LLFR-00406: printed at once, so a dialog that never
                # closes still leaves the earlier lines.
                print(line_str, file=output_stream)
                output_stream.flush()
    return line_list


def report_startup(application, main_start_s: float, exposed_b: bool,
                   load_file, environment_dict: dict,
                   output_stream=None,
                   splash_visible_b: bool = False,
                   main_window=None) -> None:
    """Print the startup report and quit the app.

    Inputs:
        application: the QApplication (only its ``exit`` is used).
        main_start_s: time.perf_counter() when src/main.py started.
        exposed_b: whether the window was exposed when reporting.
        load_file: the app's file loader, for the probe files.
        environment_dict: the environment variables (os.environ).
        output_stream: where to print; standard output when None.
        splash_visible_b: whether the splash screen was still shown.
        main_window: the app's MainWindow, for the dialog part of the
            probe (LLFR-00406); None skips it.
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
    # LLFR-00406: how fast each file dialog appears.
    if main_window is not None and dialog_probe_enabled(environment_dict):
        dialog_line_list(main_window, application, stream)
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
                           splash_visible_b=splash_visible_b,
                           main_window=main_window)
        except Exception:
            # LLFR-00058: a probe failure must end the run with an
            # error, not open an error box that waits for a user.
            traceback.print_exc()
            application.exit(1)

    poll_timer.timeout.connect(check_window)
    poll_timer.start()
    return True
