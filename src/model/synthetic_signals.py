"""Synthetic signals of the open data files (HLFR-00053), without Qt.

A synthetic signal is computed from one or two signals of the signal
list (data file signals or other synthetic signals) by one of the
operations of model.synthetic_operations. Synthetic signals live only
in memory (HLFR-00055, LLFR-00595): one SyntheticSignalStore holds the
synthetic signals of every open data file, in creation order.

Each synthetic signal belongs to the data file of the signal it was
computed from, the right-clicked signal of a product (LLFR-00940), and
its name starts with the prefix ``file<N>_`` of that file, followed by
the name of LLFR-00240 built from the names of its sources without
their prefix (LLFR-00908); the second signal of a product always
keeps its own prefix (LLFR-00958). The signal also keeps its plain
name, without any prefix the app put into it, for the Save signals
button (LLFR-00945). ``ordered_signal_names`` gives the order of the
signal list: file after file, each file's synthetic signals after its
own signals (LLFR-00939).

Public API:

- ``synthetic_name(operation_str, source_name_list, parameter,
  used_name_set)``: the name of a new synthetic signal (LLFR-00240,
  LLFR-00241); ``base_synthetic_name`` gives it before LLFR-00241.
- ``SyntheticSignal``: one synthetic signal.
- ``SyntheticSignalStore``: create, look up, rename and delete
  synthetic signals, and turn them into layout file entries and back.
- ``entries_text(entry_list)``: the JSON text of a list of entries, as
  "Copy equation" puts it on the clipboard (LLFR-00279).
- ``LayoutSignalLoader``: create the synthetic signals of a layout file,
  reusing identical ones and renaming those whose name is in use, and
  say which were not created and why (LLFR-00262, LLFR-00282,
  LLFR-00237); ``create_layout_signals`` runs it.

Layout file entries (LLFR-00225 item 10, LLFR-00227)
----------------------------------------------------
The layout file holds the synthetic signals as a JSON list, under the
key ``"synthetic_signals"``, in creation order, except the FFT signals,
which are neither saved nor loaded (LLFR-00283). Each entry is a JSON
object with these keys:

- ``"name"``: the current name of the synthetic signal (string);
- ``"operation"``: the operation id (string), one of ``integral``,
  ``derivative``, ``lowpass``, ``highpass``, ``movingaverage``, ``max``,
  ``min``, ``greater``, ``less``, ``greaterorequal``, ``lessorequal``,
  ``add``, ``subtract``, ``multiply``, ``divide``, ``abs``, ``product``
  (an ``fft`` entry is reported and not created, LLFR-00283). These ids
  are not the abbreviations of the menu (LLFR-00268) that start the
  signal names (LLFR-00240): they stay as they were, so that older
  layout files, whose entries hold the older names, still load with the
  names they saved;
- ``"signals"``: the current names of the signals it is computed from
  (list of strings; two names for ``product``, the right-clicked signal
  first, one name otherwise);
- ``"parameter"``: for ``lowpass`` and ``highpass``, an object
  ``{"cutoff": <Hz>, "order": <whole number>, "start": "first_value"
  | "zero"}`` with the cutoff frequency in Hz, the filter order and how
  the filter starts (LLFR-00245, LLFR-00246); the window size
  in samples (whole number) for ``movingaverage``; the constant
  (number) for the Comparison and Arithmetic operations with a
  constant; ``null`` for the others.

Example::

    [
      {
        "name": "file1_lpf_2p5Hz_order2_Speed",
        "operation": "lowpass",
        "signals": [
          "file1_Speed"
        ],
        "parameter": {
          "cutoff": 2.5,
          "order": 2,
          "start": "first_value"
        }
      },
      {
        "name": "file1_lpf_2p5Hz_order2_Speed_prod_file2_Torque",
        "operation": "product",
        "signals": [
          "file1_lpf_2p5Hz_order2_Speed",
          "file2_Torque"
        ],
        "parameter": null
      }
    ]

Numbers are written by Python's json module, which writes floats with
repr precision, so they are read back as the same value (LLFR-00227).
"""

import json
import re
from dataclasses import dataclass, field

import numpy as np

from model import synthetic_operations as operations
from model.data_files import (
    file_prefix, identical_time_signals_b, prefix_number, without_prefix)
from model.errors import (
    EmptySyntheticNameError, SyntheticEntryError, SyntheticNameInUseError,
    SyntheticSignalError, SyntheticSourceError)
from model.number_format import format_name_number

# LLFR-00227: keys of a layout file entry of a synthetic signal.
NAME_KEY_STR = "name"
OPERATION_KEY_STR = "operation"
SIGNALS_KEY_STR = "signals"
PARAMETER_KEY_STR = "parameter"
START_KEY_STR = "start"
END_KEY_STR = "end"
CUTOFF_KEY_STR = "cutoff"
ORDER_KEY_STR = "order"
FILTER_START_KEY_STR = "start"
# LLFR-00225: key of the list of entries in the layout file.
LAYOUT_KEY_STR = "synthetic_signals"
# LLFR-00227: the layout file is indented by 2 spaces.
JSON_INDENT_I = 2
# LLFR-00283: the reason an FFT entry of a layout file is not created.
FFT_NOT_LOADED_STR = "FFT signals are not loaded from layout files."
# LLFR-00241: first number added to a name that is already used.
FIRST_SUFFIX_NUMBER_I = 2


def parameter_name_part(operation_str: str, parameter) -> str:
    """Return the part of a synthetic name that shows the parameter.

    Inputs:
        operation_str: the operation id, e.g. "lowpass".
        parameter: the checked parameter of the operation (see
            model.synthetic_operations), or None.
    Outputs: "" for the operations without a parameter (and for the
        product, whose second signal is a source); else the text that
        LLFR-00240 puts between the abbreviation and the source name:
        "<constant>", "<cutoff>Hz_order<order>", "<window>samples" or
        "<start>s_to_<end>s". Every number is written with letters and
        digits only, with the significant digits of the data tip values
        (format_name_number), for example "2p5" or "2n0".
    """
    # LLFR-00240: every number with letters and digits only, rounded to
    # the data tip's significant digits; how a filter starts is never
    # part of the name.
    kind_str = operations.find_operation(operation_str).parameter_kind_str
    if kind_str == operations.CONSTANT_PARAMETER_STR:
        return format_name_number(parameter)
    if kind_str == operations.FILTER_PARAMETER_STR:
        cutoff_hz, order_i = parameter[0], parameter[1]
        return (f"{format_name_number(cutoff_hz)}Hz_order"
                f"{format_name_number(int(order_i))}")
    if kind_str == operations.WINDOW_PARAMETER_STR:
        return f"{format_name_number(int(parameter))}samples"
    if kind_str == operations.TIME_RANGE_PARAMETER_STR or (
            kind_str == operations.STATISTIC_RANGE_PARAMETER_STR
            and parameter is not None):
        # LLFR-00240: the FFT time range (LLFR-00248), and the shown
        # range of a statistic (LLFR-01310).
        start_s, end_s = parameter
        return (f"{format_name_number(start_s)}s_to_"
                f"{format_name_number(end_s)}s")
    if kind_str == operations.GENERATOR_PARAMETER_STR:
        # LLFR-01301: the values of a signal made from scratch.
        return generator_name_part(operation_str, parameter)
    return ""


