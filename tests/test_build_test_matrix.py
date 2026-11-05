"""Self-tests for tests/build_test_matrix.py (PCR-00022, PCR-00023,
PCR-00042, PCR-00059, PCR-00063 to PCR-00071)."""

import io
import os
import tempfile
import unittest
from unittest import mock

from tests.build_test_matrix import (FAILED_STR, KNOWN_FAILURE_STR,
                                     PASSED_STR, SKIPPED_STR,
                                     RecordingResult, build_matrix,
                                     affected_hlfrs_have_tests,
                                     environment_status, fail_star_section,
                                     hlfr_result, main, mark_known_failures,
                                     mark_environment_limits,
                                     read_not_implemented, untested_hlfrs)
from tests.check_pr_ready import fail_star_entries
from tests.support import covers

QT_STATUS_STR = "Fail* (PyQt6 missing)"
H5PY_STATUS_STR = "Fail* (h5py missing)"


def matrix_row(matrix_str: str, hlfr_id_str: str) -> str:
    """Return the table row of one HLFR.

    Inputs:
        matrix_str: the text of a test matrix.
        hlfr_id_str: the HLFR ID, for example "HLFR-00014".
    Outputs: the row, or an empty text when there is none.
    """
    for line_str in matrix_str.splitlines():
        if line_str.startswith(f"| {hlfr_id_str} "):
            return line_str
    return ""


def run_sample_suite(test_case_class) -> RecordingResult:
    """Run every test of one TestCase class through RecordingResult.

    Inputs:
        test_case_class: a unittest.TestCase subclass to run.
    Outputs: the RecordingResult of the run.
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(test_case_class)
    runner = unittest.TextTestRunner(stream=io.StringIO(),
                                     resultclass=RecordingResult)
    return runner.run(suite)


class RecordingResultTest(unittest.TestCase):
    """Check that every test outcome is recorded once and correctly."""

    @covers("PCR-00022")
    def test_failing_subtest_marks_the_test_failed(self) -> None:
        """A test whose subtest fails is recorded once, as failed.

        Inputs: none.
        Outputs: none.
        """
        class SubtestSample(unittest.TestCase):
            """Sample test with one passing and one failing subtest."""

            @covers("LLFR-00024")
            def test_with_subtests(self) -> None:
                """Run a passing and a failing subtest.

                Inputs: none.
                Outputs: none.
                """
                for value_i in (1, 2):
                    with self.subTest(value_i=value_i):
                        self.assertEqual(value_i, 1)

        sample_result = run_sample_suite(SubtestSample)
        self.assertFalse(sample_result.wasSuccessful())
        self.assertEqual(len(sample_result.status_list), 1)
        test_id_str, requirement_list, status_str = (
            sample_result.status_list[0])
        self.assertEqual(status_str, FAILED_STR)
        self.assertEqual(requirement_list, ["LLFR-00024"])

    @covers("PCR-00022")
    def test_pass_fail_error_and_skip_are_recorded(self) -> None:
        """Passed, failed, error and skipped tests get the right status.

        Inputs: none.
        Outputs: none.
        """
        class MixedSample(unittest.TestCase):
            """Sample tests with every kind of outcome."""

            def test_a_passes(self) -> None:
                """Pass.

                Inputs: none.
                Outputs: none.
                """

            def test_b_fails(self) -> None:
                """Fail an assertion.

                Inputs: none.
                Outputs: none.
                """
                self.fail("expected failure")

            def test_c_errors(self) -> None:
                """Raise an unexpected exception.

                Inputs: none.
                Outputs: none.
                """
                raise RuntimeError("expected error")

            @unittest.skip("expected skip")
            def test_d_skipped(self) -> None:
                """Be skipped.

                Inputs: none.
                Outputs: none.
                """

        status_dict = {test_id_str.rsplit(".", 1)[-1]: status_str
                       for test_id_str, _, status_str
                       in run_sample_suite(MixedSample).status_list}
        self.assertEqual(status_dict, {
            "test_a_passes": PASSED_STR,
            "test_b_fails": FAILED_STR,
            "test_c_errors": FAILED_STR,
            "test_d_skipped": SKIPPED_STR,
        })


class MatrixResultTest(unittest.TestCase):
    """Check column 4 and the linking of tests to HLFRs."""

    @covers("PCR-00023", "PCR-00042")
    def test_hlfr_result_values(self) -> None:
        """Column 4 is pass, fail, not run or no tests as documented.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(hlfr_result([PASSED_STR, PASSED_STR]), "pass")
        self.assertEqual(hlfr_result([PASSED_STR, FAILED_STR]), "fail")
        self.assertEqual(hlfr_result([SKIPPED_STR, FAILED_STR]), "fail")
        self.assertEqual(hlfr_result([PASSED_STR, SKIPPED_STR]), "not run")
        self.assertEqual(hlfr_result([]), "no tests")

    @covers("PCR-00020", "PCR-00021", "PCR-00022", "PCR-00023", "PCR-00042")
    def test_failed_llfr_test_fails_its_hlfr_row(self) -> None:
        """A failed test tagged with an LLFR makes its HLFR row fail.

        Inputs: none.
        Outputs: none.
        """
        matrix_str, untested_list = build_matrix(
            [("tests.sample.test_x", ["LLFR-00024"], FAILED_STR)])
        row_list = [line_str for line_str in matrix_str.splitlines()
                    if line_str.startswith("| HLFR-00014 ")]
        self.assertEqual(len(row_list), 1)
        self.assertIn("LLFR-00024", row_list[0])
        self.assertIn("`sample.test_x` failed", row_list[0])
        self.assertTrue(row_list[0].rstrip().endswith("| fail |"))
        self.assertNotIn("LLFR-00024", untested_list)


