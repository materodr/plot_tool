"""Shapes of the top panel icons and of the app icon, as plain data.

The pictures are described here as vector paths, with no Qt import, so
that one drawing serves every size and every screen (LLFR-00159,
LLFR-00183), and view.icons turns them into QIcon objects. Keeping the
shapes as data also keeps the icons in one visual language: every
button icon is drawn with the same pen (ICON_STROKE_WIDTH_F on a
24 by 24 grid, round caps and joins) and only the Tip icon has a filled
dot, the point the tip reads.

A shape is a list of layers. Each layer is a tuple
``(command_list, stroke_role_str, fill_role_str, width_f)``:
- ``command_list``: path commands on the shape's grid, each a tuple
  that starts with a letter: ("M", x, y) move, ("L", x, y) line,
  ("Q", cx, cy, x, y) quadratic curve, ("C", c1x, c1y, c2x, c2y, x, y)
  cubic curve, ("Z",) close the subpath, ("O", cx, cy, r) circle and
  ("R", x, y, width, height, radius) rounded rectangle;
- ``stroke_role_str`` and ``fill_role_str``: the names of the colors
  used to stroke and to fill the layer, or NO_ROLE_STR for none; the
  renderer maps a role to a color (the icon color for INK_ROLE_STR);
- ``width_f``: the pen width, in grid units.
"""

# ----------------------------------------------------------------------
# Button icons (LLFR-00159), on a 24 by 24 grid
# ----------------------------------------------------------------------
ICON_GRID_F = 24.0
# LLFR-00159: one stroke weight for every button icon.
ICON_STROKE_WIDTH_F = 1.75
NO_ROLE_STR = ""
INK_ROLE_STR = "ink"
# LLFR-00159: the dashes of the Vertical marker icon (top of each dash
# and dash length, in grid units).
MARKER_DASH_START_TUPLE = (11.25, 15.0, 18.75)
MARKER_DASH_LENGTH_F = 2.25

# LLFR-00159: the names of the 12 icons. Delta X and Delta Y are drawn
# here for their buttons (LLFR-00161, LLFR-00162).
OPEN_FILE_ICON_STR = "open_file"
UNDO_ICON_STR = "undo"
TIP_ICON_STR = "tip"
ZOOM_ICON_STR = "zoom"
RESET_ZOOM_ICON_STR = "reset_zoom"
MARKER_ICON_STR = "vertical_marker"
DELTA_X_ICON_STR = "delta_x"
DELTA_Y_ICON_STR = "delta_y"
GRID_ICON_STR = "grid"
EXPORT_ICON_STR = "export"
COPY_ICON_STR = "copy"
# LLFR-00159 item 12, LLFR-00190: the Redo icon.
REDO_ICON_STR = "redo"


def ink_layer(command_list: list) -> tuple:
    """Return a layer stroked with the icon color and the icon pen.

    Inputs:
        command_list: path commands on the 24 by 24 grid.
    Outputs: the layer tuple (command_list, INK_ROLE_STR, NO_ROLE_STR,
        ICON_STROKE_WIDTH_F).
    """
    # LLFR-00159: every outline of a button icon uses the same pen.
    return (command_list, INK_ROLE_STR, NO_ROLE_STR, ICON_STROKE_WIDTH_F)


def ink_dot_layer(center_x_f: float, center_y_f: float,
                  radius_f: float) -> tuple:
    """Return a layer that fills a dot with the icon color.

    Inputs:
        center_x_f: x of the dot center, on the 24 by 24 grid.
        center_y_f: y of the dot center.
        radius_f: radius of the dot.
    Outputs: the layer tuple of a filled circle with no outline.
    """
    # LLFR-00159: the dot on the curve of the Tip icon.
    return ([("O", center_x_f, center_y_f, radius_f)], NO_ROLE_STR,
            INK_ROLE_STR, 0.0)


def segment(start_x_f: float, start_y_f: float, end_x_f: float,
            end_y_f: float) -> list:
    """Return the commands of one straight line.

    Inputs:
        start_x_f, start_y_f: the start point.
        end_x_f, end_y_f: the end point.
    Outputs: a list with a move and a line command.
    """
    # LLFR-00159: the straight strokes of the icons.
    return [("M", start_x_f, start_y_f), ("L", end_x_f, end_y_f)]