def generator_name_part(operation_str: str, value_tuple: tuple) -> str:
    """Return the part of a name that shows the values of a new signal.

    Inputs:
        operation_str: one of operations.GENERATOR_OPERATION_TUPLE.
        value_tuple: its checked values.
    Outputs: the text after the abbreviation of LLFR-01301, for example
        "1s_0_to_5" for a step.
    """
    # LLFR-01301: every number written as in LLFR-00569.
    number_list = [format_name_number(value_f) for value_f in value_tuple]
    if operation_str == operations.STEP_SIGNAL_STR:
        return f"{number_list[0]}s_{number_list[1]}_to_{number_list[2]}"
    if operation_str == operations.RAMP_SIGNAL_STR:
        return (f"{number_list[0]}s_slope{number_list[1]}_from"
                f"{number_list[2]}")
    if operation_str == operations.POLYNOMIAL_SIGNAL_STR:
        return f"a{number_list[0]}_b{number_list[1]}_c{number_list[2]}"
    if operation_str in (operations.SINE_SIGNAL_STR,
                         operations.COSINE_SIGNAL_STR):
        return (f"amp{number_list[0]}_{number_list[1]}Hz_ph"
                f"{number_list[2]}deg_off{number_list[3]}")
    return number_list[0]


def base_synthetic_name(operation_str: str, source_name_list: list,
                        parameter) -> str:
    """Return the name of LLFR-00240, before LLFR-00241 is applied.

    Inputs:
        operation_str: the operation id, e.g. "integral".
        source_name_list: the current names of the signals it is
            computed from (two for "product", the right-clicked signal
            first).
        parameter: the checked parameter of the operation, or None.
    Outputs: ``<abbreviation>_<signal>``,
        ``<abbreviation>_<parameter>_<signal>``, or for a product
        ``<first>_prod_<second>``.
    """
    # LLFR-00240: the abbreviation of the menu (LLFR-00268) and the full
    # current name of each source, so that chains build up from left to
    # right.
    abbreviation_str = operations.find_operation(
        operation_str).abbreviation_str
    source_list = [str(name_str) for name_str in source_name_list]
    if operation_str == operations.PRODUCT_STR:
        # LLFR-00240: <right-clicked signal>_prod_<second signal>.
        return "_".join([source_list[0], abbreviation_str] + source_list[1:])
    parameter_str = parameter_name_part(operation_str, parameter)
    part_list = [abbreviation_str]
    if parameter_str:
        part_list.append(parameter_str)
    # LLFR-01301: a signal made from scratch shows no source, since its
    # only source is the time signal of its file.
    if operations.find_operation(operation_str).generator_b:
        return "_".join(part_list)
    return "_".join(part_list + source_list)


def synthetic_name(operation_str: str, source_name_list: list,
                   parameter, used_name_set: set) -> str:
    """Return the name of a new synthetic signal.

    Inputs:
        operation_str: the operation id, e.g. "integral".
        source_name_list: the current names of the signals it is
            computed from (two for "product", the right-clicked signal
            first).
        parameter: the checked parameter of the operation (the time
            range (start_s, end_s) for "fft"), or None.
        used_name_set: the names of every signal in the signal list
            (data file and synthetic signals).
    Outputs: the name of base_synthetic_name, followed by ``_2``,
        ``_3``... (the smallest number from 2 up) when the name is
        already used.
    """
    # LLFR-00240: abbreviation, parameter and full current source names.
    base_name_str = base_synthetic_name(operation_str, source_name_list,
                                        parameter)
    # LLFR-00241: smallest number from 2 up that makes the name unique.
    return unique_name(base_name_str, used_name_set)


@dataclass
class SyntheticSignal:
    """One synthetic signal (HLFR-00053).

    Inputs:
        name_str: its current name (LLFR-00240, LLFR-00266).
        operation_str: the operation id, e.g. "lowpass".
        source_name_list: the current names of the signals it was
            computed from (two for "product").
        parameter: (cutoff in Hz, order, start) (tuple), window size
            (int),
            constant (float), time range (start_s, end_s) (tuple) or
            None,
            according to the operation (see model.synthetic_operations).
        value_array: its samples: one per time sample of the data file,
            or one per frequency for an FFT signal.
        frequency_array: the frequencies in Hz of an FFT signal's
            samples (its x-axis, HLFR-00058); None for the others,
            whose x-axis is the time signal.
        file_number_i: the number of the data file it belongs to
            (LLFR-00940), or None for a signal whose sources have no
            file prefix.
        plain_name_str: its name with every prefix that the app put
            into it removed (LLFR-00945); "" takes the name without its
            own prefix.
    """

    name_str: str
    operation_str: str
    source_name_list: list
    parameter: object
    value_array: np.ndarray
    frequency_array: object = field(default=None)
    file_number_i: object = field(default=None)
    plain_name_str: str = field(default="")

    @property
    def prefix_str(self) -> str:
        """Return the prefix of the signal's data file.

        Inputs: none.
        Outputs: ``file<N>_`` (LLFR-00908), or "" when it belongs to no
            numbered file.
        """
        # LLFR-00908, LLFR-00940: the prefix of the file it belongs to.
        if self.file_number_i is None:
            return ""
        return file_prefix(self.file_number_i)

    @property
    def editable_name_str(self) -> str:
        """Return the part of the name after the prefix of its file.

        Inputs: none.
        Outputs: the text the rename field shows (LLFR-00959).
        """
        # LLFR-00959: only the part after the prefix can be typed.
        if self.prefix_str and self.name_str.startswith(self.prefix_str):
            return self.name_str[len(self.prefix_str):]
        return self.name_str

    @property
    def saved_name_str(self) -> str:
        """Return the plain name the signal is saved under.

        Inputs: none.
        Outputs: the name without the prefixes the app put into it
            (LLFR-00945).
        """
        # LLFR-00945: a renamed signal keeps the typed text; a signal
        # made without a plain name is saved under its editable name,
        # which leaves out only the prefix of its own data file.
        return self.plain_name_str or self.editable_name_str

    @property
    def is_fft_b(self) -> bool:
        """Tell whether this is an FFT signal.

        Inputs: none.
        Outputs: True when the operation is "fft" (LLFR-00251).
        """
        # LLFR-00251, LLFR-00256: FFT signals have a frequency x-axis.
        return self.operation_str == operations.FFT_STR

    @property
    def operation(self) -> operations.SyntheticOperation:
        """Return the operation that computed this signal.

        Inputs: none.
        Outputs: its SyntheticOperation (menu label, parameter kind).
        """
        # LLFR-00268: the operation's menu entry.
        return operations.OPERATION_DICT[self.operation_str]


