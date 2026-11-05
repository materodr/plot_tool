"""Self-tests for tests/ci_changed_files.py (PCR-00057, PCR-00058,
PCR-00078 to PCR-00080, PCR-00083)."""

import os
import re
import subprocess
import tempfile
import unittest

from tests.ci_changed_files import (branch_needs_full_suite, changed_paths,
                                    needs_full_suite, path_needs_full_suite,
                                    pushed_paths)
from tests.support import covers

REPOSITORY_ROOT_STR = os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))
WORKFLOW_FOLDER_STR = os.path.join(REPOSITORY_ROOT_STR, ".github",
                                   "workflows")


def workflow_paths_filter(workflow_text_str: str) -> list:
    """Read the paths filter of the pull_request trigger of a workflow.

    Inputs:
        workflow_text_str: the text of a workflow file.
    Outputs: the entries of the first `paths:` list of the file, in their
        order, without their "- " and surrounding quotes.
    """
    path_list = []
    in_paths_b = False
    for line_str in workflow_text_str.splitlines():
        if re.match(r"^\s+paths:\s*$", line_str):
            in_paths_b = True
            continue
        if not in_paths_b:
            continue
        entry_match = re.match(r"^\s+-\s+['\"]?([^'\"]+?)['\"]?\s*$",
                               line_str)
        if not entry_match:
            break
        path_list.append(entry_match.group(1))
    return path_list


class PathRuleTest(unittest.TestCase):
    """Check which changed files run every test."""

    @covers("PCR-00078")
    def test_code_tests_and_build_files_run_every_test(self) -> None:
        """Each kind of file of PCR-00078 runs every test.

        Inputs: none.
        Outputs: none.
        """
        for path_str in (
                "src/main.py", "src/view/plot_view.py", "tests/support.py",
                "tests/test_matrix.md", "tests/user_tests/good/signals.csv",
                "tests/user_tests/bad/empty.xlsx", "bin/.gitkeep",
                ".github/workflows/tests.yml", "build_executable.py",
                "rebuild_and_launch.py", "requirements.txt",
                "requirements-build.txt",
                "docs/requirements/high_level_functional_requirements.md",
                "docs/requirements/low_level_functional_requirements.md"):
            with self.subTest(path_str=path_str):
                self.assertTrue(path_needs_full_suite(path_str))

    @covers("PCR-00079")
    def test_other_files_run_no_test(self) -> None:
        """COR, PCR, CLAUDE.md, skills and other Markdown files skip.

        Inputs: none.
        Outputs: none.
        """
        for path_str in (
                "docs/requirements/code_and_organization.md",
                "docs/requirements/process_of_collaboration.md",
                "docs/requirements/README.md", "CLAUDE.md", "README.md",
                ".claude/skills/requirement-validation/SKILL.md",
                ".claude/settings.json", ".github/ISSUE_TEMPLATE/fix.yml",
                ".github/CODEOWNERS", ".gitignore", "notes/src/x.py",
                "docs/src/requirements.txt"):
            with self.subTest(path_str=path_str):
                self.assertFalse(path_needs_full_suite(path_str))

    @covers("PCR-00078")
    def test_prefixes_match_whole_folder_names(self) -> None:
        """A file whose name only starts like a folder doesn't count.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(path_needs_full_suite("srcnotes.md"))
        self.assertFalse(path_needs_full_suite("tests.md"))
        self.assertFalse(path_needs_full_suite(
            "docs/requirements/high_level_functional_requirements.md.bak"))


class DecisionTest(unittest.TestCase):
    """Check the decision for a whole pull request."""

    @covers("PCR-00079")
    def test_only_other_files_skip_the_tests(self) -> None:
        """A branch that changes only PCR and COR files runs no test.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(needs_full_suite(
            ["docs/requirements/code_and_organization.md",
             "docs/requirements/process_of_collaboration.md"], "develop"))

    @covers("PCR-00078")
    def test_one_listed_file_runs_every_test(self) -> None:
        """One file of PCR-00078 among others runs every test.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(needs_full_suite(
            ["CLAUDE.md",
             "docs/requirements/low_level_functional_requirements.md"],
            "develop"))

    @covers("PCR-00058")
    def test_main_always_runs_every_test(self) -> None:
        """A pull request into main runs every test, whatever it changes.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(needs_full_suite(["CLAUDE.md"], "main"))

    @covers("PCR-00079")
    def test_push_follows_the_list_on_any_branch(self) -> None:
        """A push (no base branch) skips for docs, also on main.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(needs_full_suite(["CLAUDE.md"], ""))
        self.assertTrue(needs_full_suite(["src/main.py"], ""))

    @covers("PCR-00083", "PCR-00058")
    def test_matrix_only_change_skips_everywhere(self) -> None:
        """The matrix pull request and its merge run no test, into main too.

        Inputs: none.
        Outputs: none.
        """
        for base_str in ("main", "develop", ""):
            with self.subTest(base_str=base_str):
                self.assertFalse(needs_full_suite(["tests/test_matrix.md"],
                                                  base_str))
        self.assertTrue(needs_full_suite(
            ["tests/test_matrix.md", "CLAUDE.md"], "main"))
        self.assertTrue(needs_full_suite(
            ["tests/test_matrix.md", "src/main.py"], "develop"))

    @covers("PCR-00057")
    def test_no_changed_file_runs_every_test(self) -> None:
        """With no changed file to judge, every test runs.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(needs_full_suite([], "develop"))


