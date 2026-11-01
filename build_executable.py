"""Build the standalone plot_tool app into bin/ (COR-00007).

Usage:
    pip install -r requirements.txt -r requirements-build.txt
    python build_executable.py

The app is built with PyInstaller as one folder (``--onedir``), not as
one file (issue #67). A one-file executable unpacks the whole app into
a temporary folder on every launch and then starts it again as a
second process, which takes tens of seconds and, on macOS, makes the
Dock icon disappear and reappear. A one-folder build starts directly.

Output (never committed, see .gitignore):
- macOS: ``bin/plot_tool.app``, an app bundle to open from Finder. It is
  signed ad hoc, so a locally built app opens without extra Gatekeeper
  checks; an app downloaded from elsewhere still needs to be approved
  once (right-click, Open).
- Windows: ``bin\\plot_tool\\plot_tool.exe`` (keep the whole folder).
- Linux: ``bin/plot_tool/plot_tool`` (keep the whole folder).

Modules the app never uses are left out to make the build smaller and
quicker to start. The file loaders (pandas, openpyxl, scipy.io, h5py)
and matplotlib's QtAgg backend are kept.
"""

import os
import shutil
import subprocess
import sys

REPOSITORY_ROOT_STR = os.path.dirname(os.path.abspath(__file__))
APP_NAME_STR = "plot_tool"
BUNDLE_IDENTIFIER_STR = "io.github.materodr.plot_tool"
BIN_FOLDER_STR = os.path.join(REPOSITORY_ROOT_STR, "bin")
WORK_FOLDER_STR = os.path.join(REPOSITORY_ROOT_STR, "build")
SOURCE_FOLDER_STR = os.path.join(REPOSITORY_ROOT_STR, "src")
ENTRY_SCRIPT_STR = os.path.join(SOURCE_FOLDER_STR, "main.py")

# Modules that PyInstaller would find through optional imports of the
# libraries but that the app never uses: other GUI toolkits and their
# matplotlib backends, interactive shells, notebooks and test runners.
EXCLUDED_MODULE_LIST = [
    "tkinter", "_tkinter", "PyQt5", "PySide2", "PySide6", "wx", "gi",
    "IPython", "ipykernel", "jupyter_client", "notebook", "nbformat",
    "pytest", "_pytest", "sphinx", "docutils",
    "matplotlib.backends.backend_tkagg",
    "matplotlib.backends.backend_tkcairo",
    "matplotlib.backends._backend_tk",
    "matplotlib.backends.backend_gtk3", "matplotlib.backends.backend_gtk3agg",
    "matplotlib.backends.backend_gtk3cairo",
    "matplotlib.backends.backend_gtk4", "matplotlib.backends.backend_gtk4agg",
    "matplotlib.backends.backend_gtk4cairo",
    "matplotlib.backends.backend_wx", "matplotlib.backends.backend_wxagg",
    "matplotlib.backends.backend_wxcairo",
    "matplotlib.backends.backend_macosx",
    "matplotlib.backends.backend_webagg",
    "matplotlib.backends.backend_webagg_core",
    "matplotlib.backends.backend_nbagg",
    "matplotlib.backends.backend_qt5", "matplotlib.backends.backend_qt5agg",
    "matplotlib.backends.backend_qt5cairo",
    "pandas.tests", "scipy.io.tests", "h5py.tests", "matplotlib.tests",
]


def pyinstaller_argument_list() -> list:
    """Return the PyInstaller command-line arguments of the build.

    Inputs: none.
    Outputs: a list of argument strings for PyInstaller.
    """
    argument_list = [
        "--name", APP_NAME_STR,
        "--onedir", "--windowed", "--noconfirm", "--clean",
        "--distpath", BIN_FOLDER_STR,
        "--workpath", WORK_FOLDER_STR,
        "--specpath", WORK_FOLDER_STR,
        "--paths", SOURCE_FOLDER_STR,
        "--osx-bundle-identifier", BUNDLE_IDENTIFIER_STR,
    ]
    for module_str in EXCLUDED_MODULE_LIST:
        argument_list += ["--exclude-module", module_str]
    return argument_list + [ENTRY_SCRIPT_STR]


def sign_macos_bundle(bundle_path_str: str) -> None:
    """Sign the macOS app bundle ad hoc and verify the signature.

    Inputs:
        bundle_path_str: path of bin/plot_tool.app.
    Outputs: none. Raises CalledProcessError when codesign fails.
    """
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-",
                    bundle_path_str], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict",
                    bundle_path_str], check=True)


def main() -> int:
    """Build the app and print where it is.

    Inputs: none.
    Outputs: the exit code, 0 on success.
    """
    import PyInstaller.__main__
    PyInstaller.__main__.run(pyinstaller_argument_list())
    folder_path_str = os.path.join(BIN_FOLDER_STR, APP_NAME_STR)
    if sys.platform == "darwin":
        bundle_path_str = os.path.join(BIN_FOLDER_STR, APP_NAME_STR + ".app")
        # The bundle holds its own copy of every file, so the plain
        # folder that PyInstaller also leaves in bin/ is removed to
        # avoid two copies of the app.
        shutil.rmtree(folder_path_str, ignore_errors=True)
        sign_macos_bundle(bundle_path_str)
        print(f"Built {bundle_path_str}")
    else:
        executable_str = APP_NAME_STR + (
            ".exe" if sys.platform == "win32" else "")
        print(f"Built {os.path.join(folder_path_str, executable_str)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
