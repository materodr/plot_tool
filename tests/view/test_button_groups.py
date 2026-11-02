"""Tests for the button groups of the top panel and for the Area and
Text buttons (issue #127).

Covers LLFR-00347 (order of the groups), LLFR-00348 (joined buttons),
LLFR-00349 (space between groups), LLFR-00350 (button states inside a
group), LLFR-00286 and LLFR-00320 (the Area and Text buttons) with
their icons (LLFR-00159 items 15 and 16, LLFR-00160), and the plot tool
rules they follow (LLFR-00079, LLFR-00109, LLFR-00002).
"""

import unittest

from tests.support import (
    button_name, button_tip_line_list, covers, get_qt_application,
    requires_qt)

from controller.plot_tools import (
    AREA_TOOL_STR, NO_TOOL_STR, PLOT_TOOL_TUPLE, TEXT_TOOL_STR)
from view import icon_shapes, theme

# LLFR-00347: the names of the buttons of each group, left to right.
EXPECTED_GROUP_LIST = [
    ["Open file", "Save layout", "Load layout"],
    ["Data tip", "Zoom", "Pan", "Flag", "Delta X", "Delta Y",
     "Area", "Text"],
    ["Reset zoom", "Grid"],
    ["Export", "Copy", "Save signals"],
    ["Undo", "Redo"],
    ["Report a bug"]]


def expected_segment_list(button_count_i: int) -> list:
    """Return the segment names expected for a group.

    Inputs:
        button_count_i: the number of buttons of the group.
    Outputs: single for a group of one button (Report a bug,
        LLFR-00347 item 6); otherwise first, then middle for each inner
        button, then last.
    """
    if button_count_i == 1:
        return [theme.SEGMENT_SINGLE_STR]
    return ([theme.SEGMENT_FIRST_STR]
            + [theme.SEGMENT_MIDDLE_STR] * (button_count_i - 2)
            + [theme.SEGMENT_LAST_STR])


