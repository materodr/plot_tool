"""Self-tests for tests/install_local_wheels.sh and the ci-wheels branch
(PCR-00002, PCR-00130, PCR-00131).

Each test of the script builds, in temporary folders, a bare repository
with an orphan ci-wheels branch of fake wheels and a clone of it that
holds a copy of the script, so the fetch, the joining of split wheels,
the checksums and the pip retry run with no network. The workflow tests
read the files of .github/workflows.
"""

import hashlib
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest

import yaml

from tests.support import REPOSITORY_ROOT_STR, covers

SCRIPT_PATH_STR = os.path.join(REPOSITORY_ROOT_STR, "tests",
                               "install_local_wheels.sh")
WORKFLOW_FOLDER_STR = os.path.join(REPOSITORY_ROOT_STR, ".github",
                                   "workflows")
SMALL_WHEEL_STR = ("h5py-3.12.1-cp313-cp313-manylinux_2_17_x86_64."
                   "manylinux2014_x86_64.whl")
BIG_WHEEL_STR = "PyQt6_Qt6-6.9.0-py3-none-manylinux_2_28_x86_64.whl"
BIG_CONTENT_BYTES = b"0123456789abcdefghijklmnopqrstuvwxyz" * 3
PART_SIZE_I = 40
REQUIREMENTS_TEXT_STR = ("PyQt6>=6.5        # user interface\n"
                         "numpy>=1.24       # arrays\n"
                         "h5py>=3.8         # HDF5\n")
# A stand-in for python3: it logs each pip call, refuses the first one
# as an externally managed environment, and prints the versions.
FAKE_PYTHON_STR = """#!/usr/bin/env bash
if [ "$1" = "-m" ] && [ "$2" = "pip" ]; then
    echo "$*" >> "$FAKE_PIP_LOG"
    case " $* " in
        *" --break-system-packages "*) exit 0 ;;
    esac
    echo "error: externally-managed-environment"
    exit 1
fi
cat > /dev/null
echo "PyQt6 6.9.0 (Qt 6.9.0), h5py 3.12.1"
"""


def run_git(folder_str: str, *argument_tuple: str) -> str:
    """Run a git command that must succeed and return its output.

    Inputs:
        folder_str: the folder to run git in.
        argument_tuple: the arguments that follow ``git``.
    Outputs: the standard output, without surrounding spaces.
    """
    identity_list = ["-c", "user.name=test", "-c", "user.email=test@test",
                     "-c", "init.defaultBranch=develop"]
    result = subprocess.run(["git", *identity_list, *argument_tuple],
                            cwd=folder_str, check=True,
                            capture_output=True, text=True)
    return result.stdout.strip()


def sha256_line(name_str: str, content_bytes: bytes) -> str:
    """Make one line of a SHA256SUMS file, as sha256sum writes it.

    Inputs:
        name_str: the file name.
        content_bytes: the content of the file.
    Outputs: the line, with its newline.
    """
    return f"{hashlib.sha256(content_bytes).hexdigest()}  {name_str}\n"


def wheel_branch_files(big_parts_b: bool = True) -> dict:
    """Make the files of a ci-wheels branch as the workflow writes them.

    Inputs:
        big_parts_b: True to store the big wheel as parts of PART_SIZE_I
            bytes, False to store it whole.
    Outputs: a dict from each file name to its content as bytes.
    """
    small_content_bytes = b"small wheel content"
    file_dict = {
        SMALL_WHEEL_STR: small_content_bytes,
        "README.md": b"# ci-wheels\n",
        "SHA256SUMS": (sha256_line(BIG_WHEEL_STR, BIG_CONTENT_BYTES)
                       + sha256_line(SMALL_WHEEL_STR, small_content_bytes)
                       ).encode(),
    }
    if not big_parts_b:
        file_dict[BIG_WHEEL_STR] = BIG_CONTENT_BYTES
        return file_dict
    for index_i, start_i in enumerate(range(0, len(BIG_CONTENT_BYTES),
                                            PART_SIZE_I)):
        file_dict[f"{BIG_WHEEL_STR}.part-{index_i:02d}"] = (
            BIG_CONTENT_BYTES[start_i:start_i + PART_SIZE_I])
    return file_dict


