"""Self-tests for tests/check_pr_ready.py (PCR-00060, PCR-00062,
PCR-00064, PCR-00065, PCR-00069, PCR-00070, PCR-00081, PCR-00085)."""

import os
import subprocess
import tempfile
import unittest

from tests.build_test_matrix import fail_star_section
from tests.check_pr_ready import (MATRIX_PATH_STR, NO_FAIL_STAR_SECTION_STR,
                                  branch_problems, command_body,
                                  description_problems, expected_entries,
                                  green_light_problems,
                                  fail_star_entries, listed_explanations,
                                  not_implemented_entries,
                                  pull_request_target, run_matrix_problems,
                                  source_hash,
                                  starts_with_fail_star_section)
from tests.support import covers

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
PLAIN_MATRIX_STR = ("# Test matrix\n\nSource hash: `abc1`\n\n"
                    "| HLFR | LLFR | Tests (last run status) | Result |\n"
                    "|---|---|---|---|\n"
                    "| HLFR-00001 A | LLFR-00001 | `a.test` passed<br>"
                    "`b.test` known macOS failure | pass |\n")


def section_body(entry_list: list, rest_str: str = "## Summary\n") -> str:
    """Write a description that starts with a Fail* section.

    Inputs:
        entry_list: the entry texts of the section, without "- ".
        rest_str: the text after the section.
    Outputs: the description text.
    """
    return ("## Fail* (PCR-00070)\n\n"
            + "".join(f"- {entry_str}\n" for entry_str in entry_list)
            + "\n" + rest_str)


class RunMatrixProblemsTest(unittest.TestCase):
    """Check how the matrix of a CI run is judged."""

    @covers("PCR-00062")
    def test_matrix_with_no_failed_test_passes(self) -> None:
        """Passed tests and known macOS failures are no problem.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(run_matrix_problems(PLAIN_MATRIX_STR, "develop"), [])
        self.assertEqual(run_matrix_problems(PLAIN_MATRIX_STR, "main"), [])

    @covers("PCR-00062")
    def test_failed_test_fails(self) -> None:
        """A matrix with a failed test is a problem into any branch.

        Inputs: none.
        Outputs: none.
        """
        text_str = PLAIN_MATRIX_STR.replace("`a.test` passed",
                                            "`a.test` failed")
        self.assertEqual(len(run_matrix_problems(text_str, "develop")), 1)
        self.assertEqual(len(run_matrix_problems(text_str, "main")), 1)

    @covers("PCR-00064", "PCR-00068")
    def test_fail_star_is_accepted_into_develop(self) -> None:
        """Both kinds of Fail* can go into develop.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(
            run_matrix_problems(FAIL_STAR_MATRIX_STR, "develop"), [])

    @covers("PCR-00069", "PCR-00064")
    def test_no_fail_star_of_any_kind_into_main(self) -> None:
        """Into main, an environment and a not-implemented Fail* both fail.

        Inputs: none.
        Outputs: none.
        """
        problem_list = run_matrix_problems(FAIL_STAR_MATRIX_STR, "main")
        self.assertEqual(len(problem_list), 2)
        self.assertIn("Environment, PyQt6", problem_list[0])
        self.assertIn("HLFR-00014", problem_list[1])


class FailStarEntryTest(unittest.TestCase):
    """Check how the Fail* entries are read and written."""

    @covers("PCR-00070")
    def test_entries_are_read(self) -> None:
        """The entries of the section are read, and nothing else.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(fail_star_entries(FAIL_STAR_MATRIX_STR),
                         [ENVIRONMENT_ENTRY_STR, NOT_IMPLEMENTED_ENTRY_STR])
        self.assertEqual(fail_star_entries(PLAIN_MATRIX_STR), [])
        self.assertEqual(fail_star_entries(NO_FAIL_STAR_SECTION_STR),
                         ["none"])

    @covers("PCR-00066")
    def test_list_is_read_without_comments(self) -> None:
        """The list gives each HLFR with its explanation.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(
            listed_explanations("# comment\n  # HLFR-00001 no\n\n"
                                "HLFR-00014 Waits for #190.\n"),
            {"HLFR-00014": "Waits for #190."})

    @covers("PCR-00065", "PCR-00070")
    def test_entries_match_the_matrix_builder(self) -> None:
        """The check writes the same entries as the matrix builder.

        Inputs: none.
        Outputs: none.
        """
        explanation_dict = {"HLFR-00014": "Waits for #190.",
                            "HLFR-00002": "Later."}
        self.assertEqual(
            not_implemented_entries(explanation_dict),
            fail_star_entries(fail_star_section([], explanation_dict)))
        self.assertIn(NOT_IMPLEMENTED_ENTRY_STR, not_implemented_entries(
            {"HLFR-00014": "Waits for #190."}))


