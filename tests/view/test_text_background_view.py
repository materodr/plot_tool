"""Qt tests of the text background (#270, HLFR-00167).

They use a shown plot widget (tests.view.test_labels_view) and, for the
settings and every window, a real MainWindow. The settings are an INI
file of the test (LLFR-01426), and the choice of view.theme is put back
after each test, so no other test sees it. The rules follow the owner's
answers of 2026-11-06 in #270, batches 1 to 3.
"""

import os
import tempfile
import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt
from tests.view.test_labels_view import (
    ARROW_TUPLE, DELTA_X_TUPLE, ORANGE_STR, LabelWidgetTestCase, center_of)

TRANSPARENT_STR = "transparent"
AUTO_CONTRAST_STR = "auto_contrast"


def is_transparent_box(text) -> bool:
    """Tell whether a matplotlib text has no fill and no border.

    Inputs:
        text: a matplotlib Text, possibly with a box.
    Outputs: True when the text has no box, or a box with a fully
        transparent fill and no border line.
    """
    box_patch = text.get_bbox_patch()
    if box_patch is None:
        return True
    return (box_patch.get_facecolor()[3] == 0.0
            and (box_patch.get_linewidth() == 0.0
                 or box_patch.get_edgecolor()[3] == 0.0))


@requires_qt
class TextBackgroundWidgetTest(LabelWidgetTestCase):
    """The menu option and the boxes of the texts of one plot."""

    def setUp(self) -> None:
        """Create the widget and put back the theme's choice afterwards.

        Inputs: none.
        Outputs: none.
        """
        super().setUp()
        from view import theme
        self.theme = theme
        self.addCleanup(theme.set_text_background, theme.text_background_str)
        theme.set_text_background(AUTO_CONTRAST_STR)

    def submenu_entries(self, display_tuple: tuple) -> list:
        """Return the entries of the "Text background" submenu at a point.

        Inputs:
            display_tuple: (x, y) in display pixels.
        Outputs: a list of (text, checked) of the submenu, or None when
            the menu has no such option.
        """
        from PyQt6 import sip
        menu = self.build_menu(display_tuple)
        entry_list = None
        for action in menu.actions():
            if action.text() == "Text background" and action.menu():
                entry_list = [(entry.text(), entry.isChecked())
                              for entry in action.menu().actions()]
        sip.delete(menu)
        return entry_list

    def object_point_dict(self) -> dict:
        """Draw one object of each kind and return a point on each.

        Inputs: none.
        Outputs: object name -> (x, y) in display pixels.
        """
        widget = self.plot_widget
        widget.set_markers([(9, "Start", 5.5, ORANGE_STR)])
        widget.set_areas([(1, "Warm-up", 6.0, 8.0, ORANGE_STR)])
        widget.set_delta_markers([DELTA_X_TUPLE])
        widget.set_arrows([ARROW_TUPLE])
        widget.set_text_notes([("Note text", 4.5, 2.0)])
        widget.set_pinned_tips([("Ramp", 9.0, 3.9, (0.0, -60.0),
                                 "Data tip 1")])
        self.draw()
        return {
            "flag": self.data_display(5.5, 0.0),
            "area": self.data_display(7.0, 1.6),
            "delta": self.data_display(2.0, 3.2),
            "arrow": self.data_display(2.0, 2.0),
            "text note": center_of(widget.text_note_box_extent(0)),
            "tip": center_of(self.box_of(widget.pinned_tip_annotation(0))),
        }

    @covers("LLFR-01418", "LLFR-01419", "HLFR-00167")
    def test_option_in_every_object_menu(self) -> None:
        """Each object menu has "Text background" with "Transparent" and
        "Auto contrast", the current one checked; the curve and plot
        menus have none.

        Inputs: none.
        Outputs: none.
        """
        point_dict = self.object_point_dict()
        for name_str, display_tuple in point_dict.items():
            with self.subTest(menu=name_str):
                self.assertEqual(self.submenu_entries(display_tuple),
                                 [("Transparent", False),
                                  ("Auto contrast", True)])
        self.theme.set_text_background(TRANSPARENT_STR)
        self.assertEqual(self.submenu_entries(point_dict["arrow"]),
                         [("Transparent", True), ("Auto contrast", False)])
        self.plot_widget.set_markers([])
        self.plot_widget.set_areas([])
        self.plot_widget.set_delta_markers([])
        self.plot_widget.set_arrows([])
        self.plot_widget.set_text_notes([])
        self.plot_widget.set_pinned_tips([])
        self.draw()
        self.assertIsNone(self.submenu_entries(
            self.data_display(5.0, 3.5)))
        self.assertIsNone(self.submenu_entries(
            self.data_display(9.0, -0.5)))

    @covers("LLFR-01418", "LLFR-01420", "HLFR-00167")
    def test_choice_asks_for_the_background(self) -> None:
        """Choosing an entry emits text_background_requested with it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6 import sip
        widget = self.plot_widget
        chosen_list = []
        widget.text_background_requested.connect(chosen_list.append)
        point_dict = self.object_point_dict()
        menu = self.build_menu(point_dict["flag"])
        for action in menu.actions():
            if action.text() == "Text background":
                action.menu().actions()[0].trigger()
        sip.delete(menu)
        self.assertEqual(chosen_list, [TRANSPARENT_STR])

    @covers("LLFR-01421", "LLFR-01422", "LLFR-01423", "LLFR-01424",
            "LLFR-00704", "LLFR-00336", "HLFR-00167")
    def test_boxes_follow_the_choice(self) -> None:
        """"Transparent" leaves every text of the objects with no fill
        and no border; "Auto contrast" gives back the grey fills and the
        borders; the hover data tip keeps its white box.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.colors import to_hex
        widget = self.plot_widget
        self.object_point_dict()
        self.theme.set_text_background(TRANSPARENT_STR)
        widget.refresh_text_background()
        self.draw()
        flag_label = widget.marker_artist_dict[9][1]
        _, area_label, area_times = widget.area_artist_tuple(1)
        text_list = [flag_label, area_label, area_times,
                     widget.arrow_label(0),
                     widget.text_note_annotation(0),
                     widget.pinned_tip_annotation(0)]
        for index_i, text in enumerate(text_list):
            with self.subTest(text=index_i):
                self.assertTrue(is_transparent_box(text))
        hover_patch = widget.hover_annotation.get_bbox_patch()
        self.assertEqual(to_hex(hover_patch.get_facecolor()), "#ffffff")
        self.theme.set_text_background(AUTO_CONTRAST_STR)
        widget.refresh_text_background()
        self.draw()
        flag_label = widget.marker_artist_dict[9][1]
        self.assertEqual(to_hex(flag_label.get_bbox_patch()
                                .get_facecolor()),
                         self.theme.area_label_box_color_str(ORANGE_STR))
        note_patch = widget.text_note_annotation(0).get_bbox_patch()
        self.assertGreater(note_patch.get_linewidth(), 0.0)
        tip_patch = widget.pinned_tip_annotation(0).get_bbox_patch()
        self.assertGreater(tip_patch.get_linewidth(), 0.0)
        self.assertEqual(to_hex(tip_patch.get_facecolor()), "#ffffff")

    @covers("LLFR-01421", "LLFR-01422", "HLFR-00167")
    def test_previews_follow_the_choice(self) -> None:
        """The time of the flag preview and the value of the delta
        preview follow the choice.

        Inputs: none.
        Outputs: none.
        """
        widget = self.plot_widget
        self.theme.set_text_background(TRANSPARENT_STR)
        widget.refresh_text_background()
        self.assertTrue(is_transparent_box(widget.preview_time_text))
        self.assertTrue(is_transparent_box(
            widget.delta_preview_artist_tuple[2]))
        self.theme.set_text_background(AUTO_CONTRAST_STR)
        widget.refresh_text_background()
        self.assertFalse(is_transparent_box(widget.preview_time_text))


