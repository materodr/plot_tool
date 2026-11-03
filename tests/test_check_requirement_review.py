"""Self-tests for tests/check_requirement_review.py (PCR-00050 to
PCR-00053)."""

import io
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from tests.check_requirement_review import (DEVELOP_HEADING_STR,
                                            DEVELOP_SCOPE_DICT,
                                            MAIN_HEADING_STR, MAIN_SCOPE_DICT,
                                            added_requirement_ids,
                                            has_review_section, main,
                                            missing_scope, run_hook)
from tests.support import covers

MODULE_STR = "tests.check_requirement_review"
MAIN_BODY_STR = (f"Release.\n\n## {MAIN_HEADING_STR}\n"
                 "Scope: all. Result: pass.\n")
DEVELOP_BODY_STR = (f"Feature.\n\n## {DEVELOP_HEADING_STR}\n"
                    "Scope: PCR-00052. Result: pass.\n")
BAD_BODY_STR = "No review.\n"


class ReviewSectionTest(unittest.TestCase):
    """Check how a pull request description is read."""

    @covers("PCR-00051")
    def test_section_with_content_passes(self) -> None:
        """A heading with text below it counts.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(has_review_section(MAIN_BODY_STR, MAIN_HEADING_STR))

    @covers("PCR-00051", "PCR-00053")
    def test_each_scope_has_its_own_heading(self) -> None:
        """The section of one scope doesn't count for the other.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(has_review_section(MAIN_BODY_STR,
                                            DEVELOP_HEADING_STR))
        self.assertFalse(has_review_section(DEVELOP_BODY_STR,
                                            MAIN_HEADING_STR))
        self.assertTrue(has_review_section(DEVELOP_BODY_STR,
                                           DEVELOP_HEADING_STR))

    @covers("PCR-00051")
    def test_windows_line_ends_pass(self) -> None:
        """A description written on the GitHub website has CRLF line ends.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(has_review_section(
            MAIN_BODY_STR.replace("\n", "\r\n"), MAIN_HEADING_STR))

    @covers("PCR-00051")
    def test_missing_section_fails(self) -> None:
        """A description without the heading doesn't count.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(has_review_section(BAD_BODY_STR, MAIN_HEADING_STR))

    @covers("PCR-00051")
    def test_empty_section_fails(self) -> None:
        """A heading with nothing below it doesn't count.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(has_review_section(f"## {MAIN_HEADING_STR}\n\n",
                                            MAIN_HEADING_STR))

    @covers("PCR-00051")
    def test_section_followed_by_heading_fails(self) -> None:
        """Text under the next heading isn't the section's content.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(has_review_section(
            f"## {MAIN_HEADING_STR}\n\n## Other\nText\n", MAIN_HEADING_STR))

    @covers("PCR-00051")
    def test_mention_in_a_sentence_fails(self) -> None:
        """Naming the section in a sentence doesn't count.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(has_review_section(
            f"This has no {MAIN_HEADING_STR} section.\nMore text.\n",
            MAIN_HEADING_STR))


class AddedRequirementsTest(unittest.TestCase):
    """Check which requirements count as added, in a real git repository."""

    def setUp(self) -> None:
        """Create a repository whose develop holds two requirements.

        Inputs: none.
        Outputs: none.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder_str = folder.name
        self.git("init", "-q")
        os.makedirs(os.path.join(self.folder_str, "docs", "requirements"))
        self.write_file("### PCR-00001 Host\nOld.\n\n"
                        "### PCR-00002 Other\nOld.\n")
        self.commit()
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

    def write_file(self, text_str: str,
                   name_str: str = "process_of_collaboration.md") -> None:
        """Write a file of docs/requirements.

        Inputs:
            text_str: the file's text.
            name_str: the file's name.
        Outputs: none.
        """
        path_str = os.path.join(self.folder_str, "docs", "requirements",
                                name_str)
        with open(path_str, "w", encoding="utf-8") as text_file:
            text_file.write(text_str)

    def commit(self) -> None:
        """Commit everything in the temporary repository.

        Inputs: none.
        Outputs: none.
        """
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "change")

    def added(self) -> list:
        """Find what the current branch adds to develop.

        Inputs: none.
        Outputs: the added requirement IDs.
        """
        return added_requirement_ids("develop", "HEAD", self.folder_str)

    @covers("PCR-00052")
    def test_new_requirement_counts(self) -> None:
        """Only the new heading is listed.

        Inputs: none.
        Outputs: none.
        """
        self.write_file("### PCR-00001 Host\nOld.\n\n"
                        "### PCR-00002 Other\nOld.\n\n"
                        "### PCR-00003 New\nNew.\n")
        self.commit()
        self.assertEqual(self.added(), ["PCR-00003"])

    @covers("PCR-00052")
    def test_changed_requirement_does_not_count(self) -> None:
        """Changing a requirement's text or title adds nothing.

        Inputs: none.
        Outputs: none.
        """
        self.write_file("### PCR-00001 Renamed\nChanged.\n\n"
                        "### PCR-00002 Other\nOld.\n")
        self.commit()
        self.assertEqual(self.added(), [])

    @covers("PCR-00052")
    def test_readme_examples_do_not_count(self) -> None:
        """The examples in the requirements README aren't requirements.

        Inputs: none.
        Outputs: none.
        """
        self.write_file("### COR-00001 Example\nText.\n", "README.md")
        self.commit()
        self.assertEqual(self.added(), [])

    @covers("PCR-00052")
    def test_unknown_branch_gives_none(self) -> None:
        """A branch git can't find is reported, not read as no requirement.

        Inputs: none.
        Outputs: none.
        """
        self.assertIsNone(added_requirement_ids("develop", "missing",
                                                self.folder_str))


