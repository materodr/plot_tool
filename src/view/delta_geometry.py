"""Shapes of the delta markers, in display pixels (no Qt needed).

A delta marker (HLFR-00043, HLFR-00044) is drawn from its two points:

- a Delta X marker (LLFR-00168) has a horizontal curly bracket whose
  ends are at the times of the two points, a small gap above the higher
  point, with its middle tip pointing up;
- a Delta Y marker (LLFR-00170) has a vertical curly bracket whose ends
  are at the values of the two points, a small gap to the right of the
  later point, with its middle tip pointing right.

Thin leader lines join each point to its end of the bracket, so that
the bracket is visibly attached to both points.

The bracket is computed in display pixels from the points' display
positions every time it is drawn, so it stays attached to its points
at any zoom, pan or plot size (LLFR-00173), while its depth and gap stay
the same size on screen. In this module "along" is the measured axis (x
for Delta X, y for Delta Y) and "across" the other one, growing away
from the points (up for Delta X, right for Delta Y).
"""

import numpy as np
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.transforms import IdentityTransform

# LLFR-00168, LLFR-00170: the two kinds of delta markers.
from model.workspace import DELTA_X_KIND_STR, DELTA_Y_KIND_STR  # noqa: F401

# LLFR-00168, LLFR-00170: gap (points) from the higher (Delta X) or the
# later (Delta Y) point to the bracket's ends, and the bracket's depth
# from its ends to its middle tip. Points keep the size on screen and
# in the PDF export (LLFR-00129).
DELTA_GAP_POINTS_F = 5.0
DELTA_DEPTH_POINTS_F = 9.0
POINTS_PER_INCH_F = 72.0


def brace_point_list(start_along_px: float, end_along_px: float,
                     depth_px: float) -> tuple:
    """Return the vertices and codes of a curly bracket lying flat.

    The bracket starts at (start, 0), curls to half its depth, runs to
    the middle, rises to its tip at (middle, depth) and goes down again
    the same way to (end, 0). Each curl is a quadratic Bezier curve.

    Inputs:
        start_along_px: one end along the measured axis.
        end_along_px: the other end.
        depth_px: the height of the middle tip above the ends.
    Outputs: a tuple (vertex list of (along_px, across_px), code list
        of matplotlib Path codes).
    """
    # LLFR-00168, LLFR-00170: the classic brace shape "⏞", with its
    # middle tip pointing away from the points.
    low_px, high_px = sorted((float(start_along_px), float(end_along_px)))
    middle_px = (low_px + high_px) / 2.0
    half_depth_px = float(depth_px) / 2.0
    # The curls are round when there is room; a short bracket gets
    # flatter curls so the two halves never overlap.
    curl_px = min(half_depth_px, (high_px - low_px) / 4.0)
    vertex_list = [
        (low_px, 0.0),
        (low_px, half_depth_px), (low_px + curl_px, half_depth_px),
        (middle_px - curl_px, half_depth_px),
        (middle_px, half_depth_px), (middle_px, 2.0 * half_depth_px),
        (middle_px, half_depth_px), (middle_px + curl_px, half_depth_px),
        (high_px - curl_px, half_depth_px),
        (high_px, half_depth_px), (high_px, 0.0)]
    code_list = [Path.MOVETO,
                 Path.CURVE3, Path.CURVE3,
                 Path.LINETO,
                 Path.CURVE3, Path.CURVE3,
                 Path.CURVE3, Path.CURVE3,
                 Path.LINETO,
                 Path.CURVE3, Path.CURVE3]
    return vertex_list, code_list


