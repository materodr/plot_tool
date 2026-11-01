"""Tests for the plot controller with a fake view (no Qt needed).

A real Workspace and a SignalFile built in the test are used; the fake
view records every call the controller makes.
"""

import random
import unittest

import numpy as np

from tests.support import covers

from controller.plot_controller import PlotController
from model.curve_colors import PALETTE_COLOR_TUPLE
from model.signal_file import SignalFile
from model.workspace import DEFAULT_WIDTH_I, Workspace


class FakeFileController:
    """Stand-in for FileController that keeps the listeners."""

    def __init__(self) -> None:
        """Start with no listeners.

        Inputs: none.
        Outputs: none.
        """
        self.listener_list = []

    def add_file_opened_listener(self, listener) -> None:
        """Record a file-opened listener.

        Inputs:
            listener: function taking (signal_file, replaced_b).
        Outputs: none.
        """
        self.listener_list.append(listener)

    def open(self, signal_file, replaced_b: bool) -> None:
        """Call every listener as the real controller does.

        Inputs:
            signal_file: the SignalFile to report as opened.
            replaced_b: True when it replaces another file.
        Outputs: none.
        """
        for listener in self.listener_list:
            listener(signal_file, replaced_b)


class FakePlotView:
    """Stand-in for MainWindow that records the plot-panel calls.

    Attributes:
        call_list: every call as a tuple (method name, arguments...).
        tab_dict: shown tab id -> name, in order.
        current_tab_id_i: the selected tab id.
        plot_tab_dict: shown plot id -> tab id.
        drawn_dict: plot id -> (curve_data_list, pinned_tip_list) of
            the last draw_plot call.
        range_dict: plot id -> (start_s, end_s) shown.
        delete_enabled_b: last value given to set_tab_delete_enabled.
        full_tab_count_i: how many Full Tab boxes were shown.
        tab_name_taken_list: names given to
            show_tab_name_taken_notification, in order.
        plot_tool_str: last value given to set_plot_tool.
        marker_drawn_dict: plot id -> marker_data_list of the last
            draw_plot or set_markers call.
        marker_name_answer_list: answers returned, in order, by
            ask_marker_name (None stands for a cancelled dialog).
        marker_name_question_list: the current names given to
            ask_marker_name.
        grid_shown_b: last value given to set_grid_shown.
        undo_enabled_b: last value given to set_undo_enabled.
        redo_enabled_b: last value given to set_redo_enabled.
        delta_drawn_dict: plot id -> delta_marker_data_list of the last
            draw_plot call.
        delta_first_point_dict: plot id -> point tuple last given to
            set_delta_first_point (() when the dot was removed).
    """

    def __init__(self) -> None:
        """Start with no tabs and no handlers.

        Inputs: none.
        Outputs: none.
        """
        self.call_list = []
        self.tab_dict = {}
        self.current_tab_id_i = -1
        self.plot_tab_dict = {}
        self.drawn_dict = {}
        self.range_dict = {}
        self.delete_enabled_b = True
        self.full_tab_count_i = 0
        self.tab_name_taken_list = []
        self.plot_tool_str = ""
        self.handler_dict = {}
        self.marker_drawn_dict = {}
        self.marker_name_answer_list = []
        self.marker_name_question_list = []
        self.grid_shown_b = None
        self.undo_enabled_b = None
        self.redo_enabled_b = None
        self.delta_drawn_dict = {}
        self.delta_first_point_dict = {}

    def set_signal_double_click_handler(self, handler) -> None:
        """Record the double-click handler.

        Inputs:
            handler: function taking a signal name.
        Outputs: none.
        """
        self.handler_dict["double_click"] = handler

    def set_plot_tool_handler(self, handler) -> None:
        """Record the plot tool handler.

        Inputs:
            handler: function taking a plot tool name.
        Outputs: none.
        """
        self.handler_dict["plot_tool"] = handler

    def set_tab_handlers(self, add_tab_handler, delete_tab_handler,
                         rename_tab_handler) -> None:
        """Record the tab handlers.

        Inputs:
            add_tab_handler: function without arguments.
            delete_tab_handler: function taking a tab id.
            rename_tab_handler: function taking a tab id and a name.
        Outputs: none.
        """
        self.handler_dict["add_tab"] = add_tab_handler
        self.handler_dict["delete_tab"] = delete_tab_handler
        self.handler_dict["rename_tab"] = rename_tab_handler

    def set_plot_handlers(self, **handler_dict) -> None:
        """Record the plot handlers.

        Inputs:
            handler_dict: handler name -> function.
        Outputs: none.
        """
        self.handler_dict.update(handler_dict)

    def set_reset_zoom_handler(self, handler) -> None:
        """Record the Reset zoom handler.

        Inputs:
            handler: function without arguments.
        Outputs: none.
        """
        self.handler_dict["reset_zoom"] = handler

    def set_grid_handler(self, handler) -> None:
        """Record the Grid button handler.

        Inputs:
            handler: function taking True or False.
        Outputs: none.
        """
        self.handler_dict["grid"] = handler

    def set_undo_handler(self, handler) -> None:
        """Record the Undo button and shortcut handler.

        Inputs:
            handler: function without arguments.
        Outputs: none.
        """
        self.handler_dict["undo"] = handler

    def set_undo_enabled(self, enabled_b: bool) -> None:
        """Record whether the Undo button is enabled.

        Not added to call_list, so that tests of the call order of other
        actions are not affected.

        Inputs:
            enabled_b: True when an action can be undone.
        Outputs: none.
        """
        self.undo_enabled_b = enabled_b

    def set_redo_handler(self, handler) -> None:
        """Record the Redo button and shortcut handler.

        Inputs:
            handler: function without arguments.
        Outputs: none.
        """
        self.handler_dict["redo"] = handler

    def set_redo_enabled(self, enabled_b: bool) -> None:
        """Record whether the Redo button is enabled.

        Not added to call_list, like set_undo_enabled.

        Inputs:
            enabled_b: True when an undone action can be redone.
        Outputs: none.
        """
        self.redo_enabled_b = enabled_b

    def set_grid_shown(self, shown_b: bool) -> None:
        """Record whether the grid is shown.

        Inputs:
            shown_b: True when the grid is shown.
        Outputs: none.
        """
        self.call_list.append(("set_grid_shown", shown_b))
        self.grid_shown_b = shown_b

    def clear_tab_views(self) -> None:
        """Remove every tab and plot.

        Inputs: none.
        Outputs: none.
        """
        self.call_list.append(("clear_tab_views",))
        self.tab_dict = {}
        self.plot_tab_dict = {}
        self.drawn_dict = {}
        self.range_dict = {}

    def add_tab_view(self, tab_id_i: int, name_str: str) -> None:
        """Add a tab.

        Inputs:
            tab_id_i: id of the tab.
            name_str: name of the tab.
        Outputs: none.
        """
        self.call_list.append(("add_tab_view", tab_id_i, name_str))
        self.tab_dict[tab_id_i] = name_str

    def remove_tab_view(self, tab_id_i: int) -> None:
        """Remove a tab and its plots.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: none.
        """
        self.call_list.append(("remove_tab_view", tab_id_i))
        del self.tab_dict[tab_id_i]
        for plot_id_i in [plot_id_i for plot_id_i, owner_i
                          in self.plot_tab_dict.items()
                          if owner_i == tab_id_i]:
            del self.plot_tab_dict[plot_id_i]
        if self.current_tab_id_i == tab_id_i:
            self.current_tab_id_i = next(iter(self.tab_dict))

    def rename_tab_view(self, tab_id_i: int, name_str: str) -> None:
        """Rename a tab.

        Inputs:
            tab_id_i: id of the tab.
            name_str: new name.
        Outputs: none.
        """
        self.call_list.append(("rename_tab_view", tab_id_i, name_str))
        self.tab_dict[tab_id_i] = name_str

    def set_current_tab(self, tab_id_i: int) -> None:
        """Select a tab.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: none.
        """
        self.call_list.append(("set_current_tab", tab_id_i))
        self.current_tab_id_i = tab_id_i

    def current_tab_id(self) -> int:
        """Return the selected tab id.

        Inputs: none.
        Outputs: the id.
        """
        return self.current_tab_id_i

    def set_tab_delete_enabled(self, enabled_b: bool) -> None:
        """Record whether the tab menu's Delete is enabled.

        Inputs:
            enabled_b: the new state.
        Outputs: none.
        """
        self.delete_enabled_b = enabled_b

    def add_plot_view(self, tab_id_i: int, plot_id_i: int) -> None:
        """Add a plot at the bottom of a tab.

        Inputs:
            tab_id_i: id of the tab.
            plot_id_i: id of the plot.
        Outputs: none.
        """
        self.call_list.append(("add_plot_view", tab_id_i, plot_id_i))
        self.plot_tab_dict[plot_id_i] = tab_id_i
        self.range_dict[plot_id_i] = (0.0, 1.0)

    def remove_plot_view(self, plot_id_i: int) -> None:
        """Remove a plot.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: none.
        """
        self.call_list.append(("remove_plot_view", plot_id_i))
        del self.plot_tab_dict[plot_id_i]

    def draw_plot(self, plot_id_i: int, curve_data_list: list,
                  pinned_tip_list: list, marker_data_list=(),
                  delta_marker_data_list=()) -> None:
        """Record what a plot draws; resets its range like PlotWidget.

        Inputs:
            plot_id_i: id of the plot.
            curve_data_list: the curve tuples.
            pinned_tip_list: the pinned tip tuples.
            marker_data_list: the vertical marker tuples (marker_id_i,
                name_str, time_s).
            delta_marker_data_list: the delta marker tuples
                (delta_marker_id_i, kind_str, first_point_tuple,
                second_point_tuple, delta_f).
        Outputs: none.
        """
        self.call_list.append(("draw_plot", plot_id_i))
        self.delta_drawn_dict[plot_id_i] = list(delta_marker_data_list)
        self.drawn_dict[plot_id_i] = (curve_data_list, pinned_tip_list)
        self.marker_drawn_dict[plot_id_i] = list(marker_data_list)
        if curve_data_list:
            time_array = curve_data_list[0][1]
            self.range_dict[plot_id_i] = (float(time_array[0]),
                                          float(time_array[-1]))

    def set_markers(self, marker_data_list: list) -> None:
        """Record the shared markers drawn on every shown plot.

        Inputs:
            marker_data_list: the vertical marker tuples (marker_id_i,
                name_str, time_s).
        Outputs: none.
        """
        self.call_list.append(("set_markers", len(marker_data_list)))
        for plot_id_i in self.plot_tab_dict:
            self.marker_drawn_dict[plot_id_i] = list(marker_data_list)

    def set_plot_time_range(self, plot_id_i: int, start_s: float,
                            end_s: float) -> None:
        """Set the time range of a plot.

        Inputs:
            plot_id_i: id of the plot.
            start_s: start in seconds.
            end_s: end in seconds.
        Outputs: none.
        """
        self.call_list.append(("set_plot_time_range", plot_id_i, start_s,
                               end_s))
        self.range_dict[plot_id_i] = (start_s, end_s)

    def plot_time_range(self, plot_id_i: int) -> tuple:
        """Return the time range of a plot.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: (start_s, end_s).
        """
        return self.range_dict[plot_id_i]

    def set_plot_tool(self, tool_str: str) -> None:
        """Record the plot tool.

        Inputs:
            tool_str: the new plot tool name.
        Outputs: none.
        """
        self.call_list.append(("set_plot_tool", tool_str))
        self.plot_tool_str = tool_str

    def set_delta_first_point(self, plot_id_i: int,
                              point_tuple: tuple) -> None:
        """Record the dot of a delta marker's first point.

        Inputs:
            plot_id_i: id of the plot.
            point_tuple: (signal_name_str, time_s, value_f), or () to
                remove the dot.
        Outputs: none.
        """
        self.call_list.append(("set_delta_first_point", plot_id_i,
                               tuple(point_tuple)))
        self.delta_first_point_dict[plot_id_i] = tuple(point_tuple)

    def show_full_tab_notification(self) -> None:
        """Count a Full Tab box.

        Inputs: none.
        Outputs: none.
        """
        self.call_list.append(("show_full_tab_notification",))
        self.full_tab_count_i += 1

    def show_tab_name_taken_notification(self, name_str: str) -> None:
        """Record a Tab Name Taken box.

        Inputs:
            name_str: the name the box says is taken.
        Outputs: none.
        """
        self.call_list.append(("show_tab_name_taken_notification",
                               name_str))
        self.tab_name_taken_list.append(name_str)

    def ask_marker_name(self, current_name_str: str):
        """Answer a marker name question with the next prepared answer.

        Inputs:
            current_name_str: the name the dialog would start with.
        Outputs: the next answer of marker_name_answer_list, or None
            (cancelled) when there is none.
        """
        self.call_list.append(("ask_marker_name", current_name_str))
        self.marker_name_question_list.append(current_name_str)
        if not self.marker_name_answer_list:
            return None
        return self.marker_name_answer_list.pop(0)

    def plot_id_list(self, tab_id_i: int) -> list:
        """Return the shown plots of a tab, in creation order.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: a list of plot ids.
        """
        return [plot_id_i for plot_id_i, owner_i
                in self.plot_tab_dict.items() if owner_i == tab_id_i]

    def drawn_names(self, plot_id_i: int) -> list:
        """Return the signal names last drawn in a plot.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: a list of names in curve order.
        """
        return [curve_tuple[0]
                for curve_tuple in self.drawn_dict[plot_id_i][0]]

    def method_names(self) -> list:
        """Return the names of the recorded calls.

        Inputs: none.
        Outputs: a list of method names.
        """
        return [call_tuple[0] for call_tuple in self.call_list]


