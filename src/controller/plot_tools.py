"""Names of the plot tools of the top panel (HLFR-00032).

Plain strings without any Qt dependency, so that the controller and the
view share the same names (COR-00009). Only one plot tool is active at a
time (LLFR-00079); NO_TOOL_STR means that none is active.

Constants:
    NO_TOOL_STR: no plot tool is active.
    TIP_TOOL_STR: the Tip tool (LLFR-00018, LLFR-00042, LLFR-00045).
    ZOOM_TOOL_STR: the Zoom tool (LLFR-00077, LLFR-00078).
    PAN_TOOL_STR: the Pan tool (LLFR-00355, LLFR-00356).
    MARKER_TOOL_STR: the Vertical marker tool (LLFR-00080).
    DELTA_X_TOOL_STR: the Delta X tool (LLFR-00161, LLFR-00163).
    DELTA_Y_TOOL_STR: the Delta Y tool (LLFR-00162, LLFR-00163).
    DELTA_TOOL_TUPLE: the two delta marker tools.
    AREA_TOOL_STR: the Area tool (LLFR-00286, LLFR-00287).
    TEXT_TOOL_STR: the Text tool (LLFR-00320, LLFR-00321).
    ARROW_TOOL_STR: the Arrow tool (LLFR-00366, LLFR-00367).
    PLOT_TOOL_TUPLE: every plot tool name, NO_TOOL_STR excluded.
"""

# LLFR-00079: the names of the plot tools; at most one is active.
NO_TOOL_STR = ""
TIP_TOOL_STR = "tip"
ZOOM_TOOL_STR = "zoom"
# LLFR-00355, LLFR-00356: the Pan tool (HLFR-00036), between Zoom and
# Vertical marker in the plot tool group (LLFR-00347).
PAN_TOOL_STR = "pan"
MARKER_TOOL_STR = "marker"
# LLFR-00161, LLFR-00162: the Delta X and Delta Y tools (HLFR-00032).
DELTA_X_TOOL_STR = "delta_x"
DELTA_Y_TOOL_STR = "delta_y"
DELTA_TOOL_TUPLE = (DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR)
# LLFR-00286, LLFR-00320: the Area and Text tools (HLFR-00066,
# HLFR-00073), the last two plot tools of LLFR-00347. Activating them
# only changes the active tool; what they do on the plots is added with
# the areas and the text notes.
AREA_TOOL_STR = "area"
TEXT_TOOL_STR = "text"
# LLFR-00366: the Arrow tool (HLFR-00081), the last plot tool of
# LLFR-00347, right of Text.
ARROW_TOOL_STR = "arrow"
# LLFR-00347: in the order of their buttons.
PLOT_TOOL_TUPLE = (TIP_TOOL_STR, ZOOM_TOOL_STR, PAN_TOOL_STR,
                   MARKER_TOOL_STR, DELTA_X_TOOL_STR, DELTA_Y_TOOL_STR,
                   AREA_TOOL_STR, TEXT_TOOL_STR, ARROW_TOOL_STR)


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
