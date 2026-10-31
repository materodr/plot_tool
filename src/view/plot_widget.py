"""Plot widget: one plot area where signal curves are drawn.

The widget is pure view (COR-00003, COR-00009). It draws the curves,
legend and tips it is given and emits a Qt signal for every request the
user makes (delete a curve, change a width, delete the plot, pin a tip,
delete a pinned tip, drop a signal, change the time range). The plot
controller decides what to do with each request.

Two coordinate systems are used:
- widget coordinates: Qt pixels of this widget, y grows downwards;
- display coordinates: matplotlib pixels of the canvas, y grows upwards
  and the values are scaled by the device pixel ratio.
All conversions between them go through ``widget_to_display_tuple`` and
``display_to_widget_point``.
"""

import numpy as np
from matplotlib.backend_bases import MouseButton
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.colors import to_hex
from matplotlib.figure import Figure
from PyQt6 import sip
from PyQt6.QtCore import QPoint, QTimer, pyqtSignal
from PyQt6.QtWidgets import QMenu, QVBoxLayout, QWidget

from controller.plot_tools import NO_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR

# LLFR-00021: same literal string the signal list uses for its drags.
SIGNAL_MIME_TYPE_STR = "application/x-plot-tool-signal"
# LLFR-00041, LLFR-00052: preset width -> matplotlib line width; a
# higher preset is a wider curve (HLFR-00023).
WIDTH_PIXELS_DICT = {1: 1.0, 2: 2.0, 3: 3.0, 4: 4.5, 5: 6.0}
# LLFR-00038, LLFR-00042: how close (screen pixels) the mouse must be to
# a curve, or to a pinned tip's point, to be "on" it.
PICK_TOLERANCE_PIXELS_I = 6

TIME_AXIS_LABEL_STR = "Time (s)"
# LLFR-00074: range width kept per forward wheel step.
ZOOM_IN_FACTOR_F = 0.8
# LLFR-00078: a click with the Zoom tool halves the range width.
CLICK_ZOOM_FACTOR_F = 0.5
SINGLE_SAMPLE_HALF_RANGE_S = 0.5
VALUE_MARGIN_RATIO_F = 0.05
CONSTANT_VALUE_HALF_RANGE_F = 0.5
LEGEND_FONT_SIZE_LIST = [10.0, 9.0, 8.0, 7.0, 6.0]
LEGEND_MAXIMUM_HEIGHT_RATIO_F = 0.4
LEGEND_USABLE_WIDTH_RATIO_F = 0.95
POINTS_PER_INCH_F = 72.0
TIP_OFFSET_POINTS_F = 10.0
DEFAULT_TIP_COLOR_STR = "#000000"


def format_tip_text(signal_name_str: str, time_s: float,
                    value_f: float) -> str:
    """Return the two-line text of a hover or pinned tip.

    Inputs:
        signal_name_str: name of the signal of the curve.
        time_s: x-axis value of the point, in seconds.
        value_f: y-axis value of the point, as stored in the file.
    Outputs: the text ``t = <time> s`` and ``<name> = <value>`` on two
        lines.
    """
    # LLFR-00043: the x value is shown in seconds.
    # LLFR-00044: the y value is shown as stored, without a unit.
    return f"t = {time_s:.6g} s\n{signal_name_str} = {value_f:.6g}"


def padded_range_tuple(low_f: float, high_f: float,
                       half_range_f: float) -> tuple:
    """Return a range that matplotlib can show without warnings.

    Inputs:
        low_f: lower end of the range.
        high_f: upper end of the range.
        half_range_f: half width used when both ends are equal.
    Outputs: a tuple (low, high) with low < high.
    """
    # LLFR-00070: a single sample or a constant signal still gets a
    # visible, non-empty range.
    low_f, high_f = sorted((float(low_f), float(high_f)))
    if high_f - low_f <= 0.0:
        return (low_f - half_range_f, high_f + half_range_f)
    return (low_f, high_f)


def visible_value_range_tuple(time_array, value_array, start_s: float,
                              end_s: float, sorted_b: bool) -> tuple:
    """Return the lowest and highest value a curve shows in a time range.

    The curve is drawn as straight segments between its samples, so the
    part of a segment inside the range is cut at the range's ends and the
    values at the cuts are interpolated. This also covers a segment that
    crosses the whole range between two samples outside it.

    Inputs:
        time_array: the curve's time samples in seconds (numpy array).
        value_array: the curve's values (numpy array, same size).
        start_s: start of the shown range, in seconds.
        end_s: end of the shown range, in seconds.
        sorted_b: True when time_array is sorted in increasing order,
            which allows looking only at the samples near the range.
    Outputs: a tuple (low_f, high_f), or an empty tuple when no part of
        the curve is inside the range.
    """
    # LLFR-00076: every visible part of the curve must fit in the y range.
    if time_array.size == 0:
        return ()
    if time_array.size == 1:
        if start_s <= time_array[0] <= end_s:
            return (float(value_array[0]), float(value_array[0]))
        return ()
    if sorted_b:
        # Only the samples inside the range and one neighbour on each
        # side can belong to a visible segment.
        first_i = max(0, int(np.searchsorted(time_array, start_s,
                                             side="left")) - 1)
        last_i = min(time_array.size, int(np.searchsorted(
            time_array, end_s, side="right")) + 1)
        time_array = time_array[first_i:last_i]
        value_array = value_array[first_i:last_i]
        if time_array.size < 2:
            return visible_value_range_tuple(time_array, value_array,
                                             start_s, end_s, False)
    segment_start_s_array = time_array[:-1]
    segment_end_s_array = time_array[1:]
    overlap_array = ((np.maximum(segment_start_s_array, segment_end_s_array)
                      >= start_s)
                     & (np.minimum(segment_start_s_array,
                                   segment_end_s_array) <= end_s))
    if not np.any(overlap_array):
        return ()
    segment_start_s_array = segment_start_s_array[overlap_array]
    segment_end_s_array = segment_end_s_array[overlap_array]
    start_value_array = value_array[:-1][overlap_array]
    end_value_array = value_array[1:][overlap_array]
    duration_s_array = segment_end_s_array - segment_start_s_array
    safe_duration_s_array = np.where(duration_s_array != 0.0,
                                     duration_s_array, 1.0)
    value_list = []
    for endpoint_s_array, vertical_ratio_f in ((segment_start_s_array, 0.0),
                                               (segment_end_s_array, 1.0)):
        # The ends of the visible part of each segment. A vertical
        # segment (two samples at the same time) shows both its values.
        cut_s_array = np.clip(endpoint_s_array, start_s, end_s)
        ratio_array = np.where(
            duration_s_array != 0.0,
            (cut_s_array - segment_start_s_array) / safe_duration_s_array,
            vertical_ratio_f)
        value_list.append(start_value_array + ratio_array
                          * (end_value_array - start_value_array))
    visible_array = np.concatenate(value_list)
    return (float(np.min(visible_array)), float(np.max(visible_array)))


