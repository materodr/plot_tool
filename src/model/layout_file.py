"""Layout files: save and load the layout of the plots (HLFR-00049 to
HLFR-00052).

A layout file is a JSON text file (HLFR-00051, LLFR-00227) that holds
what the plot panel shows and how (LLFR-00225): the tabs, their plots,
the curves of each plot with their color and width, the pinned data
tips and the delta markers of each plot, the vertical markers, the
shared time range, the grid setting and the panel widths. It holds no
path or name of the data file, no undo or redo history, no active plot
tool and no search text (LLFR-00226).

Plots, curves, data tips and delta markers are found by their position
in the file: a plot is an entry of the ``plots`` list of its tab, and
its curves, data tips and delta markers are entries of its own lists.
No internal id of the app is written.

An example of a layout file::

    {
      "format": "plot_tool layout",
      "version": 1,
      "shown_tab": 0,
      "time_range": {"start": 0.5, "end": 2.25},
      "grid": true,
      "panel_widths": {"plot_panel": 900, "signal_list_panel": 300},
      "vertical_markers": [{"name": "Marker 1", "time": 1.0}],
      "synthetic_signals": [],
      "tabs": [
        {"name": "Tab 1",
         "plots": [
           {"curves": [{"signal": "Speed", "color": "#1f77b4",
                        "width": 1}],
            "data_tips": [{"signal": "Speed", "time": 1.5,
                           "label_position": {"right_points": 20.0,
                                              "up_points": 15.0}}],
            "delta_markers": [{"kind": "delta_x",
                               "first_point": {"signal": "Speed",
                                               "time": 0.5},
                               "second_point": {"signal": "Speed",
                                                "time": 2.0}}]}]}]
    }

(The app writes every value on its own line, indented by 2 spaces.)
A ``label_position`` of ``null`` means that the data tip was never
moved, so the app places its label beside the point by itself.

The list ``synthetic_signals`` is the place of the synthetic signals of
LLFR-00225 item 10 and LLFR-00262. This version writes it empty and its
loader hands its entries, unchanged, to an optional builder function
(``synthetic_signal_builder`` of ``rebuild_layout``) that does nothing
by default.

Loading rebuilds the layout in a Workspace with the signals of the open
data file (LLFR-00229 to LLFR-00235) and collects in a LayoutReport what
could not be rebuilt or was changed (LLFR-00237). A hand-edited file of
the right format but with wrong types never raises: such values are
replaced or skipped and named in the report.

This module holds no Qt code (COR-00009).
"""

import json
import math
import re

import numpy as np

from model.curve_colors import is_far_from_marker_color
from model.workspace import (
    AUTOMATIC_LABEL_OFFSET_TUPLE, DEFAULT_WIDTH_I, DELTA_X_KIND_STR,
    DELTA_Y_KIND_STR, MAXIMUM_PLOTS_PER_TAB_I, PRESET_WIDTH_TUPLE)

# LLFR-00228: the identification of a layout file.
LAYOUT_FORMAT_STR = "plot_tool layout"
LAYOUT_VERSION_I = 1
# LLFR-00219, LLFR-00221: the extension of a layout file.
LAYOUT_SUFFIX_STR = ".json"
# LLFR-00227: the JSON text is indented by 2 spaces.
LAYOUT_INDENT_I = 2
# LLFR-00232: largest difference between a saved time and the time of
# the sample a data tip or delta marker point is placed on.
SAMPLE_TIME_TOLERANCE_S = 1e-6

# LLFR-00225, LLFR-00227: the keys of the file, English words that
# describe their values.
FORMAT_KEY_STR = "format"
VERSION_KEY_STR = "version"
SHOWN_TAB_KEY_STR = "shown_tab"
TIME_RANGE_KEY_STR = "time_range"
START_KEY_STR = "start"
END_KEY_STR = "end"
GRID_KEY_STR = "grid"
PANEL_WIDTHS_KEY_STR = "panel_widths"
PLOT_PANEL_KEY_STR = "plot_panel"
SIGNAL_LIST_PANEL_KEY_STR = "signal_list_panel"
VERTICAL_MARKERS_KEY_STR = "vertical_markers"
SYNTHETIC_SIGNALS_KEY_STR = "synthetic_signals"
TABS_KEY_STR = "tabs"
NAME_KEY_STR = "name"
PLOTS_KEY_STR = "plots"
CURVES_KEY_STR = "curves"
SIGNAL_KEY_STR = "signal"
COLOR_KEY_STR = "color"
WIDTH_KEY_STR = "width"
TIME_KEY_STR = "time"
DATA_TIPS_KEY_STR = "data_tips"
LABEL_POSITION_KEY_STR = "label_position"
RIGHT_POINTS_KEY_STR = "right_points"
UP_POINTS_KEY_STR = "up_points"
DELTA_MARKERS_KEY_STR = "delta_markers"
KIND_KEY_STR = "kind"
FIRST_POINT_KEY_STR = "first_point"
SECOND_POINT_KEY_STR = "second_point"
# LLFR-00225 item 8: the two kinds of delta markers, as written.
DELTA_X_KIND_NAME_STR = "delta_x"
DELTA_Y_KIND_NAME_STR = "delta_y"
KIND_NAME_DICT = {DELTA_X_KIND_STR: DELTA_X_KIND_NAME_STR,
                  DELTA_Y_KIND_STR: DELTA_Y_KIND_NAME_STR}
KIND_FROM_NAME_DICT = {name_str: kind_str
                       for kind_str, name_str in KIND_NAME_DICT.items()}
KIND_LABEL_DICT = {DELTA_X_KIND_STR: "Delta X marker",
                   DELTA_Y_KIND_STR: "Delta Y marker"}
# LLFR-00235: a valid curve color.
COLOR_PATTERN_STR = r"#[0-9a-fA-F]{6}"

# LLFR-00236: the messages of the error box of an unreadable file.
UNREADABLE_MESSAGE_STR = (
    "The file '{path}' could not be read as a layout file. {reason}")
NOT_READABLE_REASON_STR = "The file could not be read: {error}"
NOT_UTF8_REASON_STR = "The file is not a UTF-8 text file."
NOT_JSON_REASON_STR = "The file is not valid JSON text: {error}"
NOT_LAYOUT_REASON_STR = (
    "The file does not start with the entries \"format\": "
    "\"plot_tool layout\" and \"version\".")
NEWER_VERSION_REASON_STR = (
    "The file has layout format version {version}, but this app reads "
    "only versions up to {supported}.")

# LLFR-00237: the headings of the load report.
SYNTHETIC_HEADING_STR = "Synthetic signals not created:"
MISSING_HEADING_STR = "Signals not in the data file:"
NOT_REBUILT_HEADING_STR = "Not rebuilt:"
TIME_RANGE_HEADING_STR = "Time range:"
REPLACED_HEADING_STR = "Values replaced:"
REPORT_ITEM_PREFIX_STR = "  - "


