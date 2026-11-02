"""Checks of the one-command rebuild tool (rebuild_and_launch.py).

Each test uses temporary folders and git repositories. The build and
the launch run only when the tool is used by hand.
"""

import importlib.util
import os
import re
import subprocess
import tempfile
import unittest

from tests.support import REPOSITORY_ROOT_STR

TOOL_PATH_STR = os.path.join(REPOSITORY_ROOT_STR, "rebuild_and_launch.py")


def load_tool():
    """Import rebuild_and_launch.py as a module without running it.

    Inputs: none.
    Outputs: the module object.
    """
    specification = importlib.util.spec_from_file_location(
        "rebuild_and_launch", TOOL_PATH_STR)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def run_git_checked(folder_str: str, *argument_tuple: str) -> str:
    """Run a git command that must succeed and return its output.

    Inputs:
        folder_str: the folder to run git in.
        argument_tuple: the arguments that follow ``git``.
    Outputs: the standard output, without surrounding spaces.
    """
    identity_list = ["-c", "user.name=test", "-c", "user.email=test@test"]
    result = subprocess.run(["git", *identity_list, *argument_tuple],
                            cwd=folder_str, check=True,
                            capture_output=True, text=True)
    return result.stdout.strip()


def commit_file(folder_str: str, file_name_str: str) -> None:
    """Create a file in a repository and commit it.

    Inputs:
        folder_str: the repository folder.
        file_name_str: the name of the new file.
    Outputs: none.
    """
    with open(os.path.join(folder_str, file_name_str), "w") as file:
        file.write("content\n")
    run_git_checked(folder_str, "add", file_name_str)
    run_git_checked(folder_str, "commit", "-m", file_name_str)


class UpdateBranchTest(unittest.TestCase):
    """The branch is fast-forwarded, or the tool stops if it cannot be."""

    def setUp(self) -> None:
        """Create a repository, its remote and a second clone.

        Inputs: none.
        Outputs: none.
        """
        temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_folder.cleanup)
        self.tool = load_tool()
        remote_str = os.path.join(temporary_folder.name, "remote.git")
        self.local_str = os.path.join(temporary_folder.name, "local")
        self.other_str = os.path.join(temporary_folder.name, "other")
        run_git_checked(temporary_folder.name, "init", "--bare", remote_str)
        run_git_checked(temporary_folder.name, "clone", remote_str,
                        self.local_str)
        commit_file(self.local_str, "first.txt")
        run_git_checked(self.local_str, "push", "-u", "origin", "HEAD")
        run_git_checked(temporary_folder.name, "clone", remote_str,
                        self.other_str)

    def test_fast_forwards_to_the_remote(self) -> None:
        """A new commit on the remote reaches the local branch.

        Inputs: none.
        Outputs: none.
        """
        commit_file(self.other_str, "second.txt")
        run_git_checked(self.other_str, "push")
        self.tool.update_branch(self.local_str)
        self.assertTrue(os.path.exists(
            os.path.join(self.local_str, "second.txt")))

    def test_keeps_local_commits_that_are_ahead(self) -> None:
        """A branch ahead of the remote is left as it is.

        Inputs: none.
        Outputs: none.
        """
        commit_file(self.local_str, "local.txt")
        head_before_str = run_git_checked(self.local_str, "rev-parse", "HEAD")
        self.tool.update_branch(self.local_str)
        self.assertEqual(
            run_git_checked(self.local_str, "rev-parse", "HEAD"),
            head_before_str)

    def test_stops_when_the_branch_has_diverged(self) -> None:
        """Diverged histories raise RebuildError and change nothing.

        Inputs: none.
        Outputs: none.
        """
        commit_file(self.other_str, "second.txt")
        run_git_checked(self.other_str, "push")
        commit_file(self.local_str, "local.txt")
        head_before_str = run_git_checked(self.local_str, "rev-parse", "HEAD")
        with self.assertRaises(self.tool.RebuildError):
            self.tool.update_branch(self.local_str)
        self.assertEqual(
            run_git_checked(self.local_str, "rev-parse", "HEAD"),
            head_before_str)

    def test_branch_without_a_remote_copy_is_built_as_it_is(self) -> None:
        """A branch with no upstream is left as it is, with no error.

        Inputs: none.
        Outputs: none.
        """
        run_git_checked(self.local_str, "switch", "-c", "only_local")
        head_before_str = run_git_checked(self.local_str, "rev-parse", "HEAD")
        self.tool.update_branch(self.local_str)
        self.assertEqual(
            run_git_checked(self.local_str, "rev-parse", "HEAD"),
            head_before_str)

    def test_unreachable_remote_only_warns(self) -> None:
        """A remote that cannot be reached does not stop the tool.

        Inputs: none.
        Outputs: none.
        """
        run_git_checked(self.local_str, "remote", "set-url", "origin",
                        os.path.join(self.local_str, "missing.git"))
        self.tool.update_branch(self.local_str)


