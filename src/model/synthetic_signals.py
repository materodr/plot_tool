"""Synthetic signals of the opened data file (HLFR-00053), without Qt.

A synthetic signal is computed from one or two signals of the signal
list (data file signals or other synthetic signals) by one of the
operations of model.synthetic_operations. Synthetic signals live only
in memory (HLFR-00055, LLFR-00253): one SyntheticSignalStore per opened
data file holds them in creation order.

Public API:

- ``synthetic_name(operation_str, source_name_list, time_range_tuple,
  used_name_set)``: the name of a new synthetic signal (LLFR-00240,
  LLFR-00241).
- ``SyntheticSignal``: one synthetic signal.
- ``SyntheticSignalStore``: create, look up, rename and delete
  synthetic signals, and turn them into layout file entries and back.
- ``entries_text(entry_list)``: the JSON text of a list of entries, as
  "Copy equation" puts it on the clipboard (LLFR-00279).
- ``create_layout_signals(store, entry_list, signal_lookup, time_array,
  data_name_set)``: create the synthetic signals of a layout file and
  say which were not created and why (LLFR-00262, LLFR-00237).
- ``same_signal(old_signal, store, new_signal)``: whether a synthetic
  signal created by a layout load equals the one it replaced.

Layout file entries (LLFR-00225 item 10, LLFR-00227)
----------------------------------------------------
The layout file holds the synthetic signals as a JSON list, under the
key ``"synthetic_signals"``, in creation order. Each entry is a JSON
object with these keys:

- ``"name"``: the current name of the synthetic signal (string);
- ``"operation"``: the operation id (string), one of ``integral``,
  ``derivative``, ``lowpass``, ``highpass``, ``movingaverage``, ``max``,
  ``min``, ``greater``, ``less``, ``greaterorequal``, ``lessorequal``,
  ``add``, ``subtract``, ``multiply``, ``divide``, ``product``, ``fft``;
- ``"signals"``: the current names of the signals it is computed from
  (list of strings; two names for ``product``, the right-clicked signal
  first, one name otherwise);
- ``"parameter"``: for ``lowpass`` and ``highpass``, an object
  ``{"cutoff": <Hz>, "order": <whole number>, "start": "first_value"
  | "zero"}`` with the cutoff frequency in Hz, the filter order and how
  the filter starts (LLFR-00245, LLFR-00246); the window size
  in samples (whole number) for ``movingaverage``; the constant
  (number) for the Comparison and Arithmetic operations with a
  constant; an object
  ``{"start": <s>, "end": <s>}`` with the time range in seconds for
  ``fft``; ``null`` for the others.

Example::

    [
      {
        "name": "lowpass_Speed",
        "operation": "lowpass",
        "signals": [
          "Speed"
        ],
        "parameter": {
          "cutoff": 2.5,
          "order": 2,
          "start": "first_value"
        }
      },
      {
        "name": "fft_lowpass_Speed_1.5s_to_3s",
        "operation": "fft",
        "signals": [
          "lowpass_Speed"
        ],
        "parameter": {
          "start": 1.5,
          "end": 3.0
        }
      }
    ]

Numbers are written by Python's json module, which writes floats with
repr precision, so they are read back as the same value (LLFR-00227).
"""

import json
import math
from dataclasses import dataclass, field

import numpy as np

from model import synthetic_operations as operations
from model.errors import (
    EmptySyntheticNameError, SyntheticEntryError, SyntheticNameInUseError,
    SyntheticSignalError, SyntheticSourceError)
from model.number_format import format_time_value

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
# LLFR-00241: first number added to a name that is already used.
FIRST_SUFFIX_NUMBER_I = 2


