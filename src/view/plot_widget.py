"""Plot widget: one plot area where signal curves are drawn.

The widget is pure view (COR-00003, COR-00009). It draws the curves,
legend, tips, vertical markers and delta markers it is given and emits
a Qt signal for every request the user makes (delete a curve, change a
width, delete the plot, pin a tip, delete a pinned tip, drop a signal,
change the time range, place, move, rename or delete a vertical marker,
pick a delta marker point, delete a delta marker). The plot controller
decides what to do with each request.

A right-click picks the topmost item under the mouse, in drawing order:
a pinned tip, then a vertical marker, then a delta marker, then a
curve, else the empty plot area (LLFR-00046, LLFR-00110, LLFR-00177,
LLFR-00038, LLFR-00048).

A left press is handled in the same order: on a pinned tip it starts
moving the tip's label, with any plot tool or none (LLFR-00152,
LLFR-00153); with the Vertical marker tool, on a marker it starts
dragging the marker (LLFR-00086); otherwise it is a click of the active
tool (LLFR-00045, LLFR-00078, LLFR-00081). With the Delta X or Delta Y
tool, a click on a curve reports its nearest sample (LLFR-00163,
LLFR-00164), also when a vertical marker or a delta marker lies over
the curve there; a click off every curve does nothing (LLFR-00165).
The controller keeps the picked first point and tells the widget where
to draw its dot. The wheel button pans (LLFR-00117) and the right
button opens the menus; a right press first cancels any pan or drag in
progress.

A drag whose button release never arrived (for example because it
happened outside the application) is ended at the next mouse move that
shows the button is no longer held: a pan just stops, and a marker or a
pinned tip is left at its last shown position, as if the button had
been released there.

Two coordinate systems are used:
- widget coordinates: Qt pixels of this widget, y grows downwards;
- display coordinates: matplotlib pixels of the canvas, y grows upwards
  and the values are scaled by the device pixel ratio.
All conversions between them go through ``widget_to_display_tuple`` and
``display_to_widget_point``.

A pinned tip's label is drawn at the position the user gave it, moved
by the shortest distance that keeps its whole box inside the axes
(LLFR-00179). This is done each time the tip is drawn, after the
constrained layout has given the axes their final size, so it follows
every resize, zoom, pan and drag. Only the drawn position is moved: the
stored offset is kept, so the label goes back towards it when the plot
grows again.

Vertical markers are shared by every plot (LLFR-00205): the controller
gives every plot the same list. While a marker is dragged, the widget
emits marker_drag_moved on every move, and the plot panel moves the
same marker on the other plots of the tab (the plots of hidden tabs get
the new time from the controller when the button is released).

With the Vertical marker tool, a pale dashed preview line with its time
shows where a click would place a marker (LLFR-00203). The hovered plot
emits marker_preview_changed, and the plot panel shows the same preview
on the other plots of the tab. The preview is drawn by blitting, on top
of the image of the last full draw, so that following the mouse only
redraws the preview and never the curves. Its artists are not added to
the axes, so a full draw, the PDF export (LLFR-00129) and the copied
image (LLFR-00133) never contain it.

A delta marker's bracket and leader lines are computed again in display
pixels at every draw (screen, image and PDF export), from the current
position of its two points (DeltaBracketPatch), so they stay attached
to them when the range or the size changes (LLFR-00173). While a Delta
X marker is in the shown range, the top of the y-axis range is raised,
if needed, so that its bracket and value fit above its higher point;
every curve stays fully visible (LLFR-00076).
"""

import functools

import numpy as np
from matplotlib.backend_bases import MouseButton
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.colors import to_hex, to_rgb
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Annotation
from PyQt6 import sip
from PyQt6.QtCore import QEvent, QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QMenu, QVBoxLayout, QWidget

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR,
    is_delta_tool)
from model.curve_colors import MARKER_COLOR_STR
from model.workspace import DELTA_X_KIND_STR
from view import delta_geometry, theme, value_text
from view.delta_geometry import DeltaBracketPatch

# LLFR-00068: every plot uses the look of view.theme (spines, ticks,
# grid, fonts); curve and marker colors are always given explicitly.
theme.apply_matplotlib_style()

# LLFR-00021: same literal string the signal list uses for its drags.
SIGNAL_MIME_TYPE_STR = "application/x-plot-tool-signal"
# LLFR-00041, LLFR-00052: preset width -> matplotlib line width; a
# higher preset is a wider curve (HLFR-00023).
WIDTH_PIXELS_DICT = {1: 1.0, 2: 2.0, 3: 3.0, 4: 4.5, 5: 6.0}
# LLFR-00038, LLFR-00042: how close (screen pixels) the mouse must be to
# a curve, or to a pinned tip's point, to be "on" it.
PICK_TOLERANCE_PIXELS_I = 6

TIME_AXIS_LABEL_STR = "Time (s)"
# LLFR-00074, LLFR-00113: range width kept per forward wheel notch
# (narrow to 95%; a backward notch widens to 1/0.95).
ZOOM_IN_FACTOR_F = 0.95
# LLFR-00113: one wheel notch is 15 degrees, which Qt reports as 120
# eighths of a degree in QWheelEvent.angleDelta().
WHEEL_NOTCH_EIGHTHS_I = 120
# LLFR-00078: a click with the Zoom tool narrows the range to 95%.
CLICK_ZOOM_FACTOR_F = 0.95
# LLFR-00118: relative tolerance used to tell that a plot shows the
# whole time range of the file.
FULL_RANGE_TOLERANCE_F = 1e-9
SINGLE_SAMPLE_HALF_RANGE_S = 0.5
VALUE_MARGIN_RATIO_F = 0.05
CONSTANT_VALUE_HALF_RANGE_F = 0.5
LEGEND_FONT_SIZE_LIST = [10.0, 9.0, 8.0, 7.0, 6.0]
LEGEND_MAXIMUM_HEIGHT_RATIO_F = 0.4
LEGEND_USABLE_WIDTH_RATIO_F = 0.95
POINTS_PER_INCH_F = 72.0
TIP_OFFSET_POINTS_F = 10.0
DEFAULT_TIP_COLOR_STR = theme.DEFAULT_TIP_COLOR_STR
# LLFR-00082, LLFR-00083, LLFR-00084, LLFR-00092: look of a vertical
# marker. The marker is drawn above the curves and below the tips.
MARKER_LINE_WIDTH_F = 1.5
# LLFR-00143: the marker line is dashed (6 points on, 4 points off).
MARKER_LINE_STYLE_TUPLE = (0, (6, 4))
MARKER_ZORDER_F = 8.0
MARKER_FONT_SIZE_F = 9.0
# LLFR-00084: gap (points) between the line top and its label.
MARKER_LABEL_OFFSET_POINTS_F = 3.0
# LLFR-00092: gap (points) between the label and the time below it.
MARKER_TIME_GAP_POINTS_F = 3.0
MARKER_TEXT_BOX_DICT = theme.MARKER_TEXT_BOX_DICT
# LLFR-00086: no marker is being dragged.
NO_MARKER_ID_I = -1
# LLFR-00203: the preview is the marker color mixed with this much of
# the plot background (a paler version of the same color), drawn with
# the same dashes as a marker and a thinner line.
MARKER_PREVIEW_PALE_RATIO_F = 0.55
MARKER_PREVIEW_LINE_WIDTH_F = 1.2
# LLFR-00203: the value marker_preview_changed carries to hide it.
NO_PREVIEW_TIME_S = float("nan")
# LLFR-00152: no pinned tip is being moved.
NO_TIP_INDEX_I = -1
# LLFR-00151: look of the dashed leader line from a pinned tip's label
# to its point; it ends exactly at the point (no shrinking at that end).
TIP_LEADER_LINE_WIDTH_F = 1.0
TIP_LEADER_LINE_STYLE_STR = "--"
# LLFR-00168, LLFR-00170, LLFR-00172: look of a delta marker, in the
# reserved marker color. The bracket is dashed; the thin leader lines
# from the points to the bracket's ends are dotted.
DELTA_LINE_WIDTH_F = 1.3
DELTA_LINE_STYLE_TUPLE = (0, (3.0, 1.6))
DELTA_LEADER_LINE_WIDTH_F = 0.9
DELTA_LEADER_LINE_STYLE_TUPLE = (0, (1.0, 2.0))
# LLFR-00168, LLFR-00170: gap (points) from the higher (Delta X) or the
# later (Delta Y) point to the bracket's ends, and the bracket's depth
# from its ends to its middle tip.
DELTA_GAP_POINTS_F = delta_geometry.DELTA_GAP_POINTS_F
DELTA_DEPTH_POINTS_F = delta_geometry.DELTA_DEPTH_POINTS_F
# LLFR-00169, LLFR-00171: gap (points) between the tip and the box of
# the value.
DELTA_LABEL_GAP_POINTS_F = 2.0
DELTA_FONT_SIZE_F = 9.0
# LLFR-00169, LLFR-00171: the value sits in the box of a pinned tip,
# with a border in the marker color, so curves never show through it.
DELTA_LABEL_BOX_DICT = dict(theme.PINNED_TIP_BOX_DICT,
                            edgecolor=MARKER_COLOR_STR)
# The box padding of theme.PINNED_TIP_BOX_DICT ("pad=0.45", in font
# sizes), in points: the text is set this much further from the tip.
DELTA_LABEL_BOX_PAD_POINTS_F = 0.45 * DELTA_FONT_SIZE_F
# Offset (points) from a point to the value text, beyond the bracket.
DELTA_LABEL_OFFSET_POINTS_F = (DELTA_GAP_POINTS_F + DELTA_DEPTH_POINTS_F
                               + DELTA_LABEL_GAP_POINTS_F
                               + DELTA_LABEL_BOX_PAD_POINTS_F)
# LLFR-00163, LLFR-00168, LLFR-00170: the dots on the points.
DELTA_DOT_SIZE_F = 6.0
DELTA_FIRST_DOT_SIZE_F = 7.5
DELTA_DOT_EDGE_COLOR_STR = theme.PLOT_BACKGROUND_COLOR_STR
DELTA_DOT_EDGE_WIDTH_F = 1.0
# Above the vertical markers, below the tips (LLFR-00153: a pinned tip
# stays on top of everything).
DELTA_ZORDER_F = 8.5
# LLFR-00168: room (points) kept above a Delta X marker's higher point
# for its bracket and its value, at most this part of the plot height.
DELTA_HEADROOM_POINTS_F = (DELTA_GAP_POINTS_F + DELTA_DEPTH_POINTS_F
                           + DELTA_LABEL_GAP_POINTS_F
                           + 1.6 * DELTA_FONT_SIZE_F
                           + 2.0 * DELTA_LABEL_BOX_PAD_POINTS_F)
DELTA_HEADROOM_MAXIMUM_RATIO_F = 0.45
# LLFR-00175: no delta marker is under the mouse.
NO_DELTA_MARKER_ID_I = -1


def mouse_button_held_b(event, qt_button) -> bool:
    """Tell whether a mouse button is still held during a mouse move.

    Inputs:
        event: the matplotlib MouseEvent; its ``guiEvent`` is the Qt
            mouse event when the event came from Qt.
        qt_button: the Qt.MouseButton to check.
    Outputs: True when the button is held, or when the event does not
        say which buttons are held (an event made by matplotlib itself).
    """
    # LLFR-00086, LLFR-00117, LLFR-00152: a lost release ends a drag at
    # the next move that shows the button is up.
    gui_event = getattr(event, "guiEvent", None)
    if gui_event is None or not hasattr(gui_event, "buttons"):
        return True
    return bool(gui_event.buttons() & qt_button)


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
    # LLFR-00169, LLFR-00171: the same formats as the delta markers.
    return value_text.format_tip_text(signal_name_str, time_s, value_f)


def format_time_text(time_s: float) -> str:
    """Return a time as shown in tips and below marker labels.

    Inputs:
        time_s: the time, in seconds.
    Outputs: the text ``t = <time> s`` with 6 significant digits.
    """
    # LLFR-00043, LLFR-00092: times are shown in seconds.
    return value_text.format_time_text(time_s)


def is_shift_horizontal_wheel(wheel_event) -> bool:
    """Tell whether a Qt wheel event is a Shift+wheel turned sideways.

    Inputs:
        wheel_event: a QWheelEvent.
    Outputs: True when Shift is held, the vertical rotation is 0 and the
        horizontal one is not, as macOS reports Shift+wheel.
    """
    # LLFR-00154, LLFR-00074: holding Shift for the marker tool must not
    # stop the wheel zoom; macOS turns Shift+wheel into a sideways wheel.
    shift_held_b = bool(wheel_event.modifiers()
                        & Qt.KeyboardModifier.ShiftModifier)
    angle_delta = wheel_event.angleDelta()
    return (shift_held_b and angle_delta.y() == 0
            and angle_delta.x() != 0)


