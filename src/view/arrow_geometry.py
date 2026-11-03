"""Shape of an arrow drawn on a plot (HLFR-00081), in display pixels.

An arrow is a straight dashed line with a filled, solid arrowhead at its end
(LLFR-00373). Its two ends are attached to x-axis and y-axis values
(LLFR-00374), so its shape in pixels is computed again at every draw,
on screen, in the copied image and in the PDF export, from the current
position of its ends; the arrowhead keeps its size in points, so it
looks the same at every zoom and resolution.

The arrowhead is drawn only while the end that holds it is inside the
plot's drawing area (LLFR-00374); the line is clipped to the drawing
area by matplotlib (the patch is clipped to the axes), so only the part
inside it is drawn.

The functions here are pure geometry (numpy only), so that the plot
widget's hit tests (LLFR-00373) and the drawn shape always agree.
"""

import math

import numpy as np
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.text import Text
from matplotlib.transforms import IdentityTransform

# LLFR-00373: the size of the arrowhead, in points, and the line width.
ARROW_HEAD_LENGTH_POINTS_F = 9.0
ARROW_HEAD_HALF_WIDTH_POINTS_F = 3.6
ARROW_LINE_WIDTH_F = 1.6
# LLFR-00373: the line of an arrow is dashed (dash and gap lengths in
# multiples of the line width); its head stays filled and solid.
ARROW_LINE_STYLE_TUPLE = (0, (4.0, 2.0))
ARROW_HEAD_LINE_STYLE_STR = "-"
POINTS_PER_INCH_F = 72.0
# LLFR-00373: an arrowhead is never longer than this part of its arrow,
# so that a short arrow (5 pixels at least, LLFR-00377) still shows a
# line behind its head.
ARROW_HEAD_MAXIMUM_SHARE_F = 0.6


def head_size_tuple(start_tuple: tuple, end_tuple: tuple,
                    pixels_per_point_f: float) -> tuple:
    """Return the length and the half width of an arrowhead, in pixels.

    Inputs:
        start_tuple: (x, y) of the start, in display pixels.
        end_tuple: (x, y) of the end that holds the head.
        pixels_per_point_f: display pixels per typographic point.
    Outputs: (head_length_px, head_half_width_px), smaller than the
        nominal size for a short arrow.
    """
    # LLFR-00373: the nominal size in points, shrunk for short arrows.
    arrow_length_px = math.hypot(end_tuple[0] - start_tuple[0],
                                 end_tuple[1] - start_tuple[1])
    head_length_px = ARROW_HEAD_LENGTH_POINTS_F * pixels_per_point_f
    half_width_px = ARROW_HEAD_HALF_WIDTH_POINTS_F * pixels_per_point_f
    largest_length_px = ARROW_HEAD_MAXIMUM_SHARE_F * arrow_length_px
    if head_length_px > largest_length_px > 0.0:
        scale_f = largest_length_px / head_length_px
        head_length_px *= scale_f
        half_width_px *= scale_f
    return (head_length_px, half_width_px)


def head_vertex_array(start_tuple: tuple, end_tuple: tuple,
                      pixels_per_point_f: float):
    """Return the three corners of an arrowhead, in display pixels.

    Inputs:
        start_tuple: (x, y) of the start, in display pixels.
        end_tuple: (x, y) of the end that holds the head.
        pixels_per_point_f: display pixels per typographic point.
    Outputs: numpy array of shape (3, 2): the point at the end, then the
        two back corners; three times the end when both ends are the
        same point.
    """
    # LLFR-00373: a filled triangle whose point is the arrow's end and
    # which points away from the start.
    start_array = np.asarray(start_tuple, dtype=float)
    end_array = np.asarray(end_tuple, dtype=float)
    direction_array = end_array - start_array
    length_px = float(np.hypot(direction_array[0], direction_array[1]))
    if length_px <= 0.0:
        return np.array([end_array, end_array, end_array])
    unit_array = direction_array / length_px
    normal_array = np.array([-unit_array[1], unit_array[0]])
    head_length_px, half_width_px = head_size_tuple(
        start_tuple, end_tuple, pixels_per_point_f)
    base_array = end_array - head_length_px * unit_array
    return np.array([end_array, base_array + half_width_px * normal_array,
                     base_array - half_width_px * normal_array])


