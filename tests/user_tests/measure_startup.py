"""Measure how long plot_tool takes to show its window (issue #67).

Run from the repository root, with the app built or from source:

    python tests/user_tests/measure_startup.py \\
        bin/plot_tool.app/Contents/MacOS/plot_tool
    python tests/user_tests/measure_startup.py --runs 2 --limit-s 10 \\
        --probe-good-files -- python src/main.py

The command after the options is launched ``--runs`` times with
``PLOT_TOOL_STARTUP_PROBE=1`` (see src/view/startup_probe.py). For each
run the script prints the time from launch to the shown window, and
checks that the window was reported by the launched process itself:
a one-file PyInstaller build would report from a second process. The
first run is the cold launch, the others are warm launches. With
``--probe-good-files`` the app also opens every file of
tests/user_tests/good and the run fails if one can't be opened.

In GitHub Actions the timings are also printed as ``::notice``
annotations. The exit code is 1 when a run fails, when the window is
reported by another process, or when the last run takes longer than
``--limit-s`` seconds.
"""

import argparse
import os
import re
import subprocess
import sys
import time

USER_TESTS_FOLDER_STR = os.path.dirname(os.path.abspath(__file__))
GOOD_FOLDER_STR = os.path.join(USER_TESTS_FOLDER_STR, "good")
STARTUP_PROBE_VARIABLE_STR = "PLOT_TOOL_STARTUP_PROBE"
PROBE_FILES_VARIABLE_STR = "PLOT_TOOL_PROBE_FILES"
STARTUP_LINE_PATTERN_STR = (
    r"^plot_tool startup: window_shown_epoch_s=(?P<epoch>[\d.]+) "
    r"since_main_s=(?P<since_main>[\d.]+) exposed=(?P<exposed>yes|no) "
    r"pid=(?P<pid>\d+)$")
PROBE_FILE_PREFIX_STR = "plot_tool probe file:"


def parse_startup_line(output_str: str) -> dict:
    """Find and read the startup probe line in the app's output.

    Inputs:
        output_str: everything the app printed to standard output.
    Outputs: a dict with "window_shown_epoch_s" and "since_main_s"
        (floats), "exposed_b" (bool) and "process_id_i" (int); an empty
        dict when the line is missing.
    """
    for line_str in output_str.splitlines():
        match = re.match(STARTUP_LINE_PATTERN_STR, line_str.strip())
        if match:
            return {"window_shown_epoch_s": float(match["epoch"]),
                    "since_main_s": float(match["since_main"]),
                    "exposed_b": match["exposed"] == "yes",
                    "process_id_i": int(match["pid"])}
    return {}


def good_file_path_list() -> list:
    """Return the sample files that the app must open.

    Inputs: none.
    Outputs: the sorted paths of the files in tests/user_tests/good.
    """
    return sorted(os.path.join(GOOD_FOLDER_STR, file_name_str)
                  for file_name_str in os.listdir(GOOD_FOLDER_STR)
                  if not file_name_str.startswith("."))


def launch_once(command_list: list, probe_path_list: list,
                timeout_s: float) -> dict:
    """Launch the app once with the startup probe and time it.

    Inputs:
        command_list: the command that starts the app.
        probe_path_list: files the app must open after the window shows.
        timeout_s: how long to wait for the app to quit by itself.
    Outputs: a dict with "launch_to_window_s" (float, or None when the
        probe line is missing), "same_process_b", "exposed_b",
        "exit_code_i" and "output_str".
    """
    environment_dict = dict(os.environ)
    environment_dict[STARTUP_PROBE_VARIABLE_STR] = "1"
    environment_dict[PROBE_FILES_VARIABLE_STR] = os.pathsep.join(
        probe_path_list)
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
    result_dict = {"launch_to_window_s": None, "same_process_b": False,
                   "exposed_b": False, "exit_code_i": process.returncode,
                   "output_str": output_str}
    if startup_dict:
        result_dict["launch_to_window_s"] = (
            startup_dict["window_shown_epoch_s"] - launch_epoch_s)
        result_dict["same_process_b"] = (
            startup_dict["process_id_i"] == process.pid)
        result_dict["exposed_b"] = startup_dict["exposed_b"]
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


def main() -> int:
    """Launch the app several times and report the startup times.

    Inputs: none (reads the command line).
    Outputs: the exit code, 0 when every check passed.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=2,
                        help="number of launches; the first is cold")
    parser.add_argument("--limit-s", type=float, default=10.0,
                        help="maximum time of the last (warm) launch")
    parser.add_argument("--timeout-s", type=float, default=180.0,
                        help="time after which a launch is killed")
    parser.add_argument("--probe-good-files", action="store_true",
                        help="open every file of tests/user_tests/good")
    parser.add_argument("command", nargs="+",
                        help="the command that starts the app")
    argument_namespace = parser.parse_args()
    probe_path_list = (good_file_path_list()
                       if argument_namespace.probe_good_files else [])
    in_actions_b = os.environ.get("GITHUB_ACTIONS") == "true"
    failed_b = False
    last_time_s = None
    for run_i in range(1, argument_namespace.runs + 1):
        kind_str = "cold" if run_i == 1 else "warm"
        result_dict = launch_once(argument_namespace.command,
                                  probe_path_list,
                                  argument_namespace.timeout_s)
        print(f"--- run {run_i} ({kind_str}) output ---")
        print(result_dict["output_str"].rstrip())
        failure_str = run_failure_str(result_dict)
        if failure_str:
            failed_b = True
            print(f"run {run_i} ({kind_str}) FAILED: {failure_str}")
            if in_actions_b:
                print(f"::error title=Startup run {run_i}::{failure_str}")
            continue
        last_time_s = result_dict["launch_to_window_s"]
        exposed_str = "" if result_dict["exposed_b"] else (
            " (window not reported as exposed)")
        summary_str = (f"run {run_i} ({kind_str}): window shown "
                       f"{last_time_s:.2f} s after launch, single "
                       f"process{exposed_str}")
        print(summary_str)
        if in_actions_b:
            print(f"::notice title=Startup time::{summary_str}")
    if last_time_s is not None and last_time_s > argument_namespace.limit_s:
        failed_b = True
        message_str = (f"last launch took {last_time_s:.2f} s, more than "
                       f"{argument_namespace.limit_s} s")
        print(message_str)
        if in_actions_b:
            print(f"::error title=Startup too slow::{message_str}")
    return 1 if failed_b else 0


if __name__ == "__main__":
    sys.exit(main())