def wheel_step_f(event) -> float:
    """Return how many wheel notches a matplotlib scroll event stands for.

    Inputs:
        event: the matplotlib MouseEvent of a scroll; its ``guiEvent``
            is the QWheelEvent when the event came from Qt.
    Outputs: the number of notches, positive forward, possibly
        fractional (touchpads and high-resolution wheels).
    """
    # LLFR-00113: Qt gives the rotation in eighths of a degree for mice
    # and touchpads alike, and one notch is 120 of them. matplotlib's
    # own ``step`` uses raw pixels instead on some platforms (touchpads
    # on macOS), so the Qt value is preferred whenever it is there.
    gui_event = getattr(event, "guiEvent", None)
    angle_delta = None
    if gui_event is not None and hasattr(gui_event, "angleDelta"):
        angle_delta = gui_event.angleDelta()
    if angle_delta is not None:
        angle_eighths_i = int(angle_delta.y())
        # LLFR-00113: some touchpads report only pixels; 120 pixels are
        # then taken as one notch, so that they still zoom in proportion.
        if angle_eighths_i == 0 and hasattr(gui_event, "pixelDelta"):
            return (float(gui_event.pixelDelta().y())
                    / WHEEL_NOTCH_EIGHTHS_I)
        return float(angle_eighths_i) / WHEEL_NOTCH_EIGHTHS_I
    return float(event.step)


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


def inside_shift_px(box_low_px: float, box_high_px: float,
                    area_low_px: float, area_high_px: float,
                    keep_high_b: bool) -> float:
    """Return the shortest shift that puts a segment inside another one.

    Inputs:
        box_low_px: low end of the segment to move, in display pixels.
        box_high_px: high end of the segment to move.
        area_low_px: low end of the segment it must stay in.
        area_high_px: high end of that segment.
        keep_high_b: when the segment is longer than the area, True
            aligns the high ends, False aligns the low ends.
    Outputs: the shift in display pixels (0 when already inside).
    """
    # LLFR-00179: the label moves only as far as needed; a label larger
    # than the plot is aligned to one edge (top or left) instead.
    if box_high_px - box_low_px > area_high_px - area_low_px:
        if keep_high_b:
            return area_high_px - box_high_px
        return area_low_px - box_low_px
    if box_low_px < area_low_px:
        return area_low_px - box_low_px
    if box_high_px > area_high_px:
        return area_high_px - box_high_px
    return 0.0


def pale_color_str(color_str: str, background_str: str,
                   pale_ratio_f: float) -> str:
    """Return a paler version of a color, mixed with a background.

    Inputs:
        color_str: the color to make paler, any matplotlib color.
        background_str: the background color it is mixed with.
        pale_ratio_f: share of the background in the mix, 0 to 1.
    Outputs: the mixed color, written as "#rrggbb".
    """
    # LLFR-00203: the preview uses a paler version of the marker color.
    color_tuple = to_rgb(color_str)
    background_tuple = to_rgb(background_str)
    return to_hex(tuple(
        (1.0 - pale_ratio_f) * color_f + pale_ratio_f * background_f
        for color_f, background_f in zip(color_tuple, background_tuple)))


