"""GUI tests of the "Delete all ..." menu options (HLFR-00093, LLFR-00046,
LLFR-00090, LLFR-00175, LLFR-00314, LLFR-00412 to LLFR-00417) and of the
double-click on a text note (LLFR-00411).

The plot widget tests drive the matplotlib callbacks that real mouse
events reach and replace ``execute_menu``, so no modal menu is ever
opened. The end-to-end tests use a real MainWindow and MainController
with a patched file dialog.
"""

import os
import tempfile
import unittest
from unittest import mock

import numpy as np

from tests.support import (
    OPEN_FILE_DIALOG_TARGET_STR, covers, get_qt_application, requires_qt)
from tests.view.menu_texts import (
    menu_option_texts,
    AREA_MENU_TEXT_LIST, DELTA_MENU_TEXT_LIST, FLAG_MENU_TEXT_LIST,
    TIP_MENU_TEXT_LIST)
from tests.view.test_plot_tools import (
    ALL_TOOL_TUPLE, GRAB_TOOL_TUPLE, PlotWidgetToolTestCase, recorder)
from tests.view.test_text_notes_view import (
    EMPTY_PLACE_TUPLE, TextNoteWidgetTestCase, all_menu_actions)

from controller.plot_tools import (
    AREA_TOOL_STR, DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR, MARKER_TOOL_STR,
    NO_TOOL_STR, TEXT_TOOL_STR)

FILE_TEXT_STR = (
    "Time,speed,force\n"
    "0,0,1\n0.5,1,0\n1,2,-1\n1.5,3,0\n2,4,1\n")
# The six "Delete all" requests of the plot widget and the texts of the
# options that emit them.
DELETE_ALL_SIGNAL_DICT = {
    "Delete all data tips in this plot":
        "plot_pinned_tips_delete_requested",
    "Delete all data tips in all plots": "all_pinned_tips_delete_requested",
    "Delete all delta markers in this plot":
        "plot_delta_markers_delete_requested",
    "Delete all delta markers in all plots":
        "all_delta_markers_delete_requested",
    "Delete all flags": "all_markers_delete_requested",
    "Delete all areas": "all_areas_delete_requested",
}


