"""Tests of several data files in the controllers (no Qt needed).

The real MainController is used with the fake window of the synthetic
signal tests, so the real FileController adds the files, with their
numbers and prefixes (HLFR-00113 to HLFR-00117), and closes them
(HLFR-00118, HLFR-00119).
"""

import unittest

import numpy as np

from tests.support import covers

from controller.main_controller import MainController
from controller.plot_tools import (
    AREA_TOOL_STR, ARROW_TOOL_STR, DELTA_X_TOOL_STR, MARKER_TOOL_STR,
    NO_TOOL_STR, TEXT_TOOL_STR)
from model.signal_file import SignalFile
from tests.controller.test_synthetic_controller import FakeSyntheticWindow


def make_time_file(path_str: str, start_s: float, end_s: float,
                   sample_count_i: int = 101) -> SignalFile:
    """Build a file with Time, Speed and Torque between two times.

    Inputs:
        path_str: the path of the file.
        start_s: the first time sample, in seconds.
        end_s: the last time sample, in seconds.
        sample_count_i: the number of samples.
    Outputs: the SignalFile; Speed is 1 + Time and Torque is 2 * Time.
    """
    time_array = np.linspace(start_s, end_s, sample_count_i)
    return SignalFile(path_str, {"Time": time_array,
                                 "Speed": time_array + 1.0,
                                 "Torque": time_array * 2.0})


class SeveralFilesTestCase(unittest.TestCase):
    """Shared setup: the controllers of the app with a fake window."""

    def setUp(self) -> None:
        """Create the controllers; no file is open.

        Inputs: none.
        Outputs: none.
        """
        self.view = FakeSyntheticWindow()
        self.main_controller = MainController(self.view)
        self.file_controller = self.main_controller.file_controller
        self.plot_controller = self.main_controller.plot_controller
        self.workspace = self.plot_controller.workspace

    def open(self, signal_file: SignalFile) -> None:
        """Open a file through the real open-file flow.

        Inputs:
            signal_file: the file the loader returns.
        Outputs: none.
        """
        self.file_controller.load_function = lambda path_str: signal_file
        self.view.open_path_str = signal_file.path_str
        self.file_controller.open_file_requested()

    def plot(self, *name_tuple: str) -> int:
        """Create a plot in the current tab with some signals.

        Inputs:
            name_tuple: the signals, the first one double-clicked.
        Outputs: the id of the new plot.
        """
        self.plot_controller.on_signal_double_clicked(name_tuple[0])
        tab = self.workspace.find_tab(self.view.current_tab_id())
        plot_id_i = tab.plot_list[-1].plot_id_i
        for name_str in name_tuple[1:]:
            self.plot_controller.on_signal_dropped(plot_id_i, name_str)
        return plot_id_i

    def add_tab(self) -> int:
        """Add a tab, which becomes the current tab.

        Inputs: none.
        Outputs: the id of the new tab.
        """
        self.plot_controller.on_add_tab()
        return self.view.current_tab_id()

    def curve_names(self, plot_id_i: int) -> list:
        """Return the curves of a plot in the model.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: the signal names, in order.
        """
        return [curve.signal_name_str for curve in
                self.workspace.find_plot(plot_id_i).curve_list]

    def tab_names(self) -> list:
        """Return the names of the tabs in the model.

        Inputs: none.
        Outputs: the names, in tab order.
        """
        return [tab.name_str for tab in self.workspace.tab_list]


