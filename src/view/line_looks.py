"""Widths and styles of the lines of the plot objects (no Qt).

Flags, curves, delta markers, arrows, text note boxes and shapes have a
preset width 1 to 5 and a line style (HLFR-00159, HLFR-00160). Width 1
is the thickness each object had before the widths could be chosen
(LLFR-01361), and higher widths grow as the curve widths do
(LLFR-01362). A dashed line keeps the dash pattern of its kind
(LLFR-01367).
"""

from model.workspace import (
    LINE_STYLE_CONTINUOUS_STR, LINE_STYLE_DASH_DOTTED_STR,
    LINE_STYLE_DASHED_STR, LINE_STYLE_DOTTED_STR, LINE_STYLE_TUPLE,
    PRESET_WIDTH_TUPLE)

# LLFR-01362: the thickness of preset width N as a multiple of width 1,
# as the curve widths grow (LLFR-00041).
WIDTH_FACTOR_DICT = {1: 1.0, 2: 2.0, 3: 3.0, 4: 4.5, 5: 6.0}
# LLFR-01364: the texts of the "Line style" option, in menu order.
LINE_STYLE_TEXT_DICT = {
    LINE_STYLE_CONTINUOUS_STR: "Continuous",
    LINE_STYLE_DASHED_STR: "Dashed",
    LINE_STYLE_DOTTED_STR: "Dotted",
    LINE_STYLE_DASH_DOTTED_STR: "Dash-dotted",
}
# LLFR-01367: the dash pattern of a dashed text note box and shape, in
# points (6 on, 4 off), and the dotted and dash-dotted lines.
DEFAULT_DASH_TUPLE = (0, (6.0, 4.0))
DOTTED_DASH_TUPLE = (0, (1.0, 2.0))
DASH_DOTTED_DASH_TUPLE = (0, (6.0, 2.5, 1.0, 2.5))


def line_width_f(base_width_f: float, width_i: int) -> float:
    """Return the thickness of a line of a preset width.

    Inputs:
        base_width_f: the thickness of preset width 1, in points.
        width_i: the preset width 1 to 5; any other value counts as 1.
    Outputs: the thickness, in points.
    """
    # LLFR-01373, LLFR-01362: width 1 is the former thickness.
    if width_i not in PRESET_WIDTH_TUPLE:
        width_i = 1
    return float(base_width_f) * WIDTH_FACTOR_DICT[width_i]


def matplotlib_line_style(line_style_str: str, dashed_value=None):
    """Return the matplotlib line style of a line style.

    Inputs:
        line_style_str: one of LINE_STYLE_TUPLE; any other value counts
            as continuous.
        dashed_value: the dash pattern of the object's kind for a dashed
            line (LLFR-01367); None for DEFAULT_DASH_TUPLE.
    Outputs: "-" or a dash tuple (offset, (on, off, ...)).
    """
    # LLFR-01365, LLFR-01367: the four styles.
    if line_style_str == LINE_STYLE_DASHED_STR:
        return DEFAULT_DASH_TUPLE if dashed_value is None else dashed_value
    if line_style_str == LINE_STYLE_DOTTED_STR:
        return DOTTED_DASH_TUPLE
    if line_style_str == LINE_STYLE_DASH_DOTTED_STR:
        return DASH_DOTTED_DASH_TUPLE
    return "-"


def line_style_or(style_value, default_style_str: str) -> str:
    """Return a usable line style.

    Inputs:
        style_value: any value.
        default_style_str: the style to use when it is not a style.
    Outputs: style_value when it is one of LINE_STYLE_TUPLE, else the
        default.
    """
    # LLFR-01366: the default style of each kind.
    if isinstance(style_value, str) and style_value in LINE_STYLE_TUPLE:
        return style_value
    return default_style_str


def width_or_one(width_value) -> int:
    """Return a usable preset width.

    Inputs:
        width_value: any value.
    Outputs: width_value when it is a preset width, else 1.
    """
    # LLFR-01361: width 1 by default.
    if isinstance(width_value, bool) or width_value not in PRESET_WIDTH_TUPLE:
        return 1
    return int(width_value)
