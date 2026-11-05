"""Model of the plot panel: tabs, plots, curves, tips, markers, areas.

The workspace holds no Qt code (COR-00009). The view draws what the
workspace holds, and the controller changes the workspace when the user
acts.
"""

import copy
import math
import random
import re
from dataclasses import dataclass

from model.curve_colors import (
    MARKER_COLOR_STR, PALETTE_COLOR_TUPLE, hex_color_or_none,
    next_curve_color)

# LLFR-01122: the plot matrix of a new tab, 5 rows and 1 column
# (HLFR-00151).
DEFAULT_MATRIX_ROWS_I = 5
DEFAULT_MATRIX_COLUMNS_I = 1
# LLFR-01097: the rows and the columns of a plot matrix go from 1 to 10
# (HLFR-00146).
MINIMUM_MATRIX_SIZE_I = 1
MAXIMUM_MATRIX_SIZE_I = 10
# LLFR-00031: maximum number of plots in a tab with the default plot
# matrix (HLFR-00018): its rows times its columns.
MAXIMUM_PLOTS_PER_TAB_I = DEFAULT_MATRIX_ROWS_I * DEFAULT_MATRIX_COLUMNS_I
# LLFR-00041: preset curve widths (HLFR-00023).
PRESET_WIDTH_TUPLE = (1, 2, 3, 4, 5)
# LLFR-00052: width of a newly drawn curve.
DEFAULT_WIDTH_I = 1
# LLFR-00024: prefix of the default tab names ("Tab 1", "Tab 2", ...).
TAB_NAME_PREFIX_STR = "Tab "
# LLFR-00085: default name of a new flag ("Flag 1", "Flag 2", ...). In
# the code, a flag is a "marker" (VerticalMarker).
DEFAULT_MARKER_NAME_FORMAT_STR = "Flag {}"
# LLFR-00111, LLFR-00233: a default flag name, to read its number back
# when a flag of a layout file keeps its saved name.
DEFAULT_MARKER_NAME_PATTERN_STR = r"Flag (\d+)"
# LLFR-00309: default name of a new area ("Area 1", "Area 2", ...).
DEFAULT_AREA_NAME_FORMAT_STR = "Area {}"
# LLFR-00309, LLFR-00319: a default area name, to read its number back
# when an area of a layout file keeps its saved name.
DEFAULT_AREA_NAME_PATTERN_STR = r"Area (\d+)"
# LLFR-00083: the color of a new flag, the reserved marker color.
DEFAULT_FLAG_COLOR_STR = MARKER_COLOR_STR
# LLFR-00172: the color of a new delta marker, the reserved marker
# color; the user may change it (LLFR-00409).
DEFAULT_DELTA_MARKER_COLOR_STR = MARKER_COLOR_STR
# LLFR-00351: the color of a new area, the reserved marker color; the
# view draws every area see-through (LLFR-00305).
DEFAULT_AREA_COLOR_STR = MARKER_COLOR_STR
# LLFR-00385: the sizes of a text note's text, in points, and the size
# of a new text note.
TEXT_NOTE_SIZE_TUPLE = (8, 10, 12, 16, 20, 24, 32)
DEFAULT_TEXT_NOTE_SIZE_I = 12
# LLFR-00336: the text color of a new text note, the app's text color,
# a near-black dark grey, and its border color, the reserved marker
# color.
DEFAULT_TEXT_NOTE_COLOR_STR = "#24303b"
DEFAULT_TEXT_NOTE_BORDER_COLOR_STR = MARKER_COLOR_STR
# LLFR-00373: the color of a new arrow, the reserved marker color.
DEFAULT_ARROW_COLOR_STR = MARKER_COLOR_STR
# LLFR-00438: default name of a new arrow ("Arrow 1", "Arrow 2", ...).
DEFAULT_ARROW_NAME_FORMAT_STR = "Arrow {}"
# LLFR-00152: label offset of a pinned tip that was never moved; the
# view then places the label beside its point by itself.
AUTOMATIC_LABEL_OFFSET_TUPLE = ()
# LLFR-00168, LLFR-00170: the two kinds of delta markers, a Delta X
# marker (time difference) and a Delta Y marker (value difference).
DELTA_X_KIND_STR = "x"
DELTA_Y_KIND_STR = "y"
DELTA_KIND_TUPLE = (DELTA_X_KIND_STR, DELTA_Y_KIND_STR)
# LLFR-00428: default names of new delta markers, "Delta X N" and
# "Delta Y N", numbered separately for each kind.
DEFAULT_DELTA_NAME_FORMAT_DICT = {DELTA_X_KIND_STR: "Delta X {}",
                                  DELTA_Y_KIND_STR: "Delta Y {}"}
# LLFR-00256, HLFR-00058: the two kinds of plots, a time plot (time in
# seconds on its x-axis, LLFR-00068) and a frequency plot (frequency in
# Hz on its x-axis, for FFT signals). Plot.kind_str holds one of them.
TIME_PLOT_KIND_STR = "time"
FREQUENCY_PLOT_KIND_STR = "frequency"
PLOT_KIND_TUPLE = (TIME_PLOT_KIND_STR, FREQUENCY_PLOT_KIND_STR)
# LLFR-00258: Plot.frequency_range_tuple of a frequency plot that shows
# its whole frequency range, from 0 Hz to its highest frequency.
WHOLE_FREQUENCY_RANGE_TUPLE = ()


@dataclass
class Curve:
    """One signal drawn in a plot.

    Inputs:
        signal_name_str: name of the drawn signal.
        color_str: color of the curve, written as "#rrggbb".
        width_i: preset width of the curve, one of PRESET_WIDTH_TUPLE.
    """

    signal_name_str: str
    color_str: str
    width_i: int = DEFAULT_WIDTH_I


@dataclass
class PinnedTip:
    """A tip fixed at one point of a curve (LLFR-00045).

    Inputs:
        signal_name_str: name of the signal whose curve holds the point.
        time_s: x-axis value of the point, in seconds.
        value_f: y-axis value of the point, as stored in the file.
        label_offset_tuple: where the tip's label is drawn, as the
            offset (x, y) in typographic points from the point to the
            center of the label, x to the right and y upwards; the
            empty tuple AUTOMATIC_LABEL_OFFSET_TUPLE until the user
            moves the tip (LLFR-00152). An offset in points keeps the
            label at the same place on screen relative to its point
            when the plot is zoomed or panned.
    """

    signal_name_str: str
    time_s: float
    value_f: float
    label_offset_tuple: tuple = AUTOMATIC_LABEL_OFFSET_TUPLE


@dataclass
class TextNote:
    """A text written at one place of a plot (HLFR-00073).

    Inputs:
        text_str: the text shown, without leading and trailing spaces
            and never empty (LLFR-00334).
        time_s: x-axis value the note is attached to, in seconds (in Hz
            on a frequency plot, LLFR-00333).
        value_f: y-axis value the note is attached to (LLFR-00337).
        size_i: the chosen size of the text, in points, one of
            TEXT_NOTE_SIZE_TUPLE (LLFR-00385).
        border_color_str: color of the box's border, "#rrggbb" in
            lowercase (LLFR-00336, LLFR-00387).
        text_color_str: color of the text, "#rrggbb" in lowercase.
    """

    text_str: str
    time_s: float
    value_f: float
    size_i: int = DEFAULT_TEXT_NOTE_SIZE_I
    border_color_str: str = DEFAULT_TEXT_NOTE_BORDER_COLOR_STR
    text_color_str: str = DEFAULT_TEXT_NOTE_COLOR_STR


@dataclass
class Arrow:
    """A straight arrow drawn on one plot (HLFR-00081).

    Inputs:
        start_time_s: x-axis value of the end without the arrowhead, in
            seconds (in Hz on a frequency plot).
        start_value_f: y-axis value of that end.
        end_time_s: x-axis value of the end with the arrowhead (s or
            Hz, LLFR-00372).
        end_value_f: y-axis value of the arrowhead's end.
        color_str: color of the line and the arrowhead, "#rrggbb" in
            lowercase (LLFR-00373, LLFR-00379).
        name_str: name shown in the arrow's label (LLFR-00436), never
            empty once the arrow is in a plot (LLFR-00438, LLFR-00874).
    """

    start_time_s: float
    start_value_f: float
    end_time_s: float
    end_value_f: float
    color_str: str = DEFAULT_ARROW_COLOR_STR
    name_str: str = ""


def finite_arrow_tuple(start_time_s: float, start_value_f: float,
                       end_time_s: float, end_value_f: float) -> tuple:
    """Return the two ends of an arrow as four finite floats.

    Inputs:
        start_time_s: x value of the start (s, or Hz on a frequency
            plot).
        start_value_f: y value of the start.
        end_time_s: x value of the arrowhead's end.
        end_value_f: y value of the arrowhead's end.
    Outputs: (start_time_s, start_value_f, end_time_s, end_value_f) as
        floats. Raises ValueError when a value is not a finite number or
        when the two ends are the same point.
    """
    # LLFR-00372, LLFR-00374: an arrow is attached to the x and y values
    # of its two ends, which must be places it can be drawn at.
    end_tuple = (float(start_time_s), float(start_value_f),
                 float(end_time_s), float(end_value_f))
    if not all(math.isfinite(number_f) for number_f in end_tuple):
        raise ValueError("An arrow needs finite x and y values.")
    # LLFR-00372, LLFR-00377: the ends are apart (the view keeps them at
    # least 5 pixels apart), so the arrow has a direction.
    if end_tuple[:2] == end_tuple[2:]:
        raise ValueError("The two ends of an arrow must differ.")
    return end_tuple


def text_note_text(text_str) -> str:
    """Return the text a text note keeps for a typed text.

    Inputs:
        text_str: the typed text.
    Outputs: the text without leading and trailing spaces; "" when it is
        empty or made only of spaces (LLFR-00334, LLFR-00342).
    """
    # LLFR-00334, LLFR-00342: a blank text writes nothing.
    return str(text_str).strip()


def finite_place_tuple(time_s: float, value_f: float) -> tuple:
    """Return a text note place as two finite floats.

    Inputs:
        time_s: x-axis value (s, or Hz on a frequency plot).
        value_f: y-axis value.
    Outputs: (time_s, value_f) as floats. Raises ValueError when a value
        is not a finite number.
    """
    # LLFR-00333, LLFR-00339: a note is attached to a place it can be
    # drawn at.
    place_tuple = (float(time_s), float(value_f))
    if not all(math.isfinite(number_f) for number_f in place_tuple):
        raise ValueError("A text note needs a finite x and y value.")
    return place_tuple


@dataclass
class VerticalMarker:
    """A vertical line drawn across a plot at one time value (HLFR-00028).

    Inputs:
        marker_id_i: id of the marker, unique within the workspace and
            never reused.
        name_str: name shown in the marker's label (LLFR-00084).
        time_s: time of the marker on the x-axis, in seconds.
        color_str: color of its line, label text and time value,
            "#rrggbb" in lowercase (LLFR-00083, LLFR-00392).
    """

    marker_id_i: int
    name_str: str
    time_s: float
    color_str: str = DEFAULT_FLAG_COLOR_STR


@dataclass
class Area:
    """A shaded band across the time plots between two times (HLFR-00066).

    Inputs:
        area_id_i: id of the area, unique within the workspace and never
            reused.
        name_str: name shown in the area's label (LLFR-00307).
        start_s: time of the left edge of the band, in seconds.
        end_s: time of the right edge, in seconds, after start_s.
        color_str: its color, "#rrggbb" in lowercase (LLFR-00351); the
            view draws it see-through (LLFR-00305).
    """

    area_id_i: int
    name_str: str
    start_s: float
    end_s: float
    color_str: str = DEFAULT_AREA_COLOR_STR


def area_span_tuple(start_s: float, end_s: float) -> tuple:
    """Check the two times of an area and return them in order.

    Inputs:
        start_s: one edge of the area, in seconds.
        end_s: the other edge, in seconds.
    Outputs: (start_s, end_s) as floats with start_s < end_s. Raises
        ValueError when a time is not finite or both are equal.
    """
    # LLFR-00304: an area lies between two different times.
    start_s, end_s = sorted((float(start_s), float(end_s)))
    if not (math.isfinite(start_s) and math.isfinite(end_s)):
        raise ValueError("The times of an area must be finite.")
    if not end_s > start_s:
        raise ValueError("An area needs a start time before its end time.")
    return (start_s, end_s)


def spans_overlap_b(first_start_s: float, first_end_s: float,
                    second_start_s: float, second_end_s: float) -> bool:
    """Tell whether two time spans overlap by more than a shared edge.

    Inputs:
        first_start_s, first_end_s: the first span, start before end.
        second_start_s, second_end_s: the second span, start before end.
    Outputs: True when the spans have a part in common that is longer
        than one point; two spans that only share an edge do not overlap.
    """
    # LLFR-00304: areas must not overlap, but may share an edge.
    return first_start_s < second_end_s and second_start_s < first_end_s


@dataclass
class DeltaMarker:
    """A measurement between two curve points (HLFR-00043, HLFR-00044).

    Inputs:
        delta_marker_id_i: id of the delta marker, unique within the
            workspace and never reused.
        kind_str: DELTA_X_KIND_STR for a Delta X marker (LLFR-00168) or
            DELTA_Y_KIND_STR for a Delta Y marker (LLFR-00170).
        first_point_tuple: the first picked point (LLFR-00163), as
            (signal_name_str, time_s, value_f): the exact values of the
            curve sample.
        second_point_tuple: the second picked point (LLFR-00164), in the
            same form.
        color_str: color of its curly bracket, dots, value text and
            label, "#rrggbb" in lowercase (LLFR-00172, LLFR-00409,
            LLFR-00818).
        name_str: name shown in its label (LLFR-00427), never empty once
            the marker is in a plot (LLFR-00428, LLFR-00854).
    """

    delta_marker_id_i: int
    kind_str: str
    first_point_tuple: tuple
    second_point_tuple: tuple
    color_str: str = DEFAULT_DELTA_MARKER_COLOR_STR
    name_str: str = ""

    def delta_f(self) -> float:
        """Return the measured difference, second point minus first.

        Inputs: none.
        Outputs: for a Delta X marker the time difference in seconds
            (LLFR-00169); for a Delta Y marker the value difference
            (LLFR-00171). It is signed.
        """
        # LLFR-00169, LLFR-00171: second minus first, never the absolute
        # value, so the sign tells the order of the two points.
        return delta_value_f(self.kind_str, self.first_point_tuple,
                             self.second_point_tuple)

    def has_point_on(self, signal_name_str: str) -> bool:
        """Tell whether one of the two points is on a signal's curve.

        Inputs:
            signal_name_str: name of the signal.
        Outputs: True when the first or the second point is on it.
        """
        # LLFR-00178: such a marker goes away with the curve.
        return signal_name_str in (self.first_point_tuple[0],
                                   self.second_point_tuple[0])


def delta_value_f(kind_str: str, first_point_tuple,
                  second_point_tuple) -> float:
    """Return the value a delta marker between two points would show.

    Inputs:
        kind_str: DELTA_X_KIND_STR or DELTA_Y_KIND_STR.
        first_point_tuple: (signal_name_str, time_s, value_f) of the
            first point.
        second_point_tuple: the same for the second point.
    Outputs: the second point minus the first point: the time (the
        frequency, on a frequency plot) for a Delta X marker
        (LLFR-00169, LLFR-00261), the y-axis value for a Delta Y marker
        (LLFR-00171).
    """
    # LLFR-00169, LLFR-00171, LLFR-00431: the measured coordinate.
    index_i = 1 if kind_str == DELTA_X_KIND_STR else 2
    return (float(second_point_tuple[index_i])
            - float(first_point_tuple[index_i]))


def delta_value_zero_b(kind_str: str, first_point_tuple,
                       second_point_tuple) -> bool:
    """Tell whether a delta marker between two points would measure zero.

    Inputs:
        kind_str: DELTA_X_KIND_STR or DELTA_Y_KIND_STR.
        first_point_tuple: (signal_name_str, time_s, value_f).
        second_point_tuple: the same for the second point.
    Outputs: True when the two points have exactly the same time (the
        frequency, on a frequency plot) for a Delta X marker, or exactly
        the same y-axis value for a Delta Y marker.
    """
    # LLFR-00431: such a marker measures nothing (HLFR-00098).
    return delta_value_f(kind_str, first_point_tuple,
                         second_point_tuple) == 0.0


