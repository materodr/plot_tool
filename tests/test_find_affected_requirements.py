"""Self-tests for tests/find_affected_requirements.py (PCR-00059)."""

import os
import subprocess
import tempfile
import unittest

from tests.find_affected_requirements import (HIGH_LEVEL_PATH_STR,
                                              LOW_LEVEL_PATH_STR,
                                              find_affected_hlfrs,
                                              parse_changed_lines)
from tests.support import covers

HIGH_LEVEL_TEXT_STR = ("# High\n\n## General\n\n"
                       "### HLFR-00001 One\nThe app must do one.\n\n"
                       "### HLFR-00002 Two\nThe app must do two.\n\n"
                       "### HLFR-00003 Three\nThe app must do three.\n")
LOW_LEVEL_TEXT_STR = ("# Low\n\n## General\n\n"
                      "### LLFR-00001 Child of one\nIt must work.\n\n"
                      "*Parent: HLFR-00001*\n\n"
                      "### LLFR-00002 Child of two\nIt must work.\n\n"
                      "*Parent: HLFR-00002*\n")
SOURCE_TEXT_STR = ('"""Module."""\n\n\n'
                   "def first():\n"
                   "    # LLFR-00001\n"
                   "    return 1\n\n\n"
                   "def second():\n"
                   "    # LLFR-00002\n"
                   "    return 2\n")
SOURCE_PATH_STR = "src/model/code.py"


class ParseChangedLinesTest(unittest.TestCase):
    """Check how the output of git diff is read."""

    @covers("PCR-00059")
    def test_deleted_file_adds_no_lines(self) -> None:
        """A deleted file's hunk isn't counted in the file before it.

        Inputs: none.
        Outputs: none.
        """
        diff_str = ("+++ b/a.py\n@@ -1 +1 @@\n"
                    "+++ /dev/null\n@@ -5,3 +0,0 @@\n")
        self.assertEqual(parse_changed_lines(diff_str), {"a.py": {1}})


class FindAffectedTest(unittest.TestCase):
    """Check which HLFRs count as affected, in a real git repository."""

    def setUp(self) -> None:
        """Create a repository whose develop holds requirements and code.

        Inputs: none.
        Outputs: none.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder_str = folder.name
        self.git("init", "-q")
        self.write_file(HIGH_LEVEL_PATH_STR, HIGH_LEVEL_TEXT_STR)
        self.write_file(LOW_LEVEL_PATH_STR, LOW_LEVEL_TEXT_STR)
        self.write_file(SOURCE_PATH_STR, SOURCE_TEXT_STR)
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

    def write_file(self, path_str: str, text_str: str) -> None:
        """Write a file of the temporary repository.

        Inputs:
            path_str: the path relative to the repository.
            text_str: the file's text.
        Outputs: none.
        """
        full_path_str = os.path.join(self.folder_str, path_str)
        os.makedirs(os.path.dirname(full_path_str), exist_ok=True)
        with open(full_path_str, "w", encoding="utf-8") as text_file:
            text_file.write(text_str)

    def commit(self) -> None:
        """Commit everything in the temporary repository.

        Inputs: none.
        Outputs: none.
        """
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "change")

    def affected(self) -> set:
        """Find what the current branch affects, after committing it.

        Inputs: none.
        Outputs: the affected HLFR IDs.
        """
        self.commit()
        return find_affected_hlfrs("develop", "HEAD", self.folder_str)

    @covers("PCR-00059")
    def test_changed_hlfr_counts(self) -> None:
        """Changing the text of an HLFR affects only that HLFR.

        Inputs: none.
        Outputs: none.
        """
        self.write_file(HIGH_LEVEL_PATH_STR, HIGH_LEVEL_TEXT_STR.replace(
            "do two", "do two well"))
        self.assertEqual(self.affected(), {"HLFR-00002"})

    @covers("PCR-00059")
    def test_changed_llfr_affects_its_parent(self) -> None:
        """Changing the text of an LLFR affects its parent HLFR.

        Inputs: none.
        Outputs: none.
        """
        self.write_file(LOW_LEVEL_PATH_STR, LOW_LEVEL_TEXT_STR.replace(
            "### LLFR-00001 Child of one\nIt must work.",
            "### LLFR-00001 Child of one\nIt must work well."))
        self.assertEqual(self.affected(), {"HLFR-00001"})

    @covers("PCR-00059")
    def test_changed_function_affects_the_parent_of_its_llfr(self) -> None:
        """Changing a function affects only the HLFR of the LLFR it names.

        Inputs: none.
        Outputs: none.
        """
        self.write_file(SOURCE_PATH_STR,
                        SOURCE_TEXT_STR.replace("return 2", "return 22"))
        self.assertEqual(self.affected(), {"HLFR-00002"})

    @covers("PCR-00059")
    def test_removed_line_counts(self) -> None:
        """Removing a line from a function also counts as changing it.

        Inputs: none.
        Outputs: none.
        """
        two_line_text_str = SOURCE_TEXT_STR.replace(
            "    return 2\n", "    x_i = 2\n    return 2\n")
        self.write_file(SOURCE_PATH_STR, two_line_text_str)
        self.commit()
        self.git("update-ref", "refs/remotes/origin/develop", "HEAD")
        self.write_file(SOURCE_PATH_STR, SOURCE_TEXT_STR)
        self.assertEqual(self.affected(), {"HLFR-00002"})

    @covers("PCR-00059")
    def test_other_files_do_not_count(self) -> None:
        """A change outside the requirements and src affects nothing.

        Inputs: none.
        Outputs: none.
        """
        self.write_file("README.md", "Text.\n")
        self.assertEqual(self.affected(), set())

    @covers("PCR-00059")
    def test_unknown_head_gives_none(self) -> None:
        """A commit git can't find is reported, not read as no change.

        Inputs: none.
        Outputs: none.
        """
        self.assertIsNone(find_affected_hlfrs("develop", "missing",
                                              self.folder_str))


if __name__ == "__main__":
    unittest.main()
