"""Run all tests and write the test matrix (PCR-00019 to PCR-00023,
PCR-00042, PCR-00063 to PCR-00071).

Usage:
    python tests/build_test_matrix.py [--output PATH] [--require-qt]
                                      [--require-h5py]
                                      [--environment-limit [TEXT]]
                                      [--base BRANCH --head COMMIT]
    python tests/build_test_matrix.py --shard K/N --results-output FILE
                                      [--require-qt] [--require-h5py]
                                      [--environment-limit [TEXT]]
    python tests/build_test_matrix.py --from-results FOLDER
                                      [--output PATH]
                                      [--durations-output FILE]
                                      [--base BRANCH --head COMMIT]

The matrix has one row per HLFR with four columns:
1. the HLFR (PCR-00020);
2. its child LLFRs (PCR-00021);
3. the tests linked to the HLFR and their last run status (PCR-00022);
4. "pass" when all those tests passed, "fail" when at least one failed
   (PCR-00023, PCR-00042).

A test is linked to an HLFR when it is tagged (tests/support.covers)
with the HLFR itself or with one of its child LLFRs. Column 4 shows
"no tests" when no test is linked, and "not run" when linked tests were
skipped (for example without PyQt6) and none failed.

The script exits with code 1 when a test fails, when --require-qt is
given and PyQt6 is not installed, or when --require-h5py is given and
h5py (needed by the HDF5 tests) is not installed. CI passes both, so
those tests can't be skipped there without failing the run. With --base
and --head, it also exits with code 1 when an HLFR that the branch
affects has no test, or when git can't tell which HLFRs it affects
(PCR-00059).

Justified exceptions, shown as `Fail*` with their justification:
- --environment-limit, for an environment where PyQt6 or h5py can't be
  installed: the tests skipped because one of them is missing show as
  "Fail* (PyQt6 missing)" or "Fail* (h5py missing)" in column 3
  (PCR-00063), and column 4 shows the missing capabilities (PCR-00071).
  They count as passed (PCR-00064), so --require-qt and --require-h5py
  don't fail the run for them. TEXT is added to the justification.
  Without the option, the two --require options fail as before.
- tests/not_implemented.txt, one HLFR ID per line followed by the
  explanation (PCR-00066): column 4 of those HLFRs shows "Fail*: the
  implementation has not been done yet." and the explanation, unless a
  test failed (PCR-00065, PCR-00042). Into develop, such an HLFR with no
  test doesn't fail the check of PCR-00059 (PCR-00068).
Every Fail* is listed in the section "Fail* (PCR-00070)" above the
table, and the script prints that section, ready to paste at the top of
the pull request description, or the section with the single entry
`none` when there is no Fail* (PCR-00070).

Parallel shards (PCR-00127, PCR-00128): with --shard K/N the script
runs only the test modules of shard K of N (tests/ci_shards.py) and
writes their statuses and timings to the JSON file of
--results-output, with no matrix; it exits with code 1 when one of its
tests fails. With --from-results the script runs no test: it reads the
shard files below FOLDER, checks that every shard reported and that
every test ran in exactly one shard, and builds the matrix from them,
with the same checks as a whole run. --durations-output then writes the
measured seconds of each module, ready to replace
tests/ci_test_durations.json. Every run prints the 30 slowest tests.

CI runs the shards and then this script with --from-results and
--output test_matrix_ci.md, and posts that file on each pull request.
After a release, an agent opens two pull requests, one into main and
one into develop, that put the release run's file in
tests/test_matrix.md (PCR-00061, PCR-00085). Run locally, the script
writes test_matrix_local.md at the repository root by default, which git
ignores, so that a branch leaves tests/test_matrix.md unchanged
(PCR-00081).
"""

import argparse
import os
import re
import subprocess
import sys
import time
import unittest

TESTS_FOLDER_STR = os.path.dirname(os.path.abspath(__file__))
REPOSITORY_ROOT_STR = os.path.dirname(TESTS_FOLDER_STR)
if REPOSITORY_ROOT_STR not in sys.path:
    sys.path.insert(0, REPOSITORY_ROOT_STR)

from tests import ci_shards  # noqa
from tests.check_pr_ready import (  # noqa
    ENVIRONMENT_ENTRY_START_STR, FAIL_STAR_HEADING_STR, FAIL_STAR_STR,
    MAIN_BRANCH_STR, NO_FAIL_STAR_SECTION_STR, NOT_IMPLEMENTED_TEXT_STR,
    not_implemented_entry, source_hash)
from tests.find_affected_requirements import find_affected_hlfrs  # noqa
from tests.support import (  # noqa
    COVERED_ATTRIBUTE_STR, H5PY_AVAILABLE_B, QT_AVAILABLE_B)

