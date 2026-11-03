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
