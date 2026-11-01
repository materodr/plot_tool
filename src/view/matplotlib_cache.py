"""Keep matplotlib's font cache between launches of the standalone app.

PyInstaller's matplotlib runtime hook points ``MPLCONFIGDIR`` at a new
temporary folder on every launch of a built app, so matplotlib scans
every installed font again each time, which takes many seconds on a
Mac with many fonts (issue #67). ``use_persistent_matplotlib_folder``
points it at a folder in the user's cache folder instead, so the font
list is built once, on the first launch. It must run before matplotlib
is imported. When the app runs from source nothing changes: matplotlib
uses its own folder (``~/.matplotlib`` or ``~/.config/matplotlib``).

No Qt code is used here, so the module can be tested without PyQt6.
"""

import os
import sys

APP_FOLDER_NAME_STR = "plot_tool"
MATPLOTLIB_FOLDER_NAME_STR = "matplotlib"


def user_cache_folder_str(platform_str: str, environment_dict: dict,
                          home_folder_str: str) -> str:
    """Return the folder where the operating system keeps user caches.

    Inputs:
        platform_str: sys.platform ("darwin", "win32", "linux", ...).
        environment_dict: the environment variables (os.environ).
        home_folder_str: the user's home folder.
    Outputs: ~/Library/Caches on macOS, %LOCALAPPDATA% on Windows, and
        $XDG_CACHE_HOME or ~/.cache elsewhere.
    """
    # LLFR-00068, LLFR-00189: a folder that survives between launches.
    if platform_str == "darwin":
        return os.path.join(home_folder_str, "Library", "Caches")
    if platform_str == "win32":
        return environment_dict.get(
            "LOCALAPPDATA", os.path.join(home_folder_str, "AppData",
                                         "Local"))
    return environment_dict.get("XDG_CACHE_HOME",
                                os.path.join(home_folder_str, ".cache"))


def persistent_matplotlib_folder_str(platform_str: str,
                                     environment_dict: dict,
                                     home_folder_str: str) -> str:
    """Return the matplotlib folder used by the standalone app.

    Inputs:
        platform_str: sys.platform.
        environment_dict: the environment variables (os.environ).
        home_folder_str: the user's home folder.
    Outputs: <user cache folder>/plot_tool/matplotlib.
    """
    # LLFR-00068, LLFR-00189: matplotlib keeps its font list for the
    # plots here.
    return os.path.join(
        user_cache_folder_str(platform_str, environment_dict,
                              home_folder_str),
        APP_FOLDER_NAME_STR, MATPLOTLIB_FOLDER_NAME_STR)


def use_persistent_matplotlib_folder(environment_dict=None,
                                     frozen_b: bool = None) -> str:
    """Point matplotlib at a lasting folder when the app is a build.

    Inputs:
        environment_dict: the environment to change; os.environ when
            None.
        frozen_b: whether the app runs from a PyInstaller build; read
            from sys.frozen when None.
    Outputs: the folder now in MPLCONFIGDIR, or an empty string when
        nothing was changed (app run from source, or the folder can't
        be created, in which case matplotlib keeps its own choice).
    """
    # LLFR-00068, LLFR-00189: only a built app needs this; from source
    # matplotlib already keeps its cache.
    if environment_dict is None:
        environment_dict = os.environ
    if frozen_b is None:
        frozen_b = bool(getattr(sys, "frozen", False))
    if not frozen_b:
        return ""
    folder_str = persistent_matplotlib_folder_str(
        sys.platform, environment_dict, os.path.expanduser("~"))
    try:
        os.makedirs(folder_str, exist_ok=True)
    except OSError:
        return ""
    if not os.access(folder_str, os.W_OK):
        return ""
    environment_dict["MPLCONFIGDIR"] = folder_str
    return folder_str