REQUIREMENTS_FOLDER_STR = os.path.join(REPOSITORY_ROOT_STR, "docs",
                                       "requirements")
REQUIREMENTS_PATH_TUPLE = (
    os.path.join(REQUIREMENTS_FOLDER_STR,
                 "high_level_functional_requirements.md"),
    os.path.join(REQUIREMENTS_FOLDER_STR,
                 "low_level_functional_requirements.md"),
)
# PCR-00081: only CI writes tests/test_matrix.md.
DEFAULT_OUTPUT_PATH_STR = os.path.join(REPOSITORY_ROOT_STR,
                                       "test_matrix_local.md")
HEADING_PATTERN_STR = r"^### ((?:HLFR|LLFR)-\d{5}) (.+)$"
PARENT_PATTERN_STR = r"^\*Parent: (.+)\*$"
PASSED_STR = "passed"
FAILED_STR = "failed"
SKIPPED_STR = "skipped"
KNOWN_FAILURE_STR = "known macOS failure"
KNOWN_FAILURES_PATH_STR = os.path.join(TESTS_FOLDER_STR,
                                       "known_macos_failures.txt")
NOT_IMPLEMENTED_PATH_STR = os.path.join(TESTS_FOLDER_STR,
                                        "not_implemented.txt")
NOT_IMPLEMENTED_LINE_PATTERN_STR = r"^(HLFR-\d{5})\s+(\S.*)$"
# PCR-00063: the skip reasons of tests/support.requires_qt and
# requires_h5py, and the capability each one names.
CAPABILITY_BY_SKIP_REASON_DICT = {"PyQt6 is not installed": "PyQt6",
                                  "h5py is not installed": "h5py"}


def read_requirements() -> tuple:
    """Read the HLFRs and the LLFR parent links from the requirements.

    Inputs: none (reads the high-level and low-level functional
        requirement files in docs/requirements, in that order).
    Outputs: a tuple (hlfr_list, children_dict) where hlfr_list holds
        (ID, title) pairs sorted by ID and children_dict maps each HLFR
        ID to the list of its child LLFR IDs, sorted by ID. Sorting keeps
        the matrix in ID order, although the files group requirements by
        part of the interface.
    """
    line_list = []
    for requirement_path_str in REQUIREMENTS_PATH_TUPLE:
        with open(requirement_path_str,
                  encoding="utf-8") as requirement_file:
            line_list.extend(requirement_file.read().splitlines())
    hlfr_list = []
    children_dict = {}
    current_id_str = ""
    for line_str in line_list:
        heading_match = re.match(HEADING_PATTERN_STR, line_str)
        if heading_match:
            current_id_str = heading_match.group(1)
            if current_id_str.startswith("HLFR"):
                hlfr_list.append((current_id_str, heading_match.group(2)))
                children_dict.setdefault(current_id_str, [])
            continue
        parent_match = re.match(PARENT_PATTERN_STR, line_str)
        if parent_match and current_id_str.startswith("LLFR"):
            for parent_str in parent_match.group(1).split(","):
                children_dict.setdefault(parent_str.strip(), []).append(
                    current_id_str)
    for child_list in children_dict.values():
        child_list.sort()
    return sorted(hlfr_list), children_dict