def delta_point_tuple(point_tuple) -> tuple:
    """Check a delta marker point and return it as plain values.

    Inputs:
        point_tuple: (signal_name_str, time_s, value_f).
    Outputs: the tuple (str, float, float). Raises ValueError when it
        does not have three items or the numbers are not finite.
    """
    # LLFR-00163, LLFR-00164: a point is a curve sample with finite
    # values, so it can be drawn and measured.
    point_tuple = tuple(point_tuple)
    if len(point_tuple) != 3:
        raise ValueError("A delta marker point needs a signal name, a "
                         "time and a value.")
    time_s = float(point_tuple[1])
    value_f = float(point_tuple[2])
    if not (math.isfinite(time_s) and math.isfinite(value_f)):
        raise ValueError("A delta marker point must be finite.")
    return (str(point_tuple[0]), time_s, value_f)


def first_free_name(name_format_str: str, used_name_set: set,
                    first_number_i: int = 1) -> str:
    """Return the first default name that is not in use.

    Inputs:
        name_format_str: the default name with "{}" for its number, for
            example "Delta X {}".
        used_name_set: the names already in use.
        first_number_i: the smallest number to try.
    Outputs: the name with the smallest number from first_number_i up
        that is not in used_name_set.
    """
    # LLFR-00428, LLFR-00852, LLFR-00438: a new default name is never
    # the name of another item of the same kind.
    number_i = int(first_number_i)
    while name_format_str.format(number_i) in used_name_set:
        number_i += 1
    return name_format_str.format(number_i)