def entries_text(entry_list: list) -> str:
    """Return a list of layout file entries as JSON text.

    Inputs:
        entry_list: entries of SyntheticSignalStore.layout_entry.
    Outputs: a JSON list indented by 2 spaces, with each value on its
        own line, that can be pasted into the "synthetic_signals" list
        of a layout file (LLFR-00279).
    """
    # LLFR-00227, LLFR-00279: JSON indented by 2 spaces, UTF-8 text.
    return json.dumps(entry_list, indent=JSON_INDENT_I, ensure_ascii=False)


def entry_parameter(signal: SyntheticSignal):
    """Return the layout file value of a synthetic signal's parameter.

    Inputs:
        signal: the synthetic signal.
    Outputs: a float, an int, a dict {"cutoff": Hz, "order": n,
        "start": start}, a dict {"start": s, "end": s} or None.
    """
    # LLFR-00225 item 10: cutoff and order, window size, constant or
    # time range.
    kind_str = signal.operation.parameter_kind_str
    if kind_str == operations.FILTER_PARAMETER_STR:
        # LLFR-00227: the cutoff in Hz, the order and the start.
        cutoff_hz, order_i, start_str = signal.parameter
        return {CUTOFF_KEY_STR: float(cutoff_hz),
                ORDER_KEY_STR: int(order_i),
                FILTER_START_KEY_STR: str(start_str)}
    if kind_str == operations.TIME_RANGE_PARAMETER_STR or (
            kind_str == operations.STATISTIC_RANGE_PARAMETER_STR
            and signal.parameter is not None):
        # LLFR-00227: times as floats, written with repr precision;
        # LLFR-00225 item 10: the shown range of a statistic.
        start_s, end_s = signal.parameter
        return {START_KEY_STR: float(start_s), END_KEY_STR: float(end_s)}
    if kind_str == operations.GENERATOR_PARAMETER_STR:
        # LLFR-01304: the values of the dialog under English keys.
        return {key_str: float(value_f) for key_str, value_f in zip(
            operations.GENERATOR_VALUE_KEY_DICT[signal.operation_str],
            signal.parameter)}
    if kind_str == operations.WINDOW_PARAMETER_STR:
        return int(signal.parameter)
    if kind_str == operations.CONSTANT_PARAMETER_STR:
        return float(signal.parameter)
    return None


def parameter_from_entry(operation_str: str, parameter_value):
    """Turn the parameter of a layout file entry into a parameter.

    Inputs:
        operation_str: the operation id of the entry.
        parameter_value: the "parameter" value of the entry.
    Outputs: the parameter in the form SyntheticSignalStore.create
        takes; the values themselves are checked there.
    Raises: SyntheticEntryError when an FFT time range is not an object
        with "start" and "end", or a filter parameter is not an object
        with "cutoff", "order" and "start".
    """
    # LLFR-00262: the FFT time range is saved as {"start", "end"}.
    kind_str = operations.find_operation(operation_str).parameter_kind_str
    if kind_str == operations.FILTER_PARAMETER_STR:
        # LLFR-00225 item 10: a filter is saved as {"cutoff", "order",
        # "start"}.
        if (not isinstance(parameter_value, dict)
                or CUTOFF_KEY_STR not in parameter_value
                or ORDER_KEY_STR not in parameter_value
                or FILTER_START_KEY_STR not in parameter_value):
            raise SyntheticEntryError(
                'The parameter of a filter must be an object with a '
                '"cutoff" frequency, in Hz, an "order" and a "start".')
        return (parameter_value[CUTOFF_KEY_STR],
                parameter_value[ORDER_KEY_STR],
                parameter_value[FILTER_START_KEY_STR])
    if kind_str == operations.GENERATOR_PARAMETER_STR:
        # LLFR-01304: an object with the values under their keys.
        key_tuple = operations.GENERATOR_VALUE_KEY_DICT[operation_str]
        if (not isinstance(parameter_value, dict)
                or not all(key_str in parameter_value
                           for key_str in key_tuple)):
            raise SyntheticEntryError(
                "The parameter must be an object with the values "
                + ", ".join(f'"{key_str}"' for key_str in key_tuple)
                + ".")
        return tuple(parameter_value[key_str] for key_str in key_tuple)
    if kind_str == operations.STATISTIC_RANGE_PARAMETER_STR and (
            parameter_value is None):
        # LLFR-01309: null is the whole signal, as in older files.
        return None
    if kind_str not in (operations.TIME_RANGE_PARAMETER_STR,
                        operations.STATISTIC_RANGE_PARAMETER_STR):
        return parameter_value
    if (not isinstance(parameter_value, dict)
            or START_KEY_STR not in parameter_value
            or END_KEY_STR not in parameter_value):
        raise SyntheticEntryError(
            'The time range of an FFT must be an object with "start" '
            'and "end" times, in seconds.')
    return (parameter_value[START_KEY_STR], parameter_value[END_KEY_STR])