def delta_geometry_tuple(kind_str: str, first_px_tuple: tuple,
                         second_px_tuple: tuple, gap_px: float,
                         depth_px: float) -> tuple:
    """Return the bracket, the leader lines and the tip of a marker.

    Inputs:
        kind_str: DELTA_X_KIND_STR or DELTA_Y_KIND_STR.
        first_px_tuple: (x, y) of the first point, in display pixels (y
            grows upwards).
        second_px_tuple: (x, y) of the second point.
        gap_px: distance from the higher (Delta X) or later (Delta Y)
            point to the ends of the bracket.
        depth_px: height of the bracket's middle tip above its ends.
    Outputs: a tuple (bracket Path, leader Path, tip (x, y)), all in
        display pixels.
    """
    first_x_px, first_y_px = (float(first_px_tuple[0]),
                              float(first_px_tuple[1]))
    second_x_px, second_y_px = (float(second_px_tuple[0]),
                                float(second_px_tuple[1]))
    if kind_str == DELTA_X_KIND_STR:
        # LLFR-00168: along x, just above the higher point.
        along_tuple = (first_x_px, second_x_px)
        point_across_tuple = (first_y_px, second_y_px)
    else:
        # LLFR-00170: along y, just to the right of the later point
        # (time grows to the right, so the later point is the rightmost).
        along_tuple = (first_y_px, second_y_px)
        point_across_tuple = (first_x_px, second_x_px)
    base_px = max(point_across_tuple) + float(gap_px)
    vertex_list, code_list = brace_point_list(along_tuple[0],
                                              along_tuple[1], depth_px)
    # LLFR-00173: the leader lines join each point to its end of the
    # bracket.
    leader_vertex_list = []
    leader_code_list = []
    for along_px, across_px in zip(along_tuple, point_across_tuple):
        leader_vertex_list += [(along_px, across_px - base_px),
                               (along_px, 0.0)]
        leader_code_list += [Path.MOVETO, Path.LINETO]
    middle_px = (along_tuple[0] + along_tuple[1]) / 2.0
    tip_tuple = (middle_px, float(depth_px))

    def to_display_array(point_list: list):
        """Turn (along, across) points into display (x, y) points.

        Inputs:
            point_list: points relative to the bracket's ends.
        Outputs: numpy array of shape (N, 2) in display pixels.
        """
        # LLFR-00168, LLFR-00170: across grows up (Delta X) or right
        # (Delta Y), away from the points.
        local_array = np.asarray(point_list, dtype=float).reshape(-1, 2)
        if kind_str == DELTA_X_KIND_STR:
            return np.column_stack((local_array[:, 0],
                                    local_array[:, 1] + base_px))
        return np.column_stack((local_array[:, 1] + base_px,
                                local_array[:, 0]))

    bracket_path = Path(to_display_array(vertex_list), code_list)
    leader_path = Path(to_display_array(leader_vertex_list),
                       leader_code_list)
    tip_x_px, tip_y_px = to_display_array([tip_tuple])[0]
    return bracket_path, leader_path, (float(tip_x_px), float(tip_y_px))


def path_distance_px(path, point_x_px: float, point_y_px: float) -> float:
    """Return the distance from a point to the drawn line of a path.

    Inputs:
        path: a matplotlib Path in display pixels (curves allowed).
        point_x_px: x of the point.
        point_y_px: y of the point.
    Outputs: the smallest distance to any segment of the flattened path;
        infinity for an empty path.
    """
    # LLFR-00175: a right-click near the bracket hits the marker.
    point_array = np.array([float(point_x_px), float(point_y_px)])
    best_px = float("inf")
    for polygon_array in path.to_polygons(closed_only=False):
        polygon_array = np.asarray(polygon_array, dtype=float)
        if polygon_array.shape[0] == 0:
            continue
        if polygon_array.shape[0] == 1:
            best_px = min(best_px, float(np.hypot(
                *(polygon_array[0] - point_array))))
            continue
        start_array = polygon_array[:-1]
        direction_array = polygon_array[1:] - start_array
        length_square_array = np.sum(direction_array ** 2, axis=1)
        safe_length_array = np.where(length_square_array > 0.0,
                                     length_square_array, 1.0)
        ratio_array = np.clip(np.sum(
            (point_array - start_array) * direction_array, axis=1)
            / safe_length_array, 0.0, 1.0)
        nearest_array = start_array + ratio_array[:, None] * direction_array
        best_px = min(best_px, float(np.min(np.hypot(
            nearest_array[:, 0] - point_array[0],
            nearest_array[:, 1] - point_array[1]))))
    return best_px


