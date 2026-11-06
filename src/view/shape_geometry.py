"""Geometry of the circles and rectangles of the plots, in display pixels.

Pure math (numpy only), so that the hit tests of the plot widget and the
drawn shapes always agree (HLFR-00158). A shape is drawn in its box, the
rectangle with sides parallel to the axes between two opposite corners
(LLFR-01314); a circle is the ellipse that fits inside the box
(LLFR-01321), a rectangle the four sides of the box (LLFR-01322).
"""

import math

import numpy as np

# LLFR-01321, LLFR-01322: the two kinds, as the model names them.
CIRCLE_KIND_STR = "circle"
RECTANGLE_KIND_STR = "rectangle"
# LLFR-01324: the ellipse is compared with this many points of its line.
ELLIPSE_POINT_COUNT_I = 180


def box_tuple(first_tuple: tuple, second_tuple: tuple) -> tuple:
    """Return the box of two opposite corners.

    Inputs:
        first_tuple: (x, y) of one corner.
        second_tuple: (x, y) of the opposite corner.
    Outputs: (left, bottom, right, top), left <= right, bottom <= top.
    """
    # LLFR-01314: the box with sides parallel to the axes.
    return (min(first_tuple[0], second_tuple[0]),
            min(first_tuple[1], second_tuple[1]),
            max(first_tuple[0], second_tuple[0]),
            max(first_tuple[1], second_tuple[1]))


def corner_list(first_tuple: tuple, second_tuple: tuple) -> list:
    """Return the four corners of a box.

    Inputs:
        first_tuple, second_tuple: two opposite corners (x, y).
    Outputs: [(left, bottom), (right, bottom), (right, top),
        (left, top)].
    """
    # LLFR-01338: the corners that a press may drag.
    left_f, bottom_f, right_f, top_f = box_tuple(first_tuple, second_tuple)
    return [(left_f, bottom_f), (right_f, bottom_f), (right_f, top_f),
            (left_f, top_f)]


def segment_distance_f(point_tuple: tuple, start_tuple: tuple,
                       end_tuple: tuple) -> float:
    """Return the distance from a point to a segment.

    Inputs:
        point_tuple: (x, y).
        start_tuple, end_tuple: the ends of the segment.
    Outputs: the shortest distance.
    """
    # LLFR-01324: within 5 pixels of the line of a rectangle.
    delta_x_f = end_tuple[0] - start_tuple[0]
    delta_y_f = end_tuple[1] - start_tuple[1]
    length_f = delta_x_f * delta_x_f + delta_y_f * delta_y_f
    share_f = 0.0
    if length_f > 0.0:
        share_f = ((point_tuple[0] - start_tuple[0]) * delta_x_f
                   + (point_tuple[1] - start_tuple[1]) * delta_y_f) / length_f
        share_f = min(max(share_f, 0.0), 1.0)
    return math.hypot(point_tuple[0] - (start_tuple[0] + share_f * delta_x_f),
                      point_tuple[1] - (start_tuple[1] + share_f * delta_y_f))


def ellipse_point_array(first_tuple: tuple, second_tuple: tuple,
                        point_count_i: int = ELLIPSE_POINT_COUNT_I):
    """Return points of the ellipse that fits inside a box.

    Inputs:
        first_tuple, second_tuple: two opposite corners of the box.
        point_count_i: the number of points.
    Outputs: an array of shape (point_count_i + 1, 2), closed.
    """
    # LLFR-01321: the ellipse touches the middle of each side of the box.
    left_f, bottom_f, right_f, top_f = box_tuple(first_tuple, second_tuple)
    angle_array = np.linspace(0.0, 2.0 * np.pi, point_count_i + 1)
    center_x_f = 0.5 * (left_f + right_f)
    center_y_f = 0.5 * (bottom_f + top_f)
    return np.column_stack((
        center_x_f + 0.5 * (right_f - left_f) * np.cos(angle_array),
        center_y_f + 0.5 * (top_f - bottom_f) * np.sin(angle_array)))


def line_distance_f(kind_str: str, point_tuple: tuple, first_tuple: tuple,
                    second_tuple: tuple) -> float:
    """Return the distance from a point to the line of a shape.

    Inputs:
        kind_str: CIRCLE_KIND_STR or RECTANGLE_KIND_STR.
        point_tuple: (x, y).
        first_tuple, second_tuple: two opposite corners of the box.
    Outputs: the shortest distance to the ellipse or to the four sides.
    """
    # LLFR-01324: the inside of a shape is not on it.
    if kind_str == CIRCLE_KIND_STR:
        point_array = ellipse_point_array(first_tuple, second_tuple)
    else:
        point_array = np.array(corner_list(first_tuple, second_tuple)
                               + [corner_list(first_tuple,
                                              second_tuple)[0]])
    return min(segment_distance_f(point_tuple, tuple(point_array[index_i]),
                                  tuple(point_array[index_i + 1]))
               for index_i in range(len(point_array) - 1))


