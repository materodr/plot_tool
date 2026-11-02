"""Number formats of the values the app shows (no Qt needed).

The view formats tip, marker and delta marker values with these
functions (view.value_text), and the model uses the same time format in
the names of synthetic signals (LLFR-00240), so that both always agree.
In a synthetic signal name, a number is written with letters and digits
only (format_name_number).
"""

from decimal import Decimal

# LLFR-00043, LLFR-00044: 6 significant digits, as Python's "g" format.
VALUE_FORMAT_STR = ".6g"
# LLFR-00240: in a synthetic signal name, the decimal point of a
# positive number is written "p", that of a negative number "n", and a
# negative whole number ends with "n0".
POSITIVE_POINT_STR = "p"
NEGATIVE_POINT_STR = "n"
NEGATIVE_WHOLE_SUFFIX_STR = "n0"


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


def format_name_number(value_f: float) -> str:
    """Return a number as it is written in a synthetic signal name.

    Inputs:
        value_f: the number (a constant, a cutoff frequency, a filter
            order, a window size or an FFT time); finite.
    Outputs: the number with letters and digits only, rounded to the 6
        significant digits of the data tip values and written without
        an exponent: 2.5 is "2p5", -2.5 is "2n5", 2 is "2", -2 is "2n0",
        1e+06 is "1000000", 1e-07 is "0p0000001", 1234567 is "1234570"
        and zero is "0".
    """
    # LLFR-00240 item 4: zero (also -0.0, or a value rounded to zero) is
    # written "0".
    number_f = float(value_f)
    # LLFR-00240 item 3, LLFR-00043, LLFR-00044: rounded to the same
    # significant digits as the data tip values, then written with all
    # its digits and no exponent (Decimal's "f" format).
    rounded_str = format(abs(number_f), VALUE_FORMAT_STR)
    digits_str = format(Decimal(rounded_str), "f")
    if Decimal(digits_str) == 0:
        return "0"
    negative_b = number_f < 0
    # LLFR-00240 item 1: the decimal point is "p" or "n", with no minus.
    if "." in digits_str:
        point_str = NEGATIVE_POINT_STR if negative_b else POSITIVE_POINT_STR
        return digits_str.replace(".", point_str)
    # LLFR-00240 item 2: a whole number as it is; "n0" when negative.
    if negative_b:
        return digits_str + NEGATIVE_WHOLE_SUFFIX_STR
    return digits_str