class KnownFailureTest(unittest.TestCase):
    """Check the tests that are known to fail on macOS."""

    @covers("PCR-00062")
    def test_only_listed_failures_on_macos_change(self) -> None:
        """A listed failure changes on macOS, and nothing else does.

        Inputs: none.
        Outputs: none.
        """
        status_list = [("a", [], FAILED_STR), ("b", [], FAILED_STR),
                       ("c", [], PASSED_STR)]
        marked_list = mark_known_failures(status_list, "darwin", {"a", "c"})
        self.assertEqual([item[2] for item in marked_list],
                         [KNOWN_FAILURE_STR, FAILED_STR, PASSED_STR])
        self.assertEqual(mark_known_failures(status_list, "linux", {"a"}),
                         status_list)
        self.assertEqual(hlfr_result([KNOWN_FAILURE_STR, PASSED_STR]), "pass")


class UntestedHlfrTest(unittest.TestCase):
    """Check which affected HLFRs count as having no test."""

    @covers("PCR-00059")
    def test_only_given_hlfrs_without_links_are_listed(self) -> None:
        """A test of the HLFR or of a child LLFR counts as its test.

        Inputs: none.
        Outputs: none.
        """
        requirements_tuple = ([], {"HLFR-00001": ["LLFR-00001"],
                                   "HLFR-00002": [],
                                   "HLFR-00003": [],
                                   "HLFR-00004": []})
        status_list = [("a", ["LLFR-00001"], PASSED_STR),
                       ("b", ["HLFR-00002"], PASSED_STR)]
        with mock.patch("tests.build_test_matrix.read_requirements",
                        return_value=requirements_tuple):
            self.assertEqual(
                untested_hlfrs(status_list, {"HLFR-00001", "HLFR-00002",
                                             "HLFR-00003"}),
                ["HLFR-00003"])