class SyntheticSignalStore:
    """The synthetic signals of the open data files, in creation order.

    Inputs: none.
    Outputs: an empty store. The controller keeps one store for every
        open data file; closing a file deletes the synthetic signals
        computed from its signals (LLFR-00926).

    Every method that changes the store keeps these rules: names are
    unique among the data file signals and the synthetic signals; every
    synthetic signal is created after the synthetic signals it is
    computed from; and no synthetic signal is computed from an FFT
    signal (LLFR-00251).
    """

    def __init__(self) -> None:
        """Create an empty store.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00242: synthetic signals, in the order they were created.
        self.signal_list = []
        # LLFR-01294: tells whether a name is the time signal of a data
        # file; the controller sets it (time_signal_name_set).
        self.time_name_function = lambda name_str: True

    def names(self) -> list:
        """Return the names of the synthetic signals.

        Inputs: none.
        Outputs: the names, in creation order (LLFR-00242).
        """
        # LLFR-00242: shown after the data file signals, in this order.
        return [signal.name_str for signal in self.signal_list]

    def get(self, name_str: str) -> SyntheticSignal:
        """Return the synthetic signal with the given name.

        Inputs:
            name_str: the current name of a synthetic signal.
        Outputs: the SyntheticSignal.
        Raises: KeyError when no synthetic signal has that name.
        """
        # LLFR-00242: look up a synthetic signal by its current name.
        for signal in self.signal_list:
            if signal.name_str == name_str:
                return signal
        raise KeyError(name_str)

    def contains(self, name_str: str) -> bool:
        """Tell whether a synthetic signal has the given name.

        Inputs:
            name_str: a signal name.
        Outputs: True when it is the name of a synthetic signal.
        """
        # LLFR-00254: only synthetic signals can be deleted or renamed.
        return name_str in self.names()

    def is_fft(self, name_str: str) -> bool:
        """Tell whether the named signal is an FFT signal.

        Inputs:
            name_str: a signal name (data file or synthetic).
        Outputs: True only for a synthetic FFT signal.
        """
        # LLFR-00251, LLFR-00275: FFT signals can't be a source.
        return self.contains(name_str) and self.get(name_str).is_fft_b

    def clear(self) -> None:
        """Remove every synthetic signal.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00595: the synthetic signals exist only in this store.
        self.signal_list = []

    def file_number_of(self, name_str: str):
        """Return the number of the data file a signal belongs to.

        Inputs:
            name_str: a signal of a data file or a synthetic signal.
        Outputs: the file number (LLFR-00940): the one stored with a
            synthetic signal, or the one of the prefix of a data file
            signal (LLFR-00905); None for a name without a prefix.
        """
        # LLFR-00940: a synthetic signal belongs to the file of the
        # signal it was computed from; LLFR-00905: a data file signal
        # carries the number of its file in its prefix.
        if self.contains(name_str):
            return self.get(name_str).file_number_i
        return prefix_number(name_str)

    def name_without_prefix(self, name_str: str) -> str:
        """Return a signal's name without the prefix of its file.

        Inputs:
            name_str: a signal of a data file or a synthetic signal.
        Outputs: the part after ``file<N>_`` (LLFR-00908).
        """
        # LLFR-00240, LLFR-00908: the names are built from the names
        # without their prefix.
        if self.contains(name_str):
            return self.get(name_str).editable_name_str
        return without_prefix(name_str)

    def plain_name_of(self, name_str: str) -> str:
        """Return the name a signal is saved under, before numbering.

        Inputs:
            name_str: a signal of a data file or a synthetic signal.
        Outputs: its plain name (LLFR-00945): the name in its file for
            a data file signal, the stored plain name for a synthetic
            signal.
        """
        # LLFR-00945: every prefix the app put into the name removed.
        if self.contains(name_str):
            return self.get(name_str).saved_name_str
        return without_prefix(name_str)

    def default_names(self, operation_str: str, source_name_list: list,
                      parameter) -> tuple:
        """Return the name and the plain name of LLFR-00908.

        Inputs:
            operation_str: the operation id.
            source_name_list: the current names of its sources.
            parameter: the checked parameter, or None.
        Outputs: a tuple (file number or None, name before LLFR-00241,
            plain name before LLFR-00241).
        """
        # LLFR-00940: the file of the (right-clicked) first source.
        file_number_i = self.file_number_of(source_name_list[0])
        shown_list = []
        for index_i, source_str in enumerate(source_name_list):
            source_number_i = self.file_number_of(source_str)
            if index_i > 0 and source_number_i is not None:
                # LLFR-00958: the second signal of a product keeps the
                # prefix of its own file, of this file or of another.
                shown_list.append(file_prefix(source_number_i)
                                  + self.name_without_prefix(source_str))
            else:
                # LLFR-00240, LLFR-00908: the name without its prefix.
                shown_list.append(self.name_without_prefix(source_str))
        prefix_str = "" if file_number_i is None else file_prefix(
            file_number_i)
        name_str = prefix_str + base_synthetic_name(
            operation_str, shown_list, parameter)
        # LLFR-00945: the plain name holds no prefix at all.
        plain_str = base_synthetic_name(
            operation_str, [self.plain_name_of(source_str)
                            for source_str in source_name_list], parameter)
        return file_number_i, name_str, plain_str

    def check_sources(self, operation_str: str, source_name_list: list,
                      data_name_set: set) -> None:
        """Check the signals a new synthetic signal is computed from.

        Inputs:
            operation_str: the operation id.
            source_name_list: the names of the source signals.
            data_name_set: the names of the data file signals.
        Outputs: none.
        Raises: SyntheticEntryError when the number of sources is wrong;
            SyntheticSourceError when a source is missing or is an FFT
            signal.
        """
        # LLFR-00240, LLFR-00275: one source, or two for "product".
        expected_count_i = operations.find_operation(
            operation_str).source_count_i
        if (not isinstance(source_name_list, (list, tuple))
                or len(source_name_list) != expected_count_i):
            raise SyntheticEntryError(
                f'The operation "{operation_str}" is computed from '
                f'{expected_count_i} signal name(s).')
        # LLFR-00262: a hand-edited entry may hold other values.
        if not all(isinstance(name_str, str)
                   for name_str in source_name_list):
            raise SyntheticEntryError(
                'The names of the signals it is computed from must be '
                'texts.')
        # LLFR-01294, LLFR-01304: a signal made from scratch is computed
        # from the time signal of its data file alone.
        if operations.find_operation(operation_str).generator_b and (
                not self.time_name_function(source_name_list[0])):
            raise SyntheticSourceError(
                f'The signal "{source_name_list[0]}" is not the time '
                f'signal of a data file.')
        for name_str in source_name_list:
            # LLFR-00262: a missing source stops the creation.
            if name_str not in data_name_set and not self.contains(
                    name_str):
                raise SyntheticSourceError(
                    f'The signal "{name_str}" it is computed from is '
                    f'missing.')
            # LLFR-00251, LLFR-00275: no operation on FFT signals.
            if self.is_fft(name_str):
                raise SyntheticSourceError(
                    f'The signal "{name_str}" is an FFT signal, and no '
                    f'operation can be done on an FFT signal.')

    def compute_signal(self, operation_str: str, source_name_list: list,
                       parameter, signal_lookup, time_array,
                       data_name_set: set, name_str: str
                       ) -> SyntheticSignal:
        """Check, compute and append a synthetic signal.

        Inputs: as create(), plus name_str: the name to give it, or an
            empty string to name it by LLFR-00240 and LLFR-00241.
        Outputs: the new SyntheticSignal, appended to the store.
        Raises: as create().
        """
        # LLFR-00251, LLFR-00262: the sources must exist and not be FFTs.
        self.check_sources(operation_str, source_name_list, data_name_set)
        source_array_list = [np.asarray(signal_lookup(source_name_str),
                                        dtype=np.float64)
                             for source_name_str in source_name_list]
        # LLFR-00941: a function gives the time signal of the file of the
        # first source (the right-clicked signal of a product).
        if callable(time_array):
            time_function = time_array
            time_array = time_function(source_name_list[0])
            # LLFR-00496, LLFR-00275, LLFR-00977, LLFR-00978: the signals
            # of a product must have identical time signals.
            for source_name_str in source_name_list[1:]:
                if not identical_time_signals_b(
                        time_function(source_name_str), time_array):
                    raise SyntheticSourceError(
                        f'The signals "{source_name_list[0]}" and '
                        f'"{source_name_str}" belong to data files whose '
                        f'time signals are not the same.')
        # LLFR-00245, LLFR-00269, LLFR-00272: the parameter is allowed.
        parameter = operations.check_parameter(
            operation_str, parameter, time_array,
            source_array_list[0].size)
        # LLFR-00243 to LLFR-00276: compute the samples.
        value_array, frequency_array = operations.compute(
            operation_str, time_array, source_array_list, parameter)
        # LLFR-00908, LLFR-00940, LLFR-00958: the prefix of the file of
        # the first source, then the names without their prefix, except
        # the second signal of a product, which keeps its own.
        file_number_i, default_name_str, plain_str = self.default_names(
            operation_str, source_name_list, parameter)
        if not name_str:
            # LLFR-00240, LLFR-00241: unique among all signal names.
            name_str = unique_name(default_name_str,
                                   set(data_name_set) | set(self.names()))
        # LLFR-00945: the number of LLFR-00241 stays in the plain name;
        # a name that is not the app's own keeps the text after its
        # prefix.
        suffix_match = re.fullmatch(re.escape(default_name_str)
                                    + r"(_[0-9]+)?", name_str)
        if suffix_match is not None:
            plain_str += suffix_match.group(1) or ""
        else:
            plain_str = ""
        signal = SyntheticSignal(name_str, operation_str,
                                 list(source_name_list), parameter,
                                 value_array, frequency_array,
                                 file_number_i, plain_str)
        self.signal_list.append(signal)
        return signal

    def create(self, operation_str: str, source_name_list: list,
               parameter, signal_lookup, time_array,
               data_name_set: set) -> SyntheticSignal:
        """Create a synthetic signal and add it after the others.

        Inputs:
            operation_str: the operation id, e.g. "lowpass".
            source_name_list: the current names of the signals it is
                computed from: the right-clicked signal, and for
                "product" the second signal after it (LLFR-00275).
            parameter: the parameter of the operation's kind: (cutoff
                in Hz, order, start) for the filters, window size, constant,
                (start_s, end_s) for "fft" (the time range shown in the
                time plots, LLFR-00248), or None.
            signal_lookup: function name -> samples (array-like) of any
                signal in the signal list, data file or synthetic.
            time_array: the time signal of the data file, in seconds,
                or a function that takes a signal name and returns the
                time signal of its data file (LLFR-00941).
            data_name_set: the names of the data file signals.
        Outputs: the new SyntheticSignal, named by LLFR-00240 and
            LLFR-00241.
        Raises: SyntheticSourceError (missing or FFT source),
            SyntheticParameterError (parameter not allowed),
            SyntheticOperationError and its subclasses
            UnevenTimeStepError and TooFewSamplesError (operation
            impossible), SyntheticEntryError (wrong number of sources).
            The store is unchanged when an error is raised.
        """
        # LLFR-00239, LLFR-00264: create from any non-FFT signal.
        return self.compute_signal(operation_str, source_name_list,
                                   parameter, signal_lookup, time_array,
                                   data_name_set, "")

    def dependents(self, name_str: str) -> list:
        """Return the synthetic signals computed from a signal.

        Inputs:
            name_str: the name of a signal (data file or synthetic).
        Outputs: the names of the synthetic signals computed from it,
            directly or through other synthetic signals, in creation
            order. The signal itself is not in the list.
        """
        # LLFR-00255: direct and indirect dependents. Sources are always
        # created before their dependents, so one pass is enough.
        reached_name_set = {name_str}
        dependent_name_list = []
        for signal in self.signal_list:
            if signal.name_str == name_str:
                continue
            if reached_name_set.intersection(signal.source_name_list):
                reached_name_set.add(signal.name_str)
                dependent_name_list.append(signal.name_str)
        return dependent_name_list

    def delete(self, name_str: str) -> list:
        """Delete a synthetic signal and every signal computed from it.

        Inputs:
            name_str: the name of a synthetic signal.
        Outputs: the names of the removed signals, in creation order
            (the signal first, then its dependents).
        Raises: KeyError when no synthetic signal has that name.
        """
        # LLFR-00255: remove the signal and its dependents.
        self.get(name_str)
        removed_name_set = {name_str, *self.dependents(name_str)}
        removed_name_list = [signal.name_str for signal in self.signal_list
                             if signal.name_str in removed_name_set]
        self.signal_list = [signal for signal in self.signal_list
                            if signal.name_str not in removed_name_set]
        return removed_name_list

    def rename(self, old_name_str: str, new_name_str: str,
               data_name_set: set) -> str:
        """Rename a synthetic signal.

        Inputs:
            old_name_str: the current name of a synthetic signal.
            new_name_str: the name the user typed: the part after the
                prefix of its data file (LLFR-00959).
            data_name_set: the names of the data file signals.
        Outputs: the stored new name: the prefix of its data file and
            the typed text without leading and trailing spaces.
            Entering the signal's own name changes nothing.
        Raises: KeyError when no synthetic signal has old_name_str;
            EmptySyntheticNameError for an empty name (the app shows no
            message); SyntheticNameInUseError for the name of another
            signal (the app shows an information box). The store is
            unchanged when an error is raised.
        """
        # LLFR-00267: the name is compared without outer spaces.
        signal = self.get(old_name_str)
        typed_name_str = new_name_str.strip()
        # LLFR-00975: the empty-name check is on the typed part.
        if not typed_name_str:
            raise EmptySyntheticNameError("The name is empty.")
        # LLFR-00959, LLFR-00976: the prefix of its file stays in front
        # of the typed part, and the whole name is checked.
        trimmed_name_str = signal.prefix_str + typed_name_str
        if trimmed_name_str == old_name_str:
            return trimmed_name_str
        # LLFR-00267: no two signals of the signal list share a name.
        if trimmed_name_str in data_name_set or self.contains(
                trimmed_name_str):
            raise SyntheticNameInUseError(
                f'A signal named "{trimmed_name_str}" already exists.')
        signal.name_str = trimmed_name_str
        # LLFR-00945: the text the user typed is the plain name.
        signal.plain_name_str = typed_name_str
        # LLFR-00266: dependents keep their own names, but their stored
        # sources follow the new name (LLFR-00225 item 10).
        for dependent in self.signal_list:
            dependent.source_name_list = [
                trimmed_name_str if source_str == old_name_str
                else source_str
                for source_str in dependent.source_name_list]
        return trimmed_name_str

    def layout_entry(self, signal: SyntheticSignal) -> dict:
        """Return the layout file entry of a synthetic signal.

        Inputs:
            signal: a synthetic signal of this store.
        Outputs: a dict with the keys "name", "operation", "signals"
            and "parameter" (see the module docstring), ready for
            json.dumps.
        """
        # LLFR-00225 item 10, LLFR-00227: current names, English keys.
        return {
            NAME_KEY_STR: signal.name_str,
            OPERATION_KEY_STR: signal.operation_str,
            SIGNALS_KEY_STR: list(signal.source_name_list),
            PARAMETER_KEY_STR: entry_parameter(signal),
        }

    def layout_entries(self) -> list:
        """Return the layout file entries of every synthetic signal.

        Inputs: none.
        Outputs: a list of entries (layout_entry), in creation order,
            for the "synthetic_signals" key of the layout file, without
            the FFT signals (LLFR-00283).
        """
        # LLFR-00225 item 10: every synthetic signal, in creation order;
        # LLFR-00283: except the FFT signals. No other signal is
        # computed from an FFT signal (LLFR-00251), so none is lost.
        return [self.layout_entry(signal) for signal in self.signal_list
                if not signal.is_fft_b]

    def equation_entries(self, name_str: str) -> list:
        """Return the equation of a synthetic signal.

        Inputs:
            name_str: the name of a synthetic signal.
        Outputs: the layout file entries of the signal and of every
            synthetic signal it is computed from, directly or through
            other synthetic signals, in creation order.
        Raises: KeyError when no synthetic signal has that name.
        """
        # LLFR-00279: the signal and all its synthetic ancestors. Walk
        # backwards, since sources are created before their dependents.
        self.get(name_str)
        needed_name_set = {name_str}
        for signal in reversed(self.signal_list):
            if signal.name_str in needed_name_set:
                needed_name_set.update(signal.source_name_list)
        return [self.layout_entry(signal) for signal in self.signal_list
                if signal.name_str in needed_name_set]

    def equation_text(self, name_str: str) -> str:
        """Return the equation of a synthetic signal as JSON text.

        Inputs:
            name_str: the name of a synthetic signal.
        Outputs: the JSON list of equation_entries, for the clipboard.
        Raises: KeyError when no synthetic signal has that name.
        """
        # LLFR-00279: a JSON list that can be pasted in a layout file.
        return entries_text(self.equation_entries(name_str))

    def create_from_entry(self, entry_dict, signal_lookup, time_array,
                          data_name_set: set) -> SyntheticSignal:
        """Create a synthetic signal from a layout file entry, strictly.

        A saved name that is in use is refused here; a layout load uses
        LayoutSignalLoader, which renames it instead (LLFR-00282).

        Inputs:
            entry_dict: one entry of the "synthetic_signals" list (see
                the module docstring), as read by json.load.
            signal_lookup: function name -> samples of any signal in
                the signal list, data file or synthetic.
            time_array: the time signal of the data file, in seconds,
                or a function that takes a signal name and returns the
                time signal of its data file (LLFR-00941).
            data_name_set: the names of the data file signals.
        Outputs: the new SyntheticSignal, with the saved name, appended
            to the store. An FFT entry is never created (LLFR-00283).
        Raises: a SyntheticSignalError subclass whose ``str()`` is the
            reason for the load report (LLFR-00237): SyntheticEntryError
            (malformed entry), SyntheticSourceError (missing or FFT
            source), SyntheticParameterError (parameter not allowed),
            SyntheticOperationError and its subclasses (operation
            impossible), SyntheticNameInUseError (saved name of a data
            file signal or of an earlier synthetic signal). The store is
            unchanged when an error is raised.
        """
        # LLFR-00262: rebuild with the saved name, operation, signals
        # and parameter.
        name_str, operation_str, source_name_list, parameter = (
            self.read_entry(entry_dict))
        # LLFR-00267: names are kept without outer spaces, as rename().
        name_str = name_str.strip()
        # LLFR-00267: no two signals share a name. A layout load uses
        # LayoutSignalLoader instead, which gives such a signal a unique
        # name (LLFR-00282).
        if name_str in data_name_set:
            raise SyntheticNameInUseError(
                f'"{name_str}" is the name of a signal of the data file.')
        if self.contains(name_str):
            raise SyntheticNameInUseError(
                f'"{name_str}" is already the name of an earlier '
                f'synthetic signal.')
        return self.compute_signal(operation_str, source_name_list,
                                   parameter, signal_lookup, time_array,
                                   data_name_set, name_str)

    def read_entry(self, entry_dict) -> tuple:
        """Read and type-check the values of a layout file entry.

        Inputs:
            entry_dict: one entry of the "synthetic_signals" list.
        Outputs: a tuple (name, operation id, source names, parameter in
            the form create() takes).
        Raises: SyntheticEntryError when a key is missing or has the
            wrong type, or for an FFT signal (LLFR-00283);
            SyntheticOperationError for an unknown operation.
        """
        # LLFR-00262: hand-edited files may hold anything.
        if not isinstance(entry_dict, dict):
            raise SyntheticEntryError(
                "A synthetic signal entry must be a JSON object.")
        for key_str in (NAME_KEY_STR, OPERATION_KEY_STR, SIGNALS_KEY_STR):
            if key_str not in entry_dict:
                raise SyntheticEntryError(
                    f'The synthetic signal entry has no "{key_str}".')
        name_str = entry_dict[NAME_KEY_STR]
        if not isinstance(name_str, str) or not name_str.strip():
            raise SyntheticEntryError(
                "The name of a synthetic signal must be a text that is "
                "not empty.")
        operation_str = entry_dict[OPERATION_KEY_STR]
        operations.find_operation(operation_str)
        if operation_str == operations.FFT_STR:
            # LLFR-00283: FFT signals are not loaded from layout files.
            raise SyntheticEntryError(FFT_NOT_LOADED_STR)
        source_name_list = entry_dict[SIGNALS_KEY_STR]
        if not isinstance(source_name_list, list):
            raise SyntheticEntryError(
                'The "signals" of a synthetic signal must be a list of '
                'signal names.')
        parameter = parameter_from_entry(
            operation_str, entry_dict.get(PARAMETER_KEY_STR))
        return name_str, operation_str, list(source_name_list), parameter