class RecordingResult(unittest.TextTestResult):
    """Test result that keeps one status for every test.

    A test is recorded once. "failed" wins over any other status, so a
    test with a failing subtest is failed even if unittest reports
    nothing else for it.
    """

    def __init__(self, *argument_tuple, **keyword_dict) -> None:
        """Create the result with an empty status record.

        Inputs: the arguments of unittest.TextTestResult.
        Outputs: none.
        """
        super().__init__(*argument_tuple, **keyword_dict)
        self.status_dict = {}
        self.skip_reason_dict = {}
        # PCR-00127: the timings that balance the shards and the list of
        # the slowest tests. The time between the end of one test and the
        # end of the next goes to the module of the next one, so that the
        # module's imports and class set-ups count too.
        self.test_seconds_list = []
        self.module_seconds_dict = {}
        self.last_stop_s = time.perf_counter()

    @property
    def status_list(self) -> list:
        """Return the recorded tests in the order they first finished.

        Inputs: none.
        Outputs: a list of (test ID, requirement list, status) tuples.
        """
        return [(test_id_str, requirement_list, status_str)
                for test_id_str, (requirement_list, status_str)
                in self.status_dict.items()]

    def record(self, test, status_str: str) -> None:
        """Store a test, its requirement tags and its status.

        Inputs:
            test: the finished unittest.TestCase (for a subtest, the
                parent test).
            status_str: PASSED_STR, FAILED_STR or SKIPPED_STR.
        Outputs: none.
        """
        method = getattr(test, getattr(test, "_testMethodName", ""), None)
        requirement_list = getattr(method, COVERED_ATTRIBUTE_STR, [])
        previous_tuple = self.status_dict.get(test.id())
        if previous_tuple and previous_tuple[1] == FAILED_STR:
            return
        self.status_dict[test.id()] = (requirement_list, status_str)

    def stopTest(self, test) -> None:
        """Add the time since the previous test to the test's module.

        Inputs:
            test: the finished test.
        Outputs: none.
        """
        super().stopTest(test)
        now_s = time.perf_counter()
        module_str = ci_shards.module_of(test)
        self.module_seconds_dict[module_str] = (
            self.module_seconds_dict.get(module_str, 0.0)
            + now_s - self.last_stop_s)
        self.last_stop_s = now_s

    def addDuration(self, test, elapsed_s: float) -> None:
        """Keep the duration of a test (Python 3.12 and later).

        Inputs:
            test: the finished test.
            elapsed_s: its run time, set-up and tear-down included.
        Outputs: none.
        """
        super().addDuration(test, elapsed_s)
        self.test_seconds_list.append((test.id(), elapsed_s))

    def addSuccess(self, test) -> None:
        """Record a passed test.

        Inputs:
            test: the finished test.
        Outputs: none.
        """
        super().addSuccess(test)
        self.record(test, PASSED_STR)

    def addFailure(self, test, error_tuple) -> None:
        """Record a failed test.

        Inputs:
            test: the finished test.
            error_tuple: the exception information.
        Outputs: none.
        """
        super().addFailure(test, error_tuple)
        self.record(test, FAILED_STR)

    def addError(self, test, error_tuple) -> None:
        """Record a test that raised an error, as failed.

        Inputs:
            test: the finished test.
            error_tuple: the exception information.
        Outputs: none.
        """
        super().addError(test, error_tuple)
        self.record(test, FAILED_STR)

    def addSkip(self, test, reason_str: str) -> None:
        """Record a skipped test.

        Inputs:
            test: the skipped test.
            reason_str: why it was skipped.
        Outputs: none.
        """
        super().addSkip(test, reason_str)
        self.skip_reason_dict[test.id()] = reason_str
        self.record(test, SKIPPED_STR)

    def addSubTest(self, test, subtest, error_tuple) -> None:
        """Record the parent test as failed when one of its subtests fails.

        Inputs:
            test: the parent test.
            subtest: the subtest that finished.
            error_tuple: the exception information, or None on success.
        Outputs: none.
        """
        super().addSubTest(test, subtest, error_tuple)
        if error_tuple is not None:
            self.record(test, FAILED_STR)


def discover_suite():
    """Discover every test in the tests folder.

    Inputs: none.
    Outputs: the unittest.TestSuite of every test_*.py module.
    """
    loader = unittest.TestLoader()
    return loader.discover(TESTS_FOLDER_STR, pattern="test_*.py",
                           top_level_dir=REPOSITORY_ROOT_STR)


def run_suite(suite):
    """Run a test suite through RecordingResult.

    Inputs:
        suite: the unittest.TestSuite to run.
    Outputs: the RecordingResult of the run.
    """
    runner = unittest.TextTestRunner(resultclass=RecordingResult,
                                     verbosity=1)
    return runner.run(suite)


def run_all_tests():
    """Discover and run every test in the tests folder.

    Inputs: none.
    Outputs: the RecordingResult of the run.
    """
    return run_suite(discover_suite())


def test_seconds_of(test_result) -> list:
    """Read the test durations of a test result, if it has them.

    Inputs:
        test_result: a RecordingResult, or a stand-in in the self-tests.
    Outputs: the list of (test ID, seconds) pairs, or an empty list.
    """
    value = getattr(test_result, "test_seconds_list", [])
    return value if isinstance(value, list) else []


def read_known_failures() -> set:
    """Read the tests that are known to fail on macOS (PCR-00062).

    Inputs: none (reads tests/known_macos_failures.txt).
    Outputs: the set of test IDs.
    """
    with open(KNOWN_FAILURES_PATH_STR, encoding="utf-8") as known_file:
        return {line_str.strip() for line_str in known_file
                if line_str.strip() and not line_str.startswith("#")}


