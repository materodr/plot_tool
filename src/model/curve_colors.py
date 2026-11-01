"""Colors of the signal curves in a plot (HLFR-00020).

The first 8 curves drawn in a plot use a fixed palette (LLFR-00033)
that starts with blue, black and red (LLFR-00144).
From the 9th curve on, each new curve gets a random color that is
clearly different from the colors already used in the plot
(LLFR-00034). Vertical markers use a reserved color that is never
given to a curve (LLFR-00083).
"""

# LLFR-00033: 8 colors that are easy to tell apart on a white
# background (taken from the Tableau 10 set, plus black).
# LLFR-00144: the first three are blue, black and red, in that order.
PALETTE_COLOR_TUPLE = (
    "#1f77b4",  # blue
    "#000000",  # black
    "#d62728",  # red
    "#2ca02c",  # green
    "#ff7f0e",  # orange
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#17becf",  # cyan
)

# LLFR-00083: reserved color of the vertical markers. It is not in the
# palette, every palette color is far from it, and random curve colors
# always keep at least MINIMUM_COLOR_DISTANCE_F from it.
MARKER_COLOR_STR = "#ff00ff"  # magenta

# LLFR-00034: minimum Euclidean RGB distance between a random color and
# every color already used in the plot.
MINIMUM_COLOR_DISTANCE_F = 70.0
# LLFR-00034: colors lighter than this relative luminance (0 to 1) are
# hard to see on a white background and are not used. The value is just
# above the lightest palette color (cyan, about 0.61), so random colors
# keep at least the contrast of the palette.
MAXIMUM_LUMINANCE_F = 0.62
# LLFR-00034: random tries before the minimum distance is relaxed.
TRIES_PER_DISTANCE_I = 200
# LLFR-00034: factor applied to the minimum distance after each round of
# failed tries.
DISTANCE_RELAX_FACTOR_F = 0.5


def hex_to_rgb(color_str: str) -> tuple:
    """Convert a "#rrggbb" color to its red, green and blue values.

    Inputs:
        color_str: color written as "#rrggbb".
    Outputs: a tuple (red, green, blue) of ints from 0 to 255.
    """
    # LLFR-00034: colors are compared as RGB values.
    hex_digits_str = color_str.lstrip("#")
    return tuple(int(hex_digits_str[index_i:index_i + 2], 16)
                 for index_i in (0, 2, 4))


def rgb_to_hex(rgb_tuple: tuple) -> str:
    """Convert red, green and blue values to a "#rrggbb" color.

    Inputs:
        rgb_tuple: a tuple (red, green, blue) of ints from 0 to 255.
    Outputs: the color written as "#rrggbb" in lower case.
    """
    # LLFR-00034: random colors are returned in the palette's format.
    return "#{:02x}{:02x}{:02x}".format(*rgb_tuple)


def color_distance(first_color_str: str, second_color_str: str) -> float:
    """Return the Euclidean distance between two colors in RGB space.

    Inputs:
        first_color_str: color written as "#rrggbb".
        second_color_str: color written as "#rrggbb".
    Outputs: the distance, from 0 (same color) to about 441.7.
    """
    # LLFR-00034: a large distance means the colors are easy to tell apart.
    squared_sum_f = 0.0
    for first_value_i, second_value_i in zip(hex_to_rgb(first_color_str),
                                             hex_to_rgb(second_color_str)):
        squared_sum_f += (first_value_i - second_value_i) ** 2
    return squared_sum_f ** 0.5


def color_luminance(color_str: str) -> float:
    """Return the relative luminance of a color (approximate, linear).

    Inputs:
        color_str: color written as "#rrggbb".
    Outputs: a value from 0 (black) to 1 (white).
    """
    # LLFR-00034: used to reject colors too light for a white background.
    red_i, green_i, blue_i = hex_to_rgb(color_str)
    return (0.2126 * red_i + 0.7152 * green_i + 0.0722 * blue_i) / 255.0


def random_color(random_generator) -> str:
    """Return a random color that is visible on a white background.

    Inputs:
        random_generator: a random.Random used to draw the color.
    Outputs: a color written as "#rrggbb" whose luminance is at most
        MAXIMUM_LUMINANCE_F.
    """
    # LLFR-00034: draw until the color is dark enough to be seen.
    while True:
        color_str = rgb_to_hex(tuple(random_generator.randint(0, 255)
                                     for _ in range(3)))
        if color_luminance(color_str) <= MAXIMUM_LUMINANCE_F:
            return color_str


def is_far_from_marker_color(color_str: str) -> bool:
    """Tell whether a color is clearly different from the marker color.

    Inputs:
        color_str: color written as "#rrggbb".
    Outputs: True when the color is at least MINIMUM_COLOR_DISTANCE_F
        away from MARKER_COLOR_STR.
    """
    # LLFR-00083: curves never look like a vertical marker.
    return (color_distance(color_str, MARKER_COLOR_STR)
            >= MINIMUM_COLOR_DISTANCE_F)


def next_curve_color(drawn_count_i: int, used_color_list: list,
                     random_generator) -> str:
    """Choose the color of the next curve drawn in a plot.

    Inputs:
        drawn_count_i: how many curves have ever been drawn in the plot
            before this one.
        used_color_list: colors ("#rrggbb") of the curves currently in
            the plot.
        random_generator: a random.Random used from the 9th curve on.
    Outputs: the color of the new curve, written as "#rrggbb".
    """
    # LLFR-00033: the first 8 curves take the palette colors in order.
    if drawn_count_i < len(PALETTE_COLOR_TUPLE):
        return PALETTE_COLOR_TUPLE[drawn_count_i]
    # LLFR-00034: a random color far from every used color. If no such
    # color is found, relax the distance, but never repeat a used color.
    used_lower_set = {color_str.lower() for color_str in used_color_list}
    minimum_distance_f = MINIMUM_COLOR_DISTANCE_F
    while True:
        for _ in range(TRIES_PER_DISTANCE_I):
            color_str = random_color(random_generator)
            if color_str in used_lower_set:
                continue
            # LLFR-00083: the marker color counts as always used, and its
            # distance is never relaxed.
            if not is_far_from_marker_color(color_str):
                continue
            if all(color_distance(color_str, used_str) >= minimum_distance_f
                   for used_str in used_lower_set):
                return color_str
        minimum_distance_f *= DISTANCE_RELAX_FACTOR_F
