"""Self-tests for tests/check_pr_ready.py (PCR-00060 to PCR-00062,
PCR-00064, PCR-00069, PCR-00070, PCR-00079, PCR-00081)."""

import os
import re
import subprocess
import tempfile
import unittest

from tests.check_pr_ready import (MATRIX_PATH_STR, TEST_CELL_PATTERN_STR,
                                  branch_problems, description_problems,
                                  fail_star_entries, matrix_problems,
                                  pull_request_target, source_hash,
                                  starts_with_fail_star_section)
from tests.support import covers


class MatrixProblemsTest(unittest.TestCase):
    """Check how a committed matrix is judged."""

    @covers("PCR-00061", "PCR-00062")
    def test_current_matrix_passes(self) -> None:
        """The right hash with no failed test is no problem.

        Inputs: none.
        Outputs: none.
        """
        text_str = "Source hash: `abc1`\n\n`a.test` passed `b.test` known\n"
        self.assertEqual(matrix_problems(text_str, "abc1"), [])

    @covers("PCR-00061")
    def test_old_or_missing_hash_fails(self) -> None:
        """A matrix built from other code is a problem.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(len(matrix_problems("Source hash: `abc1`\n", "ff")),
                         1)
        self.assertEqual(len(matrix_problems("No hash\n", "ff")), 1)

    @covers("PCR-00062")
    def test_failed_test_fails(self) -> None:
        """A matrix with a failed test is a problem.

        Inputs: none.
        Outputs: none.
        """
        text_str = "Source hash: `abc1`\n\n`a.test` failed\n"
        self.assertEqual(len(matrix_problems(text_str, "abc1")), 1)


ENVIRONMENT_ENTRY_STR = ("Environment, PyQt6: 2 tests shown as \"Fail* (PyQt6 "
                         "missing)\". PyQt6 cannot be installed in the "
                         "environment that built this matrix.")
NOT_IMPLEMENTED_ENTRY_STR = ("Not implemented, HLFR-00014: Fail* in column 4, "
                             "the implementation has not been done yet. "
                             "Waits for #190.")
FAIL_STAR_MATRIX_STR = (
    "# Test matrix\n\nSource hash: `abc1`\n\n## Fail* (PCR-00070)\n\n"
    f"- {ENVIRONMENT_ENTRY_STR}\n- {NOT_IMPLEMENTED_ENTRY_STR}\n\n"
    "| HLFR | LLFR | Tests (last run status) | Result |\n|---|---|---|---|\n"
    "| HLFR-00001 A | LLFR-00001 | `view.test_a` Fail* (PyQt6 missing)"
    "<br>`model.test_b` passed | Fail* (PyQt6 missing) |\n")


class FailStarMatrixTest(unittest.TestCase):
    """Check how a committed matrix with Fail* is judged."""

    @covers("PCR-00064")
    def test_environment_fail_star_counts_as_passed(self) -> None:
        """An environment Fail* isn't a failed test, into any branch.

        Inputs: none.
        Outputs: none.
        """
        text_str = FAIL_STAR_MATRIX_STR.replace(
            f"- {NOT_IMPLEMENTED_ENTRY_STR}\n", "")
        self.assertEqual(matrix_problems(text_str, "abc1", "develop"), [])
        self.assertEqual(matrix_problems(text_str, "abc1", "main"), [])

    @covers("PCR-00068", "PCR-00069")
    def test_not_implemented_only_into_develop(self) -> None:
        """A not-implemented Fail* goes into develop, never into main.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(
            matrix_problems(FAIL_STAR_MATRIX_STR, "abc1", "develop"), [])
        problem_list = matrix_problems(FAIL_STAR_MATRIX_STR, "abc1", "main")
        self.assertEqual(len(problem_list), 1)
        self.assertIn("HLFR-00014", problem_list[0])

    @covers("PCR-00061", "PCR-00063")
    def test_fail_star_cells_are_tests_of_the_matrix(self) -> None:
        """The comparison with the CI matrix sees the Fail* tests too.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(
            set(re.findall(TEST_CELL_PATTERN_STR, FAIL_STAR_MATRIX_STR)),
            {"view.test_a", "model.test_b"})


class FailStarDescriptionTest(unittest.TestCase):
    """Check the Fail* section at the top of the description."""

    @covers("PCR-00070")
    def test_entries_are_read(self) -> None:
        """The entries of the section are read, and nothing else.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(fail_star_entries(FAIL_STAR_MATRIX_STR),
                         [ENVIRONMENT_ENTRY_STR, NOT_IMPLEMENTED_ENTRY_STR])
        self.assertEqual(fail_star_entries("# Test matrix\n\n| a |\n"), [])

    @covers("PCR-00070")
    def test_complete_section_first_passes(self) -> None:
        """A description that starts with every entry passes.

        Inputs: none.
        Outputs: none.
        """
        body_str = (f"\n## Fail* (PCR-00070)\n\n- {ENVIRONMENT_ENTRY_STR}\n"
                    f"- {NOT_IMPLEMENTED_ENTRY_STR}\n\n## Summary\n\nText\n")
        self.assertTrue(starts_with_fail_star_section(body_str))
        self.assertEqual(description_problems(body_str, FAIL_STAR_MATRIX_STR),
                         [])

    @covers("PCR-00070")
    def test_section_not_first_or_incomplete_fails(self) -> None:
        """The section must be first and hold every entry.

        Inputs: none.
        Outputs: none.
        """
        late_body_str = (f"Closes #1\n\n## Fail* (PCR-00070)\n\n"
                         f"- {ENVIRONMENT_ENTRY_STR}\n"
                         f"- {NOT_IMPLEMENTED_ENTRY_STR}\n")
        self.assertFalse(starts_with_fail_star_section(late_body_str))
        self.assertEqual(
            len(description_problems(late_body_str, FAIL_STAR_MATRIX_STR)), 1)
        short_body_str = f"## Fail* (PCR-00070)\n\n- {ENVIRONMENT_ENTRY_STR}\n"
        problem_list = description_problems(short_body_str,
                                            FAIL_STAR_MATRIX_STR)
        self.assertEqual(len(problem_list), 1)
        self.assertIn("HLFR-00014", problem_list[0])
        self.assertEqual(len(description_problems("", FAIL_STAR_MATRIX_STR)),
                         1)

    @covers("PCR-00070")
    def test_matrix_without_fail_star_needs_no_section(self) -> None:
        """With no Fail* in the matrix, any description passes.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(description_problems(
            "Closes #1", "Source hash: `a`\n\n| a |\n"), [])


class TargetTest(unittest.TestCase):
    """Check which commands count as creating a pull request."""

    @covers("PCR-00061")
    def test_targets(self) -> None:
        """Base and head are read, and other commands give None.

        Inputs: none.
        Outputs: none.
        """
        for command_str, expected in (
                ("gh pr create --fill", ("main", "HEAD")),
                ("gh pr create --base develop --head x", ("develop", "x")),
                ("gh api repos/a/b/pulls -f base=develop -f head=y",
                 ("develop", "y")),
                ("gh api -X GET repos/a/b/pulls -f base=main", None),
                ("gh pr view 5", None),
                ("ls", None)):
            with self.subTest(command_str=command_str):
                self.assertEqual(pull_request_target(command_str), expected)


class BranchProblemsTest(unittest.TestCase):
    """Check a branch in a real temporary git repository."""

    def setUp(self) -> None:
        """Create a repository with a develop branch and a feature branch.

        Inputs: none.
        Outputs: none.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder_str = folder.name
        self.git("init", "-q")
        for folder_str in ("tests", "src", "docs"):
            os.makedirs(os.path.join(self.folder_str, folder_str))
        self.write_file("src/code.py", "one\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "first")
        self.git("update-ref", "refs/remotes/origin/develop", "HEAD")

    def git(self, *argument_tuple: str) -> None:
        """Run git in the temporary repository.

        Inputs:
            argument_tuple: the arguments of git.
        Outputs: none.
        """
        subprocess.run(["git", "-C", self.folder_str, "-c", "user.name=t",
                        "-c", "user.email=t@t"] + list(argument_tuple),
                       check=True, capture_output=True)

    def write_file(self, path_str: str, text_str: str) -> None:
        """Write a file of the temporary repository.

        Inputs:
            path_str: the path relative to the repository.
            text_str: the file's text.
        Outputs: none.
        """
        with open(os.path.join(self.folder_str, path_str), "w",
                  encoding="utf-8") as text_file:
            text_file.write(text_str)

    def commit_current_matrix(self) -> None:
        """Commit a matrix that holds the hash of the current commit.

        Inputs: none.
        Outputs: none.
        """
        hash_str = source_hash("HEAD", self.folder_str)
        self.write_file(MATRIX_PATH_STR, f"Source hash: `{hash_str}`\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "matrix")

    @covers("PCR-00060", "PCR-00061")
    def test_ready_branch_has_no_problem(self) -> None:
        """The matrix commit itself doesn't make the matrix old.

        Inputs: none.
        Outputs: none.
        """
        self.commit_current_matrix()
        self.assertEqual(
            branch_problems("develop", "HEAD", self.folder_str), [])

    @covers("PCR-00061")
    def test_code_after_the_matrix_is_a_problem(self) -> None:
        """A code commit after the matrix makes the matrix old.

        Inputs: none.
        Outputs: none.
        """
        self.commit_current_matrix()
        self.write_file("src/code.py", "two\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "more")
        self.assertEqual(
            len(branch_problems("develop", "HEAD", self.folder_str)), 1)

    @covers("PCR-00060")
    def test_branch_behind_develop_is_a_problem(self) -> None:
        """A newer develop is a problem into develop, not into main.

        Inputs: none.
        Outputs: none.
        """
        self.git("checkout", "-q", "-b", "feature")
        self.commit_current_matrix()
        self.git("checkout", "-q", "-b", "newer", "HEAD~1")
        self.write_file("other.py", "x\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "newer")
        self.git("update-ref", "refs/remotes/origin/develop", "HEAD")
        self.assertEqual(
            len(branch_problems("develop", "feature", self.folder_str)), 1)
        self.assertEqual(
            branch_problems("main", "feature", self.folder_str), [])

    @covers("PCR-00066", "PCR-00069")
    def test_listed_hlfr_is_a_problem_only_into_main(self) -> None:
        """An HLFR in tests/not_implemented.txt can't go into main.

        Inputs: none.
        Outputs: none.
        """
        self.write_file("tests/not_implemented.txt",
                        "# comment\n  # indented comment\n"
                        "HLFR-00014 Waits for #190.\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "list")
        self.commit_current_matrix()
        self.assertEqual(
            branch_problems("develop", "HEAD", self.folder_str), [])
        problem_list = branch_problems("main", "HEAD", self.folder_str)
        self.assertEqual(len(problem_list), 1)
        self.assertIn("HLFR-00014", problem_list[0])

    def commit_docs_change_after_develop_matrix(self) -> None:
        """Make develop hold a matrix, then change only a PCR-like file.

        Inputs: none.
        Outputs: none. origin/develop points at the matrix commit, and
            HEAD is one commit later that changes only docs/process.md.
        """
        self.commit_current_matrix()
        self.git("update-ref", "refs/remotes/origin/develop", "HEAD")
        self.write_file("docs/process.md", "new rule\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "docs")

    @covers("PCR-00079", "PCR-00081", "PCR-00061")
    def test_docs_only_branch_keeps_the_develop_matrix(self) -> None:
        """A branch that runs no test isn't asked for its own matrix.

        Inputs: none.
        Outputs: none.
        """
        self.commit_docs_change_after_develop_matrix()
        self.assertEqual(
            branch_problems("develop", "HEAD", self.folder_str), [])

    @covers("PCR-00058", "PCR-00061")
    def test_docs_only_branch_into_main_needs_its_matrix(self) -> None:
        """Into main every test runs, so the old hash is a problem.

        Inputs: none.
        Outputs: none.
        """
        self.commit_docs_change_after_develop_matrix()
        problem_list = branch_problems("main", "HEAD", self.folder_str)
        self.assertEqual(len(problem_list), 1)
        self.assertIn("PCR-00061", problem_list[0])

    @covers("PCR-00078", "PCR-00061")
    def test_code_branch_after_develop_matrix_is_a_problem(self) -> None:
        """A change under src after develop's matrix makes it old.

        Inputs: none.
        Outputs: none.
        """
        self.commit_docs_change_after_develop_matrix()
        self.write_file("src/code.py", "three\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "code")
        self.assertEqual(
            len(branch_problems("develop", "HEAD", self.folder_str)), 1)

    @covers("PCR-00079", "PCR-00062")
    def test_docs_only_branch_still_checks_failed_tests(self) -> None:
        """The checks that need no test run still apply.

        Inputs: none.
        Outputs: none.
        """
        self.write_file(MATRIX_PATH_STR, "Source hash: `0`\n`a.t` failed\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "matrix")
        self.git("update-ref", "refs/remotes/origin/develop", "HEAD")
        self.write_file("docs/process.md", "new rule\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "docs")
        problem_list = branch_problems("develop", "HEAD", self.folder_str)
        self.assertEqual(len(problem_list), 1)
        self.assertIn("PCR-00062", problem_list[0])


if __name__ == "__main__":
    unittest.main()
