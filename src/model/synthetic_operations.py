"""Operations that compute synthetic signals (HLFR-00053), without Qt.

Every operation is a pure function on 1-D numpy arrays. Times are in
seconds (HLFR-00007), frequencies in Hz. The functions never change
their input arrays and always return new float64 arrays.

Public API (used by model.synthetic_signals and the user interface):

- ``OPERATION_DICT``: operation id -> SyntheticOperation (menu label,
  abbreviation, group, parameter kind). The operation id is the
  ``operation`` value of the layout file entries (LLFR-00225); it is not
  the abbreviation, which the menu shows in parentheses (LLFR-00268) and
  which starts the names of the synthetic signals (LLFR-00240).
- ``OPERATION_GROUP_LIST``: the menu groups of LLFR-00268, in order, as
  tuples (group label, tuple of operation ids).
- ``operation_group_list()``: the same groups with SyntheticOperation
  objects, ready to build the "Create synthetic signal" menu.
- The operations: ``integral``, ``derivative``, ``lowpass``,
  ``highpass``, ``moving_average``, ``maximum``, ``minimum``,
  ``greater``, ``less``, ``greater_or_equal``, ``less_or_equal``,
  ``add``, ``subtract``, ``multiply``, ``divide``, ``absolute``,
  ``product``, ``fft``.
- The parameter rules for the dialogs: ``sampling_rate_hz``,
  ``allowed_cutoff_range_hz``, ``allowed_filter_order_range`` (and
  ``DEFAULT_FILTER_ORDER_I``, the order the filter dialog starts with),
  ``FILTER_START_TUPLE`` (how a filter starts, ``DEFAULT_FILTER_START_STR``
  selected at first),
  ``allowed_window_range``, ``check_parameter`` (raises
  SyntheticParameterError with a sentence that the dialog can show as
  it is).
- ``compute(operation_str, time_array, source_array_list, parameter)``:
  run any operation by its id.

The parameter of each kind of operation is:

=================  ===========================================
parameter kind     parameter
=================  ===========================================
``none``           None
``filter``         tuple (cutoff_hz, order_i, start_str): the
                   cutoff frequency in Hz, the filter order and
                   how the filter starts (FILTER_START_TUPLE)
``window_i``       window size in samples (int)
``constant_f``     the constant (float)
``second_signal``  None (the second signal is the 2nd source)
``time_range``     tuple (start_s, end_s), in seconds
=================  ===========================================
"""

import math
from dataclasses import dataclass

import numpy as np

from model.errors import (
    SyntheticOperationError, SyntheticParameterError, TooFewSamplesError,
    UnevenTimeStepError)
from model.number_format import format_signal_value

# LLFR-00225: operation ids, the "operation" values of the layout file
# entries. They are kept as they were before the abbreviations of
# LLFR-00268, so that older layout files still load.
INTEGRAL_STR = "integral"
DERIVATIVE_STR = "derivative"
LOWPASS_STR = "lowpass"
HIGHPASS_STR = "highpass"
MOVING_AVERAGE_STR = "movingaverage"
MAXIMUM_STR = "max"
MINIMUM_STR = "min"
GREATER_STR = "greater"
LESS_STR = "less"
GREATER_OR_EQUAL_STR = "greaterorequal"
LESS_OR_EQUAL_STR = "lessorequal"
ADD_STR = "add"
SUBTRACT_STR = "subtract"
MULTIPLY_STR = "multiply"
DIVIDE_STR = "divide"
ABSOLUTE_STR = "abs"
PRODUCT_STR = "product"
FFT_STR = "fft"

# LLFR-00245, LLFR-00269, LLFR-00272, LLFR-00275, LLFR-00248: the kinds
# of parameter an operation asks for.
NO_PARAMETER_STR = "none"
FILTER_PARAMETER_STR = "filter"
WINDOW_PARAMETER_STR = "window_i"
CONSTANT_PARAMETER_STR = "constant_f"
SECOND_SIGNAL_PARAMETER_STR = "second_signal"
TIME_RANGE_PARAMETER_STR = "time_range"

# LLFR-00245: the filter orders the user may choose, and the order the
# filter dialog starts with.
MINIMUM_FILTER_ORDER_I = 1
MAXIMUM_FILTER_ORDER_I = 8
DEFAULT_FILTER_ORDER_I = 2
# LLFR-00245, LLFR-00246: how a filter starts: as if the signal had kept
# its first value before the first sample (steady state, the default),
# or at rest (zero initial state), like a filter switched on at the
# first sample.
FILTER_START_FIRST_VALUE_STR = "first_value"
FILTER_START_ZERO_STR = "zero"
FILTER_START_TUPLE = (FILTER_START_FIRST_VALUE_STR, FILTER_START_ZERO_STR)
DEFAULT_FILTER_START_STR = FILTER_START_FIRST_VALUE_STR
# LLFR-00247: largest allowed difference of a time step from the mean
# step, as a fraction of the mean step.
TIME_STEP_TOLERANCE_F = 0.01
# LLFR-00250: fewest samples an FFT needs.
MINIMUM_FFT_SAMPLES_I = 8
# LLFR-00269: smallest moving average window.
MINIMUM_WINDOW_I = 2

