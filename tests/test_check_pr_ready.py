"""Self-tests for tests/check_pr_ready.py (PCR-00060 to PCR-00062)."""

import os
import subprocess
import tempfile
import unittest

from tests.check_pr_ready import (MATRIX_PATH_STR, branch_problems,
                                  matrix_problems, pull_request_target,
                                  source_hash)
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
        os.makedirs(os.path.join(self.folder_str, "tests"))
        self.write_file("code.py", "one\n")
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
        self.write_file("code.py", "two\n")
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


if __name__ == "__main__":
    unittest.main()
