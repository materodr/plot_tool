"""Self-tests for tests/check_release_pr.py (PCR-00050, PCR-00051)."""

import io
import json
import os
import tempfile
import unittest
from unittest import mock

from tests.check_release_pr import (SECTION_HEADING_STR, command_may_run,
                                    has_review_section, main, run_hook)
from tests.support import covers

GOOD_BODY_STR = ("Release.\n\n"
                 f"## {SECTION_HEADING_STR}\n"
                 "Scope: LLFR-00001. Result: pass.\n")
BAD_BODY_STR = "Release, with no review.\n"


class ReviewSectionTest(unittest.TestCase):
    """Check how a pull request description is read."""

    @covers("PCR-00051")
    def test_section_with_content_passes(self) -> None:
        """A heading with text below it counts.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(has_review_section(GOOD_BODY_STR))

    @covers("PCR-00051")
    def test_windows_line_ends_pass(self) -> None:
        """A description written on the GitHub website has CRLF line ends.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(has_review_section(
            GOOD_BODY_STR.replace("\n", "\r\n")))

    @covers("PCR-00051")
    def test_missing_section_fails(self) -> None:
        """A description without the heading doesn't count.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(has_review_section(BAD_BODY_STR))

    @covers("PCR-00051")
    def test_empty_section_fails(self) -> None:
        """A heading with nothing below it doesn't count.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(has_review_section(f"## {SECTION_HEADING_STR}\n\n"))

    @covers("PCR-00051")
    def test_section_followed_by_heading_fails(self) -> None:
        """Text under the next heading isn't the section's content.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(has_review_section(
            f"## {SECTION_HEADING_STR}\n\n## Other\nText\n"))

    @covers("PCR-00051")
    def test_mention_in_a_sentence_fails(self) -> None:
        """Naming the section in a sentence doesn't count.

        Inputs: none.
        Outputs: none.
        """
        self.assertFalse(has_review_section(
            f"This has no {SECTION_HEADING_STR} section.\nMore text.\n"))


class CommandTest(unittest.TestCase):
    """Check which shell commands the hook lets run."""

    def setUp(self) -> None:
        """Create a folder with a good and a bad description file.

        Inputs: none.
        Outputs: none.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder_str = folder.name
        for name_str, text_str in (("good.md", GOOD_BODY_STR),
                                   ("bad.md", BAD_BODY_STR)):
            path_str = os.path.join(self.folder_str, name_str)
            with open(path_str, "w", encoding="utf-8") as text_file:
                text_file.write(text_str)

    def may_run(self, command_str: str) -> bool:
        """Check a command in the temporary folder.

        Inputs:
            command_str: the shell command.
        Outputs: True when the hook lets the command run.
        """
        return command_may_run(command_str, self.folder_str)

    @covers("PCR-00050")
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
                self.assertTrue(self.may_run(command_str))

    @covers("PCR-00050")
    def test_pull_request_into_develop_runs(self) -> None:
        """A pull request into another branch needs no section.

        Inputs: none.
        Outputs: none.
        """
        for command_str in ("gh pr create --base develop --body-file bad.md",
                            "gh pr create --base=develop --fill",
                            "gh pr create -B develop --fill",
                            "gh api repos/a/b/pulls -f base=develop"):
            with self.subTest(command_str=command_str):
                self.assertTrue(self.may_run(command_str))

    @covers("PCR-00050")
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
                            "gh api repos/a/b/pulls -f base=main -f body=x",
                            "gh api repos/a/b/pulls -f base=main "
                            "-F body=@bad.md"):
            with self.subTest(command_str=command_str):
                self.assertFalse(self.may_run(command_str))

    @covers("PCR-00050")
    def test_pull_request_into_main_with_the_section_runs(self) -> None:
        """A description in a file or in the command itself is read.

        Inputs: none.
        Outputs: none.
        """
        heredoc_str = ("gh pr create --base main --body-file - <<'EOF'\n"
                       f"{GOOD_BODY_STR}EOF\n")
        for command_str in ("gh pr create --base main --body-file good.md",
                            "gh pr create --body-file good.md",
                            heredoc_str,
                            "gh pr create --base main --body "
                            f"'## {SECTION_HEADING_STR}\nResult: pass'",
                            "gh api repos/a/b/pulls -f base=main "
                            "-F body=@good.md"):
            with self.subTest(command_str=command_str):
                self.assertTrue(self.may_run(command_str))

    @covers("PCR-00050")
    def test_api_input_file_is_read(self) -> None:
        """The base and description of a gh api --input file are used.

        Inputs: none.
        Outputs: none.
        """
        for name_str, input_dict, expected_b in (
                ("a.json", {"base": "main", "body": GOOD_BODY_STR}, True),
                ("b.json", {"base": "main", "body": BAD_BODY_STR}, False),
                ("c.json", {"base": "develop", "body": ""}, True)):
            path_str = os.path.join(self.folder_str, name_str)
            with open(path_str, "w", encoding="utf-8") as input_file:
                json.dump(input_dict, input_file)
            with self.subTest(name_str=name_str):
                self.assertEqual(
                    self.may_run(f"gh api repos/a/b/pulls --input {name_str}"),
                    expected_b)


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

    @covers("PCR-00050")
    def test_hook_blocks_with_code_2(self) -> None:
        """A blocked command gets code 2 and a message that names the skill.

        Inputs: none.
        Outputs: none.
        """
        exit_code_i, error_str = self.run_hook_with(json.dumps(
            {"tool_input": {"command": "gh pr create --base main --fill"}}))
        self.assertEqual(exit_code_i, 2)
        self.assertIn("requirement-validation", error_str)

    @covers("PCR-00050")
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
    def test_body_file_exit_codes(self) -> None:
        """The CI check gives 0 with the section and 1 without it.

        Inputs: none.
        Outputs: none.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        for text_str, expected_i in ((GOOD_BODY_STR, 0), (BAD_BODY_STR, 1)):
            path_str = os.path.join(folder.name, "body.md")
            with open(path_str, "w", encoding="utf-8") as body_file:
                body_file.write(text_str)
            with mock.patch("sys.argv", ["check", "--body-file", path_str]), \
                    mock.patch("sys.stdout", io.StringIO()):
                self.assertEqual(main(), expected_i)


if __name__ == "__main__":
    unittest.main()
