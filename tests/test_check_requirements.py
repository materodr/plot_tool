"""Self-tests for tests/check_requirements.py (PCR-00036 to PCR-00038)."""

import os
import tempfile
import unittest
from unittest import mock

from tests.check_requirements import (CHILD_RULE_STR, ID_RULE_STR,
                                      MUST_RULE_STR, PARENT_RULE_STR,
                                      PREFIX_FILE_DICT, REFERENCE_RULE_STR,
                                      build_report, check_requirement_folder,
                                      main)
from tests.support import covers

GOOD_TEXT_DICT = {
    "COR": "### COR-00001 Language\nThe code must be in Python.\n",
    "PCR": ("### PCR-00001 Host\nThe project must be on GitHub.\n\n"
            "Note: This must stay true, and a note may say must.\n\n"
            "### PCR-00002 DELETED\nDELETED\n"),
    "HLFR": "## General\n\n### HLFR-00001 Open\nThe user must open a file.\n",
    "LLFR": ("## General\n\n### LLFR-00001 Button\n"
             "The panel must hold a button (HLFR-00001).\n\n"
             "*Parent: HLFR-00001*\n"),
}


class CheckRequirementsTest(unittest.TestCase):
    """Check what the script finds in small requirement files."""

    def setUp(self) -> None:
        """Create a temporary folder for the requirement files.

        Inputs: none.
        Outputs: none.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder_str = folder.name

    def problems_with(self, **changed_text_dict: str) -> list:
        """Write the requirement files and check them.

        Inputs:
            changed_text_dict: file texts by prefix that replace the
                good ones.
        Outputs: the (rule, ID, description) problems that were found.
        """
        text_dict = {**GOOD_TEXT_DICT, **changed_text_dict}
        for prefix_str, file_name_str in PREFIX_FILE_DICT.items():
            with open(os.path.join(self.folder_str, file_name_str), "w",
                      encoding="utf-8") as requirement_file:
                requirement_file.write(text_dict[prefix_str])
        return check_requirement_folder(self.folder_str)[1]

    @covers("PCR-00036", "PCR-00037")
    def test_good_requirements_have_no_problem(self) -> None:
        """Notes are not counted and deleted requirements are skipped.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.problems_with(), [])

    @covers("PCR-00036")
    def test_two_musts_are_a_problem(self) -> None:
        """A statement with two uses of must is reported.

        Inputs: none.
        Outputs: none.
        """
        problem_list = self.problems_with(
            COR="### COR-00001 Language\nCode must be short and must run.\n")
        self.assertEqual([(problem_tuple[0], problem_tuple[1])
                          for problem_tuple in problem_list],
                         [(MUST_RULE_STR, "COR-00001")])

    @covers("PCR-00036")
    def test_no_must_is_a_problem(self) -> None:
        """A statement without must is reported.

        Inputs: none.
        Outputs: none.
        """
        problem_list = self.problems_with(
            COR="### COR-00001 Language\nThe code is in Python.\n")
        self.assertEqual(problem_list[0][0], MUST_RULE_STR)

    @covers("PCR-00037")
    def test_gap_and_repeated_id_are_problems(self) -> None:
        """IDs with a gap or used twice are reported.

        Inputs: none.
        Outputs: none.
        """
        gap_list = self.problems_with(
            COR="### COR-00002 Language\nThe code must be in Python.\n")
        self.assertIn((ID_RULE_STR, "COR-00001"),
                      [problem_tuple[:2] for problem_tuple in gap_list])
        repeated_list = self.problems_with(
            COR=GOOD_TEXT_DICT["COR"] + GOOD_TEXT_DICT["COR"])
        self.assertIn((ID_RULE_STR, "COR-00001"),
                      [problem_tuple[:2] for problem_tuple in repeated_list])

    @covers("PCR-00037")
    def test_unknown_reference_is_a_problem(self) -> None:
        """An ID that does not exist is reported where it is named.

        Inputs: none.
        Outputs: none.
        """
        problem_list = self.problems_with(
            COR="### COR-00001 Language\nCode must follow LLFR-00099.\n")
        self.assertEqual(problem_list[0][:2],
                         (REFERENCE_RULE_STR, "COR-00001"))

    @covers("PCR-00031", "PCR-00037")
    def test_parent_links_are_checked(self) -> None:
        """A missing parent and an HLFR without a child are reported.

        Inputs: none.
        Outputs: none.
        """
        problem_list = self.problems_with(
            LLFR="### LLFR-00001 Button\nThe panel must hold a button.\n")
        self.assertEqual([problem_tuple[0] for problem_tuple in problem_list],
                         [PARENT_RULE_STR, CHILD_RULE_STR])

    @covers("PCR-00038")
    def test_report_shows_the_result_and_each_problem(self) -> None:
        """The report names the result and lists every problem.

        Inputs: none.
        Outputs: none.
        """
        good_report_str = build_report(3, [])
        self.assertIn("**pass**", good_report_str)
        bad_report_str = build_report(
            3, [(MUST_RULE_STR, "COR-00001", "uses must 2 times")])
        self.assertIn("**fail**", bad_report_str)
        self.assertIn("| COR-00001 | One must | uses must 2 times |",
                      bad_report_str)

    @covers("PCR-00037", "PCR-00038")
    def test_main_writes_the_report_and_sets_the_exit_code(self) -> None:
        """The exit code is 0 with no problem and 1 with one.

        Inputs: none.
        Outputs: none.
        """
        output_path_str = os.path.join(self.folder_str, "report.md")
        argument_list = ["check_requirements.py", "--folder", self.folder_str,
                         "--output", output_path_str]
        self.problems_with()
        with mock.patch("sys.argv", argument_list):
            self.assertEqual(main(), 0)
        self.assertTrue(os.path.exists(output_path_str))
        self.problems_with(COR="### COR-00001 Language\nThe code is Python.\n")
        with mock.patch("sys.argv", argument_list):
            self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
