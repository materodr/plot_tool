"""Number formats of the values the plots show (no Qt needed).

The hover and pinned tips, the vertical marker times and the delta
marker values all format their numbers here, so that a delta marker
shows its value "in the same number format as the tip" (LLFR-00169,
LLFR-00171).
"""

# LLFR-00043, LLFR-00044: 6 significant digits, as Python's "g" format.
VALUE_FORMAT_STR = ".6g"
# LLFR-00169, LLFR-00171: "Δ" is a plain Unicode character, drawn by the
# plot fonts (every font of view.theme.PLOT_FONT_FAMILY_LIST has it).
DELTA_SIGN_STR = "Δ"


def format_time_value(time_s: float) -> str:
    """Return a time as the tips show it, without the unit.

    Inputs:
        time_s: the time, in seconds.
    Outputs: the number with 6 significant digits.
    """
    # LLFR-00043: the tip's x value.
    return format(float(time_s), VALUE_FORMAT_STR)


def format_signal_value(value_f: float) -> str:
    """Return a y-axis value as the tips show it.

    Inputs:
        value_f: the value, as stored in the file.
    Outputs: the number with 6 significant digits.
    """
    # LLFR-00044: the tip's y value, without a unit.
    return format(float(value_f), VALUE_FORMAT_STR)


def format_time_text(time_s: float) -> str:
    """Return a time as shown in tips and below marker labels.

    Inputs:
        time_s: the time, in seconds.
    Outputs: the text ``t = <time> s``.
    """
    # LLFR-00043, LLFR-00092: times are shown in seconds.
    return f"t = {format_time_value(time_s)} s"


def format_tip_text(signal_name_str: str, time_s: float,
                    value_f: float) -> str:
    """Return the two-line text of a hover or pinned tip.

    Inputs:
        signal_name_str: name of the signal of the curve.
        time_s: x-axis value of the point, in seconds.
        value_f: y-axis value of the point, as stored in the file.
    Outputs: the text ``t = <time> s`` and ``<name> = <value>`` on two
        lines.
    """
    # LLFR-00043: the x value is shown in seconds.
    # LLFR-00044: the y value is shown as stored, without a unit.
    return (f"{format_time_text(time_s)}\n"
            f"{signal_name_str} = {format_signal_value(value_f)}")


def format_delta_x_text(delta_s: float) -> str:
    """Return the text of a Delta X marker.

    Inputs:
        delta_s: time of the second point minus time of the first, in s.
    Outputs: the text ``Δt = <value> s``.
    """
    # LLFR-00169: signed, in seconds, in the tip's x format.
    return f"{DELTA_SIGN_STR}t = {format_time_value(delta_s)} s"


def format_delta_y_text(delta_f: float) -> str:
    """Return the text of a Delta Y marker.

    Inputs:
        delta_f: value of the second point minus value of the first.
    Outputs: the text ``Δy = <value>``, without a unit.
    """
    # LLFR-00171: signed, without a unit, in the tip's y format.
    return f"{DELTA_SIGN_STR}y = {format_signal_value(delta_f)}"
