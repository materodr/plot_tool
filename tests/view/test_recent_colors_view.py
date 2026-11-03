"""Tests for the recent colors of the color submenus, the delta marker
colors and the area label colors in the view (issue #167): HLFR-00088,
HLFR-00092, HLFR-00066.

The recent colors are kept in the app's settings (QSettings). Every test
that builds a color submenu or confirms a color uses
``isolate_recent_colors``, which points view.color_picker at an INI file
in a temporary folder, so the tests never read or change the settings of
the user and always start from a known list. No modal dialog or menu is
opened: menus are built and their actions triggered directly, and
QColorDialog.exec is patched.
"""

import os
import tempfile
import unittest
from unittest import mock

import numpy as np

from tests.support import covers, get_qt_application, requires_qt
from tests.view.menu_texts import DELTA_MENU_TEXT_LIST
from tests.view.test_plot_tools import PlotWidgetToolTestCase, recorder

from controller.plot_tools import (
    DELTA_X_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR)
from model.curve_colors import MARKER_COLOR_STR


def isolate_recent_colors(test_case, color_list=(), stored_value=None):
    """Use a settings file of the test for the recent colors.

    Inputs:
        test_case: the running unittest.TestCase; the settings file and
            the patch are removed when the test ends.
        color_list: the recent colors the file starts with, most recent
            first.
        stored_value: a raw value to store instead of color_list, for
            example one that is not a list of colors.
    Outputs: the path of the INI file.
    """
    from PyQt6.QtCore import QSettings
    from view import color_picker
    folder = tempfile.TemporaryDirectory()
    test_case.addCleanup(folder.cleanup)
    path_str = os.path.join(folder.name, "recent_colors.ini")
    patcher = mock.patch.object(color_picker, "settings_file_path_str",
                                path_str)
    patcher.start()
    test_case.addCleanup(patcher.stop)
    value = list(color_list) if stored_value is None else stored_value
    if value or stored_value is not None:
        settings = QSettings(path_str, QSettings.Format.IniFormat)
        settings.setValue(color_picker.RECENT_COLORS_KEY_STR, value)
        settings.sync()
    return path_str


def to_hex_str(color_value) -> str:
    """Return a matplotlib color as "#rrggbb".

    Inputs:
        color_value: any matplotlib color.
    Outputs: the color in lowercase "#rrggbb", without alpha.
    """
    from matplotlib.colors import to_hex
    return to_hex(color_value)


def submenu_entries(menu, title_str: str) -> list:
    """Return the entries of one submenu of a menu.

    Inputs:
        menu: the QMenu.
        title_str: the text of the submenu's option.
    Outputs: the list of QAction of the submenu.
    """
    for action in menu.actions():
        if action.text() == title_str and action.menu() is not None:
            return list(action.menu().actions())
    raise AssertionError(f"No submenu {title_str!r}.")