class SignalsOfSeveralFilesTest(SeveralFilesTestCase):
    """Curves of several files (HLFR-00116)."""

    @covers("LLFR-00911", "LLFR-00912", "LLFR-00913", "LLFR-00914",
            "LLFR-00068", "LLFR-00905", "LLFR-00907", "HLFR-00116")
    def test_each_curve_on_the_time_of_its_file(self) -> None:
        """One plot draws curves of two files, each on its own times.

        Inputs: none.
        Outputs: none.
        """
        self.open(make_time_file("a.csv", 0.0, 10.0))
        self.open(make_time_file("b.csv", 20.0, 30.0, 11))
        plot_id_i = self.plot("file1_Speed", "file2_Speed")
        self.assertEqual(self.curve_names(plot_id_i),
                         ["file1_Speed", "file2_Speed"])
        curve_list = self.view.drawn_dict[plot_id_i][0]
        np.testing.assert_array_equal(curve_list[0][1],
                                      np.linspace(0.0, 10.0, 101))
        np.testing.assert_array_equal(curve_list[1][1],
                                      np.linspace(20.0, 30.0, 11))
        np.testing.assert_array_equal(curve_list[1][2],
                                      np.linspace(21.0, 31.0, 11))

    @covers("LLFR-00915", "LLFR-00164", "HLFR-00116")
    def test_delta_marker_between_two_files(self) -> None:
        """A Delta X marker can have its points on curves of two files.

        Inputs: none.
        Outputs: none.
        """
        self.open(make_time_file("a.csv", 0.0, 10.0))
        self.open(make_time_file("b.csv", 20.0, 30.0, 11))
        plot_id_i = self.plot("file1_Speed", "file2_Speed")
        self.plot_controller.on_plot_tool_changed(DELTA_X_TOOL_STR)
        self.plot_controller.on_delta_point_pick(plot_id_i, "file1_Speed",
                                                 2.0, 3.0)
        self.plot_controller.on_delta_point_pick(plot_id_i, "file2_Speed",
                                                 25.0, 26.0)
        delta_marker = self.workspace.find_plot(
            plot_id_i).delta_marker_list[0]
        self.assertEqual(delta_marker.first_point_tuple[0], "file1_Speed")
        self.assertEqual(delta_marker.second_point_tuple[0], "file2_Speed")
        self.assertAlmostEqual(delta_marker.delta_f(), 23.0)


class TimeRangeTest(SeveralFilesTestCase):
    """The time range of the open data files (LLFR-00916)."""

    @covers("LLFR-00916", "LLFR-00115", "LLFR-00119", "LLFR-00676",
            "LLFR-00917", "HLFR-00035", "HLFR-00113")
    def test_range_of_every_open_file(self) -> None:
        """Reset zoom and the view limits use every open file; opening a
        file keeps the range the plots show.

        Inputs: none.
        Outputs: none.
        """
        self.open(make_time_file("a.csv", 0.0, 10.0))
        self.assertEqual(self.view.files_time_range_tuple, (0.0, 10.0))
        plot_id_i = self.plot("file1_Speed")
        self.assertEqual(self.view.range_dict[plot_id_i], (0.0, 10.0))
        self.open(make_time_file("b.csv", 20.0, 30.0, 11))
        # LLFR-00917: the time plot keeps its range.
        self.assertEqual(self.plot_controller.shared_time_range_tuple,
                         (0.0, 10.0))
        second_plot_id_i = self.plot("file2_Speed")
        self.assertEqual(self.view.range_dict[second_plot_id_i],
                         (0.0, 10.0))
        # LLFR-00119, LLFR-00676: the view limits zooms and pans to the
        # times of every open file.
        self.assertEqual(self.view.files_time_range_tuple, (0.0, 30.0))
        # LLFR-00115: Reset zoom shows the range of every open file.
        self.plot_controller.on_reset_zoom()
        self.assertEqual(self.view.range_dict[plot_id_i], (0.0, 30.0))
        self.assertEqual(self.view.range_dict[second_plot_id_i],
                         (0.0, 30.0))
        self.assertEqual(self.plot_controller.time_plot_range_tuple(),
                         (0.0, 30.0))

    @covers("LLFR-00688", "LLFR-00916")
    def test_first_time_plot_shows_every_open_file(self) -> None:
        """With no time plot, a new plot has the whole range of files.

        Inputs: none.
        Outputs: none.
        """
        self.open(make_time_file("a.csv", 0.0, 10.0))
        self.open(make_time_file("b.csv", -5.0, 5.0))
        self.assertEqual(self.plot_controller.shared_time_range_tuple, ())
        self.assertEqual(self.plot_controller.file_time_range_tuple(),
                         (-5.0, 10.0))
        self.assertEqual(self.view.files_time_range_tuple, (-5.0, 10.0))

    @covers("LLFR-00918", "LLFR-00916", "HLFR-00118")
    def test_close_limits_the_range_to_the_files_left(self) -> None:
        """A range that goes beyond the files left is cut to them.

        Inputs: none.
        Outputs: none.
        """
        self.open(make_time_file("a.csv", 0.0, 10.0))
        self.open(make_time_file("b.csv", 20.0, 30.0, 11))
        plot_id_i = self.plot("file1_Speed")
        self.plot("file2_Speed")
        self.plot_controller.on_time_range_changed(plot_id_i, 5.0, 25.0)
        self.file_controller.close_file(2)
        self.assertEqual(self.plot_controller.shared_time_range_tuple,
                         (5.0, 10.0))
        self.assertEqual(self.view.range_dict[plot_id_i], (5.0, 10.0))
        self.assertEqual(self.view.files_time_range_tuple, (0.0, 10.0))

    @covers("LLFR-00919", "LLFR-00916", "HLFR-00118")
    def test_range_outside_the_files_left_shows_their_range(self) -> None:
        """A range with no overlap shows the whole range of the files.

        Inputs: none.
        Outputs: none.
        """
        self.open(make_time_file("a.csv", 0.0, 10.0))
        self.open(make_time_file("b.csv", 20.0, 30.0, 11))
        plot_id_i = self.plot("file1_Speed")
        self.plot("file2_Speed")
        self.plot_controller.on_time_range_changed(plot_id_i, 22.0, 28.0)
        self.file_controller.close_file(2)
        self.assertEqual(self.plot_controller.shared_time_range_tuple, ())
        self.assertEqual(self.view.range_dict[plot_id_i], (0.0, 10.0))