def entry_label(entry_dict, entry_number_i: int) -> str:
    """Return how the load report names a synthetic signal entry.

    Inputs:
        entry_dict: one entry of the "synthetic_signals" list.
        entry_number_i: its position in the list, from 1.
    Outputs: its saved name, or "Entry <n> of the synthetic signals"
        when it has no usable name.
    """
    # LLFR-00237: each synthetic signal not created is named.
    name_value = (entry_dict.get(NAME_KEY_STR)
                  if isinstance(entry_dict, dict) else None)
    if isinstance(name_value, str) and name_value.strip():
        return name_value.strip()
    return f"Entry {entry_number_i} of the synthetic signals"


def unique_name(base_name_str: str, used_name_set: set) -> str:
    """Return a name made unique as in LLFR-00241.

    Inputs:
        base_name_str: the wanted name.
        used_name_set: the names already in the signal list.
    Outputs: base_name_str when it is free, else base_name_str followed
        by ``_2``, ``_3``... (the smallest free number from 2 up).
    """
    # LLFR-00241, LLFR-00282: the smallest number from 2 up.
    name_str = base_name_str
    number_i = FIRST_SUFFIX_NUMBER_I
    while name_str in used_name_set:
        name_str = f"{base_name_str}_{number_i}"
        number_i += 1
    return name_str