def make_signal_file(signal_count_i: int = 3) -> SignalFile:
    """Build a SignalFile with Time and some signals.

    Inputs:
        signal_count_i: how many signals besides Time.
    Outputs: the SignalFile; signal "s<k>" has the values k * Time.
    """
    time_array = np.linspace(0.0, 10.0, 11)
    signal_dict = {"Time": time_array}
    for index_i in range(1, signal_count_i + 1):
        signal_dict[f"s{index_i}"] = time_array * index_i
    return SignalFile("test.csv", signal_dict)


class PlotControllerTestCase(unittest.TestCase):
    """Shared setup: a controller with an opened file."""

    def setUp(self) -> None:
        """Create the fake view, the controller and open a file.

        Inputs: none.
        Outputs: none.
        """
        self.view = FakePlotView()
        self.file_controller = FakeFileController()
        self.workspace = Workspace(random.Random(5))
        self.controller = PlotController(self.view, self.file_controller,
                                         self.workspace)
        self.signal_file = make_signal_file(10)
        self.file_controller.open(self.signal_file, False)

    def first_tab_id(self) -> int:
        """Return the id of the first tab of the workspace.

        Inputs: none.
        Outputs: the tab id.
        """
        return self.workspace.tab_list[0].tab_id_i

    def double_click(self, signal_name_str: str) -> None:
        """Run the double-click handler.

        Inputs:
            signal_name_str: the signal name.
        Outputs: none.
        """
        self.view.handler_dict["double_click"](signal_name_str)

    def drop(self, plot_id_i: int, signal_name_str: str) -> None:
        """Run the drop handler.

        Inputs:
            plot_id_i: id of the target plot.
            signal_name_str: the signal name.
        Outputs: none.
        """
        self.view.handler_dict["signal_drop_handler"](plot_id_i,
                                                      signal_name_str)

    def current_plot_ids(self) -> list:
        """Return the plot ids of the current tab, top to bottom.

        Inputs: none.
        Outputs: a list of ids from the model.
        """
        tab = self.workspace.find_tab(self.view.current_tab_id())
        return [plot.plot_id_i for plot in tab.plot_list]


