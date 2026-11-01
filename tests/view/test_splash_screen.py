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
        # LLFR-00184: the 2 s splash limit holds for every launch.
        late_dict = dict(good_dict, launch_to_splash_s=2.5)
        for warm_b in (False, True):
            with self.subTest(warm_b=warm_b):
                self.assertEqual(len(check(late_dict, warm_b, 5.0, 2.0)), 1)
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
        splash = self.splash_screen.SplashScreen(2.0)
        self.splash_list.append(splash)
        pixmap = splash.icon_label.pixmap()
        self.assertEqual(pixmap.width(), 224)
        self.assertAlmostEqual(pixmap.devicePixelRatio(), 2.0)

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
        """start_main_window closes the splash once the window is shown.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMainWindow
        splash = self.shown_splash()
        window = QMainWindow()
        visible_during_build_list = []

        def build_window(application) -> tuple:
            """Show a window, as build_main_window does.

            Inputs:
                application: the QApplication.
            Outputs: the tuple (window, controller).
            """
            visible_during_build_list.append(splash.isVisible())
            window.show()
            return window, None

        show_error = mock.Mock()
        window_tuple = self.main.start_main_window(
            self.application, splash, build_window, show_error)
        try:
            self.assertIs(window_tuple[0], window)
            self.assertEqual(visible_during_build_list, [True])
            self.assertFalse(splash.isVisible())
            self.assertTrue(window.isVisible())
            show_error.assert_not_called()
        finally:
            window.close()
            window.deleteLater()

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