@requires_qt
class DeleteAllMenuTest(PlotWidgetToolTestCase):
    """The menus list the "Delete all" options in the required order, and
    each option emits its own request once."""

    def setUp(self) -> None:
        """Record every request of the plot widget.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.request_dict = {
            text_str: recorder(getattr(self.plot_widget, signal_name_str))
            for text_str, signal_name_str in DELETE_ALL_SIGNAL_DICT.items()}
        self.single_delete_list = []
        for signal_name_str in (
                "pinned_tip_delete_requested", "marker_delete_requested",
                "delta_marker_delete_requested", "area_delete_requested",
                "plot_delete_requested"):
            getattr(self.plot_widget, signal_name_str).connect(
                lambda *argument_tuple, name_str=signal_name_str:
                self.single_delete_list.append(name_str))

    def menu_texts(self, time_s: float, value_f: float,
                   chosen_text_str: str = "") -> list:
        """Right-click at a data point and choose an option.

        Inputs:
            time_s: x value.
            value_f: y value.
            chosen_text_str: text of the option to choose, "" for none.
        Outputs: the texts of the top-level options of the menu.
        """
        shown_list = []

        def fake_execute_menu(menu, global_point):
            """Record the menu and return the chosen action.

            Inputs:
                menu: the QMenu that would be shown.
                global_point: QPoint in screen coordinates.
            Outputs: the matching QAction, or None.
            """
            shown_list.extend(menu_option_texts(menu))
            for action in all_menu_actions(menu):
                if action.text() == chosen_text_str:
                    return action
            return None

        self.plot_widget.execute_menu = fake_execute_menu
        self.plot_widget.show_context_menu(self.point_at(time_s, value_f))
        self.application.processEvents()
        return shown_list

    def assert_only_request(self, text_str: str) -> None:
        """Check that only the request of one option was emitted, once.

        Inputs:
            text_str: the text of the chosen option.
        Outputs: none.
        """
        for option_str, record_list in self.request_dict.items():
            with self.subTest(option=option_str):
                self.assertEqual(record_list,
                                 [()] if option_str == text_str else [])
        self.assertEqual(self.single_delete_list, [])

    def check_menu(self, time_s: float, value_f: float,
                   expected_list: list) -> None:
        """Check a menu with every tool, then choose each of its "Delete
        all" options.

        Inputs:
            time_s: x value of the right-clicked item.
            value_f: y value of the right-clicked item.
            expected_list: the texts the menu must show, in order.
        Outputs: none.
        """
        for tool_str in ALL_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.assertEqual(self.menu_texts(time_s, value_f),
                                 expected_list)
        self.plot_widget.set_plot_tool(NO_TOOL_STR)
        self.assert_only_request("")
        for text_str in expected_list:
            if text_str not in DELETE_ALL_SIGNAL_DICT:
                continue
            for record_list in self.request_dict.values():
                record_list.clear()
            self.menu_texts(time_s, value_f, text_str)
            self.assert_only_request(text_str)

    @covers("LLFR-00046", "LLFR-00412", "LLFR-00413")
    def test_pinned_tip_menu(self) -> None:
        """Delete, then the two "Delete all data tips" options.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_pinned_tips([("Ramp", 5.0, 3.5),
                                          ("Sine", 2.0, float(np.sin(2.0)))])
        self.draw()
        self.check_menu(5.0, 3.5, TIP_MENU_TEXT_LIST)
        self.assertEqual(TIP_MENU_TEXT_LIST[:3],
                         ["Delete", "Delete all data tips in this plot",
                          "Delete all data tips in all plots"])

    @covers("LLFR-00090", "LLFR-00416", "LLFR-00391")
    def test_flag_menu(self) -> None:
        """"Delete all flags" directly follows "Delete".

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_markers([(3, "Flag 1", 5.0), (4, "Flag 2", 8.0)])
        self.draw()
        self.check_menu(5.0, 2.0, FLAG_MENU_TEXT_LIST)
        delete_index_i = FLAG_MENU_TEXT_LIST.index("Delete")
        self.assertEqual(FLAG_MENU_TEXT_LIST[delete_index_i + 1],
                         "Delete all flags")

    @covers("LLFR-00175", "LLFR-00414", "LLFR-00415")
    def test_delta_marker_menu(self) -> None:
        """Delete, then the two "Delete all delta markers" options.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_delta_markers([
            (6, "y", ("Ramp", 4.5, 3.45),
             ("Sine", 4.5, float(np.sin(4.5))), 0.0),
            (7, "x", ("Ramp", 7.0, 3.7), ("Ramp", 9.0, 3.9), 2.0)])
        self.draw()
        self.check_menu(4.5, 3.45, DELTA_MENU_TEXT_LIST)
        delete_index_i = DELTA_MENU_TEXT_LIST.index("Delete")
        self.assertEqual(DELTA_MENU_TEXT_LIST[delete_index_i:],
                         ["Delete", "Delete all delta markers in this plot",
                          "Delete all delta markers in all plots"])

    @covers("LLFR-00314", "LLFR-00417")
    def test_area_menu(self) -> None:
        """Rename, Color, Delete, Delete all areas, Position, Delete plot.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_areas([(1, "Area 1", 3.0, 5.0),
                                    (2, "Area 2", 7.0, 8.0)])
        self.draw()
        self.check_menu(4.0, 2.0, AREA_MENU_TEXT_LIST)
        self.assertEqual(AREA_MENU_TEXT_LIST,
                         ["Rename", "Color", "Delete", "Delete all areas",
                          "Position", "Delete plot"])

    @covers("LLFR-00048", "LLFR-00038")
    def test_other_menus_have_no_delete_all(self) -> None:
        """The curve menu and the empty plot menu show no "Delete all".

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.menu_texts(8.0, 3.8),
                         ["Delete signal", "Width"])
        self.assertEqual(self.menu_texts(8.0, 2.0),
                         ["Position", "Delete plot"])