def segment_distance_array(point_array, start_array, end_array):
    """Return the distance from a point to each segment of a polyline.

    Inputs:
        point_array: the point, numpy array of shape (2,).
        start_array: segment start points, numpy array of shape (N, 2).
        end_array: segment end points, numpy array of shape (N, 2).
    Outputs: numpy array of shape (N,) with the distances.
    """
    # LLFR-00038, LLFR-00042: a curve is hit when the mouse is close to
    # one of its segments, not only to one of its samples.
    direction_array = end_array - start_array
    length_square_array = np.sum(direction_array ** 2, axis=1)
    safe_length_array = np.where(length_square_array > 0.0,
                                 length_square_array, 1.0)
    ratio_array = np.sum((point_array - start_array) * direction_array,
                         axis=1) / safe_length_array
    ratio_array = np.clip(np.where(length_square_array > 0.0, ratio_array,
                                   0.0), 0.0, 1.0)
    nearest_array = start_array + ratio_array[:, None] * direction_array
    return np.sqrt(np.sum((nearest_array - point_array) ** 2, axis=1))


class PlotWidget(QWidget):
    """One plot: signal curves against time, legend, menus and tips.

    Inputs:
        plot_id_i: identifier of the plot, chosen by the caller.
        parent: optional parent widget.
    Signals:
        curve_delete_requested(str): "Delete signal" chosen for a curve.
        curve_width_requested(str, int): a preset width 1..5 chosen.
        plot_delete_requested(): "Delete plot" chosen.
        signal_dropped(str): a signal name was dropped on the plot.
        tip_pin_requested(str, float, float): the shown hover tip
            (signal name, time in s, value) should be pinned.
        pinned_tip_delete_requested(int): "Delete" chosen on a pinned
            tip; the index refers to the list given to set_pinned_tips.
        time_range_changed(float, float): the user changed the time
            range (start in s, end in s).
    Attributes:
        plot_id_i: the identifier given at creation.
        figure: the matplotlib Figure.
        canvas: the FigureCanvasQTAgg that shows the figure.
        axes: the matplotlib Axes where the curves are drawn.
    """

    curve_delete_requested = pyqtSignal(str)
    curve_width_requested = pyqtSignal(str, int)
    plot_delete_requested = pyqtSignal()
    signal_dropped = pyqtSignal(str)
    tip_pin_requested = pyqtSignal(str, float, float)
    pinned_tip_delete_requested = pyqtSignal(int)
    time_range_changed = pyqtSignal(float, float)

    def __init__(self, plot_id_i: int, parent=None) -> None:
        """Create an empty plot.

        Inputs:
            plot_id_i: identifier of the plot.
            parent: optional parent widget.
        Outputs: none.
        """
        super().__init__(parent)
        # LLFR-00068: the plot starts as empty axes with time on x.
        self.plot_id_i = plot_id_i
        self.curve_data_list = []
        self.curve_line_dict = {}
        self.curve_width_dict = {}
        self.pinned_tip_list = []
        self.pinned_annotation_list = []
        self.pinned_marker_list = []
        self.curve_sorted_list = []
        # LLFR-00042, LLFR-00045, LLFR-00078: the active plot tool.
        self.plot_tool_str = NO_TOOL_STR
        self.hover_point_tuple = ()
        self.pending_menu_point = QPoint()

        # LLFR-00035: constrained layout keeps room for the legend above
        # the axes when the widget is resized.
        self.figure = Figure(layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setParent(self)
        self.canvas.setAcceptDrops(False)
        widget_layout = QVBoxLayout(self)
        widget_layout.setContentsMargins(0, 0, 0, 0)
        widget_layout.addWidget(self.canvas)
        self.axes = self.figure.add_subplot()

        # LLFR-00021: drops are handled by this widget, not the canvas.
        self.setAcceptDrops(True)

        # LLFR-00042, LLFR-00045, LLFR-00038, LLFR-00070: the real mouse
        # events go to the same code as the public helpers.
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("button_press_event", self.on_mouse_press)
        self.canvas.mpl_connect("scroll_event", self.on_mouse_scroll)
        self.canvas.mpl_connect("figure_leave_event", self.on_mouse_leave)
        # LLFR-00035: the legend is fitted again when the canvas resizes.
        self.canvas.mpl_connect("resize_event", self.on_canvas_resize)

        self.time_range_s_tuple = (0.0, 1.0)
        self.rebuild_axes()

    # ----------------------------------------------------------------
    # Drawing
    # ----------------------------------------------------------------

    def set_curves(self, curve_data_list: list) -> None:
        """Replace all curves of the plot and redraw it.

        Inputs:
            curve_data_list: list of tuples (signal_name_str, time_array,
                value_array, color_str, width_i), in drawing order.
        Outputs: none. The time range is reset to the full range of the
            data.
        """
        # LLFR-00068: every curve is drawn against the time array.
        self.curve_data_list = [
            (str(signal_name_str), np.asarray(time_array, dtype=float),
             np.asarray(value_array, dtype=float), str(color_str),
             int(width_i))
            for (signal_name_str, time_array, value_array, color_str,
                 width_i) in curve_data_list]
        # LLFR-00042: a sorted time array allows a fast hit test.
        self.curve_sorted_list = [
            bool(curve_tuple[1].size < 2
                 or np.all(np.diff(curve_tuple[1]) >= 0.0))
            for curve_tuple in self.curve_data_list]
        # LLFR-00070: a new set of curves shows the whole time range.
        self.time_range_s_tuple = self.full_time_range_tuple()
        self.rebuild_axes()

    def set_pinned_tips(self, pinned_tip_list: list) -> None:
        """Replace the pinned tips drawn in the plot.

        Inputs:
            pinned_tip_list: list of tuples (signal_name_str, time_s,
                value_f).
        Outputs: none.
        """
        # LLFR-00045: pinned tips are drawn as persistent annotations.
        self.pinned_tip_list = [
            (str(signal_name_str), float(time_s), float(value_f))
            for (signal_name_str, time_s, value_f) in pinned_tip_list]
        self.draw_pinned_tips()
        self.canvas.draw_idle()

    def set_plot_tool(self, tool_str: str) -> None:
        """Choose how the plot reacts to hovers and left clicks.

        Inputs:
            tool_str: a name of controller.plot_tools: TIP_TOOL_STR
                (hover tips and pinning), ZOOM_TOOL_STR (click to zoom),
                MARKER_TOOL_STR, or NO_TOOL_STR.
        Outputs: none. Leaving the Tip tool hides the hover tip.
        """
        # LLFR-00042, LLFR-00045: tips only with the Tip tool.
        # LLFR-00078: click zoom only with the Zoom tool.
        self.plot_tool_str = str(tool_str)
        if self.plot_tool_str != TIP_TOOL_STR:
            self.hide_hover_tip()

    def set_tip_mode(self, enabled_b: bool) -> None:
        """Turn the Tip tool on or off (kept for the plot panel).

        Inputs:
            enabled_b: True selects the Tip tool; False leaves no tool
                active if the Tip tool was active, and otherwise keeps
                the current tool.
        Outputs: none.
        """
        # LLFR-00042: PlotPanel.add_plot_view still calls this with its
        # own tip state; MainWindow then applies the real tool with
        # set_plot_tool, so a False here never ends another tool.
        if enabled_b:
            self.set_plot_tool(TIP_TOOL_STR)
        elif self.plot_tool_str == TIP_TOOL_STR:
            self.set_plot_tool(NO_TOOL_STR)

    def set_time_range(self, start_s: float, end_s: float) -> None:
        """Show the given time range without emitting time_range_changed.

        Inputs:
            start_s: start of the range, in seconds.
            end_s: end of the range, in seconds.
        Outputs: none.
        """
        # LLFR-00070: the plot panel applies a range shared by the tab.
        self.time_range_s_tuple = padded_range_tuple(
            start_s, end_s, SINGLE_SAMPLE_HALF_RANGE_S)
        self.apply_time_range()
        self.canvas.draw_idle()

    def time_range_tuple(self) -> tuple:
        """Return the time range currently shown.

        Inputs: none.
        Outputs: a tuple (start_s, end_s) in seconds.
        """
        # LLFR-00070: the shown range, read from the axes.
        start_s, end_s = self.axes.get_xlim()
        return (float(start_s), float(end_s))

    def rebuild_axes(self) -> None:
        """Clear the axes and draw curves, legend and tips again.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00068: the x-axis is time in seconds.
        self.axes.clear()
        self.axes.set_xlabel(TIME_AXIS_LABEL_STR)
        # LLFR-00075: matplotlib's own pan and zoom never act on these
        # axes (there is no navigation toolbar either); the y range is
        # only set by apply_time_range (LLFR-00076).
        self.axes.set_navigate(False)
        self.curve_line_dict = {}
        self.curve_width_dict = {}
        for (signal_name_str, time_array, value_array, color_str,
             width_i) in self.curve_data_list:
            # HLFR-00020, LLFR-00041, LLFR-00052: color and width are
            # applied exactly as given.
            (line,) = self.axes.plot(
                time_array, value_array, color=color_str,
                linewidth=WIDTH_PIXELS_DICT.get(width_i, 1.0),
                label=signal_name_str)
            self.curve_line_dict[signal_name_str] = line
            self.curve_width_dict[signal_name_str] = width_i
        self.update_legend()

        # LLFR-00042: one hover annotation, hidden until needed. It is
        # left out of the layout so that it never moves the axes.
        self.hover_point_tuple = ()
        self.hover_annotation = self.axes.annotate(
            "", xy=(0.0, 0.0), xytext=(TIP_OFFSET_POINTS_F,
                                       TIP_OFFSET_POINTS_F),
            textcoords="offset points", parse_math=False,
            bbox={"boxstyle": "round", "facecolor": "#ffffe0",
                  "alpha": 0.9},
            zorder=10)
        self.hover_annotation.set_visible(False)
        self.hover_annotation.set_in_layout(False)
        self.pinned_annotation_list = []
        self.pinned_marker_list = []
        self.draw_pinned_tips()
        self.apply_time_range()
        self.canvas.draw_idle()

    def update_legend(self) -> None:
        """Draw the legend directly above the axes, or remove it.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00036: no curves, no legend.
        old_legend = self.axes.get_legend()
        if old_legend is not None:
            old_legend.remove()
        if not self.curve_line_dict:
            return
        # LLFR-00035: the legend sits above the axes, outside them, and
        # spans their width. The font size and the number of columns are
        # chosen so that the whole legend fits in the figure.
        line_list = list(self.curve_line_dict.values())
        name_list = list(self.curve_line_dict.keys())
        renderer = self.canvas.get_renderer()
        figure_width_px = float(self.figure.bbox.width)
        maximum_height_px = (float(self.figure.bbox.height)
                             * LEGEND_MAXIMUM_HEIGHT_RATIO_F)
        for font_size_f in LEGEND_FONT_SIZE_LIST:
            legend = self.place_legend(line_list, name_list, 1,
                                       font_size_f)
            text_width_px = max(text.get_window_extent(renderer).width
                                for text in legend.get_texts())
            spacing_px = ((legend.handlelength + legend.handletextpad
                           + legend.columnspacing) * font_size_f
                          * self.figure.dpi / POINTS_PER_INCH_F)
            column_count_i = max(1, min(len(line_list), int(
                figure_width_px * LEGEND_USABLE_WIDTH_RATIO_F
                // (text_width_px + spacing_px))))
            legend.remove()
            legend = self.place_legend(line_list, name_list,
                                       column_count_i, font_size_f)
            if legend.get_window_extent(renderer).height <= (
                    maximum_height_px):
                break

    def place_legend(self, line_list: list, name_list: list,
                     column_count_i: int, font_size_f: float):
        """Create the legend above the axes with plain-text names.

        Inputs:
            line_list: the curves' Line2D objects, in curve order.
            name_list: the signal names, in the same order.
            column_count_i: number of legend columns.
            font_size_f: font size in points.
        Outputs: the matplotlib Legend.
        """
        # LLFR-00035: anchored on top of the axes, outside them.
        legend = self.axes.legend(
            line_list, name_list, loc="lower left",
            bbox_to_anchor=(0.0, 1.02, 1.0, 0.2), mode="expand",
            ncol=column_count_i, borderaxespad=0.0, frameon=False,
            fontsize=font_size_f)
        for text, line in zip(legend.get_texts(), line_list):
            # LLFR-00036: names are shown literally, never as mathtext.
            text.set_parse_math(False)
            # LLFR-00037: each name has the color of its curve.
            text.set_color(line.get_color())
        return legend

    def draw_pinned_tips(self) -> None:
        """Draw the stored pinned tips, replacing the previous ones.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00045: remove the old annotations before drawing new ones.
        for artist in self.pinned_annotation_list + self.pinned_marker_list:
            artist.remove()
        self.pinned_annotation_list = []
        self.pinned_marker_list = []
        for signal_name_str, time_s, value_f in self.pinned_tip_list:
            line = self.curve_line_dict.get(signal_name_str)
            color_str = (line.get_color() if line is not None
                         else DEFAULT_TIP_COLOR_STR)
            (marker,) = self.axes.plot(
                [time_s], [value_f], marker="o", color=color_str,
                markersize=5, linestyle="none", zorder=9)
            marker.set_in_layout(False)
            annotation = self.axes.annotate(
                format_tip_text(signal_name_str, time_s, value_f),
                xy=(time_s, value_f),
                xytext=(TIP_OFFSET_POINTS_F, TIP_OFFSET_POINTS_F),
                textcoords="offset points", parse_math=False,
                bbox={"boxstyle": "round", "facecolor": "#ffffff",
                      "edgecolor": color_str, "alpha": 0.9},
                zorder=9)
            annotation.set_in_layout(False)
            self.pinned_marker_list.append(marker)
            self.pinned_annotation_list.append(annotation)
        self.place_tips()

    def full_time_range_tuple(self) -> tuple:
        """Return the time range that covers all the curves.

        Inputs: none.
        Outputs: a tuple (start_s, end_s); (0, 1) when there are no
            curves.
        """
        # LLFR-00070: the default view shows all samples.
        time_list = [curve_tuple[1] for curve_tuple in self.curve_data_list
                     if curve_tuple[1].size > 0]
        if not time_list:
            return (0.0, 1.0)
        start_s = min(float(np.min(time_array)) for time_array in time_list)
        end_s = max(float(np.max(time_array)) for time_array in time_list)
        return padded_range_tuple(start_s, end_s,
                                  SINGLE_SAMPLE_HALF_RANGE_S)

    def apply_time_range(self) -> None:
        """Set the x limits and fit the y-axis to the visible data.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00070: x shows the stored range.
        start_s, end_s = self.time_range_s_tuple
        self.axes.set_xlim(start_s, end_s)
        # LLFR-00076: y fits every curve, including segments that cross
        # the range between two samples outside it.
        range_list = []
        for curve_tuple, sorted_b in zip(self.curve_data_list,
                                         self.curve_sorted_list):
            range_tuple = visible_value_range_tuple(
                curve_tuple[1], curve_tuple[2], start_s, end_s, sorted_b)
            if range_tuple:
                range_list.append(range_tuple)
        if range_list:
            low_f = min(range_tuple[0] for range_tuple in range_list)
            high_f = max(range_tuple[1] for range_tuple in range_list)
            margin_f = (high_f - low_f) * VALUE_MARGIN_RATIO_F
            self.axes.set_ylim(*padded_range_tuple(
                low_f - margin_f, high_f + margin_f,
                max(CONSTANT_VALUE_HALF_RANGE_F,
                    abs(low_f) * VALUE_MARGIN_RATIO_F)))
        self.place_tips()

    def place_tips(self) -> None:
        """Turn tip boxes towards the inside of the axes.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00042, LLFR-00045: a tip near the right or top edge is
        # drawn on the other side of its point so it stays readable.
        annotation_list = list(self.pinned_annotation_list)
        if self.hover_point_tuple:
            annotation_list.append(self.hover_annotation)
        start_s, end_s = self.axes.get_xlim()
        low_f, high_f = self.axes.get_ylim()
        for annotation in annotation_list:
            time_s, value_f = annotation.xy
            right_half_b = time_s > (start_s + end_s) / 2.0
            upper_half_b = value_f > (low_f + high_f) / 2.0
            annotation.set_position((
                -TIP_OFFSET_POINTS_F if right_half_b
                else TIP_OFFSET_POINTS_F,
                -TIP_OFFSET_POINTS_F if upper_half_b
                else TIP_OFFSET_POINTS_F))
            annotation.set_horizontalalignment(
                "right" if right_half_b else "left")
            annotation.set_verticalalignment(
                "top" if upper_half_b else "bottom")

    def on_canvas_resize(self, event) -> None:
        """Fit the legend again after the canvas changed size.

        Inputs:
            event: the matplotlib ResizeEvent.
        Outputs: none.
        """
        # LLFR-00035: the legend stays whole above the axes after resize.
        self.update_legend()
        self.canvas.draw_idle()

    # ----------------------------------------------------------------
    # Inspection helpers (used by tests and by the plot panel)
    # ----------------------------------------------------------------

    def legend_entry_list(self) -> list:
        """Return the legend entries in curve order.

        Inputs: none.
        Outputs: list of tuples (signal_name_str, text_color_str), with
            colors as lower-case "#rrggbb" strings; empty without legend.
        """
        # LLFR-00036, LLFR-00037: names and their text colors.
        legend = self.axes.get_legend()
        if legend is None:
            return []
        return [(text.get_text(), to_hex(text.get_color()))
                for text in legend.get_texts()]

    def curve_line_width(self, signal_name_str: str) -> float:
        """Return the matplotlib line width of a curve.

        Inputs:
            signal_name_str: name of the signal of the curve.
        Outputs: the line width; 0.0 when there is no such curve.
        """
        # LLFR-00041, LLFR-00052: the width the curve is drawn with.
        line = self.curve_line_dict.get(signal_name_str)
        return float(line.get_linewidth()) if line is not None else 0.0

    def hover_tip_text(self) -> str:
        """Return the text of the visible hover tip.

        Inputs: none.
        Outputs: the tip text, or "" when the hover tip is hidden.
        """
        # LLFR-00042: the hover tip is visible only when a point is shown.
        if not self.hover_point_tuple:
            return ""
        return self.hover_annotation.get_text()

    def pinned_tip_count(self) -> int:
        """Return how many pinned tips are drawn.

        Inputs: none.
        Outputs: the number of pinned tip annotations in the plot.
        """
        # LLFR-00045: one annotation per pinned tip.
        return len(self.pinned_annotation_list)

    # ----------------------------------------------------------------
    # Coordinates
    # ----------------------------------------------------------------

    def pixel_ratio_f(self) -> float:
        """Return the canvas device pixel ratio.

        Inputs: none.
        Outputs: display pixels per widget pixel.
        """
        # LLFR-00038, LLFR-00042: display pixels may be scaled.
        return float(getattr(self.canvas, "device_pixel_ratio", 1.0) or 1.0)

    def widget_to_display_tuple(self, widget_point) -> tuple:
        """Convert a point of this widget to matplotlib display pixels.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: a tuple (x, y) in display pixels (y up from the bottom
            of the canvas, scaled by the device pixel ratio).
        """
        # LLFR-00038, LLFR-00042, LLFR-00046: the single conversion from
        # Qt to matplotlib coordinates.
        canvas_point = self.canvas.mapFrom(self, widget_point)
        ratio_f = self.pixel_ratio_f()
        return (canvas_point.x() * ratio_f,
                self.figure.bbox.height - canvas_point.y() * ratio_f)

    def display_to_widget_point(self, display_x_px: float,
                                display_y_px: float):
        """Convert matplotlib display pixels to a point of this widget.

        Inputs:
            display_x_px: x in display pixels.
            display_y_px: y in display pixels (up from the bottom).
        Outputs: QPoint in this widget's coordinates.
        """
        # LLFR-00038, LLFR-00042, LLFR-00046: inverse of
        # widget_to_display_tuple.
        ratio_f = self.pixel_ratio_f()
        canvas_point = QPoint(
            int(round(display_x_px / ratio_f)),
            int(round((self.figure.bbox.height - display_y_px) / ratio_f)))
        return self.canvas.mapTo(self, canvas_point)

    def data_to_widget_point(self, time_s: float, value_f: float):
        """Convert a data point of the axes to a point of this widget.

        Inputs:
            time_s: x value in seconds.
            value_f: y value.
        Outputs: QPoint in this widget's coordinates.
        """
        # LLFR-00042: lets callers aim at a sample of a curve.
        display_x_px, display_y_px = self.axes.transData.transform(
            (time_s, value_f))
        return self.display_to_widget_point(float(display_x_px),
                                            float(display_y_px))

    def inside_axes_b(self, display_x_px: float,
                      display_y_px: float) -> bool:
        """Tell whether a display point is inside the axes area.

        Inputs:
            display_x_px: x in display pixels.
            display_y_px: y in display pixels.
        Outputs: True when the point is inside the axes.
        """
        # LLFR-00038, LLFR-00048: only the axes area holds curves.
        return bool(self.axes.bbox.contains(display_x_px, display_y_px))

    # ----------------------------------------------------------------
    # Hit tests
    # ----------------------------------------------------------------

    def nearest_curve_tuple(self, widget_point) -> tuple:
        """Find the curve under a point and its nearest sample.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: a tuple (signal_name_str, time_s, value_f) of the nearest
            sample of the closest curve within PICK_TOLERANCE_PIXELS_I, or
            an empty tuple when no curve is close enough.
        """
        # LLFR-00038, LLFR-00042: hit test in display pixels.
        display_x_px, display_y_px = self.widget_to_display_tuple(
            widget_point)
        if not self.inside_axes_b(display_x_px, display_y_px):
            return ()
        point_array = np.array([display_x_px, display_y_px])
        tolerance_px = PICK_TOLERANCE_PIXELS_I * self.pixel_ratio_f()
        inverse_transform = self.axes.transData.inverted()
        window_start_s = float(inverse_transform.transform(
            (display_x_px - tolerance_px, display_y_px))[0])
        window_end_s = float(inverse_transform.transform(
            (display_x_px + tolerance_px, display_y_px))[0])
        best_distance_px = tolerance_px
        best_tuple = ()
        for curve_tuple, sorted_b in zip(self.curve_data_list,
                                         self.curve_sorted_list):
            signal_name_str, time_array, value_array = curve_tuple[:3]
            if sorted_b:
                # Only samples near the mouse time can be within the
                # tolerance; one more on each side keeps the segments
                # that cross the window.
                first_i = max(0, int(np.searchsorted(
                    time_array, window_start_s, side="left")) - 1)
                last_i = min(time_array.size, int(np.searchsorted(
                    time_array, window_end_s, side="right")) + 1)
            else:
                first_i, last_i = 0, time_array.size
            if last_i <= first_i:
                continue
            sample_array = self.axes.transData.transform(np.column_stack(
                (time_array[first_i:last_i], value_array[first_i:last_i])))
            if sample_array.shape[0] == 1:
                distance_px = float(np.hypot(
                    *(sample_array[0] - point_array)))
            else:
                distance_px = float(np.min(segment_distance_array(
                    point_array, sample_array[:-1], sample_array[1:])))
            # Later curves are drawn on top, so they win ties.
            if distance_px <= best_distance_px:
                sample_distance_array = np.hypot(
                    sample_array[:, 0] - point_array[0],
                    sample_array[:, 1] - point_array[1])
                index_i = first_i + int(np.argmin(sample_distance_array))
                best_distance_px = distance_px
                best_tuple = (signal_name_str, float(time_array[index_i]),
                              float(value_array[index_i]))
        return best_tuple

    def curve_at(self, widget_point) -> str:
        """Return the name of the curve under a point.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: the signal name, or "" when no curve is there.
        """
        # LLFR-00038, LLFR-00040: the curve a right-click refers to.
        nearest_tuple = self.nearest_curve_tuple(widget_point)
        return nearest_tuple[0] if nearest_tuple else ""

    def pinned_tip_at(self, widget_point) -> int:
        """Return the index of the pinned tip under a point.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: the index in the list given to set_pinned_tips, or -1
            when no pinned tip is there.
        """
        # LLFR-00046: a pinned tip is hit on its box or near its point.
        display_x_px, display_y_px = self.widget_to_display_tuple(
            widget_point)
        tolerance_px = PICK_TOLERANCE_PIXELS_I * self.pixel_ratio_f()
        renderer = self.canvas.get_renderer()
        # The last drawn tip is on top, so it is checked first.
        for index_i in reversed(range(len(self.pinned_annotation_list))):
            annotation = self.pinned_annotation_list[index_i]
            point_x_px, point_y_px = self.axes.transData.transform(
                annotation.xy)
            # A tip whose point is out of view is not drawn.
            if not self.inside_axes_b(float(point_x_px), float(point_y_px)):
                continue
            if np.hypot(point_x_px - display_x_px,
                        point_y_px - display_y_px) <= tolerance_px:
                return index_i
            if annotation.get_window_extent(renderer).contains(
                    display_x_px, display_y_px):
                return index_i
        return -1

    # ----------------------------------------------------------------
    # User actions
    # ----------------------------------------------------------------

    def context_menu_and_requests(self, widget_point) -> tuple:
        """Build the context menu for a point and the request of each item.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: a tuple (menu, request_list). The data of each action is
            the index in request_list of the function (no arguments) that
            emits that action's request. No action is connected yet.
        """
        menu = QMenu(self)
        request_list = []

        def add_request_action(target_menu, text_str: str, request):
            """Add an action and remember the request it stands for.

            Inputs:
                target_menu: the QMenu that receives the action.
                text_str: the action text.
                request: function without arguments that emits the
                    request.
            Outputs: the new QAction.
            """
            # LLFR-00038, LLFR-00040, LLFR-00046, LLFR-00048.
            action = target_menu.addAction(text_str)
            action.setData(len(request_list))
            request_list.append(request)
            return action

        # LLFR-00046: a pinned tip has priority over a curve under it.
        tip_index_i = self.pinned_tip_at(widget_point)
        if tip_index_i >= 0:
            add_request_action(
                menu, "Delete",
                lambda index_i=tip_index_i:
                self.pinned_tip_delete_requested.emit(index_i))
            return menu, request_list
        signal_name_str = self.curve_at(widget_point)
        if signal_name_str:
            # LLFR-00038: delete the curve.
            add_request_action(
                menu, "Delete signal",
                lambda name_str=signal_name_str:
                self.curve_delete_requested.emit(name_str))
            # LLFR-00040: the preset widths, the current one checked.
            width_menu = menu.addMenu("Width")
            current_width_i = self.curve_width_dict.get(signal_name_str, 1)
            for width_i in sorted(WIDTH_PIXELS_DICT):
                width_action = add_request_action(
                    width_menu, str(width_i),
                    lambda name_str=signal_name_str,
                    chosen_width_i=width_i:
                    self.curve_width_requested.emit(name_str,
                                                    chosen_width_i))
                width_action.setCheckable(True)
                width_action.setChecked(width_i == current_width_i)
            return menu, request_list
        # LLFR-00048: empty area of the plot.
        add_request_action(menu, "Delete plot",
                           lambda: self.plot_delete_requested.emit())
        return menu, request_list

    def build_context_menu(self, widget_point) -> QMenu:
        """Build the menu that a right-click at a point shows.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: a QMenu (not shown) whose actions emit their request
            when triggered. On a pinned tip it has "Delete"; on a curve
            "Delete signal" and a "Width" submenu with 1..5; elsewhere
            "Delete plot".
        """
        # LLFR-00038, LLFR-00040, LLFR-00046, LLFR-00048.
        menu, request_list = self.context_menu_and_requests(widget_point)
        action_list = list(menu.actions())
        for action in list(action_list):
            if action.menu() is not None:
                action_list.extend(action.menu().actions())
        for action in action_list:
            if action.data() is not None:
                action.triggered.connect(
                    lambda checked_b=False,
                    request=request_list[action.data()]: request())
        return menu

    def request_context_menu(self, widget_point) -> None:
        """Open the context menu for a point once control is back in Qt.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none.
        """
        # LLFR-00038, LLFR-00046, LLFR-00048: the menu is not run inside
        # the mouse press handling, so a request that deletes this
        # widget never deletes code that is still running.
        self.pending_menu_point = QPoint(widget_point)
        QTimer.singleShot(0, self.show_pending_context_menu)

    def show_pending_context_menu(self) -> None:
        """Show the menu asked for by request_context_menu.

        Inputs: none.
        Outputs: none. Does nothing if the widget was deleted meanwhile.
        """
        # LLFR-00038, LLFR-00046, LLFR-00048.
        if sip.isdeleted(self):
            return
        self.show_context_menu(self.pending_menu_point)

    def execute_menu(self, menu, global_point):
        """Run a menu modally and return the chosen action.

        Inputs:
            menu: the QMenu to show.
            global_point: QPoint in screen coordinates.
        Outputs: the chosen QAction, or None when the menu was closed
            without a choice. Tests replace this method to choose an
            action without a real modal menu.
        """
        # LLFR-00038, LLFR-00046, LLFR-00048: the modal menu.
        return menu.exec(global_point)

    def show_context_menu(self, widget_point) -> None:
        """Show the context menu at a point and emit the chosen request.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none. The request is emitted after the menu has closed
            and been deleted, as the very last step, so the receiver may
            delete this widget.
        """
        # LLFR-00039, LLFR-00041, LLFR-00047, LLFR-00049: run the menu,
        # clean it up, then emit.
        menu, request_list = self.context_menu_and_requests(widget_point)
        chosen_action = self.execute_menu(menu,
                                          self.mapToGlobal(widget_point))
        chosen_index = (chosen_action.data() if chosen_action is not None
                        else None)
        sip.delete(menu)
        if chosen_index is None:
            return
        request_list[chosen_index]()

    def hover_at(self, widget_point) -> None:
        """Show or hide the hover tip for the mouse at a point.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none.
        """
        # LLFR-00042: tips only with the Tip tool and only on a curve.
        if self.plot_tool_str != TIP_TOOL_STR:
            self.hide_hover_tip()
            return
        nearest_tuple = self.nearest_curve_tuple(widget_point)
        if not nearest_tuple:
            self.hide_hover_tip()
            return
        if nearest_tuple == self.hover_point_tuple:
            return
        signal_name_str, time_s, value_f = nearest_tuple
        self.hover_point_tuple = nearest_tuple
        # LLFR-00043, LLFR-00044: time in seconds, value as stored.
        self.hover_annotation.set_text(
            format_tip_text(signal_name_str, time_s, value_f))
        self.hover_annotation.xy = (time_s, value_f)
        self.hover_annotation.set_visible(True)
        self.place_tips()
        self.canvas.draw_idle()

    def hide_hover_tip(self) -> None:
        """Hide the hover tip if it is shown.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00042: the tip disappears off curves or out of tip mode.
        if not self.hover_point_tuple:
            return
        self.hover_point_tuple = ()
        self.hover_annotation.set_visible(False)
        self.canvas.draw_idle()

    def click_at(self, widget_point) -> None:
        """Do what a left click at a point does with the active tool.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none. With the Tip tool, emits tip_pin_requested when a
            hover tip is shown; with the Zoom tool, zooms in (see
            zoom_click_at). Other tools do nothing here.
        """
        # LLFR-00109: using a tool never changes the active tool.
        if self.plot_tool_str == ZOOM_TOOL_STR:
            # LLFR-00078: click to zoom.
            self.zoom_click_at(widget_point)
            return
        # LLFR-00045: pin the point of the hover tip that is shown.
        if self.plot_tool_str != TIP_TOOL_STR or not self.hover_point_tuple:
            return
        signal_name_str, time_s, value_f = self.hover_point_tuple
        self.tip_pin_requested.emit(signal_name_str, time_s, value_f)

    def time_at(self, widget_point) -> float:
        """Return the time on the x-axis under a point.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: the time in seconds.
        """
        # LLFR-00074, LLFR-00078: zooms are centred on this time.
        display_x_px, display_y_px = self.widget_to_display_tuple(
            widget_point)
        return float(self.axes.transData.inverted().transform(
            (display_x_px, display_y_px))[0])

    def zoom_click_at(self, widget_point) -> None:
        """Zoom the time axis in by 2, centred on the clicked time.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none. Emits time_range_changed with the new range. A
            click outside the axes area does nothing.
        """
        # LLFR-00078: only a click on the axes has a time to zoom on.
        display_x_px, display_y_px = self.widget_to_display_tuple(
            widget_point)
        if not self.inside_axes_b(display_x_px, display_y_px):
            return
        center_s = self.time_at(widget_point)
        start_s, end_s = self.time_range_tuple()
        # LLFR-00078: half the width, centred on the click.
        half_width_s = (end_s - start_s) * CLICK_ZOOM_FACTOR_F / 2.0
        self.zoom_to_range(center_s - half_width_s, center_s + half_width_s)

    def wheel_at(self, widget_point, step_f: float) -> None:
        """Zoom the time axis around a point, as the mouse wheel does.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
            step_f: wheel steps; positive (forward) zooms in, negative
                (backward) zooms out.
        Outputs: none. Emits time_range_changed with the new range.
        """
        # LLFR-00074: zoom around the time under the mouse.
        # LLFR-00108: whatever plot tool is active, or none.
        if step_f == 0:
            return
        center_s = self.time_at(widget_point)
        factor_f = ZOOM_IN_FACTOR_F ** float(step_f)
        start_s, end_s = self.time_range_tuple()
        self.zoom_to_range(center_s + (start_s - center_s) * factor_f,
                           center_s + (end_s - center_s) * factor_f)

    def zoom_to_range(self, new_start_s: float, new_end_s: float) -> None:
        """Show a zoomed time range, kept inside the data's range.

        Inputs:
            new_start_s: wanted start of the range, in seconds.
            new_end_s: wanted end of the range, in seconds.
        Outputs: none. Emits time_range_changed when the range changed,
            so that the whole tab follows (LLFR-00070).
        """
        # LLFR-00074, LLFR-00078: an empty range cannot be shown.
        if not new_end_s > new_start_s:
            return
        start_s, end_s = self.time_range_tuple()
        # LLFR-00074: zooming out never goes beyond the data's range.
        full_start_s, full_end_s = self.full_time_range_tuple()
        if new_end_s - new_start_s >= full_end_s - full_start_s:
            new_start_s, new_end_s = full_start_s, full_end_s
        elif new_start_s < full_start_s:
            new_start_s, new_end_s = (
                full_start_s, full_start_s + new_end_s - new_start_s)
        elif new_end_s > full_end_s:
            new_start_s, new_end_s = (
                full_end_s - (new_end_s - new_start_s), full_end_s)
        if (new_start_s, new_end_s) == (start_s, end_s):
            return
        # LLFR-00076: apply_time_range fits y to the new range.
        self.time_range_s_tuple = (new_start_s, new_end_s)
        self.apply_time_range()
        self.canvas.draw_idle()
        # LLFR-00070: the plot panel shares the range with the tab.
        self.time_range_changed.emit(new_start_s, new_end_s)

    # ----------------------------------------------------------------
    # matplotlib event handlers
    # ----------------------------------------------------------------

    def on_mouse_move(self, event) -> None:
        """Handle a matplotlib mouse move on the canvas.

        Inputs:
            event: the matplotlib MouseEvent.
        Outputs: none.
        """
        # LLFR-00042: a move runs the hover code.
        self.hover_at(self.display_to_widget_point(event.x, event.y))

    def on_mouse_press(self, event) -> None:
        """Handle a matplotlib mouse press on the canvas.

        Inputs:
            event: the matplotlib MouseEvent.
        Outputs: none.
        """
        # LLFR-00045, LLFR-00078: the second press of a double-click must
        # not pin the same tip again nor zoom a second time.
        if event.dblclick:
            return
        widget_point = self.display_to_widget_point(event.x, event.y)
        if event.button == MouseButton.LEFT:
            # LLFR-00045: a left click pins the shown tip; LLFR-00078:
            # with the Zoom tool it zooms in.
            self.click_at(widget_point)
        elif event.button == MouseButton.RIGHT:
            # LLFR-00038, LLFR-00046, LLFR-00048: show the menu once this
            # press has been handled.
            self.request_context_menu(widget_point)

    def on_mouse_scroll(self, event) -> None:
        """Handle a matplotlib scroll on the canvas.

        Inputs:
            event: the matplotlib MouseEvent of the wheel.
        Outputs: none.
        """
        # LLFR-00074, LLFR-00108: the wheel runs the zoom code with any
        # tool.
        self.wheel_at(self.display_to_widget_point(event.x, event.y),
                      float(event.step))

    def on_mouse_leave(self, event) -> None:
        """Hide the hover tip when the mouse leaves the canvas.

        Inputs:
            event: the matplotlib LocationEvent.
        Outputs: none.
        """
        # LLFR-00042: no curve under the mouse, no tip.
        self.hide_hover_tip()

    # ----------------------------------------------------------------
    # Drag and drop
    # ----------------------------------------------------------------

    def signal_name_from_mime(self, mime_data) -> str:
        """Return the signal name carried by drag data.

        Inputs:
            mime_data: the QMimeData of the drag.
        Outputs: the signal name, or "" when the data is not a signal.
        """
        # LLFR-00021: only drags of the signal list carry this type.
        if mime_data is None or not mime_data.hasFormat(
                SIGNAL_MIME_TYPE_STR):
            return ""
        raw_bytes = mime_data.data(SIGNAL_MIME_TYPE_STR).data()
        return raw_bytes.decode("utf-8", errors="replace")

    def dragEnterEvent(self, event) -> None:
        """Accept a drag only when it carries a signal name.

        Inputs:
            event: the QDragEnterEvent.
        Outputs: none.
        """
        # LLFR-00021: accept signal drags, ignore anything else.
        if self.signal_name_from_mime(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        """Keep accepting a signal drag while it moves over the plot.

        Inputs:
            event: the QDragMoveEvent.
        Outputs: none.
        """
        # LLFR-00021: same rule as on enter.
        if self.signal_name_from_mime(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        """Emit signal_dropped with the dropped signal name.

        Inputs:
            event: the QDropEvent.
        Outputs: none.
        """
        # LLFR-00021: the controller decides what to do with the name
        # (including duplicates, LLFR-00056 and LLFR-00057).
        signal_name_str = self.signal_name_from_mime(event.mimeData())
        if not signal_name_str:
            event.ignore()
            return
        event.acceptProposedAction()
        self.signal_dropped.emit(signal_name_str)