def point_in_triangle_b(point_tuple: tuple, vertex_array) -> bool:
    """Tell whether a point is inside a triangle or on its border.

    Inputs:
        point_tuple: (x, y) of the point.
        vertex_array: numpy array of shape (3, 2), the corners.
    Outputs: True when the point is inside or on the border.
    """
    # LLFR-00373: a point on the arrowhead is on the arrow.
    point_array = np.asarray(point_tuple, dtype=float)
    sign_list = []
    for index_i in range(3):
        first_array = vertex_array[index_i]
        second_array = vertex_array[(index_i + 1) % 3]
        cross_f = float(
            (second_array[0] - first_array[0])
            * (point_array[1] - first_array[1])
            - (second_array[1] - first_array[1])
            * (point_array[0] - first_array[0]))
        sign_list.append(cross_f)
    return (all(sign_f >= 0.0 for sign_f in sign_list)
            or all(sign_f <= 0.0 for sign_f in sign_list))


def segment_distance_f(point_tuple: tuple, start_tuple: tuple,
                       end_tuple: tuple) -> float:
    """Return the distance from a point to a straight segment.

    Inputs:
        point_tuple: (x, y) of the point.
        start_tuple: (x, y) of one end of the segment.
        end_tuple: (x, y) of its other end.
    Outputs: the shortest distance, in the units of the inputs.
    """
    # LLFR-00373: a point within 5 pixels of the line is on the arrow.
    point_array = np.asarray(point_tuple, dtype=float)
    start_array = np.asarray(start_tuple, dtype=float)
    direction_array = np.asarray(end_tuple, dtype=float) - start_array
    length_square_f = float(np.dot(direction_array, direction_array))
    ratio_f = 0.0
    if length_square_f > 0.0:
        ratio_f = float(np.dot(point_array - start_array, direction_array)
                        / length_square_f)
        ratio_f = min(max(ratio_f, 0.0), 1.0)
    nearest_array = start_array + ratio_f * direction_array
    return float(np.hypot(*(point_array - nearest_array)))


def arrow_path(start_tuple: tuple, end_tuple: tuple,
               pixels_per_point_f: float, head_shown_b: bool):
    """Return the path of an arrow, in display pixels.

    Inputs:
        start_tuple: (x, y) of the start, in display pixels.
        end_tuple: (x, y) of the end that holds the head.
        pixels_per_point_f: display pixels per typographic point.
        head_shown_b: False when the end is outside the drawing area, so
            that only the line is drawn (LLFR-00374).
    Outputs: a matplotlib Path: the line, then the closed arrowhead.
    """
    # LLFR-00373: the line stops inside the head, so the head's point
    # stays sharp.
    if not head_shown_b:
        return Path(np.array([start_tuple, end_tuple], dtype=float),
                    [Path.MOVETO, Path.LINETO])
    vertex_array = head_vertex_array(start_tuple, end_tuple,
                                     pixels_per_point_f)
    line_end_array = (vertex_array[1] + vertex_array[2]) / 2.0
    vertex_list = [start_tuple, tuple(line_end_array),
                   tuple(vertex_array[0]), tuple(vertex_array[1]),
                   tuple(vertex_array[2]), tuple(vertex_array[0])]
    code_list = [Path.MOVETO, Path.LINETO, Path.MOVETO, Path.LINETO,
                 Path.LINETO, Path.CLOSEPOLY]
    return Path(np.array(vertex_list, dtype=float), code_list)


