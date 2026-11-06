"""Checks of the build script and macOS build job (LLFR-00182, COR-00020).

The build itself runs only in the macOS build workflow
(.github/workflows/macos_build.yml), which also checks that the bundle
holds the icon file and that Info.plist names it.
"""

import importlib.util
import inspect
import os
import subprocess
import tempfile
import unittest

from tests.support import REPOSITORY_ROOT_STR, covers

BUILD_SCRIPT_PATH_STR = os.path.join(REPOSITORY_ROOT_STR,
                                     "build_executable.py")
MACOS_WORKFLOW_PATH_STR = os.path.join(
    REPOSITORY_ROOT_STR, ".github", "workflows", "macos_build.yml")


def load_build_script():
    """Import build_executable.py as a module without running it.

    Inputs: none.
    Outputs: the module object.
    """
    specification = importlib.util.spec_from_file_location(
        "build_executable", BUILD_SCRIPT_PATH_STR)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class BuildScriptIconTest(unittest.TestCase):
    """The executable gets the app icon instead of PyInstaller's."""

    @covers("LLFR-00182")
    def test_icon_is_passed_to_pyinstaller(self) -> None:
        """--icon carries the icon path, before the entry script.

        Inputs: none.
        Outputs: none.
        """
        build_module = load_build_script()
        icon_path_str = os.path.join(build_module.ICON_FOLDER_STR,
                                     "plot_tool.icns")
        argument_list = build_module.pyinstaller_argument_list(icon_path_str)
        icon_index_i = argument_list.index("--icon")
        self.assertEqual(argument_list[icon_index_i + 1], icon_path_str)
        self.assertTrue(os.path.isabs(icon_path_str))
        self.assertEqual(argument_list[-1], build_module.ENTRY_SCRIPT_STR)
        self.assertNotIn("--icon", build_module.pyinstaller_argument_list())

    @covers("LLFR-00182")
    def test_main_writes_the_icon_before_the_build(self) -> None:
        """main() writes the icon files and passes the platform's one.

        Inputs: none.
        Outputs: none.
        """
        build_module = load_build_script()
        main_source_str = inspect.getsource(build_module.main)
        self.assertIn("write_icon_file()", main_source_str)
        self.assertIn("pyinstaller_argument_list(icon_path_str)",
                      main_source_str)
        icon_source_str = inspect.getsource(build_module.write_icon_file)
        self.assertIn("write_app_icon_files", icon_source_str)
        self.assertIn("platform_icon_path", icon_source_str)
        # The icon is written to the build folder, never committed.
        self.assertTrue(build_module.ICON_FOLDER_STR.startswith(
            build_module.WORK_FOLDER_STR))

    @covers("LLFR-00182")
    def test_macos_job_checks_the_bundle_icon(self) -> None:
        """The macOS build job checks the .icns and its Info.plist name.

        Inputs: none.
        Outputs: none.
        """
        with open(MACOS_WORKFLOW_PATH_STR, encoding="utf-8") as file:
            workflow_str = file.read()
        for expected_str in ("Contents/Resources/plot_tool.icns",
                             "CFBundleIconFile", "iconutil",
                             "src/view/icons.py",
                             "src/view/icon_shapes.py",
                             "src/view/app_icon_files.py"):
            self.assertIn(expected_str, workflow_str)