class InstallScriptTest(unittest.TestCase):
    """Run tests/install_local_wheels.sh against a local ci-wheels."""

    def setUp(self) -> None:
        """Create the bare remote and its clone with the script.

        Inputs: none.
        Outputs: none.
        """
        self.temporary = tempfile.TemporaryDirectory()
        base_str = self.temporary.name
        self.remote_str = os.path.join(base_str, "remote.git")
        self.clone_str = os.path.join(base_str, "clone")
        self.output_str = os.path.join(base_str, "wheels")
        self.log_str = os.path.join(base_str, "pip.log")
        run_git(base_str, "init", "--bare", "-q", self.remote_str)
        os.makedirs(os.path.join(self.clone_str, "tests"))
        run_git(self.clone_str, "init", "-q")
        shutil.copy(SCRIPT_PATH_STR, os.path.join(self.clone_str, "tests"))
        with open(os.path.join(self.clone_str, "requirements.txt"), "w",
                  encoding="utf-8") as requirements_file:
            requirements_file.write(REQUIREMENTS_TEXT_STR)
        run_git(self.clone_str, "add", ".")
        run_git(self.clone_str, "commit", "-q", "-m", "develop")
        run_git(self.clone_str, "remote", "add", "origin", self.remote_str)
        run_git(self.clone_str, "push", "-q", "origin", "HEAD:develop")
        self.fake_python_str = os.path.join(base_str, "fake_python")
        with open(self.fake_python_str, "w", encoding="utf-8") as fake_file:
            fake_file.write(FAKE_PYTHON_STR)
        os.chmod(self.fake_python_str, stat.S_IRWXU)

    def tearDown(self) -> None:
        """Remove the temporary folders.

        Inputs: none.
        Outputs: none.
        """
        self.temporary.cleanup()

    def push_wheel_branch(self, file_dict: dict) -> None:
        """Push an orphan ci-wheels branch with the given files.

        Inputs:
            file_dict: a dict from each file name to its content as bytes.
        Outputs: none.
        """
        branch_str = os.path.join(self.temporary.name, "branch")
        shutil.rmtree(branch_str, ignore_errors=True)
        os.makedirs(branch_str)
        run_git(branch_str, "init", "-q")
        for name_str, content_bytes in file_dict.items():
            with open(os.path.join(branch_str, name_str), "wb") as out_file:
                out_file.write(content_bytes)
        run_git(branch_str, "add", ".")
        run_git(branch_str, "commit", "-q", "-m", "wheels")
        run_git(branch_str, "push", "-q", "--force", self.remote_str,
                "HEAD:refs/heads/ci-wheels")

    def run_script(self, *argument_tuple: str,
                   folder_str: str = "") -> subprocess.CompletedProcess:
        """Run the copy of the script in the clone.

        Inputs:
            argument_tuple: more arguments of the script.
            folder_str: the --folder value, by default self.output_str.
        Outputs: the completed process, with its text output.
        """
        environment_dict = dict(os.environ, PYTHON=self.fake_python_str,
                                FAKE_PIP_LOG=self.log_str)
        environment_dict.pop("PLOT_TOOL_WHEELS_FOLDER", None)
        return subprocess.run(
            ["bash", os.path.join(self.clone_str, "tests",
                                  "install_local_wheels.sh"),
             "--folder", folder_str or self.output_str, *argument_tuple],
            cwd=self.clone_str, capture_output=True, text=True,
            env=environment_dict)

    def assert_failed_with(self, result: subprocess.CompletedProcess,
                           reason_str: str) -> None:
        """Check that the script failed with a reason and the advice.

        Inputs:
            result: the completed process of run_script.
            reason_str: a text that the reason must hold.
        Outputs: none.
        """
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(reason_str, result.stderr)
        self.assertIn("carry on", result.stderr)
        self.assertIn("PCR-00131", result.stderr)

    @covers("PCR-00131")
    def test_joins_parts_and_checks_the_sums(self) -> None:
        """Split wheels are joined, and the sums pass.

        Inputs: none.
        Outputs: none.
        """
        self.push_wheel_branch(wheel_branch_files())
        result = self.run_script("--no-install")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with open(os.path.join(self.output_str, BIG_WHEEL_STR), "rb") as file:
            self.assertEqual(file.read(), BIG_CONTENT_BYTES)
        self.assertEqual(
            [name_str for name_str in os.listdir(self.output_str)
             if ".part-" in name_str], [])
        self.assertIn("Joined 3 parts", result.stdout)
        self.assertIn("All 2 wheels match SHA256SUMS", result.stdout)
        self.assertFalse(os.path.exists(self.log_str))

    @covers("PCR-00131")
    def test_whole_wheels_need_no_join(self) -> None:
        """A branch with no split wheel passes too.

        Inputs: none.
        Outputs: none.
        """
        self.push_wheel_branch(wheel_branch_files(big_parts_b=False))
        result = self.run_script("--no-install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Joined", result.stdout)

    @covers("PCR-00131")
    def test_wrong_checksum_fails(self) -> None:
        """A wheel that doesn't match SHA256SUMS fails the script.

        Inputs: none.
        Outputs: none.
        """
        file_dict = wheel_branch_files()
        file_dict[SMALL_WHEEL_STR] = b"changed content"
        self.push_wheel_branch(file_dict)
        self.assert_failed_with(self.run_script("--no-install"),
                                "doesn't match SHA256SUMS")

    @covers("PCR-00131")
    def test_wrong_part_order_fails(self) -> None:
        """Parts joined in the wrong order would fail the checksum.

        Inputs: none.
        Outputs: none.
        """
        file_dict = wheel_branch_files()
        first_bytes = file_dict[f"{BIG_WHEEL_STR}.part-00"]
        file_dict[f"{BIG_WHEEL_STR}.part-00"] = file_dict[
            f"{BIG_WHEEL_STR}.part-01"]
        file_dict[f"{BIG_WHEEL_STR}.part-01"] = first_bytes
        self.push_wheel_branch(file_dict)
        self.assert_failed_with(self.run_script("--no-install"),
                                "doesn't match SHA256SUMS")

    @covers("PCR-00131")
    def test_unlisted_wheel_fails(self) -> None:
        """A wheel that SHA256SUMS doesn't list fails the script.

        Inputs: none.
        Outputs: none.
        """
        file_dict = wheel_branch_files()
        file_dict["extra-1.0-py3-none-any.whl"] = b"extra"
        self.push_wheel_branch(file_dict)
        self.assert_failed_with(
            self.run_script("--no-install"),
            "extra-1.0-py3-none-any.whl is not listed in SHA256SUMS")

    @covers("PCR-00131")
    def test_missing_first_part_fails(self) -> None:
        """Parts without their .part-00 fail the script.

        Inputs: none.
        Outputs: none.
        """
        file_dict = wheel_branch_files()
        del file_dict[f"{BIG_WHEEL_STR}.part-00"]
        self.push_wheel_branch(file_dict)
        self.assert_failed_with(self.run_script("--no-install"),
                                "parts without a first part")

    @covers("PCR-00131")
    def test_missing_checksum_file_fails(self) -> None:
        """A branch without SHA256SUMS fails the script.

        Inputs: none.
        Outputs: none.
        """
        file_dict = wheel_branch_files()
        del file_dict["SHA256SUMS"]
        self.push_wheel_branch(file_dict)
        self.assert_failed_with(self.run_script("--no-install"),
                                "has no SHA256SUMS file")

    @covers("PCR-00131")
    def test_missing_branch_fails_with_a_clear_message(self) -> None:
        """Without ci-wheels the script says so and how to carry on.

        Inputs: none.
        Outputs: none.
        """
        self.assert_failed_with(self.run_script("--no-install"),
                                "the branch may not exist yet")

    @covers("PCR-00131")
    def test_folder_inside_the_worktree_is_refused(self) -> None:
        """The wheels never go into the worktree.

        Inputs: none.
        Outputs: none.
        """
        self.push_wheel_branch(wheel_branch_files())
        result = self.run_script(
            "--no-install", folder_str=os.path.join(self.clone_str, "w"))
        self.assert_failed_with(result, "is inside the worktree")

    @covers("PCR-00131")
    def test_foreign_folder_is_not_emptied(self) -> None:
        """A non-empty folder that the script didn't write stays as is.

        Inputs: none.
        Outputs: none.
        """
        self.push_wheel_branch(wheel_branch_files())
        os.makedirs(self.output_str)
        keep_path_str = os.path.join(self.output_str, "keep.txt")
        with open(keep_path_str, "w", encoding="utf-8") as keep_file:
            keep_file.write("keep")
        self.assert_failed_with(self.run_script("--no-install"),
                                "was not written by this script")
        self.assertTrue(os.path.exists(keep_path_str))

    @covers("PCR-00131")
    def test_second_run_replaces_its_folder(self) -> None:
        """A new run replaces what an earlier run wrote.

        Inputs: none.
        Outputs: none.
        """
        file_dict = wheel_branch_files()
        file_dict["old-1.0-py3-none-any.whl"] = b"old"
        file_dict["SHA256SUMS"] += sha256_line(
            "old-1.0-py3-none-any.whl", b"old").encode()
        self.push_wheel_branch(file_dict)
        self.assertEqual(self.run_script("--no-install").returncode, 0)
        self.push_wheel_branch(wheel_branch_files())
        result = self.run_script("--no-install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(os.path.exists(
            os.path.join(self.output_str, "old-1.0-py3-none-any.whl")))

    @covers("PCR-00131")
    def test_install_retries_for_an_externally_managed_python(self) -> None:
        """pip runs offline with the requirements, then with the flag.

        Inputs: none.
        Outputs: none.
        """
        self.push_wheel_branch(wheel_branch_files())
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with open(self.log_str, encoding="utf-8") as log_file:
            call_list = log_file.read().splitlines()
        self.assertEqual(len(call_list), 2)
        for call_str in call_list:
            self.assertIn(f"--no-index --find-links {self.output_str}",
                          call_str)
            self.assertTrue(call_str.endswith("PyQt6>=6.5 h5py>=3.8"),
                            call_str)
        self.assertNotIn("--break-system-packages", call_list[0])
        self.assertIn("--break-system-packages", call_list[1])
        self.assertIn("PyQt6 6.9.0 (Qt 6.9.0), h5py 3.12.1", result.stdout)
        self.assertIn("QT_QPA_PLATFORM=offscreen", result.stdout)