class StartAndFileTest(PlotControllerTestCase):
    """Starting the controller and opening files."""

    @covers("LLFR-00024", "LLFR-00066", "HLFR-00014")
    def test_start_shows_one_tab_with_delete_disabled(self) -> None:
        """A new controller shows one tab "Tab 1"; Delete is disabled.

        Inputs: none.
        Outputs: none.
        """
        view = FakePlotView()
        PlotController(view, FakeFileController())
        self.assertEqual(list(view.tab_dict.values()), ["Tab 1"])
        self.assertEqual(view.current_tab_id_i, next(iter(view.tab_dict)))
        self.assertFalse(view.delete_enabled_b)

    @covers("LLFR-00015", "LLFR-00016", "HLFR-00010")
    def test_new_file_closes_tabs_and_plots(self) -> None:
        """A replaced file leaves one empty tab and no plots.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        self.view.handler_dict["add_tab"]()
        self.double_click("s2")
        self.view.handler_dict["rename_tab"](self.view.current_tab_id(),
                                             "Mine")
        self.assertEqual(len(self.view.plot_tab_dict), 2)
        new_file = make_signal_file(1)
        self.file_controller.open(new_file, True)
        self.assertEqual(list(self.view.tab_dict.values()), ["Tab 1"])
        self.assertEqual(self.view.plot_tab_dict, {})
        self.assertEqual(len(self.workspace.tab_list), 1)
        self.assertEqual(self.workspace.tab_list[0].plot_list, [])
        self.assertFalse(self.view.delete_enabled_b)
        self.assertIs(self.controller.signal_file, new_file)
        self.assertIn(self.view.current_tab_id(), self.view.tab_dict)

    @covers("LLFR-00015", "LLFR-00016")
    def test_old_plot_ids_are_ignored_after_replace(self) -> None:
        """Requests for plots of the previous file do nothing.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        old_plot_id_i = self.current_plot_ids()[0]
        self.file_controller.open(make_signal_file(2), True)
        call_count_i = len(self.view.call_list)
        self.drop(old_plot_id_i, "s2")
        self.view.handler_dict["curve_delete_handler"](old_plot_id_i, "s1")
        self.view.handler_dict["plot_delete_handler"](old_plot_id_i)
        self.assertEqual(len(self.view.call_list), call_count_i)

    @covers("LLFR-00019")
    def test_double_click_without_file_does_nothing(self) -> None:
        """Before any file is open, a double-click creates no plot.

        Inputs: none.
        Outputs: none.
        """
        view = FakePlotView()
        PlotController(view, FakeFileController())
        view.handler_dict["double_click"]("s1")
        self.assertEqual(view.plot_tab_dict, {})
        self.assertNotIn("add_plot_view", view.method_names())


