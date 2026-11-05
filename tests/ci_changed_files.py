"""Decide whether a pull request must run every test (PCR-00078).

Usage:
    python tests/ci_changed_files.py --base BRANCH --head COMMIT
        [--github-output PATH]

A pull request runs every test when its branch changes a file of the
list of PCR-00078: a file under src/, tests/ (the sample files of
tests/user_tests included), bin/ or .github/workflows/, a build script,
a requirements*.txt file, or the HLFR or LLFR file. A pull request from
develop to main always runs every test (PCR-00058). Otherwise the tests
are skipped (PCR-00079), and the requirement checks still run
(PCR-00080).

The script prints its decision and the changed files. With
--github-output it also appends `full_suite=true` or `full_suite=false`
to that file, the $GITHUB_OUTPUT of a GitHub Actions step. When git
can't tell the changed files, or the branch changes no file, it decides
to run every test, so that a doubt never skips a test.

It uses only the standard library, so any Python 3 can run it.
"""

import argparse
import fnmatch
import os
import subprocess
import sys

TESTS_FOLDER_STR = os.path.dirname(os.path.abspath(__file__))
REPOSITORY_ROOT_STR = os.path.dirname(TESTS_FOLDER_STR)
if REPOSITORY_ROOT_STR not in sys.path:
    sys.path.insert(0, REPOSITORY_ROOT_STR)

from tests.find_affected_requirements import (  # noqa
    HIGH_LEVEL_PATH_STR, LOW_LEVEL_PATH_STR, run_git)

MAIN_BRANCH_STR = "main"
# PCR-00078: the folders, files and file patterns whose change runs every
# test. The sample files are under tests/user_tests.
FULL_SUITE_FOLDER_TUPLE = ("src/", "tests/", "bin/", ".github/workflows/")
FULL_SUITE_FILE_TUPLE = ("build_executable.py", "rebuild_and_launch.py",
                         HIGH_LEVEL_PATH_STR, LOW_LEVEL_PATH_STR)
FULL_SUITE_PATTERN_TUPLE = ("requirements*.txt",)


def path_needs_full_suite(path_str: str) -> bool:
    """Tell whether a change to one file runs every test (PCR-00078).

    Inputs:
        path_str: the path of the file, relative to the repository root,
            with "/" between folders, as git prints it.
    Outputs: True when the file is in the list of PCR-00078.
    """
    return (path_str.startswith(FULL_SUITE_FOLDER_TUPLE)
            or path_str in FULL_SUITE_FILE_TUPLE
            or any(fnmatch.fnmatchcase(path_str, pattern_str)
                   for pattern_str in FULL_SUITE_PATTERN_TUPLE))


def needs_full_suite(changed_path_list: list, base_str: str) -> bool:
    """Tell whether a pull request runs every test.

    Inputs:
        changed_path_list: the files that the branch changes, added and
            deleted files included.
        base_str: the branch the pull request goes into.
    Outputs: True into main (PCR-00058), when no file changed, or when a
        file is in the list of PCR-00078; False when every file is
        outside it (PCR-00079).
    """
    if base_str == MAIN_BRANCH_STR or not changed_path_list:
        return True
    return any(path_needs_full_suite(path_str)
               for path_str in changed_path_list)


def changed_paths(base_str: str, head_str: str, folder_str: str) -> list:
    """List the files that a branch changes since it left its base.

    Inputs:
        base_str: the branch the pull request goes into; its copy
            origin/<base_str> is compared.
        head_str: the branch or commit of the pull request.
        folder_str: a folder of the git checkout.
    Outputs: the paths of the changed files, in git's order. A renamed
        file gives both its old and its new path. Raises OSError or
        subprocess.CalledProcessError when git fails.
    """
    diff_str = run_git(folder_str, "diff", "--name-only", "--no-renames",
                       f"origin/{base_str}...{head_str}")
    return [line_str for line_str in diff_str.splitlines() if line_str]


def branch_needs_full_suite(base_str: str, head_str: str,
                            folder_str: str) -> bool:
    """Tell whether the pull request of a branch runs every test.

    Inputs:
        base_str: the branch the pull request goes into.
        head_str: the branch or commit of the pull request.
        folder_str: a folder of the git checkout.
    Outputs: the decision of needs_full_suite, or True when git can't
        list the changed files.
    """
    if base_str == MAIN_BRANCH_STR:
        return True
    try:
        changed_path_list = changed_paths(base_str, head_str, folder_str)
    except (OSError, subprocess.CalledProcessError):
        return True
    return needs_full_suite(changed_path_list, base_str)


def main() -> int:
    """Print the decision for a pull request, and write it for CI.

    Inputs: command-line arguments (see module docstring).
    Outputs: the process exit code, always 0.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--github-output", default="")
    argument_namespace = parser.parse_args()
    base_str = argument_namespace.base
    try:
        changed_path_list = changed_paths(base_str, argument_namespace.head,
                                          REPOSITORY_ROOT_STR)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"git can't list the changed files: {error}")
        changed_path_list = []
    full_suite_b = needs_full_suite(changed_path_list, base_str)
    for path_str in changed_path_list:
        mark_str = "runs tests" if path_needs_full_suite(path_str) else "-"
        print(f"{mark_str:>10}  {path_str}")
    if full_suite_b:
        print("Result: every test runs (PCR-00057, PCR-00058, PCR-00078).")
    else:
        print("Result: the tests are skipped, because every changed file is "
              "outside the list of PCR-00078 (PCR-00079). The requirement "
              "checks still run (PCR-00080).")
    if argument_namespace.github_output:
        with open(argument_namespace.github_output, "a",
                  encoding="utf-8") as output_file:
            output_file.write(
                f"full_suite={'true' if full_suite_b else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