@requires_qt
class DoubleClickTextNoteTest(TextNoteWidgetTestCase):
    """A double-click on a text note opens its Edit field (LLFR-00411)."""

    def setUp(self) -> None:
        """Draw one note over the ramp curve, a flag and an area, and
        record the other requests.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        self.area_create_list = recorder(
            self.plot_widget.area_create_requested)
        self.area_change_list = recorder(
            self.plot_widget.area_change_requested)
        self.arrow_create_list = recorder(
            self.plot_widget.arrow_create_requested)
        self.arrow_change_list = recorder(
            self.plot_widget.arrow_change_requested)
        self.marker_move_list = recorder(
            self.plot_widget.marker_move_requested)
        self.plot_delete_list = recorder(
            self.plot_widget.plot_delete_requested)
        self.drop_list = recorder(self.plot_widget.signals_dropped)
        self.note_tuple = ("double-click me", 5.0, 3.5)

    def double_click_display(self, display_tuple: tuple) -> None:
        """Send the four events of a left double-click at a point.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton
        self.send("button_press_event", display_tuple, MouseButton.LEFT)
        self.send("button_release_event", display_tuple, MouseButton.LEFT)
        self.send("button_press_event", display_tuple, MouseButton.LEFT,
                  double_click_b=True)
        self.send("button_release_event", display_tuple, MouseButton.LEFT)
        self.application.processEvents()

    def assert_nothing_else(self, range_tuple: tuple) -> None:
        """Check that no request other than the edit field was made.

        Inputs:
            range_tuple: the time range shown before the double-click.
        Outputs: none.
        """
        for record_list in (
                self.create_list, self.move_list, self.edit_list,
                self.delete_list, self.marker_place_list, self.delta_list,
                self.tip_move_list, self.pin_list, self.range_list,
                self.area_create_list, self.area_change_list,
                self.arrow_create_list, self.arrow_change_list,
                self.marker_move_list, self.plot_delete_list,
                self.drop_list):
            self.assertEqual(record_list, [])
        self.assertEqual(self.plot_widget.time_range_tuple(), range_tuple)
        self.assertFalse(self.plot_widget.is_mouse_drag_in_progress())
        self.assertFalse(self.plot_widget.time_span_line_shown())
        self.assertFalse(self.plot_widget.area_preview_shown())
        self.assertFalse(self.plot_widget.arrow_preview_shown())
        self.assertEqual(self.plot_widget.delta_first_point_tuple, ())
        self.assertEqual(self.plot_widget.text_note_list[0][:3],
                         self.note_tuple)

    @covers("LLFR-00411", "LLFR-00342", "LLFR-00339", "LLFR-00825")
    def test_double_click_with_every_tool_opens_edit(self) -> None:
        """With any plot tool or none, except the tools whose preview
        places an object there (LLFR-01248), the double-click opens the
        field of "Edit" over the note, with its text and the keyboard
        focus, and does nothing else.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_markers([(1, "Flag 1", 5.0)])
        self.plot_widget.set_areas([(2, "Area 1", 4.0, 6.0)])
        for tool_str in GRAB_TOOL_TUPLE:
            with self.subTest(tool=tool_str):
                self.plot_widget.set_text_notes([self.note_tuple])
                self.plot_widget.set_plot_tool(tool_str)
                self.draw()
                range_tuple = self.plot_widget.time_range_tuple()
                box = self.plot_widget.text_note_box_extent(0)
                self.double_click_display(self.note_center())
                self.assertTrue(self.editor.isVisible())
                self.assertEqual(self.editor.text(), self.note_tuple[0])
                self.assertIs(self.application.focusWidget(), self.editor)
                self.assertEqual(self.plot_widget.editor_note_index_i, 0)
                # The same place as the field of "Edit".
                left_point = self.plot_widget.display_to_widget_point(
                    float(box.x0), float(box.y0))
                self.assertLessEqual(abs(self.editor.geometry().left()
                                         - left_point.x()), 2)
                self.assert_nothing_else(range_tuple)
                self.assertEqual(self.plot_widget.plot_tool_str, tool_str)
                self.assertEqual(self.plot_widget.marker_time_s(1), 5.0)
                self.assertEqual(self.plot_widget.area_drawn_span_tuple(2),
                                 (4.0, 6.0))
                self.type_and_press("", "Key_Escape")
                self.assertFalse(self.editor.isVisible())
                self.assertEqual(self.edit_list, [])

    @covers("LLFR-01248", "LLFR-00825", "LLFR-00411", "LLFR-00081")
    def test_double_click_with_the_flag_tool_places_then_edits(self) -> None:
        """With the Flag tool, the first press of a double-click on a
        note places the flag of the preview (LLFR-01248), and the second
        press opens the field of "Edit".

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_text_notes([self.note_tuple])
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.draw()
        self.marker_place_list.clear()
        self.double_click_display(self.note_center())
        self.assertEqual(len(self.marker_place_list), 1)
        self.assertTrue(self.editor.isVisible())
        self.assertEqual(self.plot_widget.editor_note_index_i, 0)
        self.type_and_press("", "Key_Escape")
        self.assertEqual(self.edit_list, [])

    @covers("LLFR-00411", "LLFR-00342", "LLFR-00746")
    def test_double_click_then_enter_edits_the_text(self) -> None:
        """Enter in the field asks for the new text, as with "Edit"; a
        blank text asks for nothing.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_text_notes([self.note_tuple])
        self.plot_widget.set_plot_tool(TEXT_TOOL_STR)
        self.draw()
        self.double_click_display(self.note_center())
        self.type_and_press("new text", "Key_Return")
        self.assertEqual(self.edit_list, [(0, "new text")])
        self.assertEqual(self.create_list, [])
        self.double_click_display(self.note_center())
        self.type_and_press("   ", "Key_Return")
        self.assertEqual(self.edit_list, [(0, "new text")])

    @covers("LLFR-00411")
    def test_double_click_on_the_last_drawn_note(self) -> None:
        """Where two notes overlap, the one drawn last is edited.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_text_notes([self.note_tuple,
                                         ("on top", 5.0, 3.5)])
        self.draw()
        self.double_click_display(self.note_center(1))
        self.assertEqual(self.plot_widget.editor_note_index_i, 1)
        self.assertEqual(self.editor.text(), "on top")
        self.type_and_press("", "Key_Escape")

    @covers("LLFR-00411", "LLFR-00045", "LLFR-00078")
    def test_double_click_elsewhere_opens_no_field(self) -> None:
        """A double-click away from any note opens no field, and its
        second press still does nothing (no second pin or zoom).

        Inputs: none.
        Outputs: none.
        """
        for tool_str in (NO_TOOL_STR, MARKER_TOOL_STR, AREA_TOOL_STR,
                         DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR):
            with self.subTest(tool=tool_str):
                self.plot_widget.set_plot_tool(tool_str)
                self.marker_place_list.clear()
                self.double_click_display(
                    self.display_of(*EMPTY_PLACE_TUPLE))
                self.assertFalse(self.plot_widget.text_note_editor_open_b)
                self.assertLessEqual(len(self.marker_place_list), 1)
                self.assertEqual(self.edit_list, [])


