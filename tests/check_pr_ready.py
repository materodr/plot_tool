"""Check that a branch followed the flow before its pull request.

Usage:
    python tests/check_pr_ready.py --hook
    python tests/check_pr_ready.py --base BRANCH --head COMMIT
        --ci-matrix PATH
    python tests/check_pr_ready.py --base BRANCH --head COMMIT
        --body-file PATH

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

Two justified exceptions show as `Fail*` in the matrix, each with its
justification, and are listed in its "Fail* (PCR-00070)" section:
- a test that couldn't run because the environment lacked PyQt6 or h5py
  (PCR-00063). It counts as passed (PCR-00064);
- an HLFR of tests/not_implemented.txt (PCR-00065, PCR-00066). It is
  accepted into develop and refused into main (PCR-00069).
A pull request into develop whose changed files are all outside the
list of PCR-00078 runs no test (PCR-00079) and keeps the matrix of
develop (PCR-00081), so the checks that the matrix was built from the
branch's code and lists the tests of the CI run are skipped for it;
the other checks still apply.
--body-file is for the fail-star-section CI job: when the committed
matrix has a `Fail*`, the pull request description must start with the
same section, listing every `Fail*` with its justification (PCR-00070).

It uses only the standard library, so any Python 3 can run it.
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
from tests.ci_changed_files import branch_needs_full_suite  # noqa
from tests.find_affected_requirements import run_git  # noqa

MATRIX_PATH_STR = "tests/test_matrix.md"
NOT_IMPLEMENTED_LIST_PATH_STR = "tests/not_implemented.txt"
MAIN_BRANCH_STR = "main"
DEVELOP_BRANCH_STR = "develop"
HASH_PATTERN_STR = r"^Source hash: `([0-9a-f]+)`"
FAILED_CELL_PATTERN_STR = r"` failed\b"
TEST_CELL_PATTERN_STR = (r"`([^`\s]+)` "
                         r"(?:passed|failed|skipped|known|Fail\*)")
MATRIX_COMMAND_STR = ("python tests/build_test_matrix.py --require-qt "
                      "--require-h5py --base develop --head HEAD")
# PCR-00063 to PCR-00070: the justified exceptions to the test rules.
FAIL_STAR_STR = "Fail*"
FAIL_STAR_HEADING_STR = "Fail* (PCR-00070)"
HEADING_LINE_PATTERN_STR = r"^#{1,6}[ \t]+(.*?)[ \t#]*$"
ENVIRONMENT_ENTRY_START_STR = "Environment, "
NOT_IMPLEMENTED_ENTRY_START_STR = "Not implemented, "


def listed_hlfr_ids(list_text_str: str) -> list:
    """Read the HLFR IDs of a tests/not_implemented.txt text.

    Inputs:
        list_text_str: the text of the list (PCR-00066).
    Outputs: the HLFR IDs that start its lines that are neither blank
        nor comments, in their order.
    """
    id_list = []
    for line_str in list_text_str.splitlines():
        id_match = re.match(r"\s*(HLFR-\d{5})\b", line_str)
        if id_match and not line_str.strip().startswith("#"):
            id_list.append(id_match.group(1))
    return id_list


def fail_star_entries(text_str: str) -> list:
    """Read the entries of the Fail* section of a matrix or description.

    Inputs:
        text_str: the text of a test matrix or of a pull request
            description.
    Outputs: the list of the entries of the first section headed
        FAIL_STAR_HEADING_STR, each one the text of a "- " line without
        its "- " and its surrounding spaces, in their order. It is empty
        when there is no such section (PCR-00070).
    """
    entry_list = []
    in_section_b = False
    for line_str in text_str.splitlines():
        heading_match = re.match(HEADING_LINE_PATTERN_STR, line_str.strip())
        if heading_match:
            if in_section_b:
                break
            in_section_b = heading_match.group(1) == FAIL_STAR_HEADING_STR
            continue
        if not in_section_b:
            continue
        if line_str.startswith("|"):
            break
        if line_str.strip().startswith("- "):
            entry_list.append(line_str.strip()[2:].strip())
    return entry_list


def starts_with_fail_star_section(body_str: str) -> bool:
    """Tell whether a description starts with the Fail* section.

    Inputs:
        body_str: the text of the pull request description.
    Outputs: True when its first line that isn't blank is a heading with
        the text FAIL_STAR_HEADING_STR (PCR-00070).
    """
    for line_str in body_str.splitlines():
        if not line_str.strip():
            continue
        heading_match = re.match(HEADING_LINE_PATTERN_STR, line_str.strip())
        return bool(heading_match
                    and heading_match.group(1) == FAIL_STAR_HEADING_STR)
    return False


def description_problems(body_str: str, matrix_str: str) -> list:
    """Check that a description lists every Fail* of a matrix first.

    Inputs:
        body_str: the text of the pull request description.
        matrix_str: the text of the matrix committed on the branch.
    Outputs: a list of problem texts, empty when the matrix has no
        Fail* or when the description starts with the Fail* section and
        that section holds every entry of the matrix's section, with its
        justification (PCR-00070).
    """
    matrix_entry_list = fail_star_entries(matrix_str)
    if not matrix_entry_list:
        return []
    if not starts_with_fail_star_section(body_str):
        return [f"The test matrix shows {len(matrix_entry_list)} Fail*, so "
                "the description must start with the section "
                f"\"## {FAIL_STAR_HEADING_STR}\" (PCR-00070). Copy it from "
                "tests/test_matrix.md."]
    body_entry_list = fail_star_entries(body_str)
    return [f"The section \"## {FAIL_STAR_HEADING_STR}\" of the description "
            f"is missing this Fail* of the matrix: \"- {entry_str}\" "
            "(PCR-00070)."
            for entry_str in matrix_entry_list
            if entry_str not in body_entry_list]


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


def matrix_problems(matrix_str: str, expected_hash_str: str,
                    base_str: str = DEVELOP_BRANCH_STR,
                    hash_check_b: bool = True) -> list:
    """Check a committed matrix against the code of its branch.

    Inputs:
        matrix_str: the text of the matrix.
        expected_hash_str: the hash of the branch's files.
        base_str: the branch the pull request goes into.
        hash_check_b: False for a pull request that runs no test
            (PCR-00079), whose matrix is the one of develop (PCR-00081),
            so that its hash isn't checked.
    Outputs: a list of problem texts, empty when the matrix is good. A
        test shown as Fail* for an environment limit isn't a failed test
        (PCR-00064). An HLFR shown as Fail* because it isn't implemented
        yet is a problem only into main (PCR-00069).
    """
    problem_list = []
    hash_match = re.search(HASH_PATTERN_STR, matrix_str, re.MULTILINE)
    if hash_check_b and (not hash_match
                         or hash_match.group(1) != expected_hash_str):
        problem_list.append(
            "tests/test_matrix.md wasn't built from the code of this branch "
            f"(PCR-00061). Commit the code, run `{MATRIX_COMMAND_STR}` and "
            "commit the matrix.")
    if re.search(FAILED_CELL_PATTERN_STR, matrix_str):
        problem_list.append(
            "tests/test_matrix.md shows failed tests (PCR-00062).")
    if base_str == MAIN_BRANCH_STR:
        problem_list.extend(
            f"tests/test_matrix.md shows a Fail* for an HLFR that isn't "
            f"implemented yet, which can't go into main (PCR-00069): "
            f"\"{entry_str}\"."
            for entry_str in fail_star_entries(matrix_str)
            if entry_str.startswith(NOT_IMPLEMENTED_ENTRY_START_STR))
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
    if base_str == MAIN_BRANCH_STR:
        # PCR-00069: the list itself, so that a matrix edited by hand
        # can't hide an HLFR that isn't implemented yet.
        try:
            list_text_str = run_git(
                folder_str, "show",
                f"{head_str}:{NOT_IMPLEMENTED_LIST_PATH_STR}")
        except subprocess.CalledProcessError:
            list_text_str = ""
        listed_id_list = listed_hlfr_ids(list_text_str)
        if listed_id_list:
            problem_list.append(
                f"{NOT_IMPLEMENTED_LIST_PATH_STR} lists HLFRs that aren't "
                "implemented yet, which can't go into main (PCR-00069): "
                + ", ".join(listed_id_list) + ".")
    matrix_str = run_git(folder_str, "show", f"{head_str}:{MATRIX_PATH_STR}")
    # PCR-00079, PCR-00081: a branch that runs no test keeps the matrix
    # of develop, so its hash isn't the one of the branch's files.
    full_suite_b = branch_needs_full_suite(base_str, head_str, folder_str)
    return problem_list + matrix_problems(
        matrix_str, source_hash(head_str, folder_str), base_str,
        full_suite_b)


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
    Outputs: the process exit code, 0 when there is no problem. When
        the pull request runs no test (PCR-00079), there is no matrix of
        the run to compare, and the other checks still apply.
    """
    try:
        problem_list = branch_problems(base_str, head_str,
                                       REPOSITORY_ROOT_STR)
        matrix_str = run_git(REPOSITORY_ROOT_STR, "show",
                             f"{head_str}:{MATRIX_PATH_STR}")
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Result: fail, git can't read the branch: {error}")
        return 1
    if branch_needs_full_suite(base_str, head_str, REPOSITORY_ROOT_STR):
        with open(matrix_path_str, encoding="utf-8") as matrix_file:
            ci_matrix_str = matrix_file.read()
        if (set(re.findall(TEST_CELL_PATTERN_STR, matrix_str))
                != set(re.findall(TEST_CELL_PATTERN_STR, ci_matrix_str))):
            problem_list.append("The committed matrix lists other tests "
                                "than this run (PCR-00061).")
    else:
        print("The tests of this pull request are skipped (PCR-00079), so "
              "the matrix of develop is kept (PCR-00081).")
    for problem_str in problem_list:
        print("Result: fail. " + problem_str)
    if not problem_list:
        print("Result: pass, the branch and its matrix are ready.")
    return 1 if problem_list else 0


