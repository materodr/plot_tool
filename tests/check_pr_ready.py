"""Check that a branch followed the flow before its pull request.

Usage:
    python tests/check_pr_ready.py --hook
    python tests/check_pr_ready.py --base BRANCH --head COMMIT
        --ci-matrix PATH [--body-file PATH]
    python tests/check_pr_ready.py --base BRANCH --head COMMIT
        --body-file PATH

The flow is: make the change, run locally the tests deemed necessary
before each push (PCR-00082), bring the branch up to date with
develop (PCR-00060), and open the pull request. CI is the only builder
of the test matrix: it builds it on every pull request that runs the
tests and posts it on the pull request. After a release, an agent opens
one pull request into main and one into develop, from test matrix
branches, that put the matrix of the release run in
tests/test_matrix.md (PCR-00061, PCR-00085). Any other branch into
develop leaves tests/test_matrix.md as develop has it (PCR-00081).

--hook is the Claude Code PreToolUse hook of .claude/settings.json: it
exits with code 2, which blocks the command, when the command creates a
pull request into develop or main from a branch that isn't ready.
The hook also checks the Fail* section of a description given in a
file (--body-file, -F or body=@).
--ci-matrix is for the `tests` CI job: it checks the branch, and the
matrix that this run built from the branch's code (PCR-00062,
PCR-00069). With --body-file too, it checks only that the description
lists the environment Fail* of that run, which is rare and happens only
into develop (PCR-00072), so that editing a description almost never
needs the tests to run again. A pull request that skips the tests
(PCR-00079, PCR-00083) has no matrix of its own, so that part is
skipped.
--green-light with --body-file is for the green-light CI job: into
develop, the description must end its record of the review with a line
`Green light: <SHA>` that names the head commit, so that any commit
after the green light fails the check (PCR-00105, PCR-00111, PCR-00112).
--body-file alone is for the fail-star-section CI job, which runs
without the tests and again on each edit of the description: the
description must start with the Fail* section, with an entry for each
HLFR of tests/not_implemented.txt and for each environment Fail* of
the matrix that the `tests` job posted for the head commit
(--run-matrix), or the single entry `none` (PCR-00070). It exits with
code 1 when it finds a problem.

Two justified exceptions show as `Fail*` in the matrix, each with its
justification, and are listed in the "Fail* (PCR-00070)" section:
- a test that couldn't run because the environment lacked PyQt6 or h5py
  (PCR-00063). It counts as passed into develop (PCR-00064);
- an HLFR of tests/not_implemented.txt (PCR-00065, PCR-00066).
A pull request into develop may carry both; one into main carries none
(PCR-00069).

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
    API_PULLS_PATTERN_STR, PR_CREATE_PATTERN_STR, option_value,
    read_text_file)
from tests.ci_changed_files import (  # noqa
    branch_needs_full_suite, is_test_matrix_branch)
from tests.find_affected_requirements import run_git  # noqa

MATRIX_PATH_STR = "tests/test_matrix.md"
NOT_IMPLEMENTED_LIST_PATH_STR = "tests/not_implemented.txt"
MAIN_BRANCH_STR = "main"
DEVELOP_BRANCH_STR = "develop"
FAILED_CELL_PATTERN_STR = r"` failed\b"
# PCR-00063 to PCR-00070: the justified exceptions to the test rules.
FAIL_STAR_STR = "Fail*"
FAIL_STAR_HEADING_STR = "Fail* (PCR-00070)"
NO_FAIL_STAR_ENTRY_STR = "none"
HEADING_LINE_PATTERN_STR = r"^#{1,6}[ \t]+(.*?)[ \t#]*$"
ENVIRONMENT_ENTRY_START_STR = "Environment, "
NOT_IMPLEMENTED_ENTRY_START_STR = "Not implemented, "
NOT_IMPLEMENTED_TEXT_STR = "the implementation has not been done yet."
LISTED_LINE_PATTERN_STR = r"^\s*(HLFR-\d{5})\b\s*(.*?)\s*$"
NO_FAIL_STAR_SECTION_STR = f"## {FAIL_STAR_HEADING_STR}\n\n- none\n"
# PCR-00111, PCR-00112: the line of the description that records the
# commit the reviewer gave its green light to.
GREEN_LIGHT_PATTERN_STR = r"^Green light:\s*`?([0-9a-f]{40})`?\s*$"


def listed_explanations(list_text_str: str) -> dict:
    """Read the HLFRs of a tests/not_implemented.txt text.

    Inputs:
        list_text_str: the text of the list (PCR-00066).
    Outputs: a dict from each HLFR ID that starts a line that is
        neither blank nor a comment to the explanation after it, in the
        order of the lines.
    """
    explanation_dict = {}
    for line_str in list_text_str.splitlines():
        id_match = re.match(LISTED_LINE_PATTERN_STR, line_str)
        if id_match and not line_str.strip().startswith("#"):
            explanation_dict[id_match.group(1)] = id_match.group(2)
    return explanation_dict


def listed_hlfr_ids(list_text_str: str) -> list:
    """Read the HLFR IDs of a tests/not_implemented.txt text.

    Inputs:
        list_text_str: the text of the list (PCR-00066).
    Outputs: the HLFR IDs that start its lines that are neither blank
        nor comments, in their order.
    """
    return list(listed_explanations(list_text_str))


def not_implemented_entry(hlfr_id_str: str, explanation_str: str) -> str:
    """Write the Fail* entry of an HLFR that isn't implemented yet.

    Inputs:
        hlfr_id_str: the HLFR ID (PCR-00065).
        explanation_str: its explanation in tests/not_implemented.txt.
    Outputs: the text of the entry, without its "- ", as
        tests/build_test_matrix.py writes it (PCR-00070).
    """
    return (f"{NOT_IMPLEMENTED_ENTRY_START_STR}{hlfr_id_str}: "
            f"{FAIL_STAR_STR} in column 4, {NOT_IMPLEMENTED_TEXT_STR} "
            f"{explanation_str}")


def not_implemented_entries(explanation_dict: dict) -> list:
    """Write the Fail* entries of every HLFR not implemented yet.

    Inputs:
        explanation_dict: the HLFRs of listed_explanations.
    Outputs: the entry texts, sorted by HLFR ID (PCR-00065, PCR-00070).
    """
    return [not_implemented_entry(hlfr_id_str, explanation_dict[hlfr_id_str])
            for hlfr_id_str in sorted(explanation_dict)]


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


def description_problems(body_str: str, expected_entry_list: list,
                         base_str: str = DEVELOP_BRANCH_STR) -> list:
    """Check the Fail* section at the top of a description.

    Inputs:
        body_str: the text of the pull request description.
        expected_entry_list: the entries the section must hold, for
            example those of not_implemented_entries or of the matrix
            built by CI.
        base_str: the branch the pull request goes into.
    Outputs: a list of problem texts, empty when the description starts
        with the Fail* section (PCR-00070), the section holds every
        expected entry, or only the entry `none` when none is expected,
        and, into main, no Fail* at all (PCR-00069).
    """
    if not starts_with_fail_star_section(body_str):
        return [f"The description must start with the section \"## "
                f"{FAIL_STAR_HEADING_STR}\" (PCR-00070). With no Fail*, "
                f"write it with the single entry \"- "
                f"{NO_FAIL_STAR_ENTRY_STR}\":\n\n{NO_FAIL_STAR_SECTION_STR}"]
    body_entry_list = fail_star_entries(body_str)
    exception_list = [entry_str for entry_str in body_entry_list
                      if entry_str != NO_FAIL_STAR_ENTRY_STR]
    problem_list = []
    if not body_entry_list:
        problem_list.append(
            f"The section \"## {FAIL_STAR_HEADING_STR}\" has no entry. "
            f"With no Fail*, write \"- {NO_FAIL_STAR_ENTRY_STR}\" "
            "(PCR-00070).")
    if exception_list and len(exception_list) < len(body_entry_list):
        problem_list.append(
            f"The section \"## {FAIL_STAR_HEADING_STR}\" holds \"- "
            f"{NO_FAIL_STAR_ENTRY_STR}\" and other entries; keep only one "
            "of the two (PCR-00070).")
    problem_list.extend(
        f"The section \"## {FAIL_STAR_HEADING_STR}\" of the description "
        f"is missing this Fail*: \"- {entry_str}\" (PCR-00070)."
        for entry_str in expected_entry_list
        if entry_str not in body_entry_list)
    problem_list.extend(
        f"The section \"## {FAIL_STAR_HEADING_STR}\" lists an HLFR that "
        f"isn't in {NOT_IMPLEMENTED_LIST_PATH_STR}: \"- {entry_str}\" "
        "(PCR-00065)."
        for entry_str in exception_list
        if entry_str.startswith(NOT_IMPLEMENTED_ENTRY_START_STR)
        and entry_str not in expected_entry_list)
    if base_str == MAIN_BRANCH_STR and exception_list:
        problem_list.append(
            "A pull request into main can't carry a Fail* of any kind "
            f"(PCR-00069), but its section lists {len(exception_list)}.")
    return problem_list


def green_light_problems(body_str: str, head_sha_str: str,
                         base_str: str = DEVELOP_BRANCH_STR,
                         head_branch_str: str = "") -> list:
    """Check that a pull request's head is the commit of its green light.

    Inputs:
        body_str: the text of the pull request description.
        head_sha_str: the full SHA of the head commit of the pull
            request.
        base_str: the branch the pull request goes into.
        head_branch_str: the name of the branch of the pull request.
    Outputs: a list of problem texts, empty into a branch other than
        develop, for a test matrix branch (PCR-00087), or when the last
        line `Green light: <SHA>` of the description names the head
        commit (PCR-00105, PCR-00111, PCR-00112).
    """
    if base_str != DEVELOP_BRANCH_STR or is_test_matrix_branch(
            head_branch_str):
        return []
    sha_list = re.findall(GREEN_LIGHT_PATTERN_STR, body_str, re.MULTILINE)
    if not sha_list:
        return ["The description has no line `Green light: <commit SHA>`: "
                "the reviewer records its green light there, with the head "
                "commit it approved (PCR-00111)."]
    if sha_list[-1] != head_sha_str:
        return [f"The branch changed after the green light of commit "
                f"{sha_list[-1]}: the head is now {head_sha_str}. After the "
                "green light nobody changes the branch (PCR-00105), so the "
                "work goes back to the implementer's loop (PCR-00106, "
                "PCR-00110)."]
    return []


def source_hash(head_str: str, folder_str: str) -> str:
    """Compute the hash of a commit's files, without the matrix itself.

    Inputs:
        head_str: the branch or commit.
        folder_str: a folder of the git checkout.
    Outputs: the hash as a hexadecimal text, which the matrix shows so
        that a reader can tell which code it was built from. Raises
        OSError or subprocess.CalledProcessError when git fails.
    """
    listing_str = run_git(folder_str, "ls-tree", "-r", head_str)
    kept_line_list = [line_str for line_str in listing_str.splitlines()
                      if not line_str.endswith("\t" + MATRIX_PATH_STR)]
    return hashlib.sha256("\n".join(kept_line_list).encode()).hexdigest()


def run_matrix_problems(matrix_str: str,
                        base_str: str = DEVELOP_BRANCH_STR) -> list:
    """Check the matrix that the CI run built from the branch's code.

    Inputs:
        matrix_str: the text of the matrix of the run (PCR-00061).
        base_str: the branch the pull request goes into.
    Outputs: a list of problem texts, empty when no test failed
        (PCR-00062) and, into main, the matrix shows no Fail* of any
        kind (PCR-00069). A test shown as Fail* for an environment limit
        isn't a failed test into develop (PCR-00064).
    """
    problem_list = []
    if re.search(FAILED_CELL_PATTERN_STR, matrix_str):
        problem_list.append("The test matrix of this run shows failed tests "
                            "(PCR-00062).")
    if base_str == MAIN_BRANCH_STR:
        problem_list.extend(
            "The test matrix of this run shows a Fail*, which can't go "
            f"into main (PCR-00069): \"{entry_str}\"."
            for entry_str in fail_star_entries(matrix_str))
    return problem_list


def branch_problems(base_str: str, head_str: str, folder_str: str,
                    head_branch_str: str = "") -> list:
    """Check a branch that is about to go into a base branch.

    Inputs:
        base_str: the branch the pull request goes into.
        head_str: the branch or commit of the pull request.
        folder_str: a folder of the git checkout.
        head_branch_str: the name of the branch of the pull request, if
            known, to tell a test matrix branch (PCR-00002).
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
        changed_path_list = run_git(
            folder_str, "diff", "--name-only", "--no-renames",
            f"origin/{base_str}...{head_str}").split()
        if is_test_matrix_branch(head_branch_str):
            # PCR-00085: the matrix pull request into develop changes
            # only the matrix.
            if any(path_str != MATRIX_PATH_STR
                   for path_str in changed_path_list):
                problem_list.append(
                    f"A test matrix branch changes only {MATRIX_PATH_STR} "
                    "(PCR-00085), but this one changes other files too.")
        elif MATRIX_PATH_STR in changed_path_list:
            # PCR-00081: only the matrix pull requests change the matrix.
            problem_list.append(
                f"The branch changes {MATRIX_PATH_STR}, which only the "
                "matrix pull requests of a release change (PCR-00061, "
                "PCR-00081, PCR-00085). Put it back as develop has it: "
                f"`git checkout origin/develop -- {MATRIX_PATH_STR}`, then "
                "commit.")
    if base_str == MAIN_BRANCH_STR:
        # PCR-00069: the list itself, so that no HLFR that isn't
        # implemented yet goes into main.
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
    return problem_list


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