@requires_qt
class EndToEndTestCase(unittest.TestCase):
    """Base class: a real window with two tabs holding tips, delta
    markers, flags and areas."""

    def setUp(self) -> None:
        """Open a CSV, plot speed in Tab 1 and force in Tab 2, and add
        the items through the controller.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        path_str = os.path.join(self.temporary_folder.name, "all.csv")
        with open(path_str, "w", encoding="utf-8") as file:
            file.write(FILE_TEXT_STR)
        self.main_window = MainWindow()
        self.main_window.resize(1100, 800)
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.main_window.show()
        with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                        return_value=path_str):
            QTest.mouseClick(self.main_window.top_panel.open_file_button,
                             Qt.MouseButton.LeftButton)
            self.process_events()
        self.plot_controller = self.controller.plot_controller
        self.workspace = self.plot_controller.workspace
        self.main_window.signal_double_click_handler("file1_speed")
        self.plot_controller.on_add_tab()
        self.main_window.signal_double_click_handler("file1_force")
        self.process_events()
        self.plot_list = [tab.plot_list[0] for tab in self.workspace.tab_list]
        self.assertEqual(len(self.plot_list), 2)
        for plot, signal_name_str in zip(self.plot_list, ("file1_speed",
                                                          "file1_force")):
            values_array = self.plot_controller.signal_values(
                signal_name_str)
            self.plot_controller.on_tip_pin(plot.plot_id_i, signal_name_str,
                                            1.0, float(values_array[2]))
            self.plot_controller.on_plot_tool_changed(DELTA_X_TOOL_STR)
            for index_i in (1, 3):
                self.plot_controller.on_delta_point_pick(
                    plot.plot_id_i, signal_name_str, index_i * 0.5,
                    float(values_array[index_i]))
        first_plot_id_i = self.plot_list[0].plot_id_i
        self.plot_controller.on_plot_tool_changed(MARKER_TOOL_STR)
        self.plot_controller.on_marker_place(first_plot_id_i, 0.75)
        self.plot_controller.on_marker_place(first_plot_id_i, 1.25)
        self.plot_controller.on_plot_tool_changed(AREA_TOOL_STR)
        self.plot_controller.on_area_create(first_plot_id_i, 0.1, 0.3)
        self.plot_controller.on_area_create(first_plot_id_i, 1.6, 1.9)
        self.plot_controller.on_plot_tool_changed(NO_TOOL_STR)
        self.process_events()
        self.assertEqual(len(self.workspace.marker_list), 2)
        self.assertEqual(len(self.workspace.area_list), 2)
        for plot in self.plot_list:
            self.assertEqual(len(plot.pinned_tip_list), 1)
            self.assertEqual(len(plot.delta_marker_list), 1)

    def tearDown(self) -> None:
        """Close the window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.process_events()

    def process_events(self) -> None:
        """Let Qt run deferred work and draw the plots.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(3):
            self.application.processEvents()
        for plot_widget in (
                self.main_window.plot_panel.plot_widget_dict.values()):
            plot_widget.canvas.draw()

    def widget(self, plot):
        """Return the plot widget of a model plot.

        Inputs:
            plot: the model Plot.
        Outputs: the PlotWidget.
        """
        return self.main_window.plot_panel.plot_widget_dict[plot.plot_id_i]

    def state_tuple(self) -> tuple:
        """Return what the model and the widgets hold.

        Inputs: none.
        Outputs: (tips per plot, delta markers per plot, flags, areas),
            each count read from the model and from the widgets.
        """
        plot_list = [tab.plot_list[0] for tab in self.workspace.tab_list]
        return (
            [(len(plot.pinned_tip_list),
              self.widget(plot).pinned_tip_count()) for plot in plot_list],
            [(len(plot.delta_marker_list),
              len(self.widget(plot).delta_marker_id_list()))
             for plot in plot_list],
            [(len(self.workspace.marker_list),
              self.widget(plot).marker_count()) for plot in plot_list],
            [(len(self.workspace.area_list),
              len(self.widget(plot).area_id_list())) for plot in plot_list])

    def choose(self, plot, time_s: float, value_f: float,
               text_str: str) -> list:
        """Right-click a plot at a data point and choose an option.

        Inputs:
            plot: the model Plot of the right-clicked widget.
            time_s: x value.
            value_f: y value.
            text_str: text of the option to choose.
        Outputs: the texts of the menu shown.
        """
        plot_widget = self.widget(plot)
        shown_list = []

        def fake_execute_menu(menu, global_point):
            """Record the menu and return the chosen action.

            Inputs:
                menu: the QMenu that would be shown.
                global_point: QPoint in screen coordinates.
            Outputs: the matching QAction, or None.
            """
            shown_list.extend(menu_option_texts(menu))
            for action in all_menu_actions(menu):
                if action.text() == text_str:
                    return action
            return None

        plot_widget.execute_menu = fake_execute_menu
        plot_widget.show_context_menu(
            plot_widget.data_to_widget_point(time_s, value_f))
        self.process_events()
        return shown_list

    def run_and_undo(self, action, expected_tuple: tuple) -> None:
        """Run an action, check the state, undo, check, redo, check.

        Inputs:
            action: function without arguments.
            expected_tuple: the state_tuple expected after the action.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        before_tuple = self.state_tuple()
        with mock.patch.object(QMessageBox, "exec") as box_mock:
            action()
            self.process_events()
        # No confirmation and no message.
        self.assertEqual(box_mock.call_count, 0)
        self.assertEqual(self.state_tuple(), expected_tuple)
        self.main_window.run_undo()
        self.process_events()
        self.assertEqual(self.state_tuple(), before_tuple)
        self.main_window.run_redo()
        self.process_events()
        self.assertEqual(self.state_tuple(), expected_tuple)


