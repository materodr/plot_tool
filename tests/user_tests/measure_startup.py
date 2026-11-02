"""Measure how long plot_tool takes to show its splash and its window.

Run from the repository root, with the app built or from source:

    python tests/user_tests/measure_startup.py \\
        bin/plot_tool.app/Contents/MacOS/plot_tool
    python tests/user_tests/measure_startup.py --runs 2 --limit-s 10 \\
        --probe-good-files -- python src/main.py

The command after the options is launched ``--runs`` times with
``PLOT_TOOL_STARTUP_PROBE=1`` (see src/view/startup_probe.py). For each
run the script prints the time from launch to the shown splash screen
(LLFR-00184) and to the shown window (LLFR-00188), and checks that the
window was reported by the launched process itself: a one-file
PyInstaller build would report from a second process. The first run is
the cold launch, the others are warm launches. With
``--probe-good-files`` the app also opens every file of
tests/user_tests/good and the run fails if one can't be opened.

Checks, each switched on by its option:
- ``--limit-s``: the last launch shows the window within this time;
- ``--warm-limit-s``: every warm launch shows the window within this
  time (LLFR-00188: 5 s);
- ``--splash-limit-s``: every launch, the cold one included, shows the
  splash screen within this time (LLFR-00184: 2 s), with no slow module
  imported yet, and closes it when the window is shown (LLFR-00186);
- ``--font-cache-folder``: matplotlib's font list in this folder is
  written by the first launch and never again (LLFR-00189). With
  ``--clear-font-cache`` the folder is emptied before the first launch,
  so that the first launch is really cold;
- ``--dialog-limit-s``: every launch also asks for each file dialog
  twice, as a click would (``PLOT_TOOL_DIALOG_PROBE=1``); on every
  launch the dialogs must be prepared with no dialog shown before the
  first request and every request must show its dialog; on every warm
  launch each dialog must be shown within this time (LLFR-00406: 0.65
  s; as in LLFR-00188, the work done once on the first launch does not
  count, so the cold launch is only reported);
- ``--turn-limit-s``: with ``--dialog-limit-s``, no turn of the event
  loop may take longer than this while the dialogs are prepared after
  the window is shown, so that the window answers the user at once
  (LLFR-00188).

In GitHub Actions the timings are also printed as ``::notice``
annotations and the failures as ``::error`` annotations. The exit code
is 1 when a run or a check fails.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import time

USER_TESTS_FOLDER_STR = os.path.dirname(os.path.abspath(__file__))
GOOD_FOLDER_STR = os.path.join(USER_TESTS_FOLDER_STR, "good")
STARTUP_PROBE_VARIABLE_STR = "PLOT_TOOL_STARTUP_PROBE"
PROBE_FILES_VARIABLE_STR = "PLOT_TOOL_PROBE_FILES"
STARTUP_LINE_PREFIX_STR = "plot_tool startup:"
SPLASH_LINE_PREFIX_STR = "plot_tool splash:"
PROBE_FILE_PREFIX_STR = "plot_tool probe file:"
DIALOG_PROBE_VARIABLE_STR = "PLOT_TOOL_DIALOG_PROBE"
DIALOG_LINE_PREFIX_STR = "plot_tool dialog:"
PREPARE_LINE_PREFIX_STR = "plot_tool prepare:"
# LLFR-00406: the probe asks for 5 dialogs, twice each.
DIALOG_REQUEST_COUNT_I = 10
FONT_LIST_PATTERN_STR = "fontlist-*.json"


def parse_probe_line_dict(output_str: str, prefix_str: str) -> dict:
    """Find a probe line and read its ``key=value`` fields.

    Inputs:
        output_str: everything the app printed to standard output.
        prefix_str: the start of the line, such as "plot_tool startup:".
    Outputs: field name -> value text, from the first line that starts
        with prefix_str; an empty dict when there is no such line.
    """
    for line_str in output_str.splitlines():
        line_str = line_str.strip()
        if not line_str.startswith(prefix_str):
            continue
        field_dict = {}
        for field_str in line_str[len(prefix_str):].split():
            key_str, separator_str, value_str = field_str.partition("=")
            if separator_str:
                field_dict[key_str] = value_str
        return field_dict
    return {}


def parse_startup_line(output_str: str) -> dict:
    """Find and read the window line of the startup probe.

    Inputs:
        output_str: everything the app printed to standard output.
    Outputs: a dict with "window_shown_epoch_s" and "since_main_s"
        (floats), "exposed_b" (bool), "process_id_i" (int) and
        "splash_visible_b" (bool, False when the field is missing); an
        empty dict when the line is missing or incomplete.
    """
    field_dict = parse_probe_line_dict(output_str, STARTUP_LINE_PREFIX_STR)
    try:
        return {"window_shown_epoch_s": float(
                    field_dict["window_shown_epoch_s"]),
                "since_main_s": float(field_dict["since_main_s"]),
                "exposed_b": field_dict["exposed"] == "yes",
                "process_id_i": int(field_dict["pid"]),
                "splash_visible_b": field_dict.get(
                    "splash_visible", "no") == "yes"}
    except (KeyError, ValueError):
        return {}


def parse_splash_line(output_str: str) -> dict:
    """Find and read the splash line of the startup probe.

    Inputs:
        output_str: everything the app printed to standard output.
    Outputs: a dict with "splash_shown_epoch_s" and "since_main_s"
        (floats), "exposed_b" (bool), "heavy_module_list" (the slow
        modules already imported, empty when none) and "process_id_i"
        (int); an empty dict when the line is missing or incomplete.
    """
    field_dict = parse_probe_line_dict(output_str, SPLASH_LINE_PREFIX_STR)
    try:
        heavy_modules_str = field_dict["heavy_modules"]
        return {"splash_shown_epoch_s": float(
                    field_dict["splash_shown_epoch_s"]),
                "since_main_s": float(field_dict["since_main_s"]),
                "exposed_b": field_dict["exposed"] == "yes",
                "heavy_module_list": (
                    [] if heavy_modules_str == "none"
                    else heavy_modules_str.split(",")),
                "process_id_i": int(field_dict["pid"])}
    except (KeyError, ValueError):
        return {}


def parse_prepare_line(output_str: str) -> dict:
    """Find and read the line on the preparation of the file dialogs.

    Inputs:
        output_str: everything the app printed to standard output.
    Outputs: a dict with "prepared_b" and "dialog_seen_b" (bools),
        "waited_s", "prepare_s", "longest_step_s" and "longest_turn_s"
        (floats), "step_count_i" (int) and "panel_state_str"; an empty
        dict when the line is missing or incomplete.
    """
    field_dict = parse_probe_line_dict(output_str, PREPARE_LINE_PREFIX_STR)
    try:
        return {"prepared_b": field_dict["prepared"] == "yes",
                "dialog_seen_b": field_dict["dialog_seen"] == "yes",
                "waited_s": float(field_dict["waited_s"]),
                "prepare_s": float(field_dict["prepare_s"]),
                "longest_step_s": float(field_dict["longest_step_s"]),
                "longest_turn_s": float(field_dict["longest_turn_s"]),
                "step_count_i": int(field_dict["steps"]),
                "panel_state_str": field_dict["panels"]}
    except (KeyError, ValueError):
        return {}


def parse_dialog_line_list(output_str: str) -> list:
    """Find and read every dialog line of the startup probe.

    Inputs:
        output_str: everything the app printed to standard output.
    Outputs: one dict per line, in order, with "name_str",
        "click_i" (int), "shown_s" (float) and "visible_b" (bool);
        lines that cannot be read are left out.
    """
    dialog_list = []
    for line_str in output_str.splitlines():
        line_str = line_str.strip()
        if not line_str.startswith(DIALOG_LINE_PREFIX_STR):
            continue
        field_dict = parse_probe_line_dict(line_str, DIALOG_LINE_PREFIX_STR)
        try:
            dialog_list.append({
                "name_str": field_dict["name"],
                "click_i": int(field_dict["click"]),
                "shown_s": float(field_dict["shown_s"]),
                "visible_b": field_dict["visible"] == "yes"})
        except (KeyError, ValueError):
            continue
    return dialog_list


def dialog_failure_list(output_str: str, warm_b: bool,
                        dialog_limit_s: float,
                        turn_limit_s: float = None) -> list:
    """Check the dialog lines of one launch.

    Inputs:
        output_str: everything the app printed to standard output.
        warm_b: whether the launch is a warm one (not the first).
        dialog_limit_s: the longest time from a request to its dialog
            for a warm launch (LLFR-00406).
        turn_limit_s: the longest event-loop turn allowed while the
            dialogs are prepared, or None for no check (LLFR-00188).
    Outputs: the list of failure descriptions; empty when every check
        passed.
    """
    failure_list = []
    prepare_dict = parse_prepare_line(output_str)
    if not prepare_dict:
        failure_list.append("the app did not report the preparation of "
                            "its file dialogs (LLFR-00406)")
    else:
        if not prepare_dict["prepared_b"]:
            failure_list.append("the file dialogs were not prepared "
                                "(LLFR-00406)")
        if prepare_dict["dialog_seen_b"]:
            failure_list.append("a file dialog was shown before any "
                                "request (issue #165)")
        if (turn_limit_s is not None
                and prepare_dict["longest_turn_s"] > turn_limit_s):
            failure_list.append(
                "the window was kept busy for "
                f"{prepare_dict['longest_turn_s']:.3f} s while the "
                f"dialogs were prepared, more than {turn_limit_s} s "
                "(LLFR-00188)")
    dialog_list = parse_dialog_line_list(output_str)
    if len(dialog_list) < DIALOG_REQUEST_COUNT_I:
        failure_list.append(f"{len(dialog_list)} of "
                            f"{DIALOG_REQUEST_COUNT_I} dialog requests "
                            "were reported (LLFR-00406)")
    for dialog_dict in dialog_list:
        request_str = (f"{dialog_dict['name_str']} request "
                       f"{dialog_dict['click_i']}")
        if not dialog_dict["visible_b"]:
            failure_list.append(f"{request_str} showed no dialog "
                                "(LLFR-00406)")
        elif warm_b and dialog_dict["shown_s"] > dialog_limit_s:
            failure_list.append(
                f"{request_str} showed its dialog after "
                f"{dialog_dict['shown_s']:.3f} s, more than "
                f"{dialog_limit_s} s (LLFR-00406)")
    return failure_list


def dialog_summary_str(output_str: str) -> str:
    """Summarize the dialog lines of one launch.

    Inputs:
        output_str: everything the app printed to standard output.
    Outputs: one line with the slowest first and second request and the
        preparation figures; "no dialog lines" when there are none.
    """
    dialog_list = parse_dialog_line_list(output_str)
    if not dialog_list:
        return "no dialog lines"
    first_s = max([dialog_dict["shown_s"] for dialog_dict in dialog_list
                   if dialog_dict["click_i"] == 1] or [0.0])
    second_s = max([dialog_dict["shown_s"] for dialog_dict in dialog_list
                    if dialog_dict["click_i"] != 1] or [0.0])
    summary_str = (f"slowest dialog {first_s:.3f} s on the first request,"
                   f" {second_s:.3f} s on the second")
    prepare_dict = parse_prepare_line(output_str)
    if prepare_dict:
        summary_str += (
            f"; prepared in {prepare_dict['prepare_s']:.3f} s "
            f"({prepare_dict['step_count_i']} steps, longest "
            f"{prepare_dict['longest_step_s']:.3f} s, longest event-loop"
            f" turn {prepare_dict['longest_turn_s']:.3f} s, panels "
            f"{prepare_dict['panel_state_str']})")
    return summary_str


def good_file_path_list() -> list:
    """Return the sample files that the app must open.

    Inputs: none.
    Outputs: the sorted paths of the files in tests/user_tests/good.
    """
    return sorted(os.path.join(GOOD_FOLDER_STR, file_name_str)
                  for file_name_str in os.listdir(GOOD_FOLDER_STR)
                  if not file_name_str.startswith("."))


def font_list_state_dict(folder_str: str) -> dict:
    """Return matplotlib's font list files and when they were written.

    Inputs:
        folder_str: matplotlib's cache folder (MPLCONFIGDIR).
    Outputs: file name -> modification time in nanoseconds, for every
        fontlist-*.json file of the folder; empty when there is none.
    """
    return {os.path.basename(path_str): os.stat(path_str).st_mtime_ns
            for path_str in glob.glob(os.path.join(folder_str,
                                                   FONT_LIST_PATTERN_STR))}


def launch_once(command_list: list, probe_path_list: list,
                timeout_s: float, dialog_probe_b: bool = False) -> dict:
    """Launch the app once with the startup probe and time it.

    Inputs:
        command_list: the command that starts the app.
        probe_path_list: files the app must open after the window shows.
        timeout_s: how long to wait for the app to quit by itself.
        dialog_probe_b: whether the app also measures its file dialogs
            (PLOT_TOOL_DIALOG_PROBE=1).
    Outputs: a dict with "launch_to_window_s" and "launch_to_splash_s"
        (floats, or None when the probe line is missing),
        "same_process_b", "exposed_b", "splash_exposed_b",
        "splash_visible_b" (still shown with the window),
        "heavy_module_list" (slow modules imported before the splash),
        "exit_code_i" and "output_str".
    """
    environment_dict = dict(os.environ)
    environment_dict[STARTUP_PROBE_VARIABLE_STR] = "1"
    environment_dict[PROBE_FILES_VARIABLE_STR] = os.pathsep.join(
        probe_path_list)
    if dialog_probe_b:
        environment_dict[DIALOG_PROBE_VARIABLE_STR] = "1"
    launch_epoch_s = time.time()
    process = subprocess.Popen(command_list, env=environment_dict,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True)
    try:
        output_str, _ = process.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        process.kill()
        output_str, _ = process.communicate()
        output_str += f"\n(killed after {timeout_s} s)"
    startup_dict = parse_startup_line(output_str)
    splash_dict = parse_splash_line(output_str)
    result_dict = {"launch_to_window_s": None, "launch_to_splash_s": None,
                   "same_process_b": False, "exposed_b": False,
                   "splash_exposed_b": False, "splash_visible_b": False,
                   "heavy_module_list": [],
                   "exit_code_i": process.returncode,
                   "output_str": output_str}
    if startup_dict:
        result_dict["launch_to_window_s"] = (
            startup_dict["window_shown_epoch_s"] - launch_epoch_s)
        result_dict["same_process_b"] = (
            startup_dict["process_id_i"] == process.pid)
        result_dict["exposed_b"] = startup_dict["exposed_b"]
        result_dict["splash_visible_b"] = startup_dict["splash_visible_b"]
    if splash_dict:
        result_dict["launch_to_splash_s"] = (
            splash_dict["splash_shown_epoch_s"] - launch_epoch_s)
        result_dict["splash_exposed_b"] = splash_dict["exposed_b"]
        result_dict["heavy_module_list"] = splash_dict["heavy_module_list"]
    return result_dict


def run_failure_str(result_dict: dict) -> str:
    """Describe why a run failed.

    Inputs:
        result_dict: the result of launch_once.
    Outputs: the reason, or an empty string when the run is fine.
    """
    if result_dict["launch_to_window_s"] is None:
        return "the app did not report a shown window"
    if not result_dict["same_process_b"]:
        return ("the window was shown by another process than the one "
                "launched (one-file build?)")
    if result_dict["exit_code_i"] != 0:
        return f"the app exited with code {result_dict['exit_code_i']}"
    return ""


def limit_failure_list(result_dict: dict, warm_b: bool,
                       warm_limit_s: float = None,
                       splash_limit_s: float = None) -> list:
    """Check the time limits of one successful run.

    Inputs:
        result_dict: the result of launch_once.
        warm_b: whether the run is a warm launch (not the first one).
        warm_limit_s: the longest time to the window for a warm launch
            (LLFR-00188), or None for no check.
        splash_limit_s: the longest time to the splash for any launch
            (LLFR-00184), or None for no check.
    Outputs: the list of failure descriptions; empty when every check
        passed.
    """
    failure_list = []
    window_s = result_dict["launch_to_window_s"]
    if warm_b and warm_limit_s is not None and window_s is not None:
        if window_s > warm_limit_s:
            failure_list.append(
                f"warm launch showed the window after {window_s:.2f} s, "
                f"more than {warm_limit_s} s (LLFR-00188)")
    if splash_limit_s is None:
        return failure_list
    splash_s = result_dict["launch_to_splash_s"]
    if splash_s is None:
        failure_list.append("the app did not report a shown splash screen "
                            "(LLFR-00184)")
        return failure_list
    if splash_s > splash_limit_s:
        failure_list.append(
            f"the splash screen was shown after {splash_s:.2f} s, more "
            f"than {splash_limit_s} s (LLFR-00184)")
    if not result_dict["splash_exposed_b"]:
        failure_list.append("the splash screen was not exposed on screen "
                            "(LLFR-00184)")
    if result_dict["heavy_module_list"]:
        failure_list.append(
            "slow modules were imported before the splash screen: "
            + ",".join(result_dict["heavy_module_list"]) + " (LLFR-00184)")
    if result_dict["splash_visible_b"]:
        failure_list.append("the splash screen was still shown with the "
                            "window (LLFR-00186)")
    return failure_list


def font_cache_failure_str(first_state_dict: dict,
                           state_dict: dict) -> str:
    """Check that a later launch did not rebuild the font list.

    Inputs:
        first_state_dict: font_list_state_dict after the first launch.
        state_dict: font_list_state_dict after a later launch.
    Outputs: the failure description, or an empty string when the font
        list written by the first launch is unchanged (LLFR-00189).
    """
    if not first_state_dict:
        return "the first launch wrote no font list (LLFR-00189)"
    if state_dict != first_state_dict:
        return ("the font list was written again by a later launch "
                f"({first_state_dict} -> {state_dict}) (LLFR-00189)")
    return ""


def report(message_str: str, kind_str: str, title_str: str,
           in_actions_b: bool) -> None:
    """Print a message, and its GitHub Actions annotation.

    Inputs:
        message_str: the message.
        kind_str: "notice" or "error".
        title_str: the title of the annotation.
        in_actions_b: whether the script runs in GitHub Actions.
    Outputs: none.
    """
    print(message_str)
    if in_actions_b:
        print(f"::{kind_str} title={title_str}::{message_str}")


def build_argument_parser() -> argparse.ArgumentParser:
    """Return the parser of the command line.

    Inputs: none.
    Outputs: the ArgumentParser.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=2,
                        help="number of launches; the first is cold")
    parser.add_argument("--limit-s", type=float, default=10.0,
                        help="maximum time of the last launch")
    parser.add_argument("--warm-limit-s", type=float, default=None,
                        help="maximum time to the window of every warm "
                        "launch (LLFR-00188)")
    parser.add_argument("--splash-limit-s", type=float, default=None,
                        help="maximum time to the splash screen of every "
                        "launch (LLFR-00184)")
    parser.add_argument("--font-cache-folder", default=None,
                        help="matplotlib's cache folder, whose font list "
                        "must be written only once (LLFR-00189)")
    parser.add_argument("--clear-font-cache", action="store_true",
                        help="empty --font-cache-folder before the first "
                        "launch")
    parser.add_argument("--timeout-s", type=float, default=180.0,
                        help="time after which a launch is killed")
    parser.add_argument("--dialog-limit-s", type=float, default=None,
                        help="also measure the file dialogs; maximum time "
                        "from a request to its dialog on a warm launch "
                        "(LLFR-00406)")
    parser.add_argument("--turn-limit-s", type=float, default=None,
                        help="with --dialog-limit-s, maximum event-loop "
                        "turn while the dialogs are prepared (LLFR-00188)")
    parser.add_argument("--probe-good-files", action="store_true",
                        help="open every file of tests/user_tests/good")
    parser.add_argument("command", nargs="+",
                        help="the command that starts the app")
    return parser


