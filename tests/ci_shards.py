"""Split the test suite into parallel CI shards and merge their results
(PCR-00127, PCR-00128).

The Tests workflow runs the suite in several shard jobs at the same
time. Each shard discovers the whole suite, computes the same
assignment of test files (modules) to shards and runs only its own
modules (`tests/build_test_matrix.py --shard K/N`). The assignment is
balanced by the expected time of each module, read from
`tests/ci_test_durations.json`: the longest module goes to the shard
with the least expected time so far, the lower shard number first when
times are equal. A module that the file doesn't know is estimated from
its number of tests times the mean seconds per test of the known
modules.

Each shard writes its results as JSON. The `tests` job reads every
shard's file (`tests/build_test_matrix.py --from-results FOLDER`),
checks that every discovered test was planned in exactly one shard and
that every shard reported, and builds the one test matrix of the run.

Only the standard library is used (COR-00011).
"""

import json
import os
import unittest

TESTS_FOLDER_STR = os.path.dirname(os.path.abspath(__file__))
DURATIONS_PATH_STR = os.path.join(TESTS_FOLDER_STR, "ci_test_durations.json")
RESULTS_FORMAT_STR = "plot_tool shard results"
RESULTS_VERSION_I = 1
# Used only when no module of the durations file is known: about the
# mean seconds per test of the CI runs of 2026-11-06.
DEFAULT_SECONDS_PER_TEST_S = 0.25
FAILED_IMPORT_PREFIX_STR = "unittest.loader._FailedTest."
SLOWEST_COUNT_I = 30


def iterate_tests(suite) -> list:
    """Flatten a test suite into its test cases, in run order.

    Inputs:
        suite: a unittest.TestSuite, maybe nested, or a single test.
    Outputs: the list of the unittest.TestCase objects it holds.
    """
    if isinstance(suite, unittest.TestSuite):
        test_list = []
        for member in suite:
            test_list.extend(iterate_tests(member))
        return test_list
    return [suite]


def module_of(test) -> str:
    """Return the module name that a discovered test belongs to.

    Inputs:
        test: a unittest.TestCase, or the placeholder test of a module
            that could not be imported.
    Outputs: the dotted module name, for example "tests.view.test_x".
        A module that failed to import is named after that module, so
        that its import error is run, and fails, in exactly one shard.
    """
    test_id_str = test.id()
    if test_id_str.startswith(FAILED_IMPORT_PREFIX_STR):
        return test_id_str[len(FAILED_IMPORT_PREFIX_STR):]
    return type(test).__module__


def module_test_counts(test_list: list) -> dict:
    """Count the tests of each module.

    Inputs:
        test_list: the tests of iterate_tests.
    Outputs: a dict from each module name to its number of tests.
    """
    count_dict = {}
    for test in test_list:
        module_str = module_of(test)
        count_dict[module_str] = count_dict.get(module_str, 0) + 1
    return count_dict


def read_durations(path_str: str = DURATIONS_PATH_STR) -> dict:
    """Read the expected seconds of each module.

    Inputs:
        path_str: the durations file, tests/ci_test_durations.json by
            default.
    Outputs: a dict from module name to seconds. A missing or unreadable
        file, or a value that isn't a number of 0 or more, gives no
        entry, so that a bad file only unbalances the shards and never
        loses a test.
    """
    try:
        with open(path_str, encoding="utf-8") as durations_file:
            content_dict = json.load(durations_file)
        seconds_dict = content_dict["seconds_by_module"]
    except (OSError, ValueError, KeyError, TypeError):
        return {}
    if not isinstance(seconds_dict, dict):
        return {}
    return {str(module_str): float(seconds_s)
            for module_str, seconds_s in seconds_dict.items()
            if isinstance(seconds_s, (int, float))
            and not isinstance(seconds_s, bool) and seconds_s >= 0}