@requires_qt
class DeleteAllEndToEndTest(EndToEndTestCase):
    """Each "Delete all" option in a real window, undo and redo."""

    @covers("LLFR-00413", "LLFR-00046", "LLFR-00140", "LLFR-00138",
            "LLFR-00192", "LLFR-00828", "LLFR-00878")
    def test_all_tips_from_the_menu(self) -> None:
        """"Delete all data tips in all plots", chosen on the tip of the
        shown tab, removes the tip of the hidden tab too.

        Inputs: none.
        Outputs: none.
        """
        plot = self.plot_list[1]
        tip = plot.pinned_tip_list[0]
        self.run_and_undo(
            lambda: self.assertEqual(
                self.choose(plot, tip.time_s, tip.value_f,
                            "Delete all data tips in all plots"),
                TIP_MENU_TEXT_LIST),
            ([(0, 0), (0, 0)], [(1, 1), (1, 1)], [(2, 2), (2, 2)],
             [(2, 2), (2, 2)]))

    @covers("LLFR-00412", "LLFR-00414", "LLFR-00415", "LLFR-00416",
            "LLFR-00417", "LLFR-00140", "LLFR-00827", "LLFR-00877",
            "LLFR-00831", "LLFR-00879", "LLFR-00833", "LLFR-00880",
            "LLFR-00834", "LLFR-00881", "LLFR-00835", "LLFR-00882")
    def test_every_request_reaches_the_controller(self) -> None:
        """Each "Delete all" request of a plot widget runs its action on
        the model and on every plot widget, as one undoable action.

        Inputs: none.
        Outputs: none.
        """
        def emit_from_first_plot(signal_name_str: str) -> None:
            """Emit a request from the plot widget of Tab 1, as shown now
            (an undo may have built it again).

            Inputs:
                signal_name_str: the name of the request signal.
            Outputs: none.
            """
            getattr(self.widget(self.workspace.tab_list[0].plot_list[0]),
                    signal_name_str).emit()
        case_list = [
            ("plot_pinned_tips_delete_requested",
             ([(0, 0), (1, 1)], [(1, 1), (1, 1)], [(2, 2), (2, 2)],
              [(2, 2), (2, 2)])),
            ("plot_delta_markers_delete_requested",
             ([(1, 1), (1, 1)], [(0, 0), (1, 1)], [(2, 2), (2, 2)],
              [(2, 2), (2, 2)])),
            ("all_delta_markers_delete_requested",
             ([(1, 1), (1, 1)], [(0, 0), (0, 0)], [(2, 2), (2, 2)],
              [(2, 2), (2, 2)])),
            ("all_markers_delete_requested",
             ([(1, 1), (1, 1)], [(1, 1), (1, 1)], [(0, 0), (0, 0)],
              [(2, 2), (2, 2)])),
            ("all_areas_delete_requested",
             ([(1, 1), (1, 1)], [(1, 1), (1, 1)], [(2, 2), (2, 2)],
              [(0, 0), (0, 0)])),
        ]
        for signal_name_str, expected_tuple in case_list:
            with self.subTest(request=signal_name_str):
                self.run_and_undo(
                    lambda name_str=signal_name_str:
                    emit_from_first_plot(name_str),
                    expected_tuple)
                self.main_window.run_undo()
                self.process_events()