def main() -> int:
    """Launch the app several times and report the startup times.

    Inputs: none (reads the command line).
    Outputs: the exit code, 0 when every check passed.
    """
    argument_namespace = build_argument_parser().parse_args()
    probe_path_list = (good_file_path_list()
                       if argument_namespace.probe_good_files else [])
    in_actions_b = os.environ.get("GITHUB_ACTIONS") == "true"
    font_folder_str = argument_namespace.font_cache_folder
    if font_folder_str and argument_namespace.clear_font_cache:
        shutil.rmtree(font_folder_str, ignore_errors=True)
        print(f"emptied {font_folder_str} before the cold launch")
    failed_b = False
    last_time_s = None
    first_font_state_dict = None
    for run_i in range(1, argument_namespace.runs + 1):
        kind_str = "cold" if run_i == 1 else "warm"
        title_str = f"Startup run {run_i} ({kind_str})"
        dialog_limit_s = argument_namespace.dialog_limit_s
        result_dict = launch_once(argument_namespace.command,
                                  probe_path_list,
                                  argument_namespace.timeout_s,
                                  dialog_limit_s is not None)
        print(f"--- run {run_i} ({kind_str}) output ---")
        print(result_dict["output_str"].rstrip())
        failure_list = []
        failure_str = run_failure_str(result_dict)
        if failure_str:
            failure_list.append(failure_str)
        else:
            last_time_s = result_dict["launch_to_window_s"]
            splash_s = result_dict["launch_to_splash_s"]
            splash_str = ("no splash reported" if splash_s is None
                          else f"splash shown {splash_s:.2f} s")
            exposed_str = "" if result_dict["exposed_b"] else (
                " (window not reported as exposed)")
            report(f"run {run_i} ({kind_str}): {splash_str}, window "
                   f"shown {last_time_s:.2f} s after launch, single "
                   f"process{exposed_str}", "notice", "Startup time",
                   in_actions_b)
            failure_list += limit_failure_list(
                result_dict, run_i > 1, argument_namespace.warm_limit_s,
                argument_namespace.splash_limit_s)
        if dialog_limit_s is not None:
            report(f"run {run_i} ({kind_str}): "
                   + dialog_summary_str(result_dict["output_str"]),
                   "notice", "Dialog time", in_actions_b)
            failure_list += dialog_failure_list(
                result_dict["output_str"], run_i > 1, dialog_limit_s,
                argument_namespace.turn_limit_s)
        if font_folder_str:
            font_state_dict = font_list_state_dict(font_folder_str)
            print(f"font list after run {run_i}: {font_state_dict}")
            if first_font_state_dict is None:
                first_font_state_dict = font_state_dict
                if not font_state_dict:
                    failure_list.append(font_cache_failure_str({}, {}))
            else:
                cache_failure_str = font_cache_failure_str(
                    first_font_state_dict, font_state_dict)
                if cache_failure_str:
                    failure_list.append(cache_failure_str)
                else:
                    report(f"run {run_i} ({kind_str}): the font list of "
                           "the first launch was reused, not rebuilt",
                           "notice", "Font cache", in_actions_b)
        for failure_str in failure_list:
            failed_b = True
            report(f"run {run_i} ({kind_str}) FAILED: {failure_str}",
                   "error", title_str, in_actions_b)
    if last_time_s is not None and last_time_s > argument_namespace.limit_s:
        failed_b = True
        report(f"last launch took {last_time_s:.2f} s, more than "
               f"{argument_namespace.limit_s} s", "error",
               "Startup too slow", in_actions_b)
    return 1 if failed_b else 0


if __name__ == "__main__":
    sys.exit(main())
