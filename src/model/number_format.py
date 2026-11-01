"""Number formats of the values the app shows (no Qt needed).

The view formats tip, marker and delta marker values with these
functions (view.value_text), and the model uses the same time format in
the names of FFT signals (LLFR-00240), so that both always agree.
"""

# LLFR-00043, LLFR-00044: 6 significant digits, as Python's "g" format.
VALUE_FORMAT_STR = ".6g"


def format_time_value(time_s: float) -> str:
    """Return a time as the data tips show it, without the unit.

    Inputs:
        time_s: the time, in seconds.
    Outputs: the number with 6 significant digits, for example "1.5".
    """
    # LLFR-00043: the data tip's x value; LLFR-00240 uses it in FFT names.
    return format(float(time_s), VALUE_FORMAT_STR)


def format_signal_value(value_f: float) -> str:
    """Return a y-axis value as the data tips show it.

    Inputs:
        value_f: the value, as stored in the file.
    Outputs: the number with 6 significant digits.
    """
    # LLFR-00044: the tip's y value, without a unit.
    return format(float(value_f), VALUE_FORMAT_STR)
