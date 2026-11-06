"""Reviewer's tests of issue #278 (PCR-00130, PCR-00131).

They cover two gaps of tests/test_install_local_wheels.py:
1. the CI checkout of a pull request is a merge commit whose second
   parent, the head of the pull request, is on no fetched branch; the
   fetch step of the workflows must still give every commit and ref that
   tests/ci_changed_files.py, tests/check_pr_ready.py and
   tests/check_requirement_review.py read;
2. the shard jobs of CI install only requirements.txt, which has no
   PyYAML, so a test module must import without it.
"""

import os
import subprocess
import sys
import tempfile
import unittest

from tests.support import REPOSITORY_ROOT_STR, covers

# The fetch step of the workflows, with the base branch filled in.
FETCH_ARGUMENT_LIST = ["fetch", "-q", "--no-tags", "--unshallow", "origin",
                       "+refs/heads/develop:refs/remotes/origin/develop"]


def run_git(folder_str: str, *argument_tuple: str) -> str:
    """Run a git command that must succeed and return its output.

    Inputs:
        folder_str: the folder to run git in.
        argument_tuple: the arguments that follow ``git``.
    Outputs: the standard output, without surrounding spaces.
    """
    identity_list = ["-c", "user.name=test", "-c", "user.email=test@test",
                     "-c", "init.defaultBranch=develop"]
    result = subprocess.run(["git", *identity_list, *argument_tuple],
                            cwd=folder_str, check=True,
                            capture_output=True, text=True)
    return result.stdout.strip()


def commit_file(folder_str: str, name_str: str, text_str: str) -> str:
    """Write a file, commit it and return the commit's SHA.

    Inputs:
        folder_str: the git folder.
        name_str: the file name.
        text_str: the content of the file.
    Outputs: the SHA of the new commit.
    """
    with open(os.path.join(folder_str, name_str), "w",
              encoding="utf-8") as out_file:
        out_file.write(text_str)
    run_git(folder_str, "add", name_str)
    run_git(folder_str, "commit", "-q", "-m", name_str)
    return run_git(folder_str, "rev-parse", "HEAD")


class MergeCommitCheckoutTest(unittest.TestCase):
    """The fetch step works on the merge commit that CI checks out."""

    def setUp(self) -> None:
        """Build a remote with develop, a feature branch, the merge ref of
        its pull request and an orphan ci-wheels branch.

        Inputs: none.
        Outputs: none.
        """
        self.temporary = tempfile.TemporaryDirectory()
        base_str = self.temporary.name
        source_str = os.path.join(base_str, "source")
        os.makedirs(source_str)
        run_git(source_str, "init", "-q")
        for index_i in range(3):
            commit_file(source_str, "base.txt", f"develop {index_i}\n")
        run_git(source_str, "checkout", "-q", "-b", "feature/1-x")
        commit_file(source_str, "feature.txt", "first\n")
        self.head_str = commit_file(source_str, "feature.txt", "second\n")
        run_git(source_str, "checkout", "-q", "develop")
        self.base_tip_str = commit_file(source_str, "base.txt", "moved\n")
        # The merge commit that GitHub keeps under refs/pull/<n>/merge:
        # first parent the base, second parent the head.
        run_git(source_str, "merge", "-q", "--no-ff", "--no-edit",
                "feature/1-x")
        merge_str = run_git(source_str, "rev-parse", "HEAD")
        run_git(source_str, "update-ref", "refs/pull/1/merge", merge_str)
        run_git(source_str, "reset", "-q", "--hard", self.base_tip_str)
        run_git(source_str, "checkout", "-q", "--orphan", "ci-wheels")
        commit_file(source_str, "big.whl", "wheel\n")
        self.wheels_str = run_git(source_str, "rev-parse", "HEAD")
        run_git(source_str, "checkout", "-q", "develop")
        self.checkout_str = os.path.join(base_str, "checkout")
        os.makedirs(self.checkout_str)
        run_git(self.checkout_str, "init", "-q")
        run_git(self.checkout_str, "remote", "add", "origin",
                "file://" + source_str)
        # What actions/checkout does on a pull request, depth 1.
        run_git(self.checkout_str, "fetch", "-q", "--no-tags", "--depth=1",
                "origin", f"+{merge_str}:refs/remotes/pull/1/merge")
        run_git(self.checkout_str, "checkout", "-q",
                "refs/remotes/pull/1/merge")
        run_git(self.checkout_str, *FETCH_ARGUMENT_LIST)

    def tearDown(self) -> None:
        """Remove the temporary folders.

        Inputs: none.
        Outputs: none.
        """
        self.temporary.cleanup()

    @covers("PCR-00130")
    def test_head_history_and_base_are_complete(self) -> None:
        """The head of the pull request and the base are fully there.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(run_git(self.checkout_str,
                                 "rev-parse", "--is-shallow-repository"),
                         "false")
        self.assertEqual(run_git(self.checkout_str, "rev-parse",
                                 "origin/develop"), self.base_tip_str)
        self.assertEqual(run_git(self.checkout_str, "rev-list", "--count",
                                 self.head_str), "5")
        missing = subprocess.run(["git", "cat-file", "-e", self.wheels_str],
                                 cwd=self.checkout_str, capture_output=True)
        self.assertNotEqual(missing.returncode, 0)

    @covers("PCR-00130")
    def test_commands_of_the_check_scripts_work(self) -> None:
        """The git commands of the check scripts run on the head commit.

        Inputs: none.
        Outputs: none.
        """
        changed_str = run_git(self.checkout_str, "diff", "--name-only",
                              "--no-renames",
                              f"origin/develop...{self.head_str}")
        self.assertEqual(changed_str, "feature.txt")
        self.assertEqual(run_git(self.checkout_str, "show",
                                 f"{self.head_str}:feature.txt"), "second")
        self.assertIn("feature.txt", run_git(self.checkout_str, "ls-tree",
                                             "-r", self.head_str))
        # The base moved after the branch left it: the up-to-date check
        # of tests/check_pr_ready.py must see it.
        behind = subprocess.run(
            ["git", "merge-base", "--is-ancestor", "origin/develop",
             self.head_str], cwd=self.checkout_str, capture_output=True)
        self.assertEqual(behind.returncode, 1)


class ImportWithoutYamlTest(unittest.TestCase):
    """The new test module imports where PyYAML isn't installed."""

    @covers("PCR-00130")
    def test_module_imports_without_pyyaml(self) -> None:
        """CI's shards have no PyYAML (it isn't in requirements.txt).

        Inputs: none.
        Outputs: none.
        """
        code_str = ("import sys; sys.modules['yaml'] = None; "
                    "import tests.test_install_local_wheels")
        result = subprocess.run([sys.executable, "-c", code_str],
                                cwd=REPOSITORY_ROOT_STR,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr[-500:])


if __name__ == "__main__":
    unittest.main()
