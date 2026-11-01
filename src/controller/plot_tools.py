"""Names of the plot tools of the top panel (HLFR-00032).

Plain strings without any Qt dependency, so that the controller and the
view share the same names (COR-00009). Only one plot tool is active at a
time (LLFR-00079); NO_TOOL_STR means that none is active.

Constants:
    NO_TOOL_STR: no plot tool is active.
    TIP_TOOL_STR: the Tip tool (LLFR-00018, LLFR-00042, LLFR-00045).
    ZOOM_TOOL_STR: the Zoom tool (LLFR-00077, LLFR-00078).
    MARKER_TOOL_STR: the Vertical marker tool (LLFR-00080).
    DELTA_X_TOOL_STR: the Delta X tool (LLFR-00161, LLFR-00163).
    DELTA_Y_TOOL_STR: the Delta Y tool (LLFR-00162, LLFR-00163).
    DELTA_TOOL_TUPLE: the two delta marker tools.
    PLOT_TOOL_TUPLE: every plot tool name, NO_TOOL_STR excluded.
"""

# LLFR-00079: the names of the plot tools; at most one is active.
NO_TOOL_STR = ""
TIP_TOOL_STR = "tip"
ZOOM_TOOL_STR = "zoom"
MARKER_TOOL_STR = "marker"
# LLFR-00161, LLFR-00162: the Delta X and Delta Y tools (HLFR-00032).
DELTA_X_TOOL_STR = "delta_x"
DELTA_Y_TOOL_STR = "delta_y"
DELTA_TOOL_TUPLE = (DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR)
PLOT_TOOL_TUPLE = (TIP_TOOL_STR, ZOOM_TOOL_STR, MARKER_TOOL_STR,
                   DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR)


def is_known_plot_tool(tool_str: str) -> bool:
    """Tell whether a name is a plot tool or NO_TOOL_STR.

    Inputs:
        tool_str: the name to check.
    Outputs: True for NO_TOOL_STR and for every name in PLOT_TOOL_TUPLE.
    """
    # LLFR-00079, LLFR-00109: only these values describe a tool state.
    return tool_str == NO_TOOL_STR or tool_str in PLOT_TOOL_TUPLE


def is_delta_tool(tool_str: str) -> bool:
    """Tell whether a tool picks the points of a delta marker.

    Inputs:
        tool_str: the tool name.
    Outputs: True for DELTA_X_TOOL_STR and DELTA_Y_TOOL_STR.
    """
    # LLFR-00163: a left click on a curve picks a point with these tools.
    return tool_str in DELTA_TOOL_TUPLE