def mark_known_failures(test_status_list: list, platform_str: str,
                        known_set: set) -> list:
    """Mark the listed tests that failed on macOS as known failures.

    Inputs:
        test_status_list: the tuples returned by run_all_tests.
        platform_str: the value of sys.platform.
        known_set: the IDs of the known failures.
    Outputs: the list with those statuses changed. On any other system
        it is unchanged, so a listed test that fails there still fails.
    """
    if platform_str != "darwin":
        return test_status_list
    return [(test_id_str, requirement_list,
             KNOWN_FAILURE_STR if status_str == FAILED_STR
             and test_id_str in known_set else status_str)
            for test_id_str, requirement_list, status_str in test_status_list]


def environment_status(capability_str: str) -> str:
    """Return the column 3 status of a test the environment couldn't run.

    Inputs:
        capability_str: the missing capability, for example "PyQt6".
    Outputs: the status, for example "Fail* (PyQt6 missing)" (PCR-00063).
    """
    return f"{FAIL_STAR_STR} ({capability_str} missing)"


def environment_capability(status_str: str) -> str:
    """Return the capability that an environment Fail* status names.

    Inputs:
        status_str: a test status.
    Outputs: the capability, or an empty text for any other status.
    """
    match = re.fullmatch(re.escape(FAIL_STAR_STR) + r" \((.+) missing\)",
                         status_str)
    return match.group(1) if match else ""


def mark_environment_limits(test_status_list: list,
                            skip_reason_dict: dict) -> list:
    """Show the tests that the environment couldn't run as Fail*.

    Inputs:
        test_status_list: the tuples returned by run_all_tests.
        skip_reason_dict: the skip reason of each skipped test ID.
    Outputs: the list with the status of every test skipped because
        PyQt6 or h5py is missing changed to its Fail* (PCR-00063). Other
        skipped tests, and tests that ran, keep their status, so a test
        that ran and failed stays failed.
    """
    marked_list = []
    for test_id_str, requirement_list, status_str in test_status_list:
        capability_str = CAPABILITY_BY_SKIP_REASON_DICT.get(
            skip_reason_dict.get(test_id_str, ""), "")
        if status_str == SKIPPED_STR and capability_str:
            status_str = environment_status(capability_str)
        marked_list.append((test_id_str, requirement_list, status_str))
    return marked_list


def escape_cell(text_str: str) -> str:
    """Make a text safe inside a Markdown table cell.

    Inputs:
        text_str: the text.
    Outputs: the text with each "|" escaped.
    """
    return text_str.replace("|", "\\|")


def not_implemented_result(explanation_str: str) -> str:
    """Return the column 4 value of an HLFR that isn't implemented yet.

    Inputs:
        explanation_str: its explanation in tests/not_implemented.txt.
    Outputs: the value, for example "Fail*: the implementation has not
        been done yet. Waits for #190." (PCR-00065).
    """
    return escape_cell(f"{FAIL_STAR_STR}: {NOT_IMPLEMENTED_TEXT_STR} "
                       f"{explanation_str}")


def hlfr_result(status_list: list, explanation_str: str = None) -> str:
    """Return the column 4 value for the statuses of one HLFR's tests.

    Inputs:
        status_list: the statuses of the tests linked to the HLFR.
        explanation_str: the explanation of tests/not_implemented.txt
            when the HLFR is listed there, else None.
    Outputs: "fail" when a test failed (PCR-00042); otherwise the Fail*
        of an HLFR not implemented yet (PCR-00065); otherwise the Fail*
        that names the missing capabilities (PCR-00071); otherwise "no
        tests", "not run" or "pass" (PCR-00023).
    """
    if FAILED_STR in status_list:
        return "fail"
    if explanation_str is not None:
        return not_implemented_result(explanation_str)
    capability_list = sorted({environment_capability(status_str)
                              for status_str in status_list}
                             - {""})
    if capability_list:
        return (f"{FAIL_STAR_STR} ({', '.join(capability_list)} "
                "missing)")
    if not status_list:
        return "no tests"
    if SKIPPED_STR in status_list:
        return "not run"
    return "pass"


def read_not_implemented(path_str: str = NOT_IMPLEMENTED_PATH_STR) -> dict:
    """Read the HLFRs that aren't implemented yet (PCR-00066).

    Inputs:
        path_str: the list file, tests/not_implemented.txt by default.
    Outputs: a dict from each HLFR ID to its explanation. A missing file
        is an empty list. Raises ValueError for a line that isn't a
        comment, a blank line or an HLFR ID followed by an explanation,
        and for an ID listed twice.
    """
    if not os.path.exists(path_str):
        return {}
    explanation_dict = {}
    with open(path_str, encoding="utf-8") as list_file:
        for line_number_i, line_str in enumerate(list_file, start=1):
            line_str = line_str.strip()
            if not line_str or line_str.startswith("#"):
                continue
            line_match = re.match(NOT_IMPLEMENTED_LINE_PATTERN_STR, line_str)
            if not line_match:
                raise ValueError(
                    f"{path_str}, line {line_number_i}: write an HLFR ID "
                    "followed by the explanation (PCR-00066).")
            if line_match.group(1) in explanation_dict:
                raise ValueError(f"{path_str}, line {line_number_i}: "
                                 f"{line_match.group(1)} is listed twice.")
            explanation_dict[line_match.group(1)] = line_match.group(2)
    return explanation_dict


