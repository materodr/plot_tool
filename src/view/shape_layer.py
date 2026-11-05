"""Circles and rectangles of a plot widget (HLFR-00158).

ShapeLayer is a mixin of view.plot_widget.PlotWidget, which defines the
Qt signals ``shape_create_requested(str, float, float, float, float)``
and ``shape_change_requested(int, float, float, float, float)`` and the
helpers used here (widget_to_display_tuple, clamped_display_tuple,
inside_axes_b, pixel_ratio_f, blit_overlay, hide_hover_tip,
leave_marker_preview, hide_delta_preview).

Shapes work like arrows (LLFR-00371 to LLFR-00381): they belong to the
plot they were drawn on, are attached to the x and y values of two
opposite corners of their box (LLFR-01318), and are drawn above the
curves, flags, areas and delta markers and below the arrows, tips and
text notes (LLFR-01314). With the Circle or the Rectangle tool, a press
on a shape of that kind, or with no tool a press on any shape, moves it
(LLFR-01323) or, within 5 pixels of a corner of its box, resizes it
(LLFR-01327); any other press with the tool draws a new shape
(LLFR-01303). The previews are blitted like the arrow previews, so they
are never part of a full draw, an export or the copied image
(LLFR-01316), and the request is emitted once, at the release.
"""

import functools
import math

from matplotlib.colors import to_hex, to_rgb
from matplotlib.patches import Ellipse, Rectangle
from matplotlib.text import Text
from matplotlib.transforms import IdentityTransform
from PyQt6.QtCore import QPoint

from model.curve_colors import MARKER_COLOR_STR, hex_color_or_none
from model.workspace import (
    CIRCLE_KIND_STR, DEFAULT_SHAPE_STYLE_STR, RECTANGLE_KIND_STR,
    SHAPE_KIND_TUPLE)
from view import shape_geometry, theme
from view.line_looks import line_style_or, line_width_f, \
    matplotlib_line_style, width_or_one

# LLFR-01314: shapes above the delta markers (8.5), below the arrows
# (8.8).
SHAPE_ZORDER_F = 8.7
# LLFR-01310, LLFR-01311: the thickness of preset width 1, in points.
SHAPE_LINE_WIDTH_F = 1.5
# LLFR-01303, LLFR-01313, LLFR-01327: the 5 pixel rules.
SHAPE_THRESHOLD_PIXELS_F = 5.0
# LLFR-01315: the previews are the shape's color mixed with this share
# of the plot background.
SHAPE_PREVIEW_PALE_RATIO_F = 0.55
# LLFR-01342: the label's font size and its gap to the box, in points.
SHAPE_LABEL_FONT_SIZE_F = 9.0
SHAPE_LABEL_GAP_POINTS_F = 3.0
# LLFR-01323: no shape is pressed.
NO_SHAPE_INDEX_I = -1
# LLFR-01303, LLFR-01323, LLFR-01327: what a press on the shapes does.
SHAPE_DRAG_NONE_STR = ""
SHAPE_DRAG_CREATE_STR = "create"
SHAPE_DRAG_MOVE_STR = "move"
SHAPE_DRAG_CORNER_STR = "corner"


def shape_data_tuple(shape_tuple) -> tuple:
    """Return the drawing data of a shape, with usable values.

    Inputs:
        shape_tuple: (kind_str, start_time_s, start_value_f, end_time_s,
            end_value_f) and, optionally, color_str, name_str, width_i
            and line_style_str.
    Outputs: the 9-tuple with a known kind, floats, a "#rrggbb" color, a
        name, a preset width and a line style.
    """
    # LLFR-01312, LLFR-01361, LLFR-01366: the defaults of a new shape.
    shape_tuple = tuple(shape_tuple)
    kind_str = (shape_tuple[0] if shape_tuple[0] in SHAPE_KIND_TUPLE
                else RECTANGLE_KIND_STR)
    corner_tuple = tuple(float(value_f) for value_f in shape_tuple[1:5])
    color_str = None
    if len(shape_tuple) > 5:
        color_str = hex_color_or_none(shape_tuple[5])
    name_str = str(shape_tuple[6]) if len(shape_tuple) > 6 else ""
    width_i = width_or_one(shape_tuple[7] if len(shape_tuple) > 7 else 1)
    style_str = line_style_or(shape_tuple[8] if len(shape_tuple) > 8
                              else None, DEFAULT_SHAPE_STYLE_STR)
    return ((kind_str,) + corner_tuple
            + (color_str or MARKER_COLOR_STR, name_str, width_i, style_str))