def command_body(command_str: str, folder_str: str) -> str:
    """Read the description of a command that creates a pull request.

    Inputs:
        command_str: the whole shell command.
        folder_str: the folder the command runs in.
    Outputs: the text of the file given with --body-file, -F or body=@,
        or an empty text when the description isn't in a file.
    """
    path_str = option_value(r"(?:--body-file[= ]|-F[= ]?)", command_str)
    body_match = re.search(r"\bbody=@(['\"]?)(.+?)\1(?:\s|$)", command_str,
                           re.MULTILINE)
    if body_match:
        path_str = body_match.group(2)
    if not path_str or path_str == "-" or path_str.startswith("body="):
        return ""
    return read_text_file(path_str, folder_str)


def expected_entries(head_str: str, folder_str: str,
                     run_matrix_str: str = "") -> list:
    """List the Fail* entries that a description must hold.

    Inputs:
        head_str: the branch or commit of the pull request.
        folder_str: a folder of the git checkout.
        run_matrix_str: the matrix that the `tests` job built for that
            commit, or an empty text when it isn't known.
    Outputs: the entries of the HLFRs of tests/not_implemented.txt of the
        head (PCR-00065), then the environment entries of the run's
        matrix (PCR-00063) (PCR-00070). Raises OSError when git can't
        run.
    """
    try:
        list_text_str = run_git(
            folder_str, "show",
            f"{head_str}:{NOT_IMPLEMENTED_LIST_PATH_STR}")
    except subprocess.CalledProcessError:
        list_text_str = ""
    return (not_implemented_entries(listed_explanations(list_text_str))
            + [entry_str for entry_str in fail_star_entries(run_matrix_str)
               if entry_str.startswith(ENVIRONMENT_ENTRY_START_STR)])


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
    base_str, head_str = target_tuple
    try:
        head_branch_str = (head_str if head_str != "HEAD" else run_git(
            folder_str, "rev-parse", "--abbrev-ref", "HEAD").strip())
        problem_list = branch_problems(base_str, head_str, folder_str,
                                       head_branch_str)
        body_str = command_body(command_str, folder_str)
        if body_str:
            # PCR-00070: the environment Fail* comes later, from CI.
            problem_list.extend(description_problems(
                body_str, expected_entries(head_str, folder_str), base_str))
    except (OSError, subprocess.CalledProcessError):
        return 0
    if not problem_list:
        return 0
    print("Blocked: " + " ".join(problem_list), file=sys.stderr)
    return 2