class LayoutFileError(Exception):
    """A file that cannot be read as a layout file (LLFR-00236).

    Inputs:
        message_str: the text shown in the error box.
    """


class LayoutReport:
    """What loading a layout could not rebuild or changed (LLFR-00237).

    Inputs: none.
    Attributes:
        synthetic_line_list: synthetic signals not created, with the
            reason (LLFR-00262; filled by the synthetic signal builder).
        missing_signal_list: the signals not in the data file, each named
            once, in the order they were met (LLFR-00231).
        not_rebuilt_line_list: data tips, vertical markers, delta
            markers, plots and curves not rebuilt, with time and reason
            (LLFR-00231 to LLFR-00233, LLFR-00235).
        time_range_line_list: how the time range was changed
            (LLFR-00234).
        replaced_line_list: the values that were replaced (LLFR-00235).
    """

    def __init__(self) -> None:
        """Start with nothing to report.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00237: one list per kind of entry of the report.
        self.synthetic_line_list = []
        self.missing_signal_list = []
        self.not_rebuilt_line_list = []
        self.time_range_line_list = []
        self.replaced_line_list = []

    def add_missing_signal(self, signal_name_str: str) -> None:
        """Note a signal that is not in the data file, once.

        Inputs:
            signal_name_str: the name of the signal.
        Outputs: none.
        """
        # LLFR-00237: each missing signal is named once.
        if signal_name_str not in self.missing_signal_list:
            self.missing_signal_list.append(signal_name_str)

    def add_synthetic_signal(self, line_str: str) -> None:
        """Note a synthetic signal that was not created, with the reason.

        Inputs:
            line_str: the text of the entry.
        Outputs: none.
        """
        # LLFR-00262, LLFR-00237: filled by the builder of issue #110.
        self.synthetic_line_list.append(str(line_str))

    def add_not_rebuilt(self, line_str: str) -> None:
        """Note a part of the layout that was not rebuilt.

        Inputs:
            line_str: the text of the entry, with time and reason.
        Outputs: none.
        """
        # LLFR-00237: each item not rebuilt, with its time and reason.
        self.not_rebuilt_line_list.append(str(line_str))

    def add_time_range(self, line_str: str) -> None:
        """Note how the time range was changed.

        Inputs:
            line_str: the text of the entry.
        Outputs: none.
        """
        # LLFR-00237: the time range when it was changed.
        self.time_range_line_list.append(str(line_str))

    def add_replaced(self, line_str: str) -> None:
        """Note a value that was replaced.

        Inputs:
            line_str: the text of the entry, with the old and new value.
        Outputs: none.
        """
        # LLFR-00237: each value that was replaced.
        self.replaced_line_list.append(str(line_str))

    def is_empty(self) -> bool:
        """Tell whether everything was rebuilt as saved.

        Inputs: none.
        Outputs: True when there is nothing to report.
        """
        # LLFR-00237: then no message is shown.
        return not (self.synthetic_line_list or self.missing_signal_list
                    or self.not_rebuilt_line_list
                    or self.time_range_line_list or self.replaced_line_list)

    def section_list(self) -> list:
        """Return the non-empty sections of the report.

        Inputs: none.
        Outputs: a list of tuples (heading_str, entry list), in the order
            of LLFR-00237.
        """
        # LLFR-00237: synthetic signals, missing signals, items not
        # rebuilt, the time range and the replaced values.
        section_list = [
            (SYNTHETIC_HEADING_STR, self.synthetic_line_list),
            (MISSING_HEADING_STR, self.missing_signal_list),
            (NOT_REBUILT_HEADING_STR, self.not_rebuilt_line_list),
            (TIME_RANGE_HEADING_STR, self.time_range_line_list),
            (REPLACED_HEADING_STR, self.replaced_line_list)]
        return [(heading_str, list(entry_list))
                for heading_str, entry_list in section_list if entry_list]

    def text(self) -> str:
        """Return the report as the text of the information box.

        Inputs: none.
        Outputs: the text, one entry per line under its heading; "" when
            the report is empty.
        """
        # LLFR-00237: one box that lists everything.
        if self.is_empty():
            return ""
        line_list = []
        for heading_str, entry_list in self.section_list():
            if line_list:
                line_list.append("")
            line_list.append(heading_str)
            line_list += [REPORT_ITEM_PREFIX_STR + entry_str
                          for entry_str in entry_list]
        return "\n".join(line_list)


class LayoutResult:
    """What the controller applies after the model was rebuilt.

    Inputs:
        report: the LayoutReport of the load.
        first_tab_id_i: id of the first tab of the layout file, -1 when
            the file added no tab.
        time_range_tuple: the (start_s, end_s) range to show in every
            plot, or () for the whole time range of the data file.
        grid_shown_b: the grid setting of the file, or None when it could
            not be used (the grid is then left as it is).
        panel_width_tuple: (plot panel width, signal list panel width) in
            pixels, or () when they could not be used.
        tabs_replaced_b: True when the tabs of the file replaced the
            current tabs (LLFR-00229).
    """

    def __init__(self, report: LayoutReport, first_tab_id_i: int,
                 time_range_tuple: tuple, grid_shown_b,
                 panel_width_tuple: tuple, tabs_replaced_b: bool) -> None:
        """Store the result.

        Inputs: see the class docstring.
        Outputs: none.
        """
        # LLFR-00229, LLFR-00230: what is applied to the view.
        self.report = report
        self.first_tab_id_i = int(first_tab_id_i)
        self.time_range_tuple = tuple(time_range_tuple)
        self.grid_shown_b = grid_shown_b
        self.panel_width_tuple = tuple(panel_width_tuple)
        self.tabs_replaced_b = bool(tabs_replaced_b)


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------

def ensure_layout_suffix(path_str: str) -> str:
    """Add ``.json`` to a path whose file name has no extension.

    Inputs:
        path_str: the path chosen in the save file dialog.
    Outputs: path_str followed by ``.json`` when its file name has no
        extension, else path_str unchanged.
    """
    # LLFR-00219: only a name typed without an extension gets ".json".
    file_name_str = path_str.replace("\\", "/").rsplit("/", 1)[-1]
    stem_str = file_name_str.lstrip(".")
    if "." in stem_str:
        return path_str
    return path_str + LAYOUT_SUFFIX_STR


def finite_number(value):
    """Return a JSON value as a finite float, if it is one.

    Inputs:
        value: any value read from the file.
    Outputs: the float, or None for a value that is not a finite number
        (text, true or false, null, a list, NaN, ...).
    """
    # LLFR-00235: a hand-edited file may hold text instead of a number.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number_f = float(value)
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(number_f):
        return None
    return number_f


def list_entry(container, key_str: str) -> list:
    """Return a list entry of a JSON object, or an empty list.

    Inputs:
        container: a value read from the file, normally a dict.
        key_str: the key of the entry.
    Outputs: the list, or [] when the container is not a dict or the
        entry is missing or not a list.
    """
    # LLFR-00235: a missing or wrong entry is treated as empty.
    if not isinstance(container, dict):
        return []
    value = container.get(key_str)
    return value if isinstance(value, list) else []


def describe_value(value) -> str:
    """Return a short text that shows a value read from the file.

    Inputs:
        value: any JSON value.
    Outputs: the value as JSON text, cut to 40 characters.
    """
    # LLFR-00237: replaced values are named in the report.
    try:
        text_str = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        text_str = repr(value)
    if len(text_str) > 40:
        text_str = text_str[:37] + "..."
    return text_str


def format_time(time_s: float) -> str:
    """Return a time for the report, in seconds.

    Inputs:
        time_s: the time, or None when it is not a number.
    Outputs: for example "1.25 s", or "an unreadable time".
    """
    # LLFR-00237: the report gives the time of each item not rebuilt.
    if time_s is None:
        return "an unreadable time"
    return f"{time_s:.9g} s"


def file_time_range(time_array) -> tuple:
    """Return the first and last time of the data file.

    Inputs:
        time_array: the values of the time signal.
    Outputs: (start_s, end_s), or () when no time is finite.
    """
    # LLFR-00119, LLFR-00233, LLFR-00234: the time range of the file.
    finite_time_array = np.asarray(time_array, dtype=float)
    finite_time_array = finite_time_array[np.isfinite(finite_time_array)]
    if finite_time_array.size == 0:
        return ()
    return (float(np.min(finite_time_array)),
            float(np.max(finite_time_array)))


# ----------------------------------------------------------------------
# Writing (LLFR-00225 to LLFR-00228)
# ----------------------------------------------------------------------

def point_entry(point_tuple: tuple) -> dict:
    """Return the file entry of a delta marker point.

    Inputs:
        point_tuple: (signal_name_str, time_s, value_f).
    Outputs: a dict with the signal and the time of the point.
    """
    # LLFR-00225 item 8: the signal and time of each point; the value is
    # read again from the data file when the layout is loaded.
    return {SIGNAL_KEY_STR: str(point_tuple[0]),
            TIME_KEY_STR: float(point_tuple[1])}


def plot_entry(plot) -> dict:
    """Return the file entry of a plot.

    Inputs:
        plot: a model Plot.
    Outputs: a dict with its curves, data tips and delta markers.
    """
    # LLFR-00225 item 3: the curves in drawing order, with signal name,
    # color and width.
    curve_list = [{SIGNAL_KEY_STR: curve.signal_name_str,
                   COLOR_KEY_STR: curve.color_str,
                   WIDTH_KEY_STR: int(curve.width_i)}
                  for curve in plot.curve_list]
    # LLFR-00225 item 7: each pinned data tip, with the signal and time
    # of its point and the position of its label relative to the point.
    data_tip_list = []
    for pinned_tip in plot.pinned_tip_list:
        offset_tuple = tuple(pinned_tip.label_offset_tuple)
        label_position_dict = None
        if len(offset_tuple) == 2:
            label_position_dict = {
                RIGHT_POINTS_KEY_STR: float(offset_tuple[0]),
                UP_POINTS_KEY_STR: float(offset_tuple[1])}
        data_tip_list.append({SIGNAL_KEY_STR: pinned_tip.signal_name_str,
                              TIME_KEY_STR: float(pinned_tip.time_s),
                              LABEL_POSITION_KEY_STR: label_position_dict})
    # LLFR-00225 item 8: the kind and the two points of each delta marker.
    delta_marker_list = [
        {KIND_KEY_STR: KIND_NAME_DICT[delta_marker.kind_str],
         FIRST_POINT_KEY_STR: point_entry(delta_marker.first_point_tuple),
         SECOND_POINT_KEY_STR: point_entry(delta_marker.second_point_tuple)}
        for delta_marker in plot.delta_marker_list]
    return {CURVES_KEY_STR: curve_list, DATA_TIPS_KEY_STR: data_tip_list,
            DELTA_MARKERS_KEY_STR: delta_marker_list}


def build_layout_dict(workspace, shown_tab_id_i: int,
                      time_range_tuple: tuple, grid_shown_b: bool,
                      panel_width_tuple: tuple = (),
                      synthetic_signal_list: list = ()) -> dict:
    """Return the content of a layout file for the current layout.

    Inputs:
        workspace: the Workspace with the tabs, plots and markers.
        shown_tab_id_i: id of the tab shown in the plot panel.
        time_range_tuple: (start_s, end_s) shared by the plots, or ()
            when no range is known.
        grid_shown_b: True while the grid is shown.
        panel_width_tuple: (plot panel width, signal list panel width)
            in pixels, or () when unknown.
        synthetic_signal_list: the entries of the synthetic signals
            (LLFR-00225 item 10), already as JSON values; empty until
            issue #110 fills it.
    Outputs: a dict whose first entries are "format" and "version"
        (LLFR-00228), ready for layout_text.
    """
    # LLFR-00228: the identification comes first.
    layout_dict = {FORMAT_KEY_STR: LAYOUT_FORMAT_STR,
                   VERSION_KEY_STR: LAYOUT_VERSION_I}
    # LLFR-00225 item 1: which tab is shown, by its position.
    shown_index_i = 0
    for tab_index_i, tab in enumerate(workspace.tab_list):
        if tab.tab_id_i == shown_tab_id_i:
            shown_index_i = tab_index_i
    layout_dict[SHOWN_TAB_KEY_STR] = shown_index_i
    # LLFR-00225 item 4: the shared x-axis range, in seconds.
    if len(time_range_tuple) == 2:
        layout_dict[TIME_RANGE_KEY_STR] = {
            START_KEY_STR: float(time_range_tuple[0]),
            END_KEY_STR: float(time_range_tuple[1])}
    else:
        layout_dict[TIME_RANGE_KEY_STR] = None
    # LLFR-00225 item 5: whether the grid is shown.
    layout_dict[GRID_KEY_STR] = bool(grid_shown_b)
    # LLFR-00225 item 9: the panel widths, in pixels.
    if len(panel_width_tuple) == 2:
        layout_dict[PANEL_WIDTHS_KEY_STR] = {
            PLOT_PANEL_KEY_STR: int(panel_width_tuple[0]),
            SIGNAL_LIST_PANEL_KEY_STR: int(panel_width_tuple[1])}
    else:
        layout_dict[PANEL_WIDTHS_KEY_STR] = None
    # LLFR-00225 item 6: each vertical marker, with its name and time.
    layout_dict[VERTICAL_MARKERS_KEY_STR] = [
        {NAME_KEY_STR: marker.name_str, TIME_KEY_STR: float(marker.time_s)}
        for marker in workspace.marker_list]
    # LLFR-00225 item 10, LLFR-00262: the synthetic signals (issue #110).
    layout_dict[SYNTHETIC_SIGNALS_KEY_STR] = list(synthetic_signal_list)
    # LLFR-00225 items 1 and 2: the tabs in order, each with its plots
    # from top to bottom.
    layout_dict[TABS_KEY_STR] = [
        {NAME_KEY_STR: tab.name_str,
         PLOTS_KEY_STR: [plot_entry(plot) for plot in tab.plot_list]}
        for tab in workspace.tab_list]
    return layout_dict


def layout_text(layout_dict: dict) -> str:
    """Return the JSON text of a layout file.

    Inputs:
        layout_dict: the content built by build_layout_dict.
    Outputs: the text, indented by 2 spaces with each value on its own
        line, ending with a newline. Times are written with Python's
        shortest exact representation, so they are read back as the
        same value (LLFR-00227).
    """
    # LLFR-00227: JSON indented by 2 spaces; non-ASCII names are kept as
    # they are, since the file is written in UTF-8.
    return json.dumps(layout_dict, indent=LAYOUT_INDENT_I,
                      ensure_ascii=False, allow_nan=False) + "\n"


def layout_bytes(layout_dict: dict) -> bytes:
    """Return the bytes of a layout file.

    Inputs:
        layout_dict: the content built by build_layout_dict.
    Outputs: the JSON text encoded in UTF-8 (LLFR-00227).
    """
    # LLFR-00227: the file is written in UTF-8.
    return layout_text(layout_dict).encode("utf-8")


# ----------------------------------------------------------------------
# Reading (LLFR-00228, LLFR-00236)
# ----------------------------------------------------------------------

def parse_layout_text(text_str: str, path_str: str = "") -> dict:
    """Read the content of a layout file from its text.

    Inputs:
        text_str: the text of the file.
        path_str: the path of the file, named in error messages.
    Outputs: the content as a dict. Raises LayoutFileError when the text
        is not valid JSON or does not identify itself as a layout file
        of a version this app reads.
    """
    # LLFR-00236: not valid JSON.
    try:
        layout_dict = json.loads(text_str)
    except (ValueError, RecursionError) as error:
        raise LayoutFileError(UNREADABLE_MESSAGE_STR.format(
            path=path_str, reason=NOT_JSON_REASON_STR.format(
                error=error))) from None
    # LLFR-00228, LLFR-00236: the "format" and "version" entries tell a
    # layout file from other JSON files.
    if not isinstance(layout_dict, dict):
        raise LayoutFileError(UNREADABLE_MESSAGE_STR.format(
            path=path_str, reason=NOT_LAYOUT_REASON_STR))
    version_value = layout_dict.get(VERSION_KEY_STR)
    # LLFR-00228: a whole number, also when hand-edited as 1.0.
    version_i = 0
    if isinstance(version_value, int) and not isinstance(version_value,
                                                         bool):
        version_i = int(version_value)
    elif (isinstance(version_value, float) and math.isfinite(version_value)
          and version_value.is_integer()):
        version_i = int(version_value)
    if layout_dict.get(FORMAT_KEY_STR) != LAYOUT_FORMAT_STR or version_i < 1:
        raise LayoutFileError(UNREADABLE_MESSAGE_STR.format(
            path=path_str, reason=NOT_LAYOUT_REASON_STR))
    # LLFR-00228: a later format may hold entries this app cannot read.
    if version_i > LAYOUT_VERSION_I:
        raise LayoutFileError(UNREADABLE_MESSAGE_STR.format(
            path=path_str, reason=NEWER_VERSION_REASON_STR.format(
                version=version_i, supported=LAYOUT_VERSION_I)))
    return layout_dict


def read_layout_file(path_str: str) -> dict:
    """Read a layout file from the disk.

    Inputs:
        path_str: the path of the file.
    Outputs: its content as a dict. Raises LayoutFileError when the file
        cannot be read, is not UTF-8 text, is not valid JSON or is not a
        layout file (LLFR-00236).
    """
    # LLFR-00236: a file that cannot be read.
    try:
        with open(path_str, "rb") as layout_file:
            content_bytes = layout_file.read()
    except OSError as error:
        reason_str = NOT_READABLE_REASON_STR.format(
            error=error.strerror or error)
        raise LayoutFileError(UNREADABLE_MESSAGE_STR.format(
            path=path_str, reason=reason_str)) from None
    # LLFR-00227, LLFR-00236: the file is UTF-8 text; a byte order mark
    # written by some text editors is accepted.
    try:
        text_str = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise LayoutFileError(UNREADABLE_MESSAGE_STR.format(
            path=path_str, reason=NOT_UTF8_REASON_STR)) from None
    return parse_layout_text(text_str, path_str)


def synthetic_signal_entry_list(layout_dict: dict) -> list:
    """Return the entries of the synthetic signals of a layout file.

    Inputs:
        layout_dict: the content of the file.
    Outputs: the list of "synthetic_signals", or [] when it is missing
        or not a list.
    """
    # LLFR-00262: the place of the synthetic signals (issue #110).
    return list_entry(layout_dict, SYNTHETIC_SIGNALS_KEY_STR)


# ----------------------------------------------------------------------
# Rebuilding (LLFR-00229 to LLFR-00235)
# ----------------------------------------------------------------------

class LayoutBuilder:
    """Rebuilds the layout of a file in a workspace.

    Inputs:
        workspace: the Workspace to add the layout to.
        signal_dict: signal name -> numpy array of the open data file
            (and, from issue #110, of the synthetic signals).
        time_array: the values of the time signal, in seconds.
    Attributes:
        report: the LayoutReport being filled.
    """

    def __init__(self, workspace, signal_dict: dict, time_array) -> None:
        """Store the workspace and the signals.

        Inputs: see the class docstring.
        Outputs: none.
        """
        # LLFR-00230: the layout is rebuilt with the signals of the open
        # data file.
        self.workspace = workspace
        self.signal_dict = signal_dict
        self.time_array = np.asarray(time_array, dtype=float)
        self.file_range_tuple = file_time_range(self.time_array)
        self.report = LayoutReport()

    # Signals and points ---------------------------------------------

    def signal_name(self, entry, owner_str: str, what_str: str):
        """Return the signal name of an entry, if it is usable.

        Inputs:
            entry: a curve, data tip or point entry.
            owner_str: where the entry is, for the report.
            what_str: what the entry is, for the report.
        Outputs: the name, or None when the entry has no name (reported).
        """
        # LLFR-00235: a hand-edited entry may have no signal name.
        name_value = entry.get(SIGNAL_KEY_STR) if isinstance(
            entry, dict) else None
        if not isinstance(name_value, str):
            self.report.add_not_rebuilt(
                f"{what_str} in {owner_str}: it has no valid signal name.")
            return None
        return name_value

    def sample_point(self, plot, point_entry_value):
        """Find the sample a saved data tip or delta point is placed on.

        Inputs:
            plot: the rebuilt model Plot.
            point_entry_value: the entry, with "signal" and "time".
        Outputs: a tuple (point_tuple, time_s, reason_str): point_tuple is
            (signal_name_str, sample time, sample value) or () when the
            point cannot be rebuilt; time_s is the saved time (None when
            unreadable); reason_str says why the point was not placed.
        """
        # LLFR-00232: the signal must be drawn in the plot and have a
        # sample within 1 microsecond of the saved time.
        if not isinstance(point_entry_value, dict):
            return ((), None, "a point of it could not be read")
        time_s = finite_number(point_entry_value.get(TIME_KEY_STR))
        signal_value = point_entry_value.get(SIGNAL_KEY_STR)
        if not isinstance(signal_value, str):
            return ((), time_s, "a point of it has no valid signal name")
        if time_s is None:
            return ((), None, "the time of a point is not a number")
        if signal_value not in self.signal_dict:
            # LLFR-00231, LLFR-00237: named in the missing signals too.
            self.report.add_missing_signal(signal_value)
            return ((), time_s,
                    f"the signal {signal_value} is not in the data file")
        if not plot.has_signal(signal_value):
            return ((), time_s,
                    f"the signal {signal_value} is not drawn in its plot")
        difference_array = np.abs(self.time_array - time_s)
        if not np.any(np.isfinite(difference_array)):
            return ((), time_s, "the data file has no valid time")
        sample_index_i = int(np.nanargmin(difference_array))
        if difference_array[sample_index_i] > SAMPLE_TIME_TOLERANCE_S:
            return ((), time_s,
                    f"the signal {signal_value} has no sample within 1 "
                    f"microsecond of this time")
        sample_time_s = float(self.time_array[sample_index_i])
        value_array = np.asarray(self.signal_dict[signal_value],
                                 dtype=float)
        if sample_index_i >= value_array.size:
            return ((), time_s,
                    f"the signal {signal_value} has no sample here")
        sample_value_f = float(value_array[sample_index_i])
        if not math.isfinite(sample_value_f):
            return ((), time_s,
                    f"the sample of {signal_value} here is not a number")
        # LLFR-00232: the point is placed on that sample.
        return ((signal_value, sample_time_s, sample_value_f), time_s, "")

    # Curves ---------------------------------------------------------

    def usable_curve_list(self, plot_entry_value, owner_str: str) -> list:
        """Return the curve entries of a plot that can be drawn.

        Inputs:
            plot_entry_value: the plot entry of the file.
            owner_str: the plot, for the report.
        Outputs: a list of (signal_name_str, curve entry) in file order,
            leaving out the signals not in the data file (LLFR-00231) and
            a second curve of the same signal (LLFR-00056).
        """
        # LLFR-00230: the curves in the order they were drawn.
        usable_list = []
        seen_name_set = set()
        for curve_entry in list_entry(plot_entry_value, CURVES_KEY_STR):
            signal_name_str = self.signal_name(curve_entry, owner_str,
                                               "A curve")
            if signal_name_str is None:
                continue
            # LLFR-00231: a signal not in the data file is not drawn.
            if signal_name_str not in self.signal_dict:
                self.report.add_missing_signal(signal_name_str)
                continue
            # LLFR-00056: a signal is drawn only once in a plot.
            if signal_name_str in seen_name_set:
                self.report.add_not_rebuilt(
                    f"Curve of {signal_name_str} in {owner_str}: the "
                    f"signal is drawn only once in a plot.")
                continue
            seen_name_set.add(signal_name_str)
            usable_list.append((signal_name_str, curve_entry))
        return usable_list

    def curve_color(self, plot, color_value, owner_str: str,
                    signal_name_str: str) -> str:
        """Return the color a rebuilt curve is drawn in.

        Inputs:
            plot: the model Plot the curve is added to.
            color_value: the saved color.
            owner_str: the plot, for the report.
            signal_name_str: the signal of the curve, for the report.
        Outputs: the saved color, or the next color of the plot when the
            saved one is not valid, is already used in the plot or looks
            like the marker color (LLFR-00235, LLFR-00083).
        """
        # LLFR-00235: a valid "#rrggbb" color not used in the plot.
        reason_str = ""
        if not (isinstance(color_value, str)
                and re.fullmatch(COLOR_PATTERN_STR, color_value)):
            reason_str = "is not a valid color"
        else:
            color_str = color_value.lower()
            used_set = {curve.color_str.lower() for curve in plot.curve_list}
            if color_str in used_set:
                reason_str = "is already used in the plot"
            elif not is_far_from_marker_color(color_str):
                # LLFR-00083: the marker color is never used for curves.
                reason_str = "is too close to the marker color"
            else:
                return color_str
        # LLFR-00033, LLFR-00034: the color a new curve would get.
        new_color_str = plot.next_color()
        self.report.add_replaced(
            f"Color {describe_value(color_value)} of the curve of "
            f"{signal_name_str} in {owner_str} {reason_str}; replaced by "
            f"{new_color_str}.")
        return new_color_str

    def curve_width(self, width_value, owner_str: str,
                    signal_name_str: str) -> int:
        """Return the width a rebuilt curve is drawn with.

        Inputs:
            width_value: the saved width.
            owner_str: the plot, for the report.
            signal_name_str: the signal of the curve, for the report.
        Outputs: the saved width when it is a preset width 1 to 5, else
            width 1 (LLFR-00235, LLFR-00052).
        """
        # LLFR-00235: only the preset widths are used as saved.
        if (not isinstance(width_value, bool)
                and isinstance(width_value, int)
                and width_value in PRESET_WIDTH_TUPLE):
            return int(width_value)
        self.report.add_replaced(
            f"Width {describe_value(width_value)} of the curve of "
            f"{signal_name_str} in {owner_str} is not one of the preset "
            f"widths 1 to 5; replaced by {DEFAULT_WIDTH_I}.")
        return DEFAULT_WIDTH_I

    # Data tips and delta markers ------------------------------------

    def report_lost_items(self, plot_entry_value, owner_str: str,
                          reason_str: str) -> None:
        """Report every data tip and delta marker of a plot not created.

        Inputs:
            plot_entry_value: the plot entry of the file.
            owner_str: the plot, for the report.
            reason_str: why the plot was not created.
        Outputs: none.
        """
        # LLFR-00237: each data tip and delta marker not rebuilt, with
        # its time and the reason.
        for tip_entry in list_entry(plot_entry_value, DATA_TIPS_KEY_STR):
            time_s = (finite_number(tip_entry.get(TIME_KEY_STR))
                      if isinstance(tip_entry, dict) else None)
            self.report.add_not_rebuilt(
                f"Data tip at {format_time(time_s)} in {owner_str}: "
                f"{reason_str}.")
        for delta_entry in list_entry(plot_entry_value,
                                      DELTA_MARKERS_KEY_STR):
            self.report.add_not_rebuilt(
                f"{self.delta_label(delta_entry)} "
                f"{self.delta_times(delta_entry)} in {owner_str}: "
                f"{reason_str}.")

    def label_offset(self, tip_entry_dict: dict, owner_str: str,
                     time_s: float) -> tuple:
        """Return the saved label position of a data tip.

        Inputs:
            tip_entry_dict: the data tip entry.
            owner_str: the plot, for the report.
            time_s: the saved time of the tip, for the report.
        Outputs: (right, up) in points, or AUTOMATIC_LABEL_OFFSET_TUPLE
            when the tip was never moved or the position is not usable
            (then reported as replaced, LLFR-00235).
        """
        # LLFR-00225 item 7: the position relative to the point.
        position_value = tip_entry_dict.get(LABEL_POSITION_KEY_STR)
        if position_value is None:
            return AUTOMATIC_LABEL_OFFSET_TUPLE
        if isinstance(position_value, dict):
            right_f = finite_number(position_value.get(RIGHT_POINTS_KEY_STR))
            up_f = finite_number(position_value.get(UP_POINTS_KEY_STR))
            if right_f is not None and up_f is not None:
                return (right_f, up_f)
        self.report.add_replaced(
            f"Label position {describe_value(position_value)} of the data "
            f"tip at {format_time(time_s)} in {owner_str} could not be "
            f"used; the label is placed beside its point.")
        return AUTOMATIC_LABEL_OFFSET_TUPLE

    def rebuild_data_tips(self, plot, plot_entry_value,
                          owner_str: str) -> None:
        """Pin the saved data tips of a plot again.

        Inputs:
            plot: the rebuilt model Plot.
            plot_entry_value: the plot entry of the file.
            owner_str: the plot, for the report.
        Outputs: none.
        """
        # LLFR-00230: the data tips in the file's order.
        for tip_entry in list_entry(plot_entry_value, DATA_TIPS_KEY_STR):
            point_tuple, time_s, reason_str = self.sample_point(
                plot, tip_entry)
            if not point_tuple:
                # LLFR-00232, LLFR-00237: not rebuilt, time and reason.
                self.report.add_not_rebuilt(
                    f"Data tip at {format_time(time_s)} in {owner_str}: "
                    f"{reason_str}.")
                continue
            # LLFR-00232: placed on the sample found.
            pinned_tip = plot.add_pinned_tip(*point_tuple)
            offset_tuple = self.label_offset(tip_entry, owner_str, time_s)
            if offset_tuple:
                # LLFR-00152, LLFR-00225 item 7: where the user left it.
                plot.move_pinned_tip(pinned_tip, offset_tuple)

    @staticmethod
    def delta_label(delta_entry) -> str:
        """Return the name of a delta marker's kind, for the report.

        Inputs:
            delta_entry: the delta marker entry.
        Outputs: "Delta X marker", "Delta Y marker" or "Delta marker".
        """
        # LLFR-00237: each delta marker is named by its kind.
        kind_value = (delta_entry.get(KIND_KEY_STR)
                      if isinstance(delta_entry, dict) else None)
        kind_str = (KIND_FROM_NAME_DICT.get(kind_value, "")
                    if isinstance(kind_value, str) else "")
        return KIND_LABEL_DICT.get(kind_str, "Delta marker")

    @staticmethod
    def delta_times(delta_entry) -> str:
        """Return the times of a delta marker's points, for the report.

        Inputs:
            delta_entry: the delta marker entry.
        Outputs: for example "between 1 s and 2 s".
        """
        # LLFR-00237: the time of each item not rebuilt.
        time_list = []
        for key_str in (FIRST_POINT_KEY_STR, SECOND_POINT_KEY_STR):
            point_value = (delta_entry.get(key_str)
                           if isinstance(delta_entry, dict) else None)
            time_list.append(finite_number(point_value.get(TIME_KEY_STR))
                             if isinstance(point_value, dict) else None)
        return (f"between {format_time(time_list[0])} and "
                f"{format_time(time_list[1])}")

    def rebuild_delta_markers(self, plot, plot_entry_value,
                              owner_str: str) -> None:
        """Place the saved delta markers of a plot again.

        Inputs:
            plot: the rebuilt model Plot.
            plot_entry_value: the plot entry of the file.
            owner_str: the plot, for the report.
        Outputs: none.
        """
        # LLFR-00230: the delta markers in the file's order.
        for delta_entry in list_entry(plot_entry_value,
                                      DELTA_MARKERS_KEY_STR):
            label_str = (f"{self.delta_label(delta_entry)} "
                         f"{self.delta_times(delta_entry)} in {owner_str}")
            kind_value = (delta_entry.get(KIND_KEY_STR)
                          if isinstance(delta_entry, dict) else None)
            kind_str = (KIND_FROM_NAME_DICT.get(kind_value, "")
                        if isinstance(kind_value, str) else "")
            if not kind_str:
                # LLFR-00225 item 8: the kind must be Delta X or Delta Y.
                self.report.add_not_rebuilt(
                    f"{label_str}: its kind "
                    f"{describe_value(kind_value)} is neither "
                    f"\"{DELTA_X_KIND_NAME_STR}\" nor "
                    f"\"{DELTA_Y_KIND_NAME_STR}\".")
                continue
            point_list = []
            reason_str = ""
            for key_str in (FIRST_POINT_KEY_STR, SECOND_POINT_KEY_STR):
                point_tuple, _, reason_str = self.sample_point(
                    plot, delta_entry.get(key_str))
                if not point_tuple:
                    break
                point_list.append(point_tuple)
            if len(point_list) != 2:
                # LLFR-00232, LLFR-00237: not rebuilt, times and reason.
                self.report.add_not_rebuilt(f"{label_str}: {reason_str}.")
                continue
            # LLFR-00232: both points are placed on their samples.
            plot.add_delta_marker(kind_str, point_list[0], point_list[1])

    # Plots and tabs -------------------------------------------------

    def rebuild_plot(self, tab, plot_entry_value, owner_str: str) -> bool:
        """Create one saved plot in a tab, with its curves and items.

        Inputs:
            tab: the model Tab.
            plot_entry_value: the plot entry of the file.
            owner_str: the plot, for the report.
        Outputs: True when the plot was created.
        """
        if not isinstance(plot_entry_value, dict):
            # LLFR-00235: an entry that is not a plot.
            self.report.add_not_rebuilt(
                f"{owner_str[0].upper()}{owner_str[1:]}: the entry could "
                f"not be read as a plot.")
            return False
        usable_list = self.usable_curve_list(plot_entry_value, owner_str)
        if not usable_list:
            # LLFR-00231: no plot is left with no curve.
            reason_str = ("its plot was not created, because none of its "
                          "signals is in the data file")
            self.report.add_not_rebuilt(
                f"{owner_str[0].upper()}{owner_str[1:]}: not created, "
                f"because none of its signals is in the data file.")
            self.report_lost_items(plot_entry_value, owner_str, reason_str)
            return False
        if tab.is_full():
            # LLFR-00235, HLFR-00018: at most 5 plots in a tab.
            self.report.add_not_rebuilt(
                f"{owner_str[0].upper()}{owner_str[1:]}: not created, "
                f"because a tab holds at most {MAXIMUM_PLOTS_PER_TAB_I} "
                f"plots.")
            self.report_lost_items(
                plot_entry_value, owner_str,
                "its plot was not created, because the tab is full")
            return False
        plot = self.workspace.add_plot(tab.tab_id_i)
        # LLFR-00230: the curves in the order they were drawn, with their
        # saved color and width, or replaced values (LLFR-00235).
        for signal_name_str, curve_entry in usable_list:
            color_value = (curve_entry.get(COLOR_KEY_STR)
                           if isinstance(curve_entry, dict) else None)
            width_value = (curve_entry.get(WIDTH_KEY_STR)
                           if isinstance(curve_entry, dict) else None)
            color_str = self.curve_color(plot, color_value, owner_str,
                                         signal_name_str)
            width_i = self.curve_width(width_value, owner_str,
                                       signal_name_str)
            plot.add_styled_curve(signal_name_str, color_str, width_i)
        # LLFR-00230, LLFR-00232: then its data tips and delta markers.
        self.rebuild_data_tips(plot, plot_entry_value, owner_str)
        self.rebuild_delta_markers(plot, plot_entry_value, owner_str)
        return True

    def tab_name(self, tab_entry, tab_number_i: int,
                 file_name_set: set) -> str:
        """Return the saved name of a tab, if it can be used.

        Inputs:
            tab_entry: the tab entry of the file.
            tab_number_i: the position of the tab in the file, from 1.
            file_name_set: the stripped valid names of the earlier tabs
                of the same file; this tab's valid name is added to it.
        Outputs: the name without surrounding spaces, or "" when the tab
            gets the next default name instead. A name that is not a
            text, is empty or repeats an earlier tab of the file is
            reported (LLFR-00235); a valid name that another tab already
            has (a kept tab, LLFR-00229, or a tab this load named) is
            replaced without a report.
        """
        name_value = (tab_entry.get(NAME_KEY_STR)
                      if isinstance(tab_entry, dict) else None)
        if isinstance(name_value, str) and name_value.strip():
            stripped_name_str = name_value.strip()
            # LLFR-00235: a repeat within the file is a hand edit; the
            # name is still noted so that later repeats are found too.
            if stripped_name_str in file_name_set:
                reason_str = ("is already the name of an earlier tab of "
                              "the file")
            else:
                file_name_set.add(stripped_name_str)
                # LLFR-00235, LLFR-00210, LLFR-00212: a valid name that
                # another tab has is replaced silently (LLFR-00237).
                if self.workspace.is_tab_name_taken(stripped_name_str):
                    return ""
                return stripped_name_str
        elif isinstance(name_value, str):
            reason_str = "is empty"
        else:
            reason_str = "is not a text"
        # LLFR-00235, LLFR-00237: the replaced value is reported.
        self.report.add_replaced(
            f"Name {describe_value(name_value)} of tab {tab_number_i} of "
            f"the file {reason_str}; replaced by "
            f"\"{self.workspace.next_tab_name()}\".")
        return ""

    def rebuild_tabs(self, tab_entry_list: list) -> int:
        """Create the saved tabs, with their plots, after the current ones.

        Inputs:
            tab_entry_list: the "tabs" list of the file.
        Outputs: the id of the first created tab, -1 when none.
        """
        # LLFR-00235: the valid names met so far in the file.
        file_name_set = set()
        first_tab_id_i = -1
        for tab_index_i, tab_entry in enumerate(tab_entry_list):
            # LLFR-00231: every tab of the file is created, even one left
            # with no plot. LLFR-00235, LLFR-00210: a name that cannot be
            # used is replaced by the next default name.
            name_str = self.tab_name(tab_entry, tab_index_i + 1,
                                     file_name_set)
            if name_str:
                tab = self.workspace.add_named_tab(name_str)
            else:
                tab = self.workspace.add_tab()
            if first_tab_id_i < 0:
                first_tab_id_i = tab.tab_id_i
            # LLFR-00230: the plots from top to bottom.
            for plot_index_i, plot_entry_value in enumerate(
                    list_entry(tab_entry, PLOTS_KEY_STR)):
                owner_str = (f"plot {plot_index_i + 1} of tab "
                             f"\"{tab.name_str}\"")
                self.rebuild_plot(tab, plot_entry_value, owner_str)
        return first_tab_id_i

    # Markers, range, grid and widths ------------------------------------

    def rebuild_vertical_markers(self, marker_entry_list: list) -> None:
        """Add the saved vertical markers to the current ones.

        Inputs:
            marker_entry_list: the "vertical_markers" list of the file.
        Outputs: none.
        """
        # LLFR-00230, LLFR-00205: added to the current markers, shown on
        # every plot.
        for marker_entry in marker_entry_list:
            name_value = (marker_entry.get(NAME_KEY_STR)
                          if isinstance(marker_entry, dict) else None)
            time_s = (finite_number(marker_entry.get(TIME_KEY_STR))
                      if isinstance(marker_entry, dict) else None)
            label_str = (f"Vertical marker {describe_value(name_value)} at "
                         f"{format_time(time_s)}")
            if time_s is None:
                self.report.add_not_rebuilt(
                    f"{label_str}: its time is not a number.")
                continue
            # LLFR-00233: only inside the time range of the data file.
            if (not self.file_range_tuple
                    or not (self.file_range_tuple[0] <= time_s
                            <= self.file_range_tuple[1])):
                self.report.add_not_rebuilt(
                    f"{label_str}: its time is outside the time range of "
                    f"the data file{self.file_range_text()}.")
                continue
            # LLFR-00205: markers exist only while a plot exists.
            if not self.workspace.has_plots():
                self.report.add_not_rebuilt(
                    f"{label_str}: no plot was rebuilt to show it on.")
                continue
            if isinstance(name_value, str) and name_value.strip():
                # LLFR-00230: the saved name, kept even when another
                # marker has the same name (marker names need not be
                # unique, LLFR-00088).
                self.workspace.add_named_marker(name_value, time_s)
                continue
            # LLFR-00235, LLFR-00085: a name that cannot be used is
            # replaced by the name of a new marker.
            marker = self.workspace.add_marker(time_s)
            self.report.add_replaced(
                f"Name {describe_value(name_value)} of the vertical marker "
                f"at {format_time(time_s)} is empty or not a text; "
                f"replaced by \"{marker.name_str}\".")

    def file_range_text(self) -> str:
        """Return the time range of the data file, for the report.

        Inputs: none.
        Outputs: for example " (0 s to 10 s)", or "" when unknown.
        """
        # LLFR-00237: the report says what the range of the file is.
        if not self.file_range_tuple:
            return ""
        return (f" ({format_time(self.file_range_tuple[0])} to "
                f"{format_time(self.file_range_tuple[1])})")

    def time_range(self, range_value) -> tuple:
        """Return the time range to show, limited to the data file.

        Inputs:
            range_value: the "time_range" entry of the file.
        Outputs: (start_s, end_s), or () for the whole time range of the
            data file (LLFR-00234).
        """
        if range_value is None:
            # LLFR-00234: a layout saved without a range shows the whole
            # time range of the data file; nothing was changed.
            return ()
        start_s = end_s = None
        if isinstance(range_value, dict):
            start_s = finite_number(range_value.get(START_KEY_STR))
            end_s = finite_number(range_value.get(END_KEY_STR))
        if start_s is None or end_s is None or start_s >= end_s:
            # LLFR-00235: a range that cannot be used.
            self.report.add_time_range(
                f"The saved time range {describe_value(range_value)} could "
                f"not be used; the whole time range of the data "
                f"file{self.file_range_text()} is shown.")
            return ()
        saved_text_str = f"{format_time(start_s)} to {format_time(end_s)}"
        if not self.file_range_tuple:
            return ()
        file_start_s, file_end_s = self.file_range_tuple
        # LLFR-00234, LLFR-00119: limited to the time range of the file.
        limited_start_s = max(start_s, file_start_s)
        limited_end_s = min(end_s, file_end_s)
        if limited_start_s >= limited_end_s:
            # LLFR-00234: no overlap, the whole time range of the file.
            self.report.add_time_range(
                f"The saved time range {saved_text_str} is outside the "
                f"time range of the data file; the whole time range"
                f"{self.file_range_text()} is shown.")
            return ()
        if (limited_start_s, limited_end_s) != (start_s, end_s):
            self.report.add_time_range(
                f"The saved time range {saved_text_str} was limited to "
                f"{format_time(limited_start_s)} to "
                f"{format_time(limited_end_s)}, the part inside the time "
                f"range of the data file.")
        if (limited_start_s, limited_end_s) == self.file_range_tuple:
            return ()
        return (limited_start_s, limited_end_s)

    def grid_setting(self, grid_value):
        """Return the saved grid setting, if it can be used.

        Inputs:
            grid_value: the "grid" entry of the file.
        Outputs: True or False, or None when it is not true or false
            (reported; the grid is then left as it is).
        """
        # LLFR-00230: the grid setting of the file.
        if isinstance(grid_value, bool):
            return grid_value
        self.report.add_replaced(
            f"Grid setting {describe_value(grid_value)} is neither true nor "
            f"false; the grid was left as it was.")
        return None

    def panel_widths(self, widths_value) -> tuple:
        """Return the saved panel widths, if they can be used.

        Inputs:
            widths_value: the "panel_widths" entry of the file, None when
                it is missing or null (the app writes null when it does
                not know the widths).
        Outputs: (plot panel width, signal list panel width) in pixels,
            or () when they are missing or not two positive whole numbers
            (reported unless missing; the widths are then left as they
            are).
        """
        # LLFR-00230: the panel widths of the file.
        if widths_value is None:
            return ()
        width_list = []
        if isinstance(widths_value, dict):
            for key_str in (PLOT_PANEL_KEY_STR, SIGNAL_LIST_PANEL_KEY_STR):
                width_value = widths_value.get(key_str)
                if (isinstance(width_value, int)
                        and not isinstance(width_value, bool)
                        and width_value > 0):
                    width_list.append(int(width_value))
        if len(width_list) == 2:
            return tuple(width_list)
        self.report.add_replaced(
            f"Panel widths {describe_value(widths_value)} are not two "
            f"positive whole numbers of pixels; the panels kept their "
            f"widths.")
        return ()

    def rebuild(self, layout_dict: dict,
                synthetic_signal_builder=None) -> LayoutResult:
        """Rebuild the whole layout of a file in the workspace.

        Inputs:
            layout_dict: the content of the file (parse_layout_text).
            synthetic_signal_builder: optional function taking (entry
                list, report) that creates the synthetic signals before
                the plots are rebuilt and adds their names to
                signal_dict (LLFR-00262, issue #110); None does nothing.
        Outputs: the LayoutResult to apply to the view.
        """
        # LLFR-00262: the synthetic signals come first (issue #110).
        if synthetic_signal_builder is not None:
            synthetic_signal_builder(synthetic_signal_entry_list(layout_dict),
                                     self.report)
        tab_entry_list = layout_dict.get(TABS_KEY_STR)
        if not isinstance(tab_entry_list, list):
            # LLFR-00235: no list of tabs; nothing to add.
            self.report.add_not_rebuilt(
                f"Tabs: the entry \"{TABS_KEY_STR}\" is not a list, so no "
                f"tab was added.")
            tab_entry_list = []
        # LLFR-00229: with no plot in any current tab, the tabs of the
        # file replace the current ones; else they are added after them.
        tabs_replaced_b = (bool(tab_entry_list)
                           and not self.workspace.has_plots())
        if tabs_replaced_b:
            self.workspace.remove_all_tabs()
        first_tab_id_i = self.rebuild_tabs(tab_entry_list)
        # LLFR-00230, LLFR-00233: the vertical markers of the file.
        self.rebuild_vertical_markers(
            list_entry(layout_dict, VERTICAL_MARKERS_KEY_STR))
        # LLFR-00234: the time range, limited to the data file.
        time_range_tuple = self.time_range(
            layout_dict.get(TIME_RANGE_KEY_STR))
        # LLFR-00230: the grid and the panel widths.
        # A missing "grid" or "panel_widths" entry leaves the grid or the
        # widths as they are, without a report; a value that is there but
        # cannot be used is reported (LLFR-00235).
        grid_shown_b = None
        if GRID_KEY_STR in layout_dict:
            grid_shown_b = self.grid_setting(layout_dict[GRID_KEY_STR])
        panel_width_tuple = self.panel_widths(
            layout_dict.get(PANEL_WIDTHS_KEY_STR))
        return LayoutResult(self.report, first_tab_id_i, time_range_tuple,
                            grid_shown_b, panel_width_tuple,
                            tabs_replaced_b)


def rebuild_layout(workspace, layout_dict: dict, signal_dict: dict,
                   time_array, synthetic_signal_builder=None):
    """Rebuild the layout of a file in a workspace.

    Inputs:
        workspace: the Workspace to add the layout to.
        layout_dict: the content of the file (parse_layout_text).
        signal_dict: signal name -> numpy array of the open data file.
        time_array: the values of the time signal, in seconds.
        synthetic_signal_builder: optional function of LayoutBuilder.
            rebuild for the synthetic signals (issue #110).
    Outputs: the LayoutResult.
    """
    # LLFR-00229 to LLFR-00235: see LayoutBuilder.
    return LayoutBuilder(workspace, signal_dict, time_array).rebuild(
        layout_dict, synthetic_signal_builder)
