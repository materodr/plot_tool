"""Static checks of the build script and macOS build job (LLFR-00182).

The build itself runs only in the macOS build workflow
(.github/workflows/macos_build.yml), which also checks that the bundle
holds the icon file and that Info.plist names it.
"""

import importlib.util
import inspect
import os
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


if __name__ == "__main__":
    unittest.main()
