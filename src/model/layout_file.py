"""Layout files: save and load the layout of the plots (HLFR-00049 to
HLFR-00052).

A layout file is a JSON text file (HLFR-00051, LLFR-00227) that holds
what the plot panel shows and how (LLFR-00225): the tabs, their plots,
the curves of each plot with their color and width, the pinned data
tips and the delta markers of each plot, the flags, the
areas, the shared time range, the grid setting and the panel widths.
It holds no path or name of the data file, no undo or redo history, no
active plot tool, no search text and no text notes (LLFR-00226).

Plots, curves, data tips and delta markers are found by their position
in the file: a plot is an entry of the ``plots`` list of its tab, and
its curves, data tips and delta markers are entries of its own lists.
No internal id of the app is written.

An example of a layout file::

    {
      "format": "plot_tool layout",
      "version": 3,
      "shown_tab": 0,
      "time_range": {"start": 0.5, "end": 2.25},
      "grid": true,
      "panel_widths": {"plot_panel": 900, "signal_list_panel": 300},
      "flags": [{"name": "Flag 1", "time": 1.0, "color": "#ff8000"}],
      "areas": [{"name": "Area 1", "start": 0.75, "end": 1.25,
                 "color": "#ff8000"}],
      "synthetic_signals": [],
      "tabs": [
        {"name": "Tab 1",
         "plots": [
           {"curves": [{"signal": "Speed", "color": "#1f77b4",
                        "width": 1}],
            "data_tips": [{"signal": "Speed", "time": 1.5,
                           "label_position": {"right_points": 20.0,
                                              "up_points": 15.0}}],
            "delta_markers": [{"name": "Delta X 1",
                               "kind": "delta_x",
                               "first_point": {"signal": "Speed",
                                               "time": 0.5},
                               "second_point": {"signal": "Speed",
                                                "time": 2.0},
                               "color": "#ff8000"}]}]}]
    }

(The app writes every value on its own line, indented by 2 spaces.)
Colors of flags, delta markers and areas are written as "#rrggbb" in
lowercase (LLFR-00225 items 6, 8 and 11). A value whose key is missing
from the file, for example the color of a delta marker, gets its default
value and is listed in the report as a replaced value (LLFR-01200). A
file of an earlier version is read with the same rules (LLFR-00228):
for example, its flags, saved under the key ``vertical_markers`` in
version 1, are not rebuilt.

A ``label_position`` of ``null`` means that the data tip was never
moved, so the app places its label beside the point by itself.

The list ``synthetic_signals`` holds the synthetic signals of LLFR-00225
item 10 that are not FFT signals (LLFR-00283), in creation order, as the
entries described in model.synthetic_signals (the same entries "Copy
equation" puts on the clipboard, LLFR-00279). On load, the entries are
handed, unchanged, to a builder function (``synthetic_signal_builder``
of ``rebuild_layout``) that keeps the current synthetic signals,
creates those of the file (reusing an identical signal of the same name,
renaming one whose name is in use, LLFR-00282) and fills the report
(LLFR-00262); the plots are then rebuilt with the signals of the data
file and the synthetic signals, a renamed one under its new name.

Frequency plots, with their curves, data tips and delta markers, are
not saved (LLFR-00283): a tab keeps only its time plots. On load, only
the tabs of the file that are left with at least one plot are created
(LLFR-00231, LLFR-00229).

Loading rebuilds the layout in a Workspace with the signals of the open
data file (LLFR-00229 to LLFR-00235) and collects in a LayoutReport what
could not be rebuilt or was changed (LLFR-00237). A hand-edited file of
the right format but with wrong types never raises: such values are
replaced or skipped and named in the report.

This module holds no Qt code (COR-00009).
"""

import json
import math
import os
import re

import numpy as np

from model.curve_colors import hex_color_or_none, is_far_from_marker_color
from model.message_lists import sections_text
from model.workspace import (
    AUTOMATIC_LABEL_OFFSET_TUPLE, DEFAULT_AREA_COLOR_STR,
    DEFAULT_DELTA_MARKER_COLOR_STR, DEFAULT_FLAG_COLOR_STR,
    DEFAULT_MATRIX_COLUMNS_I, DEFAULT_MATRIX_ROWS_I,
    DEFAULT_WIDTH_I, DELTA_X_KIND_STR,
    DELTA_Y_KIND_STR, PRESET_WIDTH_TUPLE, delta_value_zero_b,
    first_panel_width_i, is_matrix_size, spans_overlap_b)

# LLFR-00228, LLFR-00471: the identification of a layout file; the
# version is 3, whose signal names carry the file prefix (LLFR-00948).
LAYOUT_FORMAT_STR = "plot_tool layout"
LAYOUT_VERSION_I = 3
# LLFR-00963: the first version whose names carry the file prefix, and
# the prefix that the names of an older file are read with.
PREFIXED_NAMES_VERSION_I = 3
OLDER_LAYOUT_PREFIX_STR = "file1_"
# LLFR-00225 item 10: the keys of the name and the sources of a
# synthetic signal entry (model.synthetic_signals).
SYNTHETIC_NAME_KEY_STR = "name"
SYNTHETIC_SOURCES_KEY_STR = "signals"
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
# LLFR-00225 item 9, LLFR-01214: whether the main window shows its signal
# list panel.
MAIN_PANEL_SHOWN_KEY_STR = "signal_list_panel_shown"
# LLFR-01081, LLFR-01146: the largest size of a Qt window (QWIDGETSIZE_MAX),
# the limit of every window position, size and panel width of a file.
MAXIMUM_WINDOW_PIXELS_I = 16777215
PLOT_PANEL_KEY_STR = "plot_panel"
SIGNAL_LIST_PANEL_KEY_STR = "signal_list_panel"
# LLFR-00225 item 6: the list of flags, each with "name", "time" and
# "color" ("#rrggbb", COLOR_KEY_STR). A file without it has no flag.
FLAGS_KEY_STR = "flags"
# LLFR-00225 item 11: the list of areas, each with "name", "start",
# "end" (START_KEY_STR, END_KEY_STR) and "color" ("#rrggbb",
# COLOR_KEY_STR, LLFR-00351). A file without it has no area.
AREAS_KEY_STR = "areas"
SYNTHETIC_SIGNALS_KEY_STR = "synthetic_signals"
# LLFR-00225 items 12 to 15, LLFR-01075: the keys of the undocked state,
# the window, its signal list panel and the plot matrix of a tab.
UNDOCKED_KEY_STR = "undocked"
WINDOW_KEY_STR = "window"
# LLFR-00225 item 16, LLFR-01159: the number of the undocked window of a
# tab, the same for the tabs that share a window.
WINDOW_NUMBER_KEY_STR = "window_number"
X_KEY_STR = "x"
Y_KEY_STR = "y"
HEIGHT_KEY_STR = "height"
SHOWN_KEY_STR = "shown"
PLOT_MATRIX_KEY_STR = "plot_matrix"
ROWS_KEY_STR = "rows"
COLUMNS_KEY_STR = "columns"
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
# LLFR-01227: the heading of the data files of the layout file that are
# not open.
DATA_FILES_HEADING_STR = "Data files not opened:"
SYNTHETIC_HEADING_STR = "Synthetic signals not created:"
RENAMED_HEADING_STR = "Renamed:"
# LLFR-00237: how a renamed tab or synthetic signal is listed.
RENAMED_TAB_LINE_STR = "Tab \"{saved}\" \u2192 \"{new}\""
RENAMED_SIGNAL_LINE_STR = "Synthetic signal \"{saved}\" \u2192 \"{new}\""
MISSING_HEADING_STR = "Signals not in the data file:"
NOT_REBUILT_HEADING_STR = "Not rebuilt:"
TIME_RANGE_HEADING_STR = "Time range:"
REPLACED_HEADING_STR = "Values replaced:"
# LLFR-01200: the reason given for a value whose key is missing.
MISSING_REASON_STR = "is missing"
# LLFR-01200, LLFR-00235: what saved_color found instead of a color.
COLOR_MISSING_STR = "missing"
COLOR_UNUSABLE_STR = "unusable"


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
        renamed_line_list: tabs and synthetic signals of the file given
            another name because theirs was in use (LLFR-00235,
            LLFR-00282).
        missing_signal_list: the signals not in the data file, each named
            once, in the order they were met (LLFR-00231).
        not_rebuilt_line_list: data tips, flags, areas, delta
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
        self.renamed_line_list = []
        self.missing_signal_list = []
        self.not_rebuilt_line_list = []
        self.time_range_line_list = []
        self.replaced_line_list = []
        # LLFR-01227: the data files of the file that are not open.
        self.data_file_line_list = []

    def add_data_file(self, line_str: str) -> None:
        """Note a data file of the layout file that is not open.

        Inputs:
            line_str: the text of the entry, with the path and reason.
        Outputs: none.
        """
        # LLFR-01227: listed under "Data files not opened:".
        self.data_file_line_list.append(str(line_str))

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
        # LLFR-00262, LLFR-00237: filled by the synthetic builder.
        self.synthetic_line_list.append(str(line_str))

    def add_renamed(self, line_str: str) -> None:
        """Note a tab or synthetic signal of the file that was renamed.

        Inputs:
            line_str: the text of the entry, "<saved> \u2192 <new>".
        Outputs: none.
        """
        # LLFR-00237: each renamed tab and synthetic signal, with its
        # saved and its new name.
        self.renamed_line_list.append(str(line_str))

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
        return not (self.data_file_line_list
                    or self.synthetic_line_list or self.renamed_line_list
                    or self.missing_signal_list
                    or self.not_rebuilt_line_list
                    or self.time_range_line_list or self.replaced_line_list)

    def section_list(self) -> list:
        """Return the non-empty sections of the report.

        Inputs: none.
        Outputs: a list of tuples (heading_str, entry list), in the order
            of LLFR-00237.
        """
        # LLFR-00237: synthetic signals, missing signals, items not
        # rebuilt, the time range and the replaced values; the renamed
        # tabs and synthetic signals.
        # LLFR-01227: the data files that are not open come first, as
        # they explain the signals missing below.
        section_list = [
            (DATA_FILES_HEADING_STR, self.data_file_line_list),
            (SYNTHETIC_HEADING_STR, self.synthetic_line_list),
            (RENAMED_HEADING_STR, self.renamed_line_list),
            (MISSING_HEADING_STR, self.missing_signal_list),
            (NOT_REBUILT_HEADING_STR, self.not_rebuilt_line_list),
            (TIME_RANGE_HEADING_STR, self.time_range_line_list),
            (REPLACED_HEADING_STR, self.replaced_line_list)]
        return [(heading_str, list(entry_list))
                for heading_str, entry_list in section_list if entry_list]

    def text(self) -> str:
        """Return the report as the text of the information box.

        Inputs: none.
        Outputs: the text, each heading followed by its entries, numbered
            when the report holds two or more entries (LLFR-00987,
            LLFR-00988); "" when the report is empty.
        """
        # LLFR-00237: one box that lists everything; LLFR-00980 to
        # LLFR-00989: in the shared format of the boxes with a list.
        if self.is_empty():
            return ""
        return sections_text(self.section_list())


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
        # LLFR-01214: whether the main window shows its signal list
        # panel, None when the file does not say.
        self.main_panel_shown_b = None


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


