"""Test the quality of the requirements (PCR-00037).

Usage:
    python tests/check_requirements.py [--folder PATH] [--output PATH]

The script reads the four requirement files in docs/requirements and
checks that:
- each ID is valid, used once, and the IDs of a prefix have no gaps
  (PCR-00045);
- each ID named anywhere in the files exists;
- each active LLFR has one Parent line that names existing HLFRs
  (PCR-00031), and each active HLFR has at least one child LLFR
  (PCR-00055);
- each active requirement uses the word "must" exactly once in its
  statement (PCR-00036). Note and Parent lines are not part of the
  statement, and deleted requirements are skipped. A mention of the
  words in quotes or backticks, such as "must not", is not a use;
- each active requirement whose ID is above the last ID of its prefix
  when PCR-00049 was added (LAST_ID_BEFORE_POSITIVE_RULE_DICT) states
  its obligation without the words "must not" (PCR-00049), in its
  statement only.

A script can't tell whether a requirement talks about only one thing, so
the second half of PCR-00036 still has to be checked by reading it
(PCR-00048). The script doesn't check the older requirements against
PCR-00049 either, even when they change: the reviewer of PCR-00048 does.
It can't tell whether a requirement is clear and unambiguous (PCR-00054)
either: the requirements review of the requirement-validation skill and
the reviewer of PCR-00056 do.

The script prints a Markdown report, or writes it to --output for the
pull request (PCR-00038), and exits with code 1 when it finds a problem.
It uses only the standard library, so any Python 3 can run it.
"""

import argparse
import os
import re
import sys

TESTS_FOLDER_STR = os.path.dirname(os.path.abspath(__file__))
REPOSITORY_ROOT_STR = os.path.dirname(TESTS_FOLDER_STR)
DEFAULT_FOLDER_STR = os.path.join(REPOSITORY_ROOT_STR, "docs",
                                  "requirements")
# COR, PCR, HLFR and LLFR: the prefix kept in each file (README.md).
PREFIX_FILE_DICT = {
    "COR": "code_and_organization.md",
    "PCR": "process_of_collaboration.md",
    "HLFR": "high_level_functional_requirements.md",
    "LLFR": "low_level_functional_requirements.md",
}
HEADING_PATTERN_STR = r"^### (\S+) (.*)$"
VALID_ID_PATTERN_STR = r"^(COR|PCR|HLFR|LLFR)-\d{5}$"
REFERENCE_PATTERN_STR = r"\b(?:COR|PCR|HLFR|LLFR)-\d{5}\b"
PARENT_PATTERN_STR = r"^\*Parent: (.+)\*$"
MUST_PATTERN_STR = r"\bmust\b"
MUST_NOT_PATTERN_STR = r"\bmust\s+not\b"
# PCR-00036, PCR-00049: a quoted mention of the words is not a use.
MUST_MENTION_PATTERN_STR = r"[\"`]must(?:\s+not)?[\"`]"
# PCR-00049: the last ID of each prefix when the rule was added. Only
# the requirements created after it must avoid "must not".
LAST_ID_BEFORE_POSITIVE_RULE_DICT = {
    "COR": 22,
    "PCR": 49,
    "HLFR": 112,
    "LLFR": 885,
}
DELETED_STR = "DELETED"
ID_RULE_STR = "IDs"
REFERENCE_RULE_STR = "References"
PARENT_RULE_STR = "Parent links"
CHILD_RULE_STR = "HLFR children"
MUST_RULE_STR = "One must"
POSITIVE_RULE_STR = "Positive statement"


def read_requirement_file(path_str: str) -> list:
    """Split one requirement file into its requirements.

    Inputs:
        path_str: the path of the requirement file.
    Outputs: a list of dicts, in file order, with the keys "id", "title"
        and "body" (the lines below the heading, up to the next heading).
    """
    with open(path_str, encoding="utf-8") as requirement_file:
        line_list = requirement_file.read().splitlines()
    entry_list = []
    current_entry_dict = None
    for line_str in line_list:
        heading_match = re.match(HEADING_PATTERN_STR, line_str)
        if heading_match:
            current_entry_dict = {"id": heading_match.group(1),
                                  "title": heading_match.group(2),
                                  "body": []}
            entry_list.append(current_entry_dict)
        elif line_str.startswith("#"):
            current_entry_dict = None
        elif current_entry_dict is not None:
            current_entry_dict["body"].append(line_str)
    return entry_list


def is_deleted(entry_dict: dict) -> bool:
    """Tell whether a requirement is a deleted one (PCR-00043).

    Inputs:
        entry_dict: a requirement from read_requirement_file.
    Outputs: True when its title and its text are both DELETED.
    """
    text_list = [line_str for line_str in entry_dict["body"] if line_str]
    return entry_dict["title"] == DELETED_STR and text_list == [DELETED_STR]