class ArrowPatch(PathPatch):
    """One arrow, or the preview of one, drawn in display pixels.

    Inputs:
        start_tuple: (x, y) of the end without the arrowhead.
        end_tuple: (x, y) of the end with the arrowhead.
        color_str: the color of the line and the head.
        data_b: True when the ends are x-axis and y-axis values (a drawn
            arrow), False when they are display pixels (a preview).
        patch_keyword_dict: more PathPatch style (zorder).
    Attributes:
        start_tuple: the start, as given.
        end_tuple: the end that holds the head, as given.
        data_b: whether the ends are data values.
    """

    def __init__(self, start_tuple: tuple, end_tuple: tuple,
                 color_str: str, data_b: bool = True,
                 **patch_keyword_dict) -> None:
        """Create the patch with an empty path.

        Inputs:
            start_tuple: the start.
            end_tuple: the end with the head.
            color_str: the color.
            data_b: True for data values, False for display pixels.
            patch_keyword_dict: more PathPatch style.
        Outputs: none.
        """
        # LLFR-00373: a dashed line and a filled head in the same color.
        super().__init__(Path(np.zeros((1, 2))),
                         transform=IdentityTransform(), facecolor=color_str,
                         edgecolor=color_str, linewidth=ARROW_LINE_WIDTH_F,
                         linestyle=ARROW_LINE_STYLE_TUPLE, capstyle="butt",
                         joinstyle="miter",
                         **patch_keyword_dict)
        self.start_tuple = tuple(float(value_f) for value_f in start_tuple)
        self.end_tuple = tuple(float(value_f) for value_f in end_tuple)
        self.data_b = bool(data_b)

    def display_end_tuple(self) -> tuple:
        """Return the two ends in display pixels for the current axes.

        Inputs: none.
        Outputs: ((start_x_px, start_y_px), (end_x_px, end_y_px)).
        """
        # LLFR-00374: attached to the x and y values of its ends.
        if not self.data_b:
            return (self.start_tuple, self.end_tuple)
        transform = self.axes.transData
        start_array = transform.transform(self.start_tuple)
        end_array = transform.transform(self.end_tuple)
        return ((float(start_array[0]), float(start_array[1])),
                (float(end_array[0]), float(end_array[1])))

    def head_shown_b(self, end_px_tuple: tuple) -> bool:
        """Tell whether the end that holds the head is in the drawing area.

        Inputs:
            end_px_tuple: (x, y) of that end, in display pixels.
        Outputs: True when it is inside the axes or on their border.
        """
        # LLFR-00374: the arrowhead only while its end is shown.
        return bool(self.axes.bbox.contains(end_px_tuple[0],
                                            end_px_tuple[1]))

    def draw(self, renderer) -> None:
        """Compute the path again, then draw it.

        Inputs:
            renderer: the matplotlib renderer of this draw.
        Outputs: none.
        """
        # LLFR-00374: every draw (screen, image, PDF) places the arrow at
        # its ends; the head keeps its size in points (LLFR-00129).
        if self.axes is None:
            return
        start_px_tuple, end_px_tuple = self.display_end_tuple()
        if not all(math.isfinite(value_f) for value_f in
                   start_px_tuple + end_px_tuple):
            return
        pixels_per_point_f = float(self.axes.figure.dpi) / POINTS_PER_INCH_F
        full_path = arrow_path(start_px_tuple, end_px_tuple,
                               pixels_per_point_f,
                               self.head_shown_b(end_px_tuple))
        # LLFR-00373: the line (its first two vertices) is drawn dashed,
        # the head (the closed triangle after them) solid and filled.
        line_path = Path(full_path.vertices[:2], full_path.codes[:2])
        if len(full_path.vertices) > 2:
            self._path = Path(full_path.vertices[2:], full_path.codes[2:])
            self.set_linestyle(ARROW_HEAD_LINE_STYLE_STR)
            super().draw(renderer)
        self._path = line_path
        self.set_linestyle(ARROW_LINE_STYLE_TUPLE)
        super().draw(renderer)
        # The patch keeps the whole path, line and head, for hit tests.
        self._path = full_path


# LLFR-00436: the arrow label's text size, in points, and the gap, in
# points, between the line and the near side of the label's box.
ARROW_LABEL_FONT_SIZE_F = 9.0
ARROW_LABEL_GAP_POINTS_F = 2.0
# LLFR-00436, LLFR-00704: the padding of the label's box, in multiples
# of the font size (the "pad" of view.theme.MARKER_TEXT_BOX_DICT).
ARROW_LABEL_BOX_PAD_F = 0.2