def saved_color(entry_dict: dict, default_color_str: str) -> tuple:
    """Read the saved color of a flag, a delta marker or an area.

    Inputs:
        entry_dict: the entry of the flag or area in the file.
        default_color_str: the color of a new item of that kind
            (DEFAULT_FLAG_COLOR_STR, DEFAULT_DELTA_MARKER_COLOR_STR or
            DEFAULT_AREA_COLOR_STR).
    Outputs: a tuple (color_str, state_str): the lowercase "#rrggbb"
        color to use, and "" when it is the saved color,
        COLOR_MISSING_STR when the color is missing, or
        COLOR_UNUSABLE_STR when a saved value that is not written as
        "#rrggbb" was replaced by the default color.
    """
    # LLFR-00815, LLFR-00822, LLFR-00726, LLFR-01200: a missing color is
    # the default color, listed as a replaced value.
    if COLOR_KEY_STR not in entry_dict:
        return default_color_str, COLOR_MISSING_STR
    # LLFR-00393, LLFR-00410, LLFR-00319: a "#rrggbb" color, in
    # uppercase or lowercase, is used as it is; anything else is
    # replaced by the default color and reported.
    color_str = hex_color_or_none(entry_dict.get(COLOR_KEY_STR))
    if color_str is None:
        return default_color_str, COLOR_UNUSABLE_STR
    return color_str, ""


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
    # LLFR-00225 item 8: the name (LLFR-00427), the kind, the two points
    # and the color ("#rrggbb" in lowercase, LLFR-00409) of each delta
    # marker.
    delta_marker_list = [
        {NAME_KEY_STR: delta_marker.name_str,
         KIND_KEY_STR: KIND_NAME_DICT[delta_marker.kind_str],
         FIRST_POINT_KEY_STR: point_entry(delta_marker.first_point_tuple),
         SECOND_POINT_KEY_STR: point_entry(delta_marker.second_point_tuple),
         COLOR_KEY_STR: delta_marker.color_str.lower()}
        for delta_marker in plot.delta_marker_list]
    # LLFR-00226: the text notes of the plot (Plot.text_note_list) and
    # its arrows (Plot.arrow_list) are never written to the layout file.
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
            (LLFR-00225 item 10), already as JSON values, in creation
            order (SyntheticSignalStore.layout_entries).
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
    # LLFR-00225 item 9, LLFR-01211: whether the main window shows its
    # signal list panel.
    layout_dict[MAIN_PANEL_SHOWN_KEY_STR] = bool(
        getattr(workspace, "main_panel_shown_b", True))
    # LLFR-00225 item 6: under "flags", each flag with its name, time
    # and color ("#rrggbb" in lowercase).
    layout_dict[FLAGS_KEY_STR] = [
        {NAME_KEY_STR: marker.name_str, TIME_KEY_STR: float(marker.time_s),
         COLOR_KEY_STR: marker.color_str}
        for marker in workspace.marker_list]
    # LLFR-00225 item 11: each area, with its name, start and end time
    # and color ("#rrggbb" in lowercase).
    layout_dict[AREAS_KEY_STR] = [
        {NAME_KEY_STR: area.name_str, START_KEY_STR: float(area.start_s),
         END_KEY_STR: float(area.end_s), COLOR_KEY_STR: area.color_str}
        for area in workspace.area_list]
    # LLFR-00225 item 10, LLFR-00262: the synthetic signals.
    layout_dict[SYNTHETIC_SIGNALS_KEY_STR] = list(synthetic_signal_list)
    # LLFR-00225 items 1 and 2: the tabs in order, each with its time
    # plots from top to bottom; LLFR-00283: no frequency plot, but a tab
    # of only frequency plots is still saved.
    # LLFR-00225 item 16: the undocked windows numbered from 1, in the
    # tab order (LLFR-01091).
    window_number_dict = {window_id_i: number_i + 1
                          for number_i, window_id_i
                          in enumerate(workspace.window_id_list())}
    layout_dict[TABS_KEY_STR] = [
        tab_entry(tab, workspace.main_panel_width_i,
                  window_number_dict.get(tab.window_id_i, 0))
        for tab in workspace.tab_list]
    return layout_dict


def tab_entry(tab, main_panel_width_i: int = 0,
              window_number_i: int = 0) -> dict:
    """Return the file entry of a tab.

    Inputs:
        tab: a model Tab.
        main_panel_width_i: width of the main window's signal list
            panel, in pixels, used as the first width of a panel that
            was never shown (LLFR-01051).
        window_number_i: the number of its undocked window in the file,
            from 1 (LLFR-00225 item 16); 0 for a docked tab.
    Outputs: a dict with its name, whether it is undocked, its plot
        matrix and its time plots, and, for an undocked tab, its window
        and the window's signal list panel.
    """
    # LLFR-00225 items 1 and 2: the name and the time plots, in fill
    # order; LLFR-00283: no frequency plot.
    entry_dict = {NAME_KEY_STR: tab.name_str,
                  # LLFR-00225 item 12: whether the tab is undocked.
                  UNDOCKED_KEY_STR: bool(tab.undocked_b),
                  # LLFR-00225 item 15: the plot matrix of the tab.
                  PLOT_MATRIX_KEY_STR: {
                      ROWS_KEY_STR: int(tab.row_count_i),
                      COLUMNS_KEY_STR: int(tab.column_count_i)}}
    if tab.undocked_b:
        # LLFR-00225 item 13, LLFR-01075: the window's position and size
        # in whole desktop pixels.
        if len(tab.window_tuple) == 4:
            x_i, y_i, width_i, height_i = (int(value_i) for value_i
                                           in tab.window_tuple)
            entry_dict[WINDOW_KEY_STR] = {
                X_KEY_STR: x_i, Y_KEY_STR: y_i, WIDTH_KEY_STR: width_i,
                HEIGHT_KEY_STR: height_i}
        else:
            entry_dict[WINDOW_KEY_STR] = None
        # LLFR-00225 item 16, LLFR-01159: the tabs that share a window
        # have the same number; their order in the file is their order
        # in the window.
        entry_dict[WINDOW_NUMBER_KEY_STR] = max(int(window_number_i), 1)
        # LLFR-00225 item 14: whether its panel is shown, and its width;
        # a panel never shown gets the width it would first get.
        panel_width_i = int(tab.panel_width_i)
        if panel_width_i < 1:
            window_width_i = (int(tab.window_tuple[2])
                              if len(tab.window_tuple) == 4 else 0)
            panel_width_i = first_panel_width_i(main_panel_width_i,
                                                window_width_i)
        entry_dict[SIGNAL_LIST_PANEL_KEY_STR] = {
            SHOWN_KEY_STR: bool(tab.panel_shown_b),
            WIDTH_KEY_STR: panel_width_i}
    entry_dict[PLOTS_KEY_STR] = [plot_entry(plot) for plot in tab.plot_list
                                 if not plot.is_frequency_plot()]
    return entry_dict


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
    # LLFR-00228: a whole number, also when hand-edited as 1.0; any lower
    # version, 0 included, is read with the current rules.
    version_i = None
    if isinstance(version_value, int) and not isinstance(version_value,
                                                         bool):
        version_i = int(version_value)
    elif (isinstance(version_value, float) and math.isfinite(version_value)
          and version_value.is_integer()):
        version_i = int(version_value)
    if (layout_dict.get(FORMAT_KEY_STR) != LAYOUT_FORMAT_STR
            or version_i is None):
        raise LayoutFileError(UNREADABLE_MESSAGE_STR.format(
            path=path_str, reason=NOT_LAYOUT_REASON_STR))
    # LLFR-00228: a later format may hold entries this app cannot read.
    if version_i > LAYOUT_VERSION_I:
        raise LayoutFileError(UNREADABLE_MESSAGE_STR.format(
            path=path_str, reason=NEWER_VERSION_REASON_STR.format(
                version=version_i, supported=LAYOUT_VERSION_I)))
    # LLFR-00963, LLFR-00472: the names of an older file mean file 1.
    if version_i < PREFIXED_NAMES_VERSION_I:
        prefix_older_names(layout_dict)
    return layout_dict