def environment_justification(capability_str: str,
                              extra_text_str: str) -> str:
    """Write the justification of an environment Fail* (PCR-00063).

    Inputs:
        capability_str: the missing capability, for example "PyQt6".
        extra_text_str: the text of --environment-limit, maybe empty.
    Outputs: the justification, for example "PyQt6 cannot be installed in
        the environment that built this matrix."
    """
    justification_str = (f"{capability_str} cannot be installed in the "
                         "environment that built this matrix.")
    if extra_text_str.strip():
        justification_str += " " + extra_text_str.strip()
    return justification_str


def fail_star_section(test_status_list: list, explanation_dict: dict,
                      extra_text_str: str = "") -> str:
    """Write the section that lists every Fail* (PCR-00070).

    Inputs:
        test_status_list: the tuples returned by run_all_tests, after
            mark_environment_limits.
        explanation_dict: the HLFRs of read_not_implemented, limited to
            the HLFRs of the matrix.
        extra_text_str: the text of --environment-limit, maybe empty.
    Outputs: the Markdown section, or an empty text when there is no
        Fail*. Each entry is one line, so it can be pasted at the top of
        the pull request description as it is.
    """
    count_dict = {}
    for _, _, status_str in test_status_list:
        capability_str = environment_capability(status_str)
        if capability_str:
            count_dict[capability_str] = count_dict.get(capability_str, 0) + 1
    entry_list = [
        f"- {ENVIRONMENT_ENTRY_START_STR}{capability_str}: "
        f"{count_dict[capability_str]} tests shown as "
        f"\"{environment_status(capability_str)}\". "
        f"{environment_justification(capability_str, extra_text_str)}"
        for capability_str in sorted(count_dict)]
    entry_list.extend(
        "- " + not_implemented_entry(hlfr_id_str,
                                     explanation_dict[hlfr_id_str])
        for hlfr_id_str in sorted(explanation_dict))
    if not entry_list:
        return ""
    return f"## {FAIL_STAR_HEADING_STR}\n\n" + "\n".join(entry_list) + "\n"


def build_matrix(test_status_list: list, hash_str: str = "",
                 explanation_dict: dict = None,
                 extra_text_str: str = "",
                 qt_available_b: bool = None) -> tuple:
    """Build the test matrix table and the list of untested LLFRs.

    Inputs:
        test_status_list: the tuples returned by run_all_tests, after
            mark_known_failures and mark_environment_limits.
        hash_str: the hash of the files tested (PCR-00061), if known.
        explanation_dict: the HLFRs of read_not_implemented (PCR-00066),
            none by default.
        extra_text_str: the text of --environment-limit, maybe empty.
        qt_available_b: whether the runs had PyQt6; by default, whether
            this run has it. The shards of a CI run tell it to the run
            that merges them (PCR-00127), which needs no PyQt6 itself.
    Outputs: a tuple (markdown text, list of LLFR IDs without tests).
        The text holds the Fail* section (PCR-00070) above the table
        when there is a Fail*.
    """
    explanation_dict = explanation_dict or {}
    hlfr_list, children_dict = read_requirements()
    tested_set = {requirement_str
                  for _, requirement_list, _ in test_status_list
                  for requirement_str in requirement_list}
    row_list = ["| HLFR | LLFR | Tests (last run status) | Result |",
                "|---|---|---|---|"]
    untested_list = []
    for hlfr_id_str, title_str in hlfr_list:
        child_list = sorted(children_dict.get(hlfr_id_str, []))
        linked_set = set(child_list) | {hlfr_id_str}
        test_cell_list = []
        status_list = []
        for test_id_str, requirement_list, status_str in test_status_list:
            if linked_set & set(requirement_list):
                short_id_str = test_id_str.replace("tests.", "", 1)
                test_cell_list.append(f"`{short_id_str}` {status_str}")
                status_list.append(status_str)
        untested_list.extend(child for child in child_list
                             if child not in tested_set)
        row_list.append(
            f"| {hlfr_id_str} {title_str} | {'<br>'.join(child_list)} | "
            f"{'<br>'.join(test_cell_list) or '-'} | "
            f"{hlfr_result(status_list, explanation_dict.get(hlfr_id_str))}"
            " |")
    shown_explanation_dict = {
        hlfr_id_str: explanation_dict[hlfr_id_str]
        for hlfr_id_str, _ in hlfr_list if hlfr_id_str in explanation_dict}
    section_str = fail_star_section(test_status_list, shown_explanation_dict,
                                    extra_text_str)
    if qt_available_b is None:
        qt_available_b = QT_AVAILABLE_B
    environment_str = ("PyQt6 installed" if qt_available_b
                       else "PyQt6 not installed: GUI tests skipped")
    if any(environment_capability(status_str)
           for _, _, status_str in test_status_list):
        environment_str = ("environment limit: the tests it can't run are "
                           f"shown as {FAIL_STAR_STR}")
    text_str = ("# Test matrix\n\n"
                "Generated by `tests/build_test_matrix.py` "
                f"({environment_str}). Do not edit by hand.\n\n"
                + (f"Source hash: `{hash_str}`\n\n" if hash_str else "")
                + (section_str + "\n" if section_str else "")
                + "\n".join(row_list) + "\n")
    return text_str, sorted(set(untested_list))


