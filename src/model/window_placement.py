"""Where an undocked window is opened (HLFR-00123, HLFR-00141).

The rules are plain arithmetic on rectangles, so they hold no Qt code
(COR-00009): the view passes the available areas of the screens, as
(x, y, width, height) tuples in desktop pixels, and gets back the
position and size to give the window.

- A new undocked window gets the size of the main window's plot panel
  (LLFR-00981) and its position moved 30 pixels to the right and down
  (LLFR-01093).
- A window whose top edge lies on a screen over less than 100 pixels of
  its width is moved onto the screen that shows the main window, to the
  nearest position where the whole window is on that screen
  (LLFR-01048).
- A window larger than the available area of the screen it is placed on
  is made smaller to fit it (LLFR-01049).
"""

# LLFR-01093: the offset of a new undocked window from the plot panel.
NEW_WINDOW_OFFSET_I = 30
# LLFR-01048: the part of the top edge that must lie on a screen.
MINIMUM_TOP_EDGE_ON_SCREEN_I = 100
# LLFR-01046: the smallest usable size of a window or a panel.
MINIMUM_WINDOW_SIZE_I = 1


def new_window_tuple(plot_panel_tuple: tuple) -> tuple:
    """Return the window of a new undock.

    Inputs:
        plot_panel_tuple: (x, y, width, height) of the main window's plot
            panel, in desktop pixels.
    Outputs: (x, y, width, height) of the new undocked window, before it
        is kept on a screen (placed_window_tuple).
    """
    # LLFR-00981: the size of the plot panel; LLFR-01093: its position
    # moved 30 pixels to the right and 30 pixels down.
    x_i, y_i, width_i, height_i = (int(value_i)
                                   for value_i in plot_panel_tuple)
    return (x_i + NEW_WINDOW_OFFSET_I, y_i + NEW_WINDOW_OFFSET_I,
            max(width_i, MINIMUM_WINDOW_SIZE_I),
            max(height_i, MINIMUM_WINDOW_SIZE_I))


def top_edge_overlap_i(window_tuple: tuple, screen_tuple: tuple) -> int:
    """Return how much of a window's top edge lies on a screen.

    Inputs:
        window_tuple: (x, y, width, height) of the window.
        screen_tuple: (x, y, width, height) of the screen's available
            area.
    Outputs: the number of pixels of the window's top edge inside the
        screen, 0 when the edge is above or below it.
    """
    # LLFR-01048: the top edge holds the title bar the user drags.
    x_i, y_i, width_i, _ = window_tuple
    screen_x_i, screen_y_i, screen_width_i, screen_height_i = screen_tuple
    if not screen_y_i <= y_i < screen_y_i + screen_height_i:
        return 0
    left_i = max(x_i, screen_x_i)
    right_i = min(x_i + width_i, screen_x_i + screen_width_i)
    return max(right_i - left_i, 0)


def limited_size_tuple(window_tuple: tuple, screen_tuple: tuple) -> tuple:
    """Return a window made no larger than a screen's available area.

    Inputs:
        window_tuple: (x, y, width, height) of the window.
        screen_tuple: (x, y, width, height) of the available area.
    Outputs: (x, y, width, height) with the width and height reduced to
        those of the area when they are larger.
    """
    # LLFR-01049: the width or the height, or both, fit the screen.
    x_i, y_i, width_i, height_i = window_tuple
    return (x_i, y_i,
            max(min(width_i, screen_tuple[2]), MINIMUM_WINDOW_SIZE_I),
            max(min(height_i, screen_tuple[3]), MINIMUM_WINDOW_SIZE_I))


def nearest_inside_tuple(window_tuple: tuple, screen_tuple: tuple) -> tuple:
    """Return a window moved to the nearest place fully on a screen.

    Inputs:
        window_tuple: (x, y, width, height), already no larger than the
            screen's available area.
        screen_tuple: (x, y, width, height) of the available area.
    Outputs: (x, y, width, height) at the nearest position where the
        whole window is inside the area.
    """
    # LLFR-01048: the nearest position, each coordinate on its own.
    x_i, y_i, width_i, height_i = window_tuple
    screen_x_i, screen_y_i, screen_width_i, screen_height_i = screen_tuple
    x_i = min(max(x_i, screen_x_i), screen_x_i + screen_width_i - width_i)
    y_i = min(max(y_i, screen_y_i), screen_y_i + screen_height_i - height_i)
    return (x_i, y_i, width_i, height_i)


def placed_window_tuple(window_tuple: tuple, screen_list: list,
                        main_screen_tuple: tuple) -> tuple:
    """Return where an undocked window is opened, kept on a screen.

    Inputs:
        window_tuple: (x, y, width, height) asked for, in desktop pixels.
        screen_list: the (x, y, width, height) available areas of every
            screen.
        main_screen_tuple: the available area of the screen that shows
            the main window, or () when unknown (the first screen is
            used then).
    Outputs: (x, y, width, height) to give the window. With no screen
        known, the window is returned unchanged.
    """
    window_tuple = tuple(int(value_i) for value_i in window_tuple)
    screen_list = [tuple(int(value_i) for value_i in screen_tuple)
                   for screen_tuple in screen_list]
    if not screen_list:
        return window_tuple
    if not main_screen_tuple:
        main_screen_tuple = screen_list[0]
    main_screen_tuple = tuple(int(value_i) for value_i in main_screen_tuple)
    # LLFR-01048: the screen that holds most of the top edge.
    best_screen_tuple = max(
        screen_list,
        key=lambda screen_tuple: top_edge_overlap_i(window_tuple,
                                                    screen_tuple))
    needed_i = min(MINIMUM_TOP_EDGE_ON_SCREEN_I, window_tuple[2])
    if top_edge_overlap_i(window_tuple, best_screen_tuple) >= needed_i:
        # LLFR-01049: kept where it is, no larger than that screen.
        return limited_size_tuple(window_tuple, best_screen_tuple)
    # LLFR-01048, LLFR-01049: onto the main window's screen, whole.
    return nearest_inside_tuple(
        limited_size_tuple(window_tuple, main_screen_tuple),
        main_screen_tuple)