class CommandTest(unittest.TestCase):
    """Check which shell commands the hook lets run."""

    def setUp(self) -> None:
        """Create a folder with description files.

        Inputs: none.
        Outputs: none.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder_str = folder.name
        for name_str, text_str in (("main.md", MAIN_BODY_STR),
                                   ("develop.md", DEVELOP_BODY_STR),
                                   ("bad.md", BAD_BODY_STR)):
            path_str = os.path.join(self.folder_str, name_str)
            with open(path_str, "w", encoding="utf-8") as text_file:
                text_file.write(text_str)

    def missing(self, command_str: str, added_id_list: list = None) -> dict:
        """Check a command in the temporary folder.

        Inputs:
            command_str: the shell command.
            added_id_list: what the branch adds, by default nothing.
        Outputs: the scope whose section is missing, or an empty dict.
        """
        with mock.patch(f"{MODULE_STR}.added_requirement_ids",
                        return_value=added_id_list or []):
            return missing_scope(command_str, self.folder_str)

    @covers("PCR-00051", "PCR-00053")
    def test_other_commands_run(self) -> None:
        """Commands that create no pull request are never blocked.

        Inputs: none.
        Outputs: none.
        """
        for command_str in ("ls", "git push origin develop",
                            "gh pr view 5", "gh pr list --base main",
                            "gh api repos/a/b/pulls",
                            "gh api -X GET repos/a/b/pulls -f base=main",
                            'git commit -m "explain gh pr create --base main"',
                            "grep -n 'gh pr create' README.md"):
            with self.subTest(command_str=command_str):
                self.assertEqual(self.missing(command_str, ["PCR-00001"]), {})

    @covers("PCR-00051")
    def test_pull_request_into_main_needs_the_section(self) -> None:
        """Every way of targeting main without the section is blocked.

        Inputs: none.
        Outputs: none.
        """
        for command_str in ("gh pr create --base main --body-file bad.md",
                            'gh pr create --base "main" --fill',
                            "gh pr create -B main --body 'Release'",
                            "cd x && gh pr create --base main --fill",
                            "GH_TOKEN=abc gh pr create --base main --fill",
                            "gh pr create --body-file bad.md",
                            "gh pr create --base main --body-file none.md",
                            'gh pr create --base main --body-file "$BODY"',
                            "gh pr create --base main --body-file develop.md",
                            "gh api repos/a/b/pulls -f base=main -f body=x",
                            "gh api repos/a/b/pulls -f base=main "
                            "-F body=@bad.md"):
            with self.subTest(command_str=command_str):
                self.assertEqual(self.missing(command_str), MAIN_SCOPE_DICT)

    @covers("PCR-00051")
    def test_pull_request_into_main_with_the_section_runs(self) -> None:
        """A description in a file or in the command itself is read.

        Inputs: none.
        Outputs: none.
        """
        heredoc_str = ("gh pr create --base main --body-file - <<'EOF'\n"
                       f"{MAIN_BODY_STR}EOF\n")
        for command_str in ("gh pr create --base main --body-file main.md",
                            "gh pr create --body-file main.md",
                            heredoc_str,
                            "gh pr create --base main --body "
                            f"'## {MAIN_HEADING_STR}\nResult: pass'",
                            "gh api repos/a/b/pulls -f base=main "
                            "-F body=@main.md"):
            with self.subTest(command_str=command_str):
                self.assertEqual(self.missing(command_str), {})

    @covers("PCR-00053")
    def test_develop_branch_with_no_new_requirement_runs(self) -> None:
        """A branch that adds no requirement needs no section.

        Inputs: none.
        Outputs: none.
        """
        for command_str in ("gh pr create --base develop --body-file bad.md",
                            "gh pr create --base=develop --fill",
                            "gh pr create -B develop --fill",
                            "gh api repos/a/b/pulls -f base=develop"):
            with self.subTest(command_str=command_str):
                self.assertEqual(self.missing(command_str), {})

    @covers("PCR-00053")
    def test_develop_branch_with_new_requirement_needs_the_section(
            self) -> None:
        """A branch that adds a requirement is blocked without the section.

        Inputs: none.
        Outputs: none.
        """
        for command_str in ("gh pr create --base develop --body-file bad.md",
                            "gh pr create --base develop --body-file main.md",
                            "gh pr create -B develop --fill",
                            "gh api repos/a/b/pulls -f base=develop"):
            with self.subTest(command_str=command_str):
                self.assertEqual(self.missing(command_str, ["PCR-00052"]),
                                 DEVELOP_SCOPE_DICT)

    @covers("PCR-00053")
    def test_develop_branch_with_new_requirement_and_section_runs(
            self) -> None:
        """A branch that adds a requirement runs with the section.

        Inputs: none.
        Outputs: none.
        """
        for command_str in ("gh pr create --base develop "
                            "--body-file develop.md",
                            "gh pr create --base develop --body "
                            f"'## {DEVELOP_HEADING_STR}\nResult: pass'",
                            "gh api repos/a/b/pulls -f base=develop "
                            "-F body=@develop.md"):
            with self.subTest(command_str=command_str):
                self.assertEqual(self.missing(command_str, ["PCR-00052"]), {})

    @covers("PCR-00053")
    def test_head_option_names_the_branch_to_compare(self) -> None:
        """The --head branch is compared, not the current checkout.

        Inputs: none.
        Outputs: none.
        """
        with mock.patch(f"{MODULE_STR}.added_requirement_ids",
                        return_value=[]) as added_mock:
            missing_scope("gh pr create --base develop --head feature/1-x "
                          "--fill", self.folder_str)
        added_mock.assert_called_once_with("develop", "feature/1-x",
                                           self.folder_str)

    @covers("PCR-00051", "PCR-00053")
    def test_other_base_branch_runs(self) -> None:
        """A pull request into another branch needs no section.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.missing("gh pr create --base feature/1-x --fill",
                                      ["PCR-00052"]), {})

    @covers("PCR-00051", "PCR-00053")
    def test_api_input_file_is_read(self) -> None:
        """The base and description of a gh api --input file are used.

        Inputs: none.
        Outputs: none.
        """
        for name_str, input_dict, expected_dict in (
                ("a.json", {"base": "main", "body": MAIN_BODY_STR}, {}),
                ("b.json", {"base": "main", "body": BAD_BODY_STR},
                 MAIN_SCOPE_DICT),
                ("c.json", {"base": "develop", "body": DEVELOP_BODY_STR}, {}),
                ("d.json", {"base": "develop", "body": BAD_BODY_STR},
                 DEVELOP_SCOPE_DICT)):
            path_str = os.path.join(self.folder_str, name_str)
            with open(path_str, "w", encoding="utf-8") as input_file:
                json.dump(input_dict, input_file)
            with self.subTest(name_str=name_str):
                self.assertEqual(
                    self.missing(f"gh api repos/a/b/pulls --input {name_str}",
                                 ["PCR-00052"]),
                    expected_dict)


