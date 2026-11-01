"""Download the screenshots CI posted on a pull request and save PNGs.

Run from anywhere (the GitHub CLI ``gh`` must be logged in):

    python tests/user_tests/fetch_screenshots.py <pull number> \
        --output screenshots [--kind screenshot|before-screenshot]

CI (.github/workflows/tests.yml) posts each PNG made by
make_screenshots.py as base64 text split over several comments, each
starting with ``<!-- screenshot <name> part <i>/<n> ... -->``. This helper
reads those comments with ``gh api``, puts the parts of each image back
together in order and writes ``<output>/<name>.png``. Comments of the
kind ``before-screenshot`` hold images of the code before a change and
are never replaced by CI.
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys

DEFAULT_REPOSITORY_STR = "materodr/plot_tool"
DEFAULT_KIND_STR = "screenshot"
HEADER_PATTERN_STR = (r"^<!-- (?P<kind>[a-z-]+) (?P<name>[\w.-]+) "
                      r"part (?P<part>\d+)/(?P<count>\d+)[^>]*-->")
# The base64 text is the content of the body's fenced code block.
BASE64_BLOCK_PATTERN_STR = r"```\s*([A-Za-z0-9+/=\s]*?)\s*```"


def read_comment_list(repository_str: str, pull_number_i: int) -> list:
    """Return every comment of a pull request, oldest first.

    Inputs:
        repository_str: "owner/name" of the GitHub repository.
        pull_number_i: number of the pull request.
    Outputs: a list of comment dicts as returned by the GitHub API.
    """
    output_str = subprocess.run(
        ["gh", "api", "--paginate",
         f"repos/{repository_str}/issues/{pull_number_i}/comments",
         "--jq", ".[] | {id: .id, body: .body}"],
        check=True, capture_output=True, text=True).stdout
    return [json.loads(line_str) for line_str in output_str.splitlines()
            if line_str.strip()]


def assemble_image_dict(comment_list: list, kind_str: str) -> dict:
    """Put the base64 parts of each image together.

    Inputs:
        comment_list: comment dicts with a "body" key.
        kind_str: the comment kind to read ("screenshot" or
            "before-screenshot").
    Outputs: a dict image name -> PNG bytes, for every image whose parts
        are all present. When an image was posted several times, the
        last complete set of parts wins.
    """
    part_dict = {}
    count_dict = {}
    for comment_dict in comment_list:
        body_str = comment_dict["body"]
        match = re.match(HEADER_PATTERN_STR, body_str)
        if match is None or match.group("kind") != kind_str:
            continue
        name_str = match.group("name")
        block_match = re.search(BASE64_BLOCK_PATTERN_STR,
                                body_str[match.end():])
        if block_match is None:
            continue
        payload_str = "".join(block_match.group(1).split())
        part_dict.setdefault(name_str, {})[int(match.group("part"))] = (
            payload_str)
        count_dict[name_str] = int(match.group("count"))
    image_dict = {}
    for name_str, parts_dict in part_dict.items():
        count_i = count_dict[name_str]
        if sorted(parts_dict) != list(range(1, count_i + 1)):
            print(f"skipped {name_str}: parts missing", file=sys.stderr)
            continue
        image_dict[name_str] = base64.b64decode(
            "".join(parts_dict[index_i]
                    for index_i in range(1, count_i + 1)))
    return image_dict


def main() -> int:
    """Download, assemble and save the screenshots of a pull request.

    Inputs: none (command-line arguments, see the module docstring).
    Outputs: the exit code, 0 when at least one image was saved.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pull_number", type=int)
    parser.add_argument("--output", default="screenshots")
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY_STR)
    parser.add_argument("--kind", default=DEFAULT_KIND_STR)
    argument_namespace = parser.parse_args()
    comment_list = read_comment_list(argument_namespace.repository,
                                     argument_namespace.pull_number)
    image_dict = assemble_image_dict(comment_list, argument_namespace.kind)
    os.makedirs(argument_namespace.output, exist_ok=True)
    for name_str, image_bytes in sorted(image_dict.items()):
        path_str = os.path.join(argument_namespace.output, name_str + ".png")
        with open(path_str, "wb") as image_file:
            image_file.write(image_bytes)
        print(f"saved {path_str}")
    return 0 if image_dict else 1


if __name__ == "__main__":
    sys.exit(main())
