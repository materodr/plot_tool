"""Tests for the shared color picker, the flag colors and the text note
style in the view (issue #152): HLFR-00086 to HLFR-00089.

No modal dialog or menu is ever opened: QColorDialog.exec is patched,
menus are built and their actions triggered directly, and the color
picker of MainWindow is replaced in the end-to-end tests.
"""

import os
import unittest
from unittest import mock

import numpy as np

from tests.support import covers, get_qt_application, requires_qt
from tests.view.menu_texts import FLAG_MENU_TEXT_LIST, menu_option_texts
from tests.view.test_plot_tools import PlotWidgetToolTestCase, recorder

from controller.plot_tools import MARKER_TOOL_STR
from model.curve_colors import MARKER_COLOR_STR

# The source folder, to check which modules use QColorDialog.
SOURCE_FOLDER_STR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "src")


def to_hex_str(color_value) -> str:
    """Return a matplotlib color as "#rrggbb".

    Inputs:
        color_value: any matplotlib color.
    Outputs: the color in lowercase "#rrggbb".
    """
    from matplotlib.colors import to_hex
    return to_hex(color_value)


def menu_action_dict(menu) -> dict:
    """Return the actions of a menu and its submenus by their text.

    Inputs:
        menu: a QMenu.
    Outputs: a dict text -> QAction; submenu actions are keyed
        "<submenu text>/<action text>".
    """
    action_dict = {}
    for action in menu.actions():
        action_dict[action.text()] = action
        if action.menu() is not None:
            for sub_action in action.menu().actions():
                action_dict[f"{action.text()}/{sub_action.text()}"] = (
                    sub_action)
    return action_dict


class SharedPickerSourceTest(unittest.TestCase):
    """One picker for every item (LLFR-00388). No Qt is needed."""

    @covers("LLFR-00388", "LLFR-00809")
    def test_only_the_picker_module_uses_qcolordialog(self) -> None:
        """QColorDialog appears only in view/color_picker.py, and the
        main window's ask_color calls its pick_color, so every "Color"
        option opens the same picker window.

        Inputs: none.
        Outputs: none.
        """
        user_list = []
        for folder_str, _, file_name_list in os.walk(SOURCE_FOLDER_STR):
            for file_name_str in file_name_list:
                if not file_name_str.endswith(".py"):
                    continue
                path_str = os.path.join(folder_str, file_name_str)
                with open(path_str, encoding="utf-8") as source_file:
                    if "QColorDialog" in source_file.read():
                        user_list.append(file_name_str)
        self.assertEqual(user_list, ["color_picker.py"])
        with open(os.path.join(SOURCE_FOLDER_STR, "view", "main_window.py"),
                  encoding="utf-8") as source_file:
            self.assertIn("color_picker.pick_color(", source_file.read())