UNEVEN_STEP_MESSAGE_STR = (
    "The operation needs evenly spaced time samples.")
TOO_FEW_SAMPLES_MESSAGE_STR = (
    "The time range holds too few samples for an FFT: it holds {} "
    "samples, and at least 8 are needed.")


@dataclass(frozen=True)
class SyntheticOperation:
    """One operation of the "Create synthetic signal" menu (LLFR-00268).

    Inputs:
        operation_str: the operation id of the layout file entries
            (LLFR-00225), e.g. "lowpass".
        label_str: the operation's name, e.g. "Low-pass filter", also
            the title of its parameter dialog.
        abbreviation_str: the abbreviation that starts the names of its
            synthetic signals (LLFR-00240), e.g. "lpf".
        group_str: the menu group, e.g. "Filters".
        parameter_kind_str: one of the *_PARAMETER_STR kinds.
        source_count_i: number of signals it is computed from (2 for
            Product with signal, 1 otherwise).
    """

    operation_str: str
    label_str: str
    abbreviation_str: str
    group_str: str
    parameter_kind_str: str
    source_count_i: int = 1

    @property
    def menu_label_str(self) -> str:
        """Return the text of the operation in the menu.

        Inputs: none.
        Outputs: the name followed by the abbreviation in parentheses,
            e.g. "Low-pass filter (lpf)".
        """
        # LLFR-00268: each operation shows its abbreviation.
        return f"{self.label_str} ({self.abbreviation_str})"


# LLFR-00268: the menu groups and their operations, in menu order:
# (operation id, name, abbreviation, parameter kind).
OPERATION_TABLE_TUPLE = (
    ("Calculus", (
        (INTEGRAL_STR, "Integral", "int", NO_PARAMETER_STR),
        (DERIVATIVE_STR, "Derivative", "der", NO_PARAMETER_STR))),
    ("Filters", (
        (LOWPASS_STR, "Low-pass filter", "lpf", FILTER_PARAMETER_STR),
        (HIGHPASS_STR, "High-pass filter", "hpf", FILTER_PARAMETER_STR),
        (MOVING_AVERAGE_STR, "Moving average", "mavg",
         WINDOW_PARAMETER_STR))),
    ("Statistics", (
        (MAXIMUM_STR, "Max", "max", NO_PARAMETER_STR),
        (MINIMUM_STR, "Min", "min", NO_PARAMETER_STR))),
    ("Comparison", (
        (GREATER_STR, "Greater than", "gt", CONSTANT_PARAMETER_STR),
        (LESS_STR, "Less than", "lt", CONSTANT_PARAMETER_STR),
        (GREATER_OR_EQUAL_STR, "Greater than or equal", "ge",
         CONSTANT_PARAMETER_STR),
        (LESS_OR_EQUAL_STR, "Less than or equal", "le",
         CONSTANT_PARAMETER_STR))),
    ("Arithmetic", (
        (ADD_STR, "Add constant", "add", CONSTANT_PARAMETER_STR),
        (SUBTRACT_STR, "Subtract constant", "sub", CONSTANT_PARAMETER_STR),
        (MULTIPLY_STR, "Multiply by constant", "mul",
         CONSTANT_PARAMETER_STR),
        (DIVIDE_STR, "Divide by constant", "div", CONSTANT_PARAMETER_STR),
        (ABSOLUTE_STR, "Absolute value", "abs", NO_PARAMETER_STR),
        (PRODUCT_STR, "Product with signal", "prod",
         SECOND_SIGNAL_PARAMETER_STR))),
    ("Spectrum", (
        (FFT_STR, "FFT", "fft", TIME_RANGE_PARAMETER_STR),)),
)

# LLFR-00268: operation id -> SyntheticOperation, in menu order.
OPERATION_DICT = {
    operation_str: SyntheticOperation(
        operation_str, label_str, abbreviation_str, group_str, kind_str,
        2 if kind_str == SECOND_SIGNAL_PARAMETER_STR else 1)
    for group_str, row_tuple in OPERATION_TABLE_TUPLE
    for operation_str, label_str, abbreviation_str, kind_str in row_tuple}

# LLFR-00268: (group label, operation ids) in menu order.
OPERATION_GROUP_LIST = [
    (group_str, tuple(row[0] for row in row_tuple))
    for group_str, row_tuple in OPERATION_TABLE_TUPLE]