def polyline(point_list: list) -> list:
    """Return the commands of an open line through several points.

    Inputs:
        point_list: (x, y) tuples, at least two.
    Outputs: a move command to the first point and line commands to the
        others.
    """
    # LLFR-00159: arrow heads and folded corners.
    first_point_tuple = point_list[0]
    command_list = [("M", first_point_tuple[0], first_point_tuple[1])]
    for point_tuple in point_list[1:]:
        command_list.append(("L", point_tuple[0], point_tuple[1]))
    return command_list


def arrow_head(tip_x_f: float, tip_y_f: float, direction_str: str,
               size_f: float = 2.5) -> list:
    """Return the commands of an open arrow head (a chevron).

    Inputs:
        tip_x_f, tip_y_f: the point of the arrow.
        direction_str: where the arrow points: "left", "right", "up" or
            "down".
        size_f: the length of each side, along both axes.
    Outputs: the commands of the two sides of the head.
    """
    # LLFR-00159: the arrows of Undo, Redo, Reset zoom, Delta X, Delta Y and
    # Export share one head shape.
    if direction_str == "left":
        offset_tuple = (size_f, size_f, size_f, -size_f)
    elif direction_str == "right":
        offset_tuple = (-size_f, size_f, -size_f, -size_f)
    elif direction_str == "up":
        offset_tuple = (size_f, size_f, -size_f, size_f)
    else:
        offset_tuple = (size_f, -size_f, -size_f, -size_f)
    return polyline([
        (tip_x_f + offset_tuple[0], tip_y_f + offset_tuple[1]),
        (tip_x_f, tip_y_f),
        (tip_x_f + offset_tuple[2], tip_y_f + offset_tuple[3])])


def magnifier_layer_list() -> list:
    """Return the lens and handle of the Zoom and Reset zoom icons.

    Inputs: none.
    Outputs: a list of layers: the lens circle and the handle.
    """
    # LLFR-00159: items 4 and 5 share the same magnifying glass.
    return [ink_layer([("O", 10.5, 10.5, 6.75)]),
            ink_layer(segment(15.5, 15.5, 20.5, 20.5))]


def open_file_shape() -> list:
    """Return the Open file icon: an open folder (LLFR-00159, item 1).

    Inputs: none.
    Outputs: the list of layers.
    """
    # LLFR-00159: the back of the folder with its tab, and the front
    # flap tilted open.
    back_list = [("M", 3.5, 18.5), ("L", 3.5, 6.0), ("Q", 3.5, 4.5, 5.0, 4.5),
                 ("L", 8.75, 4.5), ("L", 10.75, 6.75), ("L", 17.0, 6.75),
                 ("Q", 18.5, 6.75, 18.5, 8.25), ("L", 18.5, 10.5)]
    front_list = [("M", 3.5, 19.5), ("L", 7.0, 11.75),
                  ("Q", 7.4, 10.5, 8.75, 10.5), ("L", 20.25, 10.5),
                  ("Q", 21.75, 10.5, 21.25, 12.0), ("L", 18.6, 18.6),
                  ("Q", 18.25, 19.5, 17.25, 19.5), ("Z",)]
    return [ink_layer(back_list), ink_layer(front_list)]


def undo_shape() -> list:
    """Return the Undo icon: an arrow curving to the left (item 2).

    Inputs: none.
    Outputs: the list of layers.
    """
    # LLFR-00159: the shaft bends from the lower right up and to the
    # left, and ends in an arrow head pointing left.
    shaft_list = [("M", 19.5, 19.0), ("C", 19.5, 13.0, 16.5, 9.5, 11.5, 9.5),
                  ("L", 4.5, 9.5)]
    return [ink_layer(shaft_list),
            ink_layer(arrow_head(4.5, 9.5, "left", 4.0))]


def redo_shape() -> list:
    """Return the Redo icon: an arrow curving to the right (item 12).

    Inputs: none.
    Outputs: the list of layers, the Undo icon mirrored left to right.
    """
    # LLFR-00159: the shaft bends from the lower left up and to the
    # right, and ends in an arrow head pointing right.
    shaft_list = [("M", 4.5, 19.0), ("C", 4.5, 13.0, 7.5, 9.5, 12.5, 9.5),
                  ("L", 19.5, 9.5)]
    return [ink_layer(shaft_list),
            ink_layer(arrow_head(19.5, 9.5, "right", 4.0))]


