"""Tests for the startup probe used to check the standalone build.

The probe (src/view/startup_probe.py) is off unless
PLOT_TOOL_STARTUP_PROBE is "1"; then it reports when the main window
with its three panels (LLFR-00058) is shown, and quits. The end-to-end
test launches ``src/main.py`` in a separate process, as the build check
in .github/workflows/macos_build.yml launches the built app.
"""

import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from tests.support import (
    REPOSITORY_ROOT_STR, SOURCE_FOLDER_STR, covers, get_qt_application,
    requires_qt)
from tests.user_tests import measure_startup


class FakeApplication:
    """Stand-in for QApplication that records the exit code."""

    def __init__(self) -> None:
        """Start with no exit code.

        Inputs: none.
        Outputs: none.
        """
        self.exit_code_list = []

    def exit(self, exit_code_i: int) -> None:
        """Record the exit code instead of ending an event loop.

        Inputs:
            exit_code_i: the code the app would exit with.
        Outputs: none.
        """
        self.exit_code_list.append(exit_code_i)


class MeasureStartupParseTest(unittest.TestCase):
    """Check how tests/user_tests/measure_startup.py reads the probe."""

    @covers("LLFR-00058")
    def test_parse_startup_line(self) -> None:
        """The probe line is found among other output and read.

        Inputs: none.
        Outputs: none.
        """
        output_str = ("Qt warning\nplot_tool startup: "
                      "window_shown_epoch_s=1700000000.250 "
                      "since_main_s=1.500 exposed=yes pid=4321\n"
                      "plot_tool probe file: OK a.csv signals=2\n")
        startup_dict = measure_startup.parse_startup_line(output_str)
        self.assertAlmostEqual(startup_dict["window_shown_epoch_s"],
                               1700000000.25)
        self.assertAlmostEqual(startup_dict["since_main_s"], 1.5)
        self.assertTrue(startup_dict["exposed_b"])
        self.assertEqual(startup_dict["process_id_i"], 4321)
        self.assertEqual(measure_startup.parse_startup_line("nothing"), {})

    @covers("LLFR-00058")
    def test_run_failure_reasons(self) -> None:
        """A missing line, another process or a bad exit code fail a run.

        Inputs: none.
        Outputs: none.
        """
        good_dict = {"launch_to_window_s": 1.0, "same_process_b": True,
                     "exposed_b": True, "exit_code_i": 0, "output_str": ""}
        self.assertEqual(measure_startup.run_failure_str(good_dict), "")
        for key_str, value in (("launch_to_window_s", None),
                               ("same_process_b", False),
                               ("exit_code_i", 1)):
            with self.subTest(key_str=key_str):
                bad_dict = dict(good_dict)
                bad_dict[key_str] = value
                self.assertNotEqual(
                    measure_startup.run_failure_str(bad_dict), "")


