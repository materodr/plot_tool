"""Self-tests for tests/ci/download_pr_matrix.sh (PCR-00019, PCR-00022)."""

import os
import stat
import subprocess
import tempfile
import unittest

from tests.support import REPOSITORY_ROOT_STR, covers

SCRIPT_PATH_STR = os.path.join(REPOSITORY_ROOT_STR, "tests", "ci",
                               "download_pr_matrix.sh")
FAILING_GH_STR = ('#!/usr/bin/env bash\n'
                  'echo \'{"message":"No commit found"}\'\n'
                  'exit 1\n')


class DownloadMatrixTest(unittest.TestCase):
    """Check the script with a stand-in for the gh command."""

    @covers("PCR-00022")
    def test_failed_gh_api_counts_as_no_pull_request(self) -> None:
        """The error text of gh api isn't read as a commit.

        Inputs: none.
        Outputs: none.
        """
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        gh_path_str = os.path.join(folder.name, "gh")
        with open(gh_path_str, "w", encoding="utf-8") as gh_file:
            gh_file.write(FAILING_GH_STR)
        os.chmod(gh_path_str, os.stat(gh_path_str).st_mode | stat.S_IXUSR)
        environment_dict = dict(os.environ)
        environment_dict["PATH"] = (folder.name + os.pathsep
                                    + environment_dict["PATH"])
        result = subprocess.run(
            ["bash", SCRIPT_PATH_STR, "owner/name", "abc",
             os.path.join(folder.name, "output")],
            capture_output=True, text=True, env=environment_dict)
        self.assertEqual(result.returncode, 0)
        self.assertIn("abc has no pull request", result.stdout)
        self.assertNotIn("message", result.stdout)


if __name__ == "__main__":
    unittest.main()