def tip_shape() -> list:
    """Return the Tip icon: a callout pointing at a dot on a curve (3).

    Inputs: none.
    Outputs: the list of layers.
    """
    # LLFR-00159: a wavy curve, a dot on it, and a rounded callout box
    # whose tail points down at the dot.
    curve_list = [("M", 2.5, 21.0), ("C", 4.5, 21.0, 5.0, 17.5, 7.0, 17.5),
                  ("C", 9.5, 17.5, 10.0, 21.0, 13.5, 21.0),
                  ("C", 17.0, 21.0, 18.5, 17.25, 21.5, 16.25)]
    callout_list = [("M", 11.0, 12.0), ("L", 8.5, 14.75), ("L", 14.5, 12.0),
                    ("L", 19.0, 12.0), ("Q", 21.0, 12.0, 21.0, 10.0),
                    ("L", 21.0, 5.0), ("Q", 21.0, 3.0, 19.0, 3.0),
                    ("L", 11.0, 3.0), ("Q", 9.0, 3.0, 9.0, 5.0),
                    ("L", 9.0, 10.0), ("Q", 9.0, 12.0, 11.0, 12.0), ("Z",)]
    return [ink_layer(curve_list), ink_layer(callout_list),
            ink_dot_layer(7.0, 17.5, 2.0)]


def zoom_shape() -> list:
    """Return the Zoom icon: a magnifying glass with a plus (item 4).

    Inputs: none.
    Outputs: the list of layers.
    """
    # LLFR-00159: the plus sign sits in the middle of the lens.
    return magnifier_layer_list() + [
        ink_layer(segment(10.5, 7.5, 10.5, 13.5)),
        ink_layer(segment(7.5, 10.5, 13.5, 10.5))]


def reset_zoom_shape() -> list:
    """Return the Reset zoom icon: a lens with arrows apart (item 5).

    Inputs: none.
    Outputs: the list of layers.
    """
    # LLFR-00159: two arrows in the lens, pointing away from each other
    # to the left and to the right.
    return magnifier_layer_list() + [
        ink_layer(segment(6.75, 10.5, 14.25, 10.5)),
        ink_layer(arrow_head(6.75, 10.5, "left", 1.75)),
        ink_layer(arrow_head(14.25, 10.5, "right", 1.75))]


def marker_shape() -> list:
    """Return the Vertical marker icon: a dashed line with a flag (6).

    Inputs: none.
    Outputs: the list of layers.
    """
    # LLFR-00159: the flag at the top is a pennant with a notch; its
    # left edge is the top of the line. The line below is dashed, as
    # the vertical markers of the plots are (LLFR-00143).
    flag_list = [("M", 7.0, 3.0), ("L", 17.5, 3.0), ("L", 15.0, 6.0),
                 ("L", 17.5, 9.0), ("L", 7.0, 9.0), ("Z",)]
    layer_list = [ink_layer(flag_list)]
    # LLFR-00159: the dashes are filled bars of the pen width, so the
    # gaps stay open at small sizes (round caps would close them).
    half_width_f = ICON_STROKE_WIDTH_F / 2.0
    for dash_start_y_f in MARKER_DASH_START_TUPLE:
        layer_list.append(([("R", 7.0 - half_width_f, dash_start_y_f,
                             ICON_STROKE_WIDTH_F, MARKER_DASH_LENGTH_F,
                             0.4)], NO_ROLE_STR, INK_ROLE_STR, 0.0))
    return layer_list


def delta_x_shape() -> list:
    """Return the Delta X icon: a horizontal arrow between two lines (7).

    Inputs: none.
    Outputs: the list of layers.
    """
    # LLFR-00159: two vertical lines and a double-headed arrow between
    # them.
    return [ink_layer(segment(3.75, 4.0, 3.75, 20.0)),
            ink_layer(segment(20.25, 4.0, 20.25, 20.0)),
            ink_layer(segment(7.5, 12.0, 16.5, 12.0)),
            ink_layer(arrow_head(7.5, 12.0, "left", 2.5)),
            ink_layer(arrow_head(16.5, 12.0, "right", 2.5))]


