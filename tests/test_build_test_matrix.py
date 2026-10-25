"""Self-tests for tests/build_test_matrix.py (PCR-00022, PCR-00023)."""

import io
import unittest

from tests.build_test_matrix import (FAILED_STR, PASSED_STR, SKIPPED_STR,
                                     RecordingResult, build_matrix,
                                     hlfr_result)
from tests.support import covers


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

    @covers("PCR-00023")
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

    @covers("PCR-00020", "PCR-00021", "PCR-00022", "PCR-00023")
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


if __name__ == "__main__":
    unittest.main()
