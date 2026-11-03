"""Tests for the recent colors and the delta marker colors in the plot
controller (issue #167): HLFR-00088, HLFR-00092.

Every color handler takes, after the item, the color the user chose in
the recent colors of the color submenu (LLFR-00419), or "" for "Other
color...", which asks the shared picker (``ask_color`` of the fake view).
No Qt is needed.
"""

from tests.support import covers

from controller.plot_tools import (
    AREA_TOOL_STR, ARROW_TOOL_STR, DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR,
    MARKER_TOOL_STR, NO_TOOL_STR, TEXT_TOOL_STR)
from model.curve_colors import MARKER_COLOR_STR
from tests.controller.test_plot_controller import PlotControllerTestCase


class RecentColorControllerTestCase(PlotControllerTestCase):
    """Shared setup: one plot of s1 and s2 with a flag, an area, a text
    note, an arrow and two delta markers."""

    def setUp(self) -> None:
        """Open the file, plot s1 and s2 and place one of each item.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.double_click("s1")
        self.plot_id_i = self.current_plot_ids()[0]
        self.drop(self.plot_id_i, "s2")
        handler_dict = self.view.handler_dict
        handler_dict["plot_tool"](MARKER_TOOL_STR)
        handler_dict["marker_place_handler"](self.plot_id_i, 1.0)
        handler_dict["plot_tool"](AREA_TOOL_STR)
        handler_dict["area_create_handler"](self.plot_id_i, 2.0, 3.0)
        handler_dict["plot_tool"](TEXT_TOOL_STR)
        handler_dict["text_note_create_handler"](self.plot_id_i, "Peak",
                                                 2.0, 3.0)
        handler_dict["plot_tool"](ARROW_TOOL_STR)
        handler_dict["arrow_create_handler"](self.plot_id_i, 1.0, 1.0,
                                             4.0, 4.0)
        for tool_str, first_tuple, second_tuple in (
                (DELTA_X_TOOL_STR, ("s1", 2.0), ("s2", 7.0)),
                (DELTA_Y_TOOL_STR, ("s1", 1.0), ("s1", 5.0))):
            handler_dict["plot_tool"](tool_str)
            for name_str, time_s in (first_tuple, second_tuple):
                value_f = float(self.signal_file.signal_array(name_str)[
                    int(time_s)])
                handler_dict["delta_point_pick_handler"](
                    self.plot_id_i, name_str, time_s, value_f)
        handler_dict["plot_tool"](NO_TOOL_STR)
        self.plot = self.workspace.find_plot(self.plot_id_i)
        self.flag_id_i = self.workspace.marker_list[0].marker_id_i
        self.area_id_i = self.workspace.area_list[0].area_id_i
        self.delta_id_list = [delta_marker.delta_marker_id_i for
                              delta_marker in self.plot.delta_marker_list]

    def undo_depth(self) -> int:
        """Return how many actions can be undone.

        Inputs: none.
        Outputs: the depth of the undo history.
        """
        return self.controller.undo_history.depth()

    def drawn_delta_colors(self) -> list:
        """Return the colors of the delta markers last drawn in the plot.

        Inputs: none.
        Outputs: a list of "#rrggbb", in placing order.
        """
        return [delta_tuple[5] for delta_tuple
                in self.view.delta_drawn_dict[self.plot_id_i]]

    def color_option_list(self) -> list:
        """Return every color option, with its handler and item.

        Inputs: none.
        Outputs: a list of (name_str, call, read_color) where call(color_str)
            runs the handler for the item and read_color() returns the
            item's current color in the model.
        """
        handler_dict = self.view.handler_dict

        def plot():
            """Return the model plot as it is now (an undo replaces it).

            Inputs: none.
            Outputs: the model Plot.
            """
            return self.workspace.find_plot(self.plot_id_i)

        def call_with(handler_name_str: str, item_i: int):
            """Return a function that runs one color handler.

            Inputs:
                handler_name_str: name of the handler.
                item_i: id or index of the item.
            Outputs: function(color_str).
            """
            return lambda color_str: handler_dict[handler_name_str](
                self.plot_id_i, item_i, color_str)

        return [
            ("flag", call_with("marker_color_handler", self.flag_id_i),
             lambda: self.workspace.marker_list[0].color_str),
            ("area", call_with("area_color_handler", self.area_id_i),
             lambda: self.workspace.area_list[0].color_str),
            ("arrow", call_with("arrow_color_handler", 0),
             lambda: plot().arrow_list[0].color_str),
            ("border", call_with("text_note_border_color_handler", 0),
             lambda: plot().text_note_list[0].border_color_str),
            ("text", call_with("text_note_text_color_handler", 0),
             lambda: plot().text_note_list[0].text_color_str),
            ("delta marker",
             call_with("delta_marker_color_handler", self.delta_id_list[0]),
             lambda: plot().delta_marker_list[0].color_str)]


class RecentColorChoiceTest(RecentColorControllerTestCase):
    """A recent color chosen in a submenu (LLFR-00419, LLFR-00390)."""

    @covers("LLFR-00419", "LLFR-00390", "LLFR-00140", "LLFR-00388",
            "LLFR-00392", "LLFR-00351", "LLFR-00379", "LLFR-00387",
            "LLFR-00409")
    def test_recent_color_is_one_undoable_action(self) -> None:
        """For every color option, a recent color is applied without
        opening the picker, as one undoable action; undo brings the old
        color back.

        Inputs: none.
        Outputs: none.
        """
        for name_str, call, read_color in self.color_option_list():
            with self.subTest(option=name_str):
                old_color_str = read_color()
                depth_i = self.undo_depth()
                call("#12AB34")
                self.assertEqual(read_color(), "#12ab34")
                self.assertEqual(self.undo_depth(), depth_i + 1)
                self.assertEqual(self.view.color_question_list, [])
                self.view.handler_dict["undo"]()
                self.assertEqual(read_color(), old_color_str)

    @covers("LLFR-00419", "LLFR-00390", "LLFR-00140")
    def test_current_color_records_nothing(self) -> None:
        """Choosing the recent color the item already has, in any case,
        changes nothing and adds no undoable action.

        Inputs: none.
        Outputs: none.
        """
        for name_str, call, read_color in self.color_option_list():
            with self.subTest(option=name_str):
                depth_i = self.undo_depth()
                current_color_str = read_color()
                call(current_color_str.upper())
                self.assertEqual(read_color(), current_color_str)
                self.assertEqual(self.undo_depth(), depth_i)

    @covers("LLFR-00388", "LLFR-00389", "LLFR-00390")
    def test_other_color_opens_the_picker(self) -> None:
        """"Other color..." ("") opens the picker at the item's color;
        a confirmed color is applied, a cancel changes nothing.

        Inputs: none.
        Outputs: none.
        """
        for name_str, call, read_color in self.color_option_list():
            with self.subTest(option=name_str):
                current_color_str = read_color()
                self.view.color_question_list = []
                self.view.color_answer_list = [None, "#abcdef"]
                depth_i = self.undo_depth()
                call("")
                self.assertEqual(read_color(), current_color_str)
                self.assertEqual(self.undo_depth(), depth_i)
                call("")
                self.assertEqual(read_color(), "#abcdef")
                self.assertEqual(self.undo_depth(), depth_i + 1)
                self.assertEqual(self.view.color_question_list,
                                 [current_color_str] * 2)

    @covers("LLFR-00390", "LLFR-00419")
    def test_invalid_recent_color_changes_nothing(self) -> None:
        """A chosen value that is not "#rrggbb" changes nothing.

        Inputs: none.
        Outputs: none.
        """
        for name_str, call, read_color in self.color_option_list():
            with self.subTest(option=name_str):
                current_color_str = read_color()
                depth_i = self.undo_depth()
                call("blue")
                self.assertEqual(read_color(), current_color_str)
                self.assertEqual(self.undo_depth(), depth_i)


class DeltaMarkerColorControllerTest(RecentColorControllerTestCase):
    """"Color" in the delta marker menu (LLFR-00409, LLFR-00172)."""

    @covers("LLFR-00172", "LLFR-00083")
    def test_new_delta_markers_get_the_marker_color(self) -> None:
        """Every new delta marker has, and is drawn in, the reserved
        marker color.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.drawn_delta_colors(), [MARKER_COLOR_STR] * 2)
        self.assertEqual([delta_marker.color_str for delta_marker
                          in self.workspace.find_plot(
                              self.plot_id_i).delta_marker_list],
                         [MARKER_COLOR_STR] * 2)

    @covers("LLFR-00409", "LLFR-00389", "LLFR-00390", "LLFR-00140",
            "LLFR-00138", "LLFR-00192")
    def test_color_of_one_delta_marker(self) -> None:
        """The picker starts at the marker's color; the confirmed color
        is drawn for that marker only, with its points and value
        unchanged, as one undoable action that undo and redo follow.

        Inputs: none.
        Outputs: none.
        """
        before_list = list(self.view.delta_drawn_dict[self.plot_id_i])
        depth_i = self.undo_depth()
        self.view.color_answer_list = ["#1F77B4"]
        self.view.handler_dict["delta_marker_color_handler"](
            self.plot_id_i, self.delta_id_list[1])
        self.assertEqual(self.view.color_question_list, [MARKER_COLOR_STR])
        self.assertEqual(self.undo_depth(), depth_i + 1)
        self.assertEqual(self.drawn_delta_colors(),
                         [MARKER_COLOR_STR, "#1f77b4"])
        after_list = self.view.delta_drawn_dict[self.plot_id_i]
        for before_tuple, after_tuple in zip(before_list, after_list):
            self.assertEqual(before_tuple[:5], after_tuple[:5])
        self.view.handler_dict["undo"]()
        self.assertEqual(self.drawn_delta_colors(), [MARKER_COLOR_STR] * 2)
        self.view.handler_dict["redo"]()
        self.assertEqual(self.drawn_delta_colors(),
                         [MARKER_COLOR_STR, "#1f77b4"])

    @covers("LLFR-00409", "LLFR-00390")
    def test_unknown_ids_cancel_and_same_color(self) -> None:
        """Unknown plot or marker ids, a cancelled picker and the
        marker's own color change nothing and record nothing.

        Inputs: none.
        Outputs: none.
        """
        handler = self.view.handler_dict["delta_marker_color_handler"]
        depth_i = self.undo_depth()
        handler(999, self.delta_id_list[0], "#00ff00")
        handler(self.plot_id_i, 999, "#00ff00")
        self.view.color_answer_list = [None, MARKER_COLOR_STR]
        handler(self.plot_id_i, self.delta_id_list[0])
        handler(self.plot_id_i, self.delta_id_list[0])
        self.assertEqual(self.undo_depth(), depth_i)
        self.assertEqual(self.drawn_delta_colors(), [MARKER_COLOR_STR] * 2)

    @covers("LLFR-00172", "LLFR-00409")
    def test_first_point_dot_keeps_the_marker_color(self) -> None:
        """After a marker got another color, a new first point and a new
        delta marker still use the reserved marker color: the first
        point is only a point, its color is the view's (LLFR-00172), and
        the new marker is drawn in the marker color.

        Inputs: none.
        Outputs: none.
        """
        self.view.handler_dict["delta_marker_color_handler"](
            self.plot_id_i, self.delta_id_list[0], "#00aa00")
        self.view.handler_dict["plot_tool"](DELTA_X_TOOL_STR)
        for name_str, time_s in (("s1", 3.0), ("s2", 4.0)):
            value_f = float(self.signal_file.signal_array(name_str)[
                int(time_s)])
            self.view.handler_dict["delta_point_pick_handler"](
                self.plot_id_i, name_str, time_s, value_f)
        self.assertEqual(self.drawn_delta_colors(),
                         ["#00aa00", MARKER_COLOR_STR, MARKER_COLOR_STR])