def untested_hlfrs(test_status_list: list, hlfr_id_set: set,
                   excused_id_set: set = frozenset()) -> list:
    """Find which of the given HLFRs have no linked test (PCR-00059).

    Inputs:
        test_status_list: the tuples returned by run_all_tests.
        hlfr_id_set: the HLFR IDs to check.
        excused_id_set: the HLFR IDs that pass the check with no test,
            those of tests/not_implemented.txt in a pull request into
            develop (PCR-00068).
    Outputs: the sorted IDs of those with no test tagged with the HLFR
        or with one of its child LLFRs, apart from the excused ones.
    """
    _, children_dict = read_requirements()
    tested_set = {requirement_str
                  for _, requirement_list, _ in test_status_list
                  for requirement_str in requirement_list}
    return sorted(
        hlfr_id_str for hlfr_id_str in set(hlfr_id_set) - set(excused_id_set)
        if not ({hlfr_id_str} | set(children_dict.get(hlfr_id_str, [])))
        & tested_set)


def affected_hlfrs_have_tests(test_status_list: list, base_str: str,
                              head_str: str,
                              not_implemented_set: set = frozenset()) -> bool:
    """Report whether every HLFR that a branch affects has a test.

    Inputs:
        test_status_list: the tuples returned by run_all_tests.
        base_str: the branch the pull request goes into.
        head_str: the commit of the pull request.
        not_implemented_set: the HLFR IDs of tests/not_implemented.txt.
    Outputs: True when they all have one (PCR-00059), counting those of
        not_implemented_set as having one, except into main (PCR-00068,
        PCR-00069).
    """
    hlfr_id_set = find_affected_hlfrs(base_str, head_str,
                                      REPOSITORY_ROOT_STR)
    if hlfr_id_set is None:
        print("git can't tell which HLFRs this branch affects.",
              file=sys.stderr)
        return False
    excused_id_set = (set() if base_str == MAIN_BRANCH_STR
                      else set(not_implemented_set))
    missing_list = untested_hlfrs(test_status_list, hlfr_id_set,
                                  excused_id_set)
    if missing_list:
        print("HLFRs affected by this branch without tests: "
              + ", ".join(missing_list), file=sys.stderr)
    return not missing_list


def report_to_github(test_status_list: list, untested_list: list) -> None:
    """Print GitHub Actions annotations for failed tests and coverage.

    Inputs:
        test_status_list: the tuples returned by run_all_tests.
        untested_list: LLFR IDs that no test covers.
    Outputs: none (prints workflow commands when run in GitHub Actions).
    """
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    count_dict = {PASSED_STR: 0, FAILED_STR: 0, SKIPPED_STR: 0}
    for test_id_str, _, status_str in test_status_list:
        count_dict[status_str] = count_dict.get(status_str, 0) + 1
        if status_str == FAILED_STR:
            print(f"::error title=Test failed::{test_id_str}")
    print(f"::notice title=Test totals::{count_dict[PASSED_STR]} passed, "
          f"{count_dict[FAILED_STR]} failed, "
          f"{count_dict[SKIPPED_STR]} skipped")
    if untested_list:
        print("::warning title=LLFRs without tests::"
              + ", ".join(untested_list))


