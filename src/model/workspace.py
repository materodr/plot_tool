"""Model of the plot panel: tabs, plots, curves, tips and markers.

The workspace holds no Qt code (COR-00009). The view draws what the
workspace holds, and the controller changes the workspace when the user
acts.
"""

import copy
import math
import random
import re
from dataclasses import dataclass

from model.curve_colors import PALETTE_COLOR_TUPLE, next_curve_color

# LLFR-00031: maximum number of plots in one tab (HLFR-00018).
MAXIMUM_PLOTS_PER_TAB_I = 5
# LLFR-00041: preset curve widths (HLFR-00023).
PRESET_WIDTH_TUPLE = (1, 2, 3, 4, 5)
# LLFR-00052: width of a newly drawn curve.
DEFAULT_WIDTH_I = 1
# LLFR-00024: prefix of the default tab names ("Tab 1", "Tab 2", ...).
TAB_NAME_PREFIX_STR = "Tab "
# LLFR-00085: default name of a new vertical marker ("Marker 1", ...).
DEFAULT_MARKER_NAME_FORMAT_STR = "Marker {}"
# LLFR-00111, LLFR-00233: a default marker name, to read its number back
# when a marker of a layout file keeps its saved name.
DEFAULT_MARKER_NAME_PATTERN_STR = r"Marker (\d+)"
# LLFR-00152: label offset of a pinned tip that was never moved; the
# view then places the label beside its point by itself.
AUTOMATIC_LABEL_OFFSET_TUPLE = ()
# LLFR-00168, LLFR-00170: the two kinds of delta markers, a Delta X
# marker (time difference) and a Delta Y marker (value difference).
DELTA_X_KIND_STR = "x"
DELTA_Y_KIND_STR = "y"
DELTA_KIND_TUPLE = (DELTA_X_KIND_STR, DELTA_Y_KIND_STR)


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
class VerticalMarker:
    """A vertical line drawn across a plot at one time value (HLFR-00028).

    Inputs:
        marker_id_i: id of the marker, unique within the workspace and
            never reused.
        name_str: name shown in the marker's label (LLFR-00084).
        time_s: time of the marker on the x-axis, in seconds.
    """

    marker_id_i: int
    name_str: str
    time_s: float


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
    """

    delta_marker_id_i: int
    kind_str: str
    first_point_tuple: tuple
    second_point_tuple: tuple

    def delta_f(self) -> float:
        """Return the measured difference, second point minus first.

        Inputs: none.
        Outputs: for a Delta X marker the time difference in seconds
            (LLFR-00169); for a Delta Y marker the value difference
            (LLFR-00171). It is signed.
        """
        # LLFR-00169, LLFR-00171: second minus first, never the absolute
        # value, so the sign tells the order of the two points.
        index_i = 1 if self.kind_str == DELTA_X_KIND_STR else 2
        return (float(self.second_point_tuple[index_i])
                - float(self.first_point_tuple[index_i]))

    def has_point_on(self, signal_name_str: str) -> bool:
        """Tell whether one of the two points is on a signal's curve.

        Inputs:
            signal_name_str: name of the signal.
        Outputs: True when the first or the second point is on it.
        """
        # LLFR-00178: such a marker goes away with the curve.
        return signal_name_str in (self.first_point_tuple[0],
                                   self.second_point_tuple[0])


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

    Inputs:
        plot_id_i: id of the plot, unique within the workspace.
        random_generator: random.Random used for the curve colors from
            the 9th curve on (LLFR-00034).
        marker_id_counter: optional MarkerIdCounter shared with the other
            plots of the workspace; a new one is used when it is None.
    """

    def __init__(self, plot_id_i: int, random_generator,
                 marker_id_counter=None) -> None:
        """Create an empty plot.

        Inputs:
            plot_id_i: id of the plot, unique within the workspace.
            random_generator: random.Random used for curve colors.
            marker_id_counter: optional shared MarkerIdCounter for the
                delta marker ids.
        Outputs: none.
        """
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

    def is_empty(self) -> bool:
        """Tell whether the plot has no curves.

        Inputs: none.
        Outputs: True when the plot has no curves.
        """
        # LLFR-00051: an empty plot is deleted by the workspace; markers
        # are not curves, so they do not keep the plot alive.
        return not self.curve_list

    def add_delta_marker(self, kind_str: str, first_point_tuple,
                         second_point_tuple) -> DeltaMarker:
        """Place a new delta marker between two curve points.

        Inputs:
            kind_str: DELTA_X_KIND_STR or DELTA_Y_KIND_STR.
            first_point_tuple: (signal_name_str, time_s, value_f) of the
                first picked point.
            second_point_tuple: the same for the second picked point; it
                may be on the same curve or on another one.
        Outputs: the new DeltaMarker. Raises ValueError for an unknown
            kind, a point that is not finite, or a point on a signal
            that is not in the plot.
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
        # LLFR-00174: markers are added, never replaced.
        delta_marker = DeltaMarker(self.marker_id_counter.take_next_id(),
                                   kind_str, first_point_tuple,
                                   second_point_tuple)
        self.delta_marker_list.append(delta_marker)
        return delta_marker

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


class Tab:
    """A tab of the plot panel, holding plots stacked top to bottom.

    Inputs:
        tab_id_i: id of the tab, unique within the workspace.
        name_str: name shown on the tab.
    """

    def __init__(self, tab_id_i: int, name_str: str) -> None:
        """Create a tab with no plots.

        Inputs:
            tab_id_i: id of the tab, unique within the workspace.
            name_str: name shown on the tab.
        Outputs: none.
        """
        # LLFR-00026: a new tab has no plots.
        self.tab_id_i = tab_id_i
        self.name_str = name_str
        # LLFR-00069: plots in order from top to bottom.
        self.plot_list = []

    def is_full(self) -> bool:
        """Tell whether the tab holds the maximum number of plots.

        Inputs: none.
        Outputs: True when no more plots can be added (LLFR-00031).
        """
        # LLFR-00031: a full tab blocks new plots.
        return len(self.plot_list) >= MAXIMUM_PLOTS_PER_TAB_I

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


def plot_state_tuple(plot) -> tuple:
    """Return everything an undo restores of a plot, as plain values.

    Inputs:
        plot: the Plot.
    Outputs: a tuple (plot_id_i, drawn_count_i, curve tuples
        (signal_name_str, color_str, width_i), pinned tip tuples
        (signal_name_str, time_s, value_f, label_offset_tuple), delta
        marker tuples (delta_marker_id_i, kind_str, first_point_tuple,
        second_point_tuple)).
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
    # LLFR-00140: placing and deleting a delta marker are undoable.
    delta_marker_tuple = tuple(
        (delta_marker.delta_marker_id_i, delta_marker.kind_str,
         tuple(delta_marker.first_point_tuple),
         tuple(delta_marker.second_point_tuple))
        for delta_marker in plot.delta_marker_list)
    return (plot.plot_id_i, plot.drawn_count_i, curve_tuple,
            pinned_tip_tuple, delta_marker_tuple)


