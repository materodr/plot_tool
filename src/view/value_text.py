"""Texts of the values the plots show (no Qt needed).

The hover and pinned tips, the vertical marker times and the delta
marker values all format their numbers here, so that a delta marker
shows its value "in the same number format as the tip" (LLFR-00169,
LLFR-00171).
"""

# LLFR-00043, LLFR-00044: the number formats live in the model, so
# that the names of FFT signals (LLFR-00240) use the same time format.
from model.number_format import (  # noqa: F401 (re-exported)
    VALUE_FORMAT_STR, format_signal_value, format_time_value)

# LLFR-00169, LLFR-00171: "Δ" is a plain Unicode character, drawn by the
# plot fonts (every font of view.theme.PLOT_FONT_FAMILY_LIST has it).
DELTA_SIGN_STR = "Δ"


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


def format_frequency_text(frequency_hz: float) -> str:
    """Return a frequency as shown in the data tips of a frequency plot.

    Inputs:
        frequency_hz: the frequency, in Hz.
    Outputs: the text ``f = <frequency> Hz``, in the number format of
        the times (LLFR-00043).
    """
    # LLFR-00260: frequency plots show the x value in Hz.
    return f"f = {format_time_value(frequency_hz)} Hz"


def format_frequency_tip_text(signal_name_str: str, frequency_hz: float,
                              value_f: float) -> str:
    """Return the two-line text of a data tip on a frequency plot.

    Inputs:
        signal_name_str: name of the FFT signal of the curve.
        frequency_hz: x-axis value of the point, in Hz.
        value_f: y-axis value of the point (the amplitude).
    Outputs: the text ``f = <frequency> Hz`` and ``<name> = <value>``
        on two lines.
    """
    # LLFR-00260: the x value in Hz, instead of seconds; LLFR-00044: the
    # y value as for every data tip.
    return (f"{format_frequency_text(frequency_hz)}\n"
            f"{signal_name_str} = {format_signal_value(value_f)}")


def format_delta_frequency_text(delta_hz: float) -> str:
    """Return the text of a Delta X marker on a frequency plot.

    Inputs:
        delta_hz: frequency of the second point minus frequency of the
            first, in Hz.
    Outputs: the text ``Δf = <value> Hz``.
    """
    # LLFR-00261: signed, in Hz, in the number format of the data tip's
    # x value (LLFR-00260).
    return f"{DELTA_SIGN_STR}f = {format_time_value(delta_hz)} Hz"


def format_delta_y_text(delta_f: float) -> str:
    """Return the text of a Delta Y marker.

    Inputs:
        delta_f: value of the second point minus value of the first.
    Outputs: the text ``Δy = <value>``, without a unit.
    """
    # LLFR-00171: signed, without a unit, in the tip's y format.
    return f"{DELTA_SIGN_STR}y = {format_signal_value(delta_f)}"