def check_libraries(argument_namespace, environment_limit_b: bool) -> bool:
    """Check that the libraries the run requires are installed.

    Inputs:
        argument_namespace: the parsed command-line arguments.
        environment_limit_b: True when --environment-limit was given.
    Outputs: True when the run may go on (PCR-00063).
    """
    for required_b, available_b, name_str in (
            (argument_namespace.require_qt, QT_AVAILABLE_B, "PyQt6"),
            (argument_namespace.require_h5py, H5PY_AVAILABLE_B, "h5py")):
        if required_b and not available_b and not environment_limit_b:
            print(f"{name_str} is required but not installed. If it can't "
                  "be installed here, add --environment-limit (PCR-00063).",
                  file=sys.stderr)
            return False
    return True


def marked_statuses(test_result, environment_limit_b: bool) -> list:
    """Return the statuses of a run with the justified exceptions marked.

    Inputs:
        test_result: the RecordingResult of the run.
        environment_limit_b: True when --environment-limit was given.
    Outputs: the (test ID, requirement list, status) tuples, with the
        known macOS failures (PCR-00062) and, with the option, the
        environment Fail* (PCR-00063) marked.
    """
    test_status_list = mark_known_failures(
        test_result.status_list, sys.platform, read_known_failures())
    if environment_limit_b:
        test_status_list = mark_environment_limits(
            test_status_list, test_result.skip_reason_dict)
    return test_status_list


def run_shard(shard_str: str, results_path_str: str,
              environment_limit_b: bool, extra_text_str: str) -> int:
    """Run the tests of one CI shard and write its results (PCR-00127).

    Inputs:
        shard_str: the shard as K/N.
        results_path_str: the JSON file to write.
        environment_limit_b: True when --environment-limit was given.
        extra_text_str: the text of --environment-limit, maybe empty.
    Outputs: the process exit code: 0 when every test of the shard
        passed, 1 when one failed or the arguments are wrong.
    """
    try:
        shard_index_i, shard_count_i = ci_shards.parse_shard(shard_str)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    if not results_path_str:
        print("--shard needs --results-output.", file=sys.stderr)
        return 1
    test_list = ci_shards.iterate_tests(discover_suite())
    suite, module_list, expected_s = ci_shards.select_shard(
        test_list, shard_index_i, shard_count_i, ci_shards.read_durations())
    print(f"Shard {shard_index_i} of {shard_count_i}: {len(module_list)} "
          f"modules, {suite.countTestCases()} tests, about "
          f"{expected_s:.0f} s expected.")
    # unittest empties a suite while it runs it, so the planned tests are
    # listed first.
    planned_id_list = [test.id() for test in ci_shards.iterate_tests(suite)]
    start_s = time.perf_counter()
    test_result = run_suite(suite)
    run_s = time.perf_counter() - start_s
    test_status_list = marked_statuses(test_result, environment_limit_b)
    test_seconds_list = test_seconds_of(test_result)
    ci_shards.write_results(results_path_str, {
        "shard_index": shard_index_i,
        "shard_count": shard_count_i,
        "discovered_test_ids": [test.id() for test in test_list],
        "planned_test_ids": planned_id_list,
        "modules": module_list,
        "statuses": [list(status_tuple) for status_tuple
                     in test_status_list],
        "environment_text": extra_text_str if environment_limit_b else None,
        "qt_available": QT_AVAILABLE_B,
        "module_seconds": {module_str: round(seconds_f, 3)
                           for module_str, seconds_f in sorted(
                               test_result.module_seconds_dict.items())},
        "test_seconds": [[test_id_str, round(seconds_f, 3)]
                         for test_id_str, seconds_f in test_seconds_list],
        "expected_seconds": round(expected_s, 1),
        "run_seconds": round(run_s, 1)})
    print(f"Shard results written to {results_path_str} ({run_s:.0f} s).")
    print(ci_shards.slowest_tests_report(test_seconds_list))
    failed_b = any(status_str == FAILED_STR
                   for _, _, status_str in test_status_list)
    return 1 if failed_b else 0


def read_shard_results(folder_str: str, durations_path_str: str) -> tuple:
    """Read the results of every CI shard (PCR-00127, PCR-00128).

    Inputs:
        folder_str: the folder of --from-results.
        durations_path_str: the file of --durations-output, maybe empty.
    Outputs: the tuple (statuses, environment limited, environment text,
        PyQt6 available, problems): the merged (test ID, requirement
        list, status) tuples, whether a shard ran with
        --environment-limit, their joined texts, whether every shard had
        PyQt6, and the problems of ci_shards.shard_problems, or of a file
        that can't be read. Prints the timing report and writes the
        durations file.
    """
    try:
        result_list = ci_shards.read_results_folder(folder_str)
    except (OSError, ValueError) as error:
        return [], False, "", False, [str(error)]
    problem_list = ci_shards.shard_problems(result_list)
    environment_limit_b, extra_text_str = (
        ci_shards.merged_environment_text(result_list))
    report_str = ci_shards.timing_report(result_list)
    print(report_str)
    summary_path_str = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if summary_path_str:
        with open(summary_path_str, "a", encoding="utf-8") as summary_file:
            summary_file.write(report_str + "\n")
    if durations_path_str:
        with open(durations_path_str, "w",
                  encoding="utf-8") as durations_file:
            durations_file.write(ci_shards.durations_file_text(
                ci_shards.merged_module_seconds(result_list)))
    qt_available_b = bool(result_list) and all(
        content_dict.get("qt_available") for content_dict in result_list)
    return (ci_shards.merged_statuses(result_list), environment_limit_b,
            extra_text_str, qt_available_b, problem_list)