def clipped_segment_tuple(start_tuple: tuple, end_tuple: tuple,
                          box_tuple: tuple) -> tuple:
    """Return the part of a segment that lies inside a box.

    Inputs:
        start_tuple: (x, y) of one end of the segment.
        end_tuple: (x, y) of its other end.
        box_tuple: (left, bottom, right, top) of the box, left < right
            and bottom < top.
    Outputs: ((x, y), (x, y)) of the two ends of the part inside the
        box, in the direction from start to end; () when no part of the
        segment is inside the box.
    """
    # LLFR-00437, LLFR-00871: the label goes with the part of the line
    # that is shown (Liang-Barsky clipping).
    left_f, bottom_f, right_f, top_f = (float(value_f)
                                        for value_f in box_tuple)
    start_x_f, start_y_f = float(start_tuple[0]), float(start_tuple[1])
    delta_x_f = float(end_tuple[0]) - start_x_f
    delta_y_f = float(end_tuple[1]) - start_y_f
    low_f, high_f = 0.0, 1.0
    for step_f, room_f in ((-delta_x_f, start_x_f - left_f),
                           (delta_x_f, right_f - start_x_f),
                           (-delta_y_f, start_y_f - bottom_f),
                           (delta_y_f, top_f - start_y_f)):
        if step_f == 0.0:
            if room_f < 0.0:
                return ()
            continue
        ratio_f = room_f / step_f
        if step_f < 0.0:
            low_f = max(low_f, ratio_f)
        else:
            high_f = min(high_f, ratio_f)
        if low_f > high_f:
            return ()
    return ((start_x_f + low_f * delta_x_f, start_y_f + low_f * delta_y_f),
            (start_x_f + high_f * delta_x_f,
             start_y_f + high_f * delta_y_f))


def reading_direction_tuple(start_tuple: tuple, end_tuple: tuple) -> tuple:
    """Return the unit direction a label along a line is read in.

    Inputs:
        start_tuple: (x, y) of the start of the line, in display pixels
            (y upwards).
        end_tuple: (x, y) of its end.
    Outputs: (x, y) of a unit vector along the line that never points
        to the left, or straight down, so that text written in that
        direction is never upside down; (1.0, 0.0) for a line of zero
        length.
    """
    # LLFR-00436: parallel to the line. LLFR-00869: never upside down,
    # whatever the direction of the arrow.
    delta_x_f = float(end_tuple[0]) - float(start_tuple[0])
    delta_y_f = float(end_tuple[1]) - float(start_tuple[1])
    length_f = math.hypot(delta_x_f, delta_y_f)
    if length_f <= 0.0:
        return (1.0, 0.0)
    unit_x_f, unit_y_f = delta_x_f / length_f, delta_y_f / length_f
    if unit_x_f < 0.0 or (unit_x_f == 0.0 and unit_y_f < 0.0):
        unit_x_f, unit_y_f = -unit_x_f, -unit_y_f
    return (unit_x_f, unit_y_f)


def label_place_tuple(start_tuple: tuple, end_tuple: tuple,
                      width_px: float, height_px: float, gap_px: float,
                      box_tuple: tuple) -> tuple:
    """Return where the label of an arrow is drawn, in display pixels.

    Inputs:
        start_tuple: (x, y) of the start of the arrow, display pixels.
        end_tuple: (x, y) of the end that holds the arrowhead.
        width_px: width of the label's box, along the line.
        height_px: height of the label's box, across the line.
        gap_px: gap between the line and the near side of the box.
        box_tuple: (left, bottom, right, top) of the plot's drawing
            area.
    Outputs: (center_x_px, center_y_px, angle_deg) of the label's box,
        whose text is turned by angle_deg (counterclockwise, between -90
        and 90 degrees); () when no part of the line is inside the
        drawing area (LLFR-00871).
    """
    # LLFR-00437, LLFR-00871: only the part of the line that is shown.
    visible_tuple = clipped_segment_tuple(start_tuple, end_tuple, box_tuple)
    if not visible_tuple:
        return ()
    # LLFR-00436, LLFR-00869: parallel to the line, readable.
    unit_x_f, unit_y_f = reading_direction_tuple(start_tuple, end_tuple)
    normal_x_f, normal_y_f = -unit_y_f, unit_x_f
    angle_deg = math.degrees(math.atan2(unit_y_f, unit_x_f))
    # LLFR-00436, LLFR-00887: next to the middle of the line, beside it:
    # above it as the text is read, or below it when only that side fits.
    (visible_start_tuple, visible_end_tuple) = visible_tuple
    middle_tuple = ((visible_start_tuple[0] + visible_end_tuple[0]) / 2.0,
                    (visible_start_tuple[1] + visible_end_tuple[1]) / 2.0)
    side_px = height_px / 2.0 + gap_px
    first_place_tuple = ()
    for side_sign_f in (1.0, -1.0):
        center_tuple = (middle_tuple[0] + side_sign_f * normal_x_f * side_px,
                        middle_tuple[1] + side_sign_f * normal_y_f * side_px)
        shift_px = inside_shift_along_f(center_tuple, (unit_x_f, unit_y_f),
                                        width_px, height_px, box_tuple)
        if shift_px is None:
            if not first_place_tuple:
                first_place_tuple = center_tuple + (angle_deg,)
            continue
        return (center_tuple[0] + shift_px * unit_x_f,
                center_tuple[1] + shift_px * unit_y_f, angle_deg)
    # LLFR-00437: no shift along the line fits it: next to the middle.
    return first_place_tuple