class SegmentStyleTest(unittest.TestCase):
    """LLFR-00348, LLFR-00350: the style rules of joined buttons."""

    @covers("LLFR-00348")
    def test_corner_rule_of_each_position(self) -> None:
        """Only the outer side of the first and last buttons is rounded;
        middle and last buttons have no left border of their own.

        Inputs: none.
        Outputs: none.
        """
        radius_str = f"{theme.BUTTON_RADIUS_I}px"
        first_str = theme.segment_corner_rule(theme.SEGMENT_FIRST_STR)
        self.assertIn(f"border-top-left-radius: {radius_str}", first_str)
        self.assertIn(f"border-bottom-left-radius: {radius_str}", first_str)
        self.assertIn("border-top-right-radius: 0px", first_str)
        self.assertIn("border-bottom-right-radius: 0px", first_str)
        self.assertNotIn("border-left-width: 0px", first_str)
        middle_str = theme.segment_corner_rule(theme.SEGMENT_MIDDLE_STR)
        self.assertIn("border-radius: 0px", middle_str)
        self.assertIn("border-left-width: 0px", middle_str)
        last_str = theme.segment_corner_rule(theme.SEGMENT_LAST_STR)
        self.assertIn(f"border-top-right-radius: {radius_str}", last_str)
        self.assertIn(f"border-bottom-right-radius: {radius_str}", last_str)
        self.assertIn("border-top-left-radius: 0px", last_str)
        self.assertIn("border-bottom-left-radius: 0px", last_str)
        self.assertIn("border-left-width: 0px", last_str)
        self.assertEqual(theme.segment_corner_rule(theme.SEGMENT_SINGLE_STR),
                         f"border-radius: {radius_str};")

    @covers("LLFR-00350", "LLFR-00348", "LLFR-00141")
    def test_disabled_button_keeps_the_shared_line_normal(self) -> None:
        """A disabled first or middle button draws the line it shares
        with its right neighbour in the normal border color, so that the
        neighbour does not look disabled; its own colors stay paler.

        Inputs: none.
        Outputs: none.
        """
        for segment_str in (theme.SEGMENT_FIRST_STR,
                            theme.SEGMENT_MIDDLE_STR):
            with self.subTest(segment=segment_str):
                style_str = theme.toggle_button_style_sheet(
                    "undo_button", False, segment_str, disabled_rule_b=True,
                    icon_only_b=True)
                disabled_rule_str = [
                    rule_str for rule_str in style_str.split("\n")
                    if ":disabled" in rule_str][0]
                self.assertIn(
                    f"border-right-color: {theme.BUTTON_BORDER_COLOR_STR}",
                    disabled_rule_str)
                self.assertIn(
                    f"background-color: {theme.DISABLED_COLOR_STR}",
                    disabled_rule_str)
                self.assertIn(f"color: {theme.DISABLED_TEXT_COLOR_STR}",
                              disabled_rule_str)
        for segment_str in (theme.SEGMENT_LAST_STR,
                            theme.SEGMENT_SINGLE_STR):
            with self.subTest(segment=segment_str):
                self.assertEqual(theme.shared_border_rule(segment_str), "")

    @covers("LLFR-00349")
    def test_group_gap_is_16_pixels(self) -> None:
        """The gap between groups is 16 px.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(theme.TOOLBAR_GROUP_GAP_I, 16)


class AreaTextShapeTest(unittest.TestCase):
    """LLFR-00159 items 15 and 16: the shapes of the new icons."""

    @covers("LLFR-00159", "LLFR-00286", "LLFR-00320")
    def test_area_icon_is_two_lines_shaded_between(self) -> None:
        """Two vertical lines and diagonal hatch lines between them.

        Inputs: none.
        Outputs: none.
        """
        layer_list = icon_shapes.icon_layer_list(icon_shapes.AREA_ICON_STR)
        left_f, top_f, right_f, bottom_f = icon_shapes.AREA_BAND_TUPLE
        vertical_list = []
        hatch_list = []
        for command_list, _, _, _ in layer_list:
            self.assertEqual(len(command_list), 2)
            (_, start_x_f, start_y_f), (_, end_x_f, end_y_f) = command_list
            if start_x_f == end_x_f:
                vertical_list.append((start_x_f, start_y_f, end_y_f))
            else:
                hatch_list.append((start_x_f, start_y_f, end_x_f, end_y_f))
        self.assertEqual(vertical_list, [(left_f, top_f, bottom_f),
                                         (right_f, top_f, bottom_f)])
        # The shading: at least 3 diagonal lines, all between the two
        # vertical lines, rising at 45 degrees.
        self.assertGreaterEqual(len(hatch_list), 3)
        for start_x_f, start_y_f, end_x_f, end_y_f in hatch_list:
            for x_f in (start_x_f, end_x_f):
                self.assertGreaterEqual(x_f, left_f)
                self.assertLessEqual(x_f, right_f)
            for y_f in (start_y_f, end_y_f):
                self.assertGreaterEqual(y_f, top_f)
                self.assertLessEqual(y_f, bottom_f)
            self.assertAlmostEqual(start_x_f + start_y_f, end_x_f + end_y_f)
            self.assertGreater(end_x_f - start_x_f, 1.0)
        # A line that misses the band gives no segment.
        self.assertEqual(icon_shapes.hatch_segment_list(
            icon_shapes.AREA_BAND_TUPLE, 1.0), [])

    @covers("LLFR-00159", "LLFR-00320")
    def test_text_icon_is_a_capital_t_in_a_box(self) -> None:
        """A rounded box, a horizontal bar and a vertical stem from the
        middle of the bar, all inside the box.

        Inputs: none.
        Outputs: none.
        """
        layer_list = icon_shapes.icon_layer_list(icon_shapes.TEXT_ICON_STR)
        self.assertEqual(len(layer_list), 3)
        box_tuple = layer_list[0][0][0]
        self.assertEqual(box_tuple[0], "R")
        _, box_x_f, box_y_f, box_width_f, box_height_f, _ = box_tuple
        bar_list = layer_list[1][0]
        stem_list = layer_list[2][0]
        # The bar is horizontal, the stem vertical and starts on the bar
        # at its middle, below it.
        self.assertEqual(bar_list[0][2], bar_list[1][2])
        self.assertEqual(stem_list[0][1], stem_list[1][1])
        self.assertAlmostEqual(stem_list[0][1],
                               (bar_list[0][1] + bar_list[1][1]) / 2.0)
        self.assertEqual(stem_list[0][2], bar_list[0][2])
        self.assertGreater(stem_list[1][2], stem_list[0][2])
        for command_tuple in bar_list + stem_list:
            self.assertGreater(command_tuple[1], box_x_f)
            self.assertLess(command_tuple[1], box_x_f + box_width_f)
            self.assertGreater(command_tuple[2], box_y_f)
            self.assertLess(command_tuple[2], box_y_f + box_height_f)
        # Smaller than the frame of the Grid icon, so they differ.
        grid_box_tuple = icon_shapes.icon_layer_list(
            icon_shapes.GRID_ICON_STR)[0][0][0]
        self.assertLess(box_width_f, grid_box_tuple[3])


@requires_qt
class ButtonGroupTest(unittest.TestCase):
    """LLFR-00347 to LLFR-00350 on a shown top panel."""

    def setUp(self) -> None:
        """Create and show a top panel wide enough for every button.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.top_panel import TopPanel
        self.top_panel = TopPanel()
        self.top_panel.resize(1000, 60)
        self.top_panel.show()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close and delete the panel.

        Inputs: none.
        Outputs: none.
        """
        self.top_panel.close()
        self.top_panel.deleteLater()
        self.application.processEvents()

    def top_center_color_str(self, button) -> str:
        """Return the painted color near the top middle of a button.

        Inputs:
            button: a top panel button.
        Outputs: the "#rrggbb" color 4 pixels below the top edge, where
            the icon does not reach.
        """
        from PyQt6.QtGui import QColor
        image = button.grab().toImage()
        return QColor(image.pixel(image.width() // 2, 4)).name()

    def right_edge_color_str(self, button) -> str:
        """Return the painted color of the right border line.

        Inputs:
            button: a top panel button.
        Outputs: the "#rrggbb" color of the rightmost pixel column, at
            half the button's height.
        """
        from PyQt6.QtGui import QColor
        image = button.grab().toImage()
        return QColor(image.pixel(image.width() - 1,
                                  image.height() // 2)).name()

    @covers("LLFR-00347", "LLFR-00286", "LLFR-00320")
    def test_buttons_in_the_order_of_the_groups(self) -> None:
        """The groups hold the buttons of the requirement, in order, and
        the panel shows them from left to right in that order.

        Inputs: none.
        Outputs: none.
        """
        group_name_list = [
            [button_name(button) for button in button_group]
            for button_group in self.top_panel.button_group_list]
        self.assertEqual(group_name_list, EXPECTED_GROUP_LIST)
        flat_button_list = [button for button_group in
                            self.top_panel.button_group_list
                            for button in button_group]
        self.assertEqual(self.top_panel.button_list(), flat_button_list)
        x_list = [button.x() for button in flat_button_list]
        self.assertEqual(x_list, sorted(x_list))
        self.assertEqual(len(set(x_list)), len(x_list))
        for button in flat_button_list:
            with self.subTest(button=button_name(button)):
                self.assertTrue(button.isVisible())
                self.assertEqual(button.y(), flat_button_list[0].y())
        # LLFR-00286, LLFR-00320: the Area and Text buttons.
        self.assertEqual(button_name(self.top_panel.area_button), "Area")
        self.assertEqual(button_name(self.top_panel.text_button), "Text")
        self.assertEqual(list(self.top_panel.plot_tool_button_dict),
                         list(PLOT_TOOL_TUPLE))

    @covers("LLFR-00348", "LLFR-00349")
    def test_no_gap_inside_a_group_and_16_px_between(self) -> None:
        """Buttons of a group touch; 16 px separate the groups.

        Inputs: none.
        Outputs: none.
        """
        group_list = self.top_panel.button_group_list
        for button_group in group_list:
            for left_button, right_button in zip(button_group,
                                                 button_group[1:]):
                with self.subTest(left=button_name(left_button)):
                    self.assertEqual(left_button.geometry().right() + 1,
                                     right_button.geometry().left())
        for left_group, right_group in zip(group_list, group_list[1:]):
            with self.subTest(left=button_name(left_group[-1])):
                gap_i = (right_group[0].geometry().left()
                         - left_group[-1].geometry().right() - 1)
                self.assertEqual(gap_i, theme.TOOLBAR_GROUP_GAP_I)
                self.assertEqual(gap_i, 16)

    @covers("LLFR-00348")
    def test_segment_position_of_every_button(self) -> None:
        """First, middle and last positions in every group, and their
        style sheets carry the matching corner rule.

        Inputs: none.
        Outputs: none.
        """
        for button_group in self.top_panel.button_group_list:
            for segment_str, button in zip(
                    expected_segment_list(len(button_group)), button_group):
                with self.subTest(button=button_name(button)):
                    self.assertEqual(button.segment_position_str, segment_str)
                    self.assertIn(theme.segment_corner_rule(segment_str),
                                  button.styleSheet())

    @covers("LLFR-00348", "LLFR-00350")
    def test_shared_border_line_is_drawn_once(self) -> None:
        """The first button draws its right border, the next button
        draws none on its left, so the pair shows one line.

        Inputs: none.
        Outputs: none.
        """
        export_button = self.top_panel.export_button
        copy_button = self.top_panel.copy_button
        self.assertEqual(self.right_edge_color_str(export_button),
                         theme.BUTTON_BORDER_COLOR_STR)
        from PyQt6.QtGui import QColor
        image = copy_button.grab().toImage()
        self.assertNotEqual(
            QColor(image.pixel(0, image.height() // 2)).name(),
            theme.BUTTON_BORDER_COLOR_STR)

    @covers("LLFR-00350", "LLFR-00001", "LLFR-00141", "LLFR-00194",
            "LLFR-00218")
    def test_each_button_shows_its_own_state(self) -> None:
        """In every group, one button active or disabled leaves the
        colors of its neighbours unchanged.

        Inputs: none.
        Outputs: none.
        """
        from view.undo_button import UndoButton
        for button_group in self.top_panel.button_group_list:
            for changed_button in button_group:
                saved_enabled_dict = {button: button.isEnabled()
                                      for button in button_group}
                for button in button_group:
                    button.setEnabled(True)
                    button.finish()
                self.application.processEvents()
                if isinstance(changed_button, UndoButton):
                    # LLFR-00141, LLFR-00194, LLFR-00218: disabled.
                    changed_button.setEnabled(False)
                    expected_str = theme.DISABLED_COLOR_STR
                else:
                    # LLFR-00001: active.
                    changed_button.setChecked(True)
                    expected_str = theme.ACTIVE_COLOR_STR
                self.application.processEvents()
                for button in button_group:
                    with self.subTest(changed=button_name(changed_button),
                                      button=button_name(button)):
                        self.assertEqual(
                            self.top_center_color_str(button),
                            expected_str if button is changed_button
                            else theme.NORMAL_COLOR_STR)
                changed_button.finish()
                for button, enabled_b in saved_enabled_dict.items():
                    button.setEnabled(enabled_b)
                self.application.processEvents()

    @covers("LLFR-00350", "LLFR-00141", "LLFR-00194")
    def test_disabled_undo_beside_enabled_redo(self) -> None:
        """With Undo disabled and Redo enabled, each shows its state and
        the line they share keeps the normal border color.

        Inputs: none.
        Outputs: none.
        """
        undo_button = self.top_panel.undo_button
        redo_button = self.top_panel.redo_button
        undo_button.setEnabled(False)
        redo_button.setEnabled(True)
        self.application.processEvents()
        self.assertEqual(self.top_center_color_str(undo_button),
                         theme.DISABLED_COLOR_STR)
        self.assertEqual(self.top_center_color_str(redo_button),
                         theme.NORMAL_COLOR_STR)
        self.assertEqual(self.right_edge_color_str(undo_button),
                         theme.BUTTON_BORDER_COLOR_STR)
        # And the other way round.
        undo_button.setEnabled(True)
        redo_button.setEnabled(False)
        self.application.processEvents()
        self.assertEqual(self.top_center_color_str(undo_button),
                         theme.NORMAL_COLOR_STR)
        self.assertEqual(self.top_center_color_str(redo_button),
                         theme.DISABLED_COLOR_STR)

    @covers("LLFR-00286", "LLFR-00320", "LLFR-00079", "LLFR-00109",
            "LLFR-00002", "LLFR-00001")
    def test_area_and_text_are_exclusive_plot_tools(self) -> None:
        """A click on Area or Text makes it the only active tool, it
        stays active until clicked again or another tool is chosen, and
        the change is reported.

        Inputs: none.
        Outputs: none.
        """
        reported_list = []
        self.top_panel.plot_tool_changed.connect(reported_list.append)
        for tool_str in (AREA_TOOL_STR, TEXT_TOOL_STR):
            button = self.top_panel.plot_tool_button_dict[tool_str]
            for other_tool_str in PLOT_TOOL_TUPLE:
                if other_tool_str == tool_str:
                    continue
                with self.subTest(tool=tool_str, other=other_tool_str):
                    other_button = self.top_panel.plot_tool_button_dict[
                        other_tool_str]
                    other_button.click()
                    self.assertEqual(self.top_panel.active_plot_tool(),
                                     other_tool_str)
                    button.click()
                    self.assertTrue(button.is_active())
                    self.assertFalse(other_button.is_active())
                    self.assertEqual(self.top_panel.active_plot_tool(),
                                     tool_str)
                    self.assertEqual(reported_list[-1], tool_str)
                    self.application.processEvents()
                    self.assertEqual(self.top_center_color_str(button),
                                     theme.ACTIVE_COLOR_STR)
                    # LLFR-00109: still active after events are handled.
                    self.assertTrue(button.is_active())
                    # Another tool deactivates it (LLFR-00079).
                    other_button.click()
                    self.assertFalse(button.is_active())
                    self.assertEqual(reported_list[-1], other_tool_str)
                    other_button.click()
            # LLFR-00002: a second click leaves no tool active.
            button.click()
            button.click()
            self.assertFalse(button.is_active())
            self.assertEqual(self.top_panel.active_plot_tool(), NO_TOOL_STR)
            self.assertEqual(reported_list[-1], NO_TOOL_STR)
        # show_plot_tool shows them like any other tool.
        self.top_panel.show_plot_tool(TEXT_TOOL_STR)
        self.assertTrue(self.top_panel.text_button.is_active())
        self.top_panel.show_plot_tool(NO_TOOL_STR)
        self.assertFalse(self.top_panel.text_button.is_active())

    @covers("LLFR-00159", "LLFR-00160", "LLFR-00286", "LLFR-00320",
            "LLFR-00215", "LLFR-00158")
    def test_area_and_text_icons_and_tips(self) -> None:
        """Both buttons show only their own icon, distinct from every
        other icon in the normal, active and disabled states, and their
        button tips say "Hold A" and "Hold T".

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QColor, QIcon
        from tests.view.test_icons import image_digest_str
        from view.icons import icon_for
        for button, icon_str, name_str, key_str in (
                (self.top_panel.area_button, icon_shapes.AREA_ICON_STR,
                 "Area", "Hold A"),
                (self.top_panel.text_button, icon_shapes.TEXT_ICON_STR,
                 "Text", "Hold T")):
            with self.subTest(button=name_str):
                self.assertEqual(button.text(), "")
                self.assertEqual(button.icon_name_str, icon_str)
                self.assertEqual(button_tip_line_list(button),
                                 [name_str, key_str])
        for mode, state, color_str in (
                (QIcon.Mode.Normal, QIcon.State.Off, theme.ICON_COLOR_STR),
                (QIcon.Mode.Normal, QIcon.State.On,
                 theme.ICON_ACTIVE_COLOR_STR),
                (QIcon.Mode.Disabled, QIcon.State.Off,
                 theme.ICON_DISABLED_COLOR_STR)):
            digest_dict = {}
            for icon_name_str in icon_shapes.ICON_NAME_TUPLE:
                image = icon_for(icon_name_str).pixmap(
                    QSize(24, 24), mode, state).toImage()
                digest_dict[icon_name_str] = image_digest_str(image)
                if icon_name_str not in (icon_shapes.AREA_ICON_STR,
                                         icon_shapes.TEXT_ICON_STR):
                    continue
                with self.subTest(icon=icon_name_str, color=color_str):
                    # The icon is drawn in the color of the state.
                    opaque_color_set = set()
                    for y_i in range(image.height()):
                        for x_i in range(image.width()):
                            color = QColor.fromRgba(image.pixel(x_i, y_i))
                            if color.alpha() == 255:
                                opaque_color_set.add(color.name())
                    self.assertEqual(opaque_color_set, {color_str})
            self.assertEqual(len(set(digest_dict.values())),
                             len(icon_shapes.ICON_NAME_TUPLE))
