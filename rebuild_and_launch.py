#!/usr/bin/env python3
"""Update the current branch, rebuild the app into bin/ and launch it.

Usage:
    python3 rebuild_and_launch.py

The script works on the branch checked out in the folder that holds it,
so a worktree builds into its own bin/ (COR-00007, PCR-00026). It:

1. prints the branch and warns about uncommitted changes, which are
   included in the build;
2. fast-forwards the branch to its copy on GitHub. It continues with a
   warning when GitHub cannot be reached, and stops when the branch has
   diverged, before anything is deleted;
3. installs the requirements, which downloads only what is missing or
   does not match;
4. quits the running app of this folder and clears bin/, keeping
   .gitkeep;
5. builds with build_executable.py and launches the new build.

It uses only the standard library, so any Python 3 can run it. The
build itself runs in the .venv of this folder or, in a worktree that
has none, the .venv of the main checkout.
"""

import os
import re
import shutil
import subprocess
import sys
import time

REPOSITORY_ROOT_STR = os.path.dirname(os.path.abspath(__file__))
APP_NAME_STR = "plot_tool"
KEPT_BIN_FILE_STR = ".gitkeep"
QUIT_TIMEOUT_S = 10.0
QUIT_POLL_PERIOD_S = 0.2


class RebuildError(Exception):
    """A step failed in a way that must stop the script."""


def run_git(root_folder_str: str, argument_list: list) -> tuple:
    """Run a git command and capture its result.

    Inputs:
        root_folder_str: the folder to run git in.
        argument_list: the arguments that follow ``git``.
    Outputs: a tuple (succeeded_b, output_str), where output_str holds
        the standard output, or the error text when the command failed.
    """
    result = subprocess.run(["git", *argument_list], cwd=root_folder_str,
                            capture_output=True, text=True)
    succeeded_b = result.returncode == 0
    output_str = result.stdout if succeeded_b else result.stderr
    return succeeded_b, output_str.strip()


def report_branch(root_folder_str: str) -> None:
    """Print the current branch and warn about uncommitted changes.

    Inputs:
        root_folder_str: the checkout to report on.
    Outputs: none. Raises RebuildError outside a git checkout.
    """
    succeeded_b, branch_str = run_git(
        root_folder_str, ["rev-parse", "--abbrev-ref", "HEAD"])
    if not succeeded_b:
        raise RebuildError(f"Could not read the branch: {branch_str}")
    print(f"Branch: {branch_str}")
    _, changes_str = run_git(root_folder_str, ["status", "--porcelain"])
    if changes_str:
        print("Warning: uncommitted changes are included in this build.")


def update_branch(root_folder_str: str) -> None:
    """Fast-forward the current branch to its copy on GitHub.

    Inputs:
        root_folder_str: the checkout to update.
    Outputs: none. A branch that has no copy on GitHub is built as it
        is, and so is any branch when GitHub cannot be reached. Raises
        RebuildError when the update is not a simple fast-forward.
    """
    has_upstream_b, _ = run_git(
        root_folder_str, ["rev-parse", "--abbrev-ref", "@{upstream}"])
    if not has_upstream_b:
        print("The branch has no copy on GitHub; building it as it is.")
        return
    fetched_b, fetch_error_str = run_git(root_folder_str, ["fetch"])
    if not fetched_b:
        print(f"Warning: could not reach GitHub: {fetch_error_str}")
        print("Building the branch as it is.")
        return
    merged_b, merge_error_str = run_git(
        root_folder_str, ["merge", "--ff-only", "@{upstream}"])
    if not merged_b:
        raise RebuildError(
            "The branch cannot be fast-forwarded to its copy on GitHub. "
            f"Nothing was deleted.\n{merge_error_str}")


def virtual_environment_python_path(root_folder_str: str) -> str:
    """Find the Python of the project's virtual environment.

    Inputs:
        root_folder_str: the checkout being built.
    Outputs: the path of that checkout's .venv Python or, when it has
        none, of the main checkout's. Raises RebuildError when neither
        exists.
    """
    relative_path_tuple = (
        (".venv", "Scripts", "python.exe") if sys.platform == "win32"
        else (".venv", "bin", "python"))
    _, common_folder_str = run_git(
        root_folder_str,
        ["rev-parse", "--path-format=absolute", "--git-common-dir"])
    main_checkout_str = os.path.dirname(common_folder_str)
    for checkout_str in (root_folder_str, main_checkout_str):
        python_path_str = os.path.join(checkout_str, *relative_path_tuple)
        if os.path.exists(python_path_str):
            return python_path_str
    raise RebuildError(
        f"No .venv found in {root_folder_str} or {main_checkout_str}.")