def nearest_corner_index(point_tuple: tuple, first_tuple: tuple,
                         second_tuple: tuple, threshold_f: float) -> int:
    """Return the corner of a box within a distance of a point.

    Inputs:
        point_tuple: (x, y).
        first_tuple, second_tuple: two opposite corners.
        threshold_f: the largest distance.
    Outputs: the index in corner_list of the nearest corner within the
        distance, or -1 when none is.
    """
    # LLFR-01338, LLFR-01340: the nearest corner moves.
    best_index_i = -1
    best_distance_f = float(threshold_f)
    for index_i, corner_tuple in enumerate(corner_list(first_tuple,
                                                       second_tuple)):
        distance_f = math.hypot(point_tuple[0] - corner_tuple[0],
                                point_tuple[1] - corner_tuple[1])
        if distance_f <= best_distance_f:
            best_index_i = index_i
            best_distance_f = distance_f
    return best_index_i


def opposite_corner(corner_index_i: int, first_tuple: tuple,
                    second_tuple: tuple) -> tuple:
    """Return the corner opposite to a corner of a box.

    Inputs:
        corner_index_i: an index of corner_list.
        first_tuple, second_tuple: two opposite corners.
    Outputs: (x, y) of the opposite corner.
    """
    # LLFR-01339: the opposite corner stays in place.
    return corner_list(first_tuple, second_tuple)[(corner_index_i + 2) % 4]


def kept_apart_corner(fixed_tuple: tuple, pointer_tuple: tuple,
                      moved_tuple: tuple, minimum_f: float) -> tuple:
    """Return the place of a dragged corner, keeping the box large enough.

    Inputs:
        fixed_tuple: (x, y) of the corner that stays.
        pointer_tuple: (x, y) where the dragged corner would go.
        moved_tuple: (x, y) of the dragged corner before the drag, for
            the side when the pointer is level with the fixed corner.
        minimum_f: the smallest width and height of the box.
    Outputs: (x, y): the pointer, moved away from the fixed corner in x
        or y when it is closer than minimum_f.
    """
    # LLFR-01341: at least 5 pixels wide and 5 pixels high.
    result_list = []
    for axis_i in (0, 1):
        offset_f = pointer_tuple[axis_i] - fixed_tuple[axis_i]
        if abs(offset_f) < minimum_f:
            side_f = offset_f or (moved_tuple[axis_i] - fixed_tuple[axis_i])
            offset_f = math.copysign(minimum_f, side_f or 1.0)
        result_list.append(fixed_tuple[axis_i] + offset_f)
    return tuple(result_list)


def line_shown_b(kind_str: str, first_tuple: tuple, second_tuple: tuple,
                 area_tuple: tuple) -> bool:
    """Tell whether a part of the line of a shape is inside an area.

    Inputs:
        kind_str: CIRCLE_KIND_STR or RECTANGLE_KIND_STR.
        first_tuple, second_tuple: two opposite corners of the box.
        area_tuple: (left, bottom, right, top) of the drawing area.
    Outputs: True when some point of the line is inside the area.
    """
    # LLFR-01355: the label is hidden while no part of the line shows.
    left_f, bottom_f, right_f, top_f = area_tuple
    if kind_str == CIRCLE_KIND_STR:
        point_array = ellipse_point_array(first_tuple, second_tuple, 360)
    else:
        corner_array = np.array(corner_list(first_tuple, second_tuple)
                                + [corner_list(first_tuple, second_tuple)[0]])
        point_array = np.vstack([
            np.linspace(corner_array[index_i], corner_array[index_i + 1], 90)
            for index_i in range(4)])
    inside_array = ((point_array[:, 0] >= left_f)
                    & (point_array[:, 0] <= right_f)
                    & (point_array[:, 1] >= bottom_f)
                    & (point_array[:, 1] <= top_f))
    return bool(np.any(inside_array))


def label_place_tuple(first_tuple: tuple, second_tuple: tuple,
                      label_size_tuple: tuple, area_tuple: tuple,
                      gap_f: float) -> tuple:
    """Return where the label of a shape is drawn.

    Inputs:
        first_tuple, second_tuple: two opposite corners of the box.
        label_size_tuple: (width, height) of the label.
        area_tuple: (left, bottom, right, top) of the drawing area.
        gap_f: the gap between the box's corner and the label.
    Outputs: (left, top) of the label: just inside the top-left corner
        of the box, moved by the shortest distance that keeps the whole
        label inside the area.
    """
    # LLFR-01353: inside the top-left corner; LLFR-01354: kept inside.
    left_f, _, _, top_f = box_tuple(first_tuple, second_tuple)
    width_f, height_f = label_size_tuple
    area_left_f, area_bottom_f, area_right_f, area_top_f = area_tuple
    place_left_f = min(max(left_f + gap_f, area_left_f),
                       area_right_f - width_f)
    place_top_f = max(min(top_f - gap_f, area_top_f),
                      area_bottom_f + height_f)
    return (max(place_left_f, area_left_f), min(place_top_f, area_top_f))