def operation_group_list() -> list:
    """Return the operation groups of the synthetic signal menu.

    Inputs: none.
    Outputs: a list of tuples (group label, list of SyntheticOperation),
        groups and operations in the order of LLFR-00268.
    """
    # LLFR-00268: groups Calculus, Filters, Statistics, Comparison,
    # Arithmetic and Spectrum, in this order.
    return [(group_str, [OPERATION_DICT[operation_str]
                         for operation_str in operation_tuple])
            for group_str, operation_tuple in OPERATION_GROUP_LIST]


def find_operation(operation_str: str) -> SyntheticOperation:
    """Return the operation with the given id.

    Inputs:
        operation_str: an operation id of LLFR-00225, e.g. "integral".
    Outputs: its SyntheticOperation.
    Raises: SyntheticOperationError when the id is not known.
    """
    # LLFR-00240, LLFR-00262: only the operations of HLFR-00053 exist.
    if (not isinstance(operation_str, str)
            or operation_str not in OPERATION_DICT):
        raise SyntheticOperationError(
            f'"{operation_str}" is not a known operation.')
    return OPERATION_DICT[operation_str]


def as_float_array(value_array) -> np.ndarray:
    """Return the samples as a new 1-D float64 array.

    Inputs:
        value_array: array-like samples.
    Outputs: a float64 copy, so that the input is never changed.
    """
    # LLFR-00253: operations never change the signals they read.
    return np.array(value_array, dtype=np.float64).reshape(-1)


def integral(time_array, value_array) -> np.ndarray:
    """Return the cumulative integral of a signal over time.

    Inputs:
        time_array: the time samples, in seconds.
        value_array: the signal samples, as many as the time samples.
    Outputs: at each sample, the trapezoidal integral from the first
        sample up to it; the first value is 0.
    """
    # LLFR-00243: trapezoidal rule, first sample 0.
    times_array = as_float_array(time_array)
    values_array = as_float_array(value_array)
    if values_array.size == 0:
        return values_array
    area_array = (np.diff(times_array)
                  * (values_array[1:] + values_array[:-1]) / 2.0)
    return np.concatenate(([0.0], np.cumsum(area_array)))


def derivative(time_array, value_array) -> np.ndarray:
    """Return the rate of change of a signal with respect to time.

    Inputs:
        time_array: the time samples, in seconds.
        value_array: the signal samples, as many as the time samples.
    Outputs: central differences of the neighbors on both sides, and
        one-sided differences at the first and last samples.
    Raises: SyntheticOperationError with fewer than 2 samples.
    """
    # LLFR-00244: central differences inside, one neighbor at the ends.
    times_array = as_float_array(time_array)
    values_array = as_float_array(value_array)
    if values_array.size < 2:
        raise SyntheticOperationError(
            "The derivative needs at least 2 time samples.")
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.gradient(values_array, times_array)


def sampling_rate_hz(time_array) -> float:
    """Return the sampling rate of the time signal.

    Inputs:
        time_array: the time samples, in seconds.
    Outputs: 1 divided by the mean time step, in Hz.
    Raises: SyntheticOperationError with fewer than 2 samples or a mean
        step that is not positive; UnevenTimeStepError when a time step
        differs from the mean step by more than 1%.
    """
    # LLFR-00247: sampling rate = 1 / mean time step.
    times_array = as_float_array(time_array)
    if times_array.size < 2:
        raise SyntheticOperationError(
            "The operation needs at least 2 time samples.")
    step_array = np.diff(times_array)
    mean_step_s = float(np.mean(step_array))
    if not math.isfinite(mean_step_s) or mean_step_s <= 0.0:
        raise UnevenTimeStepError(UNEVEN_STEP_MESSAGE_STR)
    # LLFR-00247: every step within 1% of the mean step.
    largest_deviation_s = float(np.max(np.abs(step_array - mean_step_s)))
    if largest_deviation_s > TIME_STEP_TOLERANCE_F * mean_step_s:
        raise UnevenTimeStepError(UNEVEN_STEP_MESSAGE_STR)
    return 1.0 / mean_step_s


def allowed_cutoff_range_hz(time_array) -> tuple:
    """Return the allowed cutoff frequencies of the filters.

    Inputs:
        time_array: the time samples, in seconds.
    Outputs: a tuple (lowest, highest) in Hz; both limits are excluded:
        the cutoff must be greater than 0 and less than half the
        sampling rate.
    Raises: the errors of sampling_rate_hz.
    """
    # LLFR-00245: greater than 0 and less than half the sampling rate.
    return (0.0, sampling_rate_hz(time_array) / 2.0)


def allowed_window_range(sample_count_i: int) -> tuple:
    """Return the allowed moving average window sizes.

    Inputs:
        sample_count_i: number of samples of the signal.
    Outputs: a tuple (smallest, largest) of whole numbers; both limits
        are included. The range is empty (smallest > largest) when the
        signal has fewer than 2 samples.
    """
    # LLFR-00269: from 2 up to the number of samples of the signal.
    return (MINIMUM_WINDOW_I, int(sample_count_i))