def inside_shift_along_f(center_tuple: tuple, unit_tuple: tuple,
                         width_px: float, height_px: float,
                         box_tuple: tuple):
    """Return the shortest shift along a line that fits a turned box.

    Inputs:
        center_tuple: (x, y) of the center of the box, display pixels.
        unit_tuple: (x, y) unit vector along the line; the box's width
            is along it and its height across it.
        width_px: width of the box.
        height_px: height of the box.
        box_tuple: (left, bottom, right, top) of the drawing area.
    Outputs: the signed shift, in pixels along unit_tuple, of smallest
        size that puts the whole box inside the drawing area; None when
        no shift along the line does.
    """
    # LLFR-00437: each corner of the box gives a range of shifts.
    unit_x_f, unit_y_f = unit_tuple
    normal_x_f, normal_y_f = -unit_y_f, unit_x_f
    left_f, bottom_f, right_f, top_f = (float(value_f)
                                        for value_f in box_tuple)
    low_f, high_f = -math.inf, math.inf
    for along_sign_f in (-1.0, 1.0):
        for across_sign_f in (-1.0, 1.0):
            corner_x_px = (center_tuple[0]
                           + along_sign_f * unit_x_f * width_px / 2.0
                           + across_sign_f * normal_x_f * height_px / 2.0)
            corner_y_px = (center_tuple[1]
                           + along_sign_f * unit_y_f * width_px / 2.0
                           + across_sign_f * normal_y_f * height_px / 2.0)
            for position_px, step_f, minimum_f, maximum_f in (
                    (corner_x_px, unit_x_f, left_f, right_f),
                    (corner_y_px, unit_y_f, bottom_f, top_f)):
                if abs(step_f) < 1e-12:
                    if not minimum_f <= position_px <= maximum_f:
                        return None
                    continue
                first_f = (minimum_f - position_px) / step_f
                second_f = (maximum_f - position_px) / step_f
                low_f = max(low_f, min(first_f, second_f))
                high_f = min(high_f, max(first_f, second_f))
    if low_f > high_f:
        return None
    return min(max(0.0, low_f), high_f)


def point_in_label_b(point_tuple: tuple, place_tuple: tuple,
                     width_px: float, height_px: float) -> bool:
    """Tell whether a point is on the turned box of an arrow label.

    Inputs:
        point_tuple: (x, y) of the point, in display pixels.
        place_tuple: (center_x_px, center_y_px, angle_deg) of the box,
            as label_place_tuple returns it, or () for a hidden label.
        width_px: width of the box, along the line.
        height_px: height of the box, across the line.
    Outputs: True when the point is inside the box or on its border.
    """
    # LLFR-00373: a point on the label is on the arrow. LLFR-00420: a
    # double-click on it renames the arrow.
    if not place_tuple:
        return False
    center_x_px, center_y_px, angle_deg = place_tuple
    angle_f = math.radians(angle_deg)
    offset_x_px = float(point_tuple[0]) - center_x_px
    offset_y_px = float(point_tuple[1]) - center_y_px
    along_px = (offset_x_px * math.cos(angle_f)
                + offset_y_px * math.sin(angle_f))
    across_px = (-offset_x_px * math.sin(angle_f)
                 + offset_y_px * math.cos(angle_f))
    return (abs(along_px) <= width_px / 2.0
            and abs(across_px) <= height_px / 2.0)