class FailStarDescriptionTest(unittest.TestCase):
    """Check the Fail* section at the top of the description."""

    @covers("PCR-00070")
    def test_none_section_passes(self) -> None:
        """With no Fail*, the section with "- none" passes everywhere.

        Inputs: none.
        Outputs: none.
        """
        body_str = NO_FAIL_STAR_SECTION_STR + "\n## Summary\n\nText\n"
        self.assertTrue(starts_with_fail_star_section(body_str))
        self.assertEqual(description_problems(body_str, [], "develop"), [])
        self.assertEqual(description_problems(body_str, [], "main"), [])

    @covers("PCR-00070")
    def test_section_is_always_required(self) -> None:
        """A description with no section, or not first, fails.

        Inputs: none.
        Outputs: none.
        """
        for body_str in ("", "Closes #1",
                         "Closes #1\n\n" + NO_FAIL_STAR_SECTION_STR):
            with self.subTest(body_str=body_str):
                problem_list = description_problems(body_str, [], "develop")
                self.assertEqual(len(problem_list), 1)
                self.assertIn("- none", problem_list[0])

    @covers("PCR-00070")
    def test_empty_section_or_none_with_entries_fails(self) -> None:
        """The section holds "none" alone, or only real entries.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(len(description_problems(section_body([]), [])), 1)
        self.assertEqual(len(description_problems(
            section_body(["none", ENVIRONMENT_ENTRY_STR]), [])), 1)

    @covers("PCR-00070", "PCR-00065")
    def test_missing_expected_entry_fails(self) -> None:
        """Every expected entry must be in the section.

        Inputs: none.
        Outputs: none.
        """
        problem_list = description_problems(
            section_body(["none"]), [NOT_IMPLEMENTED_ENTRY_STR])
        self.assertEqual(len(problem_list), 1)
        self.assertIn("HLFR-00014", problem_list[0])
        self.assertEqual(description_problems(
            section_body([NOT_IMPLEMENTED_ENTRY_STR]),
            [NOT_IMPLEMENTED_ENTRY_STR]), [])

    @covers("PCR-00065")
    def test_unlisted_not_implemented_entry_fails(self) -> None:
        """A not-implemented entry needs its HLFR in the list.

        Inputs: none.
        Outputs: none.
        """
        problem_list = description_problems(
            section_body([NOT_IMPLEMENTED_ENTRY_STR]), [])
        self.assertEqual(len(problem_list), 1)
        self.assertIn("not_implemented.txt", problem_list[0])

    @covers("PCR-00064", "PCR-00070")
    def test_declared_environment_entry_into_develop_passes(self) -> None:
        """An environment entry the check doesn't know is kept into develop.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(description_problems(
            section_body([ENVIRONMENT_ENTRY_STR]), [], "develop"), [])

    @covers("PCR-00069")
    def test_any_entry_into_main_fails(self) -> None:
        """Into main, the section holds only "none".

        Inputs: none.
        Outputs: none.
        """
        for entry_str in (ENVIRONMENT_ENTRY_STR, NOT_IMPLEMENTED_ENTRY_STR):
            with self.subTest(entry_str=entry_str):
                problem_list = description_problems(
                    section_body([entry_str]), [entry_str], "main")
                self.assertEqual(len(problem_list), 1)
                self.assertIn("PCR-00069", problem_list[0])


HEAD_SHA_STR = "a" * 40
OTHER_SHA_STR = "b" * 40


