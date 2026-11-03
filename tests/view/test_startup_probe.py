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

    @covers("LLFR-00406")
    def test_dialog_probe_switch_and_line(self) -> None:
        """The dialog probe is off by default; its line is parsable.

        Inputs: none.
        Outputs: none.
        """
        probe = self.startup_probe
        self.assertFalse(probe.dialog_probe_enabled({}))
        self.assertFalse(probe.dialog_probe_enabled(
            {"PLOT_TOOL_DIALOG_PROBE": "0"}))
        self.assertTrue(probe.dialog_probe_enabled(
            {"PLOT_TOOL_DIALOG_PROBE": "1"}))
        pool = mock.Mock(prepared_b=True, step_count_i=3,
                         prepare_duration_s=0.4, longest_step_s=0.25,
                         step_duration_list=[0.25, 0.1, 0.05])
        pool.panel_state_str.return_value = "warmed,warmed"
        self.assertEqual(
            probe.prepare_line_str(pool, 0.5, 0.26, False),
            "plot_tool prepare: prepared=yes waited_s=0.500 steps=3 "
            "prepare_s=0.400 longest_step_s=0.250 longest_turn_s=0.260 "
            "step_s=0.250,0.100,0.050 panels=warmed,warmed "
            "dialog_seen=no")
        pool.step_duration_list = []
        self.assertIn("step_s=none panels=warmed,warmed dialog_seen=yes",
                      probe.prepare_line_str(pool, 0.5, 0.16, True))
        line_str = probe.dialog_line_str("save_pdf", 2, 0.0456, True,
                                         False, 0.25)
        self.assertEqual(line_str, "plot_tool dialog: name=save_pdf "
                         "click=2 shown_s=0.046 visible=yes prepared=no "
                         "prepare_s=0.250")
        self.assertEqual([entry[1] for entry in probe.PROBE_DIALOG_TUPLE],
                         ["open_file", "save_layout", "load_layout",
                          "save_pdf", "save_signals"])

    @covers("LLFR-00406")
    def test_report_measures_each_dialog_twice(self) -> None:
        """With the dialog probe on, each dialog is shown twice.

        Inputs: none.
        Outputs: none.
        """
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        main_window = MainWindow()
        controller = MainController(main_window)
        controller.start()
        main_window.schedule_file_dialog_preparation()
        pool = main_window.file_dialog_pool
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QFileDialog
        call_list = []
        for _, key_str in self.startup_probe.PROBE_DIALOG_TUPLE:
            dialog = pool.dialog(key_str)
            # Shown as a standalone, non-modal window, as exec shows it.
            dialog.show = (lambda key_str=key_str, dialog=dialog: (
                call_list.append((key_str, dialog.windowModality())),
                QFileDialog.show(dialog)))
        pool.dialog("save_pdf").setWindowModality(
            Qt.WindowModality.ApplicationModal)
        output_stream = io.StringIO()
        fake_application = FakeApplication()
        fake_application.processEvents = self.application.processEvents
        pause_patch = mock.patch.object(self.startup_probe,
                                        "PROBE_PAUSE_S", 0.01)
        pause_patch.start()
        self.addCleanup(pause_patch.stop)
        try:
            self.startup_probe.report_startup(
                fake_application, 0.0, True, mock.Mock(),
                {"PLOT_TOOL_DIALOG_PROBE": "1"}, output_stream,
                main_window=main_window)
            dialog_line_list = [
                line_str
                for line_str in output_stream.getvalue().splitlines()
                if line_str.startswith("plot_tool dialog:")]
            self.assertEqual(len(dialog_line_list), 10)
            non_modal = Qt.WindowModality.NonModal
            self.assertEqual(call_list, [
                (key_str, non_modal) for key_str in (
                    "open_file", "open_file", "save_layout", "save_layout",
                    "load_layout", "load_layout", "save_pdf", "save_pdf",
                    "save_signals", "save_signals")])
            # The modality the dialog had is given back.
            self.assertEqual(pool.dialog("save_pdf").windowModality(),
                             Qt.WindowModality.ApplicationModal)
            self.assertEqual(pool.dialog("open_file").windowModality(),
                             non_modal)
            for line_str in dialog_line_list:
                self.assertIn("visible=yes prepared=yes", line_str)
            # LLFR-00406, issue #165: the preparation line comes first,
            # with no dialog seen before the first request.
            output_str = output_stream.getvalue()
            self.assertLess(output_str.index("plot_tool prepare:"),
                            output_str.index("plot_tool dialog:"))
            prepare_dict = measure_startup.parse_prepare_line(output_str)
            self.assertTrue(prepare_dict["prepared_b"])
            self.assertFalse(prepare_dict["dialog_seen_b"])
            self.assertEqual(prepare_dict["step_count_i"], 5)
            self.assertEqual(measure_startup.dialog_failure_list(
                output_str, True), [])
            # Every dialog is closed again.
            for _, key_str in self.startup_probe.PROBE_DIALOG_TUPLE:
                self.assertFalse(pool.dialog(key_str).isVisible())
            self.assertEqual(fake_application.exit_code_list, [0])
            # Without the variable, no dialog is shown.
            call_list.clear()
            self.startup_probe.report_startup(
                FakeApplication(), 0.0, True, mock.Mock(), {},
                io.StringIO(), main_window=main_window)
            self.assertEqual(call_list, [])
        finally:
            main_window.close()
            main_window.deleteLater()
            self.application.processEvents()

    @covers("LLFR-00406", "HLFR-00091")
    def test_main_shows_every_dialog_quickly(self) -> None:
        """src/main.py: every file dialog appears within 0.6 s.

        The app is started as the user starts it; the probe shows each
        dialog twice, the first time right after the dialogs were
        prepared, as the first click after the start would.

        Inputs: none.
        Outputs: none.
        """
        environment_dict = dict(os.environ)
        environment_dict["PLOT_TOOL_STARTUP_PROBE"] = "1"
        environment_dict["PLOT_TOOL_DIALOG_PROBE"] = "1"
        environment_dict.setdefault("QT_QPA_PLATFORM", "offscreen")
        environment_dict.pop("PLOT_TOOL_PROBE_FILES", None)
        process = subprocess.Popen(
            [sys.executable, os.path.join(SOURCE_FOLDER_STR, "main.py")],
            env=environment_dict, cwd=REPOSITORY_ROOT_STR,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            output_str, error_str = process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            self.fail("the app did not quit with the dialog probe")
        self.assertEqual(process.returncode, 0, error_str)
        dialog_line_list = [
            line_str for line_str in output_str.splitlines()
            if line_str.startswith("plot_tool dialog:")]
        self.assertEqual(len(dialog_line_list), 10, output_str + error_str)
        name_list = []
        for line_str in dialog_line_list:
            field_dict = dict(part.split("=", 1)
                              for part in line_str.split()[2:])
            name_list.append((field_dict["name"], field_dict["click"]))
            with self.subTest(line_str=line_str):
                self.assertEqual(field_dict["visible"], "yes")
                self.assertEqual(field_dict["prepared"], "yes")
                self.assertLessEqual(float(field_dict["shown_s"]), 0.6)
        self.assertEqual(name_list, [
            (name_str, click_str)
            for name_str in ("open_file", "save_layout", "load_layout",
                             "save_pdf", "save_signals")
            for click_str in ("1", "2")])

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
