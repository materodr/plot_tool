"""Self-tests for the CI shards: tests/ci_shards.py, the --shard and
--from-results options of tests/build_test_matrix.py and the jobs of
.github/workflows/tests.yml (PCR-00127, PCR-00128, PCR-00129,
PCR-00072, PCR-00079, PCR-00107)."""

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

from tests import ci_shards
from tests.build_test_matrix import (FAILED_STR, PASSED_STR,
                                     REPOSITORY_ROOT_STR, main)
from tests.support import covers

WORKFLOW_PATH_STR = os.path.join(REPOSITORY_ROOT_STR, ".github",
                                 "workflows", "tests.yml")
YAML_AVAILABLE_B = importlib.util.find_spec("yaml") is not None


def sample_case_class():
    """Make the TestCase class that the --shard self-tests run.

    It is made inside a function, so that discovery doesn't run it as a
    test of the suite.

    Inputs: none.
    Outputs: a unittest.TestCase subclass with two passing tests.
    """
    class SampleTest(unittest.TestCase):
        """Two passing tests."""

        def test_passes(self) -> None:
            """Pass.

            Inputs: none.
            Outputs: none.
            """

        def test_also_passes(self) -> None:
            """Pass.

            Inputs: none.
            Outputs: none.
            """

    return SampleTest


class FakeTest:
    """A stand-in for a discovered test, with an ID and a module."""

    def __init__(self, test_id_str: str) -> None:
        """Keep the test ID.

        Inputs:
            test_id_str: the dotted ID, for example "tests.a.C.test_x".
        Outputs: none.
        """
        self.test_id_str = test_id_str

    def id(self) -> str:
        """Return the test ID.

        Inputs: none.
        Outputs: the ID.
        """
        return self.test_id_str


def fake_tests(count_dict: dict) -> list:
    """Make fake tests, grouped by module.

    Inputs:
        count_dict: the number of tests of each module name.
    Outputs: the list of FakeTest objects, module by module.
    """
    return [FakeTest(f"{module_str}.Case.test_{index_i}")
            for module_str, count_i in count_dict.items()
            for index_i in range(count_i)]


def shard_result(shard_index_i: int, shard_count_i: int,
                 discovered_list: list, planned_list: list,
                 **extra_dict) -> dict:
    """Build the result dict of one shard, as read_results_folder does.

    Inputs:
        shard_index_i: the shard number.
        shard_count_i: the number of shards.
        discovered_list: the IDs of every discovered test.
        planned_list: the IDs planned in this shard.
        extra_dict: other entries, for example statuses.
    Outputs: the dict.
    """
    content_dict = {"format": ci_shards.RESULTS_FORMAT_STR,
                    "shard_index": shard_index_i,
                    "shard_count": shard_count_i,
                    "discovered_test_ids": discovered_list,
                    "planned_test_ids": planned_list,
                    "statuses": [[test_id_str, [], PASSED_STR]
                                 for test_id_str in planned_list]}
    content_dict.update(extra_dict)
    return content_dict