@requires_qt
class TextBackgroundWindowTest(unittest.TestCase):
    """The choice of the main window, its settings and its exports."""

    def setUp(self) -> None:
        """Create the main window and controller with test settings.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view import text_background_settings, theme
        self.theme = theme
        self.settings_module = text_background_settings
        self.addCleanup(theme.set_text_background, theme.text_background_str)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.settings_path_str = os.path.join(folder.name, "settings.ini")
        settings_patch = mock.patch.object(
            text_background_settings, "settings_file_path_str",
            self.settings_path_str)
        settings_patch.start()
        self.addCleanup(settings_patch.stop)

    def start_window(self):
        """Create a MainWindow and its MainController, as at a launch.

        Inputs: none.
        Outputs: (main window, main controller).
        """
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        main_window = MainWindow()
        controller = MainController(main_window)
        controller.start()
        self.application.processEvents()
        self.addCleanup(main_window.deleteLater)
        self.addCleanup(main_window.close)
        return main_window, controller

    @covers("LLFR-01425", "LLFR-01426", "LLFR-01420", "HLFR-00167")
    def test_choice_kept_between_launches(self) -> None:
        """The first launch uses "Auto contrast"; a choice is written to
        the settings and is the choice of the next launch.

        Inputs: none.
        Outputs: none.
        """
        main_window, controller = self.start_window()
        self.assertEqual(self.theme.text_background_str, AUTO_CONTRAST_STR)
        self.assertEqual(
            controller.plot_controller.workspace.text_background_str,
            AUTO_CONTRAST_STR)
        controller.plot_controller.on_text_background(-1, TRANSPARENT_STR)
        self.assertEqual(self.settings_module.remembered_text_background(),
                         TRANSPARENT_STR)
        main_window.close()
        self.theme.set_text_background(AUTO_CONTRAST_STR)
        _, second_controller = self.start_window()
        self.assertEqual(self.theme.text_background_str, TRANSPARENT_STR)
        self.assertEqual(
            second_controller.plot_controller.workspace.text_background_str,
            TRANSPARENT_STR)

    @covers("LLFR-01427", "LLFR-01426", "HLFR-00167", "HLFR-00040")
    def test_undo_puts_back_the_remembered_choice(self) -> None:
        """Undoing the change puts the previous choice back in the theme
        and in the settings; redoing applies it again.

        Inputs: none.
        Outputs: none.
        """
        _, controller = self.start_window()
        plot_controller = controller.plot_controller
        plot_controller.on_text_background(-1, TRANSPARENT_STR)
        plot_controller.on_undo()
        self.assertEqual(self.theme.text_background_str, AUTO_CONTRAST_STR)
        self.assertEqual(self.settings_module.remembered_text_background(),
                         AUTO_CONTRAST_STR)
        plot_controller.on_redo()
        self.assertEqual(self.theme.text_background_str, TRANSPARENT_STR)
        self.assertEqual(self.settings_module.remembered_text_background(),
                         TRANSPARENT_STR)

    @covers("LLFR-01425", "LLFR-01426", "HLFR-00167")
    def test_unreadable_settings_give_auto_contrast(self) -> None:
        """A value that is no choice, or settings that cannot be read,
        give "Auto contrast"; a failed write is ignored.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QSettings
        settings = QSettings(self.settings_path_str,
                             QSettings.Format.IniFormat)
        settings.setValue(self.settings_module.TEXT_BACKGROUND_KEY_STR,
                          "black")
        settings.sync()
        self.assertEqual(self.settings_module.remembered_text_background(),
                         AUTO_CONTRAST_STR)
        with mock.patch.object(self.settings_module, "open_settings",
                               side_effect=OSError("no settings")):
            self.assertEqual(
                self.settings_module.remembered_text_background(),
                AUTO_CONTRAST_STR)
            self.settings_module.remember_text_background(TRANSPARENT_STR)


if __name__ == "__main__":
    unittest.main()