# LLFR-00203: the color of the marker preview.
MARKER_PREVIEW_COLOR_STR = pale_color_str(
    MARKER_COLOR_STR, theme.PLOT_BACKGROUND_COLOR_STR,
    MARKER_PREVIEW_PALE_RATIO_F)


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
        pinned_tip_move_requested(int, float, float): a pinned tip's
            label was dragged and released (tip index, then the offset
            x and y, in points, from the tip's point to the label's
            center, y upwards).
        time_range_changed(float, float): the user changed the time
            range (start in s, end in s), by a zoom or a pan.
        marker_place_requested(float): a left click with the Vertical
            marker tool, not on a marker (time in s).
        marker_move_requested(int, float): a marker was dragged and
            released (marker id, time in s).
        marker_rename_requested(int): "Rename" chosen on a marker.
        marker_delete_requested(int): "Delete" chosen on a marker.
        delta_point_picked(str, float, float): a left click on a curve
            with the Delta X or Delta Y tool (signal name, time in s
            and value of the nearest sample).
        delta_marker_delete_requested(int): "Delete" chosen on a delta
            marker (its id).
        marker_drag_moved(int, float): a dragged marker is now shown at
            this time (marker id, time in s), so that the other plots of
            the tab show it there too (LLFR-00205).
        marker_preview_changed(float): the marker preview of the hovered
            plot moved to this time in s, or was hidden (NaN), so that
            the other plots of the tab follow (LLFR-00203).
    Attributes:
        plot_id_i: the identifier given at creation.
        figure: the matplotlib Figure.
        canvas: the FigureCanvasQTAgg that shows the figure.
        axes: the matplotlib Axes where the curves are drawn.
        redraw_pending_b: True when a time range was set while the
            widget was hidden and the canvas still shows the old one.
        time_span_drag_b: True while a time span is being selected with
            the mouse (LLFR-00208); counted by is_mouse_drag_in_progress.
    """

    curve_delete_requested = pyqtSignal(str)
    curve_width_requested = pyqtSignal(str, int)
    plot_delete_requested = pyqtSignal()
    signal_dropped = pyqtSignal(str)
    tip_pin_requested = pyqtSignal(str, float, float)
    pinned_tip_delete_requested = pyqtSignal(int)
    pinned_tip_move_requested = pyqtSignal(int, float, float)
    time_range_changed = pyqtSignal(float, float)
    marker_place_requested = pyqtSignal(float)
    marker_move_requested = pyqtSignal(int, float)
    marker_rename_requested = pyqtSignal(int)
    marker_delete_requested = pyqtSignal(int)
    delta_point_picked = pyqtSignal(str, float, float)
    delta_marker_delete_requested = pyqtSignal(int)
    marker_drag_moved = pyqtSignal(int, float)
    marker_preview_changed = pyqtSignal(float)

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
        # LLFR-00081, LLFR-00084, LLFR-00092: markers to draw, as tuples
        # (marker_id_i, name_str, time_s), and their artists by id as
        # tuples (line, label annotation, time annotation).
        self.marker_data_list = []
        self.marker_artist_dict = {}
        # LLFR-00168, LLFR-00170: delta markers to draw, as tuples
        # (delta_marker_id_i, kind_str, first_point_tuple,
        # second_point_tuple, delta_f), and their artists by id as tuples
        # (bracket, leader lines, dots, value label).
        self.delta_marker_data_list = []
        self.delta_artist_dict = {}
        # LLFR-00163: the picked first point (signal_name_str, time_s,
        # value_f) and its dot, or () and None.
        self.delta_first_point_tuple = ()
        self.delta_first_point_artist = None
        # LLFR-00086, LLFR-00093: the marker being dragged, if any.
        self.drag_marker_id_i = NO_MARKER_ID_I
        self.drag_time_s = 0.0
        self.drag_moved_b = False
        # LLFR-00086: x pixel of the press, and the time from the mouse
        # to the line, so the grabbed line does not jump to the mouse.
        self.drag_press_x_i = 0
        self.drag_offset_s = 0.0
        # LLFR-00152: the pinned tip being moved, if any; where it was
        # pressed; the display pixels from the pointer to the label's
        # center, so the grabbed label does not jump; and the label
        # offset (points) shown while it is dragged.
        self.drag_tip_index_i = NO_TIP_INDEX_I
        self.tip_press_point = QPoint()
        self.tip_grab_offset_tuple = (0.0, 0.0)
        self.tip_drag_offset_tuple = ()
        self.tip_drag_moved_b = False
        # LLFR-00203: time of the marker preview, None while hidden; the
        # canvas image it is blitted on; its artists (made by
        # rebuild_axes).
        self.preview_time_s = None
        self.preview_background = None
        self.preview_line = None
        self.preview_time_text = None
        # LLFR-00042, LLFR-00045, LLFR-00078: the active plot tool.
        self.plot_tool_str = NO_TOOL_STR
        self.hover_point_tuple = ()
        self.pending_menu_point = QPoint()
        # LLFR-00138: True once the widget is being removed (retire), so
        # that a deferred context menu is not shown any more.
        self.retired_b = False
        # LLFR-00117: whether the wheel button is held for a pan, and the
        # time that was under the pointer when it was pressed.
        self.panning_b = False
        self.pan_anchor_s = 0.0
        # LLFR-00207, LLFR-00208: True while a time span is selected with
        # the mouse; the time span selection sets it on this instance, so
        # that the Z key does nothing during its drag.
        self.time_span_drag_b = False
        # LLFR-00122, LLFR-00123, LLFR-00125, LLFR-00147: whether the
        # grid is drawn; hidden until the Grid button is clicked.
        self.grid_shown_b = False

        # LLFR-00035: constrained layout keeps room for the legend above
        # the axes when the widget is resized.
        self.figure = Figure(layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setParent(self)
        self.canvas.setAcceptDrops(False)
        # LLFR-00137: a click on the plot takes the keyboard focus away
        # from the text fields (search box), so that the next Ctrl+Z
        # (Cmd+Z) runs the workspace undo and not the text undo.
        self.canvas.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
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
        # LLFR-00086: the release ends a marker drag.
        self.canvas.mpl_connect("button_release_event",
                                self.on_mouse_release)
        self.canvas.mpl_connect("scroll_event", self.on_mouse_scroll)
        # LLFR-00154, LLFR-00074: matplotlib drops a sideways wheel, so
        # the Shift+wheel of macOS is caught before it (eventFilter).
        self.canvas.installEventFilter(self)
        self.canvas.mpl_connect("figure_leave_event", self.on_mouse_leave)
        # LLFR-00035: the legend is fitted again when the canvas resizes.
        self.canvas.mpl_connect("resize_event", self.on_canvas_resize)

        self.time_range_s_tuple = (0.0, 1.0)
        # LLFR-00070: a hidden plot (another tab) draws its new time
        # range only when it is shown; any real draw clears the flag.
        self.redraw_pending_b = False
        self.canvas.mpl_connect("draw_event", self.on_canvas_drawn)
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
                value_f) or (signal_name_str, time_s, value_f,
                label_offset_tuple); label_offset_tuple is the offset
                (x, y) in points from the point to the label's center,
                or () to place the label automatically.
        Outputs: none.
        """
        # LLFR-00045: pinned tips are drawn as persistent annotations.
        # LLFR-00152: a moved tip keeps the offset of its label.
        tip_tuple_list = []
        for tip_tuple in pinned_tip_list:
            offset_tuple = tuple(tip_tuple[3]) if len(tip_tuple) > 3 else ()
            if len(offset_tuple) == 2:
                offset_tuple = (float(offset_tuple[0]),
                                float(offset_tuple[1]))
            else:
                offset_tuple = ()
            tip_tuple_list.append((str(tip_tuple[0]), float(tip_tuple[1]),
                                   float(tip_tuple[2]), offset_tuple))
        self.pinned_tip_list = tip_tuple_list
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
        # LLFR-00086: a marker is only dragged with the Vertical marker
        # tool; leaving it drops the drag (the marker stays where it was).
        if self.plot_tool_str != MARKER_TOOL_STR:
            self.cancel_marker_drag()
            # LLFR-00203: the preview goes when the tool is deactivated.
            self.hide_marker_preview()
        else:
            # LLFR-00203, LLFR-00154: a tool activated with the pointer
            # already on the plot (Shift pressed) shows the preview at
            # once, without waiting for a mouse move.
            self.update_marker_preview_from_cursor()
        # LLFR-00167: leaving the delta tools removes the dot of a first
        # point (the controller also says so).
        if not is_delta_tool(self.plot_tool_str):
            self.set_delta_first_point(())

    def set_markers(self, marker_data_list: list) -> None:
        """Replace the vertical markers drawn in the plot.

        Inputs:
            marker_data_list: list of tuples (marker_id_i, name_str,
                time_s), in placing order.
        Outputs: none. Only the markers are redrawn.
        """
        # LLFR-00081, LLFR-00091, LLFR-00112: draw exactly these markers.
        self.marker_data_list = [
            (int(marker_id_i), str(name_str), float(time_s))
            for (marker_id_i, name_str, time_s) in marker_data_list]
        # LLFR-00086: a drag of a marker that is gone ends here.
        if self.drag_marker_id_i not in {
                marker_tuple[0] for marker_tuple in self.marker_data_list}:
            self.cancel_marker_drag()
        # LLFR-00203: a marker may now be under the pointer (one was just
        # placed there); the next mouse move shows the preview again.
        self.hide_marker_preview()
        self.draw_markers()
        # LLFR-00205: the markers change on every plot of every tab; a
        # hidden plot draws them only when it is shown (showEvent).
        self.draw_when_visible()

    def draw_when_visible(self) -> None:
        """Redraw the canvas now if shown, else when it is shown.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00070, LLFR-00205: hidden tabs do not pay for a draw.
        if self.isVisible():
            self.canvas.draw_idle()
        else:
            self.redraw_pending_b = True

    def set_delta_markers(self, delta_marker_data_list: list) -> None:
        """Replace the delta markers drawn in the plot.

        Inputs:
            delta_marker_data_list: list of tuples (delta_marker_id_i,
                kind_str, first_point_tuple, second_point_tuple, delta_f)
                in placing order; each point is (signal_name_str, time_s,
                value_f) and delta_f is the value shown (second minus
                first).
        Outputs: none.
        """
        # LLFR-00164, LLFR-00174, LLFR-00176: draw exactly these.
        self.delta_marker_data_list = [
            (int(marker_tuple[0]), str(marker_tuple[1]),
             (str(marker_tuple[2][0]), float(marker_tuple[2][1]),
              float(marker_tuple[2][2])),
             (str(marker_tuple[3][0]), float(marker_tuple[3][1]),
              float(marker_tuple[3][2])),
             float(marker_tuple[4]))
            for marker_tuple in delta_marker_data_list]
        self.draw_delta_markers()
        # LLFR-00168: the y range keeps room above the Delta X markers.
        self.apply_time_range()
        self.canvas.draw_idle()

    def set_delta_first_point(self, point_tuple: tuple) -> None:
        """Show or remove the dot of a delta marker's first point.

        Inputs:
            point_tuple: (signal_name_str, time_s, value_f) of the first
                point, or () to remove the dot.
        Outputs: none.
        """
        # LLFR-00163, LLFR-00164, LLFR-00167: the controller says where
        # the first point is, and when it is gone.
        point_tuple = tuple(point_tuple)
        if len(point_tuple) == 3:
            point_tuple = (str(point_tuple[0]), float(point_tuple[1]),
                           float(point_tuple[2]))
        else:
            point_tuple = ()
        if point_tuple == self.delta_first_point_tuple:
            return
        self.delta_first_point_tuple = point_tuple
        self.draw_delta_first_point()
        self.canvas.draw_idle()

    def set_time_range(self, start_s: float, end_s: float) -> None:
        """Show the given time range without emitting time_range_changed.

        Inputs:
            start_s: start of the range, in seconds.
            end_s: end of the range, in seconds.
        Outputs: none.
        """
        # LLFR-00070: the controller applies the range shared by every
        # plot of every tab. The range, x limits and y fit (LLFR-00076)
        # are always updated, so time_range_tuple and the PDF export
        # (LLFR-00129) see them; the costly canvas draw of a hidden plot
        # waits until it is shown (showEvent).
        self.time_range_s_tuple = padded_range_tuple(
            start_s, end_s, SINGLE_SAMPLE_HALF_RANGE_S)
        self.apply_time_range()
        if self.isVisible():
            self.canvas.draw_idle()
        else:
            self.redraw_pending_b = True

    def showEvent(self, event) -> None:
        """Draw a time range that was set while the plot was hidden.

        Inputs:
            event: the QShowEvent.
        Outputs: none.
        """
        # LLFR-00070: a tab shown again displays the shared time range.
        super().showEvent(event)
        if self.redraw_pending_b:
            self.redraw_pending_b = False
            self.canvas.draw_idle()

    def on_canvas_drawn(self, event) -> None:
        """Forget a pending redraw once the canvas has been drawn.

        Inputs:
            event: the matplotlib DrawEvent.
        Outputs: none.
        """
        # LLFR-00070, LLFR-00129: a draw by the PDF export or a resize
        # already shows the current range.
        self.redraw_pending_b = False
        # LLFR-00203: the canvas image changed, so the preview is blitted
        # again on the new image once this draw is shown. Not inside an
        # export (savefig), whose image must not contain it.
        self.preview_background = None
        if self.preview_time_s is not None and not self.canvas.is_saving():
            QTimer.singleShot(0, self.blit_marker_preview)

    def time_range_tuple(self) -> tuple:
        """Return the time range currently shown.

        Inputs: none.
        Outputs: a tuple (start_s, end_s) in seconds.
        """
        # LLFR-00070: the shown range, read from the axes.
        start_s, end_s = self.axes.get_xlim()
        return (float(start_s), float(end_s))

    def set_grid_shown(self, shown_b: bool) -> None:
        """Show or hide the grid of the plot.

        Inputs:
            shown_b: True to show the grid, False to hide it.
        Outputs: none. The choice is kept when the curves are redrawn.
        """
        # LLFR-00122, LLFR-00123: show or hide the grid lines.
        self.grid_shown_b = bool(shown_b)
        self.axes.grid(self.grid_shown_b)
        self.canvas.draw_idle()

    def grid_shown(self) -> bool:
        """Tell whether the axes draw their grid lines.

        Inputs: none.
        Outputs: True when the x and y grid lines are visible.
        """
        # LLFR-00122, LLFR-00123: read from the axes, not from the flag,
        # so that the drawn state is what is reported.
        line_list = (list(self.axes.get_xgridlines())
                     + list(self.axes.get_ygridlines()))
        return bool(line_list) and all(
            line.get_visible() for line in line_list)

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
        # LLFR-00122, LLFR-00125: axes.clear() removes the grid, so it is
        # drawn again as chosen.
        self.axes.grid(self.grid_shown_b)
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
            color=theme.TIP_TEXT_COLOR_STR,
            fontsize=theme.PLOT_TIP_FONT_SIZE_F,
            bbox=dict(theme.HOVER_TIP_BOX_DICT),
            zorder=10)
        self.hover_annotation.set_visible(False)
        self.hover_annotation.set_in_layout(False)
        self.pinned_annotation_list = []
        self.pinned_marker_list = []
        self.draw_pinned_tips()
        # LLFR-00081: the markers survive a redraw of the curves; the
        # old artists went away with axes.clear().
        self.marker_artist_dict = {}
        self.draw_markers()
        # LLFR-00168, LLFR-00170, LLFR-00163: the delta markers and the
        # dot of a first point survive the redraw too.
        self.delta_artist_dict = {}
        self.delta_first_point_artist = None
        self.draw_delta_markers()
        self.draw_delta_first_point()
        # LLFR-00203: the preview artists went away with axes.clear().
        self.create_preview_artists()
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
        # LLFR-00152: the tips are replaced, so a tip drag in progress
        # refers to a tip that is gone; it ends without a request.
        self.reset_tip_drag()
        for signal_name_str, time_s, value_f, _ in self.pinned_tip_list:
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
                color=theme.TIP_TEXT_COLOR_STR,
                fontsize=theme.PLOT_TIP_FONT_SIZE_F,
                bbox=dict(theme.PINNED_TIP_BOX_DICT, edgecolor=color_str),
                # LLFR-00151: a dashed leader line from the label's box
                # to the point, in the curve's color.
                arrowprops={"arrowstyle": "-", "color": color_str,
                            "linestyle": TIP_LEADER_LINE_STYLE_STR,
                            "linewidth": TIP_LEADER_LINE_WIDTH_F,
                            "shrinkA": 0.0, "shrinkB": 0.0},
                zorder=9)
            annotation.set_in_layout(False)
            # LLFR-00179: every draw of the label first keeps it inside
            # the axes, with the axes size of that very draw.
            annotation.draw = functools.partial(
                self.draw_pinned_tip, len(self.pinned_annotation_list),
                annotation, annotation.draw)
            self.pinned_marker_list.append(marker)
            self.pinned_annotation_list.append(annotation)
        self.place_tips()

    def draw_pinned_tip(self, tip_index_i: int, annotation, original_draw,
                        renderer) -> None:
        """Draw a pinned tip after keeping its label inside the axes.

        Inputs:
            tip_index_i: index of the tip in the list of set_pinned_tips.
            annotation: the matplotlib Annotation of the tip.
            original_draw: the Annotation's own draw method.
            renderer: the matplotlib renderer of this draw.
        Outputs: none.
        """
        # LLFR-00179: matplotlib calls this for each draw (screen, image
        # and PDF export), after the layout gave the axes their size.
        if (tip_index_i < len(self.pinned_annotation_list)
                and self.pinned_annotation_list[tip_index_i] is annotation):
            self.place_pinned_tip(tip_index_i, annotation, renderer)
        original_draw(renderer)

    def draw_markers(self) -> None:
        """Draw the stored vertical markers, replacing the previous ones.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00091: remove the old lines and labels first.
        for artist_tuple in self.marker_artist_dict.values():
            for artist in artist_tuple:
                artist.remove()
        self.marker_artist_dict = {}
        for marker_id_i, name_str, time_s in self.marker_data_list:
            # LLFR-00082: axvline spans the axes in axes coordinates
            # (0 to 1) in y, so it covers the whole y range at any zoom.
            # LLFR-00083: in the reserved marker color.
            # LLFR-00143: the line is dashed.
            line = self.axes.axvline(
                time_s, color=MARKER_COLOR_STR,
                linewidth=MARKER_LINE_WIDTH_F,
                linestyle=MARKER_LINE_STYLE_TUPLE, zorder=MARKER_ZORDER_F)
            line.set_in_layout(False)
            # LLFR-00084: the name at the top of the line, inside the
            # axes, shown literally (never as mathtext).
            label = self.axes.annotate(
                name_str, xy=(time_s, 1.0),
                xycoords=self.axes.get_xaxis_transform(),
                xytext=(MARKER_LABEL_OFFSET_POINTS_F,
                        -MARKER_LABEL_OFFSET_POINTS_F),
                textcoords="offset points", parse_math=False,
                color=MARKER_COLOR_STR, fontsize=MARKER_FONT_SIZE_F,
                horizontalalignment="left", verticalalignment="top",
                bbox=dict(MARKER_TEXT_BOX_DICT), zorder=MARKER_ZORDER_F)
            label.set_in_layout(False)
            # LLFR-00092: the time directly below the label. Its anchor
            # is the label's own box, so it follows the label.
            time_text = self.axes.annotate(
                format_time_text(time_s), xy=(0.0, 0.0), xycoords=label,
                xytext=(0.0, -MARKER_TIME_GAP_POINTS_F),
                textcoords="offset points", parse_math=False,
                color=MARKER_COLOR_STR, fontsize=MARKER_FONT_SIZE_F,
                horizontalalignment="left", verticalalignment="top",
                bbox=dict(MARKER_TEXT_BOX_DICT), zorder=MARKER_ZORDER_F)
            time_text.set_in_layout(False)
            self.marker_artist_dict[marker_id_i] = (line, label, time_text)
        self.place_markers()

    def draw_delta_markers(self) -> None:
        """Draw the stored delta markers, replacing the previous ones.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00176: remove the old artists first.
        for artist_tuple in self.delta_artist_dict.values():
            for artist in artist_tuple:
                artist.remove()
        self.delta_artist_dict = {}
        for (delta_marker_id_i, kind_str, first_point_tuple,
             second_point_tuple, delta_f) in self.delta_marker_data_list:
            self.delta_artist_dict[delta_marker_id_i] = (
                self.new_delta_artist_tuple(kind_str, first_point_tuple,
                                            second_point_tuple, delta_f))

    def new_delta_artist_tuple(self, kind_str: str, first_point_tuple: tuple,
                               second_point_tuple: tuple,
                               delta_f: float) -> tuple:
        """Create the artists of one delta marker in the axes.

        Inputs:
            kind_str: DELTA_X_KIND_STR or DELTA_Y_KIND_STR.
            first_point_tuple: (signal_name_str, time_s, value_f).
            second_point_tuple: the same for the second point.
            delta_f: the value shown, second minus first.
        Outputs: a tuple (bracket, leader lines, dots, value label).
        """
        # LLFR-00172: everything in the reserved marker color.
        # LLFR-00168, LLFR-00170: a dashed curly bracket; dotted leader
        # lines join it to the points.
        bracket = DeltaBracketPatch(
            kind_str, first_point_tuple, second_point_tuple, False,
            edgecolor=MARKER_COLOR_STR, linewidth=DELTA_LINE_WIDTH_F,
            linestyle=DELTA_LINE_STYLE_TUPLE, capstyle="round",
            joinstyle="round", zorder=DELTA_ZORDER_F)
        leader = DeltaBracketPatch(
            kind_str, first_point_tuple, second_point_tuple, True,
            edgecolor=MARKER_COLOR_STR, linewidth=DELTA_LEADER_LINE_WIDTH_F,
            linestyle=DELTA_LEADER_LINE_STYLE_TUPLE, capstyle="round",
            zorder=DELTA_ZORDER_F)
        for patch in (leader, bracket):
            # LLFR-00174: clipped to the axes (add_artist clips to the
            # axes patch), so only the visible part is drawn.
            self.axes.add_artist(patch)
            patch.set_in_layout(False)
        # LLFR-00168, LLFR-00170: a dot on each point.
        (dots,) = self.axes.plot(
            [first_point_tuple[1], second_point_tuple[1]],
            [first_point_tuple[2], second_point_tuple[2]],
            linestyle="none", marker="o", markersize=DELTA_DOT_SIZE_F,
            markerfacecolor=MARKER_COLOR_STR,
            markeredgecolor=DELTA_DOT_EDGE_COLOR_STR,
            markeredgewidth=DELTA_DOT_EDGE_WIDTH_F,
            zorder=DELTA_ZORDER_F + 0.1)
        dots.set_in_layout(False)
        if kind_str == DELTA_X_KIND_STR:
            # LLFR-00169: "Δt = <value> s".
            text_str = value_text.format_delta_x_text(delta_f)
        else:
            # LLFR-00171: "Δy = <value>".
            text_str = value_text.format_delta_y_text(delta_f)
        label = self.axes.annotate(
            text_str, xy=(first_point_tuple[1], first_point_tuple[2]),
            xytext=(0.0, 0.0), textcoords="offset points",
            parse_math=False, color=MARKER_COLOR_STR,
            fontsize=DELTA_FONT_SIZE_F, bbox=dict(DELTA_LABEL_BOX_DICT),
            zorder=DELTA_ZORDER_F + 0.2)
        label.set_in_layout(False)
        if kind_str != DELTA_X_KIND_STR:
            # LLFR-00170: the bracket, the leader lines and the value
            # always take the same side, chosen again at every draw.
            side_function = functools.partial(
                self.delta_y_side_str, first_point_tuple,
                second_point_tuple, label)
            bracket.side_function = side_function
            leader.side_function = side_function
        self.place_delta_label(label, kind_str, first_point_tuple,
                               second_point_tuple)
        # LLFR-00173: every draw places the value next to the tip again
        # and keeps it inside the plot, as for pinned tips.
        label.draw = functools.partial(
            self.draw_delta_label, label, kind_str, first_point_tuple,
            second_point_tuple, label.draw)
        return (bracket, leader, dots, label)

    def delta_y_side_str(self, first_point_tuple: tuple,
                         second_point_tuple: tuple, label,
                         renderer=None) -> str:
        """Return the side a Delta Y bracket and its value are drawn on.

        Inputs:
            first_point_tuple: (signal_name_str, time_s, value_f).
            second_point_tuple: the same for the second point.
            label: the matplotlib Annotation of the value.
            renderer: the renderer of the draw, or None for the canvas's.
        Outputs: delta_geometry.RIGHT_SIDE_STR or LEFT_SIDE_STR.
        """
        # LLFR-00170: right of the later point when the gap, the bracket
        # and the value fit inside the plot's drawing area, else mirrored
        # left of the earlier point; with neither, the side with more
        # room. Measured with the current axes and resolution, so the
        # screen and the PDF export (LLFR-00129) agree.
        if renderer is None:
            renderer = self.canvas.get_renderer()
        pixels_per_point_f = float(self.figure.dpi) / POINTS_PER_INCH_F
        label_width_px = float(self.tip_box_extent(label, renderer).width)
        needed_px = ((DELTA_GAP_POINTS_F + DELTA_DEPTH_POINTS_F
                      + DELTA_LABEL_GAP_POINTS_F) * pixels_per_point_f
                     + label_width_px)
        first_x_px = float(self.axes.transData.transform(
            (first_point_tuple[1], first_point_tuple[2]))[0])
        second_x_px = float(self.axes.transData.transform(
            (second_point_tuple[1], second_point_tuple[2]))[0])
        axes_box = self.axes.bbox
        return delta_geometry.choose_delta_y_side(
            first_x_px, second_x_px, needed_px, float(axes_box.x0),
            float(axes_box.x1))

    def place_delta_label(self, label, kind_str: str,
                          first_point_tuple: tuple, second_point_tuple: tuple,
                          renderer=None) -> None:
        """Put a delta marker's value next to the middle tip of its bracket.

        Inputs:
            label: the matplotlib Annotation of the value.
            kind_str: DELTA_X_KIND_STR or DELTA_Y_KIND_STR.
            first_point_tuple: (signal_name_str, time_s, value_f).
            second_point_tuple: the same for the second point.
            renderer: the renderer of the draw, or None for the canvas's.
        Outputs: none.
        """
        if kind_str == DELTA_X_KIND_STR:
            # LLFR-00169: above the middle tip, which is above the
            # higher point.
            label.xy = ((first_point_tuple[1] + second_point_tuple[1]) / 2.0,
                        max(first_point_tuple[2], second_point_tuple[2]))
            label.set_position((0.0, DELTA_LABEL_OFFSET_POINTS_F))
            label.set_horizontalalignment("center")
            label.set_verticalalignment("bottom")
            return
        # LLFR-00171: beside the middle tip, on the side of LLFR-00170.
        middle_value_f = (first_point_tuple[2] + second_point_tuple[2]) / 2.0
        label.set_verticalalignment("center")
        if self.delta_y_side_str(first_point_tuple, second_point_tuple,
                                 label, renderer) == (
                delta_geometry.RIGHT_SIDE_STR):
            label.xy = (max(first_point_tuple[1], second_point_tuple[1]),
                        middle_value_f)
            label.set_position((DELTA_LABEL_OFFSET_POINTS_F, 0.0))
            label.set_horizontalalignment("left")
        else:
            label.xy = (min(first_point_tuple[1], second_point_tuple[1]),
                        middle_value_f)
            label.set_position((-DELTA_LABEL_OFFSET_POINTS_F, 0.0))
            label.set_horizontalalignment("right")

    def draw_delta_label(self, label, kind_str: str, first_point_tuple: tuple,
                         second_point_tuple: tuple, original_draw,
                         renderer) -> None:
        """Draw a delta marker's value beside its tip, inside the axes.

        Inputs:
            label: the matplotlib Annotation of the value.
            kind_str: DELTA_X_KIND_STR or DELTA_Y_KIND_STR.
            first_point_tuple: (signal_name_str, time_s, value_f).
            second_point_tuple: the same for the second point.
            original_draw: the Annotation's own draw method.
            renderer: the matplotlib renderer of this draw.
        Outputs: none.
        """
        # LLFR-00169, LLFR-00171, LLFR-00173: next to the middle tip, on
        # the side of this draw, moved only as far as needed to stay
        # readable in the plot.
        self.place_delta_label(label, kind_str, first_point_tuple,
                               second_point_tuple, renderer)
        self.keep_tip_inside_axes(label, renderer)
        original_draw(renderer)

    def draw_delta_first_point(self) -> None:
        """Draw the dot of the picked first point, or remove it.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00164, LLFR-00167: an old dot is removed.
        if self.delta_first_point_artist is not None:
            self.delta_first_point_artist.remove()
            self.delta_first_point_artist = None
        if not self.delta_first_point_tuple:
            return
        # LLFR-00163, LLFR-00172: a dot in the marker color.
        _, time_s, value_f = self.delta_first_point_tuple
        (dot,) = self.axes.plot(
            [time_s], [value_f], linestyle="none", marker="o",
            markersize=DELTA_FIRST_DOT_SIZE_F,
            markerfacecolor=MARKER_COLOR_STR,
            markeredgecolor=DELTA_DOT_EDGE_COLOR_STR,
            markeredgewidth=DELTA_DOT_EDGE_WIDTH_F,
            zorder=DELTA_ZORDER_F + 0.1)
        dot.set_in_layout(False)
        self.delta_first_point_artist = dot

    def delta_headroom_range_tuple(self, low_f: float, high_f: float,
                                   start_s: float, end_s: float) -> tuple:
        """Raise the top of a y range to fit the Delta X brackets.

        Inputs:
            low_f: bottom of the y range that fits the curves.
            high_f: top of that range.
            start_s: start of the shown time range, in seconds.
            end_s: end of the shown time range.
        Outputs: a tuple (low_f, high_f); high_f is only ever raised,
            so every curve stays fully visible (LLFR-00076).
        """
        # LLFR-00168: the bracket sits just above the higher point and
        # its value above it; both must fit in the plot.
        axes_height_points_f = (float(self.axes.bbox.height)
                                / self.pixels_per_point_f())
        if axes_height_points_f <= 0.0:
            return (low_f, high_f)
        ratio_f = min(DELTA_HEADROOM_POINTS_F / axes_height_points_f,
                      DELTA_HEADROOM_MAXIMUM_RATIO_F)
        for (_, kind_str, first_point_tuple, second_point_tuple,
             _) in self.delta_marker_data_list:
            if kind_str != DELTA_X_KIND_STR:
                continue
            first_s, second_s = sorted((first_point_tuple[1],
                                        second_point_tuple[1]))
            # LLFR-00174: only the markers with a visible part.
            if second_s < start_s or first_s > end_s:
                continue
            high_f = delta_geometry.headroom_high_f(
                low_f, high_f, max(first_point_tuple[2],
                                   second_point_tuple[2]), ratio_f)
        return (low_f, high_f)

    def place_markers(self) -> None:
        """Show the markers inside the time range, beside their line.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00084, LLFR-00092: the label and time follow their marker
        # when the range changes. A marker outside the shown range is
        # hidden (its line is also clipped by the axes).
        start_s, end_s = sorted(self.axes.get_xlim())
        for line, label, time_text in self.marker_artist_dict.values():
            time_s = float(line.get_xdata()[0])
            visible_b = bool(start_s <= time_s <= end_s)
            for artist in (line, label, time_text):
                artist.set_visible(visible_b)
            # A marker in the right half has its texts on its left, so
            # that they stay inside the plot.
            right_half_b = time_s > (start_s + end_s) / 2.0
            label.set_position((
                -MARKER_LABEL_OFFSET_POINTS_F if right_half_b
                else MARKER_LABEL_OFFSET_POINTS_F,
                -MARKER_LABEL_OFFSET_POINTS_F))
            alignment_str = "right" if right_half_b else "left"
            label.set_horizontalalignment(alignment_str)
            time_text.set_horizontalalignment(alignment_str)
            time_text.xy = (1.0 if right_half_b else 0.0, 0.0)

    def create_preview_artists(self) -> None:
        """Create the hidden line and time text of the marker preview.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00203, LLFR-00129, LLFR-00133: the artists are not added
        # to the axes, so no full draw, export or copy ever draws them,
        # and they are not among the plot's lines and texts; only
        # blit_marker_preview draws them, over the axes.
        # LLFR-00203: a dashed vertical line across the plot, in a paler
        # marker color. LLFR-00082, LLFR-00143: the same shape as a
        # marker's line: x in data, y from bottom (0) to top (1).
        x_axis_transform = self.axes.get_xaxis_transform()
        self.preview_line = Line2D(
            [0.0, 0.0], [0.0, 1.0], transform=x_axis_transform,
            color=MARKER_PREVIEW_COLOR_STR,
            linewidth=MARKER_PREVIEW_LINE_WIDTH_F,
            linestyle=MARKER_LINE_STYLE_TUPLE)
        # LLFR-00092: the time value in seconds, at the top of the line.
        self.preview_time_text = Annotation(
            "", xy=(0.0, 1.0), xycoords=x_axis_transform,
            xytext=(MARKER_LABEL_OFFSET_POINTS_F,
                    -MARKER_LABEL_OFFSET_POINTS_F),
            textcoords="offset points", parse_math=False,
            color=MARKER_PREVIEW_COLOR_STR, fontsize=MARKER_FONT_SIZE_F,
            horizontalalignment="left", verticalalignment="top",
            bbox=dict(MARKER_TEXT_BOX_DICT,
                      edgecolor=MARKER_PREVIEW_COLOR_STR))
        for artist in (self.preview_line, self.preview_time_text):
            artist.set_figure(self.figure)
            artist.axes = self.axes
            # The line is cut at the edges of the drawing area.
            artist.set_clip_box(self.axes.bbox)
        self.preview_background = None

    def place_preview_artists(self) -> None:
        """Put the preview line and time text at the preview's time.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00203: the line at the time under the pointer, its time
        # value beside its top, on the inner side like a marker's label.
        time_s = self.preview_time_s
        start_s, end_s = sorted(self.axes.get_xlim())
        self.preview_line.set_xdata([time_s, time_s])
        self.preview_time_text.xy = (time_s, 1.0)
        self.preview_time_text.set_text(format_time_text(time_s))
        right_half_b = time_s > (start_s + end_s) / 2.0
        self.preview_time_text.set_position((
            -MARKER_LABEL_OFFSET_POINTS_F if right_half_b
            else MARKER_LABEL_OFFSET_POINTS_F,
            -MARKER_LABEL_OFFSET_POINTS_F))
        self.preview_time_text.set_horizontalalignment(
            "right" if right_half_b else "left")

    def blit_marker_preview(self) -> None:
        """Draw the marker preview over the last full draw of the canvas.

        Inputs: none.
        Outputs: none. Only the preview is drawn: the image of the last
            full draw is put back first, then the preview is drawn over
            it while it is shown.
        """
        # LLFR-00203: fast enough to follow the mouse on every plot of
        # the tab. Nothing is drawn for a deleted, removed or hidden plot.
        if sip.isdeleted(self) or self.retired_b or not self.isVisible():
            return
        if self.preview_line is None:
            return
        if getattr(self.canvas, "renderer", None) is None:
            # The canvas was never drawn: draw it, and on_canvas_drawn
            # blits the preview afterwards.
            if self.preview_time_s is not None:
                self.canvas.draw_idle()
            return
        if self.preview_background is None:
            # The image is that of the last full draw (on_canvas_drawn
            # forgets the background at every draw), so it is clean.
            if self.preview_time_s is None:
                return
            self.preview_background = self.canvas.copy_from_bbox(
                self.figure.bbox)
        else:
            self.canvas.restore_region(self.preview_background)
        if self.preview_time_s is not None:
            self.place_preview_artists()
            self.axes.draw_artist(self.preview_line)
            self.axes.draw_artist(self.preview_time_text)
        self.canvas.blit(self.figure.bbox)

    def show_marker_preview(self, time_s: float) -> None:
        """Show the marker preview at a time.

        Inputs:
            time_s: time of the preview line, in seconds.
        Outputs: none. Emits nothing; see update_marker_preview.
        """
        # LLFR-00203: also used by the plot panel for the other plots of
        # the tab. Never while a marker is dragged (LLFR-00086).
        time_s = float(time_s)
        if not np.isfinite(time_s):
            self.hide_marker_preview()
            return
        if self.drag_marker_id_i != NO_MARKER_ID_I:
            return
        if self.preview_time_s == time_s:
            return
        self.preview_time_s = time_s
        self.blit_marker_preview()

    def hide_marker_preview(self) -> None:
        """Hide the marker preview if it is shown.

        Inputs: none.
        Outputs: none. Emits nothing.
        """
        # LLFR-00203: the canvas shows the last full draw again.
        if self.preview_time_s is None:
            return
        self.preview_time_s = None
        self.blit_marker_preview()

    def marker_preview_time_s(self) -> float:
        """Return the time of the marker preview.

        Inputs: none.
        Outputs: the time in seconds, or NaN while the preview is hidden.
        """
        # LLFR-00203: for the plot panel and the tests.
        if self.preview_time_s is None:
            return NO_PREVIEW_TIME_S
        return float(self.preview_time_s)

    def marker_preview_shown(self) -> bool:
        """Tell whether the marker preview is shown.

        Inputs: none.
        Outputs: True while the preview is shown.
        """
        # LLFR-00203: for the tests.
        return self.preview_time_s is not None

    def marker_preview_text(self) -> str:
        """Return the time text of the marker preview.

        Inputs: none.
        Outputs: the text, or "" while the preview is hidden.
        """
        # LLFR-00203, LLFR-00092: the time value of the preview.
        if self.preview_time_s is None:
            return ""
        return format_time_text(self.preview_time_s)

    def marker_preview_time_at(self, widget_point) -> float:
        """Return where a click at a point would place a marker.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: the time under the point, in seconds, or NaN when a
            click there would not place a marker: no Vertical marker
            tool, a drag in progress, outside the drawing area, or on an
            existing marker or a pinned tip.
        """
        # LLFR-00203: the preview shows the marker a click would place
        # (LLFR-00081); LLFR-00153: a click on a pinned tip moves it.
        if self.plot_tool_str != MARKER_TOOL_STR or self.retired_b:
            return NO_PREVIEW_TIME_S
        if (self.drag_marker_id_i != NO_MARKER_ID_I
                or self.drag_tip_index_i != NO_TIP_INDEX_I):
            return NO_PREVIEW_TIME_S
        display_x_px, display_y_px = self.widget_to_display_tuple(
            widget_point)
        if not self.inside_axes_b(display_x_px, display_y_px):
            return NO_PREVIEW_TIME_S
        if self.marker_at(widget_point) != NO_MARKER_ID_I:
            return NO_PREVIEW_TIME_S
        if self.pinned_tip_at(widget_point) != NO_TIP_INDEX_I:
            return NO_PREVIEW_TIME_S
        return self.time_at(widget_point)

    def update_marker_preview(self, widget_point) -> None:
        """Show or hide the preview for the pointer at a point.

        Inputs:
            widget_point: QPoint in this widget's coordinates, where the
                mouse pointer is.
        Outputs: none. Emits marker_preview_changed when the preview of
            this plot moved or was hidden, as the last step.
        """
        # LLFR-00203: the preview follows the mouse on the hovered plot.
        time_s = self.marker_preview_time_at(widget_point)
        old_time_s = self.marker_preview_time_s()
        if np.isfinite(time_s):
            self.show_marker_preview(time_s)
        else:
            self.hide_marker_preview()
        new_time_s = self.marker_preview_time_s()
        if (new_time_s != old_time_s
                and not (np.isnan(new_time_s) and np.isnan(old_time_s))):
            # LLFR-00203: the plot panel shows it on the other plots of
            # the current tab.
            self.marker_preview_changed.emit(new_time_s)

    def leave_marker_preview(self) -> None:
        """Hide the preview because the pointer left the plot.

        Inputs: none.
        Outputs: none. Emits marker_preview_changed(NaN) when the preview
            was shown.
        """
        # LLFR-00203: no preview once the pointer leaves the plots.
        if self.preview_time_s is None:
            return
        self.hide_marker_preview()
        self.marker_preview_changed.emit(NO_PREVIEW_TIME_S)

    def update_marker_preview_from_cursor(self) -> None:
        """Show the preview when the pointer already is on the plot.

        Inputs: none.
        Outputs: none. Does nothing when the plot is hidden or the
            pointer is not on its canvas.
        """
        # LLFR-00203, LLFR-00154: holding Shift without moving the mouse
        # shows the preview too.
        if self.retired_b or not self.isVisible():
            return
        canvas_point = self.canvas.mapFromGlobal(QCursor.pos())
        if not self.canvas.rect().contains(canvas_point):
            return
        self.update_marker_preview(self.canvas.mapTo(self, canvas_point))

    def follow_marker_drag(self, marker_id_i: int, time_s: float) -> None:
        """Show a marker dragged on another plot at its current time.

        Inputs:
            marker_id_i: id of the dragged marker.
            time_s: the time it is shown at on the dragged plot, in s.
        Outputs: none. The stored markers do not change.
        """
        # LLFR-00205: while a marker is dragged on one plot, it follows
        # the pointer on every plot of the current tab. LLFR-00093: its
        # time value too.
        if marker_id_i not in self.marker_artist_dict:
            return
        self.hide_marker_preview()
        self.move_marker_artists(int(marker_id_i), float(time_s))
        self.draw_when_visible()

    def move_marker_artists(self, marker_id_i: int, time_s: float) -> None:
        """Move a drawn marker's line, label and time to a new time.

        Inputs:
            marker_id_i: id of the marker.
            time_s: the new time, in seconds.
        Outputs: none. Only the drawing changes; the stored markers are
            changed by the controller after the drag.
        """
        # LLFR-00086: the marker follows the mouse while dragged.
        artist_tuple = self.marker_artist_dict.get(marker_id_i)
        if artist_tuple is None:
            return
        line, label, time_text = artist_tuple
        line.set_xdata([time_s, time_s])
        label.xy = (time_s, 1.0)
        # LLFR-00093: the time shown follows the marker's position.
        time_text.set_text(format_time_text(time_s))
        self.place_markers()

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
            fitted_tuple = padded_range_tuple(
                low_f - margin_f, high_f + margin_f,
                max(CONSTANT_VALUE_HALF_RANGE_F,
                    abs(low_f) * VALUE_MARGIN_RATIO_F))
            # LLFR-00168: room for the Delta X brackets above their points.
            self.axes.set_ylim(*self.delta_headroom_range_tuple(
                fitted_tuple[0], fitted_tuple[1], start_s, end_s))
        self.place_tips()
        # LLFR-00082, LLFR-00084: markers follow the new range.
        self.place_markers()

    def place_tips(self) -> None:
        """Place the hover tip and the pinned tips around their points.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00042, LLFR-00045, LLFR-00179: every tip is placed again
        # after a change of range, size or drag.
        for index_i, annotation in enumerate(self.pinned_annotation_list):
            self.place_pinned_tip(index_i, annotation)
        if self.hover_point_tuple:
            self.place_tip_beside_point(self.hover_annotation)

    def place_tip_beside_point(self, annotation) -> None:
        """Turn a tip box towards the inside of the axes.

        Inputs:
            annotation: the matplotlib Annotation of a tip.
        Outputs: none.
        """
        # LLFR-00042, LLFR-00045: a tip near the right or top edge is
        # drawn on the other side of its point so it stays readable.
        start_s, end_s = self.axes.get_xlim()
        low_f, high_f = self.axes.get_ylim()
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

    def place_pinned_tip(self, tip_index_i: int, annotation,
                         renderer=None) -> None:
        """Place a pinned tip's label where the user put it, inside the axes.

        Inputs:
            tip_index_i: index of the tip in the list of set_pinned_tips.
            annotation: the matplotlib Annotation of the tip.
            renderer: the matplotlib renderer, or None for the canvas's.
        Outputs: none. Only the drawn position changes, never the stored
            offset.
        """
        # LLFR-00152: a moved tip's label keeps its offset from the
        # point, centred there, at any zoom or pan.
        offset_tuple = self.tip_label_offset_tuple(tip_index_i)
        if offset_tuple:
            annotation.set_position(offset_tuple)
            annotation.set_horizontalalignment("center")
            annotation.set_verticalalignment("center")
        else:
            # LLFR-00045: otherwise it is placed beside its point.
            self.place_tip_beside_point(annotation)
        # LLFR-00179: then it is moved into the axes when needed.
        self.keep_tip_inside_axes(annotation, renderer)

    def keep_tip_inside_axes(self, annotation, renderer=None) -> None:
        """Move a pinned tip's label the shortest way into the axes.

        Inputs:
            annotation: the matplotlib Annotation of the tip, already at
                the position the user gave it.
            renderer: the matplotlib renderer, or None for the canvas's.
        Outputs: none. A tip whose point is outside the shown range is
            left alone (matplotlib does not draw it).
        """
        # LLFR-00179: only tips whose point is shown are kept inside.
        if renderer is None:
            renderer = self.canvas.get_renderer()
        point_x_px, point_y_px = self.axes.transData.transform(
            annotation.xy)
        if not self.inside_axes_b(float(point_x_px), float(point_y_px)):
            return
        # LLFR-00151, LLFR-00179: the label box as drawn at the current
        # axes position; the leader line then joins it to the point.
        annotation.update_positions(renderer)
        box = self.tip_box_extent(annotation, renderer)
        axes_box = self.axes.bbox
        shift_x_px = inside_shift_px(float(box.x0), float(box.x1),
                                     float(axes_box.x0),
                                     float(axes_box.x1), False)
        shift_y_px = inside_shift_px(float(box.y0), float(box.y1),
                                     float(axes_box.y0),
                                     float(axes_box.y1), True)
        if shift_x_px == 0.0 and shift_y_px == 0.0:
            return
        # The offset is in points; the figure dpi already includes the
        # device pixel ratio, as for matplotlib's "offset points".
        pixels_per_point_f = self.pixels_per_point_f()
        position_x_f, position_y_f = annotation.get_position()
        annotation.set_position((
            float(position_x_f) + shift_x_px / pixels_per_point_f,
            float(position_y_f) + shift_y_px / pixels_per_point_f))
        annotation.update_positions(renderer)

    def on_canvas_resize(self, event) -> None:
        """Fit the legend again after the canvas changed size.

        Inputs:
            event: the matplotlib ResizeEvent.
        Outputs: none.
        """
        # LLFR-00035: the legend stays whole above the axes after resize.
        self.update_legend()
        # LLFR-00168, LLFR-00173: the room kept above the Delta X markers
        # is in points, so it is computed again for the new height.
        if self.delta_marker_data_list:
            self.apply_time_range()
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

    def pinned_tip_annotation(self, tip_index_i: int):
        """Return the annotation that draws a pinned tip.

        Inputs:
            tip_index_i: index in the list given to set_pinned_tips.
        Outputs: the matplotlib Annotation (its arrow_patch is the
            leader line), or None for an unknown index.
        """
        # LLFR-00151, LLFR-00152: for checks of the label and its line.
        if not 0 <= tip_index_i < len(self.pinned_annotation_list):
            return None
        return self.pinned_annotation_list[tip_index_i]

    def pinned_tip_text(self, tip_index_i: int) -> str:
        """Return the text shown by a pinned tip.

        Inputs:
            tip_index_i: index in the list given to set_pinned_tips.
        Outputs: the tip text, or "" for an unknown index.
        """
        # LLFR-00152: a moved tip keeps showing the same values.
        annotation = self.pinned_tip_annotation(tip_index_i)
        return annotation.get_text() if annotation is not None else ""

    def marker_count(self) -> int:
        """Return how many vertical markers are drawn.

        Inputs: none.
        Outputs: the number of markers in the plot.
        """
        # LLFR-00081, LLFR-00091: one line per marker.
        return len(self.marker_artist_dict)

    def marker_id_list(self) -> list:
        """Return the ids of the drawn markers, in placing order.

        Inputs: none.
        Outputs: a list of int.
        """
        # LLFR-00081: the markers given to set_markers.
        return [marker_tuple[0] for marker_tuple in self.marker_data_list]

    def marker_label_text(self, marker_id_i: int) -> str:
        """Return the text of a marker's label.

        Inputs:
            marker_id_i: id of the marker.
        Outputs: the name shown, or "" for an unknown id.
        """
        # LLFR-00084, LLFR-00112: the label shows the marker's name.
        artist_tuple = self.marker_artist_dict.get(marker_id_i)
        return artist_tuple[1].get_text() if artist_tuple else ""

    def marker_time_text(self, marker_id_i: int) -> str:
        """Return the time text shown below a marker's label.

        Inputs:
            marker_id_i: id of the marker.
        Outputs: the text, or "" for an unknown id.
        """
        # LLFR-00092, LLFR-00093: the marker's time in seconds.
        artist_tuple = self.marker_artist_dict.get(marker_id_i)
        return artist_tuple[2].get_text() if artist_tuple else ""

    def marker_time_s(self, marker_id_i: int) -> float:
        """Return the time at which a marker's line is drawn.

        Inputs:
            marker_id_i: id of the marker.
        Outputs: the time in seconds, or NaN for an unknown id.
        """
        # LLFR-00086: where the line is, also during a drag.
        artist_tuple = self.marker_artist_dict.get(marker_id_i)
        if artist_tuple is None:
            return float("nan")
        return float(artist_tuple[0].get_xdata()[0])

    def marker_artist_tuple(self, marker_id_i: int) -> tuple:
        """Return the artists of a marker.

        Inputs:
            marker_id_i: id of the marker.
        Outputs: a tuple (line, label, time_text), or () when unknown.
        """
        # LLFR-00082, LLFR-00084, LLFR-00092: for position checks.
        return self.marker_artist_dict.get(marker_id_i, ())

    def delta_marker_id_list(self) -> list:
        """Return the ids of the drawn delta markers, in placing order.

        Inputs: none.
        Outputs: a list of int.
        """
        # LLFR-00164, LLFR-00174: the markers given to set_delta_markers.
        return [marker_tuple[0]
                for marker_tuple in self.delta_marker_data_list]

    def delta_artist_tuple(self, delta_marker_id_i: int) -> tuple:
        """Return the artists of a delta marker.

        Inputs:
            delta_marker_id_i: id of the delta marker.
        Outputs: a tuple (bracket, leader lines, dots, value label), or
            () for an unknown id.
        """
        # LLFR-00168, LLFR-00170, LLFR-00172: for checks of the drawing.
        return self.delta_artist_dict.get(delta_marker_id_i, ())

    def delta_label_text(self, delta_marker_id_i: int) -> str:
        """Return the value text of a delta marker.

        Inputs:
            delta_marker_id_i: id of the delta marker.
        Outputs: the text, or "" for an unknown id.
        """
        # LLFR-00169, LLFR-00171: "Δt = ... s" or "Δy = ...".
        artist_tuple = self.delta_artist_dict.get(delta_marker_id_i)
        return artist_tuple[3].get_text() if artist_tuple else ""

    def delta_bracket_path(self, delta_marker_id_i: int):
        """Return a delta marker's bracket as it would be drawn now.

        Inputs:
            delta_marker_id_i: id of the delta marker.
        Outputs: a matplotlib Path in display pixels, or None for an
            unknown id.
        """
        # LLFR-00168, LLFR-00170, LLFR-00173: for position checks.
        artist_tuple = self.delta_artist_dict.get(delta_marker_id_i)
        if not artist_tuple:
            return None
        return artist_tuple[0].display_path()

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
            # LLFR-00151: only the label's box counts, not the leader
            # line (the annotation's own extent includes the line).
            if self.tip_box_extent(annotation, renderer).contains(
                    display_x_px, display_y_px):
                return index_i
        return NO_TIP_INDEX_I

    def tip_box_extent(self, annotation, renderer=None):
        """Return the display box of a tip's label, as drawn now.

        Inputs:
            annotation: the matplotlib Annotation of a tip.
            renderer: the canvas renderer, or None to get it.
        Outputs: a matplotlib Bbox in display pixels.
        """
        # LLFR-00046, LLFR-00152: the box follows the label's latest
        # position, even before the canvas is drawn again.
        if renderer is None:
            renderer = self.canvas.get_renderer()
        bbox_patch = annotation.get_bbox_patch()
        if bbox_patch is None:
            return annotation.get_window_extent(renderer)
        annotation.update_bbox_position_size(renderer)
        return bbox_patch.get_window_extent(renderer)

    def marker_at(self, widget_point) -> int:
        """Return the id of the vertical marker under a point.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: the marker id, or -1 when no marker is there. A marker
            is hit within PICK_TOLERANCE_PIXELS_I of its line inside the
            axes, or on its label or time text.
        """
        # LLFR-00081, LLFR-00086, LLFR-00087, LLFR-00110: hit test in
        # display pixels; the last placed marker is on top.
        display_x_px, display_y_px = self.widget_to_display_tuple(
            widget_point)
        tolerance_px = PICK_TOLERANCE_PIXELS_I * self.pixel_ratio_f()
        inside_b = self.inside_axes_b(display_x_px, display_y_px)
        renderer = self.canvas.get_renderer()
        for marker_id_i in reversed(self.marker_id_list()):
            artist_tuple = self.marker_artist_dict.get(marker_id_i)
            if artist_tuple is None:
                continue
            line, label, time_text = artist_tuple
            if not line.get_visible():
                continue
            line_x_px = float(self.axes.transData.transform(
                (float(line.get_xdata()[0]), 0.0))[0])
            if inside_b and abs(line_x_px - display_x_px) <= tolerance_px:
                return marker_id_i
            for text in (label, time_text):
                if text.get_window_extent(renderer).contains(
                        display_x_px, display_y_px):
                    return marker_id_i
        return NO_MARKER_ID_I

    def delta_marker_at(self, widget_point) -> int:
        """Return the id of the delta marker under a point.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: the delta marker id, or -1 when none is there. A delta
            marker is hit within PICK_TOLERANCE_PIXELS_I of its bracket,
            its leader lines or its dots inside the axes, or on its
            value label.
        """
        # LLFR-00175, LLFR-00177: hit test in display pixels; the last
        # placed marker is on top.
        display_x_px, display_y_px = self.widget_to_display_tuple(
            widget_point)
        if not self.inside_axes_b(display_x_px, display_y_px):
            return NO_DELTA_MARKER_ID_I
        tolerance_px = PICK_TOLERANCE_PIXELS_I * self.pixel_ratio_f()
        renderer = self.canvas.get_renderer()
        for delta_marker_id_i in reversed(self.delta_marker_id_list()):
            artist_tuple = self.delta_artist_dict.get(delta_marker_id_i)
            if not artist_tuple:
                continue
            bracket, leader, dots, label = artist_tuple
            for patch in (bracket, leader):
                if delta_geometry.path_distance_px(
                        patch.display_path(), display_x_px,
                        display_y_px) <= tolerance_px:
                    return delta_marker_id_i
            dot_px_array = self.axes.transData.transform(np.column_stack(
                (dots.get_xdata(), dots.get_ydata())))
            if np.any(np.hypot(dot_px_array[:, 0] - display_x_px,
                               dot_px_array[:, 1] - display_y_px)
                      <= tolerance_px):
                return delta_marker_id_i
            if self.tip_box_extent(label, renderer).contains(
                    display_x_px, display_y_px):
                return delta_marker_id_i
        return NO_DELTA_MARKER_ID_I

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

        # LLFR-00046: a pinned tip has priority over a curve under it
        # (and over a marker: tips are drawn on top of markers).
        tip_index_i = self.pinned_tip_at(widget_point)
        if tip_index_i >= 0:
            add_request_action(
                menu, "Delete",
                lambda index_i=tip_index_i:
                self.pinned_tip_delete_requested.emit(index_i))
            return menu, request_list
        # LLFR-00110: a marker has priority over a curve under it.
        # LLFR-00087, LLFR-00090: whatever plot tool is active.
        marker_id_i = self.marker_at(widget_point)
        if marker_id_i != NO_MARKER_ID_I:
            add_request_action(
                menu, "Rename",
                lambda chosen_id_i=marker_id_i:
                self.marker_rename_requested.emit(chosen_id_i))
            add_request_action(
                menu, "Delete",
                lambda chosen_id_i=marker_id_i:
                self.marker_delete_requested.emit(chosen_id_i))
            return menu, request_list
        # LLFR-00175, LLFR-00177: a delta marker has priority over a
        # curve under it, whatever plot tool is active.
        delta_marker_id_i = self.delta_marker_at(widget_point)
        if delta_marker_id_i != NO_DELTA_MARKER_ID_I:
            add_request_action(
                menu, "Delete",
                lambda chosen_id_i=delta_marker_id_i:
                self.delta_marker_delete_requested.emit(chosen_id_i))
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
        # LLFR-00048: empty area of the plot (no curve, pinned tip,
        # vertical marker or delta marker under the mouse).
        add_request_action(menu, "Delete plot",
                           lambda: self.plot_delete_requested.emit())
        return menu, request_list

    def build_context_menu(self, widget_point) -> QMenu:
        """Build the menu that a right-click at a point shows.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: a QMenu (not shown) whose actions emit their request
            when triggered. On a pinned tip it has "Delete"; on a marker
            "Rename" and "Delete"; on a delta marker "Delete"; on a
            curve "Delete signal" and a "Width" submenu with 1..5;
            elsewhere "Delete plot".
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
        # LLFR-00038, LLFR-00046, LLFR-00048. LLFR-00138: nor once the
        # widget was removed by an undo or a file replace.
        if sip.isdeleted(self) or self.retired_b:
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
            zoom_click_at); with the Vertical marker tool, emits
            marker_place_requested unless the click is on a marker;
            with the Delta X or Delta Y tool, emits delta_point_picked
            when the click is on a curve.
        """
        # LLFR-00109: using a tool never changes the active tool.
        if is_delta_tool(self.plot_tool_str):
            # LLFR-00163, LLFR-00164: pick a point of a delta marker.
            self.delta_click_at(widget_point)
            return
        if self.plot_tool_str == ZOOM_TOOL_STR:
            # LLFR-00078: click to zoom.
            self.zoom_click_at(widget_point)
            return
        if self.plot_tool_str == MARKER_TOOL_STR:
            # LLFR-00081: place a marker at the clicked time.
            self.marker_click_at(widget_point)
            return
        # LLFR-00045: pin the point of the hover tip that is shown.
        if self.plot_tool_str != TIP_TOOL_STR or not self.hover_point_tuple:
            return
        signal_name_str, time_s, value_f = self.hover_point_tuple
        self.tip_pin_requested.emit(signal_name_str, time_s, value_f)

    def delta_click_at(self, widget_point) -> None:
        """Report the curve sample nearest to a click with a delta tool.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none. Emits delta_point_picked, as the last step, when
            the click is on a curve; a click off every curve does
            nothing and shows nothing (LLFR-00165).
        """
        # LLFR-00163, LLFR-00164: the sample of the curve under the
        # mouse that is nearest to it, within the pick tolerance.
        nearest_tuple = self.nearest_curve_tuple(widget_point)
        if not nearest_tuple:
            return
        # The receiver redraws this widget, so this is the last step.
        self.delta_point_picked.emit(*nearest_tuple)

    def marker_click_at(self, widget_point) -> None:
        """Ask for a new marker at the time of a clicked point.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none. Emits marker_place_requested with the time, unless
            the click is outside the axes or on an existing marker.
        """
        # LLFR-00081: only a click on the axes, and not on a marker.
        display_x_px, display_y_px = self.widget_to_display_tuple(
            widget_point)
        if not self.inside_axes_b(display_x_px, display_y_px):
            return
        if self.marker_at(widget_point) != NO_MARKER_ID_I:
            return
        self.marker_place_requested.emit(self.time_at(widget_point))

    def press_at(self, widget_point) -> None:
        """Do what a left press at a point does with the active tool.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none. A press on a pinned tip starts moving it, with any
            tool or none; with the Vertical marker tool, a press on a
            marker starts dragging it; any other press is a click
            (click_at).
        """
        # LLFR-00086, LLFR-00152: a drag whose release was lost (no move
        # came after it) is dropped; the item stays where it was.
        self.cancel_tip_drag()
        self.cancel_marker_drag()
        # LLFR-00153: a pinned tip is on top of everything else, so a
        # press on it moves it and never pins, zooms or places a marker.
        tip_index_i = self.pinned_tip_at(widget_point)
        if tip_index_i != NO_TIP_INDEX_I:
            self.tip_press_at(widget_point, tip_index_i)
            return
        # LLFR-00086: a press on a marker starts a drag and does nothing
        # else (no new marker, no zoom, no pin).
        if self.plot_tool_str == MARKER_TOOL_STR:
            marker_id_i = self.marker_at(widget_point)
            if marker_id_i != NO_MARKER_ID_I:
                # LLFR-00203: no preview while a marker is dragged.
                self.leave_marker_preview()
                self.drag_marker_id_i = marker_id_i
                self.drag_time_s = self.marker_time_s(marker_id_i)
                self.drag_moved_b = False
                self.drag_press_x_i = widget_point.x()
                self.drag_offset_s = (self.drag_time_s
                                      - self.time_at(widget_point))
                return
        self.click_at(widget_point)

    def drag_time_s_at(self, widget_point) -> float:
        """Return the time a dragged marker takes for a mouse point.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: the time under the point plus the grab offset, in
            seconds, clamped to the time range shown, so the marker never
            leaves the plot.
        """
        # LLFR-00086: the marker moves along the x-axis with the mouse.
        start_s, end_s = sorted(self.time_range_tuple())
        time_s = self.time_at(widget_point) + self.drag_offset_s
        return min(max(time_s, start_s), end_s)

    def drag_to(self, widget_point) -> None:
        """Move the dragged marker to the time under a point.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none. Does nothing when no marker is dragged.
        """
        # LLFR-00086, LLFR-00093: line, label and time follow the mouse.
        if self.drag_marker_id_i == NO_MARKER_ID_I:
            return
        # LLFR-00086: until the mouse leaves the pressed pixel column,
        # nothing moves (a press and release is not a drag).
        if not self.drag_moved_b and widget_point.x() == self.drag_press_x_i:
            return
        time_s = self.drag_time_s_at(widget_point)
        if time_s == self.drag_time_s:
            return
        self.drag_time_s = time_s
        self.drag_moved_b = True
        self.move_marker_artists(self.drag_marker_id_i, time_s)
        self.canvas.draw_idle()
        # LLFR-00205: the other plots of the tab show the marker here.
        self.marker_drag_moved.emit(self.drag_marker_id_i, time_s)

    def release_at(self, widget_point) -> None:
        """End a marker drag at a point.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none. Emits marker_move_requested once, as the last
            step, when the marker was moved; a press and release without
            movement emits nothing.
        """
        # LLFR-00086: the marker is left where the button is released.
        if self.drag_marker_id_i == NO_MARKER_ID_I:
            return
        self.drag_to(widget_point)
        self.finish_marker_drag()

    def finish_marker_drag(self) -> None:
        """End a marker drag at the marker's last shown position.

        Inputs: none.
        Outputs: none. Emits marker_move_requested once, as the last
            step, when the marker was moved.
        """
        # LLFR-00086: also used when the release was lost, so that the
        # marker stays where the user last saw it.
        if self.drag_marker_id_i == NO_MARKER_ID_I:
            return
        marker_id_i = self.drag_marker_id_i
        time_s = self.drag_time_s
        moved_b = self.drag_moved_b
        # The drawn marker stays where it was released; the controller
        # redraws it there from the model.
        self.drag_marker_id_i = NO_MARKER_ID_I
        self.drag_moved_b = False
        if moved_b:
            # The receiver may redraw (or delete) this widget, so this is
            # the very last step.
            self.marker_move_requested.emit(marker_id_i, time_s)

    def cancel_marker_drag(self) -> None:
        """Forget the marker drag in progress, if any.

        Inputs: none.
        Outputs: none. The stored markers are drawn again where they
            were, if a dragged marker was moved.
        """
        # LLFR-00086: without a release, the marker is not moved.
        moved_b = (self.drag_marker_id_i != NO_MARKER_ID_I
                   and self.drag_moved_b)
        marker_id_i = self.drag_marker_id_i
        self.drag_marker_id_i = NO_MARKER_ID_I
        self.drag_moved_b = False
        if moved_b:
            self.draw_markers()
            self.canvas.draw_idle()
            # LLFR-00205: the other plots of the tab show it back at its
            # stored time.
            for stored_id_i, _, stored_time_s in self.marker_data_list:
                if stored_id_i == marker_id_i:
                    self.marker_drag_moved.emit(marker_id_i, stored_time_s)

    def tip_label_offset_tuple(self, tip_index_i: int) -> tuple:
        """Return the label offset a pinned tip is drawn with now.

        Inputs:
            tip_index_i: index in the list given to set_pinned_tips.
        Outputs: the offset (x, y) in points from the point to the
            label's center, or () when the label is placed
            automatically.
        """
        # LLFR-00152: during a drag, the dragged position is shown.
        if (tip_index_i == self.drag_tip_index_i and self.tip_drag_moved_b
                and self.tip_drag_offset_tuple):
            return self.tip_drag_offset_tuple
        if 0 <= tip_index_i < len(self.pinned_tip_list):
            return self.pinned_tip_list[tip_index_i][3]
        return ()

    def tip_label_center_tuple(self, tip_index_i: int) -> tuple:
        """Return the center of a pinned tip's label box.

        Inputs:
            tip_index_i: index in the list given to set_pinned_tips.
        Outputs: a tuple (x, y) in display pixels, or () for an unknown
            index.
        """
        # LLFR-00152: the label is grabbed and moved by its center.
        annotation = self.pinned_tip_annotation(tip_index_i)
        if annotation is None:
            return ()
        extent = self.tip_box_extent(annotation)
        return ((float(extent.x0) + float(extent.x1)) / 2.0,
                (float(extent.y0) + float(extent.y1)) / 2.0)

    def pixels_per_point_f(self) -> float:
        """Return how many display pixels one typographic point takes.

        Inputs: none.
        Outputs: the figure's dots per inch divided by 72.
        """
        # LLFR-00152: label offsets are kept in points, as matplotlib's
        # "offset points", so they do not depend on the zoom.
        return float(self.figure.dpi) / POINTS_PER_INCH_F

    def tip_press_at(self, widget_point, tip_index_i: int) -> None:
        """Start moving a pinned tip's label from a pressed point.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
            tip_index_i: index of the pressed tip.
        Outputs: none. Nothing moves until the mouse moves.
        """
        # LLFR-00152, LLFR-00153: grab the label where it is, whatever
        # plot tool is active.
        center_tuple = self.tip_label_center_tuple(tip_index_i)
        if not center_tuple:
            return
        pointer_x_px, pointer_y_px = self.widget_to_display_tuple(
            widget_point)
        self.hide_hover_tip()
        self.drag_tip_index_i = tip_index_i
        self.tip_press_point = QPoint(widget_point)
        self.tip_grab_offset_tuple = (center_tuple[0] - pointer_x_px,
                                      center_tuple[1] - pointer_y_px)
        self.tip_drag_offset_tuple = ()
        self.tip_drag_moved_b = False

    def tip_drag_to(self, widget_point) -> None:
        """Move the dragged pinned tip's label with the mouse pointer.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none. The label's center stays inside the axes; the
            point, values and leader line end stay the same. Does
            nothing when no tip is dragged.
        """
        # LLFR-00152: until the mouse leaves the pressed pixel, nothing
        # moves (a press and release is not a drag).
        if self.drag_tip_index_i == NO_TIP_INDEX_I:
            return
        if not self.tip_drag_moved_b and widget_point == self.tip_press_point:
            return
        annotation = self.pinned_tip_annotation(self.drag_tip_index_i)
        if annotation is None:
            self.reset_tip_drag()
            return
        pointer_x_px, pointer_y_px = self.widget_to_display_tuple(
            widget_point)
        axes_box = self.axes.bbox
        # HLFR-00041: the label is moved to another place in the plot,
        # so its center never leaves the axes.
        center_x_px = min(max(pointer_x_px + self.tip_grab_offset_tuple[0],
                              float(axes_box.x0)), float(axes_box.x1))
        center_y_px = min(max(pointer_y_px + self.tip_grab_offset_tuple[1],
                              float(axes_box.y0)), float(axes_box.y1))
        point_x_px, point_y_px = self.axes.transData.transform(
            annotation.xy)
        pixels_per_point_f = self.pixels_per_point_f()
        offset_tuple = ((center_x_px - float(point_x_px))
                        / pixels_per_point_f,
                        (center_y_px - float(point_y_px))
                        / pixels_per_point_f)
        if self.tip_drag_moved_b and offset_tuple == (
                self.tip_drag_offset_tuple):
            return
        self.tip_drag_offset_tuple = offset_tuple
        self.tip_drag_moved_b = True
        # LLFR-00151: the leader line follows the label when drawn.
        self.place_tips()
        self.canvas.draw_idle()

    def tip_release_at(self, widget_point) -> None:
        """End a pinned tip drag at the point where the button was released.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none. Emits pinned_tip_move_requested once, as the last
            step, when the label was moved.
        """
        # LLFR-00152: the tip is left where the button is released.
        if self.drag_tip_index_i == NO_TIP_INDEX_I:
            return
        self.tip_drag_to(widget_point)
        self.finish_tip_drag()

    def finish_tip_drag(self) -> None:
        """End a pinned tip drag at the label's last shown position.

        Inputs: none.
        Outputs: none. Emits pinned_tip_move_requested once, as the last
            step, when the label was moved; a press and release without
            movement emits nothing.
        """
        # LLFR-00152: also used when the release was lost.
        if self.drag_tip_index_i == NO_TIP_INDEX_I:
            return
        tip_index_i = self.drag_tip_index_i
        offset_tuple = self.tip_drag_offset_tuple
        moved_b = self.tip_drag_moved_b and bool(offset_tuple)
        if moved_b and 0 <= tip_index_i < len(self.pinned_tip_list):
            # The drawn label stays where it was released until the
            # controller draws the tips again from the model.
            name_str, time_s, value_f, _ = self.pinned_tip_list[tip_index_i]
            self.pinned_tip_list[tip_index_i] = (name_str, time_s, value_f,
                                                 offset_tuple)
        self.reset_tip_drag()
        if moved_b:
            # The receiver may redraw (or delete) this widget, so this is
            # the very last step.
            self.pinned_tip_move_requested.emit(
                tip_index_i, offset_tuple[0], offset_tuple[1])

    def cancel_tip_drag(self) -> None:
        """Forget the pinned tip drag in progress, if any.

        Inputs: none.
        Outputs: none. A moved label goes back to where it was.
        """
        # LLFR-00152: without a release, the tip is not moved.
        moved_b = (self.drag_tip_index_i != NO_TIP_INDEX_I
                   and self.tip_drag_moved_b)
        self.reset_tip_drag()
        if moved_b:
            self.place_tips()
            self.canvas.draw_idle()

    def reset_tip_drag(self) -> None:
        """Clear the state of a pinned tip drag without redrawing.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00152: no pinned tip is being moved.
        self.drag_tip_index_i = NO_TIP_INDEX_I
        self.tip_drag_offset_tuple = ()
        self.tip_drag_moved_b = False

    def cancel_drags(self) -> None:
        """Stop any pan, marker drag or pinned tip drag in progress.

        Inputs: none.
        Outputs: none. Nothing is emitted; dragged items go back.
        """
        # LLFR-00117, LLFR-00086, LLFR-00152: a right press during a drag
        # cancels it before the menu is handled.
        self.panning_b = False
        self.cancel_marker_drag()
        self.cancel_tip_drag()

    def is_mouse_drag_in_progress(self) -> bool:
        """Tell whether the user is dragging the mouse on this plot.

        Inputs: none.
        Outputs: True during a pan (LLFR-00117), a marker drag
            (LLFR-00086), a pinned tip drag (LLFR-00152) or a time span
            selection (LLFR-00208, flag time_span_drag_b), from the
            press to the release.
        """
        # LLFR-00207: the Z key does nothing while one of these drags is
        # in progress. A new kind of drag only has to be added here.
        return (self.panning_b
                or self.drag_marker_id_i != NO_MARKER_ID_I
                or self.drag_tip_index_i != NO_TIP_INDEX_I
                or self.time_span_drag_b)

    def retire(self) -> None:
        """Stop all interaction before the widget is removed.

        Inputs: none.
        Outputs: none. Any pan, marker drag or pinned tip drag in
            progress is dropped without a redraw, a deferred context
            menu is not shown, and the widget emits no request from now
            on, so that a late mouse release on it is not applied to the
            plot that replaced it.
        """
        # LLFR-00138, LLFR-00086, LLFR-00152: after an undo (or a file
        # replace), the plots are drawn again on new widgets with the
        # same plot ids, and this widget is only deleted later by the
        # event loop; a move it still sent would change the restored
        # plot and be recorded as a new undoable action.
        # LLFR-00117: a pan in progress only changed the view; it stops.
        self.panning_b = False
        self.drag_marker_id_i = NO_MARKER_ID_I
        self.drag_moved_b = False
        self.reset_tip_drag()
        # LLFR-00203: a removed plot shows no preview.
        self.preview_time_s = None
        # LLFR-00207, LLFR-00208: a time span selection stops too, so a
        # removed plot never blocks the Z key.
        self.time_span_drag_b = False
        # LLFR-00038, LLFR-00046, LLFR-00048: no menu for a removed plot.
        self.retired_b = True
        self.blockSignals(True)

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
        """Narrow the time axis to 95%, centred on the clicked time.

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
        # LLFR-00078: 95% of the width, centred on the click.
        half_width_s = (end_s - start_s) * CLICK_ZOOM_FACTOR_F / 2.0
        self.zoom_to_range(center_s - half_width_s, center_s + half_width_s)

    def wheel_at(self, widget_point, step_f: float) -> None:
        """Zoom the time axis around a point, as the mouse wheel does.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
            step_f: wheel notches; positive (forward) zooms in, negative
                (backward) zooms out; a fraction zooms in proportion.
        Outputs: none. Emits time_range_changed with the new range.
        """
        # LLFR-00074: zoom around the time under the mouse.
        # LLFR-00113: each notch keeps 95% of the width (0.95 ** steps).
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

    def pan_press_at(self, widget_point) -> None:
        """Start a pan with the wheel button pressed at a point.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none. Nothing starts while a marker is being dragged.
        """
        # LLFR-00117: the time under the pointer is held under it while
        # the mouse moves; any plot tool, or none, may be active.
        # LLFR-00086, LLFR-00152: not while a marker or tip is dragged.
        if (self.drag_marker_id_i != NO_MARKER_ID_I
                or self.drag_tip_index_i != NO_TIP_INDEX_I):
            return
        self.panning_b = True
        self.pan_anchor_s = self.time_at(widget_point)
        # LLFR-00042: a pan is not a hover over a curve.
        self.hide_hover_tip()

    def pan_to(self, widget_point) -> None:
        """Shift the time range so the grabbed time is under a point.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none. Emits time_range_changed when the range moved,
            so that the whole tab follows (LLFR-00070). Does nothing
            when no pan is in progress.
        """
        # LLFR-00117: the curves follow the pointer horizontally.
        if not self.panning_b:
            return
        start_s, end_s = self.time_range_tuple()
        width_s = end_s - start_s
        full_start_s, full_end_s = self.full_time_range_tuple()
        full_width_s = full_end_s - full_start_s
        # LLFR-00118: at the whole time range there is nothing to pan.
        if width_s >= full_width_s * (1.0 - FULL_RANGE_TOLERANCE_F):
            return
        # The shift is computed first, so a pointer back at the press
        # point gives exactly no shift (start + a - a can differ from
        # start in floating point and would report a false pan).
        new_start_s = start_s + (self.pan_anchor_s - self.time_at(
            widget_point))
        # LLFR-00119: never before the first or after the last sample;
        # the width is kept.
        new_start_s = min(max(new_start_s, full_start_s),
                          full_end_s - width_s)
        # A shift far below one pixel is floating-point noise of the
        # pixel-to-time conversion, not a move of the pointer.
        if abs(new_start_s - start_s) <= width_s * FULL_RANGE_TOLERANCE_F:
            return
        new_end_s = new_start_s + width_s
        # LLFR-00120: apply_time_range fits y to the new range.
        self.time_range_s_tuple = (new_start_s, new_end_s)
        self.apply_time_range()
        # draw_idle merges the redraws of fast mouse moves into one.
        self.canvas.draw_idle()
        # LLFR-00070: the plot panel shares the range with the tab.
        self.time_range_changed.emit(new_start_s, new_end_s)

    def pan_release_at(self, widget_point) -> None:
        """End a pan at the point where the wheel button was released.

        Inputs:
            widget_point: QPoint in this widget's coordinates.
        Outputs: none.
        """
        # LLFR-00117: the last move is applied, then the pan ends.
        if not self.panning_b:
            return
        self.pan_to(widget_point)
        self.panning_b = False

    # ----------------------------------------------------------------
    # matplotlib event handlers
    # ----------------------------------------------------------------

    def on_mouse_move(self, event) -> None:
        """Handle a matplotlib mouse move on the canvas.

        Inputs:
            event: the matplotlib MouseEvent.
        Outputs: none.
        """
        # LLFR-00086, LLFR-00093: a move with a marker held drags it.
        widget_point = self.display_to_widget_point(event.x, event.y)
        # LLFR-00117: a move with the wheel button held pans. A pan whose
        # release was lost just stops.
        if self.panning_b:
            if not mouse_button_held_b(event, Qt.MouseButton.MiddleButton):
                self.panning_b = False
                return
            self.pan_to(widget_point)
            # LLFR-00203: the preview stays at the time under the pointer.
            self.update_marker_preview(widget_point)
            return
        # LLFR-00152: a move with a pinned tip held moves its label. A
        # lost release leaves it at its last shown position.
        if self.drag_tip_index_i != NO_TIP_INDEX_I:
            if not mouse_button_held_b(event, Qt.MouseButton.LeftButton):
                self.finish_tip_drag()
                return
            self.tip_drag_to(widget_point)
            return
        if self.drag_marker_id_i != NO_MARKER_ID_I:
            # LLFR-00086: a lost release leaves the marker at its last
            # shown position.
            if not mouse_button_held_b(event, Qt.MouseButton.LeftButton):
                self.finish_marker_drag()
                return
            self.drag_to(widget_point)
            return
        # LLFR-00042: any other move runs the hover code.
        self.hover_at(widget_point)
        # LLFR-00203: and moves the marker preview with the pointer.
        self.update_marker_preview(widget_point)

    def on_mouse_press(self, event) -> None:
        """Handle a matplotlib mouse press on the canvas.

        Inputs:
            event: the matplotlib MouseEvent.
        Outputs: none.
        """
        # LLFR-00137: any press on the plot gives it the keyboard focus,
        # so that Ctrl+Z (Cmd+Z) is not taken by a text field.
        self.canvas.setFocus(Qt.FocusReason.MouseFocusReason)
        widget_point = self.display_to_widget_point(event.x, event.y)
        # LLFR-00117: the wheel button starts a pan, with any tool, and
        # never zooms, pins, places or grabs a marker, or opens a menu.
        if event.button == MouseButton.MIDDLE:
            self.pan_press_at(widget_point)
            return
        if event.button == MouseButton.RIGHT:
            # LLFR-00117, LLFR-00086, LLFR-00152: a right press cancels a
            # pan or drag in progress before the menu logic runs.
            self.cancel_drags()
            # LLFR-00038, LLFR-00046, LLFR-00048: show the menu once this
            # press has been handled (not for the second press of a
            # double-click).
            if not event.dblclick:
                self.request_context_menu(widget_point)
            return
        # LLFR-00117: the left button does nothing while panning.
        if self.panning_b:
            return
        # LLFR-00045, LLFR-00078: the second press of a double-click must
        # not pin the same tip again nor zoom a second time.
        if event.dblclick:
            return
        if event.button == MouseButton.LEFT:
            # LLFR-00153: a press on a pinned tip moves it; LLFR-00045: a
            # left click pins the shown tip; LLFR-00078: with the Zoom
            # tool it zooms in; LLFR-00081, LLFR-00086: with the Vertical
            # marker tool it places or grabs a marker.
            self.press_at(widget_point)

    def on_mouse_release(self, event) -> None:
        """Handle a matplotlib mouse release on the canvas.

        Inputs:
            event: the matplotlib MouseEvent.
        Outputs: none.
        """
        widget_point = self.display_to_widget_point(event.x, event.y)
        # LLFR-00117: releasing the wheel button ends a pan.
        if event.button == MouseButton.MIDDLE:
            self.pan_release_at(widget_point)
            return
        # LLFR-00086: releasing the left button leaves a dragged marker.
        if event.button != MouseButton.LEFT:
            return
        # LLFR-00152: or a dragged pinned tip.
        if self.drag_tip_index_i != NO_TIP_INDEX_I:
            self.tip_release_at(widget_point)
            return
        self.release_at(widget_point)

    def on_mouse_scroll(self, event) -> None:
        """Handle a matplotlib scroll on the canvas.

        Inputs:
            event: the matplotlib MouseEvent of the wheel.
        Outputs: none.
        """
        # LLFR-00074, LLFR-00108: the wheel runs the zoom code with any
        # tool. LLFR-00113: the notches come from Qt's rotation angle.
        widget_point = self.display_to_widget_point(event.x, event.y)
        self.wheel_at(widget_point, wheel_step_f(event))
        # LLFR-00203: after a zoom, another time is under the pointer.
        self.update_marker_preview(widget_point)

    def eventFilter(self, watched, event) -> bool:
        """Zoom on a Shift+wheel turned sideways, which matplotlib drops.

        Inputs:
            watched: the object the event is sent to (the canvas).
            event: the QEvent.
        Outputs: True only for a sideways Shift+wheel on the canvas, which
            is then handled here; False for every other event.
        """
        # LLFR-00154, LLFR-00074, LLFR-00108: holding Shift (the marker
        # key) still zooms with the wheel; matplotlib only reads the
        # vertical wheel, so this case never reaches on_mouse_scroll.
        if (event.type() == QEvent.Type.Wheel and watched is self.canvas
                and is_shift_horizontal_wheel(event)):
            widget_point = self.mapFrom(self.canvas,
                                        event.position().toPoint())
            self.wheel_at(widget_point, float(event.angleDelta().x())
                          / WHEEL_NOTCH_EIGHTHS_I)
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def on_mouse_leave(self, event) -> None:
        """Hide the hover tip when the mouse leaves the canvas.

        Inputs:
            event: the matplotlib LocationEvent.
        Outputs: none.
        """
        # LLFR-00042: no curve under the mouse, no tip.
        self.hide_hover_tip()
        # LLFR-00203: the pointer left the plot's drawing area.
        self.leave_marker_preview()

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
        # LLFR-00021: accept signal drags, ignore anything else. The drop
        # is always a copy, also with Shift or Cmd held (LLFR-00154), so
        # the signal list never removes the dragged name.
        if self.signal_name_from_mime(event.mimeData()):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        """Keep accepting a signal drag while it moves over the plot.

        Inputs:
            event: the QDragMoveEvent.
        Outputs: none.
        """
        # LLFR-00021: same rule as on enter, always as a copy.
        if self.signal_name_from_mime(event.mimeData()):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
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
        # LLFR-00021: a copy, never a move (see dragEnterEvent).
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()
        self.signal_dropped.emit(signal_name_str)