class ArrowLabel(Text):
    """The label with the name of an arrow (LLFR-00436).

    It is placed again at every draw (screen, image, PDF) from the
    current place of its arrow's ends, so it follows the arrow and the
    plot's ranges and size (LLFR-00437), and the preview of a moved,
    turned or stretched arrow (LLFR-00870).

    Inputs:
        arrow_patch: the ArrowPatch of the arrow (or of its preview);
            its display_end_tuple gives the ends in display pixels.
        name_str: the text shown, the arrow's name.
        color_str: the color of the text (LLFR-00436, LLFR-00788).
        box_dict: the style of the label's box (LLFR-00704).
        text_keyword_dict: more Text style (zorder).
    Attributes:
        arrow_patch: the patch it follows.
    """

    def __init__(self, arrow_patch, name_str: str, color_str: str,
                 box_dict: dict, **text_keyword_dict) -> None:
        """Create the label, not yet placed.

        Inputs:
            arrow_patch: the ArrowPatch it follows.
            name_str: the arrow's name.
            color_str: the color of the text.
            box_dict: the style of the label's box.
            text_keyword_dict: more Text style.
        Outputs: none.
        """
        # LLFR-00436: the name, shown literally, in the arrow's color,
        # on a label box; the position is in display pixels.
        super().__init__(0.0, 0.0, str(name_str), color=color_str,
                         fontsize=ARROW_LABEL_FONT_SIZE_F,
                         horizontalalignment="center",
                         verticalalignment="center",
                         rotation_mode="anchor", parse_math=False,
                         transform=IdentityTransform(), bbox=dict(box_dict),
                         **text_keyword_dict)
        self.arrow_patch = arrow_patch

    def box_size_tuple(self, renderer) -> tuple:
        """Return the size of the label's box before it is turned.

        Inputs:
            renderer: the matplotlib renderer of the draw.
        Outputs: (width_px, height_px) in display pixels.
        """
        # LLFR-00436, LLFR-00437: the text and the padding of its box.
        rotation_f = self.get_rotation()
        self.set_rotation(0.0)
        text_box = Text.get_window_extent(self, renderer)
        self.set_rotation(rotation_f)
        pixels_per_point_f = float(self.figure.dpi) / POINTS_PER_INCH_F
        pad_px = (2.0 * ARROW_LABEL_BOX_PAD_F * self.get_fontsize()
                  * pixels_per_point_f)
        return (float(text_box.width) + pad_px,
                float(text_box.height) + pad_px)

    def place_tuple(self, renderer) -> tuple:
        """Return where the label is drawn now, and its box size.

        Inputs:
            renderer: the matplotlib renderer of the draw.
        Outputs: (center_x_px, center_y_px, angle_deg, width_px,
            height_px), or () when the label is hidden: no text, or no
            part of the arrow's line shown (LLFR-00871).
        """
        # LLFR-00437: placed from the current ends of the arrow.
        axes = self.arrow_patch.axes
        if axes is None or not self.get_text():
            return ()
        start_tuple, end_tuple = self.arrow_patch.display_end_tuple()
        if not all(math.isfinite(value_f)
                   for value_f in tuple(start_tuple) + tuple(end_tuple)):
            return ()
        width_px, height_px = self.box_size_tuple(renderer)
        pixels_per_point_f = float(self.figure.dpi) / POINTS_PER_INCH_F
        box = axes.bbox
        place_tuple = label_place_tuple(
            start_tuple, end_tuple, width_px, height_px,
            ARROW_LABEL_GAP_POINTS_F * pixels_per_point_f,
            (float(box.x0), float(box.y0), float(box.x1), float(box.y1)))
        if not place_tuple:
            return ()
        return place_tuple + (width_px, height_px)

    def contains_point_b(self, point_tuple: tuple, renderer) -> bool:
        """Tell whether a display point is on the label.

        Inputs:
            point_tuple: (x, y) in display pixels.
            renderer: the matplotlib renderer.
        Outputs: True when the label is shown and the point is on its
            box.
        """
        # LLFR-00373, LLFR-00420: the label is part of the arrow.
        place_tuple = self.place_tuple(renderer)
        if not place_tuple:
            return False
        return point_in_label_b(point_tuple, place_tuple[:3],
                                place_tuple[3], place_tuple[4])

    def draw(self, renderer) -> None:
        """Place the label next to its arrow, then draw it.

        Inputs:
            renderer: the matplotlib renderer of this draw.
        Outputs: none. Nothing is drawn while the label is hidden.
        """
        # LLFR-00437, LLFR-00871, LLFR-00870: at every draw, from the
        # arrow's current ends (or its preview's).
        place_tuple = self.place_tuple(renderer)
        if not place_tuple:
            return
        self.set_position(place_tuple[:2])
        self.set_rotation(place_tuple[2])
        super().draw(renderer)