def prefixed_older_name(name_value):
    """Return a signal name of an older layout file as read now.

    Inputs:
        name_value: a value saved as a signal name.
    Outputs: ``file1_`` followed by the name for a text (LLFR-00963);
        any other value unchanged, so that the load report names it as
        it would without this reading.
    """
    # LLFR-00963: `Speed` means `file1_Speed`.
    if isinstance(name_value, str):
        return OLDER_LAYOUT_PREFIX_STR + name_value
    return name_value


def prefix_older_point(entry) -> None:
    """Prefix the signal name of a data tip or delta marker point.

    Inputs:
        entry: a data tip entry or a point entry of a delta marker, as
            read by json; any value is accepted.
    Outputs: none; the "signal" value of a dict is changed in place.
    """
    # LLFR-00963: the names of the pinned data tips and delta markers.
    if isinstance(entry, dict) and SIGNAL_KEY_STR in entry:
        entry[SIGNAL_KEY_STR] = prefixed_older_name(entry[SIGNAL_KEY_STR])


def prefix_older_names(layout_dict: dict) -> None:
    """Read the signal names of an older layout file as names of file 1.

    Inputs:
        layout_dict: the content of a layout file whose version is lower
            than 3 (LLFR-00471); hand-edited values are accepted.
    Outputs: none; every signal name of its curves, pinned data tips,
        delta markers and synthetic signal entries (the names of the
        synthetic signals and of the signals they are computed from) is
        given the prefix ``file1_`` in place (LLFR-00963). The names are
        then used as if they had been saved so, so the load report does
        not list them (LLFR-00964).
    """
    # LLFR-00963: the curves, data tips and delta markers of each plot.
    for tab_entry in list_entry(layout_dict, TABS_KEY_STR):
        for plot_entry_value in list_entry(tab_entry, PLOTS_KEY_STR):
            for curve_entry in list_entry(plot_entry_value, CURVES_KEY_STR):
                prefix_older_point(curve_entry)
            for tip_entry in list_entry(plot_entry_value,
                                        DATA_TIPS_KEY_STR):
                prefix_older_point(tip_entry)
            for delta_entry in list_entry(plot_entry_value,
                                          DELTA_MARKERS_KEY_STR):
                if isinstance(delta_entry, dict):
                    prefix_older_point(delta_entry.get(FIRST_POINT_KEY_STR))
                    prefix_older_point(delta_entry.get(SECOND_POINT_KEY_STR))
    # LLFR-00963: the synthetic signals and the signals they come from.
    for signal_entry in list_entry(layout_dict, SYNTHETIC_SIGNALS_KEY_STR):
        if not isinstance(signal_entry, dict):
            continue
        if SYNTHETIC_NAME_KEY_STR in signal_entry:
            signal_entry[SYNTHETIC_NAME_KEY_STR] = prefixed_older_name(
                signal_entry[SYNTHETIC_NAME_KEY_STR])
        source_value = signal_entry.get(SYNTHETIC_SOURCES_KEY_STR)
        if isinstance(source_value, list):
            signal_entry[SYNTHETIC_SOURCES_KEY_STR] = [
                prefixed_older_name(name_value)
                for name_value in source_value]


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
    # LLFR-00262: the synthetic signals of the file, in creation order.
    return list_entry(layout_dict, SYNTHETIC_SIGNALS_KEY_STR)


# ----------------------------------------------------------------------
# Rebuilding (LLFR-00229 to LLFR-00235)
# ----------------------------------------------------------------------