def own_prefix_name(name_str: str, file_number_i) -> str:
    """Return a saved name with the prefix of its own data file.

    Inputs:
        name_str: the saved name of a synthetic signal of a layout file.
        file_number_i: the number of its data file (LLFR-00940), or
            None.
    Outputs: the name itself when it starts with ``file<N>_`` of its
        file or when file_number_i is None; else the name with that
        prefix in place of the prefix of another file, or in front of
        the name when it has no prefix (LLFR-00970).
    """
    # LLFR-00970: for example `my_int` of file 2 becomes `file2_my_int`
    # and `file1_x` of file 2 becomes `file2_x`.
    if file_number_i is None:
        return name_str
    prefix_str = file_prefix(file_number_i)
    if name_str.startswith(prefix_str):
        return name_str
    return prefix_str + without_prefix(name_str)


def is_numbered_name(name_str: str, base_name_str: str) -> bool:
    """Tell whether a name is a name, or that name and a number.

    Inputs:
        name_str: a name of the signal list.
        base_name_str: the corrected name of a synthetic signal of a
            layout file (LLFR-01198).
    Outputs: True when name_str is base_name_str, or base_name_str, an
        underscore and a whole number from 2 up written without leading
        zeros, as LLFR-00241 makes names.
    """
    # LLFR-00282, LLFR-00241: the names an earlier load may have given
    # to a signal of the same saved name.
    if name_str == base_name_str:
        return True
    prefix_str = base_name_str + "_"
    if not name_str.startswith(prefix_str):
        return False
    number_str = name_str[len(prefix_str):]
    return (number_str.isdigit() and number_str.isascii()
            and not number_str.startswith("0")
            and int(number_str) >= FIRST_SUFFIX_NUMBER_I)