def allowed_filter_order_range() -> tuple:
    """Return the filter orders the user may choose.

    Inputs: none.
    Outputs: a tuple (smallest, largest) of whole numbers; both limits
        are included.
    """
    # LLFR-00245: a whole number from 1 to 8.
    return (MINIMUM_FILTER_ORDER_I, MAXIMUM_FILTER_ORDER_I)


def butterworth_filter(time_array, value_array, cutoff_hz: float,
                       order_i: int, start_str: str,
                       filter_type_str: str) -> np.ndarray:
    """Filter a signal forward in time with a Butterworth filter.

    Inputs:
        time_array: the time samples, in seconds, evenly spaced.
        value_array: the signal samples.
        cutoff_hz: the cutoff frequency, inside allowed_cutoff_range_hz.
        order_i: the filter order, inside allowed_filter_order_range.
        start_str: FILTER_START_FIRST_VALUE_STR or FILTER_START_ZERO_STR.
        filter_type_str: "lowpass" or "highpass" (scipy's btype).
    Outputs: the filtered samples, delayed in time like the output of a
        real-time filter.
    Raises: the errors of sampling_rate_hz; SyntheticParameterError when
        the cutoff, the order or the start is not allowed.

    The filter is scipy.signal.sosfilt, run once over the samples in
    time order. With the "first_value" start, its state starts at the
    steady state for a signal that had kept the value of its first
    sample before it (scipy.signal.sosfilt_zi times the first sample),
    so the curve does not jump at the start: a constant signal stays
    constant through a low-pass filter and gives 0 through a high-pass
    filter. With the "zero" start, the state starts at 0, as if the
    signal had been 0 before the first sample, like a filter switched
    on at the first sample, so the curve settles after the start: for
    a constant signal, a low-pass output starts below the constant and
    rises towards it, and a high-pass output starts at a part of the
    constant and decays towards 0.
    """
    # LLFR-00246: Butterworth filter of the chosen order, applied once,
    # forward in time, as a real-time filter. scipy.signal is imported
    # here so that the app starts fast (LLFR-00189): it is only needed
    # when a filter is created.
    from scipy import signal as scipy_signal
    values_array = as_float_array(value_array)
    sampling_hz = sampling_rate_hz(time_array)
    cutoff_hz, order_i, start_str = check_filter(
        (cutoff_hz, order_i, start_str), time_array)
    section_array = scipy_signal.butter(
        order_i, cutoff_hz / (sampling_hz / 2.0), btype=filter_type_str,
        output="sos")
    if values_array.size == 0:
        return values_array
    # LLFR-00246: the start the user chose: the steady state of the
    # first sample, or at rest.
    if start_str == FILTER_START_ZERO_STR:
        initial_state_array = np.zeros((section_array.shape[0], 2))
    else:
        initial_state_array = (scipy_signal.sosfilt_zi(section_array)
                               * values_array[0])
    filtered_array, _ = scipy_signal.sosfilt(section_array, values_array,
                                             zi=initial_state_array)
    return filtered_array


def lowpass(time_array, value_array, cutoff_hz: float,
            order_i: int = DEFAULT_FILTER_ORDER_I,
            start_str: str = DEFAULT_FILTER_START_STR) -> np.ndarray:
    """Return the signal filtered by a low-pass Butterworth filter.

    Inputs:
        time_array: the time samples, in seconds, evenly spaced.
        value_array: the signal samples.
        cutoff_hz: the cutoff frequency, in Hz.
        order_i: the filter order, 1 to 8.
        start_str: how the filter starts (FILTER_START_TUPLE).
    Outputs: the filtered samples (see butterworth_filter).
    Raises: see butterworth_filter.
    """
    # LLFR-00246: low-pass filter.
    return butterworth_filter(time_array, value_array, cutoff_hz,
                              order_i, start_str, "lowpass")


def highpass(time_array, value_array, cutoff_hz: float,
             order_i: int = DEFAULT_FILTER_ORDER_I,
             start_str: str = DEFAULT_FILTER_START_STR) -> np.ndarray:
    """Return the signal filtered by a high-pass Butterworth filter.

    Inputs:
        time_array: the time samples, in seconds, evenly spaced.
        value_array: the signal samples.
        cutoff_hz: the cutoff frequency, in Hz.
        order_i: the filter order, 1 to 8.
        start_str: how the filter starts (FILTER_START_TUPLE).
    Outputs: the filtered samples (see butterworth_filter).
    Raises: see butterworth_filter.
    """
    # LLFR-00246: high-pass filter.
    return butterworth_filter(time_array, value_array, cutoff_hz,
                              order_i, start_str, "highpass")