def paler_color_str(color_str: str) -> str:
    """Return a paler version of a color, mixed with the plot background.

    Inputs:
        color_str: any matplotlib color.
    Outputs: "#rrggbb".
    """
    # LLFR-01315: the previews are paler.
    color_tuple = to_rgb(color_str)
    background_tuple = to_rgb(theme.PLOT_BACKGROUND_COLOR_STR)
    return to_hex(tuple(
        (1.0 - SHAPE_PREVIEW_PALE_RATIO_F) * color_f
        + SHAPE_PREVIEW_PALE_RATIO_F * background_f
        for color_f, background_f in zip(color_tuple, background_tuple)))


def new_shape_patch(kind_str: str, color_str: str, width_i: int,
                    style_str: str, transform=None):
    """Return the patch of a shape, a box of 1 by 1 at first.

    Inputs:
        kind_str: CIRCLE_KIND_STR or RECTANGLE_KIND_STR.
        color_str: the color of its line.
        width_i: its preset width.
        style_str: its line style.
        transform: None for data values, or a transform (the previews
            use display pixels).
    Outputs: an Ellipse or a Rectangle with no fill.
    """
    # LLFR-01310, LLFR-01311: a line in the shape's color, width and
    # style, with no fill.
    keyword_dict = {"fill": False, "edgecolor": color_str,
                    "linewidth": line_width_f(SHAPE_LINE_WIDTH_F, width_i),
                    "linestyle": matplotlib_line_style(style_str),
                    "zorder": SHAPE_ZORDER_F}
    if transform is not None:
        keyword_dict["transform"] = transform
    if kind_str == CIRCLE_KIND_STR:
        return Ellipse((0.5, 0.5), 1.0, 1.0, **keyword_dict)
    return Rectangle((0.0, 0.0), 1.0, 1.0, **keyword_dict)


def place_shape_patch(patch, first_tuple: tuple, second_tuple: tuple) -> None:
    """Give a shape patch the box of two opposite corners.

    Inputs:
        patch: an Ellipse or a Rectangle of new_shape_patch.
        first_tuple, second_tuple: the corners, in the patch's units.
    Outputs: none.
    """
    # LLFR-01310: the ellipse fills the box; LLFR-01311: the rectangle
    # is the box.
    left_f, bottom_f, right_f, top_f = shape_geometry.box_tuple(
        first_tuple, second_tuple)
    if isinstance(patch, Ellipse):
        patch.set_center((0.5 * (left_f + right_f), 0.5 * (bottom_f + top_f)))
        patch.set_width(right_f - left_f)
        patch.set_height(top_f - bottom_f)
        return
    patch.set_xy((left_f, bottom_f))
    patch.set_width(right_f - left_f)
    patch.set_height(top_f - bottom_f)