def synthetic_name(operation_str: str, source_name_list: list,
                   time_range_tuple, used_name_set: set) -> str:
    """Return the name of a new synthetic signal.

    Inputs:
        operation_str: the operation id, e.g. "integral".
        source_name_list: the current names of the signals it is
            computed from (two for "product", the right-clicked signal
            first).
        time_range_tuple: (start_s, end_s) for "fft", else None.
        used_name_set: the names of every signal in the signal list
            (data file and synthetic signals).
    Outputs: ``<operation>_<source>`` (``product_<first>_<second>``,
        ``fft_<source>_<start>s_to_<end>s``), followed by ``_2``,
        ``_3``... (the smallest number from 2 up) when the name is
        already used.
    """
    # LLFR-00240: operation name, underscore, full current source names.
    base_name_str = "_".join([operation_str] + list(source_name_list))
    if operation_str == operations.FFT_STR:
        # LLFR-00240: FFT names end with the time range, in the number
        # format of the data tip's x value (LLFR-00043).
        start_s, end_s = time_range_tuple
        base_name_str += (f"_{format_time_value(start_s)}s_to_"
                          f"{format_time_value(end_s)}s")
    # LLFR-00241: smallest number from 2 up that makes the name unique.
    name_str = base_name_str
    number_i = FIRST_SUFFIX_NUMBER_I
    while name_str in used_name_set:
        name_str = f"{base_name_str}_{number_i}"
        number_i += 1
    return name_str


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
    """

    name_str: str
    operation_str: str
    source_name_list: list
    parameter: object
    value_array: np.ndarray
    frequency_array: object = field(default=None)

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
    if kind_str == operations.TIME_RANGE_PARAMETER_STR:
        # LLFR-00227: times as floats, written with repr precision.
        start_s, end_s = signal.parameter
        return {START_KEY_STR: float(start_s), END_KEY_STR: float(end_s)}
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
    if kind_str != operations.TIME_RANGE_PARAMETER_STR:
        return parameter_value
    if (not isinstance(parameter_value, dict)
            or START_KEY_STR not in parameter_value
            or END_KEY_STR not in parameter_value):
        raise SyntheticEntryError(
            'The time range of an FFT must be an object with "start" '
            'and "end" times, in seconds.')
    return (parameter_value[START_KEY_STR], parameter_value[END_KEY_STR])


class SyntheticSignalStore:
    """The synthetic signals of one opened data file, in creation order.

    Inputs: none.
    Outputs: an empty store. The controller creates one store per opened
        data file, or calls clear() when the data file is replaced
        (LLFR-00252).

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
        # LLFR-00252: a new data file starts with no synthetic signal.
        self.signal_list = []

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
        # LLFR-00245, LLFR-00269, LLFR-00272: the parameter is allowed.
        parameter = operations.check_parameter(
            operation_str, parameter, time_array,
            source_array_list[0].size)
        # LLFR-00243 to LLFR-00276: compute the samples.
        value_array, frequency_array = operations.compute(
            operation_str, time_array, source_array_list, parameter)
        if not name_str:
            # LLFR-00240, LLFR-00241: unique among all signal names.
            name_str = synthetic_name(
                operation_str, source_name_list, parameter,
                set(data_name_set) | set(self.names()))
        signal = SyntheticSignal(name_str, operation_str,
                                 list(source_name_list), parameter,
                                 value_array, frequency_array)
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
            time_array: the time signal of the data file, in seconds.
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
            new_name_str: the name the user typed.
            data_name_set: the names of the data file signals.
        Outputs: the stored new name, without leading and trailing
            spaces. Entering the signal's own name changes nothing.
        Raises: KeyError when no synthetic signal has old_name_str;
            EmptySyntheticNameError for an empty name (the app shows no
            message); SyntheticNameInUseError for the name of another
            signal (the app shows an information box). The store is
            unchanged when an error is raised.
        """
        # LLFR-00267: the name is compared without outer spaces.
        signal = self.get(old_name_str)
        trimmed_name_str = new_name_str.strip()
        if not trimmed_name_str:
            raise EmptySyntheticNameError("The name is empty.")
        if trimmed_name_str == old_name_str:
            return trimmed_name_str
        # LLFR-00267: no two signals of the signal list share a name.
        if trimmed_name_str in data_name_set or self.contains(
                trimmed_name_str):
            raise SyntheticNameInUseError(
                f'A signal named "{trimmed_name_str}" already exists.')
        signal.name_str = trimmed_name_str
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
            for the "synthetic_signals" key of the layout file.
        """
        # LLFR-00225 item 10: every synthetic signal, in creation order.
        return [self.layout_entry(signal) for signal in self.signal_list]

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
        """Create a synthetic signal from a layout file entry.

        Inputs:
            entry_dict: one entry of the "synthetic_signals" list (see
                the module docstring), as read by json.load.
            signal_lookup: function name -> samples of any signal in
                the signal list, data file or synthetic.
            time_array: the time signal of the data file, in seconds.
            data_name_set: the names of the data file signals.
        Outputs: the new SyntheticSignal, with the saved name, appended
            to the store. An FFT time range is first limited to the time
            range of the data file.
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
        # LLFR-00262: the saved name must not be a data file signal's,
        # nor the name of a synthetic signal created before it.
        if name_str in data_name_set:
            raise SyntheticNameInUseError(
                f'"{name_str}" is the name of a signal of the data file.')
        if self.contains(name_str):
            raise SyntheticNameInUseError(
                f'"{name_str}" is already the name of an earlier '
                f'synthetic signal.')
        if operation_str == operations.FFT_STR:
            # LLFR-00262: the FFT range is limited to the file's range.
            parameter = limited_time_range(
                operations.check_time_range(parameter), time_array)
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
            wrong type; SyntheticOperationError for an unknown
            operation.
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
        source_name_list = entry_dict[SIGNALS_KEY_STR]
        if not isinstance(source_name_list, list):
            raise SyntheticEntryError(
                'The "signals" of a synthetic signal must be a list of '
                'signal names.')
        parameter = parameter_from_entry(
            operation_str, entry_dict.get(PARAMETER_KEY_STR))
        return name_str, operation_str, list(source_name_list), parameter


def limited_time_range(time_range_tuple: tuple, time_array) -> tuple:
    """Limit an FFT time range to the time range of the data file.

    Inputs:
        time_range_tuple: (start_s, end_s), in seconds.
        time_array: the time signal of the data file, in seconds.
    Outputs: (max(start_s, first time), min(end_s, last time)); the
        range is returned unchanged when the time signal is empty.
    """
    # LLFR-00262: the saved range limited to the data file's range.
    times_array = np.asarray(time_array, dtype=np.float64)
    start_s, end_s = time_range_tuple
    if times_array.size == 0:
        return (start_s, end_s)
    first_s = float(np.nanmin(times_array))
    last_s = float(np.nanmax(times_array))
    return (max(start_s, first_s) if math.isfinite(first_s) else start_s,
            min(end_s, last_s) if math.isfinite(last_s) else end_s)


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


def entry_source_reason(store: SyntheticSignalStore, entry_dict,
                        data_name_set: set, later_name_set: set,
                        failed_name_set: set) -> str:
    """Explain a source of an entry that is not in the signal list yet.

    Inputs:
        store: the store the entries are created in.
        entry_dict: one entry of the "synthetic_signals" list.
        data_name_set: the names of the data file signals.
        later_name_set: the names of the entries after this one.
        failed_name_set: the names of the earlier entries that were not
            created.
    Outputs: the reason for the load report, or "" when every source
        is listed, or is missing for a reason that create_from_entry
        gives itself.
    """
    # LLFR-00262: a source must exist when the signal is created; a
    # hand-edited list may name a signal that was not created, or one
    # that comes later in the list (a forward reference or a cycle).
    source_value = (entry_dict.get(SIGNALS_KEY_STR)
                    if isinstance(entry_dict, dict) else None)
    if not isinstance(source_value, list):
        return ""
    for source_name_str in source_value:
        if (not isinstance(source_name_str, str)
                or source_name_str in data_name_set
                or store.contains(source_name_str)):
            continue
        if source_name_str in failed_name_set:
            return (f'The signal "{source_name_str}" it is computed from '
                    f'was not created.')
        if source_name_str in later_name_set:
            return (f'The signal "{source_name_str}" it is computed from '
                    f'comes later in the list of synthetic signals; a '
                    f'synthetic signal must come after the signals it is '
                    f'computed from.')
    return ""


def create_layout_signals(store: SyntheticSignalStore, entry_list: list,
                          signal_lookup, time_array,
                          data_name_set: set) -> tuple:
    """Create the synthetic signals of a layout file, in its order.

    Inputs:
        store: the store to add the signals to (emptied by the caller,
            LLFR-00262).
        entry_list: the "synthetic_signals" list of the layout file, as
            read by json.load; any value is accepted.
        signal_lookup: function name -> samples of any signal of the
            signal list, data file or synthetic.
        time_array: the time signal of the data file, in seconds.
        data_name_set: the names of the data file signals.
    Outputs: a tuple (not_created_list, limited_list):
        not_created_list holds (label_str, reason_str) for each entry
        that was not created (LLFR-00237); limited_list holds
        (name_str, saved range tuple, used range tuple) for each FFT
        whose saved time range was limited to the data file.
    Never raises: an entry that cannot be created is skipped.
    """
    # LLFR-00262: in the file's order, with their saved names.
    if not isinstance(entry_list, list):
        entry_list = []
    name_list = [entry_label(entry_dict, index_i + 1)
                 for index_i, entry_dict in enumerate(entry_list)]
    not_created_list = []
    limited_list = []
    failed_name_set = set()
    for index_i, entry_dict in enumerate(entry_list):
        label_str = name_list[index_i]
        try:
            # LLFR-00262: hand-edited entries are type-checked first.
            store.read_entry(entry_dict)
            reason_str = entry_source_reason(
                store, entry_dict, data_name_set,
                set(name_list[index_i + 1:]), failed_name_set)
            if reason_str:
                raise SyntheticSourceError(reason_str)
            signal = store.create_from_entry(entry_dict, signal_lookup,
                                             time_array, data_name_set)
        except SyntheticSignalError as error:
            # LLFR-00262, LLFR-00237: not created, with the reason.
            reason_str = str(error)
        except Exception as error:
            # PCR-00025: an unexpected failure only skips this entry.
            reason_str = (f"It could not be created because of an "
                          f"unexpected error: {error}")
        else:
            if signal.is_fft_b:
                # LLFR-00262: the saved range limited to the data file.
                saved_tuple = parameter_from_entry(
                    signal.operation_str,
                    entry_dict.get(PARAMETER_KEY_STR))
                saved_tuple = (float(saved_tuple[0]),
                               float(saved_tuple[1]))
                if saved_tuple != tuple(signal.parameter):
                    limited_list.append((signal.name_str, saved_tuple,
                                         tuple(signal.parameter)))
            continue
        not_created_list.append((label_str, reason_str))
        if not (label_str in data_name_set or store.contains(label_str)):
            failed_name_set.add(label_str)
    return not_created_list, limited_list


def same_signal(old_signal: SyntheticSignal, store: SyntheticSignalStore,
                new_signal: SyntheticSignal) -> bool:
    """Tell whether a recreated synthetic signal equals an old one.

    Inputs:
        old_signal: a synthetic signal removed by a layout load.
        store: the store that holds new_signal.
        new_signal: the synthetic signal of the layout file with the
            same name.
    Outputs: True when both have the same layout file entry (operation,
        sources and parameter) and the same samples, so that a curve of
        a kept tab shows exactly what it showed before (LLFR-00229).
    """
    # LLFR-00282: the curve of a kept tab would not change.
    if store.layout_entry(old_signal) != store.layout_entry(new_signal):
        return False
    if not np.array_equal(np.asarray(old_signal.value_array),
                          np.asarray(new_signal.value_array),
                          equal_nan=True):
        return False
    if (old_signal.frequency_array is None) != (
            new_signal.frequency_array is None):
        return False
    return old_signal.frequency_array is None or np.array_equal(
        old_signal.frequency_array, new_signal.frequency_array,
        equal_nan=True)