class AssignmentTest(unittest.TestCase):
    """Check how the modules are shared out among the shards."""

    @covers("PCR-00127")
    def test_every_module_in_exactly_one_shard(self) -> None:
        """Every module goes to one shard, and the result is repeatable.

        Inputs: none.
        Outputs: none.
        """
        seconds_dict = {f"tests.m{index_i}": float(index_i % 7 + 1)
                        for index_i in range(40)}
        for shard_count_i in (1, 2, 3, 4, 6):
            with self.subTest(shard_count_i=shard_count_i):
                shard_list = ci_shards.assign_shards(seconds_dict,
                                                     shard_count_i)
                self.assertEqual(len(shard_list), shard_count_i)
                all_list = [module_str for module_list in shard_list
                            for module_str in module_list]
                self.assertEqual(sorted(all_list), sorted(seconds_dict))
                self.assertEqual(shard_list, ci_shards.assign_shards(
                    dict(reversed(list(seconds_dict.items()))),
                    shard_count_i))

    @covers("PCR-00127")
    def test_balanced_by_time_not_by_count(self) -> None:
        """One long module fills a shard alone; short ones share the rest.

        Inputs: none.
        Outputs: none.
        """
        seconds_dict = {"tests.long": 100.0}
        seconds_dict.update({f"tests.short{index_i}": 10.0
                             for index_i in range(10)})
        shard_list = ci_shards.assign_shards(seconds_dict, 2)
        self.assertEqual(shard_list[0], ["tests.long"])
        self.assertEqual(len(shard_list[1]), 10)

    @covers("PCR-00127")
    def test_more_shards_than_modules(self) -> None:
        """Extra shards are empty, and a shard count below 1 is refused.

        Inputs: none.
        Outputs: none.
        """
        shard_list = ci_shards.assign_shards({"tests.a": 1.0}, 3)
        self.assertEqual(shard_list, [["tests.a"], [], []])
        with self.assertRaises(ValueError):
            ci_shards.assign_shards({"tests.a": 1.0}, 0)

    @covers("PCR-00127")
    def test_unknown_module_estimated_from_test_count(self) -> None:
        """A module not in the durations file gets count times the mean.

        Inputs: none.
        Outputs: none.
        """
        seconds_dict = ci_shards.expected_seconds(
            {"tests.known": 10, "tests.new": 4, "tests.gone_elsewhere": 2},
            {"tests.known": 5.0, "tests.deleted": 99.0})
        self.assertEqual(seconds_dict["tests.known"], 5.0)
        self.assertAlmostEqual(seconds_dict["tests.new"], 2.0)
        self.assertAlmostEqual(seconds_dict["tests.gone_elsewhere"], 1.0)
        self.assertNotIn("tests.deleted", seconds_dict)
        self.assertAlmostEqual(
            ci_shards.expected_seconds({"tests.a": 4}, {})["tests.a"],
            4 * ci_shards.DEFAULT_SECONDS_PER_TEST_S)

    @covers("PCR-00127")
    def test_shards_split_the_tests_in_discovery_order(self) -> None:
        """The shards hold every test once, each in discovery order.

        Inputs: none.
        Outputs: none.
        """
        test_list = fake_tests({"tests.a": 3, "tests.b": 5, "tests.c": 1,
                                "tests.d": 2})
        with mock.patch.object(ci_shards, "module_of",
                               lambda test: test.id().rsplit(".", 2)[0]), \
                mock.patch.object(ci_shards.unittest, "TestSuite", list):
            id_list_list = [
                [test.id() for test in ci_shards.select_shard(
                    test_list, shard_index_i, 3, {})[0]]
                for shard_index_i in (1, 2, 3)]
        all_list = [test_id_str for id_list in id_list_list
                    for test_id_str in id_list]
        self.assertEqual(sorted(all_list),
                         sorted(test.id() for test in test_list))
        position_dict = {test.id(): index_i
                         for index_i, test in enumerate(test_list)}
        for id_list in id_list_list:
            self.assertEqual(id_list, sorted(id_list,
                                             key=position_dict.get))

    @covers("PCR-00127")
    def test_module_of_a_test_and_of_an_import_failure(self) -> None:
        """A module that can't be imported is named after that module.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(
            ci_shards.module_of(sample_case_class()("test_passes")),
            __name__)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        package_str = os.path.join(folder.name, "shard_sample_package")
        os.makedirs(package_str)
        for name_str, text_str in (("__init__.py", ""),
                                   ("test_broken.py",
                                    "import no_such_library_for_shards\n")):
            with open(os.path.join(package_str, name_str), "w",
                      encoding="utf-8") as module_file:
                module_file.write(text_str)
        self.addCleanup(sys.path.remove, folder.name)
        suite = unittest.TestLoader().discover(package_str,
                                               top_level_dir=folder.name)
        failed_list = ci_shards.iterate_tests(suite)
        self.assertEqual([ci_shards.module_of(test) for test in failed_list],
                         ["shard_sample_package.test_broken"])

    @covers("PCR-00127")
    def test_parse_shard(self) -> None:
        """K/N is read, and a wrong shard is refused.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(ci_shards.parse_shard("2/4"), (2, 4))
        for shard_str in ("0/4", "5/4", "2", "a/b", "1/0"):
            with self.subTest(shard_str=shard_str), \
                    self.assertRaises(ValueError):
                ci_shards.parse_shard(shard_str)