class GreenLightTest(unittest.TestCase):
    """Check the green-light record of a pull request into develop."""

    @covers("PCR-00111", "PCR-00112")
    def test_green_light_of_the_head_passes(self) -> None:
        """The last green-light line names the head commit.

        Inputs: none.
        Outputs: none.
        """
        for line_str in (f"Green light: {HEAD_SHA_STR}",
                         f"Green light: `{HEAD_SHA_STR}`"):
            with self.subTest(line_str=line_str):
                self.assertEqual(green_light_problems(
                    f"Text\n{line_str}\n", HEAD_SHA_STR), [])
        self.assertEqual(green_light_problems(
            f"Green light: {OTHER_SHA_STR}\nGreen light: {HEAD_SHA_STR}\n",
            HEAD_SHA_STR), [])

    @covers("PCR-00105", "PCR-00106", "PCR-00112")
    def test_commit_after_the_green_light_fails(self) -> None:
        """A head that isn't the green-light commit goes back.

        Inputs: none.
        Outputs: none.
        """
        problem_list = green_light_problems(
            f"Green light: {OTHER_SHA_STR}\n", HEAD_SHA_STR)
        self.assertEqual(len(problem_list), 1)
        self.assertIn("PCR-00105", problem_list[0])

    @covers("PCR-00111")
    def test_missing_green_light_fails(self) -> None:
        """A pull request into develop needs the green-light line.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(len(green_light_problems("Closes #1",
                                                  HEAD_SHA_STR)), 1)
        self.assertEqual(len(green_light_problems(
            "Green light: abc\n", HEAD_SHA_STR)), 1)

    @covers("PCR-00087", "PCR-00112")
    def test_main_and_matrix_branches_need_no_green_light(self) -> None:
        """Releases and the matrix pull request into develop are exempt.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(green_light_problems("", HEAD_SHA_STR, "main"), [])
        self.assertEqual(green_light_problems(
            "", HEAD_SHA_STR, "develop", "test-matrix/254-develop"), [])