def print_result(problem_list: list, pass_text_str: str) -> int:
    """Print the problems or the pass line of a check.

    Inputs:
        problem_list: the problem texts found.
        pass_text_str: the text printed after "Result: pass, " when
            there is no problem.
    Outputs: the process exit code, 0 when there is no problem.
    """
    for problem_str in problem_list:
        print("Result: fail. " + problem_str)
    if not problem_list:
        print("Result: pass, " + pass_text_str)
    return 1 if problem_list else 0


def check_in_ci(base_str: str, head_str: str, matrix_path_str: str,
                body_path_str: str = "", head_branch_str: str = "") -> int:
    """Check a pull request's branch and the matrix of its CI run.

    Inputs:
        base_str: the branch the pull request goes into.
        head_str: the commit of the pull request.
        matrix_path_str: the matrix that the CI run built.
        body_path_str: the saved description, or empty to skip that
            part.
        head_branch_str: the name of the branch of the pull request.
    Outputs: the process exit code, 0 when there is no problem. When
        the pull request skips the tests (PCR-00079, PCR-00083), there is
        no matrix of the run to check, and the branch is still checked.
        Of the description, only the environment Fail* of this run is
        checked here (PCR-00070); the fail-star-section job checks the
        rest.
    """
    try:
        problem_list = branch_problems(base_str, head_str,
                                       REPOSITORY_ROOT_STR, head_branch_str)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Result: fail, git can't read the branch: {error}")
        return 1
    if not branch_needs_full_suite(base_str, head_str, REPOSITORY_ROOT_STR,
                                   head_branch_str):
        print("The tests of this pull request are skipped (PCR-00079, "
              "PCR-00083), so there is no matrix of this run to check.")
        return print_result(problem_list, "the branch is ready.")
    if not os.path.exists(matrix_path_str):
        problem_list.append(f"This run built no test matrix at "
                            f"{matrix_path_str}.")
        return print_result(problem_list, "")
    with open(matrix_path_str, encoding="utf-8") as matrix_file:
        matrix_str = matrix_file.read()
    problem_list.extend(run_matrix_problems(matrix_str, base_str))
    environment_entry_list = [
        entry_str for entry_str in fail_star_entries(matrix_str)
        if entry_str.startswith(ENVIRONMENT_ENTRY_START_STR)]
    if body_path_str and environment_entry_list:
        with open(body_path_str, encoding="utf-8") as body_file:
            body_entry_list = fail_star_entries(body_file.read())
        problem_list.extend(
            f"This run has an environment Fail* that the section \"## "
            f"{FAIL_STAR_HEADING_STR}\" of the description doesn't list: "
            f"\"- {entry_str}\" (PCR-00070). Add it, then run this job "
            "again." for entry_str in environment_entry_list
            if entry_str not in body_entry_list)
    return print_result(problem_list,
                        "the branch and the matrix of this run are ready.")


