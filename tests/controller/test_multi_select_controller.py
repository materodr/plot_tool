"""Tests for plotting several selected signals at once (no Qt needed).

The plot controller runs on the fake views of the plot and synthetic
signal tests. The Enter key of the signal list reaches the controller
through ``set_selected_signals_plot_handler`` (LLFR-00295) and a drop
of several names through ``signals_drop_handler`` (LLFR-00297).
"""

import unittest

from tests.support import covers

from tests.controller.test_frequency_plots_controller import (
    FrequencyPlotTestCase)
from tests.controller.test_plot_controller import PlotControllerTestCase
from tests.controller.test_signal_list_controller import (
    FakeSignalListView)
from tests.controller.test_plot_controller import (
    FakeFileController, make_signal_file)

from controller.signal_list_controller import SignalListController
from model.curve_colors import PALETTE_COLOR_TUPLE
from model.workspace import (
    FREQUENCY_PLOT_KIND_STR, MAXIMUM_PLOTS_PER_TAB_I, TIME_PLOT_KIND_STR)


class MultiSelectTestCase(PlotControllerTestCase):
    """Shared helpers: press Enter and drop several names."""

    def press_enter(self, signal_name_list: list) -> None:
        """Run the Enter key handler with the selected names.

        Inputs:
            signal_name_list: the selected names, in list order.
        Outputs: none.
        """
        self.view.handler_dict["plot_selection"](signal_name_list)

    def drop_names(self, plot_id_i: int, signal_name_list: list) -> None:
        """Run the handler of a drop of several names.

        Inputs:
            plot_id_i: id of the target plot.
            signal_name_list: the dropped names, in list order.
        Outputs: none.
        """
        self.view.handler_dict["signals_drop_handler"](plot_id_i,
                                                       signal_name_list)

    def drawn_colors(self, plot_id_i: int) -> list:
        """Return the curve colors last drawn in a plot.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: a list of color strings, in curve order.
        """
        return [curve_tuple[3]
                for curve_tuple in self.view.drawn_dict[plot_id_i][0]]

    def undo(self) -> None:
        """Run the Undo handler.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["undo"]()


class EnterKeyPlotTest(MultiSelectTestCase):
    """The Enter key plots the selection in one new plot."""

    @covers("LLFR-00295", "LLFR-00033", "LLFR-00144", "HLFR-00064",
            "HLFR-00020", "LLFR-00629")
    def test_enter_creates_one_plot_with_every_signal(self) -> None:
        """One new plot draws every selected signal, in list order.

        Inputs: none.
        Outputs: none.
        """
        self.press_enter(["s2", "s5", "Time"])
        plot_id_list = self.current_plot_ids()
        self.assertEqual(len(plot_id_list), 1)
        plot_id_i = plot_id_list[0]
        self.assertEqual(self.view.drawn_names(plot_id_i),
                         ["s2", "s5", "Time"])
        self.assertEqual(self.drawn_colors(plot_id_i),
                         list(PALETTE_COLOR_TUPLE[:3]))
        self.assertEqual(self.view.plot_kind_dict[plot_id_i],
                         TIME_PLOT_KIND_STR)
        self.assertEqual(self.view.plot_tab_dict[plot_id_i],
                         self.view.current_tab_id())

    @covers("LLFR-00295", "LLFR-01074", "HLFR-00064")
    def test_enter_adds_the_plot_below_the_others(self) -> None:
        """The new plot goes below the existing plots of the tab.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        first_plot_id_i = self.current_plot_ids()[0]
        self.press_enter(["s3", "s4"])
        plot_id_list = self.current_plot_ids()
        self.assertEqual(len(plot_id_list), 2)
        self.assertEqual(plot_id_list[0], first_plot_id_i)
        self.assertEqual(self.view.drawn_names(plot_id_list[1]),
                         ["s3", "s4"])
        self.assertEqual(self.view.drawn_names(first_plot_id_i), ["s1"])

    @covers("LLFR-00295", "LLFR-00034", "HLFR-00064", "HLFR-00020",
            "LLFR-00629")
    def test_enter_with_more_than_eight_signals(self) -> None:
        """Signals after the 8th get distinct random colors.

        Inputs: none.
        Outputs: none.
        """
        name_list = [f"s{index_i}" for index_i in range(1, 11)]
        self.press_enter(name_list)
        plot_id_i = self.current_plot_ids()[0]
        self.assertEqual(self.view.drawn_names(plot_id_i), name_list)
        color_list = self.drawn_colors(plot_id_i)
        self.assertEqual(color_list[:8], list(PALETTE_COLOR_TUPLE[:8]))
        self.assertEqual(len(set(color_list)), len(color_list))

    @covers("LLFR-00295", "LLFR-00031", "LLFR-00032", "HLFR-00018",
            "LLFR-00630")
    def test_enter_in_a_full_tab_shows_the_full_tab_box(self) -> None:
        """A full tab gets no new plot and the Full Tab box is shown.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(MAXIMUM_PLOTS_PER_TAB_I):
            self.double_click("s1")
        self.assertEqual(self.view.full_tab_count_i, 0)
        plot_id_list = self.current_plot_ids()
        self.press_enter(["s2", "s3"])
        self.assertEqual(self.current_plot_ids(), plot_id_list)
        self.assertEqual(self.view.full_tab_count_i, 1)
        self.assertFalse(self.controller.undo_history.can_redo())

    @covers("LLFR-00295", "LLFR-00056", "HLFR-00064", "LLFR-00629")
    def test_enter_with_repeated_names_draws_each_once(self) -> None:
        """A name given twice is drawn once; unknown names are skipped.

        Inputs: none.
        Outputs: none.
        """
        self.press_enter(["s1", "nope", "s1", "s2"])
        plot_id_i = self.current_plot_ids()[0]
        self.assertEqual(self.view.drawn_names(plot_id_i), ["s1", "s2"])

    @covers("LLFR-00296", "HLFR-00064", "LLFR-00632")
    def test_enter_with_nothing_selected_does_nothing(self) -> None:
        """An empty selection creates no plot and shows no message.

        Inputs: none.
        Outputs: none.
        """
        self.view.call_list.clear()
        self.press_enter([])
        self.press_enter(["unknown"])
        self.assertEqual(self.view.call_list, [])
        self.assertEqual(self.current_plot_ids(), [])
        self.assertEqual(self.view.full_tab_count_i, 0)
        self.assertEqual(self.view.kind_mismatch_count_i, 0)

    @covers("LLFR-00301", "LLFR-00140", "HLFR-00064", "HLFR-00040")
    def test_one_undo_removes_the_whole_plot(self) -> None:
        """One undo removes the new plot with all its curves.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        self.press_enter(["s2", "s3", "s4"])
        self.assertEqual(len(self.current_plot_ids()), 2)
        self.undo()
        plot_id_list = self.current_plot_ids()
        self.assertEqual(len(plot_id_list), 1)
        self.assertEqual(self.view.drawn_names(plot_id_list[0]), ["s1"])
        self.undo()
        self.assertEqual(self.current_plot_ids(), [])

    @covers("LLFR-00301", "LLFR-00192", "HLFR-00048")
    def test_redo_brings_the_whole_plot_back(self) -> None:
        """Redo brings the plot back with every curve.

        Inputs: none.
        Outputs: none.
        """
        self.press_enter(["s2", "s3"])
        self.undo()
        self.view.handler_dict["redo"]()
        plot_id_list = self.current_plot_ids()
        self.assertEqual(len(plot_id_list), 1)
        self.assertEqual(self.view.drawn_names(plot_id_list[0]),
                         ["s2", "s3"])


