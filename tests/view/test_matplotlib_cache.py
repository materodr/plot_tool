"""Tests for the lasting matplotlib folder of the built app (issue #67).

src/view/matplotlib_cache.py has no Qt code, so these tests run without
PyQt6.
"""

import os
import tempfile
import unittest

from tests.support import covers
from view import matplotlib_cache


class MatplotlibCacheTest(unittest.TestCase):
    """Check where a built app keeps matplotlib's font cache."""

    @covers("LLFR-00068")
    def test_cache_folder_of_each_platform(self) -> None:
        """Each operating system's user cache folder is used.

        Inputs: none.
        Outputs: none.
        """
        home_str = os.path.join("home", "user")
        case_list = [
            ("darwin", {}, os.path.join(home_str, "Library", "Caches")),
            ("win32", {"LOCALAPPDATA": "local"}, "local"),
            ("win32", {}, os.path.join(home_str, "AppData", "Local")),
            ("linux", {"XDG_CACHE_HOME": "xdg"}, "xdg"),
            ("linux", {}, os.path.join(home_str, ".cache")),
        ]
        for platform_str, environment_dict, cache_str in case_list:
            with self.subTest(platform_str=platform_str,
                              environment_dict=environment_dict):
                self.assertEqual(
                    matplotlib_cache.persistent_matplotlib_folder_str(
                        platform_str, environment_dict, home_str),
                    os.path.join(cache_str, "plot_tool", "matplotlib"))

    @covers("LLFR-00068")
    def test_source_run_changes_nothing(self) -> None:
        """Run from source, MPLCONFIGDIR is left as it is.

        Inputs: none.
        Outputs: none.
        """
        environment_dict = {"MPLCONFIGDIR": "temporary"}
        folder_str = matplotlib_cache.use_persistent_matplotlib_folder(
            environment_dict, frozen_b=False)
        self.assertEqual(folder_str, "")
        self.assertEqual(environment_dict, {"MPLCONFIGDIR": "temporary"})

    @covers("LLFR-00068")
    def test_built_app_uses_a_lasting_folder(self) -> None:
        """A built app replaces the temporary MPLCONFIGDIR and creates it.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as cache_str:
            environment_dict = {"MPLCONFIGDIR": "temporary",
                                "XDG_CACHE_HOME": cache_str,
                                "LOCALAPPDATA": cache_str}
            original_expanduser = os.path.expanduser
            self.addCleanup(setattr, os.path, "expanduser",
                            original_expanduser)
            os.path.expanduser = lambda path_str: cache_str
            folder_str = matplotlib_cache.use_persistent_matplotlib_folder(
                environment_dict, frozen_b=True)
            self.assertTrue(folder_str.startswith(cache_str))
            self.assertTrue(folder_str.endswith(
                os.path.join("plot_tool", "matplotlib")))
            self.assertTrue(os.path.isdir(folder_str))
            self.assertEqual(environment_dict["MPLCONFIGDIR"], folder_str)

    @covers("LLFR-00068")
    def test_unwritable_folder_changes_nothing(self) -> None:
        """When the folder can't be created, matplotlib keeps its choice.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as cache_str:
            blocking_path_str = os.path.join(cache_str, "file")
            with open(blocking_path_str, "w", encoding="utf-8"):
                pass
            environment_dict = {"MPLCONFIGDIR": "temporary",
                                "XDG_CACHE_HOME": blocking_path_str,
                                "LOCALAPPDATA": blocking_path_str}
            original_expanduser = os.path.expanduser
            self.addCleanup(setattr, os.path, "expanduser",
                            original_expanduser)
            os.path.expanduser = lambda path_str: blocking_path_str
            folder_str = matplotlib_cache.use_persistent_matplotlib_folder(
                environment_dict, frozen_b=True)
        self.assertEqual(folder_str, "")
        self.assertEqual(environment_dict["MPLCONFIGDIR"], "temporary")


if __name__ == "__main__":
    unittest.main()