class DoubleClickTest(PlotControllerTestCase):
    """Double-click creates a plot (HLFR-00012)."""

    @covers("LLFR-00019", "LLFR-00020", "LLFR-00068", "LLFR-00052",
            "LLFR-00033", "HLFR-00012")
    def test_double_click_creates_plot_with_signal(self) -> None:
        """A double-click adds a plot in the current tab and draws it.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s2")
        plot_id_list = self.view.plot_id_list(self.first_tab_id())
        self.assertEqual(len(plot_id_list), 1)
        self.assertEqual(plot_id_list, self.current_plot_ids())
        curve_data_list, pinned_tip_list = self.view.drawn_dict[
            plot_id_list[0]]
        self.assertEqual(len(curve_data_list), 1)
        name_str, time_array, value_array, color_str, width_i = (
            curve_data_list[0])
        self.assertEqual(name_str, "s2")
        np.testing.assert_array_equal(time_array,
                                      self.signal_file.time_array)
        np.testing.assert_array_equal(value_array,
                                      self.signal_file.signal_array("s2"))
        self.assertEqual(color_str, PALETTE_COLOR_TUPLE[0])
        self.assertEqual(width_i, DEFAULT_WIDTH_I)
        self.assertEqual(width_i, 1)
        self.assertEqual(pinned_tip_list, [])

    @covers("LLFR-00055", "LLFR-00068", "HLFR-00012")
    def test_time_signal_can_be_plotted(self) -> None:
        """Time is plotted like any other signal, against time.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("Time")
        plot_id_i = self.current_plot_ids()[0]
        self.assertEqual(self.view.drawn_names(plot_id_i), ["Time"])
        _, time_array, value_array, _, _ = self.view.drawn_dict[
            plot_id_i][0][0]
        np.testing.assert_array_equal(time_array, value_array)

    @covers("LLFR-00019", "LLFR-00069")
    def test_plots_go_in_order_into_current_tab(self) -> None:
        """Each double-click adds a plot below, in the current tab.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        self.view.handler_dict["add_tab"]()
        second_tab_id_i = self.view.current_tab_id()
        self.double_click("s2")
        self.double_click("s3")
        self.assertEqual(len(self.view.plot_id_list(self.first_tab_id())),
                         1)
        second_plot_list = self.view.plot_id_list(second_tab_id_i)
        self.assertEqual(second_plot_list, self.current_plot_ids())
        self.assertEqual([self.view.drawn_names(plot_id_i)
                          for plot_id_i in second_plot_list],
                         [["s2"], ["s3"]])

    @covers("LLFR-00019")
    def test_unknown_signal_name_is_ignored(self) -> None:
        """A name that is not in the file creates no plot.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("missing")
        self.double_click("time")
        self.assertEqual(self.view.plot_tab_dict, {})

    @covers("LLFR-00031", "LLFR-00032", "HLFR-00018")
    def test_full_tab_blocks_sixth_plot_and_notifies(self) -> None:
        """The 6th double-click shows the Full Tab box and adds nothing.

        Inputs: none.
        Outputs: none.
        """
        for index_i in range(1, 6):
            self.double_click(f"s{index_i}")
        self.assertEqual(self.view.full_tab_count_i, 0)
        call_count_i = len(self.view.call_list)
        self.double_click("s6")
        self.assertEqual(len(self.view.plot_id_list(self.first_tab_id())),
                         5)
        self.assertEqual(len(self.current_plot_ids()), 5)
        self.assertEqual(self.view.full_tab_count_i, 1)
        self.assertEqual(self.view.method_names()[call_count_i:],
                         ["show_full_tab_notification"])

    @covers("LLFR-00031", "LLFR-00032", "HLFR-00018")
    def test_deleting_a_plot_frees_a_place(self) -> None:
        """After deleting a plot of a full tab, a new one fits.

        Inputs: none.
        Outputs: none.
        """
        for index_i in range(1, 6):
            self.double_click(f"s{index_i}")
        self.view.handler_dict["plot_delete_handler"](
            self.current_plot_ids()[0])
        self.double_click("s6")
        self.assertEqual(self.view.full_tab_count_i, 0)
        self.assertEqual(len(self.current_plot_ids()), 5)

    @covers("LLFR-00070", "LLFR-00180", "LLFR-00019")
    def test_new_plot_takes_the_shared_time_range(self) -> None:
        """A new plot in a tab with plots gets their time range.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        first_plot_id_i = self.current_plot_ids()[0]
        self.view.set_plot_time_range(first_plot_id_i, 2.0, 4.0)
        self.view.handler_dict["time_range_handler"](first_plot_id_i,
                                                     2.0, 4.0)
        self.double_click("s2")
        second_plot_id_i = self.current_plot_ids()[1]
        self.assertEqual(self.view.range_dict[second_plot_id_i],
                         (2.0, 4.0))

    @covers("LLFR-00070", "LLFR-00180", "HLFR-00014")
    def test_new_plot_in_another_tab_takes_the_shared_range(self) -> None:
        """A plot created in a new tab shows the range zoomed elsewhere.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        first_plot_id_i = self.current_plot_ids()[0]
        self.view.handler_dict["time_range_handler"](first_plot_id_i,
                                                     1.5, 3.0)
        self.view.handler_dict["add_tab"]()
        self.double_click("s2")
        new_plot_id_i = self.current_plot_ids()[0]
        self.assertEqual(self.view.range_dict[new_plot_id_i], (1.5, 3.0))
        self.assertEqual(self.controller.shared_time_range_tuple,
                         (1.5, 3.0))

    @covers("LLFR-00070", "LLFR-00180")
    def test_first_plot_keeps_full_range(self) -> None:
        """The first plot of the workspace shows the whole time range.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.assertNotIn("set_plot_time_range", self.view.method_names())
        self.assertEqual(self.view.range_dict[plot_id_i], (0.0, 10.0))

    @covers("LLFR-00180", "LLFR-00049")
    def test_plot_after_deleting_every_plot_shows_whole_range(
            self) -> None:
        """Once every plot is gone, the next plot starts unzoomed.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        self.double_click("s2")
        first_plot_id_i, second_plot_id_i = self.current_plot_ids()
        self.view.handler_dict["time_range_handler"](first_plot_id_i,
                                                     2.0, 3.0)
        self.view.handler_dict["plot_delete_handler"](first_plot_id_i)
        # One plot is still there: the shared range is kept.
        self.assertEqual(self.controller.shared_time_range_tuple,
                         (2.0, 3.0))
        self.view.handler_dict["plot_delete_handler"](second_plot_id_i)
        self.assertEqual(self.controller.shared_time_range_tuple, ())
        self.view.call_list.clear()
        self.double_click("s3")
        new_plot_id_i = self.current_plot_ids()[0]
        self.assertNotIn("set_plot_time_range", self.view.method_names())
        self.assertEqual(self.view.range_dict[new_plot_id_i], (0.0, 10.0))

    @covers("LLFR-00180", "LLFR-00051", "LLFR-00028")
    def test_last_plot_removed_by_curve_or_tab_resets_range(self) -> None:
        """Removing the last curve, or the last tab with plots, also resets.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.view.handler_dict["time_range_handler"](plot_id_i, 2.0, 3.0)
        self.view.handler_dict["curve_delete_handler"](plot_id_i, "s1")
        self.assertEqual(self.controller.shared_time_range_tuple, ())
        # A tab that holds the only plot is deleted.
        self.view.handler_dict["add_tab"]()
        second_tab_id_i = self.view.current_tab_id()
        self.double_click("s2")
        plot_id_i = self.current_plot_ids()[0]
        self.view.handler_dict["time_range_handler"](plot_id_i, 4.0, 5.0)
        self.view.handler_dict["delete_tab"](second_tab_id_i)
        self.assertEqual(self.controller.shared_time_range_tuple, ())
        self.double_click("s3")
        self.assertEqual(
            self.view.range_dict[self.current_plot_ids()[0]], (0.0, 10.0))

    @covers("LLFR-00180", "LLFR-00015")
    def test_file_replace_resets_the_shared_range(self) -> None:
        """A newly opened file starts with the whole time range.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.view.handler_dict["time_range_handler"](plot_id_i, 2.0, 3.0)
        self.file_controller.open(make_signal_file(3), True)
        self.assertEqual(self.controller.shared_time_range_tuple, ())
        self.view.call_list.clear()
        self.double_click("s1")
        self.assertNotIn("set_plot_time_range", self.view.method_names())
        self.assertEqual(
            self.view.range_dict[self.current_plot_ids()[0]], (0.0, 10.0))