def headroom_high_f(low_f: float, high_f: float, top_value_f: float,
                    headroom_ratio_f: float) -> float:
    """Return the top of a y range that leaves room above a value.

    Inputs:
        low_f: bottom of the y range.
        high_f: top of the y range that fits the curves (LLFR-00076).
        top_value_f: the value that needs room above it (the higher
            point of a Delta X marker).
        headroom_ratio_f: the part of the plot height, from 0 to below
            1, that must be free above top_value_f.
    Outputs: the new top, never below high_f, so every curve stays
        fully visible.
    """
    # LLFR-00168, LLFR-00076: the bracket and its value above the higher
    # point fit in the plot, and the curves still fit too.
    ratio_f = min(max(float(headroom_ratio_f), 0.0), 0.9)
    needed_f = (float(top_value_f) - ratio_f * float(low_f)) / (1.0 - ratio_f)
    return max(float(high_f), needed_f)


class DeltaBracketPatch(PathPatch):
    """The bracket, or the leader lines, of one delta marker.

    The path is computed in display pixels from the marker's two points
    each time the patch is drawn, so it follows every zoom, pan, resize
    and export resolution (LLFR-00173).

    Inputs:
        kind_str: DELTA_X_KIND_STR or DELTA_Y_KIND_STR.
        first_point_tuple: (signal_name_str, time_s, value_f).
        second_point_tuple: the same for the second point.
        leader_b: True for the leader lines, False for the bracket.
        patch_keyword_dict: the PathPatch style (color, width, dashes).
    """

    def __init__(self, kind_str: str, first_point_tuple: tuple,
                 second_point_tuple: tuple, leader_b: bool,
                 **patch_keyword_dict) -> None:
        """Create the patch with an empty path.

        Inputs:
            kind_str: the marker kind.
            first_point_tuple: the first point.
            second_point_tuple: the second point.
            leader_b: True for the leader lines.
            patch_keyword_dict: the PathPatch style.
        Outputs: none.
        """
        # LLFR-00168, LLFR-00170: drawn in display pixels.
        super().__init__(Path(np.zeros((1, 2))),
                         transform=IdentityTransform(), fill=False,
                         **patch_keyword_dict)
        self.kind_str = str(kind_str)
        self.first_point_tuple = tuple(first_point_tuple)
        self.second_point_tuple = tuple(second_point_tuple)
        self.leader_b = bool(leader_b)

    def display_path(self):
        """Return the path for the current axes position and resolution.

        Inputs: none.
        Outputs: a matplotlib Path in display pixels.
        """
        # LLFR-00173: from the points' display positions; the gap and
        # depth are in points, so they keep their size on screen and in
        # the PDF (LLFR-00129).
        axes = self.axes
        pixels_per_point_f = float(axes.figure.dpi) / POINTS_PER_INCH_F
        first_px_array = axes.transData.transform(
            (self.first_point_tuple[1], self.first_point_tuple[2]))
        second_px_array = axes.transData.transform(
            (self.second_point_tuple[1], self.second_point_tuple[2]))
        bracket_path, leader_path, _ = delta_geometry_tuple(
            self.kind_str, tuple(first_px_array), tuple(second_px_array),
            DELTA_GAP_POINTS_F * pixels_per_point_f,
            DELTA_DEPTH_POINTS_F * pixels_per_point_f)
        return leader_path if self.leader_b else bracket_path

    def draw(self, renderer) -> None:
        """Compute the path again, then draw it.

        Inputs:
            renderer: the matplotlib renderer of this draw.
        Outputs: none.
        """
        # LLFR-00173: every draw places the bracket at its points.
        if self.axes is None:
            return
        self._path = self.display_path()
        super().draw(renderer)