def moving_average(value_array, window_i: int) -> np.ndarray:
    """Return the centered moving average of a signal.

    Inputs:
        value_array: the signal samples.
        window_i: the window size, in samples, inside
            allowed_window_range.
    Outputs: at each sample, the mean of the window centered on it. An
        even window holds one more sample after the sample than before
        it. Near the ends the window holds only the samples that exist.
        A window that holds a NaN sample gives NaN.
    Raises: SyntheticParameterError when the window is out of range.
    """
    # LLFR-00270: centered window, one more sample after when even.
    values_array = as_float_array(value_array)
    window_i = check_window(window_i, values_array.size)
    before_i = (window_i - 1) // 2
    after_i = window_i // 2
    index_array = np.arange(values_array.size)
    # LLFR-00270: the window shrinks to the samples that exist.
    first_array = np.maximum(index_array - before_i, 0)
    end_array = np.minimum(index_array + after_i + 1, values_array.size)
    missing_array = np.isnan(values_array)
    sum_array = np.concatenate(
        ([0.0], np.cumsum(np.where(missing_array, 0.0, values_array))))
    nan_count_array = np.concatenate(([0], np.cumsum(missing_array)))
    window_sum_array = sum_array[end_array] - sum_array[first_array]
    count_array = end_array - first_array
    mean_array = window_sum_array / count_array
    window_nan_count_array = (nan_count_array[end_array]
                              - nan_count_array[first_array])
    mean_array[window_nan_count_array > 0] = np.nan
    return mean_array


def constant_like(value_array, constant_f: float) -> np.ndarray:
    """Return a constant signal with as many samples as another one.

    Inputs:
        value_array: the signal whose sample count is used.
        constant_f: the value of every sample.
    Outputs: the constant float64 array.
    """
    # LLFR-00271: Max and Min are constant signals.
    return np.full(as_float_array(value_array).size, constant_f,
                   dtype=np.float64)


def maximum(value_array) -> np.ndarray:
    """Return the constant signal of the largest sample.

    Inputs:
        value_array: the signal samples over the whole time range.
    Outputs: at every sample, the largest value of all samples (NaN
        samples are ignored; all NaN gives NaN).
    """
    # LLFR-00271: largest value over the whole time range of the file.
    values_array = as_float_array(value_array)
    if values_array.size == 0 or np.all(np.isnan(values_array)):
        return constant_like(values_array, np.nan)
    return constant_like(values_array, float(np.nanmax(values_array)))


def minimum(value_array) -> np.ndarray:
    """Return the constant signal of the smallest sample.

    Inputs:
        value_array: the signal samples over the whole time range.
    Outputs: at every sample, the smallest value of all samples (NaN
        samples are ignored; all NaN gives NaN).
    """
    # LLFR-00271: smallest value over the whole time range of the file.
    values_array = as_float_array(value_array)
    if values_array.size == 0 or np.all(np.isnan(values_array)):
        return constant_like(values_array, np.nan)
    return constant_like(values_array, float(np.nanmin(values_array)))


def greater(value_array, constant_f: float) -> np.ndarray:
    """Return 1 where the signal is greater than the constant, else 0.

    Inputs:
        value_array: the signal samples.
        constant_f: the constant.
    Outputs: a float64 array of 1.0 and 0.0.
    """
    # LLFR-00273: "Greater than".
    return (as_float_array(value_array) > constant_f).astype(np.float64)


def less(value_array, constant_f: float) -> np.ndarray:
    """Return 1 where the signal is less than the constant, else 0.

    Inputs:
        value_array: the signal samples.
        constant_f: the constant.
    Outputs: a float64 array of 1.0 and 0.0.
    """
    # LLFR-00273: "Less than".
    return (as_float_array(value_array) < constant_f).astype(np.float64)


def greater_or_equal(value_array, constant_f: float) -> np.ndarray:
    """Return 1 where the signal is >= the constant, else 0.

    Inputs:
        value_array: the signal samples.
        constant_f: the constant.
    Outputs: a float64 array of 1.0 and 0.0.
    """
    # LLFR-00273: "Greater than or equal".
    return (as_float_array(value_array) >= constant_f).astype(np.float64)


def less_or_equal(value_array, constant_f: float) -> np.ndarray:
    """Return 1 where the signal is <= the constant, else 0.

    Inputs:
        value_array: the signal samples.
        constant_f: the constant.
    Outputs: a float64 array of 1.0 and 0.0.
    """
    # LLFR-00273: "Less than or equal".
    return (as_float_array(value_array) <= constant_f).astype(np.float64)


def add(value_array, constant_f: float) -> np.ndarray:
    """Return the signal plus a constant.

    Inputs:
        value_array: the signal samples.
        constant_f: the constant.
    Outputs: each sample plus the constant.
    """
    # LLFR-00274: "Add constant".
    return as_float_array(value_array) + float(constant_f)