class EntryPointTest(unittest.TestCase):
    """Check the exit codes of the hook and of the CI check."""

    def run_hook_with(self, stdin_str: str) -> tuple:
        """Run the hook with a text on standard input.

        Inputs:
            stdin_str: the text the hook reads.
        Outputs: a tuple of the exit code and what the hook wrote to
            standard error.
        """
        error_stream = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(stdin_str)), \
                mock.patch("sys.stderr", error_stream):
            exit_code_i = run_hook()
        return exit_code_i, error_stream.getvalue()

    def run_body_check(self, text_str: str, base_str: str,
                       added_id_list: list = None) -> int:
        """Run the CI check on a description.

        Inputs:
            text_str: the description.
            base_str: the branch the pull request goes into.
            added_id_list: what git reports that the branch adds.
        Outputs: the exit code.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path_str = os.path.join(folder.name, "body.md")
        with open(path_str, "w", encoding="utf-8") as body_file:
            body_file.write(text_str)
        argument_list = ["check", "--body-file", path_str, "--base", base_str,
                         "--head", "abc"]
        with mock.patch("sys.argv", argument_list), \
                mock.patch("sys.stdout", io.StringIO()), \
                mock.patch(f"{MODULE_STR}.added_requirement_ids",
                           return_value=added_id_list):
            return main()

    @covers("PCR-00050", "PCR-00051")
    def test_hook_blocks_main_with_code_2(self) -> None:
        """The message for main names the skill and every requirement.

        Inputs: none.
        Outputs: none.
        """
        exit_code_i, error_str = self.run_hook_with(json.dumps(
            {"tool_input": {"command": "gh pr create --base main --fill"}}))
        self.assertEqual(exit_code_i, 2)
        self.assertIn("requirement-validation", error_str)
        self.assertIn("every active requirement", error_str)
        self.assertIn(MAIN_HEADING_STR, error_str)

    @covers("PCR-00052", "PCR-00053")
    def test_hook_blocks_develop_with_code_2(self) -> None:
        """The message for develop names the requirements the branch adds.

        Inputs: none.
        Outputs: none.
        """
        with mock.patch(f"{MODULE_STR}.added_requirement_ids",
                        return_value=["PCR-00052"]):
            exit_code_i, error_str = self.run_hook_with(json.dumps(
                {"tool_input": {
                    "command": "gh pr create --base develop --fill"}}))
        self.assertEqual(exit_code_i, 2)
        self.assertIn("every requirement that this branch adds", error_str)
        self.assertIn(DEVELOP_HEADING_STR, error_str)

    @covers("PCR-00051", "PCR-00053")
    def test_hook_lets_other_input_pass(self) -> None:
        """Other commands and input it can't read get code 0 in silence.

        Inputs: none.
        Outputs: none.
        """
        for stdin_str in (json.dumps({"tool_input": {"command": "ls"}}),
                          "not JSON", "{}", "[]"):
            with self.subTest(stdin_str=stdin_str):
                self.assertEqual(self.run_hook_with(stdin_str), (0, ""))

    @covers("PCR-00051")
    def test_ci_check_for_main(self) -> None:
        """Into main, the section is always needed.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.run_body_check(MAIN_BODY_STR, "main"), 0)
        self.assertEqual(self.run_body_check(BAD_BODY_STR, "main"), 1)
        self.assertEqual(self.run_body_check(DEVELOP_BODY_STR, "main"), 1)

    @covers("PCR-00053")
    def test_ci_check_for_develop(self) -> None:
        """Into develop, the section is needed when the branch adds any.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.run_body_check(BAD_BODY_STR, "develop", []), 0)
        self.assertEqual(self.run_body_check(DEVELOP_BODY_STR, "develop",
                                             ["PCR-00052"]), 0)
        self.assertEqual(self.run_body_check(BAD_BODY_STR, "develop",
                                             ["PCR-00052"]), 1)
        self.assertEqual(self.run_body_check(MAIN_BODY_STR, "develop",
                                             ["PCR-00052"]), 1)

    @covers("PCR-00053")
    def test_ci_check_fails_when_git_cannot_tell(self) -> None:
        """A git failure in CI is a failure, not a pass.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.run_body_check(BAD_BODY_STR, "develop", None), 1)


if __name__ == "__main__":
    unittest.main()