def main() -> int:
    """Run the tests, write the matrix and report the result.

    Inputs: command-line arguments (see module docstring).
    Outputs: the process exit code (0 when every test passed).
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH_STR)
    parser.add_argument("--require-qt", action="store_true")
    parser.add_argument("--require-h5py", action="store_true")
    parser.add_argument("--environment-limit", nargs="?", const="",
                        default=None, metavar="TEXT")
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="")
    parser.add_argument("--shard", default="", metavar="K/N")
    parser.add_argument("--results-output", default="", metavar="FILE")
    parser.add_argument("--from-results", default="", metavar="FOLDER")
    parser.add_argument("--durations-output", default="", metavar="FILE")
    argument_namespace = parser.parse_args()
    environment_limit_b = argument_namespace.environment_limit is not None
    extra_text_str = argument_namespace.environment_limit or ""
    if argument_namespace.shard and argument_namespace.from_results:
        print("Give --shard or --from-results, not both.", file=sys.stderr)
        return 1
    # The --from-results run runs no test, so it needs no library.
    if (not argument_namespace.from_results
            and not check_libraries(argument_namespace,
                                    environment_limit_b)):
        return 1
    if argument_namespace.shard:
        return run_shard(argument_namespace.shard,
                         argument_namespace.results_output,
                         environment_limit_b, extra_text_str)
    try:
        explanation_dict = read_not_implemented()
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    hlfr_id_set = {hlfr_id_str for hlfr_id_str, _ in read_requirements()[0]}
    unknown_list = sorted(set(explanation_dict) - hlfr_id_set)
    if unknown_list:
        print("tests/not_implemented.txt lists IDs that aren't HLFRs: "
              + ", ".join(unknown_list), file=sys.stderr)
        return 1
    problem_list = []
    qt_available_b = None
    if argument_namespace.from_results:
        (test_status_list, environment_limit_b, extra_text_str,
         qt_available_b, problem_list) = read_shard_results(
            argument_namespace.from_results,
            argument_namespace.durations_output)
    else:
        test_result = run_all_tests()
        test_status_list = marked_statuses(test_result, environment_limit_b)
        print(ci_shards.slowest_tests_report(test_seconds_of(test_result)))
    try:
        hash_str = source_hash("HEAD", REPOSITORY_ROOT_STR)
    except (OSError, subprocess.CalledProcessError):
        hash_str = ""
    matrix_str, untested_list = build_matrix(
        test_status_list, hash_str, explanation_dict, extra_text_str,
        qt_available_b)
    with open(argument_namespace.output, "w",
              encoding="utf-8") as matrix_file:
        matrix_file.write(matrix_str)
    report_to_github(test_status_list, untested_list)
    print(f"Test matrix written to {argument_namespace.output}")
    section_str = fail_star_section(test_status_list, explanation_dict,
                                    extra_text_str)
    if section_str:
        print("\nThe matrix shows Fail*. Start the pull request description "
              "with this section (PCR-00070):\n\n" + section_str)
    else:
        print("\nThe matrix shows no Fail*. Start the pull request "
              "description with this section (PCR-00070):\n\n"
              + NO_FAIL_STAR_SECTION_STR)
    if untested_list:
        print("LLFRs without tests: " + ", ".join(untested_list))
    failed_b = any(status_str == FAILED_STR
                   for _, _, status_str in test_status_list)
    # PCR-00128: a shard that didn't report, or a test that ran in no
    # shard or in two, fails the run.
    for problem_str in problem_list:
        failed_b = True
        print(f"Shard problem (PCR-00128): {problem_str}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::error title=Shard problem (PCR-00128)::{problem_str}")
    if argument_namespace.base and not affected_hlfrs_have_tests(
            test_status_list, argument_namespace.base,
            argument_namespace.head, set(explanation_dict)):
        failed_b = True
    return 1 if failed_b else 0


if __name__ == "__main__":
    sys.exit(main())