def recipe(store: SyntheticSignalStore, signal: SyntheticSignal) -> dict:
    """Return the recipe of a synthetic signal: its entry without name.

    Inputs:
        store: the store that holds the signal.
        signal: the synthetic signal.
    Outputs: its layout file entry without "name": operation, current
        source names and parameter (LLFR-00282).
    """
    # LLFR-00282: two signals of the same name are the same signal when
    # their operation, sources and parameter are the same.
    entry_dict = store.layout_entry(signal)
    del entry_dict[NAME_KEY_STR]
    return entry_dict


class LayoutSignalLoader:
    """Creates the synthetic signals of a layout file (LLFR-00262).

    Inputs:
        store: the store of the open data file; its current signals are
            kept (LLFR-00229).
        signal_lookup: function name -> samples of any signal of the
            signal list, data file or synthetic.
        time_array: the time signal of the data file, in seconds, or a
            function that takes a signal name and returns the time
            signal of its data file (LLFR-00941).
        data_name_set: the names of the data file signals.
    Attributes:
        name_dict: file name of each synthetic entry -> the name of the
            signal the layout uses for it (the saved name, or the name
            made unique by LLFR-00282), or None when it was not created.
        not_created_list: (label_str, reason_str) of each entry that was
            not created (LLFR-00237).
        renamed_list: (saved name, new name) of each entry created under
            a new name because its name was in use (LLFR-00282).
    """

    def __init__(self, store: SyntheticSignalStore, signal_lookup,
                 time_array, data_name_set: set) -> None:
        """Store the parts.

        Inputs: see the class docstring.
        Outputs: none.
        """
        # LLFR-00262: the signals of the data file and the store.
        self.store = store
        self.signal_lookup = signal_lookup
        self.time_array = time_array
        self.data_name_set = set(data_name_set)
        self.name_dict = {}
        self.not_created_list = []
        self.renamed_list = []

    def source_name(self, file_name_str):
        """Return the signal a source name of the file stands for.

        Inputs:
            file_name_str: a source name as saved in the file.
        Outputs: the name of the signal of the signal list it uses (it
            follows the renames of LLFR-00282), or the saved value when
            the file did not create it.
        """
        # LLFR-00282: a renamed signal is used under its new name.
        if isinstance(file_name_str, str) and file_name_str in (
                self.name_dict):
            return self.name_dict[file_name_str] or file_name_str
        return file_name_str

    def source_reason(self, source_value, later_name_set: set) -> str:
        """Explain a source of an entry that is not in the signal list.

        Inputs:
            source_value: the "signals" value of the entry.
            later_name_set: the names of the entries after this one.
        Outputs: the reason for the load report, or "" when every source
            is listed, or is missing for a reason that the store gives
            itself.
        """
        # LLFR-00262: a source must exist when the signal is created; a
        # hand-edited list may name a signal that was not created, or one
        # that comes later in the list (a forward reference or a cycle).
        if not isinstance(source_value, list):
            return ""
        for source_name_str in source_value:
            if not isinstance(source_name_str, str):
                continue
            if (source_name_str in self.name_dict
                    and self.name_dict[source_name_str] is None):
                return (f'The signal "{source_name_str}" it is computed '
                        f'from was not created.')
            if (source_name_str in self.name_dict
                    or source_name_str in self.data_name_set):
                continue
            # LLFR-00262: the file means its own later signal, even when
            # a current synthetic signal has that name.
            if source_name_str in later_name_set:
                return (f'The signal "{source_name_str}" it is computed '
                        f'from comes later in the list of synthetic '
                        f'signals; a synthetic signal must come after the '
                        f'signals it is computed from.')
        return ""

    def create_entry(self, entry_dict, later_name_set: set) -> str:
        """Create, or find, the synthetic signal of one entry.

        Inputs:
            entry_dict: one entry of the "synthetic_signals" list.
            later_name_set: the names of the entries after this one.
        Outputs: the name of the signal the layout uses for the entry.
        Raises: SyntheticSignalError (with the reason for the report)
            when it cannot be created.
        """
        # LLFR-00262, LLFR-00283: type-checked, FFT entries refused.
        name_str, operation_str, source_name_list, parameter = (
            self.store.read_entry(entry_dict))
        name_str = name_str.strip()
        reason_str = self.source_reason(source_name_list, later_name_set)
        if reason_str:
            raise SyntheticSourceError(reason_str)
        # LLFR-00282: the sources follow the renames of this load.
        source_name_list = [self.source_name(source_value)
                            for source_value in source_name_list]
        saved_name_str = name_str
        # LLFR-00970: a saved name that does not start with the prefix
        # of its own data file gets that prefix, in place of the prefix
        # of another file or in front of the name.
        self.store.check_sources(operation_str, source_name_list,
                                 self.data_name_set)
        name_str = own_prefix_name(
            name_str, self.store.file_number_of(source_name_list[0]))
        used_name_set = self.data_name_set | set(self.store.names())
        # LLFR-00282: a free saved name is kept; a name in use is made
        # unique as in LLFR-00241.
        signal = self.store.compute_signal(
            operation_str, source_name_list, parameter, self.signal_lookup,
            self.time_array, self.data_name_set,
            unique_name(name_str, used_name_set))
        signal_recipe_dict = recipe(self.store, signal)
        # LLFR-01198: name_str is now the corrected name.
        # LLFR-01199: the candidates in the order of the signal list.
        for candidate in list(self.store.signal_list):
            if (candidate is not signal
                    and is_numbered_name(candidate.name_str, name_str)
                    and recipe(self.store, candidate)
                    == signal_recipe_dict):
                # LLFR-00282: the same signal already exists under the
                # corrected name, or under that name and a number: it is
                # used, and nothing is created; LLFR-01199: the first
                # one in the order of the signal list.
                self.store.signal_list.remove(signal)
                return candidate.name_str
        if signal.name_str != saved_name_str:
            # LLFR-00499, LLFR-00970, LLFR-00501: the rename is reported,
            # with the saved and the new name.
            self.renamed_list.append((saved_name_str, signal.name_str))
        return signal.name_str

    def load(self, entry_list) -> None:
        """Create the synthetic signals of the file, in its order.

        Inputs:
            entry_list: the "synthetic_signals" list of the layout file,
                as read by json.load; any value is accepted.
        Outputs: none; fills name_dict and not_created_list. Never
            raises: an entry that cannot be created is skipped.
        """
        # LLFR-00262: in the file's order.
        if not isinstance(entry_list, list):
            entry_list = []
        label_list = [entry_label(entry_dict, index_i + 1)
                      for index_i, entry_dict in enumerate(entry_list)]
        for index_i, entry_dict in enumerate(entry_list):
            label_str = label_list[index_i]
            try:
                used_name_str = self.create_entry(
                    entry_dict, set(label_list[index_i + 1:]))
            except SyntheticSignalError as error:
                # LLFR-00262, LLFR-00237: not created, with the reason.
                reason_str = str(error)
            except Exception as error:
                # PCR-00025: an unexpected failure only skips this entry.
                reason_str = (f"It could not be created because of an "
                              f"unexpected error: {error}")
            else:
                self.name_dict[label_str] = used_name_str
                continue
            self.not_created_list.append((label_str, reason_str))
            if label_str != entry_label(None, index_i + 1):
                # LLFR-00262: its curves and dependents are missing.
                self.name_dict[label_str] = None

    def drawn_name_dict(self) -> dict:
        """Return what the layout builder draws for each signal name.

        Inputs: none.
        Outputs: a dict signal name -> (name of the signal drawn, its
            samples), or None for a synthetic signal of the file that
            was not created. It holds every synthetic signal of the
            store that is not an FFT signal under its own name, then the
            names of the file's entries, which win (LLFR-00282).
        """
        # LLFR-00230: the file's curves may name any synthetic signal
        # drawn against time; LLFR-00283: FFT signals are not.
        name_dict = {signal.name_str: (signal.name_str, signal.value_array)
                     for signal in self.store.signal_list
                     if not signal.is_fft_b}
        for file_name_str, used_name_str in self.name_dict.items():
            # LLFR-00282: the file's name stands for the signal used;
            # LLFR-00262: a signal not created is missing.
            name_dict[file_name_str] = (
                None if used_name_str is None
                else name_dict.get(used_name_str))
        return name_dict