def statement_text(entry_dict: dict) -> str:
    """Return the statement of a requirement.

    Inputs:
        entry_dict: a requirement from read_requirement_file.
    Outputs: the text above its first Note or Parent line.
    """
    statement_line_list = []
    for line_str in entry_dict["body"]:
        if line_str.startswith("Note:") or line_str.startswith("*Parent:"):
            break
        statement_line_list.append(line_str)
    return "\n".join(statement_line_list)


def statement_without_mentions(entry_dict: dict) -> str:
    """Return the statement of a requirement without quoted mentions.

    Inputs:
        entry_dict: a requirement from read_requirement_file.
    Outputs: the statement, with each quoted "must" or "must not"
        removed, because a mention of the words is not a use of them
        (PCR-00036, PCR-00049).
    """
    return re.sub(MUST_MENTION_PATTERN_STR, "", statement_text(entry_dict),
                  flags=re.IGNORECASE)


def check_identifiers(prefix_str: str, entry_list: list) -> list:
    """Check the IDs of one file (PCR-00044, PCR-00045).

    Inputs:
        prefix_str: the prefix that the file must use.
        entry_list: the requirements of the file.
    Outputs: a list of (rule, ID, description) tuples, one per problem.
    """
    problem_list = []
    seen_number_set = set()
    for entry_dict in entry_list:
        id_str = entry_dict["id"]
        if (not re.match(VALID_ID_PATTERN_STR, id_str)
                or not id_str.startswith(prefix_str + "-")):
            problem_list.append((ID_RULE_STR, id_str,
                                 f"not a valid {prefix_str} ID"))
            continue
        number_i = int(id_str.split("-")[1])
        if number_i in seen_number_set:
            problem_list.append((ID_RULE_STR, id_str, "used more than once"))
        seen_number_set.add(number_i)
    if seen_number_set:
        for number_i in range(1, max(seen_number_set) + 1):
            if number_i not in seen_number_set:
                problem_list.append((ID_RULE_STR,
                                     f"{prefix_str}-{number_i:05d}",
                                     "missing, IDs must not have gaps"))
    return problem_list


def check_references(entry_list: list, known_id_set: set) -> list:
    """Check that the IDs named in the requirements exist.

    Inputs:
        entry_list: the requirements of every file.
        known_id_set: the IDs of every file.
    Outputs: a list of (rule, ID, description) tuples, one per problem.
    """
    problem_list = []
    for entry_dict in entry_list:
        text_str = "\n".join([entry_dict["title"]] + entry_dict["body"])
        for reference_str in sorted(set(re.findall(REFERENCE_PATTERN_STR,
                                                   text_str))):
            if reference_str not in known_id_set:
                problem_list.append((REFERENCE_RULE_STR, entry_dict["id"],
                                     f"names unknown {reference_str}"))
    return problem_list


def check_parents(hlfr_list: list, llfr_list: list) -> list:
    """Check the links between LLFRs and HLFRs (PCR-00031, PCR-00055).

    Inputs:
        hlfr_list: the HLFRs.
        llfr_list: the LLFRs.
    Outputs: a list of (rule, ID, description) tuples, one per problem.
    """
    problem_list = []
    hlfr_id_set = {entry_dict["id"] for entry_dict in hlfr_list}
    child_parent_set = set()
    for entry_dict in llfr_list:
        if is_deleted(entry_dict):
            continue
        parent_line_list = [
            line_str for line_str in entry_dict["body"]
            if re.match(PARENT_PATTERN_STR, line_str)]
        if len(parent_line_list) != 1:
            problem_list.append((
                PARENT_RULE_STR, entry_dict["id"],
                f"has {len(parent_line_list)} Parent lines, not 1"))
            continue
        parent_text_str = re.match(PARENT_PATTERN_STR,
                                   parent_line_list[0]).group(1)
        for parent_str in parent_text_str.split(","):
            parent_str = parent_str.strip()
            child_parent_set.add(parent_str)
            if parent_str not in hlfr_id_set:
                problem_list.append((PARENT_RULE_STR, entry_dict["id"],
                                     f"names unknown parent {parent_str}"))
    for entry_dict in hlfr_list:
        if (not is_deleted(entry_dict)
                and entry_dict["id"] not in child_parent_set):
            problem_list.append((CHILD_RULE_STR, entry_dict["id"],
                                 "has no child LLFR"))
    return problem_list


def check_one_must(entry_list: list) -> list:
    """Check that each statement uses "must" exactly once (PCR-00036).

    Inputs:
        entry_list: the requirements of every file.
    Outputs: a list of (rule, ID, description) tuples, one per problem.
    """
    problem_list = []
    for entry_dict in entry_list:
        if is_deleted(entry_dict):
            continue
        must_count_i = len(re.findall(MUST_PATTERN_STR,
                                      statement_without_mentions(entry_dict),
                                      re.IGNORECASE))
        if must_count_i != 1:
            problem_list.append((MUST_RULE_STR, entry_dict["id"],
                                 f'uses "must" {must_count_i} times, not 1'))
    return problem_list