def check_description(base_str: str, head_str: str,
                      body_path_str: str) -> int:
    """Check a saved pull request description, for the CI job.

    Inputs:
        base_str: the branch the pull request goes into.
        head_str: the commit of the pull request.
        body_path_str: the path of the saved description.
    Outputs: the process exit code, 0 when the description lists every
        Fail* of the committed matrix at its top, or the matrix has none
        (PCR-00070).
    """
    try:
        matrix_str = run_git(REPOSITORY_ROOT_STR, "show",
                             f"{head_str}:{MATRIX_PATH_STR}")
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Result: fail, git can't read the matrix of {head_str} "
              f"(into {base_str}): {error}")
        return 1
    with open(body_path_str, encoding="utf-8") as body_file:
        body_str = body_file.read()
    problem_list = description_problems(body_str, matrix_str)
    for problem_str in problem_list:
        print("Result: fail. " + problem_str)
    if not problem_list:
        entry_count_i = len(fail_star_entries(matrix_str))
        print("Result: pass, " + (
            f"the description lists the {entry_count_i} Fail* of the "
            "matrix at its top." if entry_count_i
            else "the matrix shows no Fail*."))
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
    parser.add_argument("--body-file", default="")
    argument_namespace = parser.parse_args()
    if argument_namespace.hook:
        return run_hook()
    if argument_namespace.body_file:
        return check_description(argument_namespace.base,
                                 argument_namespace.head,
                                 argument_namespace.body_file)
    return check_in_ci(argument_namespace.base, argument_namespace.head,
                       argument_namespace.ci_matrix)


if __name__ == "__main__":
    sys.exit(main())