class CloseFileTest(SeveralFilesTestCase):
    """Closing one data file (HLFR-00118)."""

    @covers("LLFR-00926", "LLFR-00927", "LLFR-00928", "LLFR-00930",
            "LLFR-00931", "LLFR-00178", "LLFR-00915", "HLFR-00118")
    def test_close_removes_the_file_and_what_it_drew(self) -> None:
        """Its curves, tips, delta markers and emptied plots go; the
        other file's stay, and the history is cleared.

        Inputs: none.
        Outputs: none.
        """
        self.open(make_time_file("a.csv", 0.0, 10.0))
        self.open(make_time_file("b.csv", 0.0, 10.0))
        shared_plot_id_i = self.plot("file1_Speed", "file2_Speed")
        self.plot_controller.on_plot_tool_changed(NO_TOOL_STR)
        self.plot_controller.on_tip_pin(shared_plot_id_i, "file1_Speed",
                                        1.0, 2.0)
        self.plot_controller.on_tip_pin(shared_plot_id_i, "file2_Speed",
                                        2.0, 3.0)
        self.plot_controller.on_plot_tool_changed(DELTA_X_TOOL_STR)
        for name_str, time_s in (("file1_Speed", 1.0), ("file2_Speed", 3.0),
                                 ("file2_Speed", 4.0), ("file2_Speed", 6.0)):
            self.plot_controller.on_delta_point_pick(
                shared_plot_id_i, name_str, time_s, time_s + 1.0)
        lone_plot_id_i = self.plot("file1_Torque")
        self.plot_controller.on_plot_tool_changed(TEXT_TOOL_STR)
        self.plot_controller.on_text_note_create(lone_plot_id_i, "note",
                                                 1.0, 1.0)
        self.assertTrue(self.view.undo_enabled_b)
        self.file_controller.close_file(1)
        shared_plot = self.workspace.find_plot(shared_plot_id_i)
        self.assertEqual(self.curve_names(shared_plot_id_i),
                         ["file2_Speed"])
        self.assertEqual([tip.signal_name_str
                          for tip in shared_plot.pinned_tip_list],
                         ["file2_Speed"])
        self.assertEqual(len(shared_plot.delta_marker_list), 1)
        self.assertEqual(shared_plot.delta_marker_list[0]
                         .first_point_tuple[0], "file2_Speed")
        # LLFR-00928: the plot of file 1 only is deleted, its note too.
        self.assertIsNone(self.workspace.find_plot(lone_plot_id_i))
        self.assertNotIn(lone_plot_id_i, self.view.plot_tab_dict)
        # LLFR-00930: the history is cleared.
        self.assertFalse(self.view.undo_enabled_b)
        self.assertFalse(self.view.redo_enabled_b)
        self.assertEqual(self.view.shown_name_list,
                         ["file2_Time", "file2_Speed", "file2_Torque"])

    @covers("LLFR-00929", "LLFR-00163")
    def test_first_point_on_a_closed_curve_is_discarded(self) -> None:
        """A first point picked on a curve of the closed file goes.

        Inputs: none.
        Outputs: none.
        """
        self.open(make_time_file("a.csv", 0.0, 10.0))
        self.open(make_time_file("b.csv", 0.0, 10.0))
        plot_id_i = self.plot("file1_Speed", "file2_Speed")
        self.plot_controller.on_plot_tool_changed(DELTA_X_TOOL_STR)
        self.plot_controller.on_delta_point_pick(plot_id_i, "file2_Speed",
                                                 1.0, 2.0)
        self.file_controller.close_file(1)
        self.assertNotEqual(self.plot_controller.pending_delta_tuple, ())
        self.file_controller.close_file(2)
        self.assertEqual(self.plot_controller.pending_delta_tuple, ())

    @covers("LLFR-00928", "LLFR-00926", "HLFR-00058")
    def test_frequency_plot_of_a_closed_file_is_deleted(self) -> None:
        """An FFT of a closed file goes with its frequency plot.

        Inputs: none.
        Outputs: none.
        """
        self.open(make_time_file("a.csv", 0.0, 10.0))
        self.open(make_time_file("b.csv", 0.0, 10.0))
        self.view.signal_menu_handler_dict["create"]("file1_Speed", "fft")
        fft_name_str = self.main_controller.synthetic_controller.store.names(
            )[0]
        frequency_plot_id_i = self.plot(fft_name_str)
        time_plot_id_i = self.plot("file2_Speed")
        self.file_controller.close_file(1)
        self.assertIsNone(self.workspace.find_plot(frequency_plot_id_i))
        self.assertIsNotNone(self.workspace.find_plot(time_plot_id_i))
        self.assertEqual(
            self.main_controller.synthetic_controller.store.names(), [])