def is_new_requirement(id_str: str) -> bool:
    """Tell whether a requirement was created after PCR-00049.

    Inputs:
        id_str: the ID of the requirement.
    Outputs: True when the ID is valid and its number is above the last
        number of its prefix in LAST_ID_BEFORE_POSITIVE_RULE_DICT.
    """
    if not re.match(VALID_ID_PATTERN_STR, id_str):
        return False
    prefix_str, number_str = id_str.split("-")
    return int(number_str) > LAST_ID_BEFORE_POSITIVE_RULE_DICT[prefix_str]


def check_positive_statements(entry_list: list) -> list:
    """Check that new statements don't use "must not" (PCR-00049).

    Inputs:
        entry_list: the requirements of every file.
    Outputs: a list of (rule, ID, description) tuples, one per problem.
    """
    problem_list = []
    for entry_dict in entry_list:
        if is_deleted(entry_dict) or not is_new_requirement(
                entry_dict["id"]):
            continue
        if re.search(MUST_NOT_PATTERN_STR,
                     statement_without_mentions(entry_dict), re.IGNORECASE):
            problem_list.append((POSITIVE_RULE_STR, entry_dict["id"],
                                 'uses "must not" in a new requirement'))
    return problem_list


def check_requirement_folder(folder_str: str) -> tuple:
    """Run every check on the requirement files of a folder.

    Inputs:
        folder_str: the folder that holds the four requirement files.
    Outputs: a tuple (active_count_i, problem_list), where active_count_i
        is the number of requirements that are not deleted and
        problem_list holds (rule, ID, description) tuples.
    """
    entries_of_prefix_dict = {}
    problem_list = []
    for prefix_str, file_name_str in PREFIX_FILE_DICT.items():
        entry_list = read_requirement_file(os.path.join(folder_str,
                                                        file_name_str))
        entries_of_prefix_dict[prefix_str] = entry_list
        problem_list.extend(check_identifiers(prefix_str, entry_list))
    all_entry_list = [entry_dict
                      for entry_list in entries_of_prefix_dict.values()
                      for entry_dict in entry_list]
    known_id_set = {entry_dict["id"] for entry_dict in all_entry_list}
    problem_list.extend(check_references(all_entry_list, known_id_set))
    problem_list.extend(check_parents(entries_of_prefix_dict["HLFR"],
                                      entries_of_prefix_dict["LLFR"]))
    problem_list.extend(check_one_must(all_entry_list))
    problem_list.extend(check_positive_statements(all_entry_list))
    active_count_i = sum(not is_deleted(entry_dict)
                         for entry_dict in all_entry_list)
    return active_count_i, problem_list


def build_report(active_count_i: int, problem_list: list) -> str:
    """Write the result of the checks as Markdown (PCR-00038).

    Inputs:
        active_count_i: the number of requirements that are not deleted.
        problem_list: the (rule, ID, description) tuples of the checks.
    Outputs: the report text.
    """
    result_str = "fail" if problem_list else "pass"
    line_list = ["## Requirements quality", "",
                 f"Result: **{result_str}**, {len(problem_list)} problems "
                 f"in {active_count_i} active requirements.", "",
                 "| Check | Problems |", "|---|---|"]
    for rule_str in (ID_RULE_STR, REFERENCE_RULE_STR, PARENT_RULE_STR,
                     CHILD_RULE_STR, MUST_RULE_STR, POSITIVE_RULE_STR):
        rule_count_i = sum(problem_tuple[0] == rule_str
                           for problem_tuple in problem_list)
        line_list.append(f"| {rule_str} | {rule_count_i} |")
    if problem_list:
        line_list.extend(["", "| Requirement | Check | Problem |",
                          "|---|---|---|"])
        for rule_str, id_str, description_str in sorted(
                problem_list, key=lambda problem_tuple: problem_tuple[1]):
            line_list.append(f"| {id_str} | {rule_str} | {description_str} |")
    return "\n".join(line_list) + "\n"


def main() -> int:
    """Check the requirements and report the result.

    Inputs: command-line arguments (see module docstring).
    Outputs: the process exit code (0 when no problem was found).
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--folder", default=DEFAULT_FOLDER_STR)
    parser.add_argument("--output", default="")
    argument_namespace = parser.parse_args()
    active_count_i, problem_list = check_requirement_folder(
        argument_namespace.folder)
    report_str = build_report(active_count_i, problem_list)
    if argument_namespace.output:
        with open(argument_namespace.output, "w",
                  encoding="utf-8") as report_file:
            report_file.write(report_str)
    else:
        print(report_str)
    return 1 if problem_list else 0


if __name__ == "__main__":
    sys.exit(main())