class SampleCopyTest(unittest.TestCase):
    """The build copies the sample files next to the app (COR-00020)."""

    def make_repository(self, root_str: str) -> None:
        """Write a small tests/user_tests tree under root_str.

        Inputs:
            root_str: the folder that plays the repository folder.
        Outputs: none.
        """
        for relative_path_str, content_str in (
                ("good/signals.csv", "Time,a\n0,1\n"),
                ("good/signals.h5", "h5"),
                ("good/nested/inner.mat", "mat"),
                ("bad/corrupt.xlsx", "xlsx")):
            path_str = os.path.join(root_str, "tests", "user_tests",
                                    *relative_path_str.split("/"))
            os.makedirs(os.path.dirname(path_str), exist_ok=True)
            with open(path_str, "w", encoding="utf-8") as file:
                file.write(content_str)

    def relative_file_set(self, folder_str: str) -> set:
        """Return the paths of every file under a folder.

        Inputs:
            folder_str: the folder to list.
        Outputs: the paths relative to folder_str, with "/".
        """
        path_set = set()
        for parent_str, _, file_name_list in os.walk(folder_str):
            for file_name_str in file_name_list:
                path_set.add(os.path.relpath(
                    os.path.join(parent_str, file_name_str),
                    folder_str).replace(os.sep, "/"))
        return path_set

    @covers("COR-00020", "COR-00007")
    def test_copies_good_and_bad(self) -> None:
        """Both folders are copied to bin/user_tests, file for file.

        Inputs: none.
        Outputs: none.
        """
        build_module = load_build_script()
        with tempfile.TemporaryDirectory() as root_str:
            self.make_repository(root_str)
            bin_str = os.path.join(root_str, "bin")
            written_list = build_module.copy_sample_folders(root_str,
                                                            bin_str)
            self.assertEqual(written_list, [
                os.path.join(bin_str, "user_tests", "good"),
                os.path.join(bin_str, "user_tests", "bad")])
            for folder_name_str in ("good", "bad"):
                source_str = os.path.join(root_str, "tests", "user_tests",
                                          folder_name_str)
                target_str = os.path.join(bin_str, "user_tests",
                                          folder_name_str)
                self.assertEqual(self.relative_file_set(target_str),
                                 self.relative_file_set(source_str))
            with open(os.path.join(bin_str, "user_tests", "good",
                                   "signals.csv"),
                      encoding="utf-8") as file:
                self.assertEqual(file.read(), "Time,a\n0,1\n")
            # The originals stay in tests/user_tests.
            self.assertTrue(os.path.isfile(os.path.join(
                root_str, "tests", "user_tests", "bad", "corrupt.xlsx")))

    @covers("COR-00020")
    def test_replaces_an_earlier_copy(self) -> None:
        """A second build leaves no file of the earlier copy behind.

        Inputs: none.
        Outputs: none.
        """
        build_module = load_build_script()
        with tempfile.TemporaryDirectory() as root_str:
            self.make_repository(root_str)
            bin_str = os.path.join(root_str, "bin")
            build_module.copy_sample_folders(root_str, bin_str)
            stale_path_str = os.path.join(bin_str, "user_tests", "good",
                                          "removed_sample.csv")
            with open(stale_path_str, "w", encoding="utf-8") as file:
                file.write("old")
            changed_path_str = os.path.join(bin_str, "user_tests", "bad",
                                            "corrupt.xlsx")
            with open(changed_path_str, "w", encoding="utf-8") as file:
                file.write("edited copy")
            # The app next to the copy is not touched.
            app_path_str = os.path.join(bin_str, "plot_tool.app")
            os.makedirs(app_path_str)
            build_module.copy_sample_folders(root_str, bin_str)
            self.assertFalse(os.path.exists(stale_path_str))
            with open(changed_path_str, encoding="utf-8") as file:
                self.assertEqual(file.read(), "xlsx")
            self.assertTrue(os.path.isdir(app_path_str))

    @covers("COR-00020", "COR-00023")
    def test_real_samples_cover_every_format(self) -> None:
        """The real good samples hold every format of HLFR-00005.

        Inputs: none.
        Outputs: none.
        """
        build_module = load_build_script()
        with tempfile.TemporaryDirectory() as bin_str:
            build_module.copy_sample_folders(REPOSITORY_ROOT_STR, bin_str)
            good_set = self.relative_file_set(
                os.path.join(bin_str, "user_tests", "good"))
            for extension_str in (".csv", ".xlsx", ".mat", ".h5"):
                with self.subTest(extension_str=extension_str):
                    self.assertTrue(any(name_str.endswith(extension_str)
                                        for name_str in good_set))
            self.assertTrue(self.relative_file_set(
                os.path.join(bin_str, "user_tests", "bad")))

    @covers("COR-00020")
    def test_main_copies_after_the_build(self) -> None:
        """main() copies the samples after PyInstaller has run.

        Inputs: none.
        Outputs: none.
        """
        build_module = load_build_script()
        main_source_str = inspect.getsource(build_module.main)
        self.assertIn("copy_sample_folders()", main_source_str)
        self.assertLess(main_source_str.index("PyInstaller.__main__.run"),
                        main_source_str.index("copy_sample_folders()"))
        self.assertEqual(
            os.path.dirname(build_module.BIN_FOLDER_STR),
            build_module.REPOSITORY_ROOT_STR)

    @covers("COR-00007", "COR-00020", "COR-00021")
    def test_copy_is_never_committed(self) -> None:
        """bin/user_tests is ignored by git.

        Inputs: none.
        Outputs: none.
        """
        for path_str in ("bin/user_tests/good/signals.csv",
                         "bin/user_tests/bad/corrupt.h5"):
            with self.subTest(path_str=path_str):
                result = subprocess.run(
                    ["git", "check-ignore", "--no-index", "-q", path_str],
                    cwd=REPOSITORY_ROOT_STR, check=False)
                self.assertEqual(result.returncode, 0)

    @covers("COR-00020", "COR-00023")
    def test_macos_job_checks_the_copy(self) -> None:
        """The macOS build job checks the copy and one sample per format.

        Inputs: none.
        Outputs: none.
        """
        with open(MACOS_WORKFLOW_PATH_STR, encoding="utf-8") as file:
            workflow_str = file.read()
        for expected_str in ("Check the sample files next to the app",
                             "bin/user_tests/$folder",
                             'diff -r "tests/user_tests/$folder"',
                             "for extension in csv xlsx mat h5",
                             "build_executable.py"):
            self.assertIn(expected_str, workflow_str)
        self.assertLess(workflow_str.index("name: Build the app"),
                        workflow_str.index(
                            "Check the sample files next to the app"))


