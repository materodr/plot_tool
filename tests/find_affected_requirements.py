"""Find the HLFRs that a branch affects (PCR-00059).

A branch affects an HLFR when, since it left its base branch, it changes:
- the text of the HLFR or of one of its child LLFRs;
- a function in src whose lines name one of its child LLFRs (COR-00010).

The files are read at the head commit, because the line numbers of the
diff refer to it. Changes in src outside a function don't count, because
no comment ties them to a requirement. The script uses only the standard
library and git.
"""

import ast
import re
import subprocess
from typing import Optional

HIGH_LEVEL_PATH_STR = "docs/requirements/high_level_functional_requirements.md"
LOW_LEVEL_PATH_STR = "docs/requirements/low_level_functional_requirements.md"
HEADING_PATTERN_STR = r"^### ((?:HLFR|LLFR)-\d{5}) (.+)$"
PARENT_PATTERN_STR = r"^\*Parent: (.+)\*$"
FILE_PATTERN_STR = r"^\+\+\+ b/(.+)$"
HUNK_PATTERN_STR = r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@"
LLFR_PATTERN_STR = r"LLFR-\d{5}"
DELETED_TITLE_STR = "DELETED"


def run_git(folder_str: str, *argument_tuple: str) -> str:
    """Run git and return what it prints.

    Inputs:
        folder_str: a folder of the git checkout.
        argument_tuple: the arguments of git.
    Outputs: the standard output of git. Raises OSError or
        subprocess.CalledProcessError when git fails.
    """
    return subprocess.run(["git", "-C", folder_str] + list(argument_tuple),
                          check=True, capture_output=True, text=True,
                          encoding="utf-8").stdout


def parse_changed_lines(diff_str: str) -> dict:
    """Read which lines of each file a diff changes.

    Inputs:
        diff_str: the output of git diff --unified=0.
    Outputs: a dict from each file path to the set of its changed line
        numbers. A removal counts as the line next to where it was.
    """
    changed_line_dict = {}
    path_str = ""
    for line_str in diff_str.splitlines():
        file_match = re.match(FILE_PATTERN_STR, line_str)
        if file_match:
            path_str = file_match.group(1)
            changed_line_dict[path_str] = set()
            continue
        if line_str.startswith("+++ "):
            # A deleted file ("+++ /dev/null") has no lines at the head.
            path_str = ""
            continue
        hunk_match = re.match(HUNK_PATTERN_STR, line_str)
        if hunk_match and path_str:
            start_i = int(hunk_match.group(1))
            count_i = int(hunk_match.group(2) or 1)
            changed_line_dict[path_str].update(
                range(start_i, start_i + max(count_i, 1) + 1 - (count_i > 0)))
    return changed_line_dict


def requirements_on_lines(text_str: str, line_set: set) -> set:
    """Find the requirements whose sections hold the given lines.

    Inputs:
        text_str: the text of a requirement file.
        line_set: line numbers of that file, counted from 1.
    Outputs: the set of requirement IDs, without deleted requirements.
    """
    id_set = set()
    current_id_str = ""
    for line_number_i, line_str in enumerate(text_str.splitlines(), 1):
        heading_match = re.match(HEADING_PATTERN_STR, line_str)
        if heading_match:
            is_deleted_b = heading_match.group(2) == DELETED_TITLE_STR
            current_id_str = "" if is_deleted_b else heading_match.group(1)
        elif line_str.startswith("#"):
            current_id_str = ""
        if current_id_str and line_number_i in line_set:
            id_set.add(current_id_str)
    return id_set


def llfrs_of_changed_functions(source_str: str, line_set: set) -> set:
    """Find the LLFRs named by the functions that hold the given lines.

    Inputs:
        source_str: the Python source of a file.
        line_set: line numbers of that file, counted from 1.
    Outputs: the set of LLFR IDs. A file that can't be parsed gives none.
    """
    try:
        tree = ast.parse(source_str)
    except (SyntaxError, ValueError):
        return set()
    source_line_list = source_str.splitlines()
    id_set = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if line_set & set(range(node.lineno, node.end_lineno + 1)):
                body_str = "\n".join(
                    source_line_list[node.lineno - 1:node.end_lineno])
                id_set.update(re.findall(LLFR_PATTERN_STR, body_str))
    return id_set


def read_parents(low_level_text_str: str) -> dict:
    """Read the parent HLFRs of each LLFR.

    Inputs:
        low_level_text_str: the text of the low-level requirement file.
    Outputs: a dict from each LLFR ID to the list of its parent HLFR IDs.
    """
    parent_dict = {}
    current_id_str = ""
    for line_str in low_level_text_str.splitlines():
        heading_match = re.match(HEADING_PATTERN_STR, line_str)
        if heading_match:
            current_id_str = heading_match.group(1)
            continue
        parent_match = re.match(PARENT_PATTERN_STR, line_str)
        if parent_match and current_id_str:
            parent_dict[current_id_str] = [
                parent_str.strip()
                for parent_str in parent_match.group(1).split(",")]
    return parent_dict


def find_affected_hlfrs(base_str: str, head_str: str,
                        folder_str: str) -> Optional[set]:
    """Find the HLFRs that a branch affects.

    Inputs:
        base_str: the branch the pull request goes into.
        head_str: the branch or commit of the pull request.
        folder_str: a folder of the git checkout.
    Outputs: the set of HLFR IDs, or None when git can't tell.
    """
    try:
        changed_line_dict = parse_changed_lines(run_git(
            folder_str, "diff", "--unified=0",
            f"origin/{base_str}...{head_str}", "--",
            HIGH_LEVEL_PATH_STR, LOW_LEVEL_PATH_STR, "src"))
        low_level_text_str = run_git(folder_str, "show",
                                     f"{head_str}:{LOW_LEVEL_PATH_STR}")
        affected_id_set = set()
        for path_str, line_set in changed_line_dict.items():
            text_str = run_git(folder_str, "show", f"{head_str}:{path_str}")
            if path_str.startswith("docs/"):
                affected_id_set |= requirements_on_lines(text_str, line_set)
            elif path_str.endswith(".py"):
                affected_id_set |= llfrs_of_changed_functions(text_str,
                                                              line_set)
    except (OSError, subprocess.CalledProcessError):
        return None
    parent_dict = read_parents(low_level_text_str)
    hlfr_id_set = set()
    for id_str in affected_id_set:
        if id_str.startswith("HLFR"):
            hlfr_id_set.add(id_str)
        else:
            hlfr_id_set.update(parent_dict.get(id_str, []))
    return hlfr_id_set
