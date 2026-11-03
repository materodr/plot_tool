"""Check that a branch followed the flow before its pull request.

Usage:
    python tests/check_pr_ready.py --hook
    python tests/check_pr_ready.py --base BRANCH --head COMMIT
        --ci-matrix PATH

The flow is: make the change, bring the branch up to date with develop
(PCR-00060), run every test and commit the test matrix (PCR-00061), and
open the pull request only if they passed (PCR-00062).

The matrix holds a hash of the files it was built from, so comparing it
with the branch shows whether it is current. --hook is the Claude Code
PreToolUse hook of .claude/settings.json: it exits with code 2, which
blocks the command, when the command creates a pull request into develop
or main from a branch that isn't ready. --ci-matrix is for the CI job,
which also compares the tests of the committed matrix with those of its
own run. It exits with code 1 when it finds a problem.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

TESTS_FOLDER_STR = os.path.dirname(os.path.abspath(__file__))
REPOSITORY_ROOT_STR = os.path.dirname(TESTS_FOLDER_STR)
if REPOSITORY_ROOT_STR not in sys.path:
    sys.path.insert(0, REPOSITORY_ROOT_STR)

from tests.check_requirement_review import (  # noqa
    API_PULLS_PATTERN_STR, PR_CREATE_PATTERN_STR, option_value)
from tests.find_affected_requirements import run_git  # noqa

MATRIX_PATH_STR = "tests/test_matrix.md"
MAIN_BRANCH_STR = "main"
DEVELOP_BRANCH_STR = "develop"
HASH_PATTERN_STR = r"^Source hash: `([0-9a-f]+)`"
FAILED_CELL_PATTERN_STR = r"` failed\b"
TEST_CELL_PATTERN_STR = r"`([^`\s]+)` (?:passed|failed|skipped|known)"
MATRIX_COMMAND_STR = ("python tests/build_test_matrix.py --require-qt "
                      "--require-h5py --base develop --head HEAD")


def source_hash(head_str: str, folder_str: str) -> str:
    """Compute the hash of a commit's files, without the matrix itself.

    Inputs:
        head_str: the branch or commit.
        folder_str: a folder of the git checkout.
    Outputs: the hash as a hexadecimal text. Raises OSError or
        subprocess.CalledProcessError when git fails.
    """
    listing_str = run_git(folder_str, "ls-tree", "-r", head_str)
    kept_line_list = [line_str for line_str in listing_str.splitlines()
                      if not line_str.endswith("\t" + MATRIX_PATH_STR)]
    return hashlib.sha256("\n".join(kept_line_list).encode()).hexdigest()


def matrix_problems(matrix_str: str, expected_hash_str: str) -> list:
    """Check a committed matrix against the code of its branch.

    Inputs:
        matrix_str: the text of the matrix.
        expected_hash_str: the hash of the branch's files.
    Outputs: a list of problem texts, empty when the matrix is good.
    """
    problem_list = []
    hash_match = re.search(HASH_PATTERN_STR, matrix_str, re.MULTILINE)
    if not hash_match or hash_match.group(1) != expected_hash_str:
        problem_list.append(
            "tests/test_matrix.md wasn't built from the code of this branch "
            f"(PCR-00061). Commit the code, run `{MATRIX_COMMAND_STR}` and "
            "commit the matrix.")
    if re.search(FAILED_CELL_PATTERN_STR, matrix_str):
        problem_list.append(
            "tests/test_matrix.md shows failed tests (PCR-00062).")
    return problem_list


def branch_problems(base_str: str, head_str: str, folder_str: str) -> list:
    """Check a branch that is about to go into a base branch.

    Inputs:
        base_str: the branch the pull request goes into.
        head_str: the branch or commit of the pull request.
        folder_str: a folder of the git checkout.
    Outputs: a list of problem texts. Raises OSError or
        subprocess.CalledProcessError when git can't read the branch.
    """
    problem_list = []
    if base_str == DEVELOP_BRANCH_STR:
        try:
            run_git(folder_str, "merge-base", "--is-ancestor",
                    f"origin/{base_str}", head_str)
        except subprocess.CalledProcessError:
            problem_list.append(
                f"The branch doesn't contain the latest {base_str} "
                "(PCR-00060). Update it and run the tests again.")
    matrix_str = run_git(folder_str, "show", f"{head_str}:{MATRIX_PATH_STR}")
    return problem_list + matrix_problems(
        matrix_str, source_hash(head_str, folder_str))


def pull_request_target(command_str: str) -> tuple:
    """Find the base and head of a command that creates a pull request.

    Inputs:
        command_str: the whole shell command.
    Outputs: a tuple (base, head), or None for any other command. With
        no --base, gh uses the repository's default branch, main.
    """
    match = re.search(PR_CREATE_PATTERN_STR, command_str, re.MULTILINE)
    if match:
        rest_str = command_str[match.start():]
        return (option_value(r"(?:--base[= ]|-B[= ]?)", rest_str)
                or MAIN_BRANCH_STR,
                option_value(r"(?:--head[= ]|-H[= ]?)", rest_str) or "HEAD")
    match = re.search(API_PULLS_PATTERN_STR, command_str, re.MULTILINE)
    if match:
        rest_str = command_str[match.start():]
        base_match = re.search(r"\bbase=['\"]?([^\s'\"]+)", rest_str)
        head_match = re.search(r"\bhead=['\"]?([^\s'\"]+)", rest_str)
        if base_match and not re.search(
                r"(?:-X|--method)[= ]?\s*['\"]?GET\b", rest_str):
            return (base_match.group(1),
                    head_match.group(1) if head_match else "HEAD")
    return None


def run_hook() -> int:
    """Check the command that Claude Code is about to run.

    Inputs: the hook's JSON on standard input.
    Outputs: the process exit code, 2 to block the command and 0 to let
        it run. What can't be read lets the command run, because the CI
        job still checks the pull request.
    """
    try:
        hook_dict = json.load(sys.stdin)
        command_str = hook_dict["tool_input"]["command"]
    except (ValueError, KeyError, TypeError):
        return 0
    target_tuple = pull_request_target(command_str)
    if target_tuple is None or target_tuple[0] not in (MAIN_BRANCH_STR,
                                                       DEVELOP_BRANCH_STR):
        return 0
    folder_str = hook_dict.get("cwd") or os.getcwd()
    try:
        problem_list = branch_problems(target_tuple[0], target_tuple[1],
                                       folder_str)
    except (OSError, subprocess.CalledProcessError):
        return 0
    if not problem_list:
        return 0
    print("Blocked: " + " ".join(problem_list), file=sys.stderr)
    return 2


def check_in_ci(base_str: str, head_str: str, matrix_path_str: str) -> int:
    """Check a pull request's branch and matrix in the CI job.

    Inputs:
        base_str: the branch the pull request goes into.
        head_str: the commit of the pull request.
        matrix_path_str: the matrix that the CI run built.
    Outputs: the process exit code, 0 when there is no problem.
    """
    try:
        problem_list = branch_problems(base_str, head_str,
                                       REPOSITORY_ROOT_STR)
        matrix_str = run_git(REPOSITORY_ROOT_STR, "show",
                             f"{head_str}:{MATRIX_PATH_STR}")
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Result: fail, git can't read the branch: {error}")
        return 1
    with open(matrix_path_str, encoding="utf-8") as matrix_file:
        ci_matrix_str = matrix_file.read()
    if (set(re.findall(TEST_CELL_PATTERN_STR, matrix_str))
            != set(re.findall(TEST_CELL_PATTERN_STR, ci_matrix_str))):
        problem_list.append("The committed matrix lists other tests than "
                            "this run (PCR-00061).")
    for problem_str in problem_list:
        print("Result: fail. " + problem_str)
    if not problem_list:
        print("Result: pass, the branch and its matrix are ready.")
    return 1 if problem_list else 0


def main() -> int:
    """Run the check that the command-line arguments ask for.

    Inputs: command-line arguments (see module docstring).
    Outputs: the process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hook", action="store_true")
    parser.add_argument("--base", default=DEVELOP_BRANCH_STR)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--ci-matrix", default="")
    argument_namespace = parser.parse_args()
    if argument_namespace.hook:
        return run_hook()
    return check_in_ci(argument_namespace.base, argument_namespace.head,
                       argument_namespace.ci_matrix)


if __name__ == "__main__":
    sys.exit(main())