def swatch_color_str(action) -> str:
    """Return the color in the middle of an entry's swatch icon.

    Inputs:
        action: the QAction of a recent color.
    Outputs: "#rrggbb", or "" when the action has no icon.
    """
    from view.color_picker import SWATCH_SIZE_I
    icon = action.icon()
    if icon.isNull():
        return ""
    image = icon.pixmap(SWATCH_SIZE_I, SWATCH_SIZE_I).toImage()
    return image.pixelColor(image.width() // 2,
                            image.height() // 2).name()


@requires_qt
class RecentColorSettingsTest(unittest.TestCase):
    """The list kept in the settings (LLFR-00419)."""

    def setUp(self) -> None:
        """Start the application.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()

    @covers("LLFR-00419")
    def test_list_is_kept_between_launches(self) -> None:
        """Remembered colors are written to the settings file, most
        recent first, without repeats, at most 8, and read back by a new
        settings object as after a new launch.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QSettings
        from view import color_picker
        path_str = isolate_recent_colors(self)
        self.assertEqual(color_picker.recent_color_list(), [])
        for number_i in range(10):
            color_picker.remember_color(f"#0000{number_i:02X}")
        color_picker.remember_color("#000003")
        expected_list = ["#000003"] + [
            f"#0000{number_i:02x}" for number_i in (9, 8, 7, 6, 5, 4, 2)]
        self.assertEqual(color_picker.recent_color_list(), expected_list)
        stored_value = QSettings(path_str, QSettings.Format.IniFormat).value(
            color_picker.RECENT_COLORS_KEY_STR)
        self.assertEqual(list(stored_value), expected_list)

    @covers("LLFR-00419")
    def test_settings_that_cannot_be_read_give_no_color(self) -> None:
        """A stored value that is not a list of colors gives an empty
        list, and a list with wrong entries keeps only the colors.

        Inputs: none.
        Outputs: none.
        """
        from view import color_picker
        isolate_recent_colors(self, stored_value=5)
        self.assertEqual(color_picker.recent_color_list(), [])
        isolate_recent_colors(self, stored_value=["#AABBCC", "red"])
        self.assertEqual(color_picker.recent_color_list(), ["#aabbcc"])
        # A single color may come back as one text.
        isolate_recent_colors(self, stored_value="#010203")
        self.assertEqual(color_picker.recent_color_list(), ["#010203"])

    @covers("LLFR-00419")
    def test_settings_failure_never_raises(self) -> None:
        """When the settings cannot be opened, the list is empty and
        remembering a color does not raise.

        Inputs: none.
        Outputs: none.
        """
        from view import color_picker
        with mock.patch.object(color_picker, "open_settings",
                               side_effect=OSError("no settings")):
            self.assertEqual(color_picker.recent_color_list(), [])
            color_picker.remember_color("#123456")

    @covers("LLFR-00419", "LLFR-00390")
    def test_picker_confirm_puts_the_color_first(self) -> None:
        """A confirmed color, also the item's current color, goes first
        in the list; a cancelled picker changes nothing.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor
        from PyQt6.QtWidgets import QColorDialog, QDialog
        from view import color_picker
        isolate_recent_colors(self, ["#111111", "#ff8000"])

        def accept(dialog) -> int:
            """Confirm the color the picker started at.

            Inputs:
                dialog: the QColorDialog.
            Outputs: the Accepted code.
            """
            return QDialog.DialogCode.Accepted

        def reject(dialog) -> int:
            """Choose a color and cancel.

            Inputs:
                dialog: the QColorDialog.
            Outputs: the Rejected code.
            """
            dialog.setCurrentColor(QColor(1, 2, 3))
            return QDialog.DialogCode.Rejected

        with mock.patch.object(QColorDialog, "exec", accept):
            self.assertEqual(color_picker.pick_color(None, "#FF8000"),
                             "#ff8000")
        self.assertEqual(color_picker.recent_color_list(),
                         ["#ff8000", "#111111"])
        with mock.patch.object(QColorDialog, "exec", reject):
            self.assertIsNone(color_picker.pick_color(None, "#ff8000"))
        self.assertEqual(color_picker.recent_color_list(),
                         ["#ff8000", "#111111"])


@requires_qt
class ColorSubmenuTest(PlotWidgetToolTestCase):
    """The color submenu of every color option (LLFR-00388,
    LLFR-00419)."""

    RECENT_TUPLE = ("#00aa00", "#ffff00", "#123456")

    def setUp(self) -> None:
        """Use a settings file with three recent colors.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        isolate_recent_colors(self, self.RECENT_TUPLE)

    def option_list(self) -> list:
        """Draw one item of each kind and return its color options.

        Inputs: none.
        Outputs: a list of (name_str, widget_point, option_str, signal,
            item_i): where to right-click, the option's text, the signal
            its entries emit and the id or index they carry.
        """
        plot_widget = self.plot_widget
        plot_widget.set_markers([(7, "Flag 1", 5.0, "#00aa00")])
        plot_widget.set_areas([(4, "Area 1", 8.0, 9.5, "#ff8000")])
        plot_widget.set_arrows([(0.5, 1.8, 2.5, 1.8, "#24303b")])
        plot_widget.set_text_notes([("Note", 3.5, -0.5, 12, "#24303b",
                                     "#24303b")])
        plot_widget.set_delta_markers([
            (9, "y", ("Ramp", 6.5, 3.65), ("Ramp", 7.5, 3.75), 0.1)])
        self.draw()
        box = plot_widget.text_note_box_extent(0)
        note_point = plot_widget.display_to_widget_point(
            (box.x0 + box.x1) / 2.0, (box.y0 + box.y1) / 2.0)
        return [
            ("flag", self.point_at(5.0, 2.0), "Color",
             plot_widget.marker_color_requested, 7),
            ("area", self.point_at(9.0, 2.0), "Color",
             plot_widget.area_color_requested, 4),
            ("arrow", self.point_at(1.5, 1.8), "Color",
             plot_widget.arrow_color_requested, 0),
            ("border", note_point, "Border color",
             plot_widget.text_note_border_color_requested, 0),
            ("text", note_point, "Text color",
             plot_widget.text_note_text_color_requested, 0),
            ("delta marker", self.point_at(6.5, 3.65), "Color",
             plot_widget.delta_marker_color_requested, 9)]

    @covers("LLFR-00388", "LLFR-00419", "LLFR-00391", "LLFR-00351",
            "LLFR-00379", "LLFR-00387", "LLFR-00409", "LLFR-00175")
    def test_every_option_lists_recent_colors_then_other(self) -> None:
        """Each color option is a submenu with the recent colors, most
        recent first, each with its swatch and "#rrggbb" code, then
        "Other color..." with no swatch.

        Inputs: none.
        Outputs: none.
        """
        for name_str, point, option_str, _, _ in self.option_list():
            with self.subTest(option=name_str):
                menu = self.plot_widget.build_context_menu(point)
                entry_list = submenu_entries(menu, option_str)
                self.assertEqual([action.text() for action in entry_list],
                                 list(self.RECENT_TUPLE)
                                 + ["Other color..."])
                self.assertEqual([swatch_color_str(action)
                                  for action in entry_list],
                                 list(self.RECENT_TUPLE) + [""])
                menu.deleteLater()

    @covers("LLFR-00175", "LLFR-00409")
    def test_delta_marker_menu_starts_with_color(self) -> None:
        """The delta marker menu is "Color", "Delete" and the two
        "Delete all delta markers" options, in this order.

        Inputs: none.
        Outputs: none.
        """
        option_tuple = self.option_list()[-1]
        menu = self.plot_widget.build_context_menu(option_tuple[1])
        self.assertEqual([action.text() for action in menu.actions()],
                         DELTA_MENU_TEXT_LIST)
        menu.deleteLater()

    @covers("LLFR-00419", "LLFR-00390", "LLFR-00388")
    def test_entries_ask_for_their_color_and_update_the_list(self) -> None:
        """A recent entry asks for its color with the item and puts it
        first in the list; "Other color..." asks with "" and leaves the
        list as it is.

        Inputs: none.
        Outputs: none.
        """
        from view import color_picker
        for name_str, point, option_str, signal, item_i in (
                self.option_list()):
            with self.subTest(option=name_str):
                isolate_recent_colors(self, self.RECENT_TUPLE)
                request_list = recorder(signal)
                menu = self.plot_widget.build_context_menu(point)
                entry_list = submenu_entries(menu, option_str)
                entry_list[2].trigger()
                self.assertEqual(request_list, [(item_i, "#123456")])
                self.assertEqual(color_picker.recent_color_list(),
                                 ["#123456", "#00aa00", "#ffff00"])
                entry_list[-1].trigger()
                self.assertEqual(request_list[-1], (item_i, ""))
                self.assertEqual(color_picker.recent_color_list(),
                                 ["#123456", "#00aa00", "#ffff00"])
                menu.deleteLater()
                signal.disconnect()

    @covers("LLFR-00419", "LLFR-00388")
    def test_empty_list_shows_only_other_color(self) -> None:
        """With no recent color, every submenu holds only "Other
        color...".

        Inputs: none.
        Outputs: none.
        """
        isolate_recent_colors(self)
        for name_str, point, option_str, _, _ in self.option_list():
            with self.subTest(option=name_str):
                menu = self.plot_widget.build_context_menu(point)
                self.assertEqual([action.text() for action in
                                  submenu_entries(menu, option_str)],
                                 ["Other color..."])
                menu.deleteLater()

    @covers("LLFR-00390", "LLFR-00419")
    def test_closed_menu_emits_nothing(self) -> None:
        """A menu closed without a choice asks for no color and leaves
        the list as it is.

        Inputs: none.
        Outputs: none.
        """
        from view import color_picker
        name_str, point, _, signal, _ = self.option_list()[0]
        request_list = recorder(signal)
        self.plot_widget.execute_menu = lambda menu, global_point: None
        self.plot_widget.show_context_menu(point)
        self.application.processEvents()
        self.assertEqual(request_list, [])
        self.assertEqual(color_picker.recent_color_list(),
                         list(self.RECENT_TUPLE))


@requires_qt
class DeltaMarkerColorViewTest(PlotWidgetToolTestCase):
    """A delta marker drawn in its color (LLFR-00409, LLFR-00172)."""

    def delta_colors(self, delta_marker_id_i: int) -> dict:
        """Return the colors of a delta marker's parts.

        Inputs:
            delta_marker_id_i: id of the delta marker.
        Outputs: a dict part name -> "#rrggbb".
        """
        bracket, leader, dots, label = self.plot_widget.delta_artist_tuple(
            delta_marker_id_i)
        return {"bracket": to_hex_str(bracket.get_edgecolor()),
                "leader": to_hex_str(leader.get_edgecolor()),
                "dots": to_hex_str(dots.get_markerfacecolor()),
                "text": to_hex_str(label.get_color()),
                "box border": to_hex_str(
                    label.get_bbox_patch().get_edgecolor())}

    @covers("LLFR-00409", "LLFR-00172", "LLFR-00168", "LLFR-00170",
            "LLFR-00169", "LLFR-00171")
    def test_bracket_dots_and_value_in_the_marker_color(self) -> None:
        """Each delta marker draws its bracket, dots and value in its own
        color; one without a usable color in the reserved marker color.

        Inputs: none.
        Outputs: none.
        """
        self.plot_widget.set_delta_markers([
            (1, "x", ("Ramp", 2.0, 3.2), ("Ramp", 4.0, 3.4), 2.0,
             "#1F77B4"),
            (2, "y", ("Ramp", 6.0, 3.6), ("Ramp", 7.0, 3.7), 0.1),
            (3, "y", ("Ramp", 8.0, 3.8), ("Ramp", 9.0, 3.9), 0.1, "red")])
        self.draw()
        self.assertEqual(set(self.delta_colors(1).values()), {"#1f77b4"})
        self.assertEqual(set(self.delta_colors(2).values()),
                         {MARKER_COLOR_STR})
        self.assertEqual(set(self.delta_colors(3).values()),
                         {MARKER_COLOR_STR})
        self.assertEqual(self.plot_widget.delta_label_text(1), "Δt = 2 s")

    @covers("LLFR-00172", "LLFR-00083", "LLFR-00352", "LLFR-00353")
    def test_first_dot_and_previews_stay_orange(self) -> None:
        """With colored delta markers drawn, the dot of a first point
        stays the marker color and the previews the pale marker color.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import DELTA_PREVIEW_COLOR_STR
        self.plot_widget.set_delta_markers([
            (1, "x", ("Ramp", 2.0, 3.2), ("Ramp", 4.0, 3.4), 2.0,
             "#1f77b4")])
        self.plot_widget.set_plot_tool(DELTA_X_TOOL_STR)
        self.plot_widget.set_delta_first_point(("Ramp", 5.0, 3.5))
        self.draw()
        self.assertEqual(to_hex_str(
            self.plot_widget.delta_first_point_artist.get_markerfacecolor()),
            MARKER_COLOR_STR)
        self.assertEqual(to_hex_str(
            self.plot_widget.delta_preview_dot.get_markerfacecolor()),
            DELTA_PREVIEW_COLOR_STR)
        leader, bracket, label = self.plot_widget.delta_preview_artist_tuple
        for color_value in (leader.get_edgecolor(), bracket.get_edgecolor(),
                            label.get_color()):
            self.assertEqual(to_hex_str(color_value),
                             DELTA_PREVIEW_COLOR_STR)


@requires_qt
class AreaLabelColorViewTest(PlotWidgetToolTestCase):
    """Area name and times in the area's color (LLFR-00307,
    LLFR-00308)."""

    @covers("LLFR-00307", "LLFR-00308", "LLFR-00351", "LLFR-00305")
    def test_label_and_times_follow_the_area_color(self) -> None:
        """The name and the times are drawn in the area's color at full
        opacity, on the white label box, while the band stays
        see-through; a light yellow keeps its box.

        Inputs: none.
        Outputs: none.
        """
        from view.plot_widget import AREA_ALPHA_F, MARKER_TEXT_BOX_DICT
        self.plot_widget.set_areas([(1, "Area 1", 2.0, 4.0, "#FFFF00"),
                                    (2, "Area 2", 6.0, 8.0)])
        self.draw()
        for area_id_i, color_str in ((1, "#ffff00"), (2, MARKER_COLOR_STR)):
            band, label, times_text = self.plot_widget.area_artist_tuple(
                area_id_i)
            with self.subTest(area=area_id_i):
                self.assertEqual(to_hex_str(band.get_facecolor()),
                                 color_str)
                self.assertAlmostEqual(band.get_alpha(), AREA_ALPHA_F)
                for text in (label, times_text):
                    self.assertEqual(to_hex_str(text.get_color()),
                                     color_str)
                    self.assertIn(text.get_alpha(), (None, 1.0))
                    self.assertEqual(
                        to_hex_str(text.get_bbox_patch().get_facecolor()),
                        to_hex_str(MARKER_TEXT_BOX_DICT["facecolor"]))
        # A new color draws the label and times again in that color.
        self.plot_widget.set_areas([(1, "Area 1", 2.0, 4.0, "#2f7dff")])
        self.draw()
        _, label, times_text = self.plot_widget.area_artist_tuple(1)
        self.assertEqual(to_hex_str(label.get_color()), "#2f7dff")
        self.assertEqual(to_hex_str(times_text.get_color()), "#2f7dff")


@requires_qt
class RecentColorEndToEndTest(unittest.TestCase):
    """Recent colors through MainWindow and the real controllers."""

    def setUp(self) -> None:
        """Create the window with a file and one plot in each of two
        tabs, a flag and a delta marker in the first plot.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        isolate_recent_colors(self, ["#00aa00", MARKER_COLOR_STR])
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
        first_tab_id_i = self.main_window.current_tab_id()
        self.plot_id_i = self.widgets()[0].plot_id_i
        self.main_window.plot_panel.request_add_tab()
        self.main_window.signal_double_click_handler("speed")
        self.main_window.set_current_tab(first_tab_id_i)
        self.plot_controller.on_plot_tool_changed(MARKER_TOOL_STR)
        self.plot_controller.on_marker_place(self.plot_id_i, 2.0)
        self.plot_controller.on_plot_tool_changed(DELTA_X_TOOL_STR)
        self.plot_controller.on_delta_point_pick(self.plot_id_i, "speed",
                                                 0.5, 1.0)
        self.plot_controller.on_delta_point_pick(self.plot_id_i, "speed",
                                                 3.5, 7.0)
        self.plot_controller.on_plot_tool_changed(NO_TOOL_STR)
        self.process_events()
        self.flag_id_i = self.plot_controller.workspace.marker_list[
            0].marker_id_i

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

    def widgets(self) -> list:
        """Return the plot widgets of every tab, first tab first.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        return list(self.main_window.plot_panel.plot_widget_dict.values())

    def choose(self, data_tuple: tuple, option_str: str,
               entry_str: str) -> None:
        """Right-click the first plot and choose a submenu entry.

        Inputs:
            data_tuple: (x, y) of the right-click, in data values.
            option_str: the submenu's option text.
            entry_str: the entry text.
        Outputs: none.
        """
        plot_widget = self.widgets()[0]
        plot_widget.canvas.draw()
        menu = plot_widget.build_context_menu(
            plot_widget.data_to_widget_point(*data_tuple))
        entry = next(action for action in submenu_entries(menu, option_str)
                     if action.text() == entry_str)
        entry.trigger()
        menu.deleteLater()
        self.process_events()

    def flag_colors(self) -> list:
        """Return the color of the flag's line on every plot.

        Inputs: none.
        Outputs: a list of "#rrggbb".
        """
        return [to_hex_str(widget.marker_artist_tuple(self.flag_id_i)[0]
                           .get_color()) for widget in self.widgets()]

    def depth(self) -> int:
        """Return how many actions can be undone.

        Inputs: none.
        Outputs: the depth of the undo history.
        """
        return self.plot_controller.undo_history.depth()

    @covers("LLFR-00419", "LLFR-00390", "LLFR-00392", "LLFR-00205",
            "LLFR-00138", "LLFR-00140")
    def test_recent_color_on_a_flag(self) -> None:
        """A recent color is drawn on every plot as one undoable action;
        choosing the flag's own color moves it first in the list and
        records nothing.

        Inputs: none.
        Outputs: none.
        """
        from view import color_picker
        depth_i = self.depth()
        flag_tuple = (2.0, 1.0)
        self.choose(flag_tuple, "Color", "#00aa00")
        self.assertEqual(self.flag_colors(), ["#00aa00", "#00aa00"])
        self.assertEqual(self.depth(), depth_i + 1)
        self.choose(flag_tuple, "Color", "#00aa00")
        self.assertEqual(self.depth(), depth_i + 1)
        self.choose(flag_tuple, "Color", MARKER_COLOR_STR)
        self.assertEqual(self.flag_colors(), [MARKER_COLOR_STR] * 2)
        self.assertEqual(color_picker.recent_color_list(),
                         [MARKER_COLOR_STR, "#00aa00"])
        self.choose(flag_tuple, "Color", MARKER_COLOR_STR)
        self.assertEqual(self.depth(), depth_i + 2)
        self.main_window.run_undo()
        self.process_events()
        self.assertEqual(self.flag_colors(), ["#00aa00", "#00aa00"])

    @covers("LLFR-00409", "LLFR-00388", "LLFR-00389", "LLFR-00390",
            "LLFR-00419", "LLFR-00138", "LLFR-00192")
    def test_picker_color_on_a_delta_marker(self) -> None:
        """"Other color..." on a delta marker opens the real picker at
        the marker's color; the confirmed color is drawn on its bracket,
        dots and value, goes first in the recent colors, and undo and
        redo follow.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor
        from PyQt6.QtWidgets import QColorDialog, QDialog
        from view import color_picker
        start_list = []

        def accept(dialog) -> int:
            """Choose a dark blue and confirm.

            Inputs:
                dialog: the QColorDialog.
            Outputs: the Accepted code.
            """
            start_list.append(dialog.currentColor().name())
            dialog.setCurrentColor(QColor("#123456"))
            return QDialog.DialogCode.Accepted

        def bracket_color() -> str:
            """Return the bracket color of the plot's delta marker.

            Inputs: none.
            Outputs: "#rrggbb".
            """
            plot_widget = self.widgets()[0]
            delta_id_i = plot_widget.delta_marker_id_list()[0]
            return to_hex_str(plot_widget.delta_artist_tuple(delta_id_i)[0]
                              .get_edgecolor())

        depth_i = self.depth()
        with mock.patch.object(QColorDialog, "exec", accept):
            self.choose((0.5, 1.0), "Color", "Other color...")
        self.assertEqual(start_list, [MARKER_COLOR_STR])
        self.assertEqual(bracket_color(), "#123456")
        self.assertEqual(self.depth(), depth_i + 1)
        self.assertEqual(color_picker.recent_color_list(),
                         ["#123456", "#00aa00", MARKER_COLOR_STR])
        self.main_window.run_undo()
        self.process_events()
        self.assertEqual(bracket_color(), MARKER_COLOR_STR)
        self.main_window.run_redo()
        self.process_events()
        self.assertEqual(bracket_color(), "#123456")


if __name__ == "__main__":
    unittest.main()