class MacosFilterTest(unittest.TestCase):
    """Check that the macOS build filter agrees with PCR-00078."""

    @covers("PCR-00078")
    def test_macos_build_paths_also_run_every_test(self) -> None:
        """Every file that starts the macOS build also runs every test.

        Inputs: none.
        Outputs: none.
        """
        with open(os.path.join(WORKFLOW_FOLDER_STR, "macos_build.yml"),
                  encoding="utf-8") as workflow_file:
            path_list = workflow_paths_filter(workflow_file.read())
        self.assertGreater(len(path_list), 0)
        self.assertEqual(
            [path_str for path_str in path_list
             if not path_needs_full_suite(path_str)], [])


class ChangedPathsTest(unittest.TestCase):
    """Check the changed files read from a real temporary repository."""

    def setUp(self) -> None:
        """Create a repository whose first commit is origin/develop.

        Inputs: none.
        Outputs: none.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder_str = folder.name
        self.git("init", "-q")
        os.makedirs(os.path.join(self.folder_str, "src"))
        self.write_file("src/code.py", "one\n")
        self.write_file("CLAUDE.md", "rules\n")
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

    @covers("PCR-00079")
    def test_docs_only_branch_skips(self) -> None:
        """A commit that changes only CLAUDE.md runs no test.

        Inputs: none.
        Outputs: none.
        """
        self.write_file("CLAUDE.md", "more rules\n")
        self.git("commit", "-q", "-am", "docs")
        self.assertEqual(changed_paths("develop", "HEAD", self.folder_str),
                         ["CLAUDE.md"])
        self.assertFalse(branch_needs_full_suite("develop", "HEAD",
                                                 self.folder_str))

    @covers("PCR-00078")
    def test_renamed_code_file_runs_every_test(self) -> None:
        """Moving a file out of src counts both its old and new path.

        Inputs: none.
        Outputs: none.
        """
        self.git("mv", "src/code.py", "code.md")
        self.git("commit", "-q", "-m", "move")
        self.assertEqual(
            sorted(changed_paths("develop", "HEAD", self.folder_str)),
            ["code.md", "src/code.py"])
        self.assertTrue(branch_needs_full_suite("develop", "HEAD",
                                                self.folder_str))

    @covers("PCR-00079")
    def test_pushed_paths_compare_with_the_commit_before(self) -> None:
        """A push is judged on what it brought since the previous tip.

        Inputs: none.
        Outputs: none.
        """
        self.write_file("CLAUDE.md", "more rules\n")
        self.git("commit", "-q", "-am", "docs")
        self.assertEqual(pushed_paths("HEAD~1", "HEAD", self.folder_str),
                         ["CLAUDE.md"])
        with self.assertRaises(subprocess.CalledProcessError):
            pushed_paths("0" * 40, "HEAD", self.folder_str)

    @covers("PCR-00078")
    def test_git_failure_runs_every_test(self) -> None:
        """When git can't compare with the base, every test runs.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(branch_needs_full_suite("no-such-branch", "HEAD",
                                                self.folder_str))


if __name__ == "__main__":
    unittest.main()
