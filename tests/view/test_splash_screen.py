"""Tests for the splash screen and the opening time (issue #75).

HLFR-00046 (splash screen) and HLFR-00047 (opening time):
- LLFR-00184: src/main.py shows the splash screen before it imports
  matplotlib, numpy, pandas or the plot views (checked on the import
  graph of the source, and by running src/main.py with the startup
  probe, which reports the modules already imported when the splash
  was shown); the macOS build job checks the 2 s limit on the built app
  with tests/user_tests/measure_startup.py, whose checks are tested
  here;
- LLFR-00185: the splash shows the app icon, "plot_tool" and
  "Loading...";
- LLFR-00186: the splash closes when the main window is shown, and not
  on a click;
- LLFR-00187: on a startup error the splash is closed before the error
  box is shown, and the app exits with an error code;
- LLFR-00188 and LLFR-00189: a warm launch from source shows the window
  within 5 s and does not write matplotlib's font list again; the
  checks of measure_startup.py used on the built app are tested too.
"""

import ast
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

from tests.support import (
    REPOSITORY_ROOT_STR, SOURCE_FOLDER_STR, covers, get_qt_application,
    requires_qt)
from tests.user_tests import measure_startup
from view import matplotlib_cache

MAIN_PATH_STR = os.path.join(SOURCE_FOLDER_STR, "main.py")
# LLFR-00184: libraries and app modules that are slow to import.
HEAVY_MODULE_SET = {"matplotlib", "numpy", "pandas", "scipy", "openpyxl",
                    "h5py", "view.main_window", "view.plot_widget",
                    "view.plot_panel", "controller.main_controller",
                    "model.file_loader"}
# LLFR-00188: the longest time to the window of a warm launch.
WARM_LIMIT_S = 5.0
LAUNCH_TIMEOUT_S = 120.0


def module_path_str(module_name_str: str) -> str:
    """Return the source file of a module of src, if there is one.

    Inputs:
        module_name_str: a dotted module name such as "view.icons".
    Outputs: the path of the .py file (or the package __init__.py); an
        empty string when the module is not part of src.
    """
    base_str = os.path.join(SOURCE_FOLDER_STR, *module_name_str.split("."))
    for path_str in (base_str + ".py", os.path.join(base_str,
                                                    "__init__.py")):
        if os.path.isfile(path_str):
            return path_str
    return ""


def import_time_statement_list(body_list: list) -> list:
    """Return the import statements run when a module is imported.

    Inputs:
        body_list: the statements of a module (ast nodes).
    Outputs: the Import and ImportFrom nodes outside functions, also
        inside if, try, with and class blocks.
    """
    statement_list = []
    for node in body_list:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            statement_list.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        else:
            for field_str in ("body", "orelse", "finalbody", "handlers"):
                child_list = getattr(node, field_str, None)
                if isinstance(child_list, list):
                    statement_list += import_time_statement_list(
                        [child for child in child_list
                         if isinstance(child, ast.AST)])
    return statement_list


def imported_name_list(statement) -> list:
    """Return the modules an import statement may import.

    Inputs:
        statement: an ast.Import or ast.ImportFrom node.
    Outputs: dotted module names; for ``from package import name`` both
        the package and package.name (name may be a module).
    """
    if isinstance(statement, ast.Import):
        return [alias.name for alias in statement.names]
    name_list = [statement.module]
    name_list += [f"{statement.module}.{alias.name}"
                  for alias in statement.names]
    return name_list


def import_time_module_set(module_name_str: str) -> set:
    """Return every module imported when a module of src is imported.

    Inputs:
        module_name_str: the dotted name of a module of src ("main").
    Outputs: the set of module names imported at import time, following
        the modules of src, with their parent packages; outside
        libraries are listed by their dotted name but not followed.
    """
    seen_set = set()
    pending_list = [module_name_str]
    while pending_list:
        name_str = pending_list.pop()
        if name_str in seen_set:
            continue
        path_str = module_path_str(name_str)
        part_list = name_str.split(".")
        if not path_str:
            if module_path_str(part_list[0]):
                # A function or class imported from a module of src.
                continue
            # An outside library: listed, not followed.
            seen_set.add(name_str)
            seen_set.add(part_list[0])
            continue
        seen_set.add(name_str)
        for index_i in range(1, len(part_list)):
            pending_list.append(".".join(part_list[:index_i]))
        with open(path_str, encoding="utf-8") as source_file:
            tree = ast.parse(source_file.read())
        for statement in import_time_statement_list(tree.body):
            pending_list += imported_name_list(statement)
    return seen_set