class DropTest(PlotControllerTestCase):
    """Dropping a signal on a plot (HLFR-00013)."""

    @covers("LLFR-00021", "LLFR-00034", "HLFR-00013", "HLFR-00020")
    def test_drop_adds_curve_with_new_color(self) -> None:
        """A dropped signal is drawn in that plot in a new color.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.drop(plot_id_i, "s2")
        self.assertEqual(self.view.drawn_names(plot_id_i), ["s1", "s2"])
        for index_i in range(3, 11):
            self.drop(plot_id_i, f"s{index_i}")
        self.drop(plot_id_i, "Time")
        curve_data_list = self.view.drawn_dict[plot_id_i][0]
        color_list = [curve_tuple[3] for curve_tuple in curve_data_list]
        self.assertEqual(len(color_list), 11)
        self.assertEqual(len(set(color_list)), 11)
        self.assertEqual(color_list[:8], list(PALETTE_COLOR_TUPLE))
        for color_str in color_list[8:]:
            self.assertNotIn(color_str, PALETTE_COLOR_TUPLE)

    @covers("LLFR-00055", "LLFR-00021")
    def test_drop_time_signal(self) -> None:
        """Time can be dropped on a plot like any other signal.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.drop(plot_id_i, "Time")
        self.assertEqual(self.view.drawn_names(plot_id_i), ["s1", "Time"])

    @covers("LLFR-00056", "LLFR-00057", "HLFR-00013")
    def test_duplicate_drop_does_nothing(self) -> None:
        """Dropping a signal already in the plot makes no call at all.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.drop(plot_id_i, "s2")
        call_count_i = len(self.view.call_list)
        self.drop(plot_id_i, "s2")
        self.drop(plot_id_i, "s1")
        self.assertEqual(len(self.view.call_list), call_count_i)
        self.assertEqual(self.view.full_tab_count_i, 0)
        self.assertEqual(len(self.workspace.find_plot(plot_id_i)
                             .curve_list), 2)

    @covers("LLFR-00022", "LLFR-00023")
    def test_drop_without_a_known_plot_does_nothing(self) -> None:
        """A drop with no valid plot id creates nothing and shows nothing.

        The view only reports drops made on a plot widget, so the only
        way a drop reaches the controller is with a plot id; an unknown
        id must not create a plot or a message.

        Inputs: none.
        Outputs: none.
        """
        call_count_i = len(self.view.call_list)
        for plot_id_i in (-1, 0, 999):
            self.drop(plot_id_i, "s1")
        self.assertEqual(len(self.view.call_list), call_count_i)
        self.assertEqual(self.current_plot_ids(), [])
        self.assertEqual(self.view.full_tab_count_i, 0)

    @covers("LLFR-00022", "LLFR-00023")
    def test_drop_on_full_tab_plot_shows_no_message(self) -> None:
        """A drop never creates a plot, even when the tab is full.

        Inputs: none.
        Outputs: none.
        """
        for index_i in range(1, 6):
            self.double_click(f"s{index_i}")
        self.drop(self.current_plot_ids()[0], "s6")
        self.assertEqual(len(self.current_plot_ids()), 5)
        self.assertEqual(self.view.full_tab_count_i, 0)

    @covers("LLFR-00021")
    def test_drop_of_unknown_signal_is_ignored(self) -> None:
        """A dropped name that is not in the file draws nothing.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.drop(plot_id_i, "nope")
        self.assertEqual(self.view.drawn_names(plot_id_i), ["s1"])

    @covers("LLFR-00021", "LLFR-00070")
    def test_drop_keeps_the_plot_time_range(self) -> None:
        """Redrawing after a drop keeps the shared range of the plot.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.view.set_plot_time_range(plot_id_i, 3.0, 5.0)
        self.view.handler_dict["time_range_handler"](plot_id_i, 3.0, 5.0)
        self.drop(plot_id_i, "s2")
        self.assertEqual(self.view.range_dict[plot_id_i], (3.0, 5.0))


class CurveAndPlotActionTest(PlotControllerTestCase):
    """Curve menu and plot menu actions."""

    @covers("LLFR-00039", "HLFR-00022")
    def test_delete_signal_removes_curve(self) -> None:
        """Delete signal redraws the plot without that curve.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.drop(plot_id_i, "s2")
        self.view.handler_dict["curve_delete_handler"](plot_id_i, "s1")
        self.assertEqual(self.view.drawn_names(plot_id_i), ["s2"])
        self.assertIn(plot_id_i, self.view.plot_tab_dict)

    @covers("LLFR-00051", "LLFR-00049", "LLFR-00050", "HLFR-00019")
    def test_deleting_last_curve_deletes_plot(self) -> None:
        """Removing the last curve removes the plot from model and view.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        self.double_click("s2")
        first_plot_id_i, second_plot_id_i = self.current_plot_ids()
        self.view.handler_dict["curve_delete_handler"](first_plot_id_i,
                                                       "s1")
        self.assertEqual(self.current_plot_ids(), [second_plot_id_i])
        self.assertEqual(self.view.call_list[-1],
                         ("remove_plot_view", first_plot_id_i))
        self.assertEqual(self.view.plot_id_list(self.first_tab_id()),
                         [second_plot_id_i])

    @covers("LLFR-00039")
    def test_delete_unknown_signal_does_nothing(self) -> None:
        """Deleting a signal not in the plot makes no call.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        call_count_i = len(self.view.call_list)
        self.view.handler_dict["curve_delete_handler"](plot_id_i, "s9")
        self.view.handler_dict["curve_delete_handler"](999, "s1")
        self.assertEqual(len(self.view.call_list), call_count_i)

    @covers("LLFR-00041", "HLFR-00023")
    def test_width_is_stored_and_drawn(self) -> None:
        """Choosing a width redraws that curve with it.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.drop(plot_id_i, "s2")
        for width_i in (5, 3):
            self.view.handler_dict["curve_width_handler"](plot_id_i, "s2",
                                                          width_i)
            curve_data_list = self.view.drawn_dict[plot_id_i][0]
            self.assertEqual([curve_tuple[4]
                              for curve_tuple in curve_data_list],
                             [1, width_i])

    @covers("LLFR-00041")
    def test_invalid_width_is_ignored(self) -> None:
        """A width outside 1..5 or an unknown curve changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        call_count_i = len(self.view.call_list)
        self.view.handler_dict["curve_width_handler"](plot_id_i, "s1", 9)
        self.view.handler_dict["curve_width_handler"](plot_id_i, "s7", 2)
        self.view.handler_dict["curve_width_handler"](999, "s1", 2)
        self.assertEqual(len(self.view.call_list), call_count_i)
        self.assertEqual(self.workspace.find_plot(plot_id_i)
                         .curve_list[0].width_i, 1)

    @covers("LLFR-00049", "LLFR-00050", "HLFR-00019")
    def test_delete_plot_removes_it_and_its_curves(self) -> None:
        """Delete plot removes the middle plot; the others stay in order.

        Inputs: none.
        Outputs: none.
        """
        for index_i in range(1, 4):
            self.double_click(f"s{index_i}")
        first_i, middle_i, last_i = self.current_plot_ids()
        self.drop(middle_i, "s5")
        self.view.handler_dict["plot_delete_handler"](middle_i)
        self.assertEqual(self.current_plot_ids(), [first_i, last_i])
        self.assertEqual(self.view.call_list[-1],
                         ("remove_plot_view", middle_i))
        self.assertIsNone(self.workspace.find_plot(middle_i))
        call_count_i = len(self.view.call_list)
        self.view.handler_dict["plot_delete_handler"](middle_i)
        self.assertEqual(len(self.view.call_list), call_count_i)

    @covers("LLFR-00070", "HLFR-00014")
    def test_time_range_applies_to_every_tab(self) -> None:
        """A range change in one plot goes to every plot of every tab.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        self.double_click("s2")
        self.double_click("s3")
        plot_id_list = self.current_plot_ids()
        self.view.handler_dict["add_tab"]()
        self.double_click("s4")
        self.double_click("s5")
        other_tab_plot_list = self.current_plot_ids()
        # The first tab is shown again; the second one is hidden.
        self.view.set_current_tab(self.first_tab_id())
        call_count_i = len(self.view.call_list)
        self.view.handler_dict["time_range_handler"](plot_id_list[1],
                                                     1.5, 6.0)
        set_call_list = self.view.call_list[call_count_i:]
        self.assertEqual(
            sorted(set_call_list),
            sorted([("set_plot_time_range", plot_id_i, 1.5, 6.0)
                    for plot_id_i in (plot_id_list[0], plot_id_list[2],
                                      *other_tab_plot_list)]))
        for plot_id_i in other_tab_plot_list:
            self.assertEqual(self.view.range_dict[plot_id_i], (1.5, 6.0))

    @covers("LLFR-00070")
    def test_time_range_from_a_hidden_tab_applies_everywhere(self) -> None:
        """A change reported by a plot of another tab reaches all plots.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        first_plot_id_i = self.current_plot_ids()[0]
        self.view.handler_dict["add_tab"]()
        self.double_click("s2")
        second_plot_id_i = self.current_plot_ids()[0]
        self.view.handler_dict["time_range_handler"](second_plot_id_i,
                                                     7.0, 9.0)
        self.assertEqual(self.view.range_dict[first_plot_id_i], (7.0, 9.0))
        self.view.handler_dict["time_range_handler"](first_plot_id_i,
                                                     1.0, 2.0)
        self.assertEqual(self.view.range_dict[second_plot_id_i],
                         (1.0, 2.0))

    @covers("LLFR-00070")
    def test_time_range_that_is_not_finite_is_ignored(self) -> None:
        """A NaN or infinite range is neither stored nor applied.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        self.double_click("s2")
        first_plot_id_i = self.current_plot_ids()[0]
        call_count_i = len(self.view.call_list)
        self.view.handler_dict["time_range_handler"](
            first_plot_id_i, float("nan"), 2.0)
        self.view.handler_dict["time_range_handler"](
            first_plot_id_i, 1.0, float("inf"))
        self.assertEqual(len(self.view.call_list), call_count_i)
        self.assertEqual(self.controller.shared_time_range_tuple, ())

    @covers("LLFR-00070")
    def test_time_range_of_unknown_plot_is_ignored(self) -> None:
        """A range change for an unknown plot makes no call.

        Inputs: none.
        Outputs: none.
        """
        call_count_i = len(self.view.call_list)
        self.view.handler_dict["time_range_handler"](999, 1.0, 2.0)
        self.assertEqual(len(self.view.call_list), call_count_i)


class TipTest(PlotControllerTestCase):
    """Tip button, pinned tips (HLFR-00024, HLFR-00025)."""

    @covers("LLFR-00042", "HLFR-00024")
    def test_tip_button_sets_tip_tool(self) -> None:
        """Tip on and off is passed to the view as the plot tool.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["plot_tool"]("tip")
        self.assertEqual(self.view.plot_tool_str, "tip")
        self.assertEqual(self.controller.plot_tool_str, "tip")
        self.view.handler_dict["plot_tool"]("")
        self.assertEqual(self.view.plot_tool_str, "")
        self.assertEqual([call_tuple for call_tuple in self.view.call_list
                          if call_tuple[0] == "set_plot_tool"],
                         [("set_plot_tool", "tip"), ("set_plot_tool", "")])

    @covers("LLFR-00045", "HLFR-00025")
    def test_pin_stores_and_draws_tip(self) -> None:
        """A pin request is kept and drawn with the curves.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.view.handler_dict["tip_pin_handler"](plot_id_i, "s1", 2.0,
                                                  2.0)
        self.view.handler_dict["tip_pin_handler"](plot_id_i, "s1", 4.0,
                                                  4.0)
        curve_data_list, pinned_tip_list = self.view.drawn_dict[plot_id_i]
        self.assertEqual(pinned_tip_list, [("s1", 2.0, 2.0, ()),
                                           ("s1", 4.0, 4.0, ())])
        self.assertEqual(len(curve_data_list), 1)
        self.assertEqual(len(self.workspace.find_plot(plot_id_i)
                             .pinned_tip_list), 2)

    @covers("LLFR-00045")
    def test_pin_on_unknown_curve_or_plot_is_ignored(self) -> None:
        """Pins for a signal not in the plot or an unknown plot do nothing.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        call_count_i = len(self.view.call_list)
        self.view.handler_dict["tip_pin_handler"](plot_id_i, "s2", 1.0,
                                                  2.0)
        self.view.handler_dict["tip_pin_handler"](999, "s1", 1.0, 1.0)
        self.assertEqual(len(self.view.call_list), call_count_i)

    @covers("LLFR-00047", "HLFR-00025")
    def test_delete_pinned_tip_by_index(self) -> None:
        """Delete removes the tip at the given index and redraws.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        for time_s in (1.0, 2.0, 3.0):
            self.view.handler_dict["tip_pin_handler"](plot_id_i, "s1",
                                                      time_s, time_s)
        self.view.handler_dict["pinned_tip_delete_handler"](plot_id_i, 1)
        self.assertEqual(self.view.drawn_dict[plot_id_i][1],
                         [("s1", 1.0, 1.0, ()), ("s1", 3.0, 3.0, ())])
        call_count_i = len(self.view.call_list)
        for tip_index_i in (-1, 2, 7):
            self.view.handler_dict["pinned_tip_delete_handler"](
                plot_id_i, tip_index_i)
        self.view.handler_dict["pinned_tip_delete_handler"](999, 0)
        self.assertEqual(len(self.view.call_list), call_count_i)

    @covers("LLFR-00047", "LLFR-00039")
    def test_deleting_curve_removes_its_tips(self) -> None:
        """Tips on a removed curve are not drawn anymore.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        plot_id_i = self.current_plot_ids()[0]
        self.drop(plot_id_i, "s2")
        self.view.handler_dict["tip_pin_handler"](plot_id_i, "s1", 1.0,
                                                  1.0)
        self.view.handler_dict["tip_pin_handler"](plot_id_i, "s2", 1.0,
                                                  2.0)
        self.view.handler_dict["curve_delete_handler"](plot_id_i, "s1")
        self.assertEqual(self.view.drawn_dict[plot_id_i][1],
                         [("s2", 1.0, 2.0, ())])