def subtract(value_array, constant_f: float) -> np.ndarray:
    """Return the signal minus a constant.

    Inputs:
        value_array: the signal samples.
        constant_f: the constant.
    Outputs: each sample minus the constant.
    """
    # LLFR-00274: "Subtract constant".
    return as_float_array(value_array) - float(constant_f)


def multiply(value_array, constant_f: float) -> np.ndarray:
    """Return the signal multiplied by a constant.

    Inputs:
        value_array: the signal samples.
        constant_f: the constant.
    Outputs: each sample multiplied by the constant.
    """
    # LLFR-00274: "Multiply by constant".
    return as_float_array(value_array) * float(constant_f)


def divide(value_array, constant_f: float) -> np.ndarray:
    """Return the signal divided by a constant.

    Inputs:
        value_array: the signal samples.
        constant_f: the constant, not 0.
    Outputs: each sample divided by the constant.
    Raises: SyntheticParameterError when the constant is 0.
    """
    # LLFR-00272, LLFR-00274: "Divide by constant", never by 0.
    constant_f = check_constant(DIVIDE_STR, constant_f)
    return as_float_array(value_array) / constant_f


def absolute(value_array) -> np.ndarray:
    """Return the absolute value of a signal.

    Inputs:
        value_array: the signal samples.
    Outputs: the absolute value of each sample.
    """
    # LLFR-00284: "Absolute value", sample by sample.
    return np.abs(as_float_array(value_array))


def product(first_array, second_array) -> np.ndarray:
    """Return two signals multiplied sample by sample.

    Inputs:
        first_array: samples of the right-clicked signal.
        second_array: samples of the second signal, as many.
    Outputs: first sample times second sample at each time sample.
    Raises: SyntheticOperationError when the sample counts differ.
    """
    # LLFR-00276: product at the same time sample.
    first_values_array = as_float_array(first_array)
    second_values_array = as_float_array(second_array)
    if first_values_array.size != second_values_array.size:
        raise SyntheticOperationError(
            "The two signals must have the same number of samples.")
    return first_values_array * second_values_array


def fft(time_array, value_array, start_s: float, end_s: float) -> tuple:
    """Return the one-sided amplitude spectrum of part of a signal.

    Inputs:
        time_array: the time samples of the whole file, in seconds.
        value_array: the signal samples, as many as the time samples.
        start_s: first time of the range, in seconds (included).
        end_s: last time of the range, in seconds (included).
    Outputs: a tuple (frequency_array, amplitude_array): frequencies from
        0 Hz up to half the sampling rate, in Hz, and the amplitude at
        each one. The samples are weighted by a periodic Hann window and
        scaled by 2 / sum(window), with the 0 Hz value (and the value
        at half the sampling rate, for an even sample count) not
        doubled, so that a sine of amplitude A whose period count in
        the range is a whole number gives a peak of height A; for other
        sines the Hann window keeps the peak above 0.84 A.
    Raises: UnevenTimeStepError when the time signal is not evenly
        spaced; TooFewSamplesError when fewer than 8 samples are in the
        range.
    """
    # LLFR-00247: the sampling rate of the whole time signal.
    sampling_hz = sampling_rate_hz(time_array)
    times_array = as_float_array(time_array)
    values_array = as_float_array(value_array)
    # LLFR-00248: only the samples whose time is within the range.
    inside_array = (times_array >= start_s) & (times_array <= end_s)
    selected_array = values_array[inside_array]
    # LLFR-00250: at least 8 samples.
    if selected_array.size < MINIMUM_FFT_SAMPLES_I:
        raise TooFewSamplesError(
            TOO_FEW_SAMPLES_MESSAGE_STR.format(selected_array.size))
    # LLFR-00249: Hann window, one-sided amplitude, 0 Hz to fs / 2.
    # The periodic Hann window (the DFT-even form used for spectra):
    # a whole number of periods leaks into the two neighbor bins only.
    sample_index_array = np.arange(selected_array.size)
    window_array = 0.5 - 0.5 * np.cos(
        2.0 * np.pi * sample_index_array / selected_array.size)
    spectrum_array = np.fft.rfft(selected_array * window_array)
    amplitude_array = np.abs(spectrum_array) * 2.0 / np.sum(window_array)
    amplitude_array[0] /= 2.0
    if selected_array.size % 2 == 0:
        amplitude_array[-1] /= 2.0
    frequency_array = np.fft.rfftfreq(selected_array.size,
                                      d=1.0 / sampling_hz)
    return frequency_array, amplitude_array


def is_real_number(value) -> bool:
    """Tell whether a value is a finite int or float (not a bool).

    Inputs:
        value: any object.
    Outputs: True for a finite Python or numpy int or float.
    """
    # LLFR-00245, LLFR-00272: a parameter must be a number.
    if isinstance(value, (bool, np.bool_)):
        return False
    if not isinstance(value, (int, float, np.integer, np.floating)):
        return False
    return math.isfinite(float(value))