def delta_y_shape() -> list:
    """Return the Delta Y icon: a vertical arrow between two lines (8).

    Inputs: none.
    Outputs: the list of layers.
    """
    # LLFR-00159: the Delta X icon turned by a quarter turn.
    return [ink_layer(segment(4.0, 3.75, 20.0, 3.75)),
            ink_layer(segment(4.0, 20.25, 20.0, 20.25)),
            ink_layer(segment(12.0, 7.5, 12.0, 16.5)),
            ink_layer(arrow_head(12.0, 7.5, "up", 2.5)),
            ink_layer(arrow_head(12.0, 16.5, "down", 2.5))]


def grid_shape() -> list:
    """Return the Grid icon: a square divided into 3 by 3 cells (9).

    Inputs: none.
    Outputs: the list of layers.
    """
    # LLFR-00159: the frame and two lines in each direction.
    start_f = 3.0
    side_f = 18.0
    layer_list = [ink_layer([("R", start_f, start_f, side_f, side_f, 2.5)])]
    for index_i in (1, 2):
        line_f = start_f + side_f * index_i / 3.0
        layer_list.append(ink_layer(segment(
            line_f, start_f, line_f, start_f + side_f)))
        layer_list.append(ink_layer(segment(
            start_f, line_f, start_f + side_f, line_f)))
    return layer_list


def export_shape() -> list:
    """Return the Export icon: a sheet with an arrow out of it (10).

    Inputs: none.
    Outputs: the list of layers.
    """
    # LLFR-00159: a sheet with a folded corner; its right edge opens
    # where the arrow leaves it.
    sheet_list = [("M", 18.0, 9.75), ("L", 18.0, 8.0), ("L", 13.0, 3.0),
                  ("L", 6.0, 3.0), ("Q", 4.0, 3.0, 4.0, 5.0),
                  ("L", 4.0, 19.0), ("Q", 4.0, 21.0, 6.0, 21.0),
                  ("L", 16.0, 21.0), ("Q", 18.0, 21.0, 18.0, 19.0),
                  ("L", 18.0, 17.75)]
    fold_list = polyline([(13.0, 3.0), (13.0, 8.0), (18.0, 8.0)])
    return [ink_layer(sheet_list), ink_layer(fold_list),
            ink_layer(segment(9.5, 13.75, 21.5, 13.75)),
            ink_layer(arrow_head(21.5, 13.75, "right", 3.0))]


def copy_shape() -> list:
    """Return the Copy icon: two overlapping sheets of paper (11).

    Inputs: none.
    Outputs: the list of layers.
    """
    # LLFR-00159: the front sheet is whole; of the sheet behind it only
    # the part that shows is drawn, with a small gap at the front.
    back_list = [("M", 15.0, 6.25), ("L", 15.0, 5.5),
                 ("Q", 15.0, 3.5, 13.0, 3.5), ("L", 5.5, 3.5),
                 ("Q", 3.5, 3.5, 3.5, 5.5), ("L", 3.5, 13.0),
                 ("Q", 3.5, 15.0, 5.5, 15.0), ("L", 6.25, 15.0)]
    return [ink_layer([("R", 9.0, 9.0, 11.5, 11.5, 2.0)]),
            ink_layer(back_list)]


# LLFR-00159: icon name -> function that returns its layers.
ICON_SHAPE_FUNCTION_DICT = {
    OPEN_FILE_ICON_STR: open_file_shape,
    UNDO_ICON_STR: undo_shape,
    TIP_ICON_STR: tip_shape,
    ZOOM_ICON_STR: zoom_shape,
    RESET_ZOOM_ICON_STR: reset_zoom_shape,
    MARKER_ICON_STR: marker_shape,
    DELTA_X_ICON_STR: delta_x_shape,
    DELTA_Y_ICON_STR: delta_y_shape,
    GRID_ICON_STR: grid_shape,
    EXPORT_ICON_STR: export_shape,
    COPY_ICON_STR: copy_shape,
    REDO_ICON_STR: redo_shape,
}
ICON_NAME_TUPLE = tuple(ICON_SHAPE_FUNCTION_DICT)


def icon_layer_list(icon_name_str: str) -> list:
    """Return the layers of one button icon.

    Inputs:
        icon_name_str: one of ICON_NAME_TUPLE.
    Outputs: the list of layers, on the 24 by 24 grid. Raises KeyError
        for an unknown name.
    """
    # LLFR-00159: one drawing per icon.
    return ICON_SHAPE_FUNCTION_DICT[icon_name_str]()