def tabs_state_tuple(tab_list: list, marker_list: list) -> tuple:
    """Return tabs and vertical markers as plain values.

    Inputs:
        tab_list: the Tab objects, in tab order.
        marker_list: the VerticalMarker objects, in placing order.
    Outputs: a tuple (tab tuple, marker tuple): one entry (tab_id_i,
        name_str, plot state tuples) per tab and one entry (marker_id_i,
        name_str, time_s) per marker; two states with equal tuples show
        the same thing (LLFR-00140).
    """
    # LLFR-00138, LLFR-00140: what an undo restores.
    tab_tuple = tuple(
        (tab.tab_id_i, tab.name_str,
         tuple(plot_state_tuple(plot) for plot in tab.plot_list))
        for tab in tab_list)
    marker_tuple = tuple((marker.marker_id_i, marker.name_str, marker.time_s)
                         for marker in marker_list)
    return (tab_tuple, marker_tuple)


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
    """

    def __init__(self, tab_list: list, state_tuple: tuple,
                 current_tab_id_i: int = -1, marker_list=()) -> None:
        """Store the saved state.

        Inputs:
            tab_list: deep copy of the tabs.
            state_tuple: plain-value dump of the tabs and markers.
            current_tab_id_i: id of the selected tab, -1 when unknown.
            marker_list: copies of the vertical markers.
        Outputs: none.
        """
        # LLFR-00138: the state to return to. LLFR-00205: the shared
        # vertical markers are part of it.
        self.tab_list = tab_list
        self.state_tuple = state_tuple
        self.current_tab_id_i = current_tab_id_i
        self.marker_list = list(marker_list)

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
                                            self.marker_list)


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
        # grows, and only reset() (a file opened) restarts it.
        self.next_tab_number_i = 1
        # LLFR-00081: marker ids are unique across all plots and keep
        # counting up after reset().
        self.marker_id_counter = MarkerIdCounter()
        self.tab_list = []
        # LLFR-00205: the vertical markers, shared by every plot of every
        # tab, in the order they were placed.
        self.marker_list = []
        # LLFR-00085, LLFR-00111: number of the next "Marker N"; it only
        # grows, also on undo, until a file is opened (reset).
        self.next_marker_number_i = 1
        # LLFR-00024: the app starts with one tab.
        self.reset()

    def reset(self) -> None:
        """Close all tabs and plots and leave one empty tab "Tab 1".

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00015: close all tabs and plots of the previous file.
        self.tab_list = []
        # LLFR-00205: with no plot left, no marker is left either.
        # LLFR-00085, LLFR-00111: a new file numbers from "Marker 1".
        self.marker_list = []
        self.next_marker_number_i = 1
        # LLFR-00210, LLFR-00016: tab numbering restarts with "Tab 1".
        self.next_tab_number_i = 1
        # LLFR-00016: one tab with no plots; ids keep counting up.
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
        self.tab_list.append(tab)
        return tab

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
        self.tab_list.append(tab)
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

    def can_delete_tab(self) -> bool:
        """Tell whether a tab may be deleted.

        Inputs: none.
        Outputs: False when only one tab is left (LLFR-00066).
        """
        # LLFR-00066: the last tab cannot be deleted.
        return len(self.tab_list) > 1

    def delete_tab(self, tab_id_i: int) -> bool:
        """Delete a tab and all its plots.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: True when the tab was deleted; False when it is the last
            tab (LLFR-00066) or no tab has that id.
        """
        # LLFR-00066: refuse to delete the last tab.
        tab = self.find_tab(tab_id_i)
        if tab is None or not self.can_delete_tab():
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

    def add_plot(self, tab_id_i: int):
        """Add a new empty plot at the bottom of a tab.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: the new Plot, or None when the tab is full (LLFR-00031)
            or no tab has that id.
        """
        # LLFR-00031: a full tab gets no new plot.
        tab = self.find_tab(tab_id_i)
        if tab is None or tab.is_full():
            return None
        # LLFR-00069: the new plot goes below the existing ones.
        plot = Plot(self.next_plot_id_i, self.random_generator,
                    self.marker_id_counter)
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
        # LLFR-00205: markers are only kept while a plot exists.
        return any(tab.plot_list for tab in self.tab_list)

    def clear_markers_without_plots(self) -> None:
        """Delete every vertical marker when no plot is left.

        Inputs: none.
        Outputs: none. The marker numbering is not restarted
            (LLFR-00111): only opening a file restarts it.
        """
        # LLFR-00205: no plot left in any tab, no marker left.
        if not self.has_plots():
            self.marker_list = []

    def add_marker(self, time_s: float) -> VerticalMarker:
        """Place a new vertical marker, shown on every plot.

        Inputs:
            time_s: time of the marker, in seconds; stored as given.
        Outputs: the new VerticalMarker, named "Marker N" (LLFR-00085).
        """
        # LLFR-00081, LLFR-00205: one marker for every plot of every tab.
        # LLFR-00085: "Marker N", N counting across the whole workspace.
        name_str = DEFAULT_MARKER_NAME_FORMAT_STR.format(
            self.next_marker_number_i)
        # LLFR-00111: the number only grows and is never reused.
        self.next_marker_number_i += 1
        marker = VerticalMarker(self.marker_id_counter.take_next_id(),
                                name_str, float(time_s))
        self.marker_list.append(marker)
        return marker

    def add_named_marker(self, name_str: str,
                         time_s: float) -> VerticalMarker:
        """Place a new vertical marker with a given name.

        Inputs:
            name_str: the name shown in the marker's label; leading and
                trailing spaces are removed. The caller makes sure it is
                not empty (LLFR-00089).
            time_s: time of the marker, in seconds.
        Outputs: the new VerticalMarker.
        """
        # LLFR-00230, LLFR-00205: a marker of a layout file keeps its
        # saved name and is shown on every plot.
        stripped_name_str = str(name_str).strip()
        marker = VerticalMarker(self.marker_id_counter.take_next_id(),
                                stripped_name_str, float(time_s))
        self.marker_list.append(marker)
        # LLFR-00085, LLFR-00111: a saved name "Marker N" uses up N, so
        # that a marker placed later never gets the same default name.
        number_match = re.fullmatch(DEFAULT_MARKER_NAME_PATTERN_STR,
                                    stripped_name_str)
        if number_match is not None:
            self.next_marker_number_i = max(
                self.next_marker_number_i, int(number_match.group(1)) + 1)
        return marker

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

    def marker_state_tuple(self) -> tuple:
        """Return the vertical markers as plain values.

        Inputs: none.
        Outputs: a tuple of (marker_id_i, name_str, time_s), in placing
            order.
        """
        # LLFR-00140, LLFR-00205: placing, moving, renaming and deleting
        # a marker change this, so they are recorded for undo.
        return tuple((marker.marker_id_i, marker.name_str, marker.time_s)
                     for marker in self.marker_list)

    def state_tuple(self) -> tuple:
        """Return the tabs, plots, curves, tips and markers as plain values.

        Inputs: none.
        Outputs: a tuple (tab tuple, marker tuple): one entry (tab_id_i,
            name_str, plot state tuples) per tab, in tab order, and the
            vertical markers (marker_state_tuple); two workspaces with
            equal tuples show the same thing (LLFR-00140).
        """
        # LLFR-00138, LLFR-00140: what an undo restores; the id counters
        # and the marker numbering are not part of it, since they only
        # grow (LLFR-00111).
        return tabs_state_tuple(self.tab_list, self.marker_list)

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
        return WorkspaceSnapshot(self.copy_tab_list(self.tab_list),
                                 self.state_tuple(), int(current_tab_id_i),
                                 copy.deepcopy(self.marker_list))

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
        # LLFR-00024, LLFR-00081: ids only grow, also after an undo.
        highest_tab_id_i = max((tab.tab_id_i for tab in self.tab_list),
                               default=0)
        self.next_tab_id_i = max(self.next_tab_id_i, highest_tab_id_i + 1)
        highest_plot_id_i = max((plot.plot_id_i for tab in self.tab_list
                                 for plot in tab.plot_list), default=0)
        self.next_plot_id_i = max(self.next_plot_id_i,
                                  highest_plot_id_i + 1)

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