class TabsAfterCloseTest(SeveralFilesTestCase):
    """The tabs emptied by a close (LLFR-00932, LLFR-00960 to 00962)."""

    def setUp(self) -> None:
        """Open two files from 0 s to 10 s.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.open(make_time_file("a.csv", 0.0, 10.0))
        self.open(make_time_file("b.csv", 0.0, 10.0))

    @covers("LLFR-00932", "LLFR-00960", "LLFR-00962", "HLFR-00118")
    def test_emptied_tabs_close_and_empty_tabs_stay(self) -> None:
        """Tabs left with no plot close; a tab empty before stays; the
        shown tab moves to the nearest tab on its left.

        Inputs: none.
        Outputs: none.
        """
        first_tab_id_i = self.workspace.tab_list[0].tab_id_i
        self.add_tab()
        self.plot("file2_Speed")
        self.add_tab()
        self.plot("file1_Speed")
        self.add_tab()
        self.plot("file1_Torque")
        self.assertEqual(self.tab_names(),
                         ["Tab 1", "Tab 2", "Tab 3", "Tab 4"])
        self.file_controller.close_file(1)
        self.assertEqual(self.tab_names(), ["Tab 1", "Tab 2"])
        self.assertEqual(list(self.view.tab_dict.values()),
                         ["Tab 1", "Tab 2"])
        # LLFR-00962: Tab 4 was shown; Tab 2 is the nearest on its left.
        self.assertEqual(self.view.current_tab_id(),
                         self.workspace.tab_list[1].tab_id_i)
        self.assertEqual(self.workspace.tab_list[0].tab_id_i,
                         first_tab_id_i)

    @covers("LLFR-00962")
    def test_shown_first_tab_moves_to_the_right(self) -> None:
        """With no tab left on its left, the nearest on its right.

        Inputs: none.
        Outputs: none.
        """
        self.plot("file1_Speed")
        second_tab_id_i = self.add_tab()
        self.plot("file2_Speed")
        self.plot_controller.view.set_current_tab(
            self.workspace.tab_list[0].tab_id_i)
        self.file_controller.close_file(1)
        self.assertEqual(self.tab_names(), ["Tab 2"])
        self.assertEqual(self.view.current_tab_id(), second_tab_id_i)

    @covers("LLFR-00961", "LLFR-00654", "LLFR-00066", "LLFR-00936",
            "HLFR-00119")
    def test_one_tab_always_left(self) -> None:
        """When every tab would close, the first one stays, empty.

        Inputs: none.
        Outputs: none.
        """
        self.plot_controller.on_rename_tab(
            self.workspace.tab_list[0].tab_id_i, "Main")
        self.plot("file1_Speed")
        self.add_tab()
        self.plot("file2_Speed")
        self.file_controller.close_all_files()
        self.assertEqual(self.tab_names(), ["Main"])
        self.assertEqual(self.workspace.tab_list[0].plot_list, [])
        self.assertEqual(self.view.current_tab_id(),
                         self.workspace.tab_list[0].tab_id_i)
        self.assertFalse(self.view.delete_enabled_b)
        # LLFR-00654: the tab numbering goes on.
        self.add_tab()
        self.assertEqual(self.tab_names(), ["Main", "Tab 3"])


class FlagsAndAreasAfterCloseTest(SeveralFilesTestCase):
    """Flags and areas outside the files left (LLFR-00933, LLFR-00950)."""

    def setUp(self) -> None:
        """Open a file from 0 s to 10 s and one from 20 s to 30 s.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.open(make_time_file("a.csv", 0.0, 10.0))
        self.open(make_time_file("b.csv", 20.0, 30.0, 11))
        self.first_plot_id_i = self.plot("file1_Speed")
        self.second_plot_id_i = self.plot("file2_Speed")

    @covers("LLFR-00933", "LLFR-00950", "HLFR-00118", "HLFR-00031",
            "HLFR-00069")
    def test_flags_and_areas_outside_are_deleted(self) -> None:
        """A flag on an end and an area touching an end stay.

        Inputs: none.
        Outputs: none.
        """
        self.plot_controller.on_plot_tool_changed(MARKER_TOOL_STR)
        for time_s in (5.0, 10.0, 20.0, 25.0, 30.0):
            self.plot_controller.on_marker_place(self.second_plot_id_i,
                                                 time_s)
        self.plot_controller.on_plot_tool_changed(AREA_TOOL_STR)
        for start_s, end_s in ((2.0, 4.0), (14.0, 20.0), (24.0, 26.0)):
            self.plot_controller.on_area_create(self.second_plot_id_i,
                                                start_s, end_s)
        self.assertEqual(len(self.workspace.area_list), 3)
        self.file_controller.close_file(1)
        self.assertEqual([marker.time_s for marker in
                          self.workspace.marker_list], [20.0, 25.0, 30.0])
        self.assertEqual([(area.start_s, area.end_s) for area in
                          self.workspace.area_list],
                         [(14.0, 20.0), (24.0, 26.0)])
        self.assertEqual(self.view.marker_drawn_dict[
            self.second_plot_id_i][0][2], 20.0)

    @covers("LLFR-00667", "LLFR-00711", "LLFR-00936", "LLFR-00937",
            "LLFR-00218", "LLFR-00395", "HLFR-00119")
    def test_close_all_files_deletes_every_flag_and_area(self) -> None:
        """No file left: no plot, flag, area or signal is left.

        Inputs: none.
        Outputs: none.
        """
        self.plot_controller.on_plot_tool_changed(MARKER_TOOL_STR)
        self.plot_controller.on_marker_place(self.second_plot_id_i, 25.0)
        self.plot_controller.on_plot_tool_changed(AREA_TOOL_STR)
        self.plot_controller.on_area_create(self.second_plot_id_i, 24.0,
                                            26.0)
        self.plot_controller.on_plot_tool_changed(ARROW_TOOL_STR)
        self.plot_controller.on_arrow_create(self.second_plot_id_i, 21.0,
                                             22.0, 23.0, 24.0)
        self.file_controller.close_all_files()
        self.assertFalse(self.workspace.has_plots())
        self.assertEqual(self.workspace.marker_list, [])
        self.assertEqual(self.workspace.area_list, [])
        self.assertEqual(self.view.shown_name_list, [])
        # LLFR-00937: no file name row is left.
        self.assertEqual(self.view.file_row_list, [])
        self.assertEqual(self.view.plot_tab_dict, {})
        self.assertFalse(self.view.layout_buttons_enabled_b)
        self.assertFalse(self.view.save_signals_enabled_b)
        self.assertEqual(self.view.files_time_range_tuple, ())
        self.assertEqual(self.plot_controller.shared_time_range_tuple, ())

    @covers("LLFR-00966", "LLFR-00950", "LLFR-00715", "HLFR-00106")
    def test_area_partly_outside_is_limited_when_resized(self) -> None:
        """An area that a close left partly outside the files is cut to
        their range when it is resized.

        Inputs: none.
        Outputs: none.
        """
        self.plot_controller.on_plot_tool_changed(AREA_TOOL_STR)
        self.plot_controller.on_area_create(self.first_plot_id_i, 8.0,
                                            22.0)
        area_id_i = self.workspace.area_list[0].area_id_i
        self.file_controller.close_file(2)
        self.assertEqual([(area.start_s, area.end_s) for area in
                          self.workspace.area_list], [(8.0, 22.0)])
        self.plot_controller.on_area_change(self.first_plot_id_i,
                                            area_id_i, 7.0, 22.0)
        self.assertEqual([(area.start_s, area.end_s) for area in
                          self.workspace.area_list], [(7.0, 10.0)])