class ShapeLayer:
    """The shapes of a plot widget: drawing, hit tests and drags.

    Inputs: none (a mixin; init_shape_state is called by PlotWidget).
    """

    def init_shape_state(self) -> None:
        """Create the shape attributes of the widget.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01318, LLFR-01320: the shapes of this plot, as tuples of
        # shape_data_tuple, their patches and their labels.
        self.shape_list = []
        self.shape_artist_list = []
        self.shape_label_list = []
        # LLFR-01303, LLFR-01323, LLFR-01327: the press in progress.
        self.shape_drag_mode_str = SHAPE_DRAG_NONE_STR
        self.shape_drag_index_i = NO_SHAPE_INDEX_I
        self.shape_drag_kind_str = RECTANGLE_KIND_STR
        self.shape_drag_corner_i = -1
        self.shape_press_point = QPoint()
        self.shape_press_display_tuple = (0.0, 0.0)
        self.shape_last_point = QPoint()
        self.shape_drag_moved_b = False
        self.shape_preview_tuple = ()
        self.shape_preview_patch_dict = {}
        self.shape_preview_label = None

    # Drawing ---------------------------------------------------------

    def set_shapes(self, shape_data_list: list) -> None:
        """Replace the shapes drawn in the plot.

        Inputs:
            shape_data_list: tuples (kind_str, start_time_s,
                start_value_f, end_time_s, end_value_f, color_str,
                name_str, width_i, line_style_str), in drawing order; the
                x values are in Hz on a frequency plot.
        Outputs: none. Only the shapes are drawn again.
        """
        # LLFR-01318, LLFR-01320: exactly the shapes of this plot.
        self.shape_list = [shape_data_tuple(shape_tuple)
                           for shape_tuple in shape_data_list]
        self.draw_shapes()
        self.draw_when_visible()

    def draw_shapes(self) -> None:
        """Draw the stored shapes, replacing the previous ones.

        Inputs: none.
        Outputs: none. An edit drag in progress ends without a request.
        """
        # LLFR-01339: remove the old artists first.
        for artist in self.shape_artist_list + self.shape_label_list:
            try:
                artist.remove()
            except (ValueError, NotImplementedError):
                pass
        self.shape_artist_list = []
        self.shape_label_list = []
        # LLFR-01323, LLFR-01327: a shape is named by its index, so a
        # drag of one cannot go on with a new list.
        if self.shape_drag_mode_str not in (SHAPE_DRAG_NONE_STR,
                                            SHAPE_DRAG_CREATE_STR):
            self.cancel_shape_drag()
        for (kind_str, start_time_s, start_value_f, end_time_s,
             end_value_f, color_str, name_str, width_i,
             style_str) in self.shape_list:
            # LLFR-01310, LLFR-01311, LLFR-01318: in data values, clipped
            # to the drawing area (LLFR-01319).
            patch = new_shape_patch(kind_str, color_str, width_i, style_str)
            place_shape_patch(patch, (start_time_s, start_value_f),
                              (end_time_s, end_value_f))
            self.axes.add_patch(patch)
            patch.set_in_layout(False)
            self.shape_artist_list.append(patch)
            # LLFR-01342, LLFR-01270: the name label, unless the labels
            # are hidden (LLFR-01274).
            label = Text(0.0, 0.0, "" if self.labels_hidden_b else name_str,
                         color=color_str, fontsize=SHAPE_LABEL_FONT_SIZE_F,
                         horizontalalignment="left",
                         verticalalignment="top",
                         bbox=theme.contrast_label_box_dict(color_str),
                         transform=IdentityTransform(),
                         zorder=SHAPE_ZORDER_F + 0.05)
            label.set_in_layout(False)
            label.set_clip_on(False)
            self.axes.add_artist(label)
            # LLFR-01343: placed again at every draw, inside the area.
            label.draw = functools.partial(
                self.draw_shape_label, len(self.shape_label_list), label,
                label.draw)
            self.shape_label_list.append(label)

    def draw_shape_label(self, shape_index_i: int, label, original_draw,
                         renderer) -> None:
        """Place the label of a shape, then draw it.

        Inputs:
            shape_index_i: index of the shape.
            label: its Text.
            original_draw: the Text's own draw method.
            renderer: the renderer of this draw.
        Outputs: none.
        """
        # LLFR-01342 to LLFR-01344: inside the top-left corner of the
        # box, kept inside the drawing area, hidden with no line shown.
        corner_pair_tuple = self.shape_display_tuple(shape_index_i)
        if not corner_pair_tuple or not label.get_text():
            return
        self.place_shape_label(label, corner_pair_tuple,
                               self.shape_list[shape_index_i][0], renderer)
        if label.get_visible():
            original_draw(renderer)

    def place_shape_label(self, label, corner_pair_tuple: tuple,
                          kind_str: str, renderer) -> None:
        """Move a shape label to its place for a box in display pixels.

        Inputs:
            label: the Text.
            corner_pair_tuple: two opposite corners, display pixels.
            kind_str: the shape's kind.
            renderer: a renderer to measure the label.
        Outputs: none. The label is hidden while no part of the line is
            in the drawing area.
        """
        # LLFR-01344: hidden while no part of the line is shown.
        box = self.axes.bbox
        area_tuple = (float(box.x0), float(box.y0), float(box.x1),
                      float(box.y1))
        shown_b = shape_geometry.line_shown_b(kind_str, *corner_pair_tuple,
                                              area_tuple)
        label.set_visible(shown_b)
        if not shown_b:
            return
        extent = label.get_window_extent(renderer)
        gap_px = SHAPE_LABEL_GAP_POINTS_F * self.pixels_per_point_f()
        left_px, top_px = shape_geometry.label_place_tuple(
            corner_pair_tuple[0], corner_pair_tuple[1],
            (float(extent.width), float(extent.height)), area_tuple, gap_px)
        label.set_position((left_px, top_px))

    def shape_display_tuple(self, shape_index_i: int) -> tuple:
        """Return the two corners of a drawn shape, in display pixels.

        Inputs:
            shape_index_i: index in the list of set_shapes.
        Outputs: ((x, y), (x, y)), or () for an unknown index.
        """
        # LLFR-01318: where the values of its corners are shown now.
        if not 0 <= shape_index_i < len(self.shape_list):
            return ()
        shape_tuple = self.shape_list[shape_index_i]
        transform = self.axes.transData
        first_array = transform.transform(shape_tuple[1:3])
        second_array = transform.transform(shape_tuple[3:5])
        return ((float(first_array[0]), float(first_array[1])),
                (float(second_array[0]), float(second_array[1])))

    # Hit tests -------------------------------------------------------

    def shape_threshold_px(self) -> float:
        """Return the 5 pixel distance of the shape rules, display pixels.

        Inputs: none.
        Outputs: 5 screen pixels in display pixels.
        """
        # LLFR-01313: screen pixels, whatever the device pixel ratio.
        return SHAPE_THRESHOLD_PIXELS_F * self.pixel_ratio_f()

    def shape_label_at_b(self, shape_index_i: int,
                         point_tuple: tuple) -> bool:
        """Tell whether a display point is on the label of a shape.

        Inputs:
            shape_index_i: index of the shape.
            point_tuple: (x, y), display pixels.
        Outputs: True when its label is shown and the point is on it.
        """
        # LLFR-01313, LLFR-01276: a hidden label is not there.
        if not 0 <= shape_index_i < len(self.shape_label_list):
            return False
        label = self.shape_label_list[shape_index_i]
        if not label.get_text() or not label.get_visible():
            return False
        renderer = self.canvas.get_renderer()
        corner_pair_tuple = self.shape_display_tuple(shape_index_i)
        if not corner_pair_tuple:
            return False
        self.place_shape_label(label, corner_pair_tuple,
                               self.shape_list[shape_index_i][0], renderer)
        if not label.get_visible():
            return False
        patch = label.get_bbox_patch()
        extent = (patch.get_window_extent(renderer) if patch is not None
                  else label.get_window_extent(renderer))
        return bool(extent.contains(*point_tuple))

    def shape_at(self, widget_point, kind_str: str = "") -> int:
        """Return the shape under a point.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
            kind_str: "" for any kind, or only shapes of that kind.
        Outputs: the index of the shape drawn last among those under the
            point, or NO_SHAPE_INDEX_I.
        """
        # LLFR-01313: within 5 pixels of its line or of a corner of its
        # box, or on its label; only inside the drawing area.
        point_tuple = self.widget_to_display_tuple(widget_point)
        if not self.inside_axes_b(*point_tuple):
            return NO_SHAPE_INDEX_I
        threshold_px = self.shape_threshold_px()
        # LLFR-00797: among shapes, the one drawn last.
        for index_i in reversed(range(len(self.shape_list))):
            shape_kind_str = self.shape_list[index_i][0]
            if kind_str and shape_kind_str != kind_str:
                continue
            if self.shape_label_at_b(index_i, point_tuple):
                return index_i
            first_tuple, second_tuple = self.shape_display_tuple(index_i)
            if shape_geometry.nearest_corner_index(
                    point_tuple, first_tuple, second_tuple,
                    threshold_px) >= 0:
                return index_i
            if shape_geometry.line_distance_f(
                    shape_kind_str, point_tuple, first_tuple,
                    second_tuple) <= threshold_px:
                return index_i
        return NO_SHAPE_INDEX_I

    def shape_name_str(self, shape_index_i: int) -> str:
        """Return the name of a drawn shape.

        Inputs:
            shape_index_i: index of the shape.
        Outputs: its name, or "".
        """
        # LLFR-00426, LLFR-01342: the name of its label and menu title.
        if not 0 <= shape_index_i < len(self.shape_list):
            return ""
        return self.shape_list[shape_index_i][6]

    # Presses and drags -----------------------------------------------

    def shape_tool_press_at(self, widget_point, kind_str: str) -> None:
        """Handle a left press made with the Circle or Rectangle tool.

        Inputs:
            widget_point: QPoint, where no text note or tip is.
            kind_str: the kind of the active tool.
        Outputs: none. On a shape of that kind an edit starts; anywhere
            else on the drawing area a new shape may start.
        """
        # LLFR-01334: the tool edits only the shapes of its kind;
        # LLFR-01335: any other press draws a new shape (LLFR-01303).
        shape_index_i = self.shape_at(widget_point, kind_str)
        if shape_index_i != NO_SHAPE_INDEX_I:
            self.shape_edit_press_at(widget_point, shape_index_i)
            return
        if not self.inside_axes_b(*self.widget_to_display_tuple(
                widget_point)):
            return
        self.start_shape_press(widget_point, SHAPE_DRAG_CREATE_STR,
                               NO_SHAPE_INDEX_I, kind_str, -1)

    def shape_edit_press_at(self, widget_point, shape_index_i: int) -> None:
        """Start moving or resizing a shape.

        Inputs:
            widget_point: QPoint on the shape.
            shape_index_i: index of the pressed shape.
        Outputs: none.
        """
        # LLFR-01327, LLFR-01329: within 5 pixels of a corner, the
        # nearest corner moves; LLFR-01323: else the shape moves.
        point_tuple = self.widget_to_display_tuple(widget_point)
        first_tuple, second_tuple = self.shape_display_tuple(shape_index_i)
        corner_i = shape_geometry.nearest_corner_index(
            point_tuple, first_tuple, second_tuple,
            self.shape_threshold_px())
        mode_str = (SHAPE_DRAG_CORNER_STR if corner_i >= 0
                    else SHAPE_DRAG_MOVE_STR)
        self.start_shape_press(widget_point, mode_str, shape_index_i,
                               self.shape_list[shape_index_i][0], corner_i)

    def start_shape_press(self, widget_point, mode_str: str,
                          shape_index_i: int, kind_str: str,
                          corner_i: int) -> None:
        """Remember a left press that may draw or change a shape.

        Inputs:
            widget_point: QPoint of the press.
            mode_str: one of the SHAPE_DRAG_* values but NONE.
            shape_index_i: the pressed shape, or NO_SHAPE_INDEX_I.
            kind_str: the kind of the shape.
            corner_i: the pressed corner, or -1.
        Outputs: none. Nothing is shown until the pointer is 5 pixels
            from the press.
        """
        # LLFR-01303, LLFR-00454: from the press to the release.
        self.shape_drag_mode_str = mode_str
        self.shape_drag_index_i = shape_index_i
        self.shape_drag_kind_str = kind_str
        self.shape_drag_corner_i = corner_i
        self.shape_press_point = QPoint(widget_point)
        self.shape_press_display_tuple = self.widget_to_display_tuple(
            widget_point)
        self.shape_last_point = QPoint(widget_point)
        self.shape_drag_moved_b = False
        self.shape_preview_tuple = ()
        self.hide_hover_tip()
        self.leave_marker_preview()
        self.hide_delta_preview()

    def shape_reached_b(self, widget_point) -> bool:
        """Tell whether a point is 5 pixels or more from the press.

        Inputs:
            widget_point: QPoint.
        Outputs: True from 5 screen pixels on.
        """
        # LLFR-01303, LLFR-01326, LLFR-01332: screen pixels.
        return math.hypot(
            widget_point.x() - self.shape_press_point.x(),
            widget_point.y() - self.shape_press_point.y()
        ) >= SHAPE_THRESHOLD_PIXELS_F

    def dragged_shape_display_tuple(self, widget_point) -> tuple:
        """Return the box that the drag in progress shows for a point.

        Inputs:
            widget_point: QPoint.
        Outputs: two opposite corners in display pixels, or () when the
            dragged shape is gone.
        """
        # LLFR-01307, LLFR-01325, LLFR-01331: a pointer outside the
        # drawing area counts at its nearest point.
        pointer_tuple = self.clamped_display_tuple(widget_point)
        if self.shape_drag_mode_str == SHAPE_DRAG_CREATE_STR:
            # LLFR-01303: from the press to the pointer.
            return (tuple(self.shape_press_display_tuple), pointer_tuple)
        corner_pair_tuple = self.shape_display_tuple(self.shape_drag_index_i)
        if not corner_pair_tuple:
            return ()
        first_tuple, second_tuple = corner_pair_tuple
        if self.shape_drag_mode_str == SHAPE_DRAG_MOVE_STR:
            # LLFR-01323, LLFR-01324: moved, keeping its size.
            shift_x_px = pointer_tuple[0] - self.shape_press_display_tuple[0]
            shift_y_px = pointer_tuple[1] - self.shape_press_display_tuple[1]
            return ((first_tuple[0] + shift_x_px, first_tuple[1] + shift_y_px),
                    (second_tuple[0] + shift_x_px,
                     second_tuple[1] + shift_y_px))
        # LLFR-01328: the pressed corner follows, the opposite one stays;
        # LLFR-01330: the box keeps 5 pixels of width and height.
        corner_list = shape_geometry.corner_list(first_tuple, second_tuple)
        moved_tuple = corner_list[self.shape_drag_corner_i]
        fixed_tuple = shape_geometry.opposite_corner(
            self.shape_drag_corner_i, first_tuple, second_tuple)
        return (fixed_tuple, shape_geometry.kept_apart_corner(
            fixed_tuple, pointer_tuple, moved_tuple,
            self.shape_threshold_px()))

    def shape_drag_to(self, widget_point) -> None:
        """Follow the pointer while the left button is held on the shapes.

        Inputs:
            widget_point: QPoint.
        Outputs: none.
        """
        # LLFR-01304, LLFR-01324, LLFR-01328: the preview follows the
        # pointer once it is 5 pixels from the press.
        if self.shape_drag_mode_str == SHAPE_DRAG_NONE_STR:
            return
        self.shape_last_point = QPoint(widget_point)
        if not self.shape_drag_moved_b:
            if not self.shape_reached_b(widget_point):
                return
            self.shape_drag_moved_b = True
        preview_tuple = self.dragged_shape_display_tuple(widget_point)
        if not preview_tuple:
            self.cancel_shape_drag()
            return
        if preview_tuple == self.shape_preview_tuple:
            return
        self.shape_preview_tuple = preview_tuple
        self.blit_overlay()

    def shape_release_at(self, widget_point) -> None:
        """End a press on the shapes where the button was released.

        Inputs:
            widget_point: QPoint.
        Outputs: none.
        """
        # LLFR-01305, LLFR-01323, LLFR-01327: only the release decides.
        if self.shape_drag_mode_str == SHAPE_DRAG_NONE_STR:
            return
        self.shape_last_point = QPoint(widget_point)
        self.finish_shape_drag()

    def finish_shape_drag(self) -> None:
        """End a press on the shapes at the last pointer point.

        Inputs: none.
        Outputs: none. Emits the request of the drag as the last step.
        """
        # LLFR-01308, LLFR-01309, LLFR-01326, LLFR-01332: a release less
        # than 5 pixels from the press changes nothing, silently.
        if self.shape_drag_mode_str == SHAPE_DRAG_NONE_STR:
            return
        release_point = QPoint(self.shape_last_point)
        final_tuple = ()
        if self.shape_reached_b(release_point):
            final_tuple = self.dragged_shape_display_tuple(release_point)
        mode_str = self.shape_drag_mode_str
        shape_index_i = self.shape_drag_index_i
        kind_str = self.shape_drag_kind_str
        # LLFR-01306: the preview goes away.
        self.cancel_shape_drag()
        if not final_tuple:
            return
        threshold_px = self.shape_threshold_px()
        first_tuple, second_tuple = final_tuple
        if (abs(first_tuple[0] - second_tuple[0]) < threshold_px
                or abs(first_tuple[1] - second_tuple[1]) < threshold_px):
            # LLFR-01308: a box under 5 pixels wide or high draws nothing.
            return
        inverse_transform = self.axes.transData.inverted()
        first_array = inverse_transform.transform(first_tuple)
        second_array = inverse_transform.transform(second_tuple)
        value_tuple = (float(first_array[0]), float(first_array[1]),
                       float(second_array[0]), float(second_array[1]))
        if not all(math.isfinite(value_f) for value_f in value_tuple):
            return
        if mode_str == SHAPE_DRAG_CREATE_STR:
            # LLFR-01305: the shape of the preview.
            self.shape_create_requested.emit(kind_str, *value_tuple)
            return
        # LLFR-01323, LLFR-01327: the shape takes the preview's box.
        if 0 <= shape_index_i < len(self.shape_list):
            self.shape_list[shape_index_i] = (
                (self.shape_list[shape_index_i][0],) + value_tuple
                + tuple(self.shape_list[shape_index_i][5:]))
        self.shape_change_requested.emit(shape_index_i, *value_tuple)

    def cancel_shape_drag(self) -> None:
        """Forget the press on the shapes in progress, if any.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01306: the preview, if shown, is removed.
        shown_b = self.shape_preview_shown()
        self.reset_shape_drag()
        if shown_b:
            self.blit_overlay()

    def reset_shape_drag(self) -> None:
        """Clear the state of a press on the shapes without redrawing.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00454: no shape is drawn or dragged.
        self.shape_drag_mode_str = SHAPE_DRAG_NONE_STR
        self.shape_drag_index_i = NO_SHAPE_INDEX_I
        self.shape_drag_corner_i = -1
        self.shape_drag_moved_b = False
        self.shape_preview_tuple = ()

    # Previews --------------------------------------------------------

    def shape_preview_shown(self) -> bool:
        """Tell whether a shape preview is shown.

        Inputs: none.
        Outputs: True while a preview of a new, moved or resized shape is
            shown.
        """
        # LLFR-01303, LLFR-01324, LLFR-01328.
        return (self.shape_drag_mode_str != SHAPE_DRAG_NONE_STR
                and len(self.shape_preview_tuple) == 2)

    def draw_shape_preview(self) -> None:
        """Draw the shape preview over the canvas image (blit_overlay).

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01315: in a paler version of the shape's color;
        # LLFR-01316: not added to the axes, so never in an export.
        if not self.shape_preview_shown():
            return
        color_str = MARKER_COLOR_STR
        width_i, style_str, name_str = 1, DEFAULT_SHAPE_STYLE_STR, ""
        if 0 <= self.shape_drag_index_i < len(self.shape_list):
            shape_tuple = self.shape_list[self.shape_drag_index_i]
            color_str, name_str, width_i, style_str = shape_tuple[5:9]
        pale_str = paler_color_str(color_str)
        patch = new_shape_patch(self.shape_drag_kind_str, pale_str, width_i,
                                style_str, IdentityTransform())
        patch.set_figure(self.figure)
        patch.axes = self.axes
        patch.set_clip_box(self.axes.bbox)
        place_shape_patch(patch, *self.shape_preview_tuple)
        self.axes.draw_artist(patch)
        # LLFR-01317: no label on a new shape; LLFR-01345: the label
        # follows the preview of a moved or resized shape.
        if (self.shape_drag_mode_str == SHAPE_DRAG_CREATE_STR or not name_str
                or self.labels_hidden_b):
            return
        label = Text(0.0, 0.0, name_str, color=pale_str,
                     fontsize=SHAPE_LABEL_FONT_SIZE_F,
                     horizontalalignment="left", verticalalignment="top",
                     bbox=theme.contrast_label_box_dict(pale_str),
                     transform=IdentityTransform(),
                     zorder=SHAPE_ZORDER_F + 0.05)
        label.set_figure(self.figure)
        label.axes = self.axes
        label.set_clip_on(False)
        self.place_shape_label(label, self.shape_preview_tuple,
                               self.shape_drag_kind_str,
                               self.canvas.get_renderer())
        self.shape_preview_label = label
        if label.get_visible():
            self.axes.draw_artist(label)

    def shape_preview_display_tuple(self) -> tuple:
        """Return the corners of the shape preview shown.

        Inputs: none.
        Outputs: two opposite corners in display pixels, or ().
        """
        # LLFR-01303, LLFR-01324, LLFR-01328: for the tests.
        if not self.shape_preview_shown():
            return ()
        return tuple(self.shape_preview_tuple)

    def shape_count(self) -> int:
        """Return the number of shapes drawn in the plot.

        Inputs: none.
        Outputs: the number of shapes given to set_shapes.
        """
        # LLFR-01322: for the tests.
        return len(self.shape_artist_list)

    def shape_patch(self, shape_index_i: int):
        """Return the patch of a shape.

        Inputs:
            shape_index_i: index of the shape.
        Outputs: the Ellipse or Rectangle, or None.
        """
        # LLFR-01310, LLFR-01311: for the tests.
        if 0 <= shape_index_i < len(self.shape_artist_list):
            return self.shape_artist_list[shape_index_i]
        return None

    def shape_label(self, shape_index_i: int):
        """Return the label of a shape.

        Inputs:
            shape_index_i: index of the shape.
        Outputs: its Text, or None.
        """
        # LLFR-01342: for the tests.
        if 0 <= shape_index_i < len(self.shape_label_list):
            return self.shape_label_list[shape_index_i]
        return None
