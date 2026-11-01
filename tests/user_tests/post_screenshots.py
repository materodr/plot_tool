"""Post PNG screenshots on a pull request as base64 comments.

Run from anywhere (the GitHub CLI ``gh`` must be logged in):

    python tests/user_tests/post_screenshots.py <pull number> \
        --input screenshots [--kind screenshot|before-screenshot] \
        [--commit <sha>]

Each PNG of the input folder is sent as base64 text split over comments
of less than 60,000 characters, each starting with
``<!-- <kind> <name> part <i>/<n> ... -->``. The comments of the same
kind posted earlier on the pull request are deleted first, so only the
latest set is kept. CI runs it with the kind ``screenshot`` after
make_screenshots.py (see .github/workflows/tests.yml);
fetch_screenshots.py turns the comments back into PNG files.
"""

import argparse
import base64
import glob
import json
import os
import subprocess
import sys

DEFAULT_REPOSITORY_STR = "materodr/plot_tool"
DEFAULT_KIND_STR = "screenshot"
# Base64 characters per comment; with the wrapper the comment stays
# well under GitHub's 65,536 character limit and the 60,000 of the spec.
CHUNK_LENGTH_I = 58000


def run_gh(argument_list: list, input_str: str = "") -> str:
    """Run a ``gh`` command and return its standard output.

    Inputs:
        argument_list: the arguments after ``gh``.
        input_str: text given on standard input, if any.
    Outputs: the standard output as text.
    """
    return subprocess.run(["gh"] + argument_list, check=True,
                          capture_output=True, text=True,
                          input=input_str or None).stdout


def delete_old_comments(repository_str: str, pull_number_i: int,
                        kind_str: str) -> int:
    """Delete the comments of one kind posted earlier on the pull request.

    Inputs:
        repository_str: "owner/name" of the GitHub repository.
        pull_number_i: number of the pull request.
        kind_str: the comment kind, e.g. "screenshot".
    Outputs: the number of deleted comments.
    """
    output_str = run_gh([
        "api", "--paginate",
        f"repos/{repository_str}/issues/{pull_number_i}/comments",
        "--jq", ".[] | {id: .id, body: .body}"])
    prefix_str = f"<!-- {kind_str} "
    deleted_count_i = 0
    for line_str in output_str.splitlines():
        if not line_str.strip():
            continue
        comment_dict = json.loads(line_str)
        if comment_dict["body"].startswith(prefix_str):
            run_gh(["api", "-X", "DELETE",
                    f"repos/{repository_str}/issues/comments/"
                    f"{comment_dict['id']}"])
            deleted_count_i += 1
    return deleted_count_i


def comment_body_list(name_str: str, image_bytes: bytes, kind_str: str,
                      commit_str: str) -> list:
    """Return the comment bodies that carry one PNG image.

    Inputs:
        name_str: the image name, without extension.
        image_bytes: the PNG file content.
        kind_str: the comment kind.
        commit_str: the commit the image was made from ("" if unknown).
    Outputs: a list of str, one comment body per part.
    """
    encoded_str = base64.b64encode(image_bytes).decode("ascii")
    chunk_list = [encoded_str[start_i:start_i + CHUNK_LENGTH_I]
                  for start_i in range(0, len(encoded_str),
                                       CHUNK_LENGTH_I)] or [""]
    commit_note_str = f" commit {commit_str}" if commit_str else ""
    body_list = []
    for index_i, chunk_str in enumerate(chunk_list, start=1):
        part_str = f"part {index_i}/{len(chunk_list)}"
        body_list.append(
            f"<!-- {kind_str} {name_str} {part_str}{commit_note_str} -->\n"
            f"<details><summary>{kind_str} <code>{name_str}.png</code> "
            f"{part_str}{commit_note_str} (base64; read it with "
            "tests/user_tests/fetch_screenshots.py)</summary>\n\n"
            f"```\n{chunk_str}\n```\n</details>\n")
    return body_list


def main() -> int:
    """Post every PNG of the input folder on the pull request.

    Inputs: none (command-line arguments, see the module docstring).
    Outputs: the exit code, 0 when every comment was posted.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pull_number", type=int)
    parser.add_argument("--input", default="screenshots")
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY_STR)
    parser.add_argument("--kind", default=DEFAULT_KIND_STR)
    parser.add_argument("--commit", default="")
    argument_namespace = parser.parse_args()
    path_list = sorted(glob.glob(os.path.join(argument_namespace.input,
                                              "*.png")))
    if not path_list:
        print("no PNG files to post", file=sys.stderr)
        return 1
    deleted_count_i = delete_old_comments(
        argument_namespace.repository, argument_namespace.pull_number,
        argument_namespace.kind)
    print(f"deleted {deleted_count_i} old comments")
    for path_str in path_list:
        name_str = os.path.splitext(os.path.basename(path_str))[0]
        with open(path_str, "rb") as image_file:
            image_bytes = image_file.read()
        for body_str in comment_body_list(name_str, image_bytes,
                                          argument_namespace.kind,
                                          argument_namespace.commit):
            run_gh(["api",
                    f"repos/{argument_namespace.repository}/issues/"
                    f"{argument_namespace.pull_number}/comments",
                    "-F", "body=@-"], input_str=body_str)
        print(f"posted {name_str}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
