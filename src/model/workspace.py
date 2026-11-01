"""Model of the plot panel: tabs, plots, curves and pinned tips.

The workspace holds no Qt code (COR-00009). The view draws what the
workspace holds, and the controller changes the workspace when the user
acts.
"""

import math
import random
from dataclasses import dataclass

from model.curve_colors import next_curve_color

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
# LLFR-00152: label offset of a pinned tip that was never moved; the
# view then places the label beside its point by itself.
AUTOMATIC_LABEL_OFFSET_TUPLE = ()


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


class MarkerIdCounter:
    """Hands out vertical marker ids that are never reused.

    One counter is shared by all plots of a workspace, so that marker
    ids are unique across the whole workspace.

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
                vertical marker ids.
        Outputs: none.
        """
        # LLFR-00019: a new plot starts with no curves and no tips.
        self.plot_id_i = plot_id_i
        self.random_generator = random_generator
        self.curve_list = []
        self.pinned_tip_list = []
        # LLFR-00033: counts every curve ever drawn here, for the colors.
        self.drawn_count_i = 0
        # LLFR-00081: vertical markers in the order they were placed.
        if marker_id_counter is None:
            marker_id_counter = MarkerIdCounter()
        self.marker_id_counter = marker_id_counter
        self.marker_list = []
        # LLFR-00085, LLFR-00111: number of the next "Marker N"; it only
        # grows, so a deleted marker's number is never reused.
        self.next_marker_number_i = 1

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
        # LLFR-00056: a signal already in the plot is not drawn again.
        if self.has_signal(signal_name_str):
            return None
        # LLFR-00033, LLFR-00034: pick a color not used in this plot.
        used_color_list = [curve.color_str for curve in self.curve_list]
        color_str = next_curve_color(self.drawn_count_i, used_color_list,
                                     self.random_generator)
        # LLFR-00052: a new curve uses preset width 1.
        curve = Curve(signal_name_str, color_str, DEFAULT_WIDTH_I)
        self.curve_list.append(curve)
        self.drawn_count_i += 1
        return curve

    def remove_curve(self, signal_name_str: str) -> bool:
        """Remove a signal's curve and its pinned tips from the plot.

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

    def add_marker(self, time_s: float) -> VerticalMarker:
        """Place a new vertical marker in the plot.

        Inputs:
            time_s: time of the marker, in seconds; stored as given.
        Outputs: the new VerticalMarker, named "Marker N" (LLFR-00085).
        """
        # LLFR-00081: the marker is placed at the clicked time.
        # LLFR-00085: "Marker N" with N counting per plot.
        name_str = DEFAULT_MARKER_NAME_FORMAT_STR.format(
            self.next_marker_number_i)
        # LLFR-00111: the number only grows and is never reused.
        self.next_marker_number_i += 1
        marker = VerticalMarker(self.marker_id_counter.take_next_id(),
                                name_str, float(time_s))
        self.marker_list.append(marker)
        return marker

    def find_marker(self, marker_id_i: int):
        """Return a vertical marker of this plot by its id.

        Inputs:
            marker_id_i: id of the marker.
        Outputs: the VerticalMarker, or None when it is not in this plot.
        """
        # LLFR-00086, LLFR-00088, LLFR-00091: markers are found by id.
        for marker in self.marker_list:
            if marker.marker_id_i == marker_id_i:
                return marker
        return None

    def move_marker(self, marker_id_i: int, time_s: float) -> bool:
        """Move a vertical marker to a new time.

        Inputs:
            marker_id_i: id of the marker.
            time_s: new time of the marker, in seconds; stored as given.
        Outputs: True when the marker was moved, False when it is not in
            this plot.
        """
        # LLFR-00086: the marker is left where the mouse button is
        # released.
        marker = self.find_marker(marker_id_i)
        if marker is None:
            return False
        marker.time_s = float(time_s)
        return True

    def rename_marker(self, marker_id_i: int, new_name_str: str) -> bool:
        """Rename a vertical marker.

        Inputs:
            marker_id_i: id of the marker.
            new_name_str: the name typed by the user; surrounding spaces
                are removed.
        Outputs: True when the marker was renamed; False when the name is
            empty or only spaces (LLFR-00089) or the marker is not in
            this plot.
        """
        # LLFR-00089: an empty or blank name keeps the previous name.
        stripped_name_str = new_name_str.strip()
        marker = self.find_marker(marker_id_i)
        if marker is None or not stripped_name_str:
            return False
        # LLFR-00088, LLFR-00112: the label shows the typed name.
        marker.name_str = stripped_name_str
        return True

    def remove_marker(self, marker_id_i: int) -> bool:
        """Remove a vertical marker from the plot.

        Inputs:
            marker_id_i: id of the marker.
        Outputs: True when the marker was removed, False when it is not
            in this plot.
        """
        # LLFR-00091: the marker and its label leave the plot.
        marker = self.find_marker(marker_id_i)
        if marker is None:
            return False
        # LLFR-00111: next_marker_number_i is not lowered, so the
        # deleted number is not reused.
        self.marker_list.remove(marker)
        return True


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
        # LLFR-00081: marker ids are unique across all plots and keep
        # counting up after reset().
        self.marker_id_counter = MarkerIdCounter()
        self.tab_list = []
        # LLFR-00024: the app starts with one tab.
        self.reset()

    def reset(self) -> None:
        """Close all tabs and plots and leave one empty tab "Tab 1".

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00015: close all tabs and plots of the previous file.
        self.tab_list = []
        # LLFR-00016: one tab with no plots; ids keep counting up.
        self.add_tab()

    def next_tab_name(self) -> str:
        """Return the default name of a new tab.

        Inputs: none.
        Outputs: "Tab <n>", where n is the smallest number from 1 up
            that no current tab name uses.
        """
        # LLFR-00026: default names "Tab 1", "Tab 2", ...
        used_name_set = {tab.name_str for tab in self.tab_list}
        number_i = 1
        while f"{TAB_NAME_PREFIX_STR}{number_i}" in used_name_set:
            number_i += 1
        return f"{TAB_NAME_PREFIX_STR}{number_i}"

    def add_tab(self) -> Tab:
        """Add a new empty tab after the last one.

        Inputs: none.
        Outputs: the new Tab.
        """
        # LLFR-00026: the "+" button adds a new tab.
        tab = Tab(self.next_tab_id_i, self.next_tab_name())
        self.next_tab_id_i += 1
        self.tab_list.append(tab)
        return tab

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
        return True

    def rename_tab(self, tab_id_i: int, new_name_str: str) -> bool:
        """Rename a tab.

        Inputs:
            tab_id_i: id of the tab.
            new_name_str: the name typed by the user; surrounding spaces
                are removed.
        Outputs: True when the tab was renamed; False when the name is
            empty or only spaces (LLFR-00067) or no tab has that id.
        """
        # LLFR-00067: an empty or blank name keeps the previous name.
        stripped_name_str = new_name_str.strip()
        tab = self.find_tab(tab_id_i)
        if tab is None or not stripped_name_str:
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