def create_layout_signals(store: SyntheticSignalStore, entry_list,
                          signal_lookup, time_array,
                          data_name_set: set) -> list:
    """Create the synthetic signals of a layout file, in its order.

    Inputs:
        store: the store to add the signals to; its signals are kept.
        entry_list: the "synthetic_signals" list of the layout file.
        signal_lookup: function name -> samples of any signal.
        time_array: the time signal of the data file, in seconds, or a
            function that takes a signal name and returns the time
            signal of its data file (LLFR-00941).
        data_name_set: the names of the data file signals.
    Outputs: a list of (label_str, reason_str) for each entry that was
        not created (LLFR-00237), FFT entries included (LLFR-00283).
    """
    # LLFR-00262, LLFR-00282: see LayoutSignalLoader.
    loader = LayoutSignalLoader(store, signal_lookup, time_array,
                                data_name_set)
    loader.load(entry_list)
    return loader.not_created_list


def ordered_signal_names(data_files, synthetic_name_list: list,
                         file_number_dict: dict) -> list:
    """Return every name of the signal list, in the list's order.

    Inputs:
        data_files: the DataFileSet of the open data files (or one
            SignalFile, or None).
        synthetic_name_list: the synthetic signals, in creation order.
        file_number_dict: synthetic signal name -> number of its data
            file (LLFR-00940); a missing name or None puts the signal
            after every file.
    Outputs: the files in the order of their numbers, each with its
        time signal first (LLFR-01009), then its other signals in the
        file's order, followed by its synthetic signals in creation
        order (LLFR-00938, LLFR-00939, LLFR-00242).
    """
    # LLFR-00938, LLFR-00939, LLFR-00242: file after file, each file's
    # synthetic signals right after its own signals.
    if data_files is None:
        return list(synthetic_name_list)
    file_list = list(getattr(data_files, "file_list", []))
    if not file_list:
        return list(data_files.signal_name_list) + list(synthetic_name_list)
    name_list = []
    placed_name_set = set()
    for data_file in file_list:
        # LLFR-01009: the time signal is the first signal of its file.
        name_list.extend(data_file.listed_signal_name_list)
        for name_str in synthetic_name_list:
            if file_number_dict.get(name_str) == data_file.number_i:
                name_list.append(name_str)
                placed_name_set.add(name_str)
    # LLFR-00242: a synthetic signal of no open file comes last.
    name_list.extend(name_str for name_str in synthetic_name_list
                     if name_str not in placed_name_set)
    return name_list