# ----------------------------------------------------------------------
# App icon (LLFR-00183), on a 100 by 100 grid
# ----------------------------------------------------------------------
APP_ICON_GRID_F = 100.0
# LLFR-00183: below this size in pixels the simpler drawing is used: a
# fuller square, curves kept apart and no tick marks.
APP_ICON_SMALL_SIZE_I = 32
BACKGROUND_ROLE_STR = "background"
BORDER_ROLE_STR = "border"
AXIS_ROLE_STR = "axis"
BLUE_ROLE_STR = "blue"
RED_ROLE_STR = "red"


def app_icon_layer_list(size_i: int) -> list:
    """Return the layers of the app icon drawn at one size.

    Inputs:
        size_i: the side of the drawn icon, in pixels.
    Outputs: the list of layers, on the 100 by 100 grid: the light
        rounded square, the pair of axes, the blue curve and the red
        curve (LLFR-00183). The lines never get thinner than about
        1.25 px, and below APP_ICON_SMALL_SIZE_I the curves are kept
        apart and the tick marks are left out, so the chart stays
        recognizable at 16 by 16 pixels.
    """
    # LLFR-00183: a light rounded square with a small line chart.
    small_b = size_i < APP_ICON_SMALL_SIZE_I
    # LLFR-00183: the lines keep a visible width in pixels at small
    # sizes and grow with the icon at large sizes.
    unit_per_pixel_f = APP_ICON_GRID_F / max(1, size_i)
    axis_width_f = max(1.25 * unit_per_pixel_f, 4.0)
    curve_width_f = max(1.6 * unit_per_pixel_f, 5.0)
    border_width_f = max(1.0 * unit_per_pixel_f, 1.25)
    if small_b:
        # LLFR-00183: a fuller square and two curves kept apart, so they
        # don't blur into each other at 16 by 16 pixels.
        square_tuple = (1.5, 1.5, 97.0, 97.0, 20.0)
        axis_list = polyline([(20.0, 18.0), (20.0, 80.0), (84.0, 80.0)])
        blue_list = [("M", 30.0, 54.0),
                     ("C", 42.0, 54.0, 46.0, 24.0, 60.0, 24.0),
                     ("C", 70.0, 24.0, 74.0, 30.0, 84.0, 28.0)]
        red_list = [("M", 30.0, 70.0),
                    ("C", 44.0, 70.0, 52.0, 56.0, 64.0, 58.0),
                    ("C", 74.0, 60.0, 78.0, 66.0, 84.0, 64.0)]
    else:
        square_tuple = (4.0, 4.0, 92.0, 92.0, 21.0)
        axis_list = polyline([(22.0, 20.0), (22.0, 78.0), (82.0, 78.0)])
        blue_list = [("M", 29.0, 62.0),
                     ("C", 40.0, 62.0, 43.0, 30.0, 55.0, 30.0),
                     ("C", 64.0, 30.0, 68.0, 42.0, 78.0, 38.0)]
        red_list = [("M", 29.0, 46.0),
                    ("C", 40.0, 46.0, 46.0, 66.0, 57.0, 63.0),
                    ("C", 66.0, 60.0, 70.0, 52.0, 78.0, 53.0)]
    layer_list = [
        ([("R",) + square_tuple], BORDER_ROLE_STR, BACKGROUND_ROLE_STR,
         border_width_f),
        (axis_list, AXIS_ROLE_STR, NO_ROLE_STR, axis_width_f)]
    if not small_b:
        # LLFR-00183: tick marks only where they can be seen.
        tick_list = []
        for tick_x_f in (42.0, 62.0):
            tick_list += segment(tick_x_f, 78.0, tick_x_f, 83.0)
        for tick_y_f in (39.0, 58.5):
            tick_list += segment(17.0, tick_y_f, 22.0, tick_y_f)
        layer_list.append((tick_list, AXIS_ROLE_STR, NO_ROLE_STR, 3.5))
    layer_list.append((red_list, RED_ROLE_STR, NO_ROLE_STR, curve_width_f))
    layer_list.append((blue_list, BLUE_ROLE_STR, NO_ROLE_STR, curve_width_f))
    return layer_list
