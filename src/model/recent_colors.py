"""The rules of the recent colors list of the color submenu (LLFR-00419).

The list holds the last 8 different colors that the user confirmed in
the color picker or chose from the list, most recent first, with no
color listed twice. It is shared by every color option (LLFR-00388).
The view keeps it in the app's settings between launches; this module
only holds the rules, with no Qt code (COR-00009), so that they can be
tested without a display.
"""

from model.curve_colors import hex_color_or_none

# LLFR-00419: how many colors the list keeps.
MAXIMUM_RECENT_COLORS_I = 8


def cleaned_recent_colors(stored_value) -> list:
    """Return the usable recent colors read from the app's settings.

    Inputs:
        stored_value: the value read from the settings: a list of texts,
            a single text, None, or anything else when the settings
            were edited or cannot be read.
    Outputs: a list of at most MAXIMUM_RECENT_COLORS_I lowercase
        "#rrggbb" colors, in the stored order, without repeats; entries
        that are not "#rrggbb" are left out. A value that cannot be read
        gives an empty list.
    """
    # LLFR-00419: while the settings cannot be read the list is empty, so
    # the submenu shows only "Other color...".
    if isinstance(stored_value, str):
        stored_list = [stored_value]
    elif isinstance(stored_value, (list, tuple)):
        stored_list = list(stored_value)
    else:
        return []
    color_list = []
    for stored_entry in stored_list:
        color_str = hex_color_or_none(stored_entry)
        # LLFR-00419: no color listed twice, and at most 8 colors.
        if color_str is None or color_str in color_list:
            continue
        color_list.append(color_str)
        if len(color_list) == MAXIMUM_RECENT_COLORS_I:
            break
    return color_list


def recent_colors_after_use(recent_color_list: list,
                            used_color_str: str) -> list:
    """Return the recent colors after the user confirmed or chose one.

    Inputs:
        recent_color_list: the current list, most recent first.
        used_color_str: the color confirmed in the picker or chosen from
            the list, "#rrggbb" in any case; it may be the color the
            item already has.
    Outputs: a new list with the used color first, removed from any
        later place, and only the first MAXIMUM_RECENT_COLORS_I colors.
        A value that is not "#rrggbb" leaves the list unchanged.
    """
    # LLFR-00419: the used color goes first, even when it is the item's
    # current color or already in the list.
    color_list = cleaned_recent_colors(recent_color_list)
    used_color_str = hex_color_or_none(used_color_str)
    if used_color_str is None:
        return color_list
    color_list = [used_color_str] + [
        color_str for color_str in color_list
        if color_str != used_color_str]
    # LLFR-00419: only the last 8 different colors are kept.
    return color_list[:MAXIMUM_RECENT_COLORS_I]