@requires_qt
class ColorPickerTest(unittest.TestCase):
    """The color picker window (LLFR-00388 to LLFR-00390)."""

    def setUp(self) -> None:
        """Start the Qt application.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()

    @covers("LLFR-00389", "LLFR-00388", "LLFR-00810")
    def test_starts_at_the_current_color_without_alpha(self) -> None:
        """The window shows the item's color as chosen and has no alpha
        channel, so every color is opaque; an unusable start is black.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QColorDialog
        from view.color_picker import build_color_dialog
        dialog = build_color_dialog(None, "#1F77B4")
        self.assertEqual(dialog.currentColor().name(), "#1f77b4")
        self.assertFalse(dialog.testOption(
            QColorDialog.ColorDialogOption.ShowAlphaChannel))
        self.assertTrue(dialog.windowTitle())
        dialog.deleteLater()
        dialog = build_color_dialog(None, "not a color")
        self.assertEqual(dialog.currentColor().name(), "#000000")
        dialog.deleteLater()

    @covers("LLFR-00390", "LLFR-00388", "LLFR-00810")
    def test_confirm_returns_the_opaque_color_and_cancel_none(self) -> None:
        """Confirming gives the chosen color in lowercase "#rrggbb",
        opaque even if the window held a see-through color; cancelling
        gives None.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor
        from PyQt6.QtWidgets import QColorDialog, QDialog
        from view import color_picker
        from tests.view.test_recent_colors_view import isolate_recent_colors
        isolate_recent_colors(self)
        start_list = []

        def accept(dialog) -> int:
            """Choose a half see-through teal and confirm.

            Inputs:
                dialog: the QColorDialog.
            Outputs: the Accepted code.
            """
            start_list.append(dialog.currentColor().name())
            dialog.setCurrentColor(QColor(18, 171, 52, 128))
            return QDialog.DialogCode.Accepted

        with mock.patch.object(QColorDialog, "exec", accept):
            self.assertEqual(color_picker.pick_color(None, "#ff8000"),
                             "#12ab34")
        self.assertEqual(start_list, ["#ff8000"])

        def reject(dialog) -> int:
            """Choose a color and cancel.

            Inputs:
                dialog: the QColorDialog.
            Outputs: the Rejected code.
            """
            dialog.setCurrentColor(QColor(1, 2, 3))
            return QDialog.DialogCode.Rejected

        with mock.patch.object(QColorDialog, "exec", reject):
            self.assertIsNone(color_picker.pick_color(None, "#ff8000"))

    @covers("LLFR-00388", "LLFR-00389", "LLFR-00809")
    def test_main_window_asks_the_shared_picker(self) -> None:
        """MainWindow.ask_color passes the current color to pick_color
        and returns its answer.

        Inputs: none.
        Outputs: none.
        """
        from view.main_window import MainWindow
        main_window = MainWindow()
        try:
            with mock.patch("view.color_picker.pick_color",
                            return_value="#123456") as pick_mock:
                self.assertEqual(main_window.ask_color("#abcdef"),
                                 "#123456")
            self.assertEqual(pick_mock.call_args.args[1], "#abcdef")
            self.assertIs(pick_mock.call_args.args[0], main_window)
        finally:
            main_window.close()
            main_window.deleteLater()
            self.application.processEvents()


@requires_qt
class FlagColorViewTest(PlotWidgetToolTestCase):
    """A flag drawn in its color, and its menu (LLFR-00391, LLFR-00392)."""

    def flag_colors(self, flag_id_i: int) -> list:
        """Return the colors of a flag's line, label and time value.

        Inputs:
            flag_id_i: id of the flag.
        Outputs: a list of three "#rrggbb".
        """
        line, label, time_text = self.plot_widget.marker_artist_tuple(
            flag_id_i)
        return [to_hex_str(line.get_color()), to_hex_str(label.get_color()),
                to_hex_str(time_text.get_color())]

    @covers("LLFR-00392", "LLFR-00083", "LLFR-00084", "LLFR-00092",
            "LLFR-00813")
    def test_line_label_and_time_in_the_flag_color(self) -> None:
        """Each flag's line, name label and time value are drawn in its
        own color; a flag without a usable color in the default color.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_markers([
            (1, "Flag 1", 2.0, "#1F77B4"), (2, "Flag 2", 4.0),
            (3, "Flag 3", 6.0, "violet"), (4, "Flag 4", 8.0, "#000000")])
        self.draw()
        self.assertEqual(self.flag_colors(1), ["#1f77b4"] * 3)
        self.assertEqual(self.flag_colors(2), [MARKER_COLOR_STR] * 3)
        self.assertEqual(self.flag_colors(3), [MARKER_COLOR_STR] * 3)
        self.assertEqual(self.flag_colors(4), ["#000000"] * 3)

    @covers("LLFR-00083", "LLFR-00203", "LLFR-00172", "LLFR-00660")
    def test_preview_and_delta_markers_keep_the_marker_color(self) -> None:
        """Whatever the flags' colors, the flag preview stays the pale
        marker color and the delta markers the marker color.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import MARKER_PREVIEW_COLOR_STR
        self.plot_widget.set_markers([(1, "Flag 1", 2.0, "#1f77b4")])
        self.plot_widget.set_delta_markers([
            (5, "x", ("Ramp", 6.0, 3.6), ("Ramp", 7.0, 3.7), 1.0)])
        self.plot_widget.set_plot_tool(MARKER_TOOL_STR)
        self.draw()
        self.plot_widget.show_marker_preview(5.0)
        self.assertEqual(to_hex_str(self.plot_widget.preview_line.get_color()),
                         MARKER_PREVIEW_COLOR_STR)
        bracket = self.plot_widget.delta_artist_tuple(5)[0]
        self.assertEqual(to_hex_str(bracket.get_edgecolor()),
                         MARKER_COLOR_STR)

    @covers("LLFR-00391", "LLFR-00087", "LLFR-00090", "LLFR-00392")
    def test_color_option_between_rename_and_delete(self) -> None:
        """The flag menu is Rename, Color, Delete; Color asks for the
        picker with the flag's id.

        Inputs: none.
        Outputs: none.
        """
        color_list = recorder(self.plot_widget.marker_color_requested)
        self.plot_widget.set_markers([(7, "Flag 1", 5.0, "#00aa00")])
        self.draw()
        menu = self.plot_widget.build_context_menu(self.point_at(5.0, 2.0))
        self.assertEqual(menu_option_texts(menu),
                         FLAG_MENU_TEXT_LIST)
        menu_action_dict(menu)["Color/Other color..."].trigger()
        self.assertEqual(color_list, [(7, "")])
        menu.deleteLater()


@requires_qt
class TextNoteStyleViewTest(PlotWidgetToolTestCase):
    """The look, size and menu of a text note (LLFR-00336, LLFR-00341,
    LLFR-00385 to LLFR-00387)."""

    def note_box(self):
        """Return the box of the first note, as drawn now.

        Inputs: none.
        Outputs: a matplotlib Bbox in display pixels.
        """
        return self.plot_widget.text_note_box_extent(0)

    def note_menu(self):
        """Build the menu of a right-click on the first note.

        Inputs: none.
        Outputs: the QMenu (not shown).
        """
        box = self.note_box()
        point = self.plot_widget.display_to_widget_point(
            (float(box.x0) + float(box.x1)) / 2.0,
            (float(box.y0) + float(box.y1)) / 2.0)
        return self.plot_widget.build_context_menu(point)

    def resize_to(self, height_i: int) -> None:
        """Resize the plot widget and draw it.

        Inputs:
            height_i: the new height, in pixels.
        Outputs: none.
        """
        self.plot_widget.resize(600, height_i)
        for _ in range(3):
            self.application.processEvents()
        self.plot_widget.canvas.draw()

    def height_limit_px(self) -> float:
        """Return 25% of the height of the drawing area.

        Inputs: none.
        Outputs: the height in display pixels.
        """
        return 0.25 * float(self.plot_widget.axes.bbox.height)

    @covers("LLFR-00336", "LLFR-00385", "LLFR-00739", "LLFR-00740",
            "LLFR-00803")
    def test_white_rounded_box_with_the_default_colors(self) -> None:
        """A new note is #24303b text at 12 points on a white rounded box
        with an orange #ff8000 border, the box of a pinned data tip.

        Inputs: none.
        Outputs: none.
        """
        from view import theme
        self.plot_widget.set_text_notes([("Readable", 5.0, 2.0)])
        self.draw()
        annotation = self.plot_widget.text_note_annotation(0)
        patch = annotation.get_bbox_patch()
        self.assertEqual(to_hex_str(patch.get_facecolor()), "#ffffff")
        self.assertEqual(to_hex_str(patch.get_edgecolor()), "#ff8000")
        self.assertEqual(to_hex_str(annotation.get_color()), "#24303b")
        self.assertEqual(annotation.get_fontsize(), 12.0)
        self.assertEqual(patch.get_boxstyle().__class__.__name__, "Round")
        self.assertEqual(patch.get_linewidth(),
                         theme.PINNED_TIP_BOX_DICT["linewidth"])

    @covers("LLFR-00336", "LLFR-00387", "LLFR-00385", "LLFR-00739",
            "LLFR-00802", "LLFR-00808")
    def test_each_note_in_its_own_size_and_colors(self) -> None:
        """Each note is drawn with its size, border color and text color;
        the box stays white.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_text_notes([
            ("Red border", 2.0, 2.0, 8, "#ff0000", "#24303b"),
            ("Blue text", 6.0, 2.0, 16, "#24303b", "#0000FF")])
        self.draw()
        first = self.plot_widget.text_note_annotation(0)
        second = self.plot_widget.text_note_annotation(1)
        self.assertEqual(to_hex_str(first.get_bbox_patch().get_edgecolor()),
                         "#ff0000")
        self.assertEqual(to_hex_str(first.get_color()), "#24303b")
        self.assertEqual(first.get_fontsize(), 8.0)
        self.assertEqual(to_hex_str(second.get_color()), "#0000ff")
        self.assertEqual(second.get_fontsize(), 16.0)
        for annotation in (first, second):
            self.assertEqual(
                to_hex_str(annotation.get_bbox_patch().get_facecolor()),
                "#ffffff")
        self.assertGreater(self.plot_widget.text_note_box_extent(1).height,
                           self.plot_widget.text_note_box_extent(0).height)

    @covers("LLFR-00341", "LLFR-00385", "LLFR-00387", "LLFR-00802")
    def test_menu_size_presets_and_color_requests(self) -> None:
        """The menu is Edit, Size, Border color, Text color, Delete; Size
        lists the presets with the chosen one checked; each option asks
        for its change with the note's index.

        Inputs: none.
        Outputs: none.
        """
        size_list = recorder(self.plot_widget.text_note_size_requested)
        border_list = recorder(
            self.plot_widget.text_note_border_color_requested)
        text_list = recorder(self.plot_widget.text_note_text_color_requested)
        self.plot_widget.set_text_notes([("Note", 5.0, 2.0, 20, "#24303b",
                                          "#24303b")])
        self.draw()
        menu = self.note_menu()
        self.assertEqual(menu_option_texts(menu),
                         ["Edit", "Size", "Border color", "Text color",
                          "Text background", "Width", "Line style",
                          "Delete"])
        action_dict = menu_action_dict(menu)
        size_action_list = action_dict["Size"].menu().actions()
        self.assertEqual([action.text() for action in size_action_list],
                         ["8", "10", "12", "16", "20", "24", "32"])
        self.assertEqual([action.text() for action in size_action_list
                          if action.isChecked()], ["20"])
        action_dict["Size/32"].trigger()
        action_dict["Border color/Other color..."].trigger()
        action_dict["Text color/Other color..."].trigger()
        self.assertEqual(size_list, [(0, 32)])
        self.assertEqual(border_list, [(0, "")])
        self.assertEqual(text_list, [(0, "")])
        menu.deleteLater()

    @covers("LLFR-00386", "LLFR-00385", "LLFR-00804", "LLFR-00805",
            "LLFR-00806", "LLFR-00807")
    def test_never_taller_than_a_quarter_of_the_plot(self) -> None:
        """A 32-point note in a short plot is drawn at the largest size
        that keeps it within 25% of the drawing area's height; the menu
        still shows 32 as chosen; when the plot grows, it is drawn at 32
        again, and it shrinks again when the plot shrinks.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_text_notes([("Big", 5.0, 2.0, 32, "#24303b",
                                          "#24303b")])
        self.resize_to(300)
        drawn_size_f = self.plot_widget.text_note_drawn_size_f(0)
        self.assertLess(drawn_size_f, 32.0)
        self.assertLessEqual(self.note_box().height,
                             self.height_limit_px() + 0.5)
        # The largest that fits: a little larger does not fit.
        annotation = self.plot_widget.text_note_annotation(0)
        renderer = self.plot_widget.canvas.get_renderer()
        self.assertGreater(self.plot_widget.text_note_height_px(
            annotation, drawn_size_f + 0.5, renderer),
            self.height_limit_px())
        annotation.set_fontsize(drawn_size_f)
        menu = self.note_menu()
        self.assertEqual([action.text() for action
                          in menu_action_dict(menu)["Size"].menu().actions()
                          if action.isChecked()], ["32"])
        menu.deleteLater()
        self.resize_to(1000)
        self.assertEqual(self.plot_widget.text_note_drawn_size_f(0), 32.0)
        self.assertLessEqual(self.note_box().height, self.height_limit_px())
        self.resize_to(200)
        self.assertLess(self.plot_widget.text_note_drawn_size_f(0),
                        drawn_size_f)
        self.assertLessEqual(self.note_box().height,
                             self.height_limit_px() + 0.5)

    @covers("LLFR-00386")
    def test_small_size_is_not_enlarged(self) -> None:
        """A note that fits is drawn at its chosen size, never larger.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_text_notes([("Small", 5.0, 2.0, 8, "#24303b",
                                          "#24303b")])
        self.resize_to(1000)
        self.assertEqual(self.plot_widget.text_note_drawn_size_f(0), 8.0)


