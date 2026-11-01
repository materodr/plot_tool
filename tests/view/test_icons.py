"""Tests for the button icons, hover names and app icon (issue #74).

Covers LLFR-00158 (icon instead of the name), LLFR-00159 (icon
pictures), LLFR-00160 (icon visibility), LLFR-00181 (button name on
hover), LLFR-00182 (where the app icon is shown) and LLFR-00183 (app
icon picture).
"""

import hashlib
import time
import unittest

from tests.support import (
    button_name, covers, get_qt_application, requires_qt)

from model.curve_colors import PALETTE_COLOR_TUPLE
from view import icon_shapes, theme

# LLFR-00158, LLFR-00181: top panel attribute -> the button's name.
BUTTON_NAME_DICT = {
    "open_file_button": "Open file",
    "tip_button": "Tip",
    "zoom_button": "Zoom",
    "marker_button": "Vertical marker",
    "delta_x_button": "Delta X",
    "delta_y_button": "Delta Y",
    "reset_zoom_button": "Reset zoom",
    "grid_button": "Grid",
    "export_button": "Export",
    "copy_button": "Copy",
    "undo_button": "Undo",
    "redo_button": "Redo",
}
# LLFR-00159: the 12 icons of the requirement, in its order.
REQUIRED_ICON_TUPLE = (
    "open_file", "undo", "tip", "zoom", "reset_zoom", "vertical_marker",
    "delta_x", "delta_y", "grid", "export", "copy", "redo")


def hex_to_rgb_tuple(color_str: str) -> tuple:
    """Return the (red, green, blue) channels of a "#rrggbb" color.

    Inputs:
        color_str: the color.
    Outputs: a tuple of three ints from 0 to 255.
    """
    return tuple(int(color_str[index_i:index_i + 2], 16)
                 for index_i in (1, 3, 5))


def color_distance_f(first_tuple: tuple, second_tuple: tuple) -> float:
    """Return the Euclidean distance between two RGB colors.

    Inputs:
        first_tuple: (red, green, blue) of one color.
        second_tuple: (red, green, blue) of the other.
    Outputs: the distance, 0.0 for equal colors.
    """
    return sum((first_i - second_i) ** 2 for first_i, second_i in zip(
        first_tuple, second_tuple)) ** 0.5


def ink_pixel_list(image) -> list:
    """Return the colors of the pixels of an image that are not clear.

    Inputs:
        image: a QImage with an alpha channel.
    Outputs: a list of (red, green, blue, alpha) tuples of the pixels
        whose alpha is above zero, colors not premultiplied.
    """
    from PyQt6.QtGui import QColor
    pixel_list = []
    for y_i in range(image.height()):
        for x_i in range(image.width()):
            color = QColor.fromRgba(image.pixel(x_i, y_i))
            if color.alpha() > 0:
                pixel_list.append((color.red(), color.green(), color.blue(),
                                   color.alpha()))
    return pixel_list


def image_digest_str(image) -> str:
    """Return a hash of the pixels of an image.

    Inputs:
        image: a QImage.
    Outputs: the SHA-256 hex digest of its pixel values.
    """
    value_list = [image.pixel(x_i, y_i) for y_i in range(image.height())
                  for x_i in range(image.width())]
    return hashlib.sha256(repr(value_list).encode("ascii")).hexdigest()


