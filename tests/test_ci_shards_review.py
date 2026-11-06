"""Reviewer's tests of the CI shards (issue #274): the split of the real
suite, the merge of tampered shard results through build_test_matrix
--from-results, and the final check step of the "tests" job
(PCR-00127, PCR-00128)."""

import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from tests import ci_shards
from tests.build_test_matrix import (FAILED_STR, PASSED_STR,
                                     REPOSITORY_ROOT_STR, discover_suite,
                                     main)
from tests.support import covers

WORKFLOW_PATH_STR = os.path.join(REPOSITORY_ROOT_STR, ".github",
                                 "workflows", "tests.yml")
YAML_AVAILABLE_B = importlib.util.find_spec("yaml") is not None
BASH_AVAILABLE_B = shutil.which("bash") is not None
FINAL_STEP_NAME_STR = "Check that every shard succeeded"


class RealSuiteSplitTest(unittest.TestCase):
    """Split the real suite of tests/ into shards."""

    @classmethod
    def setUpClass(cls) -> None:
        """Discover the real suite once.

        Inputs: none.
        Outputs: none.
        """
        cls.test_list = ci_shards.iterate_tests(discover_suite())
        cls.test_id_list = [test.id() for test in cls.test_list]
        cls.module_set = {ci_shards.module_of(test)
                          for test in cls.test_list}

    def planned_ids(self, durations_dict: dict, shard_count_i: int) -> list:
        """Return the test IDs that each shard plans.

        Inputs:
            durations_dict: the known seconds of the modules.
            shard_count_i: the number of shards.
        Outputs: a list with the list of planned IDs of each shard.
        """
        return [[test.id() for test in ci_shards.iterate_tests(
                    ci_shards.select_shard(self.test_list, shard_index_i,
                                           shard_count_i,
                                           durations_dict)[0])]
                for shard_index_i in range(1, shard_count_i + 1)]

    @covers("PCR-00127")
    def test_every_test_file_in_exactly_one_shard(self) -> None:
        """For 1 to 8 shards, each test file of tests/ is in one shard.

        Inputs: none.
        Outputs: none.
        """
        durations_dict = ci_shards.read_durations()
        for shard_count_i in range(1, 9):
            with self.subTest(shard_count_i=shard_count_i):
                module_list_list = ci_shards.assign_shards(
                    ci_shards.expected_seconds(
                        ci_shards.module_test_counts(self.test_list),
                        durations_dict), shard_count_i)
                all_module_list = [module_str for module_list
                                   in module_list_list
                                   for module_str in module_list]
                self.assertEqual(len(all_module_list),
                                 len(set(all_module_list)))
                self.assertEqual(set(all_module_list), self.module_set)

    @covers("PCR-00127")
    def test_every_test_planned_once_in_the_four_shards(self) -> None:
        """The four shards of CI plan every discovered test once.

        Inputs: none.
        Outputs: none.
        """
        planned_list_list = self.planned_ids(ci_shards.read_durations(), 4)
        all_planned_list = [test_id_str for planned_list
                            in planned_list_list
                            for test_id_str in planned_list]
        self.assertEqual(sorted(all_planned_list),
                         sorted(self.test_id_list))
        self.assertTrue(all(planned_list
                            for planned_list in planned_list_list))

    @covers("PCR-00127")
    def test_new_test_file_without_duration_is_assigned(self) -> None:
        """A test file missing from the durations file still runs once.

        Inputs: none.
        Outputs: none.
        """
        durations_dict = ci_shards.read_durations()
        missing_str = __name__
        durations_dict.pop(missing_str, None)
        planned_list_list = self.planned_ids(durations_dict, 4)
        shard_count_i = sum(
            1 for planned_list in planned_list_list
            if any(test_id_str.startswith(missing_str + ".")
                   for test_id_str in planned_list))
        self.assertEqual(shard_count_i, 1)
        all_planned_list = [test_id_str for planned_list
                            in planned_list_list
                            for test_id_str in planned_list]
        self.assertEqual(sorted(all_planned_list),
                         sorted(self.test_id_list))

    @covers("PCR-00127")
    def test_empty_durations_file_still_covers_the_suite(self) -> None:
        """With no known duration, the shards still plan every test once.

        Inputs: none.
        Outputs: none.
        """
        all_planned_list = [test_id_str for planned_list
                            in self.planned_ids({}, 4)
                            for test_id_str in planned_list]
        self.assertEqual(sorted(all_planned_list),
                         sorted(self.test_id_list))


