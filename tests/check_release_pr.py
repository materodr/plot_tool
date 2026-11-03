"""Check that a pull request into main shows the requirements review.

Usage:
    python tests/check_release_pr.py --body-file PATH
    python tests/check_release_pr.py --hook

PCR-00050 asks for the review of the requirement-validation skill before
every pull request from develop to main, and PCR-00051 asks the pull
request to show its result, in a section with the heading of
SECTION_HEADING_STR. A script can't tell whether the review was good, so
this only checks that the section is there.

--body-file checks a saved pull request description, for the CI job. It
exits with code 1 when the section is missing or empty.

--hook is the Claude Code PreToolUse hook of .claude/settings.json. It
reads the hook's JSON from standard input and exits with code 2, which
blocks the command, when the command creates a pull request into main
without the section. It reads the command's text only, so it can't see
the value of a shell variable: a description or a file named through one
counts as missing, and the message says to name the file literally.

It uses only the standard library, so any Python 3 can run it.
"""

import argparse
import json
import os
import re
import sys

SECTION_HEADING_STR = "Requirement validation (PCR-00050)"
HEADING_PATTERN_STR = r"#{1,6}[ \t]+"
SECTION_PATTERN_STR = HEADING_PATTERN_STR + re.escape(SECTION_HEADING_STR)
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
    "Blocked: a pull request into main must show the requirements review "
    "(PCR-00050, PCR-00051). Run the requirement-validation skill on every "
    "requirement created or changed since the last merge into main, and "
    f"put its result in a section with the heading \"## "
    f"{SECTION_HEADING_STR}\". Give the description in the command itself "
    "or in a file named with a literal path, not through a shell variable."
)


def has_review_section(body_str: str) -> bool:
    """Tell whether a description has the review section, with content.

    Inputs:
        body_str: the text of the pull request description.
    Outputs: True when a line is the section's heading and a line that
        isn't blank follows it before the next heading.
    """
    in_section_b = False
    for line_str in body_str.splitlines():
        if in_section_b:
            if re.match(HEADING_PATTERN_STR, line_str):
                in_section_b = False
            elif line_str.strip():
                return True
        if re.fullmatch(SECTION_PATTERN_STR + r"\s*", line_str.strip()):
            in_section_b = True
    return False


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


def check_pr_create(command_str: str, folder_str: str) -> bool:
    """Tell whether a gh pr create command may run.

    Inputs:
        command_str: the command's text from gh pr create onward.
        folder_str: the folder the command runs in.
    Outputs: False when it targets main without the review section. With
        no --base, gh uses the repository's default branch, which is main.
    """
    base_str = option_value(r"(?:--base[= ]|-B[= ]?)", command_str)
    if base_str not in ("", "main"):
        return True
    path_str = option_value(r"(?:--body-file[= ]|-F[= ]?)", command_str)
    if path_str and path_str != "-":
        return has_review_section(read_text_file(path_str, folder_str))
    # The description is in the command itself: an option or a here
    # document. Its quotes and line breaks can't be read reliably here,
    # so the heading is enough, and the CI job checks the content.
    return re.search(SECTION_PATTERN_STR, command_str) is not None


def check_api_pulls(command_str: str, folder_str: str) -> bool:
    """Tell whether a gh api command on the pulls endpoint may run.

    Inputs:
        command_str: the command's text from gh api onward.
        folder_str: the folder the command runs in.
    Outputs: False when it creates a pull request into main without the
        review section. Reading pull requests is always allowed.
    """
    if re.search(r"(?:-X|--method)[= ]?\s*['\"]?GET\b", command_str):
        return True
    input_path_str = option_value(r"--input[= ]", command_str)
    if input_path_str:
        try:
            input_dict = json.loads(read_text_file(input_path_str,
                                                   folder_str))
        except ValueError:
            return False
        if input_dict.get("base") != "main":
            return True
        return has_review_section(str(input_dict.get("body") or ""))
    if not re.search(r"\bbase=['\"]?main\b", command_str):
        return True
    body_path_match = re.search(r"\bbody=@(['\"]?)(.+?)\1(?:\s|$)",
                                command_str, re.MULTILINE)
    if body_path_match:
        return has_review_section(read_text_file(body_path_match.group(2),
                                                 folder_str))
    return re.search(SECTION_PATTERN_STR, command_str) is not None


def command_may_run(command_str: str, folder_str: str) -> bool:
    """Tell whether a shell command may run under PCR-00050.

    Inputs:
        command_str: the whole shell command.
        folder_str: the folder the command runs in.
    Outputs: False when it creates a pull request into main without the
        review section, and True for any other command.
    """
    for pattern_str, check_function in ((PR_CREATE_PATTERN_STR,
                                         check_pr_create),
                                        (API_PULLS_PATTERN_STR,
                                         check_api_pulls)):
        match = re.search(pattern_str, command_str, re.MULTILINE)
        if match and not check_function(command_str[match.start():],
                                        folder_str):
            return False
    return True


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
    if command_may_run(command_str, folder_str):
        return 0
    print(BLOCKED_MESSAGE_STR, file=sys.stderr)
    return 2


def main() -> int:
    """Run the check that the command-line arguments ask for.

    Inputs: command-line arguments (see module docstring).
    Outputs: the process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--body-file", default="")
    parser.add_argument("--hook", action="store_true")
    argument_namespace = parser.parse_args()
    if argument_namespace.hook:
        return run_hook()
    with open(argument_namespace.body_file,
              encoding="utf-8") as body_file:
        body_str = body_file.read()
    if has_review_section(body_str):
        print(f"Result: pass, the section \"{SECTION_HEADING_STR}\" is there.")
        return 0
    print(f"Result: fail, the section \"{SECTION_HEADING_STR}\" is missing "
          "or empty (PCR-00051). Run the requirement-validation skill and "
          "add its result to the pull request description.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