def check_cutoff_hz(cutoff_hz, time_array) -> float:
    """Check a cutoff frequency against the allowed range.

    Inputs:
        cutoff_hz: the cutoff frequency, in Hz.
        time_array: the time samples, in seconds.
    Outputs: the cutoff as a float.
    Raises: the errors of sampling_rate_hz; SyntheticParameterError
        when the cutoff is not a number or not in the allowed range.
    """
    # LLFR-00245: greater than 0 and less than half the sampling rate.
    lowest_hz, highest_hz = allowed_cutoff_range_hz(time_array)
    # LLFR-00245: the limits in the number format of the data tips.
    range_text_str = (f"The cutoff frequency must be a number greater "
                      f"than {format_signal_value(lowest_hz)} Hz and "
                      f"less than {format_signal_value(highest_hz)} Hz.")
    if not is_real_number(cutoff_hz):
        raise SyntheticParameterError(range_text_str)
    if not lowest_hz < float(cutoff_hz) < highest_hz:
        raise SyntheticParameterError(range_text_str)
    return float(cutoff_hz)


def check_filter_order(order_i) -> int:
    """Check a filter order against the allowed range.

    Inputs:
        order_i: the order; an int, or a float with a whole value (as a
            hand-edited layout file may hold).
    Outputs: the order as an int.
    Raises: SyntheticParameterError when the order is not a whole number
        or not in the allowed range.
    """
    # LLFR-00245: a whole number from 1 to 8.
    smallest_i, largest_i = allowed_filter_order_range()
    range_text_str = (f"The filter order must be a whole number from "
                      f"{smallest_i} to {largest_i}.")
    if not is_real_number(order_i) or not float(order_i).is_integer():
        raise SyntheticParameterError(range_text_str)
    if not smallest_i <= int(order_i) <= largest_i:
        raise SyntheticParameterError(range_text_str)
    return int(order_i)


def check_filter_start(start_str) -> str:
    """Check how a filter starts.

    Inputs:
        start_str: one of FILTER_START_TUPLE.
    Outputs: the same text.
    Raises: SyntheticParameterError for any other value.
    """
    # LLFR-00245, LLFR-00246: from the first value or from zero.
    if not isinstance(start_str, str) or start_str not in (
            FILTER_START_TUPLE):
        raise SyntheticParameterError(
            f'The filter start must be "{FILTER_START_FIRST_VALUE_STR}" '
            f'(from the first value) or "{FILTER_START_ZERO_STR}" (from '
            f'zero).')
    return start_str


def check_filter(filter_tuple, time_array) -> tuple:
    """Check the cutoff frequency, the order and the start of a filter.

    Inputs:
        filter_tuple: a tuple or list (cutoff_hz, order_i, start_str).
        time_array: the time samples, in seconds.
    Outputs: the tuple (cutoff as a float, order as an int, start).
    Raises: the errors of sampling_rate_hz; SyntheticParameterError when
        it is not three values, or a value is not allowed (the cutoff
        is checked first, then the order, then the start).
    """
    # LLFR-00245: every value must be allowed.
    if (not isinstance(filter_tuple, (tuple, list))
            or len(filter_tuple) != 3):
        raise SyntheticParameterError(
            "A filter needs a cutoff frequency, in Hz, an order and a "
            "start.")
    cutoff_hz = check_cutoff_hz(filter_tuple[0], time_array)
    return (cutoff_hz, check_filter_order(filter_tuple[1]),
            check_filter_start(filter_tuple[2]))


def check_window(window_i, sample_count_i: int) -> int:
    """Check a moving average window size against the allowed range.

    Inputs:
        window_i: the window size; an int, or a float with a whole
            value (as a hand-edited layout file may hold).
        sample_count_i: number of samples of the signal.
    Outputs: the window size as an int.
    Raises: SyntheticParameterError when the size is not a whole number
        or not in the allowed range.
    """
    # LLFR-00269: a whole number from 2 up to the number of samples.
    smallest_i, largest_i = allowed_window_range(sample_count_i)
    range_text_str = (f"The window size must be a whole number of "
                      f"samples from {smallest_i} to {largest_i}.")
    if not is_real_number(window_i) or not float(window_i).is_integer():
        raise SyntheticParameterError(range_text_str)
    if not smallest_i <= int(window_i) <= largest_i:
        raise SyntheticParameterError(range_text_str)
    return int(window_i)


def check_constant(operation_str: str, constant_f) -> float:
    """Check the constant of a Comparison or Arithmetic operation.

    Inputs:
        operation_str: the operation id, e.g. "divide".
        constant_f: the constant.
    Outputs: the constant as a float.
    Raises: SyntheticParameterError when it is not a finite number, or
        is 0 for "divide".
    """
    # LLFR-00272: a number, not 0 for "Divide by constant".
    if not is_real_number(constant_f):
        raise SyntheticParameterError("The constant must be a number.")
    if operation_str == DIVIDE_STR and float(constant_f) == 0.0:
        raise SyntheticParameterError(
            "The constant must not be 0 for a division.")
    return float(constant_f)