class MarkerIdCounter:
    """Hands out marker ids that are never reused.

    One counter is shared by the workspace and all its plots, so that
    marker ids are unique across the whole workspace. Vertical markers
    (kept by the workspace, LLFR-00205) and delta markers (kept by their
    plot) take their ids from the same counter, so an id never names two
    markers of any kind.

    Inputs: none.
    """

    def __init__(self) -> None:
        """Create a counter whose first id is 1.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00091: ids count up, so a deleted marker's id stays unused.
        self.next_marker_id_i = 1

    def take_next_id(self) -> int:
        """Return a new marker id and advance the counter.

        Inputs: none.
        Outputs: the new id.
        """
        # LLFR-00081: every placed marker gets its own id.
        marker_id_i = self.next_marker_id_i
        self.next_marker_id_i += 1
        return marker_id_i


class Plot:
    """An area of a tab in which signal curves are drawn.

    A plot is a time plot or a frequency plot (HLFR-00058), as its
    ``kind_str`` says; the kind is chosen when the plot is created and
    never changes. A frequency plot only draws FFT signals, a time plot
    only the other signals (LLFR-00257); the controller checks this.

    Inputs:
        plot_id_i: id of the plot, unique within the workspace.
        random_generator: random.Random used for the curve colors from
            the 9th curve on (LLFR-00034).
        marker_id_counter: optional MarkerIdCounter shared with the other
            plots of the workspace; a new one is used when it is None.
        kind_str: TIME_PLOT_KIND_STR (the default) or
            FREQUENCY_PLOT_KIND_STR.
    Attributes:
        kind_str: the kind of the plot, one of PLOT_KIND_TUPLE.
        frequency_range_tuple: for a frequency plot, its own x-axis range
            (start_hz, end_hz) (LLFR-00258), or
            WHOLE_FREQUENCY_RANGE_TUPLE (the empty tuple) while it shows
            its whole frequency range; always () for a time plot, whose
            range is shared by every time plot (LLFR-00070) and kept by
            the controller. It is view state: it is not part of the undo
            states (plot_state_tuple), as zooms are not undoable
            (LLFR-00140).
    """

    def __init__(self, plot_id_i: int, random_generator,
                 marker_id_counter=None,
                 kind_str: str = TIME_PLOT_KIND_STR) -> None:
        """Create an empty plot.

        Inputs:
            plot_id_i: id of the plot, unique within the workspace.
            random_generator: random.Random used for curve colors.
            marker_id_counter: optional shared MarkerIdCounter for the
                delta marker ids.
            kind_str: TIME_PLOT_KIND_STR or FREQUENCY_PLOT_KIND_STR.
        Outputs: none. Raises ValueError for an unknown kind.
        """
        # LLFR-00256, HLFR-00058: a time plot or a frequency plot.
        if kind_str not in PLOT_KIND_TUPLE:
            raise ValueError(f"Unknown plot kind {kind_str!r}.")
        self.kind_str = kind_str
        # LLFR-00258: a new frequency plot shows its whole range.
        self.frequency_range_tuple = WHOLE_FREQUENCY_RANGE_TUPLE
        # LLFR-00019: a new plot starts with no curves and no tips.
        self.plot_id_i = plot_id_i
        self.random_generator = random_generator
        self.curve_list = []
        self.pinned_tip_list = []
        # LLFR-00033: counts every curve ever drawn here, for the colors.
        self.drawn_count_i = 0
        # LLFR-00164: delta marker ids come from the counter shared by
        # the workspace. LLFR-00205: vertical markers are not kept here;
        # they belong to the workspace and are shown on every plot.
        if marker_id_counter is None:
            marker_id_counter = MarkerIdCounter()
        self.marker_id_counter = marker_id_counter
        # LLFR-00164, LLFR-00174: any number of delta markers, in the
        # order they were placed.
        self.delta_marker_list = []
        # LLFR-00340: any number of text notes, in the order they were
        # written; they belong to this plot only.
        self.text_note_list = []
        # LLFR-00375: any number of arrows, in the order they were
        # drawn; they belong to this plot only.
        self.arrow_list = []

    def is_frequency_plot(self) -> bool:
        """Tell whether the plot is a frequency plot.

        Inputs: none.
        Outputs: True for a frequency plot, False for a time plot.
        """
        # LLFR-00256, HLFR-00058: frequency in Hz on the x-axis.
        return self.kind_str == FREQUENCY_PLOT_KIND_STR

    def set_frequency_range(self, start_hz: float, end_hz: float) -> bool:
        """Keep the x-axis range a frequency plot shows.

        Inputs:
            start_hz: start of the range, in Hz.
            end_hz: end of the range, in Hz, greater than start_hz.
        Outputs: True when the range was kept; False for a time plot or
            a range that is not finite or not increasing.
        """
        # LLFR-00258: each frequency plot has its own range; time plots
        # share theirs (LLFR-00070), which the plot does not keep.
        if not self.is_frequency_plot():
            return False
        start_hz = float(start_hz)
        end_hz = float(end_hz)
        if not (math.isfinite(start_hz) and math.isfinite(end_hz)
                and end_hz > start_hz):
            return False
        self.frequency_range_tuple = (start_hz, end_hz)
        return True

    def has_signal(self, signal_name_str: str) -> bool:
        """Tell whether the plot shows a signal.

        Inputs:
            signal_name_str: name of the signal.
        Outputs: True when a curve of that signal is in the plot.
        """
        # LLFR-00056: used to avoid drawing a signal twice.
        return self.find_curve(signal_name_str) is not None

    def find_curve(self, signal_name_str: str):
        """Return the curve of a signal in this plot.

        Inputs:
            signal_name_str: name of the signal.
        Outputs: the Curve, or None when the signal is not in the plot.
        """
        # LLFR-00039: curves are found by their signal name.
        for curve in self.curve_list:
            if curve.signal_name_str == signal_name_str:
                return curve
        return None

    def add_curve(self, signal_name_str: str):
        """Draw a signal in the plot.

        Inputs:
            signal_name_str: name of the signal to draw.
        Outputs: the new Curve, or None when the plot already shows the
            signal (LLFR-00056).
        """
        # LLFR-00056: a signal already in the plot is not drawn again;
        # checked before the color is picked, so a refused drop draws no
        # random color (LLFR-00034).
        if self.has_signal(signal_name_str):
            return None
        # LLFR-00033, LLFR-00034: pick a color not used in this plot.
        # LLFR-00052: a new curve uses preset width 1.
        return self.add_styled_curve(signal_name_str, self.next_color(),
                                     DEFAULT_WIDTH_I)

    def next_color(self) -> str:
        """Return the color the next new curve of this plot gets.

        Inputs: none.
        Outputs: the palette color of the next curve (LLFR-00033), or a
            random color from the 9th curve on (LLFR-00034); never a
            color that a curve of this plot already uses.
        """
        # LLFR-00033: the palette color in drawing order. LLFR-00235: a
        # plot rebuilt from a layout file may already use that palette
        # color for another curve, so palette colors in use are skipped.
        used_color_list = [curve.color_str for curve in self.curve_list]
        used_lower_set = {color_str.lower() for color_str in used_color_list}
        for palette_index_i in range(self.drawn_count_i,
                                     len(PALETTE_COLOR_TUPLE)):
            color_str = PALETTE_COLOR_TUPLE[palette_index_i]
            if color_str.lower() not in used_lower_set:
                return color_str
        # LLFR-00034: a random color different from every used color.
        return next_curve_color(len(PALETTE_COLOR_TUPLE), used_color_list,
                                self.random_generator)

    def add_styled_curve(self, signal_name_str: str, color_str: str,
                         width_i: int):
        """Draw a signal in the plot with a given color and width.

        Inputs:
            signal_name_str: name of the signal to draw.
            color_str: color of the curve, "#rrggbb", not used by another
                curve of the plot.
            width_i: preset width of the curve, one of PRESET_WIDTH_TUPLE.
        Outputs: the new Curve, or None when the plot already shows the
            signal (LLFR-00056). Raises ValueError for a width that is not
            a preset width.
        """
        # LLFR-00056: a signal already in the plot is not drawn again.
        if self.has_signal(signal_name_str):
            return None
        # LLFR-00041, LLFR-00235: only the preset widths 1 to 5.
        if isinstance(width_i, bool) or width_i not in PRESET_WIDTH_TUPLE:
            raise ValueError(f"Width {width_i!r} is not a preset width "
                             f"{PRESET_WIDTH_TUPLE}.")
        # LLFR-00230: a curve of a layout file keeps its saved color and
        # width; LLFR-00033: it counts as a drawn curve for the colors.
        curve = Curve(signal_name_str, str(color_str), int(width_i))
        self.curve_list.append(curve)
        self.drawn_count_i += 1
        return curve

    def remove_curve(self, signal_name_str: str) -> bool:
        """Remove a signal's curve, its pinned tips and delta markers.

        Inputs:
            signal_name_str: name of the signal to remove.
        Outputs: True when the curve was removed, False when the signal
            was not in the plot.
        """
        # LLFR-00039: remove the curve from the plot.
        curve = self.find_curve(signal_name_str)
        if curve is None:
            return False
        self.curve_list.remove(curve)
        # LLFR-00047: tips pinned on a removed curve go with it.
        self.pinned_tip_list = [
            pinned_tip for pinned_tip in self.pinned_tip_list
            if pinned_tip.signal_name_str != signal_name_str]
        # LLFR-00178: every delta marker with a point on that curve goes
        # too, in the same action (LLFR-00140 Note).
        self.remove_delta_markers_of_signal(signal_name_str)
        return True

    def set_curve_width(self, signal_name_str: str, width_i: int) -> None:
        """Set the width of a signal's curve.

        Inputs:
            signal_name_str: name of the signal.
            width_i: new width, one of PRESET_WIDTH_TUPLE.
        Outputs: none. Raises ValueError when the width is not a preset
            width or the signal is not in the plot.
        """
        # LLFR-00041: only the preset widths 1 to 5 are allowed.
        if isinstance(width_i, bool) or width_i not in PRESET_WIDTH_TUPLE:
            raise ValueError(f"Width {width_i!r} is not a preset width "
                             f"{PRESET_WIDTH_TUPLE}.")
        curve = self.find_curve(signal_name_str)
        if curve is None:
            raise ValueError(f"Signal {signal_name_str!r} is not in the "
                             f"plot.")
        curve.width_i = width_i

    def add_pinned_tip(self, signal_name_str: str, time_s: float,
                       value_f: float) -> PinnedTip:
        """Pin a tip at a point of a signal's curve.

        Inputs:
            signal_name_str: name of the signal whose curve was clicked.
            time_s: x-axis value of the point, in seconds.
            value_f: y-axis value of the point.
        Outputs: the new PinnedTip. Raises ValueError when the signal is
            not in the plot.
        """
        # LLFR-00045: the tip stays fixed at the clicked point.
        if not self.has_signal(signal_name_str):
            raise ValueError(f"Signal {signal_name_str!r} is not in the "
                             f"plot.")
        pinned_tip = PinnedTip(signal_name_str, time_s, value_f)
        self.pinned_tip_list.append(pinned_tip)
        return pinned_tip

    def remove_pinned_tip(self, pinned_tip: PinnedTip) -> bool:
        """Remove a pinned tip from the plot.

        Inputs:
            pinned_tip: the PinnedTip object to remove.
        Outputs: True when it was removed, False when it was not here.
        """
        # LLFR-00047: compare by identity, so that two tips at the same
        # point are removed one at a time.
        for index_i, held_tip in enumerate(self.pinned_tip_list):
            if held_tip is pinned_tip:
                del self.pinned_tip_list[index_i]
                return True
        return False

    def remove_all_pinned_tips(self) -> int:
        """Remove every pinned tip of the plot.

        Inputs: none.
        Outputs: the number of pinned tips removed.
        """
        # LLFR-00412: "Delete all data tips in this plot".
        removed_count_i = len(self.pinned_tip_list)
        self.pinned_tip_list = []
        return removed_count_i

    def move_pinned_tip(self, pinned_tip: PinnedTip,
                        label_offset_tuple: tuple) -> bool:
        """Move the label of a pinned tip; its point stays the same.

        Inputs:
            pinned_tip: the PinnedTip object to move.
            label_offset_tuple: the new offset (x, y), in points, from
                the tip's point to the center of its label.
        Outputs: True when the tip was moved, False when it is not in
            this plot. Raises ValueError when the offset is not two
            finite numbers.
        """
        # LLFR-00152, HLFR-00041: only the label moves; the signal, time
        # and value shown stay those of the same point.
        offset_tuple = tuple(label_offset_tuple)
        if len(offset_tuple) != 2:
            raise ValueError("A label offset needs an x and a y value.")
        offset_x_f, offset_y_f = (float(offset_tuple[0]),
                                  float(offset_tuple[1]))
        if not (math.isfinite(offset_x_f) and math.isfinite(offset_y_f)):
            raise ValueError("A label offset must be finite.")
        # LLFR-00152: compare by identity, as remove_pinned_tip does.
        for held_tip in self.pinned_tip_list:
            if held_tip is pinned_tip:
                held_tip.label_offset_tuple = (offset_x_f, offset_y_f)
                return True
        return False

    def add_text_note(self, text_str: str, time_s: float,
                      value_f: float):
        """Write a text note at a place of the plot.

        Inputs:
            text_str: the typed text.
            time_s: x-axis value of the place (s, or Hz on a frequency
                plot).
            value_f: y-axis value of the place.
        Outputs: the new TextNote, or None when the text is empty or made
            only of spaces (nothing is written). Raises ValueError when
            the place is not finite.
        """
        # LLFR-00334: a blank text creates no note.
        note_text_str = text_note_text(text_str)
        place_tuple = finite_place_tuple(time_s, value_f)
        if not note_text_str:
            return None
        # LLFR-00340: any number of notes per plot.
        text_note = TextNote(note_text_str, *place_tuple)
        self.text_note_list.append(text_note)
        return text_note

    def has_text_note_index(self, note_index_i: int) -> bool:
        """Tell whether an index points at a text note of the plot.

        Inputs:
            note_index_i: index in text_note_list.
        Outputs: True for a valid index.
        """
        # LLFR-00339, LLFR-00342, LLFR-00343: the view names a note by
        # its index in the list it last drew.
        return (isinstance(note_index_i, int)
                and 0 <= note_index_i < len(self.text_note_list))

    def edit_text_note(self, note_index_i: int, text_str: str) -> bool:
        """Change the text of a text note.

        Inputs:
            note_index_i: index of the note in text_note_list.
            text_str: the typed text.
        Outputs: True when the text changed; False for an unknown index,
            a blank text (the previous text is kept) or the same text.
        """
        # LLFR-00342: a blank text keeps the previous one.
        note_text_str = text_note_text(text_str)
        if not note_text_str or not self.has_text_note_index(note_index_i):
            return False
        text_note = self.text_note_list[note_index_i]
        if text_note.text_str == note_text_str:
            return False
        text_note.text_str = note_text_str
        return True

    def move_text_note(self, note_index_i: int, time_s: float,
                       value_f: float) -> bool:
        """Attach a text note to another place of the plot.

        Inputs:
            note_index_i: index of the note in text_note_list.
            time_s: new x-axis value (s, or Hz on a frequency plot).
            value_f: new y-axis value.
        Outputs: True when the note moved; False for an unknown index or
            the same place. Raises ValueError when the place is not
            finite.
        """
        # LLFR-00339: the note is attached to the values of the place
        # where the button was released.
        place_tuple = finite_place_tuple(time_s, value_f)
        if not self.has_text_note_index(note_index_i):
            return False
        text_note = self.text_note_list[note_index_i]
        if (text_note.time_s, text_note.value_f) == place_tuple:
            return False
        text_note.time_s, text_note.value_f = place_tuple
        return True

    def remove_text_note(self, note_index_i: int) -> bool:
        """Remove a text note from the plot.

        Inputs:
            note_index_i: index of the note in text_note_list.
        Outputs: True when it was removed, False for an unknown index.
        """
        # LLFR-00343: the note leaves the plot.
        if not self.has_text_note_index(note_index_i):
            return False
        del self.text_note_list[note_index_i]
        return True

    def set_text_note_size(self, note_index_i: int, size_i: int) -> bool:
        """Give the text of a text note another chosen size.

        Inputs:
            note_index_i: index of the note in text_note_list.
            size_i: the size in points, one of TEXT_NOTE_SIZE_TUPLE.
        Outputs: True when the size changed; False for an unknown index,
            a size that is not a preset or the note's current size.
        """
        # LLFR-00385: one of the preset sizes; LLFR-00386: the chosen
        # size is kept as chosen, whatever size the view can draw.
        if (not self.has_text_note_index(note_index_i)
                or isinstance(size_i, bool)
                or size_i not in TEXT_NOTE_SIZE_TUPLE):
            return False
        text_note = self.text_note_list[note_index_i]
        if text_note.size_i == int(size_i):
            return False
        text_note.size_i = int(size_i)
        return True

    def set_text_note_border_color(self, note_index_i: int,
                                   color_str: str) -> bool:
        """Give the border of a text note another color.

        Inputs:
            note_index_i: index of the note in text_note_list.
            color_str: the color, written as "#rrggbb" (any case).
        Outputs: True when the color changed; False for an unknown index,
            a value that is not "#rrggbb" or the current border color.
        """
        # LLFR-00387, LLFR-00390: the confirmed color, but nothing when
        # it is the color the border already has.
        new_color_str = hex_color_or_none(color_str)
        if new_color_str is None or not self.has_text_note_index(
                note_index_i):
            return False
        text_note = self.text_note_list[note_index_i]
        if text_note.border_color_str == new_color_str:
            return False
        text_note.border_color_str = new_color_str
        return True

    def set_text_note_text_color(self, note_index_i: int,
                                 color_str: str) -> bool:
        """Give the text of a text note another color.

        Inputs:
            note_index_i: index of the note in text_note_list.
            color_str: the color, written as "#rrggbb" (any case).
        Outputs: True when the color changed; False for an unknown index,
            a value that is not "#rrggbb" or the current text color.
        """
        # LLFR-00387, LLFR-00390: the confirmed color, but nothing when
        # it is the color the text already has.
        new_color_str = hex_color_or_none(color_str)
        if new_color_str is None or not self.has_text_note_index(
                note_index_i):
            return False
        text_note = self.text_note_list[note_index_i]
        if text_note.text_color_str == new_color_str:
            return False
        text_note.text_color_str = new_color_str
        return True

    def add_arrow(self, start_time_s: float, start_value_f: float,
                  end_time_s: float, end_value_f: float,
                  name_str: str = "") -> Arrow:
        """Draw a new arrow on the plot.

        Inputs:
            start_time_s: x value of the press point (s, or Hz on a
                frequency plot).
            start_value_f: y value of the press point.
            end_time_s: x value of the release point, where the
                arrowhead is.
            end_value_f: y value of the release point.
            name_str: the name of its label (LLFR-00436); the workspace
                gives a new arrow "Arrow N" (Workspace.take_arrow_name).
                Empty or blank gives "Arrow N" with the smallest N not
                used by an arrow of this plot.
        Outputs: the new Arrow, in the default color. Raises ValueError
            when a value is not finite or the two ends are the same.
        """
        # LLFR-00372: from the press to the release, with the arrowhead
        # at the release. LLFR-00373: in the default color.
        end_tuple = finite_arrow_tuple(start_time_s, start_value_f,
                                       end_time_s, end_value_f)
        # LLFR-00438: every arrow has a name.
        arrow_name_str = str(name_str).strip()
        if not arrow_name_str:
            used_name_set = {arrow.name_str for arrow in self.arrow_list}
            arrow_name_str = first_free_name(DEFAULT_ARROW_NAME_FORMAT_STR,
                                             used_name_set)
        # LLFR-00375: any number of arrows per plot.
        arrow = Arrow(*end_tuple, name_str=arrow_name_str)
        self.arrow_list.append(arrow)
        return arrow

    def rename_arrow(self, arrow_index_i: int, new_name_str: str) -> bool:
        """Give an arrow the name typed by the user.

        Inputs:
            arrow_index_i: index of the arrow in arrow_list.
            new_name_str: the typed name; surrounding spaces are removed.
        Outputs: True when the name changed; False for an unknown index,
            a name that is empty or only spaces (LLFR-00874) or the
            current name.
        """
        # LLFR-00439, LLFR-00873: the label shows the typed name.
        # LLFR-00874: a blank name keeps the previous one.
        stripped_name_str = str(new_name_str).strip()
        if not stripped_name_str or not self.has_arrow_index(arrow_index_i):
            return False
        arrow = self.arrow_list[arrow_index_i]
        if arrow.name_str == stripped_name_str:
            return False
        # LLFR-00876: the ends and the color stay as they are.
        arrow.name_str = stripped_name_str
        return True

    def has_arrow_index(self, arrow_index_i: int) -> bool:
        """Tell whether an index points at an arrow of the plot.

        Inputs:
            arrow_index_i: index in arrow_list.
        Outputs: True for a valid index.
        """
        # LLFR-00376, LLFR-00377, LLFR-00379, LLFR-00380: the view names
        # an arrow by its index in the list it last drew.
        return (isinstance(arrow_index_i, int)
                and not isinstance(arrow_index_i, bool)
                and 0 <= arrow_index_i < len(self.arrow_list))

    def set_arrow_ends(self, arrow_index_i: int, start_time_s: float,
                       start_value_f: float, end_time_s: float,
                       end_value_f: float) -> bool:
        """Give an arrow new ends, after a move, a rotation or a stretch.

        Inputs:
            arrow_index_i: index of the arrow in arrow_list.
            start_time_s: new x value of the end without the arrowhead.
            start_value_f: new y value of that end.
            end_time_s: new x value of the arrowhead's end.
            end_value_f: new y value of the arrowhead's end.
        Outputs: True when the arrow changed; False for an unknown index
            or the same ends. Raises ValueError when a value is not
            finite or the two ends are the same.
        """
        # LLFR-00376, LLFR-00377: attached to the values of its new ends;
        # the arrowhead stays at the end it was at.
        end_tuple = finite_arrow_tuple(start_time_s, start_value_f,
                                       end_time_s, end_value_f)
        if not self.has_arrow_index(arrow_index_i):
            return False
        arrow = self.arrow_list[arrow_index_i]
        if arrow_end_tuple(arrow) == end_tuple:
            return False
        (arrow.start_time_s, arrow.start_value_f, arrow.end_time_s,
         arrow.end_value_f) = end_tuple
        return True

    def set_arrow_color(self, arrow_index_i: int, color_str: str) -> bool:
        """Give an arrow another color.

        Inputs:
            arrow_index_i: index of the arrow in arrow_list.
            color_str: the color, written as "#rrggbb" (any case).
        Outputs: True when the color changed; False for an unknown index,
            a value that is not "#rrggbb" or the current color.
        """
        # LLFR-00379, LLFR-00390: the confirmed color, but nothing when
        # it is the color the arrow already has.
        new_color_str = hex_color_or_none(color_str)
        if new_color_str is None or not self.has_arrow_index(arrow_index_i):
            return False
        arrow = self.arrow_list[arrow_index_i]
        if arrow.color_str == new_color_str:
            return False
        arrow.color_str = new_color_str
        return True

    def remove_arrow(self, arrow_index_i: int) -> bool:
        """Remove an arrow from the plot.

        Inputs:
            arrow_index_i: index of the arrow in arrow_list.
        Outputs: True when it was removed, False for an unknown index.
        """
        # LLFR-00380: the arrow leaves the plot.
        if not self.has_arrow_index(arrow_index_i):
            return False
        del self.arrow_list[arrow_index_i]
        return True

    def is_empty(self) -> bool:
        """Tell whether the plot has no curves.

        Inputs: none.
        Outputs: True when the plot has no curves.
        """
        # LLFR-00051: an empty plot is deleted by the workspace; markers
        # are not curves, so they do not keep the plot alive.
        return not self.curve_list

    def add_delta_marker(self, kind_str: str, first_point_tuple,
                         second_point_tuple,
                         color_str: str = DEFAULT_DELTA_MARKER_COLOR_STR,
                         name_str: str = "") -> DeltaMarker:
        """Place a new delta marker between two curve points.

        Inputs:
            kind_str: DELTA_X_KIND_STR or DELTA_Y_KIND_STR.
            first_point_tuple: (signal_name_str, time_s, value_f) of the
                first picked point.
            second_point_tuple: the same for the second picked point; it
                may be on the same curve or on another one.
            color_str: its color, "#rrggbb" (any case); a new marker gets
                the default color (LLFR-00172), a marker of a layout file
                its saved color (LLFR-00410). A value that is not
                "#rrggbb" gives the default color.
            name_str: the name of its label (LLFR-00427); the workspace
                gives a new marker "Delta X N" or "Delta Y N"
                (Workspace.take_delta_marker_name), a marker of a layout
                file its saved name (LLFR-00430). Empty or blank gives
                the default name with the smallest N not used by a
                marker of that kind in this plot.
        Outputs: the new DeltaMarker. Raises ValueError for an unknown
            kind, a point that is not finite, a point on a signal that
            is not in the plot, or two points that give a value of zero
            (LLFR-00431).
        """
        # LLFR-00168, LLFR-00170: a Delta X or a Delta Y marker.
        if kind_str not in DELTA_KIND_TUPLE:
            raise ValueError(f"Unknown delta marker kind {kind_str!r}.")
        first_point_tuple = delta_point_tuple(first_point_tuple)
        second_point_tuple = delta_point_tuple(second_point_tuple)
        # LLFR-00164: both points are on curves of this plot.
        for point_tuple in (first_point_tuple, second_point_tuple):
            if not self.has_signal(point_tuple[0]):
                raise ValueError(f"Signal {point_tuple[0]!r} is not in "
                                 f"the plot.")
        # LLFR-00431, LLFR-00486: never a delta marker of value zero.
        if delta_value_zero_b(kind_str, first_point_tuple,
                              second_point_tuple):
            raise ValueError("A delta marker must not measure zero.")
        # LLFR-00172, LLFR-00410: the default color unless a usable
        # color is given.
        marker_color_str = hex_color_or_none(color_str)
        if marker_color_str is None:
            marker_color_str = DEFAULT_DELTA_MARKER_COLOR_STR
        # LLFR-00428: every delta marker has a name.
        marker_name_str = str(name_str).strip()
        if not marker_name_str:
            used_name_set = {delta_marker.name_str for delta_marker
                             in self.delta_marker_list}
            marker_name_str = first_free_name(
                DEFAULT_DELTA_NAME_FORMAT_DICT[kind_str], used_name_set)
        # LLFR-00174: markers are added, never replaced.
        delta_marker = DeltaMarker(self.marker_id_counter.take_next_id(),
                                   kind_str, first_point_tuple,
                                   second_point_tuple, marker_color_str,
                                   marker_name_str)
        self.delta_marker_list.append(delta_marker)
        return delta_marker

    def rename_delta_marker(self, delta_marker_id_i: int,
                            new_name_str: str) -> bool:
        """Give one delta marker of this plot the name typed by the user.

        Inputs:
            delta_marker_id_i: id of the delta marker.
            new_name_str: the typed name; surrounding spaces are removed.
        Outputs: True when the name changed; False when no delta marker
            of this plot has that id, the name is empty or only spaces
            (LLFR-00854) or it is the current name.
        """
        # LLFR-00429, LLFR-00853: the label shows the typed name.
        # LLFR-00854: a blank name keeps the previous one.
        stripped_name_str = str(new_name_str).strip()
        delta_marker = self.find_delta_marker(delta_marker_id_i)
        if delta_marker is None or not stripped_name_str:
            return False
        if delta_marker.name_str == stripped_name_str:
            return False
        # LLFR-00856: the points, the value and the color stay as they
        # are.
        delta_marker.name_str = stripped_name_str
        return True

    def set_delta_marker_color(self, delta_marker_id_i: int,
                               color_str: str) -> bool:
        """Give one delta marker of this plot another color.

        Inputs:
            delta_marker_id_i: id of the delta marker.
            color_str: the color, written as "#rrggbb" (any case).
        Outputs: True when the color changed; False when no delta marker
            of this plot has that id, the value is not "#rrggbb" or it is
            the marker's current color.
        """
        # LLFR-00409, LLFR-00390: the chosen color, but nothing when it
        # is the color the marker already has; the points, the value and
        # the other delta markers stay as they are.
        new_color_str = hex_color_or_none(color_str)
        delta_marker = self.find_delta_marker(delta_marker_id_i)
        if delta_marker is None or new_color_str is None:
            return False
        if delta_marker.color_str == new_color_str:
            return False
        delta_marker.color_str = new_color_str
        return True

    def find_delta_marker(self, delta_marker_id_i: int):
        """Return a delta marker of this plot by its id.

        Inputs:
            delta_marker_id_i: id of the delta marker.
        Outputs: the DeltaMarker, or None when it is not in this plot.
        """
        # LLFR-00176: delta markers are found by id to delete them.
        for delta_marker in self.delta_marker_list:
            if delta_marker.delta_marker_id_i == delta_marker_id_i:
                return delta_marker
        return None

    def move_delta_marker_point(self, delta_marker_id_i: int,
                                point_index_i: int, time_s: float,
                                value_f: float) -> bool:
        """Move one point of a delta marker to another sample of its curve.

        Inputs:
            delta_marker_id_i: id of the delta marker.
            point_index_i: 0 for the first point, 1 for the second one.
            time_s: time of the new sample (its frequency, in Hz, on a
                frequency plot).
            value_f: value of the new sample.
        Outputs: True when the point moved; False when no delta marker
            of this plot has that id, the index is not 0 or 1, a number
            is not finite, the new point would give a value of zero
            (LLFR-00435), or the point is already there.
        """
        # LLFR-00433: the dragged point is left on the chosen sample.
        delta_marker = self.find_delta_marker(delta_marker_id_i)
        if delta_marker is None or point_index_i not in (0, 1):
            return False
        point_list = [delta_marker.first_point_tuple,
                      delta_marker.second_point_tuple]
        # LLFR-00862: the point stays on the same curve.
        try:
            new_point_tuple = delta_point_tuple(
                (point_list[point_index_i][0], time_s, value_f))
        except (TypeError, ValueError):
            return False
        if new_point_tuple == point_list[point_index_i]:
            return False
        # LLFR-00863: the other point stays in place.
        point_list[point_index_i] = new_point_tuple
        # LLFR-00435: never a value of zero.
        if delta_value_zero_b(delta_marker.kind_str, point_list[0],
                              point_list[1]):
            return False
        delta_marker.first_point_tuple = point_list[0]
        delta_marker.second_point_tuple = point_list[1]
        return True

    def remove_delta_marker(self, delta_marker_id_i: int) -> bool:
        """Remove a delta marker from the plot.

        Inputs:
            delta_marker_id_i: id of the delta marker.
        Outputs: True when it was removed, False when it is not in this
            plot.
        """
        # LLFR-00176: "Delete" in the delta marker menu.
        delta_marker = self.find_delta_marker(delta_marker_id_i)
        if delta_marker is None:
            return False
        self.delta_marker_list.remove(delta_marker)
        return True

    def remove_all_delta_markers(self) -> int:
        """Remove every Delta X and Delta Y marker of the plot.

        Inputs: none.
        Outputs: the number of delta markers removed.
        """
        # LLFR-00414: "Delete all delta markers in this plot".
        removed_count_i = len(self.delta_marker_list)
        self.delta_marker_list = []
        return removed_count_i

    def remove_delta_markers_of_signal(self, signal_name_str: str) -> int:
        """Remove every delta marker with a point on a signal's curve.

        Inputs:
            signal_name_str: name of the signal.
        Outputs: the number of delta markers removed.
        """
        # LLFR-00178: the markers that measure on a removed curve.
        kept_list = [delta_marker for delta_marker in self.delta_marker_list
                     if not delta_marker.has_point_on(signal_name_str)]
        removed_count_i = len(self.delta_marker_list) - len(kept_list)
        self.delta_marker_list = kept_list
        return removed_count_i


def is_matrix_size(size_value) -> bool:
    """Tell whether a value is a number of rows or columns of a matrix.

    Inputs:
        size_value: any value.
    Outputs: True for a whole number (not a bool) from
        MINIMUM_MATRIX_SIZE_I to MAXIMUM_MATRIX_SIZE_I.
    """
    # LLFR-01097: a plot matrix has 1 to 10 rows and 1 to 10 columns.
    if isinstance(size_value, bool) or not isinstance(size_value, int):
        return False
    return MINIMUM_MATRIX_SIZE_I <= size_value <= MAXIMUM_MATRIX_SIZE_I


def matrix_slot_tuple(plot_index_i: int, column_count_i: int) -> tuple:
    """Return the slot of a plot in the fill order of a plot matrix.

    Inputs:
        plot_index_i: place of the plot in the tab's plot list, from 0.
        column_count_i: number of columns of the plot matrix, 1 or more.
    Outputs: (row_index_i, column_index_i), both counted from 0.
    """
    # LLFR-01108: row 1 is filled from left to right up to the number
    # of columns, then row 2, and so on.
    return divmod(int(plot_index_i), max(int(column_count_i), 1))


def matrix_row_list(item_list: list, column_count_i: int) -> list:
    """Split the plots of a tab into the rows of its plot matrix.

    Inputs:
        item_list: the plots (or their ids or widgets), in fill order.
        column_count_i: number of columns of the plot matrix.
    Outputs: one list per row that holds at least one plot, top to
        bottom, each with its plots from left to right. The last row
        may hold fewer plots than the number of columns.
    """
    # LLFR-01108: the fill order; LLFR-01110: only the rows in use.
    column_count_i = max(int(column_count_i), 1)
    return [list(item_list[start_i:start_i + column_count_i])
            for start_i in range(0, len(item_list), column_count_i)]


class Tab:
    """A tab of the plot panel, holding plots in its plot matrix.

    Inputs:
        tab_id_i: id of the tab, unique within the workspace.
        name_str: name shown on the tab.
    Attributes:
        plot_list: the plots, in the fill order of the plot matrix
            (LLFR-01108).
        row_count_i: number of rows of the plot matrix (HLFR-00146).
        column_count_i: number of columns of the plot matrix.
        window_id_i: id of the undocked window that holds the tab
            (HLFR-00124, HLFR-00126), unique within the workspace; 0
            while it is a docked tab of the main window. The tabs of one
            window share their window values below.
        undocked_b: (read-only) True while the tab is in an undocked
            window.
        window_shown_b: True for the tab that its undocked window shows
            (LLFR-01061, LLFR-01156).
        window_tuple: (x, y, width, height) of its undocked window, in
            desktop pixels, with the position of the window's top-left
            corner (LLFR-01075); () when unknown.
        panel_shown_b: True while the signal list panel of its undocked
            window is shown (LLFR-01047, LLFR-01048).
        panel_width_i: width of that panel, in pixels, also while it is
            hidden (the width it gets back, LLFR-01048); 0 while it was
            never shown, so that its first width is chosen when it is
            shown (LLFR-01051).
    """

    def __init__(self, tab_id_i: int, name_str: str) -> None:
        """Create a tab with no plots and the default plot matrix.

        Inputs:
            tab_id_i: id of the tab, unique within the workspace.
            name_str: name shown on the tab.
        Outputs: none.
        """
        # LLFR-00026: a new tab has no plots.
        self.tab_id_i = tab_id_i
        self.name_str = name_str
        # LLFR-01108: plots in the fill order of the plot matrix.
        self.plot_list = []
        # LLFR-01122: every new tab gets the 5 x 1 plot matrix.
        self.row_count_i = DEFAULT_MATRIX_ROWS_I
        self.column_count_i = DEFAULT_MATRIX_COLUMNS_I
        # LLFR-00025, LLFR-01012: a new tab is a docked tab of the main
        # window.
        self.window_id_i = 0
        # LLFR-01061, LLFR-01156: whether its undocked window shows it.
        self.window_shown_b = False
        # LLFR-01075, LLFR-01059: the window an undo or a layout opens
        # again; set by an undock.
        self.window_tuple = ()
        # LLFR-01050, LLFR-01051: the panel of a new undocked window is
        # hidden and was never shown.
        self.panel_shown_b = False
        self.panel_width_i = 0

    @property
    def undocked_b(self) -> bool:
        """Tell whether the tab is in an undocked window.

        Inputs: none.
        Outputs: True while it is in an undocked window (HLFR-00124).
        """
        # LLFR-01015, LLFR-01028: an undocked tab has a window id.
        return self.window_id_i > 0

    def copy_window_values(self, other_tab) -> None:
        """Give the tab the window values of another tab of a window.

        Inputs:
            other_tab: a Tab of the window that the tab joins.
        Outputs: none. The tab gets its window id, position, size and
            signal list panel.
        """
        # LLFR-01150, LLFR-01159: the tabs of one window share them.
        self.window_id_i = other_tab.window_id_i
        self.window_tuple = tuple(other_tab.window_tuple)
        self.panel_shown_b = bool(other_tab.panel_shown_b)
        self.panel_width_i = int(other_tab.panel_width_i)

    def slot_count(self) -> int:
        """Return the number of slots of the tab's plot matrix.

        Inputs: none.
        Outputs: its number of rows times its number of columns.
        """
        # HLFR-00018, LLFR-00031: the most plots the tab can hold.
        return self.row_count_i * self.column_count_i

    def is_full(self) -> bool:
        """Tell whether every slot of the plot matrix holds a plot.

        Inputs: none.
        Outputs: True when no more plots can be added (LLFR-00031).
        """
        # LLFR-00031: a full tab blocks new plots; HLFR-00018: the
        # maximum is the number of slots of the plot matrix.
        return len(self.plot_list) >= self.slot_count()

    def can_take_matrix(self, row_count_i: int, column_count_i: int) -> bool:
        """Tell whether the tab may get a plot matrix.

        Inputs:
            row_count_i: number of rows asked for.
            column_count_i: number of columns asked for.
        Outputs: True when both are from 1 to 10 and the matrix has at
            least as many slots as the tab has plots (LLFR-01106).
        """
        # LLFR-01097: 1 to 10 rows and columns.
        if not (is_matrix_size(row_count_i)
                and is_matrix_size(column_count_i)):
            return False
        # LLFR-01106, LLFR-01107, HLFR-00147: a matrix too small for the
        # plots of the tab cannot be chosen.
        return row_count_i * column_count_i >= len(self.plot_list)

    def find_plot(self, plot_id_i: int):
        """Return a plot of this tab by its id.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: the Plot, or None when it is not in this tab.
        """
        # LLFR-00049: plots are found by id to delete them.
        for plot in self.plot_list:
            if plot.plot_id_i == plot_id_i:
                return plot
        return None

    def window_state_tuple(self) -> tuple:
        """Return what an undo or a redo restores of the tab's window.

        Inputs: none.
        Outputs: (window_id_i, panel_shown_b, panel_width_i). The window
            position and size are not part of it: moving or resizing a
            window is not an undoable action (LLFR-01056, LLFR-00140);
            nor is the tab a window shows.
        """
        # LLFR-01060: undocking and docking are undoable; LLFR-01153:
        # moving a tab into another window; LLFR-01053: hiding and
        # showing the panel; LLFR-01055: a panel width drag.
        return (int(self.window_id_i), bool(self.panel_shown_b),
                int(self.panel_width_i))


# LLFR-01051: the share of an undocked window that its signal list
# panel takes the first time it is shown.
FIRST_PANEL_WIDTH_FRACTION_F = 0.20


def first_panel_width_i(main_panel_width_i: int, window_width_i: int) -> int:
    """Return the width of a panel shown for the first time.

    Inputs:
        main_panel_width_i: width of the signal list panel of the main
            window, in pixels (0 when unknown), used only when the
            window's width is unknown.
        window_width_i: width of the undocked window, in pixels (0 when
            unknown).
    Outputs: 20% of the window's width, rounded to whole pixels, or the
        main panel's width when the window's width is unknown; at least
        1 pixel.
    """
    # LLFR-01051: 20% of the undocked window's width, as the main
    # window's panel starts at 20% of its window (LLFR-00072).
    if int(window_width_i) > 1:
        return max(int(round(int(window_width_i)
                             * FIRST_PANEL_WIDTH_FRACTION_F)), 1)
    return max(int(main_panel_width_i), 1)


def arrow_end_tuple(arrow) -> tuple:
    """Return the two ends of an arrow as plain values.

    Inputs:
        arrow: an Arrow.
    Outputs: (start_time_s, start_value_f, end_time_s, end_value_f).
    """
    # LLFR-00374: the values the arrow is attached to.
    return (arrow.start_time_s, arrow.start_value_f, arrow.end_time_s,
            arrow.end_value_f)


def plot_state_tuple(plot) -> tuple:
    """Return everything an undo restores of a plot, as plain values.

    Inputs:
        plot: the Plot.
    Outputs: a tuple (plot_id_i, drawn_count_i, curve tuples
        (signal_name_str, color_str, width_i), pinned tip tuples
        (signal_name_str, time_s, value_f, label_offset_tuple), delta
        marker tuples (delta_marker_id_i, kind_str, first_point_tuple,
        second_point_tuple, color_str, name_str), text note tuples
        (text_str, time_s, value_f, size_i, border_color_str,
        text_color_str), arrow tuples (start_time_s, start_value_f,
        end_time_s, end_value_f, color_str, name_str), plot kind_str).
        For a frequency plot, the time_s of the tips, delta marker
        points, text notes and arrows is a frequency in Hz.
    """
    # LLFR-00140: curves with color and width, pinned tips with their
    # label offsets, and the counter that picks the next color. The
    # vertical markers belong to the workspace (LLFR-00205), see
    # Workspace.state_tuple.
    curve_tuple = tuple((curve.signal_name_str, curve.color_str,
                         curve.width_i) for curve in plot.curve_list)
    pinned_tip_tuple = tuple(
        (pinned_tip.signal_name_str, pinned_tip.time_s, pinned_tip.value_f,
         tuple(pinned_tip.label_offset_tuple))
        for pinned_tip in plot.pinned_tip_list)
    # LLFR-00140: placing, changing the color of (LLFR-00409) and
    # deleting a delta marker are undoable.
    delta_marker_tuple = tuple(
        (delta_marker.delta_marker_id_i, delta_marker.kind_str,
         tuple(delta_marker.first_point_tuple),
         tuple(delta_marker.second_point_tuple), delta_marker.color_str,
         delta_marker.name_str)
        for delta_marker in plot.delta_marker_list)
    # LLFR-00256, LLFR-00140: creating a frequency plot is undoable like
    # creating a time plot, and an undo gives the plot back its kind.
    # LLFR-00140: creating, moving, editing and deleting a text note are
    # undoable; LLFR-00340: the notes are part of their plot's state.
    # LLFR-00385, LLFR-00387: changing a note's size, border color or
    # text color is undoable too.
    text_note_tuple = tuple(
        (text_note.text_str, text_note.time_s, text_note.value_f,
         text_note.size_i, text_note.border_color_str,
         text_note.text_color_str)
        for text_note in plot.text_note_list)
    # LLFR-00140: drawing, moving, rotating or stretching, recoloring and
    # deleting an arrow are undoable; LLFR-00375: the arrows are part of
    # their plot's state.
    # LLFR-00140: renaming a delta marker or an arrow is undoable too.
    arrow_tuple = tuple(arrow_end_tuple(arrow) + (arrow.color_str,
                                                  arrow.name_str)
                        for arrow in plot.arrow_list)
    return (plot.plot_id_i, plot.drawn_count_i, curve_tuple,
            pinned_tip_tuple, delta_marker_tuple, text_note_tuple,
            arrow_tuple, plot.kind_str)


def tabs_state_tuple(tab_list: list, marker_list: list,
                     area_list=(), main_panel_width_i: int = 0,
                     grid_shown_b: bool = True,
                     main_panel_shown_b: bool = True) -> tuple:
    """Return tabs, vertical markers and areas as plain values.

    Inputs:
        tab_list: the Tab objects, in tab order.
        marker_list: the VerticalMarker objects, in placing order.
        area_list: the Area objects, in creation order.
        main_panel_width_i: width of the signal list panel of the main
            window, in pixels, 0 when unknown.
        grid_shown_b: True while the grid is shown (LLFR-01132).
        main_panel_shown_b: True while the main window shows its signal
            list panel (LLFR-01053, LLFR-01205).
    Outputs: a tuple (tab tuple, marker tuple, area tuple, main panel
        width, grid shown, main panel shown): one entry (tab_id_i,
        name_str, plot state tuples, row_count_i, column_count_i,
        window state tuple) per tab, in tab order, one entry
        (marker_id_i, name_str, time_s, color_str) per marker and one
        entry (area_id_i, name_str, start_s, end_s, color_str) per area;
        two states with equal tuples show the same thing (LLFR-00140).
    """
    # LLFR-00138, LLFR-00140: what an undo restores. LLFR-01089: the
    # order of the tabs; LLFR-01120: the order of the plots, which is
    # their fill order; LLFR-01103: the plot matrix of each tab.
    tab_tuple = tuple(
        (tab.tab_id_i, tab.name_str,
         tuple(plot_state_tuple(plot) for plot in tab.plot_list),
         tab.row_count_i, tab.column_count_i,
         # LLFR-01060, LLFR-01053, LLFR-01055: docked or undocked, and
         # the shown state and width of the window's panel.
         tab.window_state_tuple())
        for tab in tab_list)
    # LLFR-00392, LLFR-00140: changing a flag's color is undoable.
    marker_tuple = tuple((marker.marker_id_i, marker.name_str, marker.time_s,
                          marker.color_str)
                         for marker in marker_list)
    # LLFR-00140: creating, moving, resizing, renaming and deleting an
    # area are undoable.
    # LLFR-00351: and changing its color.
    area_tuple = tuple((area.area_id_i, area.name_str, area.start_s,
                        area.end_s, area.color_str)
                       for area in area_list)
    # LLFR-01055: a drag of the main window's panel border is undoable;
    # LLFR-01132: and so is a click on the Grid button.
    # LLFR-01053, LLFR-01205: hiding or showing the main window's panel
    # is undoable too.
    return (tab_tuple, marker_tuple, area_tuple, int(main_panel_width_i),
            bool(grid_shown_b), bool(main_panel_shown_b))


def renamed_point_tuple(point_tuple: tuple, old_name_str: str,
                        new_name_str: str) -> tuple:
    """Return a delta marker point with a signal name replaced.

    Inputs:
        point_tuple: (signal_name_str, time_s, value_f).
        old_name_str: the signal name to replace.
        new_name_str: the name that replaces it.
    Outputs: the same point, on new_name_str when it was on old_name_str.
    """
    # LLFR-00266: a renamed synthetic signal keeps its delta markers.
    if point_tuple[0] != old_name_str:
        return point_tuple
    return (new_name_str,) + tuple(point_tuple[1:])


def rename_signal_in_tabs(tab_list: list, old_name_str: str,
                          new_name_str: str) -> bool:
    """Rename a signal in every curve, pinned tip and delta marker.

    Inputs:
        tab_list: the Tab objects to update in place.
        old_name_str: the current name of the signal.
        new_name_str: its new name, not used by another curve.
    Outputs: True when at least one curve was renamed.
    """
    # LLFR-00266: every plot that draws the signal shows the new name in
    # its legend; its color, width, tips and delta markers are kept.
    renamed_b = False
    for tab in tab_list:
        for plot in tab.plot_list:
            for curve in plot.curve_list:
                if curve.signal_name_str == old_name_str:
                    curve.signal_name_str = new_name_str
                    renamed_b = True
            for pinned_tip in plot.pinned_tip_list:
                if pinned_tip.signal_name_str == old_name_str:
                    pinned_tip.signal_name_str = new_name_str
            for delta_marker in plot.delta_marker_list:
                delta_marker.first_point_tuple = renamed_point_tuple(
                    delta_marker.first_point_tuple, old_name_str,
                    new_name_str)
                delta_marker.second_point_tuple = renamed_point_tuple(
                    delta_marker.second_point_tuple, old_name_str,
                    new_name_str)
    return renamed_b


class WorkspaceSnapshot:
    """A saved copy of the tabs, plots, curves, tips and markers.

    The copy shares nothing that an action can change with the live
    workspace, so later actions do not change it (LLFR-00138).

    Inputs:
        tab_list: deep copy of the workspace's tabs, in order.
        state_tuple: the plain-value dump of those tabs (see
            Workspace.state_tuple), used to tell whether an action
            changed anything.
        current_tab_id_i: id of the tab that was selected, -1 when
            unknown.
        marker_list: copy of the workspace's vertical markers
            (LLFR-00205), in placing order.
        area_list: copy of the workspace's areas (LLFR-00310), in
            creation order.
        main_panel_width_i: width of the main window's signal list
            panel, in pixels, 0 when unknown (LLFR-01055).
        grid_shown_b: True when the grid was shown (LLFR-01132).
    """

    def __init__(self, tab_list: list, state_tuple: tuple,
                 current_tab_id_i: int = -1, marker_list=(),
                 area_list=(), main_panel_width_i: int = 0,
                 grid_shown_b: bool = True,
                 main_panel_shown_b: bool = True) -> None:
        """Store the saved state.

        Inputs:
            tab_list: deep copy of the tabs.
            state_tuple: plain-value dump of the tabs and markers.
            current_tab_id_i: id of the selected tab, -1 when unknown.
            marker_list: copies of the vertical markers.
            area_list: copies of the areas.
        Outputs: none.
        """
        # LLFR-00138: the state to return to. LLFR-00205: the shared
        # vertical markers are part of it.
        self.tab_list = tab_list
        self.state_tuple = state_tuple
        self.current_tab_id_i = current_tab_id_i
        self.marker_list = list(marker_list)
        # LLFR-00310, LLFR-00138: the shared areas are part of it too.
        self.area_list = list(area_list)
        # LLFR-01055, LLFR-00138: and the main window's panel width.
        self.main_panel_width_i = int(main_panel_width_i)
        # LLFR-01132, LLFR-00138: and whether the grid was shown.
        self.grid_shown_b = bool(grid_shown_b)
        # LLFR-01053, LLFR-00138: and whether the main window showed its
        # signal list panel.
        self.main_panel_shown_b = bool(main_panel_shown_b)

    def rename_signal(self, old_name_str: str, new_name_str: str) -> None:
        """Rename a signal in the saved state.

        Inputs:
            old_name_str: the current name of the signal.
            new_name_str: its new name.
        Outputs: none. The saved state is changed in place, so that an
            undo or a redo after the rename draws the curves of the
            signal under its new name.
        """
        # LLFR-00266: renaming a synthetic signal keeps the undo and
        # redo history, whose states must then use the new name.
        rename_signal_in_tabs(self.tab_list, old_name_str, new_name_str)
        self.state_tuple = tabs_state_tuple(self.tab_list,
                                            self.marker_list,
                                            self.area_list,
                                            self.main_panel_width_i,
                                            self.grid_shown_b,
                                            self.main_panel_shown_b)


class Workspace:
    """All tabs of the plot panel and the plots inside them.

    Inputs:
        random_generator: optional random.Random for the curve colors;
            a new unseeded one is used when it is None.
    """

    def __init__(self, random_generator=None) -> None:
        """Create the workspace with one tab named "Tab 1".

        Inputs:
            random_generator: optional random.Random for curve colors.
        Outputs: none.
        """
        # LLFR-00034: random colors come from this generator.
        if random_generator is None:
            random_generator = random.Random()
        self.random_generator = random_generator
        # LLFR-00024: ids count up and are never reused.
        self.next_tab_id_i = 1
        self.next_plot_id_i = 1
        # LLFR-00210: number of the next default tab name; it only
        # grows, and restarts only when the app starts (LLFR-00654).
        self.next_tab_number_i = 1
        # LLFR-00081: marker ids are unique across all plots and keep
        # counting up after reset().
        self.marker_id_counter = MarkerIdCounter()
        self.tab_list = []
        # LLFR-00205: the vertical markers, shared by every plot of every
        # tab, in the order they were placed.
        self.marker_list = []
        # LLFR-00085, LLFR-00111: number of the next "Flag N"; it only
        # grows, also on undo, while the app runs.
        self.next_marker_number_i = 1
        # LLFR-00310: the areas, shared by every time plot of every tab,
        # in the order they were created.
        self.area_list = []
        # LLFR-00309: number of the next "Area N"; it only grows, also on
        # undo, while the app runs.
        self.next_area_number_i = 1
        # LLFR-00428, LLFR-00851: number of the next "Delta X N" and
        # "Delta Y N", one for each kind; they only grow, also on undo,
        # while the app runs.
        self.next_delta_number_dict = {kind_str: 1
                                       for kind_str in DELTA_KIND_TUPLE}
        # LLFR-00438, LLFR-00872: number of the next "Arrow N", shared
        # by all plots; the same rules.
        self.next_arrow_number_i = 1
        # LLFR-01055: width of the main window's signal list panel, in
        # pixels, as the view last reported it; 0 while unknown.
        self.main_panel_width_i = 0
        # LLFR-01206: the main window shows its signal list panel at
        # start; LLFR-01053: hiding or showing it is undoable.
        self.main_panel_shown_b = True
        # LLFR-01015, LLFR-01159: ids of the undocked windows; they only
        # grow, also after an undo.
        self.next_window_id_i = 1
        # LLFR-00147: the grid is shown at start; LLFR-01132: whether it
        # is shown is part of the state an undo restores. A file opened
        # or replaced keeps it.
        self.grid_shown_b = True
        # LLFR-00024: the app starts with one tab.
        self.reset()

    def reset(self) -> None:
        """Start the workspace with one empty tab "Tab 1".

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00024: no tab and no plot before the first tab.
        self.tab_list = []
        # LLFR-00205: with no plot left, no marker is left either.
        # LLFR-00085, LLFR-00111: the app starts at "Flag 1".
        self.marker_list = []
        self.next_marker_number_i = 1
        # LLFR-00310, LLFR-00309: the same for the areas.
        self.area_list = []
        self.next_area_number_i = 1
        # LLFR-00428, LLFR-00851, LLFR-00438, LLFR-00872: the app
        # starts at "Delta X 1", "Delta Y 1" and "Arrow 1".
        self.next_delta_number_dict = {kind_str: 1
                                       for kind_str in DELTA_KIND_TUPLE}
        self.next_arrow_number_i = 1
        # LLFR-00210, LLFR-00654: tab numbering starts with "Tab 1".
        self.next_tab_number_i = 1
        # LLFR-00024: one tab with no plots; ids keep counting up.
        self.add_tab()

    def next_tab_number(self) -> int:
        """Return the number of the default name of a new tab.

        Inputs: none.
        Outputs: the smallest number n, starting at the tab counter, for
            which no tab is named "Tab <n>". The counter is not advanced;
            add_tab does that.
        """
        # LLFR-00210: start at the counter, so a deleted tab's number is
        # not reused.
        tab_number_i = self.next_tab_number_i
        # LLFR-00212: skip every number whose "Tab N" name another tab
        # already has (for example a tab the user renamed "Tab 5").
        while self.is_tab_name_taken(f"{TAB_NAME_PREFIX_STR}{tab_number_i}"):
            tab_number_i += 1
        return tab_number_i

    def next_tab_name(self) -> str:
        """Return the default name of a new tab.

        Inputs: none.
        Outputs: "Tab <n>", where n is next_tab_number(). The counter is
            not advanced; add_tab does that.
        """
        # LLFR-00026, LLFR-00210, LLFR-00212: default names "Tab 1",
        # "Tab 2", ... that no other tab has.
        return f"{TAB_NAME_PREFIX_STR}{self.next_tab_number()}"

    def is_tab_name_taken(self, name_str: str,
                          except_tab_id_i: int = -1) -> bool:
        """Tell whether another tab already has a name.

        Inputs:
            name_str: the name to look for; leading and trailing spaces
                are ignored.
            except_tab_id_i: id of a tab left out of the search (the tab
                being renamed), -1 to search all tabs.
        Outputs: True when a tab other than except_tab_id_i has exactly
            this name (case-sensitive) after trimming.
        """
        # LLFR-00211, LLFR-00212: names are compared exactly, after
        # removing leading and trailing spaces.
        stripped_name_str = name_str.strip()
        return any(tab.name_str.strip() == stripped_name_str
                   for tab in self.tab_list
                   if tab.tab_id_i != except_tab_id_i)

    def add_tab(self) -> Tab:
        """Add a new empty tab after the last one.

        Inputs: none.
        Outputs: the new Tab, named as next_tab_name() says.
        """
        # LLFR-00026: the "+" button adds a new tab.
        # LLFR-00210, LLFR-00212: a never-reused number, skipping names
        # other tabs already have.
        tab_number_i = self.next_tab_number()
        tab = Tab(self.next_tab_id_i, f"{TAB_NAME_PREFIX_STR}{tab_number_i}")
        self.next_tab_id_i += 1
        # LLFR-00210: the number and the skipped ones are used up, even if
        # the tab is deleted or its creation undone (restore() never rolls
        # the counter back).
        self.next_tab_number_i = tab_number_i + 1
        # LLFR-01028, LLFR-01091: the new tab is the last docked tab,
        # before the undocked tabs.
        self.insert_docked_tab(tab)
        return tab

    def add_tab_to_window(self, window_id_i: int):
        """Add a new empty tab at the end of an undocked window.

        Inputs:
            window_id_i: id of the undocked window.
        Outputs: the new Tab, named as add_tab names it, shown by the
            window; None for an unknown window, with nothing changed.
        """
        # LLFR-01197: the "+" button of an undocked window adds the tab
        # there, after its last tab; LLFR-00210, LLFR-00212: named as
        # any new tab.
        if not self.window_tab_list(window_id_i):
            return None
        tab = self.add_tab()
        # LLFR-01150, LLFR-01158: it takes the window values and the
        # window shows it.
        self.move_tab_to_window(tab.tab_id_i, int(window_id_i))
        return tab

    def insert_docked_tab(self, tab) -> None:
        """Put a docked tab after the last docked tab.

        Inputs:
            tab: the Tab, not in the tab list yet.
        Outputs: none. The tab order stays: the docked tabs, then the
            undocked tabs (LLFR-01091).
        """
        # LLFR-01091: docked tabs first, in their order in the main
        # window; LLFR-00025: a new tab goes right of the last one.
        self.tab_list.insert(len(self.docked_tab_list()), tab)

    def docked_tab_list(self) -> list:
        """Return the docked tabs, in their order in the main window.

        Inputs: none.
        Outputs: a list of Tab.
        """
        # LLFR-01091: the docked tabs come first in the tab order.
        return [tab for tab in self.tab_list if not tab.undocked_b]

    def undocked_tab_list(self) -> list:
        """Return the undocked tabs, window by window, in tab order.

        Inputs: none.
        Outputs: a list of Tab.
        """
        # LLFR-01091: after the docked tabs, window by window.
        return [tab for tab in self.tab_list if tab.undocked_b]

    def window_id_list(self) -> list:
        """Return the ids of the undocked windows, in the tab order.

        Inputs: none.
        Outputs: a list of int, each window once, in the order the
            windows were opened (LLFR-01091).
        """
        # LLFR-01091: the windows in the order they were opened.
        id_list = []
        for tab in self.tab_list:
            if tab.undocked_b and tab.window_id_i not in id_list:
                id_list.append(tab.window_id_i)
        return id_list

    def window_tab_list(self, window_id_i: int) -> list:
        """Return the tabs of an undocked window, in their order.

        Inputs:
            window_id_i: id of the window.
        Outputs: a list of Tab, empty for an unknown window.
        """
        # LLFR-01063, LLFR-01032: the tabs of the window's tab row.
        if int(window_id_i) <= 0:
            return []
        return [tab for tab in self.tab_list
                if tab.window_id_i == int(window_id_i)]

    def window_shown_tab(self, window_id_i: int):
        """Return the tab that an undocked window shows.

        Inputs:
            window_id_i: id of the window.
        Outputs: the Tab, or None for an unknown window.
        """
        # LLFR-01061, LLFR-01156: the tab marked as shown, else the
        # first.
        tab_list = self.window_tab_list(window_id_i)
        for tab in tab_list:
            if tab.window_shown_b:
                return tab
        return tab_list[0] if tab_list else None

    def show_window_tab(self, tab_id_i: int) -> None:
        """Mark a tab as the one its undocked window shows.

        Inputs:
            tab_id_i: id of an undocked tab.
        Outputs: none.
        """
        # LLFR-01149, LLFR-01158: the window shows that tab.
        tab = self.find_tab(tab_id_i)
        if tab is None or not tab.undocked_b:
            return
        for other_tab in self.window_tab_list(tab.window_id_i):
            other_tab.window_shown_b = other_tab is tab

    def window_order_dict(self) -> dict:
        """Return the tabs of every undocked window, for a later repair.

        Inputs: none.
        Outputs: {window id: list of tab ids in the window's order}.
        """
        # LLFR-01156: what the windows held before an action.
        return {window_id_i: [tab.tab_id_i
                              for tab in self.window_tab_list(window_id_i)]
                for window_id_i in self.window_id_list()}

    def repair_window_shown_tabs(self, before_dict: dict,
                                 shown_before_dict: dict) -> None:
        """Give each window that lost the tab it showed another tab.

        Inputs:
            before_dict: window_order_dict() taken before the action.
            shown_before_dict: {window id: id of the tab it showed}
                taken before the action.
        Outputs: none. A window whose shown tab left it shows the
            nearest of its tabs left of that tab, else to its right
            (LLFR-01156); a window with no shown tab shows its first.
        """
        for window_id_i in self.window_id_list():
            tab_list = self.window_tab_list(window_id_i)
            if any(tab.window_shown_b for tab in tab_list):
                continue
            id_list = [tab.tab_id_i for tab in tab_list]
            chosen_id_i = id_list[0]
            old_list = list(before_dict.get(window_id_i, []))
            old_shown_id_i = shown_before_dict.get(window_id_i, -1)
            if old_shown_id_i in old_list:
                # LLFR-01156: the nearest tab to the left, else right.
                index_i = old_list.index(old_shown_id_i)
                left_list = [tab_id_i for tab_id_i in old_list[:index_i]
                             if tab_id_i in id_list]
                right_list = [tab_id_i for tab_id_i in old_list[index_i:]
                              if tab_id_i in id_list]
                if left_list:
                    chosen_id_i = left_list[-1]
                elif right_list:
                    chosen_id_i = right_list[0]
            self.show_window_tab(chosen_id_i)

    def shown_tab_dict(self) -> dict:
        """Return the tab that each undocked window shows.

        Inputs: none.
        Outputs: {window id: tab id}.
        """
        # LLFR-01156: kept before an action that may change the windows.
        return {window_id_i: self.window_shown_tab(window_id_i).tab_id_i
                for window_id_i in self.window_id_list()}

    def order_window_tabs(self) -> None:
        """Keep the tab order: docked tabs, then window by window.

        Inputs: none.
        Outputs: none. The tabs of each undocked window follow each
            other, the windows in the order of their first tab.
        """
        # LLFR-01091: the docked tabs, then the tabs of each window.
        ordered_list = self.docked_tab_list()
        for window_id_i in self.window_id_list():
            ordered_list.extend(self.window_tab_list(window_id_i))
        self.tab_list = ordered_list

    def can_undock_tab(self, tab_id_i: int) -> bool:
        """Tell whether a tab may be undocked.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: True for a docked tab when the main window holds at
            least one other docked tab (LLFR-01018, LLFR-01019).
        """
        # LLFR-01034: whatever the number of undocked windows.
        tab = self.find_tab(tab_id_i)
        return (tab is not None and not tab.undocked_b
                and len(self.docked_tab_list()) > 1)

    def undock_tab(self, tab_id_i: int, window_tuple: tuple = ()) -> bool:
        """Move a docked tab into a new undocked window.

        Inputs:
            tab_id_i: id of the tab.
            window_tuple: (x, y, width, height) of the new window
                (LLFR-01016, LLFR-01128), or () when unknown.
        Outputs: True when the tab was undocked; False when it is the
            last docked tab, already undocked or unknown.
        """
        # LLFR-01018, LLFR-01019: the last docked tab stays.
        if not self.can_undock_tab(tab_id_i):
            return False
        tab = self.find_tab(tab_id_i)
        # LLFR-01015, LLFR-01020: the tab moves with everything it holds,
        # into a window of a new id.
        tab.window_id_i = self.next_window_id_i
        self.next_window_id_i += 1
        tab.window_shown_b = True
        tab.window_tuple = tuple(int(value_i) for value_i in window_tuple)
        # LLFR-01050, LLFR-01051: its panel starts hidden, never shown.
        tab.panel_shown_b = False
        tab.panel_width_i = 0
        # LLFR-01091: the new window follows the other windows.
        self.tab_list.remove(tab)
        self.tab_list.append(tab)
        return True

    def can_move_tab_to_window(self, tab_id_i: int,
                               window_id_i: int) -> bool:
        """Tell whether a tab may move into an undocked window.

        Inputs:
            tab_id_i: id of the tab.
            window_id_i: id of an open undocked window.
        Outputs: True for a tab of another window, or a docked tab when
            the main window keeps another docked tab (LLFR-01144).
        """
        # LLFR-01150, LLFR-01152: into another window that is open.
        tab = self.find_tab(tab_id_i)
        if tab is None or not self.window_tab_list(window_id_i):
            return False
        if tab.window_id_i == int(window_id_i):
            return False
        # LLFR-01144: the last docked tab stays docked.
        return tab.undocked_b or len(self.docked_tab_list()) > 1

    def move_tab_to_window(self, tab_id_i: int, window_id_i: int,
                           index_i: int = -1) -> bool:
        """Move a tab into another undocked window.

        Inputs:
            tab_id_i: id of the tab, docked or of another window.
            window_id_i: id of the window it moves into.
            index_i: its place among the tabs of that window, from 0;
                -1, or a place past the end, for after the last one.
        Outputs: True when the tab moved; False when it may not move
            (can_move_tab_to_window).
        """
        if not self.can_move_tab_to_window(tab_id_i, window_id_i):
            return False
        tab = self.find_tab(tab_id_i)
        window_list = self.window_tab_list(window_id_i)
        # LLFR-01020: the tab keeps all it holds; LLFR-01150: it takes
        # the window values of the window it joins.
        tab.copy_window_values(window_list[0])
        self.tab_list.remove(tab)
        if 0 <= int(index_i) < len(window_list):
            # LLFR-01151: between the tabs on either side of the drop.
            self.tab_list.insert(self.tab_list.index(
                window_list[int(index_i)]), tab)
        else:
            # LLFR-01150: after the last tab of the window.
            self.tab_list.insert(self.tab_list.index(window_list[-1]) + 1,
                                 tab)
        # LLFR-01158: the window shows the moved tab.
        tab.window_shown_b = False
        self.show_window_tab(tab_id_i)
        # LLFR-01091: a window emptied by the move is gone.
        self.order_window_tabs()
        return True

    def move_tab_to_new_window(self, tab_id_i: int,
                               window_tuple: tuple = ()) -> bool:
        """Move a tab of an undocked window into a new undocked window.

        Inputs:
            tab_id_i: id of the undocked tab.
            window_tuple: (x, y, width, height) of the new window
                (LLFR-01167), or () when unknown.
        Outputs: True when the tab moved; False when it is docked or
            unknown. The window it leaves is gone when it was its last
            tab (LLFR-01168).
        """
        # LLFR-01167: only a tab of an undocked window.
        tab = self.find_tab(tab_id_i)
        if tab is None or not tab.undocked_b:
            return False
        # LLFR-01167, LLFR-01020: the tab keeps all it holds, in a window
        # of a new id, at the drop point, with the size of LLFR-01184.
        tab.window_id_i = self.next_window_id_i
        self.next_window_id_i += 1
        tab.window_shown_b = True
        tab.window_tuple = tuple(int(value_i) for value_i in window_tuple)
        # LLFR-01050: its panel starts hidden, never shown.
        tab.panel_shown_b = False
        tab.panel_width_i = 0
        # LLFR-01091: the new window follows the other windows;
        # LLFR-01168: a window left with no tab is gone.
        self.tab_list.remove(tab)
        self.tab_list.append(tab)
        self.order_window_tabs()
        return True

    def move_tab_in_window(self, tab_id_i: int, index_i: int) -> bool:
        """Move an undocked tab to another place in its window.

        Inputs:
            tab_id_i: id of the undocked tab.
            index_i: its new place among the window's tabs, from 0.
        Outputs: True when it moved; False when it was already there,
            is docked or unknown.
        """
        # LLFR-01157, LLFR-01166: the tab is left where it is dropped.
        tab = self.find_tab(tab_id_i)
        if tab is None or not tab.undocked_b:
            return False
        window_list = self.window_tab_list(tab.window_id_i)
        index_i = max(0, min(int(index_i), len(window_list) - 1))
        # LLFR-01090: a drag back to its place changes nothing.
        if window_list.index(tab) == index_i:
            return False
        window_list.remove(tab)
        window_list.insert(index_i, tab)
        first_index_i = min(self.tab_list.index(window_tab)
                            for window_tab in window_list)
        rest_list = [other_tab for other_tab in self.tab_list
                     if other_tab not in window_list]
        self.tab_list = (rest_list[:first_index_i] + window_list
                         + rest_list[first_index_i:])
        return True

    def dock_tab(self, tab_id_i: int, docked_index_i: int = -1) -> bool:
        """Put an undocked tab back into the main window.

        Inputs:
            tab_id_i: id of the tab.
            docked_index_i: its place among the docked tabs, from 0
                (LLFR-01143); -1, or a place past the last docked tab,
                for the last docked tab (LLFR-01028).
        Outputs: True when the tab was docked; False when it is not an
            undocked tab.
        """
        tab = self.find_tab(tab_id_i)
        if tab is None or not tab.undocked_b:
            return False
        # LLFR-01028, LLFR-01020: the last docked tab, unchanged; the
        # other tabs of its window stay in it (LLFR-01029).
        self.tab_list.remove(tab)
        tab.window_id_i = 0
        tab.window_shown_b = False
        docked_count_i = len(self.docked_tab_list())
        if 0 <= int(docked_index_i) < docked_count_i:
            # LLFR-01143: between the docked tabs on either side of the
            # drop; LLFR-01091: still before every undocked tab.
            self.tab_list.insert(int(docked_index_i), tab)
        else:
            self.insert_docked_tab(tab)
        return True

    def set_window_panel(self, window_id_i: int, shown_b: bool,
                         width_i: int) -> bool:
        """Show or hide the signal list panel of an undocked window.

        Inputs:
            window_id_i: id of the undocked window.
            shown_b: True to show the panel.
            width_i: the panel width, in pixels (kept while hidden).
        Outputs: True when something changed.
        """
        # LLFR-01047, LLFR-01048, LLFR-01053: the one panel of the
        # window, kept by each of its tabs.
        tab_list = self.window_tab_list(window_id_i)
        if not tab_list:
            return False
        before_tuple = tab_list[0].window_state_tuple()
        for tab in tab_list:
            tab.panel_shown_b = bool(shown_b)
            tab.panel_width_i = max(int(width_i), 0)
        return tab_list[0].window_state_tuple() != before_tuple

    def set_panel_width(self, window_id_i: int, width_i: int) -> bool:
        """Set the width of the signal list panel of a window.

        Inputs:
            window_id_i: id of the undocked window, or -1 for the main
                window.
            width_i: the width, in pixels.
        Outputs: True when the width changed.
        """
        # LLFR-01055: a drag of the panel border of any window.
        width_i = max(int(width_i), 0)
        if window_id_i < 0:
            changed_b = self.main_panel_width_i != width_i
            self.main_panel_width_i = width_i
            return changed_b
        tab_list = self.window_tab_list(window_id_i)
        if not tab_list:
            return False
        changed_b = tab_list[0].panel_width_i != width_i
        for tab in tab_list:
            tab.panel_width_i = width_i
        return changed_b

    def set_window_geometry(self, window_id_i: int,
                            window_tuple: tuple) -> None:
        """Keep the position and size of an undocked window.

        Inputs:
            window_id_i: id of the window.
            window_tuple: (x, y, width, height) in desktop pixels.
        Outputs: none. Not an undoable change (LLFR-01056).
        """
        # LLFR-01059, LLFR-01075: the window an undo opens again.
        for tab in self.window_tab_list(window_id_i):
            tab.window_tuple = tuple(int(value_i)
                                     for value_i in window_tuple)

    def delete_window(self, window_id_i: int) -> list:
        """Delete every tab of an undocked window.

        Inputs:
            window_id_i: id of the window.
        Outputs: the ids of the deleted tabs, empty for an unknown
            window.
        """
        # LLFR-01073: all its tabs, as Delete does for each.
        deleted_id_list = [tab.tab_id_i
                           for tab in self.window_tab_list(window_id_i)]
        self.tab_list = [tab for tab in self.tab_list
                         if tab.tab_id_i not in deleted_id_list]
        # LLFR-00205: their plots may have been the last ones.
        if deleted_id_list:
            self.clear_markers_without_plots()
        return deleted_id_list

    def add_named_tab(self, name_str: str) -> Tab:
        """Add a new empty tab with a given name after the last one.

        Inputs:
            name_str: the name of the tab; leading and trailing spaces
                are removed. The caller makes sure it is not empty and
                not the name of another tab (LLFR-00235).
        Outputs: the new Tab. The counter of the default tab names is
            not changed: a later default name skips this name anyway
            (LLFR-00212).
        """
        # LLFR-00230: a tab of a layout file keeps its saved name.
        tab = Tab(self.next_tab_id_i, str(name_str).strip())
        self.next_tab_id_i += 1
        # LLFR-01077, LLFR-01091: a docked tab, after the docked ones.
        self.insert_docked_tab(tab)
        return tab

    def remove_all_tabs(self) -> None:
        """Remove every tab, leaving the workspace without tabs.

        Inputs: none.
        Outputs: none. The caller must add at least one tab afterwards.
            The id counters and the numbering of the default tab and
            marker names are kept (LLFR-00210, LLFR-00111).
        """
        # LLFR-00229: when no current tab holds a plot, the tabs of the
        # layout file replace the current ones.
        self.tab_list = []
        # LLFR-00205: with no plot left, no marker is left either.
        self.clear_markers_without_plots()

    def find_tab(self, tab_id_i: int):
        """Return a tab by its id.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: the Tab, or None when no tab has that id.
        """
        # LLFR-00028, LLFR-00030: tabs are found by id.
        for tab in self.tab_list:
            if tab.tab_id_i == tab_id_i:
                return tab
        return None

    def can_delete_tab(self, tab_id_i: int = -1) -> bool:
        """Tell whether a tab may be deleted.

        Inputs:
            tab_id_i: id of the tab, or -1 to ask about the docked tabs.
        Outputs: True for an undocked tab (LLFR-01069); for a docked tab,
            or with -1, True only when the main window holds more than
            one docked tab (LLFR-00066).
        """
        # LLFR-01069: deleting an undocked tab never deletes the last
        # tab, because the main window keeps a docked tab.
        tab = self.find_tab(tab_id_i)
        if tab is not None and tab.undocked_b:
            return True
        # LLFR-00066: the main window always keeps a docked tab.
        return len(self.docked_tab_list()) > 1

    def delete_tab(self, tab_id_i: int) -> bool:
        """Delete a tab and all its plots.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: True when the tab was deleted; False when it is the last
            tab (LLFR-00066) or no tab has that id.
        """
        # LLFR-00066: refuse to delete the last tab.
        tab = self.find_tab(tab_id_i)
        if tab is None or not self.can_delete_tab(tab_id_i):
            return False
        # LLFR-00028: remove the tab.
        self.tab_list.remove(tab)
        # LLFR-00205: its plots may have been the last ones.
        self.clear_markers_without_plots()
        return True

    def rename_tab(self, tab_id_i: int, new_name_str: str) -> bool:
        """Rename a tab.

        Inputs:
            tab_id_i: id of the tab.
            new_name_str: the name typed by the user; surrounding spaces
                are removed.
        Outputs: True when the tab was renamed; False when the name is
            empty or only spaces (LLFR-00067), is the name of another tab
            (LLFR-00211) or no tab has that id.
        """
        # LLFR-00067: an empty or blank name keeps the previous name.
        stripped_name_str = new_name_str.strip()
        tab = self.find_tab(tab_id_i)
        if tab is None or not stripped_name_str:
            return False
        # LLFR-00211: another tab's name keeps the previous name.
        if self.is_tab_name_taken(stripped_name_str, tab_id_i):
            return False
        # LLFR-00030: the tab takes the typed name.
        tab.name_str = stripped_name_str
        return True

    def move_tab(self, tab_id_i: int, new_index_i: int) -> bool:
        """Move a tab to another place in the tab order.

        Inputs:
            tab_id_i: id of the tab.
            new_index_i: the place the tab takes, from 0 (first tab);
                a place past the end means the last place.
        Outputs: True when the tab moved; False when it was already at
            that place or no tab has that id.
        """
        # LLFR-01087: the tab is left where it is dropped, between the
        # tabs on either side of it.
        tab = self.find_tab(tab_id_i)
        # LLFR-01067: an undocked tab is not moved by a drag.
        if tab is None or tab.undocked_b:
            return False
        # LLFR-01091: a docked tab moves among the docked tabs.
        new_index_i = max(0, min(int(new_index_i),
                                 len(self.docked_tab_list()) - 1))
        # LLFR-01090: a drag back to its place changes nothing.
        if self.tab_list.index(tab) == new_index_i:
            return False
        self.tab_list.remove(tab)
        self.tab_list.insert(new_index_i, tab)
        return True

    def set_plot_matrix(self, tab_id_i: int, row_count_i: int,
                        column_count_i: int) -> bool:
        """Give a tab another plot matrix.

        Inputs:
            tab_id_i: id of the tab.
            row_count_i: number of rows, 1 to 10.
            column_count_i: number of columns, 1 to 10.
        Outputs: True when the matrix changed; False when it is the
            tab's current matrix (LLFR-01104), when it has fewer slots
            than the tab has plots (LLFR-01107), when a size is not
            from 1 to 10, or when no tab has that id.
        """
        # LLFR-01101: only this tab's matrix changes.
        tab = self.find_tab(tab_id_i)
        if tab is None or not tab.can_take_matrix(row_count_i,
                                                  column_count_i):
            return False
        # LLFR-01104: the current matrix changes nothing.
        if (tab.row_count_i, tab.column_count_i) == (row_count_i,
                                                     column_count_i):
            return False
        # LLFR-01100, LLFR-01102: the plots keep their order, so their
        # place in the fill order, and everything they hold.
        tab.row_count_i = int(row_count_i)
        tab.column_count_i = int(column_count_i)
        return True

    def swap_plots(self, plot_id_i: int, other_plot_id_i: int) -> bool:
        """Swap the slots of two plots of the same tab.

        Inputs:
            plot_id_i: id of the plot the position picker was opened
                from.
            other_plot_id_i: id of the plot whose slot was chosen.
        Outputs: True when the plots were swapped; False when both ids
            are the same plot (LLFR-01121), when they are in different
            tabs or when one of them is unknown.
        """
        # LLFR-01121: the plot's own slot changes nothing.
        if plot_id_i == other_plot_id_i:
            return False
        tab = self.tab_of_plot(plot_id_i)
        if tab is None or tab.find_plot(other_plot_id_i) is None:
            return False
        # LLFR-01118: each plot takes the slot of the other; the other
        # plots keep theirs. LLFR-01119: the Plot objects are moved,
        # with everything they hold.
        first_index_i = tab.plot_list.index(tab.find_plot(plot_id_i))
        second_index_i = tab.plot_list.index(tab.find_plot(other_plot_id_i))
        tab.plot_list[first_index_i], tab.plot_list[second_index_i] = (
            tab.plot_list[second_index_i], tab.plot_list[first_index_i])
        return True

    def add_plot(self, tab_id_i: int,
                 kind_str: str = TIME_PLOT_KIND_STR):
        """Add a new empty plot in the next slot of a tab.

        Inputs:
            tab_id_i: id of the tab.
            kind_str: TIME_PLOT_KIND_STR (the default) for a time plot or
                FREQUENCY_PLOT_KIND_STR for a frequency plot.
        Outputs: the new Plot, or None when the tab is full (LLFR-00031)
            or no tab has that id. Raises ValueError for an unknown kind.
        """
        # LLFR-00031, LLFR-00256: a full tab gets no new plot, of either
        # kind: a frequency plot counts towards the maximum too.
        tab = self.find_tab(tab_id_i)
        if tab is None or tab.is_full():
            return None
        # LLFR-01109: the new plot goes after the last plot of the tab
        # in the fill order.
        plot = Plot(self.next_plot_id_i, self.random_generator,
                    self.marker_id_counter, kind_str)
        self.next_plot_id_i += 1
        tab.plot_list.append(plot)
        return plot

    def tab_of_plot(self, plot_id_i: int):
        """Return the tab that holds a plot.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: the Tab, or None when no plot has that id.
        """
        # LLFR-00049: find the tab to remove the plot from.
        for tab in self.tab_list:
            if tab.find_plot(plot_id_i) is not None:
                return tab
        return None

    def find_plot(self, plot_id_i: int):
        """Return a plot of any tab by its id.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: the Plot, or None when no plot has that id.
        """
        # LLFR-00021: plots are found by id, for example on a drop.
        tab = self.tab_of_plot(plot_id_i)
        if tab is None:
            return None
        return tab.find_plot(plot_id_i)

    def delete_plot(self, plot_id_i: int) -> bool:
        """Delete a plot and all its curves from its tab.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: True when the plot was deleted, False when no plot has
            that id.
        """
        # LLFR-00049: remove the plot; the others keep their order.
        tab = self.tab_of_plot(plot_id_i)
        if tab is None:
            return False
        tab.plot_list.remove(tab.find_plot(plot_id_i))
        # LLFR-00205: in the same action, the markers go with the last
        # plot (LLFR-00051 deletes an emptied plot through here too).
        self.clear_markers_without_plots()
        return True

    def remove_curve(self, plot_id_i: int, signal_name_str: str) -> bool:
        """Remove a signal's curve from a plot, deleting the plot if empty.

        Inputs:
            plot_id_i: id of the plot.
            signal_name_str: name of the signal to remove.
        Outputs: True when the curve was removed, False when the plot or
            the signal was not found.
        """
        # LLFR-00039: remove the curve from the plot.
        plot = self.find_plot(plot_id_i)
        if plot is None or not plot.remove_curve(signal_name_str):
            return False
        # LLFR-00051: a plot left with no curves is deleted.
        if plot.is_empty():
            self.delete_plot(plot_id_i)
        return True

    def has_plots(self) -> bool:
        """Tell whether any tab holds a plot.

        Inputs: none.
        Outputs: True when at least one plot exists.
        """
        # LLFR-00205: markers are only kept while a plot exists. A
        # frequency plot is a plot too (HLFR-00058), so the markers are
        # kept while one exists, even though it does not show them
        # (LLFR-00259); a time plot created later shows them again.
        return any(tab.plot_list for tab in self.tab_list)

    def clear_markers_without_plots(self) -> None:
        """Delete every vertical marker and area when no plot is left.

        Inputs: none.
        Outputs: none. The marker and area numbering is not restarted
            (LLFR-00111, LLFR-00309): it restarts only when the app starts.
        """
        # LLFR-00205: no plot left in any tab, no marker left.
        # LLFR-00310: and no area, in the same way.
        if not self.has_plots():
            self.marker_list = []
            self.area_list = []

    def add_marker(self, time_s: float) -> VerticalMarker:
        """Place a new vertical marker, shown on every plot.

        Inputs:
            time_s: time of the marker, in seconds; stored as given.
        Outputs: the new VerticalMarker, named "Flag N" (LLFR-00085).
        """
        # LLFR-00081, LLFR-00205: one marker for every plot of every tab.
        # LLFR-00085: "Flag N", N counting across the whole workspace.
        name_str = DEFAULT_MARKER_NAME_FORMAT_STR.format(
            self.next_marker_number_i)
        # LLFR-00111: the number only grows and is never reused.
        self.next_marker_number_i += 1
        marker = VerticalMarker(self.marker_id_counter.take_next_id(),
                                name_str, float(time_s))
        self.marker_list.append(marker)
        return marker

    def add_named_marker(self, name_str: str, time_s: float,
                         color_str: str = DEFAULT_FLAG_COLOR_STR
                         ) -> VerticalMarker:
        """Place a new vertical marker with a given name.

        Inputs:
            name_str: the name shown in the marker's label; leading and
                trailing spaces are removed. The caller makes sure it is
                not empty (LLFR-00089).
            time_s: time of the marker, in seconds.
            color_str: its color, "#rrggbb" (any case); the default flag
                color when it is not written as "#rrggbb".
        Outputs: the new VerticalMarker.
        """
        # LLFR-00230, LLFR-00205: a marker of a layout file keeps its
        # saved name and is shown on every plot.
        stripped_name_str = str(name_str).strip()
        # LLFR-00393: with its saved color, or the default color.
        marker_color_str = (hex_color_or_none(color_str)
                            or DEFAULT_FLAG_COLOR_STR)
        marker = VerticalMarker(self.marker_id_counter.take_next_id(),
                                stripped_name_str, float(time_s),
                                marker_color_str)
        self.marker_list.append(marker)
        # LLFR-00085, LLFR-00111: a saved name "Flag N" uses up N, so
        # that a marker placed later never gets the same default name.
        number_match = re.fullmatch(DEFAULT_MARKER_NAME_PATTERN_STR,
                                    stripped_name_str)
        if number_match is not None:
            self.next_marker_number_i = max(
                self.next_marker_number_i, int(number_match.group(1)) + 1)
        return marker

    def delta_marker_name_set(self, kind_str: str) -> set:
        """Return the names of the delta markers of one kind.

        Inputs:
            kind_str: DELTA_X_KIND_STR or DELTA_Y_KIND_STR.
        Outputs: the set of the names of every delta marker of that
            kind, in every plot of every tab.
        """
        # LLFR-00852: the names a new delta marker must not take.
        return {delta_marker.name_str
                for tab in self.tab_list for plot in tab.plot_list
                for delta_marker in plot.delta_marker_list
                if delta_marker.kind_str == kind_str}

    def take_delta_marker_name(self, kind_str: str) -> str:
        """Return the name of a new delta marker and use up its number.

        Inputs:
            kind_str: DELTA_X_KIND_STR or DELTA_Y_KIND_STR.
        Outputs: "Delta X N" or "Delta Y N" (LLFR-00428), N from the
            counter of that kind up, skipping every number whose name a
            delta marker of that kind already has (LLFR-00852). Raises
            ValueError for an unknown kind.
        """
        if kind_str not in DELTA_KIND_TUPLE:
            raise ValueError(f"Unknown delta marker kind {kind_str!r}.")
        # LLFR-00428, LLFR-00852: the first free number from the counter.
        name_format_str = DEFAULT_DELTA_NAME_FORMAT_DICT[kind_str]
        name_str = first_free_name(name_format_str,
                                   self.delta_marker_name_set(kind_str),
                                   self.next_delta_number_dict[kind_str])
        # LLFR-00851: the number is used up, also when the placement is
        # undone or the marker deleted; a skipped number too.
        number_i = int(name_str.rsplit(" ", 1)[1])
        self.next_delta_number_dict[kind_str] = number_i + 1
        return name_str

    def take_arrow_name(self) -> str:
        """Return the name of a new arrow and use up its number.

        Inputs: none.
        Outputs: "Arrow N" (LLFR-00438), N growing by 1 for each new
            arrow in any plot.
        """
        # LLFR-00438, LLFR-00872: the number only grows, also when the
        # drawing is undone or the arrow deleted.
        name_str = DEFAULT_ARROW_NAME_FORMAT_STR.format(
            self.next_arrow_number_i)
        self.next_arrow_number_i += 1
        return name_str

    def find_marker(self, marker_id_i: int):
        """Return a vertical marker by its id.

        Inputs:
            marker_id_i: id of the marker.
        Outputs: the VerticalMarker, or None when no marker has that id.
        """
        # LLFR-00086, LLFR-00088, LLFR-00091: markers are found by id.
        for marker in self.marker_list:
            if marker.marker_id_i == marker_id_i:
                return marker
        return None

    def move_marker(self, marker_id_i: int, time_s: float) -> bool:
        """Move a vertical marker to a new time, on every plot.

        Inputs:
            marker_id_i: id of the marker.
            time_s: new time of the marker, in seconds; stored as given.
        Outputs: True when the marker was moved, False when no marker
            has that id.
        """
        # LLFR-00086, LLFR-00205: the marker is left where the mouse
        # button is released, on every plot.
        marker = self.find_marker(marker_id_i)
        if marker is None:
            return False
        marker.time_s = float(time_s)
        return True

    def rename_marker(self, marker_id_i: int, new_name_str: str) -> bool:
        """Rename a vertical marker, on every plot.

        Inputs:
            marker_id_i: id of the marker.
            new_name_str: the name typed by the user; surrounding spaces
                are removed.
        Outputs: True when the marker was renamed; False when the name is
            empty or only spaces (LLFR-00089) or no marker has that id.
        """
        # LLFR-00089: an empty or blank name keeps the previous name.
        stripped_name_str = new_name_str.strip()
        marker = self.find_marker(marker_id_i)
        if marker is None or not stripped_name_str:
            return False
        # LLFR-00088, LLFR-00112, LLFR-00205: every label shows the name.
        marker.name_str = stripped_name_str
        return True

    def set_marker_color(self, marker_id_i: int, color_str: str) -> bool:
        """Give a vertical marker (flag) another color, on every plot.

        Inputs:
            marker_id_i: id of the marker.
            color_str: the color, written as "#rrggbb" (any case).
        Outputs: True when the color changed; False when no marker has
            that id, the value is not "#rrggbb" or it is the marker's
            current color.
        """
        # LLFR-00392, LLFR-00390: the confirmed color; the color the
        # flag already has changes nothing.
        new_color_str = hex_color_or_none(color_str)
        marker = self.find_marker(marker_id_i)
        if marker is None or new_color_str is None:
            return False
        if marker.color_str == new_color_str:
            return False
        # LLFR-00205: every time plot draws it in the new color.
        marker.color_str = new_color_str
        return True

    def remove_marker(self, marker_id_i: int) -> bool:
        """Remove a vertical marker from every plot.

        Inputs:
            marker_id_i: id of the marker.
        Outputs: True when the marker was removed, False when no marker
            has that id.
        """
        # LLFR-00091, LLFR-00205: the marker and its label leave every
        # plot.
        marker = self.find_marker(marker_id_i)
        if marker is None:
            return False
        # LLFR-00111: next_marker_number_i is not lowered, so the
        # deleted number is not reused.
        self.marker_list.remove(marker)
        return True

    def remove_all_markers(self) -> int:
        """Remove every vertical marker (flag) from every plot.

        Inputs: none.
        Outputs: the number of flags removed.
        """
        # LLFR-00416, LLFR-00205: every flag leaves every time plot.
        # LLFR-00111: next_marker_number_i is not lowered.
        removed_count_i = len(self.marker_list)
        self.marker_list = []
        return removed_count_i

    def remove_all_pinned_tips(self) -> int:
        """Remove every pinned tip of every plot of every tab.

        Inputs: none.
        Outputs: the number of pinned tips removed.
        """
        # LLFR-00413: time plots and frequency plots, in every tab.
        return sum(plot.remove_all_pinned_tips()
                   for tab in self.tab_list for plot in tab.plot_list)

    def remove_all_delta_markers(self) -> int:
        """Remove every delta marker of every plot of every tab.

        Inputs: none.
        Outputs: the number of delta markers removed.
        """
        # LLFR-00415: time plots and frequency plots, in every tab.
        return sum(plot.remove_all_delta_markers()
                   for tab in self.tab_list for plot in tab.plot_list)

    def marker_state_tuple(self) -> tuple:
        """Return the vertical markers as plain values.

        Inputs: none.
        Outputs: a tuple of (marker_id_i, name_str, time_s, color_str),
            in placing order.
        """
        # LLFR-00140, LLFR-00205: placing, moving, renaming, changing the
        # color of (LLFR-00392) and deleting a marker change this, so
        # they are recorded for undo.
        return tuple((marker.marker_id_i, marker.name_str, marker.time_s,
                      marker.color_str)
                     for marker in self.marker_list)

    def state_tuple(self) -> tuple:
        """Return the tabs, plots, curves, tips and markers as plain values.

        Inputs: none.
        Outputs: a tuple (tab tuple, marker tuple, area tuple): one entry
            (tab_id_i, name_str, plot state tuples, row_count_i,
            column_count_i) per tab, in tab order, the vertical
            markers (marker_state_tuple) and the areas
            (area_state_tuple); two workspaces with equal tuples
            show the same thing (LLFR-00140).
        """
        # LLFR-00138, LLFR-00140: what an undo restores; the id counters
        # and the marker and area numbering are not part of it, since
        # they only grow (LLFR-00111, LLFR-00309).
        return tabs_state_tuple(self.tab_list, self.marker_list,
                                self.area_list, self.main_panel_width_i,
                                self.grid_shown_b, self.main_panel_shown_b)

    def copy_tab_list(self, tab_list: list) -> list:
        """Deep-copy tabs, keeping the shared generator and id counter.

        The copied plots still use this workspace's random generator and
        marker id counter.

        Inputs:
            tab_list: the tabs to copy.
        Outputs: the copied list of Tab objects.
        """
        # LLFR-00138: the copy shares no tab, plot, curve, tip or marker
        # with the original. LLFR-00034, LLFR-00111: the color generator
        # and the marker id counter stay shared, so marker ids keep
        # counting up and are never handed out twice.
        shared_object_dict = {
            id(self.random_generator): self.random_generator,
            id(self.marker_id_counter): self.marker_id_counter}
        return copy.deepcopy(tab_list, shared_object_dict)

    def snapshot(self, current_tab_id_i: int = -1) -> WorkspaceSnapshot:
        """Save the current tabs, plots, curves, tips and markers.

        Inputs:
            current_tab_id_i: id of the tab selected in the view, kept
                so that undo can select it again; -1 when unknown.
        Outputs: the WorkspaceSnapshot.
        """
        # LLFR-00140: saved before every undoable action. LLFR-00205:
        # with the shared vertical markers.
        # LLFR-00310: and with the shared areas.
        return WorkspaceSnapshot(self.copy_tab_list(self.tab_list),
                                 self.state_tuple(), int(current_tab_id_i),
                                 copy.deepcopy(self.marker_list),
                                 copy.deepcopy(self.area_list),
                                 self.main_panel_width_i,
                                 self.grid_shown_b,
                                 self.main_panel_shown_b)

    def is_unchanged_since(self, snapshot: WorkspaceSnapshot) -> bool:
        """Tell whether the workspace still holds a saved state.

        Inputs:
            snapshot: a WorkspaceSnapshot of this workspace.
        Outputs: True when nothing changed since the snapshot was taken.
        """
        # LLFR-00140: an action that changed nothing (a refused rename,
        # a duplicate drop, a full tab) is not recorded for undo.
        return self.state_tuple() == snapshot.state_tuple

    def restore(self, snapshot: WorkspaceSnapshot) -> None:
        """Return the tabs, plots, curves, tips and markers to a saved state.

        Inputs:
            snapshot: a WorkspaceSnapshot of this workspace.
        Outputs: none. The snapshot itself is not changed. The tab, plot
            and marker id counters are not rolled back, so an id handed
            out after the snapshot is never reused.
        """
        # LLFR-00138: the state from before the undone action.
        self.tab_list = self.copy_tab_list(snapshot.tab_list)
        # LLFR-00205: the markers of that state, on every plot. The
        # marker numbering is kept (LLFR-00111): an undone placement
        # does not free its number.
        self.marker_list = copy.deepcopy(snapshot.marker_list)
        # LLFR-00310, LLFR-00309: the areas of that state; the area
        # numbering is kept, so an undone creation does not free its
        # number.
        self.area_list = copy.deepcopy(snapshot.area_list)
        # LLFR-01055, LLFR-00138: the main window's panel width.
        self.main_panel_width_i = int(getattr(snapshot,
                                              "main_panel_width_i", 0))
        # LLFR-01053, LLFR-00138: the main window's panel shown or not.
        self.main_panel_shown_b = bool(getattr(snapshot,
                                               "main_panel_shown_b", True))
        # LLFR-01132, LLFR-00138: the grid of that state.
        self.grid_shown_b = bool(getattr(snapshot, "grid_shown_b", True))
        # LLFR-00024, LLFR-00081: ids only grow, also after an undo.
        highest_tab_id_i = max((tab.tab_id_i for tab in self.tab_list),
                               default=0)
        self.next_tab_id_i = max(self.next_tab_id_i, highest_tab_id_i + 1)
        highest_plot_id_i = max((plot.plot_id_i for tab in self.tab_list
                                 for plot in tab.plot_list), default=0)
        self.next_plot_id_i = max(self.next_plot_id_i,
                                  highest_plot_id_i + 1)
        # LLFR-01059: window ids only grow too.
        highest_window_id_i = max((tab.window_id_i for tab in self.tab_list),
                                  default=0)
        self.next_window_id_i = max(self.next_window_id_i,
                                    highest_window_id_i + 1)

    def rename_signal(self, old_name_str: str, new_name_str: str) -> bool:
        """Rename a signal in every plot of every tab.

        Inputs:
            old_name_str: the current name of the signal.
            new_name_str: its new name.
        Outputs: True when at least one plot draws the signal.
        """
        # LLFR-00266: the legends show the new name; not undoable.
        return rename_signal_in_tabs(self.tab_list, old_name_str,
                                     new_name_str)

    def remove_signal_curves(self, signal_name_set: set) -> list:
        """Remove the curves of some signals from every plot.

        Inputs:
            signal_name_set: names of the signals whose curves go away.
        Outputs: the ids of the plots that were left with no curve and
            were deleted (LLFR-00051). When no plot is left in any tab,
            every vertical marker is deleted too (LLFR-00205).
        """
        # LLFR-00255: the curves of a deleted synthetic signal and of its
        # dependents leave every plot, with their tips and delta markers.
        deleted_plot_id_list = []
        for tab in self.tab_list:
            for plot in list(tab.plot_list):
                removed_b = False
                for curve in list(plot.curve_list):
                    if curve.signal_name_str in signal_name_set:
                        removed_b = (plot.remove_curve(
                            curve.signal_name_str) or removed_b)
                # LLFR-00051: a plot left with no curve is deleted.
                if removed_b and plot.is_empty():
                    tab.plot_list.remove(plot)
                    deleted_plot_id_list.append(plot.plot_id_i)
        # LLFR-00205: with no plot left, no vertical marker is left.
        self.clear_markers_without_plots()
        return deleted_plot_id_list

    def close_signals(self, signal_name_set: set, files_range_tuple: tuple,
                      shown_tab_id_i: int) -> tuple:
        """Remove what belonged to closed data files.

        Inputs:
            signal_name_set: the signals of the closed files and the
                synthetic signals computed from them (LLFR-00926).
            files_range_tuple: (start_s, end_s), the time range of the
                open data files that are left (LLFR-00916), or () when
                no file is left.
            shown_tab_id_i: the id of the tab shown before the close.
        Outputs: a tuple (deleted_plot_id_list, closed_tab_id_list,
            shown_tab_id_i): the plots deleted because they were left
            with no curve, the tabs closed, and the tab to show.
        """
        # LLFR-00960: the tabs that held a plot before the close; only
        # those can be closed.
        tab_with_plots_id_set = {tab.tab_id_i for tab in self.tab_list
                                 if tab.plot_list}
        # LLFR-00927, LLFR-00928: the curves go, with their pinned data
        # tips and delta markers, and a plot left with no curve is
        # deleted with its text notes and arrows. LLFR-00667: with no
        # plot left, every flag and area is deleted.
        deleted_plot_id_list = self.remove_signal_curves(signal_name_set)
        # LLFR-00932: a tab emptied by the close is closed.
        emptied_tab_list = [tab for tab in self.tab_list
                            if tab.tab_id_i in tab_with_plots_id_set
                            and not tab.plot_list]
        closed_tab_list = list(emptied_tab_list)
        docked_list = self.docked_tab_list()
        closed_docked_list = [tab for tab in closed_tab_list
                              if not tab.undocked_b]
        if len(closed_docked_list) == len(docked_list):
            # LLFR-00961: the main window keeps a docked tab, the first
            # of those, in tab order, with no plot. LLFR-01033: the
            # emptied undocked tabs are closed with their windows.
            closed_tab_list.remove(closed_docked_list[0])
        closed_tab_id_list = [tab.tab_id_i for tab in closed_tab_list]
        shown_index_i = next(
            (index_i for index_i, tab in enumerate(docked_list)
             if tab.tab_id_i == shown_tab_id_i), 0)
        # LLFR-00962: the nearest docked tab left of the main window.
        kept_before_list = [
            tab for tab in docked_list[:shown_index_i]
            if tab.tab_id_i not in closed_tab_id_list]
        kept_after_list = [
            tab for tab in docked_list[shown_index_i:]
            if tab.tab_id_i not in closed_tab_id_list]
        self.tab_list = [tab for tab in self.tab_list
                         if tab.tab_id_i not in closed_tab_id_list]
        # LLFR-00962: the shown tab stays shown; when it was closed, the
        # nearest tab left to its left, or else to its right.
        if shown_tab_id_i in closed_tab_id_list:
            if kept_before_list:
                shown_tab_id_i = kept_before_list[-1].tab_id_i
            elif kept_after_list:
                shown_tab_id_i = kept_after_list[0].tab_id_i
        shown_tab = self.find_tab(shown_tab_id_i)
        if (shown_tab is None or shown_tab.undocked_b) and self.tab_list:
            shown_tab_id_i = self.docked_tab_list()[0].tab_id_i
        # LLFR-00933, LLFR-00950: with a plot left, the flags and the
        # areas outside the time range of the files left are deleted.
        if self.has_plots() and files_range_tuple:
            self.remove_outside_range(*files_range_tuple)
        elif not files_range_tuple:
            # LLFR-00924: every flag and area when no file is left.
            self.marker_list = []
            self.area_list = []
        return (deleted_plot_id_list, closed_tab_id_list, shown_tab_id_i)

    def remove_outside_range(self, start_s: float, end_s: float) -> None:
        """Delete the flags and areas outside a time range.

        Inputs:
            start_s: the first time of the range, in seconds.
            end_s: the last time of the range, in seconds.
        Outputs: none. A flag on an end of the range is kept, and so is
            an area that is partly inside the range or touches an end.
        """
        # LLFR-00933: a flag outside the range goes; one on an end stays.
        self.marker_list = [marker for marker in self.marker_list
                            if start_s <= marker.time_s <= end_s]
        # LLFR-00950: an area entirely outside the range goes; one partly
        # inside or touching an end stays.
        self.area_list = [area for area in self.area_list
                          if area.end_s >= start_s and area.start_s <= end_s]

    # ----------------------------------------------------------------
    # Areas (HLFR-00066 to HLFR-00069)
    # ----------------------------------------------------------------

    def find_area(self, area_id_i: int):
        """Return an area by its id.

        Inputs:
            area_id_i: id of the area.
        Outputs: the Area, or None when no area has that id.
        """
        # LLFR-00312, LLFR-00313, LLFR-00315, LLFR-00316: areas are found
        # by id.
        for area in self.area_list:
            if area.area_id_i == area_id_i:
                return area
        return None

    def area_overlaps_b(self, start_s: float, end_s: float,
                        except_area_id_i: int = -1) -> bool:
        """Tell whether a time span overlaps an area.

        Inputs:
            start_s: start of the span, in seconds, before end_s.
            end_s: end of the span, in seconds.
            except_area_id_i: id of an area left out of the check (the
                area being moved or resized), -1 to check all areas.
        Outputs: True when the span overlaps an area by more than a
            shared edge.
        """
        # LLFR-00304, LLFR-00312, LLFR-00313: areas never overlap, but
        # may share an edge.
        return any(spans_overlap_b(start_s, end_s, area.start_s, area.end_s)
                   for area in self.area_list
                   if area.area_id_i != except_area_id_i)

    def take_area_number(self, name_str: str) -> None:
        """Use up the number of a default area name.

        Inputs:
            name_str: the name of an area that was just added.
        Outputs: none. When the name is "Area N", the next default name
            gets a number greater than N.
        """
        # LLFR-00309, LLFR-00319: a saved name "Area N" uses up N, so that
        # an area created later never gets the same default name.
        number_match = re.fullmatch(DEFAULT_AREA_NAME_PATTERN_STR, name_str)
        if number_match is not None:
            self.next_area_number_i = max(
                self.next_area_number_i, int(number_match.group(1)) + 1)

    def add_area(self, start_s: float, end_s: float, name_str: str = "",
                 color_str: str = DEFAULT_AREA_COLOR_STR):
        """Create a new area, shown on every time plot.

        Inputs:
            start_s: one edge of the area, in seconds.
            end_s: the other edge, in seconds (the two are sorted).
            name_str: the name of the area; leading and trailing spaces
                are removed. Empty (the default) gives the next default
                name "Area N" (LLFR-00309).
            color_str: its color, "#rrggbb" (any case) (LLFR-00351);
                the default color when it is not written as "#rrggbb".
        Outputs: the new Area, or None when the span is empty, not
            finite or overlaps another area (LLFR-00304). Nothing is
            changed then, and no number is used up.
        """
        # LLFR-00304: between two different times, not overlapping.
        try:
            start_s, end_s = area_span_tuple(start_s, end_s)
        except ValueError:
            return None
        if self.area_overlaps_b(start_s, end_s):
            return None
        stripped_name_str = str(name_str).strip()
        if not stripped_name_str:
            # LLFR-00309: "Area N"; N only grows and is never reused.
            stripped_name_str = DEFAULT_AREA_NAME_FORMAT_STR.format(
                self.next_area_number_i)
            self.next_area_number_i += 1
        else:
            # LLFR-00319: a saved name keeps its number used up.
            self.take_area_number(stripped_name_str)
        # LLFR-00310: one area for every time plot of every tab; its id
        # comes from the counter of the markers, so it is never reused.
        # LLFR-00351: a new area gets the default color; LLFR-00319: an
        # area of a layout file its saved color.
        area_color_str = hex_color_or_none(color_str) or DEFAULT_AREA_COLOR_STR
        area = Area(self.marker_id_counter.take_next_id(), stripped_name_str,
                    start_s, end_s, area_color_str)
        self.area_list.append(area)
        return area

    def set_area_span(self, area_id_i: int, start_s: float,
                      end_s: float) -> bool:
        """Move or resize an area, on every time plot.

        Inputs:
            area_id_i: id of the area.
            start_s: new start of the area, in seconds.
            end_s: new end of the area, in seconds (the two are sorted).
        Outputs: True when the area was changed; False when no area has
            that id, the span is empty or not finite, it overlaps another
            area, or it is the area's current span.
        """
        # LLFR-00312, LLFR-00313: the area is left where the mouse
        # button is released; it never overlaps another area.
        area = self.find_area(area_id_i)
        if area is None:
            return False
        try:
            start_s, end_s = area_span_tuple(start_s, end_s)
        except ValueError:
            return False
        if self.area_overlaps_b(start_s, end_s, area_id_i):
            return False
        if (start_s, end_s) == (area.start_s, area.end_s):
            return False
        area.start_s = start_s
        area.end_s = end_s
        return True

    def rename_area(self, area_id_i: int, new_name_str: str) -> bool:
        """Rename an area, on every time plot.

        Inputs:
            area_id_i: id of the area.
            new_name_str: the name typed by the user; surrounding spaces
                are removed.
        Outputs: True when the area was renamed; False when the name is
            empty or only spaces (LLFR-00315) or no area has that id.
        """
        # LLFR-00315: an empty or blank name keeps the previous name.
        stripped_name_str = str(new_name_str).strip()
        area = self.find_area(area_id_i)
        if area is None or not stripped_name_str:
            return False
        # LLFR-00315, LLFR-00310: every label shows the new name.
        area.name_str = stripped_name_str
        # LLFR-00309: a typed "Area N" uses up N, like LLFR-00212.
        self.take_area_number(stripped_name_str)
        return True

    def set_area_color(self, area_id_i: int, color_str: str) -> bool:
        """Give an area another color, on every time plot.

        Inputs:
            area_id_i: id of the area.
            color_str: the color, written as "#rrggbb" (any case).
        Outputs: True when the color changed; False when no area has
            that id, the value is not "#rrggbb" or it is the area's
            current color.
        """
        # LLFR-00351, LLFR-00390: any color confirmed in the picker; the
        # color the area already has changes nothing.
        new_color_str = hex_color_or_none(color_str)
        area = self.find_area(area_id_i)
        if area is None or new_color_str is None:
            return False
        if area.color_str == new_color_str:
            return False
        # LLFR-00310: every time plot draws it in the new color.
        area.color_str = new_color_str
        return True

    def remove_area(self, area_id_i: int) -> bool:
        """Remove an area from every time plot.

        Inputs:
            area_id_i: id of the area.
        Outputs: True when the area was removed, False when no area has
            that id.
        """
        # LLFR-00316: the area and its label leave every plot.
        area = self.find_area(area_id_i)
        if area is None:
            return False
        # LLFR-00309: next_area_number_i is not lowered.
        self.area_list.remove(area)
        return True

    def remove_all_areas(self) -> int:
        """Remove every area from every time plot.

        Inputs: none.
        Outputs: the number of areas removed.
        """
        # LLFR-00417, LLFR-00310: every area leaves every time plot.
        # LLFR-00309: next_area_number_i is not lowered.
        removed_count_i = len(self.area_list)
        self.area_list = []
        return removed_count_i

    def area_state_tuple(self) -> tuple:
        """Return the areas as plain values.

        Inputs: none.
        Outputs: a tuple of (area_id_i, name_str, start_s, end_s,
            color_str), in creation order.
        """
        # LLFR-00140, LLFR-00310, LLFR-00351: the drawing data of every
        # area.
        return tuple((area.area_id_i, area.name_str, area.start_s,
                      area.end_s, area.color_str)
                     for area in self.area_list)