class DurationsFileTest(unittest.TestCase):
    """Check the durations file that balances the shards."""

    def write(self, text_str: str) -> str:
        """Write a temporary durations file.

        Inputs:
            text_str: its text.
        Outputs: its path.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path_str = os.path.join(folder.name, "durations.json")
        with open(path_str, "w", encoding="utf-8") as durations_file:
            durations_file.write(text_str)
        return path_str

    @covers("PCR-00127")
    def test_committed_file_is_readable_and_covers_the_suite(self) -> None:
        """The committed file has a time for most modules of the suite.

        Inputs: none.
        Outputs: none.
        """
        seconds_dict = ci_shards.read_durations()
        self.assertGreater(len(seconds_dict), 100)
        self.assertTrue(all(seconds_f >= 0
                            for seconds_f in seconds_dict.values()))

    @covers("PCR-00127")
    def test_bad_files_give_no_entry(self) -> None:
        """A bad file or value only drops entries; it never raises.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(ci_shards.read_durations(
            os.path.join(tempfile.gettempdir(), "no_such_file.json")), {})
        for text_str in ("not json", "[]", '{"other": 1}',
                         '{"seconds_by_module": [1]}'):
            with self.subTest(text_str=text_str):
                self.assertEqual(
                    ci_shards.read_durations(self.write(text_str)), {})
        self.assertEqual(ci_shards.read_durations(self.write(json.dumps(
            {"seconds_by_module": {"a": 1, "b": -1, "c": "x", "d": True,
                                   "e": 2.5}}))), {"a": 1.0, "e": 2.5})

    @covers("PCR-00127")
    def test_written_file_reads_back(self) -> None:
        """durations_file_text writes a file that read_durations reads.

        Inputs: none.
        Outputs: none.
        """
        path_str = self.write(ci_shards.durations_file_text(
            {"tests.b": 2.0, "tests.a": 1.5}))
        self.assertEqual(ci_shards.read_durations(path_str),
                         {"tests.a": 1.5, "tests.b": 2.0})


class ShardProblemsTest(unittest.TestCase):
    """Check the checks of PCR-00128 on the shard results."""

    def setUp(self) -> None:
        """Make the IDs of four discovered tests.

        Inputs: none.
        Outputs: none.
        """
        self.id_list = ["tests.a.C.test_1", "tests.a.C.test_2",
                        "tests.b.C.test_1", "tests.b.C.test_2"]

    @covers("PCR-00128")
    def test_complete_shards_have_no_problem(self) -> None:
        """Two shards that ran every test once have no problem.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(ci_shards.shard_problems([
            shard_result(1, 2, self.id_list, self.id_list[:2]),
            shard_result(2, 2, self.id_list, self.id_list[2:])]), [])

    @covers("PCR-00128")
    def test_missing_shard(self) -> None:
        """A shard that reported nothing is named, and its tests too.

        Inputs: none.
        Outputs: none.
        """
        problem_list = ci_shards.shard_problems([
            shard_result(1, 2, self.id_list, self.id_list[:2])])
        self.assertIn("Shard 2 of 2 reported no result.", problem_list)
        self.assertIn("tests.b.C.test_1 ran in no shard.", problem_list)
        self.assertEqual(ci_shards.shard_problems([]),
                         ["No shard reported any result."])

    @covers("PCR-00128")
    def test_test_in_two_shards_and_shard_twice(self) -> None:
        """A test planned twice, and a shard reported twice, are named.

        Inputs: none.
        Outputs: none.
        """
        problem_list = ci_shards.shard_problems([
            shard_result(1, 2, self.id_list, self.id_list[:3]),
            shard_result(2, 2, self.id_list, self.id_list[2:]),
            shard_result(2, 2, self.id_list, [])])
        self.assertIn("tests.b.C.test_1 ran in more than one shard: 1, 2.",
                      problem_list)
        self.assertIn("Shard 2 of 2 reported 2 times.", problem_list)

    @covers("PCR-00128")
    def test_shards_that_disagree(self) -> None:
        """Different shard counts or discovered tests are problems.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(len(ci_shards.shard_problems([
            shard_result(1, 2, self.id_list, self.id_list),
            shard_result(2, 3, self.id_list, [])])), 1)
        self.assertIn("Shard 2 discovered other tests than shard 1.",
                      ci_shards.shard_problems([
                          shard_result(1, 2, self.id_list, self.id_list),
                          shard_result(2, 2, self.id_list[:1], [])]))