def run_main(environment_update_dict: dict, code_str: str = None) -> tuple:
    """Run src/main.py, or a small driver script, in a new process.

    Inputs:
        environment_update_dict: environment variables to set.
        code_str: Python code to run with ``-c`` instead of main.py.
    Outputs: a tuple (exit code, standard output, standard error).
    """
    environment_dict = dict(os.environ)
    environment_dict.setdefault("QT_QPA_PLATFORM", "offscreen")
    environment_dict.update(environment_update_dict)
    command_list = ([sys.executable, MAIN_PATH_STR] if code_str is None
                    else [sys.executable, "-c", code_str])
    process = subprocess.Popen(
        command_list, env=environment_dict, cwd=REPOSITORY_ROOT_STR,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        output_str, error_str = process.communicate(
            timeout=LAUNCH_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        process.kill()
        output_str, error_str = process.communicate()
        error_str += "\n(killed: the app did not quit)"
    return process.returncode, output_str, error_str


class StartupImportOrderTest(unittest.TestCase):
    """Check, on the source, what src/main.py imports before main()."""

    @covers("LLFR-00184")
    def test_main_module_imports_nothing_heavy(self) -> None:
        """Importing src/main.py imports no slow module.

        Inputs: none.
        Outputs: none.
        """
        module_set = import_time_module_set("main")
        # The splash screen and the app icon are imported at the top.
        for name_str in ("view.splash_screen", "view.icons", "view.theme",
                         "view.startup_probe", "view.message_boxes"):
            self.assertIn(name_str, module_set)
        self.assertEqual(module_set & HEAVY_MODULE_SET, set())

    @covers("LLFR-00184")
    def test_import_graph_finds_heavy_imports(self) -> None:
        """The import graph check does see the slow imports of the app.

        Inputs: none.
        Outputs: none.
        """
        # Guard against a check that can never fail: the main window
        # does import matplotlib and the loaders do import numpy.
        self.assertIn("matplotlib",
                      import_time_module_set("view.main_window"))
        self.assertIn("numpy", import_time_module_set("model.file_loader"))

    @covers("LLFR-00184")
    def test_heavy_imports_are_inside_build_main_window(self) -> None:
        """The main window and controller are imported by main.py later.

        Inputs: none.
        Outputs: none.
        """
        with open(MAIN_PATH_STR, encoding="utf-8") as source_file:
            tree = ast.parse(source_file.read())
        function_dict = {node.name: node for node in tree.body
                         if isinstance(node, ast.FunctionDef)}
        build_name_set = set()
        for statement in ast.walk(function_dict["build_main_window"]):
            if isinstance(statement, (ast.Import, ast.ImportFrom)):
                build_name_set.update(imported_name_list(statement))
        self.assertIn("view.main_window", build_name_set)
        self.assertIn("controller.main_controller", build_name_set)


class MeasureStartupChecksTest(unittest.TestCase):
    """Check the checks of measure_startup.py used on the built app."""

    def good_result_dict(self) -> dict:
        """Return the result of a launch that passes every check.

        Inputs: none.
        Outputs: a dict shaped like measure_startup.launch_once's.
        """
        return {"launch_to_window_s": 1.2, "launch_to_splash_s": 0.4,
                "same_process_b": True, "exposed_b": True,
                "splash_exposed_b": True, "splash_visible_b": False,
                "heavy_module_list": [], "exit_code_i": 0,
                "output_str": ""}

    @covers("LLFR-00184", "LLFR-00186")
    def test_parse_splash_and_window_lines(self) -> None:
        """The splash line and the window line are found and read.

        Inputs: none.
        Outputs: none.
        """
        output_str = (
            "Qt warning\nplot_tool splash: "
            "splash_shown_epoch_s=1700000000.125 since_main_s=0.300 "
            "exposed=yes heavy_modules=none pid=4321\n"
            "plot_tool startup: window_shown_epoch_s=1700000001.500 "
            "since_main_s=1.700 exposed=yes splash_visible=no pid=4321\n")
        splash_dict = measure_startup.parse_splash_line(output_str)
        self.assertAlmostEqual(splash_dict["splash_shown_epoch_s"],
                               1700000000.125)
        self.assertAlmostEqual(splash_dict["since_main_s"], 0.3)
        self.assertTrue(splash_dict["exposed_b"])
        self.assertEqual(splash_dict["heavy_module_list"], [])
        self.assertEqual(splash_dict["process_id_i"], 4321)
        startup_dict = measure_startup.parse_startup_line(output_str)
        self.assertAlmostEqual(startup_dict["window_shown_epoch_s"],
                               1700000001.5)
        self.assertFalse(startup_dict["splash_visible_b"])
        heavy_dict = measure_startup.parse_splash_line(
            "plot_tool splash: splash_shown_epoch_s=1.0 since_main_s=1.0 "
            "exposed=no heavy_modules=matplotlib,numpy pid=1")
        self.assertEqual(heavy_dict["heavy_module_list"],
                         ["matplotlib", "numpy"])
        self.assertFalse(heavy_dict["exposed_b"])
        self.assertEqual(measure_startup.parse_splash_line("nothing"), {})
        self.assertEqual(measure_startup.parse_splash_line(
            "plot_tool splash: since_main_s=1.0"), {})

    @covers("LLFR-00184", "LLFR-00186", "LLFR-00188")
    def test_limit_checks(self) -> None:
        """Each limit fails the run only when it is broken.

        Inputs: none.
        Outputs: none.
        """
        check = measure_startup.limit_failure_list
        good_dict = self.good_result_dict()
        self.assertEqual(check(good_dict, True, 5.0, 2.0), [])
        # LLFR-00188: the 5 s limit holds for warm launches only.
        slow_dict = dict(good_dict, launch_to_window_s=12.0)
        self.assertEqual(len(check(slow_dict, True, 5.0, 2.0)), 1)
        self.assertEqual(check(slow_dict, False, 5.0, 2.0), [])
        self.assertEqual(check(dict(good_dict, launch_to_window_s=5.0),
                               True, 5.0, 2.0), [])
        # LLFR-00184: the splash time of one launch is not judged here,
        # but by the median of the warm launches (test_median_checks).
        late_dict = dict(good_dict, launch_to_splash_s=2.5)
        for warm_b in (False, True):
            with self.subTest(warm_b=warm_b):
                self.assertEqual(check(late_dict, warm_b, 5.0, 2.0), [])
        case_list = [("launch_to_splash_s", None),
                     ("splash_exposed_b", False),
                     ("heavy_module_list", ["matplotlib"]),
                     ("splash_visible_b", True)]
        for key_str, value in case_list:
            with self.subTest(key_str=key_str):
                bad_dict = dict(good_dict)
                bad_dict[key_str] = value
                self.assertEqual(len(check(bad_dict, False, 5.0, 2.0)), 1)
        # No limit given, no check.
        self.assertEqual(check(dict(late_dict, launch_to_window_s=50.0),
                               True), [])

    def dialog_output_str(self, shown_s_list: list,
                          prepare_str: str = "") -> str:
        """Build the probe output of a launch that measured its dialogs.

        Inputs:
            shown_s_list: the 10 shown times, in the probe's order.
            prepare_str: the fields of the prepare line; a good line
                when empty.
        Outputs: the output text.
        """
        prepare_str = prepare_str or (
            "prepared=yes waited_s=0.400 steps=6 prepare_s=0.300 "
            "longest_step_s=0.120 longest_turn_s=0.130 panels=warmed "
            "dialog_seen=no")
        line_list = ["plot_tool prepare: " + prepare_str]
        name_list = ["open_file", "save_layout", "load_layout", "save_pdf",
                     "save_signals"]
        for index_i, shown_s in enumerate(shown_s_list):
            line_list.append(
                f"plot_tool dialog: name={name_list[index_i // 2]} "
                f"click={index_i % 2 + 1} shown_s={shown_s:.3f} "
                "visible=yes prepared=yes prepare_s=0.300")
        return "\n".join(line_list) + "\n"

    @covers("LLFR-00406", "HLFR-00091", "LLFR-00188")
    def test_dialog_checks(self) -> None:
        """The dialog checks of the macOS job fail only when broken.

        Inputs: none.
        Outputs: none.
        """
        check = measure_startup.dialog_failure_list
        good_str = self.dialog_output_str([0.3] * 10)
        prepare_dict = measure_startup.parse_prepare_line(good_str)
        self.assertEqual(prepare_dict["step_count_i"], 6)
        self.assertEqual(prepare_dict["panel_state_str"], "warmed")
        self.assertAlmostEqual(prepare_dict["longest_turn_s"], 0.13)
        self.assertFalse(prepare_dict["dialog_seen_b"])
        dialog_list = measure_startup.parse_dialog_line_list(good_str)
        self.assertEqual(len(dialog_list), 10)
        self.assertEqual(dialog_list[3], {"name_str": "save_layout",
                                          "click_i": 2, "shown_s": 0.3,
                                          "visible_b": True})
        self.assertEqual(check(good_str, True, 0.5), [])
        self.assertIn("0.300 s on the first request",
                      measure_startup.dialog_summary_str(good_str))
        # LLFR-00406: the time of one request does not fail the launch;
        # the medians of all warm launches are judged (test_median_checks).
        slow_str = self.dialog_output_str([0.9] + [0.3] * 9)
        self.assertEqual(check(slow_str, True), [])
        # Missing lines, a dialog not shown, a dialog shown by itself
        # (issue #165) and an unprepared pool fail every launch.
        bad_str_list = [
            self.dialog_output_str([0.3] * 9),
            good_str.replace("click=2 shown_s=0.300 visible=yes",
                             "click=2 shown_s=0.300 visible=no", 1),
            good_str.replace("dialog_seen=no", "dialog_seen=yes"),
            good_str.replace("prepared=yes waited_s", "prepared=no "
                             "waited_s"),
            good_str.split("\n", 1)[1]]
        for index_i, bad_str in enumerate(bad_str_list):
            for warm_b in (False, True):
                with self.subTest(index_i=index_i, warm_b=warm_b):
                    self.assertEqual(len(check(bad_str, warm_b)), 1)
        # LLFR-00188: a long event-loop turn fails only with a limit,
        # and on a warm launch.
        self.assertEqual(len(check(good_str, True, 0.1)), 1)
        self.assertEqual(check(good_str, False, 0.1), [])
        self.assertEqual(check(good_str, True), [])
        self.assertEqual(measure_startup.dialog_summary_str(""),
                         "no dialog lines")
        self.assertEqual(measure_startup.parse_prepare_line(
            "plot_tool prepare: prepared=yes"), {})

    @covers("LLFR-00406", "HLFR-00091", "LLFR-00184", "HLFR-00046")
    def test_median_checks(self) -> None:
        """Dialog and splash times are judged by their warm medians.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00406, note: the times of each dialog are gathered over
        # the warm launches, both requests of each launch included.
        time_dict = {}
        measure_startup.add_dialog_times(
            time_dict, self.dialog_output_str([0.3] * 9 + [0.9]))
        measure_startup.add_dialog_times(
            time_dict, self.dialog_output_str([0.4] * 10).replace(
                "click=1 shown_s=0.400 visible=yes",
                "click=1 shown_s=0.400 visible=no", 1))
        self.assertEqual(time_dict["save_signals"], [0.3, 0.9, 0.4, 0.4])
        # A request that showed no dialog has no time.
        self.assertEqual(time_dict["open_file"], [0.3, 0.3, 0.4])
        median = measure_startup.median_failure_list
        # The single slow request (0.9 s) does not fail: median 0.4 s.
        self.assertEqual(median(time_dict, 0.65, "dialog", "LLFR-00406"),
                         [])
        summary_str = measure_startup.median_summary_str(time_dict)
        self.assertIn("save_signals median 0.400 s, slowest 0.900 s "
                      "(4 times)", summary_str)
        # A median over the limit fails, one failure per dialog; the
        # limit itself is allowed.
        slow_dict = {"open_file": [0.7, 0.7, 0.2], "save_pdf": [0.65],
                     "load_layout": [0.66, 0.1, 0.9, 0.2]}
        failure_list = median(slow_dict, 0.65, "dialog", "LLFR-00406")
        self.assertEqual(len(failure_list), 1)
        self.assertIn("dialog open_file: median 0.700 s over 3",
                      failure_list[0])
        self.assertIn("(LLFR-00406)", failure_list[0])
        # A dialog never timed on a warm launch fails too.
        self.assertEqual(len(median({"save_pdf": []}, 0.65, "dialog",
                                    "LLFR-00406")), 1)
        self.assertEqual(measure_startup.median_summary_str({}), "no times")
        # LLFR-00184, note: the warm splash times, judged by their median.
        self.assertEqual(median({"shown": [1.0, 2.3, 1.2]}, 2.0,
                                "splash screen", "LLFR-00184"), [])
        self.assertEqual(len(median({"shown": [2.1, 2.3, 1.2]}, 2.0,
                                    "splash screen", "LLFR-00184")), 1)

    @covers("LLFR-00406", "LLFR-00188", "LLFR-00184")
    def test_workflow_thresholds(self) -> None:
        """The macOS job checks the limits of the requirements.

        Inputs: none.
        Outputs: none.
        """
        workflow_path_str = os.path.join(
            REPOSITORY_ROOT_STR, ".github", "workflows", "macos_build.yml")
        with open(workflow_path_str, encoding="utf-8") as workflow_file:
            workflow_str = workflow_file.read()
        for name_str, option_tuple in (
                ("Measure the startup time",
                 ("--runs 6 ", "--warm-limit-s 5 ", "--splash-limit-s 2 ",
                  "--clear-font-cache")),
                ("Measure the file dialog opening time",
                 ("--runs 5 ", "--dialog-limit-s 0.65 ",
                  "--turn-limit-s 2 "))):
            step_str = workflow_str[workflow_str.index(
                "name: " + name_str + "\n"):]
            step_str = step_str[:step_str.index("bin/plot_tool.app")]
            for option_str in option_tuple:
                with self.subTest(name_str=name_str, option_str=option_str):
                    self.assertIn(option_str, step_str)
            # The step is not allowed to fail.
            self.assertNotIn("continue-on-error", step_str)
        # The startup launches ask for no dialog, so that the system
        # panels of one launch never slow the next one (issue #165).
        startup_str = workflow_str[workflow_str.index(
            "name: Measure the startup time\n"):]
        startup_str = startup_str[:startup_str.index("bin/plot_tool.app")]
        self.assertNotIn("--dialog-limit-s", startup_str)
        # A change of the dialog code runs the job on a pull request.
        self.assertIn("- src/view/file_dialogs.py", workflow_str)

    @covers("LLFR-00189")
    def test_font_cache_check(self) -> None:
        """A font list written again by a later launch fails the check.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as folder_str:
            self.assertEqual(
                measure_startup.font_list_state_dict(folder_str), {})
            font_path_str = os.path.join(folder_str, "fontlist-v390.json")
            with open(font_path_str, "w", encoding="utf-8") as font_file:
                font_file.write("{}")
            os.utime(font_path_str, ns=(1_000_000_000, 1_000_000_000))
            first_dict = measure_startup.font_list_state_dict(folder_str)
            self.assertEqual(list(first_dict), ["fontlist-v390.json"])
            self.assertEqual(measure_startup.font_cache_failure_str(
                first_dict, measure_startup.font_list_state_dict(
                    folder_str)), "")
            os.utime(font_path_str, ns=(2_000_000_000, 2_000_000_000))
            self.assertNotEqual(measure_startup.font_cache_failure_str(
                first_dict, measure_startup.font_list_state_dict(
                    folder_str)), "")
        self.assertNotEqual(measure_startup.font_cache_failure_str({}, {}),
                            "")

    @covers("LLFR-00189")
    def test_built_app_keeps_one_matplotlib_folder(self) -> None:
        """Every launch of a built app uses the same lasting folder.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as folder_str:
            folder_list = []
            for _ in range(2):
                environment_dict = {"XDG_CACHE_HOME": folder_str,
                                    "LOCALAPPDATA": folder_str}
                with mock.patch.object(matplotlib_cache.os.path,
                                       "expanduser",
                                       return_value=folder_str):
                    folder_list.append(
                        matplotlib_cache.use_persistent_matplotlib_folder(
                            environment_dict, frozen_b=True))
                self.assertEqual(environment_dict["MPLCONFIGDIR"],
                                 folder_list[-1])
            self.assertEqual(folder_list[0], folder_list[1])
            self.assertTrue(folder_list[0].startswith(folder_str))
            self.assertTrue(os.path.isdir(folder_list[0]))


@requires_qt
class SplashScreenTest(unittest.TestCase):
    """Check the splash screen widget and how main.py uses it."""

    def setUp(self) -> None:
        """Get the application and the modules under test.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view import icons, message_boxes, splash_screen
        import main
        self.icons = icons
        self.message_boxes = message_boxes
        self.splash_screen = splash_screen
        self.main = main
        self.splash_list = []

    def tearDown(self) -> None:
        """Close every splash screen made by the test.

        Inputs: none.
        Outputs: none.
        """
        for splash in self.splash_list:
            splash.close()
            splash.deleteLater()
        self.application.processEvents()

    def shown_splash(self):
        """Show a splash screen as main.py does.

        Inputs: none.
        Outputs: the shown SplashScreen.
        """
        splash = self.splash_screen.show_splash(self.application)
        self.splash_list.append(splash)
        return splash

    @covers("LLFR-00185", "LLFR-00183")
    def test_splash_shows_icon_name_and_loading(self) -> None:
        """The splash holds the app icon, "plot_tool" and "Loading...".

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QImage
        splash = self.shown_splash()
        self.assertEqual(splash.name_label.text(), "plot_tool")
        self.assertEqual(splash.message_label.text(), "Loading...")
        for label in (splash.icon_label, splash.name_label,
                      splash.message_label):
            self.assertTrue(label.isVisible())
            self.assertTrue(splash.rect().contains(
                label.mapTo(splash, label.rect().center())))
        pixmap = splash.icon_label.pixmap()
        self.assertFalse(pixmap.isNull())
        ratio_f = pixmap.devicePixelRatio()
        side_i = int(round(112 * ratio_f))
        self.assertEqual((pixmap.width(), pixmap.height()),
                         (side_i, side_i))
        image_format = QImage.Format.Format_ARGB32_Premultiplied
        self.assertEqual(
            pixmap.toImage().convertToFormat(image_format),
            self.icons.app_icon_image(side_i).convertToFormat(image_format))
        # The name sits under the icon, and "Loading..." under the name.
        icon_bottom_i = splash.icon_label.mapTo(
            splash, splash.icon_label.rect().bottomLeft()).y()
        name_top_i = splash.name_label.mapTo(splash, splash.name_label.rect(
            ).topLeft()).y()
        name_bottom_i = splash.name_label.mapTo(
            splash, splash.name_label.rect().bottomLeft()).y()
        message_top_i = splash.message_label.mapTo(
            splash, splash.message_label.rect().topLeft()).y()
        self.assertLessEqual(icon_bottom_i, name_top_i)
        self.assertLessEqual(name_bottom_i, message_top_i)

    @covers("LLFR-00185", "LLFR-00183")
    def test_icon_is_sharp_on_high_density_screens(self) -> None:
        """On a 2x screen the icon is drawn with twice the pixels.

        Inputs: none.
        Outputs: none.
        """
        # The pixmap given to the label: 224 device pixels shown in 112
        # logical pixels. (QLabel.pixmap() returns it at the label's own
        # pixel ratio, which is 1 on the offscreen test screen.)
        for ratio_f, side_i in ((1.0, 112), (2.0, 224), (1.5, 168)):
            with self.subTest(ratio_f=ratio_f):
                pixmap = self.splash_screen.splash_icon_pixmap(ratio_f)
                self.assertEqual((pixmap.width(), pixmap.height()),
                                 (side_i, side_i))
                self.assertAlmostEqual(pixmap.devicePixelRatio(), ratio_f)
                self.assertAlmostEqual(
                    pixmap.deviceIndependentSize().width(), 112.0)
        splash = self.splash_screen.SplashScreen(2.0)
        self.splash_list.append(splash)
        self.assertFalse(splash.icon_label.pixmap().isNull())

    @covers("LLFR-00184")
    def test_show_splash_puts_it_on_screen_centred(self) -> None:
        """show_splash returns a splash that is exposed and centred.

        Inputs: none.
        Outputs: none.
        """
        splash = self.shown_splash()
        self.assertTrue(splash.isVisible())
        self.assertTrue(self.splash_screen.splash_exposed(splash))
        screen_center = (self.application.primaryScreen()
                         .availableGeometry().center())
        splash_center = splash.geometry().center()
        self.assertLessEqual(abs(splash_center.x() - screen_center.x()), 1)
        self.assertLessEqual(abs(splash_center.y() - screen_center.y()), 1)

    @covers("LLFR-00186")
    def test_click_does_not_close_the_splash(self) -> None:
        """A click on the splash leaves it shown.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        splash = self.shown_splash()
        QTest.mouseClick(splash, Qt.MouseButton.LeftButton)
        self.application.processEvents()
        self.assertTrue(splash.isVisible())

    @covers("LLFR-00186")
    def test_splash_closes_when_the_window_shows(self) -> None:
        """The window is shown and the splash closed in the same step.

        The splash screen stays shown while the window is built (not
        shown), and is closed right after the window is shown, with no
        event handled in between, so the window system never draws the
        splash above the visible window. The window is then raised and
        activated.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMainWindow
        splash = self.shown_splash()
        window = QMainWindow()
        step_list = []
        close_splash = splash.close
        show_window = window.show
        raise_window = window.raise_
        activate_window = window.activateWindow

        def record(name_str: str, function):
            """Return a function that records its call, then runs one.

            Inputs:
                name_str: the name recorded.
                function: the function run after the record.
            Outputs: the recording function.
            """
            def recorded(*argument_tuple):
                """Record the call with the visibility of both windows.

                Inputs:
                    argument_tuple: passed to function.
                Outputs: what function returns.
                """
                step_list.append((name_str, splash.isVisible(),
                                  window.isVisible()))
                return function(*argument_tuple)
            return recorded

        splash.close = record("close", close_splash)
        window.raise_ = record("raise", raise_window)
        window.activateWindow = record("activate", activate_window)

        def build_window(application) -> tuple:
            """Build a window without showing it, as build_main_window.

            Inputs:
                application: the QApplication.
            Outputs: the tuple (window, controller).
            """
            step_list.append(("build", splash.isVisible(),
                              window.isVisible()))
            return window, None

        def show_function(window_tuple: tuple) -> None:
            """Show the window, as show_main_window does.

            Inputs:
                window_tuple: the tuple of build_window.
            Outputs: none.
            """
            step_list.append(("show", splash.isVisible(),
                              window.isVisible()))
            show_window()

        show_error = mock.Mock()
        with mock.patch.object(
                self.application, "processEvents",
                record("events", self.application.processEvents)):
            window_tuple = self.main.start_main_window(
                self.application, splash, build_window, show_error,
                show_function)
        try:
            self.assertIs(window_tuple[0], window)
            # Built behind the splash, not shown; shown while the splash
            # is still up, the splash closed right after, with no event
            # handled in between; then raised and activated.
            self.assertEqual(step_list, [
                ("build", True, False), ("show", True, False),
                ("close", True, True), ("raise", False, True),
                ("activate", False, True)])
            self.assertFalse(splash.isVisible())
            self.assertTrue(window.isVisible())
            show_error.assert_not_called()
            # Without a show function, finish shows the window itself.
            other_splash = self.shown_splash()
            other_window = QMainWindow()
            other_splash.finish(other_window)
            self.assertTrue(other_window.isVisible())
            self.assertFalse(other_splash.isVisible())
            other_window.close()
            other_window.deleteLater()
        finally:
            window.close()
            window.deleteLater()

    @covers("LLFR-00186", "LLFR-00058")
    def test_build_main_window_does_not_show_the_window(self) -> None:
        """build_main_window leaves showing the window to the swap.

        Inputs: none.
        Outputs: none.
        """
        main_window, controller = self.main.build_main_window(
            self.application)
        try:
            self.assertFalse(main_window.isVisible())
            self.main.show_main_window((main_window, controller))
            self.assertTrue(main_window.isVisible())
        finally:
            sys.excepthook = sys.__excepthook__
            main_window.close()
            main_window.deleteLater()
            self.application.processEvents()

    @covers("LLFR-00187", "LLFR-00071")
    def test_startup_error_closes_splash_before_error_box(self) -> None:
        """A failed start closes the splash, then shows the Error box.

        Inputs: none.
        Outputs: none.
        """
        splash = self.shown_splash()
        box_record_list = []
        build_box = self.message_boxes.build_unexpected_error_box

        def build_recorded_box(parent, message_str: str):
            """Build the real box, recording instead of waiting on it.

            Inputs:
                parent: the parent widget.
                message_str: the error description.
            Outputs: the QMessageBox, whose exec only records.
            """
            box = build_box(parent, message_str)

            def record_exec() -> int:
                """Record the box and the splash state when it shows.

                Inputs: none.
                Outputs: 0, as if OK was clicked.
                """
                box_record_list.append((splash.isVisible(),
                                        box.windowTitle(), box.text()))
                return 0

            box.exec = record_exec
            return box

        def failing_build(application) -> tuple:
            """Fail as a broken startup would.

            Inputs:
                application: the QApplication.
            Outputs: none; always raises.
            """
            raise RuntimeError("no display for the plots")

        with mock.patch.object(self.message_boxes,
                               "build_unexpected_error_box",
                               side_effect=build_recorded_box), \
                mock.patch("sys.stderr"):
            window_tuple = self.main.start_main_window(
                self.application, splash, failing_build,
                self.message_boxes.show_unexpected_error)
        self.assertIsNone(window_tuple)
        self.assertEqual(len(box_record_list), 1)
        splash_visible_b, title_str, text_str = box_record_list[0]
        self.assertFalse(splash_visible_b)
        self.assertEqual(title_str, "Error")
        self.assertIn("RuntimeError: no display for the plots", text_str)
        self.assertFalse(splash.isVisible())

    @covers("LLFR-00184")
    def test_probe_reports_heavy_modules(self) -> None:
        """The probe's splash line names slow modules already imported.

        Inputs: none.
        Outputs: none.
        """
        from view import startup_probe
        self.assertEqual(startup_probe.loaded_heavy_module_list(
            {"PyQt6": None, "view.icons": None}), [])
        self.assertEqual(startup_probe.loaded_heavy_module_list(
            {"numpy": None, "matplotlib": None}), ["matplotlib", "numpy"])
        line_str = startup_probe.splash_line_str(
            time.perf_counter(), True, {"pandas": None})
        splash_dict = measure_startup.parse_splash_line(line_str)
        self.assertEqual(splash_dict["heavy_module_list"], ["pandas"])
        self.assertEqual(splash_dict["process_id_i"], os.getpid())
        self.assertFalse(startup_probe.report_splash_shown(
            mock.Mock(), 0.0, {}))


@requires_qt
class StartupEndToEndTest(unittest.TestCase):
    """Run src/main.py in a new process, as a user launches the app."""

    def setUp(self) -> None:
        """Make sure Qt can run offscreen.

        Inputs: none.
        Outputs: none.
        """
        get_qt_application()

    @covers("LLFR-00184", "LLFR-00186", "LLFR-00185")
    def test_splash_shown_before_heavy_imports(self) -> None:
        """The splash is on screen before matplotlib is imported.

        Inputs: none.
        Outputs: none.
        """
        exit_code_i, output_str, error_str = run_main(
            {"PLOT_TOOL_STARTUP_PROBE": "1"})
        self.assertEqual(exit_code_i, 0, error_str)
        splash_dict = measure_startup.parse_splash_line(output_str)
        startup_dict = measure_startup.parse_startup_line(output_str)
        self.assertTrue(splash_dict, output_str + error_str)
        self.assertTrue(startup_dict, output_str + error_str)
        # LLFR-00184: shown and exposed, with no slow module imported.
        self.assertTrue(splash_dict["exposed_b"])
        self.assertEqual(splash_dict["heavy_module_list"], [])
        self.assertLess(splash_dict["since_main_s"],
                        startup_dict["since_main_s"])
        self.assertLess(output_str.index("plot_tool splash:"),
                        output_str.index("plot_tool startup:"))
        # LLFR-00186: closed when the window is shown.
        self.assertTrue(startup_dict["exposed_b"])
        self.assertFalse(startup_dict["splash_visible_b"])

    @covers("LLFR-00187")
    def test_startup_error_exits_with_error_code(self) -> None:
        """A failed start closes the splash, shows the box, exits 1.

        Inputs: none.
        Outputs: none.
        """
        driver_str = textwrap.dedent(f"""
            import sys
            sys.path.insert(0, {SOURCE_FOLDER_STR!r})
            import main
            from PyQt6.QtWidgets import QApplication
            from view import message_boxes
            from view.splash_screen import SplashScreen

            def splash_state_str():
                splash_list = [widget for widget in
                               QApplication.topLevelWidgets()
                               if isinstance(widget, SplashScreen)]
                visible_str = "yes" if any(
                    splash.isVisible() for splash in splash_list) else "no"
                return f"splashes={{len(splash_list)}} visible={{visible_str}}"

            def failing_build(application):
                print("build: " + splash_state_str(), flush=True)
                raise RuntimeError("injected startup failure")

            def record_error(parent, message_str):
                print("error box: " + splash_state_str(), flush=True)
                print("error message: " + message_str, flush=True)

            main.build_main_window = failing_build
            message_boxes.show_unexpected_error = record_error
            sys.exit(main.main())
            """)
        exit_code_i, output_str, error_str = run_main({}, driver_str)
        self.assertEqual(exit_code_i, 1, output_str + error_str)
        self.assertIn("build: splashes=1 visible=yes", output_str)
        self.assertIn("error box: splashes=1 visible=no", output_str)
        self.assertIn("error message: RuntimeError: injected startup "
                      "failure", output_str)
        self.assertLess(output_str.index("build:"),
                        output_str.index("error box:"))
        self.assertIn("injected startup failure", error_str)

    @covers("LLFR-00189", "LLFR-00188")
    def test_second_launch_reuses_the_font_list(self) -> None:
        """A warm launch is fast and doesn't rebuild the font list.

        Inputs: none.
        Outputs: none.
        """
        with tempfile.TemporaryDirectory() as folder_str:
            environment_dict = {"PLOT_TOOL_STARTUP_PROBE": "1",
                                "MPLCONFIGDIR": folder_str}
            state_list = []
            window_time_list = []
            for _ in range(3):
                exit_code_i, output_str, error_str = run_main(
                    environment_dict)
                self.assertEqual(exit_code_i, 0, error_str)
                startup_dict = measure_startup.parse_startup_line(
                    output_str)
                self.assertTrue(startup_dict, output_str + error_str)
                window_time_list.append(startup_dict["since_main_s"])
                state_list.append(
                    measure_startup.font_list_state_dict(folder_str))
        # LLFR-00189: written by the first launch, then only read.
        self.assertTrue(state_list[0])
        self.assertEqual(state_list[1], state_list[0])
        self.assertEqual(state_list[2], state_list[0])
        # LLFR-00188: the warm launches show the window within 5 s
        # (from source; the macOS job checks the built app).
        for window_s in window_time_list[1:]:
            self.assertLess(window_s, WARM_LIMIT_S)


if __name__ == "__main__":
    unittest.main()