@requires_qt
class ItemColorEndToEndTest(unittest.TestCase):
    """Flag colors and text note style through MainWindow and the real
    controllers, with the color picker answered by the test."""

    def setUp(self) -> None:
        """Create the window with a file, one plot in each of two tabs.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from controller.main_controller import MainController
        from model.signal_file import SignalFile
        from view.main_window import MainWindow
        self.main_window = MainWindow()
        self.main_window.resize(1100, 800)
        self.controller = MainController(self.main_window)
        self.controller.start()
        time_array = np.linspace(0.0, 4.0, 41)
        signal_file = SignalFile("memory.csv", {
            "Time": time_array, "speed": time_array * 2.0})
        self.controller.plot_controller.on_file_opened(signal_file, False)
        self.controller.signal_list_controller.on_file_opened(
            signal_file, False)
        self.main_window.show()
        self.main_window.signal_double_click_handler("speed")
        self.process_events()
        self.plot_controller = self.controller.plot_controller
        self.first_tab_id_i = self.main_window.current_tab_id()
        self.plot_widget = self.widgets()[0]
        self.main_window.plot_panel.request_add_tab()
        self.main_window.signal_double_click_handler("speed")
        self.main_window.set_current_tab(self.first_tab_id_i)
        self.process_events()
        self.question_list = []
        self.answer_list = []
        self.main_window.ask_color = self.fake_ask_color

    def tearDown(self) -> None:
        """Close the window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.process_events()

    def process_events(self) -> None:
        """Let Qt handle pending events and deferred calls.

        Inputs: none.
        Outputs: none.
        """
        for _ in range(3):
            self.application.processEvents()

    def fake_ask_color(self, current_color_str: str):
        """Answer the color picker with the next prepared answer.

        Inputs:
            current_color_str: the color the picker starts at.
        Outputs: the next answer, or None (cancelled) when there is none.
        """
        self.question_list.append(current_color_str)
        if not self.answer_list:
            return None
        return self.answer_list.pop(0)

    def widgets(self) -> list:
        """Return the plot widgets of every tab.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        return list(self.main_window.plot_panel.plot_widget_dict.values())

    def choose(self, widget_point, text_str: str) -> None:
        """Build the menu at a point and trigger one of its actions.

        Inputs:
            widget_point: QPoint in the plot widget.
            text_str: the action text, "<submenu>/<action>" in a submenu.
        Outputs: none.
        """
        self.plot_widget.canvas.draw()
        menu = self.plot_widget.build_context_menu(widget_point)
        menu_action_dict(menu)[text_str].trigger()
        menu.deleteLater()
        self.process_events()

    @covers("LLFR-00392", "LLFR-00205", "LLFR-00389", "LLFR-00390",
            "LLFR-00138", "LLFR-00192", "LLFR-00664", "LLFR-00811",
            "LLFR-00813")
    def test_flag_color_on_every_tab_with_undo(self) -> None:
        """"Color" on a flag opens the picker at its color; the confirmed
        color is drawn on the plots of both tabs; a cancel changes
        nothing; undo and redo follow.

        Inputs: none.
        Outputs: none.
        """
        self.plot_controller.on_plot_tool_changed(MARKER_TOOL_STR)
        self.plot_controller.on_marker_place(self.plot_widget.plot_id_i,
                                             2.0)
        self.process_events()
        flag_id_i = self.plot_controller.workspace.marker_list[0].marker_id_i
        point = self.plot_widget.data_to_widget_point(2.0, 4.0)

        def line_colors() -> list:
            """Return the color of the flag's line on every plot.

            Inputs: none.
            Outputs: a list of "#rrggbb".
            """
            return [to_hex_str(widget.marker_artist_tuple(flag_id_i)[0]
                               .get_color()) for widget in self.widgets()]

        depth_i = self.plot_controller.undo_history.depth()
        self.choose(point, "Color/Other color...")
        self.assertEqual(self.question_list, [MARKER_COLOR_STR])
        self.assertEqual(self.plot_controller.undo_history.depth(), depth_i)
        self.answer_list = ["#1F77B4"]
        self.choose(point, "Color/Other color...")
        self.assertEqual(line_colors(), ["#1f77b4", "#1f77b4"])
        self.main_window.run_undo()
        self.process_events()
        self.assertEqual(line_colors(), [MARKER_COLOR_STR] * 2)
        self.main_window.run_redo()
        self.process_events()
        self.assertEqual(line_colors(), ["#1f77b4", "#1f77b4"])

    @covers("LLFR-00385", "LLFR-00387", "LLFR-00389", "LLFR-00390",
            "LLFR-00138", "LLFR-00802", "LLFR-00808")
    def test_text_note_size_and_colors_with_undo(self) -> None:
        """Size, Border color and Text color change the drawn note, each
        as one undoable action.

        Inputs: none.
        Outputs: none.
        """
        self.plot_controller.on_text_note_create(
            self.plot_widget.plot_id_i, "Note", 2.0, 4.0)
        self.process_events()
        self.plot_widget.canvas.draw()

        def note_point():
            """Return the center of the note.

            Inputs: none.
            Outputs: QPoint in the plot widget.
            """
            box = self.plot_widget.text_note_box_extent(0)
            return self.plot_widget.display_to_widget_point(
                (float(box.x0) + float(box.x1)) / 2.0,
                (float(box.y0) + float(box.y1)) / 2.0)

        def drawn_style() -> tuple:
            """Return the drawn size, border color and text color.

            Inputs: none.
            Outputs: (size_f, border_color_str, text_color_str).
            """
            # An undo builds the plot widgets again.
            self.plot_widget = self.widgets()[0]
            self.plot_widget.canvas.draw()
            annotation = self.plot_widget.text_note_annotation(0)
            return (annotation.get_fontsize(), to_hex_str(
                annotation.get_bbox_patch().get_edgecolor()),
                to_hex_str(annotation.get_color()))

        self.choose(note_point(), "Size/16")
        self.answer_list = ["#ff0000", "#0000ff"]
        self.choose(note_point(), "Border color/Other color...")
        self.choose(note_point(), "Text color/Other color...")
        self.assertEqual(self.question_list, ["#ff8000", "#24303b"])
        self.assertEqual(drawn_style(), (16.0, "#ff0000", "#0000ff"))
        for expected_tuple in ((16.0, "#ff0000", "#24303b"),
                               (16.0, "#ff8000", "#24303b"),
                               (12.0, "#ff8000", "#24303b")):
            self.main_window.run_undo()
            self.process_events()
            self.assertEqual(drawn_style(), expected_tuple)


if __name__ == "__main__":
    unittest.main()