@requires_qt
class DoubleClickEndToEndTest(EndToEndTestCase):
    """A real window: a double-click on a text note edits it and creates
    no plot (LLFR-00411)."""

    @covers("LLFR-00411", "LLFR-00342", "LLFR-00140", "LLFR-00825")
    def test_double_click_edits_the_note_and_creates_no_plot(self) -> None:
        """The edited text reaches the model as one undoable action; the
        plots, tips and markers do not change.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.backend_bases import MouseButton, MouseEvent
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        plot = self.plot_list[1]
        self.plot_controller.on_text_note_create(plot.plot_id_i, "old",
                                                 1.0, 0.5)
        self.process_events()
        plot_widget = self.widget(plot)
        box = plot_widget.text_note_box_extent(0)
        center_tuple = ((float(box.x0) + float(box.x1)) / 2.0,
                        (float(box.y0) + float(box.y1)) / 2.0)
        before_tuple = self.state_tuple()
        plot_count_i = sum(len(tab.plot_list)
                           for tab in self.workspace.tab_list)
        for name_str, double_click_b in (
                ("button_press_event", False),
                ("button_release_event", False),
                ("button_press_event", True),
                ("button_release_event", False)):
            event = MouseEvent(name_str, plot_widget.canvas,
                               center_tuple[0], center_tuple[1],
                               button=MouseButton.LEFT,
                               dblclick=double_click_b)
            plot_widget.canvas.callbacks.process(name_str, event)
        self.process_events()
        editor = plot_widget.text_note_editor
        self.assertTrue(editor.isVisible())
        self.assertEqual(editor.text(), "old")
        QTest.keyClicks(editor, "new")
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.process_events()
        self.assertEqual(plot.text_note_list[0].text_str, "new")
        self.assertEqual(sum(len(tab.plot_list)
                             for tab in self.workspace.tab_list),
                         plot_count_i)
        self.assertEqual(self.state_tuple(), before_tuple)
        self.main_window.run_undo()
        self.process_events()
        plot = self.workspace.find_plot(plot.plot_id_i)
        self.assertEqual(plot.text_note_list[0].text_str, "old")


if __name__ == "__main__":
    unittest.main()