def expected_seconds(count_dict: dict, durations_dict: dict) -> dict:
    """Give every module of the suite an expected time.

    Inputs:
        count_dict: the number of tests of each module.
        durations_dict: the known seconds of some modules.
    Outputs: a dict from each module of count_dict to its expected
        seconds: the known value, or its number of tests times the mean
        seconds per test of the known modules of count_dict.
    """
    known_list = [module_str for module_str in count_dict
                  if module_str in durations_dict]
    known_tests_i = sum(count_dict[module_str] for module_str in known_list)
    known_seconds_s = sum(durations_dict[module_str]
                          for module_str in known_list)
    seconds_per_test_s = (known_seconds_s / known_tests_i if known_tests_i
                          else DEFAULT_SECONDS_PER_TEST_S)
    return {module_str: durations_dict.get(
                module_str, count_i * seconds_per_test_s)
            for module_str, count_i in count_dict.items()}


def assign_shards(seconds_dict: dict, shard_count_i: int) -> list:
    """Share the modules out among the shards, balanced by time.

    Inputs:
        seconds_dict: the expected seconds of each module.
        shard_count_i: the number of shards, 1 or more.
    Outputs: a list of shard_count_i sorted lists of module names; the
        list at index K-1 holds the modules of shard K. Every module is
        in exactly one list. The result depends only on the inputs, so
        every shard computes the same assignment.
    """
    if shard_count_i < 1:
        raise ValueError("The number of shards must be 1 or more.")
    module_list_list = [[] for _ in range(shard_count_i)]
    total_list = [0.0] * shard_count_i
    for module_str in sorted(seconds_dict,
                             key=lambda name_str: (-seconds_dict[name_str],
                                                   name_str)):
        shard_index_i = min(range(shard_count_i),
                            key=lambda index_i: (total_list[index_i],
                                                 index_i))
        module_list_list[shard_index_i].append(module_str)
        total_list[shard_index_i] += seconds_dict[module_str]
    return [sorted(module_list) for module_list in module_list_list]


def parse_shard(shard_str: str) -> tuple:
    """Read a shard argument such as "2/4".

    Inputs:
        shard_str: the text K/N.
    Outputs: the tuple (K, N). Raises ValueError unless 1 <= K <= N.
    """
    try:
        index_str, count_str = shard_str.split("/")
        shard_index_i, shard_count_i = int(index_str), int(count_str)
    except ValueError:
        raise ValueError(f"Write the shard as K/N, not {shard_str!r}.")
    if not 1 <= shard_index_i <= shard_count_i:
        raise ValueError(f"The shard {shard_str} is not between 1/N and N/N.")
    return shard_index_i, shard_count_i


def select_shard(test_list: list, shard_index_i: int, shard_count_i: int,
                 durations_dict: dict) -> tuple:
    """Pick the tests of one shard.

    Inputs:
        test_list: every discovered test, from iterate_tests.
        shard_index_i: the shard number K, from 1.
        shard_count_i: the number of shards N.
        durations_dict: the known seconds of the modules.
    Outputs: the tuple (suite, module list, expected seconds) of shard K:
        a unittest.TestSuite with its tests in discovery order, its
        sorted module names and the sum of their expected seconds.
    """
    seconds_dict = expected_seconds(module_test_counts(test_list),
                                    durations_dict)
    module_list = assign_shards(seconds_dict, shard_count_i)[
        shard_index_i - 1]
    module_set = set(module_list)
    suite = unittest.TestSuite(test for test in test_list
                               if module_of(test) in module_set)
    return (suite, module_list,
            sum(seconds_dict[module_str] for module_str in module_list))


def write_results(path_str: str, content_dict: dict) -> None:
    """Write the results of one shard as JSON.

    Inputs:
        path_str: the file to write.
        content_dict: the results: shard_index, shard_count,
            discovered_test_ids, planned_test_ids, statuses (a list of
            [test ID, requirement list, status]), environment_text,
            module_seconds, test_seconds and run_seconds.
    Outputs: none (writes the file, with the format and version).
    """
    output_dict = {"format": RESULTS_FORMAT_STR,
                   "version": RESULTS_VERSION_I}
    output_dict.update(content_dict)
    with open(path_str, "w", encoding="utf-8") as results_file:
        json.dump(output_dict, results_file, indent=1)
        results_file.write("\n")