class TamperedMergeTest(unittest.TestCase):
    """Run build_test_matrix --from-results on tampered shard files."""

    discovered_list = [f"tests.fake_{letter_str}.Case.test_{number_i}"
                       for letter_str in "abcd" for number_i in range(3)]

    def setUp(self) -> None:
        """Make a folder for the shard results.

        Inputs: none.
        Outputs: none.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder_str = folder.name

    def write_shards(self, planned_list_list: list,
                     status_dict: dict = None) -> str:
        """Write one results file per shard, one artifact folder each.

        Inputs:
            planned_list_list: the planned test IDs of each shard.
            status_dict: a status for some test IDs; passed otherwise.
        Outputs: the folder of the results.
        """
        status_dict = status_dict or {}
        results_str = os.path.join(self.folder_str, "results")
        shard_count_i = len(planned_list_list)
        for shard_index_i, planned_list in enumerate(planned_list_list, 1):
            artifact_str = os.path.join(results_str,
                                        f"test-results-{shard_index_i}")
            os.makedirs(artifact_str)
            ci_shards.write_results(
                os.path.join(artifact_str, f"shard_{shard_index_i}.json"),
                {"shard_index": shard_index_i,
                 "shard_count": shard_count_i,
                 "discovered_test_ids": self.discovered_list,
                 "planned_test_ids": planned_list,
                 "statuses": [[test_id_str, [],
                               status_dict.get(test_id_str, PASSED_STR)]
                              for test_id_str in planned_list],
                 "environment_text": None,
                 "qt_available": True,
                 "module_seconds": {}, "test_seconds": [],
                 "expected_seconds": 0.0, "run_seconds": 0.0})
        return results_str

    def merge(self, results_str: str) -> tuple:
        """Run main() with --from-results.

        Inputs:
            results_str: the folder of the shard results.
        Outputs: the tuple (exit code, standard error text).
        """
        error_stream = io.StringIO()
        with mock.patch("sys.argv", [
                "build", "--from-results", results_str, "--output",
                os.path.join(self.folder_str, "matrix.md")]), \
                mock.patch("tests.build_test_matrix.read_not_implemented",
                           return_value={}), \
                mock.patch("tests.build_test_matrix.source_hash",
                           return_value=""), \
                mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "",
                                             "GITHUB_STEP_SUMMARY": ""}), \
                mock.patch("sys.stdout", io.StringIO()), \
                mock.patch("sys.stderr", error_stream):
            return main(), error_stream.getvalue()

    def quarters(self) -> list:
        """Split the fake tests into four shards of one module each.

        Inputs: none.
        Outputs: the planned test IDs of each shard.
        """
        return [self.discovered_list[index_i:index_i + 3]
                for index_i in range(0, 12, 3)]

    @covers("PCR-00127", "PCR-00128")
    def test_complete_shards_pass(self) -> None:
        """Four complete shards merge with no problem.

        Inputs: none.
        Outputs: none.
        """
        exit_i, error_str = self.merge(self.write_shards(self.quarters()))
        self.assertEqual(exit_i, 0, error_str)

    @covers("PCR-00128")
    def test_duplicate_test_fails(self) -> None:
        """A test planned in two shards fails the merge and is named.

        Inputs: none.
        Outputs: none.
        """
        planned_list_list = self.quarters()
        planned_list_list[3] = planned_list_list[3] + [
            self.discovered_list[0]]
        exit_i, error_str = self.merge(self.write_shards(planned_list_list))
        self.assertEqual(exit_i, 1)
        self.assertIn(self.discovered_list[0] + " ran in more than one",
                      error_str)

    @covers("PCR-00128")
    def test_missing_test_fails(self) -> None:
        """A test planned in no shard fails the merge and is named.

        Inputs: none.
        Outputs: none.
        """
        planned_list_list = self.quarters()
        planned_list_list[2] = planned_list_list[2][1:]
        exit_i, error_str = self.merge(self.write_shards(planned_list_list))
        self.assertEqual(exit_i, 1)
        self.assertIn(self.discovered_list[6] + " ran in no shard",
                      error_str)

    @covers("PCR-00128")
    def test_missing_shard_file_fails(self) -> None:
        """A shard whose artifact is missing fails the merge.

        Inputs: none.
        Outputs: none.
        """
        results_str = self.write_shards(self.quarters())
        shutil.rmtree(os.path.join(results_str, "test-results-2"))
        exit_i, error_str = self.merge(results_str)
        self.assertEqual(exit_i, 1)
        self.assertIn("Shard 2 of 4 reported no result", error_str)

    @covers("PCR-00128")
    def test_failed_test_of_one_shard_fails(self) -> None:
        """A failed test in one shard fails the merged run.

        Inputs: none.
        Outputs: none.
        """
        exit_i, _ = self.merge(self.write_shards(
            self.quarters(), {self.discovered_list[11]: FAILED_STR}))
        self.assertEqual(exit_i, 1)

    @covers("PCR-00128")
    def test_empty_folder_fails(self) -> None:
        """No shard result at all fails the merge.

        Inputs: none.
        Outputs: none.
        """
        results_str = os.path.join(self.folder_str, "empty")
        os.makedirs(results_str)
        exit_i, error_str = self.merge(results_str)
        self.assertEqual(exit_i, 1)
        self.assertIn("No shard reported any result", error_str)


@unittest.skipUnless(YAML_AVAILABLE_B and BASH_AVAILABLE_B,
                     "PyYAML or bash is not installed")
class FinalCheckStepTest(unittest.TestCase):
    """Run the last step of the "tests" job with the job results."""

    @classmethod
    def setUpClass(cls) -> None:
        """Read the script of the final step.

        Inputs: none.
        Outputs: none.
        """
        import yaml
        with open(WORKFLOW_PATH_STR, encoding="utf-8") as workflow_file:
            workflow_dict = yaml.safe_load(workflow_file)
        step_list = workflow_dict["jobs"]["tests"]["steps"]
        cls.script_str = next(step_dict["run"] for step_dict in step_list
                              if step_dict.get("name")
                              == FINAL_STEP_NAME_STR)

    def run_step(self, changes_str: str, shards_str: str,
                 full_suite_str: str) -> int:
        """Run the step's script as GitHub would.

        Inputs:
            changes_str: needs.changes.result.
            shards_str: needs.test-shard.result.
            full_suite_str: the decision of the changes job, maybe empty.
        Outputs: the exit code of the script.
        """
        environment_dict = dict(os.environ, CHANGES_RESULT=changes_str,
                                SHARDS_RESULT=shards_str,
                                FULL_SUITE=full_suite_str)
        return subprocess.run(["bash", "-e", "-c", self.script_str],
                              env=environment_dict, capture_output=True,
                              check=False).returncode

    @covers("PCR-00128", "PCR-00079")
    def test_outcomes(self) -> None:
        """Only succeeded shards, or shards skipped by decision, pass.

        Inputs: none.
        Outputs: none.
        """
        case_list = [
            ("success", "success", "true", 0),
            ("success", "skipped", "false", 0),
            ("success", "failure", "true", 1),
            ("success", "cancelled", "true", 1),
            ("success", "skipped", "true", 1),
            ("success", "skipped", "", 1),
            ("success", "success", "", 0),
            ("failure", "success", "", 1),
            ("cancelled", "skipped", "", 1),
        ]
        for changes_str, shards_str, full_suite_str, exit_i in case_list:
            with self.subTest(changes=changes_str, shards=shards_str,
                              full_suite=full_suite_str):
                self.assertEqual(self.run_step(changes_str, shards_str,
                                               full_suite_str), exit_i)


if __name__ == "__main__":
    unittest.main()