def check_time_range(time_range_tuple) -> tuple:
    """Check the time range of an FFT.

    Inputs:
        time_range_tuple: a tuple or list (start_s, end_s), in seconds.
    Outputs: the tuple (start_s, end_s) of floats.
    Raises: SyntheticParameterError when it is not two finite numbers.
    """
    # LLFR-00248: the time range is two times, in seconds.
    if (not isinstance(time_range_tuple, (tuple, list))
            or len(time_range_tuple) != 2
            or not all(is_real_number(time_s)
                       for time_s in time_range_tuple)):
        raise SyntheticParameterError(
            "The time range must be two numbers: a start and an end "
            "time, in seconds.")
    return (float(time_range_tuple[0]), float(time_range_tuple[1]))


def check_parameter(operation_str: str, parameter, time_array,
                    sample_count_i: int):
    """Check the parameter of an operation and return it normalized.

    The parameter dialogs (LLFR-00245, LLFR-00269, LLFR-00272) can call
    this and show the error message as it is.

    Inputs:
        operation_str: the operation id.
        parameter: the parameter of its kind (see the module docstring).
        time_array: the time samples, in seconds.
        sample_count_i: number of samples of the signal.
    Outputs: the parameter as a float, an int, a tuple (cutoff float,
        order int, start str), a tuple of two floats or None, according to the
        kind.
    Raises: SyntheticOperationError for an unknown operation or uneven
        time samples (filters); SyntheticParameterError when the
        parameter is not allowed.
    """
    # LLFR-00245, LLFR-00269, LLFR-00272: allowed parameter values.
    kind_str = find_operation(operation_str).parameter_kind_str
    if kind_str == FILTER_PARAMETER_STR:
        return check_filter(parameter, time_array)
    if kind_str == WINDOW_PARAMETER_STR:
        return check_window(parameter, sample_count_i)
    if kind_str == CONSTANT_PARAMETER_STR:
        return check_constant(operation_str, parameter)
    if kind_str == TIME_RANGE_PARAMETER_STR:
        return check_time_range(parameter)
    # LLFR-00240: the other operations take no parameter.
    if parameter is not None:
        raise SyntheticParameterError(
            f'The operation "{operation_str}" takes no parameter.')
    return None


def compute(operation_str: str, time_array, source_array_list: list,
            parameter) -> tuple:
    """Run an operation by its id.

    Inputs:
        operation_str: the operation id.
        time_array: the time samples of the file, in seconds.
        source_array_list: the samples of the signals it is computed
            from (two for "product", one otherwise).
        parameter: the parameter, already checked by check_parameter.
    Outputs: a tuple (value_array, frequency_array): frequency_array is
        the x-axis in Hz of an FFT signal, and None for the others.
    Raises: SyntheticSignalError subclasses when the operation can't be
        done.
    """
    # LLFR-00243 to LLFR-00276, LLFR-00284: dispatch to the operation.
    first_array = source_array_list[0]
    operation_function_dict = {
        INTEGRAL_STR: lambda: integral(time_array, first_array),
        DERIVATIVE_STR: lambda: derivative(time_array, first_array),
        MAXIMUM_STR: lambda: maximum(first_array),
        MINIMUM_STR: lambda: minimum(first_array),
        LOWPASS_STR: lambda: lowpass(time_array, first_array,
                                     *parameter),
        HIGHPASS_STR: lambda: highpass(time_array, first_array,
                                       *parameter),
        MOVING_AVERAGE_STR: lambda: moving_average(first_array,
                                                   parameter),
        GREATER_STR: lambda: greater(first_array, parameter),
        LESS_STR: lambda: less(first_array, parameter),
        GREATER_OR_EQUAL_STR: lambda: greater_or_equal(first_array,
                                                       parameter),
        LESS_OR_EQUAL_STR: lambda: less_or_equal(first_array, parameter),
        ADD_STR: lambda: add(first_array, parameter),
        SUBTRACT_STR: lambda: subtract(first_array, parameter),
        MULTIPLY_STR: lambda: multiply(first_array, parameter),
        DIVIDE_STR: lambda: divide(first_array, parameter),
        ABSOLUTE_STR: lambda: absolute(first_array),
        PRODUCT_STR: lambda: product(first_array, source_array_list[-1]),
    }
    find_operation(operation_str)
    if operation_str == FFT_STR:
        # LLFR-00249: an FFT signal has its own frequency x-axis.
        start_s, end_s = parameter
        frequency_array, amplitude_array = fft(time_array, first_array,
                                               start_s, end_s)
        return amplitude_array, frequency_array
    return operation_function_dict[operation_str](), None