def read_results_folder(folder_str: str) -> list:
    """Read every shard results file below a folder.

    Inputs:
        folder_str: the folder that holds the files, maybe in
            subfolders (one per downloaded artifact).
    Outputs: the list of the result dicts, sorted by shard number.
        Raises ValueError for a JSON file that isn't a shard results
        file, so that a wrong file never passes unnoticed.
    """
    result_list = []
    for root_str, _, name_list in os.walk(folder_str):
        for name_str in sorted(name_list):
            if not name_str.endswith(".json"):
                continue
            path_str = os.path.join(root_str, name_str)
            with open(path_str, encoding="utf-8") as results_file:
                content_dict = json.load(results_file)
            if (not isinstance(content_dict, dict)
                    or content_dict.get("format") != RESULTS_FORMAT_STR):
                raise ValueError(f"{path_str} is not a shard results file.")
            result_list.append(content_dict)
    return sorted(result_list,
                  key=lambda content_dict: content_dict.get("shard_index", 0))


def shard_problems(result_list: list) -> list:
    """Check that the shards together ran every test exactly once.

    Inputs:
        result_list: the result dicts of read_results_folder.
    Outputs: the list of problems as sentences, empty when every shard
        of 1 to N reported once, all shards discovered the same tests,
        and every discovered test was planned in exactly one shard
        (PCR-00128).
    """
    if not result_list:
        return ["No shard reported any result."]
    problem_list = []
    count_set = {content_dict.get("shard_count") for content_dict
                 in result_list}
    if len(count_set) != 1:
        return ["The shards don't agree on the number of shards: "
                + ", ".join(sorted(str(count_i) for count_i in count_set))
                + "."]
    shard_count_i = count_set.pop()
    index_list = [content_dict.get("shard_index") for content_dict
                  in result_list]
    for shard_index_i in range(1, shard_count_i + 1):
        reported_i = index_list.count(shard_index_i)
        if reported_i == 0:
            problem_list.append(
                f"Shard {shard_index_i} of {shard_count_i} reported no "
                "result.")
        elif reported_i > 1:
            problem_list.append(
                f"Shard {shard_index_i} of {shard_count_i} reported "
                f"{reported_i} times.")
    discovered_set = set(result_list[0].get("discovered_test_ids", []))
    for content_dict in result_list[1:]:
        if set(content_dict.get("discovered_test_ids", [])) != discovered_set:
            problem_list.append(
                f"Shard {content_dict.get('shard_index')} discovered other "
                f"tests than shard {result_list[0].get('shard_index')}.")
    shard_by_test_dict = {}
    for content_dict in result_list:
        for test_id_str in content_dict.get("planned_test_ids", []):
            shard_by_test_dict.setdefault(test_id_str, []).append(
                content_dict.get("shard_index"))
    for test_id_str in sorted(discovered_set - set(shard_by_test_dict)):
        problem_list.append(f"{test_id_str} ran in no shard.")
    for test_id_str in sorted(shard_by_test_dict):
        shard_list = shard_by_test_dict[test_id_str]
        if len(shard_list) > 1:
            problem_list.append(
                f"{test_id_str} ran in more than one shard: "
                + ", ".join(str(index_i) for index_i in shard_list) + ".")
    return problem_list


def merged_statuses(result_list: list) -> list:
    """Join the test statuses of every shard.

    Inputs:
        result_list: the result dicts of read_results_folder.
    Outputs: the list of (test ID, requirement list, status) tuples of
        all shards, as run_all_tests gives them, in the order of the
        discovered tests, so that the matrix lists the tests in the
        same order as a whole run. A status whose ID isn't a discovered
        test, such as the error of a class set-up, comes after them.
    """
    status_list = [(test_id_str, list(requirement_list), status_str)
                   for content_dict in result_list
                   for test_id_str, requirement_list, status_str
                   in content_dict.get("statuses", [])]
    discovered_list = (result_list[0].get("discovered_test_ids", [])
                       if result_list else [])
    position_dict = {test_id_str: position_i for position_i, test_id_str
                     in enumerate(discovered_list)}
    return sorted(status_list,
                  key=lambda status_tuple: position_dict.get(
                      status_tuple[0], len(position_dict)))