class TargetTest(unittest.TestCase):
    """Check which commands count as creating a pull request."""

    @covers("PCR-00060", "PCR-00081")
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
        """Create a repository whose first commit is origin/develop.

        Inputs: none.
        Outputs: none. The first commit holds src/code.py and the matrix
            that CI committed to develop.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder_str = folder.name
        self.git("init", "-q")
        for folder_str in ("tests", "src", "docs"):
            os.makedirs(os.path.join(self.folder_str, folder_str))
        self.write_file("src/code.py", "one\n")
        self.write_file(MATRIX_PATH_STR, "# Test matrix built by CI\n")
        self.commit("first")
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

    def commit(self, message_str: str) -> None:
        """Commit every change of the temporary repository.

        Inputs:
            message_str: the commit message.
        Outputs: none.
        """
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message_str)

    @covers("PCR-00060", "PCR-00081")
    def test_code_branch_has_no_problem(self) -> None:
        """A branch that changes code and not the matrix is ready.

        Inputs: none.
        Outputs: none.
        """
        self.write_file("src/code.py", "two\n")
        self.commit("code")
        self.assertEqual(
            branch_problems("develop", "HEAD", self.folder_str), [])

    @covers("PCR-00081", "PCR-00061")
    def test_branch_that_changes_the_matrix_fails(self) -> None:
        """Only CI writes the matrix; the message names the file.

        Inputs: none.
        Outputs: none.
        """
        self.write_file(MATRIX_PATH_STR, "# Built on the branch\n")
        self.commit("matrix")
        problem_list = branch_problems("develop", "HEAD", self.folder_str)
        self.assertEqual(len(problem_list), 1)
        self.assertIn(MATRIX_PATH_STR, problem_list[0])
        self.assertIn(f"git checkout origin/develop -- {MATRIX_PATH_STR}",
                      problem_list[0])

    @covers("PCR-00081", "PCR-00060")
    def test_matrix_merged_from_develop_is_no_problem(self) -> None:
        """A new CI matrix on develop, merged into the branch, is fine.

        Inputs: none.
        Outputs: none.
        """
        self.git("checkout", "-q", "-b", "feature")
        self.write_file("src/code.py", "two\n")
        self.commit("code")
        self.git("checkout", "-q", "-b", "develop_tip", "HEAD~1")
        self.write_file(MATRIX_PATH_STR, "# Newer CI matrix\n")
        self.commit("Update test matrix from CI run 1")
        self.git("update-ref", "refs/remotes/origin/develop", "HEAD")
        self.git("checkout", "-q", "feature")
        self.git("merge", "-q", "--no-edit", "develop_tip")
        self.assertEqual(
            branch_problems("develop", "feature", self.folder_str), [])

    @covers("PCR-00085", "PCR-00081")
    def test_test_matrix_branch_may_change_only_the_matrix(self) -> None:
        """The matrix pull request into develop changes only the matrix.

        Inputs: none.
        Outputs: none.
        """
        self.write_file(MATRIX_PATH_STR, "# Matrix of the release run\n")
        self.commit("Update the test matrix from the release #254")
        self.assertEqual(branch_problems(
            "develop", "HEAD", self.folder_str, "test-matrix/254-develop"),
            [])
        self.assertEqual(len(branch_problems(
            "develop", "HEAD", self.folder_str, "feature/1-x")), 1)
        self.write_file("src/code.py", "sneaked in\n")
        self.commit("code")
        problem_list = branch_problems("develop", "HEAD", self.folder_str,
                                       "test-matrix/254-develop")
        self.assertEqual(len(problem_list), 1)
        self.assertIn("PCR-00085", problem_list[0])

    @covers("PCR-00070", "PCR-00065")
    def test_expected_entries_come_from_the_list_and_the_run(self) -> None:
        """The list of the head and the environment Fail* of the run.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(expected_entries("HEAD", self.folder_str), [])
        self.write_file("tests/not_implemented.txt",
                        "HLFR-00014 Waits for #190.\n")
        self.commit("list")
        self.assertEqual(
            expected_entries("HEAD", self.folder_str, FAIL_STAR_MATRIX_STR),
            [NOT_IMPLEMENTED_ENTRY_STR, ENVIRONMENT_ENTRY_STR])

    @covers("PCR-00070")
    def test_hook_reads_the_description_file(self) -> None:
        """The hook finds the description in -F body=@ and --body-file.

        Inputs: none.
        Outputs: none.
        """
        self.write_file("body.md", NO_FAIL_STAR_SECTION_STR)
        for command_str in (
                "gh api repos/a/b/pulls -f base=develop -F body=@body.md",
                "gh pr create --base develop --body-file body.md"):
            with self.subTest(command_str=command_str):
                self.assertEqual(command_body(command_str, self.folder_str),
                                 NO_FAIL_STAR_SECTION_STR)
        self.assertEqual(command_body("gh pr create --body 'x'",
                                      self.folder_str), "")

    @covers("PCR-00060")
    def test_branch_behind_develop_is_a_problem(self) -> None:
        """A newer develop is a problem into develop, not into main.

        Inputs: none.
        Outputs: none.
        """
        self.git("checkout", "-q", "-b", "feature")
        self.write_file("src/code.py", "two\n")
        self.commit("code")
        self.git("checkout", "-q", "-b", "newer", "HEAD~1")
        self.write_file("src/other.py", "x\n")
        self.commit("newer")
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
        self.commit("list")
        self.assertEqual(
            branch_problems("develop", "HEAD", self.folder_str), [])
        problem_list = branch_problems("main", "HEAD", self.folder_str)
        self.assertEqual(len(problem_list), 1)
        self.assertIn("HLFR-00014", problem_list[0])

    @covers("PCR-00061")
    def test_hash_ignores_the_matrix(self) -> None:
        """The hash that the matrix shows doesn't depend on the matrix.

        Inputs: none.
        Outputs: none.
        """
        first_hash_str = source_hash("HEAD", self.folder_str)
        self.write_file(MATRIX_PATH_STR, "# Another matrix\n")
        self.commit("matrix")
        self.assertEqual(source_hash("HEAD", self.folder_str), first_hash_str)
        self.write_file("src/code.py", "two\n")
        self.commit("code")
        self.assertNotEqual(source_hash("HEAD", self.folder_str),
                            first_hash_str)


if __name__ == "__main__":
    unittest.main()