class TabActionTest(PlotControllerTestCase):
    """Add, delete and rename tabs (HLFR-00015 to HLFR-00017)."""

    @covers("LLFR-00026", "LLFR-00066", "HLFR-00015")
    def test_add_tab_selects_it_and_enables_delete(self) -> None:
        """The "+" handler adds "Tab 2", selects it, enables Delete.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["add_tab"]()
        self.assertEqual(list(self.view.tab_dict.values()),
                         ["Tab 1", "Tab 2"])
        self.assertEqual(self.view.current_tab_id(),
                         self.workspace.tab_list[1].tab_id_i)
        self.assertTrue(self.view.delete_enabled_b)

    @covers("LLFR-00210", "LLFR-00026", "LLFR-00028", "LLFR-00138",
            "LLFR-00016", "HLFR-00015")
    def test_tab_numbers_not_reused_until_a_file_opens(self) -> None:
        """Deleted and undone tab numbers stay used; a file restarts them.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["add_tab"]()
        second_tab_id_i = self.view.current_tab_id()
        self.view.handler_dict["add_tab"]()
        self.view.handler_dict["delete_tab"](second_tab_id_i)
        self.view.handler_dict["add_tab"]()
        self.assertEqual(list(self.view.tab_dict.values()),
                         ["Tab 1", "Tab 3", "Tab 4"])
        # LLFR-00210: undoing the add of Tab 4 does not free its number.
        self.view.handler_dict["undo"]()
        self.assertEqual(list(self.view.tab_dict.values()),
                         ["Tab 1", "Tab 3"])
        self.view.handler_dict["add_tab"]()
        self.assertEqual(list(self.view.tab_dict.values()),
                         ["Tab 1", "Tab 3", "Tab 5"])
        # LLFR-00210, LLFR-00016: a replaced file restarts at Tab 1.
        self.file_controller.open(make_signal_file(2), True)
        self.assertEqual(list(self.view.tab_dict.values()), ["Tab 1"])
        self.view.handler_dict["add_tab"]()
        self.assertEqual(list(self.view.tab_dict.values()),
                         ["Tab 1", "Tab 2"])

    @covers("LLFR-00028", "LLFR-00066", "HLFR-00016")
    def test_delete_tab_removes_it_but_never_the_last(self) -> None:
        """Delete removes a tab; the last tab is kept, Delete disabled.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["add_tab"]()
        second_tab_id_i = self.view.current_tab_id()
        self.double_click("s1")
        self.view.handler_dict["delete_tab"](second_tab_id_i)
        self.assertEqual(list(self.view.tab_dict.values()), ["Tab 1"])
        self.assertEqual(self.view.plot_tab_dict, {})
        self.assertIsNone(self.workspace.find_tab(second_tab_id_i))
        self.assertFalse(self.view.delete_enabled_b)
        call_count_i = len(self.view.call_list)
        self.view.handler_dict["delete_tab"](self.first_tab_id())
        self.view.handler_dict["delete_tab"](999)
        self.assertEqual(len(self.view.call_list), call_count_i)
        self.assertEqual(len(self.workspace.tab_list), 1)

    @covers("LLFR-00030", "HLFR-00017")
    def test_rename_tab(self) -> None:
        """Rename shows the typed name without surrounding spaces.

        Inputs: none.
        Outputs: none.
        """
        tab_id_i = self.first_tab_id()
        self.view.handler_dict["rename_tab"](tab_id_i, "  Speeds  ")
        self.assertEqual(self.view.tab_dict[tab_id_i], "Speeds")
        self.assertEqual(self.workspace.find_tab(tab_id_i).name_str,
                         "Speeds")

    @covers("LLFR-00067", "HLFR-00017")
    def test_empty_name_keeps_old_name(self) -> None:
        """Empty or blank names keep the old name and show nothing.

        Inputs: none.
        Outputs: none.
        """
        tab_id_i = self.first_tab_id()
        call_count_i = len(self.view.call_list)
        for name_str in ("", "   ", "\t"):
            self.view.handler_dict["rename_tab"](tab_id_i, name_str)
        self.view.handler_dict["rename_tab"](999, "x")
        self.assertEqual(len(self.view.call_list), call_count_i)
        self.assertEqual(self.view.tab_dict[tab_id_i], "Tab 1")


class UniqueTabNameTest(PlotControllerTestCase):
    """Tabs never share a name (LLFR-00211, LLFR-00212)."""

    def setUp(self) -> None:
        """Open a file and add a second tab, "Tab 2".

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.view.handler_dict["add_tab"]()
        self.second_tab_id_i = self.view.current_tab_id()

    def rename(self, tab_id_i: int, name_str: str) -> None:
        """Run the rename handler.

        Inputs:
            tab_id_i: id of the tab.
            name_str: the typed name.
        Outputs: none.
        """
        self.view.handler_dict["rename_tab"](tab_id_i, name_str)

    @covers("LLFR-00211", "LLFR-00030", "HLFR-00017")
    def test_rename_to_another_tab_name_is_refused(self) -> None:
        """The previous name is kept and the box names the taken name.

        Inputs: none.
        Outputs: none.
        """
        call_count_i = len(self.view.call_list)
        self.rename(self.second_tab_id_i, "Tab 1")
        self.assertEqual(self.view.call_list[call_count_i:],
                         [("show_tab_name_taken_notification", "Tab 1")])
        self.assertEqual(list(self.view.tab_dict.values()),
                         ["Tab 1", "Tab 2"])
        self.assertEqual(
            self.workspace.find_tab(self.second_tab_id_i).name_str, "Tab 2")
        self.assertEqual(self.view.full_tab_count_i, 0)

    @covers("LLFR-00211", "HLFR-00017")
    def test_surrounding_spaces_do_not_avoid_the_conflict(self) -> None:
        """"  Tab 1 " is the name of Tab 1; the box shows it trimmed.

        Inputs: none.
        Outputs: none.
        """
        self.rename(self.first_tab_id(), "Engine")
        self.rename(self.second_tab_id_i, "  Engine \t")
        self.assertEqual(self.view.tab_name_taken_list, ["Engine"])
        self.assertEqual(list(self.view.tab_dict.values()),
                         ["Engine", "Tab 2"])

    @covers("LLFR-00211", "LLFR-00030", "HLFR-00017")
    def test_own_name_and_other_case_are_accepted(self) -> None:
        """A tab's own name and a name differing only in case are free.

        Inputs: none.
        Outputs: none.
        """
        self.rename(self.second_tab_id_i, " Tab 2 ")
        self.rename(self.second_tab_id_i, "tab 1")
        self.assertEqual(self.view.tab_name_taken_list, [])
        self.assertEqual(list(self.view.tab_dict.values()),
                         ["Tab 1", "tab 1"])
        self.rename(self.second_tab_id_i, "TAB 1")
        self.assertEqual(self.view.tab_dict[self.second_tab_id_i], "TAB 1")
        self.assertEqual(self.view.tab_name_taken_list, [])

    @covers("LLFR-00211", "LLFR-00067")
    def test_blank_name_shows_no_box(self) -> None:
        """A blank name is still refused silently, not as a conflict.

        Inputs: none.
        Outputs: none.
        """
        self.rename(self.first_tab_id(), "   ")
        self.assertEqual(self.view.tab_name_taken_list, [])
        self.assertEqual(self.view.tab_dict[self.first_tab_id()], "Tab 1")

    @covers("LLFR-00211", "LLFR-00140")
    def test_refused_rename_records_no_undo_step(self) -> None:
        """A refused rename leaves the undo history as it was.

        Inputs: none.
        Outputs: none.
        """
        self.controller.undo_history.clear()
        self.view.set_undo_enabled(False)
        self.rename(self.second_tab_id_i, "Tab 1")
        self.assertFalse(self.controller.undo_history.can_undo())
        # LLFR-00140: an accepted rename is still recorded.
        self.rename(self.second_tab_id_i, "Brakes")
        self.assertTrue(self.controller.undo_history.can_undo())
        self.view.handler_dict["undo"]()
        self.assertEqual(list(self.view.tab_dict.values()),
                         ["Tab 1", "Tab 2"])
        self.assertFalse(self.controller.undo_history.can_undo())

    @covers("LLFR-00212", "LLFR-00210", "LLFR-00026", "HLFR-00015")
    def test_new_tab_skips_a_renamed_tab_name(self) -> None:
        """A tab renamed "Tab 3" makes the next new tab "Tab 4".

        Inputs: none.
        Outputs: none.
        """
        self.rename(self.second_tab_id_i, "Tab 3")
        self.view.handler_dict["add_tab"]()
        self.assertEqual(list(self.view.tab_dict.values()),
                         ["Tab 1", "Tab 3", "Tab 4"])
        self.assertEqual(len(set(self.view.tab_dict.values())), 3)

    @covers("LLFR-00212", "LLFR-00210", "LLFR-00138")
    def test_undo_keeps_tab_names_unique(self) -> None:
        """An undone rename and later adds never give two equal names.

        Inputs: none.
        Outputs: none.
        """
        # Tab 2 renamed "Tab 5"; undo brings back "Tab 2" after Tab 3
        # was added, and new tabs then skip nothing but used numbers.
        self.rename(self.second_tab_id_i, "Tab 5")
        self.view.handler_dict["add_tab"]()
        self.view.handler_dict["undo"]()
        self.view.handler_dict["undo"]()
        self.assertEqual(list(self.view.tab_dict.values()),
                         ["Tab 1", "Tab 2"])
        for _ in range(3):
            self.view.handler_dict["add_tab"]()
        name_list = list(self.view.tab_dict.values())
        self.assertEqual(name_list,
                         ["Tab 1", "Tab 2", "Tab 4", "Tab 5", "Tab 6"])
        self.assertEqual(len(set(name_list)), len(name_list))


if __name__ == "__main__":
    unittest.main()