class DropSeveralTest(MultiSelectTestCase):
    """A drop of several signals on a plot."""

    @covers("LLFR-00297", "LLFR-00033", "HLFR-00065")
    def test_drop_adds_every_signal_in_list_order(self) -> None:
        """Every dropped signal is drawn, in list order.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.drop_names(plot_id_i, ["s3", "s4", "Time"])
        self.assertEqual(self.view.drawn_names(plot_id_i),
                         ["s1", "s3", "s4", "Time"])
        self.assertEqual(self.drawn_colors(plot_id_i),
                         list(PALETTE_COLOR_TUPLE[:4]))
        self.assertEqual(len(self.current_plot_ids()), 1)

    @covers("LLFR-00299", "LLFR-00056", "LLFR-00057", "HLFR-00065")
    def test_drop_skips_signals_already_in_the_plot(self) -> None:
        """Signals already drawn are skipped, without a message.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.drop_names(plot_id_i, ["s1", "s2", "s3"])
        self.assertEqual(self.view.drawn_names(plot_id_i),
                         ["s1", "s2", "s3"])
        self.assertEqual(self.view.kind_mismatch_count_i, 0)
        self.assertEqual(self.view.full_tab_count_i, 0)

    @covers("LLFR-00299", "LLFR-00057", "LLFR-00140", "HLFR-00065")
    def test_drop_of_signals_all_in_the_plot_does_nothing(self) -> None:
        """A drop whose signals are all drawn changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.press_enter(["s1", "s2"])
        plot_id_i = self.current_plot_ids()[0]
        self.view.call_list.clear()
        self.drop_names(plot_id_i, ["s2", "s1"])
        self.assertEqual(self.view.call_list, [])
        self.undo()
        self.assertEqual(self.current_plot_ids(), [])

    @covers("LLFR-00301", "LLFR-00140", "HLFR-00065", "HLFR-00040")
    def test_one_undo_removes_every_dropped_curve(self) -> None:
        """One undo removes all the curves the drop added.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.drop_names(plot_id_i, ["s1", "s2", "s3", "s4"])
        self.assertEqual(len(self.view.drawn_names(plot_id_i)), 4)
        self.undo()
        self.assertEqual(self.view.drawn_names(plot_id_i), ["s1"])

    @covers("LLFR-00297", "LLFR-00022", "LLFR-00023", "HLFR-00065",
            "LLFR-00633")
    def test_drop_on_an_unknown_plot_does_nothing(self) -> None:
        """A drop that is not on a plot creates nothing.

        Inputs: none.
        Outputs: none.
        """
        self.view.call_list.clear()
        self.drop_names(9999, ["s1", "s2"])
        self.assertEqual(self.view.call_list, [])
        self.assertEqual(self.current_plot_ids(), [])

    @covers("LLFR-00021", "LLFR-00297", "HLFR-00013")
    def test_single_name_drop_handler_still_works(self) -> None:
        """A drop of one name is a drop of a list of one.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.drop(plot_id_i, "s2")
        self.drop_names(plot_id_i, ["s3"])
        self.assertEqual(self.view.drawn_names(plot_id_i),
                         ["s1", "s2", "s3"])


class FrequencySelectionTest(FrequencyPlotTestCase):
    """FFT signals in a selection (LLFR-00295, LLFR-00300)."""

    def press_enter(self, signal_name_list: list) -> None:
        """Run the Enter key handler with the selected names.

        Inputs:
            signal_name_list: the selected names, in list order.
        Outputs: none.
        """
        self.view.handler_dict["plot_selection"](signal_name_list)

    def drop_names(self, plot_id_i: int, signal_name_list: list) -> None:
        """Run the handler of a drop of several names.

        Inputs:
            plot_id_i: id of the target plot.
            signal_name_list: the dropped names, in list order.
        Outputs: none.
        """
        self.view.handler_dict["signals_drop_handler"](plot_id_i,
                                                       signal_name_list)

    def two_fft_names(self) -> list:
        """Create two FFT signals and return their names.

        Inputs: none.
        Outputs: the two names, in creation order.
        """
        return [self.create_fft("file1_Speed"),
                self.create_fft("file1_Torque")]

    @covers("LLFR-00295", "LLFR-00256", "HLFR-00064", "HLFR-00058",
            "LLFR-00631")
    def test_enter_with_only_fft_signals_makes_a_frequency_plot(
            self) -> None:
        """Only FFT signals selected give one frequency plot.

        Inputs: none.
        Outputs: none.
        """
        fft_name_list = self.two_fft_names()
        self.press_enter(fft_name_list)
        self.assertEqual(len(self.plot_id_list()), 1)
        plot_id_i = self.last_plot_id()
        self.assertEqual(self.plot(plot_id_i).kind_str,
                         FREQUENCY_PLOT_KIND_STR)
        self.assertEqual(self.view.plot_kind_dict[plot_id_i],
                         FREQUENCY_PLOT_KIND_STR)
        self.assertEqual(self.view.drawn_names(plot_id_i), fft_name_list)
        self.assertEqual(self.view.kind_mismatch_count_i, 0)

    @covers("LLFR-00300", "LLFR-00257", "HLFR-00064", "HLFR-00058",
            "LLFR-00635", "LLFR-00636")
    def test_enter_with_fft_and_time_signals_is_refused(self) -> None:
        """A mixed selection creates no plot and shows the box.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft("file1_Speed")
        self.press_enter(["file1_Speed", fft_name_str])
        self.assertEqual(self.plot_id_list(), [])
        self.assertEqual(self.view.kind_mismatch_count_i, 1)
        self.assertFalse(self.plot_controller.undo_history.can_undo())

    @covers("LLFR-00300", "LLFR-00257", "HLFR-00065", "HLFR-00058",
            "LLFR-00636")
    def test_drop_with_an_fft_signal_on_a_time_plot(self) -> None:
        """A drop holding an FFT signal on a time plot draws nothing.

        Inputs: none.
        Outputs: none.
        """
        fft_name_str = self.create_fft("file1_Speed")
        self.double_click("file1_Time")
        plot_id_i = self.last_plot_id()
        self.drop_names(plot_id_i, ["file1_Speed", fft_name_str,
                                    "file1_Torque"])
        self.assertEqual(self.view.drawn_names(plot_id_i), ["file1_Time"])
        self.assertEqual(self.view.kind_mismatch_count_i, 1)

    @covers("LLFR-00300", "LLFR-00257", "LLFR-00297", "HLFR-00065",
            "HLFR-00058", "LLFR-00636", "LLFR-00691")
    def test_drop_on_a_frequency_plot(self) -> None:
        """FFT signals are added; one time signal blocks the whole drop.

        Inputs: none.
        Outputs: none.
        """
        first_fft_str, second_fft_str = self.two_fft_names()
        self.double_click(first_fft_str)
        plot_id_i = self.last_plot_id()
        self.drop_names(plot_id_i, [second_fft_str, "file1_Speed"])
        self.assertEqual(self.view.drawn_names(plot_id_i), [first_fft_str])
        self.assertEqual(self.view.kind_mismatch_count_i, 1)
        self.drop_names(plot_id_i, [first_fft_str, second_fft_str])
        self.assertEqual(self.view.drawn_names(plot_id_i),
                         [first_fft_str, second_fft_str])
        self.assertEqual(self.view.kind_mismatch_count_i, 1)