class BigSampleBuildTest(unittest.TestCase):
    """The build writes the big sample files (COR-00025)."""

    @covers("COR-00025")
    def test_main_writes_big_files_unless_left_out(self) -> None:
        """main() runs the generator with --big after the copy, unless
        --no-big-files is given, which the macOS CI job passes.

        Inputs: none.
        Outputs: none.
        """
        build_module = load_build_script()
        main_source_str = inspect.getsource(build_module.main)
        self.assertLess(main_source_str.index("copy_sample_folders()"),
                        main_source_str.index("write_big_sample_files()"))
        self.assertIn("NO_BIG_FILES_FLAG_STR", main_source_str)
        writer_source_str = inspect.getsource(
            build_module.write_big_sample_files)
        self.assertIn("BIG_FILES_FLAG_STR", writer_source_str)
        self.assertEqual(build_module.BIG_FILES_FLAG_STR, "--big")
        # COR-00025: --no-big-files keeps the files of an earlier build:
        # neither main() nor the copy of COR-00020 removes them.
        self.assertNotIn("BIG_FOLDER_STR", main_source_str)
        self.assertNotIn("big", build_module.SAMPLE_FOLDER_NAME_TUPLE)
        # COR-00025, COR-00007: the files go next to the app.
        self.assertIn("BIG_FOLDER_STR", writer_source_str)
        self.assertEqual(
            os.path.normpath(build_module.BIG_FOLDER_STR),
            os.path.join(build_module.BIN_FOLDER_STR, "user_tests", "big"))
        self.assertTrue(os.path.isfile(build_module.SAMPLE_SCRIPT_PATH_STR))
        with open(MACOS_WORKFLOW_PATH_STR, encoding="utf-8") as file:
            workflow_str = file.read()
        self.assertIn("python build_executable.py --no-big-files",
                      workflow_str)


if __name__ == "__main__":
    unittest.main()