def install_requirements(python_path_str: str,
                         root_folder_str: str) -> None:
    """Install what is missing from the app's and the build's requirements.

    Inputs:
        python_path_str: the Python of the virtual environment.
        root_folder_str: the checkout that holds the requirement files.
    Outputs: none. Raises CalledProcessError when pip fails.
    """
    subprocess.run(
        [python_path_str, "-m", "pip", "install", "--quiet",
         "--disable-pip-version-check",
         "-r", "requirements.txt", "-r", "requirements-build.txt"],
        cwd=root_folder_str, check=True)


def running_app_pattern(bin_folder_str: str) -> str:
    """Return the pattern that finds the app started from a bin folder.

    Inputs:
        bin_folder_str: the absolute path of the bin folder.
    Outputs: a regular expression for pgrep, anchored at the start of
        the command line, so that an app built in another worktree and
        a shell command that only mentions this path do not match.
    """
    app_path_str = os.path.join(bin_folder_str, APP_NAME_STR)
    return (f"^{re.escape(app_path_str)}"
            f"(\\.app/Contents/MacOS)?/{APP_NAME_STR}")


def quit_running_app(bin_folder_str: str) -> None:
    """Quit the app started from a bin folder and wait until it is gone.

    Inputs:
        bin_folder_str: the absolute path of the bin folder.
    Outputs: none. Raises RebuildError when the app does not quit.
        Windows has no pgrep; there, an app left running makes the
        clearing of bin/ fail with an error instead.
    """
    if sys.platform == "win32":
        return
    pattern_str = running_app_pattern(bin_folder_str)
    subprocess.run(["pkill", "-f", pattern_str], check=False)
    deadline_s = time.monotonic() + QUIT_TIMEOUT_S
    while time.monotonic() < deadline_s:
        search = subprocess.run(["pgrep", "-f", pattern_str],
                                capture_output=True, check=False)
        if search.returncode != 0:
            return
        time.sleep(QUIT_POLL_PERIOD_S)
    raise RebuildError(
        "The running app did not quit. Nothing was deleted; "
        "close it and run this again.")


def clear_bin_folder(bin_folder_str: str) -> None:
    """Delete everything in a bin folder except the tracked .gitkeep.

    Inputs:
        bin_folder_str: the absolute path of the bin folder.
    Outputs: none.
    """
    # COR-00007: bin/ holds only build outputs, which are not committed.
    for entry in os.scandir(bin_folder_str):
        if entry.name == KEPT_BIN_FILE_STR:
            continue
        if entry.is_dir(follow_symlinks=False):
            shutil.rmtree(entry.path)
        else:
            os.remove(entry.path)


def launch_app(bin_folder_str: str) -> None:
    """Start the app that was just built.

    Inputs:
        bin_folder_str: the absolute path of the bin folder.
    Outputs: none. The app keeps running after this script ends.
    """
    if sys.platform == "darwin":
        app_path_str = os.path.join(bin_folder_str, APP_NAME_STR + ".app")
        subprocess.run(["open", app_path_str], check=True)
        return
    executable_str = APP_NAME_STR + (
        ".exe" if sys.platform == "win32" else "")
    app_path_str = os.path.join(bin_folder_str, APP_NAME_STR, executable_str)
    subprocess.Popen([app_path_str])


def main() -> int:
    """Run all the steps in order and stop at the first failure.

    Inputs: none.
    Outputs: the exit code, 0 on success and 1 on failure.
    """
    bin_folder_str = os.path.join(REPOSITORY_ROOT_STR, "bin")
    try:
        report_branch(REPOSITORY_ROOT_STR)
        update_branch(REPOSITORY_ROOT_STR)
        python_path_str = virtual_environment_python_path(REPOSITORY_ROOT_STR)
        print("Checking the requirements...")
        install_requirements(python_path_str, REPOSITORY_ROOT_STR)
        quit_running_app(bin_folder_str)
        clear_bin_folder(bin_folder_str)
        print("Building the app...")
        subprocess.run([python_path_str, "build_executable.py"],
                       cwd=REPOSITORY_ROOT_STR, check=True)
        launch_app(bin_folder_str)
    except (RebuildError, subprocess.CalledProcessError, OSError) as error:
        print(f"Stopped: {error}", file=sys.stderr)
        return 1
    print("The app is running.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
