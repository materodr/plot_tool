"""Check that a pull request shows the requirements review it needs.

Usage:
    python tests/check_requirement_review.py --body-file PATH --base BRANCH
        --head COMMIT
    python tests/check_requirement_review.py --hook

The requirement-validation skill reviews the requirements, and the pull
request has to show the result in a section with its own heading:
- into main: every active requirement, under MAIN_HEADING_STR (PCR-00050,
  PCR-00051);
- into develop: the requirements that the branch adds, under
  DEVELOP_HEADING_STR (PCR-00052, PCR-00053). A branch that adds no
  requirement needs no section.

A script can't tell whether the review was good, so this only checks that
the section is there.

--body-file checks a saved pull request description, for the CI job. It
exits with code 1 when the section is missing or empty, or when git can't
tell which requirements the branch adds.

--hook is the Claude Code PreToolUse hook of .claude/settings.json. It
reads the hook's JSON from standard input and exits with code 2, which
blocks the command, when the command creates a pull request without the
section it needs. It reads the command's text only, so it can't see the
value of a shell variable: a description or a file named through one
counts as missing, and the message says to name the file literally.

It uses only the standard library, so any Python 3 can run it.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Optional

MAIN_BRANCH_STR = "main"
DEVELOP_BRANCH_STR = "develop"
MAIN_HEADING_STR = "Requirement validation (PCR-00050)"
DEVELOP_HEADING_STR = "Requirement validation (PCR-00052)"
HEADING_PATTERN_STR = r"#{1,6}[ \t]+"
# The four files of docs/requirements/README.md. README.md itself is left
# out because its examples look like requirements.
REQUIREMENT_FILE_LIST = [
    "docs/requirements/code_and_organization.md",
    "docs/requirements/process_of_collaboration.md",
    "docs/requirements/high_level_functional_requirements.md",
    "docs/requirements/low_level_functional_requirements.md",
]
DIFF_ID_PATTERN_STR = r"^([+-])### ((?:COR|PCR|HLFR|LLFR)-\d{5})\b"
# The start of a shell command, with any VARIABLE=value before it, so
# that a mention of the command inside other text doesn't count.
COMMAND_START_STR = r"(?:^|[;&|(])\s*(?:\w+=\S*\s+)*"
PR_CREATE_PATTERN_STR = COMMAND_START_STR + r"gh\s+pr\s+create\b"
API_PULLS_PATTERN_STR = (COMMAND_START_STR
                         + r"gh\s+api\b(?:[^\n;&|]|\\\n)*?"
                         + r"/pulls['\"]?(?:\s|$)")
OPTION_START_STR = r"(?:^|\s)"
QUOTED_VALUE_STR = r"\s*(['\"]?)(.+?)\1(?:\s|$)"
BLOCKED_MESSAGE_STR = (
    "Blocked: this pull request must show the requirements review ({scope}). "
    "Run the requirement-validation skill on {reviewed}, and put its result "
    "in a section with the heading \"## {heading}\". Give the description "
    "in the command itself or in a file named with a literal path, not "
    "through a shell variable."
)
MAIN_SCOPE_DICT = {"scope": "PCR-00050, PCR-00051",
                   "reviewed": "every active requirement",
                   "heading": MAIN_HEADING_STR}
DEVELOP_SCOPE_DICT = {"scope": "PCR-00052, PCR-00053",
                      "reviewed": "every requirement that this branch adds",
                      "heading": DEVELOP_HEADING_STR}


def has_review_section(body_str: str, heading_str: str) -> bool:
    """Tell whether a description has a review section, with content.

    Inputs:
        body_str: the text of the pull request description.
        heading_str: the section's heading, without its # characters.
    Outputs: True when a line is the section's heading and a line that
        isn't blank follows it before the next heading.
    """
    section_pattern_str = HEADING_PATTERN_STR + re.escape(heading_str)
    in_section_b = False
    for line_str in body_str.splitlines():
        if in_section_b:
            if re.match(HEADING_PATTERN_STR, line_str):
                in_section_b = False
            elif line_str.strip():
                return True
        if re.fullmatch(section_pattern_str, line_str.strip()):
            in_section_b = True
    return False


def added_requirement_ids(base_str: str, head_str: str,
                          folder_str: str) -> Optional[list]:
    """Find the requirements that a branch adds (PCR-00052).

    Inputs:
        base_str: the branch the pull request goes into.
        head_str: the branch or commit of the pull request.
        folder_str: a folder of the git checkout.
    Outputs: the sorted IDs that are new since the branch left the base,
        or None when git can't tell. A requirement that only changed
        isn't new, because its heading is both removed and added.
    """
    for head_try_str in (head_str, f"origin/{head_str}"):
        try:
            diff_str = subprocess.run(
                ["git", "-C", folder_str, "diff", "--unified=0",
                 f"origin/{base_str}...{head_try_str}", "--"]
                + REQUIREMENT_FILE_LIST,
                check=True, capture_output=True, text=True,
                encoding="utf-8").stdout
        except (OSError, subprocess.CalledProcessError):
            continue
        added_id_set = set()
        removed_id_set = set()
        for match in re.finditer(DIFF_ID_PATTERN_STR, diff_str, re.MULTILINE):
            target_set = added_id_set if match.group(1) == "+" \
                else removed_id_set
            target_set.add(match.group(2))
        return sorted(added_id_set - removed_id_set)
    return None


def needed_scope(base_str: str, head_str: str, folder_str: str) -> dict:
    """Choose the review section that a pull request needs.

    Inputs:
        base_str: the branch the pull request goes into.
        head_str: the branch or commit of the pull request.
        folder_str: a folder of the git checkout.
    Outputs: MAIN_SCOPE_DICT or DEVELOP_SCOPE_DICT, or an empty dict when
        it needs no section. When git can't tell what the branch adds, it
        needs none here, because the CI job still checks the pull request.
    """
    if base_str == MAIN_BRANCH_STR:
        return MAIN_SCOPE_DICT
    if base_str == DEVELOP_BRANCH_STR and added_requirement_ids(
            base_str, head_str, folder_str):
        return DEVELOP_SCOPE_DICT
    return {}


def read_text_file(path_str: str, folder_str: str) -> str:
    """Read a text file named by a command.

    Inputs:
        path_str: the file's path, as written in the command.
        folder_str: the folder that a relative path starts from.
    Outputs: the file's text, or an empty text when it can't be read.
    """
    full_path_str = os.path.join(folder_str, os.path.expanduser(path_str))
    try:
        with open(full_path_str, encoding="utf-8") as text_file:
            return text_file.read()
    except (OSError, UnicodeDecodeError):
        return ""


def option_value(pattern_str: str, text_str: str) -> str:
    """Find the value of a command option.

    Inputs:
        pattern_str: a pattern for the option's name and what joins it to
            its value.
        text_str: the command's text.
    Outputs: the value without its quotes, or an empty text when the
        command doesn't have the option.
    """
    match = re.search(OPTION_START_STR + pattern_str + QUOTED_VALUE_STR,
                      text_str, re.MULTILINE)
    return match.group(2) if match else ""


def check_pr_create(command_str: str, folder_str: str) -> dict:
    """Check a gh pr create command.

    Inputs:
        command_str: the command's text from gh pr create onward.
        folder_str: the folder the command runs in.
    Outputs: the scope whose section is missing, or an empty dict when the
        command may run. With no --base, gh uses the repository's default
        branch, which is main.
    """
    base_str = (option_value(r"(?:--base[= ]|-B[= ]?)", command_str)
                or MAIN_BRANCH_STR)
    head_str = option_value(r"(?:--head[= ]|-H[= ]?)", command_str) or "HEAD"
    scope_dict = needed_scope(base_str, head_str, folder_str)
    if not scope_dict:
        return {}
    path_str = option_value(r"(?:--body-file[= ]|-F[= ]?)", command_str)
    if path_str and path_str != "-":
        found_b = has_review_section(read_text_file(path_str, folder_str),
                                     scope_dict["heading"])
    else:
        # The description is in the command itself: an option or a here
        # document. Its quotes and line breaks can't be read reliably
        # here, so the heading is enough, and the CI job checks the
        # content.
        found_b = re.search(HEADING_PATTERN_STR
                            + re.escape(scope_dict["heading"]),
                            command_str) is not None
    return {} if found_b else scope_dict


def check_api_pulls(command_str: str, folder_str: str) -> dict:
    """Check a gh api command on the pulls endpoint.

    Inputs:
        command_str: the command's text from gh api onward.
        folder_str: the folder the command runs in.
    Outputs: the scope whose section is missing, or an empty dict when the
        command may run. Reading pull requests is always allowed.
    """
    if re.search(r"(?:-X|--method)[= ]?\s*['\"]?GET\b", command_str):
        return {}
    input_path_str = option_value(r"--input[= ]", command_str)
    if input_path_str:
        try:
            input_dict = json.loads(read_text_file(input_path_str,
                                                   folder_str))
        except ValueError:
            return MAIN_SCOPE_DICT
        scope_dict = needed_scope(str(input_dict.get("base")),
                                  str(input_dict.get("head") or "HEAD"),
                                  folder_str)
        if scope_dict and has_review_section(
                str(input_dict.get("body") or ""), scope_dict["heading"]):
            return {}
        return scope_dict
    base_match = re.search(r"\bbase=['\"]?([^\s'\"]+)", command_str)
    if not base_match:
        return {}
    head_match = re.search(r"\bhead=['\"]?([^\s'\"]+)", command_str)
    scope_dict = needed_scope(base_match.group(1),
                              head_match.group(1) if head_match else "HEAD",
                              folder_str)
    if not scope_dict:
        return {}
    body_path_match = re.search(r"\bbody=@(['\"]?)(.+?)\1(?:\s|$)",
                                command_str, re.MULTILINE)
    if body_path_match:
        found_b = has_review_section(
            read_text_file(body_path_match.group(2), folder_str),
            scope_dict["heading"])
    else:
        found_b = re.search(HEADING_PATTERN_STR
                            + re.escape(scope_dict["heading"]),
                            command_str) is not None
    return {} if found_b else scope_dict


def missing_scope(command_str: str, folder_str: str) -> dict:
    """Check a shell command against PCR-00051 and PCR-00053.

    Inputs:
        command_str: the whole shell command.
        folder_str: the folder the command runs in.
    Outputs: the scope whose section is missing when the command creates a
        pull request without it, and an empty dict for any other command.
    """
    for pattern_str, check_function in ((PR_CREATE_PATTERN_STR,
                                         check_pr_create),
                                        (API_PULLS_PATTERN_STR,
                                         check_api_pulls)):
        match = re.search(pattern_str, command_str, re.MULTILINE)
        if match:
            scope_dict = check_function(command_str[match.start():],
                                        folder_str)
            if scope_dict:
                return scope_dict
    return {}


def run_hook() -> int:
    """Check the command that Claude Code is about to run.

    Inputs: the hook's JSON on standard input.
    Outputs: the process exit code, 2 to block the command and 0 to let
        it run. Input that isn't understood lets the command run, because
        the CI job still checks the pull request.
    """
    try:
        hook_dict = json.load(sys.stdin)
        command_str = hook_dict["tool_input"]["command"]
    except (ValueError, KeyError, TypeError):
        return 0
    folder_str = hook_dict.get("cwd") or os.getcwd()
    scope_dict = missing_scope(command_str, folder_str)
    if not scope_dict:
        return 0
    print(BLOCKED_MESSAGE_STR.format(**scope_dict), file=sys.stderr)
    return 2


def check_body_file(body_path_str: str, base_str: str, head_str: str) -> int:
    """Check a saved pull request description, for the CI job.

    Inputs:
        body_path_str: the path of the saved description.
        base_str: the branch the pull request goes into.
        head_str: the commit of the pull request.
    Outputs: the process exit code, 0 when the description has what the
        pull request needs.
    """
    with open(body_path_str, encoding="utf-8") as body_file:
        body_str = body_file.read()
    if base_str == MAIN_BRANCH_STR:
        scope_dict = MAIN_SCOPE_DICT
    else:
        added_id_list = added_requirement_ids(base_str, head_str, os.getcwd())
        if added_id_list is None:
            print("Result: fail, git can't tell which requirements this "
                  "branch adds.")
            return 1
        if not added_id_list:
            print("Result: pass, this branch adds no requirement.")
            return 0
        print("This branch adds: " + ", ".join(added_id_list))
        scope_dict = DEVELOP_SCOPE_DICT
    if has_review_section(body_str, scope_dict["heading"]):
        print(f"Result: pass, the section \"{scope_dict['heading']}\" is "
              "there.")
        return 0
    print(f"Result: fail, the section \"{scope_dict['heading']}\" is missing "
          f"or empty ({scope_dict['scope']}). Run the "
          f"requirement-validation skill on {scope_dict['reviewed']} and add "
          "its result to the pull request description.")
    return 1


def main() -> int:
    """Run the check that the command-line arguments ask for.

    Inputs: command-line arguments (see module docstring).
    Outputs: the process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--body-file", default="")
    parser.add_argument("--base", default=MAIN_BRANCH_STR)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--hook", action="store_true")
    argument_namespace = parser.parse_args()
    if argument_namespace.hook:
        return run_hook()
    return check_body_file(argument_namespace.body_file,
                           argument_namespace.base, argument_namespace.head)


if __name__ == "__main__":
    sys.exit(main())