def merged_environment_text(result_list: list) -> tuple:
    """Join the environment limits of every shard (PCR-00072).

    Inputs:
        result_list: the result dicts of read_results_folder.
    Outputs: the tuple (limited, text): limited is True when any shard
        ran with --environment-limit, and text joins their different
        justification texts, each once, in shard order.
    """
    text_list = []
    limited_b = False
    for content_dict in result_list:
        text_str = content_dict.get("environment_text")
        if text_str is None:
            continue
        limited_b = True
        if text_str.strip() and text_str.strip() not in text_list:
            text_list.append(text_str.strip())
    return limited_b, " ".join(text_list)


def merged_module_seconds(result_list: list) -> dict:
    """Join the measured seconds of each module of every shard.

    Inputs:
        result_list: the result dicts of read_results_folder.
    Outputs: a dict from module name to seconds, rounded to 0.1 s.
    """
    seconds_dict = {}
    for content_dict in result_list:
        for module_str, seconds_s in content_dict.get(
                "module_seconds", {}).items():
            seconds_dict[module_str] = round(
                seconds_dict.get(module_str, 0.0) + seconds_s, 1)
    return dict(sorted(seconds_dict.items()))


def slowest_tests(test_seconds_list: list,
                  count_i: int = SLOWEST_COUNT_I) -> list:
    """Pick the slowest tests.

    Inputs:
        test_seconds_list: a list of (test ID, seconds) pairs.
        count_i: how many to keep, 30 by default.
    Outputs: the count_i slowest pairs, slowest first, then by test ID.
    """
    return sorted(test_seconds_list,
                  key=lambda pair_tuple: (-pair_tuple[1],
                                          pair_tuple[0]))[:count_i]


def timing_report(result_list: list) -> str:
    """Write the timing summary of a sharded run, in Markdown.

    Inputs:
        result_list: the result dicts of read_results_folder.
    Outputs: a text with the run time and the expected time of each
        shard, and the 30 slowest tests of the whole run, for the log
        and the step summary.
    """
    line_list = ["## Test timing", "",
                 "| Shard | Tests | Run time (s) | Expected (s) |",
                 "|---|---|---|---|"]
    for content_dict in result_list:
        line_list.append(
            f"| {content_dict.get('shard_index')} of "
            f"{content_dict.get('shard_count')} | "
            f"{len(content_dict.get('planned_test_ids', []))} | "
            f"{content_dict.get('run_seconds', 0):.1f} | "
            f"{content_dict.get('expected_seconds', 0):.1f} |")
    test_seconds_list = [(test_id_str, seconds_s)
                         for content_dict in result_list
                         for test_id_str, seconds_s
                         in content_dict.get("test_seconds", [])]
    line_list.extend(["", slowest_tests_report(test_seconds_list)])
    return "\n".join(line_list)


def slowest_tests_report(test_seconds_list: list) -> str:
    """Write the list of the slowest tests, in Markdown.

    Inputs:
        test_seconds_list: a list of (test ID, seconds) pairs.
    Outputs: a numbered list of the 30 slowest tests with their seconds.
    """
    line_list = [f"### The {SLOWEST_COUNT_I} slowest tests", ""]
    for number_i, (test_id_str, seconds_s) in enumerate(
            slowest_tests(test_seconds_list), start=1):
        line_list.append(f"{number_i}. `{test_id_str}`: {seconds_s:.2f} s")
    if len(line_list) == 2:
        line_list.append("No test duration was measured.")
    return "\n".join(line_list) + "\n"


def durations_file_text(seconds_dict: dict) -> str:
    """Write the text of a durations file.

    Inputs:
        seconds_dict: the measured seconds of each module.
    Outputs: the JSON text, ready to replace tests/ci_test_durations.json.
    """
    return json.dumps(
        {"comment": "Seconds of each test module in a CI run, used to "
                    "balance the CI shards (PCR-00127). Copy the "
                    "test_durations.json artifact of a recent run here "
                    "when the shards drift apart.",
         "seconds_by_module": dict(sorted(seconds_dict.items()))},
        indent=2) + "\n"