class LayoutBuilder:
    """Rebuilds the layout of a file in a workspace.

    Inputs:
        workspace: the Workspace to add the layout to.
        signal_dict: signal name -> numpy array of the open data file;
            the builder copies it and adds the synthetic signals the
            file can draw (LLFR-00230, LLFR-00262).
        time_array: the values of the time signal, in seconds, or a
            function that takes a signal name and returns the time
            signal of that signal's data file (LLFR-00912).
        files_range_tuple: the time range of the open data files
            (LLFR-00916); None takes the range of time_array.
        new_window_tuple: (x, y, width, height) that an undock would
            give a new window (LLFR-01016, LLFR-01128), used for an
            unusable saved window (LLFR-01081); () when unknown.
    Attributes:
        report: the LayoutReport being filled.
    """

    def __init__(self, workspace, signal_dict: dict, time_array,
                 files_range_tuple=None, new_window_tuple=()) -> None:
        """Store the workspace and the signals.

        Inputs: see the class docstring.
        Outputs: none.
        """
        # LLFR-00230: the layout is rebuilt with the signals of the open
        # data file.
        self.workspace = workspace
        # LLFR-00230: a copy, so that the synthetic signals of the file
        # are added without changing the data file's dict.
        self.signal_dict = dict(signal_dict)
        # LLFR-00282: signal name of the file -> (name drawn, samples),
        # or None for a synthetic signal of the file not created.
        self.synthetic_name_dict = {}
        # LLFR-00912: each signal has the time signal of its own file.
        if callable(time_array):
            self.time_function = time_array
            self.time_array = None
        else:
            self.time_array = np.asarray(time_array, dtype=float)
            self.time_function = None
        # LLFR-00916, LLFR-00233, LLFR-00234: the time range of the open
        # data files.
        if files_range_tuple is not None:
            self.file_range_tuple = tuple(files_range_tuple)
        elif self.time_array is not None:
            self.file_range_tuple = file_time_range(self.time_array)
        else:
            self.file_range_tuple = ()
        # LLFR-01081: the values of an undock, for unusable values.
        self.new_window_tuple = tuple(int(value_i)
                                      for value_i in new_window_tuple)
        # LLFR-01159: window number of the file -> the first created tab
        # of that window.
        self.window_first_tab_dict = {}
        self.report = LayoutReport()

    def time_of(self, signal_name_str: str):
        """Return the time signal a signal is drawn against.

        Inputs:
            signal_name_str: a signal name of the signal list.
        Outputs: a numpy float array of times, in seconds; empty when
            the time of the signal is not known.
        """
        # LLFR-00912, LLFR-00232: the times of the signal's own file.
        if self.time_function is None:
            return self.time_array
        try:
            return np.asarray(self.time_function(signal_name_str),
                              dtype=float)
        except KeyError:
            return np.asarray([], dtype=float)

    # Signals and points ---------------------------------------------

    def resolve(self, file_name_str: str):
        """Return the signal drawn for a signal name of the file.

        Inputs:
            file_name_str: a signal name as saved in the file.
        Outputs: the name of the signal of the signal list to draw (a
            synthetic signal renamed by LLFR-00282 is drawn under its
            new name), or None when the signal is missing (LLFR-00231,
            LLFR-00262).
        """
        # LLFR-00282: the file's synthetic signals come first, since a
        # saved name equal to a data file signal was renamed.
        if file_name_str in self.synthetic_name_dict:
            used_tuple = self.synthetic_name_dict[file_name_str]
            return used_tuple[0] if used_tuple else None
        if file_name_str in self.signal_dict:
            return file_name_str
        return None

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
        used_name_str = self.resolve(signal_value)
        if used_name_str is None:
            # LLFR-00231, LLFR-00237: named in the missing signals too.
            self.report.add_missing_signal(signal_value)
            return ((), time_s,
                    f"the signal {signal_value} is not in the data file")
        # LLFR-00282: the point is on the signal drawn for that name.
        signal_value = used_name_str
        if not plot.has_signal(signal_value):
            return ((), time_s,
                    f"the signal {signal_value} is not drawn in its plot")
        signal_time_array = self.time_of(signal_value)
        difference_array = np.abs(signal_time_array - time_s)
        if not np.any(np.isfinite(difference_array)):
            return ((), time_s, "the data file has no valid time")
        sample_index_i = int(np.nanargmin(difference_array))
        if difference_array[sample_index_i] > SAMPLE_TIME_TOLERANCE_S:
            return ((), time_s,
                    f"the signal {signal_value} has no sample within 1 "
                    f"microsecond of this time")
        sample_time_s = float(signal_time_array[sample_index_i])
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
            used_name_str = self.resolve(signal_name_str)
            if used_name_str is None:
                self.report.add_missing_signal(signal_name_str)
                continue
            # LLFR-00282: drawn under the name of the signal it uses.
            signal_name_str = used_name_str
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
        if LABEL_POSITION_KEY_STR not in tip_entry_dict:
            # LLFR-01200: a missing position is listed as replaced.
            self.report.add_replaced(
                f"Label position of the data tip at {format_time(time_s)} "
                f"in {owner_str} {MISSING_REASON_STR}; the label is placed "
                f"beside its point.")
            return AUTOMATIC_LABEL_OFFSET_TUPLE
        position_value = tip_entry_dict.get(LABEL_POSITION_KEY_STR)
        if position_value is None:
            # LLFR-00225 item 7: null, a data tip that was never moved.
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
            if delta_value_zero_b(kind_str, point_list[0], point_list[1]):
                # LLFR-00486, LLFR-00237: no delta marker of value zero.
                self.report.add_not_rebuilt(
                    f"{label_str}: its value on the samples of the data "
                    f"file would be zero.")
                continue
            # LLFR-00410: the saved color; LLFR-00822, LLFR-00823: a
            # missing or unusable one is the default color, reported.
            color_str, color_reason_str = saved_color(
                delta_entry, DEFAULT_DELTA_MARKER_COLOR_STR)
            # LLFR-00430: the saved name. LLFR-00857: a missing name
            # gets the name of a new delta marker, reported (LLFR-01200).
            # LLFR-00858: so does a name that is empty or not a text.
            name_value = delta_entry.get(NAME_KEY_STR)
            name_usable_b = (isinstance(name_value, str)
                             and bool(name_value.strip()))
            if name_usable_b:
                name_str = name_value.strip()
            else:
                name_str = self.workspace.take_delta_marker_name(kind_str)
            # LLFR-00232: both points are placed on their samples.
            plot.add_delta_marker(kind_str, point_list[0], point_list[1],
                                  color_str, name_str)
            if NAME_KEY_STR not in delta_entry:
                # LLFR-00857, LLFR-01200: a missing name is listed with
                # the replaced values.
                self.report.add_replaced(
                    f"Name of the {label_str} {MISSING_REASON_STR}; "
                    f"replaced by \"{name_str}\".")
            elif not name_usable_b:
                # LLFR-00859, LLFR-00235, LLFR-00237: the replaced name
                # is listed with the replaced values.
                self.report.add_replaced(
                    f"Name {describe_value(name_value)} of the "
                    f"{label_str} is empty or not a text; replaced by "
                    f"\"{name_str}\".")
            if color_reason_str == COLOR_MISSING_STR:
                # LLFR-00822, LLFR-01200, LLFR-00237: a missing color is
                # listed as replaced by the default color.
                self.report.add_replaced(
                    f"Color of the {label_str} {MISSING_REASON_STR}; "
                    f"replaced by \"{DEFAULT_DELTA_MARKER_COLOR_STR}\".")
            elif color_reason_str:
                # LLFR-00824, LLFR-00235, LLFR-00237: a color not written
                # as "#rrggbb" is replaced by the default color.
                self.report.add_replaced(
                    f"Color {describe_value(delta_entry[COLOR_KEY_STR])} "
                    f"of the {label_str} is not written as #rrggbb; "
                    f"replaced by \"{DEFAULT_DELTA_MARKER_COLOR_STR}\".")

    # Plots and tabs -------------------------------------------------

    def rebuild_plot(self, tab, plot_entry_value, owner_str: str) -> bool:
        """Create one saved plot in a tab, with its curves and items.

        Inputs:
            tab: the model Tab, or None for a tab that is not created
                (then no curve of the plot can be drawn, LLFR-00231).
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
            # LLFR-00488, HLFR-00018: no plot beyond the slots of the
            # tab's plot matrix.
            self.report.add_not_rebuilt(
                f"{owner_str[0].upper()}{owner_str[1:]}: not created, "
                f"because the {tab.row_count_i} \u00d7 "
                f"{tab.column_count_i} plot matrix of the tab holds at "
                f"most {tab.slot_count()} plots.")
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
            replaced and listed as renamed (LLFR-00237).
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
                # another tab has is replaced, and reported as renamed
                # (LLFR-00237).
                if self.workspace.is_tab_name_taken(stripped_name_str):
                    self.report.add_renamed(RENAMED_TAB_LINE_STR.format(
                        saved=stripped_name_str,
                        new=self.workspace.next_tab_name()))
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

    def tab_will_hold_plot(self, tab_entry) -> bool:
        """Tell whether a saved tab will hold a plot once it is rebuilt.

        Inputs:
            tab_entry: the tab entry of the file.
        Outputs: True when one of its plots has a curve whose signal can
            be drawn, which is exactly when rebuild_plot creates that
            plot (the first plot of a new tab is never over the limit).
        """
        # LLFR-00231: only tabs left with a plot are created.
        for plot_entry_value in list_entry(tab_entry, PLOTS_KEY_STR):
            for curve_entry in list_entry(plot_entry_value, CURVES_KEY_STR):
                name_value = (curve_entry.get(SIGNAL_KEY_STR)
                              if isinstance(curve_entry, dict) else None)
                if isinstance(name_value, str) and (
                        self.resolve(name_value) is not None):
                    return True
        return False

    def report_skipped_tab(self, tab_entry, tab_number_i: int) -> None:
        """Report what the plots of a tab that is not created lose.

        Inputs:
            tab_entry: the tab entry of the file.
            tab_number_i: its position in the file, from 1.
        Outputs: none. The missing signals, the plots and their data
            tips and delta markers are reported as for any plot that is
            not created; the tab itself is not listed (LLFR-00237).
        """
        # LLFR-00231, LLFR-00237: the missing signals explain the tab.
        name_value = (tab_entry.get(NAME_KEY_STR)
                      if isinstance(tab_entry, dict) else None)
        if isinstance(name_value, str) and name_value.strip():
            tab_label_str = f"tab \"{name_value.strip()}\""
        else:
            tab_label_str = f"tab {tab_number_i} of the file"
        for plot_index_i, plot_entry_value in enumerate(
                list_entry(tab_entry, PLOTS_KEY_STR)):
            # LLFR-00231: rebuild_plot reports and creates no plot, since
            # none of its curves can be drawn.
            self.rebuild_plot(None, plot_entry_value,
                              f"plot {plot_index_i + 1} of {tab_label_str}")

    def rebuild_tabs(self, tab_entry_list: list) -> int:
        """Create the saved tabs, with their plots, after the current ones.

        Inputs:
            tab_entry_list: the "tabs" list of the file.
        Outputs: the id of the first created tab, -1 when none.
        """
        # LLFR-00235: the valid names of the tabs created so far.
        file_name_set = set()
        first_tab_id_i = -1
        for tab_index_i, tab_entry in enumerate(tab_entry_list):
            if not self.tab_will_hold_plot(tab_entry):
                # LLFR-00231: a tab left with no plot is not created; what
                # its plots lose is still reported, but not the tab itself
                # (LLFR-00237).
                self.report_skipped_tab(tab_entry, tab_index_i + 1)
                continue
            # LLFR-00235, LLFR-00210: a name that cannot be used is
            # replaced by the next default name.
            name_str = self.tab_name(tab_entry, tab_index_i + 1,
                                     file_name_set)
            if name_str:
                tab = self.workspace.add_named_tab(name_str)
            else:
                tab = self.workspace.add_tab()
            # LLFR-01123 to LLFR-01126: the saved plot matrix, before the
            # plots, so that it limits them (LLFR-00488).
            self.apply_plot_matrix(tab, tab_entry)
            # LLFR-01076, LLFR-01077: docked or undocked, with its window.
            self.apply_window(tab, tab_entry)
            if first_tab_id_i < 0 and not tab.undocked_b:
                # LLFR-00477: the first docked tab added is shown.
                first_tab_id_i = tab.tab_id_i
            # LLFR-00230: the plots in the fill order.
            for plot_index_i, plot_entry_value in enumerate(
                    list_entry(tab_entry, PLOTS_KEY_STR)):
                owner_str = (f"plot {plot_index_i + 1} of tab "
                             f"\"{tab.name_str}\"")
                self.rebuild_plot(tab, plot_entry_value, owner_str)
        return first_tab_id_i

    def apply_plot_matrix(self, tab, tab_entry) -> None:
        """Give a created tab its saved plot matrix.

        Inputs:
            tab: the new model Tab.
            tab_entry: its entry of the file.
        Outputs: none. A missing matrix (LLFR-01124, LLFR-01200) or an
            unusable one (LLFR-01125, LLFR-01126) gives the default and
            is reported.
        """
        if not isinstance(tab_entry, dict):
            return
        if PLOT_MATRIX_KEY_STR not in tab_entry:
            # LLFR-01124, LLFR-01200: the default 5 x 1 matrix, listed as
            # a replaced value; the new tab already has it.
            self.report.add_replaced(
                f"Plot matrix of tab \"{tab.name_str}\" "
                f"{MISSING_REASON_STR}; replaced by {DEFAULT_MATRIX_ROWS_I} "
                f"\u00d7 {DEFAULT_MATRIX_COLUMNS_I}.")
            return
        matrix_value = tab_entry[PLOT_MATRIX_KEY_STR]
        if isinstance(matrix_value, dict):
            row_value = matrix_value.get(ROWS_KEY_STR)
            column_value = matrix_value.get(COLUMNS_KEY_STR)
            if is_matrix_size(row_value) and is_matrix_size(column_value):
                # LLFR-01123: the saved matrix.
                tab.row_count_i = int(row_value)
                tab.column_count_i = int(column_value)
                return
        # LLFR-01125, LLFR-01126: the default, as a replaced value.
        tab.row_count_i = DEFAULT_MATRIX_ROWS_I
        tab.column_count_i = DEFAULT_MATRIX_COLUMNS_I
        self.report.add_replaced(
            f"Plot matrix {describe_value(matrix_value)} of tab "
            f"\"{tab.name_str}\" is not a number of rows and a number of "
            f"columns, each a whole number from 1 to 10; replaced by "
            f"{DEFAULT_MATRIX_ROWS_I} \u00d7 {DEFAULT_MATRIX_COLUMNS_I}.")

    def report_window_value(self, tab, what_str: str, value,
                            replacement_str: str) -> None:
        """Report an unusable window value of an undocked tab.

        Inputs:
            tab: the model Tab.
            what_str: what the value is, for example "Window position".
            value: the saved value.
            replacement_str: what replaced it.
        Outputs: none.
        """
        # LLFR-01082: listed as a replaced value.
        self.report.add_replaced(
            f"{what_str} {describe_value(value)} of tab \"{tab.name_str}\" "
            f"cannot be used; replaced by {replacement_str}.")

    def apply_window(self, tab, tab_entry) -> None:
        """Make a created tab docked or undocked, as the file saved it.

        Inputs:
            tab: the new model Tab, docked.
            tab_entry: its entry of the file.
        Outputs: none. An undocked tab gets the saved window and panel,
            each unusable value replaced as an undock would set it
            (LLFR-01081) and reported (LLFR-01082).
        """
        if not isinstance(tab_entry, dict):
            return
        if UNDOCKED_KEY_STR not in tab_entry:
            # LLFR-01077, LLFR-01200: a tab with no entry is docked, and
            # the missing value is listed as replaced.
            self.report.add_replaced(
                f"Undocked value of tab \"{tab.name_str}\" "
                f"{MISSING_REASON_STR}; the tab was docked.")
            return
        undocked_value = tab_entry.get(UNDOCKED_KEY_STR)
        # LLFR-01077: a tab saved as docked is docked.
        if undocked_value is False:
            return
        if undocked_value is not True:
            # LLFR-00235: neither true nor false; the tab stays docked.
            self.report.add_replaced(
                f"Undocked value {describe_value(undocked_value)} of tab "
                f"\"{tab.name_str}\" is neither true nor false; the tab "
                f"was docked.")
            return
        if self.joins_window(tab_entry):
            # LLFR-01159: the window values of the first tab of its
            # window are used, so this tab's own are not read.
            self.place_in_window(tab, tab_entry, ())
            return
        default_tuple = self.new_window_tuple
        window_value = tab_entry.get(WINDOW_KEY_STR)
        window_dict = window_value if isinstance(window_value, dict) else {}
        # LLFR-01075, LLFR-01081: whole numbers that Qt can take, sizes of
        # 1 pixel or more.
        position_list = [window_dict.get(X_KEY_STR),
                         window_dict.get(Y_KEY_STR)]
        size_list = [window_dict.get(WIDTH_KEY_STR),
                     window_dict.get(HEIGHT_KEY_STR)]
        if all(is_window_coordinate(value) for value in position_list):
            position_tuple = tuple(int(value) for value in position_list)
        else:
            position_tuple = tuple(default_tuple[:2])
            self.report_window_value(
                tab, "Window position", window_value,
                "the position of a new undocked window")
        if all(is_window_length(value) for value in size_list):
            size_tuple = tuple(int(value) for value in size_list)
        else:
            size_tuple = tuple(default_tuple[2:])
            self.report_window_value(
                tab, "Window size", window_value,
                "the size of a new undocked window")
        window_tuple = position_tuple + size_tuple
        if len(window_tuple) != 4:
            window_tuple = ()
        panel_value = tab_entry.get(SIGNAL_LIST_PANEL_KEY_STR)
        panel_dict = panel_value if isinstance(panel_value, dict) else {}
        shown_value = panel_dict.get(SHOWN_KEY_STR)
        width_value = panel_dict.get(WIDTH_KEY_STR)
        if isinstance(shown_value, bool):
            shown_b = shown_value
        else:
            # LLFR-01081, LLFR-01050: hidden, as after an undock.
            shown_b = False
            self.report_window_value(tab, "Signal list panel state",
                                     shown_value, "hidden")
        if is_window_length(width_value):
            width_i = int(width_value)
        else:
            # LLFR-01081, LLFR-01051: the first width of a new panel.
            width_i = 0
            self.report_window_value(
                tab, "Signal list panel width", width_value,
                "the width a new panel gets when it is first shown")
        self.place_in_window(tab, tab_entry, (window_tuple, shown_b,
                                              width_i))

    def joins_window(self, tab_entry) -> bool:
        """Tell whether an undocked tab joins a window created before.

        Inputs:
            tab_entry: the entry of an undocked tab of the file.
        Outputs: True when its window number is that of a tab created
            earlier in this load (LLFR-01159).
        """
        # LLFR-01159: the same window number, the same window.
        number_value = tab_entry.get(WINDOW_NUMBER_KEY_STR)
        if not (is_whole_number(number_value) and number_value >= 1):
            return False
        first_tab = self.window_first_tab_dict.get(number_value)
        return (first_tab is not None and self.workspace.find_tab(
            first_tab.tab_id_i) is not None and first_tab.undocked_b)

    def place_in_window(self, tab, tab_entry,
                        value_tuple: tuple) -> None:
        """Put an undocked tab of the file in its undocked window.

        Inputs:
            tab: the new model Tab, docked.
            tab_entry: its entry of the file.
            value_tuple: (window_tuple, panel_shown_b, panel_width_i), the
                usable window values of the entry.
        Outputs: none. A tab with the window number of a tab created
            before goes into that tab's window, after its last tab
            (LLFR-01159); a tab with no window number, or an unusable
            one, gets a window of its own (LLFR-01160, LLFR-01165).
        """
        number_value = tab_entry.get(WINDOW_NUMBER_KEY_STR)
        if WINDOW_NUMBER_KEY_STR not in tab_entry:
            # LLFR-01160, LLFR-01200: a window of its own; the missing
            # number is listed as a replaced value.
            self.report.add_replaced(
                f"Window number of tab \"{tab.name_str}\" "
                f"{MISSING_REASON_STR}; replaced by a window of its own.")
        elif not (is_whole_number(number_value) and number_value >= 1):
            # LLFR-01165, LLFR-01082: a window of its own, reported.
            self.report_window_value(tab, "Window number", number_value,
                                     "a window of its own")
            number_value = None
        first_tab = self.window_first_tab_dict.get(number_value)
        if number_value is not None and first_tab is not None and (
                self.workspace.find_tab(first_tab.tab_id_i) is not None):
            # LLFR-01159: the window of the first tab of that number,
            # with its values; LLFR-01091: in the file's order.
            last_tab = self.workspace.window_tab_list(
                first_tab.window_id_i)[-1]
            self.workspace.tab_list.remove(tab)
            self.workspace.tab_list.insert(
                self.workspace.tab_list.index(last_tab) + 1, tab)
            tab.copy_window_values(first_tab)
            tab.window_shown_b = False
            return
        # LLFR-01076, LLFR-01160: the tab opens a new undocked window;
        # LLFR-01161: which shows its first tab.
        window_tuple, shown_b, width_i = value_tuple
        self.workspace.tab_list.remove(tab)
        self.workspace.tab_list.append(tab)
        tab.window_id_i = self.workspace.next_window_id_i
        self.workspace.next_window_id_i += 1
        tab.window_shown_b = True
        tab.window_tuple = window_tuple
        tab.panel_shown_b = shown_b
        tab.panel_width_i = width_i
        if number_value is not None:
            self.window_first_tab_dict[number_value] = tab

    # Markers, range, grid and widths ------------------------------------

    def place_flag(self, name_str: str, time_s: float, color_str: str):
        """Add one flag of the file to the workspace, with its color.

        Inputs:
            name_str: the saved name, or "" for the name of a new flag.
            time_s: the time of the flag, in seconds.
            color_str: its color, lowercase "#rrggbb" (LLFR-00393).
        Outputs: the new VerticalMarker.
        """
        # LLFR-00393: the flag gets its saved color.
        if name_str:
            return self.workspace.add_named_marker(name_str, time_s,
                                                   color_str=color_str)
        # LLFR-00235, LLFR-00085: the name of a new flag.
        marker = self.workspace.add_marker(time_s)
        self.workspace.set_marker_color(marker.marker_id_i, color_str)
        return marker

    def rebuild_flags(self, marker_entry_list: list) -> None:
        """Add the saved flags to the current ones.

        Inputs:
            marker_entry_list: the "flags" list of the file.
        Outputs: none.
        """
        # LLFR-00230, LLFR-00205: added to the current flags, shown on
        # every plot.
        for marker_entry in marker_entry_list:
            name_value = (marker_entry.get(NAME_KEY_STR)
                          if isinstance(marker_entry, dict) else None)
            time_s = (finite_number(marker_entry.get(TIME_KEY_STR))
                      if isinstance(marker_entry, dict) else None)
            label_str = (f"Flag {describe_value(name_value)} at "
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
            # LLFR-00205: flags exist only while a plot exists.
            if not self.workspace.has_plots():
                self.report.add_not_rebuilt(
                    f"{label_str}: no plot was rebuilt to show it on.")
                continue
            # LLFR-00393: the saved color; LLFR-00815, LLFR-00816: the
            # default when it is missing or unusable, reported.
            color_str, color_reason_str = saved_color(
                marker_entry, DEFAULT_FLAG_COLOR_STR)
            if isinstance(name_value, str) and name_value.strip():
                # LLFR-00230: the saved name, kept even when another flag
                # has the same name (flag names need not be unique,
                # LLFR-00088).
                marker = self.place_flag(name_value, time_s, color_str)
            else:
                # LLFR-00235, LLFR-00085: a name that cannot be used is
                # replaced by the name of a new flag.
                marker = self.place_flag("", time_s, color_str)
                self.report.add_replaced(
                    f"Name {describe_value(name_value)} of the flag at "
                    f"{format_time(time_s)} is empty or not a text; "
                    f"replaced by \"{marker.name_str}\".")
            if color_reason_str == COLOR_MISSING_STR:
                # LLFR-00815, LLFR-01200, LLFR-00237: a missing color is
                # listed as replaced by the default color.
                self.report.add_replaced(
                    f"Color of the flag \"{marker.name_str}\" at "
                    f"{format_time(time_s)} {MISSING_REASON_STR}; "
                    f"replaced by \"{DEFAULT_FLAG_COLOR_STR}\".")
            elif color_reason_str:
                # LLFR-00817, LLFR-00235, LLFR-00237: a color not written
                # as "#rrggbb" is replaced by the default color.
                self.report.add_replaced(
                    f"Color {describe_value(marker_entry[COLOR_KEY_STR])} "
                    f"of the flag \"{marker.name_str}\" at "
                    f"{format_time(time_s)} is not written as #rrggbb; "
                    f"replaced by \"{DEFAULT_FLAG_COLOR_STR}\".")

    def rebuild_areas(self, area_entry_list: list) -> None:
        """Add the saved areas to the current ones.

        Inputs:
            area_entry_list: the "areas" list of the file.
        Outputs: none. Each area that is not rebuilt is reported with
            its times and the reason (LLFR-00319, LLFR-00237).
        """
        # LLFR-00230, LLFR-00310: added to the current areas, shown on
        # every time plot. LLFR-00319: the current areas, to tell an
        # overlap with one of them from one with an area of the file.
        current_id_set = {area.area_id_i for area in self.workspace.area_list}
        for area_entry in area_entry_list:
            entry_dict = area_entry if isinstance(area_entry, dict) else {}
            name_value = entry_dict.get(NAME_KEY_STR)
            start_s = finite_number(entry_dict.get(START_KEY_STR))
            end_s = finite_number(entry_dict.get(END_KEY_STR))
            label_str = (f"Area {describe_value(name_value)} from "
                         f"{format_time(start_s)} to {format_time(end_s)}")
            if start_s is None or end_s is None:
                self.report.add_not_rebuilt(
                    f"{label_str}: its start or end time is not a number.")
                continue
            # LLFR-00319: the start time must be before the end time.
            if not start_s < end_s:
                self.report.add_not_rebuilt(
                    f"{label_str}: its start time is not before its end "
                    f"time.")
                continue
            # LLFR-00319: both times within the time range of the file.
            if (not self.file_range_tuple
                    or start_s < self.file_range_tuple[0]
                    or end_s > self.file_range_tuple[1]):
                self.report.add_not_rebuilt(
                    f"{label_str}: it is not within the time range of the "
                    f"data file{self.file_range_text()}.")
                continue
            # LLFR-00310: areas exist only while a plot exists.
            if not self.workspace.has_plots():
                self.report.add_not_rebuilt(
                    f"{label_str}: no plot was rebuilt to show it on.")
                continue
            # LLFR-00319: no overlap with a current area or with an area
            # already rebuilt from this file (a shared edge is allowed).
            overlapped = next(
                (area for area in self.workspace.area_list
                 if spans_overlap_b(start_s, end_s, area.start_s,
                                    area.end_s)), None)
            if overlapped is not None:
                owner_str = ("a current area" if overlapped.area_id_i
                             in current_id_set
                             else "an area already rebuilt from this file")
                self.report.add_not_rebuilt(
                    f"{label_str}: it overlaps {owner_str}, "
                    f"\"{overlapped.name_str}\".")
                continue
            # LLFR-00319, LLFR-00351: the saved color; LLFR-00726,
            # LLFR-00728: a missing one, or one not written as
            # "#rrggbb", is replaced by the default color and reported.
            color_str, color_reason_str = saved_color(
                entry_dict, DEFAULT_AREA_COLOR_STR)
            if isinstance(name_value, str) and name_value.strip():
                # LLFR-00230: the saved name, kept even when another area
                # has the same name.
                area = self.workspace.add_area(start_s, end_s, name_value,
                                               color_str)
            else:
                # LLFR-00235, LLFR-00309: a name that cannot be used is
                # replaced by the name of a new area.
                area = self.workspace.add_area(start_s, end_s, "",
                                               color_str)
                self.report.add_replaced(
                    f"Name {describe_value(name_value)} of the area from "
                    f"{format_time(start_s)} to {format_time(end_s)} is "
                    f"empty or not a text; replaced by "
                    f"\"{area.name_str}\".")
            if color_reason_str == COLOR_MISSING_STR:
                # LLFR-00726, LLFR-01200, LLFR-00237: a missing color is
                # listed as replaced by the default color.
                self.report.add_replaced(
                    f"Color of the area \"{area.name_str}\" "
                    f"{MISSING_REASON_STR}; replaced by "
                    f"\"{DEFAULT_AREA_COLOR_STR}\".")
            elif color_reason_str:
                # LLFR-00729, LLFR-00235, LLFR-00237: a color not written
                # as "#rrggbb" is replaced by the default color.
                self.report.add_replaced(
                    f"Color {describe_value(entry_dict[COLOR_KEY_STR])} of "
                    f"the area \"{area.name_str}\" is not written as "
                    f"#rrggbb; replaced by \"{DEFAULT_AREA_COLOR_STR}\".")

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
                # LLFR-01146: a width Qt can take.
                if is_window_length(width_value):
                    width_list.append(int(width_value))
        if len(width_list) == 2:
            return tuple(width_list)
        self.report.add_replaced(
            f"Panel widths {describe_value(widths_value)} are not two "
            f"whole numbers of pixels from 1 to {MAXIMUM_WINDOW_PIXELS_I}; "
            f"the panels kept their widths.")
        return ()

    def add_synthetic_signals(self, built_value) -> None:
        """Add the synthetic signals created by the builder.

        Inputs:
            built_value: the value the synthetic signal builder
                returned: a dict signal name of the file -> (name of the
                signal drawn for it, its samples), or None for a signal
                of the file that was not created; or None.
        Outputs: none.
        """
        # LLFR-00230, LLFR-00262: the plots are rebuilt with the signals
        # of the data file and the synthetic signals.
        if not isinstance(built_value, dict):
            return
        for file_name_str, used_tuple in built_value.items():
            self.synthetic_name_dict[file_name_str] = used_tuple
            if used_tuple and used_tuple[0] not in self.signal_dict:
                # LLFR-00282: the samples, under the name drawn.
                self.signal_dict[used_tuple[0]] = used_tuple[1]

    def rebuild(self, layout_dict: dict,
                synthetic_signal_builder=None) -> LayoutResult:
        """Rebuild the whole layout of a file in the workspace.

        Inputs:
            layout_dict: the content of the file (parse_layout_text).
            synthetic_signal_builder: optional function taking (entry
                list, report) that keeps the current synthetic signals,
                creates those of the file before the plots are rebuilt,
                reports those not created, and returns the dict of
                add_synthetic_signals (LLFR-00262, LLFR-00282;
                LLFR-00283: no FFT signal is created); None creates
                none.
        Outputs: the LayoutResult to apply to the view.
        """
        # LLFR-00262: the synthetic signals come first, so that the
        # plots are rebuilt with them. LLFR-00235: a value that is not a
        # list creates none, and is reported.
        synthetic_value = layout_dict.get(SYNTHETIC_SIGNALS_KEY_STR)
        if synthetic_value is not None and not isinstance(
                synthetic_value, list):
            self.report.add_not_rebuilt(
                f"Synthetic signals: the entry "
                f"\"{SYNTHETIC_SIGNALS_KEY_STR}\" is not a list, so no "
                f"synthetic signal was created.")
        if synthetic_signal_builder is not None:
            self.add_synthetic_signals(synthetic_signal_builder(
                synthetic_signal_entry_list(layout_dict), self.report))
        tab_entry_list = layout_dict.get(TABS_KEY_STR)
        if not isinstance(tab_entry_list, list):
            # LLFR-00235: no list of tabs; nothing to add.
            self.report.add_not_rebuilt(
                f"Tabs: the entry \"{TABS_KEY_STR}\" is not a list, so no "
                f"tab was added.")
            tab_entry_list = []
        # LLFR-00229: with no plot in any current tab, the tabs of the
        # file replace the current ones; else they are added after them.
        # LLFR-00229, LLFR-00231: only when the file adds a tab with a
        # plot; otherwise the current tabs are kept.
        tabs_replaced_b = (
            not self.workspace.has_plots()
            and any(self.tab_will_hold_plot(tab_entry)
                    for tab_entry in tab_entry_list))
        # LLFR-00229: kept tabs keep their plots as they are, with their
        # text notes, which a layout file never holds (LLFR-00226).
        kept_docked_tab = None
        if tabs_replaced_b:
            # LLFR-01079: the first current docked tab, kept if every tab
            # of the file turns out to be undocked.
            kept_docked_tab = self.workspace.docked_tab_list()[0]
            self.workspace.remove_all_tabs()
        first_tab_id_i = self.rebuild_tabs(tab_entry_list)
        if kept_docked_tab is not None and not (
                self.workspace.docked_tab_list()):
            # LLFR-01079: the main window keeps a docked tab, with no
            # plot; LLFR-01080: the windows of the other tabs close.
            self.workspace.tab_list.insert(0, kept_docked_tab)
        # LLFR-00230, LLFR-00233: the flags of the file; LLFR-00228: only
        # under "flags", also in a file of an earlier version.
        self.rebuild_flags(list_entry(layout_dict, FLAGS_KEY_STR))
        # LLFR-00230, LLFR-00319: the areas of the file.
        self.rebuild_areas(list_entry(layout_dict, AREAS_KEY_STR))
        # LLFR-00234: the time range, limited to the data file.
        # LLFR-01200: a missing entry shows the whole time range, and is
        # listed as a replaced value.
        if TIME_RANGE_KEY_STR not in layout_dict:
            self.report.add_replaced(
                f"Time range {MISSING_REASON_STR}; the whole time range of "
                f"the data file{self.file_range_text()} is shown.")
        time_range_tuple = self.time_range(
            layout_dict.get(TIME_RANGE_KEY_STR))
        # LLFR-00230: the grid and the panel widths. LLFR-01200: a
        # missing "grid" or "panel_widths" entry leaves the grid or the
        # widths as they are, and is listed as a replaced value; a value
        # that is there but cannot be used is reported (LLFR-00235).
        grid_shown_b = None
        if GRID_KEY_STR in layout_dict:
            grid_shown_b = self.grid_setting(layout_dict[GRID_KEY_STR])
        else:
            self.report.add_replaced(
                f"Grid setting {MISSING_REASON_STR}; the grid was left as "
                f"it was.")
        if PANEL_WIDTHS_KEY_STR not in layout_dict:
            self.report.add_replaced(
                "Panel widths are missing; the panels kept their widths.")
        panel_width_tuple = self.panel_widths(
            layout_dict.get(PANEL_WIDTHS_KEY_STR))
        result = LayoutResult(self.report, first_tab_id_i, time_range_tuple,
                              grid_shown_b, panel_width_tuple,
                              tabs_replaced_b)
        # LLFR-01214: the main window's panel shown or hidden as saved; a
        # file without the value leaves it as it is.
        shown_value = layout_dict.get(MAIN_PANEL_SHOWN_KEY_STR)
        if isinstance(shown_value, bool):
            self.workspace.main_panel_shown_b = shown_value
            result.main_panel_shown_b = shown_value
        elif shown_value is not None:
            self.report.add_replaced(
                f"Signal list panel shown {describe_value(shown_value)} is "
                f"neither true nor false; the panel was left as it was.")
        return result


def is_whole_number(value) -> bool:
    """Tell whether a value of the file is a whole number.

    Inputs:
        value: a value read from the JSON text.
    Outputs: True for an int that is not a bool (LLFR-01075).
    """
    # LLFR-01081: a value that is not a whole number cannot be used.
    return isinstance(value, int) and not isinstance(value, bool)


def is_window_coordinate(value) -> bool:
    """Tell whether a value of the file is a usable window coordinate.

    Inputs:
        value: a value read from the JSON text.
    Outputs: True for a whole number from -MAXIMUM_WINDOW_PIXELS_I to
        MAXIMUM_WINDOW_PIXELS_I (LLFR-01081).
    """
    # LLFR-01081: a position Qt can take, also once a size is added.
    return (is_whole_number(value)
            and -MAXIMUM_WINDOW_PIXELS_I <= value
            <= MAXIMUM_WINDOW_PIXELS_I)


def is_window_length(value) -> bool:
    """Tell whether a value of the file is a usable size or width.

    Inputs:
        value: a value read from the JSON text.
    Outputs: True for a whole number from 1 to MAXIMUM_WINDOW_PIXELS_I
        (LLFR-01081, LLFR-01146).
    """
    # LLFR-01081, LLFR-01146: a size Qt can take; a larger number (for
    # example above 2**31 - 1) would make Qt raise OverflowError.
    return is_whole_number(value) and 1 <= value <= MAXIMUM_WINDOW_PIXELS_I


def rebuild_layout(workspace, layout_dict: dict, signal_dict: dict,
                   time_array, synthetic_signal_builder=None,
                   files_range_tuple=None, new_window_tuple=()):
    """Rebuild the layout of a file in a workspace.

    Inputs:
        workspace: the Workspace to add the layout to.
        layout_dict: the content of the file (parse_layout_text).
        signal_dict: signal name -> numpy array of the open data file.
        time_array: the values of the time signal, in seconds, or a
            function signal name -> time signal of its file.
        synthetic_signal_builder: optional function of LayoutBuilder.
            rebuild for the synthetic signals (LLFR-00262).
        files_range_tuple: the time range of the open data files, or
            None for the range of time_array (LLFR-00916).
        new_window_tuple: the window an undock would open (LLFR-01081).
    Outputs: the LayoutResult.
    """
    # LLFR-00229 to LLFR-00235: see LayoutBuilder.
    return LayoutBuilder(workspace, signal_dict, time_array,
                         files_range_tuple, new_window_tuple).rebuild(
        layout_dict, synthetic_signal_builder)


# ----------------------------------------------------------------------
# Save options and data files of a layout (HLFR-00156, HLFR-00157)
# ----------------------------------------------------------------------

# LLFR-01223: the keys of the data files of the layout file.
DATA_FILES_KEY_STR = "data_files"
NUMBER_KEY_STR = "number"
PATH_KEY_STR = "path"
RELATIVE_PATH_KEY_STR = "relative_path"
# LLFR-01226: a file prefix at the start of a name, or after the
# operation of a product of two signals (HLFR-00104).
FILE_PREFIX_PATTERN_STR = r"(^|_prod_)file([0-9]+)_"
# LLFR-01228: the number given to the prefix of a data file of the
# layout file that is not open; no data file ever has it (LLFR-00900).
UNUSED_FILE_NUMBER_I = 0
# LLFR-01227: the reasons of the load report.
FILE_NOT_FOUND_REASON_STR = (
    "{path}: no file at this path or at the path relative to the layout "
    "file.")
FILE_NOT_OPENED_REASON_STR = "{path}: the file could not be opened."
FILE_ENTRY_UNREADABLE_STR = (
    "Data file entry {entry} has no usable number and path.")


def layout_with_save_options(layout_dict: dict, markers_b: bool = True,
                             current_tab_only_b: bool = False) -> dict:
    """Return the content of a layout file with the save options applied.

    Inputs:
        layout_dict: the content built by build_layout_dict.
        markers_b: False to leave out the pinned data tips, flags, areas
            and delta markers (LLFR-01221).
        current_tab_only_b: True to keep only the tab that the main
            window shows, as its shown docked tab (LLFR-01222).
    Outputs: a new dict; layout_dict is not changed.
    """
    result_dict = json.loads(json.dumps(layout_dict))
    if not markers_b:
        # LLFR-01221: no marker of any kind in the file.
        result_dict[FLAGS_KEY_STR] = []
        result_dict[AREAS_KEY_STR] = []
        for tab_entry_dict in list_entry(result_dict, TABS_KEY_STR):
            for plot_entry_dict in list_entry(tab_entry_dict, PLOTS_KEY_STR):
                plot_entry_dict[DATA_TIPS_KEY_STR] = []
                plot_entry_dict[DELTA_MARKERS_KEY_STR] = []
    if current_tab_only_b:
        # LLFR-01222: the tab the main window shows (LLFR-00225 item 1),
        # docked, and shown.
        tab_list = list_entry(result_dict, TABS_KEY_STR)
        shown_index_i = result_dict.get(SHOWN_TAB_KEY_STR, 0)
        if (not isinstance(shown_index_i, int)
                or not 0 <= shown_index_i < len(tab_list)):
            shown_index_i = 0
        kept_list = tab_list[shown_index_i:shown_index_i + 1]
        for tab_entry_dict in kept_list:
            tab_entry_dict[UNDOCKED_KEY_STR] = False
            for key_str in (WINDOW_KEY_STR, WINDOW_NUMBER_KEY_STR,
                            SIGNAL_LIST_PANEL_KEY_STR):
                tab_entry_dict.pop(key_str, None)
        result_dict[TABS_KEY_STR] = kept_list
        result_dict[SHOWN_TAB_KEY_STR] = 0
    return result_dict


def relative_path_str(path_str: str, layout_path_str: str):
    """Return a path relative to the folder of a layout file.

    Inputs:
        path_str: the absolute path of a data file.
        layout_path_str: the path of the layout file.
    Outputs: the relative path, with "/" separators, or None when there
        is none (another drive on Windows).
    """
    # LLFR-01223: relative to the folder of the layout file.
    try:
        relative_str = os.path.relpath(
            path_str, os.path.dirname(os.path.abspath(layout_path_str)))
    except ValueError:
        return None
    return relative_str.replace(os.sep, "/")


def data_file_entry_list(numbered_path_list: list,
                         layout_path_str: str) -> list:
    """Return the entries of the open data files for the layout file.

    Inputs:
        numbered_path_list: one (number, path) per open data file.
        layout_path_str: the path of the layout file.
    Outputs: one dict per file, in the order of the numbers, with its
        number, absolute path and relative path (LLFR-01223).
    """
    # LLFR-01223: the number, the absolute and the relative path.
    entry_list = []
    for number_i, path_str in sorted(numbered_path_list):
        absolute_str = os.path.abspath(str(path_str))
        entry_list.append({
            NUMBER_KEY_STR: int(number_i),
            PATH_KEY_STR: absolute_str,
            RELATIVE_PATH_KEY_STR: relative_path_str(absolute_str,
                                                     layout_path_str)})
    return entry_list


def data_file_candidate_list(entry_dict: dict, layout_path_str: str) -> list:
    """Return the paths where a data file of a layout file may be.

    Inputs:
        entry_dict: an entry of the `data_files` list.
        layout_path_str: the path of the layout file being loaded.
    Outputs: its `path`, then its `relative_path` from the folder of the
        layout file, each when it is a text.
    """
    # LLFR-01224: the absolute path first, then the relative one.
    candidate_list = []
    path_value = entry_dict.get(PATH_KEY_STR)
    if isinstance(path_value, str) and path_value:
        candidate_list.append(path_value)
    relative_value = entry_dict.get(RELATIVE_PATH_KEY_STR)
    if isinstance(relative_value, str) and relative_value:
        candidate_list.append(os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(layout_path_str)),
            relative_value.replace("/", os.sep))))
    return candidate_list


def renamed_file_prefix(name_value, number_dict: dict):
    """Return a signal name with its file prefixes renumbered.

    Inputs:
        name_value: a name of the layout file (any value).
        number_dict: saved file number -> number of that file now.
    Outputs: the name with each `file<N>_` at its start, or after
        `_prod_`, given the new number of N when number_dict has one; any
        other value unchanged.
    """
    # LLFR-01226: the prefix of the number the data file has now.
    if not isinstance(name_value, str):
        return name_value

    def new_prefix(match) -> str:
        """Return the prefix with its new number.

        Inputs:
            match: the re match of FILE_PREFIX_PATTERN_STR.
        Outputs: the replacement text.
        """
        # LLFR-01226, LLFR-01228.
        number_i = int(match.group(2))
        return (f"{match.group(1)}file"
                f"{number_dict.get(number_i, number_i)}_")

    return re.sub(FILE_PREFIX_PATTERN_STR, new_prefix, name_value)


def renumber_point(entry, number_dict: dict) -> None:
    """Renumber the signal of a curve, data tip or delta marker point.

    Inputs:
        entry: a dict of the file with a `signal` key, or another value.
        number_dict: saved file number -> number now.
    Outputs: none; the entry is changed in place.
    """
    # LLFR-01226: the curves, data tips and delta marker points.
    if isinstance(entry, dict) and SIGNAL_KEY_STR in entry:
        entry[SIGNAL_KEY_STR] = renamed_file_prefix(entry[SIGNAL_KEY_STR],
                                                    number_dict)


def renumber_layout_names(layout_dict: dict, number_dict: dict) -> None:
    """Give the signal names of a layout the numbers of the open files.

    Inputs:
        layout_dict: the content of a layout file.
        number_dict: saved file number -> number of that file now; a
            saved number missing from it is kept.
    Outputs: none; the names of the curves, pinned data tips, delta
        markers and synthetic signal entries are changed in place
        (LLFR-01226, LLFR-01228).
    """
    # LLFR-01226: every name that a load matches with the signal list.
    for tab_entry_dict in list_entry(layout_dict, TABS_KEY_STR):
        for plot_entry_dict in list_entry(tab_entry_dict, PLOTS_KEY_STR):
            for curve_entry in list_entry(plot_entry_dict, CURVES_KEY_STR):
                renumber_point(curve_entry, number_dict)
            for tip_entry in list_entry(plot_entry_dict, DATA_TIPS_KEY_STR):
                renumber_point(tip_entry, number_dict)
            for delta_entry in list_entry(plot_entry_dict,
                                          DELTA_MARKERS_KEY_STR):
                if isinstance(delta_entry, dict):
                    renumber_point(delta_entry.get(FIRST_POINT_KEY_STR),
                                   number_dict)
                    renumber_point(delta_entry.get(SECOND_POINT_KEY_STR),
                                   number_dict)
    for signal_entry in list_entry(layout_dict, SYNTHETIC_SIGNALS_KEY_STR):
        if not isinstance(signal_entry, dict):
            continue
        if SYNTHETIC_NAME_KEY_STR in signal_entry:
            signal_entry[SYNTHETIC_NAME_KEY_STR] = renamed_file_prefix(
                signal_entry[SYNTHETIC_NAME_KEY_STR], number_dict)
        source_value = signal_entry.get(SYNTHETIC_SOURCES_KEY_STR)
        if isinstance(source_value, list):
            signal_entry[SYNTHETIC_SOURCES_KEY_STR] = [
                renamed_file_prefix(name_value, number_dict)
                for name_value in source_value]


def file_number_dict(saved_number_list: list, found_dict: dict,
                     open_number_list: list) -> dict:
    """Return the new number of each saved data file number.

    Inputs:
        saved_number_list: the numbers of the data files of the layout
            file.
        found_dict: saved number -> number of the open data file used
            for it (LLFR-01224, LLFR-01225).
        open_number_list: the numbers of the open data files.
    Outputs: saved number -> number to read its names with: the found
        file's number, or UNUSED_FILE_NUMBER_I for a saved file that is
        not open while another open file has its saved number
        (LLFR-01228); a saved number that no open file has is kept.
    """
    # LLFR-01226, LLFR-01228.
    number_dict = {}
    for saved_number_i in saved_number_list:
        if saved_number_i in found_dict:
            number_dict[saved_number_i] = int(found_dict[saved_number_i])
        elif saved_number_i in open_number_list:
            number_dict[saved_number_i] = UNUSED_FILE_NUMBER_I
    return number_dict


def data_file_entries_of(layout_dict: dict) -> list:
    """Return the readable entries of the data files of a layout file.

    Inputs:
        layout_dict: the content of a layout file.
    Outputs: a list of (saved number, entry dict, None) for each entry
        with a whole number of 1 or more, and (None, entry, reason) for
        each other entry.
    """
    # LLFR-01223, LLFR-01224: hand-edited values are reported.
    result_list = []
    for entry_value in list_entry(layout_dict, DATA_FILES_KEY_STR):
        number_value = (entry_value.get(NUMBER_KEY_STR)
                        if isinstance(entry_value, dict) else None)
        if (isinstance(entry_value, dict) and is_whole_number(number_value)
                and number_value >= 1):
            result_list.append((int(number_value), entry_value, None))
        else:
            result_list.append((None, entry_value,
                                FILE_ENTRY_UNREADABLE_STR.format(
                                    entry=describe_value(entry_value))))
    return result_list