@requires_qt
class StartupProbeTest(unittest.TestCase):
    """Check the probe's switch, its report and its file check."""

    def setUp(self) -> None:
        """Get the application and the probe module.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view import startup_probe
        self.startup_probe = startup_probe

    @covers("LLFR-00058")
    def test_probe_is_off_without_the_variable(self) -> None:
        """Without PLOT_TOOL_STARTUP_PROBE=1 nothing is scheduled.

        Inputs: none.
        Outputs: none.
        """
        for environment_dict in ({}, {"PLOT_TOOL_STARTUP_PROBE": "0"},
                                 {"PLOT_TOOL_STARTUP_PROBE": ""},
                                 {"PLOT_TOOL_STARTUP_PROBE": "yes"}):
            with self.subTest(environment_dict=environment_dict):
                with mock.patch.object(self.startup_probe,
                                       "QTimer") as timer_class:
                    installed_b = self.startup_probe.install_startup_probe(
                        FakeApplication(), mock.Mock(), 0.0, mock.Mock(),
                        environment_dict)
                self.assertFalse(installed_b)
                timer_class.assert_not_called()

    @covers("LLFR-00058")
    def test_probe_is_on_with_the_variable(self) -> None:
        """With PLOT_TOOL_STARTUP_PROBE=1 a polling timer is started.

        Inputs: none.
        Outputs: none.
        """
        with mock.patch.object(self.startup_probe, "QTimer") as timer_class:
            installed_b = self.startup_probe.install_startup_probe(
                FakeApplication(), mock.Mock(), 0.0, mock.Mock(),
                {"PLOT_TOOL_STARTUP_PROBE": "1"})
        self.assertTrue(installed_b)
        timer_class.return_value.start.assert_called_once()

    @covers("LLFR-00058")
    def test_report_prints_time_and_quits(self) -> None:
        """The report prints a parsable line and exits with code 0.

        Inputs: none.
        Outputs: none.
        """
        application = FakeApplication()
        output_stream = io.StringIO()
        start_s = time.perf_counter() - 2.0
        self.startup_probe.report_startup(application, start_s, True,
                                          mock.Mock(), {}, output_stream)
        startup_dict = measure_startup.parse_startup_line(
            output_stream.getvalue())
        self.assertGreaterEqual(startup_dict["since_main_s"], 2.0)
        self.assertLess(startup_dict["since_main_s"], 60.0)
        self.assertAlmostEqual(startup_dict["window_shown_epoch_s"],
                               time.time(), delta=60.0)
        self.assertEqual(startup_dict["process_id_i"], os.getpid())
        self.assertEqual(application.exit_code_list, [0])

    @covers("LLFR-00058")
    def test_report_opens_probe_files(self) -> None:
        """Probe files are opened; one failure makes the exit code 1.

        Inputs: none.
        Outputs: none.
        """
        from model.file_loader import load_signal_file
        with tempfile.TemporaryDirectory() as folder_str:
            good_path_str = os.path.join(folder_str, "good.csv")
            with open(good_path_str, "w", encoding="utf-8") as csv_file:
                csv_file.write("Time,Speed\n0,1\n1,2\n")
            bad_path_str = os.path.join(folder_str, "bad.txt")
            for path_list, exit_code_i in (([good_path_str], 0),
                                           ([good_path_str,
                                             bad_path_str], 1)):
                application = FakeApplication()
                output_stream = io.StringIO()
                environment_dict = {
                    "PLOT_TOOL_PROBE_FILES": os.pathsep.join(path_list)}
                self.startup_probe.report_startup(
                    application, 0.0, True, load_signal_file,
                    environment_dict, output_stream)
                output_str = output_stream.getvalue()
                self.assertIn("plot_tool probe file: OK good.csv "
                              "signals=2", output_str)
                self.assertEqual(application.exit_code_list, [exit_code_i])
        self.assertIn("plot_tool probe file: FAILED bad.txt", output_str)

    @covers("LLFR-00058")
    def test_main_reports_the_shown_window_and_quits(self) -> None:
        """src/main.py with the probe shows the window, reports, quits.

        Inputs: none.
        Outputs: none.
        """
        environment_dict = dict(os.environ)
        environment_dict["PLOT_TOOL_STARTUP_PROBE"] = "1"
        environment_dict.setdefault("QT_QPA_PLATFORM", "offscreen")
        sample_path_str = os.path.join(REPOSITORY_ROOT_STR, "tests",
                                       "user_tests", "good",
                                       "signals_comma.csv")
        environment_dict["PLOT_TOOL_PROBE_FILES"] = sample_path_str
        process = subprocess.Popen(
            [sys.executable, os.path.join(SOURCE_FOLDER_STR, "main.py")],
            env=environment_dict, cwd=REPOSITORY_ROOT_STR,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            output_str, error_str = process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            self.fail("the app did not quit with the startup probe")
        self.assertEqual(process.returncode, 0, error_str)
        startup_dict = measure_startup.parse_startup_line(output_str)
        self.assertTrue(startup_dict, output_str + error_str)
        self.assertTrue(startup_dict["exposed_b"])
        self.assertEqual(startup_dict["process_id_i"], process.pid)
        self.assertIn("plot_tool probe file: OK signals_comma.csv",
                      output_str)


if __name__ == "__main__":
    unittest.main()