def check_description(base_str: str, head_str: str, body_path_str: str,
                      run_matrix_path_str: str = "") -> int:
    """Check a saved pull request description, for the CI job.

    Inputs:
        base_str: the branch the pull request goes into.
        head_str: the commit of the pull request.
        body_path_str: the path of the saved description.
        run_matrix_path_str: a file with the matrix that the `tests` job
            posted for that commit, or empty when there is none yet.
    Outputs: the process exit code, 0 when the description starts with
        the Fail* section and the section lists every HLFR of the
        branch's tests/not_implemented.txt and every environment Fail* of
        the posted matrix, or only `none` (PCR-00070), with no Fail* into
        main (PCR-00069).
    """
    run_matrix_str = (read_text_file(run_matrix_path_str, "")
                      if run_matrix_path_str else "")
    try:
        expected_entry_list = expected_entries(head_str, REPOSITORY_ROOT_STR,
                                               run_matrix_str)
    except OSError as error:
        print(f"Result: fail, git can't read {head_str} (into {base_str}): "
              f"{error}")
        return 1
    with open(body_path_str, encoding="utf-8") as body_file:
        body_str = body_file.read()
    problem_list = description_problems(body_str, expected_entry_list,
                                        base_str)
    return print_result(problem_list,
                        "the description starts with its Fail* section "
                        f"({len(expected_entry_list)} Fail* expected).")


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
    parser.add_argument("--head-branch", default="")
    parser.add_argument("--run-matrix", default="")
    parser.add_argument("--green-light", action="store_true")
    argument_namespace = parser.parse_args()
    if argument_namespace.hook:
        return run_hook()
    if argument_namespace.green_light:
        with open(argument_namespace.body_file, encoding="utf-8") as body_file:
            body_str = body_file.read()
        return print_result(green_light_problems(
            body_str, argument_namespace.head, argument_namespace.base,
            argument_namespace.head_branch),
            "the head is the commit of the green light.")
    if argument_namespace.ci_matrix:
        return check_in_ci(argument_namespace.base, argument_namespace.head,
                           argument_namespace.ci_matrix,
                           argument_namespace.body_file,
                           argument_namespace.head_branch)
    if argument_namespace.body_file:
        return check_description(argument_namespace.base,
                                 argument_namespace.head,
                                 argument_namespace.body_file,
                                 argument_namespace.run_matrix)
    try:
        problem_list = branch_problems(argument_namespace.base,
                                       argument_namespace.head,
                                       REPOSITORY_ROOT_STR,
                                       argument_namespace.head_branch)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Result: fail, git can't read the branch: {error}")
        return 1
    return print_result(problem_list, "the branch is ready.")


if __name__ == "__main__":
    sys.exit(main())