class RenameSelectionTest(FrequencyPlotTestCase):
    """A renamed synthetic signal keeps its place in the selection."""

    @covers("LLFR-00292", "LLFR-00266", "HLFR-00063", "LLFR-00602")
    def test_rename_tells_the_view_before_the_list_is_shown(self) -> None:
        """The view renames the shown name, then shows the new list.

        Inputs: none.
        Outputs: none.
        """
        self.create("file1_Speed", "integral")
        self.view.name_answer_list = ["Distance"]
        self.menu("rename", "file1_int_Speed")
        self.assertEqual(self.view.renamed_shown_list,
                         [("file1_int_Speed", "file1_Distance")])
        self.assertEqual(self.view.shown_name_list[-1], "file1_Distance")
        # A rejected rename tells the view nothing.
        self.view.name_answer_list = ["   "]
        self.menu("rename", "file1_Distance")
        self.assertEqual(self.view.renamed_shown_list,
                         [("file1_int_Speed", "file1_Distance")])


class SelectionOnFileOpenTest(unittest.TestCase):
    """Opening another data file keeps the selection (LLFR-00292)."""

    @covers("LLFR-00292", "LLFR-00921", "HLFR-00063")
    def test_opening_a_file_keeps_the_selection(self) -> None:
        """An added file keeps the signals shown, so they stay selected.

        Inputs: none.
        Outputs: none.
        """
        view = FakeSignalListView()
        file_controller = FakeFileController()
        SignalListController(view, file_controller)
        file_controller.open(make_signal_file(2), None)
        file_controller.open(make_signal_file(2), None)
        self.assertEqual(view.selection_clear_count_i, 0)


if __name__ == "__main__":
    unittest.main()
