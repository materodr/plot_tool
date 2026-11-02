"""Tests for the areas in the plot controller, with a fake view
(HLFR-00066 to HLFR-00069, LLFR-00304 to LLFR-00318).

The file of PlotControllerTestCase has times from 0 s to 10 s.
"""

import types
import unittest

import numpy as np

from tests.controller.test_plot_controller import PlotControllerTestCase
from tests.model.test_layout_file import curve, minimal_layout, one_plot_tab
from tests.support import covers

from controller.plot_tools import (
    AREA_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR, PLOT_TOOL_TUPLE)
from model.workspace import FREQUENCY_PLOT_KIND_STR


class AreaControllerTestCase(PlotControllerTestCase):
    """Shared setup: one time plot and the Area tool active."""

    def setUp(self) -> None:
        """Plot s1 and activate the Area tool.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.double_click("s1")
        self.plot_id_i = self.current_plot_ids()[0]
        self.choose_tool(AREA_TOOL_STR)

    def choose_tool(self, tool_str: str) -> None:
        """Run the plot tool handler.

        Inputs:
            tool_str: the tool to activate, NO_TOOL_STR for none.
        Outputs: none.
        """
        self.view.handler_dict["plot_tool"](tool_str)

    def create(self, start_s: float, end_s: float, plot_id_i=None) -> None:
        """Run the area creation handler.

        Inputs:
            start_s: time of the press, in s.
            end_s: time of the release, in s.
            plot_id_i: the plot, the first one by default.
        Outputs: none.
        """
        self.view.handler_dict["area_create_handler"](
            self.plot_id_i if plot_id_i is None else plot_id_i,
            start_s, end_s)

    def change(self, area_id_i: int, start_s: float, end_s: float) -> None:
        """Run the area move or resize handler on the first plot.

        Inputs:
            area_id_i: id of the area.
            start_s: new start, in s.
            end_s: new end, in s.
        Outputs: none.
        """
        self.view.handler_dict["area_change_handler"](
            self.plot_id_i, area_id_i, start_s, end_s)

    def area_tuple_list(self) -> list:
        """Return the areas of the model as (name, start, end).

        Inputs: none.
        Outputs: a list of tuples in creation order.
        """
        return [(area.name_str, area.start_s, area.end_s)
                for area in self.workspace.area_list]

    def drawn_area_list(self, plot_id_i=None) -> list:
        """Return the areas the fake view last drew in a plot.

        Inputs:
            plot_id_i: the plot, the first one by default.
        Outputs: a list of (name, start, end).
        """
        plot_id_i = self.plot_id_i if plot_id_i is None else plot_id_i
        return [tuple(area_tuple[1:4]) for area_tuple
                in self.view.area_drawn_dict.get(plot_id_i, [])]

    def undo(self) -> None:
        """Run the Undo handler.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["undo"]()

    def redo(self) -> None:
        """Run the Redo handler.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["redo"]()


class CreateAreaControllerTest(AreaControllerTestCase):
    """Creating areas from the view's requests."""

    @covers("LLFR-00304", "LLFR-00309", "LLFR-00310", "LLFR-00140")
    def test_create_shows_the_area_on_every_time_plot(self) -> None:
        """A created area is drawn on every time plot of every tab,
        including one created later, and is one undoable action.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["add_tab"]()
        self.double_click("s2")
        other_plot_id_i = self.current_plot_ids()[0]
        depth_i = self.controller.undo_history.depth()
        self.create(3.0, 1.0, other_plot_id_i)
        self.assertEqual(self.area_tuple_list(), [("Area 1", 1.0, 3.0)])
        self.assertEqual(self.controller.undo_history.depth(), depth_i + 1)
        for plot_id_i in (self.plot_id_i, other_plot_id_i):
            self.assertEqual(self.drawn_area_list(plot_id_i),
                             [("Area 1", 1.0, 3.0)])
        self.double_click("s3")
        new_plot_id_i = self.current_plot_ids()[-1]
        self.assertEqual(self.drawn_area_list(new_plot_id_i),
                         [("Area 1", 1.0, 3.0)])

    @covers("LLFR-00304", "LLFR-00119")
    def test_create_is_limited_to_the_file_and_never_overlaps(self) -> None:
        """A span beyond the file is cut to it; an overlapping, empty or
        unfinished span creates nothing and records no undo step.

        Inputs: none.
        Outputs: none.
        """
        self.create(-5.0, 2.0)
        self.assertEqual(self.area_tuple_list(), [("Area 1", 0.0, 2.0)])
        depth_i = self.controller.undo_history.depth()
        for start_s, end_s in ((1.0, 4.0), (11.0, 12.0), (3.0, 3.0),
                               (float("nan"), 5.0), (-1.0, 0.0)):
            with self.subTest(span=(start_s, end_s)):
                self.create(start_s, end_s)
        self.assertEqual(self.controller.undo_history.depth(), depth_i)
        self.create(2.0, 15.0)
        self.assertEqual(self.area_tuple_list(),
                         [("Area 1", 0.0, 2.0), ("Area 2", 2.0, 10.0)])

    @covers("LLFR-00318", "LLFR-00303", "LLFR-00311")
    def test_other_tools_and_frequency_plots_create_nothing(self) -> None:
        """Without the Area tool, or on a frequency plot or an unknown
        plot, no area is created or changed.

        Inputs: none.
        Outputs: none.
        """
        self.create(1.0, 2.0)
        area_id_i = self.workspace.area_list[0].area_id_i
        for tool_str in (NO_TOOL_STR,) + tuple(
                tool_str for tool_str in PLOT_TOOL_TUPLE
                if tool_str != AREA_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.choose_tool(tool_str)
                self.create(4.0, 5.0)
                self.change(area_id_i, 6.0, 7.0)
                self.assertEqual(self.area_tuple_list(),
                                 [("Area 1", 1.0, 2.0)])
        self.choose_tool(AREA_TOOL_STR)
        frequency_plot = self.workspace.add_plot(
            self.first_tab_id(), FREQUENCY_PLOT_KIND_STR)
        self.create(4.0, 5.0, frequency_plot.plot_id_i)
        self.create(4.0, 5.0, 999)
        self.view.handler_dict["area_change_handler"](
            frequency_plot.plot_id_i, area_id_i, 6.0, 7.0)
        self.assertEqual(self.area_tuple_list(), [("Area 1", 1.0, 2.0)])

    @covers("LLFR-00311")
    def test_frequency_plot_draws_no_area(self) -> None:
        """A frequency plot is drawn with no area.

        Inputs: none.
        Outputs: none.
        """
        self.create(1.0, 2.0)
        frequency_plot = self.workspace.add_plot(
            self.first_tab_id(), FREQUENCY_PLOT_KIND_STR)
        self.controller.synthetic_store = FakeFftStore()
        frequency_plot.add_curve("fft_s1")
        self.view.add_plot_view(self.first_tab_id(),
                                frequency_plot.plot_id_i, "frequency")
        self.controller.redraw_plot(frequency_plot)
        self.assertEqual(self.drawn_area_list(frequency_plot.plot_id_i), [])
        self.create(3.0, 4.0)
        self.assertEqual(self.drawn_area_list(frequency_plot.plot_id_i), [])
        self.assertEqual(len(self.drawn_area_list()), 2)


class FakeFftStore:
    """A synthetic store that holds one FFT signal "fft_s1"."""

    def contains(self, signal_name_str: str) -> bool:
        """Tell whether the store holds a signal.

        Inputs:
            signal_name_str: a name.
        Outputs: True for "fft_s1".
        """
        return signal_name_str == "fft_s1"

    def is_fft(self, signal_name_str: str) -> bool:
        """Tell whether a signal is an FFT signal.

        Inputs:
            signal_name_str: a name.
        Outputs: True for "fft_s1".
        """
        return signal_name_str == "fft_s1"

    def get(self, signal_name_str: str):
        """Return the FFT signal.

        Inputs:
            signal_name_str: a name.
        Outputs: an object with value_array and frequency_array.
        """
        return types.SimpleNamespace(
            value_array=np.ones(5),
            frequency_array=np.linspace(0.0, 2.0, 5))


class ChangeAreaControllerTest(AreaControllerTestCase):
    """Moving, resizing, renaming and deleting areas."""

    def setUp(self) -> None:
        """Create "Area 1" from 1 s to 2 s and "Area 2" from 5 s to 6 s.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.create(1.0, 2.0)
        self.create(5.0, 6.0)
        self.first_id_i = self.workspace.area_list[0].area_id_i
        self.second_id_i = self.workspace.area_list[1].area_id_i

    @covers("LLFR-00312", "LLFR-00313", "LLFR-00310", "LLFR-00140",
            "LLFR-00308")
    def test_move_and_resize_are_undoable_and_shown_everywhere(
            self) -> None:
        """A move and a resize are one undoable action each, shown on
        every plot; undo and redo go back and forth.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s2")
        second_plot_id_i = self.current_plot_ids()[-1]
        depth_i = self.controller.undo_history.depth()
        self.change(self.first_id_i, 3.0, 4.0)
        self.change(self.first_id_i, 3.0, 4.5)
        self.assertEqual(self.controller.undo_history.depth(), depth_i + 2)
        expected_list = [("Area 1", 3.0, 4.5), ("Area 2", 5.0, 6.0)]
        self.assertEqual(self.area_tuple_list(), expected_list)
        self.assertEqual(self.drawn_area_list(second_plot_id_i),
                         expected_list)
        self.undo()
        self.assertEqual(self.area_tuple_list()[0], ("Area 1", 3.0, 4.0))
        self.assertEqual(self.drawn_area_list(second_plot_id_i)[0],
                         ("Area 1", 3.0, 4.0))
        self.undo()
        self.assertEqual(self.area_tuple_list()[0], ("Area 1", 1.0, 2.0))
        self.redo()
        self.redo()
        self.assertEqual(self.area_tuple_list(), expected_list)

    @covers("LLFR-00312", "LLFR-00313", "LLFR-00119", "LLFR-00140")
    def test_refused_change_redraws_the_area_where_it_was(self) -> None:
        """An overlapping change or one to the same place records
        nothing, and the view is told the area's real place; a change
        beyond the file is cut to the file.

        Inputs: none.
        Outputs: none.
        """
        depth_i = self.controller.undo_history.depth()
        count_i = self.view.set_areas_count_i
        self.change(self.first_id_i, 4.0, 5.5)
        self.change(self.first_id_i, 1.0, 2.0)
        self.change(self.first_id_i, float("inf"), 2.0)
        self.change(999, 7.0, 8.0)
        self.assertEqual(self.controller.undo_history.depth(), depth_i)
        self.assertEqual(self.view.set_areas_count_i, count_i + 3)
        self.assertEqual(self.drawn_area_list()[0], ("Area 1", 1.0, 2.0))
        self.change(self.second_id_i, 9.0, 11.0)
        self.assertEqual(self.area_tuple_list()[1], ("Area 2", 9.0, 10.0))
        # Two areas may share an edge.
        self.change(self.first_id_i, 2.0, 9.0)
        self.assertEqual(self.area_tuple_list()[0], ("Area 1", 2.0, 9.0))

    @covers("LLFR-00312", "LLFR-00119")
    def test_move_beyond_the_file_is_shifted_keeping_the_width(
            self) -> None:
        """A moved span (as wide as the area) that leaves the file is
        shifted back into it, not cut.

        Inputs: none.
        Outputs: none.
        """
        self.change(self.second_id_i, 9.5, 10.5)
        self.assertEqual(self.area_tuple_list()[1], ("Area 2", 9.0, 10.0))
        self.change(self.first_id_i, -0.75, 0.25)
        self.assertEqual(self.area_tuple_list()[0], ("Area 1", 0.0, 1.0))

    @covers("LLFR-00315", "LLFR-00307", "LLFR-00140")
    def test_rename_with_any_tool_and_blank_keeps_the_name(self) -> None:
        """Rename asks with the current name; a blank answer or a
        cancelled dialog keeps it and records nothing.

        Inputs: none.
        Outputs: none.
        """
        self.choose_tool(MARKER_TOOL_STR)
        depth_i = self.controller.undo_history.depth()
        self.view.area_name_answer_list = ["   ", None, "  Warm-up "]
        rename_handler = self.view.handler_dict["area_rename_handler"]
        rename_handler(self.plot_id_i, self.first_id_i)
        rename_handler(self.plot_id_i, self.first_id_i)
        self.assertEqual(self.area_tuple_list()[0][0], "Area 1")
        self.assertEqual(self.controller.undo_history.depth(), depth_i)
        rename_handler(self.plot_id_i, self.first_id_i)
        self.assertEqual(self.view.area_name_question_list,
                         ["Area 1", "Area 1", "Area 1"])
        self.assertEqual(self.area_tuple_list()[0][0], "Warm-up")
        self.assertEqual(self.drawn_area_list()[0][0], "Warm-up")
        self.assertEqual(self.controller.undo_history.depth(), depth_i + 1)
        rename_handler(999, self.first_id_i)
        rename_handler(self.plot_id_i, 999)
        self.assertEqual(len(self.view.area_name_question_list), 3)
        self.undo()
        self.assertEqual(self.area_tuple_list()[0][0], "Area 1")

    @covers("LLFR-00351", "LLFR-00310", "LLFR-00140", "LLFR-00138",
            "LLFR-00192")
    def test_color_change_is_undoable_and_shown_on_every_plot(
            self) -> None:
        """A color chosen in the menu, with any tool, is shown on every
        time plot of every tab; it is one undoable action, redone by
        redo; an unknown or the same color records nothing.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["add_tab"]()
        self.double_click("s2")
        other_plot_id_i = self.current_plot_ids()[0]
        self.choose_tool(NO_TOOL_STR)
        color_handler = self.view.handler_dict["area_color_handler"]
        depth_i = self.controller.undo_history.depth()
        color_handler(self.plot_id_i, self.first_id_i, "Purple")
        color_handler(self.plot_id_i, self.first_id_i, "Magenta")
        color_handler(999, self.first_id_i, "Blue")
        color_handler(self.plot_id_i, 999, "Blue")
        self.assertEqual(self.controller.undo_history.depth(), depth_i)
        color_handler(other_plot_id_i, self.first_id_i, "Green")
        self.assertEqual(self.controller.undo_history.depth(), depth_i + 1)
        for plot_id_i in (self.plot_id_i, other_plot_id_i):
            self.assertEqual(
                [area_tuple[4] for area_tuple
                 in self.view.area_drawn_dict[plot_id_i]],
                ["Green", "Magenta"])
        self.undo()
        self.assertEqual(self.workspace.area_list[0].color_name_str,
                         "Magenta")
        self.assertEqual(self.view.area_drawn_dict[other_plot_id_i][0][4],
                         "Magenta")
        self.redo()
        self.assertEqual(self.workspace.area_list[0].color_name_str,
                         "Green")

    @covers("LLFR-00316", "LLFR-00310", "LLFR-00140", "LLFR-00309")
    def test_delete_with_any_tool_and_undo(self) -> None:
        """Delete removes the area from every plot; undo brings it back;
        its number is not reused.

        Inputs: none.
        Outputs: none.
        """
        self.choose_tool(NO_TOOL_STR)
        delete_handler = self.view.handler_dict["area_delete_handler"]
        delete_handler(self.plot_id_i, self.first_id_i)
        self.assertEqual(self.drawn_area_list(), [("Area 2", 5.0, 6.0)])
        depth_i = self.controller.undo_history.depth()
        delete_handler(self.plot_id_i, self.first_id_i)
        delete_handler(999, self.second_id_i)
        self.assertEqual(self.controller.undo_history.depth(), depth_i)
        self.undo()
        self.assertEqual(len(self.drawn_area_list()), 2)
        self.redo()
        self.choose_tool(AREA_TOOL_STR)
        self.create(7.0, 8.0)
        self.assertEqual(self.area_tuple_list()[-1][0], "Area 3")

    @covers("LLFR-00310", "LLFR-00205", "LLFR-00138", "LLFR-00049")
    def test_deleting_the_last_plot_deletes_the_areas_undoably(
            self) -> None:
        """The last plot's deletion removes the areas in the same undo
        step; one undo brings the plot and its areas back.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["plot_delete_handler"](self.plot_id_i)
        self.assertEqual(self.workspace.area_list, [])
        self.undo()
        self.assertEqual(len(self.workspace.area_list), 2)
        self.assertEqual(len(self.drawn_area_list()), 2)

    @covers("LLFR-00310", "LLFR-00028", "LLFR-00138")
    def test_deleting_the_tab_of_the_last_plot(self) -> None:
        """Deleting the tab of the last plot removes the areas, undoably.

        Inputs: none.
        Outputs: none.
        """
        first_tab_id_i = self.first_tab_id()
        self.view.handler_dict["add_tab"]()
        self.view.handler_dict["delete_tab"](first_tab_id_i)
        self.assertEqual(self.workspace.area_list, [])
        self.undo()
        self.assertEqual(len(self.workspace.area_list), 2)

    @covers("LLFR-00310", "LLFR-00309", "LLFR-00015", "LLFR-00142")
    def test_file_replace_deletes_areas_and_restarts_numbering(
            self) -> None:
        """Opening a file removes every area, clears the history and the
        next area is "Area 1" again.

        Inputs: none.
        Outputs: none.
        """
        self.file_controller.open(self.signal_file, True)
        self.assertEqual(self.workspace.area_list, [])
        self.assertFalse(self.controller.undo_history.can_undo())
        self.double_click("s1")
        self.plot_id_i = self.current_plot_ids()[0]
        self.create(1.0, 2.0)
        self.assertEqual(self.area_tuple_list(), [("Area 1", 1.0, 2.0)])


class LayoutAreaControllerTest(AreaControllerTestCase):
    """Areas saved in and loaded from layout files by the controller."""

    @covers("LLFR-00225", "LLFR-00230", "LLFR-00319", "LLFR-00310",
            "LLFR-00238")
    def test_save_and_load_add_the_areas_to_the_current_ones(self) -> None:
        """layout_dict holds the areas; loading it adds the areas that do
        not overlap, draws them on every time plot and clears the undo
        history.

        Inputs: none.
        Outputs: none.
        """
        self.create(1.0, 2.0)
        self.assertEqual(self.controller.layout_dict()["areas"], [
            {"name": "Area 1", "start": 1.0, "end": 2.0,
             "color": "Magenta"}])
        result = self.controller.load_layout(minimal_layout(
            [one_plot_tab([curve("s2")])], areas=[
                {"name": "Saved", "start": 3.0, "end": 4.0},
                {"name": "Clash", "start": 1.5, "end": 3.5}]))
        self.assertEqual(len(result.report.not_rebuilt_line_list), 1)
        self.assertEqual(self.area_tuple_list(), [
            ("Area 1", 1.0, 2.0), ("Saved", 3.0, 4.0)])
        self.assertFalse(self.controller.undo_history.can_undo())
        for plot in self.controller.time_plot_list():
            self.assertEqual(self.drawn_area_list(plot.plot_id_i),
                             self.area_tuple_list())


if __name__ == "__main__":
    unittest.main()