class EnvironmentLimitTest(unittest.TestCase):
    """Check the Fail* of a test the environment couldn't run."""

    @covers("PCR-00022", "PCR-00063")
    def test_skip_reason_is_recorded(self) -> None:
        """RecordingResult keeps the reason of each skipped test.

        Inputs: none.
        Outputs: none.
        """
        class SkipSample(unittest.TestCase):
            """Sample test skipped because PyQt6 is missing."""

            @unittest.skip("PyQt6 is not installed")
            def test_gui(self) -> None:
                """Be skipped.

                Inputs: none.
                Outputs: none.
                """

        sample_result = run_sample_suite(SkipSample)
        self.assertEqual(list(sample_result.skip_reason_dict.values()),
                         ["PyQt6 is not installed"])

    @covers("PCR-00063", "PCR-00064")
    def test_only_missing_library_skips_become_fail_star(self) -> None:
        """PyQt6 and h5py skips become Fail*; the rest is unchanged.

        Inputs: none.
        Outputs: none.
        """
        status_list = [("qt", [], SKIPPED_STR), ("hdf", [], SKIPPED_STR),
                       ("root", [], SKIPPED_STR), ("ran", [], FAILED_STR),
                       ("ok", [], PASSED_STR)]
        reason_dict = {"qt": "PyQt6 is not installed",
                       "hdf": "h5py is not installed",
                       "root": "root may write read-only files",
                       "ran": "PyQt6 is not installed"}
        marked_list = mark_environment_limits(status_list, reason_dict)
        self.assertEqual([item[2] for item in marked_list],
                         [QT_STATUS_STR, H5PY_STATUS_STR, SKIPPED_STR,
                          FAILED_STR, PASSED_STR])
        self.assertEqual(environment_status("PyQt6"), QT_STATUS_STR)

    @covers("PCR-00042", "PCR-00071")
    def test_column_4_names_the_missing_capabilities(self) -> None:
        """Column 4 shows the Fail*, unless a test that ran failed.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(hlfr_result([PASSED_STR, QT_STATUS_STR]),
                         "Fail* (PyQt6 missing)")
        self.assertEqual(
            hlfr_result([H5PY_STATUS_STR, QT_STATUS_STR, SKIPPED_STR]),
            "Fail* (PyQt6, h5py missing)")
        self.assertEqual(hlfr_result([QT_STATUS_STR, FAILED_STR]), "fail")

    @covers("PCR-00022", "PCR-00063", "PCR-00070", "PCR-00071")
    def test_matrix_cells_and_section(self) -> None:
        """The cells and the Fail* section show the justification.

        Inputs: none.
        Outputs: none.
        """
        matrix_str, _ = build_matrix(
            [("tests.view.test_x", ["LLFR-00024"], QT_STATUS_STR),
             ("tests.model.test_y", ["LLFR-00024"], PASSED_STR)],
            "abc1", {}, "pypi.org is blocked here.")
        row_str = matrix_row(matrix_str, "HLFR-00014")
        self.assertIn("`view.test_x` Fail* (PyQt6 missing)", row_str)
        self.assertTrue(row_str.endswith("| Fail* (PyQt6 missing) |"))
        self.assertEqual(fail_star_entries(matrix_str), [
            "Environment, PyQt6: 1 tests shown as \"Fail* (PyQt6 missing)"
            "\". PyQt6 cannot be installed in the environment that built "
            "this matrix. pypi.org is blocked here."])
        self.assertLess(matrix_str.index("## Fail* (PCR-00070)"),
                        matrix_str.index("| HLFR |"))

    @covers("PCR-00070")
    def test_no_section_without_fail_star(self) -> None:
        """A matrix with no Fail* has no Fail* section.

        Inputs: none.
        Outputs: none.
        """
        matrix_str, _ = build_matrix(
            [("tests.model.test_y", ["LLFR-00024"], PASSED_STR)])
        self.assertNotIn("Fail*", matrix_str)
        self.assertEqual(fail_star_section([], {}), "")

    @covers("PCR-00063")
    def test_require_options_without_the_option(self) -> None:
        """Without --environment-limit a missing library still fails.

        Inputs: none.
        Outputs: none.
        """
        for argument_str, flag_str in (("--require-qt", "QT_AVAILABLE_B"),
                                       ("--require-h5py",
                                        "H5PY_AVAILABLE_B")):
            with self.subTest(argument_str=argument_str), \
                    mock.patch(f"tests.build_test_matrix.{flag_str}", False), \
                    mock.patch("sys.argv", ["build", argument_str]), \
                    mock.patch("tests.build_test_matrix.run_all_tests") \
                    as run_mock, mock.patch("sys.stderr", io.StringIO()):
                self.assertEqual(main(), 1)
                run_mock.assert_not_called()

    @covers("PCR-00063", "PCR-00064")
    def test_require_options_with_the_option(self) -> None:
        """With --environment-limit the run goes on and writes Fail*.

        Inputs: none.
        Outputs: none.
        """
        sample_result = mock.Mock()
        sample_result.status_list = [("tests.view.test_x", ["LLFR-00024"],
                                      SKIPPED_STR)]
        sample_result.skip_reason_dict = {
            "tests.view.test_x": "PyQt6 is not installed"}
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        output_path_str = os.path.join(folder.name, "matrix.md")
        with mock.patch("tests.build_test_matrix.QT_AVAILABLE_B", False), \
                mock.patch("tests.build_test_matrix.H5PY_AVAILABLE_B",
                           False), \
                mock.patch("sys.argv", [
                    "build", "--require-qt", "--require-h5py",
                    "--environment-limit", "--output", output_path_str]), \
                mock.patch("tests.build_test_matrix.run_all_tests",
                           return_value=sample_result), \
                mock.patch("tests.build_test_matrix.read_not_implemented",
                           return_value={}), \
                mock.patch("sys.stdout", io.StringIO()) as output:
            self.assertEqual(main(), 0)
        with open(output_path_str, encoding="utf-8") as matrix_file:
            matrix_str = matrix_file.read()
        self.assertIn("`view.test_x` Fail* (PyQt6 missing)", matrix_str)
        self.assertIn("## Fail* (PCR-00070)", output.getvalue())


class NotImplementedTest(unittest.TestCase):
    """Check the Fail* of an HLFR that isn't implemented yet."""

    def write_list(self, text_str: str) -> str:
        """Write a temporary not-implemented list.

        Inputs:
            text_str: the text of the file.
        Outputs: the path of the file.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path_str = os.path.join(folder.name, "not_implemented.txt")
        with open(path_str, "w", encoding="utf-8") as list_file:
            list_file.write(text_str)
        return path_str

    @covers("PCR-00066")
    def test_list_is_read(self) -> None:
        """Comments and blank lines are skipped; each ID has its text.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write_list(
            "# comment\n\nHLFR-00014 Waits for #190.\n")
        self.assertEqual(read_not_implemented(path_str),
                         {"HLFR-00014": "Waits for #190."})
        self.assertEqual(read_not_implemented(path_str + ".missing"), {})

    @covers("PCR-00066")
    def test_bad_lines_are_refused(self) -> None:
        """A line without explanation, or a repeated ID, is an error.

        Inputs: none.
        Outputs: none.
        """
        for text_str in ("HLFR-00014\n", "LLFR-00024 text\n",
                         "HLFR-00014 a\nHLFR-00014 b\n"):
            with self.subTest(text_str=text_str):
                with self.assertRaises(ValueError):
                    read_not_implemented(self.write_list(text_str))

    @covers("PCR-00023", "PCR-00042", "PCR-00065")
    def test_column_4_shows_the_explanation(self) -> None:
        """Column 4 shows the Fail*, unless a test failed.

        Inputs: none.
        Outputs: none.
        """
        expected_str = ("Fail*: the implementation has not been done yet. "
                        "Waits for #190.")
        self.assertEqual(hlfr_result([], "Waits for #190."), expected_str)
        self.assertEqual(hlfr_result([PASSED_STR], "Waits for #190."),
                         expected_str)
        self.assertEqual(hlfr_result([QT_STATUS_STR], "Waits for #190."),
                         expected_str)
        self.assertEqual(hlfr_result([FAILED_STR], "Waits for #190."),
                         "fail")
        self.assertEqual(hlfr_result([], "a | b"),
                         "Fail*: the implementation has not been done yet. "
                         "a \\| b")

    @covers("PCR-00065", "PCR-00070")
    def test_matrix_row_and_section(self) -> None:
        """The row and the Fail* section show the explanation.

        Inputs: none.
        Outputs: none.
        """
        matrix_str, _ = build_matrix([], "abc1",
                                     {"HLFR-00014": "Waits for #190."})
        self.assertTrue(matrix_row(matrix_str, "HLFR-00014").endswith(
            "| Fail*: the implementation has not been done yet. "
            "Waits for #190. |"))
        self.assertEqual(fail_star_entries(matrix_str), [
            "Not implemented, HLFR-00014: Fail* in column 4, the "
            "implementation has not been done yet. Waits for #190."])

    @covers("PCR-00059", "PCR-00068", "PCR-00069")
    def test_pcr_00059_check_into_develop_and_main(self) -> None:
        """A listed HLFR passes the check into develop, not into main.

        Inputs: none.
        Outputs: none.
        """
        requirements_tuple = ([], {"HLFR-00001": [], "HLFR-00002": []})
        with mock.patch("tests.build_test_matrix.read_requirements",
                        return_value=requirements_tuple):
            self.assertEqual(
                untested_hlfrs([], {"HLFR-00001", "HLFR-00002"},
                               {"HLFR-00001"}),
                ["HLFR-00002"])
            with mock.patch("tests.build_test_matrix.find_affected_hlfrs",
                            return_value={"HLFR-00001"}), \
                    mock.patch("sys.stderr", io.StringIO()):
                self.assertTrue(affected_hlfrs_have_tests(
                    [], "develop", "HEAD", {"HLFR-00001"}))
                self.assertFalse(affected_hlfrs_have_tests(
                    [], "main", "HEAD", {"HLFR-00001"}))
                self.assertFalse(affected_hlfrs_have_tests(
                    [], "develop", "HEAD", set()))

    @covers("PCR-00066")
    def test_repository_list_is_valid(self) -> None:
        """tests/not_implemented.txt lists only existing HLFRs.

        Inputs: none.
        Outputs: none.
        """
        from tests.build_test_matrix import read_requirements
        hlfr_id_set = {hlfr_id_str for hlfr_id_str, _
                       in read_requirements()[0]}
        self.assertLessEqual(set(read_not_implemented()), hlfr_id_set)


if __name__ == "__main__":
    unittest.main()