class IconShapeDataTest(unittest.TestCase):
    """Checks of the icon shapes that need no Qt (view.icon_shapes)."""

    @covers("LLFR-00159")
    def test_all_twelve_icons_are_defined(self) -> None:
        """Every icon of LLFR-00159 has a shape, including Delta X and Y
        and Redo.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(icon_shapes.ICON_NAME_TUPLE, REQUIRED_ICON_TUPLE)
        for icon_name_str in REQUIRED_ICON_TUPLE:
            with self.subTest(icon=icon_name_str):
                self.assertGreater(
                    len(icon_shapes.icon_layer_list(icon_name_str)), 0)
        with self.assertRaises(KeyError):
            icon_shapes.icon_layer_list("no_such_icon")

    @covers("LLFR-00159")
    def test_one_stroke_weight_and_inside_the_grid(self) -> None:
        """Every outline uses the same pen, and every point is in the grid.

        Inputs: none.
        Outputs: none.
        """
        for icon_name_str in REQUIRED_ICON_TUPLE:
            for command_list, stroke_role_str, fill_role_str, width_f in (
                    icon_shapes.icon_layer_list(icon_name_str)):
                with self.subTest(icon=icon_name_str):
                    if stroke_role_str:
                        self.assertEqual(stroke_role_str,
                                         icon_shapes.INK_ROLE_STR)
                        self.assertEqual(width_f,
                                         icon_shapes.ICON_STROKE_WIDTH_F)
                    else:
                        self.assertEqual(fill_role_str,
                                         icon_shapes.INK_ROLE_STR)
                    for command_tuple in command_list:
                        for value_f in command_tuple[1:]:
                            self.assertGreaterEqual(value_f, 0.0)
                            self.assertLessEqual(
                                value_f, icon_shapes.ICON_GRID_F)

    @covers("LLFR-00159")
    def test_shapes_have_the_described_parts(self) -> None:
        """Lens + plus, lens + two arrows, dot on a curve, 3x3 grid, ...

        Inputs: none.
        Outputs: none.
        """
        def commands(icon_name_str: str) -> list:
            """Return all commands of an icon.

            Inputs:
                icon_name_str: the icon name.
            Outputs: a flat list of command tuples.
            """
            return [command_tuple for layer_tuple in
                    icon_shapes.icon_layer_list(icon_name_str)
                    for command_tuple in layer_tuple[0]]

        def letters(icon_name_str: str) -> list:
            """Return the command letters of an icon.

            Inputs:
                icon_name_str: the icon name.
            Outputs: a list of letters.
            """
            return [command_tuple[0] for command_tuple in
                    commands(icon_name_str)]
        # Zoom and Reset zoom: the same magnifying glass (a circle).
        self.assertEqual(letters("zoom").count("O"), 1)
        self.assertEqual(letters("reset_zoom").count("O"), 1)
        self.assertEqual(icon_shapes.icon_layer_list("zoom")[:2],
                         icon_shapes.icon_layer_list("reset_zoom")[:2])
        # Tip: one filled dot (a fill layer).
        fill_layer_list = [
            layer_tuple for layer_tuple in icon_shapes.icon_layer_list("tip")
            if layer_tuple[2]]
        self.assertEqual(len(fill_layer_list), 1)
        self.assertEqual(fill_layer_list[0][0][0][0], "O")
        # Vertical marker: at least 3 separate dashes below the flag.
        marker_layer_list = icon_shapes.icon_layer_list("vertical_marker")
        dash_layer_list = [layer_tuple for layer_tuple in marker_layer_list
                           if layer_tuple[2]]
        self.assertGreaterEqual(len(dash_layer_list), 3)
        # Grid: a frame and 2 lines in each direction.
        self.assertEqual(letters("grid").count("R"), 1)
        self.assertEqual(letters("grid").count("L"), 4)

        # Delta Y is Delta X with x and y swapped.
        def swapped(command_tuple: tuple) -> tuple:
            """Return a command with its x and y values swapped.

            Inputs:
                command_tuple: a command.
            Outputs: the swapped command.
            """
            value_list = list(command_tuple[1:])
            for index_i in range(0, len(value_list) - 1, 2):
                value_list[index_i], value_list[index_i + 1] = (
                    value_list[index_i + 1], value_list[index_i])
            return (command_tuple[0],) + tuple(value_list)
        self.assertEqual(sorted(swapped(command_tuple) for command_tuple in
                                commands("delta_x")),
                         sorted(commands("delta_y")))
        # Redo is Undo mirrored left to right (LLFR-00159 item 12): an
        # arrow curving to the right.

        def mirrored(command_tuple: tuple) -> tuple:
            """Return a command with its x values mirrored on the grid.

            Inputs:
                command_tuple: a command with (x, y) pairs.
            Outputs: the mirrored command.
            """
            value_list = list(command_tuple[1:])
            for index_i in range(0, len(value_list) - 1, 2):
                value_list[index_i] = (icon_shapes.ICON_GRID_F
                                       - value_list[index_i])
            return (command_tuple[0],) + tuple(value_list)
        self.assertEqual(sorted(mirrored(command_tuple) for command_tuple in
                                commands("undo")),
                         sorted(commands("redo")))
        self.assertNotEqual(commands("undo"), commands("redo"))
        # The redo arrow head points right: its tip is the rightmost
        # point of the icon.
        redo_x_list = [command_tuple[-2] for command_tuple in
                       commands("redo")]
        self.assertEqual(max(redo_x_list), 19.5)
        # Copy: two sheets, the front one a whole rounded rectangle.
        self.assertEqual(letters("copy").count("R"), 1)
        self.assertEqual(len(icon_shapes.icon_layer_list("copy")), 2)

    @covers("LLFR-00160")
    def test_icon_colors_have_contrast_in_every_state(self) -> None:
        """Icon vs background is at least 3:1; disabled is paler.

        Inputs: none.
        Outputs: none.
        """
        state_list = [
            (theme.ICON_COLOR_STR, theme.NORMAL_COLOR_STR),
            (theme.ICON_COLOR_STR, theme.NORMAL_HOVER_COLOR_STR),
            (theme.ICON_COLOR_STR, theme.NORMAL_PRESSED_COLOR_STR),
            (theme.ICON_ACTIVE_COLOR_STR, theme.ACTIVE_COLOR_STR),
            (theme.ICON_DISABLED_COLOR_STR, theme.DISABLED_COLOR_STR),
        ]
        for icon_color_str, background_str in state_list:
            with self.subTest(icon=icon_color_str, background=background_str):
                self.assertGreaterEqual(
                    theme.contrast_ratio_f(icon_color_str, background_str),
                    theme.MINIMUM_ICON_CONTRAST_F)
        # LLFR-00160: paler while disabled: lighter than the normal icon
        # and with less contrast than the normal icon has.
        self.assertGreater(
            theme.relative_luminance_f(theme.ICON_DISABLED_COLOR_STR),
            theme.relative_luminance_f(theme.ICON_COLOR_STR))
        self.assertLess(
            theme.contrast_ratio_f(theme.ICON_DISABLED_COLOR_STR,
                                   theme.DISABLED_COLOR_STR),
            theme.contrast_ratio_f(theme.ICON_COLOR_STR,
                                   theme.NORMAL_COLOR_STR))

    @covers("LLFR-00183")
    def test_app_icon_shape_uses_palette_blue_and_red(self) -> None:
        """The app icon has a square, axes, a blue and a red curve.

        Inputs: none.
        Outputs: none.
        """
        for size_i in (16, 32, 256):
            with self.subTest(size=size_i):
                layer_list = icon_shapes.app_icon_layer_list(size_i)
                role_list = [layer_tuple[1] for layer_tuple in layer_list]
                self.assertEqual(layer_list[0][2],
                                 icon_shapes.BACKGROUND_ROLE_STR)
                self.assertEqual(layer_list[0][0][0][0], "R")
                for role_str in (icon_shapes.AXIS_ROLE_STR,
                                 icon_shapes.BLUE_ROLE_STR,
                                 icon_shapes.RED_ROLE_STR):
                    self.assertIn(role_str, role_list)
        # LLFR-00183: thicker strokes and no ticks below 32 px.
        small_list = icon_shapes.app_icon_layer_list(16)
        large_list = icon_shapes.app_icon_layer_list(256)
        self.assertLess(len(small_list), len(large_list))
        self.assertGreater(small_list[-1][3], large_list[-1][3])


@requires_qt
class ButtonIconTest(unittest.TestCase):
    """Icons, names and hover tips of the top panel buttons."""

    def setUp(self) -> None:
        """Create and show a top panel.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.top_panel import TopPanel
        self.top_panel = TopPanel()
        self.top_panel.resize(700, 60)
        self.top_panel.show()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Hide any tooltip and delete the panel.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QToolTip
        QToolTip.hideText()
        self.top_panel.close()
        self.top_panel.deleteLater()
        self.application.processEvents()

    def wait_until(self, condition, timeout_s: float = 3.0) -> bool:
        """Process events until a condition holds or time runs out.

        Inputs:
            condition: a function that returns a bool.
            timeout_s: the longest wait in seconds.
        Outputs: the last value of the condition.
        """
        end_s = time.monotonic() + timeout_s
        while time.monotonic() < end_s:
            self.application.processEvents()
            if condition():
                return True
            time.sleep(0.02)
        return bool(condition())

    @covers("LLFR-00158", "LLFR-00004", "LLFR-00018", "LLFR-00077",
            "LLFR-00080", "LLFR-00114", "LLFR-00121", "LLFR-00126",
            "LLFR-00132", "LLFR-00136", "LLFR-00161", "LLFR-00162",
            "LLFR-00190")
    def test_every_button_shows_only_its_icon(self) -> None:
        """All 12 buttons have an icon, no text and a square icon size.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QPushButton
        button_list = self.top_panel.button_list()
        self.assertEqual(len(button_list), len(BUTTON_NAME_DICT))
        self.assertEqual(
            set(button_list),
            set(self.top_panel.findChildren(QPushButton)))
        for attribute_str, name_str in BUTTON_NAME_DICT.items():
            button = getattr(self.top_panel, attribute_str)
            with self.subTest(button=name_str):
                self.assertIn(button, button_list)
                self.assertEqual(button.text(), "")
                self.assertFalse(button.icon().isNull())
                self.assertEqual(button_name(button), name_str)
                self.assertEqual(button.button_name(), name_str)
                self.assertEqual(button.iconSize().width(),
                                 theme.ICON_SIZE_I)
                self.assertEqual(button.width(), theme.ICON_BUTTON_SIZE_I)
                self.assertEqual(button.height(), theme.ICON_BUTTON_SIZE_I)
                self.assertTrue(button.isVisible())
                # The icon is painted: the button centre holds ink.
                image = button.grab().toImage()
                from PyQt6.QtGui import QColor
                center_color_set = {
                    QColor(image.pixel(x_i, y_i)).name()
                    for x_i in range(8, image.width() - 8)
                    for y_i in range(8, image.height() - 8)}
                self.assertGreater(len(center_color_set), 3)

    @covers("LLFR-00158")
    def test_each_button_has_its_own_icon(self) -> None:
        """No two buttons share an icon picture.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QSize
        digest_set = set()
        for button in self.top_panel.button_list():
            image = button.icon().pixmap(QSize(24, 24)).toImage()
            digest_set.add(image_digest_str(image))
        self.assertEqual(len(digest_set), len(BUTTON_NAME_DICT))

    @covers("LLFR-00181")
    def test_tooltip_is_the_button_name(self) -> None:
        """Each button's tooltip is its name, e.g. "Vertical marker".

        Inputs: none.
        Outputs: none.
        """
        for attribute_str, name_str in BUTTON_NAME_DICT.items():
            button = getattr(self.top_panel, attribute_str)
            with self.subTest(button=name_str):
                self.assertEqual(button.toolTip(), name_str)
                self.assertEqual(button.accessibleName(), name_str)

    @covers("LLFR-00181")
    def test_tooltip_shows_on_hover_and_hides_on_leave(self) -> None:
        """Hovering shows the name next to the pointer; leaving hides it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, QPoint
        from PyQt6.QtGui import QHelpEvent
        from PyQt6.QtWidgets import QApplication, QToolTip
        for attribute_str in ("zoom_button", "undo_button", "copy_button",
                              "redo_button"):
            button = getattr(self.top_panel, attribute_str)
            name_str = BUTTON_NAME_DICT[attribute_str]
            with self.subTest(button=name_str):
                local_point = QPoint(button.width() // 2,
                                     button.height() // 2)
                global_point = button.mapToGlobal(local_point)
                QApplication.sendEvent(button, QHelpEvent(
                    QEvent.Type.ToolTip, local_point, global_point))
                self.assertTrue(self.wait_until(QToolTip.isVisible))
                self.assertEqual(QToolTip.text(), name_str)
                QApplication.sendEvent(button, QEvent(QEvent.Type.Leave))
                self.assertTrue(self.wait_until(
                    lambda: not QToolTip.isVisible()))

    @covers("LLFR-00159")
    def test_each_icon_renders_a_distinct_picture(self) -> None:
        """All 12 icons draw something, and no two draw the same picture.

        Inputs: none.
        Outputs: none.
        """
        from view import icons
        for size_i in (16, 20, 40):
            digest_set = set()
            for icon_name_str in REQUIRED_ICON_TUPLE:
                with self.subTest(icon=icon_name_str, size=size_i):
                    image = icons.render_icon_image(icon_name_str,
                                                    "#000000", size_i)
                    self.assertEqual(image.width(), size_i)
                    pixel_count_i = len(ink_pixel_list(image))
                    # Drawn, but a line picture, not a filled square.
                    self.assertGreater(pixel_count_i, size_i * size_i // 10)
                    self.assertLess(pixel_count_i, size_i * size_i * 3 // 4)
                    digest_set.add(image_digest_str(image))
            self.assertEqual(len(digest_set), len(REQUIRED_ICON_TUPLE))

    @covers("LLFR-00159")
    def test_icons_scale_without_bitmap_blur(self) -> None:
        """A 40 px icon is drawn anew, not a blown-up 20 px picture.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from view import icons
        for icon_name_str in REQUIRED_ICON_TUPLE:
            with self.subTest(icon=icon_name_str):
                large_image = icons.render_icon_image(icon_name_str,
                                                      "#000000", 40)
                scaled_image = icons.render_icon_image(
                    icon_name_str, "#000000", 20).scaled(
                    40, 40, Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                # The vector drawing has more fully opaque pixels: its
                # edges are sharp.
                opaque_large_i = sum(
                    1 for pixel_tuple in ink_pixel_list(large_image)
                    if pixel_tuple[3] == 255)
                opaque_scaled_i = sum(
                    1 for pixel_tuple in ink_pixel_list(scaled_image)
                    if pixel_tuple[3] == 255)
                self.assertGreater(opaque_large_i, opaque_scaled_i)

    @covers("LLFR-00160")
    def test_icon_color_follows_mode_and_state(self) -> None:
        """Normal ink, white while active (On), paler while disabled.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QIcon
        from view import icons
        case_list = [
            (QIcon.Mode.Normal, QIcon.State.Off, theme.ICON_COLOR_STR),
            (QIcon.Mode.Active, QIcon.State.Off, theme.ICON_COLOR_STR),
            (QIcon.Mode.Selected, QIcon.State.Off, theme.ICON_COLOR_STR),
            (QIcon.Mode.Normal, QIcon.State.On, theme.ICON_ACTIVE_COLOR_STR),
            (QIcon.Mode.Active, QIcon.State.On, theme.ICON_ACTIVE_COLOR_STR),
            (QIcon.Mode.Disabled, QIcon.State.Off,
             theme.ICON_DISABLED_COLOR_STR),
            (QIcon.Mode.Disabled, QIcon.State.On,
             theme.ICON_DISABLED_COLOR_STR),
        ]
        for icon_name_str in REQUIRED_ICON_TUPLE:
            icon = icons.icon_for(icon_name_str)
            for mode, state, expected_str in case_list:
                with self.subTest(icon=icon_name_str, mode=mode,
                                  state=state):
                    self.assertEqual(icons.icon_state_color_str(mode, state),
                                     expected_str)
                    image = icon.pixmap(QSize(40, 40), mode, state).toImage()
                    opaque_list = [pixel_tuple[:3] for pixel_tuple in
                                   ink_pixel_list(image)
                                   if pixel_tuple[3] == 255]
                    self.assertGreater(len(opaque_list), 0)
                    for rgb_tuple in opaque_list:
                        self.assertLess(color_distance_f(
                            rgb_tuple, hex_to_rgb_tuple(expected_str)), 4.0)

    def closest_distance_f(self, button, color_str: str) -> float:
        """Return how close the icon area of a button gets to a color.

        Inputs:
            button: a top panel button.
            color_str: the expected icon color.
        Outputs: the smallest RGB distance between that color and a
            pixel of the icon area of the painted button.
        """
        from PyQt6.QtGui import QColor
        image = button.grab().toImage()
        target_tuple = hex_to_rgb_tuple(color_str)
        inset_i = (image.width() - theme.ICON_SIZE_I) // 2
        distance_list = []
        for y_i in range(inset_i, image.height() - inset_i):
            for x_i in range(inset_i, image.width() - inset_i):
                color = QColor(image.pixel(x_i, y_i))
                distance_list.append(color_distance_f(
                    (color.red(), color.green(), color.blue()),
                    target_tuple))
        return min(distance_list)

    @covers("LLFR-00160", "LLFR-00001", "LLFR-00141", "LLFR-00194")
    def test_painted_buttons_show_the_state_icon_color(self) -> None:
        """Painted buttons show ink, white when active, pale when disabled.

        Inputs: none.
        Outputs: none.
        """
        zoom_button = self.top_panel.zoom_button
        self.assertLess(self.closest_distance_f(
            zoom_button, theme.ICON_COLOR_STR), 30.0)
        zoom_button.setChecked(True)
        self.application.processEvents()
        self.assertLess(self.closest_distance_f(
            zoom_button, theme.ICON_ACTIVE_COLOR_STR), 30.0)
        zoom_button.finish()
        # The Undo button starts disabled (LLFR-00141): its icon is pale.
        undo_button = self.top_panel.undo_button
        self.assertFalse(undo_button.isEnabled())
        self.application.processEvents()
        self.assertLess(self.closest_distance_f(
            undo_button, theme.ICON_DISABLED_COLOR_STR), 30.0)
        # The ink color does not appear on the disabled button.
        self.assertGreater(self.closest_distance_f(
            undo_button, theme.ICON_COLOR_STR), 60.0)
        undo_button.setEnabled(True)
        self.application.processEvents()
        self.assertLess(self.closest_distance_f(
            undo_button, theme.ICON_COLOR_STR), 30.0)
        # The Redo button too (LLFR-00194): pale while disabled, ink
        # when enabled.
        redo_button = self.top_panel.redo_button
        self.assertFalse(redo_button.isEnabled())
        self.assertLess(self.closest_distance_f(
            redo_button, theme.ICON_DISABLED_COLOR_STR), 30.0)
        self.assertGreater(self.closest_distance_f(
            redo_button, theme.ICON_COLOR_STR), 60.0)
        redo_button.setEnabled(True)
        self.application.processEvents()
        self.assertLess(self.closest_distance_f(
            redo_button, theme.ICON_COLOR_STR), 30.0)


@requires_qt
class AppIconTest(unittest.TestCase):
    """The app icon picture and where it is set."""

    def setUp(self) -> None:
        """Get the shared application.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()

    def color_count_i(self, image, color_str: str,
                      tolerance_f: float = 40.0) -> int:
        """Count the opaque pixels of an image close to a color.

        Inputs:
            image: a QImage.
            color_str: the color.
            tolerance_f: the largest RGB distance counted.
        Outputs: the number of pixels.
        """
        target_tuple = hex_to_rgb_tuple(color_str)
        return sum(1 for pixel_tuple in ink_pixel_list(image)
                   if pixel_tuple[3] >= 200 and color_distance_f(
                       pixel_tuple[:3], target_tuple) <= tolerance_f)

    @covers("LLFR-00183")
    def test_blue_and_red_curves_on_a_light_rounded_square(self) -> None:
        """At 16, 32 and 256 px the icon has blue, red and dark axes.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor
        from view import icons
        for size_i in (16, 32, 256):
            with self.subTest(size=size_i):
                image = icons.app_icon_image(size_i)
                self.assertEqual((image.width(), image.height()),
                                 (size_i, size_i))
                minimum_count_i = max(3, size_i * size_i // 200)
                self.assertGreaterEqual(self.color_count_i(
                    image, PALETTE_COLOR_TUPLE[0]), minimum_count_i)
                self.assertGreaterEqual(self.color_count_i(
                    image, PALETTE_COLOR_TUPLE[2]), minimum_count_i)
                self.assertGreaterEqual(self.color_count_i(
                    image, theme.APP_ICON_AXIS_COLOR_STR, 60.0),
                    minimum_count_i)
                # Rounded: the corner pixel is clear; light: most of the
                # opaque pixels are light.
                self.assertLess(QColor.fromRgba(image.pixel(0, 0)).alpha(),
                                60)
                opaque_list = [pixel_tuple for pixel_tuple in
                               ink_pixel_list(image)
                               if pixel_tuple[3] == 255]
                light_count_i = sum(1 for pixel_tuple in opaque_list
                                    if min(pixel_tuple[:3]) >= 200)
                self.assertGreater(light_count_i, len(opaque_list) // 2)

    @covers("LLFR-00183", "LLFR-00182")
    def test_app_icon_pixmap_and_margin(self) -> None:
        """app_icon_pixmap has the asked size; a margin leaves a border.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor
        from view import icons
        pixmap = icons.app_icon_pixmap(64)
        self.assertEqual((pixmap.width(), pixmap.height()), (64, 64))
        image = icons.app_icon_image(128, 0.1)
        for point_tuple in ((10, 64), (64, 10), (117, 64), (64, 117)):
            self.assertEqual(QColor.fromRgba(
                image.pixel(*point_tuple)).alpha(), 0)
        self.assertGreater(QColor.fromRgba(image.pixel(64, 20)).alpha(), 0)
        png_bytes = icons.app_icon_png_bytes(32)
        self.assertEqual(png_bytes[:8], b"\x89PNG\r\n\x1a\n")

    @covers("LLFR-00182")
    def test_window_and_application_icon_are_set(self) -> None:
        """The main window and the application show the app icon.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QSize
        from view import icons
        from view.main_window import MainWindow
        main_window = MainWindow()
        self.addCleanup(main_window.deleteLater)
        self.assertFalse(main_window.windowIcon().isNull())
        self.assertFalse(self.application.windowIcon().isNull())
        expected_str = image_digest_str(icons.app_icon_image(32))
        for icon in (main_window.windowIcon(),
                     self.application.windowIcon()):
            image = icon.pixmap(QSize(32, 32)).toImage().convertToFormat(
                icons.app_icon_image(32).format())
            self.assertEqual(image_digest_str(image), expected_str)
        size_list = [size.width() for size in
                     main_window.windowIcon().availableSizes()]
        for side_i in (16, 32, 256, 512, 1024):
            self.assertIn(side_i, size_list)


if __name__ == "__main__":
    unittest.main()