class MergeTest(unittest.TestCase):
    """Check how the results of the shards are joined."""

    @covers("PCR-00127")
    def test_statuses_in_discovery_order(self) -> None:
        """The merged statuses follow the discovery order of the tests.

        Inputs: none.
        Outputs: none.
        """
        id_list = ["tests.a.C.test_1", "tests.b.C.test_1",
                   "tests.c.C.test_1"]
        merged_list = ci_shards.merged_statuses([
            shard_result(1, 2, id_list, [id_list[1]]),
            shard_result(2, 2, id_list, [id_list[2], id_list[0]],
                         statuses=[[id_list[2], ["LLFR-00024"], FAILED_STR],
                                   ["setUpClass (tests.c.C)", [],
                                    FAILED_STR],
                                   [id_list[0], [], PASSED_STR]])])
        self.assertEqual([status_tuple[0] for status_tuple in merged_list],
                         id_list + ["setUpClass (tests.c.C)"])
        self.assertEqual(merged_list[2],
                         (id_list[2], ["LLFR-00024"], FAILED_STR))

    @covers("PCR-00072", "PCR-00127")
    def test_environment_limits_of_any_shard(self) -> None:
        """A limit of any shard counts, each text once.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(ci_shards.merged_environment_text(
            [shard_result(1, 2, [], []), shard_result(2, 2, [], [])]),
            (False, ""))
        self.assertEqual(ci_shards.merged_environment_text([
            shard_result(1, 3, [], [], environment_text="Shard 1 failed."),
            shard_result(2, 3, [], [], environment_text=None),
            shard_result(3, 3, [], [], environment_text="Shard 1 failed.")]),
            (True, "Shard 1 failed."))
        self.assertEqual(ci_shards.merged_environment_text(
            [shard_result(1, 1, [], [], environment_text="")]), (True, ""))

    @covers("PCR-00127")
    def test_slowest_tests_and_timing_report(self) -> None:
        """The 30 slowest tests of every shard are listed, slowest first.

        Inputs: none.
        Outputs: none.
        """
        pair_list = [(f"tests.a.C.test_{index_i}", float(index_i))
                     for index_i in range(40)]
        slowest_list = ci_shards.slowest_tests(pair_list)
        self.assertEqual(len(slowest_list), 30)
        self.assertEqual(slowest_list[0], ("tests.a.C.test_39", 39.0))
        report_str = ci_shards.timing_report([
            shard_result(1, 2, [], [], test_seconds=[list(pair) for pair
                                                     in pair_list[:20]],
                         run_seconds=12.0, expected_seconds=10.0),
            shard_result(2, 2, [], [], test_seconds=[list(pair) for pair
                                                     in pair_list[20:]])])
        self.assertIn("| 1 of 2 | 0 | 12.0 | 10.0 |", report_str)
        self.assertIn("1. `tests.a.C.test_39`: 39.00 s", report_str)
        self.assertIn("30. `tests.a.C.test_10`: 10.00 s", report_str)
        self.assertNotIn("test_9`", report_str)
        self.assertIn("No test duration was measured.",
                      ci_shards.slowest_tests_report([]))

    @covers("PCR-00127")
    def test_module_seconds_added_up(self) -> None:
        """The seconds of a module measured in two shards are added.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(ci_shards.merged_module_seconds([
            shard_result(1, 2, [], [], module_seconds={"tests.b": 1.04,
                                                       "tests.a": 2.0}),
            shard_result(2, 2, [], [], module_seconds={"tests.b": 1.0})]),
            {"tests.a": 2.0, "tests.b": 2.0})

    @covers("PCR-00128")
    def test_folder_with_another_json_file(self) -> None:
        """A JSON file that isn't a shard result is refused.

        Inputs: none.
        Outputs: none.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        os.makedirs(os.path.join(folder.name, "test-results-2"))
        ci_shards.write_results(
            os.path.join(folder.name, "test-results-2", "shard_2.json"),
            {"shard_index": 2, "shard_count": 2})
        ci_shards.write_results(os.path.join(folder.name, "shard_1.json"),
                                {"shard_index": 1, "shard_count": 2})
        self.assertEqual([content_dict["shard_index"] for content_dict
                          in ci_shards.read_results_folder(folder.name)],
                         [1, 2])
        with open(os.path.join(folder.name, "other.json"), "w",
                  encoding="utf-8") as other_file:
            other_file.write("{}")
        with self.assertRaises(ValueError):
            ci_shards.read_results_folder(folder.name)


class ShardOptionsTest(unittest.TestCase):
    """Check --shard and --from-results of tests/build_test_matrix.py."""

    def run_main(self, argument_list: list) -> int:
        """Run main() of build_test_matrix with sample tests.

        Inputs:
            argument_list: the command-line arguments after the script.
        Outputs: the exit code.
        """
        suite = unittest.TestLoader().loadTestsFromTestCase(
            sample_case_class())
        with mock.patch("sys.argv", ["build"] + argument_list), \
                mock.patch("tests.build_test_matrix.discover_suite",
                           return_value=suite), \
                mock.patch("tests.build_test_matrix.read_not_implemented",
                           return_value={}), \
                mock.patch("tests.build_test_matrix.source_hash",
                           return_value=""), \
                mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "",
                                             "GITHUB_STEP_SUMMARY": ""}), \
                mock.patch("sys.stdout", io.StringIO()), \
                mock.patch("sys.stderr", io.StringIO()):
            return main()

    def setUp(self) -> None:
        """Make a folder for the shard results.

        Inputs: none.
        Outputs: none.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder_str = folder.name
        self.results_str = os.path.join(folder.name, "results")
        os.makedirs(self.results_str)

    @covers("PCR-00127", "PCR-00128")
    def test_shards_then_merge(self) -> None:
        """Two shards and their merge give one matrix of every test.

        Inputs: none.
        Outputs: none.
        """
        for shard_index_i in (1, 2):
            self.assertEqual(self.run_main([
                "--shard", f"{shard_index_i}/2", "--results-output",
                os.path.join(self.results_str,
                             f"shard_{shard_index_i}.json"),
                "--environment-limit", "sample"]), 0)
        result_list = ci_shards.read_results_folder(self.results_str)
        self.assertEqual(ci_shards.shard_problems(result_list), [])
        self.assertEqual(len(ci_shards.merged_statuses(result_list)), 2)
        matrix_path_str = os.path.join(self.folder_str, "matrix.md")
        durations_path_str = os.path.join(self.folder_str, "d.json")
        self.assertEqual(self.run_main([
            "--from-results", self.results_str, "--output", matrix_path_str,
            "--durations-output", durations_path_str]), 0)
        with open(matrix_path_str, encoding="utf-8") as matrix_file:
            self.assertIn("# Test matrix", matrix_file.read())
        self.assertIn(__name__, ci_shards.read_durations(durations_path_str))

    @covers("PCR-00128")
    def test_missing_shard_fails_the_merge(self) -> None:
        """The merge fails when a shard wrote no result.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.run_main([
            "--shard", "1/2", "--results-output",
            os.path.join(self.results_str, "shard_1.json")]), 0)
        self.assertEqual(self.run_main([
            "--from-results", self.results_str, "--output",
            os.path.join(self.folder_str, "matrix.md")]), 1)

    @covers("PCR-00127")
    def test_wrong_shard_arguments(self) -> None:
        """A wrong shard, a shard with no output, or both modes fail.

        Inputs: none.
        Outputs: none.
        """
        output_str = os.path.join(self.results_str, "x.json")
        for argument_list in (["--shard", "3/2", "--results-output",
                               output_str],
                              ["--shard", "1/2"],
                              ["--shard", "1/2", "--from-results",
                               self.results_str]):
            with self.subTest(argument_list=argument_list):
                self.assertEqual(self.run_main(argument_list), 1)


@unittest.skipUnless(YAML_AVAILABLE_B, "PyYAML is not installed")
class WorkflowTest(unittest.TestCase):
    """Check the jobs of .github/workflows/tests.yml statically."""

    def setUp(self) -> None:
        """Read the workflow.

        Inputs: none.
        Outputs: none.
        """
        import yaml
        with open(WORKFLOW_PATH_STR, encoding="utf-8") as workflow_file:
            self.workflow_dict = yaml.safe_load(workflow_file)
        self.job_dict = self.workflow_dict["jobs"]

    def step(self, job_str: str, name_str: str) -> dict:
        """Find a step of a job by its name.

        Inputs:
            job_str: the job key.
            name_str: the step name.
        Outputs: the step dict.
        """
        for step_dict in self.job_dict[job_str]["steps"]:
            if step_dict.get("name") == name_str:
                return step_dict
        self.fail(f"No step {name_str!r} in job {job_str}.")

    @covers("PCR-00127", "PCR-00128")
    def test_jobs_and_their_names(self) -> None:
        """Only the collecting job is named tests; the shards are a matrix.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(
            set(self.job_dict),
            {"changes", "test-shard", "tests", "requirements-quality"})
        shard_dict = self.job_dict["test-shard"]
        self.assertEqual(shard_dict["needs"], "changes")
        self.assertNotIn("tests", shard_dict["name"].split()[:1])
        self.assertEqual(shard_dict["strategy"]["matrix"]["shard"],
                         [1, 2, 3, 4])
        self.assertFalse(shard_dict["strategy"]["fail-fast"])
        self.assertNotIn("name", self.job_dict["tests"])
        self.assertEqual(self.job_dict["tests"]["needs"],
                         ["changes", "test-shard"])

    @covers("PCR-00128", "PCR-00079")
    def test_tests_job_runs_after_a_failed_or_skipped_shard(self) -> None:
        """tests runs unless cancelled, and fails on a bad shard result.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(
            self.job_dict["tests"]["if"],
            "${{ !cancelled() && github.event_name == 'pull_request' }}")
        self.assertIn("!cancelled()", self.job_dict["test-shard"]["if"])
        self.assertIn("needs.changes.outputs.full_suite != 'false'",
                      self.job_dict["test-shard"]["if"])
        check_dict = self.step("tests", "Check that every shard succeeded")
        self.assertEqual(check_dict["if"], "always()")
        run_str = check_dict["run"]
        self.assertIn('"$FULL_SUITE" = "false" ] && '
                      '[ "$SHARDS_RESULT" = "skipped" ]', run_str)
        self.assertIn('[ "$SHARDS_RESULT" != "success" ]', run_str)
        self.assertIn('[ "$CHANGES_RESULT" != "success" ]', run_str)

    @covers("PCR-00107")
    def test_one_concurrency_group_for_every_job(self) -> None:
        """The cancel is set for the whole workflow, not per job.

        Inputs: none.
        Outputs: none.
        """
        self.assertTrue(
            self.workflow_dict["concurrency"]["cancel-in-progress"])
        for job_str, job_dict in self.job_dict.items():
            with self.subTest(job_str=job_str):
                self.assertNotIn("concurrency", job_dict)

    @covers("PCR-00129")
    def test_screenshots_only_into_main(self) -> None:
        """The screenshots depend on a step that runs only into main.

        Inputs: none.
        Outputs: none.
        """
        install_dict = self.step("tests",
                                 "Install the packages for the screenshots")
        self.assertIn("github.event.pull_request.base.ref == 'main'",
                      install_dict["if"])
        for name_str in ("Make screenshots of the interface",
                         "Post the screenshots on the pull request",
                         "Upload the screenshots"):
            with self.subTest(name_str=name_str):
                self.assertIn(
                    "steps.screenshot_packages.outcome == 'success'",
                    self.step("tests", name_str)["if"])
        for job_str in ("changes", "test-shard"):
            self.assertNotIn("make_screenshots",
                             json.dumps(self.job_dict[job_str]))

    @covers("PCR-00127")
    def test_hdf5_commit_and_pip_cache(self) -> None:
        """The HDF5 commit runs only in changes; the shards cache pip.

        Inputs: none.
        Outputs: none.
        """
        commit_list = [job_str for job_str, job_dict in self.job_dict.items()
                       if "git push" in json.dumps(job_dict)]
        self.assertEqual(commit_list, ["changes"])
        # Only the shards cache pip: every job of a run has the same cache
        # key, and a job that installs little must not save it first.
        for job_str, cache_list in (("changes", [None]),
                                    ("test-shard", ["pip"]),
                                    ("tests", [None])):
            with self.subTest(job_str=job_str):
                setup_list = [step_dict for step_dict
                              in self.job_dict[job_str]["steps"]
                              if step_dict.get("uses", "").startswith(
                                  "actions/setup-python")]
                self.assertEqual([step_dict["with"].get("cache")
                                  for step_dict in setup_list], cache_list)


if __name__ == "__main__":
    unittest.main()
