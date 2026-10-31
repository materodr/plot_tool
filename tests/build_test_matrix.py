"""Run all tests and write the test matrix (PCR-00019 to PCR-00023).

Usage:
    python tests/build_test_matrix.py [--output PATH] [--require-qt]

The matrix has one row per HLFR with four columns:
1. the HLFR (PCR-00020);
2. its child LLFRs (PCR-00021);
3. the tests linked to the HLFR and their last run status (PCR-00022);
4. "pass" when all those tests passed, "fail" when at least one failed
   (PCR-00023).

A test is linked to an HLFR when it is tagged (tests/support.covers)
with the HLFR itself or with one of its child LLFRs. Column 4 shows
"no tests" when no test is linked, and "not run" when linked tests were
skipped (for example without PyQt6) and none failed.

The script exits with code 1 when a test fails, or when --require-qt is
given and PyQt6 is not installed.
"""

import argparse
import os
import re
import sys
import unittest

TESTS_FOLDER_STR = os.path.dirname(os.path.abspath(__file__))
REPOSITORY_ROOT_STR = os.path.dirname(TESTS_FOLDER_STR)
if REPOSITORY_ROOT_STR not in sys.path:
    sys.path.insert(0, REPOSITORY_ROOT_STR)

from tests.support import COVERED_ATTRIBUTE_STR, QT_AVAILABLE_B  # noqa

REQUIREMENTS_PATH_STR = os.path.join(REPOSITORY_ROOT_STR, "docs",
                                     "requirements",
                                     "functional_requirements.md")
DEFAULT_OUTPUT_PATH_STR = os.path.join(TESTS_FOLDER_STR, "test_matrix.md")
HEADING_PATTERN_STR = r"^#### ((?:HLFR|LLFR)-\d{5}) (.+)$"
PARENT_PATTERN_STR = r"^\*Parent: (.+)\*$"
PASSED_STR = "passed"
FAILED_STR = "failed"
SKIPPED_STR = "skipped"


def read_requirements() -> tuple:
    """Read the HLFRs and the LLFR parent links from the requirements.

    Inputs: none (reads docs/requirements/functional_requirements.md).
    Outputs: a tuple (hlfr_list, children_dict) where hlfr_list holds
        (ID, title) pairs in file order and children_dict maps each HLFR
        ID to the list of its child LLFR IDs.
    """
    with open(REQUIREMENTS_PATH_STR, encoding="utf-8") as requirement_file:
        line_list = requirement_file.read().splitlines()
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
    return hlfr_list, children_dict


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


def run_all_tests():
    """Discover and run every test in the tests folder.

    Inputs: none.
    Outputs: the RecordingResult of the run.
    """
    loader = unittest.TestLoader()
    suite = loader.discover(TESTS_FOLDER_STR, pattern="test_*.py",
                            top_level_dir=REPOSITORY_ROOT_STR)
    runner = unittest.TextTestRunner(resultclass=RecordingResult,
                                     verbosity=1)
    return runner.run(suite)


def hlfr_result(status_list: list) -> str:
    """Return the column 4 value for the statuses of one HLFR's tests.

    Inputs:
        status_list: the statuses of the tests linked to the HLFR.
    Outputs: "pass", "fail", "not run" or "no tests" (PCR-00023).
    """
    if not status_list:
        return "no tests"
    if FAILED_STR in status_list:
        return "fail"
    if SKIPPED_STR in status_list:
        return "not run"
    return "pass"


def build_matrix(test_status_list: list) -> tuple:
    """Build the test matrix table and the list of untested LLFRs.

    Inputs:
        test_status_list: the tuples returned by run_all_tests.
    Outputs: a tuple (markdown text, list of LLFR IDs without tests).
    """
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
            f"{hlfr_result(status_list)} |")
    environment_str = ("PyQt6 installed" if QT_AVAILABLE_B
                       else "PyQt6 not installed: GUI tests skipped")
    text_str = ("# Test matrix\n\n"
                "Generated by `tests/build_test_matrix.py` "
                f"({environment_str}). Do not edit by hand.\n\n"
                + "\n".join(row_list) + "\n")
    return text_str, sorted(set(untested_list))


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
        count_dict[status_str] += 1
        if status_str == FAILED_STR:
            print(f"::error title=Test failed::{test_id_str}")
    print(f"::notice title=Test totals::{count_dict[PASSED_STR]} passed, "
          f"{count_dict[FAILED_STR]} failed, "
          f"{count_dict[SKIPPED_STR]} skipped")
    if untested_list:
        print("::warning title=LLFRs without tests::"
              + ", ".join(untested_list))


def main() -> int:
    """Run the tests, write the matrix and report the result.

    Inputs: command-line arguments (see module docstring).
    Outputs: the process exit code (0 when every test passed).
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH_STR)
    parser.add_argument("--require-qt", action="store_true")
    argument_namespace = parser.parse_args()
    if argument_namespace.require_qt and not QT_AVAILABLE_B:
        print("PyQt6 is required but not installed.", file=sys.stderr)
        return 1
    test_result = run_all_tests()
    test_status_list = test_result.status_list
    matrix_str, untested_list = build_matrix(test_status_list)
    with open(argument_namespace.output, "w",
              encoding="utf-8") as matrix_file:
        matrix_file.write(matrix_str)
    report_to_github(test_status_list, untested_list)
    print(f"Test matrix written to {argument_namespace.output}")
    if untested_list:
        print("LLFRs without tests: " + ", ".join(untested_list))
    failed_b = any(status_str == FAILED_STR
                   for _, _, status_str in test_status_list)
    return 1 if failed_b or not test_result.wasSuccessful() else 0


if __name__ == "__main__":
    sys.exit(main())
