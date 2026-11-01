"""Tests for the zoom reset and the grid in the plot controller.

The fake view of test_plot_controller records every call; no Qt is
needed (HLFR-00035, HLFR-00037).
"""

import unittest

import numpy as np

from tests.support import covers

from controller.plot_controller import PlotController
from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR)
from model.signal_file import SignalFile
from tests.controller.test_plot_controller import (
    FakeFileController, FakePlotView, PlotControllerTestCase,
    make_signal_file)


class ResetZoomControllerTest(PlotControllerTestCase):
    """Reset zoom sets the whole file range in every plot of every tab."""

    def reset_zoom(self) -> None:
        """Run the Reset zoom handler as the button does.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["reset_zoom"]()

    def zoom_tab(self, tab_id_i: int, start_s: float, end_s: float) -> None:
        """Zoom the first plot of a tab as the view would report it.

        Inputs:
            tab_id_i: id of the tab.
            start_s: start of the range, in seconds.
            end_s: end of the range, in seconds.
        Outputs: none. The controller shares the range with every plot.
        """
        plot_id_i = self.workspace.find_tab(tab_id_i).plot_list[0].plot_id_i
        self.view.set_plot_time_range(plot_id_i, start_s, end_s)
        self.view.handler_dict["time_range_handler"](plot_id_i, start_s,
                                                     end_s)

    @covers("LLFR-00115", "LLFR-00070")
    def test_reset_sets_the_file_range_on_every_plot_of_the_tab(
            self) -> None:
        """Every plot of the current tab gets the whole time range.

        Inputs: none.
        Outputs: none.
        """
        for signal_name_str in ("s1", "s2", "s3"):
            self.double_click(signal_name_str)
        tab_id_i = self.first_tab_id()
        self.zoom_tab(tab_id_i, 2.0, 3.5)
        self.view.call_list.clear()
        self.reset_zoom()
        plot_id_list = self.current_plot_ids()
        self.assertEqual(len(plot_id_list), 3)
        for plot_id_i in plot_id_list:
            self.assertEqual(self.view.range_dict[plot_id_i], (0.0, 10.0))
        # Only time ranges were set: no plot was redrawn, created or
        # deleted, and the tab layout did not change.
        self.assertEqual(self.view.method_names(),
                         ["set_plot_time_range"] * 3)

    @covers("LLFR-00115", "LLFR-00070", "LLFR-00180")
    def test_reset_applies_to_every_tab(self) -> None:
        """Plots of the tabs that are not shown are reset too.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        first_tab_id_i = self.first_tab_id()
        self.view.handler_dict["add_tab"]()
        second_tab_id_i = self.view.current_tab_id()
        self.double_click("s2")
        self.double_click("s3")
        self.zoom_tab(second_tab_id_i, 4.0, 6.0)
        for tab_id_i in (first_tab_id_i, second_tab_id_i):
            for plot in self.workspace.find_tab(tab_id_i).plot_list:
                self.assertEqual(self.view.range_dict[plot.plot_id_i],
                                 (4.0, 6.0))
        self.reset_zoom()
        for tab_id_i in (first_tab_id_i, second_tab_id_i):
            for plot in self.workspace.find_tab(tab_id_i).plot_list:
                self.assertEqual(self.view.range_dict[plot.plot_id_i],
                                 (0.0, 10.0))
        # A plot created after the reset starts at the whole range.
        self.assertEqual(self.controller.shared_time_range_tuple, ())
        self.view.set_current_tab(first_tab_id_i)
        self.view.call_list.clear()
        self.double_click("s4")
        self.assertNotIn("set_plot_time_range", self.view.method_names())

    @covers("LLFR-00115")
    def test_reset_uses_first_and_last_time_sample(self) -> None:
        """The range runs from the smallest to the largest time sample.

        Inputs: none.
        Outputs: none.
        """
        time_array = np.array([-2.5, -1.0, 0.0, 4.0, 7.25])
        signal_file = SignalFile("shifted.csv", {
            "Time": time_array, "speed": time_array * 3.0})
        self.file_controller.open(signal_file, True)
        self.double_click("speed")
        plot_id_i = self.current_plot_ids()[0]
        self.view.range_dict[plot_id_i] = (0.0, 1.0)
        self.reset_zoom()
        self.assertEqual(self.view.range_dict[plot_id_i], (-2.5, 7.25))

    @covers("LLFR-00115")
    def test_reset_without_plots_or_file_does_nothing(self) -> None:
        """An empty tab, or no open file, gives no call and no error.

        Inputs: none.
        Outputs: none.
        """
        self.view.call_list.clear()
        self.reset_zoom()
        self.assertEqual(self.view.call_list, [])
        view = FakePlotView()
        PlotController(view, FakeFileController())
        view.call_list.clear()
        view.handler_dict["reset_zoom"]()
        self.assertEqual(view.call_list, [])

    @covers("LLFR-00115")
    def test_reset_does_not_depend_on_the_current_tab(self) -> None:
        """A stale current tab id still resets every plot (PCR-00025).

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.zoom_tab(self.first_tab_id(), 2.0, 3.0)
        self.view.current_tab_id_i = 9999
        self.view.call_list.clear()
        self.reset_zoom()
        self.assertEqual(self.view.call_list,
                         [("set_plot_time_range", plot_id_i, 0.0, 10.0)])

    @covers("LLFR-00115", "LLFR-00109")
    def test_reset_keeps_the_plot_tool(self) -> None:
        """Reset zoom is not a plot tool: the active tool stays.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        for tool_str in (TIP_TOOL_STR, ZOOM_TOOL_STR, MARKER_TOOL_STR,
                         NO_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.view.handler_dict["plot_tool"](tool_str)
                self.view.call_list.clear()
                self.reset_zoom()
                self.assertNotIn("set_plot_tool", self.view.method_names())
                self.assertEqual(self.controller.plot_tool_str, tool_str)


class GridControllerTest(PlotControllerTestCase):
    """The Grid button state is kept by the controller."""

    def click_grid(self, shown_b: bool) -> None:
        """Run the Grid handler as the button does.

        Inputs:
            shown_b: True when the click shows the grid.
        Outputs: none.
        """
        self.view.handler_dict["grid"](shown_b)

    @covers("LLFR-00147")
    def test_grid_is_hidden_at_start(self) -> None:
        """A new controller tells the view to hide the grid.

        Inputs: none.
        Outputs: none.
        """
        view = FakePlotView()
        controller = PlotController(view, FakeFileController())
        self.assertFalse(controller.grid_shown_b)
        self.assertIs(view.grid_shown_b, False)
        self.assertIn(("set_grid_shown", False), view.call_list)

    @covers("LLFR-00122", "LLFR-00123", "LLFR-00124")
    def test_grid_clicks_show_and_hide_the_grid(self) -> None:
        """Each click is passed to the view and kept by the controller.

        Inputs: none.
        Outputs: none.
        """
        for shown_b in (True, False, True, False):
            self.click_grid(shown_b)
            self.assertEqual(self.controller.grid_shown_b, shown_b)
            self.assertEqual(self.view.grid_shown_b, shown_b)
            self.assertEqual(self.view.call_list[-1],
                             ("set_grid_shown", shown_b))

    @covers("LLFR-00124", "LLFR-00079")
    def test_grid_and_plot_tools_are_independent(self) -> None:
        """Plot tool changes keep the grid; grid clicks keep the tool.

        Inputs: none.
        Outputs: none.
        """
        self.click_grid(True)
        self.view.call_list.clear()
        for tool_str in (TIP_TOOL_STR, ZOOM_TOOL_STR, MARKER_TOOL_STR,
                         NO_TOOL_STR):
            self.view.handler_dict["plot_tool"](tool_str)
            self.assertTrue(self.controller.grid_shown_b)
        self.assertNotIn("set_grid_shown", self.view.method_names())
        self.view.handler_dict["plot_tool"](ZOOM_TOOL_STR)
        self.view.call_list.clear()
        self.click_grid(False)
        self.assertEqual(self.controller.plot_tool_str, ZOOM_TOOL_STR)
        self.assertNotIn("set_plot_tool", self.view.method_names())

    @covers("LLFR-00125", "LLFR-00147")
    def test_grid_choice_is_kept_when_a_file_replaces_another(
            self) -> None:
        """Opening another file does not reset the grid choice.

        Inputs: none.
        Outputs: none.
        """
        self.click_grid(True)
        self.view.call_list.clear()
        self.file_controller.open(make_signal_file(2), True)
        self.assertTrue(self.controller.grid_shown_b)
        self.assertNotIn(("set_grid_shown", False), self.view.call_list)
        self.assertTrue(self.view.grid_shown_b)


if __name__ == "__main__":
    unittest.main()