class CloseQuestionTest(SeveralFilesTestCase):
    """The questions of the file menu (LLFR-00923, LLFR-00924)."""

    def setUp(self) -> None:
        """Open two files, plot from both, and script the answers.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.open(make_time_file("/data/run_A.csv", 0.0, 10.0))
        self.open(make_time_file("/data/run_B.mat", 20.0, 30.0))
        self.plot_id_i = self.plot("file1_Speed", "file2_Speed")
        self.plot_controller.on_add_tab()
        self.question_list = []
        self.answer_list = []
        self.view.ask_close_file = self.answer
        self.view.ask_close_all_files = self.answer
        self.plot_controller.on_plot_tool_changed("")

    def answer(self, question_str: str) -> bool:
        """Record a question and give the next scripted answer.

        Inputs:
            question_str: the question.
        Outputs: the answer.
        """
        self.question_list.append(question_str)
        return self.answer_list.pop(0)

    def undo_count(self) -> int:
        """Return how many actions can be undone.

        Inputs: none.
        Outputs: the depth of the undo history.
        """
        return self.plot_controller.undo_history.depth()

    @covers("LLFR-00977", "LLFR-00978", "LLFR-00979", "LLFR-00980",
            "LLFR-00924", "LLFR-00934")
    def test_close_questions_number_their_points(self) -> None:
        """The two close questions: the question, a blank line and the
        numbered points, one blank line apart.

        Inputs: none.
        Outputs: none.
        """
        from controller.file_controller import (
            CLOSE_ALL_FILES_POINT_STR, CLOSE_ALL_FILES_QUESTION_STR,
            CLOSE_FILE_SIGNALS_POINT_STR, CLOSE_HISTORY_POINT_STR,
            CLOSE_LAST_FILE_MARKERS_POINT_STR, CLOSE_TABS_POINT_STR,
            close_all_files_question, close_file_question)
        self.assertEqual(
            close_file_question("file1_run.csv", True),
            "Do you want to close file1_run.csv?\n\n"
            f"1. {CLOSE_FILE_SIGNALS_POINT_STR}\n\n"
            f"2. {CLOSE_TABS_POINT_STR}\n\n"
            f"3. {CLOSE_LAST_FILE_MARKERS_POINT_STR}\n\n"
            f"4. {CLOSE_HISTORY_POINT_STR}")
        all_str = close_all_files_question()
        self.assertTrue(all_str.startswith(
            f"{CLOSE_ALL_FILES_QUESTION_STR}\n\n"
            f"1. {CLOSE_ALL_FILES_POINT_STR}\n\n2. "))
        self.assertTrue(all_str.endswith(
            f"\n\n5. {CLOSE_HISTORY_POINT_STR}"))

    @covers("LLFR-00924", "HLFR-00118")
    def test_close_file_question_names_the_file_and_says_why(self) -> None:
        """The question names the row and the four consequences.

        Inputs: none.
        Outputs: none.
        """
        from controller.file_controller import (
            CLOSE_FILE_MARKERS_POINT_STR, CLOSE_FILE_SIGNALS_POINT_STR,
            CLOSE_HISTORY_POINT_STR, CLOSE_LAST_FILE_MARKERS_POINT_STR,
            CLOSE_TABS_POINT_STR)
        self.answer_list = [False]
        self.file_controller.close_file_requested(2)
        question_str = self.question_list[0]
        self.assertTrue(question_str.startswith(
            "Do you want to close file2_run_B.mat?"))
        # LLFR-00977, LLFR-00979, LLFR-00980: the points are numbered,
        # below the question and a blank line, one blank line apart.
        for number_i, point_str in enumerate(
                (CLOSE_FILE_SIGNALS_POINT_STR, CLOSE_TABS_POINT_STR,
                 CLOSE_FILE_MARKERS_POINT_STR, CLOSE_HISTORY_POINT_STR),
                start=1):
            self.assertIn(f"\n\n{number_i}. {point_str}", question_str)
        self.assertNotIn(CLOSE_LAST_FILE_MARKERS_POINT_STR, question_str)
        self.assertIn("synthetic signals computed from them", question_str)
        self.assertIn("removed from the signal list and from the plots",
                      question_str)
        self.assertIn("outside the time range of the files left",
                      question_str)
        self.assertIn("undo and redo history will be cleared", question_str)

    @covers("LLFR-00924", "HLFR-00118")
    def test_last_file_question_says_every_flag_and_area(self) -> None:
        """With one file left, every flag and area will be deleted.

        Inputs: none.
        Outputs: none.
        """
        from controller.file_controller import (
            CLOSE_FILE_MARKERS_POINT_STR, CLOSE_LAST_FILE_MARKERS_POINT_STR)
        self.file_controller.close_file(2)
        self.answer_list = [False]
        self.file_controller.close_file_requested(1)
        self.assertIn(CLOSE_LAST_FILE_MARKERS_POINT_STR,
                      self.question_list[0])
        self.assertNotIn(CLOSE_FILE_MARKERS_POINT_STR, self.question_list[0])

    @covers("LLFR-00924")
    def test_asked_when_no_signal_of_the_file_is_drawn(self) -> None:
        """The question is asked for a file with no curve too.

        Inputs: none.
        Outputs: none.
        """
        self.open(make_time_file("/data/run_C.csv", 0.0, 1.0))
        self.answer_list = [False]
        self.file_controller.close_file_requested(3)
        self.assertEqual(len(self.question_list), 1)
        self.assertIn("file3_run_C.csv", self.question_list[0])

    @covers("LLFR-00925", "LLFR-00924", "HLFR-00118")
    def test_declined_close_changes_nothing(self) -> None:
        """No keeps the files, the list, the plots and the history.

        Inputs: none.
        Outputs: none.
        """
        undo_count_i = self.undo_count()
        shown_list = list(self.view.shown_name_list)
        self.answer_list = [False]
        self.assertFalse(self.file_controller.close_file_requested(1))
        self.assertEqual(len(self.file_controller.data_files), 2)
        self.assertEqual(self.view.shown_name_list, shown_list)
        self.assertEqual(self.curve_names(self.plot_id_i),
                         ["file1_Speed", "file2_Speed"])
        self.assertEqual(self.undo_count(), undo_count_i)
        self.assertGreater(undo_count_i, 0)
        self.assertEqual(len(self.tab_names()), 2)

    @covers("LLFR-00926", "LLFR-00927", "LLFR-00930", "LLFR-00931",
            "LLFR-00932", "HLFR-00118")
    def test_proceeding_closes_the_file(self) -> None:
        """Yes removes the file, its curves and the history.

        Inputs: none.
        Outputs: none.
        """
        self.answer_list = [True]
        self.assertTrue(self.file_controller.close_file_requested(2))
        self.assertEqual([data_file.number_i for data_file
                          in self.file_controller.data_files.file_list], [1])
        self.assertEqual(self.curve_names(self.plot_id_i), ["file1_Speed"])
        self.assertEqual(self.view.file_row_list, ["file1_run_A.csv"])
        self.assertEqual(self.undo_count(), 0)
        # A number that is not open asks nothing.
        self.assertFalse(self.file_controller.close_file_requested(2))
        self.assertEqual(len(self.question_list), 1)

    @covers("LLFR-00934", "LLFR-00935", "LLFR-00936", "LLFR-00937",
            "LLFR-00904", "HLFR-00119")
    def test_close_all_files_asks_once(self) -> None:
        """One question with the five points; No keeps, Yes closes all.

        Inputs: none.
        Outputs: none.
        """
        from controller.file_controller import close_all_files_question
        self.answer_list = [False]
        self.assertEqual(self.file_controller.close_all_files_requested(),
                         [])
        self.assertEqual(self.question_list, [close_all_files_question()])
        self.assertEqual(len(self.file_controller.data_files), 2)
        question_str = self.question_list[0]
        for part_str in ("All the open data files will be closed",
                         "Their signals and synthetic signals will be "
                         "removed from the signal list and from the plots",
                         "The tabs left with no plot will be closed",
                         "Every flag and every area will be deleted, "
                         "because no file is left",
                         "The undo and redo history will be cleared"):
            self.assertIn(part_str, question_str)
        self.answer_list = [True]
        closed_list = self.file_controller.close_all_files_requested()
        self.assertEqual([data_file.number_i for data_file in closed_list],
                         [1, 2])
        self.assertEqual(len(self.question_list), 2)
        self.assertEqual(self.view.file_row_list, [])
        self.assertEqual(self.view.shown_name_list, [])
        # LLFR-00904: the next file is file 3.
        self.open(make_time_file("/data/run_C.csv", 0.0, 1.0))
        self.assertEqual(self.view.file_row_list, ["file3_run_C.csv"])
        # With no file open, nothing is asked.
        self.file_controller.close_all_files()
        self.assertEqual(self.file_controller.close_all_files_requested(),
                         [])
        self.assertEqual(len(self.question_list), 2)


if __name__ == "__main__":
    unittest.main()