def read_workflow(name_str: str) -> dict:
    """Read a workflow file of .github/workflows.

    Inputs:
        name_str: the file name, for example ``wheels.yml``.
    Outputs: the workflow as a dict. PyYAML reads the key ``on`` as True.
    """
    with open(os.path.join(WORKFLOW_FOLDER_STR, name_str),
              encoding="utf-8") as workflow_file:
        return yaml.safe_load(workflow_file)


class WheelsWorkflowTest(unittest.TestCase):
    """Check .github/workflows/wheels.yml."""

    @covers("PCR-00130")
    def test_triggers(self) -> None:
        """By hand, and on a push to develop of requirements.txt or itself.

        Inputs: none.
        Outputs: none.
        """
        trigger_dict = read_workflow("wheels.yml")[True]
        self.assertIn("workflow_dispatch", trigger_dict)
        self.assertEqual(set(trigger_dict), {"workflow_dispatch", "push"})
        self.assertEqual(trigger_dict["push"]["branches"], ["develop"])
        self.assertEqual(set(trigger_dict["push"]["paths"]),
                         {"requirements.txt",
                          ".github/workflows/wheels.yml"})

    @covers("PCR-00130")
    def test_only_contents_write(self) -> None:
        """The workflow may write the repository contents and nothing more.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(read_workflow("wheels.yml")["permissions"],
                         {"contents": "write"})

    @covers("PCR-00130")
    def test_downloads_and_replaces_the_branch(self) -> None:
        """Binary wheels for 3.13 and 3.12, split, summed, one commit.

        Inputs: none.
        Outputs: none.
        """
        workflow_dict = read_workflow("wheels.yml")
        script_str = "\n".join(
            step_dict.get("run", "")
            for job_dict in workflow_dict["jobs"].values()
            for step_dict in job_dict["steps"])
        for text_str in ("--only-binary=:all:", "3.13 3.12",
                         "--platform manylinux_2_28_x86_64",
                         "sha256sum *.whl > SHA256SUMS",
                         "split -b 90m -d -a 2", "> README.md",
                         "git commit-tree", "git push --force origin",
                         "refs/heads/ci-wheels"):
            self.assertIn(text_str, script_str)
        # One commit with no parent: commit-tree gets no -p.
        commit_line_str = next(line_str for line_str in script_str.split(
            "\n") if "git commit-tree" in line_str)
        self.assertNotIn(" -p ", commit_line_str)

    @covers("PCR-00130")
    def test_runs_no_test(self) -> None:
        """PCR-00121: the push to develop runs no test.

        Inputs: none.
        Outputs: none.
        """
        with open(os.path.join(WORKFLOW_FOLDER_STR, "wheels.yml"),
                  encoding="utf-8") as workflow_file:
            text_str = workflow_file.read()
        self.assertNotIn("build_test_matrix", text_str)
        self.assertNotIn("unittest", text_str)
        self.assertIn("PCR-00121", text_str)


class CheckoutTest(unittest.TestCase):
    """The CI checkouts don't fetch ci-wheels (PCR-00130)."""

    @covers("PCR-00130")
    def test_no_checkout_fetches_every_branch(self) -> None:
        """No workflow uses fetch-depth 0, which fetches every branch.

        Inputs: none.
        Outputs: none.
        """
        for name_str in sorted(os.listdir(WORKFLOW_FOLDER_STR)):
            workflow_dict = read_workflow(name_str)
            for job_dict in workflow_dict["jobs"].values():
                for step_dict in job_dict["steps"]:
                    if str(step_dict.get("uses", "")).startswith(
                            "actions/checkout"):
                        depth_str = str(step_dict.get("with", {}).get(
                            "fetch-depth", 1))
                        self.assertNotEqual(depth_str, "0", name_str)

    @covers("PCR-00130")
    def test_history_fetched_with_only_the_base_branch(self) -> None:
        """Each job that compares with the base fetches only that branch.

        Inputs: none.
        Outputs: none.
        """
        for name_str, job_name_list in (
                ("tests.yml", ["changes", "test-shard", "tests"]),
                ("requirement_review.yml",
                 ["requirement-validation-section", "fail-star-section"])):
            workflow_dict = read_workflow(name_str)
            for job_name_str in job_name_list:
                run_list = [step_dict.get("run", "") for step_dict in
                            workflow_dict["jobs"][job_name_str]["steps"]]
                fetch_list = [run_str for run_str in run_list
                              if "--unshallow" in run_str]
                self.assertEqual(len(fetch_list), 1, job_name_str)
                self.assertRegex(
                    fetch_list[0],
                    re.escape('"+refs/heads/$BASE_BRANCH:refs/remotes/'
                              'origin/$BASE_BRANCH"'))
                self.assertNotIn("refs/heads/*", fetch_list[0])

    @covers("PCR-00130")
    def test_unshallow_fetch_leaves_other_branches_out(self) -> None:
        """The fetch step gives the history and the base, not ci-wheels.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as base_str:
            source_str = os.path.join(base_str, "source")
            os.makedirs(source_str)
            run_git(source_str, "init", "-q")
            for index_i in range(4):
                with open(os.path.join(source_str, "f"), "w") as out_file:
                    out_file.write(str(index_i))
                run_git(source_str, "add", "f")
                run_git(source_str, "commit", "-q", "-m", f"c{index_i}")
            run_git(source_str, "checkout", "-q", "--orphan", "ci-wheels")
            run_git(source_str, "commit", "-q", "-m", "wheels")
            wheels_commit_str = run_git(source_str, "rev-parse", "HEAD")
            run_git(source_str, "checkout", "-q", "develop")
            checkout_str = os.path.join(base_str, "checkout")
            os.makedirs(checkout_str)
            run_git(checkout_str, "init", "-q")
            run_git(checkout_str, "remote", "add", "origin",
                    "file://" + source_str)
            # What actions/checkout does with its default depth of 1.
            run_git(checkout_str, "fetch", "-q", "--no-tags", "--depth=1",
                    "origin", "+refs/heads/develop:refs/remotes/pull/merge")
            run_git(checkout_str, "checkout", "-q", "refs/remotes/pull/merge")
            run_git(checkout_str, "fetch", "-q", "--no-tags", "--unshallow",
                    "origin",
                    "+refs/heads/develop:refs/remotes/origin/develop")
            self.assertEqual(run_git(checkout_str, "rev-list", "--count",
                                     "HEAD"), "4")
            self.assertFalse(os.path.exists(
                os.path.join(checkout_str, ".git", "shallow")))
            self.assertNotIn("ci-wheels", run_git(checkout_str, "branch",
                                                  "-a"))
            missing = subprocess.run(
                ["git", "cat-file", "-e", wheels_commit_str],
                cwd=checkout_str, capture_output=True)
            self.assertNotEqual(missing.returncode, 0)


class BranchRequirementTest(unittest.TestCase):
    """PCR-00002 lists ci-wheels, and the script is where PCR-00131 says."""

    @covers("PCR-00002", "PCR-00130", "PCR-00131")
    def test_requirements_name_the_branch_and_the_script(self) -> None:
        """The PCR file and CLAUDE.md name ci-wheels and the script.

        Inputs: none.
        Outputs: none.
        """
        with open(os.path.join(REPOSITORY_ROOT_STR, "docs", "requirements",
                               "process_of_collaboration.md"),
                  encoding="utf-8") as requirement_file:
            text_str = requirement_file.read()
        self.assertIn("6. a permanent `ci-wheels` branch, an orphan branch "
                      "that holds Python wheels (PCR-00130).", text_str)
        self.assertIn("`tests/install_local_wheels.sh` installs them.",
                      text_str)
        self.assertTrue(os.access(SCRIPT_PATH_STR, os.X_OK))
        with open(os.path.join(REPOSITORY_ROOT_STR, "CLAUDE.md"),
                  encoding="utf-8") as claude_file:
            self.assertIn("bash tests/install_local_wheels.sh",
                          claude_file.read())


if __name__ == "__main__":
    unittest.main()