class ClearBinFolderTest(unittest.TestCase):
    """Clearing bin/ removes the build outputs and keeps .gitkeep."""

    def test_keeps_only_gitkeep(self) -> None:
        """Files, folders and links go; .gitkeep and link targets stay.

        Inputs: none.
        Outputs: none.
        """
        tool = load_tool()
        with tempfile.TemporaryDirectory() as parent_str:
            bin_str = os.path.join(parent_str, "bin")
            app_str = os.path.join(bin_str, "plot_tool.app", "Contents")
            outside_str = os.path.join(parent_str, "outside")
            os.makedirs(app_str)
            os.makedirs(outside_str)
            for path_str in (os.path.join(bin_str, ".gitkeep"),
                             os.path.join(bin_str, ".DS_Store"),
                             os.path.join(app_str, "Info.plist"),
                             os.path.join(outside_str, "kept.txt")):
                open(path_str, "w").close()
            os.symlink(outside_str, os.path.join(bin_str, "link"))
            tool.clear_bin_folder(bin_str)
            self.assertEqual(os.listdir(bin_str), [".gitkeep"])
            self.assertTrue(os.path.exists(
                os.path.join(outside_str, "kept.txt")))


class RunningAppPatternTest(unittest.TestCase):
    """Only the app started from this checkout's bin/ is quit."""

    def test_matches_only_the_app_of_this_folder(self) -> None:
        """The pattern finds this bin's app and nothing else.

        Inputs: none.
        Outputs: none.
        """
        pattern_str = load_tool().running_app_pattern("/work/a.b/bin")
        for command_str in (
                "/work/a.b/bin/plot_tool.app/Contents/MacOS/plot_tool",
                "/work/a.b/bin/plot_tool/plot_tool"):
            self.assertIsNotNone(re.search(pattern_str, command_str))
        for command_str in (
                "/work/aXb/bin/plot_tool/plot_tool",
                "/other/bin/plot_tool.app/Contents/MacOS/plot_tool",
                "zsh -c open /work/a.b/bin/plot_tool.app/Contents/MacOS/"
                "plot_tool"):
            self.assertIsNone(re.search(pattern_str, command_str))


class VirtualEnvironmentTest(unittest.TestCase):
    """A worktree with no .venv uses the main checkout's."""

    def test_worktree_uses_the_main_checkout_environment(self) -> None:
        """The checkout's own .venv wins, then the main checkout's.

        Inputs: none.
        Outputs: none.
        """
        tool = load_tool()
        relative_path_list = [".venv", "bin", "python"]
        with tempfile.TemporaryDirectory() as parent_str:
            parent_str = os.path.realpath(parent_str)
            main_str = os.path.join(parent_str, "main")
            worktree_str = os.path.join(parent_str, "worktree")
            os.makedirs(main_str)
            run_git_checked(main_str, "init")
            commit_file(main_str, "first.txt")
            with self.assertRaises(tool.RebuildError):
                tool.virtual_environment_python_path(main_str)
            run_git_checked(main_str, "worktree", "add", "-b", "other",
                            worktree_str)
            for checkout_str in (main_str, worktree_str):
                python_path_str = os.path.join(checkout_str,
                                               *relative_path_list)
                os.makedirs(os.path.dirname(python_path_str))
                open(python_path_str, "w").close()
                self.assertEqual(
                    tool.virtual_environment_python_path(worktree_str),
                    python_path_str)


if __name__ == "__main__":
    unittest.main()
