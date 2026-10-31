"""Tests for the plot tool handling of the plot controller (HLFR-00032).

A fake view is used, so no Qt is needed.
"""

import unittest

from tests.support import covers

from tests.controller.test_plot_controller import PlotControllerTestCase

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, PLOT_TOOL_TUPLE, TIP_TOOL_STR,
    ZOOM_TOOL_STR, is_known_plot_tool)


class PlotToolNameTest(unittest.TestCase):
    """The tool names shared by the controller and the view."""

    @covers("LLFR-00079")
    def test_tool_names_are_distinct(self) -> None:
        """The three tools and "no tool" have different names.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(NO_TOOL_STR, "")
        self.assertEqual(PLOT_TOOL_TUPLE,
                         (TIP_TOOL_STR, ZOOM_TOOL_STR, MARKER_TOOL_STR))
        self.assertEqual(len(set(PLOT_TOOL_TUPLE + (NO_TOOL_STR,))), 4)
        for tool_str in PLOT_TOOL_TUPLE + (NO_TOOL_STR,):
            self.assertTrue(is_known_plot_tool(tool_str))
        for unknown_str in ("Tip", "pan", " ", "zoom "):
            self.assertFalse(is_known_plot_tool(unknown_str))


class PlotToolControllerTest(PlotControllerTestCase):
    """The tool reported by the view is applied to every plot."""

    def tool_call_list(self) -> list:
        """Return the set_plot_tool calls made on the fake view.

        Inputs: none.
        Outputs: list of tool names, in call order.
        """
        return [call_tuple[1] for call_tuple in self.view.call_list
                if call_tuple[0] == "set_plot_tool"]

    @covers("LLFR-00079", "LLFR-00042", "LLFR-00078", "LLFR-00080")
    def test_every_tool_change_reaches_the_view(self) -> None:
        """Each tool, switched in turn, is passed to the view.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.controller.plot_tool_str, NO_TOOL_STR)
        sequence_list = [TIP_TOOL_STR, ZOOM_TOOL_STR, MARKER_TOOL_STR,
                         TIP_TOOL_STR]
        for tool_str in sequence_list:
            self.view.handler_dict["plot_tool"](tool_str)
            self.assertEqual(self.controller.plot_tool_str, tool_str)
            self.assertEqual(self.view.plot_tool_str, tool_str)
        self.assertEqual(self.tool_call_list(), sequence_list)

    @covers("LLFR-00002", "LLFR-00109")
    def test_no_tool_is_passed_to_the_view(self) -> None:
        """A second click on the active button leaves no tool active.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["plot_tool"](ZOOM_TOOL_STR)
        self.view.handler_dict["plot_tool"](NO_TOOL_STR)
        self.assertEqual(self.controller.plot_tool_str, NO_TOOL_STR)
        self.assertEqual(self.view.plot_tool_str, NO_TOOL_STR)
        self.assertEqual(self.tool_call_list(),
                         [ZOOM_TOOL_STR, NO_TOOL_STR])

    @covers("LLFR-00079")
    def test_unknown_tool_is_ignored(self) -> None:
        """A name that is not a plot tool changes nothing.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["plot_tool"](TIP_TOOL_STR)
        self.view.handler_dict["plot_tool"]("pan")
        self.assertEqual(self.controller.plot_tool_str, TIP_TOOL_STR)
        self.assertEqual(self.tool_call_list(), [TIP_TOOL_STR])

    @covers("LLFR-00109", "LLFR-00045", "LLFR-00078", "LLFR-00070")
    def test_using_a_tool_keeps_it_active(self) -> None:
        """Pinning tips and zooming never change the active tool.

        Inputs: none.
        Outputs: none.
        """
        self.double_click("s1")
        self.double_click("s2")
        first_id_i, second_id_i = self.current_plot_ids()
        self.view.handler_dict["plot_tool"](TIP_TOOL_STR)
        self.view.handler_dict["tip_pin_handler"](first_id_i, "s1", 1.0,
                                                  2.0)
        self.assertEqual(
            len(self.workspace.find_plot(first_id_i).pinned_tip_list), 1)
        self.view.handler_dict["plot_tool"](ZOOM_TOOL_STR)
        self.view.handler_dict["time_range_handler"](first_id_i, 2.0, 4.0)
        self.assertEqual(self.view.range_dict[second_id_i], (2.0, 4.0))
        self.view.handler_dict["time_range_handler"](first_id_i, 2.5, 3.5)
        self.assertEqual(self.view.range_dict[second_id_i], (2.5, 3.5))
        self.assertEqual(self.controller.plot_tool_str, ZOOM_TOOL_STR)
        self.assertEqual(self.view.plot_tool_str, ZOOM_TOOL_STR)
        self.assertEqual(self.tool_call_list(),
                         [TIP_TOOL_STR, ZOOM_TOOL_STR])

    @covers("LLFR-00109")
    def test_opening_a_file_keeps_the_tool(self) -> None:
        """A newly opened file does not change the active tool.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["plot_tool"](MARKER_TOOL_STR)
        self.file_controller.open(self.signal_file, True)
        self.assertEqual(self.controller.plot_tool_str, MARKER_TOOL_STR)
        self.assertEqual(self.tool_call_list(), [MARKER_TOOL_STR])


if __name__ == "__main__":
    unittest.main()
